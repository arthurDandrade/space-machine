"""Gestão do canal (Fase 4): kanban de produção, ideias e calendário de publicação.

O andamento da produção vem das pastas (estado.py). O que não está nas pastas (ideia, título/descrição/tags de
publicação, data, "agendado"/"publicado", link) fica em dados/estudio.sqlite. Upload pelo sistema: não, por decisão
do Arthur (2026-10-11) — ele sobe no YouTube Studio e marca aqui.
"""
import calendar
import datetime as dt

from . import estado
from .motor_claude import _banco

COLUNAS = [
    ("ideia", "Ideias"),
    ("roteiro", "Roteiro"),
    ("producao", "Produção"),
    ("edicao_final", "Edição final"),
    ("agendado", "Agendado"),
    ("publicado", "Publicado"),
]
MANUAIS = {"edicao_final", "agendado", "publicado"}


def _db():
    con = _banco()
    con.execute("""create table if not exists videos_gestao (
        canal text, slug text, status text, titulo_pub text, descricao text, tags text, data_pub text,
        notas text, link text, atualizado text, primary key (canal, slug))""")
    con.execute("""create table if not exists ideias (
        id integer primary key, canal text, titulo text, notas text, criado text)""")
    return con


def dados_video(canal, slug):
    con = _db()
    lin = con.execute("select status, titulo_pub, descricao, tags, data_pub, notas, link, atualizado "
                      "from videos_gestao where canal=? and slug=?", (canal, slug)).fetchone()
    con.close()
    campos = ["status", "titulo_pub", "descricao", "tags", "data_pub", "notas", "link", "atualizado"]
    return dict(zip(campos, lin)) if lin else {c: "" for c in campos}


def salvar_video(canal, slug, **campos):
    atual = dados_video(canal, slug)
    atual.update({k: (v or "").strip() for k, v in campos.items()})
    con = _db()
    con.execute("""insert into videos_gestao (canal, slug, status, titulo_pub, descricao, tags, data_pub, notas, link,
                   atualizado) values (?,?,?,?,?,?,?,?,?,datetime('now','localtime'))
                   on conflict(canal, slug) do update set status=excluded.status, titulo_pub=excluded.titulo_pub,
                   descricao=excluded.descricao, tags=excluded.tags, data_pub=excluded.data_pub,
                   notas=excluded.notas, link=excluded.link, atualizado=excluded.atualizado""",
                (canal, slug, atual["status"], atual["titulo_pub"], atual["descricao"], atual["tags"],
                 atual["data_pub"], atual["notas"], atual["link"]))
    con.commit()
    con.close()


def coluna_do_video(v, g):
    """Status manual (edição final / agendado / publicado) vale; senão, deriva dos blocos."""
    if g.get("status") in MANUAIS:
        return g["status"]
    if v["n_blocos"] and v["entregues"] == v["n_blocos"]:
        return "edicao_final"
    if any(b["atual"] != "roteiro" for b in v["blocos"]):
        return "producao"
    return "roteiro"


def ideias(canal):
    con = _db()
    out = [{"id": i, "titulo": t, "notas": n, "criado": c} for i, t, n, c in
           con.execute("select id, titulo, notas, criado from ideias where canal=? order by id desc", (canal,))]
    con.close()
    return out


def nova_ideia(canal, titulo, notas=""):
    con = _db()
    con.execute("insert into ideias (canal, titulo, notas, criado) values (?,?,?,datetime('now','localtime'))",
                (canal, titulo.strip(), notas.strip()))
    con.commit()
    con.close()


def apagar_ideia(canal, ideia_id):
    con = _db()
    con.execute("delete from ideias where canal=? and id=?", (canal, ideia_id))
    con.commit()
    con.close()


def quadro(canal):
    """{coluna: [cards]} do kanban de produção do canal."""
    cols = {c: [] for c, _ in COLUNAS}
    for i in ideias(canal):
        cols["ideia"].append({"tipo": "ideia", **i})
    for v in estado.videos(canal):
        g = dados_video(canal, v["slug"])
        cols[coluna_do_video(v, g)].append({"tipo": "video", "v": v, "g": g})
    return cols


def calendario(canal, ano, mes):
    """Semanas do mês (segunda a domingo), cada dia com os vídeos de data_pub nele."""
    por_dia = {}
    for v in estado.videos(canal):
        g = dados_video(canal, v["slug"])
        if g.get("data_pub"):
            por_dia.setdefault(g["data_pub"][:10], []).append({"v": v, "g": g, "coluna": coluna_do_video(v, g)})
    semanas = []
    for semana in calendar.Calendar(firstweekday=0).monthdatescalendar(ano, mes):
        semanas.append([{"data": d, "no_mes": d.month == mes, "hoje": d == dt.date.today(),
                         "videos": por_dia.get(d.isoformat(), [])} for d in semana])
    sem_data = [v for v in estado.videos(canal) if not dados_video(canal, v["slug"]).get("data_pub")]
    return semanas, sem_data
