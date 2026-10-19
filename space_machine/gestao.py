"""Gestão do canal: colunas do quadro de produção, ideias, calendário de publicação e criação de vídeos novos.

O andamento da produção vem das pastas (estado.py). O que não está nas pastas (ideia, título/descrição/tags de
publicação, data, "agendado"/"publicado", link) fica em <dados>/space_machine.sqlite. Upload pelo sistema: não (2026-10-11) — sobe-se no YouTube
Studio e marca aqui.
"""
import calendar
import datetime as dt
import re
import subprocess
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


def ideia_virou_video(canal, ideia_id, slug):
    """A ideia que virou vídeo sai da lista; as notas dela vão para as notas do vídeo (aba Publicação).
    A ideia é a do "Virar vídeo" (ideia_id); sem ela, a que tem o mesmo título do vídeo criado."""
    con = _db()
    todas = con.execute("select id, titulo, notas from ideias where canal=?", (canal,)).fetchall()
    con.close()
    ideia = next((i for i in todas if i[0] == ideia_id), None) or \
        next((i for i in todas if slug_video(i[1]) == slug), None)
    if not ideia:
        return
    if (ideia[2] or "").strip() and not dados_video(canal, slug)["notas"]:
        salvar_video(canal, slug, notas=ideia[2])
    apagar_ideia(canal, ideia[0])


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


# ---------------- descrição do YouTube ----------------
def _duracao(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                       capture_output=True, text=True, timeout=60)
    return float(r.stdout.strip())


def _minutagem(s):
    s = int(s)
    h, m, s = s // 3600, s // 60 % 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def capitulos(vd, intro="Intro"):
    """Capítulos do YouTube tirados do vídeo final: o final.py põe os blocos entregues (final.entregues) um depois
    do outro, sem corte nem sobreposição, então cada capítulo começa na soma das durações dos anteriores
    (conferido em 2026-10-16: a soma dos bloco N.mp4 deu os mesmos 909,45 s do final renderizado).
    Nome = linha "# Nome" do roteiro do bloco; o cold open vira `intro`. Devolve [(segundos, nome)]."""
    from .final import _numero, entregues
    out, t = [], 0.0
    for mp4 in entregues(vd):
        rot = Path(vd) / "blocos" / f"{_numero(mp4):02d}" / "roteiro.txt"
        linhas = rot.read_text().splitlines() if rot.exists() else []
        m = re.match(r"^\s*#+\s*(.+?)\s*$", linhas[0]) if linhas else None
        cold = any(l.strip() == MARCA_COLD_OPEN for l in linhas[:3])
        out.append((t, intro if cold or not m else m.group(1).rstrip(".:").strip()))
        t += _duracao(mp4)
    return out


def gerar_descricao(c, slug, video):
    """Descrição pronta para o YouTube: resumo (Claude, no idioma do canal) + capítulos com minutagem do vídeo
    final + convite para seguir o canal. Nada é salvo (o texto vai para o campo e a pessoa salva).
    Devolve {"descricao", "avisos"}; ErroClaude se o Claude falhar."""
    from .final import entregues
    from .motor_claude import chamar, prompt
    from .sistema import config
    vd = Path(c["producoes"]) / video
    titulo = dados_video(slug, video).get("titulo_pub") or estado.titulo_video(vd)
    blocos = sorted(b for b in (vd / "blocos").glob("*") if b.is_dir() and b.name.isdigit()) \
        if (vd / "blocos").is_dir() else []
    roteiros = "\n\n".join(f"## Bloco {b.name}\n" + (b / "roteiro.txt").read_text().replace(MARCA_COLD_OPEN, "").strip()
                            for b in blocos if (b / "roteiro.txt").exists())
    schema = {"type": "object", "additionalProperties": False, "required": ["resumo", "intro", "cta"],
              "properties": {"resumo": {"type": "string"}, "intro": {"type": "string"}, "cta": {"type": "string"}}}
    r = chamar("descricao", prompt("descricao_youtube"),
               f"Título: {titulo}\nCanal: {c['nome']}\nIdioma: {c['idioma']}\n\n# Roteiros\n{roteiros}",
               schema=schema, modelo=config()["modelos"]["descricao"],
               ctx={"canal": slug, "video": video})
    avisos = []
    caps = capitulos(vd, r["intro"].strip() or "Intro")
    if not caps:
        avisos.append("Nenhum bloco entregue ainda: a descrição saiu sem capítulos.")
    elif len(entregues(vd)) < len(blocos):
        avisos.append(f"Só {len(entregues(vd))} de {len(blocos)} blocos entregues: os capítulos valem para o "
                      "vídeo final montado com esses blocos.")
    if caps and len(caps) < 3:
        avisos.append("O YouTube só mostra capítulos com pelo menos 3 deles.")
    partes = [r["resumo"].strip()]
    if caps:
        partes.append("\n".join(f"{_minutagem(t)} {nome}" for t, nome in caps))
    partes.append(r["cta"].strip())
    return {"descricao": "\n\n".join(p for p in partes if p), "avisos": avisos}


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


