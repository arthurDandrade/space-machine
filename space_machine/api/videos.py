"""Um vídeo: a página dele, produzir (fila ou vídeo inteiro), publicação, thumbnail, vídeo final, arquivar,
excluir e a lixeira do canal.
"""
import subprocess
from pathlib import Path

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import capas, estado, fila, final, gestao
from .. import roteiro as roteiro_mod
from .. import video as video_mod
from .. import thumb as thumb_mod
from .. import fichas, prontos
from ..sistema import config, ler_json
from .comum import _arquivo, _bloco_dir, _canal, _cauda, _curto, _video, _video_dir

api = APIRouter(prefix="/api")


def _producao_dir(slug, video):
    """A pasta de produção do vídeo, para o que mexe na produção (produzir, fila, juntar, fazer thumbnail):
    vídeo arquivado só tem a ficha."""
    vd = _video_dir(slug, video)
    if not vd.is_dir():
        raise HTTPException(409, "este vídeo está arquivado: a produção dele não existe mais")
    return vd


def _thumb_sistema(c, vd):
    """Thumbnail feita pelo sistema: os modelos do formato do canal (com a imagem de exemplo de cada um) e como está
    a última que você pediu. None se o formato não tem modelos."""
    try:
        ms = thumb_mod.modelos(c) if vd.is_dir() else None       # arquivado: não há produção de onde tirar as imagens
        if not ms:
            return None
        slug = Path(c["raiz"]).name
        for m in ms:
            m["previa"] = f"/api/c/{slug}/thumb/modelo/{m['id']}/previa?v={thumb_mod.previa(c, m['id']).stem[-10:]}"
    except (ValueError, OSError):
        return None
    est = thumb_mod.ler_estado(vd)
    return {"modelos": ms, "fundos": thumb_mod.fundos(c),
            "estado": {k: est.get(k) or "" for k in ("status", "etapa", "modelo", "modelo_nome", "erro", "aviso",
                                                     "atualizado", "fundo")} | {"rodando": est["rodando"]}}


@api.get("/c/{slug}/v/{video}")
def detalhe_video(slug: str, video: str):
    vd = _video_dir(slug, video)
    v = estado.video(slug, video)
    resumo = _video(slug, v)
    blocos = [{**info, "atual": b["atual"], "feito": b["feito"], "assets_total": b["assets_total"],
               "assets_prontos": b["assets_prontos"], "conferir": len(b["conferir_pendentes"]), "parado": b["parado"],
               "aprovado": b["aprovado"], "previas": len(b["previas"]), "mudou": b["mudou"],
               "tem_capa": bool(capas.fontes(vd, b["nn"]))}
              for b, info in zip(v["blocos"], resumo["blocos"])]
    fim = final.ler_estado(vd)
    aep, mp4 = vd / "final" / "final.aep", Path(fim.get("mp4") or vd / "final" / "-")
    if not mp4.is_file():      # o da pasta de prontos do canal; senão, um renderizado antes (ou à mão) em final/
        mp4 = prontos.atual(vd) or max((vd / "final").glob("*.mp4"), key=lambda f: f.stat().st_mtime, default=mp4)
    fim.update(tem_aep=aep.exists(), mp4_url=_arquivo(mp4) if mp4.is_file() else None,
               mp4_tamanho=mp4.stat().st_size if mp4.is_file() else 0, entregues=len(final.entregues(vd)))
    thumb = capas.info_thumbnail(vd)
    if thumb:
        thumb["url"] = _arquivo(thumb.pop("arquivo")) + f"&v={thumb['versao']}"
    prod = v.get("producao")
    if prod:
        p = vd / "producao"
        man = {a["id"]: a for a in (ler_json(p / "manifesto.json", {}) or {}).get("assets", []) if a.get("id")}
        conferir = []
        for aid, texto in prod["conferir_pendentes"].items():
            a = man.get(aid, {})
            conferir.append({"id": aid, "texto": texto, "tipo": a.get("tipo", ""), "descricao": a.get("descricao", ""),
                             "arquivo": _arquivo(p / a["arquivo"]) if a.get("arquivo") and (p / a["arquivo"]).exists() else None})
        logs = sorted((p / "_estudio").glob("log_*.txt"), key=lambda f: f.stat().st_mtime, reverse=True) \
            if (p / "_estudio").is_dir() else []
        etapa_log = next((f for f in logs if f.name != "log_rodar.txt"), None)
        mp4p = Path(prod["mp4"]) if prod["mp4"] else None
        prod = {**{k: prod[k] for k in ("rodando", "parado", "etapa_atual", "feito", "atual", "assets_total",
                                         "assets_prontos", "conferidos", "travar_conferir", "storyboard")},
                "etapas": [{**e, "detalhe": _curto(vd, e["detalhe"])} for e in prod["etapas"]],
                "capitulos": [{**{k: c[k] for k in ("nn", "topico", "narrado", "transcrito")},
                               "qa": c["qa"]["md"], "aprovado": c["qa"]["aprovado"],
                               "folha": _arquivo(c["qa"]["folha"]) if c["qa"]["folha"] else None}
                              for c in prod["capitulos"]],
                "conferir": conferir,
                "mp4": _arquivo(mp4p) + f"&v={int(mp4p.stat().st_mtime)}" if mp4p else None,
                "mp4_tamanho": mp4p.stat().st_size if mp4p else 0,
                "log_rodar": _cauda(p / "_estudio" / "log_rodar.txt", 60),
                "log_etapa": {"nome": etapa_log.name, "texto": _cauda(etapa_log, 40)} if etapa_log else None}
    rot = v.get("roteiro") or {}
    return {**resumo, "producao": prod, "blocos": blocos,
            "roteiro_estado": {k: rot.get(k) or "" for k in ("status", "etapa", "inicio", "erro", "obs")}
                              | {"rodando": bool(rot.get("rodando"))} if rot else None, "fila": v.get("fila") or None, "final": fim, "thumbnail": thumb,
            "thumb_sistema": _thumb_sistema(_canal(slug), vd),
            "publicacao": gestao.dados_video(slug, video),
            "consumo_detalhe": v.get("consumo") or {}, "etapas": [{"id": e, "rotulo": r} for e, r in estado.ETAPAS],
            "tem_roteiro": fichas.roteiro(vd).exists()}


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
    vd = _producao_dir(slug, video)
    if not fila.ler_fila(vd).get("ativa"):
        fila.lancar_fila(vd, max(1, min(maximo, 5)))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/fila/parar")
