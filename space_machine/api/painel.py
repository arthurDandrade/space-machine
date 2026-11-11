"""O que o painel mostra de cada canal: a lista de canais, a tela do canal, a busca, os avisos e o
/api/eventos, que avisa o navegador quando algo muda nas pastas.
"""
import asyncio
import hashlib
import time
from pathlib import Path

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

from .. import atualizar, capas, estado, gestao, meus_prompts, primeiros_passos, textos
from ..motor_claude import canais
from .. import fichas
from .. import sistema as sistema_mod
from ..rodar import ETAPAS as ETAPAS_RODAR
from ..sistema import DADOS, config, ficha_formato, ler_json
from .comum import _cache_falta, _canal, _consumo_7d, _estado_bloco, _identidade, _video, marca

api = APIRouter(prefix="/api")


def _rodando(slug, v, b):
    """Etapa em que uma rodada está agora (estado.json do bloco) e desde quando (o pid nasce com ela)."""
    pasta = Path(_canal(slug)["producoes"]) / v["slug"] / "blocos" / b["nn"] / "_estudio"
    est = ler_json(pasta / "estado.json", {}) or {}
    atual = est.get("atual") or ""
    try:
        desde = (pasta / "pid").stat().st_mtime
    except OSError:
        desde = None
    return {"video": v["slug"], "video_titulo": v["titulo"], "nn": b["nn"], "topico": b["topico"], "etapa": atual,
            "tem_capa": bool(capas.fontes(v["pasta"], b["nn"])),
            "indice": ETAPAS_RODAR.index(atual) + 1 if atual in ETAPAS_RODAR else 0, "total": len(ETAPAS_RODAR),
            "detalhe": (est.get("etapas", {}).get(atual) or {}).get("detalhe", ""), "desde": desde}


def _falta_algo():
    """primeiros_passos roda alguns comandos (versões): guarda a resposta por 1 min."""
    if time.time() - _cache_falta["quando"] > 60:
        _cache_falta.update(quando=time.time(), falta=primeiros_passos.falta_algo())
    return _cache_falta["falta"]


def _resumo_canal(slug, c):
    """(resumo do canal, vídeos resumidos, vídeos como estado.videos devolve) — estado.videos lê todos os blocos:
    uma vez por pedido."""
    brutos = estado.videos(slug) if c.get("ativo") else []
    vids = [_video(slug, v) for v in brutos]
    colunas = {col: 0 for col, _ in gestao.COLUNAS}
    for v in vids:
        colunas[v["coluna"]] += 1
    colunas["ideia"] = len(gestao.ideias(slug))
    atual = next((v for v in vids if v["coluna"] == "producao"), None) or next(
        (v for v in vids if v["coluna"] == "roteiro"), None)
    return {
        "slug": slug, "nome": c["nome"], "tema": c.get("tema", ""), "idioma": c.get("idioma", "en"),
        "ativo": bool(c.get("ativo")), "cores": _identidade(c),
        # o formato tem agente de roteiro: o vídeo novo pode nascer só do título (gestao.escrever_roteiro)
        "escreve_roteiro": bool((ficha_formato(c.get("formato")).get("roteiro") or {}).get("modelo")),
        "capitulo_falado": (ficha_formato(c.get("formato")).get("roteiro") or {}).get("capitulo_falado", True),
        "banner": bool(marca(c, "banner")), "logo": bool(marca(c, "logo")),
        "colunas": colunas, "n_videos": len(vids),
        "rodando": sum(v["rodando"] for v in vids), "esperando": sum(v["esperando"] for v in vids),
        "atual": {k: atual[k] for k in ("slug", "titulo", "n_blocos", "entregues", "rodando", "tem_capa", "capa_v")} if atual else None,
        "rodando_agora": [b["nn"] for b in (atual or {}).get("blocos", []) if b["estado"] == "run"],
    }, vids, brutos


# ---------------- leitura ----------------
@api.get("/sistema")
def sistema():
    idioma = config().get("idioma_painel", "pt")
    atualizar.conferir_atras_das_cortinas()      # a conferida vai à rede no máximo a cada 6 h, fora deste pedido
    return {"idioma": idioma, "textos": {**textos._idioma("pt"), **textos._idioma(idioma)},
            "falta_algo": _falta_algo(), "dados": str(DADOS), "atualizacao": atualizar.aviso()}


@api.get("/canais")
def lista_canais():
    lista = [_resumo_canal(s, c)[0] for s, c in canais().items()]
    return {"canais": lista, "rodando": sum(c["rodando"] for c in lista),
            "esperando": sum(c["esperando"] for c in lista), "consumo_7d": _consumo_7d()["total"],
            "falta_algo": _falta_algo()}


@api.post("/canais/ordem")
def ordenar_canais(ordem: list = Body(..., embed=True)):
    """A ordem dos canais na tela inicial (e na troca de canal), arrastando os cartões."""
    return {"ok": True, "ordem": sistema_mod.ordenar_canais([str(s) for s in ordem])}


