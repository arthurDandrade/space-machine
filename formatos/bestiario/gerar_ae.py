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
ENTRA, SAI = 0.35, 0.2        # entrada (sobe e aparece) e saída (some): com 0,3 s o texto que saía ficava por cima da criatura que entrava
FUSAO = 0.45                  # troca de fundo
EASE_OUT = [0, 0.1, 0, 80]    # chave que sai suave
EASE_IN = [0, 80, 0, 0.1]     # chave que chega suave


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

    def aparece(self, kw, t_in, t_out, dy=18, pos=None):
        """Entra subindo e aparecendo em ENTRA s; some em SAI s depois de t_out."""
        pos = pos or kw.get("pos")
        kw["opacity_keys"] = [[t_in, 0], [t_in + ENTRA, 100], [t_out, 100], [t_out + SAI, 0]]
        if dy and pos:
            kw["pos_keys"] = [[t_in, [pos[0], pos[1] + dy], EASE_OUT], [t_in + ENTRA * 1.4, list(pos), EASE_IN]]
        kw["in"], kw["out"] = t_in, t_out + SAI
        return kw

    def texto(self, txt, t_in, t_out, pos, tam, cor=None, fonte=FONTE, justify="center", tracking=0, max_w=1700,
              ancora="center", dy=18, nome=None):
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
                       t_in, t_out, list(pos), f"pílula {txt[:20]}", dy=18)
        return self.texto(txt, t_in, t_out, pos, tam, cor or BRANCO, FONTE_ROTULO, "center", 120, 1500)

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
               fade=True, opacidade=100, entra_dy=0):
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
            if mov == "nada":               # atravessa devagar para onde olha
                d = min(260, 22 * tela)
                kw["pos_keys"] = [[ini, [cx - sx * d / 2, cy]], [fim, [cx + sx * d / 2, cy]]]
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
            if self.luz:
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

    def voce(self, t_in, t_out, x, y, altura, olha=1, alvo=False, lanterna=False):
        """O "você" (olha = 1 para a direita, -1 para a esquerda), com as cantoneiras vermelhas de alvo e a lanterna
        acesa para a frente, como o mergulhador do Depth Theory."""
        arq = self.silhueta()
        sw, sh = Image.open(arq).size
        s = altura / max(sw, sh) * 100 * (2.2 if sw > sh else 1)    # personagem deitado (mergulhador) é mais largo
        larg = sw * s / 100
        fase = round(self.rnd.uniform(0, 6.28), 2)
        fim = t_out + SAI
        op = [[t_in, 0], [t_in + ENTRA, 100], [t_out, 100], [fim, 0]]
        bob = f"value + [0, 5*Math.sin(time*1.6 + {fase})]"
        if lanterna:     # facho de luz que sai da frente do "você"
            x0 = x + olha * larg * 0.45
            # 3 fachos de comprimentos diferentes, somados: forte perto do "você", sumindo longe (um só terminava
            # num corte reto, teste de 2026-11-03)
            fachos = [{"t": "path", "closed": True, "fill": BRANCO, "fill_op": 35,
                       "pts": [[0, -8], [olha * L, -150 * L / 640], [olha * L, 150 * L / 640], [0, 8]]}
                      for L in (260, 440, 640)]
            self.add(kind="shape", name="lanterna", pos=[x0, y], blur=45, blend="add", items=fachos,
                     opacity_keys=[[k[0], k[1] * 0.3] for k in op], expr={"pos": bob}, **{"in": t_in, "out": fim})
        self.add(kind="footage", file=str(arq), src=[sw, sh], start=t_in, pos=[x, y],
                 scale=[s * (1 if olha > 0 else -1), s], name="você", opacity_keys=op, expr={"pos": bob},
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


def cena(M, e, fim):
    lay = e["layout"]
    cards = [c for c in e.get("cards", []) if not _opc(c).get("fundo")]
    op = e.get("opcoes") or {}
    textos, rotulos = _txts(e, "textos"), _txts(e, "rotulos")
    ini = e["ini"]

    def extras_do_card(c, larg, alt, cx, cy):
        o = _opc(c)
        if o.get("rotulo"):
            r = o["rotulo"]
            M.rotulo(r["texto"], max(r.get("t", c["t"]), ini), fim, [cx + larg * 0.2, cy - alt / 2 - 30])
        if o.get("carimbo"):
            r = o["carimbo"]
            M.carimbo(r["texto"], max(r.get("t", c["t"]), ini), fim, [cx + larg * 0.18, cy + alt * 0.28])
        if c.get("legenda"):
            tx, t = c["legenda"][:2]
            M.destaque(tx, max(t, ini), fim, [CX, H - 130])

    if lay == "C1":                  # a criatura em cena
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
        larg, alt = M.imagem(c, c["t"], fim, cx, CY + 20, bw, bh, mov=mov, espelhar=bool(o.get("espelhar")))
        if o.get("voce"):
            xv = min(W - 170, max(170, cx + olha * (larg / 2 + 330)))
            t_v = max(c["t"], ini) + 0.3
            M.voce(t_v, fim, xv, CY + 30, 120, olha=-olha, alvo=bool(o.get("alvo", o.get("sonar"))),
                   lanterna=bool(o.get("lanterna", True)))
            if o.get("sonar"):
                M.sonar(t_v, fim, cx + olha * larg * 0.42, CY + 20, olha)
        extras_do_card(c, larg, alt, cx, CY + 20)
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
        if o.get("cheio"):
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
    for i, e in enumerate(estados):
        M.luz = luz_de[id(e)]
        cena(M, e, estados[i + 1]["ini"] if i + 1 < len(estados) else fim_bloco)

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
    modelo = caminhos.do_formato("edicao.modelo").read_text()
    jsx = proj / "edicao" / f"montar_{a.item}_v2.jsx"
    jsx.write_text("var DADOS = " + json.dumps(dados, ensure_ascii=False) + ";\n" + modelo)
    print(jsx, len(M.layers), "layers")


if __name__ == "__main__":
    main()
