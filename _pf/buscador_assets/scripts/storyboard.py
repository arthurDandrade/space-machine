"""Storyboard de um bloco: cena por cena, com o tempo na narração, o tipo de cena (código da Biblioteca de
Cenas, já nas 60 variações) e o que cada asset precisa mostrar. Mede a variedade e o ritmo e avisa o que
está fora das regras ANTES da busca.

Uso: python scripts/storyboard.py <projeto_do_bloco> [--item 01]
Precisa do cenas.json já compilado (plano.json + edicao/plano_edicao_<item>.json) e de _work/palavras.json.
Saída: <projeto>/storyboard_<item>.md  +  resumo e AVISOS no terminal (código 1 se houver aviso).

Criado em 2026-10-06 (vídeo "Who Makes the NFL Possible": 76% das cenas ficaram em B/C1/A, só 15 dos
60 tipos usados, ritmo 3–8 mudanças/min contra 10–21 nas referências).
"""
import argparse
import json
import sys
from pathlib import Path

NOMES = {
    "A1": "frase", "A2": "frase que se completa", "A3": "frase em 2 linhas", "A4": "frases encadeadas",
    "B1": "card grande", "B2": "card vertical", "B3": "card + frases por cima", "B4": "card + rótulo ao lado",
    "B5": "card + rótulos que trocam", "B6": "troca no mesmo quadro", "B7": "palavra/número no card",
    "B9": "lista que acumula", "B10": "card que abre espaço p/ nome", "B11": "foco por cima",
    "C1": "par lado a lado", "C2": "cascata", "C4": "comparação rotulada", "C5": "foto + mapa",
    "C8": "âncora fixa (um card troca)", "C9": "pilha", "D1": "trio", "D2": "1 grande + pequenos",
    "D3": "pessoa–objeto–pessoa", "D4": "esteira", "D5": "sanduíche", "D6": "baralho", "D7": "recorte + par",
    "E2": "recorte + card", "E3": "recorte + texto", "E4": "logo no canto", "E5": "bandeira/logo colado ao lado",
    "E6": "diagrama + card", "F8": "retrato → mapa → data", "F9": "lugar em camadas", "G1": "citação",
    "G2": "tabela", "G3": "gráfico", "M1": "mapa sozinho", "M3": "mapa que troca", "M4": "par de mapas",
    "M5": "card + globo", "M6": "silhueta + mapa", "M7": "bandeira no mapa", "LOGOS": "logos",
}
CARD_UNICO = {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B9", "B10", "M1"}
TEXTO_SOLO = {"A1", "A2", "A3", "A4"}

# metas (referências v1–v8 + o que o QA mede)
MIN_VARIACOES, MAX_CARD_UNICO, MAX_SEGUIDOS = 8, 0.35, 2
MIN_ASSET_S, MIN_ASSETS_MIN, MIN_CENAS_F = 1.8, 15.0, 0.40   # assets/min: meta da nota 20–25, aviso abaixo de 15
TEXTO_SOLO_FAIXA = (0.12, 0.35)


def variacao(est_plan, est_ed):
    """Traduz o layout do cenas.json para a variação da biblioteca (as 60), olhando os campos dos cards."""
    lay = est_plan["layout"]
    cards = est_plan.get("cards", [])
    if lay == "A":
        t = (est_plan.get("textos") or [""])[0]
        opc = t[2] if isinstance(t, list) and len(t) > 2 else ""
        return {"cresce": "A2", "2linhas": "A3"}.get(opc, "A1")
    if lay == "B":
        c = cards[0] if cards else {}
        if c.get("mapa"):
            return "M1"
        if c.get("troca"):
            return "B6"
        if c.get("sticker"):
            return "E4"
        if c.get("sobre"):
            return "B3" if len(c["sobre"]) > 1 else "B7"
        return "B2" if (est_ed.get("cards") or [{}])[0].get("orientacao") == "retrato" else "B1"
    if lay == "C1":
        mapas = sum(1 for c in cards if c.get("mapa"))
        if mapas >= 2:
            return "M4"
        if mapas:
            return "C5"
        if any(c.get("troca") for c in cards):
            return "C8"
        if any(c.get("acima") for c in cards):
            return "C4"
    if lay == "M3" or any(c.get("dissolve") for c in cards):
        return "M3"
    if any((c.get("sticker") or {}).get("pos") == "dentro" for c in cards):
        return "M7"
    return lay


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--item")
    a = ap.parse_args()
    proj = Path(a.projeto)
    cen = json.loads((proj / "cenas.json").read_text())
    item = next(i for i in cen["itens"] if not a.item or i["id"] == a.item)
    iid = item["id"]
    ed = json.loads((proj / "edicao" / f"plano_edicao_{iid}.json").read_text())
    plano = json.loads((proj / "plano.json").read_text())
    pal = json.loads((proj / "_work" / "palavras.json").read_text())
    ativos = {}
    for it in plano["itens"]:
        for c in it["cenas"]:
            for x in c["assets"]:
                ativos[x["id"]] = x
        if it.get("titulo_asset"):
            ativos[it["titulo_asset"]["id"]] = it["titulo_asset"]
    fim_bloco = ed["fim"]

    def fala(ini, fim):
        return " ".join(w["p"] for w in pal if ini - 0.05 <= w["ini"] < fim - 0.05)

    # linha do tempo de estados
    estados = []
    for ci, (c_plan, c_ed) in enumerate(zip(item["cenas"], ed["cenas"])):
        for ei, (e_plan, e_ed) in enumerate(zip(c_plan["estados"], c_ed["estados"])):
            estados.append({"cena": ci + 1, "n_est": len(c_plan["estados"]), "plan": e_plan, "ed": e_ed,
                            "ini": e_ed["ini"], "var": variacao(e_plan, e_ed)})
    for k, e in enumerate(estados):
        e["fim"] = estados[k + 1]["ini"] if k + 1 < len(estados) else fim_bloco

    linhas, avisos, entradas, curtos = [], [], 0, []   # entradas = assets de imagem/vídeo que entram na tela
    tit = ed.get("titulo", {})
    linhas.append(f"| 0 | {tit.get('t', 0):.1f}–{tit.get('fim', 0):.1f} s | {fala(0, tit.get('fim', 0))} | "
                  f"E1 título | {tit.get('asset', '')}: recorte — {ativos.get(tit.get('asset'), {}).get('descricao', '')} | "
                  f"{tit.get('texto', '')} |")
    for e in estados:
        assets, textos = [], []
        for cd in e["ed"].get("cards", []):
            seq = [(cd.get("asset") or cd.get("arquivo", "gerado"), cd["t"])] + [(t.get("asset") or t.get("arquivo", "gerado"), t["t"]) for t in cd.get("troca", [])]
            for k, (aid, t0) in enumerate(seq):
                t1 = seq[k + 1][1] if k + 1 < len(seq) else e["fim"]
                dur = t1 - t0
                entradas += 1
                x = ativos.get(aid, {})
                marca = " ⚠️" if dur < MIN_ASSET_S else ""
                if dur < MIN_ASSET_S:
                    curtos.append(f"{aid} {dur:.1f}s")
                assets.append(f"**{aid}** {x.get('tipo', 'gerado')}"
                              f"{' ' + x['orientacao'] if x.get('orientacao') else ''}: {x.get('descricao') or ('mapa/tabela gerado: ' + Path(aid).name)} "
                              f"(entra {t0:.1f}s, {dur:.1f}s na tela{marca})")
            for k in ("lateral", "sticker"):
                if cd.get(k):
                    entradas += 1
                    x = cd[k]
                    aid = x[0] if isinstance(x, list) else x.get('asset', x.get('id', ''))   # sticker = [asset, t]
                    assets.append(f"{k}: {ativos.get(aid, {}).get('descricao', aid)}")
            for k in ("sobre", "acima", "legenda"):
                for t in cd.get(k, []) if isinstance(cd.get(k), list) else ([cd[k]] if cd.get(k) else []):
                    textos.append(str(t[0] if isinstance(t, list) else t))
        for k in ("textos", "rotulos"):
            for t in e["ed"].get(k, []):
                textos.append(str(t[0] if isinstance(t, list) else t))
        nome = NOMES.get(e["var"], "")
        f_tag = " · seq." if e["n_est"] > 1 else ""
        linhas.append(f"| {e['cena']} | {e['ini']:.1f}–{e['fim']:.1f} s | {fala(e['ini'], e['fim'])} | "
                      f"{e['var']} {nome}{f_tag} | {'<br>'.join(assets) or '—'} | {' / '.join(textos) or '—'} |")

    # métricas
    dur_total = max(fim_bloco - (tit.get("fim") or 0), 1)
    vars_ = [e["var"] for e in estados]
    distintas = sorted(set(vars_))
    n_unico = sum(1 for v in vars_ if v in CARD_UNICO)
    seguidos, maior = 0, 0
    for v in vars_:
        seguidos = seguidos + 1 if v in CARD_UNICO else 0
        maior = max(maior, seguidos)
    t_texto = sum(e["fim"] - e["ini"] for e in estados if e["var"] in TEXTO_SOLO)
    cenas_f = len({e["cena"] for e in estados if e["n_est"] > 1}) / max(len(item["cenas"]), 1)
    mud_min = entradas / dur_total * 60
    if len(distintas) < MIN_VARIACOES:
        avisos.append(f"só {len(distintas)} variações diferentes (meta ≥ {MIN_VARIACOES}): {', '.join(distintas)}")
    if n_unico / len(vars_) > MAX_CARD_UNICO:
        avisos.append(f"{n_unico}/{len(vars_)} estados são card único ({n_unico/len(vars_):.0%}; meta ≤ {MAX_CARD_UNICO:.0%})")
    if maior > MAX_SEGUIDOS:
        avisos.append(f"{maior} cards únicos seguidos (máx. {MAX_SEGUIDOS})")
    if curtos:
        avisos.append(f"assets/trocas com menos de {MIN_ASSET_S}s: {', '.join(curtos)}")
    # tempo dos nomes/textos (positions, 2026-10-12): B10 sem tempo de abrir o espaço, rótulos trocando a cada
    # ~0,8 s, última palavra colada na troca de cena e "cresce" que não completa a frase anterior
    tempos = []
    for k, e in enumerate(estados):
        ed_ = e["ed"]
        rs = [r for r in (ed_.get("rotulos") or []) if isinstance(r, list)]
        ts = [x for x in (ed_.get("textos") or []) if isinstance(x, list)]
        if ed_.get("layout") == "B10" and rs and rs[0][1] - e["ini"] < 1.5:
            tempos.append(f"B10 {e['ini']:.1f}s: \"{rs[0][0]}\" entra {rs[0][1] - e['ini']:.1f}s depois do card "
                          f"(mín. 1,5 — use B4 ou comece o estado antes)")
        for r0, r1 in (zip(rs, rs[1:]) if ed_.get("layout") != "B9" else []):   # B9 empilha, não troca
            if r1[1] - r0[1] < 1.2:
                tempos.append(f"rótulos \"{r0[0]}\" → \"{r1[0]}\" a {r1[1] - r0[1]:.1f}s (mín. 1,2)")
        fim_txt = [x for x in rs + ts]
        if fim_txt and k + 1 < len(estados) and ed_.get("layout") != "A4":
            u = max(fim_txt, key=lambda x: x[1])
            if e["fim"] - u[1] < 1.2:
                tempos.append(f"\"{u[0]}\" fica {e['fim'] - u[1]:.1f}s antes da troca em {e['fim']:.1f}s (mín. 1,2 — "
                              f"comece o estado seguinte uma palavra depois)")
        if ed_.get("layout") == "A4":
            for x0, x1 in zip(ts, ts[1:]):
                if x1[1] - x0[1] < 1.0:
                    tempos.append(f"A4 \"{x0[0]}\" → \"{x1[0]}\" a {x1[1] - x0[1]:.1f}s (mín. 1,0 — o editor empilha; "
                                  f"se não for lista, junte numa frase só)")
        for j, x in enumerate(ts):
            if len(x) > 2 and x[2] == "cresce":
                ant = ts[j - 1][0] if j else ((estados[k - 1]["ed"].get("textos") or [[""]])[-1][0] if k else "")
                base = str(ant).strip(" ,.;:").lower()
                if not (base and str(x[0]).lower().startswith(base)):
                    tempos.append(f"\"{x[0]}\" marcado \"cresce\" mas não começa com \"{ant}\" (tire o \"cresce\")")
    if tempos:
        avisos.append("tempo/encadeamento de textos: " + "; ".join(tempos))
    if mud_min < MIN_ASSETS_MIN:
        avisos.append(f"{mud_min:.1f} assets/min (meta 20–25; mínimo {MIN_ASSETS_MIN:.0f})")
    if cenas_f < MIN_CENAS_F:
        avisos.append(f"só {cenas_f:.0%} das cenas evoluem com mais de um estado (meta ≥ {MIN_CENAS_F:.0%})")
    if not TEXTO_SOLO_FAIXA[0] <= t_texto / dur_total <= TEXTO_SOLO_FAIXA[1]:
        avisos.append(f"texto solo em {t_texto/dur_total:.0%} do tempo (meta {TEXTO_SOLO_FAIXA[0]:.0%}–{TEXTO_SOLO_FAIXA[1]:.0%})")

    resumo = (f"{len(item['cenas'])} cenas, {len(estados)} estados, {sum(1 for e in estados for _ in e['ed'].get('cards', []))} cards · "
              f"{len(distintas)} variações ({', '.join(distintas)}) · card único {n_unico/len(vars_):.0%} · "
              f"máx. {maior} seguidos · {mud_min:.1f} assets/min · cenas que evoluem {cenas_f:.0%} · "
              f"texto solo {t_texto/dur_total:.0%}")
    md = [f"# Storyboard — {item['nome']} (bloco {iid})", "",
          f"Narração: {fim_bloco:.1f} s · {resumo}", ""]
    md += ["## ⚠️ Fora das regras", ""] + [f"- {x}" for x in avisos] + [""] if avisos else ["✅ Dentro das regras de variedade e ritmo.", ""]
    md += ["| Cena | Tempo | Narração | Tipo de cena | Assets (o que mostrar) | Texto na tela |",
           "|---|---|---|---|---|---|"] + linhas
    saida = proj / f"storyboard_{iid}.md"
    saida.write_text("\n".join(md) + "\n")
    print(resumo)
    for x in avisos:
        print("AVISO " + x)
    print(f"→ {saida}")
    sys.exit(1 if avisos else 0)


if __name__ == "__main__":
    main()