def parar_fila(slug: str, video: str):
    fila.parar_fila(_producao_dir(slug, video))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/produzir")
def produzir_video(slug: str, video: str, de: str = Body("", embed=True), ate: str = Body("", embed=True),
                   obs: str = Body("", embed=True)):
    """Fluxo "video": roda o vídeo inteiro (rodar_video.py) a partir de onde parou, ou de/até uma etapa."""
    vd = _producao_dir(slug, video)
    if not video_mod.fluxo_video(vd):
        raise HTTPException(409, "este vídeo é produzido bloco a bloco")
    if estado.producao_video(vd)["rodando"]:
        raise HTTPException(409, "o vídeo já está sendo produzido")
    fila.lancar_rodada(video_mod.pasta(vd), de, ate, obs)
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/produzir/parar")
def parar_video(slug: str, video: str):
    fila.parar_rodada(video_mod.pasta(_producao_dir(slug, video)))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/produzir/conferir")
def conferir_video(slug: str, video: str):
    """Quem produz viu o vídeo e aprovou os itens de "conferir" (fluxo "video")."""
    estado.aprovar_conferir(video_mod.pasta(_producao_dir(slug, video)))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/publicacao")
def salvar_publicacao(slug: str, video: str, dados: dict = Body(...)):
    _video_dir(slug, video)
    campos = {k: str(dados.get(k) or "") for k in ("status", "titulo_pub", "descricao", "tags", "data_pub", "notas", "link")}
    if campos["status"] not in ("", *gestao.MANUAIS):
        raise HTTPException(400, "status inválido")
    gestao.salvar_video(slug, video, **campos)
    return {"ok": True, "publicacao": gestao.dados_video(slug, video)}


@api.post("/c/{slug}/v/{video}/descricao/gerar")
def gerar_descricao(slug: str, video: str):
    """Resumo + capítulos do vídeo final + convite para seguir o canal (nada é salvo: vai para o campo)."""
    from ..motor_claude import ErroClaude
    _video_dir(slug, video)
    try:
        return gestao.gerar_descricao(_canal(slug), slug, video)
    except ErroClaude as e:
        raise HTTPException(502, f"O Claude não respondeu: {str(e)[:300]}")


