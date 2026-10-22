"""API do painel React (painel/, servido em /app).

Lê o mesmo que o painel antigo: as pastas (estado.py), a gestão (ideias, publicação) e o consumo no sqlite.
As ações chamam as mesmas funções das rotas antigas (fila.lancar_rodada, fila.lancar_fila, ...).
/api/eventos avisa o navegador quando alguma pasta de produção muda, para a tela se atualizar sozinha.
"""
import asyncio
import datetime as dt
import hashlib
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from . import (atualizar, capas, configuracao, estado, fila, final, gestao, limpeza, meus_prompts, modelar,
               primeiros_passos, reels, textos)
from .motor_claude import _banco, canais
from .rodar import ETAPAS as ETAPAS_RODAR
from .sistema import DADOS, REPO, config, ler_json

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
            "tem_capa": bool(capas.fontes(v["pasta"], b["nn"])),
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
        "atual": {k: atual[k] for k in ("slug", "titulo", "n_blocos", "entregues", "rodando", "tem_capa", "capa_v")} if atual else None,
        "rodando_agora": [b["nn"] for b in (atual or {}).get("blocos", []) if b["estado"] == "run"],
    }, vids, brutos


# ---------------- leitura ----------------
@api.get("/sistema")
def sistema():
    idioma = config().get("idioma_painel", "pt")
    atualizar.conferir_atras_das_cortinas()      # a conferida vai à rede no máximo a cada 6 h, fora deste pedido
    return {"idioma": idioma, "textos": {**textos._idioma("pt"), **textos._idioma(idioma)},
            "falta_algo": _falta_algo(), "dados": str(DADOS), "atualizacao": atualizar.aviso()}


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
                                  "tem_capa": bool(capas.fontes(bruto["pasta"], b["nn"])),
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


def _arquivo(p):
    """Endereço de um arquivo da produção pela rota /arquivo do servidor (só serve de dentro das produções)."""
    return f"/arquivo?p={quote(str(p))}"


