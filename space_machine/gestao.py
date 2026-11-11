"""Gestão do canal: colunas do quadro de produção, ideias, calendário de publicação e criação de vídeos novos.

O andamento da produção vem das pastas (estado.py). O que é do vídeo e não da produção (título/descrição/tags de
publicação, data, "agendado"/"publicado", link) fica na ficha dele (fichas.py: <canal>/fichas/<vídeo>/); as ideias,
em <dados>/space_machine.sqlite. Upload pelo sistema: não (2026-10-11) — sobe-se no YouTube
Studio e marca aqui.
"""
import calendar
import datetime as dt
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from . import estado, fichas, prontos
from .motor_claude import _banco
from .sistema import arquivo_formato, ficha_formato, gravar_json, ler_json

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
    con.execute("""create table if not exists ideias (
        id integer primary key, canal text, titulo text, notas text, criado text)""")
    return con


CAMPOS_PUBLICACAO = fichas.PUBLICACAO


def _vd(canal, slug):
    from .sistema import canais
    return Path(canais()[canal]["producoes"]) / slug


def dados_video(canal, slug):
    """O que você preenche na aba Publicação. Fica na ficha do vídeo (fichas.py), não mais no sqlite."""
    ficha = fichas.ler(_vd(canal, slug))
    return {c: ficha.get(c) or "" for c in CAMPOS_PUBLICACAO}


