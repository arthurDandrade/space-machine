"""Mineração: garimpa no YouTube os vídeos que estouraram num nicho, para você ver o que está dando certo.

Você escreve o nicho ("arquitetura", "NFL"); o Claude transforma isso em termos de busca uma vez só e o garimpo
devolve uma grade de VÍDEOS — thumbnail, título, views e o multiplicador (quantas vezes o vídeo passou da
audiência do próprio canal). O canal que te interessar vai para a Modelagem com um clique (modelar.py).

Fica em <dados>/space_machine.sqlite (nichos, videos_minerados, garimpos, cota_youtube); thumbnails e logos em
<dados>/cache/mineracao/.

Como garimpa, pela API oficial do YouTube (chave YOUTUBE_API_KEY em <dados>/.env, no painel em Chaves › YouTube):
  1. search.list  de cada termo do nicho, order=viewCount, só vídeos dos últimos N dias → 100 unidades
  2. videos.list   em lotes de 50, para as views de verdade e o canal de cada vídeo     → 1 unidade
  3. channels.list em lotes de 50, para inscritos, total de vídeos e a data de nascimento → 1 unidade
Um nicho de 8 termos custa ~810 das 10.000 unidades por dia da chave: dá uns 12 garimpos por dia.

A regra de 2026-10-11 continua valendo para a PRODUÇÃO inteira: nenhum script da produção toca no YouTube. Isto
aqui é pesquisa de canal pela API com chave, no botão do painel (ou um garimpo por dia, se você deixar ligado):
nada abre página nem raspa busca — só o JSON da API e as imagens (thumbnail e logo) que ela mesma devolve. A
decisão de ampliar a exceção do modelar.py para cá é de 2026-10-26 e está escrita no CLAUDE.md.
"""
import datetime as dt
import json
import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import requests

from . import modelar, motor_claude
from .modelar import _campos, _chamar, chave
from .motor_claude import _banco, canais
from .sistema import DADOS, config, salvar_config

CACHE = DADOS / "cache" / "mineracao"
THUMBS = CACHE / "thumbs"

# o que cada chamada da API tira da cota de 10.000 unidades por dia
CUSTO = {"search": 100, "videos": 1, "channels": 1}
COTA_DIA = 10000
TERMOS_POR_NICHO = 8            # 8 termos = 800 unidades por garimpo de um nicho

# o que é "vídeo que estourou num canal novo". O painel manda os seus; estes são os padrões de fábrica.
FILTROS = {
    "dias": 90,                 # só vídeos publicados nos últimos N dias
    "idade_max_meses": 18,      # o canal nasceu no máximo há isso (0 = sem limite)
    "inscritos_min": 1000,      # abaixo disso é canal parado, não canal estourando
    "inscritos_max": 500000,    # acima disso já é canal grande (0 = sem limite)
    "vistas_min": 50000,        # o vídeo fez pelo menos isso de views
    "surto_min": 1.0,           # views do vídeo ÷ inscritos do canal
    "pais": "",                 # regionCode da busca (vazio = sem filtro)
    "idioma": "",               # relevanceLanguage da busca
    "por_termo": 50,            # quantos vídeos trazer de cada termo (50 é o máximo da API)
}

# referências da nota (ver _nota): o que vale a parte cheia de cada pedaço
SURTO_CHEIO = 20            # o vídeo fez 20x os inscritos do canal
VISTAS_DIA_CHEIO = 200000   # o canal faz 200 mil views por dia desde que nasceu
JOVEM_DIAS = 550            # ~18 meses: acima disso o pedaço "jovem" é zero

SITUACOES = ("novo", "descartado", "modelo")
VALIDADE_AUTOMATICO = 20 * 3600     # o garimpo do dia só repete depois disso
_trava_automatico = threading.Lock()


def _db():
    con = _banco()
    con.execute("""create table if not exists nichos (
        id integer primary key, nome text unique, termos text, criado text, ultimo text)""")
    con.execute("""create table if not exists videos_minerados (
        id integer primary key, video_id text unique, titulo text, thumb text, vistas int, publicado text,
        canal_id text, canal_nome text, canal_handle text, canal_url text, canal_logo text, canal_pais text,
        inscritos int, canal_videos int, canal_vistas int, nasceu text, idade_dias int,
        surto real, vistas_dia real, nota real, nicho text, termo text, situacao text, notas text,
        achado text, atualizado text)""")
    con.execute("""create table if not exists garimpos (
        id integer primary key, quando text, veios int, olhados int, aprovados int, novos int, cota int,
        erro text)""")
    con.execute("""create table if not exists cota_youtube (dia text primary key, unidades int)""")
    # a 1ª Mineração (manhã de 2026-10-26) guardava CANAIS achados por "veios" que você cadastrava; virou grade
    # de vídeos por nicho no mesmo dia. As duas tabelas de lá não são lidas por ninguém: um garimpo refaz tudo.
    con.execute("drop table if exists canais_minerados")
    con.execute("drop table if exists veios")
    return con


