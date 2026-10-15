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
    feito = {
        "roteiro": (b / "roteiro.txt").exists(),
        "narracao": any(b.glob("narracao.*")),
        "transcricao": (b / "_work" / "palavras.json").exists(),
        "storyboard": plano is not None,
        "busca": cand.exists() and any(cand.glob("*/candidatos.json")),
        "escolha": bool(plano) and n_assets > 0 and len(man) + sum(1 for e in escolhas.values() if e.get("pular")) >= n_assets,
        "edicao": bool(pv),
        "aprovado": bool(pv) and _aprovado(qa_md) and qa_md.stat().st_mtime >= pv[-1].stat().st_mtime - 5,
        "entregue": bool(entregue and entregue.exists()),
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
    for c in [video_dir / "estudio_video.json", video_dir / "blocos" / "01" / "cenas.json", video_dir / "cenas.json"]:
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
    return {"canal": canal_slug, "slug": video_slug, "titulo": titulo_video(vd), "pasta": str(vd),
            "blocos": blocos, "n_blocos": n, "entregues": entregues,
            "mudou": max([vd.stat().st_mtime] + [b["mudou"] for b in blocos]),
            "consumo": consumo(canal=canal_slug, video=video_slug), "fila": _fila(vd)}


def _fila(vd):
    from .fila import ler_fila          # import tardio: fila importa este módulo
    return ler_fila(vd)


def videos(canal_slug):
    c = canais()[canal_slug]
    pasta = Path(c["producoes"])
    out = []
    for vd in sorted(pasta.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if vd.is_dir() and not vd.name.startswith((".", "_")):
            out.append(video(canal_slug, vd.name))
    return out


def quando(ts):
    return time.strftime("%d/%m %H:%M", time.localtime(ts)) if ts else "—"