def _segundos(quando):
    """"2026-11-11 16:40:02" → segundos (para o painel dizer há quanto tempo), ou None."""
    try:
        return time.mktime(time.strptime(quando, "%Y-%m-%d %H:%M:%S"))
    except (TypeError, ValueError):
        return None


@api.get("/c/{slug}")
def painel_canal(slug: str):
    c = _canal(slug)
    resumo, vids, brutos = _resumo_canal(slug, c)
    esperando, rodando, filas = [], [], []
    for v, bruto in zip(vids, brutos):
        rot = bruto.get("roteiro") or {}
        if rot and not v["n_blocos"]:       # vídeo novo cujo roteiro o Claude está escrevendo (ou não conseguiu)
            linha = {"video": v["slug"], "video_titulo": v["titulo"], "nn": "", "topico": "Roteiro", "etapa": "roteiro",
                     "tem_capa": bool(capas.fontes(bruto["pasta"]))}
            if rot.get("rodando"):
                rodando.append({**linha, "indice": 0, "total": 0, "detalhe": rot.get("etapa", ""),
                                "desde": _segundos(rot.get("inicio"))})
            elif rot.get("status") in ("erro", "parado"):
                esperando.append({**linha, "motivo": rot.get("erro", ""), "mudou": bruto["mudou"]})
        prod = bruto.get("producao")
        if prod:             # fluxo "video": uma linha pelo vídeo inteiro (nn vazio = a página do vídeo)
            etapa = prod["etapa_atual"] if prod["rodando"] else (prod["parado"] or {}).get("etapa", "")
            rot = dict(estado.ETAPAS_VIDEO).get(etapa, etapa)
            linha = {"video": v["slug"], "video_titulo": v["titulo"], "nn": "", "topico": rot,
                     "tem_capa": bool(capas.fontes(bruto["pasta"])), "etapa": etapa}
            if prod["rodando"]:
                ids = [e for e, _ in estado.ETAPAS_VIDEO]
                det = next((e["detalhe"] for e in prod["etapas"] if e["id"] == etapa), "")
                rodando.append({**linha, "indice": ids.index(etapa) + 1 if etapa in ids else 0, "total": len(ids),
                                "detalhe": det, "desde": prod["mudou"] or None})
            elif prod["parado"]:
                esperando.append({**linha, "motivo": prod["parado"].get("motivo", ""), "mudou": prod["mudou"]})
            continue
        for b, info in zip(bruto["blocos"], v["blocos"]):
            if info["estado"] == "wait":
                esperando.append({"video": v["slug"], "video_titulo": v["titulo"], "nn": b["nn"], "topico": b["topico"],
                                  "tem_capa": bool(capas.fontes(bruto["pasta"], b["nn"])),
                                  "etapa": (b["parado"] or {}).get("etapa", ""),
                                  "motivo": (b["parado"] or {}).get("motivo", ""), "mudou": b["mudou"]})
            elif info["estado"] == "run":
                rodando.append(_rodando(slug, bruto, b))
        if v["fila"] and v["fila"].get("ativa"):
            filas.append({"video": v["slug"], "video_titulo": v["titulo"], **v["fila"]})
    hoje = time.strftime("%Y-%m-%d")
    publicacoes = sorted(({"video": v["slug"], "titulo": v["titulo_pub"] or v["titulo"], "data": v["data_pub"],
                           "coluna": v["coluna"]} for v in vids if v["data_pub"] >= hoje), key=lambda p: p["data"])
    destaque = next((v for v in vids if v["slug"] == (resumo["atual"] or {}).get("slug")), None)
    return {"canal": resumo, "colunas": [{"id": col, "rotulo": rot, "n": resumo["colunas"][col]}
                                         for col, rot in gestao.COLUNAS],
            "videos": vids, "destaque": destaque, "esperando": sorted(esperando, key=lambda e: -e["mudou"]),
            "rodando": rodando, "filas": filas, "publicacoes": publicacoes, "consumo_7d": _consumo_7d(slug)}


@api.get("/busca")
def busca():
    """Tudo o que a busca (⌘K) encontra: canais, vídeos e blocos dos canais ativos."""
    out = {"canais": [], "videos": [], "blocos": [], "prompts": []}
    for slug, c in canais().items():
        out["canais"].append({"slug": slug, "nome": c["nome"], "tema": c.get("tema", "")})
        out["prompts"] += [{"canal": slug, "canal_nome": c["nome"], "nome": p["nome"], "titulo": p["titulo"]}
                           for p in meus_prompts.listar(slug)]
        if not c.get("ativo"):
            continue
        for v in estado.videos(slug):
            g = gestao.dados_video(slug, v["slug"])
            titulo = g.get("titulo_pub") or v["titulo"]
            out["videos"].append({"canal": slug, "canal_nome": c["nome"], "slug": v["slug"], "titulo": titulo})
            out["blocos"] += [{"canal": slug, "video": v["slug"], "video_titulo": titulo, "nn": b["nn"],
                               "topico": b["topico"]} for b in v["blocos"]]
    return out


