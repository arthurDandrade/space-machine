"""Etapa a etapa de um bloco, do roteiro até a prévia aprovada pelo QA, sem conversa.

Uso:
  python -m space_machine rodar <bloco> [--de etapa] [--ate etapa] [--obs "..."]
  etapas: narracao, transcrever, storyboard, buscar, escolher, editar, entregar

Cada etapa vê pelos arquivos se já foi feita e pula (idempotente): dá para parar e rodar de novo.
O Claude só entra no storyboard (sessão curta com voltas de correção), na escolha (escolher.py) e na
correção automática do QA (uma vez). Exceções param o bloco com o motivo em <bloco>/_estudio/estado.json.
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from . import motor_claude as motor
from .canal import canal_do_bloco, contexto, gravar_json, ler_json, rodar_script
from .escolher import Bloco as BlocoEscolha
from . import limpeza
from .estado import conferir_pendentes, previas as previas_do_bloco
from .sistema import FORMATOS, ambiente_motor

ETAPAS = ["narracao", "transcrever", "storyboard", "buscar", "escolher", "editar", "entregar"]


def _aprovado(qa):
    """qa_NN.md: a linha "Prévia: `...` · **✅ APROVADO** (0 falha(s), ...)"."""
    linha = next((l for l in (qa or "").splitlines() if l.startswith("Prévia:")), "")
    return "APROVADO" in linha and "REPROVADO" not in linha


def _vivo(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


class Parada(Exception):
    """O bloco precisa de gente (ou de esperar): motivo vai para o estado.json."""


class Rodada:
    def __init__(self, bloco, obs=""):
        self.p = Path(bloco).resolve()
        self.slug, self.c = canal_do_bloco(self.p)
        self.ctx = contexto(self.p)
        self.nn = self.p.name
        self.video = self.p.parent.parent
        self.cfg = motor.config()
        self.obs = obs
        self.de = None
        (self.p / "_estudio").mkdir(exist_ok=True)
        self.arq_estado = self.p / "_estudio" / "estado.json"
        self.estado = ler_json(self.arq_estado, {"etapas": {}})

    # ---------- registro ----------
    def log(self, etapa):
        return self.p / "_estudio" / f"log_{etapa}.txt"

    def marcar(self, etapa, status, detalhe=""):
        self.estado["etapas"][etapa] = {"status": status, "detalhe": detalhe,
                                        "quando": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.estado["atual"] = etapa
        gravar_json(self.arq_estado, self.estado)
        print(f"[{self.nn}] {etapa}: {status}{(' — ' + detalhe) if detalhe else ''}", flush=True)

    def script(self, etapa, nome, *args, timeout=7200):
        cod, saida = rodar_script(self.c, nome, *args, timeout=timeout, log=self.log(etapa))
        return cod, saida

    # ---------- etapas ----------
    def narracao(self):
        if (self.p / "narracao.mp3").exists():
            return "já existe"
        cod, saida = self.script("narracao", "gerar_narracao.py", self.p)
        if cod != 0 or not (self.p / "narracao.mp3").exists():
            raise Parada(f"narração falhou: {saida.strip()[-300:]}")
        return "gerada (Fish Audio)"

    def transcrever(self):
        if (self.p / "_work" / "palavras.json").exists():
            return "já existe"
        cod, saida = self.script("transcrever", "transcrever.py", self.p)
        if cod != 0 or not (self.p / "_work" / "palavras.json").exists():
            raise Parada(f"transcrição falhou: {saida.strip()[-300:]}")
        return "ok"

    # ----- storyboard -----
    def _ja_buscou(self):
        cand = self.p / "_work" / "candidatos"
        return (cand.exists() and any(cand.iterdir())) or (self.p / "escolhas.json").exists()

    def _sistema_storyboard(self):
        # o que é do FORMATO vem de formatos/<formato>/; o que é do CANAL (aprendizados, regras do tema), do canal
        f = FORMATOS / self.c.get("formato", "explained")
        k = f / "conhecimento"
        arq_log = Path(self.c["conhecimento"]) / "05 - Aprendizados" / "Log de Aprendizados.md"
        entradas = re.split(r"\n(?=## 20\d\d-)", arq_log.read_text())[1:5] if arq_log.exists() else []
        compilar = (Path(self.c["scripts"]) / "compilar_cenas.py").read_text()
        doc = compilar[:compilar.index('"""', 3) + 3]
        exemplo = next((x for x in [self.video / "blocos" / "01" / "cenas.json", f / "exemplo_cenas.json"]
                        if x.exists() and x.parent != self.p), None)
        partes = [
            motor.prompt("storyboard", self.c),
            "# Regras do storyboard (o storyboard.py mede as que dá)\n" + (f / "storyboard.md").read_text(),
            "# Formato do cenas.json (topo do compilar_cenas.py)\n" + doc,
            "# Biblioteca de Cenas\n" + (k / "02 - Cenas" / "Biblioteca de Cenas.md").read_text(),
            "# Da Narração às Cenas\n" + (k / "02 - Cenas" / "Da Narração às Cenas.md").read_text(),
        ]
        if entradas:
            partes.append("# Aprendizados recentes deste canal (topo do Log)\n" + "\n".join(entradas))
        if exemplo:
            partes.append(f"# Exemplo de cenas.json pronto (só para ver a ESTRUTURA; o assunto pode ser outro)\n"
                          + exemplo.read_text())
        return "\n\n".join(partes)

    def _compilar_e_medir(self):
        if not self._ja_buscou():      # ids recomeçam limpos enquanto não houve busca (regra do storyboard)
            (self.p / "plano.json").unlink(missing_ok=True)
            (self.p / "edicao" / f"plano_edicao_{self.nn}.json").unlink(missing_ok=True)
        cod, saida = self.script("storyboard", "compilar_cenas.py", self.p)
        problemas = [l for l in saida.splitlines() if l.startswith("AVISO") or "CORRIGIR" in l
                     or l.startswith("  ") and cod != 0]
        if cod != 0:
            return False, "O compilador recusou o cenas.json:\n" + "\n".join(problemas or [saida.strip()[-1500:]])
        cod2, saida2 = self.script("storyboard", "storyboard.py", self.p)
        avisos = [l for l in saida2.splitlines() if l.startswith("AVISO")]
        resumo = "\n".join(l for l in saida2.splitlines() if not l.startswith("AVISO"))[-1500:]
        if problemas or avisos:
            return False, ("Avisos do compilador:\n" + "\n".join(problemas) + "\n\n" if problemas else "") + \
                   "Métricas do storyboard.py:\n" + resumo + "\n\nAVISOS:\n" + "\n".join(avisos)
        return True, resumo

    def cold_open(self):
        return "#! cold open" in (self.p / "roteiro.txt").read_text()

    def topico(self):
        roteiro = (self.p / "roteiro.txt").read_text()
        return next((l.lstrip("# ").strip() for l in roteiro.splitlines() if l.startswith("#")), self.nn)

    def _pedido_storyboard(self):
        roteiro = (self.p / "roteiro.txt").read_text()
        topico = self.topico()
        transc = (self.p / "_work" / "transcricao.txt").read_text()
        dur = (ler_json(self.p / "_work" / "palavras.json", [{}]) or [{}])[-1].get("fim", 0)
        titulo = (ler_json(self.video / "blocos" / "01" / "cenas.json", {}) or {}).get("titulo") \
            or self.video.name.replace("-", " ").title()
        return (f"Storyboard do bloco {self.nn} do vídeo \"{titulo}\" (canal {self.c['nome']}). "
                f"Tópico: {topico}. Narração de {dur:.0f} s.\n"
                f"O item do cenas.json tem \"id\": \"{self.nn}\" e \"nome\": \"{topico}\" (se a transcrição escreveu o "
                f"nome diferente, ponha a forma da transcrição em \"nome_fala\"); o topo tem "
                f"\"titulo\": \"{titulo}\".\n"
                + (f"Observação de quem produz: {self.obs}\n" if self.obs else "")
                + ("ESTE BLOCO É O COLD OPEN do vídeo (gancho antes do 1º tópico): NÃO tem card de título nem nome "
                   "falado — no item use \"sem_titulo\": true e não escreva \"titulo\". A 1ª cena começa na 1ª palavra "
                   "da narração e precisa prender a atenção logo (cenas curtas, imagens fortes).\n"
                   if self.cold_open() else "")
                + f"\n## roteiro.txt\n{roteiro}\n\n## _work/transcricao.txt ([tempo]palavra)\n{transc}\n\n"
                "Devolva o cenas.json completo.")

    def storyboard(self):
        if (self.p / "plano.json").exists() and (self.p / f"storyboard_{self.nn}.md").exists():
            return "já existe"
        if self._ja_buscou():
            raise Parada("já existe busca/escolhas neste bloco: refazer o storyboard é decisão sua (apague _work/candidatos e escolhas.json e rode de novo)")
        sistema = self._sistema_storyboard()
        sid = str(uuid.uuid4())
        texto = self._pedido_storyboard()
        voltas = self.cfg.get("storyboard_voltas", 4)
        ok, retorno = False, ""
        for volta in range(voltas + 1):
            r = motor.chamar("storyboard", sistema, texto, modelo=self.cfg["modelos"]["storyboard"], ctx=self.ctx,
                             timeout=self.cfg.get("storyboard_timeout_s", 1200), sessao=(sid, volta == 0),
                             texto_livre=True)
            with open(self.log("storyboard"), "a") as f:
                f.write(f"\n=== volta {volta} ({r['_uso']['equivalente']:,} equiv.)\n")
            try:
                cenas = motor._extrair_json(r["texto"])
            except (json.JSONDecodeError, TypeError):
                texto = "A resposta não era um JSON válido. Devolva só o cenas.json completo, sem texto em volta."
                continue
            if "trocar" in cenas and "itens" not in cenas:      # correção parcial: só as cenas que mudaram
                atual = ler_json(self.p / "cenas.json")
                lista = atual["itens"][0]["cenas"]
                trocar = cenas["trocar"]
                if trocar.get("_avisos_aceitos") and not cenas.get("_avisos_aceitos"):
                    cenas["_avisos_aceitos"] = trocar["_avisos_aceitos"]   # o Claude às vezes põe dentro do "trocar"
                trocar = {k: v for k, v in trocar.items() if str(k).lstrip("-").isdigit()}
                for k, cena in sorted(((int(k), v) for k, v in trocar.items()), reverse=True):
                    if cena is None:
                        lista.pop(k)
                    elif k < len(lista):
                        lista[k] = cena
                    else:
                        lista.append(cena)
                if cenas.get("_avisos_aceitos"):
                    atual["_avisos_aceitos"] = cenas["_avisos_aceitos"]
                cenas = atual
            # o nome do tópico vem do roteiro, não da transcrição (o Whisper escreveu "Lambo Field" no bloco 02)
            if self.cold_open():   # sem card de título; nome_fala = começo da narração (acha o início do bloco)
                palavras = ler_json(self.p / "_work" / "palavras.json", [])
                for it in cenas.get("itens", []):
                    it.update({"sem_titulo": True, "nome_fala": " ".join(w["p"] for w in palavras[:3])})
                    it.pop("titulo", None)
            for it in cenas.get("itens", []):
                if it.get("sem_titulo"):
                    it["id"], it["nome"] = self.nn, self.topico()
                    continue
                if it.get("nome") and it["nome"] != self.topico() and not it.get("nome_fala"):
                    it["nome_fala"] = it["nome"]          # como está na transcrição (acha o tempo do título)
                it["id"], it["nome"] = self.nn, self.topico()
            gravar_json(self.p / "cenas.json", cenas)
            ok, retorno = self._compilar_e_medir()
            if ok:
                return f"ok em {volta + 1} volta(s)"
            if volta == voltas:
                break
            texto = (retorno + "\n\nCorrija. Devolva SÓ as cenas que mudaram, em JSON compacto: "
                     "{\"trocar\": {\"<índice da cena em itens[0].cenas, começando em 0>\": {<a cena inteira nova>}, "
                     "\"<índice>\": null para apagar}}. Índice além do fim acrescenta. Se um aviso for inevitável "
                     "(ex.: bloco sem número nem lugar), inclua \"_avisos_aceitos\": \"motivo\".")
        # avisos aceitos pelo Claude com motivo não travam; erro de compilação trava
        if (self.p / "plano.json").exists() and (self.p / f"storyboard_{self.nn}.md").exists():
            aceitos = (ler_json(self.p / "cenas.json", {}) or {}).get("_avisos_aceitos")
            return f"com avisos ({'aceitos: ' + str(aceitos)[:200] if aceitos else retorno[-300:]})"
        raise Parada(f"storyboard não compilou depois de {voltas + 1} voltas: {retorno[-400:]}")

    # ----- busca e escolha -----
    def buscar(self):
        plano = ler_json(self.p / "plano.json")
        cand = self.p / "_work" / "candidatos"
        falta, so_yt = [], []
        # asset já escolhido e baixado não precisa de candidatos: num bloco entregue, a limpeza tira os candidatos
        # (limpeza.py) e a busca não baixa tudo de novo; "--de buscar" baixa o que faltar
        man = {m["id"] for m in (ler_json(self.p / "manifesto.json", {}) or {}).get("assets", [])}
        for _, _, a in BlocoEscolha(self.p).assets():
            meta = ler_json(cand / a["id"] / "candidatos.json")
            if meta is None:
                if a["id"] in man and self.de != "buscar":
                    continue
                falta.append(a["id"])
            elif meta.get("candidatos") and all(c.get("fonte") == "youtube" or "youtube.com" in str(c.get("url"))
                                                for c in meta["candidatos"]):
                so_yt.append(a["id"])        # bloco antigo: só tinha YouTube (removido em 2026-10-11)
        if not falta and not so_yt and plano:
            return "já existe"
        if falta:
            cod, saida = self.script("buscar", "buscar.py", self.p, timeout=6 * 3600)
            if cod != 0:
                raise Parada(f"busca falhou: {saida.strip()[-300:]}")
        for aid in so_yt:
            self.script("buscar", "buscar.py", self.p, "--refazer", "--asset", aid, timeout=3600)
        sem = [aid for aid in falta + so_yt if not (ler_json(cand / aid / "candidatos.json") or {}).get("candidatos")]
        return f"ok ({len(falta)} novos, {len(so_yt)} refeitos sem YouTube)" + (f" · sem candidatos: {', '.join(sem)}" if sem else "")

    def escolher(self):
        b = BlocoEscolha(self.p)
        b.obs = self.obs
        feitos = b.rodar()
        if b.parou_por_limite:
            b.finalizar(feitos)
            raise Parada("limite de uso da assinatura: rodar de novo depois do reset")
        # escolhidos numa rodada anterior cujo download falhou entram de novo
        man = {m["id"] for m in ler_json(self.p / "manifesto.json", {"assets": []})["assets"]}
        pendentes = [aid for aid, e in b.escolhas.items() if not e.get("pular") and aid not in man and aid not in feitos]
        falhou = b.finalizar(feitos + pendentes)
        b.conferir([i for i in feitos + pendentes if i not in falhou])
        man = {m["id"] for m in ler_json(self.p / "manifesto.json", {"assets": []})["assets"]}
        faltam = [a["id"] for _, _, a in b.assets()
                  if a["id"] not in man and not b.escolhas.get(a["id"], {}).get("pular")]
        pulados = [aid for aid, e in b.escolhas.items() if e.get("pular")]
        if (faltam or pulados) and self.cfg.get("resgatar_assets", True):
            # o bloco não para por asset: busca genérica → candidato não usado da cena → repete o vizinho,
            # tudo com "conferir" (2026-10-12: 10 de 21 blocos paravam aqui, quase todos por vídeo de lance)
            salvos = []
            for aid in faltam + pulados:
                self.marcar("escolher", "rodando", f"resgatando {aid}")
                r = b.resgatar(aid)
                if r:
                    b.gravar(aid, r)
                    salvos.append(aid)
            if salvos:
                b.finalizar(salvos)
            man = {m["id"] for m in ler_json(self.p / "manifesto.json", {"assets": []})["assets"]}
            faltam = [a["id"] for _, _, a in b.assets()
                      if a["id"] not in man and not b.escolhas.get(a["id"], {}).get("pular")]
            pulados = [aid for aid, e in b.escolhas.items() if e.get("pular")]
            feitos += salvos
        if faltam or pulados:
            # a edição quebra com asset faltando no manifesto (gerar_ae2 lê manif[id])
            raise Parada("assets sem arquivo: " + ", ".join(faltam + pulados)
                         + " — decidir: reaproveitar outro (--obs / reusar_candidato.py), trocar por texto ou pular a cena")
        conferir = [f"{aid}: {e['conferir']}" for aid, e in b.escolhas.items() if e.get("conferir") and aid in feitos]
        return f"{len(feitos)} escolhidos" + (f" · conferir: {'; '.join(conferir)[:400]}" if conferir else "")

    # ----- edição + QA -----
    def _versao(self):
        pv = previas_do_bloco(self.p)
        return int(re.search(r"_v(\d+)\.mp4$", pv[-1].name).group(1)) + 1 if pv else 1

    def _editar_uma(self):
        # um bloco por vez no After em todo o Mac (o After só roda um script de cada vez e trava com dois)
        trava = open(motor.DADOS / "trava_after", "w")
        self.marcar("editar", "rodando", "esperando a vez no After")
        fcntl.flock(trava, fcntl.LOCK_EX)
        try:
            self.marcar("editar", "rodando", "montando e renderizando no After")
            return self._editar_uma_travado()
        finally:
            fcntl.flock(trava, fcntl.LOCK_UN)
            trava.close()

    def _editar_uma_travado(self):
        v = self._versao()
        sh = Path(self.c["editor"]) / "editar_bloco.sh"
        with open(self.log("editar"), "a") as f:
            ini_log = f.tell()
            r = subprocess.run([str(sh), str(self.p), self.nn, str(v)], cwd=self.c["raiz"], stdout=f,
                               stderr=subprocess.STDOUT, timeout=3 * 3600, env=ambiente_motor(self.c))
        previa = self.p / "edicao" / f"previa_bloco_{self.nn}_v{v}.mp4"
        if not previa.exists():
            # erro no Python antes do After (gerar_ae2.py) não é After travado: mostra o erro
            # (o "too many values to unpack" do "2linhas" em rótulo parou os blocos 05 e 06 do draft, 2026-10-16)
            with open(self.log("editar")) as f:
                f.seek(ini_log)
                saida = f.read()
            if "Traceback" in saida:
                erro = [l for l in saida.strip().splitlines() if l.strip()][-1]
                raise Parada(f"a montagem deu erro antes de abrir o After: {erro[:200]} (ver log_editar.txt)")
            raise Parada("o After não gerou a prévia (pode estar travado num diálogo: olhar a tela)")
        qa = (self.p / "edicao" / f"qa_{self.nn}.md").read_text() if (self.p / "edicao" / f"qa_{self.nn}.md").exists() else ""
        # o qa_NN.md é regravado a cada versão: se o QA desta não rodou, o arquivo ainda é o da versão anterior
        # (talvez aprovada) e aprovaria uma prévia que ninguém mediu
        if f"`{previa.name}`" not in next((l for l in qa.splitlines() if l.startswith("Prévia:")), ""):
            qa = ""
        aprovado = _aprovado(qa)
        return v, previa, aprovado, qa

    def _corrigir_qa(self, qa):
        """Uma correção automática: o Claude recebe o QA + cenas.json e devolve o cenas.json corrigido."""
        sistema = self._sistema_storyboard() + "\n\n" + motor.prompt("qa")
        texto = (f"## Relatório do QA (qa_{self.nn}.md)\n{qa}\n\n## cenas.json atual\n"
                 f"{(self.p / 'cenas.json').read_text()}\n\n## transcrição\n"
                 f"{(self.p / '_work' / 'transcricao.txt').read_text()}\n\n"
                 "Corrija as FALHAS mexendo o mínimo possível e devolva o cenas.json completo. "
                 "Mantenha os \"id\" dos cards que já existem; card novo vem sem id.")
        r = motor.chamar("qa", sistema, texto, modelo=self.cfg["modelos"]["qa"], ctx=self.ctx,
                         timeout=self.cfg.get("storyboard_timeout_s", 1200), texto_livre=True)
        cenas = motor._extrair_json(r["texto"])
        shutil.copy2(self.p / "cenas.json", self.p / "_estudio" / f"cenas_antes_qa_{time.strftime('%H%M%S')}.json")
        gravar_json(self.p / "cenas.json", cenas)
        cod, saida = self.script("editar", "compilar_cenas.py", self.p)
        if cod != 0:
            raise Parada(f"correção do QA não compilou: {saida.strip()[-300:]}")
        self.buscar()          # só os assets novos
        self.escolher()

    def editar(self):
        previas = previas_do_bloco(self.p)
        qa_md = self.p / "edicao" / f"qa_{self.nn}.md"
        # pula só se a prévia aprovada é mais nova que tudo o que entra nela (cenas, assets e o próprio editor)
        # e se ninguém pediu para editar de novo (--de editar): antes pulava e a observação dele se perdia
        entradas = [self.p / "manifesto.json", self.p / "cenas.json", self.p / "plano.json",
                    Path(self.c["editor"]) / "gerar_ae2.py"]
        mais_novo = max((f.stat().st_mtime for f in entradas if f.exists()), default=0)
        # já entregue e nada do conteúdo mudou depois (o editor do After mudar não refaz bloco entregue): a prévia
        # foi movida para o entregue e as outras saíram na limpeza, então não há prévia a comparar
        entregue = self.video / "edicao" / f"bloco {int(self.nn)}.mp4"
        conteudo = max((f.stat().st_mtime for f in entradas[:3] if f.exists()), default=0)
        if entregue.exists() and self.de != "editar" and entregue.stat().st_mtime >= conteudo \
                and not (previas and previas[-1].stat().st_mtime > entregue.stat().st_mtime + 60):
            return "já entregue"
        if previas and qa_md.exists() and qa_md.stat().st_mtime >= previas[-1].stat().st_mtime - 5 \
                and _aprovado(qa_md.read_text()) and qa_md.stat().st_mtime >= mais_novo \
                and self.de != "editar":
            return "já aprovado"
        v, previa, ok, qa = self._editar_uma()
        if ok:
            return f"QA aprovado (v{v})"
        self.marcar("editar", "corrigindo", f"QA reprovou a v{v}: correção automática")
        self._corrigir_qa(qa)
        v, previa, ok, qa = self._editar_uma()
        if ok:
            return f"QA aprovado (v{v}, depois de 1 correção automática)"
        falhas = [l for l in qa.splitlines() if "FALHA" in l][:6]
        raise Parada(f"QA reprovou de novo (v{v}): " + " | ".join(falhas))

    def entregar(self):
        previas = previas_do_bloco(self.p)
        destino = self.video / "edicao" / f"bloco {int(self.nn)}.mp4"
        if destino.exists() and (not previas or previas[-1].stat().st_mtime <= destino.stat().st_mtime + 60):
            return "já entregue"
        if not previas:
            raise Parada("sem prévia para entregar")
        # "conferir" e assets pulados travam a entrega até alguém aprovar no painel: antes ficavam só no
        # revisao.html e um snapper do Jets debaixo do logo do Giants passou direto (2026-10-11)
        pend = conferir_pendentes(self.p) if self.cfg.get("travar_conferir") else {}
        if pend:
            raise Parada(f"{len(pend)} item(ns) para conferir antes de entregar — veja a prévia e aprove no painel: "
                         + " | ".join(f"{aid}: {t[:80]}" for aid, t in pend.items()))
        destino.parent.mkdir(exist_ok=True)
        # a prévia aprovada VIRA o entregue (copiar deixava dois arquivos iguais de ~120 MB por bloco: 52 de 67 em
        # 2026-10-14); depois, as prévias antigas, os candidatos e o Auto-Save do bloco vão para o Lixo
        os.replace(previas[-1], destino)
        detalhe = str(destino)
        try:
            r = limpeza.depois_de_entregar(self.p)
            if r:
                detalhe += f" · limpeza: {limpeza.gb(r[0])} para o Lixo"
        except OSError as e:
            detalhe += f" · limpeza não rodou: {e}"
        return detalhe

    # ---------- roteiro ----------
    def rodar(self, de=None, ate=None):
        pid = self.p / "_estudio" / "pid"
        meu = str(os.getpid())
        if pid.exists():
            outro = pid.read_text().strip()
            if outro != meu and _vivo(outro):
                # duas rodadas no mesmo bloco brigam pelo cenas.json e pela pasta _baixando da busca
                print(f"[{self.nn}] já tem uma rodada neste bloco (pid {outro}): não vou rodar outra junto.")
                return False
        pid.write_text(meu)
        try:
            return self._rodar(de, ate)
        finally:
            if pid.exists() and pid.read_text().strip() == meu:   # só apaga o pid se ainda for o meu
                pid.unlink(missing_ok=True)

    def _rodar(self, de=None, ate=None):
        self.de = de
        i0 = ETAPAS.index(de) if de else 0
        i1 = ETAPAS.index(ate) if ate else len(ETAPAS) - 1
        self.estado.pop("parado", None)
        # antes de qualquer etapa: o claude responde com os modelos que este trecho vai usar?
        # (versão velha, login vencido ou modelo errado paravam o bloco no meio da etapa)
        try:
            motor.checar_claude(ETAPAS[i0:i1 + 1])
        except motor.ErroClaude as e:
            limite = isinstance(e, motor.LimiteDeUso)
            self.estado["parado"] = {"etapa": "checagem do Claude",
                                     "motivo": f"{'limite de uso' if limite else 'erro do Claude'}: {e}"}
            gravar_json(self.arq_estado, self.estado)
            return False
        for etapa in ETAPAS[i0:i1 + 1]:
            self.marcar(etapa, "rodando")
            t0 = time.time()
            try:
                det = getattr(self, etapa)()
            except Parada as e:
                self.marcar(etapa, "parado", str(e))
                self.estado["parado"] = {"etapa": etapa, "motivo": str(e)}
                gravar_json(self.arq_estado, self.estado)
                return False
            except motor.LimiteDeUso as e:
                self.marcar(etapa, "parado", f"limite de uso: {e}")
                self.estado["parado"] = {"etapa": etapa, "motivo": f"limite de uso: {e}"}
                gravar_json(self.arq_estado, self.estado)
                return False
            except motor.ErroClaude as e:
                self.marcar(etapa, "parado", f"erro do Claude: {e}")
                self.estado["parado"] = {"etapa": etapa, "motivo": f"erro do Claude: {str(e)[:300]}"}
                gravar_json(self.arq_estado, self.estado)
                return False
            except Exception as e:
                # erro de programa: antes o bloco morria com "rodando" no estado e ninguém via (bloco 02, 2026-10-11)
                import traceback
                traceback.print_exc()
                self.marcar(etapa, "parado", f"erro inesperado: {type(e).__name__}: {e}")
                self.estado["parado"] = {"etapa": etapa,
                                         "motivo": f"erro inesperado ({type(e).__name__}: {str(e)[:200]}) — ver log_rodar.txt"}
                gravar_json(self.arq_estado, self.estado)
                return False
            self.marcar(etapa, "ok", f"{det} ({time.time() - t0:.0f} s)")
        uso = motor.consumo(**{k: v for k, v in self.ctx.items() if v})
        print(f"\n[{self.nn}] pronto · Claude: {uso['chamadas']} chamadas, {uso['equivalente']:,} tokens equiv.")
        return True


def main(argv=None):
    ap = argparse.ArgumentParser(prog="space_machine rodar")
    ap.add_argument("bloco")
    ap.add_argument("--de", choices=ETAPAS)
    ap.add_argument("--ate", choices=ETAPAS)
    ap.add_argument("--obs", default="")
    a = ap.parse_args(argv)
    r = Rodada(a.bloco, obs=a.obs)
    ok = r.rodar(a.de, a.ate)
    if not ok:
        p = r.estado.get("parado") or {}
        print(f"\nPAROU em {p.get('etapa')}: {p.get('motivo')}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