# ---------------- cota da chave ----------------
def _dia_cota():
    """O dia da cota do YouTube: ela zera à meia-noite do Pacífico (~UTC-8), não à sua."""
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=8)).strftime("%Y-%m-%d")


def _gastar(unidades):
    con = _db()
    con.execute("insert into cota_youtube (dia, unidades) values (?,?) "
                "on conflict(dia) do update set unidades = unidades + excluded.unidades",
                (_dia_cota(), int(unidades)))
    con.commit()
    con.close()


def cota():
    """Quanto da cota de hoje já foi gasto, para o painel avisar antes de você estourar."""
    con = _db()
    lin = con.execute("select unidades from cota_youtube where dia=?", (_dia_cota(),)).fetchone()
    con.close()
    usada = int(lin[0]) if lin else 0
    return {"usada": usada, "limite": COTA_DIA, "sobra": max(0, COTA_DIA - usada), "dia": _dia_cota()}


# ---------------- filtros (ficam no space_machine.json) ----------------
def filtros():
    guardados = (config().get("mineracao") or {}).get("filtros") or {}
    return {**FILTROS, **{k: v for k, v in guardados.items() if k in FILTROS}}


def salvar_filtros(novos):
    """Grava só o que é número/texto conhecido; o resto do espaço de filtros continua no padrão."""
    limpos = {}
    for k, padrao in FILTROS.items():
        if k not in (novos or {}):
            continue
        v = novos[k]
        if isinstance(padrao, str):
            limpos[k] = re.sub(r"[^A-Za-z-]", "", str(v or ""))[:5]
        elif isinstance(padrao, float):
            limpos[k] = max(0.0, round(float(v or 0), 2))
        else:
            limpos[k] = max(0, int(v or 0))
    limpos["por_termo"] = min(50, limpos.get("por_termo") or FILTROS["por_termo"])
    limpos["dias"] = min(365, max(1, limpos.get("dias") or FILTROS["dias"]))
    salvar_config({"mineracao": {"filtros": limpos}})
    return filtros()


def automatico():
    return bool((config().get("mineracao") or {}).get("automatica", True))


def salvar_automatico(ligado):
    salvar_config({"mineracao": {"automatica": bool(ligado)}})
    return automatico()


# ---------------- nichos ----------------
def _ler_nicho(lin):
    d = dict(zip(["id", "nome", "termos", "criado", "ultimo"], lin))
    d["termos"] = json.loads(d["termos"] or "[]")
    return d


def nichos(por_rodizio=False):
    """Os nichos. por_rodizio: na ordem em que o garimpo automático pega — quem nunca foi, depois o mais antigo."""
    con = _db()
    ordem = " order by ultimo is not null, ultimo, id" if por_rodizio else " order by nome"
    out = [_ler_nicho(l) for l in con.execute("select id, nome, termos, criado, ultimo from nichos" + ordem)]
    con.close()
    return out


def um_nicho(nome):
    con = _db()
    lin = con.execute("select id, nome, termos, criado, ultimo from nichos where nome=?", (nome,)).fetchone()
    con.close()
    if not lin:
        raise ValueError("esse nicho não está na lista")
    return _ler_nicho(lin)


def _termos_do_claude(nicho, idioma=""):
    """O Claude transforma o nicho em termos de busca. É o que tira de você a tarefa de cadastrar termo."""
    sistema = ("Você ajuda a garimpar vídeos do YouTube de um nicho. Responda só o JSON pedido, com termos de "
               "busca curtos (2 a 5 palavras) do jeito que o público digitaria na busca do YouTube. Cubra o "
               "nicho por ângulos diferentes (explicação, história, bastidor, erro comum, comparação), sem "
               "repetir a mesma ideia. Nada de nome de canal, de hashtag nem de aspas.")
    texto = json.dumps({"nicho": nicho, "idioma": idioma or "o idioma mais usado nesse nicho no YouTube",
                        "quantos": TERMOS_POR_NICHO}, ensure_ascii=False)
    schema = {"type": "object", "properties": {"termos": {"type": "array", "items": {"type": "string"}}},
              "required": ["termos"]}
    r = motor_claude.chamar("termos_mineracao", sistema, texto, schema=schema)
    vistos, out = set(), []
    for t in (r.get("termos") or []):
        t = re.sub(r"\s+", " ", str(t)).strip().strip('"#')[:120]
        if len(t) >= 2 and t.lower() not in vistos:
            vistos.add(t.lower())
            out.append(t)
    if not out:
        raise ValueError("O Claude não devolveu termo nenhum para esse nicho. Tente escrever de outro jeito.")
    return out[:TERMOS_POR_NICHO]


