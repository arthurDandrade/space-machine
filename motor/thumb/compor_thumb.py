"""Desenha a thumbnail de um vídeo a partir de um MODELO do formato (formatos/<formato>/thumbs/modelos.json).

Uso:
  python compor_thumb.py <pedido.json>

O pedido (quem escreve é o space_machine/thumb.py):
  {"modelo": {...},            o modelo escolhido, como está no modelos.json (layout, colunas, linhas, forma...)
   "estilo": {...},            fundo, fontes e cores do formato
   "titulo": "TEXTO *EM DESTAQUE*",          só nos modelos que têm título (o que vai entre * sai na cor de destaque)
   "itens": [{"imagem": "/caminho.png" | null, "legenda": "TEXTO", "tipo": "foto" | "logo" | "recorte",
              "titulo": "TEXTO *DESTAQUE*"}],
   "saida": "/caminho/thumbnail.png"}

Item sem imagem vira um quadro cinza com o tipo escrito: é assim que sai a prévia do modelo que o painel mostra.

Composições (medidas em 25 thumbs de um canal de referência, 2026-11-11, todas sobre branco):
  grade   N colunas × M linhas, cada item com a legenda embaixo. forma "moldura" (foto cortada no quadro, com borda
          preta), "circulo" (foto ou desenho dentro de um círculo; o desenho recortado ganha céu e grama atrás) ou
          "livre" (logo ou desenho inteiro, sem quadro).
  dupla   dois desenhos grandes lado a lado, cortados pela borda de baixo, cada um com o título em cima.
  faixa   o título numa faixa em cima e uma foto ocupando o resto.

Sai em 1280×720 (desenhado no dobro e reduzido, para o texto sair liso). PNG; se passar de 2 MB (o limite do YouTube),
JPG no mesmo nome com a extensão trocada. Imprime o caminho do arquivo gravado.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "edicao_ff"))
from compor import fonte  # noqa: E402  (a mesma busca de fontes do compositor do vídeo)

W, H, S = 1280, 720, 2          # tamanho da thumbnail e quantas vezes maior ela é desenhada
LIMITE = 2 * 1024 * 1024        # o YouTube recusa thumbnail com mais de 2 MB
ROTULO = {"foto": "FOTO", "historica": "FOTO", "logo": "LOGO", "recorte": "DESENHO"}
ESTILO = {"fundo": "#FFFFFF", "cor_texto": "#111111", "cor_destaque": "#E3120B", "cor_borda": "#111111",
          "fonte_legenda": "ChalkboardSE-Bold", "fonte_titulo": "Impact", "ceu": "#3FA9F5", "grama": "#5DB645"}


def _cor(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rosto(im):
    """O maior rosto da foto, em fração da imagem: (x do centro, y do centro, altura), ou None. Serve para o corte
    não decapitar ninguém."""
    try:
        import cv2
        import numpy as np
        g = np.asarray(im.convert("L"))
        esc = 480 / max(g.shape)
        if esc < 1:
            g = cv2.resize(g, (int(g.shape[1] * esc), int(g.shape[0] * esc)), interpolation=cv2.INTER_AREA)
        g = cv2.equalizeHist(g)
        caras = []
        for modelo in ("haarcascade_frontalface_alt2.xml", "haarcascade_frontalface_default.xml"):
            det = cv2.CascadeClassifier(cv2.data.haarcascades + modelo)
            caras = det.detectMultiScale(g, 1.1, 5, minSize=(max(20, min(g.shape) // 16),) * 2)
            if len(caras):
                break
        if len(caras):
            x, y, w, h = max(caras, key=lambda c: c[2] * c[3])
            return (x + w / 2) / g.shape[1], (y + h / 2) / g.shape[0], h / g.shape[0]
    except Exception:  # noqa: BLE001 — sem OpenCV ou imagem estranha: corta pelo meio
        pass
    return None


def cobrir(im, w, h):
    """A imagem cortada para encher w×h: centrada no rosto, se houver; sem rosto achado, pelo meio na largura e
    perto do topo na altura (num retrato de corpo inteiro a cabeça está em cima: cortar pelo meio decapitava)."""
    im = im.convert("RGBA")
    rosto = _rosto(im)
    esc = max(w / im.width, h / im.height)
    nw, nh = max(w, round(im.width * esc)), max(h, round(im.height * esc))
    im = im.resize((nw, nh), Image.LANCZOS)
    if rosto:
        x, y = round(rosto[0] * nw - w / 2), round(rosto[1] * nh - h * 0.42)
        # retrato fechado (o rosto é quase do tamanho do quadro): sobe o corte para caber o cabelo, que o detector
        # não conta (ele marca das sobrancelhas ao queixo)
        y = min(y, round((rosto[1] - rosto[2] * 0.85) * nh - h * 0.04))
    else:
        x, y = (nw - w) // 2, round((nh - h) * 0.12)
    x, y = min(max(0, x), nw - w), min(max(0, y), nh - h)
    return im.crop((x, y, x + w, y + h))


def caber(im, w, h):
    """A imagem inteira dentro de w×h (sem as bordas transparentes dela)."""
    im = im.convert("RGBA")
    caixa = im.getchannel("A").getbbox()
    if caixa:
        im = im.crop(caixa)
    esc = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * esc)), max(1, round(im.height * esc))), Image.LANCZOS)


def _transparente(im):
    """A imagem é um recorte (tem fundo transparente de verdade)?"""
    if im.mode != "RGBA":
        return False
    a = im.getchannel("A").resize((64, 64))
    return sum(1 for v in a.getdata() if v < 30) > 64 * 64 * 0.08


class Tela:
    def __init__(self, estilo):
        self.e = {**ESTILO, **(estilo or {})}
        self.im = Image.new("RGB", (W * S, H * S), _cor(self.e["fundo"]))
        self.d = ImageDraw.Draw(self.im)

    # ---------- texto ----------
    def _pedacos(self, txt):
        """"MOST *POLITICAL* CLUBS" → [("MOST ", cor do texto), ("POLITICAL", destaque), (" CLUBS", cor do texto)]."""
        out = []
        for k, parte in enumerate(txt.split("*")):
            if parte:
                out.append((parte, _cor(self.e["cor_destaque"] if k % 2 else self.e["cor_texto"])))
        return out

    def _largura(self, txt, f):
        return f.getlength(txt.replace("*", ""))

    def texto(self, txt, cx, y, tam, nome_fonte, max_w, linhas=1):
        """Texto centrado em cx, com o topo em y, encolhendo até caber em max_w (em até `linhas` linhas).
        Devolve a altura usada."""
        txt = " ".join(str(txt or "").upper().split())
        if not txt:
            return 0
        tam = tam * S
        while True:
            f = fonte(nome_fonte, tam)
            partes = [txt]
            if linhas > 1 and self._largura(txt, f) > max_w * S and " " in txt:
                pal = txt.split(" ")
                k = min(range(1, len(pal)), key=lambda i: max(self._largura(" ".join(pal[:i]), f),
                                                              self._largura(" ".join(pal[i:]), f)))
                partes = [" ".join(pal[:k]), " ".join(pal[k:])]
                # o destaque que atravessa a quebra continua valendo na 2ª linha
                if partes[0].count("*") % 2:
                    partes = [partes[0] + "*", "*" + partes[1]]
            if max(self._largura(p, f) for p in partes) <= max_w * S or tam <= 14 * S:
                break
            tam *= 0.94
        asc, desc = f.getmetrics()
        alt = asc + desc
        for k, p in enumerate(partes):
            x = cx * S - self._largura(p, f) / 2
            for pedaco, cor in self._pedacos(p):
                self.d.text((x, y * S + k * alt * 0.95), pedaco, font=f, fill=cor)
                x += f.getlength(pedaco)
        return (alt * (1 + 0.95 * (len(partes) - 1))) / S

    # ---------- itens ----------
    def _abrir(self, item):
        arq = item.get("imagem")
        if arq and Path(arq).exists():
            return Image.open(arq)
        return None

    def _vazio(self, x, y, w, h, item, circulo=False):
        caixa = [x * S, y * S, (x + w) * S, (y + h) * S]
        (self.d.ellipse if circulo else self.d.rectangle)(caixa, fill=(226, 228, 232))
        f = fonte(self.e["fonte_legenda"], min(w, h) * 0.16 * S)
        r = ROTULO.get(item.get("tipo"), "IMAGEM")
        self.d.text(((x + w / 2) * S - f.getlength(r) / 2, (y + h / 2) * S - f.size / 2), r, font=f, fill=(150, 154, 162))

    def moldura(self, item, x, y, w, h, borda=3):
        im = self._abrir(item)
        if im is None:
            self._vazio(x, y, w, h, item)
        else:
            self.im.paste(cobrir(im, round(w * S), round(h * S)).convert("RGB"), (round(x * S), round(y * S)))
        self.d.rectangle([x * S, y * S, (x + w) * S, (y + h) * S], outline=_cor(self.e["cor_borda"]), width=borda * S)

    def circulo(self, item, cx, cy, d, borda=4):
        im = self._abrir(item)
        x, y = cx - d / 2, cy - d / 2
        lado = round(d * S)
        if im is None:
            self._vazio(x, y, d, d, item, circulo=True)
        else:
            if _transparente(im.convert("RGBA")):
                # desenho recortado: céu e grama atrás, o desenho apoiado embaixo e cortado pelo círculo
                fundo = Image.new("RGBA", (lado, lado), _cor(self.e["ceu"]) + (255,))
                ImageDraw.Draw(fundo).rectangle([0, round(lado * 0.66), lado, lado], fill=_cor(self.e["grama"]) + (255,))
                des = caber(im, round(lado * 0.92), round(lado * 0.9))
                fundo.alpha_composite(des, ((lado - des.width) // 2, lado - des.height - round(lado * 0.02)))
            else:
                fundo = cobrir(im, lado, lado)
            masc = Image.new("L", (lado, lado), 0)
            ImageDraw.Draw(masc).ellipse([0, 0, lado - 1, lado - 1], fill=255)
            self.im.paste(fundo.convert("RGB"), (round(x * S), round(y * S)), masc)
        self.d.ellipse([x * S, y * S, (x + d) * S, (y + d) * S], outline=_cor(self.e["cor_borda"]), width=borda * S)

    def livre(self, item, x, y, w, h, embaixo=False):
        im = self._abrir(item)
        if im is None:
            self._vazio(x + w * 0.08, y + h * 0.08, w * 0.84, h * 0.84, item)
            return
        des = caber(im, round(w * S), round(h * S))
        px = round((x + w / 2) * S - des.width / 2)
        py = round((y + h) * S - des.height) if embaixo else round((y + h / 2) * S - des.height / 2)
        self.im.paste(des.convert("RGB"), (px, py), des.getchannel("A"))

    # ---------- composições ----------
    def grade(self, m, itens):
        cols, lin = int(m.get("colunas", 4)), int(m.get("linhas", 2))
        forma = m.get("forma", "moldura")
        mg = 12
        cw, ch = (W - mg * (cols + 1)) / cols, (H - mg * (lin + 1)) / lin
        tam = float(m.get("legenda_px") or (34 if cols <= 3 else 30))
        leg = tam * 1.5
        for k, it in enumerate(itens[:cols * lin]):
            x, y = mg + (k % cols) * (cw + mg), mg + (k // cols) * (ch + mg)
            ih = ch - leg
            if forma == "circulo":
                d = min(cw, ih)
                self.circulo(it, x + cw / 2, y + ih / 2, d)
            elif forma == "livre":
                self.livre(it, x + cw * 0.06, y + ih * 0.04, cw * 0.88, ih * 0.92)
            else:
                self.moldura(it, x, y, cw, ih)
            self.texto(it.get("legenda"), x + cw / 2, y + ih + leg * 0.08, tam, self.e["fonte_legenda"], cw - 6)

    def dupla(self, m, itens):
        tam = float(m.get("titulo_px") or 84)
        meio = W / 2
        for k, it in enumerate(itens[:2]):
            cx = meio / 2 + k * meio
            usado = self.texto(it.get("titulo") or it.get("legenda"), cx, 14, tam, self.e["fonte_titulo"], meio - 50, linhas=2)
            topo = 14 + usado + 10
            # o desenho passa um pouco da borda de baixo: é ela que corta
            self.livre(it, cx - meio * 0.5 + 8, topo, meio - 16, (H - topo) * 1.06, embaixo=False)

    def faixa(self, m, itens, titulo):
        alt = float(m.get("faixa_px") or 104)
        it = itens[0] if itens else {}
        im = self._abrir(it)
        if im is None:
            self._vazio(0, alt, W, H - alt, it)
        else:
            self.im.paste(cobrir(im, W * S, round((H - alt) * S)).convert("RGB"), (0, round(alt * S)))
        f_tam = alt * 0.78
        f = fonte(self.e["fonte_titulo"], f_tam * S)
        asc, desc = f.getmetrics()
        self.texto(titulo, W / 2, (alt - (asc + desc) / S) / 2, f_tam, self.e["fonte_titulo"], W - 40)

    def gravar(self, saida):
        saida = Path(saida)
        saida.parent.mkdir(parents=True, exist_ok=True)
        final = self.im.resize((W, H), Image.LANCZOS)
        final.save(saida.with_suffix(".png"), optimize=True)
        if saida.with_suffix(".png").stat().st_size > LIMITE:
            saida.with_suffix(".png").unlink()
            for q in (93, 88, 82, 75):
                final.save(saida.with_suffix(".jpg"), quality=q, optimize=True, subsampling=0 if q > 85 else 2)
                if saida.with_suffix(".jpg").stat().st_size <= LIMITE:
                    break
            return saida.with_suffix(".jpg")
        saida.with_suffix(".jpg").unlink(missing_ok=True)
        return saida.with_suffix(".png")


def compor(pedido):
    m = pedido.get("modelo") or {}
    t = Tela(pedido.get("estilo"))
    itens = pedido.get("itens") or []
    layout = m.get("layout", "grade")
    if layout == "dupla":
        t.dupla(m, itens)
    elif layout == "faixa":
        t.faixa(m, itens, pedido.get("titulo") or "")
    else:
        t.grade(m, itens)
    return t.gravar(pedido["saida"])


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(compor(json.loads(Path(sys.argv[1]).read_text())))


if __name__ == "__main__":
    main()
