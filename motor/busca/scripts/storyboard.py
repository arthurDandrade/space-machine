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
import collections
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import caminhos  # noqa: E402  (motor/caminhos.py: o formato do canal e os arquivos dele)

# A Biblioteca de Cenas e as metas são do FORMATO do canal: formatos/<formato>/biblioteca_cenas.json
# (nomes das variações, quais são card único, quais são texto solo e o que medir).
BIBLIOTECA = json.loads(caminhos.do_formato("cenas").read_text())
NOMES = BIBLIOTECA["nomes"]
CARD_UNICO = set(BIBLIOTECA["card_unico"])
TEXTO_SOLO = set(BIBLIOTECA["texto_solo"])
_M = BIBLIOTECA["metas"]
MIN_VARIACOES, MAX_CARD_UNICO, MAX_SEGUIDOS = _M["min_variacoes"], _M["max_card_unico"], _M["max_seguidos"]
MIN_ASSET_S, MIN_ASSETS_MIN, MIN_CENAS_F = _M["min_asset_s"], _M["min_assets_min"], _M["min_cenas_f"]
TEXTO_SOLO_FAIXA = tuple(_M["texto_solo_faixa"])
# quantas vezes um tipo de cena pode aparecer no bloco: 1 no explained (60 variações); o bestiário tem 7 e repete
MAX_REPETICOES = _M.get("max_repeticoes", 1)


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


def ler_ativos(plano):
    ativos = {}
    for it in plano["itens"]:
        for c in it["cenas"]:
            for x in c["assets"]:
                ativos[x["id"]] = x
        if it.get("titulo_asset"):
            ativos[it["titulo_asset"]["id"]] = it["titulo_asset"]
    return ativos


def medir(item, ed, pal, ativos):
    """Mede um item (o bloco, ou um capítulo do vídeo inteiro): devolve as linhas da tabela, os avisos, o resumo e a
    linha do tempo de estados (cada um com a variação "var")."""
    iid = item["id"]
    # os tempos do plano de edição contam do começo do item; os da transcrição, do começo do áudio
    off = ed.get("offset_audio", 0)
    fim_bloco = ed["fim"]

    def fala(ini, fim):
        return " ".join(w["p"] for w in pal if ini + off - 0.05 <= w["ini"] < fim + off - 0.05)

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
    ref = lambda c_: c_.get("asset") or c_.get("arquivo", "gerado")
    for i_e, e in enumerate(estados):
        assets, textos = [], []
        for cd in e["ed"].get("cards", []):
            seq = [(cd.get("asset") or cd.get("arquivo", "gerado"), cd["t"])] + [(t.get("asset") or t.get("arquivo", "gerado"), t["t"]) for t in cd.get("troca", [])]
            # a mesma imagem do estado anterior (câmera contínua do bestiário) não é entrada nova
            continua = i_e and any(ref(x) == ref(cd) for x in estados[i_e - 1]["ed"].get("cards", []))
            for k, (aid, t0) in enumerate(seq):
                t1 = seq[k + 1][1] if k + 1 < len(seq) else e["fim"]
                k2 = i_e + 1
                while k == len(seq) - 1 and k2 < len(estados) and \
                        any(ref(x) == aid for x in estados[k2]["ed"].get("cards", [])):
                    t1 = estados[k2]["fim"]
                    k2 += 1
                dur = t1 - t0
                entradas += 1                # câmera nova na mesma imagem também é mudança na tela
                x = ativos.get(aid, {})
                curto = dur < MIN_ASSET_S and not (continua and k == 0)
                marca = " ⚠️" if curto else ""
                if curto:
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
        e["continua"] = bool(i_e and any(ref(x) in {ref(y) for y in estados[i_e - 1]["ed"].get("cards", [])}
                                         for x in e["ed"].get("cards", [])))
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
    # pilha (C9) com os cards na mesma palavra: entram juntos e parecem um card só (2026-10-13)
    pilhas = [f"{e['ini']:.1f}s" for e in estados if e["ed"].get("layout") == "C9"
              and len({round(c.get("t", 0), 2) for c in e["ed"].get("cards", [])}) < len(e["ed"].get("cards", []))]
    if pilhas:
        avisos.append("pilha (C9) com os cards na mesma palavra em " + ", ".join(pilhas)
                      + ": dê um gatilho para cada card (o de trás numa palavra, o da frente numa palavra depois)")
    # o estado que continua a mesma imagem (câmera contínua) não é um tipo de cena novo
    repetidos = {v: n for v, n in collections.Counter(e["var"] for e in estados if not e.get("continua")).items()
                 if n > MAX_REPETICOES}
    if repetidos:
        avisos.append(f"tipo de cena repetido no bloco (cada um no máximo {MAX_REPETICOES}x; troque por outra variação da biblioteca): "
                      + ", ".join(f"{v} {NOMES.get(v, '')} ×{n}".replace("  ", " ") for v, n in sorted(repetidos.items())))
    if not TEXTO_SOLO_FAIXA[0] <= t_texto / dur_total <= TEXTO_SOLO_FAIXA[1]:
        avisos.append(f"texto solo em {t_texto/dur_total:.0%} do tempo (meta {TEXTO_SOLO_FAIXA[0]:.0%}–{TEXTO_SOLO_FAIXA[1]:.0%})")

    resumo = (f"{len(item['cenas'])} cenas, {len(estados)} estados, {sum(1 for e in estados for _ in e['ed'].get('cards', []))} cards · "
              f"{len(distintas)} variações ({', '.join(distintas)}) · repetidas {len(vars_) - len(distintas)} · card único {n_unico/len(vars_):.0%} · "
              f"máx. {maior} seguidos · {mud_min:.1f} assets/min · cenas que evoluem {cenas_f:.0%} · "
              f"texto solo {t_texto/dur_total:.0%}")
    return {"linhas": linhas, "avisos": avisos, "resumo": resumo, "estados": estados, "fim": fim_bloco}


