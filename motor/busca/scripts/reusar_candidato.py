"""Copia um candidato de um asset para a lista de outro (ex.: o mesmo vídeo oficial de OTA serve para 3 cards).
Imprime o novo número (n) para usar no escolhas.json do asset de destino.

Uso: python scripts/reusar_candidato.py <projeto> <asset_origem> <n> <asset_destino>
Origem pode ser de outro projeto/bloco: passe o caminho da pasta do candidato (…/_work/candidatos/<id>) no lugar do id.
Atenção: confira a "duracao" do vídeo — um "inicio" além do fim faz o download falhar.
"""
import json
import shutil
import sys
from pathlib import Path

proj, origem, n, destino = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
cand = proj / "_work" / "candidatos"
p_origem = Path(origem) if ("/" in origem or "\\" in origem) else cand / origem
src = json.loads((p_origem / "candidatos.json").read_text())
c = dict(next(x for x in src["candidatos"] if x["n"] == n))
p_dest = cand / destino / "candidatos.json"
dst = json.loads(p_dest.read_text())
igual = next((x for x in dst["candidatos"] if x.get("url") == c.get("url")), None)
if igual:
    print(igual["n"], f"(já existia; duracao={igual.get('duracao')})")
    sys.exit()
c["n"] = max((x["n"] for x in dst["candidatos"]), default=0) + 1
if c.get("arquivo") and (p_origem / c["arquivo"]).exists():   # imagem: copia o arquivo (senão "01.jpg" apontaria para o 01 do destino)
    novo = f"{c['n']:02d}{Path(c['arquivo']).suffix}"
    shutil.copy2(p_origem / c["arquivo"], cand / destino / novo)
    c["arquivo"] = novo
dst["candidatos"].append(c)
p_dest.write_text(json.dumps(dst, indent=1, ensure_ascii=False))
print(c["n"], f"(duracao={c.get('duracao')}, {c.get('titulo')})")