def _cauda(arq, linhas):
    try:
        return "\n".join(Path(arq).read_text(errors="replace").splitlines()[-linhas:])
    except OSError:
        return ""


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
    if not mp4.is_file():      # MP4 renderizado antes (ou à mão): o mais novo da pasta final/
        mp4 = max((vd / "final").glob("*.mp4"), key=lambda f: f.stat().st_mtime, default=mp4)
    fim.update(tem_aep=aep.exists(), mp4_url=_arquivo(mp4) if mp4.is_file() else None,
               mp4_tamanho=mp4.stat().st_size if mp4.is_file() else 0, entregues=len(final.entregues(vd)))
    thumb = capas.info_thumbnail(vd)
    if thumb:
        thumb["url"] = _arquivo(thumb.pop("arquivo")) + f"&v={thumb['versao']}"
    return {**resumo, "blocos": blocos, "fila": v.get("fila") or None, "final": fim, "thumbnail": thumb,
            "publicacao": gestao.dados_video(slug, video),
            "consumo_detalhe": v.get("consumo") or {}, "etapas": [{"id": e, "rotulo": r} for e, r in estado.ETAPAS],
            "tem_roteiro": (vd / "roteiro_completo.txt").exists()}


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
        "etapas": [{"id": e, **{k: (est.get("etapas", {}).get(e) or {}).get(k, "") for k in ("status", "detalhe", "quando")}}
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


@api.get("/busca")
def busca():
    """Tudo o que a busca (⌘K) encontra: canais, vídeos e blocos dos canais ativos."""
    out = {"canais": [], "videos": [], "blocos": [], "prompts": []}
    for slug, c in canais().items():
        out["canais"].append({"slug": slug, "nome": c["nome"], "tema": c.get("tema", "")})
        out["prompts"] += [{"canal": slug, "canal_nome": c["nome"], "nome": p["nome"], "titulo": p["titulo"]}
                           for p in meus_prompts.listar(slug)]
        if not c.get("ativo"):
            continue
        for v in estado.videos(slug):
            g = gestao.dados_video(slug, v["slug"])
            titulo = g.get("titulo_pub") or v["titulo"]
            out["videos"].append({"canal": slug, "canal_nome": c["nome"], "slug": v["slug"], "titulo": titulo})
            out["blocos"] += [{"canal": slug, "video": v["slug"], "video_titulo": titulo, "nn": b["nn"],
                               "topico": b["topico"]} for b in v["blocos"]]
    return out


@api.get("/avisos")
def avisos():
    """O que pede atenção, de todos os canais ativos: blocos parados esperando você, filas pausadas e blocos
    entregues nas últimas 24 h. Mais novo em cima."""
    itens, agora = [], time.time()
    for slug, c in canais().items():
        if not c.get("ativo"):
            continue
        for v in estado.videos(slug):
            f = v.get("fila") or {}
            base = {"canal": slug, "canal_nome": c["nome"], "video": v["slug"], "video_titulo": v["titulo"]}
            if f.get("ativa") and f.get("status") == "pausada":
                arq = Path(v["pasta"]) / "_estudio" / "fila.json"
                itens.append({**base, "tipo": "fila", "nn": "", "topico": "", "texto": f.get("motivo", ""),
                              "quando": arq.stat().st_mtime if arq.exists() else agora})
            for b in v["blocos"]:
                est = _estado_bloco(b, f)
                if est == "wait":
                    itens.append({**base, "tipo": "esperando", "nn": b["nn"], "topico": b["topico"],
                                  "texto": (b["parado"] or {}).get("motivo", ""), "etapa": (b["parado"] or {}).get("etapa", ""),
                                  "quando": b["mudou"] or agora})
                elif est == "ok":
                    arq = Path(v["pasta"]) / "edicao" / f"bloco {int(b['nn'])}.mp4"
                    quando = arq.stat().st_mtime if arq.exists() else 0
                    if agora - quando < 86400:
                        itens.append({**base, "tipo": "entregue", "nn": b["nn"], "topico": b["topico"], "texto": "",
                                      "quando": quando})
    for i in itens:
        i["id"] = f"{i['tipo']}:{i['canal']}:{i['video']}:{i['nn']}:{int(i['quando'])}"
    return {"itens": sorted(itens, key=lambda i: -i["quando"])[:50]}


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
    from .motor_claude import ErroClaude
    _video_dir(slug, video)
    try:
        return gestao.gerar_descricao(_canal(slug), slug, video)
    except ErroClaude as e:
        raise HTTPException(502, f"O Claude não respondeu: {str(e)[:300]}")


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
def novo_video(slug: str, titulo: str = Body(..., embed=True), roteiro: str = Body(..., embed=True),
               ideia: int = Body(0, embed=True)):
    """ideia: o id da ideia do "Virar vídeo" (sai da lista de ideias quando o vídeo é criado)."""
    try:
        video = gestao.criar_video(_canal(slug), titulo, roteiro)
    except ValueError as e:
        raise HTTPException(400, str(e))
    gestao.ideia_virou_video(slug, ideia, video)
    return {"ok": True, "video": video}


@api.post("/c/{slug}/v/{video}/thumbnail")
async def enviar_thumbnail(slug: str, video: str, arquivo: UploadFile = File(...)):
    """A thumbnail do vídeo (a que vai para o YouTube): vira a capa do vídeo no painel. A anterior é guardada."""
    vd = _video_dir(slug, video)
    dados = await arquivo.read()
    if len(dados) > 30 * 1024 * 1024:
        raise HTTPException(400, "Imagem grande demais (máx. 30 MB).")
    try:
        capas.salvar_thumbnail(vd, dados, arquivo.filename or "thumbnail.png")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "thumbnail": capas.info_thumbnail(vd) and {k: v for k, v in capas.info_thumbnail(vd).items() if k != "arquivo"}}


@api.post("/c/{slug}/v/{video}/thumbnail/remover")
def remover_thumbnail(slug: str, video: str):
    capas.remover_thumbnail(_video_dir(slug, video))
    return {"ok": True}


@api.post("/c/{slug}/v/{video}/final")
def juntar_no_after(slug: str, video: str, render: bool = Body(False, embed=True)):
    """Junta os blocos entregues num projeto do After (final/final.aep) e, se pedir, renderiza o MP4."""
    vd = _video_dir(slug, video)
    if final.ler_estado(vd)["rodando"]:
        raise HTTPException(409, "o vídeo final já está sendo montado")
    if not final.entregues(vd):
        raise HTTPException(409, "nenhum bloco entregue ainda")
    final.lancar(vd, render)
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
    if sub in ("final", "reels") and (pasta / sub).is_dir():
        pasta = pasta / sub
    subprocess.run(["open", str(pasta)], check=False)
    return {"ok": True}