def tabela(linhas):
    return ["| Cena | Tempo | Narração | Tipo de cena | Assets (o que mostrar) | Texto na tela |",
            "|---|---|---|---|---|---|"] + linhas


def bloco(proj, item_id):
    cen = json.loads((proj / "cenas.json").read_text())
    item = next(i for i in cen["itens"] if not item_id or i["id"] == item_id)
    iid = item["id"]
    ed = json.loads((proj / "edicao" / f"plano_edicao_{iid}.json").read_text())
    plano = json.loads((proj / "plano.json").read_text())
    pal = json.loads((proj / "_work" / "palavras.json").read_text())
    r = medir(item, ed, pal, ler_ativos(plano))
    avisos = r["avisos"]
    md = [f"# Storyboard — {item['nome']} (bloco {iid})", "",
          f"Narração: {r['fim']:.1f} s · {r['resumo']}", ""]
    md += ["## ⚠️ Fora das regras", ""] + [f"- {x}" for x in avisos] + [""] if avisos else ["✅ Dentro das regras de variedade e ritmo.", ""]
    md += tabela(r["linhas"])
    saida = proj / f"storyboard_{iid}.md"
    saida.write_text("\n".join(md) + "\n")
    print(r["resumo"])
    for x in avisos:
        print("AVISO " + x)
    print(f"→ {saida}")
    return 1 if avisos else 0


def _busca_principal(cd):
    return (cd.get("buscas") or [""])[0].strip().lower()


