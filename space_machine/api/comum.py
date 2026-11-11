"""O que as rotas da API têm em comum: achar o canal, o vídeo e o bloco pelo endereço (404 quando não existe)
e montar os resumos que mais de uma tela usa.
"""
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException

from .. import capas, gestao
from ..motor_claude import _banco, canais
from .. import fichas
from ..sistema import ler_json


IMAGENS = (".png", ".jpg", ".jpeg", ".webp")


# ---------------- ajudantes ----------------
def _canal(slug):
    c = canais().get(slug)
    if not c:
        raise HTTPException(404, "canal não encontrado")
    return c


def _video_dir(slug, video):
    vd = Path(_canal(slug)["producoes"]) / video
    # vídeo arquivado não tem pasta de produção: existe pela ficha (fichas.py)
    if "/" in video or video.startswith((".", "_")) or not (vd.is_dir() or fichas.existe(vd)):
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


def _estado_capitulo(prod):
    """Fluxo "video": os capítulos andam juntos, então todos têm o estado do vídeo inteiro."""
    if prod["rodando"]:
        return "run"
    if prod["feito"]["entregar"]:
        return "ok"
    if prod["parado"]:
        return "wait"
    return "meio" if prod["atual"] else "todo"


def _video(slug, v):
    f = v.get("fila") or {}
    g = gestao.dados_video(slug, v["slug"])
    prod = v.get("producao")
    blocos = [{"nn": b["nn"], "topico": b["topico"], "estado": _estado_capitulo(prod) if prod else _estado_bloco(b, f)}
              for b in v["blocos"]]
    conta = lambda e: sum(1 for b in blocos if b["estado"] == e)
    return {
        "slug": v["slug"], "titulo": v["titulo"], "titulo_pub": g.get("titulo_pub") or "",
        "coluna": gestao.coluna_do_video(v, g), "n_blocos": v["n_blocos"], "entregues": v["entregues"],
        "rodando": conta("run"), "esperando": conta("wait"), "na_fila": conta("fila"), "blocos": blocos,
        "fluxo": v.get("fluxo", "blocos"),
        "arquivado": v.get("arquivado") or "", "numero": v.get("numero") or 0, "pronto": v.get("pronto") or "",
        "duracao_s": v.get("duracao_s") or 0, "n_blocos_ficha": v.get("n_blocos_ficha") or 0,
        "mudou": v["mudou"], "data_pub": (g.get("data_pub") or "")[:10], "link": g.get("link") or "",
        "fila": _resumo_fila(f), "consumo": (v.get("consumo") or {}).get("equivalente") or 0,
        "tem_capa": bool(capas.fontes(v["pasta"])), "capa_v": _versao_capa(v["pasta"]), "thumb": _thumb(v["pasta"]),
    }


def _versao_capa(vd):
    """Muda quando a thumbnail muda: vai no endereço da capa para o navegador não mostrar a antiga do cache."""
    t = capas.thumbnail(vd)
    return int(t.stat().st_mtime) if t else 0


def _thumb(vd):
    """Thumbnail para os botões da capa nas listas (ampliar, baixar): endereço e nome do arquivo enviado."""
    info = capas.info_thumbnail(vd)
    if not info:
        return None
    return {"url": _arquivo(info["arquivo"]) + f"&v={info['versao']}", "nome": info.get("nome") or Path(info["arquivo"]).name}


def _consumo_7d(slug=None):
    con = _banco()
    filtro, vals = ("and canal = ?", (slug,)) if slug else ("and canal != 'teste'", ())
    linhas = con.execute(f"""select etapa, sum(equivalente) from chamadas
                             where ok = 1 and quando >= datetime('now', 'localtime', '-7 days') {filtro}
                             group by etapa order by 2 desc""", vals).fetchall()
    con.close()
    return {"total": sum(n or 0 for _, n in linhas), "etapas": [{"etapa": e, "tokens": n or 0} for e, n in linhas]}


_cache_falta = {"quando": 0, "falta": False}


def _arquivo(p):
    """Endereço de um arquivo da produção pela rota /arquivo do servidor (só serve de dentro das produções)."""
    return f"/arquivo?p={quote(str(p))}"


def _cauda(arq, linhas):
    try:
        return "\n".join(Path(arq).read_text(errors="replace").splitlines()[-linhas:])
    except OSError:
        return ""


def _curto(vd, texto):
    """Caminho dentro do vídeo vira relativo: na linha da etapa, no painel, o caminho inteiro só cabia cortado."""
    return texto.replace(f"{vd}/", "") if isinstance(texto, str) else texto
