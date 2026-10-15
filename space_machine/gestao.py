"""Gestão do canal: colunas do quadro de produção, ideias, calendário de publicação e criação de vídeos novos.

O andamento da produção vem das pastas (estado.py). O que não está nas pastas (ideia, título/descrição/tags de
publicação, data, "agendado"/"publicado", link) fica em <dados>/space_machine.sqlite. Upload pelo sistema: não (2026-10-11) — sobe-se no YouTube
Studio e marca aqui.
"""
import calendar
import datetime as dt
import re
import unicodedata
from pathlib import Path

from . import estado
from .motor_claude import _banco
from .sistema import gravar_json

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


def slug_video(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60]


def criar_video(c, titulo, roteiro):
    """Cria a pasta do vídeo e um bloco por tópico (00 = cold open). Devolve o slug; ValueError com o motivo
    (para mostrar a quem produz) se não der."""
    cold_open, partes = dividir_roteiro(roteiro)
    if not titulo.strip():
        raise ValueError("Dê um título ao vídeo.")
    if not partes:
        raise ValueError("O roteiro precisa ter cada tópico começando com uma linha \"# Nome do tópico\".")
    vd = Path(c["producoes"]) / slug_video(titulo)
    if not slug_video(titulo):
        raise ValueError("O título precisa ter letras ou números.")
    if vd.exists():
        raise ValueError(f"Já existe um vídeo com essa pasta ({vd.name}).")
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
    return vd.name
