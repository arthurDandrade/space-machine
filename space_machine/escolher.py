"""Etapa "escolher": escolhe os assets de um bloco com chamadas isoladas ao Claude (uma por asset),
grava escolhas.json, baixa (finalizar.py --asset) e confere.

Substituiu o subagente escolher-assets (~6× menos tokens por asset; o subagente saiu em 2026-10-13).

Uso:
  python -m space_machine escolher <bloco> [--asset ID ...] [--modelo haiku] [--sem-finalizar] [--sem-conferir]
  python -m space_machine escolher <bloco> --sombra      # refaz as escolhas que já existem em escolhas_estudio.json
                                                   # e compara com as que já existem (nada é baixado)
"""
import argparse
import json
import re
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import motor_claude as motor
from .canal import canal_do_bloco, contexto, gravar_json, ler_json, rodar_script

TIPOS_IMAGEM = ("foto", "historica", "recorte", "logo", "mapa", "bandeira")
MARGEM_VIDEO = 1.0          # finalizar.py baixa duração + video_margem_s (1 s)

S_IMAGEM = {"type": "object", "additionalProperties": False, "properties": {
    "n": {"type": "integer"}, "recortar": {"type": "boolean"}, "conferir": {"type": "string", "maxLength": 140},
    "pular": {"type": "boolean"}, "motivo": {"type": "string"},
    "nova_busca": {"type": "array", "items": {"type": "string"}, "maxItems": 3}}}
S_VIDEO = {"type": "object", "additionalProperties": False, "properties": {
    "n": {"type": "integer"}, "inicio": {"type": "number"}, "conferir": {"type": "string", "maxLength": 140},
    "detalhar": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
    "pular": {"type": "boolean"}, "motivo": {"type": "string"},
    "nova_busca": {"type": "array", "items": {"type": "string"}, "maxItems": 3}}}
S_CONFIRMAR = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {
    "ok": {"type": "boolean"}, "n": {"type": "integer"}, "inicio": {"type": "number"},
    "conferir": {"type": "string", "maxLength": 140}}}
S_CONFERIR = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {
    "ok": {"type": "boolean"}, "problema": {"type": "string"}, "detalhe": {"type": "string"}}}


def _do_youtube(c):
    return c.get("fonte") == "youtube" or "youtube.com" in str(c.get("url", ""))


