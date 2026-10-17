"""Reels 9:16 (1080x1920) de um bloco já montado. Teste de 2026-10-17, dois jeitos:

  moldura   o bloco 16:9 inteiro no meio da tela vertical, sobre o papel do canal, com o título do tópico no alto
            e legenda embaixo (da transcrição palavra a palavra). Usa o bloco_NN_v2.aep direto, sem render no meio.
  vertical  o mesmo plano montado de novo em 1080x1920 (gerar_ae2.py --vertical): cards em coluna, rótulos
            embaixo do card. Projeto à parte, bloco_NN_vertical.aep.

Uso: python reels.py <pasta do bloco> <NN> moldura|vertical [--sem-render]
Saída: <vídeo>/reels/bloco N - <modo>.mp4 (e o .aep da moldura em <vídeo>/reels/).
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import gerar_ae2 as g  # noqa: E402  (cores, fonte e fundo do canal)
import caminhos  # noqa: E402

AE = os.environ.get("SM_AFTER", "Adobe After Effects 2026")
W, H = 1080, 1920
Y_TITULO, Y_VIDEO, Y_LEGENDA = 330, 860, 1330    # Reels cobre ~250 px no alto e ~420 px embaixo com a interface

MOLDURA = r"""
(function () {
    var log = [];
    function texto(comp, t, fonte, tam, cor, y, ini, fim) {
        var L = comp.layers.addText(t);
        var tp = L.property("ADBE Text Properties").property("ADBE Text Document"), td = tp.value;
        td.font = fonte; td.fontSize = 100; td.applyFill = true; td.fillColor = cor; td.applyStroke = false;
        td.justification = ParagraphJustification.CENTER_JUSTIFY; td.leading = 108; tp.setValue(td);
        var r = L.sourceRectAtTime(0, false);
        var k = Math.min(tam, 100 * C.larg / r.width);
        td = tp.value; td.fontSize = k; td.leading = k * 1.1; tp.setValue(td);
        r = L.sourceRectAtTime(0, false);
        L.anchorPoint.setValue([r.left + r.width / 2, r.top + r.height / 2]);
        L.position.setValue([C.w / 2, y]);
        L.inPoint = ini; L.outPoint = fim;
        return L;
    }
    try {
        app.beginSuppressDialogs();
        if (app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        app.newProject();
        var p = app.project;
        var pasta = p.importFile(new ImportOptions(new File(C.aep)));
        var bloco = null;
        for (var i = 1; i <= p.numItems; i++) if (p.item(i) instanceof CompItem && p.item(i).name === C.comp) bloco = p.item(i);
        if (!bloco) throw new Error("comp não encontrada: " + C.comp);
        var comp = p.items.addComp(C.nome, C.w, C.h, 1, bloco.duration, bloco.frameRate);
        comp.bgColor = C.cor_fundo;
        comp.layers.addSolid(C.cor_fundo, "Fundo", C.w, C.h, 1, bloco.duration);
        if (C.fundo) {
            var fi = comp.layers.add(p.importFile(new ImportOptions(new File(C.fundo.file))));
            fi.opacity.setValue(C.fundo.opacidade);
            var s = 100 * C.h / fi.source.height;
            fi.scale.setValue([s, s]); fi.position.setValue([C.w / 2, C.h / 2]);
        }
        var v = comp.layers.add(bloco);
        var esc = 100 * C.w / bloco.width;
        v.scale.setValue([esc, esc]); v.position.setValue([C.w / 2, C.y_video]);
        var mk = v.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");   // cantos arredondados
        var rr = new Shape(), bw = bloco.width, bh = bloco.height, r0 = 40, kk = r0 * 0.4477;
        rr.vertices = [[r0, 0], [bw - r0, 0], [bw, r0], [bw, bh - r0], [bw - r0, bh], [r0, bh], [0, bh - r0], [0, r0]];
        rr.inTangents = [[-kk, 0], [0, 0], [0, -kk], [0, 0], [kk, 0], [0, 0], [0, kk], [0, 0]];
        rr.outTangents = [[0, 0], [kk, 0], [0, 0], [0, kk], [0, 0], [-kk, 0], [0, 0], [0, -kk]];
        rr.closed = true;
        mk.property("ADBE Mask Shape").setValue(rr);
        var sh = v.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
        sh.property("ADBE Drop Shadow-0001").setValue(C.cor_sombra);
        sh.property("ADBE Drop Shadow-0002").setValue(110);
        sh.property("ADBE Drop Shadow-0004").setValue(10);
        sh.property("ADBE Drop Shadow-0005").setValue(40);
        if (C.video_titulo) texto(comp, C.video_titulo, C.fonte_marca, 60, C.cor_texto, C.y_titulo - 120, 0, bloco.duration);
        texto(comp, C.titulo, C.fonte_marca, 150, C.cor_azul, C.y_titulo, 0, bloco.duration);
        for (var k = 0; k < C.legendas.length; k++) {
            var lg = C.legendas[k];
            var L = texto(comp, lg[0], C.fonte, 88, C.cor_texto, C.y_legenda, lg[1], lg[2]);
            L.scale.setValueAtTime(lg[1], [88, 88, 100]); L.scale.setValueAtTime(lg[1] + 0.12, [100, 100, 100]);
        }
        comp.openInViewer();
        p.save(new File(C.salvar));
        log.push("OK comp=" + comp.name);
    } catch (e) { log.push("ERRO " + e.toString() + " linha " + e.line); }
    app.endSuppressDialogs(false);
    var lf = new File(C.log); lf.encoding = "UTF-8"; lf.open("w"); lf.write(log.join("\n")); lf.close();
})();
"""


def legendas(palavras, ini_audio=0.0, max_chars=18, max_pal=3):
    """Grupos de até 3 palavras / 18 letras, quebrando na pontuação; cada um fica até o seguinte começar."""
    grupos, atual = [], []
    for w_ in palavras:
        if atual and (len(" ".join(x["p"] for x in atual + [w_])) > max_chars or len(atual) >= max_pal):
            # não termina em palavra de ligação ("DOESN'T END THE" / "COST."): ela passa para o grupo seguinte
            leva = [atual.pop()] if len(atual) > 1 and atual[-1]["p"].upper() in g.LIGACAO else []
            grupos.append(atual)
            atual = leva
        atual.append(w_)
        if re.search(r"[.,;:!?]$", w_["p"]):
            grupos.append(atual)
            atual = []
    if atual:
        grupos.append(atual)
    out = []
    for k, gr in enumerate(grupos):
        t0 = gr[0]["ini"] - ini_audio - 0.05
        prox = grupos[k + 1][0]["ini"] - ini_audio - 0.05 if k + 1 < len(grupos) else gr[-1]["fim"] - ini_audio + 0.4
        # pausa longa: a legenda sai 0,3 s depois da última palavra em vez de esperar a próxima
        t1 = min(prox, gr[-1]["fim"] - ini_audio + 0.3)
        out.append([" ".join(x["p"] for x in gr).strip(" ,;:.").upper(), round(max(0, t0), 2), round(t1, 2)])
    return out


def after(script, log, espera):
    Path(log).unlink(missing_ok=True)
    subprocess.run(["osascript", "-e", f"with timeout of {espera} seconds", "-e",
                    f'tell application "{AE}" to DoScriptFile "{script}"', "-e", "end timeout"],
                   capture_output=True, timeout=espera + 60)
    for _ in range(espera // 3):
        if Path(log).exists():
            return Path(log).read_text(errors="replace").strip()
        time.sleep(3)
    return ""


def renderizar(aep, comp, saida, log):
    jsx = Path(log).with_suffix(".jsx")
    cfg = json.dumps({"aep": str(aep), "comp": comp, "saida": str(saida), "log": str(log)}, ensure_ascii=False)
    jsx.write_text(f"var RENDER = {cfg};\n" + (AQUI / "renderizar.jsx").read_text())
    return after(jsx, log, 3600)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bloco")
    ap.add_argument("nn")
    ap.add_argument("modo", choices=("moldura", "vertical"))
    ap.add_argument("--sem-render", action="store_true")
    a = ap.parse_args()
    b = Path(a.bloco).resolve()
    nn = a.nn
    vd = b.parent.parent
    ed = b / "edicao"
    saida_dir = vd / "reels"
    saida_dir.mkdir(exist_ok=True)
    plano = json.loads((ed / f"plano_edicao_{nn}.json").read_text())
    trava = open(caminhos.dados() / "trava_after", "w")    # o After roda um script de cada vez
    fcntl.flock(trava, fcntl.LOCK_EX)
    try:
        if a.modo == "moldura":
            palavras = json.loads((b / "_work" / "palavras.json").read_text())
            est = {}
            try:
                est = json.loads((vd / "estudio_video.json").read_text())
            except (OSError, ValueError):
                pass
            titulo = (plano.get("titulo") or {}).get("texto") or plano["nome"].split(" - ", 1)[-1]
            aep = saida_dir / f"bloco_{nn}_moldura.aep"
            cfg = {"aep": str(ed / f"bloco_{nn}_v2.aep"), "comp": plano["nome"], "nome": f"Reels {plano['nome']} (moldura)",
                   "w": W, "h": H, "larg": W - 140, "y_titulo": Y_TITULO, "y_video": Y_VIDEO, "y_legenda": Y_LEGENDA,
                   "titulo": titulo.upper(),
                   "video_titulo": (est.get("titulo") or vd.name.replace("-", " ")).upper(),
                   "legendas": legendas(palavras, plano.get("offset_audio", 0)),
                   "fonte": g.FONTE, "fonte_marca": g.FONTE_MARCA, "cor_fundo": g.COR_FUNDO, "cor_texto": g.COR_TEXTO,
                   "cor_azul": g.COR_AZUL, "cor_sombra": g.COR_SOMBRA, "fundo": g.FUNDO_IMAGEM,
                   "salvar": str(aep), "log": str(saida_dir / f"log_moldura_{nn}.txt")}
            jsx = saida_dir / f"moldura_{nn}.jsx"
            jsx.write_text(f"var C = {json.dumps(cfg, ensure_ascii=False)};\n{MOLDURA}")
            r = after(jsx, cfg["log"], 1800)
            print(r)
            comp = cfg["nome"]
        else:
            r = subprocess.run([sys.executable, str(AQUI / "gerar_ae2.py"), str(b), "--item", nn, "--vertical"],
                               capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip()[-500:])
            r = after(ed / f"montar_{nn}_vertical.jsx", ed / f"log_{nn}_vertical.txt", 1800)
            print(r)
            aep, comp = ed / f"bloco_{nn}_vertical.aep", plano["nome"] + " (vertical)"
        if not r.startswith("OK"):
            sys.exit(1)
        if not a.sem_render:
            mp4 = saida_dir / f"bloco {int(nn)} - {a.modo}.mp4"
            t = time.time()
            print(renderizar(aep, comp, mp4, saida_dir / f"log_render_{a.modo}_{nn}.txt"), f"({time.time() - t:.0f} s)")
    finally:
        fcntl.flock(trava, fcntl.LOCK_UN)
        trava.close()


if __name__ == "__main__":
    main()
