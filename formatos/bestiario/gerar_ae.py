"""Editor do bestiário (animação 2D): monta um bloco a partir de edicao/plano_edicao_<item>.json e gera
edicao/montar_<item>_v2.jsx (o mesmo nome do explained: o editar_bloco.sh, o final.py e o rodar.py procuram esse) com o
montar_modelo.jsx do formato.

Uso: python gerar_ae.py <projeto> [--item 01]

O visual vem da medição dos 5 vídeos do Depth Theory (conhecimento/04 - Edição/Visual do Bestiário.md): fundo desenhado
aqui (mar com raios de luz e partículas, noite com estrelas, grade técnica) ou um cenário gerado, a criatura recortada
nadando e oscilando por cima, e gráficos de explicação (rótulo, carimbo, régua, ícones, número com barra, lista de
opções, documento, linha do tempo). Tudo entra animado; nada fica parado.
Tipos de cena (biblioteca_cenas.json): C1 criatura, E1 escala, N1 ícones, N2 número, L1 opções, D1 documento,
T1 linha do tempo, R1 real, F1 frase, S1 lado a lado.
"""
import argparse
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "motor"))
import caminhos  # noqa: E402

W, H = 1920, 1080
CX, CY = W / 2, H / 2
FPS = 30
FIM_BLOCO = 0.6
# entrada e saída (medido a 10 fps no Depth Theory, 2026-11-04: texto e rótulo aparecem numa fusão de ~0,15–0,2 s no
# lugar, sem deslizar; o nosso subia 18 px em 0,35 s e parecia modelo pronto). Saída de 0,2 s: com 0,3 s o texto que
# saía ficava por cima da criatura que entrava
ENTRA, SAI = 0.2, 0.2
CHEGADA = 0.5                 # a criatura chega num zoom rápido com borrão de movimento (1:17 do cachalote)
TROCA_CAMERA = 0.65           # a câmera troca de enquadramento rápido, não em 1,1 s
FUSAO = 0.45                  # troca de fundo
EASE_OUT = [0, 0.1, 0, 80]    # chave que sai suave
EASE_IN = [0, 80, 0, 0.1]     # chave que chega suave
SAI_RAPIDO = [0, 0.1, 0, 12]  # zoom e câmera: sai rápido...
ASSENTA = [0, 92, 0, 0.1]     # ...e assenta devagar (o "whip" do Depth Theory)


def _rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


BRANCO = _rgb("#F2F4F5")
CINZA = _rgb("#8FA3AD")
VERMELHO = _rgb("#E5484D")
PAPEL = _rgb("#EFE7D6")
TINTA = _rgb("#23262B")
PILULA = _rgb("#0A1820")
# Medido nos quadros do Depth Theory (2026-11-03): o mar deles é quase preto (#0B1D24 no alto, #03080A embaixo), os
# raios de luz quase não aparecem, há partículas desfocadas grandes e vinheta. "luz" = o preto e o claro para onde a
# criatura é tingida, para ela parecer DENTRO da água e não um adesivo por cima.
FUNDOS = {
    "mar": {"de": _rgb("#0E2E3A"), "ate": _rgb("#03090C"), "raios": True, "particulas": True, "bokeh": True,
            "luz": [_rgb("#020709"), _rgb("#B7D3DA")]},
    "noite": {"de": _rgb("#101A33"), "ate": _rgb("#04070F"), "estrelas": True, "bokeh": True,
              "luz": [_rgb("#03050C"), _rgb("#C3CCE0")]},
    "grade": {"de": _rgb("#0C202C"), "ate": _rgb("#071319"), "grade": True,
              "luz": [_rgb("#03090D"), _rgb("#C9D8DE")]},
    "escuro": {"de": _rgb("#10161B"), "ate": _rgb("#040607"), "particulas": True, "bokeh": True,
               "luz": [_rgb("#030405"), _rgb("#CCD3D8")]},
}
TINGE = 34                    # % de tingimento da criatura pela luz do fundo
CAMADAS = {"fundo": 0, "conteudo": 1, "vinheta": 2, "ui": 3}
FONTE = "AvenirNext-Bold"
FONTE_ROTULO = "AvenirNext-DemiBold"
FONTE_SERIFA = "Baskerville-SemiBold"


def quebrar(txt, limite):
    """Em 2 linhas, no espaço mais perto do meio, quando passa do limite de caracteres."""
    if len(txt) <= limite or " " not in txt:
        return txt
    meio = len(txt) / 2
    k = min((i for i, ch in enumerate(txt) if ch == " "), key=lambda i: abs(i - meio))
    return txt[:k] + "\r" + txt[k + 1:]


def largura(txt, tam, tracking=0):
    """Largura estimada de uma linha (Avenir Next em maiúsculas): para caixas, sublinhados e riscos."""
    return len(txt) * tam * (0.66 + tracking / 1000)