def video(proj):
    """O vídeo inteiro (fluxo "video", 2026-11-05): cada capítulo medido como um bloco, menos a regra de não repetir
    tipo de cena (que agora vale para o vídeo, com folga), e mais o que só aparece olhando o vídeo todo — medido no
    "worst draft pick" e no "draft explained", feitos bloco a bloco: as mesmas ~10 variações em quase todo bloco
    (A1 em 9 de 9), 11 das 44 nunca usadas, blocos abrindo igual e a mesma busca em 4 blocos."""
    cen = json.loads((proj / "cenas.json").read_text())
    plano = json.loads((proj / "plano.json").read_text())
    pal = json.loads((proj / "_work" / "palavras.json").read_text())
    ativos = ler_ativos(plano)
    mv = BIBLIOTECA.get("metas_video", {})
    caps, avisos, md_caps, todos = [], [], [], []
    for item in cen["itens"]:
        ed = json.loads((proj / "edicao" / f"plano_edicao_{item['id']}.json").read_text())
        r = medir(item, ed, pal, ativos)
        # repetir tipo de cena dentro do capítulo é medido no vídeo inteiro (abaixo)
        # e quantas variações o vídeo usa também: um capítulo curto (o cold open) não precisa ter 8
        r["avisos"] = [a for a in r["avisos"] if not a.startswith("tipo de cena repetido no bloco")
                       and "variações diferentes (meta" not in a]
        avisos += [f"capítulo {item['id']}: {a}" for a in r["avisos"]]
        md_caps += [f"## Capítulo {item['id']} — {item['nome']}", "", f"{r['fim']:.1f} s · {r['resumo']}", ""]
        md_caps += [f"- ⚠️ {a}" for a in r["avisos"]] + ([""] if r["avisos"] else [])
        md_caps += tabela(r["linhas"]) + [""]
        vs = [e["var"] for e in r["estados"] if not e.get("continua")]
        caps.append({"id": item["id"], "vars": vs})
        todos += [(item["id"], v) for v in vs]
    n = len(todos)
    cont = collections.Counter(v for _, v in todos)
    biblioteca = [v for v in NOMES if v not in mv.get("fora_da_conta", [])]
    # 1) quantas variações da biblioteca o vídeo usa
    usadas = {v for v in cont if v in NOMES}
    meta_uso = math.ceil(mv.get("min_variacoes_frac", 0.75) * len(biblioteca))
    if len(usadas & set(biblioteca)) < meta_uso:
        nunca = [v for v in biblioteca if v not in usadas]
        avisos.append(f"o vídeo usa {len(usadas & set(biblioteca))} das {len(biblioteca)} variações (meta ≥ {meta_uso}); "
                      f"nunca usadas: {', '.join(f'{v} {NOMES[v]}' for v in nunca)}")
    # 2) nenhuma variação muito mais usada que as outras, nem em capítulo demais
    teto = max(mv.get("max_usos_min", 2), math.ceil(mv.get("max_usos_fator", 1.6) * n / max(1, len(biblioteca))))
    demais = [f"{v} ×{c}" for v, c in cont.most_common() if c > teto]
    if demais:
        avisos.append(f"variações usadas demais no vídeo (máx. {teto}x cada em {n} estados): {', '.join(demais)}")
    teto_caps = max(2, math.ceil(mv.get("max_capitulos_frac", 0.5) * len(caps)))
    em_caps = [(v, sum(v in c["vars"] for c in caps)) for v in cont]
    espalhadas = [f"{v} em {k}" for v, k in sorted(em_caps, key=lambda x: -x[1]) if k > teto_caps]
    if espalhadas:
        avisos.append(f"variações em capítulos demais (máx. {teto_caps} de {len(caps)} capítulos cada; é o que deixa "
                      f"todo capítulo com a mesma cara): {', '.join(espalhadas)}")
    # 3) a mesma variação não volta logo
    dist = mv.get("min_distancia", 6)
    perto = []
    for k, (cid, v) in enumerate(todos):
        for j in range(max(0, k - dist + 1), k):
            if todos[j][1] == v:
                perto.append(f"{v} no capítulo {cid} ({k - j} estados depois)")
                break
    if perto:
        avisos.append(f"a mesma variação volta a menos de {dist} estados: " + "; ".join(perto[:12])
                      + (f" (+{len(perto) - 12})" if len(perto) > 12 else ""))
    # 4) capítulos que abrem igual (o 1º estado depois do título) e sequências de 3 que se repetem
    aberturas = collections.Counter(c["vars"][0] for c in caps if c["vars"])
    iguais = [f"{v} abre {k} capítulos" for v, k in aberturas.items() if k > 1]
    if iguais:
        avisos.append("capítulos que abrem com a mesma variação (cada um começa de um jeito): " + ", ".join(iguais))
    trincas = collections.Counter(tuple(v for _, v in todos[k:k + 3]) for k in range(n - 2))
    rep3 = [" → ".join(t) for t, k in trincas.items() if k > 1]
    if rep3:
        avisos.append("sequências de 3 variações que se repetem no vídeo: " + "; ".join(rep3))
    # 5) a mesma busca em capítulos diferentes (a mesma imagem de novo): use "reusar" se for de propósito
    onde = collections.defaultdict(set)
    for item in cen["itens"]:
        for c in item["cenas"]:
            for e in c["estados"]:
                for cd in e.get("cards", []):
                    for x in [cd] + list(cd.get("troca", [])):
                        if isinstance(x, dict) and _busca_principal(x):
                            onde[_busca_principal(x)].add(item["id"])
    dup = [f"\"{q}\" ({', '.join(sorted(ids))})" for q, ids in onde.items() if len(ids) > 1]
    if dup:
        avisos.append("a mesma busca em capítulos diferentes (a imagem vai se repetir; troque o assunto da imagem ou "
                      "use {\"reusar\": \"<id>\"} se for de propósito): " + "; ".join(dup))
    resumo = (f"{len(caps)} capítulos, {n} estados · {len(usadas)} variações usadas · a mais usada "
              f"{cont.most_common(1)[0][0] if cont else '—'} ×{cont.most_common(1)[0][1] if cont else 0}")
    md = [f"# Storyboard do vídeo — {cen.get('titulo', proj.parent.name)}", "", resumo, ""]
    md += ["## ⚠️ Fora das regras", ""] + [f"- {x}" for x in avisos] + [""] if avisos else \
        ["✅ Dentro das regras de variedade e ritmo.", ""]
    md += ["## Variações no vídeo", "", " · ".join(f"{v} ×{c}" for v, c in cont.most_common()), ""] + md_caps
    saida = proj / "storyboard_video.md"
    saida.write_text("\n".join(md) + "\n")
    print(resumo)
    for x in avisos:
        print("AVISO " + x)
    print(f"→ {saida}")
    return 1 if avisos else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--item")
    ap.add_argument("--video", action="store_true", help="o vídeo inteiro: todos os capítulos + as regras do vídeo")
    a = ap.parse_args()
    proj = Path(a.projeto)
    sys.exit(video(proj) if a.video else bloco(proj, a.item))


if __name__ == "__main__":
    main()