@api.get("/avisos")
def avisos():
    """O que pede atenção, de todos os canais ativos: blocos parados esperando você, filas pausadas e blocos
    entregues nas últimas 24 h. Mais novo em cima."""
    itens, agora = [], time.time()
    for slug, c in canais().items():
        if not c.get("ativo"):
            continue
        for v in estado.videos(slug):
            f = v.get("fila") or {}
            base = {"canal": slug, "canal_nome": c["nome"], "video": v["slug"], "video_titulo": v["titulo"]}
            if f.get("ativa") and f.get("status") == "pausada":
                arq = Path(v["pasta"]) / "_estudio" / "fila.json"
                itens.append({**base, "tipo": "fila", "nn": "", "topico": "", "texto": f.get("motivo", ""),
                              "quando": arq.stat().st_mtime if arq.exists() else agora})
            for b in v["blocos"]:
                est = _estado_bloco(b, f)
                if est == "wait":
                    itens.append({**base, "tipo": "esperando", "nn": b["nn"], "topico": b["topico"],
                                  "texto": (b["parado"] or {}).get("motivo", ""), "etapa": (b["parado"] or {}).get("etapa", ""),
                                  "quando": b["mudou"] or agora})
                elif est == "ok":
                    arq = Path(v["pasta"]) / "edicao" / f"bloco {int(b['nn'])}.mp4"
                    quando = arq.stat().st_mtime if arq.exists() else 0
                    if agora - quando < 86400:
                        itens.append({**base, "tipo": "entregue", "nn": b["nn"], "topico": b["topico"], "texto": "",
                                      "quando": quando})
    for i in itens:
        i["id"] = f"{i['tipo']}:{i['canal']}:{i['video']}:{i['nn']}:{int(i['quando'])}"
    return {"itens": sorted(itens, key=lambda i: -i["quando"])[:50]}


# ---------------- ao vivo ----------------
def assinatura():
    """Muda quando muda algo que o painel mostra: pastas e arquivos de estado dos blocos, filas, canal.json, o banco
    (consumo, gestão) e quem está vivo (uma rodada que morre sem mexer em arquivo também conta)."""
    h = hashlib.md5()

    def marcar(p):
        try:
            h.update(f"{p}:{p.stat().st_mtime_ns};".encode())
        except OSError:
            h.update(f"{p}:-;".encode())

    marcar(DADOS / "space_machine.sqlite")
    for c in canais().values():
        marcar(Path(c["raiz"]) / "canal.json")
        marcar(Path(c["raiz"]) / "prompts")
        raiz_fichas = Path(c["raiz"]) / fichas.PASTA        # publicação, thumbnail, arquivar: tudo passa pela ficha
        marcar(raiz_fichas)
        for f in raiz_fichas.iterdir() if raiz_fichas.is_dir() else []:
            marcar(f)
            marcar(f / "ficha.json")
        prod = Path(c["producoes"])
        if not prod.is_dir():
            continue
        marcar(prod)
        for vd in prod.iterdir():
            if not vd.is_dir() or vd.name.startswith((".", "_")):
                continue
            for p in (vd, vd / "edicao", vd / "_estudio" / "fila.json", vd / "_estudio" / "roteiro.json",
                      vd / "estudio_video.json", vd / "blocos",
                      vd / "final" / "estado.json"):
                marcar(p)
            if (vd / "final" / "pid").exists():
                h.update(f"vivo:{estado._vivo((vd / 'final' / 'pid').read_text().strip())};".encode())
            est_v = vd / "producao" / "_estudio"        # fluxo "video": o vídeo inteiro
            if est_v.is_dir():
                for p in (est_v, est_v / "estado.json", est_v / "log_rodar.txt", est_v / "conferir_ok.json"):
                    marcar(p)
                if (est_v / "pid").exists():
                    h.update(f"vivo:{estado._vivo((est_v / 'pid').read_text().strip())};".encode())
            if not (vd / "blocos").is_dir():
                continue
            for b in (vd / "blocos").iterdir():
                est = b / "_estudio"
                for p in (b, b / "edicao", est, est / "estado.json", est / "log_rodar.txt", est / "conferir_ok.json",
                          vd / "reels" / f"estado_{b.name}.json"):
                    marcar(p)
                if (vd / "reels" / f"pid_{b.name}").exists():
                    h.update(f"vivo:{estado._vivo((vd / 'reels' / f'pid_{b.name}').read_text().strip())};".encode())
                pid = est / "pid"
                if pid.exists():
                    h.update(f"vivo:{estado._vivo(pid.read_text().strip())};".encode())
    return h.hexdigest()


@api.get("/eventos")
async def eventos(request: Request):
    async def fluxo():
        ultima, quieto = None, 0
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            agora = await asyncio.to_thread(assinatura)
            if agora != ultima:
                ultima, quieto = agora, 0
                yield f"data: {agora}\n\n"
            else:
                quieto += 1
                if quieto % 10 == 0:
                    yield ": oi\n\n"          # mantém a conexão viva
            await asyncio.sleep(2)

    return StreamingResponse(fluxo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
