"""Etapa a etapa do VÍDEO INTEIRO, do roteiro ao MP4 final, sem conversa (fluxo "video" do explained, 2026-11-05; o
que muda em relação ao bloco a bloco está em video.py).

Uso:
  python -m space_machine rodar <pasta do vídeo> [--de etapa] [--ate etapa] [--obs "..."]
  etapas: narracao, transcrever, juntar, storyboard, buscar, escolher, montar, entregar

  narracao, transcrever  por capítulo (<vídeo>/blocos/NN), como antes: dá para refazer a voz de um só
  juntar                 emenda as narrações e as palavras em <vídeo>/producao (video.juntar)
  storyboard             uma conversa com o Claude sobre o vídeo inteiro: 1º o plano de distribuição (medido pelas
                         regras do vídeo), depois um capítulo por resposta (cada um medido com os de antes); no fim o
                         compilar_cenas + storyboard.py --video medem o vídeo e ele corrige em voltas, como no bloco
  buscar, escolher       todos os assets do vídeo de uma vez
  montar                 gerar_ae2 por capítulo → compositor sem After (render_video: os capítulos em paralelo, só o
                         que mudou) → QA de cada capítulo; uma correção automática dos que reprovarem
  entregar               emenda tudo com a narração e a trilha em <vídeo>/final/<título>.mp4

Cada etapa vê pelos arquivos se já foi feita e pula. Parou: o motivo fica em <vídeo>/producao/_estudio/estado.json.
"""
import argparse
import fcntl
import json
import math
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import final as final_mod
from . import limpeza
from . import motor_claude as motor
from . import video
from .canal import gravar_json, ler_json
from .estado import conferir_pendentes, titulo_video
from .rodar import Parada, Rodada, _aprovado
from .sistema import MOTOR, arquivo_formato, ficha_formato

sys.path.insert(0, str(MOTOR / "edicao_ff"))
import render_video  # noqa: E402  (motor/edicao_ff/render_video.py)

ETAPAS_VIDEO = ["narracao", "transcrever", "juntar", "storyboard", "buscar", "escolher", "montar", "entregar"]


