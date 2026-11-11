"""Pesquisa de canais: a Modelagem (canais que você quer modelar) e a Mineração (vídeos que estouraram).
"""
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from .. import mineracao, modelar

api = APIRouter(prefix="/api")


# ---------------- canais a modelar ----------------
@api.get("/modelar")
def canais_a_modelar():
    return {"itens": modelar.lista(), "tem_chave": bool(modelar.chave())}


@api.post("/modelar")
def adicionar_a_modelar(link: str = Body(..., embed=True)):
    try:
        return {"ok": True, "item": modelar.adicionar(link)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.post("/modelar/{ref_id}/atualizar")
def atualizar_a_modelar(ref_id: int):
    try:
        return {"ok": True, "item": modelar.atualizar(ref_id)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.post("/modelar/{ref_id}/notas")
def notas_a_modelar(ref_id: int, notas: str = Body("", embed=True)):
    try:
        modelar.salvar_notas(ref_id, notas)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


@api.post("/modelar/{ref_id}/excluir")
def excluir_a_modelar(ref_id: int):
    try:
        modelar.remover(ref_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


@api.get("/modelar/{ref_id}/logo")
def logo_a_modelar(ref_id: int):
    try:
        f = modelar.arquivo_logo(ref_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not f:
        raise HTTPException(404, "esse canal não tem logo guardado")
    return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


# ---------------- mineração: vídeos que estouraram num nicho ----------------
@api.get("/mineracao")
def mineracao_estado(situacao: str = "novo", nicho: str = "", ordem: str = "nota"):
    """A tela inteira num pedido. Aproveita para disparar o garimpo do dia, se estiver ligado e já for a hora."""
    mineracao.garimpar_atras_das_cortinas()
    return mineracao.estado(situacao, nicho, ordem)


@api.post("/mineracao/garimpar")
def mineracao_garimpar(nicho: str = Body("", embed=True), filtros: dict = Body(None, embed=True)):
    """Garimpa um nicho (sem nicho, o que está há mais tempo sem ir)."""
    try:
        return {"ok": True, "resumo": mineracao.garimpar(nicho or None, filtros)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.post("/mineracao/filtros")
def mineracao_filtros(filtros: dict = Body({}, embed=True), automatico: bool = Body(None, embed=True)):
    if automatico is not None:
        mineracao.salvar_automatico(automatico)
    return {"ok": True, "filtros": mineracao.salvar_filtros(filtros), "automatico": mineracao.automatico()}


@api.get("/mineracao/nichos")
def mineracao_nichos():
    return {"nichos": mineracao.nichos()}


@api.post("/mineracao/nichos")
def mineracao_novo_nicho(nome: str = Body(..., embed=True)):
    """Guarda o nicho; os termos de busca saem do Claude na hora, uma vez só."""
    try:
        return {"ok": True, "nicho": mineracao.salvar_nicho(nome)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@api.post("/mineracao/nichos/refazer")
def mineracao_refazer_termos(nome: str = Body(..., embed=True)):
    try:
        return {"ok": True, "nicho": mineracao.refazer_termos(nome)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@api.post("/mineracao/nichos/excluir")
def mineracao_excluir_nicho(nome: str = Body(..., embed=True)):
    mineracao.remover_nicho(nome)
    return {"ok": True}


@api.post("/mineracao/{ref_id}/{acao}")
def mineracao_acao(ref_id: int, acao: str, notas: str = Body("", embed=True)):
    """descartar (o canal inteiro) · voltar · modelar (vai para a Modelagem) · notas · excluir."""
    try:
        if acao == "descartar":
            mineracao.descartar(ref_id)
        elif acao == "voltar":
            mineracao.voltar(ref_id)
        elif acao == "modelar":
            return {"ok": True, "item": mineracao.promover(ref_id)}
        elif acao == "notas":
            mineracao.salvar_notas(ref_id, notas)
        elif acao == "excluir":
            mineracao.remover(ref_id)
        else:
            raise HTTPException(404, "essa ação não existe")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@api.get("/mineracao/{ref_id}/thumb")
def mineracao_thumb(ref_id: int):
    return _imagem_minerada(mineracao.arquivo_thumb, ref_id)


@api.get("/mineracao/{ref_id}/logo")
def mineracao_logo(ref_id: int):
    return _imagem_minerada(mineracao.arquivo_logo, ref_id)


def _imagem_minerada(de_onde, ref_id):
    try:
        f = de_onde(ref_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not f:
        raise HTTPException(404, "essa imagem não foi guardada")
    return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