def salvar_nicho(nome, termos=None):
    """Guarda o nicho. Sem termos, o Claude escreve os dele na hora (uma vez só: depois ficam guardados)."""
    nome = re.sub(r"\s+", " ", (nome or "")).strip()[:80]
    if len(nome) < 2:
        raise ValueError("Escreva o nicho (ex.: “arquitetura”, “NFL”, “história da aviação”).")
    termos = [t for t in (termos or []) if len(str(t).strip()) >= 2] or _termos_do_claude(nome, filtros()["idioma"])
    con = _db()
    con.execute("""insert into nichos (nome, termos, criado) values (?,?,datetime('now','localtime'))
                   on conflict(nome) do update set termos=excluded.termos""",
                (nome, json.dumps(termos, ensure_ascii=False)))
    con.commit()
    con.close()
    return um_nicho(nome)


def refazer_termos(nome):
    """Pede ao Claude outros termos para um nicho que já existe (quando os achados vieram ruins)."""
    um_nicho(nome)
    return salvar_nicho(nome, _termos_do_claude(nome, filtros()["idioma"]))


def remover_nicho(nome):
    """Tira o nicho da lista. Os achados dele continuam onde estão."""
    con = _db()
    con.execute("delete from nichos where nome=?", (nome,))
    con.commit()
    con.close()