@api.post("/c/{slug}/v/{video}/coluna")
def mover_video(slug: str, video: str, coluna: str = Body(..., embed=True)):
    """Quadro: soltar o vídeo em Edição final / Agendado / Publicado marca o status; em Roteiro ou Em produção,
    volta ao automático (pelos blocos)."""
    _video_dir(slug, video)
    if coluna not in ("roteiro", "producao", *gestao.MANUAIS):
        raise HTTPException(400, "coluna inválida")
    gestao.salvar_video(slug, video, status=coluna if coluna in gestao.MANUAIS else "")
    return {"ok": True}


@api.post("/c/{slug}/novo")
def novo_video(slug: str, titulo: str = Body(..., embed=True), roteiro: str = Body("", embed=True),
               ideia: int = Body(0, embed=True), instrucoes: str = Body("", embed=True)):
    """ideia: o id da ideia do "Virar vídeo" (sai da lista de ideias quando o vídeo é criado). Sem roteiro, num
    formato com agente de roteiro, o Claude escreve o roteiro a partir do título e das `instrucoes` que você mandou
    junto (pode levar alguns minutos)."""
    from ..motor_claude import ErroClaude
    try:
        if roteiro.strip():
            video = gestao.criar_video(_canal(slug), titulo, roteiro)
        else:
            # sem roteiro: o vídeo nasce já, e o Claude escreve em segundo plano com o painel mostrando (roteiro.py)
            video = roteiro_mod.comecar(_canal(slug), titulo, instrucoes.strip()[:4000])
    except ValueError as e:
        raise HTTPException(400, str(e))
    except ErroClaude as e:
        raise HTTPException(502, f"O Claude não escreveu o roteiro: {e}")
    gestao.ideia_virou_video(slug, ideia, video)
    return {"ok": True, "video": video}


@api.post("/c/{slug}/v/{video}/roteiro/parar")
def parar_roteiro(slug: str, video: str):
    roteiro_mod.parar(_producao_dir(slug, video))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/roteiro/escrever")
def escrever_roteiro_de_novo(slug: str, video: str, instrucoes: str = Body(None, embed=True)):
    """Tenta de novo o roteiro de um vídeo que ficou sem capítulos (o Claude falhou ou você parou). Sem
    `instrucoes`, repete as da última vez."""
    vd = _producao_dir(slug, video)
    est = roteiro_mod.ler_estado(vd)
    if est.get("rodando"):
        raise HTTPException(409, "o roteiro deste vídeo já está sendo escrito")
    if estado.blocos_do_video(vd):
        raise HTTPException(409, "este vídeo já tem roteiro e capítulos")
    roteiro_mod.lancar(vd, None if instrucoes is None else instrucoes.strip()[:4000])
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/thumbnail")
async def enviar_thumbnail(slug: str, video: str, arquivo: UploadFile = File(...)):
    """A thumbnail do vídeo (a que vai para o YouTube): vira a capa do vídeo no painel. A anterior vai para o Lixo do Mac."""
    vd = _video_dir(slug, video)
    dados = await arquivo.read()
    if len(dados) > 30 * 1024 * 1024:
        raise HTTPException(400, "Imagem grande demais (máx. 30 MB).")
    try:
        capas.salvar_thumbnail(vd, dados, arquivo.filename or "thumbnail.png")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "thumbnail": capas.info_thumbnail(vd) and {k: v for k, v in capas.info_thumbnail(vd).items() if k != "arquivo"}}


@api.get("/c/{slug}/thumb/modelo/{modelo}/previa")
def previa_modelo_thumbnail(slug: str, modelo: str):
    """A imagem de exemplo de um modelo de thumbnail (os lugares das imagens em cinza)."""
    try:
        return FileResponse(thumb_mod.previa(_canal(slug), modelo), headers={"Cache-Control": "max-age=86400"})
    except ValueError as e:
        raise HTTPException(404, str(e))


