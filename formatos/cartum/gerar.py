"""Montador do cartum: lê edicao/plano_edicao_<item>.json e escreve edicao/plano_render_<item>.json, que o compositor
sem After (motor/edicao_ff/compor.py) desenha. Não há modelo do After neste formato.

Uso: python gerar.py <projeto> [--item 01]

O visual vem da medição dos 4 vídeos de referência (conhecimento/01 - Formato/Vídeos de Referência.md): fundo liso
azul-claro, o nome do tópico no topo com a miniatura dele no canto, e os desenhos recortados entrando um a um na
palavra dita, EM CORTE SECO (nada de fusão, deslize ou zoom: medido quadro a quadro), até a tela limpar no estado
seguinte. Um estado do cenas.json = uma tela; os cards vão em colunas, na ordem em que foram escritos.
O que cada card pode levar: acima, legenda, sticker, troca e opcoes {balao, x, seta, circulo, tamanho}; no estado,
textos = a data embaixo do nome do tópico. Está tudo em storyboard.md.
"""
import argparse
import json
import math
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

    def xis(self, t_in, t_out, cx, cy, larg, alt):
        m = min(larg, alt) * 0.42
        self.forma([{"t": "path", "pts": [[-m, -m], [m, m]], "stroke": self.destaque, "sw": 22},
                    {"t": "path", "pts": [[m, -m], [-m, m]], "stroke": self.destaque, "sw": 22}], t_in, t_out, [cx, cy], "x")

    def circulo(self, t_in, t_out, cx, cy, larg, alt):
        self.forma([{"t": "ellipse", "size": [larg + 70, alt + 70], "stroke": self.destaque, "sw": 10, "trim": False}],
                   t_in, t_out, [cx, cy], "círculo")


