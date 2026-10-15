"""Limpeza: o que o sistema gera e não serve mais vai para o Lixo do Mac (dá para recuperar até esvaziar o Lixo).

  python -m space_machine limpar [--canal slug] [--cache] [--aplicar]   sem --aplicar, só mostra o que sairia

O que é lixo (medido em 2026-10-14: ~10 GB de 29 GB nas produções):
- prévias de um bloco ENTREGUE que não são mais novas que o entregue: o edicao/bloco N.mp4 já tem o vídeo (a entrega
  copiava a última prévia: 52 de 67 eram cópias idênticas); prévia mais nova que o entregue é trabalho em andamento e
  fica. Bloco não entregue: só as versões numeradas antigas (fica a última); prévias com outro nome ficam.
- os candidatos baixados (_work/candidatos) de um bloco entregue: serviram para escolher os assets, que já estão em
  assets/. A busca não baixa de novo o que já foi escolhido; rodar "de busca" ou "de escolha" baixa o que faltar.
- Auto-Save do After e pastas _backup_* antigas.
- com --cache: imagens do cache da busca (<dados>/cache/img) com mais de 7 dias (só servem para não baixar de novo).
Fica sempre: assets, narração, transcrição, cenas/plano/escolhas/manifesto, o .aep e o _cache da edição (o .aep usa),
QA, storyboard, logs, o vídeo final e as lixeiras do painel.
O Lixo do Mac não deixa listar, mas deixa mover: cada limpeza vira a pasta "Space Machine limpeza <data>" no Lixo.
Se não der (outro disco, sem permissão), vai para <dados>/lixo/.
"""
import argparse
import os
import re
import shutil
import time
from pathlib import Path

from .sistema import DADOS, canais, config

CATEGORIAS = {
    "previas": "Prévias já entregues ou antigas",
    "candidatos": "Candidatos baixados de blocos entregues",
    "after": "Auto-Save do After e backups antigos",
    "cache": "Cache de imagens da busca (mais de 7 dias)",
}


def _tamanho(p):
    p = Path(p)
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def _numero(f):
    m = re.search(r"_v(\d+)\.mp4$", f.name)
    return int(m.group(1)) if m else None


def lixo_do_bloco(b, vd):
    """[(caminho, categoria)] do que pode sair deste bloco."""
    b, vd = Path(b), Path(vd)
    itens = []
    entregue = vd / "edicao" / f"bloco {int(b.name)}.mp4" if b.name.isdigit() else None
    entregue = entregue if entregue and entregue.exists() else None
    ed = b / "edicao"
    previas = sorted(ed.glob(f"previa_bloco_{b.name}_*.mp4")) if ed.is_dir() else []
    if entregue:
        # mais nova que o entregue (com folga de 1 min) = alguém editou de novo depois da entrega: fica
        saem = [f for f in previas if f.stat().st_mtime <= entregue.stat().st_mtime + 60]
    else:
        numeradas = sorted((f for f in previas if _numero(f) is not None), key=_numero)
        saem = numeradas[:-1]
    for f in saem:
        itens.append((f, "previas"))
        for qa in ed.glob(f"_qa_{f.stem}.*"):        # medidas do QA daquela prévia (.jsonl e .bg.npy)
            itens.append((qa, "previas"))
    if entregue and (b / "_work" / "candidatos").is_dir():
        itens.append((b / "_work" / "candidatos", "candidatos"))
    if (ed / "Auto-Save").is_dir():
        itens.append((ed / "Auto-Save", "after"))
    itens += [(p, "after") for p in b.glob("_backup*") if p.is_dir()]
    return itens


def _rodando(b):
    """Bloco com rodada viva fica de fora (não mexer em pasta que o motor está usando)."""
    from .estado import _vivo
    pid = Path(b) / "_estudio" / "pid"
    return pid.exists() and _vivo(pid.read_text().strip())


def lixo_do_video(vd):
    vd = Path(vd)
    itens = []
    blocos = vd / "blocos"
    for b in sorted(blocos.iterdir()) if blocos.is_dir() else []:
        if b.is_dir() and b.name.isdigit() and not _rodando(b):
            itens += lixo_do_bloco(b, vd)
    if (vd / "final" / "Auto-Save").is_dir():
        itens.append((vd / "final" / "Auto-Save", "after"))
    return itens


def lixo_cache(dias=7):
    pasta = DADOS / "cache" / "img"
    limite = time.time() - dias * 86400
    return [(f, "cache") for f in pasta.rglob("*") if f.is_file() and f.stat().st_mtime < limite] if pasta.is_dir() else []


def _videos(slug):
    prod = Path(canais()[slug]["producoes"])
    return [v for v in sorted(prod.iterdir()) if v.is_dir() and not v.name.startswith((".", "_"))] if prod.is_dir() else []


