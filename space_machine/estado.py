"""Status de canais, vídeos e blocos lido direto das pastas (nada duplicado em banco: o kanban nunca fica velho).

Etapas de um bloco, na ordem do pipeline (ETAPAS); cada uma é "feita" quando o arquivo que ela produz existe.
"""
import json
import re
import time
from pathlib import Path

from .motor_claude import canais, config, consumo

ETAPAS = [
    ("roteiro", "Roteiro"),
    ("narracao", "Narração"),
    ("transcricao", "Transcrição"),
    ("storyboard", "Storyboard"),
    ("busca", "Busca"),
    ("escolha", "Assets"),
    ("edicao", "Edição"),
    ("aprovado", "QA aprovado"),
    ("entregue", "Entregue"),
]
ROTULO = dict(ETAPAS)


def _json(p, padrao=None):
    try:
        return json.loads(Path(p).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def _aprovado(qa_md):
    if not qa_md.exists():
        return False
    linha = next((l for l in qa_md.read_text().splitlines() if l.startswith("Prévia:")), "")
    return "APROVADO" in linha and "REPROVADO" not in linha


def topico(bloco):
    r = bloco / "roteiro.txt"
    if r.exists():
        for l in r.read_text().splitlines():
            if l.startswith("#"):
                return l.lstrip("# ").strip()
    plano = _json(bloco / "plano.json", {})
    itens = (plano or {}).get("itens") or []
    return itens[0].get("nome") if itens else bloco.name


def previas(bloco):
    nn = bloco.name
    vs = []
    for f in (bloco / "edicao").glob(f"previa_bloco_{nn}_v*.mp4"):
        m = re.search(r"_v(\d+)\.mp4$", f.name)
        if m:
            vs.append((int(m.group(1)), f))
    return [f for _, f in sorted(vs)]


def _para_conferir(b):
    """Tudo que pede o seu olho antes de entregar: "conferir" das escolhas e assets pulados."""
    escolhas = _json(b / "escolhas.json", {}) or {}
    itens = {}
    for aid, e in escolhas.items():
        if e.get("pular"):
            itens[aid] = f"pulado (sem asset): {e.get('motivo', '')}".strip(": ")
        elif e.get("conferir"):
            itens[aid] = e["conferir"]
    return itens


def conferir_pendentes(b):
    """Itens ainda não aprovados. A aprovação vale para aquele texto: se a escolha mudar, volta a pendente."""
    b = Path(b)
    ok = _json(b / "_estudio" / "conferir_ok.json", {}) or {}
    return {aid: t for aid, t in _para_conferir(b).items() if ok.get(aid) != t}


def aprovar_conferir(b):
    b = Path(b)
    arq = b / "_estudio" / "conferir_ok.json"
    ok = _json(arq, {}) or {}
    ok.update(_para_conferir(b))
    arq.parent.mkdir(exist_ok=True)
    arq.write_text(json.dumps(ok, ensure_ascii=False, indent=1))


def bloco(caminho, video_dir=None):
    """Status de um bloco: etapa atual, contagem de assets, prévias e o estado.json do Estúdio."""
    b = Path(caminho)
    nn = b.name
    video_dir = video_dir or b.parent.parent
    plano = _json(b / "plano.json")
    n_assets = 0
    if plano:
        for item in plano.get("itens", []):
            n_assets += 1 if item.get("titulo_asset") else 0
            n_assets += sum(len(c.get("assets", [])) for c in item.get("cenas", []))
    man = (_json(b / "manifesto.json", {}) or {}).get("assets", [])
    escolhas = _json(b / "escolhas.json", {}) or {}
    cand = b / "_work" / "candidatos"
    pv = previas(b)
    qa_md = b / "edicao" / f"qa_{nn}.md"
    entregue = (video_dir / "edicao" / f"bloco {int(nn)}.mp4") if nn.isdigit() else None
    entregue_ok = bool(entregue and entregue.exists())
    # a entrega move a prévia aprovada para o entregue e a limpeza tira as outras (limpeza.py): bloco entregue já
    # passou por edição e QA, a não ser que haja prévia mais nova que o entregue (editado de novo depois)
    editado_depois = bool(entregue_ok and pv and pv[-1].stat().st_mtime > entregue.stat().st_mtime + 60)
    feito = {
        "roteiro": (b / "roteiro.txt").exists(),
        "narracao": any(b.glob("narracao.*")),
        "transcricao": (b / "_work" / "palavras.json").exists(),
        "storyboard": plano is not None,
        "busca": cand.exists() and any(cand.glob("*/candidatos.json")),
        "escolha": bool(plano) and n_assets > 0 and len(man) + sum(1 for e in escolhas.values() if e.get("pular")) >= n_assets,
        "edicao": bool(pv) or entregue_ok,
        "aprovado": (bool(pv) and _aprovado(qa_md) and qa_md.stat().st_mtime >= pv[-1].stat().st_mtime - 5)
                    or (entregue_ok and not editado_depois),
        "entregue": entregue_ok,
    }
    atual = "roteiro"
    for k, _ in ETAPAS:
        if feito[k]:
            atual = k
        else:
            break
    est = _json(b / "_estudio" / "estado.json", {}) or {}
    # quem manda é o pid vivo, não o estado.json: na checagem do claude (antes da 1ª etapa) o estado ainda diz
    # "parado", e o botão Rodar liberado ali abriu 3 rodadas no mesmo bloco (2026-10-11)
    pid = b / "_estudio" / "pid"
    rodando = pid.exists() and _vivo(pid.read_text().strip())
    conferir = [f"{aid}: {e['conferir']}" for aid, e in escolhas.items() if e.get("conferir")]
    return {
        "nn": nn, "caminho": str(b), "topico": topico(b), "feito": feito, "atual": atual,
        "rotulo": ROTULO[atual], "assets_total": n_assets, "assets_prontos": len(man),
        "pulados": [aid for aid, e in escolhas.items() if e.get("pular")],
        "conferir": conferir, "previas": [str(p) for p in pv],
        "conferir_pendentes": conferir_pendentes(b),
        "travar_conferir": bool(config().get("travar_conferir")),
        "qa": qa_md.read_text() if qa_md.exists() else "", "aprovado": feito["aprovado"],
        "parado": est.get("parado"), "etapas_estudio": est.get("etapas", {}), "rodando": rodando,
        "storyboard_md": str(b / f"storyboard_{nn}.md") if (b / f"storyboard_{nn}.md").exists() else None,
        "revisao": str(b / "revisao.html") if (b / "revisao.html").exists() else None,
        "mudou": max([f.stat().st_mtime for f in (b / "_estudio").glob("*")] + [0]) if (b / "_estudio").exists() else 0,
    }


# etapas do vídeo inteiro (fluxo "video", rodar_video.py) e o rótulo de cada uma no painel
ETAPAS_VIDEO = [("narracao", "Narração"), ("transcrever", "Transcrição"), ("juntar", "Juntar capítulos"),
                ("storyboard", "Storyboard"), ("buscar", "Busca"), ("escolher", "Assets"), ("montar", "Render e QA"),
                ("entregar", "Vídeo final")]


def producao_video(vd):
    """Andamento do VÍDEO INTEIRO (fluxo "video"): <vídeo>/producao/_estudio/estado.json + o que os arquivos dizem
    que já está feito, os capítulos (narração, transcrição, QA) e o MP4 final."""
    from . import video
    vd = Path(vd)
    p = video.pasta(vd)
    est = _json(p / "_estudio" / "estado.json", {}) or {}
    pid = p / "_estudio" / "pid"
    rodando = pid.exists() and _vivo(pid.read_text().strip())
    caps = video.capitulos(vd)
    plano = _json(p / "plano.json")
    n_assets = 0
    for item in (plano or {}).get("itens", []):
        n_assets += 1 if item.get("titulo_asset") else 0
        n_assets += sum(len(c.get("assets", [])) for c in item.get("cenas", []))
    man = (_json(p / "manifesto.json", {}) or {}).get("assets", [])
    escolhas = _json(p / "escolhas.json", {}) or {}
    pedacos = _json(p / "edicao" / "pedacos.json", []) or []
    qa = {}
    for c in caps:
        md = p / "edicao" / f"qa_{c.name}.md"
        qa[c.name] = {"md": md.read_text() if md.exists() else "", "aprovado": _aprovado(md),
                      "folha": str(p / "edicao" / f"qa_{c.name}.jpg") if (p / "edicao" / f"qa_{c.name}.jpg").exists() else None}
    fim = _json(vd / "final" / "estado.json", {}) or {}
    mp4 = Path(fim.get("mp4") or vd / "final" / "-")
    renderizado = bool(pedacos) and all(Path(x["saida"]).exists() for x in pedacos)
    feito = {
        "narracao": bool(caps) and all(any(c.glob("narracao.*")) for c in caps),
        "transcrever": bool(caps) and all((c / "_work" / "palavras.json").exists() for c in caps),
        "juntar": video.atualizado(vd),
        "storyboard": plano is not None and (p / "storyboard_video.md").exists(),
        "buscar": (p / "_work" / "candidatos").is_dir() and any((p / "_work" / "candidatos").glob("*/candidatos.json")),
        "escolher": bool(plano) and n_assets > 0
                    and len(man) + sum(1 for e in escolhas.values() if e.get("pular")) >= n_assets,
        "montar": renderizado and all(qa.get(x["nn"], {}).get("aprovado") for x in pedacos),
        "entregar": mp4.is_file() and renderizado
                    and mp4.stat().st_mtime >= max(Path(x["saida"]).stat().st_mtime for x in pedacos),
    }
    atual = ""
    for k, _ in ETAPAS_VIDEO:
        if not feito[k]:
            break
        atual = k
    sb = p / "storyboard_video.md"
    return {
        "rodando": rodando, "parado": None if rodando else est.get("parado"), "etapa_atual": est.get("atual") or "",
        "feito": feito, "atual": atual,
        "etapas": [{"id": e, "rotulo": r, **{k: (est.get("etapas", {}).get(e) or {}).get(k, "")
                                            for k in ("status", "detalhe", "quando")}} for e, r in ETAPAS_VIDEO],
        "capitulos": [{"nn": c.name, "topico": topico(c), "narrado": any(c.glob("narracao.*")),
                       "transcrito": (c / "_work" / "palavras.json").exists(), "qa": qa[c.name]} for c in caps],
        "assets_total": n_assets, "assets_prontos": len(man),
        "conferir_pendentes": conferir_pendentes(p), "conferidos": len(_para_conferir(p)) - len(conferir_pendentes(p)),
        "travar_conferir": bool(config().get("travar_conferir")),
        "storyboard": sb.read_text() if sb.exists() else "",
        "mp4": str(mp4) if mp4.is_file() else None,
        "mudou": max([f.stat().st_mtime for f in (p / "_estudio").glob("*")] + [0]) if (p / "_estudio").exists() else 0,
    }


def _vivo(pid):
    import os
    try:
        # rodada aberta pelo painel é filha dele: quando termina vira zumbi (os.kill ainda "acha" o pid)
        # até alguém recolher. waitpid recolhe e diz que acabou; se não for filha, segue para o kill.
        if os.waitpid(int(pid), os.WNOHANG)[0] == int(pid):
            return False
    except (ChildProcessError, ValueError, OSError):
        pass
    try:
        os.kill(int(pid), 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def blocos_do_video(video_dir):
    video_dir = Path(video_dir)
    pasta = video_dir / "blocos"
    if not pasta.exists():
        return []
    return [bloco(p, video_dir) for p in sorted(pasta.iterdir()) if p.is_dir() and p.name.isdigit()]


def titulo_video(video_dir):
    video_dir = Path(video_dir)
    ficha = video_dir.parent.parent / "fichas" / video_dir.name / "ficha.json"      # fichas.py (lido direto: sem migrar)
    for c in [video_dir / "estudio_video.json", ficha, video_dir / "blocos" / "01" / "cenas.json", video_dir / "cenas.json"]:
        t = (_json(c, {}) or {}).get("titulo")
        if t:
            return t
    return video_dir.name.replace("-", " ").title()


def video(canal_slug, video_slug, com_blocos=True):
    c = canais()[canal_slug]
    vd = Path(c["producoes"]) / video_slug
    blocos = blocos_do_video(vd) if com_blocos else []
    n = len(blocos)
    entregues = sum(1 for b in blocos if b["feito"]["entregue"])
    from .video import fluxo_video
    from . import fichas
    ficha = fichas.ler(vd)
    arquivado = ficha.get("arquivado") or ""        # só a ficha ficou (gestao.arquivar_video): não há o que medir
    mudou_pasta = vd.stat().st_mtime if vd.is_dir() else (fichas.pasta(vd) / "ficha.json").stat().st_mtime
    prod = producao_video(vd) if fluxo_video(vd) and not arquivado else None
    if prod:            # fluxo "video": os capítulos não são entregues um a um; o vídeo inteiro é
        entregues = n if prod["feito"]["entregar"] else 0
    return {"canal": canal_slug, "slug": video_slug, "titulo": titulo_video(vd), "pasta": str(vd),
            "blocos": blocos, "n_blocos": n, "entregues": entregues,
            "fluxo": "video" if prod else "blocos", "producao": prod,
            "arquivado": arquivado, "numero": ficha.get("numero") or 0, "pronto": ficha.get("pronto") or "",
            "duracao_s": ficha.get("duracao_s") or 0, "n_blocos_ficha": ficha.get("n_blocos") or 0,
            "mudou": max([mudou_pasta] + [b["mudou"] for b in blocos] + [prod["mudou"] if prod else 0]),
            "consumo": consumo(canal=canal_slug, video=video_slug), "fila": _fila(vd)}


def _fila(vd):
    from .fila import ler_fila          # import tardio: fila importa este módulo
    return ler_fila(vd)


def videos(canal_slug):
    c = canais()[canal_slug]
    pasta = Path(c["producoes"])
    from . import fichas
    # os que têm pasta de produção e os que só têm ficha (arquivados): o canal continua vendo todos
    nomes = [vd.name for vd in pasta.iterdir() if vd.is_dir() and not vd.name.startswith((".", "_"))] if pasta.is_dir() else []
    nomes += [vd.name for vd in fichas.so_ficha(c)]
    out = [video(canal_slug, n) for n in nomes]
    return sorted(out, key=lambda v: v["mudou"], reverse=True)


def quando(ts):
    return time.strftime("%d/%m %H:%M", time.localtime(ts)) if ts else "—"
