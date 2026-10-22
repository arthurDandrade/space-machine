"""Servidor do painel do Space Machine no navegador (localhost).

Iniciar:  ./spacemachine   (ou .venv/bin/python -m space_machine painel)   → http://localhost:8765

O painel é o React de painel/ (build em static/app/), servido aqui na raiz; os dados e as ações vêm de api.py, que lê
as pastas (estado.py) e o registro de consumo e gestão (<dados>/space_machine.sqlite). Os botões só disparam os mesmos
comandos da linha de comando (python -m space_machine rodar ...), em segundo plano.
/arquivo serve prévias e assets de dentro das pastas de produção. Os endereços do painel antigo (páginas em Jinja,
até 2026-10-14) redirecionam para as telas novas.
"""
import sys
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from .api import api
from .motor_claude import canais

app = FastAPI(title="Space Machine")
PORTA = 8765        # a porta desta vez: atualizar.reiniciar_painel volta na mesma
app.include_router(api)
APP = Path(__file__).with_name("static") / "app"


@app.get("/arquivo")
def arquivo(p: str):
    """Serve prévias, folhas, revisão — só de dentro das pastas de produção dos canais."""
    alvo = Path(p).resolve()
    if not any(str(alvo).startswith(str(Path(c["producoes"]).resolve()) + "/") for c in canais().values()):
        raise HTTPException(403, "fora das pastas de produção")
    if not alvo.is_file():
        raise HTTPException(404)
    return FileResponse(alvo)


# ---------------- endereços do painel antigo → telas novas ----------------
def _para(destino):
    return RedirectResponse(destino, status_code=307)


@app.get("/v/{canal}/{video}", include_in_schema=False)
def antigo_video(canal: str, video: str):
    return _para(f"/c/{quote(canal)}/v/{quote(video)}")


@app.get("/b/{canal}/{video}/{nn}", include_in_schema=False)
def antigo_bloco(canal: str, video: str, nn: str):
    return _para(f"/c/{quote(canal)}/v/{quote(video)}/b/{quote(nn)}")


@app.get("/canal/{canal}/producao", include_in_schema=False)
def antigo_producao(canal: str):
    return _para(f"/c/{quote(canal)}/quadro")


@app.get("/canal/{canal}/calendario", include_in_schema=False)
def antigo_calendario(canal: str):
    return _para(f"/c/{quote(canal)}/calendario")


@app.get("/novo/{canal}", include_in_schema=False)
def antigo_novo(canal: str, titulo: str = ""):
    return _para(f"/c/{quote(canal)}/novo" + (f"?titulo={quote(titulo)}" if titulo else ""))


@app.get("/config/apis", include_in_schema=False)
def antigo_apis(canal: str = ""):
    return _para(f"/c/{quote(canal)}/chaves" if canal in canais() else "/config/canais")


@app.get("/consumo", include_in_schema=False)
def antigo_consumo():
    return _para("/config/consumo")


@app.get("/primeiros-passos", include_in_schema=False)
def antigo_primeiros_passos():
    return _para("/config/passos")


@app.get("/antigo", include_in_schema=False)
@app.get("/app", include_in_schema=False)
def antigo_inicio():
    return _para("/")


@app.get("/app/{caminho:path}", include_in_schema=False)
def antigo_app(caminho: str):
    """O painel novo morou em /app até virar a raiz (2026-10-14)."""
    return _para("/" + quote(caminho))


# ---------------- o painel (React) ----------------
@app.get("/{caminho:path}", include_in_schema=False)
def painel(caminho: str = ""):
    """Arquivos do build (painel/ → static/app/); qualquer outro endereço é uma tela do React (index.html)."""
    if caminho.startswith("api/"):
        raise HTTPException(404, "rota da API não existe")
    alvo = (APP / caminho).resolve()
    if caminho and alvo.is_file() and alvo.is_relative_to(APP.resolve()):
        return FileResponse(alvo, headers={"Cache-Control": "public, max-age=31536000, immutable"}
                            if caminho.startswith("assets/") else {})
    if not (APP / "index.html").exists():
        return HTMLResponse("<p style='font:16px sans-serif;margin:40px'>O painel ainda não foi montado. "
                            "Rode <code>./instalar.sh</code> (ou <code>cd painel && npm install && npm run build</code>)."
                            "</p>", status_code=503)
    return FileResponse(APP / "index.html", headers={"Cache-Control": "no-cache"})


def main(argv=None):
    import uvicorn
    global PORTA
    if argv and "--porta" in argv:
        PORTA = int(argv[argv.index("--porta") + 1])
    uvicorn.run(app, host="127.0.0.1", port=PORTA, log_level="warning")


if __name__ == "__main__":
    main(sys.argv[1:])