def salvar_video(canal, slug, **campos):
    fichas.anotar(_vd(canal, slug), **{k: (v or "").strip() for k, v in campos.items()},
                  atualizado=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def coluna_do_video(v, g):
    """Status manual (edição final / agendado / publicado) vale; senão, deriva dos blocos."""
    if g.get("status") in MANUAIS:
        return g["status"]
    if v.get("arquivado"):          # arquivado sem status marcado: o vídeo estava pronto
        return "edicao_final"
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
    from .video import fluxo_video, pasta
    out, t = [], 0.0
    if fluxo_video(vd):
        # fluxo "video": o render_video.py escreve onde cada capítulo começa no vídeo final (producao/edicao/pedacos.json)
        caps = {c["nn"]: c for c in (ler_json(pasta(vd) / "capitulos.json", []) or [])}
        for p in ler_json(pasta(vd) / "edicao" / "pedacos.json", []) or []:
            c = caps.get(p["nn"], {})
            out.append((p["ini"], intro if c.get("tipo") == "cold_open" else c.get("nome", p["nn"]).rstrip(".:").strip()))
        return out
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
    vd = Path(c["producoes"]) / video
    titulo = dados_video(slug, video).get("titulo_pub") or estado.titulo_video(vd)
    blocos = sorted(b for b in (vd / "blocos").glob("*") if b.is_dir() and b.name.isdigit()) \
        if (vd / "blocos").is_dir() else []
    roteiros = "\n\n".join(f"## Bloco {b.name}\n" + (b / "roteiro.txt").read_text().replace(MARCA_COLD_OPEN, "").strip()
                            for b in blocos if (b / "roteiro.txt").exists())
    schema = {"type": "object", "additionalProperties": False, "required": ["resumo", "intro", "cta"],
              "properties": {"resumo": {"type": "string"}, "intro": {"type": "string"}, "cta": {"type": "string"}}}
    r = chamar("descricao", prompt("descricao_youtube", formato=c.get("formato")),
               f"Título: {titulo}\nCanal: {c['nome']}\nIdioma: {c['idioma']}\n\n# Roteiros\n{roteiros}",
               schema=schema, canal=c, ctx={"canal": slug, "video": video})
    avisos = []
    caps = capitulos(vd, r["intro"].strip() or "Intro")
    from .video import fluxo_video
    if not caps:
        avisos.append("O vídeo ainda não foi renderizado: a descrição saiu sem capítulos." if fluxo_video(vd) else
                      "Nenhum bloco entregue ainda: a descrição saiu sem capítulos.")
    elif not fluxo_video(vd) and len(entregues(vd)) < len(blocos):
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
# formato com capítulo NÃO falado (bestiário: uma história contínua, o nome do capítulo só aparece na tela e na
# descrição): o bloco não tem a linha "Nome." narrada nem card de título (formato.json › roteiro.capitulo_falado)
MARCA_CAPITULO = "#! capítulo: o nome só aparece na tela"


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


def _modelo_roteiro(c):
    """O prompt de roteiro: o do canal (prompts/Roteiro do vídeo.md, que você altera em canal › Prompt de roteiro),
    senão o do formato."""
    do_canal = Path(c.get("raiz") or Path(c["producoes"]).parent) / "prompts" / PROMPT_ROTEIRO
    if do_canal.exists() and do_canal.read_text().strip():
        return do_canal.read_text()
    return modelo_roteiro_do_formato(c.get("formato"))


PROMPT_ROTEIRO = "Roteiro do vídeo.md"


def modelo_roteiro_do_formato(formato):
    """O prompt de roteiro que o formato traz (formato.json › roteiro.modelo), ou None se ele não escreve roteiro."""
    modelo = (ficha_formato(formato).get("roteiro") or {}).get("modelo")
    if modelo and arquivo_formato(modelo, formato, exigir=False).is_file():
        return arquivo_formato(modelo, formato).read_text()
    return None


def _medir_roteiro(texto):
    """(capítulos, palavras narradas) — o que o agente de roteiro precisa acertar."""
    cold, partes = dividir_roteiro(texto)
    palavras = len(re.findall(r"[A-Za-z0-9']+", cold + " " + " ".join(t for _, t in partes)))
    return len(partes), palavras, bool(cold)


def _ritmo_roteiro(texto):
    """(palavras por frase em média, fração de frases de até 8 palavras) do texto narrado. Roteiro de frases
    curtas, um fato por frase, sai picotado na voz: ela para ~0,8 s em cada ponto final (medido 2026-11-10:
    10,6 palavras por frase contra 15 a 20 nos vídeos de referência do cartum)."""
    cold, partes = dividir_roteiro(texto)
    corrido = re.sub(r"\s+", " ", cold + " " + " ".join(t for _, t in partes)).strip()
    n = [len(f.split()) for f in re.split(r"(?<=[.!?])\s+", corrido) if f.strip()]
    return (sum(n) / len(n), sum(x <= 8 for x in n) / len(n)) if n else (0.0, 0.0)


def escrever_roteiro(c, titulo, obs=""):
    """O agente de roteiro (formato com roteiro.modelo, 2026-11-04): só com o título, o Claude escreve o roteiro
    inteiro no molde do formato (cold open + capítulos "# Nome"), e se sair fora do molde (poucos capítulos, curto
    ou longo demais) corrige numa volta da mesma conversa. Devolve o texto; ValueError se o formato não tem modelo."""
    import uuid
    from .motor_claude import _extrair_json, chamar  # noqa: F401
    sistema = _modelo_roteiro(c)
    if not sistema:
        raise ValueError("Este formato não escreve roteiro sozinho: cole o roteiro.")
    regras = (ler_json(Path(c.get("raiz") or Path(c["producoes"]).parent) / "canal.json", {}) or {}).get("regras") or {}
    if regras.get("storyboard"):
        sistema += "\n\n## Regras do tema deste canal\n" + "\n".join(f"- {r}" for r in regras["storyboard"])
    texto = (f"Título do vídeo: {titulo.strip()}\nCanal: {c.get('nome', '')} — tema: {c.get('tema', '')}\n"
             f"Idioma da narração: {c.get('idioma', 'en')}\n" + (f"Observação de quem produz: {obs}\n" if obs else "")
             + "\nEscreva o roteiro completo. Responda só com o roteiro, sem nada antes ou depois.")
    sid = str(uuid.uuid4())
    for volta in range(2):
        r = chamar("roteiro", sistema, texto, canal=c, timeout=1800, sessao=(sid, volta == 0), texto_livre=True,
                   ctx={"canal": Path(c.get("raiz") or Path(c["producoes"]).parent).name})
        rot = re.sub(r"^```\w*\n|\n```\s*$", "", r["texto"].strip())
        n, palavras, tem_cold = _medir_roteiro(rot)
        # o molde é do formato (formato.json › roteiro.medidas); sem ele, o do bestiário, o 1º a ter agente de roteiro
        # do formato, com o que o canal trocar em canal.json › roteiro › medidas (um canal de vídeos mais curtos)
        cj = ler_json(Path(c.get("raiz") or Path(c["producoes"]).parent) / "canal.json", {}) or {}
        med = {"cold_open": True, "capitulos": [6, 11], "palavras": [1600, 3000],
               **((ficha_formato(c.get("formato")).get("roteiro") or {}).get("medidas") or {}),
               **((cj.get("roteiro") or {}).get("medidas") or {})}
        problemas = []
        if med["cold_open"] and not tem_cold:
            problemas.append("falta o cold open (texto antes do 1º \"# capítulo\")")
        if not med["cold_open"] and tem_cold:
            problemas.append("há texto antes do 1º \"# Nome\" (este formato não tem introdução: comece pelo 1º tópico)")
        if not med["capitulos"][0] <= n <= med["capitulos"][1]:
            problemas.append(f"{n} capítulos (o molde pede de {med['capitulos'][0]} a {med['capitulos'][1]}, cada um "
                             "com uma linha \"# Nome\")")
        if not med["palavras"][0] <= palavras <= med["palavras"][1]:
            problemas.append(f"{palavras} palavras narradas (o molde pede de {med['palavras'][0]} a {med['palavras'][1]})")
        fr = med.get("frases")          # {"media": [14, 22], "curtas_max": 0.2}: só os formatos que pedem
        if fr:
            media, curtas = _ritmo_roteiro(rot)
            if fr.get("media") and not fr["media"][0] <= media <= fr["media"][1]:
                problemas.append(f"as frases têm {media:.1f} palavras em média (o molde pede de {fr['media'][0]} a "
                                 f"{fr['media'][1]}: junte na mesma frase os fatos da mesma ideia, ligados por "
                                 "conectivo, em vez de um fato por frase)")
            if fr.get("curtas_max") is not None and curtas > fr["curtas_max"]:
                problemas.append(f"{curtas:.0%} das frases têm até 8 palavras (o molde aceita até "
                                 f"{fr['curtas_max']:.0%}: frase curta só como fecho de uma ideia)")
        if not problemas:
            return rot
        texto = "Fora do molde: " + "; ".join(problemas) + ". Reescreva o roteiro inteiro corrigindo isso."
    return rot


def criar_video(c, titulo, roteiro, obs=""):
    """Cria a pasta do vídeo e um bloco por tópico (00 = cold open). Sem roteiro, num formato com agente de roteiro
    (formato.json › roteiro.modelo), o Claude escreve o roteiro a partir do título. Devolve o slug; ValueError com o
    motivo (para mostrar a quem produz) se não der."""
    if not titulo.strip():
        raise ValueError("Dê um título ao vídeo.")
    if not (roteiro or "").strip():
        if Path(c["producoes"], slug_video(titulo)).exists() or fichas.existe(Path(c["producoes"], slug_video(titulo))):
            raise ValueError(f"Já existe um vídeo com essa pasta ({slug_video(titulo)}).")
        roteiro = escrever_roteiro(c, titulo, obs)
    cold_open, partes = dividir_roteiro(roteiro)
    if not partes:
        raise ValueError("O roteiro precisa ter cada tópico começando com uma linha \"# Nome do tópico\".")
    vd = Path(c["producoes"]) / slug_video(titulo)
    if not slug_video(titulo):
        raise ValueError("O título precisa ter letras ou números.")
    if vd.exists():
        raise ValueError(f"Já existe um vídeo com essa pasta ({vd.name}).")
    if fichas.existe(vd):
        raise ValueError(f"Já existe um vídeo arquivado com esse título ({vd.name}). Use outro título ou exclua o arquivado.")
    (vd / "edicao").mkdir(parents=True)
    gravar_json(vd / "estudio_video.json", {"titulo": titulo.strip()})
    fichas.criar(vd, titulo, roteiro)
    escrever_blocos(c, vd, cold_open, partes)
    return vd.name


def escrever_blocos(c, vd, cold_open, partes):
    """Os blocos do vídeo (um por tópico, 00 = cold open) e o fluxo dele, do jeito do FORMATO do canal: como o nome
    do capítulo entra na narração (roteiro.capitulo_falado) e se o vídeo anda inteiro ou bloco a bloco
    (producao.fluxo). Usado ao criar o vídeo e ao redividir um vídeo ainda não começado quando o canal troca de
    formato (formato_canal.trocar)."""
    if cold_open:
        bd = vd / "blocos" / "00"
        bd.mkdir(parents=True)
        (bd / "roteiro.txt").write_text(f"# Cold open\n{MARCA_COLD_OPEN}\n{cold_open}\n")
    falado = (ficha_formato(c.get("formato")).get("roteiro") or {}).get("capitulo_falado", True)
    for i, (nome, texto) in enumerate(partes, 1):
        bd = vd / "blocos" / f"{i:02d}"
        bd.mkdir(parents=True)
        if falado == "na_frase":
            # o nome é o começo da 1ª frase do tópico (cartum: "Derinkuyu is an ancient…"): o bloco tem título, e ele
            # fica na tela enquanto essa frase é dita; não há a linha "Nome." à parte
            (bd / "roteiro.txt").write_text(f"# {nome}\n{texto}\n")
        elif falado:
            # a linha "# Nome" não é narrada (gerar_narracao.py ignora #); a linha "Nome." logo abaixo é
            (bd / "roteiro.txt").write_text(f"# {nome}\n{nome}.\n\n{texto}\n")
        else:
            (bd / "roteiro.txt").write_text(f"# {nome}\n{MARCA_CAPITULO}\n{texto}\n")
    # fluxo do formato (formato.json › producao.fluxo): "video" = o vídeo inteiro como um projeto só (video.py)
    info = {"titulo": estado.titulo_video(vd)}
    fluxo = (ficha_formato(c.get("formato")).get("producao") or {}).get("fluxo")
    if fluxo:
        info["fluxo"] = fluxo
    gravar_json(vd / "estudio_video.json", info)


# ---------------- excluir (lixeira) ----------------
LIXEIRA = "_lixeira"      # <producoes>/_lixeira/<vídeo>__<quando>: o estado.videos ignora pastas com "_"


def _ocupado(vd):
    """Motivo para não mexer na pasta do vídeo agora (bloco rodando, fila ou vídeo final em andamento), ou ""."""
    from .fila import ler_fila
    if ler_fila(vd).get("ativa"):
        return "a fila deste vídeo está rodando: pare a fila antes"
    for pid in list(vd.glob("blocos/*/_estudio/pid")) + [vd / "final" / "pid", vd / "producao" / "_estudio" / "pid"]:
        if pid.exists() and estado._vivo(pid.read_text().strip()):
            return "tem coisa rodando neste vídeo: pare antes"
    return ""


def excluir_video(c, slug):
    """Move o vídeo inteiro para a lixeira do canal (nada é apagado; dá para restaurar)."""
    prod = Path(c["producoes"])
    vd = prod / slug
    if not slug or slug.startswith((".", "_")) or "/" in slug or not (vd.is_dir() or fichas.existe(vd)):
        raise ValueError("vídeo não encontrado")
    motivo = _ocupado(vd)
    if motivo:
        raise ValueError(motivo)
    fichas.garantir(vd)
    destino = prod / LIXEIRA / f"{slug}__{dt.datetime.now():%Y%m%d-%H%M%S}"
    destino.parent.mkdir(exist_ok=True)
    pronto = prontos.para_a_lixeira(vd, destino)       # o MP4 da pasta de prontos do canal vai junto
    if vd.is_dir():
        vd.rename(destino)
    fichas.para_a_lixeira(vd, destino)                 # e a ficha também (vídeo arquivado: só ela e o MP4)
    for de, para in pronto:
        para.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(de), str(para))
    return destino.name


