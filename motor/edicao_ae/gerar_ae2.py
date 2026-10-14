"""Editor v2: monta um bloco a partir de edicao/plano_edicao_<item>.json (cenas com estados, usando a
Biblioteca de Cenas da pasta de conhecimento). Gera edicao/montar_<item>_v2.jsx para o After Effects.

Uso: python gerar_ae2.py <projeto> [--item 01]
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import caminhos  # noqa: E402

W, H = 1920, 1080
CX, CY = W / 2, H / 2
FPS = 60
FONTE = "AvenirNext-Heavy"
# Curvas medidas nas referências a 60 fps (qa/comparar_animacao.py):
# entrada = desaceleração cúbica de ~0,7 s (50% em 0,13 s, 90% em 0,38 s); saída = aceleração cúbica de ~0,6 s.
ENTRADA, DERIVA, DERIVA_T = 0.95, 0, 0
SAIDA, SOBREPOE, ANTECIPA = 0.80, 0.12, 0.20
PILHA_ESCALONA = 0.40          # C9: atraso do card da frente quando os dois caem na mesma palavra
PUSH, PUSH_MAX = 2.5, 115
MARGEM = 50            # nada pode passar desta margem da borda durante o zoom da cena
FADE, POP = 0.18, 0.27


class Montador:
    def __init__(self, proj):
        self.proj = proj
        self.cache = proj / "edicao" / "_cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.layers = []
        self.caixas = {}       # id do null do estado -> caixas (x0, y0, x1, y1) relativas ao centro
        self.registro = []     # textos e cards por estado, para o QA (edicao/layout_<item>.json, 2026-10-13)
        man = json.loads((proj / "manifesto.json").read_text())["assets"]
        self.manif = {m["id"]: m for m in man}

    # ---------- arquivos ----------
    def arquivo(self, el):
        return self.proj / (el["arquivo"] if el.get("arquivo") else self.manif[el["asset"]]["arquivo"])

    def info(self, src, alvo_w, alvo_h, png=False):
        """Devolve (arquivo, w, h, duracao|None). PNGs são cortados no contorno; imagens grandes, reduzidas."""
        if src.suffix == ".mp4":
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height:format=duration", "-of", "json", str(src)],
                               capture_output=True, text=True)
            j = json.loads(r.stdout)
            return src, j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])
        im = Image.open(src)
        if png:
            im = im.convert("RGBA")
            bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
            if bb:
                im = im.crop(bb)
        esc = max(alvo_w / im.width, alvo_h / im.height) * 1.5
        if esc < 0.8 or png:
            esc = min(esc, 1.0)
            nw, nh = max(1, round(im.width * esc)), max(1, round(im.height * esc))
            dst = self.cache / f"{src.parent.name}_{src.stem}_{nw}{'_p' if png else ''}.png"
            if not dst.exists():
                im.resize((nw, nh), Image.LANCZOS).save(dst)
            return dst, nw, nh, None
        return src, im.width, im.height, None

    def inteiro(self, el):
        """Imagem que tem que aparecer inteira no card (mapa gerado, logo, bandeira)."""
        if "/mapas/" in (el.get("arquivo") or ""):
            return True
        return self.manif.get(el.get("asset"), {}).get("tipo") in ("logo", "mapa", "bandeira")

    def aspecto(self, el):
        if el.get("asset") in self.manif:
            m = self.manif[el["asset"]]
            return m["w"] / m["h"]
        im = Image.open(self.arquivo(el))
        return im.width / im.height

    # ---------- layers ----------
    def add(self, **kw):
        kw["id"] = len(self.layers)
        self.layers.append(kw)
        return kw["id"]

    def null_estado(self, ini, fim_vis, fim_push, nome):
        d = fim_push - ini
        s1 = min(PUSH_MAX, 100 + PUSH * d)
        i = self.add(kind="null", name=nome, parent=None, pos=[CX, CY], anchor=[0, 0],
                     **{"in": max(0, ini - 0.3), "out": fim_vis + 0.1},
                     scale_keys=[[ini, 100], [fim_push, s1]], linear_scale=True)
        self.caixas[i] = []
        return i

    def caixa(self, pai, x0, y0, x1, y1):
        if pai in self.caixas:
            self.caixas[pai].append((x0, y0, x1, y1))

    def limitar_zoom(self):
        """O push-in escala a partir do centro: limita a escala final para nenhum elemento passar da margem."""
        for i, cx in self.caixas.items():
            if not cx:
                continue
            lim = PUSH_MAX / 100
            for x0, y0, x1, y1 in cx:
                ax, ay = max(abs(x0), abs(x1)), max(abs(y0), abs(y1))
                if ax > 1:
                    lim = min(lim, (CX - MARGEM) / ax)
                if ay > 1:
                    lim = min(lim, (CY - MARGEM) / ay)
            lim = max(1.0, lim) * 100
            k = self.layers[i]["scale_keys"]
            if k[-1][1] > lim:
                k[-1][1] = round(lim, 2)

    def texto(self, txt, t_in, t_out, pai, pos, max_w, max_size, cor, sombra, ancora="center", fade=True, nome=None,
              fonte=None, caixa=None):
        kw = dict(kind="text", text=txt, parent=pai, pos=pos, max_w=max_w, max_size=max_size, color=cor,
                  shadow=sombra, anchor_mode=ancora, name=nome or txt.replace("\r", " "), font=fonte, box=caixa)
        kw["in"], kw["out"] = t_in, t_out
        linhas = txt.count("\r") + 1
        larg = min(max_w, max(len(l) for l in txt.split("\r")) * 0.60 * max_size)
        alt = max_size * 1.15 * linhas
        x0, x1 = pos[0] - larg / 2, pos[0] + larg / 2
        y0 = pos[1] if ancora == "top" else (pos[1] - alt if ancora == "bottom" else pos[1] - alt / 2)
        self.caixa(pai, x0, y0, x1, y0 + alt)
        lid_ = len(self.layers)          # índice que o add() abaixo vai receber
        if pai in self.caixas:
            self.registro.append({"tipo": "texto", "txt": txt.replace("\r", " "), "pai": pai, "lid": lid_,
                                  "box": [x0, y0, x1, y0 + alt]})
        if fade:
            kw["opacity_keys"] = [[t_in, 0], [t_in + FADE, 100]]
            kw["blur_keys"] = [[t_in, 8], [t_in + FADE, 0]]
        return self.add(**kw)


def _frase_que_cresce(ts):
    """Textos de um estado em que cada um é o anterior + mais palavras, todos marcados "cresce"."""
    if len(ts) < 2:
        return False
    for a, b in zip(ts, ts[1:]):
        base = a[0].strip(" ,.;:").lower()
        if len(b) < 3 or b[2] != "cresce" or not b[0].lower().startswith(base) or not b[0][len(base):].strip(" ,.;:"):
            return False
    return True


FIM_BLOCO = 0.6   # s de tela depois da última palavra do bloco
SOMBRA_PRETO = {"op": 45, "soft": 10, "dist": 3}
SOMBRA_BRANCO = {"op": 170, "soft": 12, "dist": 3}

# ---- identidade visual do canal (pasta de conhecimento: 04 - Edição/Identidade Visual) ----
def _rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
COR_FUNDO = _rgb("#EDF0F6")      # cinza-azulado do logo/banner
# imagem de fundo do canal (canal.json › identidade.fundo_imagem): fica entre o "Fundo" e a "Textura papel".
# Opacidade/escala/posição medidas no Pro Football (2026-10-08); o canal pode trocar com fundo_opacidade etc.
FUNDO_IMAGEM = None
_FUNDO_PADRAO = {"opacidade": 50, "escala": 119.576, "pos": [941.58, 545.26]}
COR_TEXTO = _rgb("#191A21")      # quase-preto ("INSIDE THE")
COR_AZUL = _rgb("#1D2D85")       # azul royal ("NFL WORLD")
COR_CAIXA = _rgb("#0B2479")      # caixa azul ("WORK INSIDE")
COR_SOMBRA = _rgb("#0B1A3A")     # sombras levemente azuladas
FONTE_MARCA = "Impact"           # condensada pesada, sempre em MAIÚSCULAS
IMPACT_TTF = "/System/Library/Fonts/Supplemental/Impact.ttf"
# canal.json do canal (caminhos.canal()): cores, fonte e fundo de cada canal. Sem um campo, vale o padrão acima.
_id = caminhos.identidade()
if _id:
    COR_FUNDO = _rgb(_id.get("cor_fundo", "#EDF0F6"))
    COR_TEXTO = _rgb(_id.get("cor_texto", "#191A21"))
    COR_AZUL = _rgb(_id.get("cor_destaque", "#1D2D85"))
    COR_CAIXA = _rgb(_id.get("cor_caixa", "#0B2479"))
    COR_SOMBRA = _rgb(_id.get("cor_sombra", "#0B1A3A"))
    FONTE_MARCA = _id.get("fonte_marca", FONTE_MARCA)
    IMPACT_TTF = _id.get("fonte_marca_arquivo", IMPACT_TTF)
    if _id.get("fundo_imagem"):
        FUNDO_IMAGEM = dict(_FUNDO_PADRAO, file=str(caminhos.canal() / _id["fundo_imagem"]),
                            **{k: _id[f"fundo_{k}"] for k in ("opacidade", "escala", "pos") if f"fundo_{k}" in _id})


def tamanho_impact(linhas, max_w, max_size):
    """Tamanho único (pt) para várias linhas em Impact caberem em max_w (medido com a própria fonte)."""
    from PIL import ImageFont
    f = ImageFont.truetype(IMPACT_TTF, 100)
    larg = max(f.getlength(l) for l in linhas)
    return min(max_size, 100 * max_w / larg)


LIGACAO = {"WHEN", "AND", "OF", "IN", "FOR", "WITH", "TO", "THE", "VS", "VS.", "AT", "ON", "WHY", "HOW", "WHAT", "FROM",
           "when", "and", "of", "in", "for", "with", "to", "vs", "at", "on", "why", "how", "what", "from"}


def duas_linhas(t, limite=16):
    if len(t) <= limite or " " not in t:
        return t
    pal = t.split()
    melhor, idx = 1e9, 1
    for k in range(1, len(pal)):
        a, b = " ".join(pal[:k]), " ".join(pal[k:])
        # prefere quebrar ANTES de palavra de ligação e nunca deixar uma no fim da linha
        custo = abs(len(a) - len(b)) - (8 if pal[k] in LIGACAO else 0) + (8 if pal[k - 1] in LIGACAO else 0)
        if custo < melhor:
            melhor, idx = custo, k
    return " ".join(pal[:idx]) + "\r" + " ".join(pal[idx:])


def linhas_rotulo(t):
    """Rótulo lateral: até 16 letras numa linha, até 34 em duas, mais que isso em três (bloco de texto, E3)."""
    if len(t) <= 34:
        return duas_linhas(t)
    pal, alvo, linhas, atual = t.split(), len(t) / 3, [], ""
    for p in pal:
        if atual and len(atual) + 1 + len(p) > alvo + 4 and len(linhas) < 2:
            linhas.append(atual)
            atual = p
        else:
            atual = (atual + " " + p).strip()
    linhas.append(atual)
    return "\r".join(linhas)


COR_CITACAO = "#1F2024"         # caixa escura (G1), perto do COR_TEXTO
COR_GRIFO = "#2F45C0"           # grifo azul atrás das palavras (medido em v5#19; azul da marca, mais claro)
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"


def desenhar_citacao(destino, texto, grifo="", fonte="", larg_txt=860, k=2):
    """G1: caixa escura arredondada com texto branco ~30 px, trecho grifado em azul e a fonte num selo cinza.
    Desenhada em PNG (k× para aguentar o zoom). Medidas de v5#19/v5#60 em 1080p."""
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype(ARIAL, 30 * k)
    fs = ImageFont.truetype(ARIAL, 20 * k)
    lh, px, py = 46 * k, 22 * k, 18 * k
    ini_g = texto.find(grifo) if grifo else -1
    fim_g = ini_g + len(grifo) if ini_g >= 0 else -1
    # quebra em linhas guardando a posição de cada palavra no texto
    palavras, pos = [], 0
    for w in texto.split():
        pos = texto.index(w, pos)
        palavras.append((w, pos))
        pos += len(w)
    linhas, atual, esp = [], [], f.getlength(" ")
    for w, p0 in palavras:
        x = (sum(f.getlength(a) for a, _ in atual) + esp * len(atual)) if atual else 0
        if atual and x + f.getlength(w) > larg_txt * k:
            linhas.append(atual)
            atual = []
        atual.append((w, p0))
    linhas.append(atual)
    selo = f"  {fonte}  " if fonte else ""
    larg = max(sum(f.getlength(a) for a, _ in l) + esp * (len(l) - 1) for l in linhas)
    ult = sum(f.getlength(a) for a, _ in linhas[-1]) + esp * (len(linhas[-1]) - 1)
    ws = fs.getlength(selo) if selo else 0
    if selo and ult + 12 * k + ws > larg_txt * k:
        linhas.append([])
        ult = 0
    larg = max(larg, ult + (12 * k + ws if selo else 0))
    W2, H2 = int(larg + 2 * px), int(len(linhas) * lh + 2 * py)
    im = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W2 - 1, H2 - 1], radius=10 * k, fill=COR_CITACAO)
    for n, l in enumerate(linhas):
        y, x = py + n * lh, px
        for j, (w, p0) in enumerate(l):
            lw = f.getlength(w)
            if ini_g <= p0 < fim_g:
                prox_g = j + 1 < len(l) and ini_g <= l[j + 1][1] < fim_g
                d.rectangle([x - 2 * k, y + 4 * k, x + lw + (esp if prox_g else 2 * k), y + lh - 6 * k], fill=COR_GRIFO)
            d.text((x, y + 7 * k), w, font=f, fill="white")
            x += lw + esp
    if selo:
        x, y = px + ult + (12 * k if ult else 0), py + (len(linhas) - 1) * lh
        d.rounded_rectangle([x, y + 11 * k, x + ws, y + lh - 9 * k], radius=8 * k, fill="#3C4043")
        d.text((x, y + 13 * k), selo, font=fs, fill="#BDC1C6")
    im.save(destino)
    return destino, W2, H2


