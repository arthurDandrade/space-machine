"""Linha de base: quanto as conversas e os subagentes do Claude Code gastaram até hoje.

Uso: python -m estudio.medir_sessoes [--projeto ~/.claude/projects/-Users-arthur-Canais-ProFootball] [--tipo escolher-assets]

Soma o `usage` de cada chamada (sem repetir o mesmo requestId) dos transcripts. "Equivalente" pondera como a
cobrança: entrada 1x, escrita de cache 1,25x, leitura de cache 0,1x, saída 5x (em tokens de entrada).
Para o escolher-assets, divide pelo nº de escolhas do bloco (escolhas.json) para dar o gasto por asset.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

PADRAO = Path.home() / ".claude/projects/-Users-arthur-Canais-ProFootball"
PESOS = {"input_tokens": 1, "cache_creation_input_tokens": 1.25, "cache_read_input_tokens": 0.1, "output_tokens": 5}
RE_BLOCO = re.compile(r"(/Users/arthur/Canais/[^\s\"'`]+?/blocos/\d+)")


def somar(jsonl):
    vistos, tot, primeiro, modelo, data = set(), defaultdict(int), None, None, None
    imagens = 0
    for linha in open(jsonl, encoding="utf-8"):
        try:
            d = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if primeiro is None and d.get("type") == "user":
            c = d["message"]["content"]
            primeiro = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
            data = (d.get("timestamp") or "")[:10]
        if d.get("type") != "assistant":
            continue
        for bloco in d["message"].get("content") or []:
            if isinstance(bloco, dict) and bloco.get("type") == "tool_use" and bloco.get("name") == "Read" \
                    and str(bloco.get("input", {}).get("file_path", "")).lower().endswith((".jpg", ".png")):
                imagens += 1
        rid = d.get("requestId") or d.get("uuid")
        if rid in vistos:
            continue
        vistos.add(rid)
        modelo = d.get("requestedModel") or d["message"].get("model") or modelo
        for k in PESOS:
            tot[k] += (d["message"].get("usage") or {}).get(k, 0) or 0
        tot["chamadas"] += 1
    tot["equivalente"] = int(sum(tot[k] * p for k, p in PESOS.items()))
    tot["imagens_lidas"] = imagens
    return tot, primeiro or "", modelo, data


def n_escolhas(prompt):
    m = RE_BLOCO.search(prompt)
    if not m:
        return None, None
    bloco = Path(m.group(1))
    esc = bloco / "escolhas.json"
    try:
        return bloco, len(json.loads(esc.read_text()))
    except Exception:
        return bloco, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projeto", default=str(PADRAO))
    ap.add_argument("--tipo", help="só um tipo de subagente (ex.: escolher-assets)")
    a = ap.parse_args()
    raiz = Path(a.projeto).expanduser()

    por_tipo = defaultdict(lambda: defaultdict(int))
    linhas = []
    for meta in sorted(raiz.glob("*/subagents/*.meta.json")):
        info = json.loads(meta.read_text())
        tipo = info.get("agentType", "?")
        if a.tipo and tipo != a.tipo:
            continue
        tot, prompt, modelo, data = somar(meta.with_name(meta.name.replace(".meta.json", ".jsonl")))
        bloco, n = n_escolhas(prompt) if tipo == "escolher-assets" else (None, None)
        linhas.append((data, tipo, info.get("description", "")[:45], modelo, tot, n))
        for k, v in tot.items():
            por_tipo[tipo][k] += v
        por_tipo[tipo]["execucoes"] += 1
        if n:
            por_tipo[tipo]["assets"] += n
            por_tipo[tipo]["equiv_com_assets"] += tot["equivalente"]

    print(f"{'data':10} {'tipo':16} {'descrição':45} {'chamadas':>8} {'equiv.':>10} {'imgs':>5} {'assets':>6} {'equiv/asset':>11}")
    for data, tipo, desc, modelo, tot, n in linhas:
        por_asset = f"{tot['equivalente'] // n:,}" if n else "-"
        print(f"{data:10} {tipo:16} {desc:45} {tot['chamadas']:>8} {tot['equivalente']:>10,} {tot['imagens_lidas']:>5} "
              f"{n or '-':>6} {por_asset:>11}")
    print("\nPor tipo de subagente:")
    for tipo, t in por_tipo.items():
        extra = ""
        if t.get("assets"):
            extra = f" · {t['equiv_com_assets'] // t['assets']:,} equiv./asset ({t['assets']} assets)"
        print(f"  {tipo}: {t['execucoes']} execuções · {t['equivalente']:,} tokens equiv. · "
              f"{t['equivalente'] // max(1, t['execucoes']):,} por execução{extra}")

    # conversas principais (fora dos subagentes), para ter a ordem de grandeza
    total_main = defaultdict(int)
    for j in raiz.glob("*.jsonl"):
        tot, *_ = somar(j)
        for k, v in tot.items():
            total_main[k] += v
    print(f"\nConversas principais: {total_main['chamadas']:,} chamadas · {total_main['equivalente']:,} tokens equiv.")


if __name__ == "__main__":
    main()
