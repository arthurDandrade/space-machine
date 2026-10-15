"""API do painel React (painel/, servido em /app).

Lê o mesmo que o painel antigo: as pastas (estado.py), a gestão (ideias, publicação) e o consumo no sqlite.
As ações chamam as mesmas funções das rotas antigas (fila.lancar_rodada, fila.lancar_fila, ...).
/api/eventos avisa o navegador quando alguma pasta de produção muda, para a tela se atualizar sozinha.
"""
import asyncio
import hashlib
import time
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from . import capas, estado, fila, gestao, primeiros_passos, textos
from .motor_claude import _banco, canais
from .rodar import ETAPAS as ETAPAS_RODAR
from .sistema import DADOS, config, ler_json

api = APIRouter(prefix="/api")
IMAGENS = (".png", ".jpg", ".jpeg", ".webp")


# ---------------- ajudantes ----------------
def _canal(slug):
    c = canais().get(slug)
    if not c:
        raise HTTPException(404, "canal não encontrado")
    return c


def _video_dir(slug, video):
    vd = Path(_canal(slug)["producoes"]) / video
    if "/" in video or video.startswith((".", "_")) or not vd.is_dir():
        raise HTTPException(404, "vídeo não encontrado")
    return vd


def _bloco_dir(slug, video, nn):
    b = _video_dir(slug, video) / "blocos" / nn
    if not nn.isdigit() or not b.is_dir():
        raise HTTPException(404, "bloco não encontrado")
    return b


def marca(c, nome):
    """identidade/banner.* ou identidade/logo.* do canal (o nome exato vence: logo.webp antes de logo2.png)."""
    pasta = Path(c["raiz"]) / "identidade"
    achados = [f for f in pasta.glob(f"{nome}*") if f.suffix.lower() in IMAGENS] if pasta.exists() else []
    achados.sort(key=lambda f: (f.stem != nome, f.name))
    return achados[0] if achados else None


def _identidade(c):
    ident = (ler_json(Path(c["raiz"]) / "canal.json", {}) or {}).get("identidade", {})
    return {k: ident.get(k) for k in ("cor_fundo", "cor_texto", "cor_destaque", "cor_caixa", "cor_sombra")}


def _estado_bloco(b, f):
    """run (rodando) · ok (entregue) · fila (na fila) · wait (parado, esperando você) · meio (começou) · todo."""
    if b["rodando"]:
        return "run"
    if b["feito"]["entregue"]:
        return "ok"
    if f.get("ativa") and b["nn"] in (f.get("esperando") or []):
        return "fila"
    if b["parado"]:
        return "wait"
    return "meio" if b["atual"] != "roteiro" else "todo"


def _resumo_fila(f):
    if not f:
        return None
    return {k: f.get(k) for k in ("ativa", "status", "rodando", "esperando", "parados", "max", "motivo", "inicio", "fim")}


def _video(slug, v):
    f = v.get("fila") or {}
    g = gestao.dados_video(slug, v["slug"])
    blocos = [{"nn": b["nn"], "topico": b["topico"], "estado": _estado_bloco(b, f)} for b in v["blocos"]]
    conta = lambda e: sum(1 for b in blocos if b["estado"] == e)
    return {
        "slug": v["slug"], "titulo": v["titulo"], "titulo_pub": g.get("titulo_pub") or "",
        "coluna": gestao.coluna_do_video(v, g), "n_blocos": v["n_blocos"], "entregues": v["entregues"],
        "rodando": conta("run"), "esperando": conta("wait"), "na_fila": conta("fila"), "blocos": blocos,
        "mudou": v["mudou"], "data_pub": (g.get("data_pub") or "")[:10], "link": g.get("link") or "",
        "fila": _resumo_fila(f), "consumo": (v.get("consumo") or {}).get("equivalente") or 0,
    }


def _consumo_7d(slug=None):
    con = _banco()
    filtro, vals = ("and canal = ?", (slug,)) if slug else ("and canal != 'teste'", ())
    linhas = con.execute(f"""select etapa, sum(equivalente) from chamadas
                             where ok = 1 and quando >= datetime('now', 'localtime', '-7 days') {filtro}
                             group by etapa order by 2 desc""", vals).fetchall()
    con.close()
    return {"total": sum(n or 0 for _, n in linhas), "etapas": [{"etapa": e, "tokens": n or 0} for e, n in linhas]}


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
            "indice": ETAPAS_RODAR.index(atual) + 1 if atual in ETAPAS_RODAR else 0, "total": len(ETAPAS_RODAR),
            "detalhe": (est.get("etapas", {}).get(atual) or {}).get("detalhe", ""), "desde": desde}


