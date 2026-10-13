"""Textos do painel em um lugar só (textos/<idioma>.json). Uso nos templates: {{ t("nav.inicio") }}."""
import json
from functools import lru_cache
from pathlib import Path

PASTA = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def _idioma(idioma):
    try:
        return json.loads((PASTA / f"{idioma}.json").read_text())
    except FileNotFoundError:
        return {}


def t(chave, idioma="pt"):
    return _idioma(idioma).get(chave) or _idioma("pt").get(chave) or chave
