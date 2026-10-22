"""Canais que você quer modelar: cole o link, o sistema guarda o nome, o logo e o tamanho do canal.

Fica em <dados>/space_machine.sqlite (tabela canais_modelo) e o logo em <dados>/cache/modelos/.

Nome e logo vêm da API oficial do YouTube (chave YOUTUBE_API_KEY em <dados>/.env, no painel em Chaves › YouTube):
uma chamada por link que VOCÊ cola, e só. Nada aqui busca vídeo, abre página nem baixa mídia do YouTube — a regra
de 2026-10-11 continua valendo para a produção inteira (ver CLAUDE.md).
"""
import re
from pathlib import Path

import requests

from . import configuracao
from .motor_claude import _banco
from .sistema import DADOS

CACHE = DADOS / "cache" / "modelos"
API = "https://www.googleapis.com/youtube/v3"
PARTES = "snippet,statistics,brandingSettings"

# o que dá para reconhecer num link colado
ALVOS = [
    ("id", re.compile(r"youtube\.com/channel/(UC[\w-]{10,})", re.I)),
    ("handle", re.compile(r"youtube\.com/@([\w.\-]+)", re.I)),
    ("nome", re.compile(r"youtube\.com/(?:c|user)/([\w.\-]+)", re.I)),
    ("video", re.compile(r"youtube\.com/(?:watch\?(?:[^#]*&)?v=|shorts/|live/|embed/)([\w-]{11})", re.I)),
    ("video", re.compile(r"youtu\.be/([\w-]{11})", re.I)),
]


def _db():
    con = _banco()
    con.execute("""create table if not exists canais_modelo (
        id integer primary key, canal_id text unique, url text, nome text, handle text, descricao text,
        inscritos int, videos int, vistas int, pais text, logo text, notas text, criado text, atualizado text)""")
    return con


def alvo(link):
    """O que o link aponta: ("id"|"handle"|"nome"|"video", valor). Aceita também só "@nome" ou o id UC... ."""
    link = (link or "").strip()
    if not link:
        raise ValueError("Cole o link do canal.")
    for tipo, re_ in ALVOS:
        m = re_.search(link)
        if m:
            return tipo, m.group(1)
    if re.fullmatch(r"@[\w.\-]+", link):
        return "handle", link[1:]
    if re.fullmatch(r"UC[\w-]{10,}", link):
        return "id", link
    raise ValueError("Não reconheci esse link. Use o endereço do canal (youtube.com/@nome) ou de um vídeo dele.")


def _chamar(chave, recurso, **params):
    try:
        r = requests.get(f"{API}/{recurso}", params={**params, "key": chave}, timeout=25)
    except requests.RequestException as e:
        raise ValueError(f"Não deu para falar com o YouTube: {e}")
    if not r.ok:
        erro = {}
        try:
            erro = r.json().get("error", {}) or {}
        except ValueError:
            pass
        motivos = {m.get("reason", "") for m in (erro.get("errors") or [])}
        motivos |= {d.get("reason", "") for d in (erro.get("details") or []) if isinstance(d, dict)}
        if motivos & {"quotaExceeded", "rateLimitExceeded"}:
            raise ValueError("A cota de hoje da chave do YouTube acabou. Tente amanhã.")
        if r.status_code in (400, 401, 403) or motivos & {"API_KEY_INVALID", "SERVICE_DISABLED"}:
            raise ValueError("A chave do YouTube não foi aceita (" + (erro.get("message") or f"HTTP {r.status_code}")
                             + "). Confira em Chaves › YouTube.")
        raise ValueError(f"O YouTube respondeu HTTP {r.status_code}.")
    return r.json()


def _do_youtube(chave, tipo, valor):
    """O canal como a API oficial devolve. Link de vídeo: pega o canal do vídeo."""
    if tipo == "video":
        itens = _chamar(chave, "videos", part="snippet", id=valor).get("items") or []
        if not itens:
            raise ValueError("Esse vídeo não existe mais (ou é privado).")
        tipo, valor = "id", itens[0]["snippet"]["channelId"]
    tentativas = {"id": [{"id": valor}], "handle": [{"forHandle": f"@{valor}"}]}.get(
        tipo, [{"forHandle": f"@{valor}"}, {"forUsername": valor}])
    for params in tentativas:
        itens = _chamar(chave, "channels", part=PARTES, **params).get("items") or []
        if itens:
            return itens[0]
    if tipo != "id":
        # endereço antigo (/c/Nome) não resolve por handle: a busca da própria API acha pelo nome
        achados = _chamar(chave, "search", part="snippet", type="channel", q=valor, maxResults=1).get("items") or []
        if achados:
            cid = achados[0]["id"]["channelId"]
            itens = _chamar(chave, "channels", part=PARTES, id=cid).get("items") or []
            if itens:
                return itens[0]
    raise ValueError("Não achei esse canal no YouTube.")