_cache_falta = {"quando": 0, "falta": False}


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
        "banner": bool(marca(c, "banner")), "logo": bool(marca(c, "logo")),
        "colunas": colunas, "n_videos": len(vids),
        "rodando": sum(v["rodando"] for v in vids), "esperando": sum(v["esperando"] for v in vids),
        "atual": {k: atual[k] for k in ("slug", "titulo", "n_blocos", "entregues", "rodando")} if atual else None,
        "rodando_agora": [b["nn"] for b in (atual or {}).get("blocos", []) if b["estado"] == "run"],
    }, vids, brutos


# ---------------- leitura ----------------
@api.get("/sistema")
def sistema():
    idioma = config().get("idioma_painel", "pt")
    return {"idioma": idioma, "textos": {**textos._idioma("pt"), **textos._idioma(idioma)},
            "falta_algo": _falta_algo(), "dados": str(DADOS)}


@api.get("/canais")
def lista_canais():
    lista = [_resumo_canal(s, c)[0] for s, c in canais().items()]
    return {"canais": lista, "rodando": sum(c["rodando"] for c in lista),
            "esperando": sum(c["esperando"] for c in lista), "consumo_7d": _consumo_7d()["total"],
            "falta_algo": _falta_algo()}


@api.get("/c/{slug}")
def painel_canal(slug: str):
    c = _canal(slug)
    resumo, vids, brutos = _resumo_canal(slug, c)
    esperando, rodando, filas = [], [], []
    for v, bruto in zip(vids, brutos):
        for b, info in zip(bruto["blocos"], v["blocos"]):
            if info["estado"] == "wait":
                esperando.append({"video": v["slug"], "video_titulo": v["titulo"], "nn": b["nn"], "topico": b["topico"],
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


# ---------------- imagens ----------------
@api.get("/c/{slug}/marca/{qual}")
def imagem_marca(slug: str, qual: str):
    if qual not in ("banner", "logo"):
        raise HTTPException(404)
    f = marca(_canal(slug), qual)
    if not f:
        raise HTTPException(404, f"o canal não tem {qual}")
    if qual == "banner":
        f = capas.banner(slug, f)
    return FileResponse(f, headers={"Cache-Control": "no-cache"})


@api.get("/c/{slug}/v/{video}/capa")
def imagem_capa(slug: str, video: str, nn: str = ""):
    if nn and not nn.isdigit():
        raise HTTPException(404)
    f = capas.capa(slug, _video_dir(slug, video), nn or None)
    if not f:
        raise HTTPException(404, "ainda não há de onde tirar a capa")
    return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


# ---------------- ações ----------------
@api.post("/c/{slug}/v/{video}/fila")
def produzir_todos(slug: str, video: str, maximo: int = Body(3, embed=True)):
    vd = _video_dir(slug, video)
    if not fila.ler_fila(vd).get("ativa"):
        fila.lancar_fila(vd, max(1, min(maximo, 5)))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/fila/parar")
def parar_fila(slug: str, video: str):
    fila.parar_fila(_video_dir(slug, video))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/b/{nn}/parar")
def parar_bloco(slug: str, video: str, nn: str):
    fila.parar_rodada(_bloco_dir(slug, video, nn))
    return {"ok": True}


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
        prod = Path(c["producoes"])
        if not prod.is_dir():
            continue
        marcar(prod)
        for vd in prod.iterdir():
            if not vd.is_dir() or vd.name.startswith((".", "_")):
                continue
            for p in (vd, vd / "edicao", vd / "_estudio" / "fila.json", vd / "estudio_video.json", vd / "blocos"):
                marcar(p)
            if not (vd / "blocos").is_dir():
                continue
            for b in (vd / "blocos").iterdir():
                est = b / "_estudio"
                for p in (b, b / "edicao", est, est / "estado.json", est / "log_rodar.txt", est / "conferir_ok.json"):
                    marcar(p)
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
