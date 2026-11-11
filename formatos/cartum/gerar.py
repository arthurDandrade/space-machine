"""Montador do cartum: lê edicao/plano_edicao_<item>.json e escreve edicao/plano_render_<item>.json, que o compositor
sem After (motor/edicao_ff/compor.py) desenha. Não há modelo do After neste formato.

Uso: python gerar.py <projeto> [--item 01]

O visual vem da medição dos 4 vídeos de referência (conhecimento/01 - Formato/Vídeos de Referência.md): fundo liso
azul-claro, o nome do tópico no topo com a miniatura dele no canto, e os desenhos recortados entrando um a um na
palavra dita, EM CORTE SECO (nada de fusão, deslize ou zoom: medido quadro a quadro), até a tela limpar no estado
seguinte. Um estado do cenas.json = uma tela; os cards vão em colunas, na ordem em que foram escritos.
O que cada card pode levar: acima, legenda, sticker, troca e opcoes {balao, x, seta, circulo, tamanho}; no estado,
textos = a data embaixo do nome do tópico. Está tudo em storyboard.md.
O bloco abre com a GRADE de todos os tópicos do vídeo (o desenho-símbolo e o nome de cada um, lidos dos blocos
irmãos), que aproxima no tópico que vai começar. Tópico cujo símbolo ainda não existe aparece só com o nome: por
isso o vídeo final manda gerar de novo (formato.json › edicao.regerar_no_final).
"""
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "motor"))
sys.path.insert(0, str(AQUI.parents[1] / "motor" / "edicao_ff"))
import caminhos  # noqa: E402
from compor import fonte as _fonte  # noqa: E402  (a mesma fonte que o compositor vai desenhar)

W, H = 1920, 1080
FPS = 30
FIM_BLOCO = 0.4
AREA = (70, 190, 1850, 1040)      # onde os cards ficam (x0, y0, x1, y1): abaixo do cabeçalho
VAO = 40
PESO = {"grande": 1.5, "pequeno": 0.6}
FOTO_MAX = (560, 520)             # foto real: pequena, com a borda esfumada
TOPO_NOME = (W / 2, 58)           # cabeçalho: nome do tópico
TOPO_DATA = (W / 2, 132)          # data ou número logo abaixo
MINI = (1836, 82, 150, 130)       # miniatura do tópico no canto (cx, cy, largura, altura da caixa)
TITULO_IMG = (W / 2, 470, 760, 600)
TITULO_NOME = (W / 2, 880)
VIRA = 0.35                       # o cartão do tópico encolhe para o cabeçalho
# grade de abertura (medido na referência: a grade com todos os tópicos fica 0,8 s, aproxima em 0,5 s para o tópico
# que vai começar e corta para ele; entre tópicos ela volta por ~0,5 s). Aqui: no 1º tópico segura 0,8 s, nos outros
# 0,5 s, e em 0,6 s a câmera aproxima e o tópico vira o cartão dele, sem corte.
GRADE_SEGURA_1, GRADE_SEGURA, GRADE_ZOOM = 0.6, 0.3, 0.5
CARTAO_TOPICO = 1.2               # s do cartão do tópico (símbolo grande + nome) depois da aproximação
# A abertura inteira dura ~2 s (grade 0,3 s + aproximação 0,5 s + cartão 1,2 s; no 1º tópico a grade fica
# 0,6 s), como na referência: grade inteira ~0,25 s, aproximação, ~1,75 s parada no tópico e já entra o
# conteúdo, com a 1ª frase ainda sendo dita. Até 2026-11-10 o cartão ficava parado a 1ª frase inteira (6,3 s
# em média num vídeo de 10 tópicos).
GRADE_AREA = (70, 50, 1850, 1040)
TEXTO_MIN = 1.0             # s que um rótulo, legenda ou balão precisa ficar na tela para dar para ler
ZOOM_COBRE, ZOOM_T = 1.1, 0.12  # a aproximação: o desenho com 1,1× a largura da tela; abre para o inteiro em ZOOM_T s
PESO_ZOOM = 2.6                 # depois de abrir, o desenho da aproximação fica com 2,6 colunas
EASE_OUT = [0, 0.1, 0, 80]
EASE_IN = [0, 80, 0, 0.1]
CAMADAS = {"fundo": 0, "conteudo": 1, "ui": 2}


def _rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def visual():
    """formato.json › visual, com canal.json › visual por cima."""
    return {**caminhos.ficha().get("visual", {}), **caminhos.canal_json().get("visual", {})}


def largura(txt, tam, fonte):
    return max(_fonte(fonte, tam).getlength(ln) for ln in txt.split("\r"))


def quebrar(txt, tam, fonte, max_w):
    """Quebra em até 2 linhas quando não cabe em max_w."""
    if largura(txt, tam, fonte) <= max_w or " " not in txt:
        return txt
    pal = txt.split()
    melhor = min(range(1, len(pal)), key=lambda k: max(largura(" ".join(pal[:k]), tam, fonte),
                                                       largura(" ".join(pal[k:]), tam, fonte)))
    return " ".join(pal[:melhor]) + "\r" + " ".join(pal[melhor:])


def _par(v):
    """["texto", t] do plano de edição → (texto, t); texto solto → (texto, None)."""
    if isinstance(v, (list, tuple)):
        return str(v[0]), (v[1] if len(v) > 1 and isinstance(v[1], (int, float)) else None)
    return str(v), None


