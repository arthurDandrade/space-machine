"""Controle de qualidade de um bloco: mede a prévia renderizada e o layout e reprova o que é defeito visível.

Uso: python qa/qa_bloco.py <projeto> [--item 01] [--video edicao/previa.mp4]

Saída em <projeto>/edicao/:
  qa_<item>.md    relatório (OK / FALHA, com tempos para corrigir)
  qa_<item>.jpg   folha lado a lado: nosso frame × frame de referência do mesmo tipo de cena
Código de saída 1 se houver FALHA.

Enxuto desde 2026-10-15: só o que pegou defeito de verdade (palco vazio, texto cortado na borda, texto pequeno,
texto por cima de imagem, texto rápido demais, origem dos assets). As conferências do plano (texto sobre imagem,
asset ≥ 1,8 s, variedade...) saíram porque o storyboard já cobra as mesmas regras antes de renderizar
(compilar_cenas.py + storyboard.py; em 53 QAs nenhuma reprovou), e as ATENÇÕES (ritmo, tamanho dos cards, tempo de
tela) saíram porque não travavam nada e ninguém lia. Medidas em "Controle de Qualidade.md".
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
from medidas import cards_validos, estaveis, ler_det, medir_deteccao  # noqa: E402

REF = json.loads((AQUI / "referencia.json").read_text())
sys.path.insert(0, str(AQUI.parents[1]))
import caminhos  # noqa: E402

REFS_DIR = caminhos.referencias()        # vídeos de referência do formato (opcionais: sem eles, a folha não compara)
EST = REFS_DIR / "estudo_cenas"
PY = sys.executable


class Relatorio:
    def __init__(self):
        self.linhas = []
        self.falhas = 0

    def add(self, falhou, titulo, detalhe, itens=()):
        """Os itens (tempos para corrigir) só aparecem na FALHA."""
        self.falhas += bool(falhou)
        self.linhas.append(f"| {'❌ FALHA' if falhou else '✅ OK'} | **{titulo}** | {detalhe} |")
        for it in itens if falhou else ():
            self.linhas.append(f"|  |  | ↳ {it} |")


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
    # quanto de cada frame (4 fps) é diferente do fundo de papel — conferência no pixel para os casos em que
    # o detector se perde (card + globo/bandeira encostados não é retângulo: E5/M5/F9)
    ocup = fracao_ocupada(video, Path(str(det) + ".bg.npy"), fps)
    # >5% da tela = há algo em cena. Palco vazio de verdade mede 1–2% (até 4% num frame de transição); era 8%,
    # e um logo PNG sozinho no D6 (sem moldura de card, o detector não vê) mediu 7,7–8,2% e reprovou o bloco 03
    # do draft duas vezes (2026-10-16)
    tem_algo = lambda t: ocup.get(round(t * fps), 0) > 0.05

    # palco vazio longo
    vazios, run = [], []
    for f in fr_cont + [{"t": fim + 1, "cards": [1], "textos": [], "recortes": []}]:
        if not f["cards"] and not f["textos"] and not f["recortes"]:
            run.append(f["t"])
        else:
            if len(run) / fps > 0.5 and not tem_algo(run[len(run) // 2]):
                vazios.append(f"{run[0]:.1f}–{run[-1]:.1f}s ({len(run) / fps:.1f}s)")
            run = []
    R.add(vazios, "Palco vazio", "entre cenas deve ser ~0,15s (máx. ~0,3s)", vazios)
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
    R.add(borda, "Texto cortado na borda", "nenhum texto pode encostar na borda do quadro", borda)
    # tamanho do texto solo: FALHA abaixo de 70% do p10 das referências (a faixa de 70–85% era só atenção)
    ref_alt = REF["altura_texto_solo_px"]
    alt = m["altura_texto_solo"]
    if alt:
        # texto solo de verdade = quase toda a tela é papel (texto ocupa <15%); senão é card que o detector perdeu
        solo = lambda f: not f["cards"] and not f["recortes"] and f["textos"] and ocup.get(round(f["t"] * fps), 0) < 0.15
        alt = [max(t[3] for t in f["textos"]) for f in estaveis(fr_cont) if solo(f)] or alt
        med = float(np.median(alt))
        peq = [f"{f['t']:.1f}s ({max(t[3] for t in f['textos'])}px)" for f in estaveis(fr_cont)
               if solo(f) and max(t[3] for t in f["textos"]) < ref_alt[0] * 0.75]
        R.add(med < ref_alt[0] * 0.7, "Tamanho do texto solo",
              f"altura mediana {med:.0f}px (referências {ref_alt[0]:.0f}–{ref_alt[-1]:.0f}px)", sorted(set(peq))[:8])
    # texto preto junto de cards (nome acima / rótulo lateral): FALHA abaixo de 80% do p10 das referências
    v = m["altura_texto_junto"]
    rj = REF["altura_texto_junto_px"]
    if v:
        med = float(np.median(v))
        R.add(med < rj[0] * 0.8, "Tamanho do nome/rótulo junto dos cards",
              f"altura mediana {med:.0f}px (referências: mediana {rj[2]:.0f}px, p25 {rj[1]:.0f}px)")


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
    if not arq.exists():       # o editar_bloco.sh roda o gerar_ae2.py logo antes: só falta em bloco antigo
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
    R.add(sobre, "Texto por cima de imagem",
          "texto solo/rótulo não pode ficar em cima de card ou recorte (nome SOBRE o card é outra coisa)", sobre)
    curtos = sorted(((r["out"] - r["in"], r) for r in tx if r["out"] - r["in"] < 0.7), key=lambda x: x[0])
    R.add(curtos, "Texto pouco tempo na tela", "cada texto/rótulo ≥ 0,7 s para dar para ler (o ideal é ≥ 1,0 s)",
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
    R.add(ruins, "Origem dos assets",
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
    checar_render(video, plano, det, R, ed / f"layout_{a.item}.json")
    checar_layout(proj, a.item, R)
    checar_origem(proj, R)
    folha(video, plano, ed / f"qa_{a.item}.jpg")
    status = "❌ REPROVADO" if R.falhas else "✅ APROVADO"
    md = [f"# QA — {plano['nome']}", "", f"Prévia: `{video.name}` · **{status}** ({R.falhas} falha(s))", "",
          "| Status | Verificação | Resultado |", "|---|---|---|"] + R.linhas + \
         ["", f"Folha lado a lado: `qa_{a.item}.jpg` (nosso × referência, mesmo tipo de cena)."]
    (ed / f"qa_{a.item}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(1 if R.falhas else 0)


if __name__ == "__main__":
    main()
