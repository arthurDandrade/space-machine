"""Ajustes de um canal: nome, formato, identidade, regras do tema, aprendizados, chaves, narração e modelos
do Claude.
"""
import time
from pathlib import Path

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import capas, configuracao
from .. import formato_canal
from ..sistema import FORMATO_PADRAO, ficha_formato, formatos, ler_json
from .comum import IMAGENS, _cache_falta, _canal, _identidade, marca

api = APIRouter(prefix="/api")


# ---------------- imagens ----------------
@api.get("/c/{slug}/marca/{qual}")
def imagem_marca(slug: str, qual: str):
    if qual not in ("banner", "logo", "fundo"):
        raise HTTPException(404)
    c = _canal(slug)
    f = configuracao.fundo_do_canal(slug) if qual == "fundo" else marca(c, qual)
    if not f:
        raise HTTPException(404, f"o canal não tem {qual}")
    if qual == "banner":
        f = capas.banner(slug, f)
    return FileResponse(f, headers={"Cache-Control": "no-cache"})


# ---------------- configurações do canal ----------------
@api.get("/c/{slug}/config")
def config_canal(slug: str):
    c = _canal(slug)
    cj = ler_json(Path(c["raiz"]) / "canal.json", {}) or {}
    ident = cj.get("identidade", {}) or {}
    return {"slug": slug, "nome": c["nome"], "ativo": bool(c.get("ativo")), "tema": c.get("tema", ""),
            "idioma": c.get("idioma", "en"), "formato": c.get("formato") or FORMATO_PADRAO,
            "formatos": [{"slug": s, **f} for s, f in formatos().items()],
            "cores": _identidade(c), "fonte": ident.get("fonte_marca_arquivo", ""),
            "fontes": [{"arquivo": f, "nome": Path(f).stem} for f in configuracao.fontes()],
            "banner": bool(marca(c, "banner")), "logo": bool(marca(c, "logo")),
            "usa_fundo": bool((ficha_formato(c.get("formato")).get("identidade") or {}).get("fundo_imagem")),
            "fundo": bool(configuracao.fundo_do_canal(slug)),
            "regras": configuracao.regras_em_texto(cj.get("regras", {}) or {})}


@api.post("/c/{slug}/config")
def salvar_config_canal(slug: str, nome: str = Body(..., embed=True), ativo: bool = Body(True, embed=True)):
    c = _canal(slug)
    configuracao.salvar_canal(slug, nome=nome.strip() or c["nome"], ativo=bool(ativo))
    return {"ok": True}


# o formato não se troca gravando o campo: a troca confere o canal e arruma o que dá (formato_canal.py)
@api.get("/c/{slug}/formato/conferir")
def conferir_troca_de_formato(slug: str, para: str):
    _canal(slug)
    try:
        return formato_canal.conferir(slug, para)
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.post("/c/{slug}/formato")
def trocar_formato(slug: str, formato: str = Body(..., embed=True), manter_prompt: bool = Body(False, embed=True)):
    _canal(slug)
    try:
        return {"ok": True, **formato_canal.trocar(slug, formato, manter_prompt)}
    except ValueError as e:
        raise HTTPException(409, str(e))


@api.post("/c/{slug}/identidade")
def salvar_identidade(slug: str, cores: dict = Body(..., embed=True), fonte: str = Body("", embed=True)):
    _canal(slug)
    configuracao.salvar_identidade(slug, cores, fonte)
    return {"ok": True}


@api.post("/c/{slug}/marca/{qual}")
async def enviar_marca(slug: str, qual: str, arquivo: UploadFile = File(...)):
    """Troca o logo, o banner ou a imagem de fundo dos vídeos do canal. O anterior vai para identidade/anteriores/
    (nada se perde)."""
    c = _canal(slug)
    ext = Path(arquivo.filename or "").suffix.lower()
    if qual not in ("banner", "logo", "fundo") or ext not in IMAGENS:
        raise HTTPException(400, "Envie uma imagem PNG, JPG ou WEBP.")
    dados = await arquivo.read()
    if len(dados) > 20 * 1024 * 1024:
        raise HTTPException(400, "Imagem grande demais (máx. 20 MB).")
    from io import BytesIO
    from PIL import Image
    try:
        Image.open(BytesIO(dados)).verify()
    except Exception:  # noqa: BLE001 — qualquer falha de leitura = não é imagem
        raise HTTPException(400, "Esse arquivo não é uma imagem que dê para abrir.")
    if qual == "fundo":
        configuracao.trocar_fundo(slug, Image.open(BytesIO(dados)))
        return {"ok": True}
    pasta = Path(c["raiz"]) / "identidade"
    pasta.mkdir(exist_ok=True)
    antigos = [f for f in pasta.glob(f"{qual}.*") if f.suffix.lower() in IMAGENS]
    if antigos:
        guarda = pasta / "anteriores"
        guarda.mkdir(exist_ok=True)
        for f in antigos:
            f.rename(guarda / f"{qual}_{time.strftime('%Y%m%d-%H%M%S')}{f.suffix}")
    (pasta / f"{qual}{ext}").write_bytes(dados)
    return {"ok": True}