class Bloco:
    def __init__(self, caminho, sombra=False, modelo=None):
        self.p = Path(caminho).resolve()
        self.slug, self.c = canal_do_bloco(self.p)
        self.ctx = contexto(self.p)
        self.cfg = motor.config()
        self.sombra = sombra
        self.modelo = modelo
        self.plano = ler_json(self.p / "plano.json")
        if not self.plano:
            raise SystemExit(f"{self.p}: sem plano.json (rode o storyboard/compilar antes)")
        self.palavras = ler_json(self.p / "_work" / "palavras.json", [])
        self.arq_escolhas = self.p / ("escolhas_estudio.json" if sombra else "escolhas.json")
        self.escolhas = ler_json(self.arq_escolhas, {})
        self.originais = ler_json(self.p / "escolhas.json", {})
        (self.p / "_estudio").mkdir(exist_ok=True)
        self.log = self.p / "_estudio" / "log_escolher.txt"
        self.trava = threading.Lock()
        self.notas = []          # linhas do resumo final
        self.parou_por_limite = False
        self.obs = ""            # observação de quem produz, vai junto em todo pedido (--obs)

    # ---------- dados ----------
    def assets(self):
        for item in self.plano.get("itens", []):
            if item.get("titulo_asset"):
                yield item, None, item["titulo_asset"]
            for cena in item.get("cenas", []):
                for a in cena.get("assets", []):
                    yield item, cena, a

    def fala(self, item, cena):
        ini, fim = (cena or item).get("inicio", 0), (cena or item).get("fim", 0)
        if cena is None:
            fim = min(fim, ini + 6)
        txt = " ".join(w["p"] for w in self.palavras if ini - 0.05 <= w["ini"] < fim)
        return txt or (cena or {}).get("fala", "")

    def candidatos(self, aid):
        """candidatos.json sem os candidatos do YouTube (removido do sistema em 2026-10-11: blocos antigos
        ainda guardam vídeos do YouTube que não podem mais ser baixados)."""
        meta = ler_json(self.p / "_work" / "candidatos" / aid / "candidatos.json")
        if meta:
            meta["candidatos"] = [c for c in meta.get("candidatos", []) if not _do_youtube(c)]
        return meta

    def gravar(self, aid, escolha):
        with self.trava:
            self.escolhas[aid] = escolha
            gravar_json(self.arq_escolhas, self.escolhas)

    def registrar(self, texto):
        with self.trava:
            with open(self.log, "a") as f:
                f.write(texto + "\n")

    # ---------- texto do pedido ----------
    def pedido(self, item, cena, a, meta):
        linhas = [f"Asset {a['id']} · tipo {a['tipo']} · papel {a.get('papel', 'card')} · "
                  f"orientação {a.get('orientacao', 'paisagem')}"
                  + (f" · duração do trecho {a.get('duracao', 4)} s" if a["tipo"] == "video" else ""),
                  f"Vídeo: {self.plano.get('titulo', '')} — tópico: {item.get('nome', '')}",
                  f"Pedido: {a.get('descricao', '')}",
                  f"Fala da cena: \"{self.fala(item, cena)}\" (gatilho: \"{a.get('gatilho', '')}\")",
                  "Buscas já feitas: " + "; ".join(a.get("buscas", [])[:6])]
        # o que mais entra na mesma cena (logo/sticker por cima, card ao lado): sem isso a escolha isolada
        # aceitou um snapper do Jets debaixo do logo do Giants (bloco 00 do Every NFL Position, 2026-10-11)
        outros = [o for o in (cena or {}).get("assets", []) if o.get("id") != a["id"]]   # título: sem cena
        if outros:
            linhas.append("Na mesma cena também entram: " + "; ".join(
                f"{o.get('papel', 'card')} {o['tipo']}: {o.get('descricao', '')[:90]}" for o in outros))
        if self.obs:
            linhas.append(f"Observação de quem produz: {self.obs}")
        if a["tipo"] == "video":
            linhas.append("Vídeos candidatos:")
            for v in meta["candidatos"]:
                if v.get("folha"):
                    linhas.append(f"v{v['n']} {v.get('fonte', '')} · \"{v.get('titulo', '')[:70]}\" · "
                                  f"{v.get('canal', '')[:25]} · {float(v.get('duracao') or 0):.0f} s"
                                  + (f" · {v['w']}x{v['h']}" if v.get("w") else ""))
        else:
            linhas.append("Candidatos:")
            for c in meta["candidatos"]:
                linhas.append(f"#{c['n']} {c.get('fonte', '')} {c.get('w')}x{c.get('h')} · "
                              f"\"{c.get('titulo', '')[:70]}\" · {str(c.get('licenca') or '')[:25]}")
        return "\n".join(linhas)

    def chamar(self, etapa, prompt, texto, imagens, schema, aid, modelo=None):
        r = motor.chamar(etapa, motor.prompt(prompt, self.c), texto, imagens=imagens, schema=schema,
                         modelo=modelo or self.modelo, ctx={**self.ctx, "asset": aid})
        uso = r.pop("_uso")
        self.registrar(f"[{aid}] {etapa} ({uso['modelo']}, {uso['equivalente']:,} equiv.): "
                       f"{json.dumps(r, ensure_ascii=False)}")
        return r

    # ---------- escolha ----------
    def nova_busca(self, aid, consultas, asset=None, tentativa=0):
        args = [self.p, "--refazer", "--asset", aid]
        for q in consultas[:3]:
            args += ["--consulta", q]
        # vídeo: a 2ª busca nova tenta os bancos de arquivo (Archive, Commons) no lugar de Pexels/Pixabay
        if asset and asset.get("tipo") == "video" and tentativa == 1:
            args += ["--fontes", "archive,commons,pexels,pixabay"]
        cod, saida = rodar_script(self.c, "buscar.py", *args, log=self.log)
        return "ok" if cod == 0 else f"erro {cod}"

    def escolher_imagem(self, item, cena, a, meta, evitar=None):
        pasta = self.p / "_work" / "candidatos" / a["id"]
        texto = self.pedido(item, cena, a, meta)
        if evitar and evitar[0] is not None:
            texto += f"\n\nNÃO use o #{evitar[0]}: {evitar[1]}"
        elif evitar:
            texto += ("\n\nÚLTIMA TENTATIVA: não há mais busca nova. Escolha a imagem relacionada mais próxima do "
                      "pedido, com \"conferir\" explicando a troca; pule só se nenhuma tiver relação com o assunto.")
        return self.chamar("escolher_imagem", "escolher_imagem", texto, [pasta / "folha.jpg"], S_IMAGEM, a["id"])

    def escolher_video(self, item, cena, a, meta, evitar=None):
        pasta = self.p / "_work" / "candidatos" / a["id"]
        folhas = [(f"Folha do v{v['n']}:", pasta / v["folha"]) for v in meta["candidatos"]
                  if v.get("folha") and (pasta / v["folha"]).exists()][:6]
        if not folhas:
            return {"pular": True, "motivo": "nenhum vídeo com folha (busca sem preview)"}
        texto = self.pedido(item, cena, a, meta) + (f"\n\nNÃO use o v{evitar[0]}: {evitar[1]}" if evitar else "")
        r = self.chamar("escolher_video", "escolher_video", texto, folhas, S_VIDEO, a["id"])
        if r.get("n") and r.get("detalhar") and not self.sombra:
            ini, fim = sorted(r["detalhar"])
            fim = min(fim, ini + 15)
            cod, saida = rodar_script(self.c, "detalhar_video.py", self.p, a["id"], r["n"], ini, fim, log=self.log)
            det = Path(saida.strip().splitlines()[-1]) if cod == 0 and saida.strip() else None
            if det and det.exists():
                conf = self.chamar("confirmar_trecho", "confirmar_trecho",
                                   self.pedido(item, cena, a, meta) + f"\n\nVocê escolheu v{r['n']} perto de "
                                   f"{r.get('inicio')} s. Confirme o início exato na folha densa.",
                                   [det], S_CONFIRMAR, a["id"], modelo=self.cfg["modelos"].get("confirmar_trecho"))
                if conf.get("ok") and conf.get("inicio") is not None:
                    r["inicio"] = conf["inicio"]
                    if conf.get("conferir"):
                        r["conferir"] = conf["conferir"]
            else:
                r["conferir"] = (r.get("conferir") or "") + " início escolhido sem detalhar (detalhe falhou)"
        r.pop("detalhar", None)
        return r

    def foto_no_lugar(self, item, cena, a, motivo):
        """Vídeo que não existe em banco livre (lance, torcida de um time, estádio específico): busca FOTO com a
        mesma descrição e usa a imagem no card (o editor decide pelo arquivo: .jpg entra parado, com o zoom
        normal). Desde 2026-10-11, quando o YouTube saiu do sistema."""
        aid = a["id"]
        cod, _ = rodar_script(self.c, "buscar.py", self.p, "--refazer", "--asset", aid, "--tipo", "foto", log=self.log)
        meta = self.candidatos(aid)
        if cod != 0 or not meta or not meta.get("candidatos"):
            return None
        foto = dict(a, tipo="foto")
        r = self.escolher_imagem(item, cena, foto, meta)
        if r.get("n") is None:
            return None
        c = next((x for x in meta["candidatos"] if x.get("n") == r["n"]), None)
        if not c or not c.get("arquivo"):
            return None
        out = {"arquivo": str(self.p / "_work" / "candidatos" / aid / c["arquivo"]),
               "fonte": f"{c.get('fonte', '')} — {c.get('titulo', '')[:60]} — {c.get('pagina') or c.get('url')}",
               "licenca": c.get("licenca") or "", "n_foto": r["n"],
               "conferir": f"foto no lugar do vídeo ({motivo[:60]})"}
        if r.get("conferir"):
            out["conferir"] += f"; {r['conferir']}"
        self.registrar(f"[{aid}] foto no lugar do vídeo: #{r['n']} {c.get('fonte')}")
        return out

    # ---------- resgate: o bloco não para por asset (2026-10-12) ----------
    def genericas(self, tipo):
        """Buscas genéricas do tema do canal (canal.json › regras.busca.genericas: {"historica": [...], "outros": [...]})."""
        g = (ler_json(Path(self.c["raiz"]) / "canal.json", {}) or {}).get("regras", {}).get("busca", {}).get("genericas", {})
        return g.get(tipo) or g.get("outros") or [self.c.get("tema") or self.plano.get("titulo", "")]

    def _escolha_arquivo(self, arquivo, fonte, licenca, conferir, n=None):
        out = {"arquivo": str(arquivo), "fonte": fonte, "licenca": licenca or "", "conferir": conferir}
        if n is not None:
            out["n_foto"] = n
        return out

    def resgatar(self, aid):
        """Último recurso para um asset sem arquivo, em vez de parar o bloco:
        1) foto com busca GENÉRICA e escolha que aceita imagem relacionada (não exige o lance exato);
        2) candidato ainda não usado de outro asset da mesma cena (já baixado, sem custo);
        3) repetir o asset vizinho da mesma cena.
        Tudo sai com "conferir" para quem produz ver na prévia."""
        achado = next(((it, ce, a) for it, ce, a in self.assets() if a["id"] == aid), None)
        if not achado:
            return None
        item, cena, a = achado
        tipo_busca = "historica" if a["tipo"] == "historica" else "foto"
        consultas = self.genericas("historica" if tipo_busca == "historica" else "outros")
        # 1) busca genérica + escolha "a mais próxima"
        args = [self.p, "--refazer", "--asset", aid, "--tipo", tipo_busca]
        for q in consultas:
            args += ["--consulta", q]
        cod, _ = rodar_script(self.c, "buscar.py", *args, log=self.log)
        meta = self.candidatos(aid)
        if cod == 0 and meta and meta.get("candidatos"):
            try:
                # evitar=(None, ...) = "ÚLTIMA TENTATIVA: escolha a relacionada mais próxima"
                r = self.escolher_imagem(item, cena, dict(a, tipo=tipo_busca), meta, evitar=(None, "último recurso"))
            except motor.LimiteDeUso:
                raise               # no limite, o bloco para e a fila espera o reset (não resgata no escuro)
            except motor.ErroClaude as e:
                r = {}
                self.registrar(f"[{aid}] resgate: escolha falhou ({e})")
            c = next((x for x in meta["candidatos"] if x.get("n") == r.get("n")), None)
            if c and c.get("arquivo"):
                self.registrar(f"[{aid}] resgate 1: foto genérica #{r['n']}")
                return self._escolha_arquivo(
                    self.p / "_work" / "candidatos" / aid / c["arquivo"],
                    f"{c.get('fonte', '')} — {c.get('titulo', '')[:60]} — {c.get('pagina') or c.get('url')}",
                    c.get("licenca"), "resgate: foto genérica no lugar do pedido" +
                    (f"; {r['conferir']}" if r.get("conferir") else ""), r["n"])
        # 2) candidato não usado de outro asset da mesma cena
        vizinhos = [o["id"] for o in (cena or {}).get("assets", []) if o["id"] != aid]
        for o in vizinhos:
            mo = self.candidatos(o) or {}
            usado = (self.escolhas.get(o) or {})
            usado_n = usado.get("n", usado.get("n_foto"))
            for c in mo.get("candidatos", []):
                arq = self.p / "_work" / "candidatos" / o / str(c.get("arquivo") or "")
                if c.get("n") != usado_n and c.get("arquivo") and arq.suffix.lower() in (".jpg", ".jpeg", ".png") \
                        and arq.exists():
                    self.registrar(f"[{aid}] resgate 2: candidato #{c['n']} de {o}")
                    return self._escolha_arquivo(
                        arq, f"{c.get('fonte', '')} — {c.get('titulo', '')[:60]} — {c.get('pagina') or c.get('url')}",
                        c.get("licenca"), f"resgate: reaproveitado o candidato #{c['n']} de {o} (mesma cena)")
        # 3) repetir o asset vizinho já pronto
        man = {m["id"]: m for m in ler_json(self.p / "manifesto.json", {"assets": []})["assets"]}
        for o in vizinhos:
            if o in man:
                self.registrar(f"[{aid}] resgate 3: repete {o}")
                return self._escolha_arquivo(self.p / man[o]["arquivo"], f"repetido de {o}", "",
                                             f"resgate: repete o asset {o} da mesma cena (nada encontrado)")
        return None

    def ajustar_inicio(self, a, meta, r):
        v = next((c for c in meta["candidatos"] if c.get("n") == r.get("n")), None)
        if not v:
            return {"pular": True, "motivo": f"o Claude escolheu v{r.get('n')}, que não existe"}
        total = float(v.get("duracao") or 0)
        dur = float(a.get("duracao", 4)) + MARGEM_VIDEO
        ini = max(0.0, float(r.get("inicio") or 0))
        if total and ini + dur > total:
            ini = max(0.0, round(total - dur - 0.2, 1))
            r["conferir"] = (r.get("conferir", "") + f" início puxado para {ini} s (passava do fim)").strip()
        r["inicio"] = round(ini, 1)
        return r

    def escolher(self, item, cena, a, evitar=None):
        aid = a["id"]
        for tentativa in range(self.cfg["nova_busca_max"] + 1):
            meta = self.candidatos(aid)
            if not meta or not meta.get("candidatos"):
                return {"_sem": "sem candidatos"}
            if a["tipo"] == "video":
                r = self.escolher_video(item, cena, a, meta, evitar)
                if a.get("lance") and r.get("n"):
                    r["conferir"] = (r.get("conferir", "") + " lance específico: só banco livre, conferir").strip()
            else:
                if tentativa >= self.cfg["nova_busca_max"]:
                    evitar = evitar or (None, None)
                r = self.escolher_imagem(item, cena, a, meta, evitar)
            if r.get("nova_busca") and not r.get("n"):
                if tentativa >= self.cfg["nova_busca_max"] or self.sombra:
                    return {"pular": True, "motivo": "nada serviu depois de novas buscas",
                            "_humano": "; ".join(r["nova_busca"])}
                st = self.nova_busca(aid, r["nova_busca"], a, tentativa)
                self.registrar(f"[{aid}] nova busca ({st}): {r['nova_busca']}")
                continue
            r.pop("nova_busca", None)
            if r.get("n") is not None and a["tipo"] == "video":
                r = self.ajustar_inicio(a, meta, r)
            if r.get("n") is not None and not any(c.get("n") == r["n"] for c in meta["candidatos"]):
                return {"pular": True, "motivo": f"n={r['n']} não existe na folha", "_humano": "escolha inválida"}
            return {k: v for k, v in r.items() if not (v is None or v is False or v == "")}
        return {"_sem": "sem escolha"}

    # ---------- execução ----------
    def alvos(self, so=None):
        out = []
        for item, cena, a in self.assets():
            aid = a["id"]
            if so and aid not in so:
                continue
            if self.sombra:
                orig = self.originais.get(aid)
                if not orig or orig.get("arquivo") or aid in self.escolhas:
                    continue
            elif aid in self.escolhas and not so:
                continue
            out.append((item, cena, a))
        return out

    def rodar(self, so=None):
        alvos = self.alvos(so)
        if not alvos:
            print("Nada a escolher.")
            return []
        print(f"Escolhendo {len(alvos)} assets ({'modo sombra' if self.sombra else 'valendo'})…")
        feitos, sem = [], []

        limite = []

        def um(args):
            item, cena, a = args
            if limite:
                sem.append((a["id"], "não tentado: limite de uso"))
                return
            try:
                r = self.escolher(item, cena, a)
            except motor.LimiteDeUso as e:
                limite.append(str(e))
                sem.append((a["id"], "limite de uso da assinatura"))
                return
            except motor.ErroClaude as e:
                self.registrar(f"[{a['id']}] ERRO {e}")
                sem.append((a["id"], str(e)[:120]))
                return
            if a["tipo"] == "video" and not self.sombra and ("_sem" in r or r.get("pular")):
                try:
                    foto = self.foto_no_lugar(item, cena, a, r.get("_sem") or r.get("motivo", ""))
                except motor.ErroClaude as e:
                    foto = None
                    self.registrar(f"[{a['id']}] foto no lugar falhou: {e}")
                if foto:
                    r = foto
            if "_sem" in r:
                sem.append((a["id"], r["_sem"]))
                return
            if r.pop("_humano", None):
                self.notas.append(f"{a['id']}: {r.get('motivo')}")
            self.gravar(a["id"], r)
            feitos.append(a["id"])
            print(f"  {a['id']}: {json.dumps(r, ensure_ascii=False)}")

        with ThreadPoolExecutor(self.cfg["claude_paralelo"]) as ex:
            list(ex.map(um, alvos))
        self._sem_repetidos(alvos, feitos)
        for aid, motivo in sem:
            self.notas.append(f"{aid}: {motivo}")
        if limite:
            self.notas.insert(0, f"PAROU: {limite[0]}")
            self.parou_por_limite = True
        return feitos

    def _origem(self, aid, esc):
        """Identidade do que foi escolhido (url do candidato ou arquivo), para achar repetidos entre cards."""
        if esc.get("pular"):
            return None
        if esc.get("arquivo"):
            meta = self.candidatos(aid) or {"candidatos": []}
            c = next((x for x in meta["candidatos"] if x.get("n") == esc.get("n_foto")), None)
            return (c or {}).get("url") or esc["arquivo"]
        meta = self.candidatos(aid) or {"candidatos": []}
        c = next((x for x in meta["candidatos"] if x.get("n") == esc.get("n")), None)
        return (c or {}).get("url")

    def _sem_repetidos(self, alvos, feitos):
        """As escolhas rodam em paralelo e uma não vê a outra: o mesmo arquivo pode ir para dois cards
        (02-13-c e 02-15-c do Every NFL Stadium escolheram a mesma foto). Refaz o card mais novo evitando o repetido."""
        usados = {}
        for aid, esc in self.escolhas.items():
            if aid not in feitos:
                o = self._origem(aid, esc)
                if o:
                    usados[o] = aid
        idx = {a["id"]: (item, cena, a) for item, cena, a in alvos}
        for aid in sorted(feitos):
            esc = self.escolhas.get(aid, {})
            o = self._origem(aid, esc)
            if not o:
                continue
            if o in usados and aid in idx:
                item, cena, a = idx[aid]
                n = esc.get("n_foto") or esc.get("n")
                nova = self.escolher(item, cena, a, evitar=(n, f"já usado no {usados[o]} deste bloco"))
                if nova.get("n") is not None and nova.get("n") != esc.get("n"):
                    nova["conferir"] = (nova.get("conferir", "") + f" (trocado: repetia o {usados[o]})").strip()
                    self.gravar(aid, nova)
                    self.notas.append(f"{aid}: repetia o {usados[o]}, escolhido outro")
                    o = self._origem(aid, nova)
                else:
                    self.notas.append(f"{aid}: mesmo arquivo do {usados[o]} (não achou outro)")
            usados[o] = aid

    # ---------- baixar e conferir ----------
    def finalizar(self, ids):
        ids = [i for i in ids if not self.escolhas.get(i, {}).get("pular")]
        if not ids:
            return []
        for tentativa in range(self.cfg["finalizar_tentativas"]):
            args = [self.p]
            for i in ids:
                args += ["--asset", i]
            rodar_script(self.c, "finalizar.py", *args, log=self.log)
            prontos = {m["id"] for m in ler_json(self.p / "manifesto.json", {"assets": []})["assets"]}
            ids = [i for i in ids if i not in prontos]
            if not ids:
                break
        for i in ids:
            self.notas.append(f"{i}: download falhou {self.cfg['finalizar_tentativas']}x")
        return ids

    def quadros(self, m, tmp):
        arq = self.p / m["arquivo"]
        if arq.suffix == ".mp4":
            out = []
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                        "csv=p=0", str(arq)], capture_output=True, text=True).stdout or 0)
            for k, t in enumerate((0.3, max(0.3, dur - 0.6))):
                f = Path(tmp) / f"{m['id']}_{k}.jpg"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(arq), "-frames:v", "1",
                                "-vf", "scale=960:-2", str(f)])
                if f.exists():
                    out.append(f)
            return out
        im = Image.open(arq)
        if im.mode in ("RGBA", "LA", "P"):
            fundo = Image.new("RGBA", im.size, (214, 208, 196, 255))     # papel claro, como no vídeo
            fundo.alpha_composite(im.convert("RGBA"))
            im = fundo
        f = Path(tmp) / f"{m['id']}.jpg"
        im.convert("RGB").save(f, quality=88)
        return [f]

    def tarja(self, m):
        """Corta tarja preta de vídeo (cropdetect) terminando em setsar=1. Devolve True se cortou."""
        arq = self.p / m["arquivo"]
        # limite 40 (não 24): barra preta de vídeo comprimido tem ruído acima de 24 e passava (01-10-e, 2026-10-11)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(arq), "-vf", "cropdetect=40:2:0", "-f", "null", "-"],
                           capture_output=True, text=True)
        crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
        if not crops:
            return False
        w, h, x, y = map(int, max(set(crops), key=crops.count))   # o corte que mais se repete
        if w >= m["w"] * 0.96 and h >= m["h"] * 0.94:
            return False
        tmp = arq.with_name(arq.stem + ".crop.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(arq), "-vf", f"crop={w}:{h}:{x}:{y},setsar=1",
                        "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-an", str(tmp)], check=True)
        tmp.replace(arq)
        man = ler_json(self.p / "manifesto.json")
        for a in man["assets"]:
            if a["id"] == m["id"]:
                a["w"], a["h"] = w, h
        gravar_json(self.p / "manifesto.json", man)
        self.notas.append(f"{m['id']}: tarja preta cortada ({m['w']}x{m['h']} → {w}x{h})")
        return True

    def conferir(self, ids):
        manif = {m["id"]: m for m in ler_json(self.p / "manifesto.json", {"assets": []})["assets"]}
        refazer = []
        idx = {a["id"]: (item, cena, a) for item, cena, a in self.assets()}
        with tempfile.TemporaryDirectory() as tmp:
            def um(aid):
                m = manif.get(aid)
                if not m:
                    return
                # foto copiada sem mudança já foi vista na folha: só confere o que muda no download
                # (trecho de vídeo, tarja, recorte de fundo). Antes: ~6.700 tokens por asset à toa.
                if not (m["arquivo"].endswith(".mp4") or m["arquivo"].endswith(".png")):
                    return
                if m["arquivo"].endswith(".mp4"):
                    self.tarja(m)
                q = self.quadros(m, tmp)
                if not q:
                    return
                item, cena, a = idx[aid]
                r = self.chamar("conferir", "conferir_asset",
                                f"Asset {aid} · tipo {a['tipo']} · pedido: {a.get('descricao', '')}",
                                q, S_CONFERIR, aid, modelo=self.cfg["modelos"].get("conferir"))
                if not r.get("ok"):
                    refazer.append((aid, r.get("problema", ""), r.get("detalhe", "")))
            with ThreadPoolExecutor(self.cfg["claude_paralelo"]) as ex:
                list(ex.map(um, ids))
        trocados = []
        for aid, problema, detalhe in refazer:
            esc = dict(self.escolhas.get(aid, {}))
            if problema in ("tarja", "qualidade") or esc.get("n") is None:
                esc["conferir"] = f"{problema}: {detalhe}".strip(": ")
                self.gravar(aid, esc)
                continue
            item, cena, a = idx[aid]
            nova = self.escolher(item, cena, a, evitar=(esc["n"], f"{problema} — {detalhe}"))
            if nova.get("n") is not None and nova.get("n") != esc.get("n"):
                nova["conferir"] = (nova.get("conferir", "") + f" troca automática ({problema})").strip()
                self.gravar(aid, nova)
                trocados.append(aid)
            else:
                esc["conferir"] = f"{problema}: {detalhe}".strip(": ")
                self.gravar(aid, esc)
        if trocados:
            self.finalizar(trocados)
            self.notas.append(f"trocados na conferência: {', '.join(trocados)}")
        # a revisao.html mostra o "conferir": regrava com as marcas novas sem baixar nada de novo
        if refazer and not trocados:
            rodar_script(self.c, "finalizar.py", self.p, "--asset", refazer[0][0], log=self.log)

    # ---------- modo sombra ----------
    def comparar(self):
        iguais, perto, difs = 0, 0, []
        for aid, est in self.escolhas.items():
            orig = self.originais.get(aid, {})
            if orig.get("pular") or est.get("pular"):
                ok = bool(orig.get("pular")) == bool(est.get("pular"))
            else:
                ok = orig.get("n") == est.get("n")
                if ok and "inicio" in orig:
                    if abs(float(orig.get("inicio", 0)) - float(est.get("inicio", 0))) > 3:
                        perto += 1
                        difs.append((aid, orig, est, "mesmo vídeo, início diferente"))
                        continue
            if ok:
                iguais += 1
            else:
                difs.append((aid, orig, est, ""))
        total = len(self.escolhas)
        uso = motor.consumo(**{k: v for k, v in self.ctx.items() if v})
        rel = [f"# Modo sombra — {self.ctx['video']} bloco {self.ctx['bloco']}", "",
               f"- Assets comparados: {total}",
               f"- Mesma escolha: {iguais} ({iguais / max(1, total):.0%})",
               f"- Mesmo vídeo, início diferente (> 3 s): {perto}",
               f"- Diferentes: {len(difs) - perto}",
               f"- Consumo registrado para este bloco: {uso['chamadas']} chamadas, {uso['equivalente']:,} tokens "
               f"equiv. ({uso['equivalente'] // max(1, total):,} por asset)", "",
               "| asset | atual | nova | obs. |", "|---|---|---|---|"]
        for aid, o, e, obs in difs:
            rel.append(f"| {aid} | {json.dumps(o, ensure_ascii=False)} | {json.dumps(e, ensure_ascii=False)} | {obs} |")
        (self.p / "_estudio" / "sombra.md").write_text("\n".join(rel) + "\n")
        if difs:
            self.folha_divergencias(difs)
        return iguais, perto, len(difs), total, uso

    def miniatura(self, aid, esc):
        pasta = self.p / "_work" / "candidatos" / aid
        meta = self.candidatos(aid) or {"candidatos": []}
        c = next((x for x in meta["candidatos"] if x.get("n") == esc.get("n")), None)
        if esc.get("pular") or not c:
            return None, "pulado" if esc.get("pular") else "—"
        if c.get("arquivo") and (pasta / c["arquivo"]).exists():
            return Image.open(pasta / c["arquivo"]).convert("RGB"), f"#{c['n']}"
        folha = pasta / c.get("folha", "")
        if c.get("folha") and folha.exists():
            passo = float(c.get("passo_preview_s") or 2) or 2
            i = int(round(float(esc.get("inicio", 0)) / passo))
            x, y = (i % 6) * 400, 50 + (i // 6) * 274
            im = Image.open(folha)
            if y + 240 <= im.height:
                return im.crop((x, y, x + 400, y + 240)).convert("RGB"), f"v{c['n']} t={esc.get('inicio', 0)}s"
        return None, f"n={esc.get('n')}"

    def folha_divergencias(self, difs):
        cel, rot = (420, 280), 40
        out = Image.new("RGB", (cel[0] * 2 + 360, len(difs) * (cel[1] + rot)), (235, 235, 235))
        d = ImageDraw.Draw(out)
        try:
            fonte = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
        except OSError:
            fonte = ImageFont.load_default()
        idx = {a["id"]: a for _, _, a in self.assets()}
        for k, (aid, o, e, obs) in enumerate(difs):
            y = k * (cel[1] + rot)
            a = idx.get(aid, {})
            d.text((cel[0] * 2 + 12, y + 10), f"{aid} [{a.get('tipo')}]", fill=(0, 0, 0), font=fonte)
            desc = a.get("descricao", "")
            for j in range(0, min(len(desc), 200), 34):
                d.text((cel[0] * 2 + 12, y + 36 + j // 34 * 22), desc[j:j + 34], fill=(60, 60, 60), font=fonte)
            for col, (nome, esc) in enumerate((("atual", o), ("nova", e))):
                im, rotulo = self.miniatura(aid, esc)
                x = col * cel[0]
                if im:
                    im.thumbnail((cel[0] - 10, cel[1] - 10))
                    out.paste(im, (x + (cel[0] - im.width) // 2, y + (cel[1] - im.height) // 2))
                d.rectangle([x, y + cel[1], x + cel[0], y + cel[1] + rot], fill=(20, 20, 20))
                d.text((x + 8, y + cel[1] + 10), f"{nome}: {rotulo}", fill=(255, 230, 0), font=fonte)
        destino = self.p / "_estudio" / "sombra_divergencias.jpg"
        out.save(destino, quality=85)
        return destino


def main(argv=None):
    ap = argparse.ArgumentParser(prog="space_machine escolher")
    ap.add_argument("bloco")
    ap.add_argument("--asset", action="append", default=[])
    ap.add_argument("--sombra", action="store_true")
    ap.add_argument("--modelo", help="força um modelo (haiku/sonnet/opus) na escolha")
    ap.add_argument("--obs", default="", help="observação que vai junto no pedido (ex.: o estádio atual já é o reformado)")
    ap.add_argument("--sem-finalizar", action="store_true")
    ap.add_argument("--sem-conferir", action="store_true")
    a = ap.parse_args(argv)
    if not a.modelo:
        try:
            motor.checar_claude(["escolher"])
        except motor.ErroClaude as e:
            raise SystemExit(f"Checagem do Claude falhou: {e}")
    b = Bloco(a.bloco, sombra=a.sombra, modelo=a.modelo)
    b.obs = a.obs
    feitos = b.rodar(a.asset or None)
    if a.sombra:
        iguais, perto, ndif, total, uso = b.comparar()
        print(f"\nModo sombra: {iguais}/{total} iguais ({iguais / max(1, total):.0%}), {perto} mesmo vídeo com "
              f"início diferente, {ndif - perto} diferentes · {uso['equivalente']:,} tokens equiv. "
              f"({uso['equivalente'] // max(1, total):,}/asset)")
        print(f"Relatório: {b.p / '_estudio' / 'sombra.md'}")
        if ndif:
            print(f"Divergências: {b.p / '_estudio' / 'sombra_divergencias.jpg'}")
    else:
        falhou = [] if a.sem_finalizar else b.finalizar(feitos)
        if b.parou_por_limite:
            a.sem_conferir = True      # sem Claude até o reset: baixa o que já foi escolhido e para
        if not a.sem_finalizar and not a.sem_conferir:
            b.conferir([i for i in feitos if i not in falhou])
        uso = motor.consumo(**{k: v for k, v in b.ctx.items() if v})
        man = ler_json(b.p / "manifesto.json", {"assets": []})["assets"]
        nv = sum(1 for m in man if m["arquivo"].endswith(".mp4"))
        pul = sum(1 for e in b.escolhas.values() if e.get("pular"))
        print(f"\nBloco {b.ctx['bloco']}: {len(man)} assets prontos ({nv} vídeos, {len(man) - nv} imagens), {pul} pulados."
              f" Escolhidos agora: {len(feitos)}. Consumo do bloco: {uso['equivalente']:,} tokens equiv.")
    conferir = [f"- {aid}: {e['conferir']}" for aid, e in b.escolhas.items()
                if e.get("conferir") and (aid in feitos)]
    if conferir or b.notas:
        print("Conferir:")
        print("\n".join(conferir + [f"- {n}" for n in b.notas]))
    print(f"Log: {b.log}")


if __name__ == "__main__":
    main()
