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
import unicodedata
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


@app.get("/primeiros-passos", response_class=HTMLResponse)
def pagina_primeiros_passos(request: Request, msg: str = "", ok: str = ""):
    return tpl.TemplateResponse(request, "primeiros_passos.html", {"itens": primeiros_passos.checar(),
                                                                    "msg": msg, "ok": ok})


@app.post("/primeiros-passos/testar-claude")
def testar_claude():
    from .motor_claude import CHECAGEM, ErroClaude, MODELOS_DA_ETAPA, checar_claude
    CHECAGEM.unlink(missing_ok=True)
    try:
        checar_claude(list(MODELOS_DA_ETAPA))
    except ErroClaude as e:
        return RedirectResponse("/primeiros-passos?msg=" + quote(str(e)[:500]), status_code=303)
    return RedirectResponse("/primeiros-passos?ok=1&msg=" + quote(textos.t("pp.claude_ok")), status_code=303)


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


@app.get("/consumo", response_class=HTMLResponse)
def pagina_consumo(request: Request):
    con = _banco()
    linhas = con.execute("""select canal, video, bloco, etapa, modelo, count(*), sum(equivalente), sum(custo_usd),
                            sum(case when ok=0 then 1 else 0 end), max(quando)
                            from chamadas where canal != 'teste' group by 1,2,3,4,5 order by max(quando) desc""").fetchall()
    por_etapa = con.execute("""select etapa, count(*), sum(equivalente),
                               sum(equivalente)*1.0/count(distinct coalesce(asset, bloco || etapa))
                               from chamadas where ok=1 and canal != 'teste' group by etapa order by 3 desc""").fetchall()
    con.close()
    return tpl.TemplateResponse(request, "consumo.html", {"linhas": linhas, "por_etapa": por_etapa})


# ---------------- novo vídeo ----------------
MARCA_COLD_OPEN = "#! cold open: bloco sem card de título"


def dividir_roteiro(roteiro):
    """Divide o roteiro em (cold_open, [(nome, texto)]). Tópico = linha que começa com "#" ("# Nome", "#Nome" ou
    "#Nome." — o ponto final é tirado do nome). Texto antes do 1º tópico = cold open (vira o bloco 00)."""
    cold, partes, atual = [], [], None
    for linha in roteiro.strip().splitlines():
        m = re.match(r"^\s*#+\s*(.+?)\s*$", linha)
        if m and not linha.lstrip().startswith("#!"):
            atual = [m.group(1).rstrip(".:").strip(), []]
            partes.append(atual)
        elif atual is None:
            cold.append(linha)
        else:
            atual[1].append(linha)
    return "\n".join(cold).strip(), [(n, "\n".join(t).strip()) for n, t in partes if n]


def _slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60]


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
    cold_open, partes = dividir_roteiro(roteiro)
    erro = ""
    if not titulo.strip():
        erro = "Dê um título ao vídeo."
    elif not partes:
        erro = "O roteiro precisa ter cada tópico começando com uma linha \"# Nome do tópico\"."
    vd = Path(c["producoes"]) / _slug(titulo)
    if not erro and vd.exists():
        erro = f"Já existe um vídeo com essa pasta ({vd.name})."
    if erro:
        return tpl.TemplateResponse(request, "novo.html", {"canal": canal, "nome": c["nome"], "erro": erro,
                                                           "titulo": titulo, "roteiro": roteiro}, status_code=400)
    (vd / "edicao").mkdir(parents=True)
    (vd / "roteiro_completo.txt").write_text(roteiro.strip() + "\n")
    if cold_open:
        bd = vd / "blocos" / "00"
        bd.mkdir(parents=True)
        (bd / "roteiro.txt").write_text(f"# Cold open\n{MARCA_COLD_OPEN}\n{cold_open}\n")
    for i, (nome, texto) in enumerate(partes, 1):
        bd = vd / "blocos" / f"{i:02d}"
        bd.mkdir(parents=True)
        # a linha "# Nome" não é narrada (gerar_narracao.py ignora #); a linha "Nome." logo abaixo é
        (bd / "roteiro.txt").write_text(f"# {nome}\n{nome}.\n\n{texto}\n")
    gravar_json(vd / "estudio_video.json", {"titulo": titulo.strip()})
    return RedirectResponse(f"/v/{canal}/{vd.name}", status_code=303)


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


