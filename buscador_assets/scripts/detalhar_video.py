"""Gera uma folha de frames mais densa de um vídeo candidato, para acertar o início do trecho.

Uso: python scripts/detalhar_video.py <projeto> <asset_id> <n_video> <inicio_s> <fim_s> [--passo 0.5]
Saída: _work/candidatos/<asset_id>/v<n>_detalhe_<ini>-<fim>.jpg
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from comum import folha_contato, ler_json



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("asset")
    ap.add_argument("n", type=int)
    ap.add_argument("inicio", type=float)
    ap.add_argument("fim", type=float)
    ap.add_argument("--passo", type=float, default=0.5)
    a = ap.parse_args()
    pasta = Path(a.projeto) / "_work" / "candidatos" / a.asset
    meta = ler_json(pasta / "candidatos.json")
    v = next(c for c in meta["candidatos"] if c["n"] == a.n)
    with tempfile.TemporaryDirectory() as tmp:
        if v.get("fonte", "youtube") != "youtube":     # banco livre: ffmpeg direto no arquivo leve
            fr = Path(tmp) / "f"
            fr.mkdir()
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-user_agent",
                            "ProFootballBuscadorAssets/1.0 (ferramenta pessoal de pesquisa de imagens)", "-ss", str(a.inicio),
                            "-i", v.get("url_preview") or v["url"], "-t", str(a.fim - a.inicio), "-vf",
                            f"fps=1/{a.passo},scale=400:-2", str(fr / "%03d.jpg")], check=True, timeout=1800)
            itens = [(p, f"v{a.n}  t={a.inicio + i * a.passo:.1f}s") for i, p in enumerate(sorted(fr.glob("*.jpg")))]
            destino = pasta / f"v{a.n}_detalhe_{a.inicio:g}-{a.fim:g}.jpg"
            folha_contato(itens, destino, colunas=6, celula=(400, 240), titulo=f"{a.asset} v{a.n} {a.inicio}-{a.fim}s")
            print(destino)
            return
        raise SystemExit("YouTube removido do sistema em 2026-10-11 (bloqueio de IP / acusação de fraude): este caminho não baixa mais nada do YouTube.")
    print(destino)


if __name__ == "__main__":
    main()