def arquivar_video(c, slug, com_mp4=False):
    """Vídeo que já foi (ou não vai mais ser) produzido: a produção inteira (blocos, narrações, assets, renders,
    projetos) vai para o Lixo do Mac — a pasta <canal>/producoes/<vídeo>/ deixa de existir — e a FICHA fica
    (fichas.py: título, número, roteiro, thumbnail, duração e o que está na aba Publicação). O vídeo continua no
    quadro, no calendário e na lista.
    O MP4 pronto continua na pasta de prontos do canal, a não ser com com_mp4=True. Não tem desfazer no painel: o
    que saiu fica no Lixo do Mac até você esvaziar."""
    from . import limpeza
    vd = Path(c["producoes"]) / slug
    if not slug or slug.startswith((".", "_")) or "/" in slug or not (vd.is_dir() or fichas.existe(vd)):
        raise ValueError("vídeo não encontrado")
    if prontos.arquivado(vd) or not vd.is_dir():
        raise ValueError("este vídeo já está arquivado")
    motivo = _ocupado(vd)
    if motivo:
        raise ValueError(motivo)
    mp4 = prontos.atual(vd)
    if not mp4:     # entregue antes de existir a pasta de prontos: o MP4 ainda está em final/
        from .final import ler_estado
        velho = Path(ler_estado(vd).get("mp4") or vd / "final" / "-")
        if not velho.is_file() or vd not in velho.parents:    # pasta copiada à mão aponta para o MP4 do vídeo de origem
            velho = max((vd / "final").glob("*.mp4"), key=lambda f: f.stat().st_mtime, default=vd / "final" / "-")
        if velho.is_file() and not com_mp4:
            mp4 = prontos.guardar(vd, velho)
    ficha = {"arquivado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
             "n_blocos": len(estado.blocos_do_video(vd))}
    if mp4:
        try:
            ficha["duracao_s"] = round(_duracao(mp4), 1)
        except (ValueError, OSError, subprocess.SubprocessError):
            pass
    ficha["titulo"] = estado.titulo_video(vd)          # o estudio_video.json vai embora com a pasta
    fichas.garantir(vd)                                # a thumbnail e o roteiro já estão na ficha antes de a pasta sair
    itens = [(vd, "arquivado")]
    if com_mp4 and mp4:
        itens += [(f, "arquivado") for f in [mp4] + prontos._capas(mp4)]
        ficha["pronto"] = None
    tamanho, quantos, lixo = limpeza.mandar_para_o_lixo(itens) if itens else (0, 0, Path(""))
    prontos.anotar(vd, **ficha)
    return {"tamanho": tamanho, "quantos": quantos, "lixo": lixo.name, "mp4": bool(mp4) and not com_mp4}


