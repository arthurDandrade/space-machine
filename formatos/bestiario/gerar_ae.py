"""Editor do bestiário: monta um bloco a partir de edicao/plano_edicao_<item>.json e gera edicao/montar_<item>_v2.jsx
(o mesmo nome do explained: o editar_bloco.sh, o final.py e o rodar.py procuram esse) com o montar_modelo.jsx do formato.

Uso: python gerar_ae.py <projeto> [--item 01]

O visual (conhecimento/04 - Edição/Visual do Bestiário.md): fundo preto, gravura e ilustração em traço claro sobre o
preto (modo de mesclagem "tela": o preto da imagem some no fundo), foto e vídeo reais em preto e branco, um vermelho só
para destaque. Cada imagem entra e sai em fusão (~0,45 s) e anda devagar (zoom lento, alternando aproximar e afastar).
Layouts (biblioteca_cenas.json): P1 plena, P2 plena + legenda, R1 gravura no escuro, D1 lenda × realidade,
E1 escala, T1 frase, Q1 citação.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "motor"))
import caminhos  # noqa: E402

W, H = 1920, 1080
CX, CY = W / 2, H / 2
FPS = 30                 # imagem parada que anda devagar: 60 fps não muda nada e dobra o render
FIM_BLOCO = 0.6          # s de tela depois da última palavra (igual ao explained)
FADE_IMG = 0.45          # fusão de entrada/saída das imagens
FADE_TXT = 0.25
SUBIDA_TXT = 14          # px que o texto sobe ao entrar
PUSH_S = 1.2             # % de zoom por segundo de tela
PUSH_MAX = 12            # % máximo de zoom numa imagem


def _rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


COR_FUNDO = _rgb("#060607")
BRANCO = _rgb("#EEEBE4")         # branco de papel velho, não branco de tela
VERMELHO = _rgb("#D7262B")
SOMBRA = {"op": 200, "soft": 24, "dist": 0}
FONTE_TITULO = "Baskerville-SemiBold"
FONTE_CITACAO = "Baskerville-Italic"
FONTE_ROTULO = "AvenirNext-Heavy"
CLAROS = ("gravura", "ilustracao")    # traço claro sobre preto: entram em modo "tela"


class Montador:
    def __init__(self, proj):
        self.proj = proj
        self.cache = proj / "edicao" / "_cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.layers = []
        self.registro = []          # textos e imagens com tempos e caixas (edicao/layout_<item>.json, para o QA)
        man = json.loads((proj / "manifesto.json").read_text())["assets"]
        self.manif = {m["id"]: m for m in man}
        self.vez = 0                # alterna aproximar/afastar

    # ---------- arquivos ----------
    def arquivo(self, el):
        return self.proj / (el["arquivo"] if el.get("arquivo") else self.manif[el["asset"]]["arquivo"])

    def tipo(self, el):
        return self.manif.get(el.get("asset"), {}).get("tipo", "foto")

    def preparar(self, el):
        """(arquivo, w, h, duração|None, claro). Gravura vira traço claro sobre preto (inverte o papel e corta a
        margem); ilustração clara de fundo branco também inverte; foto vira preto e branco. Vídeo vai como está
        (o preto e branco é efeito no After)."""
        src, tipo = self.arquivo(el), self.tipo(el)
        if src.suffix.lower() in (".mp4", ".mov"):
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height:format=duration", "-of", "json", str(src)],
                               capture_output=True, text=True)
            j = json.loads(r.stdout)
            return src, j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"]), False
        dst = self.cache / f"{src.parent.name}_{src.stem}_{tipo}.png"
        claro = tipo in CLAROS
        if not dst.exists():
            im = ImageOps.exif_transpose(Image.open(src))
            if im.mode in ("RGBA", "LA", "P"):
                fundo = Image.new("RGB", im.size, (255, 255, 255) if claro else (0, 0, 0))
                im = im.convert("RGBA")
                fundo.paste(im, mask=im.getchannel("A"))
                im = fundo
            cinza = ImageOps.autocontrast(im.convert("L"), cutoff=1)
            if claro:
                if sum(cinza.histogram()[128:]) > cinza.width * cinza.height / 2:   # papel claro: inverte
                    cinza = ImageOps.invert(cinza)
                # o preto do papel invertido precisa ser preto mesmo (no modo "tela", cinza escuro vira névoa)
                cinza = cinza.point(lambda v: 0 if v < 38 else min(255, int((v - 38) * 255 / 217)))
                bb = cinza.point(lambda v: 255 if v > 60 else 0).getbbox()
                if bb:
                    m = 12
                    cinza = cinza.crop((max(0, bb[0] - m), max(0, bb[1] - m),
                                        min(cinza.width, bb[2] + m), min(cinza.height, bb[3] + m)))
            esc = min(1.0, 2600 / max(cinza.size))
            if esc < 1:
                cinza = cinza.resize((round(cinza.width * esc), round(cinza.height * esc)), Image.LANCZOS)
            cinza.convert("RGB").save(dst)
        w, h = Image.open(dst).size
        return dst, w, h, None, claro

    # ---------- layers ----------
    def add(self, **kw):
        kw["id"] = len(self.layers)
        self.layers.append(kw)
        return kw["id"]

    def imagem(self, el, t_in, t_out, caixa, modo="conter", nome=None, opacidade=100, fade_in=True):
        """Imagem/vídeo de t_in a t_out (com fusão nas duas pontas) dentro da caixa (cx, cy, w, h).
        modo "cobrir" enche a caixa (corta o que sobra); "conter" cabe inteira. Devolve (largura, altura) na tela."""
        arq, sw, sh, dur, claro = self.preparar(el)
        cx, cy, bw, bh = caixa
        if modo == "cobrir" and not (claro and self.tipo(el) == "gravura"):
            s = max(bw / sw, bh / sh)
        else:
            s = min(bw / sw, bh / sh)
        s *= 100
        tela = t_out - t_in
        p = min(PUSH_MAX, PUSH_S * tela) / 100
        self.vez += 1
        s0, s1 = (s, s * (1 + p)) if self.vez % 2 else (s * (1 + p), s)
        ini = t_in - (0.05 if fade_in else 0)
        fim = t_out + FADE_IMG
        kw = dict(kind="footage", file=str(arq), src=[sw, sh], start=ini, pos=[cx, cy], parent=None,
                  name=nome or Path(str(el.get("asset") or el.get("arquivo"))).name,
                  scale_keys=[[ini, round(s0, 3)], [fim, round(s1, 3)]], linear_scale=True,
                  opacity_keys=([[ini, 0], [ini + FADE_IMG, opacidade]] if fade_in else [[ini, opacidade]])
                  + [[t_out, opacidade], [fim, 0]])
        kw["in"], kw["out"] = ini, fim
        if claro:
            kw["blend"] = "screen"
        if dur is not None:
            kw["pb"] = True                       # vídeo real em preto e branco, como as fotos
            if dur < fim - ini:
                kw["timeremap"] = True            # trecho curto: segura o último quadro
        self.add(**kw)
        larg, alt = min(bw, sw * s / 100), min(bh, sh * s / 100)
        self.registro.append({"tipo": "card", "id": el.get("asset") or el.get("arquivo"), "in": ini, "out": fim,
                              "box": [cx - larg / 2, cy - alt / 2, cx + larg / 2, cy + alt / 2]})
        return larg, alt

    def texto(self, txt, t_in, t_out, pos, max_w, max_size, cor=None, fonte=FONTE_TITULO, sombra=SOMBRA,
              ancora="center", nome=None):
        cor = cor or BRANCO
        kw = dict(kind="text", text=txt, parent=None, max_w=max_w, max_size=max_size, color=cor, shadow=sombra,
                  anchor_mode=ancora, name=nome or txt.replace("\r", " ")[:60], font=fonte,
                  pos_keys=[[t_in, [pos[0], pos[1] + SUBIDA_TXT], [0, 0.1, 0, 75]],
                            [t_in + FADE_TXT * 2, list(pos), [0, 75, 0, 0.1]]],
                  opacity_keys=[[t_in, 0], [t_in + FADE_TXT, 100], [t_out, 100], [t_out + FADE_TXT, 0]])
        kw["in"], kw["out"] = t_in, t_out + FADE_TXT
        linhas = txt.count("\r") + 1
        larg = min(max_w, max(len(l) for l in txt.split("\r")) * 0.58 * max_size)
        alt = max_size * 1.15 * linhas
        y0 = pos[1] if ancora == "top" else (pos[1] - alt if ancora == "bottom" else pos[1] - alt / 2)
        self.registro.append({"tipo": "texto", "txt": txt.replace("\r", " "), "in": t_in, "out": t_out,
                              "box": [pos[0] - larg / 2, y0, pos[0] + larg / 2, y0 + alt]})
        return self.add(**kw)

    def silhueta(self, altura_px):
        """Pessoa em pé, em branco, para a escala (E1): desenhada aqui, sem busca."""
        dst = self.cache / "pessoa.png"
        if not dst.exists():
            im = Image.new("RGBA", (200, 600), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            c = (238, 235, 228, 255)
            d.ellipse((72, 0, 128, 62), fill=c)                       # cabeça
            d.rounded_rectangle((56, 70, 144, 330), 30, fill=c)       # tronco
            d.rounded_rectangle((30, 80, 58, 300), 14, fill=c)        # braços
            d.rounded_rectangle((142, 80, 170, 300), 14, fill=c)
            d.rounded_rectangle((60, 300, 98, 600), 16, fill=c)       # pernas
            d.rounded_rectangle((102, 300, 140, 600), 16, fill=c)
            im.save(dst)
        return dst, 200 * altura_px / 600, altura_px


def quebrar(txt, limite):
    """Frase longa em 2 linhas, quebrando no espaço mais perto do meio."""
    if len(txt) <= limite or " " not in txt:
        return txt
    meio = len(txt) / 2
    k = min((i for i, ch in enumerate(txt) if ch == " "), key=lambda i: abs(i - meio))
    return txt[:k] + "\r" + txt[k + 1:]


def estado(M, e, fim):
    lay = e["layout"]
    cards = e.get("cards", [])
    textos = [t for t in e.get("textos", []) if isinstance(t, list)]
    rotulos = [t for t in e.get("rotulos", []) if isinstance(t, list)]

    def sequencia(c, caixa, modo):
        """O card e as trocas dele, uma depois da outra no mesmo lugar."""
        seq = [c] + c.get("troca", [])
        tam = None
        for k, el in enumerate(seq):
            t1 = seq[k + 1]["t"] if k + 1 < len(seq) else fim
            r = M.imagem(el, el["t"], t1, caixa, modo)
            tam = tam or r
        return tam

    if lay in ("P1", "P2"):
        for c in cards[:1]:
            sequencia(c, (CX, CY, W, H), "cobrir")
            if c.get("legenda"):
                tx, t = c["legenda"][:2]
                M.texto(tx.upper(), max(t, e["ini"]), fim, [CX, H - 120], 1500, 70, fonte=FONTE_ROTULO,
                        ancora="bottom")
    elif lay == "R1":
        for c in cards[:1]:
            sequencia(c, (CX, CY, 1560, 920), "conter")
    elif lay == "D1":
        for j, c in enumerate(cards[:2]):
            cx = CX + (-460 if j == 0 else 460)
            sequencia(c, (cx, CY + 50, 840, 760), "conter")
            if c.get("acima"):
                tx, t = c["acima"][:2]
                M.texto(tx.upper(), max(t, e["ini"]), fim, [cx, CY - 360], 800, 64, cor=VERMELHO,
                        fonte=FONTE_ROTULO, ancora="bottom")
    elif lay == "E1":
        c = cards[0] if cards else None
        if c:
            esc = c.get("escala") or {}
            larg, alt = sequencia(c, (CX + 260, CY - 30, 1260, 800), "conter")
            m = float(esc.get("tamanho_m") or 10)
            p = float(esc.get("pessoa_m") or 1.8)
            # a criatura ocupa a largura do desenho (comprimento) ou a altura dele ("altura")
            base = alt if esc.get("medida") == "altura" else larg
            h_p = max(26, min(alt, base * p / m))
            arq, pw, ph = M.silhueta(h_p)
            chao = CY - 30 + alt / 2
            x_p = CX + 260 - larg / 2 - 110
            M.add(kind="footage", file=str(arq), src=[200, 600], start=c["t"], pos=[x_p, chao - ph / 2],
                  parent=None, name="pessoa", scale=round(ph / 6, 3),
                  opacity_keys=[[c["t"] + 0.3, 0], [c["t"] + 0.3 + FADE_IMG, 100], [fim, 100], [fim + FADE_IMG, 0]],
                  **{"in": c["t"], "out": fim + FADE_IMG})
            M.texto(esc.get("pessoa_rotulo", "you").upper(), c["t"] + 0.3, fim, [x_p, chao + 24], 300, 34,
                    fonte=FONTE_ROTULO, ancora="top")
            for k, (tx, t, *_) in enumerate(rotulos[:1]):
                M.texto(tx.upper(), max(t, c["t"] + 0.3), fim, [CX + 260, chao + 24], 900, 60, cor=VERMELHO,
                        fonte=FONTE_ROTULO, ancora="top")
    elif lay == "T1":
        for k, (tx, t, *modo) in enumerate(textos):
            t1 = textos[k + 1][1] - 0.05 if k + 1 < len(textos) else fim
            cor = VERMELHO if "vermelho" in modo else BRANCO
            M.texto(quebrar(tx, 26), max(t, e["ini"]), t1, [CX, CY], 1600, 132, cor=cor)
    elif lay == "Q1":
        if textos:
            tx, t = textos[0][:2]
            tx = "“" + tx.strip('“”" ') + "”"
            M.texto(quebrar(tx, 40), max(t, e["ini"]), fim, [CX, CY - 40], 1600, 100, fonte=FONTE_CITACAO)
        for tx, t, *_ in textos[1:2]:
            M.texto(tx.upper(), max(t, e["ini"]), fim, [CX, CY + 190], 1200, 46, cor=VERMELHO,
                    fonte=FONTE_ROTULO, ancora="top")
    else:
        raise SystemExit(f"layout \"{lay}\" não existe no bestiário (P1, P2, R1, D1, E1, T1, Q1)")


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

    # título do capítulo: o nome em serifa sobre a criatura apagada
    tt = plano.get("titulo")
    if tt:
        t0, tf = max(0, tt["t"] - 0.05), tt["fim"]
        M.imagem({"asset": tt["asset"]}, t0, tf, (CX, CY, 1500, 940), "conter", nome="Título (imagem)",
                 opacidade=40, fade_in=t0 > 0.1)
        M.texto(quebrar(tt["texto"], 28), t0, tf, [CX, CY], 1500, 150, nome="Título")

    for i, e in enumerate(estados):
        fim = estados[i + 1]["ini"] if i + 1 < len(estados) else fim_bloco
        estado(M, e, fim)

    ultimo = max([L["out"] for L in M.layers] + [0])
    dur = round(min(max(fim_bloco, ultimo), plano["fim"] + 2), 2)
    for L in M.layers:              # nada passa do fim da comp
        L["out"] = min(L["out"], dur)
    dados = {"nome": plano["nome"], "dur": dur, "fps": FPS, "w": W, "h": H, "audio": str(audio),
             "audio_offset": plano.get("offset_audio", 0), "cor_fundo": COR_FUNDO, "cor_sombra": [0, 0, 0],
             "fonte": FONTE_TITULO, "layers": M.layers,
             "salvar": str(proj / "edicao" / f"bloco_{a.item}_v2.aep"),
             "log": str(proj / "edicao" / f"log_{a.item}_v2.txt")}
    (proj / "edicao" / f"layout_{a.item}.json").write_text(json.dumps(M.registro, ensure_ascii=False, indent=0))
    modelo = caminhos.do_formato("edicao.modelo").read_text()
    jsx = proj / "edicao" / f"montar_{a.item}_v2.jsx"
    jsx.write_text("var DADOS = " + json.dumps(dados, ensure_ascii=False) + ";\n" + modelo)
    print(jsx, len(M.layers), "layers")


if __name__ == "__main__":
    main()