# ---------------- a nota ----------------
def _dias_desde(iso):
    try:
        nasceu = dt.datetime.strptime(iso[:10], "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    except (ValueError, TypeError):
        return None
    return max(0, (dt.datetime.now(dt.timezone.utc) - nasceu).days)


def _surto(vistas_video, inscritos):
    """Quantas vezes o vídeo passou da audiência do próprio canal. É o sinal mais forte de formato que pega."""
    return round(vistas_video / max(inscritos, 1), 2)


def _nota(surto, vistas_dia, idade_dias):
    """0 a 100: metade é o surto, 30% o ritmo do canal (views por dia desde que nasceu) e 20% ser jovem.

    Os dois primeiros em escala log, porque a cauda é enorme: surto de 20x e 200 mil views/dia valem a parte
    cheia; o dobro disso não vale o dobro de nota. O pedaço "jovem" cai reto até os ~18 meses.
    """
    s = min(1.0, math.log10(1 + max(surto, 0)) / math.log10(1 + SURTO_CHEIO))
    r = min(1.0, math.log10(1 + max(vistas_dia, 0)) / math.log10(1 + VISTAS_DIA_CHEIO))
    j = max(0.0, 1 - (JOVEM_DIAS if idade_dias is None else idade_dias) / JOVEM_DIAS)
    return round(100 * (0.5 * s + 0.3 * r + 0.2 * j), 1)


def _passa(c, idade_dias, vistas_video, f):
    if f["idade_max_meses"] and (idade_dias is None or idade_dias > f["idade_max_meses"] * 30.4):
        return False
    if c["inscritos"] < f["inscritos_min"]:
        return False
    if f["inscritos_max"] and c["inscritos"] > f["inscritos_max"]:
        return False
    if vistas_video < f["vistas_min"]:
        return False
    return _surto(vistas_video, c["inscritos"]) >= f["surto_min"]


# ---------------- imagens (thumbnail do vídeo e logo do canal) ----------------
def _melhor(thumbs):
    for q in ("maxres", "standard", "high", "medium", "default"):
        if (thumbs.get(q) or {}).get("url"):
            return thumbs[q]["url"]
    return ""


def _baixar(url, destino):
    """Guarda a imagem que a própria resposta da API apontou. Sem ela, o card mostra um retângulo vazio."""
    if not url or destino.exists():
        return destino.name if destino.exists() else ""
    try:
        r = requests.get(url, timeout=20)
        if not r.ok or not r.headers.get("Content-Type", "").startswith("image/"):
            return ""
    except requests.RequestException:
        return ""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(r.content)
    return destino.name


def _baixar_tudo(linhas):
    """As imagens de uma vez, em paralelo: uma grade de 100 vídeos levaria minutos uma a uma.

    O logo é por CANAL, não por vídeo: baixar o mesmo arquivo em duas threads deixaria um jpg pela metade.
    """
    logos = {l["canal_id"]: l["_logo_url"] for l in linhas}
    with ThreadPoolExecutor(max_workers=8) as pool:
        thumbs = dict(zip([l["video_id"] for l in linhas], pool.map(
            lambda l: _baixar(l["_thumb_url"], THUMBS / f"{l['video_id']}.jpg"), linhas)))
        feitos = dict(zip(logos, pool.map(lambda cid: _baixar(logos[cid], CACHE / f"{cid}.jpg"), logos)))
    for l in linhas:
        l["thumb"] = thumbs.get(l["video_id"], "")
        l["canal_logo"] = feitos.get(l["canal_id"], "")
        l.pop("_thumb_url"), l.pop("_logo_url")
    return linhas


# ---------------- o garimpo ----------------
def _lotes(itens, n):
    itens = list(itens)
    return [itens[i:i + n] for i in range(0, len(itens), n)]


def _agora_utc(dias):
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")


def garimpar(nicho=None, filtros_pedidos=None):
    """Garimpa um nicho e devolve o resumo. Sem nicho, vale o que está há mais tempo sem ser garimpado."""
    ch = chave()
    if not ch:
        raise ValueError("Falta a chave da API do YouTube. Cole-a em Chaves › YouTube para o garimpo funcionar.")
    lista_nichos = nichos(por_rodizio=True)
    if not lista_nichos:
        raise ValueError("Escreva um nicho antes de garimpar (ex.: “arquitetura”).")
    n = um_nicho(nicho) if nicho else lista_nichos[0]
    f = {**filtros(), **(filtros_pedidos or {})}
    termos = n["termos"][:TERMOS_POR_NICHO]

    gasto, erro = 0, ""
    try:
        ids, de_termo = [], {}
        for termo in termos:
            p = dict(part="snippet", type="video", order="viewCount", q=termo,
                     maxResults=min(50, f["por_termo"]), publishedAfter=_agora_utc(f["dias"]))
            if f["pais"]:
                p["regionCode"] = f["pais"]
            if f["idioma"]:
                p["relevanceLanguage"] = f["idioma"]
            achados = _chamar(ch, "search", **p).get("items") or []
            gasto += CUSTO["search"]
            for it in achados:
                vid = (it.get("id") or {}).get("videoId")
                if vid and vid not in de_termo:
                    de_termo[vid] = termo
                    ids.append(vid)

        videos = {}
        for lote in _lotes(ids, 50):
            for v in _chamar(ch, "videos", part="snippet,statistics", id=",".join(lote)).get("items") or []:
                videos[v["id"]] = v
            gasto += CUSTO["videos"]

        canais_ids = {(v.get("snippet") or {}).get("channelId") for v in videos.values()} - {None}
        brutos = {}
        for lote in _lotes(canais_ids, 50):
            for c in _chamar(ch, "channels", part="snippet,statistics", id=",".join(lote)).get("items") or []:
                brutos[c["id"]] = c
            gasto += CUSTO["channels"]
    except ValueError as e:
        erro, videos, brutos, de_termo = str(e), {}, {}, {}
    finally:
        if gasto:
            _gastar(gasto)
        con = _db()
        con.execute("update nichos set ultimo=datetime('now','localtime') where nome=?", (n["nome"],))
        con.commit()
        con.close()

    con = _db()
    fora = {l[0] for l in con.execute("select distinct canal_id from videos_minerados where situacao='descartado'")}
    ja = {l[0] for l in con.execute("select video_id from videos_minerados")}
    linhas = []
    for vid, v in videos.items():
        sn = v.get("snippet") or {}
        cid = sn.get("channelId")
        bruto = brutos.get(cid)
        if not bruto or cid in fora:
            continue
        c = _campos(bruto)
        vistas = int((v.get("statistics") or {}).get("viewCount") or 0)
        nasceu = ((bruto.get("snippet") or {}).get("publishedAt") or "")[:10]
        idade = _dias_desde(nasceu)
        if not _passa(c, idade, vistas, f):
            continue
        surto = _surto(vistas, c["inscritos"])
        vistas_dia = round(c["vistas"] / max(idade or 1, 1), 1)
        linhas.append({
            "video_id": vid, "titulo": (sn.get("title") or "")[:300], "vistas": vistas,
            "publicado": (sn.get("publishedAt") or "")[:10], "canal_id": cid, "canal_nome": c["nome"],
            "canal_handle": c["handle"], "canal_url": c["url"], "canal_pais": c["pais"],
            "inscritos": c["inscritos"], "canal_videos": c["videos"], "canal_vistas": c["vistas"],
            "nasceu": nasceu, "idade_dias": idade or 0, "surto": surto, "vistas_dia": vistas_dia,
            "nota": _nota(surto, vistas_dia, idade), "nicho": n["nome"], "termo": de_termo.get(vid, ""),
            "_thumb_url": _melhor(sn.get("thumbnails") or {}), "_logo_url": c["_logo_url"],
        })
    _baixar_tudo(linhas)
    for l in linhas:
        con.execute("""insert into videos_minerados (video_id, titulo, thumb, vistas, publicado, canal_id,
                       canal_nome, canal_handle, canal_url, canal_logo, canal_pais, inscritos, canal_videos,
                       canal_vistas, nasceu, idade_dias, surto, vistas_dia, nota, nicho, termo, situacao, notas,
                       achado, atualizado)
                       values (:video_id,:titulo,:thumb,:vistas,:publicado,:canal_id,:canal_nome,:canal_handle,
                       :canal_url,:canal_logo,:canal_pais,:inscritos,:canal_videos,:canal_vistas,:nasceu,
                       :idade_dias,:surto,:vistas_dia,:nota,:nicho,:termo,'novo','',
                       datetime('now','localtime'),datetime('now','localtime'))
                       on conflict(video_id) do update set titulo=excluded.titulo, thumb=excluded.thumb,
                       vistas=excluded.vistas, canal_nome=excluded.canal_nome, canal_logo=excluded.canal_logo,
                       inscritos=excluded.inscritos, canal_videos=excluded.canal_videos,
                       canal_vistas=excluded.canal_vistas, idade_dias=excluded.idade_dias, surto=excluded.surto,
                       vistas_dia=excluded.vistas_dia, nota=excluded.nota, atualizado=excluded.atualizado""", l)
    novos = sum(1 for l in linhas if l["video_id"] not in ja)
    con.execute("""insert into garimpos (quando, veios, olhados, aprovados, novos, cota, erro)
                   values (datetime('now','localtime'),?,?,?,?,?,?)""",
                (len(termos), len(videos), len(linhas), novos, gasto, erro))
    con.commit()
    con.close()
    if erro and not linhas:
        raise ValueError(erro)
    return {"nicho": n["nome"], "termos": len(termos), "olhados": len(videos), "aprovados": len(linhas),
            "novos": novos, "cota": gasto, "erro": erro}


def ultimo_garimpo():
    con = _db()
    lin = con.execute("select quando, veios, olhados, aprovados, novos, cota, erro from garimpos "
                      "order by id desc limit 1").fetchone()
    con.close()
    if not lin:
        return None
    return dict(zip(["quando", "termos", "olhados", "aprovados", "novos", "cota", "erro"], lin))


def garimpar_atras_das_cortinas():
    """O garimpo do dia: se o último foi há mais de 20 h e existe nicho, roda numa thread (ninguém espera)."""
    if not automatico() or not chave() or not nichos():
        return
    u = ultimo_garimpo()
    if u and u["quando"]:
        try:
            passou = (dt.datetime.now() - dt.datetime.strptime(u["quando"], "%Y-%m-%d %H:%M:%S")).total_seconds()
        except ValueError:
            passou = VALIDADE_AUTOMATICO + 1
        if passou < VALIDADE_AUTOMATICO:
            return
    if cota()["sobra"] < CUSTO["search"] * TERMOS_POR_NICHO:
        return
    if not _trava_automatico.acquire(blocking=False):
        return

    def rodar():
        try:
            garimpar()
        except Exception:
            pass        # garimpo automático que falha não atrapalha o painel; o erro fica no log de garimpos
        finally:
            _trava_automatico.release()

    threading.Thread(target=rodar, daemon=True).start()


# ---------------- a grade do painel ----------------
NOMES = ["id", "video_id", "titulo", "thumb", "vistas", "publicado", "canal_id", "canal_nome", "canal_handle",
         "canal_url", "canal_logo", "canal_pais", "inscritos", "canal_videos", "canal_vistas", "nasceu",
         "idade_dias", "surto", "vistas_dia", "nota", "nicho", "termo", "situacao", "notas", "achado",
         "atualizado"]
SELECT = f"select {', '.join(NOMES)} from videos_minerados"
ORDENS = {"nota": "nota desc, vistas desc", "surto": "surto desc, vistas desc",
          "vistas": "vistas desc", "novo": "publicado desc, vistas desc"}


def _ler(lin):
    d = dict(zip(NOMES, lin))
    d["tem_thumb"] = bool(d["thumb"]) and (THUMBS / d["thumb"]).exists()
    d["tem_logo"] = bool(d["canal_logo"]) and (CACHE / d["canal_logo"]).exists()
    d["meses"] = round((d["idade_dias"] or 0) / 30.4, 1)
    d["video_url"] = f"https://www.youtube.com/watch?v={d['video_id']}"
    return d


def lista(situacao="novo", nicho="", ordem="nota"):
    con = _db()
    onde, args = ["situacao=?"], [situacao if situacao in SITUACOES else "novo"]
    if nicho:
        onde.append("nicho=?")
        args.append(nicho)
    out = [_ler(l) for l in con.execute(
        f"{SELECT} where {' and '.join(onde)} order by {ORDENS.get(ordem, ORDENS['nota'])}", args)]
    con.close()
    return out


def contas(nicho=""):
    con = _db()
    sql = "select situacao, count(*) from videos_minerados"
    args = ()
    if nicho:
        sql += " where nicho=?"
        args = (nicho,)
    c = dict(con.execute(sql + " group by situacao", args))
    con.close()
    return {s: c.get(s, 0) for s in SITUACOES}


def um(ref_id):
    con = _db()
    lin = con.execute(f"{SELECT} where id=?", (ref_id,)).fetchone()
    con.close()
    if not lin:
        raise ValueError("esse vídeo não está na mineração")
    return _ler(lin)


def descartar(ref_id):
    """Descarta o CANAL inteiro: os outros vídeos dele somem junto e ele não volta em garimpo nenhum."""
    v = um(ref_id)
    con = _db()
    con.execute("update videos_minerados set situacao='descartado' where canal_id=?", (v["canal_id"],))
    con.commit()
    con.close()


def voltar(ref_id):
    v = um(ref_id)
    con = _db()
    con.execute("update videos_minerados set situacao='novo' where canal_id=? and situacao='descartado'",
                (v["canal_id"],))
    con.commit()
    con.close()


def promover(ref_id):
    """Manda o canal do vídeo para a Modelagem (modelar.py) e marca aqui que ele já virou modelo."""
    v = um(ref_id)
    item = modelar.adicionar(v["canal_url"])
    con = _db()
    con.execute("update videos_minerados set situacao='modelo' where canal_id=? and situacao='novo'",
                (v["canal_id"],))
    con.commit()
    con.close()
    return item


def salvar_notas(ref_id, notas):
    um(ref_id)
    con = _db()
    con.execute("update videos_minerados set notas=? where id=?", ((notas or "").strip()[:2000], ref_id))
    con.commit()
    con.close()


def remover(ref_id):
    v = um(ref_id)
    con = _db()
    con.execute("delete from videos_minerados where id=?", (ref_id,))
    con.commit()
    con.close()
    if v["thumb"]:
        (THUMBS / v["thumb"]).unlink(missing_ok=True)


def arquivo_thumb(ref_id):
    v = um(ref_id)
    arq = THUMBS / v["thumb"] if v["thumb"] else None
    return arq if arq and arq.exists() else None


def arquivo_logo(ref_id):
    v = um(ref_id)
    arq = CACHE / v["canal_logo"] if v["canal_logo"] else None
    return arq if arq and arq.exists() else None


def estado(situacao="novo", nicho="", ordem="nota"):
    """Tudo o que a tela da Mineração precisa num pedido só."""
    return {"itens": lista(situacao, nicho, ordem), "situacao": situacao, "nicho": nicho, "ordem": ordem,
            "contas": contas(nicho), "nichos": nichos(), "filtros": filtros(), "padroes": FILTROS,
            "cota": cota(), "ultimo": ultimo_garimpo(), "automatico": automatico(), "tem_chave": bool(chave()),
            "custo_nicho": CUSTO["search"] * TERMOS_POR_NICHO, "ordens": list(ORDENS),
            "canais": [{"slug": s, "nome": c["nome"], "tema": c["tema"]} for s, c in canais().items()]}