def _mp4_entregues(vd, nn):
    """Os MP4 que o bloco já tinha entregue no vídeo: a edição e o Reels."""
    return [f for f in (vd / "edicao" / f"bloco {int(nn)}.mp4", vd / "reels" / f"bloco {int(nn)}.mp4") if f.exists()]


def _bloco_para_mexer(c, video, nn):
    vd = Path(c["producoes"]) / video
    b = vd / "blocos" / nn
    if not nn.isdigit() or not b.is_dir():
        raise ValueError("bloco não encontrado")
    motivo = _ocupado(vd)
    if motivo:
        raise ValueError(motivo)
    return vd, b


def limpar_bloco(c, video, nn):
    """Zera o bloco sem tirá-lo do vídeo: tudo o que a produção fez (narração, transcrição, storyboard, candidatos,
    assets, prévias, QA, .aep) e os MP4 já entregues vão para o Lixo do Mac. Fica só o roteiro.txt, então o bloco
    volta para a primeira etapa e dá para rodar de novo do zero."""
    from . import limpeza
    vd, b = _bloco_para_mexer(c, video, nn)
    itens = [(p, "bloco") for p in sorted(b.iterdir()) if p.name != "roteiro.txt"]
    itens += [(f, "bloco") for f in _mp4_entregues(vd, nn)]
    if not itens:
        return {"quantos": 0, "tamanho": 0, "lixo": ""}
    tamanho, quantos, destino = limpeza.mandar_para_o_lixo(itens)
    return {"quantos": quantos, "tamanho": tamanho, "lixo": destino.name}


