"""Compara velocidade de entrada/saída: referências × nossa prévia."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from medir_animacao import medir
import io, contextlib
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import caminhos  # noqa: E402
R = caminhos.referencias()
V = {k: str(next(R.glob(f"*{k}*"))) for k in ("Chocolate", "Luxury", "Sugars")}
REF_E = [("Chocolate", 41.5), ("Chocolate", 56.5), ("Chocolate", 156.25), ("Chocolate", 240.25), ("Luxury", 75.5), ("Luxury", 117.0), ("Luxury", 126.25), ("Sugars", 60.0), ("Sugars", 108.5), ("Sugars", 134.5)]
REF_S = [("Chocolate", 35.5), ("Chocolate", 132.25), ("Chocolate", 347.75), ("Luxury", 125.5), ("Luxury", 151.0), ("Luxury", 302.0), ("Sugars", 114.0), ("Sugars", 163.75)]
def rodar(lista):
    out = []
    for video, t0, dur, modo, rot in lista:
        with contextlib.redirect_stdout(io.StringIO()):
            r = medir(video, t0, dur, modo, rot)
        if r and r["px"] > 120:
            out.append(r)
    return out
def resumo(nome, rs):
    for modo in ("entrada", "saida"):
        x = [r for r in rs if r["modo"] == modo]
        if x:
            print(f"{nome:10s} {modo:7s} n={len(x):2d}  50%: {np.median([r['50'] for r in x]):.2f}s  90%: {np.median([r['90'] for r in x]):.2f}s  98%: {np.median([r['98'] for r in x]):.2f}s")
ref = rodar([(V[v], t - 0.3, 1.6, "entrada", f"{v} {t}") for v, t in REF_E] + [(V[v], t, 1.2, "saida", f"{v} {t}") for v, t in REF_S])
resumo("REFERÊNCIA", ref)
if len(sys.argv) > 2:
    nosso_v, plano = sys.argv[1], json.load(open(sys.argv[2]))
    est = [e for c in plano["cenas"] for e in c["estados"]]
    lst = []
    for i, e in enumerate(est):
        if e["layout"] == "B" and len(e.get("cards", [])) == 1:
            lst.append((nosso_v, min(e["cards"][0]["t"] - 0.2, e["ini"] + 0.1) - 0.25, 1.6, "entrada", f"nosso {e['ini']}"))
            if e.get("saida") == "animada" and i + 1 < len(est):
                lst.append((nosso_v, est[i + 1]["ini"] + 0.12 - 1.0, 1.2, "saida", f"nosso {e['ini']}"))
    resumo("NOSSO", rodar(lst))
