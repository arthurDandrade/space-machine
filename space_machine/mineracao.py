"""Mineração de canais: garimpa no YouTube canais novos que estão estourando, para você ver o que dá certo.

Fica em <dados>/space_machine.sqlite (tabelas veios, canais_minerados, garimpos, cota_youtube) e os logos em
<dados>/cache/mineracao/. O canal que te interessar vai para a Modelagem com um clique (modelar.py).

Como garimpa, pela API oficial do YouTube (chave YOUTUBE_API_KEY em <dados>/.env, no painel em Chaves › YouTube):
  1. search.list  de cada veio (termo de busca), order=viewCount, só vídeos dos últimos N dias → 100 unidades
  2. videos.list   em lotes de 50, para as views de verdade e o canal de cada vídeo          → 1 unidade
  3. channels.list em lotes de 50, para inscritos, total de vídeos e a data de nascimento    → 1 unidade
Um garimpo de 5 veios custa ~510 das 10.000 unidades por dia da chave: dá uns 19 garimpos por dia.

A regra de 2026-10-11 continua valendo para a PRODUÇÃO inteira: nenhum script da produção toca no YouTube. Isto
aqui é pesquisa de canal pela API com chave, no botão do painel (ou um garimpo por dia, se você deixar ligado):
nada abre página, raspa busca nem baixa mídia — só o JSON da API e o logo que ela mesma devolve. A decisão de
ampliar a exceção do modelar.py para cá é de 2026-10-26 e está escrita no CLAUDE.md.
"""
import datetime as dt
import json
import math
import re
import threading

from . import modelar, motor_claude
from .modelar import _campos, _chamar, _guardar_logo, chave
from .motor_claude import _banco, canais
from .sistema import DADOS, config, salvar_config

CACHE = DADOS / "cache" / "mineracao"

# o que cada chamada da API tira da cota de 10.000 unidades por dia
CUSTO = {"search": 100, "videos": 1, "channels": 1}
COTA_DIA = 10000
MAX_VEIOS_POR_GARIMPO = 12          # 12 veios = 1.200 unidades, um sexto da cota do dia