def _guardar_logo(canal_id, url):
    """Baixa o logo que veio na resposta da API para o cache. Sem logo, o card mostra as iniciais."""
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=25)
        if not r.ok or not r.headers.get("Content-Type", "").startswith("image/"):
            return ""
    except requests.RequestException:
        return ""
    CACHE.mkdir(parents=True, exist_ok=True)
    arq = CACHE / f"{canal_id}.jpg"
    arq.write_bytes(r.content)
    return arq.name


def _campos(bruto):
    sn, st = bruto.get("snippet", {}) or {}, bruto.get("statistics", {}) or {}
    thumbs = sn.get("thumbnails", {}) or {}
    melhor = next((thumbs[q]["url"] for q in ("high", "medium", "default") if thumbs.get(q, {}).get("url")), "")
    handle = (sn.get("customUrl") or "").lstrip("@")
    return {
        "canal_id": bruto["id"], "nome": sn.get("title", ""), "handle": handle,
        "descricao": (sn.get("description") or "").strip()[:600], "pais": sn.get("country", ""),
        "inscritos": int(st.get("subscriberCount") or 0), "videos": int(st.get("videoCount") or 0),
        "vistas": int(st.get("viewCount") or 0),
        "url": f"https://www.youtube.com/@{handle}" if handle else f"https://www.youtube.com/channel/{bruto['id']}",
        "_logo_url": melhor,
    }


def _ler(lin):
    nomes = ["id", "canal_id", "url", "nome", "handle", "descricao", "inscritos", "videos", "vistas", "pais",
             "logo", "notas", "criado", "atualizado"]
    d = dict(zip(nomes, lin))
    d["tem_logo"] = bool(d["logo"]) and (CACHE / d["logo"]).exists()
    return d


SELECT = ("select id, canal_id, url, nome, handle, descricao, inscritos, videos, vistas, pais, logo, notas, "
          "criado, atualizado from canais_modelo")


def lista():
    con = _db()
    out = [_ler(l) for l in con.execute(f"{SELECT} order by inscritos desc, id desc")]
    con.close()
    return out


def um(ref_id):
    con = _db()
    lin = con.execute(f"{SELECT} where id=?", (ref_id,)).fetchone()
    con.close()
    if not lin:
        raise ValueError("esse canal não está na lista")
    return _ler(lin)


def chave():
    return configuracao.chave_sistema("youtube")


def adicionar(link):
    """Busca o canal pelo link e guarda. Canal que já está na lista só é atualizado (não duplica)."""
    ch = chave()
    if not ch:
        raise ValueError("Falta a chave da API do YouTube. Cole-a aqui embaixo para o sistema buscar nome e logo.")
    c = _campos(_do_youtube(ch, *alvo(link)))
    c["logo"] = _guardar_logo(c["canal_id"], c.pop("_logo_url"))
    con = _db()
    con.execute("""insert into canais_modelo (canal_id, url, nome, handle, descricao, inscritos, videos, vistas,
                   pais, logo, notas, criado, atualizado)
                   values (:canal_id,:url,:nome,:handle,:descricao,:inscritos,:videos,:vistas,:pais,:logo,'',
                   datetime('now','localtime'), datetime('now','localtime'))
                   on conflict(canal_id) do update set url=excluded.url, nome=excluded.nome, handle=excluded.handle,
                   descricao=excluded.descricao, inscritos=excluded.inscritos, videos=excluded.videos,
                   vistas=excluded.vistas, pais=excluded.pais, logo=excluded.logo,
                   atualizado=excluded.atualizado""", c)
    con.commit()
    lin = con.execute(f"{SELECT} where canal_id=?", (c["canal_id"],)).fetchone()
    con.close()
    return _ler(lin)


def atualizar(ref_id):
    """Busca de novo os números e o logo de um canal que já está na lista."""
    return adicionar(um(ref_id)["url"])


def salvar_notas(ref_id, notas):
    um(ref_id)
    con = _db()
    con.execute("update canais_modelo set notas=? where id=?", ((notas or "").strip()[:2000], ref_id))
    con.commit()
    con.close()


def remover(ref_id):
    c = um(ref_id)
    con = _db()
    con.execute("delete from canais_modelo where id=?", (ref_id,))
    con.commit()
    con.close()
    if c["logo"]:
        (CACHE / c["logo"]).unlink(missing_ok=True)


def arquivo_logo(ref_id):
    c = um(ref_id)
    arq = CACHE / c["logo"] if c["logo"] else None
    return arq if arq and arq.exists() else None