# ---------------- configurações do canal ----------------
@api.get("/c/{slug}/config")
def config_canal(slug: str):
    c = _canal(slug)
    cj = ler_json(Path(c["raiz"]) / "canal.json", {}) or {}
    ident = cj.get("identidade", {}) or {}
    return {"slug": slug, "nome": c["nome"], "ativo": bool(c.get("ativo")), "tema": c.get("tema", ""),
            "idioma": c.get("idioma", "en"), "cores": _identidade(c), "fonte": ident.get("fonte_marca_arquivo", ""),
            "fontes": [{"arquivo": f, "nome": Path(f).stem} for f in configuracao.fontes()],
            "banner": bool(marca(c, "banner")), "logo": bool(marca(c, "logo")),
            "regras": configuracao.regras_em_texto(cj.get("regras", {}) or {})}


@api.post("/c/{slug}/config")
def salvar_config_canal(slug: str, nome: str = Body(..., embed=True), ativo: bool = Body(True, embed=True)):
    c = _canal(slug)
    configuracao.salvar_canal(slug, nome=nome.strip() or c["nome"], ativo=bool(ativo))
    return {"ok": True}


@api.post("/c/{slug}/identidade")
def salvar_identidade(slug: str, cores: dict = Body(..., embed=True), fonte: str = Body("", embed=True)):
    _canal(slug)
    configuracao.salvar_identidade(slug, cores, fonte)
    return {"ok": True}


@api.post("/c/{slug}/marca/{qual}")
async def enviar_marca(slug: str, qual: str, arquivo: UploadFile = File(...)):
    """Troca o logo ou o banner do canal. O anterior vai para identidade/anteriores/ (nada se perde)."""
    c = _canal(slug)
    ext = Path(arquivo.filename or "").suffix.lower()
    if qual not in ("banner", "logo") or ext not in IMAGENS:
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
    from .motor_claude import ErroClaude
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


@api.get("/c/{slug}/chaves")
def chaves(slug: str):
    return {"apis": _apis_publicas(_canal(slug))}


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
    return {"ok": True, "copiados": copiados, "apis": _apis_publicas(c)}


@api.post("/c/{slug}/chaves/{api_id}")
def salvar_chave(slug: str, api_id: str, valores: dict = Body({}, embed=True), apagar: list = Body([], embed=True)):
    c = _canal(slug)
    if api_id not in {a["id"] for a in configuracao.APIS}:
        raise HTTPException(404)
    form = {k: str(v) for k, v in valores.items()} | {f"apagar_{k}": "1" for k in apagar}
    mudou = configuracao.salvar_api(c, api_id, form)
    _cache_falta["quando"] = 0
    return {"ok": True, "mudou": mudou, "apis": _apis_publicas(c)}


@api.post("/c/{slug}/chaves/{api_id}/testar")
def testar_chave(slug: str, api_id: str):
    if api_id not in {a["id"] for a in configuracao.APIS}:
        raise HTTPException(404)
    ok, msg = configuracao.testar_api(_canal(slug), api_id)
    return {"ok": ok, "mensagem": msg}


# ---------------- configurações do produtor ----------------
@api.get("/config/modelos")
def modelos():
    return configuracao.estado_modelos()


@api.post("/config/modelos")
def salvar_modelos(modelos: dict = Body({}, embed=True), esforco: dict = Body({}, embed=True),
                   after_app: str = Body("", embed=True)):
    configuracao.salvar_modelos(modelos, esforco, after_app)
    return {"ok": True}