# o que é "canal novo estourando". O painel manda os seus; estes são os padrões de fábrica.
FILTROS = {
    "dias": 90,                 # só vídeos publicados nos últimos N dias
    "idade_max_meses": 18,      # o canal nasceu no máximo há isso (0 = sem limite)
    "inscritos_min": 1000,      # abaixo disso é canal parado, não canal estourando
    "inscritos_max": 500000,    # acima disso já é canal grande (0 = sem limite)
    "vistas_min": 50000,        # o vídeo achado fez pelo menos isso de views
    "surto_min": 1.0,           # views do vídeo ÷ inscritos do canal
    "pais": "",                 # regionCode da busca (vazio = sem filtro)
    "idioma": "",               # relevanceLanguage da busca
    "por_veio": 50,             # quantos vídeos trazer de cada veio (50 é o máximo da API)
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
    con.execute("""create table if not exists veios (
        id integer primary key, termo text unique, canal text, origem text, ativo int, criado text)""")
    con.execute("""create table if not exists canais_minerados (
        id integer primary key, canal_id text unique, url text, nome text, handle text, descricao text,
        pais text, logo text, inscritos int, videos int, vistas int, nasceu text, idade_dias int,
        surto real, vistas_dia real, nota real, video_titulo text, video_url text, video_vistas int,
        video_quando text, de_veio text, situacao text, notas text, achado text, atualizado text)""")
    con.execute("""create table if not exists garimpos (
        id integer primary key, quando text, veios int, olhados int, aprovados int, novos int, cota int,
        erro text)""")
    con.execute("""create table if not exists cota_youtube (dia text primary key, unidades int)""")
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
    limpos["por_veio"] = min(50, limpos.get("por_veio") or FILTROS["por_veio"])
    limpos["dias"] = min(365, max(1, limpos.get("dias") or FILTROS["dias"]))
    salvar_config({"mineracao": {"filtros": limpos}})
    return filtros()


def automatico():
    return bool((config().get("mineracao") or {}).get("automatica", True))


def salvar_automatico(ligado):
    salvar_config({"mineracao": {"automatica": bool(ligado)}})
    return automatico()


# ---------------- veios (os termos de busca) ----------------
def _ler_veio(lin):
    return dict(zip(["id", "termo", "canal", "origem", "ativo", "criado"], lin))


def veios(so_ativos=False):
    con = _db()
    sql = "select id, termo, canal, origem, ativo, criado from veios"
    if so_ativos:
        sql += " where ativo=1"
    out = [_ler_veio(l) for l in con.execute(sql + " order by ativo desc, termo")]
    con.close()
    return out


def salvar_veio(termo, canal="", origem="voce"):
    """Guarda um termo de busca. Termo repetido não duplica: só volta a ficar ativo."""
    termo = re.sub(r"\s+", " ", (termo or "")).strip()[:120]
    if len(termo) < 2:
        raise ValueError("Escreva o termo de busca (ex.: “history explained”).")
    con = _db()
    con.execute("""insert into veios (termo, canal, origem, ativo, criado)
                   values (?,?,?,1,datetime('now','localtime'))
                   on conflict(termo) do update set ativo=1, canal=excluded.canal""",
                (termo, canal or "", origem if origem in ("voce", "claude") else "voce"))
    con.commit()
    con.close()
    return [v for v in veios() if v["termo"] == termo][0]


def alternar_veio(ref_id, ativo):
    con = _db()
    con.execute("update veios set ativo=? where id=?", (1 if ativo else 0, ref_id))
    con.commit()
    con.close()


def remover_veio(ref_id):
    con = _db()
    con.execute("delete from veios where id=?", (ref_id,))
    con.commit()
    con.close()


def sugerir_veios(slug):
    """Termos de busca que o Claude tira do tema, do idioma e do formato DESTE canal (nada vai à rede do YouTube)."""
    c = canais().get(slug)
    if not c:
        raise ValueError("esse canal não existe")
    sistema = ("Você ajuda a garimpar canais do YouTube parecidos com o canal descrito. Responda só o JSON pedido, "
               "com termos de busca curtos (2 a 5 palavras) no IDIOMA do canal, do jeito que o público digitaria "
               "na busca do YouTube. Misture o tema com a cara do formato e com temas vizinhos do mesmo público. "
               "Nada de nome de canal, de hashtag nem de aspas.")
    texto = json.dumps({"canal": c["nome"], "tema": c["tema"], "idioma": c["idioma"], "formato": c["formato"],
                        "quantos": 10}, ensure_ascii=False)
    schema = {"type": "object", "properties": {"termos": {"type": "array", "items": {"type": "string"}}},
              "required": ["termos"]}
    r = motor_claude.chamar("termos_mineracao", sistema, texto, schema=schema, ctx={"canal": slug}, canal=c)
    termos, vistos = [], {v["termo"].lower() for v in veios()}
    for t in (r.get("termos") or [])[:14]:
        t = re.sub(r"\s+", " ", str(t)).strip().strip('"#')[:120]
        if len(t) >= 2 and t.lower() not in vistos:
            vistos.add(t.lower())
            termos.append(t)
    return termos


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


# ---------------- o garimpo ----------------
def _lotes(itens, n):
    itens = list(itens)
    return [itens[i:i + n] for i in range(0, len(itens), n)]


def _agora_utc(dias):
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")


def garimpar(termos=None, filtros_pedidos=None):
    """Um garimpo: busca, filtra, pontua e guarda. Devolve o resumo (quantos olhou, aprovou e quanto custou).

    termos: lista de termos só desta vez; sem ela, valem os veios ativos. Canal já descartado por você não volta.
    """
    ch = chave()
    if not ch:
        raise ValueError("Falta a chave da API do YouTube. Cole-a em Chaves › YouTube para o garimpo funcionar.")
    f = {**filtros(), **(filtros_pedidos or {})}
    lista = [re.sub(r"\s+", " ", str(t)).strip() for t in
             (termos if termos is not None else [v["termo"] for v in veios(so_ativos=True)])]
    lista = [t for t in lista if len(t) >= 2][:MAX_VEIOS_POR_GARIMPO]
    if not lista:
        raise ValueError("Cadastre pelo menos um veio (um termo de busca) e deixe-o ligado antes de garimpar.")

    gasto, erro = 0, ""
    try:
        ids, de_veio = [], {}
        for termo in lista:
            p = dict(part="snippet", type="video", order="viewCount", q=termo,
                     maxResults=min(50, f["por_veio"]), publishedAfter=_agora_utc(f["dias"]))
            if f["pais"]:
                p["regionCode"] = f["pais"]
            if f["idioma"]:
                p["relevanceLanguage"] = f["idioma"]
            achados = _chamar(ch, "search", **p).get("items") or []
            gasto += CUSTO["search"]
            for it in achados:
                vid = (it.get("id") or {}).get("videoId")
                if vid and vid not in de_veio:
                    de_veio[vid] = termo
                    ids.append(vid)

        videos = {}
        for lote in _lotes(ids, 50):
            for v in _chamar(ch, "videos", part="snippet,statistics", id=",".join(lote)).get("items") or []:
                videos[v["id"]] = v
            gasto += CUSTO["videos"]

        # um canal pode aparecer em vários vídeos: vale o que fez mais views
        melhor = {}
        for vid, v in videos.items():
            cid = (v.get("snippet") or {}).get("channelId")
            vistas = int((v.get("statistics") or {}).get("viewCount") or 0)
            if cid and (cid not in melhor or vistas > melhor[cid][1]):
                melhor[cid] = (vid, vistas)

        brutos = {}
        for lote in _lotes(melhor, 50):
            for c in _chamar(ch, "channels", part="snippet,statistics", id=",".join(lote)).get("items") or []:
                brutos[c["id"]] = c
            gasto += CUSTO["channels"]
    except ValueError as e:
        erro = str(e)
        brutos, melhor, videos, de_veio = {}, {}, {}, {}
    finally:
        if gasto:
            _gastar(gasto)

    con = _db()
    fora = {l[0] for l in con.execute("select canal_id from canais_minerados where situacao!='novo'")}
    ja = {l[0] for l in con.execute("select canal_id from canais_minerados")}
    aprovados, novos = 0, 0
    for cid, bruto in brutos.items():
        if cid in fora:
            continue
        c = _campos(bruto)
        nasceu = ((bruto.get("snippet") or {}).get("publishedAt") or "")[:10]
        idade = _dias_desde(nasceu)
        vid, vistas_video = melhor[cid]
        if not _passa(c, idade, vistas_video, f):
            continue
        sn = videos[vid].get("snippet") or {}
        surto = _surto(vistas_video, c["inscritos"])
        vistas_dia = round(c["vistas"] / max(idade or 1, 1), 1)
        linha = {
            **{k: v for k, v in c.items() if k != "_logo_url"},
            "logo": _guardar_logo(cid, c["_logo_url"], CACHE),
            "nasceu": nasceu, "idade_dias": idade or 0, "surto": surto, "vistas_dia": vistas_dia,
            "nota": _nota(surto, vistas_dia, idade), "video_titulo": (sn.get("title") or "")[:300],
            "video_url": f"https://www.youtube.com/watch?v={vid}", "video_vistas": vistas_video,
            "video_quando": (sn.get("publishedAt") or "")[:10], "de_veio": de_veio.get(vid, ""),
        }
        con.execute("""insert into canais_minerados (canal_id, url, nome, handle, descricao, pais, logo, inscritos,
                       videos, vistas, nasceu, idade_dias, surto, vistas_dia, nota, video_titulo, video_url,
                       video_vistas, video_quando, de_veio, situacao, notas, achado, atualizado)
                       values (:canal_id,:url,:nome,:handle,:descricao,:pais,:logo,:inscritos,:videos,:vistas,
                       :nasceu,:idade_dias,:surto,:vistas_dia,:nota,:video_titulo,:video_url,:video_vistas,
                       :video_quando,:de_veio,'novo','',datetime('now','localtime'),datetime('now','localtime'))
                       on conflict(canal_id) do update set nome=excluded.nome, handle=excluded.handle,
                       url=excluded.url, descricao=excluded.descricao, logo=excluded.logo,
                       inscritos=excluded.inscritos, videos=excluded.videos, vistas=excluded.vistas,
                       idade_dias=excluded.idade_dias, surto=excluded.surto, vistas_dia=excluded.vistas_dia,
                       nota=excluded.nota, video_titulo=excluded.video_titulo, video_url=excluded.video_url,
                       video_vistas=excluded.video_vistas, video_quando=excluded.video_quando,
                       de_veio=excluded.de_veio, atualizado=excluded.atualizado""", linha)
        aprovados += 1
        novos += cid not in ja
    con.execute("""insert into garimpos (quando, veios, olhados, aprovados, novos, cota, erro)
                   values (datetime('now','localtime'),?,?,?,?,?,?)""",
                (len(lista), len(brutos), aprovados, novos, gasto, erro))
    con.commit()
    con.close()
    if erro and not aprovados:
        raise ValueError(erro)
    return {"veios": len(lista), "olhados": len(brutos), "aprovados": aprovados, "novos": novos,
            "cota": gasto, "erro": erro}


def ultimo_garimpo():
    con = _db()
    lin = con.execute("select quando, veios, olhados, aprovados, novos, cota, erro from garimpos "
                      "order by id desc limit 1").fetchone()
    con.close()
    if not lin:
        return None
    return dict(zip(["quando", "veios", "olhados", "aprovados", "novos", "cota", "erro"], lin))


def garimpar_atras_das_cortinas():
    """O garimpo do dia: se o último foi há mais de 20 h e há veios ligados, roda numa thread (ninguém espera)."""
    if not automatico() or not chave() or not veios(so_ativos=True):
        return
    u = ultimo_garimpo()
    if u and u["quando"]:
        try:
            passou = (dt.datetime.now() - dt.datetime.strptime(u["quando"], "%Y-%m-%d %H:%M:%S")).total_seconds()
        except ValueError:
            passou = VALIDADE_AUTOMATICO + 1
        if passou < VALIDADE_AUTOMATICO:
            return
    if cota()["sobra"] < CUSTO["search"] * len(veios(so_ativos=True)):
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


# ---------------- a lista do painel ----------------
NOMES = ["id", "canal_id", "url", "nome", "handle", "descricao", "pais", "logo", "inscritos", "videos", "vistas",
         "nasceu", "idade_dias", "surto", "vistas_dia", "nota", "video_titulo", "video_url", "video_vistas",
         "video_quando", "de_veio", "situacao", "notas", "achado", "atualizado"]
SELECT = f"select {', '.join(NOMES)} from canais_minerados"


def _ler(lin):
    d = dict(zip(NOMES, lin))
    d["tem_logo"] = bool(d["logo"]) and (CACHE / d["logo"]).exists()
    d["meses"] = round((d["idade_dias"] or 0) / 30.4, 1)
    return d


def lista(situacao="novo"):
    con = _db()
    sql = f"{SELECT} where situacao=?" if situacao in SITUACOES else SELECT
    args = (situacao,) if situacao in SITUACOES else ()
    out = [_ler(l) for l in con.execute(sql + " order by nota desc, video_vistas desc", args)]
    con.close()
    return out


def contas():
    con = _db()
    c = dict(con.execute("select situacao, count(*) from canais_minerados group by situacao"))
    con.close()
    return {s: c.get(s, 0) for s in SITUACOES}


def um(ref_id):
    con = _db()
    lin = con.execute(f"{SELECT} where id=?", (ref_id,)).fetchone()
    con.close()
    if not lin:
        raise ValueError("esse canal não está na mineração")
    return _ler(lin)


def _situacao(ref_id, situacao):
    um(ref_id)
    con = _db()
    con.execute("update canais_minerados set situacao=? where id=?", (situacao, ref_id))
    con.commit()
    con.close()


def descartar(ref_id):
    """Sai da lista e não volta em garimpo nenhum (é assim que a lista fica limpa com o tempo)."""
    _situacao(ref_id, "descartado")


def voltar(ref_id):
    _situacao(ref_id, "novo")


def promover(ref_id):
    """Manda o canal para a Modelagem (modelar.py) e marca aqui que ele já virou modelo."""
    c = um(ref_id)
    item = modelar.adicionar(c["url"])
    _situacao(ref_id, "modelo")
    return item


def salvar_notas(ref_id, notas):
    um(ref_id)
    con = _db()
    con.execute("update canais_minerados set notas=? where id=?", ((notas or "").strip()[:2000], ref_id))
    con.commit()
    con.close()


def remover(ref_id):
    c = um(ref_id)
    con = _db()
    con.execute("delete from canais_minerados where id=?", (ref_id,))
    con.commit()
    con.close()
    if c["logo"]:
        (CACHE / c["logo"]).unlink(missing_ok=True)


def arquivo_logo(ref_id):
    c = um(ref_id)
    arq = CACHE / c["logo"] if c["logo"] else None
    return arq if arq and arq.exists() else None


def estado():
    """Tudo o que a tela da Mineração precisa num pedido só."""
    return {"itens": lista("novo"), "contas": contas(), "veios": veios(), "filtros": filtros(),
            "padroes": FILTROS, "cota": cota(), "ultimo": ultimo_garimpo(), "automatico": automatico(),
            "tem_chave": bool(chave()), "custo_busca": CUSTO["search"],
            "canais": [{"slug": s, "nome": c["nome"], "tema": c["tema"]} for s, c in canais().items()]}