# ---------------- configurações: canais e APIs ----------------
FONTES_DIRS = ["/System/Library/Fonts/Supplemental", "/Library/Fonts", str(Path.home() / "Library/Fonts")]


def _fontes():
    out = []
    for d in FONTES_DIRS:
        for f in sorted(Path(d).glob("*.tt[fc]")) + sorted(Path(d).glob("*.otf")):
            out.append(str(f))
    return out


@app.get("/config/canais", response_class=HTMLResponse)
def config_canais(request: Request, erro: str = "", sugestao=None):
    lista = []
    for slug, c in canais().items():
        cj = ler_json(Path(c["raiz"]) / "canal.json", {}) or {}
        lista.append({"slug": slug, **c, "canal_json": cj})
    return tpl.TemplateResponse(request, "config_canais.html", {"lista": lista, "fontes": _fontes(), "erro": erro,
                                                                "sugestao": sugestao or {}})


@app.post("/config/canais/{slug}")
def editar_canal(slug: str, nome: str = Form(...), ativo: str = Form("")):
    dados = canais()
    if slug not in dados:
        raise HTTPException(404)
    configuracao.salvar_canal(slug, nome=nome.strip() or dados[slug]["nome"], ativo=bool(ativo))
    return RedirectResponse("/config/canais", status_code=303)


@app.post("/config/canais/{slug}/identidade")
def editar_identidade(slug: str, cor_fundo: str = Form(...), cor_texto: str = Form(...), cor_destaque: str = Form(...),
                      cor_caixa: str = Form(...), cor_sombra: str = Form(...), fonte: str = Form(...)):
    c = canais().get(slug)
    if not c:
        raise HTTPException(404)
    arq = Path(c["raiz"]) / "canal.json"
    cj = ler_json(arq, {}) or {"nome": c["nome"]}
    ident = cj.setdefault("identidade", {})
    for k, v in (("cor_fundo", cor_fundo), ("cor_texto", cor_texto), ("cor_destaque", cor_destaque),
                 ("cor_caixa", cor_caixa), ("cor_sombra", cor_sombra)):
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            ident[k] = v.upper()
    if fonte in _fontes():
        ident["fonte_marca_arquivo"], ident["fonte_marca"] = fonte, Path(fonte).stem
    gravar_json(arq, cj)
    return RedirectResponse("/config/canais", status_code=303)


def _linhas(txt):
    return [l.strip() for l in (txt or "").splitlines() if l.strip()]


@app.post("/config/canais/{slug}/regras")
def salvar_regras(slug: str, escolha: str = Form(""), storyboard: str = Form(""), genericas: str = Form(""),
                  genericas_hist: str = Form(""), proibidos: str = Form(""), permitido_se: str = Form(""),
                  trocas: str = Form("")):
    if slug not in canais():
        raise HTTPException(404)
    try:
        trocas_l = json.loads(trocas) if trocas.strip() else []
        assert isinstance(trocas_l, list) and all({"padrao", "por"} <= set(x) for x in trocas_l)
        for x in trocas_l + ([{"padrao": permitido_se}] if permitido_se.strip() else []):
            re.compile(x["padrao"])
    except (ValueError, AssertionError, TypeError, re.error) as e:
        return RedirectResponse("/config/canais?erro=" + quote(f"Regras não salvas: trocas/expressão inválidas ({e})"),
                                status_code=303)
    genericas_d = {"outros": _linhas(genericas)}
    if _linhas(genericas_hist):
        genericas_d["historica"] = _linhas(genericas_hist)
    configuracao.salvar_canal(slug, regras={
        "escolha": _linhas(escolha), "storyboard": _linhas(storyboard),
        "busca": {"trocar_termos": trocas_l, "genericas": genericas_d},
        "qa": {"termos_proibidos": [x.strip().lower() for x in proibidos.split(",") if x.strip()],
               "permitido_se": permitido_se.strip()}})
    return RedirectResponse(f"/config/canais#regras-{slug}", status_code=303)