@api.delete("/c/{slug}/marca/fundo")
def tirar_fundo(slug: str):
    """Os vídeos do canal ficam sem imagem de fundo (só a cor e a textura). A imagem vai para identidade/anteriores/."""
    _canal(slug)
    configuracao.tirar_fundo(slug)
    return {"ok": True}


@api.post("/c/{slug}/regras")
def salvar_regras(slug: str, regras: dict = Body(..., embed=True)):
    _canal(slug)
    campos = {k: str(regras.get(k) or "") for k in
              ("escolha", "storyboard", "genericas", "genericas_hist", "proibidos", "permitido_se", "trocas")}
    try:
        configuracao.salvar_regras(slug, **campos)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@api.post("/c/{slug}/regras/sugerir")
def sugerir_regras(slug: str):
    from ..motor_claude import ErroClaude
    try:
        return {"regras": configuracao.sugerir_regras(_canal(slug), slug)}
    except ErroClaude as e:
        raise HTTPException(502, f"O Claude não respondeu: {str(e)[:300]}")


@api.get("/c/{slug}/aprendizados")
def aprendizados(slug: str):
    pasta = Path(_canal(slug)["conhecimento"])
    log = next(iter(sorted(pasta.glob("**/Log de Aprendizados.md"))), None) if pasta.is_dir() else None
    return {"texto": log.read_text() if log else "", "mudou": log.stat().st_mtime if log else None}


def _apis_publicas(c):
    """Estado das chaves sem nenhum segredo: de campo secreto vai só a máscara (os 4 últimos caracteres)."""
    out = []
    for a in configuracao.estado_apis(c):
        campos = [{"chave": f["chave"], "rotulo": f["rotulo"], "secreta": f["secreta"], "dica": f["dica"],
                   "tem_valor": bool(f["valor"]), "mostrar": f["mostrar"], "valor": "" if f["secreta"] else f["valor"]}
                  for f in a["campos"]]
        out.append({k: a[k] for k in ("id", "nome", "escopo", "ajuda", "configurada")} | {"campos": campos})
    return out


def _narracao(c):
    """Quem narra este canal e as opções (o cartão de chaves de cada um vem na mesma lista de APIs)."""
    return {"provedor": configuracao.provedor_narracao(c), "provedores": configuracao.PROVEDORES_NARRACAO}


@api.get("/c/{slug}/chaves")
def chaves(slug: str):
    c = _canal(slug)
    return {"apis": _apis_publicas(c), "narracao": _narracao(c)}


@api.post("/c/{slug}/narracao")
def salvar_narracao(slug: str, provedor: str = Body(..., embed=True)):
    """Troca o serviço de TTS do canal (vale para os próximos blocos; narração já gerada fica como está)."""
    _canal(slug)
    try:
        configuracao.salvar_provedor_narracao(slug, provedor)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _cache_falta["quando"] = 0
    return {"ok": True, "narracao": _narracao(_canal(slug))}


@api.get("/c/{slug}/chaves-importar")
def chaves_de_outros(slug: str):
    _canal(slug)
    return {"canais": configuracao.chaves_de_outros(slug)}


@api.post("/c/{slug}/chaves-importar")
def importar_chaves(slug: str, origem: str = Body(..., embed=True), apis: list = Body([], embed=True)):
    c = _canal(slug)
    try:
        copiados = configuracao.importar_chaves(c, origem, set(apis))
    except ValueError as e:
        raise HTTPException(404, str(e))
    _cache_falta["quando"] = 0
    return {"ok": True, "copiados": copiados, "apis": _apis_publicas(c), "narracao": _narracao(c)}


@api.post("/c/{slug}/chaves/{api_id}")
def salvar_chave(slug: str, api_id: str, valores: dict = Body({}, embed=True), apagar: list = Body([], embed=True)):
    c = _canal(slug)
    if api_id not in {a["id"] for a in configuracao.APIS}:
        raise HTTPException(404)
    form = {k: str(v) for k, v in valores.items()} | {f"apagar_{k}": "1" for k in apagar}
    mudou = configuracao.salvar_api(c, api_id, form)
    _cache_falta["quando"] = 0
    return {"ok": True, "mudou": mudou, "apis": _apis_publicas(c), "narracao": _narracao(c)}


@api.get("/c/{slug}/modelos")
def modelos(slug: str):
    """Modelo e esforço do Claude em cada etapa DESTE canal (canal.json › modelos/esforco)."""
    return configuracao.estado_modelos(slug, _canal(slug))


@api.post("/c/{slug}/modelos")
def salvar_modelos(slug: str, modelos: dict = Body({}, embed=True), esforco: dict = Body({}, embed=True)):
    _canal(slug)
    configuracao.salvar_modelos(slug, modelos, esforco)
    return {"ok": True}


@api.post("/c/{slug}/chaves/{api_id}/testar")
def testar_chave(slug: str, api_id: str):
    if api_id not in {a["id"] for a in configuracao.APIS}:
        raise HTTPException(404)
    ok, msg = configuracao.testar_api(_canal(slug), api_id)
    return {"ok": ok, "mensagem": msg}
