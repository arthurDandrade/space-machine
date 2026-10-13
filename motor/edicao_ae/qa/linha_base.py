"""Gera referencia.json a partir das detecções dos 4 vídeos de referência (4 fps)."""
import json
import sys
from pathlib import Path

import numpy as np

from medidas import ler_det, medir_deteccao, pct

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import caminhos  # noqa: E402

EST = caminhos.referencias() / "estudo_cenas"
SCR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
tot = {}
for v in range(1, 5):
    m = medir_deteccao(ler_det(EST / f"det/v{v}.jsonl"), 4)
    for k, x in m.items():
        tot.setdefault(k, []).extend(x if isinstance(x, list) else [x])
eventos = [21.4, 10.1, 10.7, 13.3]          # medido na análise (mudanças visuais/min)
base = {
    "fonte": "4 vídeos de referência, detecção a 4 fps (estudo_cenas/det)",
    "eventos_por_min": {"min": min(eventos), "max": max(eventos)},
    "frac_so_texto": {"media": round(float(np.mean(tot["frac_so_texto"])), 3), "min": round(min(tot["frac_so_texto"]), 3), "max": round(max(tot["frac_so_texto"]), 3)},
    "altura_texto_solo_px": pct(tot["altura_texto_solo"], (10, 25, 50, 75, 90)),
    "largura_texto_solo_px": pct(tot["largura_texto_solo"], (10, 25, 50, 75, 90)),
    "altura_texto_junto_px": pct(tot["altura_texto_junto"], (10, 25, 50, 75, 90)),
    "altura_1card_px": pct(tot["altura_1card"], (10, 25, 50, 75, 90)),
    "altura_2cards_px": pct(tot["altura_2cards"], (10, 25, 50, 75, 90)),
    "tempo_assets_s": pct(tot["tempo_assets"], (10, 25, 50, 75, 90)),
    "frac_vazio": {"media": round(float(np.mean(tot["frac_vazio"])), 3)},
    "palco_vazio_entre_cenas_s": {"mediana": 0.15, "p90": 0.25, "max_no_conteudo": 0.3},
    "texto_sobre_imagem_frac": 0.30,
    "palavras_texto_solo": [2, 6],
    "max_textos_solo_seguidos": 4,
}
Path("referencia.json").write_text(json.dumps(base, ensure_ascii=False, indent=2))
print(json.dumps(base, ensure_ascii=False, indent=1))