@app.post("/config/canais/{slug}/sugerir-regras", response_class=HTMLResponse)
def sugerir_regras(request: Request, slug: str):
    c = canais().get(slug)
    if not c:
        raise HTTPException(404)
    from .motor_claude import ErroClaude, chamar
    schema = {"type": "object", "additionalProperties": False,
              "required": ["escolha", "storyboard", "genericas", "genericas_hist", "proibidos", "permitido_se", "trocas"],
              "properties": {"escolha": {"type": "array", "items": {"type": "string"}},
                             "storyboard": {"type": "array", "items": {"type": "string"}},
                             "genericas": {"type": "array", "items": {"type": "string"}},
                             "genericas_hist": {"type": "array", "items": {"type": "string"}},
                             "proibidos": {"type": "array", "items": {"type": "string"}},
                             "permitido_se": {"type": "string"},
                             "trocas": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                        "required": ["padrao", "por", "exceto"],
                                        "properties": {"padrao": {"type": "string"}, "por": {"type": "string"},
                                                       "exceto": {"type": "string"}}}}}}
    try:
        r = chamar("regras", (Path(__file__).with_name("prompts") / "regras_tema.md").read_text(),
                   f"Canal: {c['nome']}\nTema: {c['tema']}\nIdioma da narração: {c['idioma']}", schema=schema,
                   modelo=config()["modelos"].get("storyboard"), ctx={"canal": slug})
    except ErroClaude as e:
        return RedirectResponse("/config/canais?erro=" + quote(f"O Claude não respondeu: {str(e)[:300]}"), status_code=303)
    r.pop("_uso", None)
    if r.get("permitido_se", "").strip() in ('""', "''"):       # o modelo às vezes devolve as aspas do exemplo
        r["permitido_se"] = ""
    return config_canais(request, sugestao={slug: r})


@app.post("/config/canais-novo")
async def novo_canal(nome: str = Form(...), tema: str = Form(...), idioma: str = Form("en"),
                     cor_fundo: str = Form(...), cor_texto: str = Form(...), cor_destaque: str = Form(...),
                     cor_caixa: str = Form(...), cor_sombra: str = Form(...), fonte: str = Form(...),
                     logo: UploadFile = File(None), fundo: UploadFile = File(None)):
    cores = {"fundo": cor_fundo, "texto": cor_texto, "destaque": cor_destaque, "caixa": cor_caixa,
             "sombra": cor_sombra}
    if not nome.strip() or not all(re.fullmatch(r"#[0-9A-Fa-f]{6}", v) for v in cores.values()) \
            or fonte not in _fontes():
        return RedirectResponse("/config/canais?erro=Preencha+nome,+cores+(#RRGGBB)+e+fonte", status_code=303)
    DADOS.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=DADOS))
    arqs = {}
    for nome_campo, up in (("logo", logo), ("fundo", fundo)):
        if up is not None and up.filename:
            destino = tmp / (nome_campo + Path(up.filename).suffix.lower())
            with open(destino, "wb") as f:
                shutil.copyfileobj(up.file, f)
            arqs[nome_campo] = destino
    try:
        slug, _ = configuracao.criar_canal(nome.strip(), tema.strip(), idioma.strip() or "en", cores, fonte,
                                           logo=arqs.get("logo"), fundo=arqs.get("fundo"))
    except ValueError as e:
        return RedirectResponse(f"/config/canais?erro={quote(str(e))}", status_code=303)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return RedirectResponse(f"/config/canais#regras-{slug}", status_code=303)


@app.get("/config/apis", response_class=HTMLResponse)
def config_apis(request: Request, canal: str = "", msg: str = "", ok: str = ""):
    lista = canais()
    if not lista:
        return RedirectResponse("/config/canais?erro=" + quote("Crie um canal primeiro: as chaves de API são por canal."),
                                status_code=303)
    canal = canal if canal in lista else next(iter(lista))
    return tpl.TemplateResponse(request, "config_apis.html", {
        "canal": canal, "lista": lista, "apis": configuracao.estado_apis(lista[canal]), "msg": msg, "ok": ok})