def clamp(a, lo, hi):
    return max(lo, min(hi, a))


def geometria(layout, asps, pngs, inteiros=None):
    """Lista de (cx, cy, w, h) por card, em coordenadas de tela."""
    n = len(asps)
    if n == 0:
        return []
    if layout == "LOGOS":
        alt, gap = 360, 140
        ws = [a * alt for a in asps]
        tot = sum(ws) + gap * (n - 1)
        if tot > 1720:          # logo muito largo (ex.: Sleep Number): reduz tudo para caber na tela
            k = (1720 - gap * (n - 1)) / sum(ws)
            alt, ws = alt * k, [w * k for w in ws]
            tot = 1720
        x, out = CX - tot / 2, []
        for w in ws:
            out.append((x + w / 2, 470, w, alt))
            x += w + gap
        return out
    if layout == "D2":
        # 1 grande à esquerda + coluna de pequenos empilhados à direita
        alt, gap = 780, 26
        m = n - 1
        big_a = clamp(asps[0], 0.56, 1.5)
        hs = (alt - gap * (m - 1)) / m
        ws = [clamp(a, 1.25, 1.78) * hs for a in asps[1:]]
        col_w = max(ws)
        tot = big_a * alt + gap + col_w
        if tot > 1720:
            k = 1720 / tot
            alt, hs, ws, col_w = alt * k, hs * k, [w * k for w in ws], col_w * k
        tot = big_a * alt + gap + col_w
        x0 = CX - tot / 2
        out = [(x0 + big_a * alt / 2, CY, big_a * alt, alt)]
        cx_col = x0 + big_a * alt + gap + col_w / 2
        y = CY - alt / 2
        for w in ws:
            out.append((cx_col, y + hs / 2, w, hs))
            y += hs + gap
        return out
    if layout == "D3":
        # moldura: objeto no centro (maior), pessoas dos lados
        alts = [500, 660, 500]
        asp = [clamp(a, 0.56, 1.0) for a in asps[:3]]
        gap = 30
        ws = [a * h for a, h in zip(asp, alts)]
        tot = sum(ws) + gap * 2
        x, out = CX - tot / 2, []
        for w, h in zip(ws, alts):
            out.append((x + w / 2, CY, w, h))
            x += w + gap
        return out
    if layout == "D4":
        # esteira: cards em fila; todos precisam caber na tela (Arthur, 2026-10-03), encolhe se não couber
        alt, gap = 560, 30
        asp = [clamp(a, 0.56, 1.0) for a in asps]
        tot = sum(a * alt for a in asp) + gap * (n - 1)
        if tot > 1720:
            alt *= (1720 - gap * (n - 1)) / (tot - gap * (n - 1))
            tot = 1720
        x, out = CX - tot / 2, []
        for a in asp:
            w = a * alt
            out.append((x + w / 2, CY, w, alt))
            x += w + gap
        return out
    if layout in ("E2", "E6", "M6", "D7"):
        # recorte (PNG) + card(s) lado a lado. E6 = diagrama recortado (v6#162), M6 = silhueta do país (v7#197),
        # D7 = recorte estreito na MESMA altura de um par (v6#101)
        alts = [700 for p in pngs] if layout == "D7" else [600 if p else 760 for p in pngs]
        asp = [a if p else clamp(a, 0.56, 1.3) for a, p in zip(asps, pngs)]
        gap = 50
        ws = [a * h for a, h in zip(asp, alts)]
        tot = sum(ws) + gap * (n - 1)
        if tot > 1720:
            k = 1720 / tot
            ws, alts = [w * k for w in ws], [h * k for h in alts]
            tot = 1720
        x, out = CX - tot / 2, []
        for w, h in zip(ws, alts):
            out.append((x + w / 2, CY, w, h))
            x += w + gap
        return out
    if layout == "D5" and n >= 3:
        # sanduíche (v8#4): o 3º card (último a entrar) vai ao meio, na frente, ~22% mais alto que os laterais
        # e cobrindo ~18% de cada um. Medido em 1080p: laterais ~700 px, meio ~860 px. Ordem de saída = ordem
        # dos cards (esq, dir, meio), para o meio ficar por cima no After.
        hs, hm, cobre = 700, 860, 0.18
        we, wd = clamp(asps[0], 0.56, 1.0) * hs, clamp(asps[1], 0.56, 1.0) * hs
        wm = clamp(asps[2], 0.56, 1.1) * hm
        tot = wm + (we + wd) * (1 - cobre)
        if tot > 1720:
            k = 1720 / tot
            hs, hm, we, wd, wm, tot = hs * k, hm * k, we * k, wd * k, wm * k, 1720
        cx_m = CX - tot / 2 + we * (1 - cobre) + wm / 2
        return [(cx_m - wm / 2 - we / 2 + we * cobre, CY, we, hs), (cx_m + wm / 2 + wd / 2 - wd * cobre, CY, wd, hs),
                (cx_m, CY, wm, hm)]
    if layout == "D6":
        # baralho (v5#39–41, v7#81, v8#248): cada card entra por cima do anterior cobrindo ~35%, com desnível
        # em y e ficando um pouco menor; o leque ocupa ~75% da largura
        alts = [800, 760, 720, 680][:n] + [680] * max(0, n - 4)
        dys = [-30, 30, -10, 40][:n] + [0] * max(0, n - 4)
        # cortados em retrato/quadrado (com 4 paisagens o leque encolhia para ~430 px de altura)
        ws = [clamp(a, 0.56, 1.0) * h for a, h in zip(asps, alts)]
        passo = 0.62
        tot = sum(w * passo for w in ws[:-1]) + ws[-1]
        if tot > 1720:
            k = 1720 / tot
            ws, alts, dys, tot = [w * k for w in ws], [h * k for h in alts], [d * k for d in dys], 1720
        x, out = CX - tot / 2, []
        for w, h, dy in zip(ws, alts, dys):
            out.append((x + w / 2, CY + dy, w, h))
            x += w * passo
        return out
    if layout == "B10":
        # posição FINAL (v8#56, v8#164): card à direita, ~740 px de altura, borda direita a ~220 px da tela.
        # Ele entra no centro e desliza para cá no 1º rótulo (ver main).
        a = clamp(asps[0], 0.56, 1.0)     # paisagem deixava o nome espremido (62 px)
        h = 740                           # v8#164: 700–730 px; borda direita a ~220 px da tela
        w = a * h
        return [(W - 220 - w / 2, CY, w, h)]
    if layout == "F8" and n >= 2:
        # v5#167: retrato/foto grande à esquerda; mapa ~77% da altura entra por cima, cobrindo ~53% dele mesmo,
        # 100 px mais baixo no topo. Medido em 1080p: foto 1180×888, mapa 696×684.
        h0 = 860
        w0 = clamp(asps[0], 1.0, 1.78) * h0
        h1 = 0.77 * h0
        w1 = clamp(asps[1], 0.8, 1.3) * h1
        tot = w0 + w1 * 0.47
        if tot > 1720:
            k = 1720 / tot
            h0, w0, h1, w1, tot = h0 * k, w0 * k, h1 * k, w1 * k, 1720
        x0 = CX - tot / 2
        top = CY - h0 / 2
        return [(x0 + w0 / 2, CY, w0, h0), (x0 + w0 - w1 * 0.53 + w1 / 2, top + 100 + h1 / 2, w1, h1)]
    if layout == "F9" and n >= 2:
        # v5#3: foto central (~880 px) com bandeira à direita ("lateral"); mapa (~65% da altura) entra pela
        # esquerda POR CIMA, cobrindo ~37% da foto
        h0 = 880
        w0 = clamp(asps[0], 0.56, 1.0) * h0
        h1 = 0.65 * h0
        w1 = clamp(asps[1], 1.0, 1.78) * h1
        dir1 = CX - w0 / 2 + 0.37 * w0
        return [(CX, CY, w0, h0), (dir1 - w1 / 2, CY, w1, h1)]
    if layout == "C9" and n >= 2:
        # pilha (v7#17): o card de TRÁS (1º da lista) aparece só ~8% acima/à direita do da frente (2º, por cima)
        a = clamp(asps[1], 0.56, 1.6)
        h = 780
        w = min(1250, a * h)
        h = w / a
        dx, dy = 0.08 * w, 0.08 * h
        return [(CX + dx / 2, CY - dy / 2, w, h), (CX - dx / 2, CY + dy / 2, w, h)]
    if layout in ("E5", "M5"):
        # E5 (v5#2): foto ~880 px centralizada, bandeira encostada à direita. M5 (v7#181): card paisagem ~1190×790
        # centralizado, globo à direita. O elemento lateral é desenhado no main ("lateral" do card).
        if layout == "E5":
            a, h = clamp(asps[0], 0.56, 1.3), 880
            return [(CX, CY, a * h, h)]
        a = clamp(asps[0], 1.0, 1.78)
        w = min(1250, 790 * a)
        return [(CX, CY, w, w / a)]
    if layout in ("G2", "G3"):
        # tabela (v7#47: ~1030×850) / gráfico: imagem inteira, sem cortar
        a = asps[0]
        mw, mh = (1100, 860) if layout == "G2" else (1500, 820)
        w = min(mw, mh * a)
        return [(CX, CY, w, w / a)]
    if layout in ("B11", "G1"):
        # B11 (v6#118, v6#200): card novo por cima da composição desfocada — retrato ~860 px, paisagem ~1250×730.
        # G1 (v5#19, v5#60): card centralizado (retrato ~900 px, paisagem ~1270×866); a caixa de citação cobre a esquerda.
        a = clamp(asps[0], 0.56, 1.78)
        hr, wl, hl = (860, 1300, 760) if layout == "B11" else (900, 1280, 866)
        if a <= 1.0:
            return [(CX, CY, a * hr, hr)]
        w = min(wl, hl * a)
        return [(CX, CY, w, w / a)]
    if layout in ("B4", "B5", "B9", "E3") and pngs and pngs[0]:
        a = asps[0]
        w, h = (900, 900 / a) if 900 / a <= 700 else (700 * a, 700)
        return [(120 + w / 2, CY, w, h)]
    if layout in ("B4", "B5", "B9", "E3"):
        a = clamp(asps[0], 0.56, 1.5)
        w, h = (820, 820 / a) if 820 / a <= 760 else (760 * a, 760)
        return [(110 + w / 2, CY, w, h)]
    if layout == "B" or n == 1:
        a = clamp(asps[0], 0.56, 1.78)
        w, h = (1400, 1400 / a) if 1400 / a <= 900 else (900 * a, 900)
        return [(CX, CY, w, h)]
    if layout == "C2":
        alt = 640
        ws = [clamp(a, 0.56, 1.78) * alt for a in asps[:2]]
        tot = ws[0] + ws[1] * 0.75
        if tot > 1650:
            k = 1650 / tot
            alt *= k
            ws = [w * k for w in ws]
            tot = 1650
        x0 = CX - tot / 2
        return [(x0 + ws[0] / 2, CY - 40, ws[0], alt), (x0 + ws[0] - ws[1] * 0.25 + ws[1] / 2, CY + 50, ws[1], alt)]
    # C1, C4, D1: em linha, mesma altura
    alt = {2: 800, 3: 560}.get(n, 480)
    if layout == "C4":
        alt = 700
    gap = 36 if n == 2 else 26
    # lado a lado: as referências cortam em retrato/quadrado (aspecto mediano 0,77) para os cards ficarem altos
    # mapa/logo (inteiros) usam o próprio formato: cortado em retrato encolhia a ~1/4 da tela (positions 14/20, 2026-10-13)
    inteiros = inteiros or [False] * n
    asp = [clamp(a, 0.56, 1.78 if it else (1.0 if n >= 2 else 1.6)) for a, it in zip(asps, inteiros)]
    tot = sum(a * alt for a in asp) + gap * (n - 1)
    if tot > 1720:
        alt *= (1720 - gap * (n - 1)) / (tot - gap * (n - 1))
    cy = CY + (45 if layout == "C4" else 0)
    tot = sum(a * alt for a in asp) + gap * (n - 1)
    x, out = CX - tot / 2, []
    for a in asp:
        out.append((x + a * alt / 2, cy, a * alt, alt))
        x += a * alt + gap
    return out