MARCA_BLOCO = "__bloco-"   # <producoes>/_lixeira/<vídeo>__bloco-NN__<quando>
ENTREGUES = "_entregues"   # dentro da pasta na lixeira: os MP4 que o bloco tinha entregue no vídeo


def excluir_bloco(c, video, nn):
    """Tira o bloco do vídeo e guarda na lixeira do canal, como o vídeo excluído: dá para restaurar no painel (e para
    jogar fora de vez pela aba Limpeza). Vai junto o que ele já tinha entregue (o MP4 da edição e o do Reels).
    Os outros blocos continuam com o número que têm — renumerar quebraria os .aep já montados e o que o roteiro diz
    de cada tópico."""
    vd, b = _bloco_para_mexer(c, video, nn)
    destino = Path(c["producoes"]) / LIXEIRA / f"{video}{MARCA_BLOCO}{nn}__{dt.datetime.now():%Y%m%d-%H%M%S}"
    destino.parent.mkdir(exist_ok=True)
    b.rename(destino)
    guardados = 0
    for f in _mp4_entregues(vd, nn):
        alvo = destino / ENTREGUES / f.parent.name / f.name
        alvo.parent.mkdir(parents=True, exist_ok=True)
        f.rename(alvo)
        guardados += 1
    return {"lixeira": destino.name, "entregues": guardados}


