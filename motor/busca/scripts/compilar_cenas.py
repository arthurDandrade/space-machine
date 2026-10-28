"""Compila <projeto>/cenas.json (o planejamento, escrito com palavras da narração) em:
  - plano.json                       → o que buscar (buscar.py / finalizar.py)
  - edicao/plano_edicao_<item>.json  → como montar (editor_ae/gerar_ae2.py)

Uso: python scripts/compilar_cenas.py <projeto>

O planejamento vem PRIMEIRO: cada cena usa um código da Biblioteca de Cenas, e é o layout que decide
o formato do asset (par → retrato, card único → paisagem, PNG → recorte/logo, troca → vídeo...).
Tempos não são escritos à mão: tudo é achado pelas palavras na transcrição (_work/palavras.json).

Formato de cenas.json:
{
 "itens": [{
   "id": "01", "nome": "Adapting the Pass When the Play Breaks Down",
   "titulo": {"descricao": "...", "buscas": ["..."]}            | {"reusar": "01-titulo"},
   "cenas": [
     {"estados": [
       {"layout": "B", "fala": "When pressure forces a quarterback to move,",
        "cards": [{"gatilho": "pressure", "tipo": "video", "descricao": "...", "buscas": ["..."],
                   "sobre": ["forces a quarterback to move"], "legenda": "...", "acima": "Nome",
                   "sticker": {"gatilho": "...", "tipo": "logo", "descricao": "...", "buscas": [...]},
                   "troca": [{"gatilho": "...", "tipo": "video", ...}]}]},
       {"layout": "A", "fala": "the available passing lanes change.",
        "textos": ["the available passing lanes change"]}
     ]}
   ]
 }]
}
- "sem_titulo": true no item = bloco sem card de título (cold open); "nome_fala" = as 2–3 primeiras palavras da fala.
- "nome_fala" no item (opcional): o nome como está na transcrição quando o Whisper erra (ex.: "Lambo Field");
  o "nome" fica com o texto certo, que vai na tela.
- Um asset pode ser {"reusar": "<id já existente>"} ou {"arquivo": "caminho relativo ao projeto"}.
- Textos/rótulos/sobre: "texto" ou ["texto", "gatilho"] ou ["texto", "gatilho", "cresce"|"2linhas"|"abaixo"|"faixa"]
  ("faixa" = branco na faixa azul; no E3 fica ao lado do recorte; no CTA, embaixo do botão).
  Sem gatilho, o gatilho são as 2 primeiras palavras do texto.
- {"layout": "CTA", "fala": "...", "clique": "subscribe", "textos": [["Nome do canal", "Inside", "faixa"]]}:
  botão de inscrever do canal (identidade/cta_botao.png) com pop e o cursor (cta_cursor.png) clicando na palavra.
- "png": true num card = recorte/logo solto (sem quadro).
- "tabela": {...} / "grafico": {...} num card = imagem GERADA por scripts/gerar_tabela.py (dados reais + "fonte").
- "lateral": {"asset"/busca de bandeira | "mapa": {..., "globo": true}, "gatilho": ...} = bandeira (E5/F9) ou globo (M5)
  encostado à direita do card. "dissolve": true num card = as trocas se dissolvem (M3/T3) em vez de corte.
- "mapa": {"eua": ["Missouri"] | "pais": ["Germany"], "pontos": ["Kansas City:39.10:-94.58"], "rotulo": "...",
           "estilo": "cheio"|"contorno", "cor": "azul"|"laranja", "formato": "4:3"} num card = mapa GERADO por
  scripts/gerar_mapa.py (Natural Earth, cores do canal) em assets/mapas/; não entra na busca.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from comum import gravar_json, ler_json, log
import caminhos   # motor/caminhos.py (o comum já põe no path): o formato do canal

# Orientação do asset por variação: é do FORMATO (formatos/<formato>/biblioteca_cenas.json). Cada código está
# explicado em conhecimento/02 - Cenas/Biblioteca de Cenas.md do formato.
ORIENTACAO = json.loads(caminhos.do_formato("cenas").read_text())["orientacao"]


def gerar_mapa(proj, spec):
    """Card com "mapa": desenha o PNG (gerar_mapa.py) e devolve o caminho relativo ao projeto."""
    chave = hashlib.md5(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:10]
    rel = Path("assets") / "mapas" / f"mapa_{chave}.png"
    (proj / rel).parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(Path(__file__).with_name("gerar_mapa.py")), str(proj / rel)]
    for k in ("eua", "pais"):
        if spec.get(k):
            cmd += [f"--{k}"] + list(spec[k])
    for pt in spec.get("pontos", []):
        cmd += ["--ponto", pt]
    for k in ("rotulo", "estilo", "cor", "formato", "vista", "largura"):
        if spec.get(k):
            cmd.append(f"--{k}={spec[k]}")  # "=" para valores que começam com "-" (vista)
    if spec.get("regioes"):
        cmd += ["--regioes"] + list(spec["regioes"])
    for k in ("sem_rotulo", "globo", "silhueta"):
        if spec.get(k):
            cmd.append("--" + k.replace("_", "-"))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"gerar_mapa falhou ({spec}): {r.stderr.strip() or r.stdout.strip()}")
    return rel.as_posix()       # com "/" também no Windows: o gerar_ae2 reconhece o mapa por "/mapas/"


def gerar_tabela(proj, spec):
    """Card com "tabela"/"grafico": desenha o PNG (gerar_tabela.py) e devolve o caminho relativo ao projeto."""
    chave = hashlib.md5(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:10]
    rel = Path("assets") / "graficos" / f"{next(iter(spec))}_{chave}.png"
    (proj / rel).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("gerar_tabela.py")), str(proj / rel),
                        json.dumps(spec)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"gerar_tabela falhou: {r.stderr.strip() or r.stdout.strip()}")
    return rel.as_posix()


def gerado(proj, spec):
    """Troca "mapa"/"tabela"/"grafico" por "arquivo" (imagem gerada, fora da busca)."""
    if spec.get("mapa"):
        return dict(spec, arquivo=gerar_mapa(proj, spec["mapa"]), png=spec.get("png", bool(
            spec["mapa"].get("globo") or spec["mapa"].get("silhueta"))))
    for k in ("tabela", "grafico"):
        if spec.get(k):
            return dict(spec, arquivo=gerar_tabela(proj, {k: spec[k]}))
    return spec


def norm(p):
    return re.sub(r"[^a-z0-9]", "", p.lower())


class Relogio:
    """Acha palavras/frases na transcrição, sempre andando para frente."""

    def __init__(self, palavras):
        self.p = palavras
        self.n = [norm(w["p"]) for w in palavras]
        self.erros = []
        self.avisos = []

    def achar(self, frase, ini, fim, onde):
        alvo = [norm(x) for x in str(frase).split() if norm(x)]
        if not alvo:
            self.erros.append(f"{onde}: gatilho vazio")
            return None
        for k in range(ini, max(ini, min(fim, len(self.n)) - len(alvo) + 1)):
            if all(self.n[k + j] and self.n[k + j].startswith(a[:5]) for j, a in enumerate(alvo)):
                return k
        trecho = " ".join(w["p"] for w in self.p[ini:min(fim, ini + 25)])
        self.erros.append(f"{onde}: não achei '{frase}' em: \"{trecho}...\"")
        return None


def gatilho_de(t):
    if isinstance(t, str):
        return t, " ".join(t.split()[:2]), ""
    texto = t[0]
    gat = t[1] if len(t) > 1 and t[1] else " ".join(texto.split()[:2])
    modo = t[2] if len(t) > 2 else ""
    return texto, gat, modo


def main():
    proj = Path(sys.argv[1]).resolve()
    cenas = ler_json(proj / "cenas.json")
    palavras = ler_json(proj / "_work" / "palavras.json")
    if not palavras:
        raise SystemExit("Rode transcrever.py antes.")
    antigo = ler_json(proj / "plano.json", {"itens": []})
    antigos = {}
    for it in antigo.get("itens", []):
        if it.get("titulo_asset"):
            antigos[it["titulo_asset"]["id"]] = it["titulo_asset"]
        for c in it.get("cenas", []):
            for a in c.get("assets", []):
                antigos[a["id"]] = a
    R = Relogio(palavras)
    usados = set(antigos)
    listados = set()          # ids já existentes nunca são reaproveitados para assets novos
    T = lambda k: palavras[k]["ini"]
    cursor = 0
    plano = {"titulo": cenas.get("titulo", proj.name), "itens": []}
    ids_novos = []

    for item in cenas["itens"]:
        iid = item["id"]
        # início do item = nome falado
        # "nome_fala" = o nome como o Whisper escreveu (ex.: "Lambo Field"); "nome" = o texto certo na tela
        falado = item.get("nome_fala") or item["nome"]
        k_nome = R.achar(" ".join(falado.split()[:3]), cursor, len(palavras), f"item {iid} (nome)")
        k_nome = cursor if k_nome is None else k_nome
        offset = max(0.0, T(k_nome) - 0.04)
        rel = lambda t: round(t - offset, 2)

        # resolve o início de cada estado
        lista = []
        # "sem_titulo": true (cold open, 2026-10-11): não há nome falado nem card de título; "nome_fala" são só as
        # primeiras palavras da narração, para achar o começo do bloco
        sem_titulo = bool(item.get("sem_titulo"))
        cur = k_nome if sem_titulo else k_nome + len(falado.split())
        for ci, cena in enumerate(item["cenas"]):
            for ei, e in enumerate(cena["estados"]):
                onde = f"item {iid} cena {ci + 1} estado {ei + 1}"
                k = R.achar(" ".join(e["fala"].split()[:3]), cur, len(palavras), onde + " (fala)")
                if k is None:
                    continue
                e["_k"], e["_cena"] = k, ci
                cur = k + 1
                lista.append(e)
        # fim do item: última palavra antes do próximo item (ou fim da narração)
        prox_item = len(palavras)
        idx_item = cenas["itens"].index(item)
        if idx_item + 1 < len(cenas["itens"]):
            prox = cenas["itens"][idx_item + 1]
            nk = R.achar(" ".join((prox.get("nome_fala") or prox["nome"]).split()[:3]), cur, len(palavras), "próximo item")
            prox_item = nk if nk is not None else prox_item
        cursor = prox_item
        fim_item = palavras[prox_item - 1]["fim"]

        p_item = {"id": iid, "nome": item["nome"], "inicio": round(offset, 2), "fim": fim_item, "cenas": []}
        ed = {"nome": f"Bloco {iid} - {item['nome'][:40]}", "fim": rel(fim_item), "offset_audio": round(offset, 2),
              "cenas": []}
        # título
        tit = {} if sem_titulo else item.get("titulo", {})
        if tit.get("reusar"):
            ta = dict(antigos.get(tit["reusar"], {"id": tit["reusar"]}))
        else:
            ta = {"id": f"{iid}-titulo", "tipo": "recorte", "papel": "titulo", "descricao": tit.get("descricao", item["nome"]),
                  "buscas": tit.get("buscas", [item["nome"]])}
        ta.update({"gatilho": falado.split()[0], "tempo": T(k_nome)})
        primeiro = T(lista[0]["_k"]) if lista else fim_item
        if not sem_titulo:
            p_item["titulo_asset"] = ta
            ed["titulo"] = {"texto": item["nome"], "asset": ta["id"], "t": rel(T(k_nome)), "fim": rel(primeiro - 0.05)}
        if not sem_titulo and primeiro - T(k_nome) < 1.0:   # nas outras produções o título fica 1–2 s; menos que isso some rápido demais
            R.avisos.append(f"item {iid}: título fica só {primeiro - T(k_nome):.1f}s na tela (mínimo ~1s). "
                            "Comece a 1ª cena numa frase seguinte.")

        n_cena = 0
        cena_atual = None
        for i, e in enumerate(lista):
            k0 = e["_k"]
            k1 = lista[i + 1]["_k"] if i + 1 < len(lista) else prox_item
            ini, fim = T(k0), (T(k1) if k1 < len(palavras) else fim_item)
            if cena_atual is None or e["_cena"] != cena_atual["_ci"]:
                n_cena += 1
                cena_atual = {"_ci": e["_cena"], "id": f"{iid}-{n_cena:02d}", "inicio": ini, "fim": fim,
                              "fala": "", "assets": [], "_letra": 0}
                p_item["cenas"].append(cena_atual)
                ed["cenas"].append({"id": cena_atual["id"], "estados": []})
            cena_atual["fim"] = fim
            cena_atual["fala"] = (cena_atual["fala"] + " " + e["fala"]).strip()
            onde = f"{cena_atual['id']} ({e['layout']}: \"{e['fala'][:30]}\")"
            est = {"layout": e["layout"], "ini": rel(ini)}
            if e.get("saida"):
                est["saida"] = e["saida"]

            def novo_asset(spec, papel, orient, t_gat, dur=None):
                if spec.get("reusar"):
                    a = dict(antigos.get(spec["reusar"], {"id": spec["reusar"]}))
                    if spec["reusar"] not in antigos:
                        R.erros.append(f"{onde}: reusar '{spec['reusar']}' não existe no plano.json antigo")
                    if a["id"] not in listados:      # reaproveitado em 2 lugares: lista uma vez só
                        listados.add(a["id"])
                        cena_atual["assets"].append(a)
                    return {"asset": a["id"]}
                if spec.get("arquivo"):
                    return {"arquivo": spec["arquivo"]}
                while True:
                    letra = chr(ord("a") + cena_atual["_letra"])
                    cena_atual["_letra"] += 1
                    if spec.get("id") or f"{cena_atual['id']}-{letra}" not in usados:
                        break
                tipo = spec.get("tipo", "foto")
                if spec.get("png") and tipo not in ("logo", "bandeira", "recorte"):
                    tipo = "recorte"
                a = {"id": spec.get("id", f"{cena_atual['id']}-{letra}"), "tipo": tipo, "gatilho": spec.get("gatilho"),
                     "papel": papel, "orientacao": spec.get("orientacao", orient),
                     "descricao": spec.get("descricao", ""), "buscas": list(spec.get("buscas", [])), "tempo": t_gat}
                usados.add(a["id"])
                if not spec.get("id"):     # grava o id no card: recompilar não renomeia (perdia as escolhas)
                    spec["id"] = a["id"]
                    ids_novos.append(a["id"])
                for k in ("buscas_por_fonte", "fontes", "quantidade", "lance"):
                    if k in spec:
                        a[k] = spec[k]
                if tipo == "video":
                    a["duracao"] = round(max(1.0, dur), 1)
                    if a["orientacao"] == "retrato":   # vídeo vertical: shorts
                        a["buscas"] += [b + " #shorts" for b in a["buscas"][:2]]
                cena_atual["assets"].append(a)
                return {"asset": a["id"]}

            def tempo(gat, local):
                k = R.achar(gat, k0, max(k1, k0 + 1), f"{onde} {local}")
                return T(k) if k is not None else ini

            if e.get("clique"):          # CTA: palavra em que o cursor clica no botão
                est["clique"] = rel(tempo(e["clique"], "clique"))

            cards = []
            orient = ORIENTACAO.get(e["layout"], "qualquer")
            for j, c in enumerate(e.get("cards", [])):
                c = gerado(proj, c)
                gat = c.get("gatilho") or " ".join(e["fala"].split()[:2])
                t = tempo(gat, f"card {j + 1}")
                o = "paisagem" if (e["layout"] == "D2" and j == 0) else orient
                trocas = [gerado(proj, tr) for tr in c.get("troca", [])]
                t_trocas = [tempo(tr["gatilho"], f"troca de {gat}") for tr in trocas]
                fim_card = t_trocas[0] if trocas else fim
                ref = novo_asset(c, "card", "retrato" if trocas else o, t, fim_card - t + 0.3)
                card = dict(ref, t=rel(t))
                if c.get("png"):
                    card["png"] = True
                if trocas:
                    card["troca"] = []
                    for q, (tr, tt) in enumerate(zip(trocas, t_trocas)):
                        fim_tr = t_trocas[q + 1] if q + 1 < len(t_trocas) else fim
                        card["troca"].append(dict(novo_asset(tr, "card", "retrato", tt, fim_tr - tt + 0.3), t=rel(tt)))
                if c.get("sticker"):
                    st = c["sticker"]
                    tt = tempo(st.get("gatilho", gat), "sticker")
                    sref = novo_asset(dict(st, png=True, tipo=st.get("tipo", "logo")), "sticker", "qualquer", tt)
                    if "asset" in sref and not st.get("id") and not st.get("reusar"):
                        st["id"] = sref["asset"]
                    if "asset" not in sref:
                        R.erros.append(f"{onde}: sticker precisa ser asset (não arquivo)")
                    else:
                        card["sticker"] = [sref["asset"], rel(tt)]
                for campo in ("sobre",):
                    if c.get(campo):
                        seq = []
                        for x in c[campo]:
                            tx, g, _ = gatilho_de(x)
                            seq.append([tx, rel(tempo(g, campo))])
                        card[campo] = seq
                for campo in ("legenda", "acima"):
                    if c.get(campo):
                        tx, g, _ = gatilho_de(c[campo])
                        card[campo] = [tx, rel(tempo(g, campo))]
                if c.get("lateral"):
                    la = gerado(proj, c["lateral"])
                    tl = tempo(la.get("gatilho", gat), "lateral")
                    lref = novo_asset(dict(la, png=True, tipo=la.get("tipo", "bandeira")), "lateral", "qualquer", tl)
                    if "asset" in lref and not la.get("id") and not la.get("reusar"):
                        la["id"] = lref["asset"]
                    card["lateral"] = dict(lref, t=rel(tl), forma="globo" if la.get("mapa", {}).get("globo") else "bandeira")
                if c.get("dissolve"):
                    card["dissolve"] = True
                if c.get("sticker") and c["sticker"].get("pos"):
                    card["sticker_pos"] = c["sticker"]["pos"]
                if c.get("citacao"):
                    ci = dict(c["citacao"])
                    ci["t"] = rel(tempo(ci.pop("gatilho", gat), "citacao"))
                    card["citacao"] = ci
                if c.get("entra"):
                    card["entra"] = c["entra"]
                if c.get("sai"):
                    card["sai"] = c["sai"]
                cards.append(card)
            if cards:
                est["cards"] = cards
            for campo in ("textos", "rotulos"):
                if e.get(campo):
                    seq = []
                    for x in e[campo]:
                        tx, g, modo = gatilho_de(x)
                        item_t = [tx, rel(tempo(g, campo))]
                        if modo:
                            item_t.append(modo)
                        seq.append(item_t)
                    # estado só de texto: o 1º texto entra junto com o estado (senão o palco fica vazio)
                    if campo == "textos" and not cards and e["layout"] != "CTA" and seq and seq[0][1] - est["ini"] > 0.5:
                        seq[0][1] = est["ini"]
                    est[campo] = seq
            ed["cenas"][-1]["estados"].append(est)

        for c in p_item["cenas"]:
            c.pop("_ci", None)
            c.pop("_letra", None)
        plano["itens"].append(p_item)
        gravar_json(proj / "edicao" / f"plano_edicao_{iid}.json", ed)

    # regras de ritmo medidas nas referências
    for item in plano["itens"]:
        ed_i = ler_json(proj / "edicao" / f"plano_edicao_{item['id']}.json")
        ests = [e for c in ed_i["cenas"] for e in c["estados"]]
        com = [e for e in ests if e.get("cards")]
        com_txt = [e for e in com if e.get("textos") or e.get("rotulos") or
                   any(cd.get(k) for cd in e["cards"] for k in ("sobre", "legenda", "acima"))]
        if com and len(com_txt) / len(com) > 0.45:
            R.avisos.append(f"item {item['id']}: {len(com_txt)}/{len(com)} cenas de imagem têm texto "
                            f"(referências: ~30%). Deixe a imagem falar sozinha; texto sobre imagem só para nome/número/data/termo.")
        for i, e in enumerate(ests):
            # B11: o estado anterior continua na tela (desfocado) até o fim do B11
            k_fim = i + 2 if i + 1 < len(ests) and ests[i + 1]["layout"] == "B11" else i + 1
            fim = ests[k_fim]["ini"] if k_fim < len(ests) else ed_i["fim"]
            for cd in e.get("cards", []):
                t = max(e["ini"], cd["t"] - 0.2)
                if fim - t < 1.8:
                    R.avisos.append(f"item {item['id']} ({e['layout']} {e['ini']:.1f}s): "
                                    f"{cd.get('asset') or cd.get('arquivo')} fica só {fim - t:.1f}s na tela (mínimo 1,8s)")
    gravar_json(proj / "plano.json", plano)
    if ids_novos:
        gravar_json(proj / "cenas.json", cenas)
        log(f"ids gravados no cenas.json: {', '.join(ids_novos)}")
    n_assets = sum(len(c["assets"]) for it in plano["itens"] for c in it["cenas"])
    n_est = sum(len(c["estados"]) for c in ed["cenas"]) if plano["itens"] else 0
    log(f"{len(plano['itens'])} item(ns), {sum(len(i['cenas']) for i in plano['itens'])} cenas, "
        f"{n_est} estados (último item), {n_assets} assets.")
    for av in R.avisos:
        log("AVISO " + av)
    if R.erros:
        log("\nCORRIGIR no cenas.json (a palavra tem que estar escrita como na transcrição):")
        for er in R.erros:
            log("  - " + er)
        sys.exit(1)
    log("OK → plano.json + edicao/plano_edicao_<item>.json")


if __name__ == "__main__":
    main()