class Montador:
    def __init__(self, proj):
        self.proj = proj
        self.cache = proj / "edicao" / "_cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.layers, self.registro = [], []
        self.manif = {m["id"]: m for m in json.loads((proj / "manifesto.json").read_text())["assets"]}
        v = visual()
        self.cor_fundo, self.cor_texto = _rgb(v.get("cor_fundo", "#BFE9FF")), _rgb(v.get("cor_texto", "#111111"))
        self.destaque = _rgb(v.get("cor_destaque", "#D7191C"))
        self.fonte, self.fonte_titulo = v.get("fonte", "ChalkboardSE-Regular"), v.get("fonte_titulo", "ChalkboardSE-Bold")

    # ---------- base ----------
    def add(self, **kw):
        kw["id"] = len(self.layers)
        kw.setdefault("parent", None)
        kw.setdefault("camada", "conteudo")
        self.layers.append(kw)
        return kw["id"]

    def reg(self, tipo, nome, t_in, t_out, box):
        self.registro.append({"tipo": tipo, "txt": nome, "id": nome, "in": round(t_in, 2), "out": round(t_out, 2),
                              "box": [round(v) for v in box], "pai": None})

    def texto(self, txt, t_in, t_out, pos, tam, fonte=None, cor=None, max_w=1500, tipo="texto", **extra):
        fonte = fonte or self.fonte
        self.add(kind="text", text=txt, pos=list(pos), size=tam, color=cor or self.cor_texto, font=fonte,
                 justify="center", tracking=0, max_w=max_w, anchor_mode="center", name=txt[:50].replace("\r", " "),
                 camada="ui", **{"in": t_in, "out": t_out, **extra})
        w_ = min(max_w, largura(txt, tam, fonte))
        h_ = tam * 1.15 * (txt.count("\r") + 1)
        self.reg(tipo, txt.replace("\r", " "), t_in, t_out, [pos[0] - w_ / 2, pos[1] - h_ / 2, pos[0] + w_ / 2, pos[1] + h_ / 2])

    def forma(self, itens, t_in, t_out, pos, nome):
        return self.add(kind="shape", items=itens, pos=list(pos), name=nome, camada="ui", **{"in": t_in, "out": t_out})

    # ---------- imagens ----------
    def arquivo(self, el):
        return self.proj / (el["arquivo"] if el.get("arquivo") else self.manif[el["asset"]]["arquivo"])

    def preparar(self, el):
        """(arquivo, largura, altura, é desenho recortado?). Desenho (PNG com alfa) é cortado no contorno; foto real
        ganha a borda esfumada. A data do arquivo entra no nome: asset trocado não usa o preparado antigo."""
        src = self.arquivo(el)
        dst = self.cache / f"{src.parent.name}_{src.stem}_{int(src.stat().st_mtime)}.png"
        im = ImageOps.exif_transpose(Image.open(src))
        recorte = im.mode in ("RGBA", "LA", "P") and im.convert("RGBA").getchannel("A").getextrema()[0] < 250
        if not dst.exists():
            im = im.convert("RGBA")
            if recorte:
                bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
                if bb:
                    im = im.crop(bb)
            esc = min(1.0, 1600 / max(im.size))
            if esc < 1:
                im = im.resize((round(im.width * esc), round(im.height * esc)), Image.LANCZOS)
            if not recorte:
                m = max(6, round(min(im.size) * 0.045))
                mascara = Image.new("L", im.size, 0)
                mascara.paste(255, (m, m, im.width - m, im.height - m))
                im.putalpha(mascara.filter(ImageFilter.GaussianBlur(m * 0.55)))
            im.save(dst)
        w, h = Image.open(dst).size
        return dst, w, h, recorte

    def imagem(self, el, t_in, t_out, cx, cy, bw, bh, nome=None, tipo="card", **extra):
        """Imagem contida na caixa (cx, cy, bw, bh), em corte seco. Devolve (largura, altura) na tela."""
        arq, sw, sh, recorte = self.preparar(el)
        if not recorte:
            bw, bh = min(bw, FOTO_MAX[0]), min(bh, FOTO_MAX[1])
        s = min(bw / sw, bh / sh) * 100
        larg, alt = sw * s / 100, sh * s / 100
        nome = nome or Path(str(el.get("asset") or el.get("arquivo"))).name
        kw = dict(kind="footage", file=str(arq), src=[sw, sh], start=t_in, pos=[cx, cy], scale=[s, s], name=nome,
                  **{"in": t_in, "out": t_out})
        kw.update(extra)
        self.add(**kw)
        self.reg(tipo, nome, t_in, t_out, [cx - larg / 2, cy - alt / 2, cx + larg / 2, cy + alt / 2])
        return larg, alt

    # ---------- o que vai em volta do card ----------
    def balao(self, txt, t_in, t_out, cx, base, max_w):
        """Balão de pensamento/fala: elipse branca de contorno preto e três bolinhas descendo para o personagem.
        `base` = y de baixo do balão. Devolve a altura ocupada."""
        tam = 40
        txt = quebrar(txt, tam, self.fonte, max(160, max_w - 90))
        bw = max(190, min(max_w, largura(txt, tam, self.fonte) + 100))
        bh = 92 + 44 * txt.count("\r")
        cy = base - 34 - bh / 2
        preto, branco = [0.07, 0.07, 0.07], [1, 1, 1]
        itens = [{"t": "ellipse", "size": [bw, bh], "fill": branco, "stroke": preto, "sw": 4, "trim": False}]
        for k, (r, dx, dy) in enumerate([(22, -bw * 0.22, bh / 2 + 8), (14, -bw * 0.30, bh / 2 + 28)]):
            itens.append({"t": "ellipse", "size": [r, r], "fill": branco, "stroke": preto, "sw": 3, "pos": [dx, dy],
                          "trim": False})
        self.forma(itens, t_in, t_out, [cx, cy], f"balão {txt[:20]}")
        self.texto(txt, t_in, t_out, [cx, cy], tam, max_w=bw - 60)
        return bh + 40

    def seta(self, t_in, t_out, p0, p1):
        """Seta vermelha do card anterior para este: ocupa o meio do caminho entre os dois centros."""
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist
        comp = max(90, min(220, dist * 0.3))
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        a, b = [-ux * comp / 2, -uy * comp / 2], [ux * comp / 2, uy * comp / 2]
        asa = 34
        e1 = [b[0] - asa * (ux * 0.8 - uy * 0.6), b[1] - asa * (uy * 0.8 + ux * 0.6)]
        e2 = [b[0] - asa * (ux * 0.8 + uy * 0.6), b[1] - asa * (uy * 0.8 - ux * 0.6)]
        self.forma([{"t": "path", "pts": [a, b], "stroke": self.destaque, "sw": 12},
                    {"t": "path", "pts": [e1, b, e2], "stroke": self.destaque, "sw": 12}], t_in, t_out, [mx, my], "seta")

    def pensamento(self, el, t_in, t_out, cx, base, larg):
        """Balão de pensamento com um DESENHO dentro (o que o personagem imagina): a nuvem branca acima do card, um
        pouco para a direita, e as bolinhas descendo para a cabeça dele. `base` = y de baixo do balão."""
        bw, bh = 330, 215
        bcx = min(W - bw / 2 - 20, cx + min(120, larg * 0.22))
        bcy = base - 30 - bh / 2
        preto, branco = [0.07, 0.07, 0.07], [1, 1, 1]
        itens = [{"t": "ellipse", "size": [bw, bh], "fill": branco, "stroke": preto, "sw": 4, "trim": False}]
        for r, dx, dy in [(26, -bw * 0.24, bh / 2 + 6), (16, -bw * 0.33, bh / 2 + 30)]:
            itens.append({"t": "ellipse", "size": [r, r], "fill": branco, "stroke": preto, "sw": 3, "pos": [dx, dy],
                          "trim": False})
        self.forma(itens, t_in, t_out, [bcx, bcy], "balão de pensamento")
        self.imagem(el, t_in, t_out, bcx, bcy, bw - 110, bh - 70, camada="ui")       # por cima do balão

    def seta_curva(self, p0, p2, t_in, t_out, nome):
        """Seta vermelha curva de p0 até p2 (sai para o lado e desce), com a ponta em p2."""
        p1 = (min(p0[0], p2[0]) - 90, p0[1] + 6)
        pts = []
        for k in range(15):
            u = k / 14
            pts.append([(1 - u) ** 2 * p0[0] + 2 * u * (1 - u) * p1[0] + u * u * p2[0] - p0[0],
                        (1 - u) ** 2 * p0[1] + 2 * u * (1 - u) * p1[1] + u * u * p2[1] - p0[1]])
        dx, dy = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]
        d = math.hypot(dx, dy) or 1
        ux, uy = dx / d, dy / d
        b, asa = pts[-1], 30
        e1 = [b[0] - asa * (ux * 0.8 - uy * 0.6), b[1] - asa * (uy * 0.8 + ux * 0.6)]
        e2 = [b[0] - asa * (ux * 0.8 + uy * 0.6), b[1] - asa * (uy * 0.8 - ux * 0.6)]
        self.forma([{"t": "path", "pts": pts, "stroke": self.destaque, "sw": 9},
                    {"t": "path", "pts": [e1, b, e2], "stroke": self.destaque, "sw": 9}], t_in, t_out, list(p0), nome)

    def aponta(self, txt, t_in, t_out, cx, cy, larg, alt, base, onde):
        """Número ou palavra acima do card com uma seta curva que termina DENTRO do desenho ("20,000" apontando
        para as pessoas no abrigo). `onde` = (fx, fy) de −1 a 1 a partir do centro do desenho."""
        tam = 56
        tw = largura(txt, tam, self.fonte_titulo)
        tx, ty = cx + min(larg * 0.2, 140), base - 40
        self.texto(txt, t_in, t_out, [tx, ty], tam, self.fonte_titulo)
        self.seta_curva((tx - tw / 2 - 18, ty + 4), (cx + onde[0] * larg / 2, cy + onde[1] * alt / 2), t_in, t_out, "aponta")

    def detalhe(self, el, txt, t_in, t_out, cx, cy, larg, alt, base, onde):
        """Miniatura circulada: um detalhe (um desenho pequeno) dentro de um círculo vermelho acima do card, com o
        número ou a palavra ao lado e uma seta curva do círculo até o ponto do desenho grande de onde ele vem.
        `base` = y de baixo do círculo."""
        r = 105
        dcx = max(r + 30, cx - min(larg * 0.28, 220))
        dcy = base - r - 14
        self.forma([{"t": "ellipse", "size": [2 * r, 2 * r], "fill": self.cor_fundo, "stroke": self.destaque, "sw": 8,
                     "trim": False}], t_in, t_out, [dcx, dcy], "círculo do detalhe")
        self.imagem(el, t_in, t_out, dcx, dcy, 2 * r - 56, 2 * r - 56, camada="ui")
        if txt:
            tam = 52
            self.texto(txt, t_in, t_out, [dcx + r + 22 + largura(txt, tam, self.fonte_titulo) / 2, dcy - 10], tam, self.fonte_titulo)
        alvo = (cx + onde[0] * larg / 2, cy + onde[1] * alt / 2)
        self.seta_curva((dcx - r * 0.55, dcy + r * 0.86), alvo, t_in, t_out, "detalhe")

    def xis(self, t_in, t_out, cx, cy, larg, alt):
        m = min(larg, alt) * 0.42
        self.forma([{"t": "path", "pts": [[-m, -m], [m, m]], "stroke": self.destaque, "sw": 22},
                    {"t": "path", "pts": [[m, -m], [-m, m]], "stroke": self.destaque, "sw": 22}], t_in, t_out, [cx, cy], "x")

    def circulo(self, t_in, t_out, cx, cy, larg, alt):
        self.forma([{"t": "ellipse", "size": [larg + 70, alt + 70], "stroke": self.destaque, "sw": 10, "trim": False}],
                   t_in, t_out, [cx, cy], "círculo")


