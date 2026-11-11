"""Um bloco de um vídeo: a página dele, rodar, parar, conferir, Reels, limpar e excluir.
"""
import re

from fastapi import APIRouter, Body, HTTPException

from .. import estado, fila, gestao, reels
from ..rodar import ETAPAS as ETAPAS_RODAR
from ..sistema import ler_json
from .comum import _arquivo, _bloco_dir, _canal, _cauda, _curto

api = APIRouter(prefix="/api")


@api.get("/c/{slug}/v/{video}/b/{nn}")
def detalhe_bloco(slug: str, video: str, nn: str):
    b = _bloco_dir(slug, video, nn)
    vd = b.parent.parent
    info = estado.bloco(b, vd)
    est = ler_json(b / "_estudio" / "estado.json", {}) or {}
    manifesto = {a["id"]: a for a in (ler_json(b / "manifesto.json", {}) or {}).get("assets", []) if a.get("id")}
    conferir = []
    for aid, texto in info["conferir_pendentes"].items():
        a = manifesto.get(aid, {})
        conferir.append({"id": aid, "texto": texto, "tipo": a.get("tipo", ""), "descricao": a.get("descricao", ""),
                         "arquivo": _arquivo(b / a["arquivo"]) if a.get("arquivo") and (b / a["arquivo"]).exists() else None})
    logs = sorted((b / "_estudio").glob("log_*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    etapa_log = next((f for f in logs if f.name != "log_rodar.txt"), None)
    irmaos = sorted(p.name for p in (vd / "blocos").iterdir() if p.is_dir() and p.name.isdigit())
    i = irmaos.index(nn)
    entregue = vd / "edicao" / f"bloco {int(nn)}.mp4"
    qa_img = b / "edicao" / f"qa_{nn}.jpg"
    sb = b / f"storyboard_{nn}.md"
    rl = reels.ler_estado(b)
    rl_mp4 = reels.mp4(b)
    return {
        "nn": nn, "topico": info["topico"], "video": video, "video_titulo": estado.titulo_video(vd),
        "feito": info["feito"], "atual": info["atual"], "rodando": info["rodando"], "parado": info["parado"],
        "aprovado": info["aprovado"], "travar_conferir": info["travar_conferir"],
        "etapa_atual": est.get("atual") or "",
        "etapas": [{"id": e, **{k: _curto(vd, (est.get("etapas", {}).get(e) or {}).get(k, "")) for k in ("status", "detalhe", "quando")}}
                   for e in ETAPAS_RODAR],
        "previas": [{"v": int(re.search(r"_v(\d+)\.mp4$", p).group(1)), "url": _arquivo(p)} for p in info["previas"]],
        "entregue": _arquivo(entregue) if entregue.exists() else None,
        "qa": info["qa"], "qa_folha": _arquivo(qa_img) if qa_img.exists() else None,
        "storyboard": sb.read_text() if sb.exists() else "",
        # roteiro do bloco sem as linhas "#" (o "# Nome" e a marca de cold open não são narrados)
        "roteiro": "\n".join(l for l in _cauda(b / "roteiro.txt", 400).splitlines() if not l.startswith("#")).strip(),
        "conferir": conferir, "conferidos": len(info["conferir"]) + len(info["pulados"]) - len(conferir),
        "revisao": _arquivo(info["revisao"]) if info["revisao"] else None,
        "assets_total": info["assets_total"], "assets_prontos": info["assets_prontos"],
        "log_rodar": _cauda(b / "_estudio" / "log_rodar.txt", 60),
        "log_etapa": {"nome": etapa_log.name, "texto": _cauda(etapa_log, 40)} if etapa_log else None,
        "anterior": irmaos[i - 1] if i > 0 else None, "proximo": irmaos[i + 1] if i + 1 < len(irmaos) else None,
        "reels": {"pode": (b / "edicao" / f"plano_edicao_{nn}.json").exists(), "rodando": rl["rodando"],
                  "status": rl.get("status", ""), "etapa": rl.get("etapa", ""), "erro": rl.get("erro", ""),
                  # durante o render o After já está gravando o MP4: só aparece pronto
                  "mp4": _arquivo(rl_mp4) + f"&v={int(rl_mp4.stat().st_mtime)}"
                  if rl_mp4.exists() and not rl["rodando"] else None},
    }


@api.post("/c/{slug}/v/{video}/b/{nn}/parar")
def parar_bloco(slug: str, video: str, nn: str):
    fila.parar_rodada(_bloco_dir(slug, video, nn))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/b/{nn}/rodar")
def rodar_bloco(slug: str, video: str, nn: str, de: str = Body("", embed=True), ate: str = Body("", embed=True),
                obs: str = Body("", embed=True)):
    b = _bloco_dir(slug, video, nn)
    if estado.bloco(b)["rodando"]:
        raise HTTPException(409, "esse bloco já está rodando")
    fila.lancar_rodada(b, de, ate, obs)
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/b/{nn}/conferir")
def conferir_bloco(slug: str, video: str, nn: str):
    """Quem produz viu a prévia e aprovou os itens de "conferir". Com a trava ligada, já entrega."""
    b = _bloco_dir(slug, video, nn)
    estado.aprovar_conferir(b)
    info = estado.bloco(b)
    if info["travar_conferir"] and not info["rodando"]:
        fila.lancar_rodada(b, "entregar", "entregar", "")
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/b/{nn}/reels")
def fazer_reels(slug: str, video: str, nn: str):
    """Monta o bloco na vertical (1080x1920) e renderiza <vídeo>/reels/bloco N.mp4."""
    b = _bloco_dir(slug, video, nn)
    if reels.ler_estado(b)["rodando"]:
        raise HTTPException(409, "o Reels deste bloco já está sendo feito")
    if not (b / "edicao" / f"plano_edicao_{nn}.json").exists():
        raise HTTPException(409, "o bloco ainda não chegou na edição")
    reels.lancar(b)
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/b/{nn}/limpar")
def limpar_bloco(slug: str, video: str, nn: str):
    """Zera o bloco (só o que a produção fez vai para o Lixo); o bloco continua no vídeo, com o roteiro."""
    try:
        return {"ok": True, **gestao.limpar_bloco(_canal(slug), video, nn)}
    except ValueError as e:
        raise HTTPException(409, str(e))


@api.post("/c/{slug}/v/{video}/b/{nn}/excluir")
def excluir_bloco(slug: str, video: str, nn: str):
    try:
        return {"ok": True, **gestao.excluir_bloco(_canal(slug), video, nn)}
    except ValueError as e:
        raise HTTPException(409, str(e))