@app.post("/config/apis/{canal}/{api_id}")
async def salvar_api(request: Request, canal: str, api_id: str):
    if canal not in canais() or api_id not in {a["id"] for a in configuracao.APIS}:
        raise HTTPException(404)
    form = dict(await request.form())
    mudou = configuracao.salvar_api(canais()[canal], api_id, form)
    msg = "Salvo: " + ", ".join(mudou) if mudou else "Nada mudou (campo secreto vazio mantém a chave atual)."
    return RedirectResponse(f"/config/apis?canal={canal}&msg={quote(msg)}&ok=1#{api_id}", status_code=303)


@app.post("/config/apis/{canal}/{api_id}/testar")
def testar_api(canal: str, api_id: str):
    if canal not in canais():
        raise HTTPException(404)
    ok, msg = configuracao.testar_api(canais()[canal], api_id)
    return RedirectResponse(f"/config/apis?canal={canal}&msg={quote(api_id + ': ' + msg)}&ok={'1' if ok else ''}#{api_id}",
                            status_code=303)


# ---------------- configurações: modelos por etapa ----------------
MODELOS = [("claude-opus-5-5", "Opus 5.5"), ("claude-sonnet-5-5", "Sonnet 5.5"), ("claude-haiku-5-5", "Haiku 5.5"),
           ("claude-fable-5-1", "Fable 5.1")]
ESFORCOS = ["low", "medium", "high", "xhigh", "max"]
ETAPAS_CLAUDE = [
    ("storyboard", "Storyboard", "Planeja as cenas do bloco e corrige até passar nas regras (a etapa mais cara)."),
    ("escolher_imagem", "Escolher imagem", "Escolhe 1 foto/recorte/logo por asset olhando a folha de contato."),
    ("escolher_video", "Escolher vídeo", "Escolhe o vídeo e o início do trecho pelas folhas de quadros."),
    ("confirmar_trecho", "Confirmar trecho", "2ª olhada num vídeo com quadros a cada 0,5 s para acertar o início."),
    ("conferir", "Conferir download", "Olha 1–2 quadros de cada vídeo/recorte baixado (texto por cima, tarja, cena errada)."),
    ("qa", "Corrigir QA", "Quando o QA reprova, corrige o cenas.json uma vez antes de parar."),
]


@app.get("/config/modelos", response_class=HTMLResponse)
def config_modelos(request: Request, msg: str = ""):
    from .motor_claude import config as cfg_estudio
    cfg = cfg_estudio()
    con = _banco()
    medias = {e: (n, eq) for e, n, eq in con.execute(
        "select etapa, count(*), avg(equivalente) from chamadas where ok=1 group by etapa")}
    ultimos = {e: m for e, m in con.execute(
        "select etapa, modelo from chamadas where ok=1 and id in (select max(id) from chamadas group by etapa)")}
    con.close()
    linhas = [{"id": i, "nome": n, "ajuda": a, "modelo": cfg["modelos"].get(i, ""), "esforco": cfg["esforco"].get(i, "low"),
               "chamadas": medias.get(i, (0, 0))[0], "media": medias.get(i, (0, 0))[1], "ultimo": ultimos.get(i, "")}
              for i, n, a in ETAPAS_CLAUDE]
    return tpl.TemplateResponse(request, "config_modelos.html", {"linhas": linhas, "modelos": MODELOS,
                                                                 "esforcos": ESFORCOS, "msg": msg,
                                                                 "after_app": cfg.get("after_app", "")})


@app.post("/config/modelos")
async def salvar_modelos(request: Request):
    form = await request.form()
    validos = {m for m, _ in MODELOS}
    modelos, esforco = {}, {}
    for etapa, _, _ in ETAPAS_CLAUDE:
        m, e = form.get(f"modelo_{etapa}"), form.get(f"esforco_{etapa}")
        if m in validos:
            modelos[etapa] = m
        if e in ESFORCOS:
            esforco[etapa] = e
    mud = {"modelos": modelos, "esforco": esforco}
    after = (form.get("after_app") or "").strip()
    if after and re.fullmatch(r"[\w .-]+", after):
        mud["after_app"] = after
    salvar_config(mud)
    return RedirectResponse("/config/modelos?msg=" + quote("Salvo. Vale a partir da próxima chamada."), status_code=303)


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
