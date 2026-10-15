"""Painel do Space Machine no navegador (localhost).

Iniciar:  ./spacemachine   (ou .venv/bin/python -m space_machine painel)   → http://localhost:8765

Tudo o que o painel mostra vem das pastas (estado.py) e do registro de consumo (<dados>/space_machine.sqlite).
Os botões só disparam os mesmos comandos da linha de comando (python -m space_machine rodar ...), em segundo plano.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import datetime as dt
from urllib.parse import quote
import shutil
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import configuracao, estado, fila, gestao, primeiros_passos, textos
from .canal import gravar_json, ler_json
from .motor_claude import _banco, canais
from .sistema import DADOS, config, salvar_config
from .rodar import ETAPAS as ETAPAS_RODAR
from .api import api

app = FastAPI(title="Space Machine")
tpl = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
tpl.env.globals.update(t=lambda chave: textos.t(chave, config().get("idioma_painel", "pt")),
                       dados=str(DADOS), ETAPAS=estado.ETAPAS, ETAPAS_RODAR=ETAPAS_RODAR, quando=estado.quando,
                       COLUNAS=gestao.COLUNAS, canais_menu=lambda: [(k, c["nome"]) for k, c in canais().items()
                                                                     if c.get("ativo")])
tpl.env.filters["milhar"] = lambda n: f"{int(n or 0):,}".replace(",", ".")


def _video_dir(canal, video):
    c = canais().get(canal)
    if not c:
        raise HTTPException(404, "canal não existe")
    vd = (Path(c["producoes"]) / video).resolve()
    if not str(vd).startswith(str(Path(c["producoes"]).resolve()) + "/") or not vd.is_dir():
        raise HTTPException(404, "vídeo não existe")
    return c, vd


def _bloco_dir(canal, video, nn):
    c, vd = _video_dir(canal, video)
    b = vd / "blocos" / nn
    if not re.fullmatch(r"\d{2,3}", nn) or not b.is_dir():
        raise HTTPException(404, "bloco não existe")
    return c, vd, b


def _cauda(arq, linhas=60):
    try:
        txt = Path(arq).read_text(errors="replace").splitlines()
    except FileNotFoundError:
        return ""
    return "\n".join(txt[-linhas:])


# ---------------- páginas ----------------
@app.get("/", include_in_schema=False)
def raiz():
    """O painel abre no React (escolha de canais); as páginas antigas seguem nos endereços delas até migrarem."""
    return RedirectResponse("/app/", status_code=307)


@app.get("/antigo", response_class=HTMLResponse)
def inicio(request: Request):
    lista = []
    for c in estado.resumo_canais():
        vids = estado.videos(c["slug"]) if c.get("ativo") else []
        lista.append({**c, "videos": vids})
    return tpl.TemplateResponse(request, "inicio.html", {"canais": lista, "falta_algo": primeiros_passos.falta_algo()})


@app.get("/v/{canal}/{video}", response_class=HTMLResponse)
def pagina_video(request: Request, canal: str, video: str):
    _video_dir(canal, video)
    return tpl.TemplateResponse(request, "video.html", {"v": estado.video(canal, video), "canal": canal,
                                                        "g": gestao.dados_video(canal, video)})


@app.get("/v/{canal}/{video}/kanban", response_class=HTMLResponse)
def kanban(request: Request, canal: str, video: str, ver: str = ""):
    _video_dir(canal, video)
    v = estado.video(canal, video)
    html = tpl.env.get_template("_kanban.html").render({"v": v, "canal": canal, "request": request})
    novo = hashlib.md5(html.encode()).hexdigest()[:12]
    if ver == novo:
        # nada mudou: 204 não mexe na página; sem bloco rodando, 286 para de perguntar (recarregar a página volta)
        rodando = any(b.get("rodando") for b in v.get("blocos", [])) or (v.get("fila") or {}).get("ativa")
        return Response(status_code=204 if rodando else 286)
    return HTMLResponse(f'<script>window._kanbanVer = "{novo}";</script>' + html)


@app.get("/b/{canal}/{video}/{nn}", response_class=HTMLResponse)
def pagina_bloco(request: Request, canal: str, video: str, nn: str):
    _, vd, b = _bloco_dir(canal, video, nn)
    return tpl.TemplateResponse(request, "bloco.html", {
        "b": estado.bloco(b, vd), "canal": canal, "video": video, "titulo": estado.titulo_video(vd),
        "storyboard": Path(b / f"storyboard_{nn}.md").read_text() if (b / f"storyboard_{nn}.md").exists() else ""})


def _versao_painel(b, info):
    """Muda quando algo do bloco muda: sem isso o painel se redesenhava a cada 4 s e o player da prévia
    recomeçava e travava (2026-10-11)."""
    arqs = list((b / "_estudio").glob("*")) + [b / "escolhas.json", b / "manifesto.json"] \
        + list((b / "edicao").glob("qa_*.md")) + list((b / "edicao").glob("previa_*.mp4"))
    m = max([f.stat().st_mtime for f in arqs if f.exists()] + [0])
    return f"{m:.3f}-{info['rodando']}"


@app.get("/b/{canal}/{video}/{nn}/painel", response_class=HTMLResponse)
def painel_bloco(request: Request, canal: str, video: str, nn: str, ver: str = ""):
    _, vd, b = _bloco_dir(canal, video, nn)
    info = estado.bloco(b, vd)
    v = _versao_painel(b, info)
    if ver and ver == v:
        # htmx não troca nada com 204 (o player continua tocando); parado, 286 faz a página parar de perguntar.
        # Rodar/Parar/Aprovar recarregam a página, então o acompanhamento volta sozinho quando precisa.
        return Response(status_code=204 if info["rodando"] else 286)
    logs = sorted((b / "_estudio").glob("log_*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    return tpl.TemplateResponse(request, "_painel_bloco.html", {
        "b": info, "canal": canal, "video": video, "ver": v,
        "log_rodar": _cauda(b / "_estudio" / "log_rodar.txt", 40),
        "log_etapa": _cauda(logs[0], 30) if logs and logs[0].name != "log_rodar.txt" else "",
        "log_nome": logs[0].name if logs else ""})


@app.post("/b/{canal}/{video}/{nn}/rodar")
def rodar(canal: str, video: str, nn: str, de: str = Form(""), ate: str = Form(""), obs: str = Form("")):
    _, vd, b = _bloco_dir(canal, video, nn)
    if estado.bloco(b, vd)["rodando"]:
        raise HTTPException(409, "esse bloco já está rodando")
    fila.lancar_rodada(b, de, ate, obs)      # solta do painel (ver fila.lancar_rodada)
    return RedirectResponse(f"/b/{canal}/{video}/{nn}", status_code=303)


@app.post("/v/{canal}/{video}/fila")
def iniciar_fila(canal: str, video: str, maximo: int = Form(3)):
    """Produzir todos: põe os blocos não entregues em fila, no máximo `maximo` rodando ao mesmo tempo."""
    _, vd = _video_dir(canal, video)
    if not fila.ler_fila(vd).get("ativa"):
        fila.lancar_fila(vd, max(1, min(maximo, 5)))
    return RedirectResponse(f"/v/{canal}/{video}", status_code=303)


@app.post("/v/{canal}/{video}/fila/parar")
def parar_fila(canal: str, video: str):
    _, vd = _video_dir(canal, video)
    fila.parar_fila(vd)
    return RedirectResponse(f"/v/{canal}/{video}", status_code=303)


@app.post("/b/{canal}/{video}/{nn}/conferir_ok")
def conferir_ok(canal: str, video: str, nn: str):
    """Quem produz viu a prévia e aprovou os itens de "conferir": grava e entrega."""
    _, _, b = _bloco_dir(canal, video, nn)
    estado.aprovar_conferir(b)
    if not estado.bloco(b)["travar_conferir"]:          # sem trava: só some da lista ("Marcar como visto")
        return RedirectResponse(f"/b/{canal}/{video}/{nn}", status_code=303)
    return rodar(canal, video, nn, de="entregar", ate="entregar", obs="")


@app.post("/b/{canal}/{video}/{nn}/parar")
def parar(canal: str, video: str, nn: str):
    _, _, b = _bloco_dir(canal, video, nn)
    fila.parar_rodada(b)
    return RedirectResponse(f"/b/{canal}/{video}/{nn}", status_code=303)


@app.get("/arquivo")
def arquivo(p: str):
    """Serve prévias, folhas, revisão — só de dentro das pastas de produção dos canais."""
    alvo = Path(p).resolve()
    if not any(str(alvo).startswith(str(Path(c["producoes"]).resolve()) + "/") for c in canais().values()):
        raise HTTPException(403, "fora das pastas de produção")
    if not alvo.is_file():
        raise HTTPException(404)
    return FileResponse(alvo)


# ---------------- novo vídeo ----------------
@app.get("/novo/{canal}", response_class=HTMLResponse)
def novo_form(request: Request, canal: str, titulo: str = ""):
    if canal not in canais():
        raise HTTPException(404)
    return tpl.TemplateResponse(request, "novo.html", {"canal": canal, "nome": canais()[canal]["nome"], "erro": "",
                                                       "titulo": titulo})


@app.post("/novo/{canal}", response_class=HTMLResponse)
def novo(request: Request, canal: str, titulo: str = Form(...), roteiro: str = Form(...)):
    c = canais().get(canal)
    if not c:
        raise HTTPException(404)
    try:
        slug = gestao.criar_video(c, titulo, roteiro)
    except ValueError as e:
        return tpl.TemplateResponse(request, "novo.html", {"canal": canal, "nome": c["nome"], "erro": str(e),
                                                           "titulo": titulo, "roteiro": roteiro}, status_code=400)
    return RedirectResponse(f"/v/{canal}/{slug}", status_code=303)


# ---------------- gestão (Fase 4) ----------------
@app.get("/canal/{canal}/producao", response_class=HTMLResponse)
def producao(request: Request, canal: str):
    if canal not in canais():
        raise HTTPException(404)
    return tpl.TemplateResponse(request, "producao.html", {"canal": canal, "nome": canais()[canal]["nome"],
                                                           "quadro": gestao.quadro(canal)})


@app.post("/canal/{canal}/ideia")
def criar_ideia(canal: str, titulo: str = Form(...), notas: str = Form("")):
    if canal not in canais() or not titulo.strip():
        raise HTTPException(400, "ideia sem título")
    gestao.nova_ideia(canal, titulo, notas)
    return RedirectResponse(f"/canal/{canal}/producao", status_code=303)


@app.post("/canal/{canal}/ideia/{ideia_id}/apagar")
def apagar_ideia(canal: str, ideia_id: int):
    gestao.apagar_ideia(canal, ideia_id)
    return RedirectResponse(f"/canal/{canal}/producao", status_code=303)


@app.post("/v/{canal}/{video}/publicacao")
def salvar_publicacao(canal: str, video: str, status: str = Form(""), titulo_pub: str = Form(""),
                      descricao: str = Form(""), tags: str = Form(""), data_pub: str = Form(""),
                      notas: str = Form(""), link: str = Form(""), voltar: str = Form("")):
    _video_dir(canal, video)
    if status not in ("", *gestao.MANUAIS):
        raise HTTPException(400, "status inválido")
    gestao.salvar_video(canal, video, status=status, titulo_pub=titulo_pub, descricao=descricao, tags=tags,
                        data_pub=data_pub, notas=notas, link=link)
    return RedirectResponse(voltar if voltar.startswith("/") else f"/v/{canal}/{video}", status_code=303)


@app.get("/canal/{canal}/calendario", response_class=HTMLResponse)
def pagina_calendario(request: Request, canal: str, mes: str = ""):
    if canal not in canais():
        raise HTTPException(404)
    hoje = dt.date.today()
    try:
        ano, m = (int(x) for x in mes.split("-")) if mes else (hoje.year, hoje.month)
    except ValueError:
        ano, m = hoje.year, hoje.month
    semanas, sem_data = gestao.calendario(canal, ano, m)
    ant = (dt.date(ano, m, 1) - dt.timedelta(days=1)).strftime("%Y-%m")
    prox = (dt.date(ano, m, 28) + dt.timedelta(days=4)).strftime("%Y-%m")
    nomes = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
             "outubro", "novembro", "dezembro"]
    return tpl.TemplateResponse(request, "calendario.html", {
        "canal": canal, "nome": canais()[canal]["nome"], "semanas": semanas, "sem_data": sem_data,
        "titulo_mes": f"{nomes[m - 1]} de {ano}", "ant": ant, "prox": prox})


# ---------------- configurações: agora no painel novo ----------------
@app.get("/config/canais", include_in_schema=False)
def config_canais():
    return RedirectResponse("/app/config/canais", status_code=307)


@app.get("/config/apis", include_in_schema=False)
def config_apis(canal: str = ""):
    return RedirectResponse(f"/app/c/{canal}/chaves" if canal in canais() else "/app/config/canais", status_code=307)


@app.get("/config/modelos", include_in_schema=False)
def config_modelos():
    return RedirectResponse("/app/config/modelos", status_code=307)


@app.get("/consumo", include_in_schema=False)
def pagina_consumo():
    return RedirectResponse("/app/config/consumo", status_code=307)


@app.get("/primeiros-passos", include_in_schema=False)
def pagina_primeiros_passos():
    return RedirectResponse("/app/config/passos", status_code=307)


# ---------------- painel novo (React, em painel/) ----------------
APP = Path(__file__).with_name("static") / "app"
app.include_router(api)


@app.get("/app", include_in_schema=False)
@app.get("/app/{caminho:path}", include_in_schema=False)
def painel_novo(caminho: str = ""):
    """Arquivos do build (painel/ → static/app/); qualquer outra rota é do React (index.html)."""
    alvo = (APP / caminho).resolve()
    if caminho and alvo.is_file() and alvo.is_relative_to(APP.resolve()):
        return FileResponse(alvo, headers={"Cache-Control": "public, max-age=31536000, immutable"}
                            if caminho.startswith("assets/") else {})
    if not (APP / "index.html").exists():
        return HTMLResponse("<p style='font:16px sans-serif;margin:40px'>O painel novo ainda não foi construído. "
                            "Rode <code>./instalar.sh</code> (ou <code>cd painel && npm install && npm run build</code>)."
                            "</p>", status_code=503)
    return FileResponse(APP / "index.html", headers={"Cache-Control": "no-cache"})


def main(argv=None):
    import uvicorn
    porta = 8765
    if argv and "--porta" in argv:
        porta = int(argv[argv.index("--porta") + 1])
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")


if __name__ == "__main__":
    main(sys.argv[1:])