def caixas(cards):
    """A caixa de cada card na AREA: uma fileira até 4, duas com 5 ou 6; a largura segue o "tamanho" do card."""
    n = len(cards)
    fileiras = [cards] if n <= 4 else [cards[:(n + 1) // 2], cards[(n + 1) // 2:]]
    x0, y0, x1, y1 = AREA
    hf = (y1 - y0 - VAO * (len(fileiras) - 1)) / len(fileiras)
    out = []
    for fi, fila in enumerate(fileiras):
        pesos = [PESO.get((c.get("opcoes") or {}).get("tamanho"), 1.0) for c in fila]
        util = min(x1 - x0, 1000 * len(fila)) - VAO * (len(fila) - 1)     # card sozinho não ocupa a tela toda
        x = (x0 + x1) / 2 - (util + VAO * (len(fila) - 1)) / 2
        for p in pesos:
            w = util * p / sum(pesos)
            out.append((x, y0 + fi * (hf + VAO), w, hf))
            x += w + VAO
    return out


def tela(M, e, fim):
    """Um estado = uma tela: os cards em colunas, cada um no seu tempo, tudo até `fim`."""
    cards = e.get("cards") or []
    ini = e["ini"]
    for v in e.get("textos") or []:
        txt, t = _par(v)
        M.texto(txt, ini if t is None else t, fim, TOPO_DATA, 50)
    anterior = None
    for c, (bx, by, bw, bh) in zip(cards, caixas(cards)):
        opc = c.get("opcoes") or {}
        t0 = c.get("t", ini)
        acima, legenda, bal = c.get("acima"), c.get("legenda"), opc.get("balao")
        topo = (42 if opc.get("circulo") else 0) + (68 if acima else 0) + (150 + (44 if bal and len(str(bal.get("texto", ""))) > 22 else 0) if bal else 0)
        pe = (42 if opc.get("circulo") else 0) + (68 if legenda else 0)
        cx, cy = bx + bw / 2, by + topo + (bh - topo - pe) / 2
        ih = bh - topo - pe
        # o desenho (e as trocas dele, no mesmo lugar)
        versoes = [(t0, c)] + [(tr.get("t", t0), tr) for tr in c.get("troca") or []]
        larg = alt = 0
        for k, (tv, el) in enumerate(versoes):
            sai = versoes[k + 1][0] if k + 1 < len(versoes) else fim
            if sai - tv > 0.05 and (el.get("asset") or el.get("arquivo")):
                larg, alt = M.imagem(el, tv, sai, cx, cy, bw, ih)
        if not larg:
            continue
        # com círculo em volta do card, o nome e a legenda vão para fora dele (o traço passava por cima do texto)
        folga = 42 if opc.get("circulo") else 0
        y_topo = cy - alt / 2 - folga
        if acima:
            txt, t = _par(acima)
            M.texto(txt, t0 if t is None else max(t0, t), fim, [cx, y_topo - 36], 46, max_w=bw + VAO - 10)
            y_topo -= 68
        if bal and bal.get("texto"):
            M.balao(str(bal["texto"]), max(t0, bal.get("t", t0)), fim, cx, y_topo, bw + VAO - 10)
        if legenda:
            txt, t = _par(legenda)
            M.texto(txt, t0 if t is None else max(t0, t), fim, [cx, cy + alt / 2 + 38 + folga], 46, max_w=bw + VAO - 10)
        st = c.get("sticker")
        if isinstance(st, (list, tuple)):       # o compilador entrega [asset, t]; do elenco, {"arquivo", "t"}
            st = {"asset": st[0], "t": st[1] if len(st) > 1 else t0}
        if st and (st.get("asset") or st.get("arquivo")):
            lado = -1 if bal else 1         # com balão, o adesivo vai para o outro canto
            sx = min(W - 120, max(120, cx + lado * (larg / 2 - 10)))
            M.imagem(st, max(t0, st.get("t", t0)), fim, sx, max(AREA[1] + 105, cy - alt / 2 + 40), 210, 210)   # abaixo do cabeçalho e da miniatura
        if opc.get("circulo"):
            M.circulo(max(t0, opc["circulo"].get("t", t0)), fim, cx, cy, larg, alt)
        if opc.get("x"):
            M.xis(max(t0, opc["x"].get("t", t0)), fim, cx, cy, larg, alt)
        if opc.get("seta") and anterior:
            M.seta(max(t0, opc["seta"].get("t", t0)), fim, anterior, (cx, cy))
        anterior = (cx, cy)


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
    M.add(kind="solid", color=M.cor_fundo, name="fundo", camada="fundo", **{"in": 0, "out": fim_bloco + 2})

    # o tópico abre com o desenho-símbolo grande e o nome embaixo, enquanto a 1ª frase é dita; quando a 1ª tela
    # entra, os dois encolhem para o cabeçalho (nome no topo, miniatura no canto) e ficam até o fim
    tt = plano.get("titulo")
    nome = (tt or {}).get("texto") or plano["nome"]
    primeiro = estados[0]["ini"] if estados else fim_bloco
    vira = max(0.0, min((tt or {}).get("fim", primeiro), primeiro))
    tam_nome = 78
    if tt and vira > 0.3:
        grande = 120 if largura(nome, 120, M.fonte_titulo) < 1500 else 96
        esc = tam_nome / grande * 100
        M.texto(quebrar(nome, grande, M.fonte_titulo, 1600), 0, fim_bloco, TITULO_NOME, grande, M.fonte_titulo,
                max_w=1700, tipo="cabecalho",
                pos_keys=[[vira, list(TITULO_NOME), EASE_OUT], [vira + VIRA, list(TOPO_NOME), EASE_IN]],
                scale_keys=[[vira, [100, 100], EASE_OUT], [vira + VIRA, [esc, esc], EASE_IN]])
        el = {"arquivo": tt["arquivo"]} if tt.get("arquivo") else {"asset": tt["asset"]}
        try:
            arq, sw, sh, _ = M.preparar(el)
        except (KeyError, FileNotFoundError):
            arq = None
        if arq:
            s0 = min(TITULO_IMG[2] / sw, TITULO_IMG[3] / sh) * 100
            s1 = min(MINI[2] / sw, MINI[3] / sh) * 100
            M.add(kind="footage", file=str(arq), src=[sw, sh], start=0, name="símbolo do tópico", camada="ui",
                  pos_keys=[[vira, list(TITULO_IMG[:2]), EASE_OUT], [vira + VIRA, list(MINI[:2]), EASE_IN]],
                  scale_keys=[[vira, [s0, s0], EASE_OUT], [vira + VIRA, [s1, s1], EASE_IN]],
                  **{"in": 0, "out": fim_bloco})
            M.reg("card", "símbolo do tópico", 0, vira, [TITULO_IMG[0] - TITULO_IMG[2] / 2, TITULO_IMG[1] - TITULO_IMG[3] / 2,
                                                         TITULO_IMG[0] + TITULO_IMG[2] / 2, TITULO_IMG[1] + TITULO_IMG[3] / 2])
    else:
        M.texto(nome, 0, fim_bloco, TOPO_NOME, tam_nome, M.fonte_titulo, max_w=1400, tipo="cabecalho")

    fins = [estados[i + 1]["ini"] if i + 1 < len(estados) else fim_bloco for i in range(len(estados))]
    for e, fim in zip(estados, fins):
        tela(M, e, fim)

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