@api.get("/consumo")
def consumo():
    con = _banco()
    por_etapa = con.execute("""select etapa, count(*), sum(equivalente),
                               sum(equivalente)*1.0/count(distinct coalesce(asset, bloco || etapa))
                               from chamadas where ok=1 and canal != 'teste' group by etapa order by 3 desc""").fetchall()
    por_video = con.execute("""select canal, video, count(*), sum(equivalente), max(quando) from chamadas
                               where canal != 'teste' group by 1, 2 order by 5 desc""").fetchall()
    linhas = con.execute("""select canal, video, bloco, etapa, modelo, count(*), sum(equivalente),
                            sum(case when ok=0 then 1 else 0 end), max(quando)
                            from chamadas where canal != 'teste' group by 1,2,3,4,5 order by max(quando) desc
                            limit 300""").fetchall()
    con.close()
    nomes = {s: c["nome"] for s, c in canais().items()}
    return {"total_7d": _consumo_7d()["total"],
            "por_etapa": [{"etapa": e, "chamadas": n, "tokens": t or 0, "media": round(m or 0)} for e, n, t, m in por_etapa],
            "por_video": [{"canal": nomes.get(c, c), "video": v or "", "chamadas": n, "tokens": t or 0, "ultima": q}
                          for c, v, n, t, q in por_video],
            "linhas": [{"canal": nomes.get(c, c), "video": v or "", "bloco": b or "", "etapa": e, "modelo": m,
                        "chamadas": n, "tokens": t or 0, "falhas": f or 0, "ultima": q}
                       for c, v, b, e, m, n, t, f, q in linhas]}


@api.get("/primeiros-passos")
def primeiros_passos_lista():
    itens = primeiros_passos.checar()
    _cache_falta.update(quando=time.time(), falta=any(not i["ok"] for i in itens))
    return {"itens": itens}


@api.post("/primeiros-passos/testar-claude")
def testar_claude():
    from .motor_claude import CHECAGEM, ErroClaude, MODELOS_DA_ETAPA, checar_claude
    CHECAGEM.unlink(missing_ok=True)
    try:
        checar_claude(list(MODELOS_DA_ETAPA))
    except ErroClaude as e:
        return {"ok": False, "mensagem": str(e)[:500]}
    return {"ok": True, "mensagem": textos.t("pp.claude_ok", config().get("idioma_painel", "pt"))}


@api.get("/limpeza")
def levantar_limpeza():
    """O que sairia na limpeza (nada é movido aqui), o espaço no disco e se a limpeza automática está ligada."""
    r = limpeza.levantar(cache=True)
    disco = shutil.disk_usage(DADOS)
    return {**r, "rotulos": limpeza.CATEGORIAS, "automatica": bool(config().get("limpeza_automatica", True)),
            "disco": {"livre": disco.free, "total": disco.total}}


@api.post("/limpeza")
def aplicar_limpeza(categorias: list = Body(..., embed=True)):
    cats = [c for c in categorias if c in limpeza.CATEGORIAS]
    if not cats:
        raise HTTPException(400, "Escolha o que limpar.")
    total, itens, pasta = limpeza.limpar(categorias=cats, cache="cache" in cats)
    no_lixo = str(pasta).startswith(str(Path.home() / ".Trash"))
    return {"ok": True, "bytes": total, "itens": itens, "pasta": pasta.name, "no_lixo_do_mac": no_lixo,
            "caminho": "" if no_lixo else str(pasta)}


@api.post("/limpeza/automatica")
def limpeza_automatica(ligada: bool = Body(..., embed=True)):
    from .sistema import salvar_config
    salvar_config({"limpeza_automatica": bool(ligada)})
    return {"ok": True}


@api.post("/limpeza/abrir-lixo")
def abrir_lixo():
    subprocess.run(["open", str(Path.home() / ".Trash")], check=False)
    return {"ok": True}


# ---------------- atualizar o Space Machine ----------------
@api.get("/atualizacao")
def ver_atualizacao(conferir: bool = False):
    """Sua versão, o que tem de novo no GitHub e, se não der para atualizar agora, por quê.
    Sem conferir=1 responde com a última conferida (vale 6 h), sem ir à rede."""
    r = atualizar.conferir(forcar=conferir)
    motivo, detalhe = atualizar.impedimento()
    return {"local": atualizar.estado_local(), "atrasado": r.get("atrasado", 0), "commits": r.get("commits", []),
            "quando": r.get("quando", 0), "erro": r.get("erro", ""), "erro_detalhe": r.get("detalhe", ""),
            "impedimento": motivo, "detalhe": detalhe}


@api.post("/atualizacao")
def aplicar_atualizacao():
    """git pull e o que mais ficou para trás (Python, painel). Depois o painel se reinicia no código novo."""
    r = atualizar.aplicar()
    if r.get("reiniciar"):
        atualizar.reiniciar_painel(espera=1.5)   # depois desta resposta sair: o navegador espera e recarrega
    return {**r, "local": atualizar.estado_local()}