def caixas(cards, layout=None):
    """A caixa de cada card na AREA e quais são os pequenos. Uma fileira até 4, duas com 5 ou 6; a largura segue o
    "tamanho" do card. Layout L1 (lista): o 1º card grande à esquerda e os outros pequenos, em grade, à direita."""
    n = len(cards)
    x0, y0, x1, y1 = AREA
    if layout == "L1" and n >= 2:
        # com aproximação, o desenho grande fica com metade da tela (com 0,42 abria numa miniatura)
        wg = (x1 - x0) * (0.5 if (cards[0].get("opcoes") or {}).get("zoom") else 0.42)
        out = [(x0, y0, wg, y1 - y0)]
        m = n - 1
        cols = m if m <= 3 else (2 if m == 4 else 3)      # até 3 itens numa fileira só: saem maiores
        lin = math.ceil(m / cols)
        gx0 = x0 + wg + VAO
        cw = (x1 - gx0 - VAO * (cols - 1)) / cols
        ch = min(520.0 if lin == 1 else 360.0, (y1 - y0 - VAO * (lin - 1)) / lin)
        gy0 = (y0 + y1) / 2 - (ch * lin + VAO * (lin - 1)) / 2
        for k in range(m):
            out.append((gx0 + (k % cols) * (cw + VAO), gy0 + (k // cols) * (ch + VAO), cw, ch))
        return out, set(range(1, n))
    fileiras = [cards] if n <= 4 else [cards[:(n + 1) // 2], cards[(n + 1) // 2:]]
    hf = (y1 - y0 - VAO * (len(fileiras) - 1)) / len(fileiras)
    out = []
    for fi, fila in enumerate(fileiras):
        # o desenho da aproximação é grande e cheio de detalhe: depois de abrir, fica com uma coluna mais larga
        # (2,6 colunas: com 1,8, numa tela de 4 cards o desenho abria numa miniatura de ~630 px, 2026-11-11)
        pesos = [max(PESO.get((c.get("opcoes") or {}).get("tamanho"), 1.0), PESO_ZOOM if (c.get("opcoes") or {}).get("zoom") else 0)
                 for c in fila]
        util = min(x1 - x0, 1000 * len(fila)) - VAO * (len(fila) - 1)     # card sozinho não ocupa a tela toda
        if any(p == PESO_ZOOM for p in pesos):
            util = x1 - x0 - VAO * (len(fila) - 1)
        x = (x0 + x1) / 2 - (util + VAO * (len(fila) - 1)) / 2
        for p in pesos:
            w = util * p / sum(pesos)
            out.append((x, y0 + fi * (hf + VAO), w, hf))
            x += w + VAO
    return out, set()


ONDE = {"centro": (0.0, 0.0), "esquerda": (-1.0, 0.0), "direita": (1.0, 0.0), "topo": (0.0, 0.0), "base": (0.0, 0.0)}


def tela(M, e, fim, espera=0.0):
    """Um estado = uma tela: os cards em colunas (ou em lista, L1), cada um no seu tempo, tudo até `fim`. `espera`:
    na 1ª tela do tópico, o tempo de o cartão do título encolher para o cabeçalho (o 1º card entrava por cima dele).
    Composições medidas na referência (2026-11-11): lista (um desenho grande e os itens pequenos se acumulando ao
    lado), o balão de pensamento com um desenho dentro ("pensa"), a seta com número que aponta para dentro do
    desenho ("aponta") e o personagem em plano médio, maior e cortado pela borda de baixo ("plano": "meio")."""
    cards = e.get("cards") or []
    ini = e["ini"] + espera
    # a data embaixo do nome: uma de cada vez (duas no mesmo estado ficavam uma por cima da outra)
    _datas = [(ini if t is None else max(ini, t), txt) for txt, t in map(_par, e.get("textos") or [])]
    # a tela nunca fica só com o fundo: o card que entra primeiro entra junto com a tela, mesmo que a
    # palavra dele venha depois (medido em 10 tópicos: 8 reprovavam no QA por 0,6 a 2 s de tela vazia)
    primeiro = min(cards, key=lambda c: c.get("t", ini)) if cards else None

    def legivel(t, t0):
        """Texto que entraria no fim da tela é adiantado para ficar TEXTO_MIN s (nunca antes do card dele)."""
        return max(t0, min(t, fim - TEXTO_MIN))
    anterior = None
    boxes, pequenos = caixas(cards, e.get("layout"))
    # aproximação ("opcoes": {"zoom": {...}} no 1º card): a tela abre com o desenho ampliado num ponto e, na palavra do
    # gatilho, abre para o desenho inteiro em ZOOM_T s (medido na referência: ~1,5 s no detalhe e 3 quadros de
    # passagem). Até lá, mais nada entra na tela — o desenho ampliado cobriria tudo.
    zoom = (cards[0].get("opcoes") or {}).get("zoom") if cards else None       # vale também na lista: o desenho grande abre ampliado
    t_abre = None
    if isinstance(zoom, dict):
        t_abre = min(max(ini + 1.0, zoom.get("t", ini + 1.5)), fim - 1.0)
        if t_abre <= ini + 0.5:
            zoom = t_abre = None
    datas = sorted(((max(t, t_abre + ZOOM_T) if t_abre else t, txt) for t, txt in _datas), key=lambda d: d[0])
    for k, (t, txt) in enumerate(datas):
        M.texto(txt, t, datas[k + 1][0] if k + 1 < len(datas) else fim, TOPO_DATA, 50)
    for idx, (c, (bx, by, bw, bh)) in enumerate(zip(cards, boxes)):
        opc = c.get("opcoes") or {}
        mini = idx in pequenos                     # item pequeno da lista: texto menor e sem balão, seta ou plano
        tam, linha = (36, 52) if mini else (46, 68)
        t0 = ini if c is primeiro else max(ini, c.get("t", ini))
        ampliado = bool(t_abre) and idx == 0
        if t_abre and idx > 0:                     # os outros cards esperam o desenho abrir
            t0 = max(t0, t_abre + ZOOM_T)
        acima, legenda, bal = c.get("acima"), c.get("legenda"), (None if mini else opc.get("balao"))
        st = c.get("sticker")
        if isinstance(st, (list, tuple)):       # o compilador entrega [asset, t]; do elenco, {"arquivo", "t"}
            st = {"asset": st[0], "t": st[1] if len(st) > 1 else t0}
        st = st if st and (st.get("asset") or st.get("arquivo")) else None
        pensa = bool(st) and bool(opc.get("pensa")) and not mini
        det = opc.get("detalhe") if (st and not mini and not pensa and isinstance(opc.get("detalhe"), dict)) else None
        aponta = None if mini else opc.get("aponta")
        meio = opc.get("plano") == "meio" and not mini
        if meio and legenda:                       # em plano médio o pé do desenho sai da tela: a legenda sobe
            acima, legenda = (acima or legenda), None
        topo = (42 if opc.get("circulo") else 0) + (linha if acima else 0) \
            + (150 + (44 if len(str(bal.get("texto", ""))) > 22 else 0) if bal else 0) \
            + (250 if pensa else 0) + (80 if aponta else 0) + (240 if det else 0)
        pe = (42 if opc.get("circulo") else 0) + (linha if legenda else 0)
        ih = bh - topo - pe
        cx, cy = bx + bw / 2, by + topo + ih / 2
        lw = bw
        if meio:                                   # 1,4× maior, preso em cima: o que passa da tela a borda corta
            ih, lw = ih * 1.4, bw * 1.06
            cy = by + topo + ih / 2
        # o desenho (e as trocas dele, no mesmo lugar)
        versoes = [(t0, c)] + [(tr.get("t", t0), tr) for tr in c.get("troca") or []]
        larg = alt = 0
        for k, (tv, el) in enumerate(versoes):
            sai = versoes[k + 1][0] if k + 1 < len(versoes) else fim
            if sai - tv > 0.05 and (el.get("asset") or el.get("arquivo")):
                larg, alt = M.imagem(el, tv, sai, cx, cy, lw, ih)
                if meio:                           # o QA mede o que está DENTRO do quadro
                    M.registro[-1]["box"][3] = min(float(H), M.registro[-1]["box"][3])
                if ampliado and k == 0:
                    L = next(x for x in reversed(M.layers) if x.get("kind") == "footage")
                    fx, _ = ONDE.get(zoom.get("onde"), ONDE["centro"])
                    # ampliado, o desenho ENCHE a tela de lado a lado, do cabeçalho até a borda de baixo, e nenhuma
                    # borda dele aparece no meio da tela. Antes (2026-11-11) ele era centrado no ponto pedido e
                    # empurrado para baixo do nome do tópico: com o ponto num canto, um terço da tela ficava vazio
                    # e o resto do desenho saía cortado pela direita. "onde" só escolhe o lado, dentro da folga.
                    teto = AREA[1] - 50
                    rz = max(W * ZOOM_COBRE / larg, (H - teto) * 1.02 / alt)
                    wz, hz = larg * rz, alt * rz
                    perto = [min(wz / 2, max(W - wz / 2, W / 2 - fx * (wz - W) / 2)), teto + hz / 2]
                    e0 = L["scale"][0]
                    L["nitido"] = True
                    L["pos_keys"] = [[t_abre, perto, EASE_OUT], [t_abre + ZOOM_T, [cx, cy], EASE_IN]]
                    L["scale_keys"] = [[t_abre, [e0 * rz, e0 * rz], EASE_OUT], [t_abre + ZOOM_T, [e0, e0], EASE_IN]]
        if not larg:
            continue
        if ampliado:                               # o que vai em volta do desenho só aparece com ele inteiro
            t0 = max(t0, t_abre + ZOOM_T)
        # com círculo em volta do card, o nome e a legenda vão para fora dele (o traço passava por cima do texto)
        folga = 42 if opc.get("circulo") else 0
        y_topo = cy - alt / 2 - folga
        if aponta and aponta.get("texto"):
            M.aponta(str(aponta["texto"]), legivel(aponta.get("t", t0), t0), fim, cx, cy, larg, alt, y_topo,
                     ONDE.get(aponta.get("onde"), ONDE["centro"]))
            y_topo -= 80
        if acima:
            txt, t = _par(acima)
            M.texto(txt, t0 if t is None else legivel(t, t0), fim, [cx, y_topo - linha / 2 - 2], tam, max_w=bw + VAO - 10)
            y_topo -= linha
        if bal and bal.get("texto"):
            M.balao(str(bal["texto"]), legivel(bal.get("t", t0), t0), fim, cx, y_topo, bw + VAO - 10)
        if legenda:
            txt, t = _par(legenda)
            M.texto(txt, t0 if t is None else legivel(t, t0), fim, [cx, cy + alt / 2 + linha / 2 + 4 + folga], tam, max_w=bw + VAO - 10)
        if pensa:
            M.pensamento(st, legivel(st.get("t", t0), t0), fim, cx, y_topo, larg)
        elif det:
            M.detalhe(st, str(det.get("texto") or ""), legivel(max(st.get("t", t0), det.get("t", t0)), t0), fim, cx, cy, larg, alt,
                      y_topo, ONDE.get(det.get("onde"), ONDE["centro"]))
        elif st:
            lado = -1 if (bal or aponta) else 1         # com balão ou número com seta, o adesivo vai para o outro canto
            sx = min(W - 120, max(120, cx + lado * (larg / 2 - 10)))
            lado_st = 120 if mini else 210
            M.imagem(st, max(t0, st.get("t", t0)), fim, sx, max(AREA[1] + 105, cy - alt / 2 + 40), lado_st, lado_st)   # abaixo do cabeçalho e da miniatura
        if opc.get("circulo"):
            M.circulo(max(t0, opc["circulo"].get("t", t0)), fim, cx, cy, larg, alt)
        if opc.get("x"):
            M.xis(max(t0, opc["x"].get("t", t0)), fim, cx, cy, larg, alt)
        if opc.get("seta") and anterior and not mini:
            M.seta(max(t0, opc["seta"].get("t", t0)), fim, anterior, (cx, cy))
        anterior = (cx, cy)


def topicos_do_video(proj):
    """[(nn, nome, arquivo do desenho-símbolo | None)] de todos os tópicos do vídeo, na ordem. O símbolo é o asset do
    título do bloco (manifesto) ou, se o bloco ainda não foi feito, o elenco do título dele em <vídeo>/elenco/."""
    out = []
    if proj.name == "producao":
        # o vídeo inteiro num projeto só (fluxo "video"): os tópicos são os itens do plano.json e o símbolo de cada
        # um é o título dele no MESMO manifesto — a grade sai completa na 1ª montagem, sem gerar de novo no final
        try:
            man = {m["id"]: m for m in json.loads((proj / "manifesto.json").read_text())["assets"]}
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            man = {}
        for it in json.loads((proj / "plano.json").read_text()).get("itens", []):
            try:
                tt = json.loads((proj / "edicao" / f"plano_edicao_{it['id']}.json").read_text()).get("titulo")
            except (FileNotFoundError, json.JSONDecodeError):
                tt = None
            if not tt:          # cold open ou capítulo sem título: não entra na grade
                continue
            arq = proj / tt["arquivo"] if tt.get("arquivo") else \
                (proj / man[tt["asset"]]["arquivo"] if tt.get("asset") in man else None)
            out.append((it["id"], it["nome"], arq if arq and arq.exists() else None))
        return out
    for b in sorted(d for d in proj.parent.iterdir() if d.is_dir() and d.name.isdigit() and (d / "roteiro.txt").exists()):
        linhas = (b / "roteiro.txt").read_text().splitlines()
        if not linhas or not linhas[0].startswith("#") or any(ln.startswith("#! cold open") for ln in linhas[:3]):
            continue
        arq = None
        try:
            man = {m["id"]: m for m in json.loads((b / "manifesto.json").read_text())["assets"]}
            if f"{b.name}-titulo" in man:
                arq = b / man[f"{b.name}-titulo"]["arquivo"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            pass
        if not (arq and arq.exists()):
            try:
                tit = json.loads((b / "cenas.json").read_text())["itens"][0].get("titulo") or {}
                el = proj.parent.parent / "elenco" / (re.sub(r"[^a-z0-9]+", "-", str(tit.get("elenco", "")).lower()).strip("-") + ".png")
                arq = el if tit.get("elenco") and el.exists() else None
            except (FileNotFoundError, KeyError, IndexError, json.JSONDecodeError):
                arq = None
        out.append((b.name, linhas[0].lstrip("# ").strip(), arq))
    return out


def grade(M, proj, topicos, atual, fim, simbolo, nome_cartao):
    """A grade com todos os tópicos (desenho + nome): parada até fim − GRADE_ZOOM, depois a câmera aproxima no
    tópico `atual` e os outros somem. O tópico atual NÃO é desenhado aqui: o desenho e o nome dele são as mesmas
    camadas do cartão do tópico, que saem do lugar deles na grade e crescem até o cartão — sem corte (2026-11-09: com
    a grade cortando para o cartão, o desenho pulava de tamanho e de lugar).
    simbolo = (largura, altura, escala no cartão) do desenho do tópico, ou None; nome_cartao = (texto, tamanho).
    Devolve onde o tópico atual começa na grade: {"img": (pos, escala) | None, "nome": (pos, escala %), "t1": ...}."""
    n = len(topicos)
    x0, y0, x1, y1 = GRADE_AREA
    cols = max(2, min(n, math.ceil(math.sqrt(n * (x1 - x0) / (y1 - y0) * 0.85))))
    lins = math.ceil(n / cols)
    cw, ch = (x1 - x0) / cols, (y1 - y0) / lins
    tam = max(22, min(54, cw * 0.105))
    centros = []
    for k in range(n):
        li, co = divmod(k, cols)
        na_linha = cols if li < lins - 1 else n - cols * (lins - 1)       # a última linha fica centrada
        centros.append((x0 + (x1 - x0 - na_linha * cw) / 2 + (co + 0.5) * cw, y0 + (li + 0.5) * ch))
    t1 = fim - GRADE_ZOOM
    img_de = lambda c: (c[0], c[1] - ch * 0.12)
    nome_de = lambda c: (c[0], c[1] + ch * 0.33)

    # o tópico atual: de onde ele sai na grade, e o quanto a câmera aproxima para ele chegar ao tamanho do cartão
    foco = img_de(centros[atual])
    txt_c, tam_c = nome_cartao
    esc_nome = min(tam / tam_c, (cw - 10) / max(1.0, largura(txt_c, tam_c, M.fonte_titulo))) * 100
    if simbolo:
        sw, sh, s_cartao = simbolo
        esc_img = min(cw * 0.78 / sw, ch * 0.60 / sh) * 100
        aumento = s_cartao / esc_img
    else:
        esc_img, aumento = None, 100 / esc_nome

    def some(pos, esc):
        """Os outros tópicos: parados até t1; depois afastam como numa aproximação de câmera e desaparecem."""
        depois = [TITULO_IMG[0] + aumento * (pos[0] - foco[0]), TITULO_IMG[1] + aumento * (pos[1] - foco[1])]
        return dict(pos_keys=[[t1, list(pos), EASE_OUT], [fim, depois, EASE_IN]],
                    scale_keys=[[t1, [esc, esc], EASE_OUT], [fim, [esc * aumento, esc * aumento], EASE_IN]],
                    opacity_keys=[[t1, 100], [t1 + GRADE_ZOOM * 0.75, 0]])

    for k, ((nn, nome, arq), c) in enumerate(zip(topicos, centros)):
        if k == atual:
            continue
        if arq:
            dst, sw_, sh_, _ = M.preparar({"arquivo": os.path.relpath(arq, proj)})
            M.add(kind="footage", file=str(dst), src=[sw_, sh_], start=0, name=f"grade {nn}", camada="ui",
                  **some(img_de(c), min(cw * 0.78 / sw_, ch * 0.60 / sh_) * 100), **{"in": 0, "out": fim})
        M.add(kind="text", text=quebrar(nome, tam, M.fonte, cw - 16), size=tam, color=M.cor_texto, font=M.fonte,
              justify="center", tracking=0, max_w=cw - 10, anchor_mode="center", name=f"grade {nome[:30]}", camada="ui",
              **some(nome_de(c), 100), **{"in": 0, "out": fim})
    M.reg("card", "grade de tópicos", 0, fim, [x0, y0, x1, y1])
    return {"img": (foco, esc_img) if simbolo else None, "nome": (nome_de(centros[atual]), esc_nome), "t1": t1,
            "fim": fim}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--item", default="01")
    a = ap.parse_args()
    proj = Path(a.projeto).resolve()
    plano = json.loads((proj / "edicao" / f"plano_edicao_{a.item}.json").read_text())
    audio = next(p for p in sorted(proj.iterdir()) if p.stem == "narracao")
    M = Montador(proj)
    estados = [e for c in plano["cenas"] for e in c["estados"]]
    fim_bloco = plano["fim"] + FIM_BLOCO
    if proj.name == "producao":
        # no vídeo inteiro o pedaço do capítulo vai até o começo do seguinte (render_video): a última tela fica até lá
        itens = json.loads((proj / "plano.json").read_text()).get("itens", [])
        k = next((i for i, it in enumerate(itens) if it["id"] == a.item), None)
        if k is not None and k + 1 < len(itens):
            fim_bloco = max(fim_bloco, itens[k + 1]["inicio"] - itens[k]["inicio"] + 0.1)
    M.add(kind="solid", color=M.cor_fundo, name="fundo", camada="fundo", **{"in": 0, "out": fim_bloco + 2})

    # o tópico abre com o desenho-símbolo grande e o nome embaixo, enquanto a 1ª frase é dita; quando a 1ª tela
    # entra, os dois encolhem para o cabeçalho (nome no topo, miniatura no canto) e ficam até o fim
    tt = plano.get("titulo")
    nome = (tt or {}).get("texto") or plano["nome"]
    primeiro = estados[0]["ini"] if estados else fim_bloco
    vira = max(0.0, min((tt or {}).get("fim", primeiro), primeiro))
    tam_nome = 78
    topicos = topicos_do_video(proj) if tt else []
    eu = next((k for k, tp in enumerate(topicos) if tp[0] == (a.item if proj.name == "producao" else proj.name)), None)
    com_grade = eu is not None and len(topicos) >= 2
    t_grade = ((GRADE_SEGURA_1 if eu == 0 else GRADE_SEGURA) + GRADE_ZOOM) if com_grade else 0.0
    if tt:
        # a 1ª tela pode começar logo depois do nome (a 1ª frase já tem tela): a abertura segura os cards dela até
        # a grade e o cartão do tópico passarem
        vira = max(vira, t_grade + CARTAO_TOPICO)
    if tt and vira > 0.3:
        grande = 120 if largura(nome, 120, M.fonte_titulo) < 1500 else 96
        esc = tam_nome / grande * 100
        txt_nome = quebrar(nome, grande, M.fonte_titulo, 1600)
        el = {"arquivo": tt["arquivo"]} if tt.get("arquivo") else {"asset": tt["asset"]}
        try:
            arq, sw, sh, _ = M.preparar(el)
        except (KeyError, FileNotFoundError):
            arq = None
        s0 = min(TITULO_IMG[2] / sw, TITULO_IMG[3] / sh) * 100 if arq else None
        s1 = min(MINI[2] / sw, MINI[3] / sh) * 100 if arq else None

        # a grade de todos os tópicos abre o bloco; o desenho e o nome deste tópico saem do lugar deles na grade e
        # crescem até o cartão (as mesmas camadas, sem corte), ficam enquanto a 1ª frase é dita e encolhem para o
        # cabeçalho quando a 1ª tela entra
        g = None
        if com_grade:
            g = grade(M, proj, topicos, eu, t_grade, (sw, sh, s0) if arq else None, (txt_nome, grande))

        def caminho(na_grade, no_cartao, no_topo):
            """Chaves grade → cartão → cabeçalho (sem a grade, só cartão → cabeçalho)."""
            antes = [[g["t1"], na_grade, EASE_OUT], [g["fim"], no_cartao, EASE_IN]] if g else []
            return antes + [[vira, no_cartao, EASE_OUT], [vira + VIRA, no_topo, EASE_IN]]

        gp, ge = g["nome"] if g else (None, None)
        M.texto(txt_nome, 0, fim_bloco, TITULO_NOME, grande, M.fonte_titulo, max_w=1700, tipo="cabecalho",
                pos_keys=caminho(list(gp) if g else None, list(TITULO_NOME), list(TOPO_NOME)),
                scale_keys=caminho([ge, ge] if g else None, [100, 100], [esc, esc]))
        if arq:
            ip, ie = g["img"] if g and g["img"] else (None, None)
            M.add(kind="footage", file=str(arq), src=[sw, sh], start=0, name="símbolo do tópico", camada="ui",
                  pos_keys=caminho(list(ip) if ip else None, list(TITULO_IMG[:2]), list(MINI[:2])),
                  scale_keys=caminho([ie, ie] if ip else None, [s0, s0], [s1, s1]),
                  **{"in": 0, "out": fim_bloco})
            M.reg("card", "símbolo do tópico", 0, vira, [TITULO_IMG[0] - TITULO_IMG[2] / 2, TITULO_IMG[1] - TITULO_IMG[3] / 2,
                                                         TITULO_IMG[0] + TITULO_IMG[2] / 2, TITULO_IMG[1] + TITULO_IMG[3] / 2])
    else:
        M.texto(nome, 0, fim_bloco, TOPO_NOME, tam_nome, M.fonte_titulo, max_w=1400, tipo="cabecalho")

    fins = [estados[i + 1]["ini"] if i + 1 < len(estados) else fim_bloco for i in range(len(estados))]
    for k, (e, fim) in enumerate(zip(estados, fins)):
        # a 1ª tela espera o cartão do tópico encolher para o cabeçalho (vira + VIRA), mesmo que a fala dela já tenha começado
        tela(M, e, fim, max(0.0, vira + VIRA - e["ini"]) if k == 0 and tt and vira > 0.3 else 0.0)

    M.layers.sort(key=lambda L: CAMADAS[L["camada"]])
    dur = round(fim_bloco, 2)
    for L in M.layers:
        L["out"] = min(L["out"], dur)
    dados = {"nome": plano["nome"], "dur": dur, "fps": FPS, "w": W, "h": H, "audio": str(audio),
             "audio_offset": plano.get("offset_audio", 0), "cor_fundo": M.cor_fundo, "layers": M.layers}
    (proj / "edicao" / f"layout_{a.item}.json").write_text(json.dumps(M.registro, ensure_ascii=False, indent=0))
    saida = proj / "edicao" / f"plano_render_{a.item}.json"
    saida.write_text(json.dumps(dados, ensure_ascii=False))
    print(saida, len(M.layers), "layers")


if __name__ == "__main__":
    main()
