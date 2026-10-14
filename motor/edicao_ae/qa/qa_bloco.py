"""Controle de qualidade de um bloco: mede a prévia renderizada + o plano e compara com as referências.

Uso: python qa/qa_bloco.py <projeto> [--item 01] [--video edicao/previa.mp4]

Saída em <projeto>/edicao/:
  qa_<item>.md    relatório (OK / ATENÇÃO / FALHA, com tempos para corrigir)
  qa_<item>.jpg   folha lado a lado: nosso frame × frame de referência do mesmo tipo de cena
Código de saída 1 se houver FALHA.
"""
import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from medidas import cards_validos, estaveis, eventos_por_min, ler_det, medir_deteccao, pct  # noqa: E402

REF = json.loads((AQUI / "referencia.json").read_text())
sys.path.insert(0, str(AQUI.parents[1]))
import caminhos  # noqa: E402

REFS_DIR = caminhos.referencias()        # vídeos de referência do formato (opcionais: sem eles, a folha não compara)
EST = REFS_DIR / "estudo_cenas"
PY = sys.executable
MIN_ASSET = 1.8


class Relatorio:
    def __init__(self):
        self.linhas = []
        self.falhas = 0
        self.atencoes = 0

    def add(self, status, titulo, detalhe, itens=()):
        if status == "FALHA":
            self.falhas += 1
        elif status == "ATENÇÃO":
            self.atencoes += 1
        icone = {"OK": "✅", "ATENÇÃO": "⚠️", "FALHA": "❌"}[status]
        self.linhas.append(f"| {icone} {status} | **{titulo}** | {detalhe} |")
        for it in itens:
            self.linhas.append(f"|  |  | ↳ {it} |")


def num(t):
    return bool(re.search(r"\d", t))


def checar_plano(plano, R):
    est = [e for c in plano["cenas"] for e in c["estados"]]
    fim_total = plano["fim"]
    # 1. texto sobre imagem
    com = [e for e in est if e.get("cards")]
    com_txt = [e for e in com if e.get("textos") or e.get("rotulos") or
               any(cd.get(k) for cd in e["cards"] for k in ("sobre", "legenda", "acima"))]
    fr = len(com_txt) / max(1, len(com))
    st = "OK" if fr <= 0.45 else ("ATENÇÃO" if fr <= 0.6 else "FALHA")
    R.add(st, "Texto sobre imagem", f"{len(com_txt)}/{len(com)} cenas de imagem com texto ({fr:.0%}); referências ~30%")
    # 2. frases (não nome/número) sobre imagem
    frases = []
    for e in com:
        for cd in e["cards"]:
            for tx, t in cd.get("sobre", []) + ([cd["legenda"]] if cd.get("legenda") else []):
                if len(tx.split()) > 3 and not num(tx):
                    frases.append(f"{t:.1f}s \"{tx}\"")
    R.add("OK" if not frases else "ATENÇÃO", "Frases sobre imagem",
          "texto sobre imagem deve ser nome/número/data/termo" + ("" if not frases else f" — {len(frases)} frase(s)"), frases)
    # 3. tempo mínimo de cada asset (pelo plano)
    curtos = []
    for i, e in enumerate(est):
        k_fim = i + 2 if i + 1 < len(est) and est[i + 1]["layout"] == "B11" else i + 1   # B11: anterior fica atrás
        fim = est[k_fim]["ini"] if k_fim < len(est) else fim_total
        for cd in e.get("cards", []):
            fontes = [(cd.get("asset") or cd.get("arquivo"), cd["t"])] + [(x.get("asset"), x["t"]) for x in cd.get("troca", [])]
            for k, (nome, t) in enumerate(fontes):
                f2 = fontes[k + 1][1] if k + 1 < len(fontes) else fim
                d = f2 - max(e["ini"], t - 0.2)
                if d < MIN_ASSET:
                    curtos.append(f"{t:.1f}s {nome}: {d:.1f}s na tela")
    R.add("OK" if not curtos else "FALHA", "Tempo mínimo de cada asset", f"mínimo {MIN_ASSET}s", curtos)
    # 4. texto solo: tamanho das frases e sequência
    longas, seq, max_seq, onde = [], 0, 0, None
    for e in est:
        if e["layout"] in ("A", "A4"):
            seq += len(e.get("textos", []))
            if seq > max_seq:
                max_seq, onde = seq, e["ini"]
            for tx in e.get("textos", []):
                n = len(tx[0].split())
                if n > 6 and (len(tx) < 3 or tx[2] != "2linhas"):
                    longas.append(f"{tx[1]:.1f}s \"{tx[0]}\" ({n} palavras)")
        else:
            seq = 0
    R.add("OK" if not longas else "ATENÇÃO", "Texto solo com 2–6 palavras", "frases maiores ficam pequenas na tela", longas)
    R.add("OK" if max_seq <= REF["max_textos_solo_seguidos"] else "ATENÇÃO", "Textos solo seguidos",
          f"máx. {max_seq} seguidos (em {onde:.1f}s)" if onde is not None else "nenhum", [])
    # 5. variedade de layouts
    lays = [e["layout"] for e in est if e["layout"] not in ("A", "A4")]
    rep = [f"{est[i]['ini']:.1f}s: {lays[i]} 3× seguidas" for i in range(len(lays) - 2)
           if lays[i] == lays[i + 1] == lays[i + 2] and lays[i] != "B"]
    b_seq = max((len(m) for m in re.findall(r"(?:B,)+", ",".join(lays) + ",")), default=0) // 2
    distintos = sorted(set(lays))
    R.add("OK" if not rep and b_seq < 4 else "ATENÇÃO", "Variedade de layouts",
          f"{len(distintos)} layouts de imagem: {', '.join(distintos)}" + (f"; {b_seq} cards únicos (B) seguidos" if b_seq >= 4 else ""), rep)
    seqs = sum(1 for c in plano["cenas"] if len(c["estados"]) > 1 or
               any(len(e.get("cards", [])) > 1 for e in c["estados"]))
    R.add("OK" if seqs / max(1, len(plano["cenas"])) >= 0.3 else "ATENÇÃO", "Cenas que evoluem",
          f"{seqs}/{len(plano['cenas'])} cenas com mais de um elemento/estado (família F)")


