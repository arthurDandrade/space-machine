"""Mostra em que pé está cada asset do projeto.

Uso: python scripts/status.py <projeto> [--pendentes]
"""
import argparse
from pathlib import Path

from comum import iter_assets, ler_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--pendentes", action="store_true", help="lista só o que falta fazer")
    a = ap.parse_args()
    proj = Path(a.projeto)
    plano = ler_json(proj / "plano.json")
    escolhas = ler_json(proj / "escolhas.json", {})
    manif = {m["id"] for m in ler_json(proj / "manifesto.json", {"assets": []})["assets"]}
    cont = {"sem busca": 0, "sem candidatos": 0, "a escolher": 0, "escolhido": 0, "pronto": 0, "pulado": 0}
    for item, cena, asset in iter_assets(plano):
        aid = asset["id"]
        meta = ler_json(proj / "_work" / "candidatos" / aid / "candidatos.json")
        esc = escolhas.get(aid)
        if esc and esc.get("pular"):
            st = "pulado"
        elif aid in manif:
            st = "pronto"
        elif esc:
            st = "escolhido"
        elif meta is None:
            st = "sem busca"
        elif not meta["candidatos"]:
            st = "sem candidatos"
        else:
            st = "a escolher"
        cont[st] += 1
        if not a.pendentes or st in ("sem busca", "sem candidatos", "a escolher", "escolhido"):
            n = len(meta["candidatos"]) if meta else 0
            print(f"{aid:12s} {asset['tipo']:9s} {st:15s} cand={n:<2d} {asset.get('descricao','')[:70]}")
    print("\n" + "  ".join(f"{k}: {v}" for k, v in cont.items()))


if __name__ == "__main__":
    main()