CTA_BOTAO_Y, CTA_BOTAO_W, CTA_CURSOR_H = -60, 1250, 230
CTA_PONTA = (0.04, 0.03)        # ponta da seta no PNG do cursor (fração da largura/altura, já cortado no contorno)


def cta(M, e, pai, ini, fim):
    """CTA: botão de inscrever do canal com pop, o cursor entra de baixo à direita e clica na palavra "clique".
    O botão vermelho genérico com "subscribe: Inside the NFL World" ao lado ficou ruim (rings, bloco 07, 2026-10-14).
    PNGs da identidade do canal: canal.json › identidade › cta_botao / cta_cursor (padrão identidade/cta_*.png)."""
    pasta = caminhos.canal()
    botao = pasta / _id.get("cta_botao", "identidade/cta_botao.png")
    cursor = pasta / _id.get("cta_cursor", "identidade/cta_cursor.png")
    if not botao.exists():
        sys.exit(f"CTA sem o botão do canal: falta {botao}")
    tc = e.get("clique", ini + 1.2)
    sai = fim - 0.3
    arq, bw, bh, _ = M.info(botao, CTA_BOTAO_W, 600, png=True)
    s = CTA_BOTAO_W / bw
    M.caixa(pai, -CTA_BOTAO_W / 2, CTA_BOTAO_Y - bh * s / 2, CTA_BOTAO_W / 2, CTA_BOTAO_Y + bh * s / 2)
    # pop na entrada; no clique afunda (92%) e volta com um pulo (104%); sai encolhendo junto com o cursor
    sk = [[ini, 0, [0, 0, 800, 18]], [ini + POP, 100, [0, 85, 0, 0]],
          [tc, 100, [0, 0, 0, 60]], [tc + 0.08, 92], [tc + 0.22, 104], [tc + 0.38, 100, [0, 60, 0, 0]],
          [sai, 100, [0, 0, 0, 85]], [fim, 0, [0, 30, 0, 0]]]
    sk = [k for k in sk if k[0] <= fim]
    slot = M.add(kind="null", name="cta botão", parent=pai, pos=[0, CTA_BOTAO_Y], anchor=[0, 0],
                 **{"in": ini, "out": fim}, scale_keys=sk)
    M.add(kind="footage", name="cta botão", file=str(arq), parent=slot, src=[bw, bh], scale=s * 100, pos=[0, 0],
          start=0, **{"in": ini, "out": fim}, shadow={"op": 110, "soft": 30 / s, "dist": 5 / s})
    if not cursor.exists():
        return
    arq, cw, ch, _ = M.info(cursor, 400, CTA_CURSOR_H, png=True)
    sc = CTA_CURSOR_H / ch
    alvo = [CTA_BOTAO_W * 0.22, CTA_BOTAO_Y + 25]        # em cima do "SUBSCRIBE", à direita do centro
    t0 = max(ini + 0.15, tc - 0.75)
    # o null fica na ponta da seta: escalar no clique afunda a seta no lugar, sem escorregar
    nc = M.add(kind="null", name="cta cursor", parent=pai, anchor=[0, 0], **{"in": t0, "out": fim},
               pos_keys=[[t0, [W / 2 + 120, H / 2 + 80], [0, 0, 0, 80]], [tc - 0.05, alvo, [0, 90, 0, 0]],
                         [sai, alvo, [0, 0, 0, 85]], [fim, [alvo[0] + 60, alvo[1] + 40], [0, 30, 0, 0]]],
               scale_keys=[[tc - 0.05, 100], [tc + 0.07, 82], [tc + 0.25, 100], [sai, 100], [fim, 0]])
    M.add(kind="footage", name="cta cursor", file=str(arq), parent=nc, src=[cw, ch], scale=sc * 100,
          pos=[(0.5 - CTA_PONTA[0]) * cw * sc, (0.5 - CTA_PONTA[1]) * ch * sc], start=0, **{"in": t0, "out": fim},
          shadow={"op": 110, "soft": 30 / sc, "dist": 5 / sc})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--item", default="01")
    a = ap.parse_args()
    proj = Path(a.projeto).resolve()
    plano = json.loads((proj / "edicao" / f"plano_edicao_{a.item}.json").read_text())
    audio = next(p for p in proj.iterdir() if p.stem.startswith("narracao"))
    M = Montador(proj)

    # ---------- título ----------
    tt = plano.get("titulo")   # sem "titulo" = bloco sem card de título (cold open, 2026-10-11)
    if tt:
        t0, tf = max(0, tt["t"] - 0.05), tt["fim"]
        pai = M.null_estado(0, tf, tf, "Título")
        linhas = duas_linhas(tt["texto"].upper(), 18).split("\r")
        tam = tamanho_impact(linhas, 1500, 150)
        y = 50
        for k, lin in enumerate(linhas):
            cor = COR_AZUL if (k == len(linhas) - 1 and len(linhas) > 1) else COR_TEXTO
            M.texto(lin, t0, tf, pai, [0, y - CY], 3000, tam, cor, None, "top", fonte=FONTE_MARCA)
            y += tam * 1.08
        topo_png = int(y + 30)
        src = M.arquivo({"asset": tt["asset"]})
        arq, sw, sh, _ = M.info(src, 1000, H - topo_png - 50, png=True)
        s = min(1000 / sw, (H - topo_png - 50) / sh)
        slot = M.add(kind="null", name="slot título", parent=pai, pos=[0, topo_png + sh * s / 2 - CY], anchor=[0, 0],
                     **{"in": t0, "out": tf}, scale_keys=[[t0, 0, [0, 0, 800, 18]], [t0 + POP, 100, [0, 85, 0, 0]]])
        M.caixa(pai, -sw * s / 2, topo_png - CY, sw * s / 2, topo_png + sh * s - CY)
        M.add(kind="footage", name="título png", file=str(arq), parent=slot, src=[sw, sh], scale=s * 100, pos=[0, 0],
              **{"in": t0, "out": tf}, start=0, shadow={"op": 110, "soft": 40 / s, "dist": 6 / s})

    # ---------- estados ----------
    estados = []
    for c in plano["cenas"]:
        for k, e in enumerate(c["estados"]):
            e["_cena"], e["_ultimo"] = c["id"], k == len(c["estados"]) - 1
            estados.append(e)
    # a última palavra que entra num estado (rótulo/texto) precisa de ≥ 1,2 s na tela: se a fala dela vem colada
    # na troca, o estado seguinte espera até 0,8 s ("receiver" do B9 ficava 0,8 s, positions bloco 05, 2026-10-12)
    for k, (e, prox) in enumerate(zip(estados, estados[1:])):
        ts = [r[1] for r in (e.get("rotulos") or [])] + [t[1] for t in (e.get("textos") or [])]
        if ts and prox["ini"] - max(ts) < 1.2:
            teto = estados[k + 2]["ini"] - 1.0 if k + 2 < len(estados) else plano["fim"]   # o seguinte não some
            prox["ini"] = max(prox["ini"], min(max(ts) + 1.2, prox["ini"] + 0.8, teto))
    for i, e in enumerate(estados):
        ini = e["ini"]
        # B11: o próximo estado entra POR CIMA; este fica na tela (desfocado) até o fim dele e sai junto
        foco = i + 1 < len(estados) and estados[i + 1]["layout"] == "B11"
        k_fim = i + 2 if foco else i + 1
        fim = estados[k_fim]["ini"] if k_fim < len(estados) else plano["fim"] + 0.6
        cards = e.get("cards", [])
        dono = estados[i + 1] if foco else e
        anim = bool(cards) and (not dono["_ultimo"] or dono.get("saida") == "animada")
        n0 = len(M.layers)
        saida_fim = fim + SOBREPOE if anim else fim
        saida_ini = saida_fim - SAIDA
        pai = M.null_estado(ini, saida_fim, saida_fim, f"{e['_cena']} {e['layout']}")

        asps = [M.aspecto(c) if not c.get("png") else None for c in cards]
        geos_png = []
        for j, c in enumerate(cards):
            if c.get("png"):
                arq, sw, sh, _ = M.info(M.arquivo(c), 600, 360, png=True)
                asps[j] = sw / sh
        lay_geo = e["layout"]
        if lay_geo in ("C1", "C8") and any(c.get("acima") for c in cards):
            lay_geo = "C4"          # com nome acima: cards um pouco menores e mais baixos (espaço para o título)
        geo = geometria(lay_geo, asps, [bool(c.get("png")) for c in cards],
                        [not c.get("png") and M.inteiro(c) for c in cards])
        # mapa/logo/bandeira não podem ser cortados para preencher o card: o card toma o formato da imagem, dentro
        # do espaço do layout ("DETROIT" cortado no mapa 4:3 em card quadrado, "G" dos Packers cortado — 2026-10-13)
        for j, c in enumerate(cards):
            if not c.get("png") and M.inteiro(c):
                x, y, w, h = geo[j]
                a_ = M.aspecto(c)
                w, h = (h * a_, h) if w / h > a_ else (w, w / a_)
                geo[j] = (x, y, w, h)

        sobre_pend = []
        t_ant = None
        for j, (c, (x, y, w, h)) in enumerate(zip(cards, geo)):
            t_in = max(ini - 0.05, c["t"] - ANTECIPA)
            if j == 0 and e["layout"] != "A":
                t_in = min(t_in, ini + 0.1)
            # pilha (C9): cards na mesma palavra subiam juntos, já empilhados, e pareciam um card só (cold open do
            # Super Bowl Rings, 2026-10-13). O de trás entra primeiro e o da frente pousa por cima PILHA_ESCALONA s
            # depois, sem passar de 1,8 s na tela.
            if e["layout"] == "C9" and t_ant is not None and t_in < t_ant + PILHA_ESCALONA:
                t_in = max(t_in, t_ant + max(0.0, min(PILHA_ESCALONA, fim - t_ant - 1.8)))
            t_ant = t_in
            png = c.get("png")
            arq, sw, sh, dur = M.info(M.arquivo(c), w, h, png=png)
            rel = [x - CX, y - CY]
            M.caixa(pai, rel[0] - w / 2, rel[1] - h / 2, rel[0] + w / 2, rel[1] + h / 2)
            M.registro.append({"tipo": "card", "pai": pai, "in": t_in, "out": saida_fim, "png": bool(png),
                               "id": c.get("asset") or c.get("arquivo"),
                               "box": [rel[0] - w / 2, rel[1] - h / 2, rel[0] + w / 2, rel[1] + h / 2]})
            if png:
                slot = M.add(kind="null", name=f"slot {j+1}", parent=pai, pos=rel, anchor=[0, 0],
                             **{"in": t_in, "out": saida_fim},
                             scale_keys=[[t_in, 0, [0, 0, 800, 18]], [t_in + POP, 100, [0, 85, 0, 0]]] +
                             ([[saida_ini, 100, [0, 0, 0, 85]], [saida_fim, 0, [0, 30, 0, 0]]] if anim else []))
                s = min(w / sw, h / sh)
                M.add(kind="footage", name=Path(arq).name, file=str(arq), parent=slot, src=[sw, sh], scale=s * 100,
                      pos=[0, 0], **{"in": t_in, "out": saida_fim}, start=0,
                      shadow={"op": 110, "soft": 30 / s, "dist": 5 / s})
            else:
                lado = x - CX
                ent = ("esq" if lado < 0 else "dir") if abs(lado) > 330 else "baixo"
                sai = ("esq" if lado < 0 else "dir") if abs(lado) > 150 else "baixo"
                if e["layout"] == "D4":
                    ent, sai = "dir", "esq"
                ent, sai = c.get("entra", ent), c.get("sai", sai)

                def fora(d):
                    if d == "baixo":
                        return [rel[0], H / 2 + h / 2 + 80]
                    if d == "esq":
                        return [-W / 2 - w / 2 - 80, rel[1]]
                    if d == "cima":
                        return [rel[0], -H / 2 - h / 2 - 80]
                    return [max(W / 2, rel[0]) + w / 2 + 80, rel[1]]

                # B10: entra no centro e, ~0,5 s antes do 1º rótulo, desliza ~0,45 s até a posição final (v8#56)
                rel_fim = rel
                desliza = e["layout"] == "B10" and j == 0 and e.get("rotulos")
                if desliza:
                    rel = [0, rel_fim[1]]
                    M.caixa(pai, -w / 2, rel[1] - h / 2, w / 2, rel[1] + h / 2)
                    ent = c.get("entra", "baixo")
                f0 = fora(ent)
                vx, vy = rel[0] - f0[0], rel[1] - f0[1]
                norm = (vx * vx + vy * vy) ** 0.5
                quase = [rel[0] - vx / norm * DERIVA, rel[1] - vy / norm * DERIVA]
                # Bézier de ease-out cúbico: sai com 3·D/T (influência 33%), chega parado (influência 67%)
                t_ent = ENTRADA
                if anim:
                    t_ent = min(ENTRADA, max(0.35, saida_ini - t_in - 0.05))
                pk = [[t_in, f0, [0, 0, 3 * norm / t_ent, 33.3]],
                      [t_in + t_ent, rel, [0, 66.7, 0, 66.7]]]
                if desliza:
                    t_d = max(t_in + t_ent + 0.05, e["rotulos"][0][1] - 0.5)
                    pk[-1][2] = [0, 66.7, 0, 50]
                    pk.append([t_d, rel, [0, 66.7, 0, 50]])
                    pk.append([t_d + 0.45, rel_fim, [0, 50, 0, 66.7]])
                    rel = rel_fim
                    e["_b10_desliza_fim"] = t_d + 0.45   # o 1º rótulo espera o card abrir o espaço
                if anim:
                    # ease-in cúbico: começa parado (influência 67%), sai a 3·D/T (influência 33%)
                    f1 = fora(sai)
                    d1 = ((f1[0] - rel[0]) ** 2 + (f1[1] - rel[1]) ** 2) ** 0.5
                    pk.append([max(saida_ini, pk[-1][0] + 0.02), rel, [0, 66.7, 0, 50]])
                    # ease-in quadrático (mais suave que o cúbico): chega à borda a 2·D/T
                    pk.append([saida_fim, f1, [2 * d1 / SAIDA, 50, 0, 33.3]])
                slot = M.add(kind="null", name=f"slot {j+1}", parent=pai, anchor=[0, 0], pos_keys=pk,
                             **{"in": t_in, "out": saida_fim})
                # B6: o quadro fica, o conteúdo troca por corte nas palavras
                fontes = [(arq, sw, sh, dur, t_in)]
                for tr in c.get("troca", []):
                    a2, sw2, sh2, d2 = M.info(M.arquivo(tr), w, h)
                    fontes.append((a2, sw2, sh2, d2, tr["t"] - 0.05))
                for k3, (a2, sw2, sh2, d2, ti) in enumerate(fontes):
                    to = fontes[k3 + 1][4] if k3 + 1 < len(fontes) else saida_fim
                    s = max(w / sw2, h / sh2)
                    lay = dict(kind="footage", name=Path(a2).name, file=str(a2), parent=slot, src=[sw2, sh2],
                               scale=s * 100, pos=[0, 0], start=ti if d2 else 0, crop=[w / s, h / s],
                               radius=0.05 * min(w, h) / s,
                               shadow={"op": 128, "soft": min(250, 30 / s), "dist": 4 / s}, motion_blur=True)
                    if k3 == 0:
                        lay["opacity_keys"] = [[t_in, 0], [t_in + 0.2, 100]]
                    elif c.get("dissolve"):
                        # M3/T3 (v8#119, v6#75): o novo conteúdo se dissolve por cima do anterior em ~0,4 s
                        lay["opacity_keys"] = [[ti, 0], [ti + 0.4, 100]]
                    if c.get("dissolve") and k3 + 1 < len(fontes):
                        to = min(saida_fim, to + 0.4)
                    lay["in"], lay["out"] = ti, to
                    if d2 and to - ti > d2 - 0.05:
                        lay["timeremap"] = True
                    M.add(**lay)

            # elementos presos ao card
            if c.get("sticker"):
                sid, st = c["sticker"]
                sa, ssw, ssh, _ = M.info(M.arquivo({"asset": sid}), 300, 200, png=True)
                sh_alvo = 0.26 * h
                ss = min(sh_alvo / ssh, 0.55 * w / ssw)   # logo largo (letreiro) não pode passar da largura do card
                if c.get("sticker_pos") == "dentro":
                    ss = min(0.13 * h / ssh, 0.25 * w / ssw)   # M7 (v6#74): bandeira pequena dentro do mapa, no alto à direita
                sh_alvo, sw_alvo = ssh * ss, ssw * ss
                pos_st = [(-w / 2 + sw_alvo / 2 + 0.03 * w) if sw_alvo > 2 * sh_alvo else (-w / 2 + sw_alvo * 0.32), -h / 2 + sh_alvo * 0.30]  # letreiro largo fica por dentro do canto
                if c.get("sticker_pos") == "dentro":
                    pos_st = [w / 2 - sw_alvo / 2 - 0.06 * w, -h / 2 + sh_alvo / 2 + 0.06 * h]
                sl = M.add(kind="null", name="sticker", parent=slot, anchor=[0, 0],
                           pos=pos_st,
                           **{"in": st - 0.1, "out": saida_fim},
                           scale_keys=[[st - 0.1, 0, [0, 0, 800, 18]], [st - 0.1 + POP, 100, [0, 85, 0, 0]]])
                M.add(kind="footage", name="sticker " + sid, file=str(sa), parent=sl, src=[ssw, ssh], scale=ss * 100,
                      pos=[0, 0], start=0, **{"in": st - 0.1, "out": saida_fim},
                      shadow={"op": 120, "soft": 14 / ss, "dist": 4 / ss})
            if c.get("lateral"):
                # E5/F9: bandeira chapada (~48% da altura do card) cobrindo ~29% da borda direita (v5#2);
                # M5: globo (~85% da altura) cobrindo ~33%, entra ROLANDO pela direita (v7#181)
                la = c["lateral"]
                globo = la.get("forma") == "globo"
                la_a, lw_, lh_, _ = M.info(M.arquivo(la), 700, 700, png=True)
                alvo_h = (0.85 if globo else 0.48) * h
                ls = alvo_h / lh_
                lwid = lw_ * ls
                # logo/bandeira larga não pode passar da margem direita da tela (o zoom da cena aumenta ~10%)
                esq = CX + rel[0] + w / 2 - (0.33 if globo else 0.29) * w
                cabe = (W - MARGEM - CX) / 1.1 + CX - esq
                if lwid > cabe:
                    ls *= cabe / lwid
                    lwid, alvo_h = cabe, lh_ * ls
                lx = w / 2 - (0.33 if globo else 0.29) * w + lwid / 2
                M.caixa(pai, rel[0] + lx - lwid / 2, rel[1] - alvo_h / 2, rel[0] + lx + lwid / 2, rel[1] + alvo_h / 2)
                tl = max(t_in + 0.3, la["t"] - 0.15)
                dist = W / 2 - (rel[0] + lx) + lwid / 2 + 80
                # rolando: ângulo = distância / raio (metade, para não girar demais); começa rápido como a posição
                ang = dist / (lwid / 2) * 57.3 * 0.5
                kw_rot = {"rot_keys": [[tl, ang, [0, 0, -3 * ang / 0.8, 33.3]], [tl + 0.8, 0, [0, 66.7, 0, 66.7]]]} if globo else {}
                ln = M.add(kind="null", name="lateral", parent=slot, anchor=[0, 0], **{"in": tl, "out": saida_fim},
                           pos_keys=[[tl, [lx + dist, 0], [0, 0, 3 * dist / 0.8, 33.3]], [tl + 0.8, [lx, 0], [0, 66.7, 0, 66.7]]],
                           **kw_rot)
                M.add(kind="footage", name="lateral " + Path(la_a).name, file=str(la_a), parent=ln, src=[lw_, lh_],
                      scale=ls * 100, pos=[0, 0], start=0, **{"in": tl, "out": saida_fim},
                      shadow={"op": 110, "soft": 30 / ls, "dist": 5 / ls}, motion_blur=True)
            seq = c.get("sobre", [])
            for k2, (txt, tt_) in enumerate(seq):
                prox = seq[k2 + 1][1] - 0.13 if k2 + 1 < len(seq) else saida_fim
                # criado depois de todos os cards do estado: um card que entra depois (mapa do F8, cascata,
                # sanduíche) não cobre o texto ("5,300 PEOPLE" coberto pelo mapa, bloco 02, 2026-10-08)
                sobre_pend.append((txt.upper(), max(t_in + 0.25, tt_ - 0.05), prox, slot, min(1300, w * 0.78),
                                   (x, y)))
            if c.get("legenda"):
                # B7: nas referências é texto branco centralizado e médio (ex.: "casein"), não rodapé miúdo
                txt, tt_ = c["legenda"]
                M.texto(txt.upper(), max(t_in + 0.25, tt_ - 0.05), saida_fim, slot, [0, 0], w * 0.78, 110, [1, 1, 1],
                        None, fonte=FONTE_MARCA, caixa=COR_CAIXA)
            if c.get("citacao"):
                # G1: caixa de citação começa a ~110 px da borda esquerda, centrada em y, por cima do card
                ci = c["citacao"]
                nome_c = "citacao_" + hashlib.md5((ci["texto"] + "|" + ci.get("grifo", "") + "|" + ci.get("fonte", "")).encode()).hexdigest()[:10] + ".png"
                ca, cw, chh = desenhar_citacao(M.cache / nome_c, ci["texto"], ci.get("grifo", ""), ci.get("fonte", ""))
                bw, bh = cw / 2, chh / 2
                tc = max(t_in + 0.3, ci["t"] - 0.05)
                pc = [110 + bw / 2 - CX, 0]
                M.caixa(pai, pc[0] - bw / 2, -bh / 2, pc[0] + bw / 2, bh / 2)
                slc = M.add(kind="null", name="citação", parent=pai, anchor=[0, 0], **{"in": tc, "out": saida_fim},
                            pos_keys=[[tc, [pc[0] - 60, 0], [0, 0, 3 * 60 / 0.35, 33.3]], [tc + 0.35, pc, [0, 66.7, 0, 66.7]]])
                okc = [[tc, 0], [tc + 0.2, 100]] + ([[saida_ini, 100], [saida_ini + 0.3, 0]] if anim else [])
                M.add(kind="footage", name="citação", file=str(ca), parent=slc, src=[cw, chh], scale=50, pos=[0, 0],
                      start=0, **{"in": tc, "out": saida_fim}, opacity_keys=okc,
                      shadow={"op": 120, "soft": 40, "dist": 8})
            if c.get("acima"):
                # B8/C4: título grande logo acima do card; com vizinhos, limita à largura do card
                txt, tt_ = c["acima"]
                largura = w * 1.05 if len(cards) > 1 else min(1500, max(w * 1.8, 700))
                M.texto(txt.upper(), tt_ - 0.05, saida_ini if anim else fim, pai, [rel[0], rel[1] - h / 2 - 12],
                        largura, 130, COR_TEXTO, SOMBRA_PRETO, "bottom", fonte=FONTE_MARCA)

        # cards que se sobrepõem (cascata D6, sanduíche...): o nome de um card sai quando o do card seguinte entra
        # em cima dele ("JERRY KRAMER / KEN BOWMAN / JETHRO PUGH / BART STARR" empilhados, positions 07, 2026-10-13)
        for p_ in range(len(sobre_pend)):
            for q_ in range(p_ + 1, len(sobre_pend)):
                A_, B_ = sobre_pend[p_], sobre_pend[q_]
                if A_[0] is None or not (A_[1] < B_[1] < A_[2]):
                    continue
                (ax, ay), (bx, by) = A_[5], B_[5]
                if abs(ax - bx) < (A_[4] + B_[4]) / 2 and abs(ay - by) < 150:
                    sobre_pend[p_] = A_[:2] + (B_[1] - 0.05,) + A_[3:]
        for txt, t0_, t1_, slot_, larg_, _c in sobre_pend:
            M.texto(txt, t0_, t1_, slot_, [0, 0], larg_, 120, [1, 1, 1], None, fonte=FONTE_MARCA, caixa=COR_CAIXA)
        if e["layout"] == "CTA":
            cta(M, e, pai, ini, fim)
        # rótulos ao lado (B4/B5) e textos do estado
        if e.get("rotulos"):
            dir_card = geo[0][0] + geo[0][2] / 2
            area_cx = (dir_card + 50 + W - 70) / 2
            area_w = W - 70 - dir_card - 50
            if e["layout"] == "B10":
                # nome à esquerda, colado no card (~30 px), como "Anna Pavlova" (v8#164)
                esq_card = geo[0][0] - geo[0][2] / 2
                area_cx, area_w = (70 + esq_card - 30) / 2, esq_card - 30 - 70
            rs = e["rotulos"]
            if e["layout"] == "B9":
                # v7#219: as palavras se EMPILHAM a partir do alto do card (não trocam); ~100 px, 147 px entre linhas
                topo = geo[0][1] - geo[0][3] / 2 + 0.12 * geo[0][3]
                tam = min(110, area_w / (max(len(t) for t, _ in rs) * 0.62))
                for k2, (txt, tt_) in enumerate(rs):
                    M.texto(txt, tt_ - 0.05, saida_ini if anim else fim, pai, [area_cx - CX, topo - CY + k2 * tam * 1.45],
                            area_w, tam, COR_TEXTO, SOMBRA_PRETO, "top")
                rs = []
            rs = [[txt, tt_] for txt, tt_ in rs]
            if rs and e.get("_b10_desliza_fim"):
                # B10: o nome só aparece no espaço que o card abriu (antes, com a fala cedo, "19 years"
                # entrava com o card ainda no centro, por cima da foto — bloco 00, 2026-10-11)
                rs[0][1] = max(rs[0][1], e["_b10_desliza_fim"] - 0.1)
            # rótulo que ficaria < 1,2 s na tela entra junto com o seguinte, em 2 linhas: "Tom Brady" → "199th pick"
            # → "2000 draft" trocava a cada ~0,8 s e não dava para ler (positions, bloco 01, 2026-10-12)
            juntos = []
            for txt, tt_ in rs:
                if juntos and tt_ - juntos[-1][1] < 1.2 and "\r" not in juntos[-1][0]:
                    juntos[-1][0] += "\r" + txt
                else:
                    juntos.append([txt, tt_])
            rs = juntos
            for k2, (txt, tt_) in enumerate(rs):
                prox = rs[k2 + 1][1] - 0.13 if k2 + 1 < len(rs) else (saida_ini if anim else fim)
                # 1 linha se couber com letra ≥ 80 px (como "the aromatics"); senão quebra
                uma_linha = "\r" in txt or len(txt) * 0.56 * 80 <= area_w
                M.texto(txt if uma_linha else linhas_rotulo(txt), tt_ - 0.05, prox, pai, [area_cx - CX, 0], area_w, 140,
                        COR_TEXTO, SOMBRA_PRETO)
        ts = e.get("textos", [])
        # A4 em que uma frase ficaria < 1 s ("a gap opens" → "then closes" 0,69 s; "one snap" 0,37 s): as frases
        # EMPILHAM em vez de trocar, como lista (positions 01/04/20, 2026-10-13 — o QA novo reprova < 0,7 s)
        pilha = (e["layout"] == "A4" and len(ts) > 1 and len(ts) <= 4
                 and any(ts[k + 1][1] - ts[k][1] < 1.0 for k in range(len(ts) - 1)))
        if (_frase_que_cresce(ts) and e["layout"] != "A4") or pilha:
            # A2 contínua ("This is" → "every NFL position" → "explained"): nada some. Cada pedaço novo entra
            # numa linha embaixo e o bloco sobe meia linha, para ficar centrado. Com A4 + troca de estado o final
            # do cold open parecia 3 cenas: a frase sumia, palco vazio, outra entrava (bloco 00, 2026-10-11)
            LH = 175
            pedacos, base = [ts[0][0]], ts[0][0]
            for tx in ts[1:]:
                pedacos.append(tx[0] if pilha else tx[0][len(base.strip(" ,.;:")):].strip(" ,;:"))
                base = tx[0]
            tempos = [max(ini - 0.02, tx[1] - 0.05) for tx in ts]
            pk = [[tempos[0], [0, 0], [0, 66.7, 0, 66.7]]]
            for k2 in range(1, len(ts)):
                pk.append([tempos[k2], [0, -(k2 - 1) * LH / 2], [0, 66.7, 0, 66.7]])
                pk.append([tempos[k2] + 0.35, [0, -k2 * LH / 2], [0, 66.7, 0, 66.7]])
            grupo = M.add(kind="null", name="frase que cresce", parent=pai, anchor=[0, 0], pos_keys=pk,
                          **{"in": tempos[0], "out": fim})
            for k2, txt in enumerate(pedacos):
                M.texto(txt, tempos[k2], fim, grupo, [0, k2 * LH], 1660, 150, COR_TEXTO, SOMBRA_PRETO)
            M.caixa(pai, -830, -len(ts) * LH / 2, 830, len(ts) * LH / 2)
            ts = []
        for k2, tx in enumerate(ts):
            txt, tt_ = tx[0], tx[1]
            modo = tx[2] if len(tx) > 2 else ""
            if modo == "cresce":
                # só "cresce" de verdade se completa a frase anterior; senão é troca normal. "November 18, 1985" →
                # "Monday Night Football" marcado cresce: a data sumia num corte e o novo entrava sem fade (08, 2026-10-13)
                ant_ = (ts[k2 - 1][0] if k2 else ((estados[i - 1].get("textos") or [[""]])[-1][0] if i > 0 else ""))
                b_ = ant_.strip(" ,.;:").lower()
                if not (b_ and txt.lower().startswith(b_) and txt[len(b_):].strip(" ,.;:")):
                    modo = ""
            if k2 + 1 < len(ts):
                nx = ts[k2 + 1]
                cresce = (len(nx) > 2 and nx[2] == "cresce" and txt.strip(" ,.;:")
                          and nx[0].lower().startswith(txt.strip(" ,.;:").lower()))
                prox = nx[1] - (0.0 if cresce else 0.13)
            else:
                prox = saida_ini if (anim and modo == "abaixo") else fim
            t_in = max(ini - 0.02, tt_ - 0.05)
            if modo == "faixa":
                # texto branco na faixa azul (o estilo do "sobre"), no lugar livre do layout: no E3 ao lado do
                # recorte. "52 diamonds = Super Bowl 52" preto por cima do anel ficou ruim (rings, bloco 06, 2026-10-14)
                if e["layout"] == "E3" and geo:
                    dir_card = geo[0][0] + geo[0][2] / 2
                    pos_, larg_ = [(dir_card + 60 + W - 200) / 2 - CX, 0], W - 200 - dir_card - 60
                elif e["layout"] == "CTA":
                    pos_, larg_ = [0, 260], 1300        # embaixo do botão (nome do canal)
                else:
                    pos_, larg_ = [0, 0], 1300
                M.texto(txt.upper(), t_in, prox, pai, pos_, larg_, 120, [1, 1, 1], None, fonte=FONTE_MARCA,
                        caixa=COR_CAIXA)
            elif modo == "abaixo":
                M.texto(txt.upper(), t_in, prox, pai, [0, 830 - CY], 1400, 130, COR_TEXTO, SOMBRA_PRETO, fonte=FONTE_MARCA)
            elif modo == "2linhas":
                M.texto(duas_linhas(txt, 10), t_in, prox, pai, [0, 0], 1500, 140, COR_TEXTO, SOMBRA_PRETO)
            elif e["layout"] == "A4":
                # frases encadeadas (v5#29–31, medido a 30 fps): a frase SOME DE UMA VEZ, ~0,17 s de palco vazio e a
                # próxima aparece em ~0,1 s no mesmo lugar (o "cinza" das folhas de contato era esse frame da entrada)
                if k2 + 1 < len(ts):
                    prox = ts[k2 + 1][1] - 0.05 - 0.17
                lid = M.texto(txt, t_in, prox, pai, [0, 0], 1660, 150, COR_TEXTO, SOMBRA_PRETO)
                M.layers[lid]["opacity_keys"] = [[t_in, 0], [t_in + 0.1, 100]]
                M.layers[lid]["blur_keys"] = [[t_in, 6], [t_in + 0.1, 0]]
            elif e["layout"] == "E3" and geo:
                # E3 (v1#139): recorte de um lado, texto do outro. Ia para o centro e ficava por cima do
                # capacete ("since 1994", positions bloco 01, 2026-10-12). Termina 200 px antes da borda: com 70
                # encostava nos adesivos do fundo
                dir_card = geo[0][0] + geo[0][2] / 2
                M.texto(txt, t_in, prox, pai, [(dir_card + 60 + W - 200) / 2 - CX, 0], W - 200 - dir_card - 60, 150,
                        COR_TEXTO, SOMBRA_PRETO)
            else:
                ant = (estados[i - 1].get("textos") or [[""]])[-1][0] if i > 0 and k2 == 0 else (ts[k2 - 1][0] if k2 else "")
                base = ant.strip(" ,.;:").lower()
                if modo == "cresce" and base and txt.lower().startswith(base) and txt[len(base):].strip(" ,.;:"):
                    # A2 que se completa: a frase de antes FICA igual (mesmo tamanho e lugar) e só o que falta
                    # entra embaixo. Trocar pela frase inteira encolhia o texto (150 → ~100 px) num salto.
                    resto = txt[len(base):].strip(" ,;:")
                    M.texto(ant, t_in, prox, pai, [0, 0], 1660, 150, COR_TEXTO, SOMBRA_PRETO, fade=False)
                    M.texto(resto, t_in, prox, pai, [0, 175], 1660, 150, COR_TEXTO, SOMBRA_PRETO)
                    continue
                M.texto(txt, t_in, prox, pai, [0, 0], 1660, 150, COR_TEXTO, SOMBRA_PRETO, fade=(modo != "cresce"))

        if anim and not foco:
            # texto que vai até o fim do estado sai JUNTO com os cards (mesma janela da saída, 0,8 s). Antes sumia
            # num corte seco no início/fim da saída e a imagem ainda ficava saindo (positions bloco 01, 2026-10-12)
            for L in M.layers[n0:]:
                if L["kind"] == "text" and saida_ini - 0.15 <= L["out"] <= saida_fim + 0.01:
                    L["out"] = saida_fim
                    ok = [k for k in (L.get("opacity_keys") or []) if k[0] < saida_ini]
                    L["opacity_keys"] = ok + [[saida_ini, 100], [saida_fim, 0]]

        if foco:
            # B11: o que está na tela desfoca (~18 px na tela) e apaga um pouco quando o card novo entra (v6#118)
            tf = estados[i + 1]["ini"]
            for L in M.layers[n0:]:
                if L["kind"] not in ("footage", "text"):
                    continue
                bl = min(500, 18 * 100 / L.get("scale", 100))   # o efeito age no tamanho original da camada
                alvo = 0 if L["kind"] == "text" else 80        # textos de trás somem (apareciam por cima do card novo)
                if L["in"] >= tf - 0.05:
                    # entra depois do foco (nome acima, troca): já nasce desfocado/escondido
                    L["blur_keys"], L["opacity_keys"] = [[L["in"], bl]], [[L["in"], alvo]]
                    continue
                for ch, v0, v1 in (("blur_keys", 0, bl), ("opacity_keys", 100, alvo)):
                    ks = [k for k in (L.get(ch) or []) if k[0] < tf]
                    L[ch] = ks + [[tf, ks[-1][1] if ks else v0], [tf + 0.4, v1]]

    M.limitar_zoom()
    # o bloco acaba 0,6 s depois da última palavra (ou quando a última saída animada termina): com + 3 s fixos
    # cada prévia tinha ~3 s de silêncio no fim e o Arthur cortava tudo à mão ao juntar os blocos (2026-10-11).
    # O bloco seguinte começa 0,2 s antes da fala, então a emenda fica com ~0,8 s de pausa.
    ultimo = max([L["out"] for L in M.layers if isinstance(L.get("out"), (int, float))] + [0])
    dur = min(max(plano["fim"] + FIM_BLOCO, ultimo), plano["fim"] + 2)
    dados = {"nome": plano["nome"], "dur": round(dur, 2), "fps": FPS, "audio": str(audio), "fonte": FONTE,
             "audio_offset": plano.get("offset_audio", 0),
             "cor_fundo": COR_FUNDO, "cor_sombra": COR_SOMBRA, "fundo_imagem": FUNDO_IMAGEM,
             "layers": M.layers, "salvar": str(proj / "edicao" / f"bloco_{a.item}_v2.aep"),
             "log": str(proj / "edicao" / f"log_{a.item}_v2.txt")}
    modelo = (Path(__file__).parent / "montar_modelo2.jsx").read_text()
    # posições/tempos finais de textos e cards (o QA confere texto por cima de imagem e texto rápido demais)
    reg = []
    for r_ in M.registro:
        r2 = {k: v for k, v in r_.items() if k != "lid"}
        r2["estado"] = M.layers[r_["pai"]].get("name", "")
        if r_["tipo"] == "texto":
            L_ = M.layers[r_["lid"]]
            r2["in"], r2["out"] = L_["in"], L_["out"]
            r2["opacidade_fim"] = (L_.get("opacity_keys") or [[0, 100]])[-1][1]
        reg.append(r2)
    (proj / "edicao" / f"layout_{a.item}.json").write_text(json.dumps(reg, ensure_ascii=False, indent=0))
    jsx = proj / "edicao" / f"montar_{a.item}_v2.jsx"
    jsx.write_text("var DADOS = " + json.dumps(dados, ensure_ascii=False) + ";\n" + modelo)
    print(jsx, len(M.layers), "layers")


if __name__ == "__main__":
    main()
