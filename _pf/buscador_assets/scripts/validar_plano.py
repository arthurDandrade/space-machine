"""Confere o plano.json e preenche o tempo de cada asset pela palavra-gatilho.

Uso: python scripts/validar_plano.py <projeto>

- Ids únicos, tipos válidos, campos obrigatórios.
- Para cada asset sem "tempo" (ou com --recalcular), procura a palavra-gatilho na
  narração dentro da janela da cena e grava o tempo de início dessa palavra.
- Lista o que não foi encontrado para ser corrigido à mão.
"""
import argparse
import re
from pathlib import Path

from comum import gravar_json, iter_assets, ler_json, log

TIPOS = {"foto", "historica", "recorte", "mapa", "logo", "bandeira", "video"}


def norm(p):
    return re.sub(r"[^a-z0-9]", "", p.lower())


def achar_gatilho(palavras, gatilho, ini, fim):
    alvo = [norm(x) for x in gatilho.split() if norm(x)]
    if not alvo:
        return None
    janela = [w for w in palavras if ini - 1.0 <= w["ini"] <= fim + 1.0]
    for k in range(len(janela) - len(alvo) + 1):
        if all(norm(janela[k + j]["p"]).startswith(alvo[j][:5]) for j in range(len(alvo))):
            return janela[k]["ini"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--recalcular", action="store_true")
    a = ap.parse_args()
    proj = Path(a.projeto)
    plano = ler_json(proj / "plano.json")
    palavras = ler_json(proj / "_work" / "palavras.json", [])
    fim_audio = palavras[-1]["fim"] if palavras else 1e9

    erros, avisos, ids = [], [], set()
    n_assets = n_cenas = 0
    for item in plano.get("itens", []):
        for cena in item.get("cenas", []):
            n_cenas += 1
            if not (0 <= cena.get("inicio", -1) < cena.get("fim", -1) <= fim_audio + 1):
                erros.append(f"cena {cena.get('id')}: inicio/fim inválidos")
    for item, cena, asset in iter_assets(plano):
        n_assets += 1
        aid = asset.get("id")
        if not aid or aid in ids:
            erros.append(f"asset sem id ou id repetido: {aid}")
        ids.add(aid)
        if asset.get("tipo") not in TIPOS:
            erros.append(f"{aid}: tipo inválido '{asset.get('tipo')}'")
        if not (asset.get("buscas") or asset.get("buscas_por_fonte")):
            erros.append(f"{aid}: sem buscas")
        if cena is None:
            continue
        if palavras and (a.recalcular or asset.get("tempo") is None):
            t = achar_gatilho(palavras, asset.get("gatilho", ""), cena["inicio"], cena["fim"])
            if t is None:
                avisos.append(f"{aid}: gatilho '{asset.get('gatilho')}' não encontrado na cena "
                              f"{cena['id']} ({cena['inicio']:.1f}–{cena['fim']:.1f}s)")
            else:
                asset["tempo"] = t
        # Vídeo fica na tela do gatilho até o fim da cena (+0,3 s da saída animada).
        if asset.get("tipo") == "video" and (a.recalcular or not asset.get("duracao")):
            ini = asset.get("tempo", cena["inicio"])
            asset["duracao"] = round(max(1.0, cena["fim"] - ini + 0.3), 1)
    gravar_json(proj / "plano.json", plano)
    log(f"{len(plano.get('itens', []))} itens, {n_cenas} cenas, {n_assets} assets.")
    for e in erros:
        log("ERRO  " + e)
    for w in avisos:
        log("AVISO " + w)
    if not erros:
        log("Plano OK.")


if __name__ == "__main__":
    main()