# ---------------- excluir (lixeira) ----------------
LIXEIRA = "_lixeira"      # <producoes>/_lixeira/<vídeo>__<quando>: o estado.videos ignora pastas com "_"


def _ocupado(vd):
    """Motivo para não mexer na pasta do vídeo agora (bloco rodando, fila ou vídeo final em andamento), ou ""."""
    from .fila import ler_fila
    if ler_fila(vd).get("ativa"):
        return "a fila deste vídeo está rodando: pare a fila antes"
    for pid in list(vd.glob("blocos/*/_estudio/pid")) + [vd / "final" / "pid"]:
        if pid.exists() and estado._vivo(pid.read_text().strip()):
            return "tem coisa rodando neste vídeo: pare antes"
    return ""


def excluir_video(c, slug):
    """Move o vídeo inteiro para a lixeira do canal (nada é apagado; dá para restaurar)."""
    prod = Path(c["producoes"])
    vd = prod / slug
    if not slug or slug.startswith((".", "_")) or "/" in slug or not vd.is_dir():
        raise ValueError("vídeo não encontrado")
    motivo = _ocupado(vd)
    if motivo:
        raise ValueError(motivo)
    destino = prod / LIXEIRA / f"{slug}__{dt.datetime.now():%Y%m%d-%H%M%S}"
    destino.parent.mkdir(exist_ok=True)
    vd.rename(destino)
    return destino.name


def excluir_bloco(c, video, nn):
    """Tira o bloco do vídeo de vez: a pasta <vídeo>/blocos/NN e o que ele já tinha entregue (o MP4 da edição e o
    do Reels) vão para o Lixo do Mac, como na Limpeza. Os outros blocos continuam com o número que têm — renumerar
    quebraria os .aep já montados e o que o roteiro diz de cada tópico."""
    from . import limpeza
    vd = Path(c["producoes"]) / video
    b = vd / "blocos" / nn
    if not nn.isdigit() or not b.is_dir():
        raise ValueError("bloco não encontrado")
    motivo = _ocupado(vd)
    if motivo:
        raise ValueError(motivo)
    itens = [(b, "bloco")]
    itens += [(f, "bloco") for f in (vd / "edicao" / f"bloco {int(nn)}.mp4", vd / "reels" / f"bloco {int(nn)}.mp4")
              if f.exists()]
    tamanho, quantos, destino = limpeza.mandar_para_o_lixo(itens)
    return {"quantos": quantos, "tamanho": tamanho, "lixo": destino.name}


def lixeira(c):
    pasta = Path(c["producoes"]) / LIXEIRA
    out = []
    for p in sorted(pasta.iterdir() if pasta.is_dir() else [], key=lambda p: p.stat().st_mtime, reverse=True):
        if not p.is_dir():
            continue
        slug, _, quando = p.name.rpartition("__")
        n = len([b for b in (p / "blocos").glob("*") if b.is_dir()]) if (p / "blocos").is_dir() else 0
        try:
            excluido = dt.datetime.strptime(quando, "%Y%m%d-%H%M%S").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            excluido = ""
        out.append({"nome": p.name, "video": slug or p.name, "titulo": estado.titulo_video(p), "n_blocos": n,
                    "excluido": excluido})
    return out


def restaurar_video(c, nome):
    """Devolve da lixeira; se já existe um vídeo com a mesma pasta, volta como <vídeo>-restaurado."""
    prod = Path(c["producoes"])
    src = prod / LIXEIRA / nome
    if "/" in nome or nome.startswith(".") or not src.is_dir():
        raise ValueError("não está na lixeira")
    slug = nome.rpartition("__")[0] or nome
    destino = prod / slug
    if destino.exists():
        destino = prod / f"{slug}-restaurado"
        if destino.exists():
            raise ValueError(f"já existe {destino.name}: renomeie a pasta antes")
    src.rename(destino)
    return destino.name