@api.post("/c/{slug}/v/{video}/thumbnail/fazer")
def fazer_thumbnail(slug: str, video: str, modelo: str = Body(..., embed=True), refazer: bool = Body(False, embed=True),
                    obs: str = Body("", embed=True), fundo: str = Body("", embed=True)):
    """O sistema monta a thumbnail do vídeo no modelo escolhido (space_machine/thumb.py). Roda solto do painel."""
    vd = _producao_dir(slug, video)
    c = _canal(slug)
    if modelo not in {m["id"] for m in thumb_mod.modelos(c)}:
        raise HTTPException(404, "o formato deste canal não tem esse modelo de thumbnail")
    if thumb_mod.ler_estado(vd)["rodando"]:
        raise HTTPException(409, "a thumbnail já está sendo feita")
    if fundo and not thumb_mod.cor_valida(fundo):
        raise HTTPException(400, "a cor do fundo precisa ser no formato #RRGGBB")
    thumb_mod.lancar(vd, modelo, refazer, obs.strip()[:500], thumb_mod.cor_valida(fundo))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/thumbnail/remover")
def remover_thumbnail(slug: str, video: str):
    capas.remover_thumbnail(_video_dir(slug, video))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/final")
def juntar_no_after(slug: str, video: str, render: bool = Body(False, embed=True)):
    """Junta os blocos entregues num projeto do After (final/final.aep) e, se pedir, renderiza o MP4."""
    vd = _producao_dir(slug, video)
    if final.ler_estado(vd)["rodando"]:
        raise HTTPException(409, "o vídeo final já está sendo montado")
    if not final.entregues(vd):
        raise HTTPException(409, "nenhum bloco entregue ainda")
    final.lancar(vd, render)
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/final/abrir")
def abrir_final(slug: str, video: str):
    """Abre o final.aep no After (o painel roda no próprio Mac)."""
    aep = _video_dir(slug, video) / "final" / "final.aep"
    if not aep.exists():
        raise HTTPException(404, "o projeto final ainda não foi montado")
    subprocess.run(["open", "-a", config().get("after_app", "Adobe After Effects 2026"), str(aep)], check=False)
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/excluir")
def excluir_video(slug: str, video: str):
    try:
        return {"ok": True, "lixeira": gestao.excluir_video(_canal(slug), video)}
    except ValueError as e:
        raise HTTPException(409, str(e))


@api.post("/c/{slug}/v/{video}/arquivar")
def arquivar_video(slug: str, video: str, com_mp4: bool = Body(False, embed=True)):
    """A produção vai para o Lixo do Mac e a ficha do vídeo fica (gestao.arquivar_video)."""
    try:
        return {"ok": True, **gestao.arquivar_video(_canal(slug), video, com_mp4)}
    except ValueError as e:
        raise HTTPException(409, str(e))


@api.post("/c/{slug}/prontos/abrir")
def abrir_prontos(slug: str):
    """Mostra no Finder a pasta dos vídeos prontos do canal (<canal>/videos)."""
    pasta = Path(_canal(slug)["raiz"]) / prontos.PASTA
    pasta.mkdir(exist_ok=True)
    subprocess.run(["open", str(pasta)], check=False)
    return {"ok": True}


@api.get("/c/{slug}/lixeira")
def lixeira(slug: str):
    return {"itens": gestao.lixeira(_canal(slug))}


@api.post("/c/{slug}/lixeira/{nome}/restaurar")
def restaurar_video(slug: str, nome: str):
    try:
        return {"ok": True, "video": gestao.restaurar_video(_canal(slug), nome)}
    except ValueError as e:
        raise HTTPException(409, str(e))


@api.post("/c/{slug}/v/{video}/abrir")
def abrir_pasta(slug: str, video: str, nn: str = Body("", embed=True), sub: str = Body("", embed=True)):
    """Mostra a pasta do vídeo (do bloco, ou a final/ ou reels/) no Finder: o painel roda no próprio Mac."""
    pasta = _bloco_dir(slug, video, nn) if nn else _video_dir(slug, video)
    pronto = prontos.atual(pasta) if sub == "final" and not nn else None
    if not nn and not pasta.is_dir():       # arquivado: o que existe do vídeo é a ficha
        pasta = fichas.pasta(pasta)
    if pronto:      # o vídeo pronto mora na pasta do canal: mostra o arquivo lá
        subprocess.run(["open", "-R", str(pronto)], check=False)
        return {"ok": True}
    if sub in ("final", "reels") and (pasta / sub).is_dir():
        pasta = pasta / sub
    subprocess.run(["open", str(pasta)], check=False)
    return {"ok": True}