class RodadaVideo(Rodada):
    PROMPT_STORYBOARD = "storyboard_video"
    ETAPAS = ETAPAS_VIDEO

    def __init__(self, pasta_video, obs=""):
        vd = Path(pasta_video).resolve()
        if vd.name == "producao":          # o painel lança pela pasta do projeto (o pid e o log ficam nela)
            vd = vd.parent
        video.pasta(vd).mkdir(parents=True, exist_ok=True)
        super().__init__(video.pasta(vd), obs)
        self.video = vd
        self.nn = "vídeo"

    # ---------- por capítulo ----------
    def _por_capitulo(self, etapa):
        novos = []
        caps = video.capitulos(self.video)
        if not caps:
            raise Parada("o vídeo não tem capítulos (blocos/NN com roteiro.txt)")
        for k, b in enumerate(caps, 1):
            self.marcar(etapa, "rodando", f"capítulo {b.name} ({k}/{len(caps)})")
            try:
                det = getattr(Rodada(b), etapa)()
            except Parada as e:
                raise Parada(f"capítulo {b.name}: {e}")
            if det != "já existe":
                novos.append(b.name)
        return f"{len(novos)} capítulo(s): {', '.join(novos)}" if novos else "já existe"

    def narracao(self):
        return self._por_capitulo("narracao")

    def transcrever(self):
        return self._por_capitulo("transcrever")

    def juntar(self):
        if video.atualizado(self.video):
            return "já existe"
        try:
            caps = video.juntar(self.video)
        except ValueError as e:
            raise Parada(str(e))
        det = f"{len(caps)} capítulos, {caps[-1]['fim'] / 60:.1f} min de narração"
        if (self.p / "cenas.json").exists() and (self.p / "plano.json").exists():
            # narração refeita depois do storyboard: os tempos vêm das palavras, então basta compilar de novo
            ok, ret = self._compilar_e_medir()
            if ret.startswith("O compilador recusou"):
                raise Parada("a narração mudou e o storyboard não acha mais as falas: " + ret[-300:])
            det += " · storyboard recompilado"
        return det

    # ---------- storyboard do vídeo inteiro ----------
    def _capitulos(self):
        return ler_json(self.p / "capitulos.json", []) or []

    def _compilar_e_medir(self):
        if not self._ja_buscou():      # ids recomeçam limpos enquanto não houve busca
            (self.p / "plano.json").unlink(missing_ok=True)
            for f in (self.p / "edicao").glob("plano_edicao_*.json"):
                f.unlink()
        cod, saida = self.script("storyboard", "compilar_cenas.py", self.p)
        problemas = [l for l in saida.splitlines() if l.startswith("AVISO") or "CORRIGIR" in l
                     or l.startswith("  ") and cod != 0]
        if cod != 0:
            return False, "O compilador recusou o cenas.json:\n" + "\n".join(problemas or [saida.strip()[-1500:]])
        cod2, saida2 = self.script("storyboard", "storyboard.py", self.p, "--video")
        avisos = [l for l in saida2.splitlines() if l.startswith("AVISO")]
        resumo = "\n".join(l for l in saida2.splitlines() if not l.startswith("AVISO"))[-1500:]
        if problemas or avisos:
            return False, ("Avisos do compilador:\n" + "\n".join(problemas) + "\n\n" if problemas else "") + \
                   "Métricas do storyboard.py --video:\n" + resumo + "\n\nAVISOS:\n" + "\n".join(avisos)
        return True, resumo

    def _pedido_storyboard(self, fim="Devolva o cenas.json completo do vídeo."):
        caps = self._capitulos()
        titulo = titulo_video(self.video)
        linhas = []
        for c in caps:
            if c["tipo"] == "cold_open":
                linhas.append(f"- \"id\": \"{c['nn']}\" — COLD OPEN (gancho antes do 1º capítulo): sem card de título nem "
                              "nome falado (\"sem_titulo\": true, sem \"titulo\"); a 1ª cena começa na 1ª palavra e "
                              "precisa prender a atenção logo (cenas curtas, imagens fortes).")
            elif c["tipo"] == "mudo":
                linhas.append(f"- \"id\": \"{c['nn']}\", \"nome\": \"{c['nome']}\" — capítulo sem nome falado "
                              "(\"sem_titulo\": true; o editor põe o nome na tela).")
            else:
                linhas.append(f"- \"id\": \"{c['nn']}\", \"nome\": \"{c['nome']}\" (se a transcrição escreveu o nome "
                              "diferente, ponha a forma dela em \"nome_fala\")")
        dur = caps[-1]["fim"] if caps else 0
        return (f"Storyboard do vídeo \"{titulo}\" (canal {self.c['nome']}): {len(caps)} capítulos, narração de "
                f"{dur / 60:.1f} min. O topo do cenas.json tem \"titulo\": \"{titulo}\" e \"itens\", um por capítulo, "
                "nesta ordem:\n" + "\n".join(linhas) + "\n"
                + (f"Observação de quem produz: {self.obs}\n" if self.obs else "")
                + self._elenco_e_gerador()
                + f"\n## roteiro.txt (todos os capítulos)\n{(self.p / 'roteiro.txt').read_text()}\n\n"
                "## _work/transcricao.txt ([tempo]palavra, no tempo do vídeo inteiro)\n"
                f"{(self.p / '_work' / 'transcricao.txt').read_text()}\n\n" + fim)

    def _acertar_itens(self, cenas, parcial=False):
        """O nome de cada capítulo vem do roteiro, não da transcrição; cold open e capítulo mudo sem card de título.
        Devolve o problema (texto para o Claude) se os itens não baterem com os capítulos, ou "".
        parcial: só os primeiros capítulos (o storyboard capítulo a capítulo)."""
        caps = self._capitulos()
        ids = [str(it.get("id")) for it in cenas.get("itens", [])]
        if ids != [c["nn"] for c in caps][:len(ids) if parcial else None]:
            return (f"Os itens do cenas.json precisam ser um por capítulo, nesta ordem de \"id\": "
                    f"{', '.join(c['nn'] for c in caps)} (vieram: {', '.join(ids) or 'nenhum'}).")
        palavras = ler_json(self.p / "_work" / "palavras.json", []) or []
        for it, c in zip(cenas["itens"], caps):
            if c["tipo"] in ("cold_open", "mudo"):
                primeiras = [w["p"] for w in palavras if w["ini"] >= c["ini"] - 0.01][:3]
                it.update({"sem_titulo": True, "nome_fala": " ".join(primeiras)})
                it.pop("titulo", None)
            elif it.get("nome") and it["nome"] != c["nome"] and not it.get("nome_fala"):
                it["nome_fala"] = it["nome"]
            it["nome"] = c["nome"]
        return ""

    _PEDE_TROCA = ("Corrija. Devolva SÓ as cenas que mudaram, em JSON compacto: {\"trocar\": {\"<id do capítulo>\": "
                   "{\"<índice da cena nos itens desse capítulo, começando em 0>\": {<a cena inteira nova>}, \"<índice>\": "
                   "null para apagar}}}. Índice além do fim acrescenta. Para distribuir melhor as variações, troque "
                   "cenas em capítulos diferentes. Se um aviso for inevitável, inclua \"_avisos_aceitos\": \"motivo\".")

    # O vídeo inteiro num pedido só (o 1º teste, 2026-11-05) variou mais que o bloco a bloco, mas saiu raso: 106
    # estados contra 152 e 16,6 assets/min contra 20,4, e a resposta passou do limite de saída. Agora, na mesma
    # conversa: 1º um plano de distribuição do vídeo (que variações cada capítulo usa e como abre), medido pelas regras
    # do vídeo antes de qualquer cena; depois um capítulo por resposta, cada um medido na hora junto com os de antes.
    S_POR_ESTADO = 4.2         # bloco a bloco, o worst draft pick teve 152 estados em 641 s
    _JSON = "Responda SÓ com o JSON, compacto (sem indentação nem quebras de linha), sem texto antes ou depois."

    def _dir_sb(self):
        d = self.p / "_work" / "storyboard"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _chamar_sb(self, sistema, texto, sid, nova, rotulo):
        timeout = int(self.cfg.get("storyboard_timeout_s", 2400) * 1.5)
        r = motor.chamar("storyboard", sistema, texto, canal=self.c, ctx=self.ctx, timeout=timeout,
                         sessao=(sid, nova), texto_livre=True)
        with open(self.log("storyboard"), "a") as f:
            f.write(f"\n=== {rotulo} ({r['_uso']['equivalente']:,} equiv.)\n")
        try:
            return motor._extrair_json(r["texto"])
        except (json.JSONDecodeError, TypeError):
            return None

    def _pedido_plano(self):
        caps = self._capitulos()
        st = self._st_metas()
        linhas = [f"- {c['nn']} {c['nome']}: {c['fim'] - c['ini']:.0f} s → ~{self._estados_previstos(c)} estados"
                  for c in caps]
        mv = st["mv"]
        # o que é do FORMATO vem de biblioteca_cenas.json › metas_video: "pedido_plano" (o ritmo e as regras do plano)
        # e "plano_extra" (o que mais o plano devolve, ex. o elenco do vídeo no cartum); sem eles, os do explained
        ritmo = mv.get("pedido_plano") or (
            f"Um estado para cada ~{self._s_por_estado():.0f} s de narração, como num capítulo feito sozinho (feito "
            "bloco a bloco, este formato teve 1 estado a cada 4,2 s e 20 assets/min; o vídeo inteiro num pedido "
            "só caiu para 1 a cada 6 s e 16,6 assets/min, raso demais):")
        regras = mv.get("regras_plano") or (
            f"As regras do vídeo, que o sistema mede no plano: o vídeo usa ≥ {st['meta_uso']} das "
            f"{st['biblioteca']} variações; nenhuma passa de ~{st['teto']}× no vídeo nem aparece em mais de "
            f"{st['teto_caps']} capítulos; a mesma só volta depois de {st['dist']} estados (contando a virada "
            "de um capítulo para o outro); cada capítulo abre com uma variação diferente; nenhuma sequência de "
            "3 variações se repete.")
        return ("## Fase 1 de 2: o plano de distribuição\n"
                "Ainda sem cenas: leia a transcrição inteira e planeje o vídeo. Depois você vai escrever um capítulo "
                "por resposta, seguindo este plano.\n"
                + ritmo + "\n" + "\n".join(linhas) + "\n"
                + regras + " Use só os códigos da Biblioteca de Cenas: " + ", ".join(st["nomes"]) + ".\n"
                "Devolva {\"plano\": {\"<id>\": {\"abre\": \"<variação do 1º estado depois do título>\", "
                "\"variacoes\": [\"<a variação de cada estado, na ordem, começando pela de abertura>\"], "
                "\"ideia\": \"<uma frase: o que este capítulo mostra e o que o faz diferente dos outros>\"}}"
                + (", " + mv["plano_extra"] if mv.get("plano_extra") else "") + "}. "
                + self._JSON)

    def _st_metas(self):
        """As metas do vídeo (biblioteca_cenas.json › metas_video) em números, para o pedido do plano."""
        bib = ler_json(arquivo_formato("cenas", self.c.get("formato")))
        mv = bib.get("metas_video", {})
        nomes = [v for v in bib["nomes"] if v not in mv.get("fora_da_conta", [])]
        n = sum(self._estados_previstos(c) for c in self._capitulos())
        return {"nomes": nomes, "biblioteca": len(nomes), "mv": mv,
                "meta_uso": math.ceil(mv.get("min_variacoes_frac", 0.75) * len(nomes)),
                "teto": max(mv.get("max_usos_min", 2), math.ceil(mv.get("max_usos_fator", 1.6) * n / len(nomes))),
                "teto_caps": max(2, math.ceil(mv.get("max_capitulos_frac", 0.5) * len(self._capitulos()))),
                "dist": mv.get("min_distancia", 6)}

    def _s_por_estado(self):
        """Segundos de narração por estado no formato do canal (metas_video › s_por_estado; o do explained é 4,2)."""
        bib = ler_json(arquivo_formato("cenas", self.c.get("formato"))) or {}
        return float((bib.get("metas_video") or {}).get("s_por_estado", self.S_POR_ESTADO))

    def _estados_previstos(self, c):
        return max(2, round((c["fim"] - c["ini"]) / self._s_por_estado()))

    def _medir_plano(self, plano):
        arq = self._dir_sb() / "plano_medir.json"
        gravar_json(arq, {"plano": plano})
        _, saida = self.script("storyboard", "storyboard.py", self.p, "--plano", arq)
        arq.unlink(missing_ok=True)
        ids = [c["nn"] for c in self._capitulos()]
        avisos = [l[6:] for l in saida.splitlines() if l.startswith("AVISO")]
        if list(plano) != ids:
            avisos.insert(0, f"o plano precisa ter um item por capítulo, nesta ordem: {', '.join(ids)}")
        return avisos

    def _plano(self, sistema, sid):
        """A fase 1. Devolve o plano (de _work/storyboard/plano.json, se uma rodada anterior já fez)."""
        arq = self._dir_sb() / "plano.json"
        if arq.exists():
            return (ler_json(arq) or {}).get("plano"), False     # de uma rodada anterior: a conversa não existe mais
        self.marcar("storyboard", "rodando", "plano do vídeo")
        texto = self._pedido_storyboard(fim=self._pedido_plano())
        plano, nova, extra = None, True, {}
        for volta in range(3):
            r = self._chamar_sb(sistema, texto, sid, nova, f"plano, volta {volta}")
            nova = False
            plano = (r or {}).get("plano") if isinstance(r, dict) else None
            if not isinstance(plano, dict):
                texto = "A resposta não era o JSON do plano. " + self._JSON
                continue
            # o que mais o formato pediu no plano (metas_video › plano_extra: o elenco do vídeo, no cartum)
            extra = {k: v for k, v in r.items() if k != "plano"}
            avisos = self._medir_plano(plano)
            if not avisos:
                break
            texto = ("O plano está fora das regras do vídeo:\n" + "\n".join(f"- {a}" for a in avisos)
                     + "\n\nCorrija e devolva o plano inteiro de novo. " + self._JSON)
        if not isinstance(plano, dict):
            raise Parada("o Claude não devolveu um plano de distribuição do vídeo")
        gravar_json(arq, {"plano": plano, **extra})      # mesmo com aviso: as regras são medidas de novo no vídeo compilado
        return plano, True

    def _plano_extra(self):
        """O que o plano trouxe além das variações (o elenco do vídeo, no cartum), para lembrar a cada capítulo."""
        d = ler_json(self._dir_sb() / "plano.json") or {}
        return {k: v for k, v in d.items() if k != "plano" and v}

    def _parcial(self, itens):
        """Compila e mede os capítulos feitos até aqui numa pasta à parte (_work/storyboard/parcial), com a narração
        cortada no fim do último: o fim do último capítulo não pode ser o fim do vídeo."""
        d = self._dir_sb() / "parcial"
        (d / "_work").mkdir(parents=True, exist_ok=True)
        if not (d / "assets").exists():
            (d / "assets").symlink_to(self.p / "assets", target_is_directory=True)
        (self.p / "assets").mkdir(exist_ok=True)
        fim = next(c["fim"] for c in self._capitulos() if c["nn"] == itens[-1]["id"])
        palavras = ler_json(self.p / "_work" / "palavras.json", []) or []
        gravar_json(d / "_work" / "palavras.json", [w for w in palavras if w["ini"] < fim - 0.01])
        gravar_json(d / "cenas.json", {"titulo": titulo_video(self.video), "itens": itens})
        for f in (d / "edicao").glob("plano_edicao_*.json") if (d / "edicao").exists() else []:
            f.unlink()
        cod, saida = self.script("storyboard", "compilar_cenas.py", d)
        if cod != 0:
            erros = [l for l in saida.splitlines() if l.startswith("  -") or l.startswith("AVISO")]
            return None, ["o compilador recusou o capítulo:"] + (erros or [saida.strip()[-800:]])
        avisos = [l[6:] for l in saida.splitlines() if l.startswith("AVISO")]
        # os tetos são os do vídeo todo (o tamanho que o plano prevê), não os dos capítulos feitos até aqui
        plano = (ler_json(self._dir_sb() / "plano.json") or {}).get("plano") or {}
        previsto = [str(len(self._capitulos())),
                    str(sum(len(v.get("variacoes") or []) for v in plano.values() if isinstance(v, dict)))]
        _, saida2 = self.script("storyboard", "storyboard.py", d, "--video", "--previsto", *previsto)
        avisos += [l[6:] for l in saida2.splitlines() if l.startswith("AVISO")]
        itens = (ler_json(d / "cenas.json") or {}).get("itens", itens)      # com os ids que o compilador gravou
        return itens, avisos

    @staticmethod
    def _deste(avisos, iid):
        """Dos avisos do vídeo parcial, os que este capítulo pode corrigir agora (os de um capítulo anterior já ficaram
        para trás). Os tetos de uso já vêm medidos contra o vídeo todo (--previsto): passou, é para este capítulo não
        usar mais aquela variação."""
        meus = []
        for a in avisos:
            if a.startswith(f"item {iid}") or a.startswith(f"capítulo {iid}:") or f"capítulo {iid}" in a \
                    or f"({iid})" in a or f", {iid})" in a or a.startswith(("capítulos que abrem", "sequências de 3",
                                                                             "variações usadas demais",
                                                                             "variações em capítulos demais")):
                meus.append(a)
        return meus

    def _o_que_ja_tem(self, feitos):
        if not feitos:
            return ""
        caps = ler_json(self._dir_sb() / "parcial" / "_work" / "variacoes_video.json", []) or []
        cont = {}
        for c in caps:
            for v in c["vars"]:
                cont[v] = cont.get(v, 0) + 1
        ultimos = [v for c in caps for v in c["vars"]][-6:]
        buscas = []
        for it in feitos:
            for cena in it.get("cenas", []):
                for e in cena.get("estados", []):
                    for cd in e.get("cards", []):
                        for x in [cd] + list(cd.get("troca", []) if isinstance(cd, dict) else []):
                            if isinstance(x, dict) and x.get("buscas"):
                                buscas.append(f"{it['id']}: {x['buscas'][0]}")
        elenco = {}
        for it in feitos:
            cards = [it.get("titulo") or {}] + [cd for cena in it.get("cenas", []) for e in cena.get("estados", [])
                                                for cd in e.get("cards", [])]
            for cd in cards:
                for x in [cd, cd.get("sticker") if isinstance(cd, dict) else None] + \
                        list(cd.get("troca", []) if isinstance(cd, dict) else []):
                    if isinstance(x, dict) and x.get("elenco") and x.get("buscas"):
                        elenco.setdefault(x["elenco"], x.get("descricao") or x["buscas"][0][:60])
        return ("O vídeo até aqui (medido): " + " · ".join(f"{c['id']} {c.get('resumo', '')}" for c in caps) + "\n"
                + "Variações já usadas: " + ", ".join(f"{v} ×{n}" for v, n in sorted(cont.items(), key=lambda x: -x[1]))
                + f"\nOs últimos {len(ultimos)} estados (não volte a eles logo no começo): {' → '.join(ultimos)}\n"
                + "Buscas já usadas (a mesma imagem não aparece em dois capítulos): " + "; ".join(buscas) + "\n"
                + ("Elenco já criado neste vídeo (para repetir o MESMO desenho, só {\"elenco\": \"<nome>\"} no "
                   "card, sem buscas): " + "; ".join(f"{k} = {v}" for k, v in elenco.items()) + "\n" if elenco else ""))

    def _pedido_capitulo(self, c, k, plano, feitos):
        pc = plano.get(c["nn"]) or {}
        palavras = [w["p"] for w in ler_json(self.p / "_work" / "palavras.json", []) or []
                    if c["ini"] - 0.01 <= w["ini"] < c["fim"] - 0.01]
        forma = {"cold_open": "sem \"titulo\" (cold open)", "mudo": "sem \"titulo\" (capítulo mudo)"}.get(
            c["tipo"], "com o \"titulo\" (o recorte do card de título)")
        mv = (ler_json(arquivo_formato("cenas", self.c.get("formato"))) or {}).get("metas_video") or {}
        detalhe = mv.get("pedido_capitulo") or (
            "Escreva com o detalhe de um capítulo feito sozinho: 20–25 assets/min, cenas que evoluem em 2–4 "
            "estados, cada asset ≥ 1,8 s. Pode desviar do plano quando a fala pedir, sem usar o que o vídeo já "
            "usou demais.")
        extra = self._plano_extra() if k == 1 or not feitos else {}      # na conversa retomada o plano inteiro já foi
        return (f"## Fase 2: capítulo {c['nn']} — {c['nome']} ({k} de {len(self._capitulos())})\n"
                f"Narração de {c['ini']:.1f} a {c['fim']:.1f} s no tempo do vídeo ({c['fim'] - c['ini']:.0f} s), de "
                f"\"{' '.join(palavras[:6])}\" a \"{' '.join(palavras[-6:])}\": todas as falas cobertas.\n"
                f"O plano dele: abre com {pc.get('abre', '?')}; variações {', '.join(pc.get('variacoes') or [])}; "
                f"{pc.get('ideia', '')}\n" + self._o_que_ja_tem(feitos)
                + ("O que o plano definiu para o vídeo todo: " + json.dumps(extra, ensure_ascii=False) + "\n"
                   if extra else "")
                + detalhe + "\n"
                f"Devolva SÓ o item deste capítulo, {forma}: {{\"id\": \"{c['nn']}\", \"nome\": \"{c['nome']}\", "
                "\"cenas\": [...]}. " + self._JSON)

    def _capitulo(self, sistema, sid, nova, c, k, plano, feitos):
        """Um capítulo da fase 2: pede, mede junto com os de antes e, se tiver aviso dele, pede uma correção."""
        arq = self._dir_sb() / f"{c['nn']}.json"
        if arq.exists():
            return ler_json(arq), nova
        voltas = self.cfg.get("storyboard_voltas_capitulo", 1)
        texto, item, avisos = self._pedido_capitulo(c, k, plano, feitos), None, []
        for volta in range(voltas + 1):
            self.marcar("storyboard", "rodando", f"capítulo {c['nn']} ({k}/{len(self._capitulos())})"
                        + (f", correção {volta}" if volta else ""))
            r = self._chamar_sb(sistema, texto, sid, nova, f"capítulo {c['nn']}, volta {volta}")
            nova = False
            if isinstance(r, dict) and "itens" in r:
                r = next((i for i in r["itens"] if str(i.get("id")) == c["nn"]), None)
            if not isinstance(r, dict) or not isinstance(r.get("cenas"), list):
                texto = f"A resposta não era o item do capítulo {c['nn']}. " + self._JSON
                continue
            r["id"] = c["nn"]
            cenas = {"itens": feitos + [r]}
            self._acertar_itens(cenas, parcial=True)
            itens, todos = self._parcial(cenas["itens"])
            if itens is None:          # não compilou: este capítulo não pode seguir assim
                texto = "\n".join(todos) + f"\n\nCorrija e devolva o item do capítulo {c['nn']} inteiro. " + self._JSON
                continue
            item, avisos = itens[-1], self._deste(todos, c["nn"])
            if not avisos:
                break
            texto = (f"Medido junto com os capítulos de antes, o {c['nn']} tem estes avisos:\n"
                     + "\n".join(f"- {a}" for a in avisos)
                     + f"\n\nCorrija e devolva o item do capítulo {c['nn']} inteiro. " + self._JSON)
        if item is None:
            raise Parada(f"storyboard: o capítulo {c['nn']} não compilou ({' '.join(todos)[-300:]})")
        gravar_json(arq, item)
        return item, nova

    def storyboard(self):
        if (self.p / "plano.json").exists() and (self.p / "storyboard_video.md").exists():
            return "já existe"
        if self._ja_buscou():
            raise Parada("já existe busca/escolhas no vídeo: refazer o storyboard é decisão sua (apague "
                         "producao/_work/candidatos e producao/escolhas.json e rode de novo)")
        sistema = self._sistema_storyboard()
        sid = str(uuid.uuid4())
        voltas = self.cfg.get("storyboard_voltas", 4)
        timeout = int(self.cfg.get("storyboard_timeout_s", 2400) * 1.5)
        ok, retorno, nova = False, "", True
        # já tem um cenas.json (rodada parada no meio, ou escrito à mão): a 1ª volta do vídeo inteiro custa ~850 mil
        # tokens equiv. (medido em 2026-11-05) — então mede o que existe e pede só a correção
        atual = ler_json(self.p / "cenas.json") if (self.p / "cenas.json").exists() else None
        if atual and not self._acertar_itens(atual):
            gravar_json(self.p / "cenas.json", atual)
            ok, retorno = self._compilar_e_medir()
            if ok:
                return "ok (o cenas.json que já existia passou)"
            texto = self._pedido_storyboard(
                fim="## cenas.json que já existe (feito antes; NÃO reescreva o vídeo, corrija só o que os avisos "
                    "abaixo apontam)\n" + json.dumps(atual, ensure_ascii=False, separators=(",", ":"))
                    + "\n\n" + retorno + "\n\n" + self._PEDE_TROCA)
        else:
            # fase 1 (o plano) e fase 2 (um capítulo por resposta), na mesma conversa; o que já foi feito numa
            # rodada anterior fica em _work/storyboard/ e não é pedido de novo
            plano, na_conversa = self._plano(sistema, sid)
            nova = not na_conversa
            feitos = []
            caps = self._capitulos()
            for k, c in enumerate(caps, 1):
                if nova and not (self._dir_sb() / f"{c['nn']}.json").exists():
                    # rodada retomada: a conversa de antes não existe mais; uma nova com o plano e o que já foi feito
                    sid = str(uuid.uuid4())
                    self._chamar_sb(sistema, self._pedido_storyboard(
                        fim="## Plano de distribuição (fase 1, já feito)\n"
                            + json.dumps({"plano": plano, **self._plano_extra()} if self._plano_extra() else plano,
                                         ensure_ascii=False)
                            + "\n\n## Capítulos já escritos (não mude)\n"
                            + json.dumps(feitos, ensure_ascii=False, separators=(",", ":"))
                            + "\n\nResponda só {\"ok\": true}; os próximos capítulos vêm um por mensagem."),
                        sid, True, "retomada")
                    nova = False
                item, nova = self._capitulo(sistema, sid, nova, c, k, plano, feitos)
                feitos.append(item)
            cenas = {"titulo": titulo_video(self.video), "itens": feitos}
            self._acertar_itens(cenas)
            gravar_json(self.p / "cenas.json", cenas)
            shutil.rmtree(self.p / "_work" / "storyboard_feito", ignore_errors=True)
            self._dir_sb().rename(self.p / "_work" / "storyboard_feito")      # refazer = apagar o cenas.json
            ok, retorno = self._compilar_e_medir()
            if ok:
                return f"ok capítulo a capítulo ({len(feitos)} capítulos)"
            texto = retorno + "\n\n" + self._PEDE_TROCA
        for volta in range(voltas + 1):
            self.marcar("storyboard", "rodando", f"vídeo inteiro: correção {volta + 1} de {voltas + 1}")
            r = motor.chamar("storyboard", sistema, texto, canal=self.c, ctx=self.ctx, timeout=timeout,
                             sessao=(sid, nova), texto_livre=True)
            nova = False
            with open(self.log("storyboard"), "a") as f:
                f.write(f"\n=== volta {volta} ({r['_uso']['equivalente']:,} equiv.)\n")
            try:
                cenas = motor._extrair_json(r["texto"])
            except (json.JSONDecodeError, TypeError):
                texto = "A resposta não era um JSON válido. Devolva só o cenas.json completo, sem texto em volta."
                continue
            if "trocar" in cenas and "itens" not in cenas:      # correção parcial: só as cenas que mudaram
                atual = ler_json(self.p / "cenas.json")
                por_id = {it["id"]: it for it in atual["itens"]}
                trocar = cenas["trocar"]
                aceitos = cenas.get("_avisos_aceitos") or (trocar.pop("_avisos_aceitos", None)
                                                           if isinstance(trocar, dict) else None)
                for iid, mudancas in (trocar.items() if isinstance(trocar, dict) else []):
                    if iid not in por_id or not isinstance(mudancas, dict):
                        continue
                    lista = por_id[iid]["cenas"]
                    num = {int(k): v for k, v in mudancas.items() if str(k).lstrip("-").isdigit()}
                    for k, cena in sorted(num.items(), reverse=True):
                        if cena is None:
                            if k < len(lista):
                                lista.pop(k)
                        elif k < len(lista):
                            lista[k] = cena
                        else:
                            lista.append(cena)
                if aceitos:
                    atual["_avisos_aceitos"] = aceitos
                cenas = atual
            problema = self._acertar_itens(cenas)
            if problema:
                texto = problema + " Devolva o cenas.json completo."
                continue
            gravar_json(self.p / "cenas.json", cenas)
            ok, retorno = self._compilar_e_medir()
            if ok:
                return f"ok em {volta + 1} volta(s)"
            if volta == voltas:
                break
            texto = retorno + "\n\n" + self._PEDE_TROCA
        if (self.p / "plano.json").exists() and (self.p / "storyboard_video.md").exists():
            aceitos = (ler_json(self.p / "cenas.json", {}) or {}).get("_avisos_aceitos")
            return f"com avisos ({'aceitos: ' + str(aceitos)[:200] if aceitos else retorno[-300:]})"
        raise Parada(f"storyboard não compilou depois de {voltas + 1} voltas: {retorno[-400:]}")

    # ---------- montagem + render + QA ----------
    def _ids(self):
        return [it["id"] for it in (ler_json(self.p / "plano.json", {}) or {}).get("itens", [])]

    def _corrigir_sar(self):
        """Vídeo com pixel não quadrado (crop do ffmpeg sem setsar=1) sai esticado: corrige antes de montar."""
        for f in (self.p / "assets").rglob("*.mp4") if (self.p / "assets").is_dir() else []:
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=sample_aspect_ratio", "-of", "csv=p=0", str(f)], capture_output=True, text=True)
            sar = r.stdout.strip()
            if sar and sar not in ("1:1", "N/A", "0:1"):
                tmp = f.with_suffix(".sar.mp4")
                if subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-vf", "setsar=1", "-c:v", "libx264",
                                   "-crf", "17", "-pix_fmt", "yuv420p", "-an", str(tmp)]).returncode == 0:
                    tmp.replace(f)

    def _gerar_planos(self):
        """O gerador (o do formato, formato.json › edicao.gerador, ou o gerar_ae2.py do motor) de cada capítulo cujo
        plano_render é mais velho que o que entra nele."""
        gerador = arquivo_formato("edicao.gerador", self.c.get("formato"), exigir=False)
        if not gerador.is_file():
            gerador = Path(self.c["editor"]) / "gerar_ae2.py"
        entradas = [self.p / "manifesto.json", self.p / "cenas.json", self.p / "plano.json", gerador]
        base = max((f.stat().st_mtime for f in entradas if f.exists()), default=0)
        feitos = []
        for nn in self._ids():
            pr = self.p / "edicao" / f"plano_render_{nn}.json"
            pe = self.p / "edicao" / f"plano_edicao_{nn}.json"
            if pr.exists() and pr.stat().st_mtime >= max(base, pe.stat().st_mtime if pe.exists() else 0) \
                    and self.de != "montar":
                continue
            cod, saida = self.script("montar", str(gerador), self.p, "--item", nn)
            if cod != 0 or not pr.exists():
                erro = [l for l in saida.strip().splitlines() if l.strip()][-1:] or ["sem saída"]
                raise Parada(f"a montagem do capítulo {nn} deu erro: {erro[0][:200]} (ver log_montar.txt)")
            feitos.append(nn)
        return feitos

    def _renderizar(self):
        # um render pesado de cada vez no Mac (a mesma trava do After e do vídeo final)
        trava = open(motor.DADOS / "trava_after", "w")
        self.marcar("montar", "rodando", "esperando a vez de renderizar")
        fcntl.flock(trava, fcntl.LOCK_EX)
        try:
            return render_video.renderizar(self.p, avisar=lambda s: self.marcar("montar", "rodando", s))
        except SystemExit as e:
            raise Parada(str(e))
        finally:
            fcntl.flock(trava, fcntl.LOCK_UN)
            trava.close()

    def _qa(self, pedacos):
        """QA de cada capítulo no pedaço dele (o qa_NN.md só vale para o pedaço que ele mediu). Devolve {nn: md} dos
        reprovados."""
        reprovados = {}
        qa_py = Path(self.c["editor"]) / "qa" / "qa_bloco.py"
        for k, p in enumerate(pedacos, 1):
            nn, mp4 = p["nn"], Path(p["saida"])
            md = self.p / "edicao" / f"qa_{nn}.md"
            texto = md.read_text() if md.exists() else ""
            linha = next((l for l in texto.splitlines() if l.startswith("Prévia:")), "")
            if not (md.exists() and md.stat().st_mtime >= mp4.stat().st_mtime and f"`{mp4.name}`" in linha):
                self.marcar("montar", "rodando", f"QA do capítulo {nn} ({k}/{len(pedacos)})")
                self.script("montar", str(qa_py), self.p, "--item", nn, "--video", mp4)
                texto = md.read_text() if md.exists() else ""
            if not _aprovado(texto):
                reprovados[nn] = texto or "o QA não rodou (ver log_montar.txt)"
        return reprovados

    def _corrigir_qa_video(self, reprovados):
        """Uma correção automática: o Claude recebe o QA dos capítulos reprovados e os itens deles, e devolve os
        itens corrigidos; depois compila, busca e escolhe só o que for novo."""
        sistema = self._sistema_storyboard() + "\n\n" + motor.prompt("qa", formato=self.c.get("formato"))
        cen = ler_json(self.p / "cenas.json")
        itens = [it for it in cen["itens"] if it["id"] in reprovados]
        texto = ("\n\n".join(f"## Relatório do QA do capítulo {nn} (qa_{nn}.md)\n{md}" for nn, md in reprovados.items())
                 + "\n\n## Os capítulos reprovados (itens do cenas.json)\n" + json.dumps(itens, ensure_ascii=False)
                 + f"\n\n## transcrição do vídeo\n{(self.p / '_work' / 'transcricao.txt').read_text()}\n\n"
                 "Corrija as FALHAS mexendo o mínimo possível. Aqui, em vez do cenas.json completo, devolva só "
                 "{\"itens\": [os itens corrigidos, com os mesmos \"id\"]}. Mantenha os \"id\" dos cards que já "
                 "existem; card novo vem sem id.")
        r = motor.chamar("qa", sistema, texto, canal=self.c, ctx=self.ctx,
                         timeout=self.cfg.get("storyboard_timeout_s", 1200), texto_livre=True)
        novos = {it.get("id"): it for it in (motor._extrair_json(r["texto"]) or {}).get("itens", [])}
        shutil.copy2(self.p / "cenas.json", self.p / "_estudio" / f"cenas_antes_qa_{time.strftime('%H%M%S')}.json")
        cen["itens"] = [novos.get(it["id"], it) for it in cen["itens"]]
        self._acertar_itens(cen)
        gravar_json(self.p / "cenas.json", cen)
        cod, saida = self.script("montar", "compilar_cenas.py", self.p)
        if cod != 0:
            raise Parada(f"correção do QA não compilou: {saida.strip()[-300:]}")
        self.buscar()          # só os assets novos
        self.escolher()

    def montar(self):
        if not self._ids():
            raise Parada("sem plano.json: rode o storyboard antes")
        self._corrigir_sar()
        self.marcar("montar", "rodando", "montando os capítulos")
        self._gerar_planos()
        pedacos = self._renderizar()
        reprovados = self._qa(pedacos)
        if not reprovados:
            return f"{len(pedacos)} capítulos renderizados · QA aprovado"
        self.marcar("montar", "corrigindo", f"QA reprovou {', '.join(reprovados)}: correção automática")
        self._corrigir_qa_video(reprovados)
        self._gerar_planos()
        pedacos = self._renderizar()
        reprovados = self._qa(pedacos)
        if not reprovados:
            return f"{len(pedacos)} capítulos renderizados · QA aprovado depois de 1 correção automática"
        falhas = [f"{nn}: {l.strip()}" for nn, md in reprovados.items() for l in md.splitlines() if "FALHA" in l][:6]
        raise Parada("QA reprovou de novo: " + " | ".join(falhas))

    # ---------- entrega ----------
    def entregar(self):
        pedacos = ler_json(self.p / "edicao" / "pedacos.json", []) or []
        if not pedacos or not all(Path(p["saida"]).exists() for p in pedacos):
            raise Parada("o vídeo ainda não foi renderizado (etapa montar)")
        pend = conferir_pendentes(self.p) if self.cfg.get("travar_conferir") else {}
        if pend:
            raise Parada(f"{len(pend)} item(ns) para conferir antes de entregar — veja o vídeo e aprove no painel: "
                         + " | ".join(f"{aid}: {t[:80]}" for aid, t in pend.items()))
        fim_dir = self.video / "final"
        fim_dir.mkdir(exist_ok=True)
        nome = re.sub(r'[/:"\\]', "-", titulo_video(self.video)).strip() or self.video.name
        mp4 = fim_dir / f"{nome}.mp4"
        mais_novo = max(Path(p["saida"]).stat().st_mtime for p in pedacos)
        if mp4.exists() and mp4.stat().st_mtime >= mais_novo and self.de != "entregar":
            return f"já entregue ({mp4.relative_to(self.video)})"
        final_mod._guardar_anterior(mp4)
        total = sum(p["dur"] for p in pedacos)
        musica = final_mod.trilha(self.video, fim_dir, total=total)
        self.marcar("entregar", "rodando", "emendando os capítulos com a narração" + (" e a trilha" if musica else ""))
        # o volume da voz é do sistema (config › voz_lufs) e o fundo das pausas é do formato (formato.json › audio);
        # o canal troca os dois em canal.json › audio
        som = {**(ficha_formato(self.c.get("formato")).get("audio") or {}),
               **((ler_json(Path(self.c["raiz"]) / "canal.json", {}) or {}).get("audio") or {})}
        try:
            render_video.emendar(self.p, pedacos, mp4, musica, voz_lufs=som.get("voz_lufs", self.cfg.get("voz_lufs")),
                                 ambiente_dbfs=None if musica else som.get("ambiente_dbfs"))
        except subprocess.CalledProcessError as e:
            raise Parada(f"o FFmpeg falhou ao emendar: {e}")
        final_mod._marcar(self.video, status="ok", etapa="pronto", mp4=str(mp4), fim=time.strftime("%Y-%m-%d %H:%M:%S"),
                          render=True, blocos=len(pedacos), erro="")
        det = f"{mp4.relative_to(self.video)} ({total / 60:.1f} min)"
        try:
            r = limpeza.depois_de_entregar_video(self.video)
            if r:
                det += f" · limpeza: {limpeza.gb(r[0])} para o Lixo"
        except OSError as e:
            det += f" · limpeza não rodou: {e}"
        return det


def main(argv=None):
    ap = argparse.ArgumentParser(prog="space_machine rodar")
    ap.add_argument("video")
    ap.add_argument("--de", choices=ETAPAS_VIDEO)
    ap.add_argument("--ate", choices=ETAPAS_VIDEO)
    ap.add_argument("--obs", default="")
    a = ap.parse_args(argv)
    r = RodadaVideo(a.video, obs=a.obs)
    ok = r.rodar(a.de, a.ate)
    if not ok:
        p = r.estado.get("parado") or {}
        print(f"\nPAROU em {p.get('etapa')}: {p.get('motivo')}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
