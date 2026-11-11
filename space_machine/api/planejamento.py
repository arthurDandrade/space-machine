"""Planejar o canal: ideias, calendário, os prompts do canal e o prompt de roteiro.
"""
import datetime as dt
import subprocess

from fastapi import APIRouter, Body, File, HTTPException, UploadFile

from .. import capas, gestao, meus_prompts
from .. import formato_canal
from .comum import _canal, _versao_capa

api = APIRouter(prefix="/api")


@api.get("/c/{slug}/ideias")
def lista_ideias(slug: str):
    _canal(slug)
    return {"ideias": gestao.ideias(slug)}


@api.get("/c/{slug}/prompts")
def lista_prompts(slug: str):
    _canal(slug)
    return {"prompts": meus_prompts.listar(slug)}


@api.get("/c/{slug}/prompts/{nome}")
def ler_prompt(slug: str, nome: str):
    _canal(slug)
    try:
        return meus_prompts.ler(slug, nome)
    except ValueError as e:
        raise HTTPException(404, str(e))


@api.post("/c/{slug}/prompts")
def salvar_prompt(slug: str, titulo: str = Body(..., embed=True), texto: str = Body("", embed=True),
                  nome_antigo: str = Body("", embed=True)):
    _canal(slug)
    try:
        return {"ok": True, "nome": meus_prompts.salvar(slug, titulo, texto, nome_antigo)}
    except ValueError as e:
        raise HTTPException(409, str(e))


@api.post("/c/{slug}/prompts-importar")
async def importar_prompts(slug: str, arquivos: list[UploadFile] = File(...)):
    _canal(slug)
    feitos, erros = [], []
    for up in arquivos:
        try:
            feitos.append(meus_prompts.importar(slug, up.filename, await up.read()))
        except ValueError as e:
            erros.append(str(e))
    return {"ok": not erros, "importados": feitos, "erros": erros}


@api.post("/c/{slug}/prompts/{nome}/apagar")
def apagar_prompt(slug: str, nome: str):
    _canal(slug)
    try:
        meus_prompts.apagar(slug, nome)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


@api.post("/c/{slug}/prompts-pasta")
def abrir_pasta_prompts(slug: str):
    _canal(slug)
    subprocess.run(["open", str(meus_prompts.pasta(slug))], check=False)
    return {"ok": True}


@api.get("/c/{slug}/calendario")
def calendario(slug: str, mes: str = ""):
    _canal(slug)
    hoje = dt.date.today()
    try:
        ano, m = (int(x) for x in mes.split("-")) if mes else (hoje.year, hoje.month)
        dt.date(ano, m, 1)
    except ValueError:
        ano, m = hoje.year, hoje.month
    semanas, sem_data = gestao.calendario(slug, ano, m)
    card = lambda v, g, col: {"slug": v["slug"], "titulo": g.get("titulo_pub") or v["titulo"], "coluna": col,
                              "tem_capa": bool(capas.fontes(v["pasta"])), "capa_v": _versao_capa(v["pasta"])}
    return {
        "mes": f"{ano}-{m:02d}", "ano": ano, "mes_n": m,
        "ant": (dt.date(ano, m, 1) - dt.timedelta(days=1)).strftime("%Y-%m"),
        "prox": (dt.date(ano, m, 28) + dt.timedelta(days=4)).strftime("%Y-%m"),
        "semanas": [[{"data": d["data"].isoformat(), "dia": d["data"].day, "no_mes": d["no_mes"], "hoje": d["hoje"],
                      "videos": [card(x["v"], x["g"], x["coluna"]) for x in d["videos"]]} for d in semana]
                    for semana in semanas],
        "sem_data": [card(v, gestao.dados_video(slug, v["slug"]),
                          gestao.coluna_do_video(v, gestao.dados_video(slug, v["slug"]))) for v in sem_data],
    }


@api.post("/c/{slug}/ideias")
def nova_ideia(slug: str, titulo: str = Body(..., embed=True), notas: str = Body("", embed=True)):
    _canal(slug)
    if not titulo.strip():
        raise HTTPException(400, "Dê um título à ideia.")
    gestao.nova_ideia(slug, titulo, notas)
    return {"ok": True}


@api.post("/c/{slug}/ideias/{ideia_id}/apagar")
def apagar_ideia(slug: str, ideia_id: int):
    _canal(slug)
    gestao.apagar_ideia(slug, ideia_id)
    return {"ok": True}


@api.get("/c/{slug}/roteiro-prompt")
def ver_prompt_roteiro(slug: str):
    _canal(slug)
    return formato_canal.prompt_roteiro(slug)


@api.post("/c/{slug}/roteiro-prompt")
def salvar_prompt_roteiro(slug: str, texto: str = Body("", embed=True)):
    _canal(slug)
    try:
        return formato_canal.salvar_prompt_roteiro(slug, texto)
    except ValueError as e:
        raise HTTPException(409, str(e))


@api.post("/c/{slug}/roteiro-prompt/padrao")
def prompt_roteiro_do_formato(slug: str):
    _canal(slug)
    formato_canal.voltar_ao_do_formato(slug)
    return formato_canal.prompt_roteiro(slug)