def levantar(slug=None, cache=True):
    """O que sairia, por canal e vídeo, com os tamanhos. Não move nada."""
    from .estado import titulo_video
    out = {"videos": [], "categorias": {k: 0 for k in CATEGORIAS}, "total": 0}
    for s, c in canais().items():
        if slug and s != slug:
            continue
        for vd in _videos(s):
            itens = lixo_do_video(vd)
            if not itens:
                continue
            por = {}
            for p, cat in itens:
                por[cat] = por.get(cat, 0) + _tamanho(p)
            tot = sum(por.values())
            out["videos"].append({"canal": s, "canal_nome": c["nome"], "video": vd.name, "titulo": titulo_video(vd),
                                  "categorias": por, "total": tot, "itens": len(itens)})
            for k, v in por.items():
                out["categorias"][k] += v
    if cache:
        out["categorias"]["cache"] = sum(f.stat().st_size for f, _ in lixo_cache())
    out["total"] = sum(out["categorias"].values())
    out["videos"].sort(key=lambda v: -v["total"])
    return out


def _destino_lixo():
    """Pasta desta limpeza no Lixo do Mac (ou em <dados>/lixo se o Lixo não aceitar)."""
    nome = f"Space Machine limpeza {time.strftime('%Y-%m-%d %Hh%M')}"
    lixo = Path.home() / ".Trash" / nome
    try:
        # dados em outro disco: mover para o Lixo seria copiar tudo; fica em <dados>/lixo, no disco dos dados
        if os.stat(DADOS).st_dev == os.stat(lixo.parent).st_dev:
            lixo.mkdir(exist_ok=True)
            return lixo
    except OSError:
        pass
    alt = DADOS / "lixo" / nome
    alt.mkdir(parents=True, exist_ok=True)
    return alt


def mandar_para_o_lixo(itens, raiz=None):
    """Move os itens para o Lixo mantendo canal/vídeo/bloco no caminho. Devolve (bytes, quantos, pasta)."""
    raiz = Path(raiz or DADOS)
    destino = _destino_lixo()
    feitos, total = 0, 0
    for p, _ in itens:
        p = Path(p)
        if not p.exists():
            continue
        tam = _tamanho(p)
        try:
            rel = p.resolve().relative_to(raiz.resolve())
        except ValueError:
            rel = Path(p.name)
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(p, alvo)
        except OSError:
            # outro disco (ou o Lixo recusou este item): vai para <dados>/lixo, no mesmo disco dos dados
            alvo = DADOS / "lixo" / destino.name / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(alvo))
        feitos += 1
        total += tam
    return total, feitos, destino


def limpar(slug=None, categorias=("previas", "candidatos", "after"), cache=False):
    itens = []
    for s in canais():
        if slug and s != slug:
            continue
        for vd in _videos(s):
            itens += [(p, cat) for p, cat in lixo_do_video(vd) if cat in categorias]
    if cache or "cache" in categorias:
        itens += lixo_cache()
    return mandar_para_o_lixo(itens)


def depois_de_entregar(b):
    """Limpeza automática de um bloco que acabou de ser entregue (config limpeza_automatica, ligada por padrão)."""
    if not config().get("limpeza_automatica", True):
        return None
    b = Path(b)
    itens = lixo_do_bloco(b, b.parent.parent)
    return mandar_para_o_lixo(itens) if itens else None


def gb(n):
    return f"{n / 1e9:.1f} GB".replace(".", ",")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m space_machine limpar", description=__doc__.split("\n")[0])
    ap.add_argument("--canal", help="só este canal (slug)")
    ap.add_argument("--cache", action="store_true", help="também o cache de imagens da busca com mais de 7 dias")
    ap.add_argument("--aplicar", action="store_true", help="manda de fato para o Lixo (sem isso, só mostra)")
    a = ap.parse_args(argv)
    r = levantar(a.canal, cache=a.cache)
    for v in r["videos"]:
        print(f"{gb(v['total']):>9}  {v['canal_nome']} › {v['video']}  ({v['itens']} itens)")
    for k, n in r["categorias"].items():
        if n:
            print(f"{gb(n):>9}  {CATEGORIAS[k]}")
    print(f"{gb(r['total']):>9}  total")
    if not a.aplicar:
        print("\nNada foi movido. Para mandar para o Lixo: --aplicar")
        return
    cats = ("previas", "candidatos", "after") + (("cache",) if a.cache else ())
    total, n, pasta = limpar(a.canal, cats, a.cache)
    print(f"\n{gb(total)} em {n} itens foram para: {pasta}\nO espaço volta quando você esvaziar o Lixo.")


if __name__ == "__main__":
    main()