class Montador:
    def __init__(self, proj):
        self.proj = proj
        self.cache = proj / "edicao" / "_cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.layers = []
        self.registro = []          # o que está na tela e quando (edicao/layout_<item>.json, para o QA)
        man = json.loads((proj / "manifesto.json").read_text())["assets"]
        self.manif = {m["id"]: m for m in man}
        self.rnd = random.Random(7)
        self.luz = FUNDOS["mar"]["luz"]   # a luz do fundo atual (tinge a criatura)

    # ---------- base ----------
    def add(self, **kw):
        kw["id"] = len(self.layers)
        kw.setdefault("parent", None)
        kw.setdefault("camada", "conteudo")     # fundo < conteúdo < vinheta < textos e gráficos (ordem no After)
        self.layers.append(kw)
        return kw["id"]

    def reg(self, tipo, nome, t_in, t_out, box=None):
        self.registro.append({"tipo": tipo, "txt": nome, "id": nome, "in": round(t_in, 2), "out": round(t_out, 2),
                              "box": box or [0, 0, 0, 0]})

    def aparece(self, kw, t_in, t_out, dy=0, pos=None):
        """Entra subindo e aparecendo em ENTRA s; some em SAI s depois de t_out."""
        pos = pos or kw.get("pos")
        kw["opacity_keys"] = [[t_in, 0], [t_in + ENTRA, 100], [t_out, 100], [t_out + SAI, 0]]
        if dy and pos:
            kw["pos_keys"] = [[t_in, [pos[0], pos[1] + dy], EASE_OUT], [t_in + ENTRA * 1.4, list(pos), EASE_IN]]
        kw["in"], kw["out"] = t_in, t_out + SAI
        return kw

    def texto(self, txt, t_in, t_out, pos, tam, cor=None, fonte=FONTE, justify="center", tracking=0, max_w=1700,
              ancora="center", dy=0, nome=None):
        kw = dict(kind="text", text=txt, pos=list(pos), size=tam, color=cor or BRANCO, font=fonte, justify=justify,
                  tracking=tracking, max_w=max_w, anchor_mode=ancora, name=nome or txt[:50], camada="ui")
        self.aparece(kw, t_in, t_out, dy, pos)
        w_ = min(max_w, largura(txt, tam, tracking))
        x0 = pos[0] - (0 if justify == "left" else (w_ if justify == "right" else w_ / 2))
        self.reg("texto", txt, t_in, t_out, [x0, pos[1] - tam / 2, x0 + w_, pos[1] + tam / 2])
        return self.add(**kw)

    def forma(self, itens, t_in, t_out, pos, nome, trim=None, dy=0, **extra):
        kw = dict(kind="shape", items=itens, pos=list(pos), name=nome, **{"camada": "ui", **extra})
        self.aparece(kw, t_in, t_out, dy, pos)
        if trim:
            kw["trim_keys"] = trim
        return self.add(**kw)

    def rotulo(self, txt, t_in, t_out, pos, cor=None, tam=34, pilula=True):
        """Rótulo pequeno em maiúsculas espaçadas, numa pílula escura (como "ORCAS: LEAVE DIVERS ALONE")."""
        txt = txt.upper()
        if pilula:
            w_ = largura(txt, tam, 120) + 44
            self.forma([{"t": "rect", "size": [w_, tam * 1.9], "radius": 8, "fill": PILULA, "fill_op": 72}],
                       t_in, t_out, list(pos), f"pílula {txt[:20]}")
        return self.texto(txt, t_in, t_out, pos, tam, cor or BRANCO, FONTE_ROTULO, "center", 120, 1500)

    def marcador(self, txt, t_in, t_out, icone="check", n=0):
        """Rótulo no canto de baixo à esquerda com ✓ verde ou ✗ vermelho ("SHARKS: RARE ✓"); n empilha para cima."""
        txt = txt.upper()
        tam = 30
        w_ = largura(txt, tam, 120) + 44 + 52
        x0, y = 120, H - 120 - n * 70
        self.forma([{"t": "rect", "size": [w_, tam * 1.9], "radius": 8, "fill": PILULA, "fill_op": 78}],
                   t_in, t_out, [x0 + w_ / 2, y], f"marcador {txt[:20]}")
        self.texto(txt, t_in, t_out, [x0 + 22, y], tam, BRANCO, FONTE_ROTULO, "left", 120, 1400)
        xi = x0 + w_ - 40
        if icone == "x":
            itens = [{"t": "path", "pts": [[-10, -10], [10, 10]], "stroke": VERMELHO, "sw": 5},
                     {"t": "path", "pts": [[10, -10], [-10, 10]], "stroke": VERMELHO, "sw": 5}]
        else:
            itens = [{"t": "ellipse", "size": [30, 30], "fill": _rgb("#3FB37F"), "trim": False},
                     {"t": "path", "pts": [[-7, 0], [-2, 6], [8, -6]], "stroke": BRANCO, "sw": 4}]
        self.forma(itens, t_in + 0.25, t_out, [xi, y], f"ícone {icone}",
                   trim=[[t_in + 0.25, 0, EASE_OUT], [t_in + 0.6, 100, EASE_IN]])

    def destaque(self, txt, t_in, t_out, pos, tam=62):
        """Frase-chave em vermelho com sublinhado que se desenha ("IT KNOWS WHERE YOU ARE")."""
        txt = txt.upper()
        self.texto(txt, t_in, t_out, pos, tam, VERMELHO, FONTE, "center", 60, 1500)
        w_ = min(1500, largura(txt, tam, 60))
        self.forma([{"t": "path", "pts": [[-w_ / 2, 0], [w_ / 2, 0]], "stroke": VERMELHO, "sw": 6}],
                   t_in, t_out, [pos[0], pos[1] + tam * 0.75], f"sublinhado {txt[:20]}",
                   trim=[[t_in + 0.1, 0, EASE_OUT], [t_in + 0.7, 100, EASE_IN]])

    def carimbo(self, txt, t, t_out, pos):
        """Carimbo vermelho torto ("PREDATOR", "FRAGILE"): entra batendo."""
        txt = txt.upper()
        tam = 52
        w_, h_ = largura(txt, tam, 40) + 50, tam * 1.6
        k = self.add(kind="null", name=f"carimbo {txt[:20]}", pos=list(pos), rot=-6, camada="ui",
                     scale_keys=[[t, 135, EASE_OUT], [t + 0.16, 100, EASE_IN]], **{"in": t, "out": t_out + SAI})
        op = [[t, 0], [t + 0.08, 100], [t_out, 100], [t_out + SAI, 0]]
        self.add(kind="shape", items=[{"t": "rect", "size": [w_, h_], "radius": 6, "stroke": VERMELHO, "sw": 5}],
                 pos=[0, 0], name="carimbo moldura", parent=k, opacity_keys=op, camada="ui", **{"in": t, "out": t_out + SAI})
        self.add(kind="text", text=txt, pos=[0, 0], size=tam, color=VERMELHO, font=FONTE, justify="center", tracking=40,
                 max_w=1200, anchor_mode="center", name=f"carimbo {txt[:20]}", parent=k, opacity_keys=op, camada="ui",
                 **{"in": t, "out": t_out + SAI})
        self.reg("texto", txt, t, t_out, [pos[0] - w_ / 2, pos[1] - h_ / 2, pos[0] + w_ / 2, pos[1] + h_ / 2])

    # ---------- imagens ----------
    def arquivo(self, el):
        return self.proj / (el["arquivo"] if el.get("arquivo") else self.manif[el["asset"]]["arquivo"])

    def preparar(self, el):
        """(arquivo, w, h, duração|None). PNG com alfa é cortado no contorno; imagem grande, reduzida."""
        src = self.arquivo(el)
        if src.suffix.lower() in (".mp4", ".mov"):
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height:format=duration", "-of", "json", str(src)],
                               capture_output=True, text=True)
            j = json.loads(r.stdout)
            return src, j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])
        # a data do arquivo entra no nome: asset trocado (outra escolha, elenco novo) não usa o preparado antigo
        dst = self.cache / f"{src.parent.name}_{src.stem}_{int(src.stat().st_mtime)}.png"
        if not dst.exists():
            im = ImageOps.exif_transpose(Image.open(src))
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
                if bb:
                    im = im.crop(bb)
            esc = min(1.0, 2400 / max(im.size))
            if esc < 1:
                im = im.resize((round(im.width * esc), round(im.height * esc)), Image.LANCZOS)
            im.save(dst)
        w, h = Image.open(dst).size
        return dst, w, h, None

    def imagem(self, el, t_in, t_out, cx, cy, bw, bh, modo="conter", nome=None, mov=None, espelhar=False,
               fade=True, opacidade=100, entra_dy=0, silhueta=False):
        """Imagem/vídeo na caixa (cx, cy, bw, bh). mov = movimento da criatura ("nada", "entra", "sobe", "close",
        "parado"; a criatura oscila em todos); sem mov, a imagem só aproxima devagar. Devolve (largura, altura)."""
        arq, sw, sh, dur = self.preparar(el)
        s = (max(bw / sw, bh / sh) if modo == "cobrir" else min(bw / sw, bh / sh)) * 100
        larg, alt = sw * s / 100, sh * s / 100
        ini, fim = t_in - 0.05, t_out + SAI
        sx = -1 if espelhar else 1          # a criatura é pedida olhando para a direita; espelhada, olha para a esquerda
        kw = dict(kind="footage", file=str(arq), src=[sw, sh], start=ini, pos=[cx, cy], motion_blur=True,
                  name=nome or Path(str(el.get("asset") or el.get("arquivo"))).name)
        kw["opacity_keys"] = ([[ini, 0], [ini + ENTRA, opacidade]] if fade else [[ini, opacidade]]) + \
            [[t_out, opacidade], [fim, 0]]
        fase = round(self.rnd.uniform(0, 6.28), 2)
        tela = t_out - t_in
        if mov is None:
            p = 1 + min(8, 1.0 * tela) / 100
            kw["scale_keys"] = [[ini, [s * sx, s]], [fim, [s * p * sx, s * p]]]
            kw["linear_scale"] = True
            if entra_dy:
                kw["pos_keys"] = [[t_in, [cx, cy + entra_dy], EASE_OUT], [t_in + 0.5, [cx, cy], EASE_IN]]
        else:
            kw["scale"] = [s * sx, s]
            if mov in ("nada", "parado") and fade:
                # chega num zoom rápido (de 145% a 100% em 0,5 s, com borrão de movimento) em vez de uma fusão
                kw.pop("scale")
                kw["scale_keys"] = [[ini, [s * 1.45 * sx, s * 1.45], SAI_RAPIDO], [ini + CHEGADA, [s * sx, s], ASSENTA]]
                kw["opacity_keys"] = [[ini, 0], [ini + 0.15, opacidade], [t_out, opacidade], [fim, 0]]
            if mov == "nada":               # atravessa devagar para onde olha
                d = min(260, 22 * tela)
                kw["pos_keys"] = [[ini, [cx - sx * d / 2, cy]], [fim, [cx + sx * d / 2, cy]]]
            elif mov == "atravessa":        # cruza a tela inteira, de fora a fora (as orcas do Depth Theory)
                fora = W / 2 + larg / 2 + 60
                kw["pos_keys"] = [[ini, [CX - sx * fora, cy]], [fim, [CX + sx * fora, cy]]]
                kw["opacity_keys"] = [[ini, opacidade], [fim, opacidade]]
            elif mov == "entra":            # chega de fora da tela pelo lado de trás
                kw["pos_keys"] = [[ini, [cx - sx * (W / 2 + larg / 2 + 40), cy], EASE_OUT], [ini + 1.4, [cx, cy], EASE_IN]]
                kw["opacity_keys"] = [[ini, opacidade], [t_out, opacidade], [fim, 0]]
            elif mov == "sobe":             # sobe do fundo
                kw["pos_keys"] = [[ini, [cx, cy + H / 2 + alt / 2], EASE_OUT], [ini + 1.6, [cx, cy], EASE_IN]]
                kw["opacity_keys"] = [[ini, opacidade], [t_out, opacidade], [fim, 0]]
            elif mov == "close":            # grande, cortada pela tela, aproximando
                p = 1 + min(10, 1.2 * tela) / 100
                kw.pop("scale")
                kw["scale_keys"] = [[ini, [s * sx, s]], [fim, [s * p * sx, s * p]]]
                kw["linear_scale"] = True
            if entra_dy and "pos_keys" not in kw:
                kw["pos_keys"] = [[t_in, [cx, cy + entra_dy], EASE_OUT], [t_in + 0.5, [cx, cy], EASE_IN]]
            amp = 6 if mov == "close" else 9
            kw["expr"] = {"pos": f"value + [0, {amp}*Math.sin(time*1.25 + {fase})]",
                          "rot": f"value + 1.4*Math.sin(time*0.85 + {fase})"}
            # dentro da água: tingida pela luz do fundo, um pouco mais escura, com a borda de cima acesa; e o corpo
            # ondula de leve (os braços/barbatanas parecem mexer)
            if silhueta:        # contraluz / vulto: quase preto, só a borda acesa
                kw["grade"] = {"tint": [[0.01, 0.02, 0.03], [0.07, 0.11, 0.13], 100],
                               "borda": [max(2.0, larg / 300), (self.luz or FUNDOS["mar"]["luz"])[1], 0.35]}
            elif self.luz:
                kw["grade"] = {"tint": [self.luz[0], self.luz[1], TINGE], "brilho": -10,
                               "borda": [max(2.0, larg / 400), self.luz[1], 0.55]}
            kw["ondula"] = [max(3.0, larg / 330), max(160.0, larg / 4.5), 0.45]
        if dur is not None and dur < fim - ini:
            kw["timeremap"] = True          # trecho curto: segura o último quadro
        kw["in"], kw["out"] = ini, fim
        self.add(**kw)
        self.reg("card", str(el.get("asset") or el.get("arquivo")), t_in, t_out,
                 [cx - larg / 2, cy - alt / 2, cx + larg / 2, cy + alt / 2])
        return larg, alt

    def foto_moldura(self, el, t_in, t_out, cx, cy, bw, bh, rot=-1.5):
        """Foto/vídeo real como uma foto impressa: borda de papel, sombra, um pouco torta, subindo."""
        arq, sw, sh, dur = self.preparar(el)
        s = min(bw / sw, bh / sh)
        larg, alt = sw * s, sh * s
        fim = t_out + SAI
        k = self.add(kind="null", name="moldura", pos=[cx, cy], rot=rot, **{"in": t_in, "out": fim},
                     pos_keys=[[t_in, [cx, cy + 40], EASE_OUT], [t_in + 0.6, [cx, cy], EASE_IN]],
                     scale_keys=[[t_in, 100], [fim, 100 + min(5, 0.6 * (t_out - t_in))]], linear_scale=True)
        op = [[t_in, 0], [t_in + ENTRA, 100], [t_out, 100], [fim, 0]]
        b = 16
        self.add(kind="shape", items=[{"t": "rect", "size": [larg + 2 * b, alt + 2 * b], "radius": 3, "fill": PAPEL}],
                 pos=[0, 0], name="moldura papel", parent=k, shadow={"op": 140, "dist": 10, "soft": 40},
                 opacity_keys=op, **{"in": t_in, "out": fim})
        kw = dict(kind="footage", file=str(arq), src=[sw, sh], start=t_in - 0.05, pos=[0, 0], scale=s * 100, parent=k,
                  name=Path(str(el.get("asset"))).name, opacity_keys=op, **{"in": t_in - 0.05, "out": fim})
        if dur is not None and dur < fim - t_in:
            kw["timeremap"] = True
        self.add(**kw)
        self.reg("card", str(el.get("asset")), t_in, t_out, [cx - larg / 2, cy - alt / 2, cx + larg / 2, cy + alt / 2])
        return larg, alt

    def silhueta(self):
        """O "você": o do elenco do vídeo (<vídeo>/elenco/voce.png), o personagem do canal (identidade/personagem.png)
        ou uma pessoa simples em branco."""
        for p in [self.proj.parent.parent / "elenco" / "voce.png"] + sorted((caminhos.canal() / "identidade").glob("personagem.*")):
            if p.exists():
                return p
        dst = self.cache / "pessoa.png"
        if not dst.exists():
            im = Image.new("RGBA", (200, 600), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            c = (242, 244, 245, 255)
            d.ellipse((72, 0, 128, 62), fill=c)
            d.rounded_rectangle((56, 70, 144, 330), 30, fill=c)
            d.rounded_rectangle((30, 80, 58, 300), 14, fill=c)
            d.rounded_rectangle((142, 80, 170, 300), 14, fill=c)
            d.rounded_rectangle((60, 300, 98, 600), 16, fill=c)
            d.rounded_rectangle((102, 300, 140, 600), 16, fill=c)
            im.save(dst)
        return dst

    def voce(self, t_in, t_out, x, y, tamanho, olha=1, alvo=False, lanterna=False):
        """O "você" com `tamanho` px no maior lado (de pé = altura, deitado = comprimento; na escala do E1, os 1,8 m)
        (olha = 1 para a direita, -1 para a esquerda), com as cantoneiras vermelhas de alvo e a lanterna acesa para a
        frente, como o mergulhador do Depth Theory."""
        arq = self.silhueta()
        sw, sh = Image.open(arq).size
        s = tamanho / max(sw, sh) * 100
        larg, alt = sw * s / 100, sh * s / 100
        fase = round(self.rnd.uniform(0, 6.28), 2)
        fim = t_out + SAI
        op = [[t_in, 0], [t_in + ENTRA, 100], [t_out, 100], [fim, 0]]
        bob = f"value + [0, 5*Math.sin(time*1.6 + {fase})]"
        deitado = sw > sh
        if lanterna:     # facho de luz que sai da mão da frente do "você" (no mergulhador deitado, embaixo à frente)
            x0 = x + olha * larg * 0.47
            y = y + (alt * 0.22 if deitado else 0)
            # 3 fachos de comprimentos diferentes, somados: forte perto do "você", sumindo longe (um só terminava
            # num corte reto, teste de 2026-11-03)
            fachos = [{"t": "path", "closed": True, "fill": BRANCO, "fill_op": 35,
                       "pts": [[0, -8], [olha * L, -150 * L / 640], [olha * L, 150 * L / 640], [0, 8]]}
                      for L in (260, 440, 640)]
            self.add(kind="shape", name="lanterna", pos=[x0, y], blur=45, blend="add", items=fachos,
                     opacity_keys=[[k[0], k[1] * 0.3] for k in op], expr={"pos": bob}, **{"in": t_in, "out": fim})
        if lanterna and deitado:
            y = y - alt * 0.22
        # borda de luz como a da criatura: o personagem escuro não some no fundo escuro
        self.add(kind="footage", file=str(arq), src=[sw, sh], start=t_in, pos=[x, y],
                 scale=[s * (1 if olha > 0 else -1), s], name="você", opacity_keys=op, expr={"pos": bob},
                 grade={"borda": [max(1.5, larg / 260), (self.luz or FUNDOS["mar"]["luz"])[1], 0.6]},
                 **{"in": t_in, "out": fim})
        if alvo:         # cantoneiras vermelhas em volta do "você" (ele foi achado)
            m, c = max(80, larg * 0.6), 26
            itens = [{"t": "path", "pts": [[sx * m, sy * (m - c)], [sx * m, sy * m], [sx * (m - c), sy * m]],
                      "stroke": VERMELHO, "sw": 4} for sx in (-1, 1) for sy in (-1, 1)]
            self.add(kind="shape", items=itens, pos=[x, y], name="alvo", camada="ui",
                     scale_keys=[[t_in + 0.4, 140, EASE_OUT], [t_in + 0.7, 100, EASE_IN]],
                     opacity_keys=[[t_in + 0.4, 0], [t_in + 0.5, 100], [t_out, 100], [fim, 0]],
                     expr={"pos": bob}, **{"in": t_in + 0.4, "out": fim})
        return larg

    def sonar(self, t_in, t_out, x, y, direcao):
        """Arcos que saem da criatura em direção ao "você" (o eco que acha você): direcao 1 = para a direita."""
        fim = t_out + SAI
        arco = [15, 35] if direcao > 0 else [65, 85]      # o trecho da elipse virado para o lado do "você"
        for k in range(4):
            self.add(kind="shape", items=[{"t": "ellipse", "size": [900, 900], "stroke": _rgb("#9FC3CC"), "sw": 3,
                                           "arco": arco}],
                     pos=[x, y], name=f"sonar {k + 1}", **{"in": t_in, "out": fim},
                     expr={"scale": f"var f = (time*0.45 + {k / 4:.3f}) % 1; [10 + f*90, 10 + f*90]",
                           "opacity": f"var f = (time*0.45 + {k / 4:.3f}) % 1; 75*Math.sin(f*Math.PI)"})

    # ---------- fundo ----------
    def fundo(self, tipo, t0, t1, primeiro):
        ini, fim = t0 - (0 if primeiro else 0.05), t1 + FUSAO
        op = ([[ini, 100]] if primeiro else [[ini, 0], [ini + FUSAO, 100]]) + [[t1, 100], [fim, 0]]
        if isinstance(tipo, dict):       # cenário gerado (um card com "fundo": true)
            self.imagem(tipo, t0, t1, CX, CY, W, H, "cobrir", nome="fundo (cenário)", fade=not primeiro)
            self.registro[-1]["tipo"] = "fundo"      # o cenário não conta como "algo em cena" no QA
            self.layers[-1]["camada"] = "fundo"
            return
        f = FUNDOS.get(tipo) or FUNDOS["escuro"]
        self.add(kind="solid", color=f["ate"], name=f"fundo {tipo}", ramp=[[CX, 0], f["de"], [CX, H], f["ate"]],
                 opacity_keys=op, camada="fundo", **{"in": ini, "out": fim})
        if f.get("raios"):
            itens = [{"t": "path", "closed": True, "fill": BRANCO,
                      "pts": [[x - w0 / 2, 0], [x + w0 / 2, 0], [x * 1.6 + w1 / 2, 1100], [x * 1.6 - w1 / 2, 1100]]}
                     for x, w0, w1 in [(-520, 90, 360), (-180, 60, 260), (160, 110, 420), (520, 70, 300)]]
            self.add(kind="shape", items=itens, pos=[CX, -60], name="raios de luz", blur=70, blend="add", camada="fundo",
                     opacity_keys=[[k_[0], k_[1] * 0.045] for k_ in op],
                     expr={"rot": "value + 2.2*Math.sin(time*0.22)"}, **{"in": ini, "out": fim})
        if f.get("particulas") or f.get("estrelas"):
            est = bool(f.get("estrelas"))
            pts = []
            for _ in range(70 if est else 55):
                r = self.rnd.uniform(1.5, 3.5) if est else self.rnd.uniform(2, 6)
                pts.append({"t": "ellipse", "size": [r, r], "fill": BRANCO,
                            "pos": [self.rnd.uniform(-CX, CX), self.rnd.uniform(-CY, CY + (0 if est else 900))]})
            ex = {"opacity": "value*(0.75 + 0.25*Math.sin(time*2.1))"} if est else \
                {"pos": "[value[0] + 12*Math.sin(time*0.3), value[1] - time*7]"}
            self.add(kind="shape", items=pts, pos=[CX, CY], name="estrelas" if est else "partículas", camada="fundo",
                     opacity_keys=[[k_[0], k_[1] * (0.55 if est else 0.35)] for k_ in op], expr=ex,
                     **{"in": ini, "out": fim})
        if f.get("bokeh"):       # partículas grandes fora de foco: dão profundidade
            bolas = [{"t": "ellipse", "size": [r, r], "fill": BRANCO,
                      "pos": [self.rnd.uniform(-CX, CX), self.rnd.uniform(-CY, CY + 500)]}
                     for r in (self.rnd.uniform(30, 95) for _ in range(16))]
            self.add(kind="shape", items=bolas, pos=[CX, CY], name="partículas desfocadas", blur=22, camada="fundo",
                     opacity_keys=[[k_[0], k_[1] * 0.07] for k_ in op],
                     expr={"pos": "[value[0] + 20*Math.sin(time*0.17), value[1] - time*4]"}, **{"in": ini, "out": fim})
        if f.get("grade"):
            cor = _rgb("#1B4152")
            linhas = [{"t": "path", "pts": [[x, -CY], [x, CY]], "stroke": cor, "sw": 1.5} for x in range(-960, 961, 80)]
            linhas += [{"t": "path", "pts": [[-CX, y], [CX, y]], "stroke": cor, "sw": 1.5} for y in range(-520, 521, 80)]
            m, c = 56, 46            # cantoneiras
            for sx_, sy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                x, y = sx_ * (CX - m), sy_ * (CY - m)
                linhas.append({"t": "path", "pts": [[x, y - sy_ * c], [x, y], [x - sx_ * c, y]], "stroke": CINZA, "sw": 3})
            self.add(kind="shape", items=linhas, pos=[CX, CY], name="grade", opacity_keys=op, camada="fundo",
                     **{"in": ini, "out": fim})


# ---------- tipos de cena ----------
def _txts(e, campo):
    return [t for t in e.get(campo, []) if isinstance(t, list)]


def _opc(c):
    return c.get("opcoes") or {}


def cena(M, e, fim, extras_de=None):
    lay = e["layout"]
    cards = [c for c in e.get("cards", []) if not _opc(c).get("fundo")]
    op = e.get("opcoes") or {}
    textos, rotulos = _txts(e, "textos"), _txts(e, "rotulos")
    ini = e["ini"]

    def vulto(c, o, fim):
        """O vulto: a mesma criatura, enorme, escura e desfocada, passando rápido na frente da câmera."""
        v = o.get("vulto")
        if not v:
            return
        t_v = max(v.get("t", c["t"]), ini)
        if o.get("so_vulto"):        # só o vulto em cena: ele ocupa o estado inteiro, desde o começo
            t_v = ini
        M.imagem(c, t_v, max(min(fim, t_v + 2.6), fim if o.get("so_vulto") else 0), CX, CY + 120, 4200, 2300,
                 mov="atravessa", espelhar=bool(o.get("espelhar")), silhueta=True, nome="vulto")
        M.layers[-1]["blur"] = 14

    def extras_do_card(c, larg, alt, cx, cy, olha=1, cam=None, nome_pos=None):
        o = _opc(c)
        if o.get("circulo"):         # círculo tracejado em volta de um detalhe (o tubarão pequeno ao longe)
            r = o["circulo"]
            fx, fy = r.get("ponto", [0.5, 0.5])
            fx = fx if olha > 0 else 1 - fx
            pc = [cx - larg / 2 + fx * larg, cy - alt / 2 + fy * alt]
            t_c = max(r.get("t", c["t"]), ini)
            d_ = 2 * float(r.get("raio", 90))
            M.add(kind="shape", items=[{"t": "ellipse", "size": [d_, d_], "stroke": BRANCO, "sw": 3, "tracejado": [9, 9]}],
                  pos=[pc[0] - CX, pc[1] - CY] if cam is not None else pc, parent=cam, name="círculo", camada="ui"
                  if cam is None else "conteudo", scale_keys=[[t_c, 135, SAI_RAPIDO], [t_c + 0.3, 100, ASSENTA]],
                  opacity_keys=[[t_c, 0], [t_c + 0.15, 85], [fim, 85], [fim + SAI, 0]], **{"in": t_c, "out": fim + SAI})
        if o.get("nome"):            # o nome embaixo, em maiúsculas brancas, sem pílula ("SPERM WHALE")
            r = o["nome"]
            M.texto(r["texto"].upper(), max(r.get("t", c["t"]), ini), fim, nome_pos or [cx, cy + alt / 2 + 60], 44,
                    BRANCO, FONTE, tracking=90, max_w=1400)
        for n, mk in enumerate(o.get("marcadores", [])):
            M.marcador(mk["texto"], max(mk.get("t", c["t"]), ini), fim, mk.get("icone", "check"), n)
        if o.get("rotulo"):
            r = o["rotulo"]
            M.rotulo(r["texto"], max(r.get("t", c["t"]), ini), fim, [cx + larg * 0.2, cy - alt / 2 - 30])
        if o.get("carimbo"):
            r = o["carimbo"]
            M.carimbo(r["texto"], max(r.get("t", c["t"]), ini), fim, [cx + larg * 0.18, cy + alt * 0.28])
        if c.get("legenda"):
            tx, t = c["legenda"][:2]
            M.destaque(tx, max(t, ini), fim, [CX, H - 130])

    if lay == "_C1_extras":          # estado dentro de uma câmera contínua: só o que não é a criatura
        larg, alt, cx, olha, cam = extras_de
        c = cards[0]
        o = _opc(c)
        if o.get("voce"):
            xv = min(W - 170, max(170, cx + olha * (larg / 2 + 330)))
            t_v = max(c["t"], ini) + 0.3
            M.voce(t_v, fim, xv, CY + 30, 270, olha=-olha, alvo=bool(o.get("alvo", o.get("sonar"))),
                   lanterna=bool(o.get("lanterna", True)))
            if o.get("sonar"):
                M.sonar(t_v, fim, cx + olha * larg * 0.42, CY + 20, olha)
        vulto(c, o, fim)
        # na câmera contínua a criatura está ampliada: rótulo e carimbo vão para lugares fixos da tela; o círculo
        # vai preso à câmera (acompanha o detalhe quando ela anda)
        circ = {k: v for k, v in o.items() if k == "circulo"}
        if circ:
            extras_do_card(dict(c, opcoes=circ, legenda=None), larg, alt, cx, CY + 20, olha=olha, cam=cam)
        resto = dict(c, opcoes={k: v for k, v in o.items() if k != "circulo"})
        extras_do_card(resto, 900, 600, CX + 200, CY, nome_pos=[CX, H - 210])
        for tx, t, *_ in textos[:1]:
            M.rotulo(tx, max(t, ini), fim, [CX, 150])
    elif lay == "C1":                  # a criatura em cena
        c = cards[0]
        o = _opc(c)
        mov = o.get("movimento", "nada")
        olha = -1 if o.get("espelhar") else 1
        # grande como nas referências: a criatura ocupa ~70% da largura; com o "você", ela fica do lado de trás e ele
        # na frente dela; no close, sai da tela pelo lado de trás
        padrao = (CX - olha * 260) if o.get("voce") else CX
        cx = {"esquerda": 640, "direita": 1280}.get(o.get("lado"), padrao)
        bw, bh = (2300, 1300) if mov == "close" else (1450, 780)
        if mov == "close":
            cx -= olha * 380
        if o.get("contraluz"):       # foco de luz atrás: a criatura vira silhueta (o mergulhador contra o sol)
            # anéis sobrepostos do pequeno ao grande: o brilho cai devagar (um disco só, mesmo desfocado, tinha borda)
            aneis = [{"t": "ellipse", "size": [d_, d_], "fill": _rgb("#CFEFF5"), "fill_op": op_}
                     for d_, op_ in ((420, 55), (700, 35), (1000, 22), (1400, 12), (1900, 6))]
            M.add(kind="shape", items=aneis, pos=[cx, CY], name="contraluz", blur=140, blend="add",
                  opacity_keys=[[c["t"], 0], [c["t"] + 0.8, 90], [fim, 90], [fim + SAI, 0]],
                  **{"in": c["t"], "out": fim + SAI})
        if o.get("so_vulto"):        # só o vulto passando (a criatura ainda não aparece)
            vulto(c, dict(o, vulto=o.get("vulto") or {"t": c["t"]}), fim)
            larg, alt = 900, 600
        else:
            larg, alt = M.imagem(c, c["t"], fim, cx, CY + 20, bw, bh, mov=mov, espelhar=bool(o.get("espelhar")),
                                 silhueta=bool(o.get("contraluz")))
            vulto(c, o, fim)
        if o.get("voce"):
            xv = min(W - 170, max(170, cx + olha * (larg / 2 + 330)))
            t_v = max(c["t"], ini) + 0.3
            M.voce(t_v, fim, xv, CY + 30, 270, olha=-olha, alvo=bool(o.get("alvo", o.get("sonar"))),
                   lanterna=bool(o.get("lanterna", True)))
            if o.get("sonar"):
                M.sonar(t_v, fim, cx + olha * larg * 0.42, CY + 20, olha)
        extras_do_card(c, larg, alt, cx, CY + 20, olha=olha)
        for tx, t, *_ in textos[:1]:
            M.rotulo(tx, max(t, ini), fim, [CX, 150])
    elif lay == "E1":                # escala: a criatura, a régua que se desenha e o tamanho
        c = cards[0]
        larg, alt = M.imagem(c, c["t"], fim, CX + 60, CY - 40, 1300, 560, mov="parado")
        y = CY - 40 + alt / 2 + 50
        x0, x1 = CX + 60 - larg / 2, CX + 60 + larg / 2
        t_r = max((rotulos[0][1] if rotulos else c["t"] + 0.6), ini)
        M.forma([{"t": "path", "pts": [[x0 - CX, 0], [x1 - CX, 0]], "stroke": BRANCO, "sw": 3},
                 {"t": "path", "pts": [[x0 - CX, -14], [x0 - CX, 14]], "stroke": BRANCO, "sw": 3, "trim": False},
                 {"t": "path", "pts": [[x1 - CX, -14], [x1 - CX, 14]], "stroke": BRANCO, "sw": 3, "trim": False}],
                t_r - 0.2, fim, [CX, y], "régua", trim=[[t_r - 0.2, 0, EASE_OUT], [t_r + 0.6, 100, EASE_IN]])
        for k, (tx, t, *_) in enumerate(rotulos[:2]):
            if k == 0:
                M.texto(tx.upper(), max(t, ini), fim, [CX + 60, y + 48], 48, BRANCO, FONTE, tracking=80)
            else:
                M.destaque(tx, max(t, ini), fim, [CX + 60, y + 130], 40)
        esc = c.get("escala") or {}
        if esc.get("tamanho_m"):
            base = alt if esc.get("medida") == "altura" else larg
            h_p = max(22, min(alt, base * float(esc.get("pessoa_m", 1.8)) / float(esc["tamanho_m"])))
            M.voce(t_r, fim, x0 - 60, CY - 40 + alt / 2 - h_p / 2, h_p, lanterna=False)
    elif lay == "N1":                # comparação em ícones ("6–7 elefantes")
        c = cards[0]
        q = float(op.get("quantidade", 5))
        n = max(1, math.ceil(q))
        passo = min(230, 1500 / n)
        x_ini = CX - (n - 1) * passo / 2
        for k in range(n):
            frac = max(0.25, min(1.0, q - k))
            lado = passo * 0.9 * frac
            M.imagem(c, c["t"] + 0.12 * k, fim, x_ini + k * passo, CY + 40 + (passo * 0.9 - lado) / 2, lado, lado,
                     mov="parado", nome=f"ícone {k + 1}", entra_dy=30)
        for tx, t, *_ in textos[:1]:
            M.destaque(tx, max(t, ini), fim, [CX, CY - 200], 44)
        for tx, t, *_ in rotulos[:1]:
            M.rotulo(tx, max(t, ini), fim, [CX, CY + 260])
    elif lay == "N2":                # número grande (com barra de nível opcional)
        for tx, t, *_ in textos[:1]:
            M.texto(tx, max(t, ini), fim, [CX, CY - 40], 230, BRANCO, FONTE, tracking=-10, dy=30)
        for tx, t, *_ in rotulos[:1]:
            M.rotulo(tx, max(t, ini), fim, [CX, CY + 110], pilula=False)
        if op.get("barra") is not None:
            f = max(0.02, min(1.0, float(op["barra"])))
            t_b = max((textos[0][1] if textos else ini), ini)
            M.forma([{"t": "rect", "size": [1000, 26], "radius": 13, "fill": _rgb("#22414F")}], t_b, fim,
                    [CX, CY - 210], "barra (trilho)")
            M.forma([{"t": "path", "pts": [[-500, 0], [-500 + 1000 * f, 0]], "stroke": VERMELHO, "sw": 26}], t_b, fim,
                    [CX, CY - 210], "barra (nível)", trim=[[t_b + 0.2, 0, EASE_OUT], [t_b + 1.4, 100, EASE_IN]])
        if op.get("titulo"):
            M.destaque(op["titulo"]["texto"], max(op["titulo"].get("t", ini), ini), fim, [CX, 190], 42)
    elif lay == "L1":                # "YOUR OPTIONS": os itens entram e são riscados
        titulo = op.get("titulo") or {"texto": "Your options"}
        M.texto(titulo["texto"].upper(), max(titulo.get("t", ini), ini), fim, [CX, 300], 40, BRANCO, FONTE, tracking=140)
        itens = op.get("itens", [])
        y0 = 400
        for k, it in enumerate(itens):
            M.texto(f"{k + 1}. {it['texto'].upper()}", max(it.get("t", ini), ini), fim, [CX - 360, y0 + 76 * k], 40,
                    BRANCO, FONTE_ROTULO, "left", 60, 1100, dy=0)
        for r in op.get("riscar", []):
            k = int(r["item"]) - 1
            if 0 <= k < len(itens):
                w_ = min(1100, largura(f"{k + 1}. {itens[k]['texto'].upper()}", 40, 60))
                t_r = max(r.get("t", ini), ini)
                M.forma([{"t": "path", "pts": [[0, 0], [w_, 0]], "stroke": VERMELHO, "sw": 5}], t_r, fim,
                        [CX - 370, y0 + 76 * k], f"risco {k + 1}", trim=[[t_r, 0, EASE_OUT], [t_r + 0.35, 100, EASE_IN]])
        if op.get("veredito"):
            v = op["veredito"]
            M.destaque(v["texto"], max(v.get("t", ini), ini), fim, [CX, y0 + 76 * len(itens) + 70], 40)
    elif lay == "D1":                # documento: artigo, crônica antiga, carta (com a gravura, se houver)
        c = cards[0] if cards else None
        k = M.add(kind="null", name="documento", pos=[CX, CY], rot=-2.0, **{"in": ini, "out": fim + SAI},
                  pos_keys=[[ini, [CX, CY + 60], EASE_OUT], [ini + 0.6, [CX, CY], EASE_IN]],
                  scale_keys=[[ini, 100], [fim + SAI, 100 + min(5, 0.5 * (fim - ini))]], linear_scale=True)
        pw, ph = (980, 780) if c else (900, 520)
        base = dict(parent=k, opacity_keys=[[ini, 0], [ini + ENTRA, 100], [fim, 100], [fim + SAI, 0]],
                    **{"in": ini, "out": fim + SAI})
        M.add(kind="shape", items=[{"t": "rect", "size": [pw, ph], "radius": 6, "fill": PAPEL}], pos=[0, 0],
              name="papel", shadow={"op": 150, "dist": 12, "soft": 45}, **base)
        y = -ph / 2 + 60
        if op.get("fonte"):
            M.add(kind="text", text=op["fonte"]["texto"].upper(), pos=[0, y], size=22, color=VERMELHO, font=FONTE_ROTULO,
                  justify="center", tracking=120, max_w=pw - 120, anchor_mode="center", name="documento fonte", **base)
            y += 50
        if op.get("titulo"):
            M.add(kind="text", text=op["titulo"]["texto"], pos=[0, y], size=46, color=TINTA, font=FONTE_SERIFA,
                  justify="center", max_w=pw - 120, anchor_mode="top", name="documento título", **base)
            y += 110
        if c:
            arq, sw, sh, _ = M.preparar(c)
            s = min((pw - 120) / sw, (ph / 2 - 50 - y) / sh)
            M.add(kind="footage", file=str(arq), src=[sw, sh], start=ini, pos=[0, y + sh * s / 2], scale=s * 100,
                  name="documento imagem", **base)
        else:
            linhas = [{"t": "rect", "size": [pw - 160 - (j % 3) * 90, 14], "radius": 7, "fill": _rgb("#CFC5B0"),
                       "pos": [-(j % 3) * 45, y + 30 + 36 * j]} for j in range(5)]
            M.add(kind="shape", items=linhas, pos=[0, 0], name="documento linhas", **base)
        M.reg("card", "documento", ini, fim, [CX - pw / 2, CY - ph / 2, CX + pw / 2, CY + ph / 2])
        for tx, t, *_ in textos[:1]:
            M.destaque(tx, max(t, ini), fim, [CX, H - 90], 40)
    elif lay == "T1":                # linha do tempo
        pontos = op.get("pontos", [])
        if op.get("titulo"):
            M.texto(op["titulo"]["texto"].upper(), max(op["titulo"].get("t", ini), ini), fim, [CX, 330], 40, BRANCO,
                    FONTE, tracking=120)
        x0, x1 = 360, W - 360
        M.forma([{"t": "path", "pts": [[x0 - CX, 0], [x1 - CX, 0]], "stroke": CINZA, "sw": 3}], ini, fim, [CX, CY],
                "linha do tempo", trim=[[ini, 0, EASE_OUT], [ini + 0.9, 100, EASE_IN]])
        M.reg("card", "linha do tempo", ini, fim, [x0, CY - 5, x1, CY + 5])
        n = max(1, len(pontos))
        for k, p in enumerate(pontos):
            x = x0 + (x1 - x0) * (k + 0.5) / n
            t_p = max(p.get("t", ini), ini + 0.3)
            cor = VERMELHO if p.get("destaque") else BRANCO
            M.forma([{"t": "ellipse", "size": [22, 22], "fill": cor}], t_p, fim, [x, CY], f"ponto {k + 1}")
            M.texto(str(p.get("rotulo", "")), t_p, fim, [x, CY - 60], 52, cor, FONTE)
            if p.get("texto"):
                M.texto(p["texto"].upper(), t_p + 0.1, fim, [x, CY + 62], 28, CINZA, FONTE_ROTULO, tracking=80,
                        max_w=(x1 - x0) / n - 20)
    elif lay == "R1":                # o real: foto/vídeo como foto impressa, ou cheio
        c = cards[0]
        o = _opc(c)
        if not o.get("moldura"):     # como no Depth Theory: a filmagem real enche a tela; "moldura" = foto impressa
            M.imagem(c, c["t"], fim, CX, CY, W, H, "cobrir")
        else:
            M.foto_moldura(c, c["t"], fim, CX, CY - 10, 1240, 740, rot=o.get("rot", -1.5))
        if c.get("legenda"):
            tx, t = c["legenda"][:2]
            M.rotulo(tx, max(t, ini), fim, [CX, H - 110])
        for tx, t, *_ in textos[:1]:
            M.rotulo(tx, max(t, ini), fim, [CX, 110])
    elif lay == "F1":                # frase
        for k, (tx, t, *modo) in enumerate(textos):
            t1 = textos[k + 1][1] - 0.05 if k + 1 < len(textos) else fim
            if "vermelho" in modo:
                M.destaque(tx, max(t, ini), t1, [CX, CY], 64)
            else:
                M.texto(tx.upper(), max(t, ini), t1, [CX, CY], 84, BRANCO, FONTE, tracking=40, max_w=1560)
    elif lay == "S1":                # lado a lado (você × ele, lenda × realidade)
        M.forma([{"t": "path", "pts": [[0, -CY], [0, CY]], "stroke": CINZA, "sw": 2}], ini, fim, [CX, CY], "divisória",
                trim=[[ini, 0, EASE_OUT], [ini + 0.6, 100, EASE_IN]])
        for j, c in enumerate(cards[:2]):
            cx = CX + (-480 if j == 0 else 480)
            M.imagem(c, c["t"], fim, cx, CY + 40, 800, 640, mov=_opc(c).get("movimento", "parado"),
                     espelhar=bool(_opc(c).get("espelhar")))
            if c.get("acima"):
                tx, t = c["acima"][:2]
                M.rotulo(tx, max(t, ini), fim, [cx, 170], cor=VERMELHO if j else BRANCO, tam=42, pilula=False)
    else:
        raise SystemExit(f"layout \"{lay}\" não existe no bestiário (C1, E1, N1, N2, L1, D1, T1, R1, F1, S1)")


ENQUADRAMENTOS = {"inteiro": (1.0, [0.5, 0.5]), "medio": (1.55, [0.62, 0.5]), "close": (2.4, [0.8, 0.5]),
                  "detalhe": (3.4, [0.85, 0.55])}


def chave_imagem(e):
    """O que identifica a criatura de um C1 (para saber se o estado seguinte é a mesma imagem)."""
    cards = [c for c in e.get("cards", []) if not _opc(c).get("fundo")]
    if e["layout"] != "C1" or not cards:
        return None
    o = _opc(cards[0])
    if o.get("so_vulto") or o.get("movimento") in ("atravessa", "close"):
        return None                  # passagens e closes isolados não viram câmera contínua
    return (cards[0].get("asset") or cards[0].get("arquivo"), bool(o.get("contraluz")))


def cena_continua(M, estados, fins):
    """Vários estados C1 seguidos com a MESMA criatura (medido no Depth Theory: o cachalote fica 15 s na tela e a
    câmera vai do plano aberto ao close da cabeça): a criatura entra uma vez e uma câmera (null pai) muda de
    enquadramento a cada estado — "opcoes": {"camera": "inteiro"|"medio"|"close"|"detalhe"|{"zoom", "ponto"}}.
    Rótulos, carimbos, legendas, marcadores e o "você" de cada estado continuam na tela, fora da câmera."""
    e0, ini, fim = estados[0], estados[0]["ini"], fins[-1]
    c0 = [c for c in e0["cards"] if not _opc(c).get("fundo")][0]
    o0 = _opc(c0)
    olha = -1 if o0.get("espelhar") else 1
    tem_voce = any(_opc([c for c in e["cards"] if not _opc(c).get("fundo")][0]).get("voce") for e in estados)
    cx = (CX - olha * 260) if tem_voce else CX
    cam = M.add(kind="null", name="câmera", pos=[CX, CY], **{"in": ini - 0.1, "out": fim + SAI})
    larg, alt = M.imagem(c0, c0["t"], fim, cx, CY + 20, 1450, 780, mov=o0.get("movimento", "parado")
                         if o0.get("movimento") in ("entra", "sobe", "parado") else "parado",
                         espelhar=bool(o0.get("espelhar")))
    cri = M.layers[-1]
    cri["parent"] = cam
    rel = lambda p_: [p_[0] - CX, p_[1] - CY]
    cri["pos"] = rel(cri["pos"])
    if cri.get("pos_keys"):
        cri["pos_keys"] = [[k[0], rel(k[1])] + k[2:] for k in cri["pos_keys"]]
    esc, pos = [], []
    anterior = None
    for k, e in enumerate(estados):
        cam_ = (e.get("opcoes") or {}).get("camera") or ("inteiro" if k == 0 else "medio")
        z, pt = (cam_["zoom"], cam_.get("ponto", [0.5, 0.5])) if isinstance(cam_, dict) else ENQUADRAMENTOS[cam_]
        px = pt[0] if olha > 0 else 1 - pt[0]           # a cabeça fica do lado para onde ela olha
        alvo = [cx - larg / 2 + px * larg, CY + 20 - alt / 2 + pt[1] * alt]
        P = [CX - z * (alvo[0] - CX), CY - z * (alvo[1] - CY)]
        t = e["ini"]
        if anterior is None:
            esc.append([t - 0.1, [z * 100, z * 100]])
            pos.append([t - 0.1, P])
        else:
            esc.append([t, [anterior[0] * 100, anterior[0] * 100], SAI_RAPIDO])
            pos.append([t, anterior[1], SAI_RAPIDO])
            esc.append([t + TROCA_CAMERA, [z * 100, z * 100], ASSENTA])
            pos.append([t + TROCA_CAMERA, P, ASSENTA])
        anterior = (z, P)
    deriva = 1 + min(0.04, 0.004 * (fim - estados[-1]["ini"]))   # o último enquadramento ainda anda um pouco
    esc.append([fim + SAI, [anterior[0] * 100 * deriva] * 2])
    M.layers[cam]["scale_keys"], M.layers[cam]["pos_keys"] = esc, pos
    # o que é de cada estado
    for e, f_ in zip(estados, fins):
        c = [c for c in e["cards"] if not _opc(c).get("fundo")][0]
        o = _opc(c)
        sub = dict(e, layout="_C1_extras")
        sub["cards"] = [c]
        cena(M, sub, f_, extras_de=(larg, alt, cx, olha, cam))


def fundo_de(e, atual):
    """O fundo do estado: um card com "fundo": true (cenário gerado), o "fundo" das opções, ou o de antes."""
    for c in e.get("cards", []):
        if _opc(c).get("fundo"):
            return {"asset": c["asset"]} if c.get("asset") else {"arquivo": c["arquivo"]}
    return (e.get("opcoes") or {}).get("fundo") or atual


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
    tt = plano.get("titulo")

    # fundos: um trecho por fundo igual seguido (a troca é uma fusão; o fundo não pisca entre os estados)
    atual = caminhos.ficha().get("fundo_padrao", "noite")
    marcos = ([(0.0, None)] if tt else []) + [(e["ini"], e) for e in estados]
    trechos = []
    for k, (t0, e) in enumerate(marcos):
        f = fundo_de(e, atual) if e else atual
        t1 = marcos[k + 1][0] if k + 1 < len(marcos) else fim_bloco
        chave = json.dumps(f, sort_keys=True)
        if trechos and trechos[-1][2] == chave:
            trechos[-1][1] = t1
        else:
            trechos.append([t0 if trechos else 0.0, t1, chave, f])
        atual = f
    for k, (t0, t1, _, f) in enumerate(trechos):
        M.fundo(f, t0, t1, primeiro=(k == 0))

    # título do capítulo: o nome grande à esquerda, sublinhado vermelho, e a criatura do título nadando à direita
    if tt:
        t0, tf = max(0, tt["t"] - 0.05), tt["fim"]
        el = {"arquivo": tt["arquivo"]} if tt.get("arquivo") else {"asset": tt["asset"]}
        if tt.get("arquivo") or M.manif.get(tt["asset"], {}).get("tipo") == "recorte":
            M.imagem(el, t0, tf, 1490, CY + 30, 700, 560, mov="nada")
        nome = quebrar(tt["texto"].upper(), 16)
        linhas = nome.count("\r") + 1
        y_topo = CY - linhas * 110 * 1.15 / 2 - 20
        M.texto(nome, t0, tf, [160, y_topo], 110, BRANCO, FONTE, "left", 20, 1000, ancora="top", nome="Título")
        M.forma([{"t": "path", "pts": [[0, 0], [260, 0]], "stroke": VERMELHO, "sw": 8}], t0, tf,
                [162, y_topo + linhas * 110 * 1.15 + 24], "título sublinhado",
                trim=[[t0 + 0.2, 0, EASE_OUT], [t0 + 0.8, 100, EASE_IN]])

    luz_de = {}
    atual = caminhos.ficha().get("fundo_padrao", "noite")
    for e in estados:
        atual = fundo_de(e, atual)
        luz_de[id(e)] = (FUNDOS.get(atual) or {}).get("luz") if isinstance(atual, str) else None
    fins = [estados[i + 1]["ini"] if i + 1 < len(estados) else fim_bloco for i in range(len(estados))]
    i = 0
    while i < len(estados):
        M.luz = luz_de[id(estados[i])]
        j = i + 1
        k_ = chave_imagem(estados[i])
        while k_ and j < len(estados) and chave_imagem(estados[j]) == k_ and luz_de[id(estados[j])] == M.luz:
            j += 1
        if j - i > 1:
            cena_continua(M, estados[i:j], fins[i:j])
        else:
            cena(M, estados[i], fins[i])
        i = j

    # marcador de capítulo (o capítulo não é falado: formato.json › roteiro.capitulo_falado = false). Como no vídeo do
    # urso do Depth Theory (4:08, "HUNT · out in the open · 3/9"): o nome grande embaixo à esquerda e as bolinhas
    # dos capítulos com o atual aceso, nos primeiros ~3 s do bloco
    rot = (proj / "roteiro.txt").read_text() if (proj / "roteiro.txt").exists() else ""
    if "#! capítulo" in rot and rot.startswith("#"):
        nome_cap = rot.splitlines()[0].lstrip("# ").strip()
        irmaos = sorted(int(b.name) for b in proj.parent.iterdir() if b.is_dir() and b.name.isdigit() and b.name != "00")
        n_cap, total = int(proj.name), max(irmaos) if irmaos else int(proj.name)
        t0 = (estados[0]["ini"] if estados else 0) + 0.15
        t1 = min(t0 + 3.0, fim_bloco - 0.3)
        y = H - 250
        M.texto(nome_cap.upper(), t0, t1, [120, y], 76, BRANCO, FONTE, "left", 30, 1200, nome="capítulo")
        bolinhas = []
        for k in range(1, total + 1):
            x = 132 + (k - 1) * 30
            if k == n_cap:
                bolinhas.append({"t": "ellipse", "size": [16, 16], "fill": VERMELHO, "pos": [x, 0], "trim": False})
            else:
                bolinhas.append({"t": "ellipse", "size": [12, 12], "stroke": CINZA, "sw": 2, "pos": [x, 0], "trim": False})
        M.forma(bolinhas, t0 + 0.15, t1, [0, y + 72], "capítulos")
        M.texto(f"{n_cap}/{total}", t0 + 0.15, t1, [132 + total * 30 + 8, y + 72], 26, CINZA, FONTE_ROTULO, "left", 60,
                200, nome="capítulo n")

    # vinheta por cima das imagens e por baixo dos textos; a ordem no After vai por camada (estável dentro dela)
    M.add(kind="solid", color=[0, 0, 0], name="vinheta", camada="vinheta", vinheta=[W / 2 + 140, H / 2 + 200, 560],
          opacity=62, **{"in": 0, "out": fim_bloco + 2})
    M.layers.sort(key=lambda L: CAMADAS[L["camada"]])

    ultimo = max([L["out"] for L in M.layers] + [0])
    dur = round(min(max(fim_bloco, ultimo), plano["fim"] + 2), 2)
    for L in M.layers:
        L["out"] = min(L["out"], dur)
    dados = {"nome": plano["nome"], "dur": dur, "fps": FPS, "w": W, "h": H, "audio": str(audio),
             "audio_offset": plano.get("offset_audio", 0), "cor_fundo": FUNDOS["escuro"]["ate"],
             "layers": M.layers, "salvar": str(proj / "edicao" / f"bloco_{a.item}_v2.aep"),
             "log": str(proj / "edicao" / f"log_{a.item}_v2.txt")}
    (proj / "edicao" / f"layout_{a.item}.json").write_text(json.dumps(M.registro, ensure_ascii=False, indent=0))
    # o mesmo plano em JSON: o compositor sem After (motor/edicao_ff/compor.py) desenha a partir dele
    (proj / "edicao" / f"plano_render_{a.item}.json").write_text(json.dumps(dados, ensure_ascii=False))
    modelo = caminhos.do_formato("edicao.modelo").read_text()
    jsx = proj / "edicao" / f"montar_{a.item}_v2.jsx"
    jsx.write_text("var DADOS = " + json.dumps(dados, ensure_ascii=False) + ";\n" + modelo)
    print(jsx, len(M.layers), "layers")


if __name__ == "__main__":
    main()