@api.post("/atualizacao/reiniciar")
def reiniciar_painel(repo: str = Body("", embed=True)):
    """Reinicia o painel no código que está em disco (quem atualizou pela linha de comando chama isto).
    Com repo, só reinicia se for o painel daquela instalação: outra pasta na mesma porta não é reiniciada."""
    if repo and Path(repo).resolve() != REPO.resolve():
        raise HTTPException(409, "este painel é de outra instalação")
    atualizar.reiniciar_painel(espera=1.0)
    return {"ok": True}


@api.get("/fontes")
def lista_fontes():
    return {"fontes": [{"arquivo": f, "nome": Path(f).stem} for f in configuracao.fontes()]}


@api.post("/canais/novo")
async def novo_canal(nome: str = Form(...), tema: str = Form(...), idioma: str = Form("en"),
                     cor_fundo: str = Form(...), cor_texto: str = Form(...), cor_destaque: str = Form(...),
                     cor_caixa: str = Form(...), cor_sombra: str = Form(...), fonte: str = Form(...),
                     logo: UploadFile = File(None), fundo: UploadFile = File(None), banner: UploadFile = File(None)):
    cores = {"fundo": cor_fundo, "texto": cor_texto, "destaque": cor_destaque, "caixa": cor_caixa, "sombra": cor_sombra}
    if not nome.strip() or not tema.strip():
        raise HTTPException(400, "Dê um nome e um tema ao canal.")
    if not all(configuracao.COR.fullmatch(v) for v in cores.values()) or fonte not in configuracao.fontes():
        raise HTTPException(400, "Escolha as cores (#RRGGBB) e a fonte dos títulos.")
    DADOS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DADOS) as tmp:
        arqs = {}
        for campo, up in (("logo", logo), ("fundo", fundo), ("banner", banner)):
            if up is not None and up.filename:
                ext = Path(up.filename).suffix.lower()
                if ext not in IMAGENS:
                    raise HTTPException(400, f"{campo}: envie PNG, JPG ou WEBP.")
                arqs[campo] = Path(tmp) / f"{campo}{ext}"
                arqs[campo].write_bytes(await up.read())
        try:
            slug, pasta = configuracao.criar_canal(nome.strip(), tema.strip(), idioma.strip() or "en", cores, fonte,
                                                   logo=arqs.get("logo"), fundo=arqs.get("fundo"))
        except ValueError as e:
            raise HTTPException(400, str(e))
        if arqs.get("banner"):
            shutil.copy2(arqs["banner"], Path(pasta) / "identidade" / arqs["banner"].name)
    _cache_falta["quando"] = 0
    return {"ok": True, "slug": slug}


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


@api.post("/config/chaves/{api_id}")
def salvar_chave_sistema(api_id: str, valor: str = Body("", embed=True)):
    """Chave que vale para todos os canais (hoje: Claude e YouTube), para não ter de entrar num canal só por isso."""
    try:
        mostrar = configuracao.salvar_chave_sistema(api_id, valor)
    except ValueError as e:
        raise HTTPException(404, str(e))
    _cache_falta["quando"] = 0
    return {"ok": True, "mostrar": mostrar}


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
        marcar(Path(c["raiz"]) / "prompts")
        prod = Path(c["producoes"])
        if not prod.is_dir():
            continue
        marcar(prod)
        for vd in prod.iterdir():
            if not vd.is_dir() or vd.name.startswith((".", "_")):
                continue
            for p in (vd, vd / "edicao", vd / "_estudio" / "fila.json", vd / "estudio_video.json", vd / "blocos",
                      vd / "final" / "estado.json"):
                marcar(p)
            if (vd / "final" / "pid").exists():
                h.update(f"vivo:{estado._vivo((vd / 'final' / 'pid').read_text().strip())};".encode())
            if not (vd / "blocos").is_dir():
                continue
            for b in (vd / "blocos").iterdir():
                est = b / "_estudio"
                for p in (b, b / "edicao", est, est / "estado.json", est / "log_rodar.txt", est / "conferir_ok.json",
                          vd / "reels" / f"estado_{b.name}.json"):
                    marcar(p)
                if (vd / "reels" / f"pid_{b.name}").exists():
                    h.update(f"vivo:{estado._vivo((vd / 'reels' / f'pid_{b.name}').read_text().strip())};".encode())
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