def fracao_ocupada(video, bg_arq, fps):
    """{índice do frame a fps: fração da tela diferente do fundo}. Uma passada só pelo vídeo (480×270)."""
    if not bg_arq.exists():
        return {}
    bg = np.load(bg_arq)
    n = 480 * 270 * 3
    pr = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale=480:270",
                           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    out, k = {}, 0
    while True:
        b = pr.stdout.read(n)
        if len(b) < n:
            break
        f = np.frombuffer(b, np.uint8).reshape(270, 480, 3).astype(np.int16)
        out[k] = float((np.abs(f - bg).max(axis=2) > 45).mean())
        k += 1
    pr.wait()
    return out


def checar_render(video, plano, det, R, layout=None):
    fr = ler_det(det)
    fps = 4
    fim = plano["fim"]
    fr_cont = [f for f in fr if f["t"] <= fim]
    ha_texto = None
    if layout and layout.exists():
        tx = [(r["in"], r["out"]) for r in json.loads(layout.read_text())
              if r["tipo"] == "texto" and r.get("estado") != "Título"]
        ha_texto = lambda t: any(a - 0.3 <= t <= b + 0.3 for a, b in tx)
    m = medir_deteccao(fr_cont, fps, ha_texto)
    # eventos por minuto
    ev = eventos_por_min(str(video), fim)
    lo, hi = REF["eventos_por_min"]["min"], REF["eventos_por_min"]["max"]
    R.add("OK" if lo * 0.9 <= ev <= hi * 1.1 else "ATENÇÃO", "Ritmo (mudanças visuais/min)",
          f"{ev:.1f} (referências {lo}–{hi})")
    # quanto de cada frame (4 fps) é diferente do fundo de papel — conferência no pixel para os casos em que
    # o detector se perde (card + globo/bandeira encostados não é retângulo: E5/M5/F9)
    ocup = fracao_ocupada(video, Path(str(det) + ".bg.npy"), fps)
    tem_algo = lambda t: ocup.get(round(t * fps), 0) > 0.08      # >8% da tela = há algo em cena

    # palco vazio longo

    vazios, run = [], []
    for f in fr_cont + [{"t": fim + 1, "cards": [1], "textos": [], "recortes": []}]:
        if not f["cards"] and not f["textos"] and not f["recortes"]:
            run.append(f["t"])
        else:
            if len(run) / fps > 0.5 and not tem_algo(run[len(run) // 2]):
                vazios.append(f"{run[0]:.1f}–{run[-1]:.1f}s ({len(run) / fps:.1f}s)")
            run = []
    R.add("OK" if not vazios else "FALHA", "Palco vazio", "entre cenas deve ser ~0,15s (máx. ~0,3s)", vazios)
    # texto cortado/encostado na borda (zoom da cena empurrando para fora)
    borda, run = [], []
    for f in fr_cont + [{"t": 1e9, "textos": []}]:
        caixas = f.get("cards", []) + f.get("recortes", [])
        dentro = lambda t: any(t[0] >= c[0] - 8 and t[1] >= c[1] - 8 and t[0] + t[2] <= c[0] + c[2] + 8 and
                               t[1] + t[3] <= c[1] + c[3] + 8 for c in caixas)   # texto do próprio vídeo do card
        b = [t for t in f["textos"] if 40 <= t[3] <= 220 and t[2] >= 80 and not dentro(t) and   # >220 px = card borrado saindo, não texto
             (t[0] <= 16 or t[0] + t[2] >= 1904 or t[1] <= 16 or t[1] + t[3] >= 1064)]
        if b:
            run.append(f["t"])
        elif run:
            if len(run) >= 2:      # 1 frame só (0,25 s) = card borrado saindo, não texto cortado
                borda.append(f"{run[0]:.1f}–{run[-1]:.1f}s")
            run = []
    R.add("OK" if not borda else "FALHA", "Texto cortado na borda", "nenhum texto pode encostar na borda do quadro", borda)
    # tamanho do texto solo
    ref_alt = REF["altura_texto_solo_px"]
    alt = m["altura_texto_solo"]
    if alt:
        # texto solo de verdade = quase toda a tela é papel (texto ocupa <15%); senão é card que o detector perdeu
        solo = lambda f: not f["cards"] and not f["recortes"] and f["textos"] and ocup.get(round(f["t"] * fps), 0) < 0.15
        alt = [max(t[3] for t in f["textos"]) for f in estaveis(fr_cont) if solo(f)] or alt
        med = float(np.median(alt))
        peq = [f"{f['t']:.1f}s ({max(t[3] for t in f['textos'])}px)" for f in estaveis(fr_cont)
               if solo(f) and max(t[3] for t in f["textos"]) < ref_alt[0] * 0.75]
        st = "OK" if med >= ref_alt[0] * 0.85 and len(peq) <= 1 else ("ATENÇÃO" if med >= ref_alt[0] * 0.7 else "FALHA")
        R.add(st, "Tamanho do texto solo", f"altura mediana {med:.0f}px (referências {ref_alt[0]:.0f}–{ref_alt[-1]:.0f}px)",
              sorted(set(peq))[:8])
    # texto preto junto de cards (nome acima / rótulo lateral)
    v = m["altura_texto_junto"]
    rj = REF["altura_texto_junto_px"]
    if v:
        med = float(np.median(v))
        st = "OK" if med >= rj[1] * 0.85 else ("ATENÇÃO" if med >= rj[0] * 0.8 else "FALHA")
        R.add(st, "Tamanho do nome/rótulo junto dos cards",
              f"altura mediana {med:.0f}px (referências: mediana {rj[2]:.0f}px, p25 {rj[1]:.0f}px)")
    # tamanho dos cards
    for chave, rot in (("altura_1card", "Card único"), ("altura_2cards", "Par de cards")):
        v = m[chave]
        r = REF[chave + "_px"]
        if v:
            med = float(np.median(v))
            st = "OK" if med >= r[1] * 0.85 else "ATENÇÃO"
            R.add(st, f"Tamanho — {rot}", f"altura mediana {med:.0f}px (referências: mediana {r[2]:.0f}px, p25 {r[1]:.0f}px)")
    # tempo de tela (render)
    t = m["tempo_assets"]
    if t:
        r = REF["tempo_assets_s"]
        R.add("OK" if r[1] * 0.8 <= np.median(t) <= r[3] * 1.2 else "ATENÇÃO", "Tempo de tela dos assets (medido)",
              f"mediana {np.median(t):.1f}s (referências: mediana {r[2]}s, faixa típica {r[1]}–{r[3]}s)")
    # proporção só texto
    fs = m["frac_so_texto"]
    rr = REF["frac_so_texto"]
    R.add("OK" if rr["min"] * 0.5 <= fs <= rr["max"] * 2.2 else "ATENÇÃO", "Tempo de tela só com texto",
          f"{fs:.0%} (referências {rr['min']:.0%}–{rr['max']:.0%} dos frames estáveis)")


CATEG = {"A": "texto", "B": "1card", "B4": "rotulo", "B5": "rotulo", "C1": "2cards", "C2": "2cards", "C4": "2cards",
         "D1": "3cards", "D2": "3cards", "D3": "3cards", "D4": "3cards", "LOGOS": "recorte", "E2": "recorte",
         "E3": "recorte", "C8": "2cards", "D5": "3cards", "D6": "3cards", "B10": "rotulo", "A4": "texto",
         "B11": "1card", "G1": "1card", "B9": "rotulo", "D7": "recorte", "E5": "1card", "E6": "recorte",
         "F8": "2cards", "F9": "2cards", "G2": "1card", "G3": "1card", "M3": "1card", "M5": "1card", "M6": "recorte",
         "M7": "1card", "C9": "1card"}


# mesma lista do buscador (domínios: "alamy.com", não "alamy" — foto licenciada da Alamy republicada pela PFF é limpa)
BLOQUEADOS = tuple(caminhos.config_busca()["dominios_bloqueados"])
# assunto errado para o tema do canal (canal.json › regras.qa): no Pro Football, soccer/FIFA/Copa
_QA = caminhos.regras().get("qa", {})
PROIBIDOS = tuple(_QA.get("termos_proibidos", []))
PERMITIDO_SE = _QA.get("permitido_se", "")


def checar_layout(proj, item, R):
    """Com edicao/layout_<item>.json (gerado pelo gerar_ae2.py desde 2026-10-13): texto por cima de imagem
    ("since 1994" sobre o capacete) e texto que some rápido demais ("199th pick" 0,8 s, "receiver" 0,8 s)."""
    arq = proj / "edicao" / f"layout_{item}.json"
    if not arq.exists():
        R.add("ATENÇÃO", "Layout de textos", "layout_<item>.json não existe (rode o gerar_ae2.py de novo)")
        return
    reg = json.loads(arq.read_text())
    tx = [r for r in reg if r["tipo"] == "texto" and r.get("estado") != "Título"]
    cd = [r for r in reg if r["tipo"] == "card"]

    def inter(a, b):
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    sobre = []
    for r in tx:
        b = r["box"]
        area = (b[2] - b[0]) * (b[3] - b[1])
        for c in cd:
            if c["pai"] != r["pai"] or not area:
                continue
            if min(r["out"], c["out"]) - max(r["in"], c["in"]) > 0.3 and inter(b, c["box"]) / area > 0.2:
                sobre.append(f"{r['in']:.1f}s \"{r['txt']}\" cobre {inter(b, c['box']) / area:.0%} de {Path(str(c['id'])).name}")
    R.add("OK" if not sobre else "FALHA", "Texto por cima de imagem",
          "texto solo/rótulo não pode ficar em cima de card ou recorte (nome SOBRE o card é outra coisa)", sobre)
    curtos = sorted((r["out"] - r["in"], r) for r in tx if r["out"] - r["in"] < 1.0)
    falha = [x for x in curtos if x[0] < 0.7]
    R.add("FALHA" if falha else ("ATENÇÃO" if curtos else "OK"), "Texto pouco tempo na tela",
          "cada texto/rótulo ≥ 1,0 s para dar para ler (FALHA abaixo de 0,7 s)",
          [f"{r['in']:.1f}s \"{r['txt']}\" {d:.2f}s" for d, r in curtos])


def checar_origem(proj, R):
    """Assets de banco com marca d'água ou de assunto proibido no tema do canal (positions 03: Copa de 2022 com selo FIFA)."""
    man = proj / "manifesto.json"
    if not man.exists():
        return
    ruins = []
    for a_ in json.loads(man.read_text()).get("assets", []):
        o = a_.get("origem", {})
        txt = " ".join(str(o.get(k, "")) for k in ("url", "pagina", "titulo", "autor")).lower()
        m = [d for d in BLOQUEADOS if d in txt]
        # termo proibido só conta se o pedido não pede esse termo (16-05-c: chute "estilo futebol" de propósito) e a
        # origem não diz também o tema certo (tags do pxhere vêm com "soccer, american football")
        if PROIBIDOS and not any(s in (a_.get("descricao") or "").lower() for s in PROIBIDOS) and \
                not (PERMITIDO_SE and re.search(PERMITIDO_SE, txt)):
            m += [s for s in PROIBIDOS if s in txt]
        if m:
            ruins.append(f"{a_['id']}: {', '.join(m)} — {o.get('pagina') or o.get('url', '')}"[:160])
    R.add("OK" if not ruins else "FALHA", "Origem dos assets",
          "sem banco com marca d'água (Vecteezy, Shutterstock...) e sem assunto proibido no tema do canal", ruins)


def frame(video, t, w=640):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={w}:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    from io import BytesIO
    return Image.open(BytesIO(r.stdout)).convert("RGB")


def frames_referencia():
    """Por categoria, uma lista de (vídeo, tempo) de referência."""
    vids = sorted(REFS_DIR.glob("*.mp4"))
    cat = {k: [] for k in set(CATEG.values())}
    for i, v in enumerate(vids, 1):
        for f in estaveis(ler_det(EST / f"det/v{i}.jsonl")):
            cs = cards_validos(f)
            if not cs and f["textos"] and not f["recortes"]:
                cat["texto"].append((v, f["t"]))
            elif len(cs) == 1 and not f["textos"]:
                cat["1card"].append((v, f["t"]))
            elif len(cs) == 1 and f["textos"] and any(t[0] > cs[0][0] + cs[0][2] for t in f["textos"]):
                cat["rotulo"].append((v, f["t"]))
            elif len(cs) == 2:
                cat["2cards"].append((v, f["t"]))
            elif len(cs) >= 3:
                cat["3cards"].append((v, f["t"]))
            elif f["recortes"] and not cs:
                cat["recorte"].append((v, f["t"]))
    return cat


def folha(video, plano, saida):
    random.seed(7)
    refs = frames_referencia()
    est = [e for c in plano["cenas"] for e in c["estados"]]
    vistos, pares = set(), []
    for i, e in enumerate(est):
        c = CATEG.get(e["layout"])
        if not c or c in vistos or not refs.get(c):
            continue
        vistos.add(c)
        fim = est[i + 1]["ini"] if i + 1 < len(est) else plano["fim"]
        t = e["ini"] + 0.7 * (fim - e["ini"])
        rv, rt = random.choice(refs[c])
        pares.append((f"{e['layout']} @ {t:.1f}s", frame(video, t), frame(rv, rt)))
    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
    W, H = 640, 360
    out = Image.new("RGB", (2 * W + 30, len(pares) * (H + 34) + 40), (30, 30, 30))
    d = ImageDraw.Draw(out)
    d.text((10, 8), "NOSSO", fill=(255, 230, 0), font=fnt)
    d.text((W + 40, 8), "REFERÊNCIA (mesmo tipo de cena)", fill=(255, 230, 0), font=fnt)
    for k, (rot, a, b) in enumerate(pares):
        y = 40 + k * (H + 34)
        d.text((10, y), rot, fill=(255, 255, 255), font=fnt)
        out.paste(a.resize((W, H)), (0, y + 28))
        out.paste(b.resize((W, H)), (W + 30, y + 28))
    out.save(saida, quality=85)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--item", default="01")
    ap.add_argument("--video")
    a = ap.parse_args()
    proj = Path(a.projeto).resolve()
    ed = proj / "edicao"
    plano = json.loads((ed / f"plano_edicao_{a.item}.json").read_text())
    video = Path(a.video) if a.video else max(ed.glob("previa*.mp4"), key=lambda p: p.stat().st_mtime)
    det = ed / f"_qa_{video.stem}.jsonl"
    if not det.exists() or det.stat().st_mtime < video.stat().st_mtime:
        print("Medindo a prévia (detecção a 4 fps)...", file=sys.stderr)
        subprocess.run([PY, str(AQUI / "detectar.py"), str(video), str(det), "--fps", "4"], check=True,
                       stdout=subprocess.DEVNULL)
    R = Relatorio()
    checar_plano(plano, R)
    checar_render(video, plano, det, R, ed / f"layout_{a.item}.json")
    checar_layout(proj, a.item, R)
    checar_origem(proj, R)
    folha(video, plano, ed / f"qa_{a.item}.jpg")
    status = "❌ REPROVADO" if R.falhas else ("⚠️ APROVADO COM ATENÇÕES" if R.atencoes else "✅ APROVADO")
    md = [f"# QA — {plano['nome']}", "", f"Prévia: `{video.name}` · **{status}** "
          f"({R.falhas} falha(s), {R.atencoes} atenção(ões))", "",
          "| Status | Verificação | Resultado |", "|---|---|---|"] + R.linhas + \
         ["", f"Folha lado a lado: `qa_{a.item}.jpg` (nosso × referência, mesmo tipo de cena)."]
    (ed / f"qa_{a.item}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(1 if R.falhas else 0)


if __name__ == "__main__":
    main()