def _partes_da_lixeira(nome):
    """<vídeo>__<quando> (vídeo inteiro) ou <vídeo>__bloco-NN__<quando> (um bloco)."""
    resto, _, quando = nome.rpartition("__")
    video, marca, nn = resto.partition(MARCA_BLOCO)
    return (video or nome), (nn if marca else ""), quando


def lixeira(c):
    pasta = Path(c["producoes"]) / LIXEIRA
    out = []
    for p in sorted(pasta.iterdir() if pasta.is_dir() else [], key=lambda p: p.stat().st_mtime, reverse=True):
        if not p.is_dir():
            continue
        video, nn, quando = _partes_da_lixeira(p.name)
        try:
            excluido = dt.datetime.strptime(quando, "%Y%m%d-%H%M%S").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            excluido = ""
        if nn:
            vd = Path(c["producoes"]) / video
            item = {"tipo": "bloco", "nn": nn, "titulo": estado.topico(p) or f"Bloco {nn}", "n_blocos": 0,
                    "video_titulo": estado.titulo_video(vd) if vd.is_dir() else video, "pode_restaurar": vd.is_dir()}
        else:
            n = len([b for b in (p / "blocos").glob("*") if b.is_dir()]) if (p / "blocos").is_dir() else 0
            titulo = (ler_json(p / fichas.GUARDADA / "ficha.json", {}) or {}).get("titulo") or estado.titulo_video(p)
            item = {"tipo": "video", "nn": "", "titulo": titulo, "n_blocos": n,
                    "video_titulo": "", "pode_restaurar": True}
        out.append({"nome": p.name, "video": video, "excluido": excluido, **item})
    return out


def restaurar_video(c, nome):
    """Devolve da lixeira o vídeo inteiro ou o bloco. Vídeo: se já existe pasta com o mesmo nome, volta como
    <vídeo>-restaurado. Bloco: volta para <vídeo>/blocos/NN com os MP4 que tinha entregue."""
    prod = Path(c["producoes"])
    src = prod / LIXEIRA / nome
    if "/" in nome or nome.startswith(".") or not src.is_dir():
        raise ValueError("não está na lixeira")
    video, nn, _ = _partes_da_lixeira(nome)
    if nn:
        vd = prod / video
        if not vd.is_dir():
            raise ValueError(f"o vídeo {video} não está mais aqui: restaure o vídeo antes")
        destino = vd / "blocos" / nn
        if destino.exists():
            raise ValueError(f"já existe o bloco {nn} neste vídeo")
        for f in sorted((src / ENTREGUES).rglob("*")) if (src / ENTREGUES).is_dir() else []:
            if f.is_file():
                alvo = vd / f.parent.name / f.name
                alvo.parent.mkdir(parents=True, exist_ok=True)
                if not alvo.exists():
                    f.rename(alvo)
        shutil.rmtree(src / ENTREGUES, ignore_errors=True)
        destino.parent.mkdir(parents=True, exist_ok=True)
        src.rename(destino)
        return f"{video}/blocos/{nn}"
    destino = prod / video
    if destino.exists():
        destino = prod / f"{video}-restaurado"
        if destino.exists():
            raise ValueError(f"já existe {destino.name}: renomeie a pasta antes")
    src.rename(destino)
    prontos.da_lixeira(destino)
    fichas.da_lixeira(destino)
    if not any(p.name != ".DS_Store" for p in destino.iterdir()):
        shutil.rmtree(destino)        # era um vídeo arquivado: só a ficha (e o MP4) voltam, não há pasta de produção
    return destino.name
