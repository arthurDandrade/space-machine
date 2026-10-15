"""Vídeo final: junta os blocos entregues de um vídeo num projeto do After e, se pedir, renderiza o MP4.

  python -m space_machine final <pasta do vídeo> [--render]

Monta <vídeo>/final/final.aep: os blocos entregues (edicao/bloco N.mp4) em sequência numa comp só, com a camada de
ajuste de ruído do vídeo final (config video_final.ruido: 6% por padrão, como o primeiro vídeo final montado à mão
em 2026-10-13; 0 = sem). Com --render, renderiza <vídeo>/final/<título>.mp4.
O After roda um script de cada vez: usa a mesma trava dos blocos (<dados>/trava_after) e, como a montagem dos blocos,
fecha o projeto que estiver aberto sem salvar. O painel lança este comando solto (lancar) e acompanha por
<vídeo>/final/estado.json.
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

from . import estado
from .sistema import DADOS, MOTOR, config, gravar_json, ler_json

MONTAR = r"""
(function () {
    var log = [];
    try {
        app.beginSuppressDialogs();
        if (app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        app.newProject();
        var p = app.project, itens = [], total = 0;
        for (var i = 0; i < CFG.blocos.length; i++) {
            var f = new File(CFG.blocos[i]);
            if (!f.exists) throw new Error("falta " + f.fsName);
            var it = p.importFile(new ImportOptions(f));
            itens.push(it);
            total += it.duration;
        }
        var W = itens[0].width, H = itens[0].height, fps = itens[0].frameRate;
        var comp = p.items.addComp(CFG.comp, W, H, 1, total, fps);
        var t = 0;
        for (var k = 0; k < itens.length; k++) {
            var L = comp.layers.add(itens[k]);
            L.startTime = t;
            L.moveToEnd();
            t += itens[k].duration;
        }
        if (CFG.ruido > 0) {
            var aj = comp.layers.addSolid([1, 1, 1], "Noise " + CFG.ruido + "%", W, H, 1, total);
            aj.adjustmentLayer = true;
            aj.moveToBeginning();
            aj.property("ADBE Effect Parade").addProperty("ADBE Noise").property(1).setValue(CFG.ruido);
        }
        comp.openInViewer();
        p.save(new File(CFG.aep));
        log.push("OK " + itens.length + " blocos, " + total.toFixed(2) + " s");
    } catch (e) { log.push("ERRO " + e.toString() + " linha " + e.line); }
    app.endSuppressDialogs(false);
    var lf = new File(CFG.log); lf.encoding = "UTF-8"; lf.open("w"); lf.write(log.join("\n")); lf.close();
})();
"""


def _numero(f):
    m = re.search(r"(\d+)", f.stem)
    return int(m.group(1)) if m else 0


def entregues(vd):
    """Blocos entregues, na ordem (bloco 0 = cold open)."""
    return sorted(Path(vd, "edicao").glob("bloco *.mp4"), key=_numero)


def ler_estado(vd):
    est = ler_json(Path(vd) / "final" / "estado.json", {}) or {}
    pid = Path(vd) / "final" / "pid"
    est["rodando"] = pid.exists() and estado._vivo(pid.read_text().strip())
    if est.get("status") == "rodando" and pid.exists() and not est["rodando"]:
        est.update(status="erro", etapa="parou no meio (processo encerrado)")
    return est


def _marcar(vd, **campos):
    arq = Path(vd) / "final" / "estado.json"
    est = ler_json(arq, {}) or {}
    est.update(campos, atualizado=time.strftime("%Y-%m-%d %H:%M:%S"))
    gravar_json(arq, est)


def _after(script, log, espera_s):
    """Roda um .jsx no After e espera o log que ele escreve (o osascript pode estourar o tempo antes)."""
    app = config().get("after_app", "Adobe After Effects 2026")
    Path(log).unlink(missing_ok=True)
    subprocess.run(["osascript", "-e", f"with timeout of {espera_s} seconds",
                    "-e", f'tell application "{app}" to DoScriptFile "{script}"', "-e", "end timeout"],
                   capture_output=True, timeout=espera_s + 60)
    for _ in range(espera_s // 3):
        if Path(log).exists():
            return Path(log).read_text(errors="replace").strip()
        time.sleep(3)
    return ""


def montar(vd, render=False):
    vd = Path(vd)
    fim_dir = vd / "final"
    fim_dir.mkdir(exist_ok=True)
    blocos = entregues(vd)
    titulo = estado.titulo_video(vd)
    total = len([b for b in (vd / "blocos").glob("*") if b.is_dir() and b.name.isdigit()]) if (vd / "blocos").is_dir() else 0
    faltam = sorted({b.name for b in (vd / "blocos").glob("*") if b.is_dir() and b.name.isdigit()}
                    - {f"{_numero(f):02d}" for f in blocos})
    _marcar(vd, status="rodando", etapa="esperando a vez no After", inicio=time.strftime("%Y-%m-%d %H:%M:%S"),
            fim="", render=render, blocos=len(blocos), total=total, faltam=faltam, erro="")
    if not blocos:
        _marcar(vd, status="erro", etapa="nenhum bloco entregue ainda", fim=time.strftime("%Y-%m-%d %H:%M:%S"))
        return 1
    aep, log = fim_dir / "final.aep", fim_dir / "log_montar.txt"
    nome_mp4 = re.sub(r'[/:"\\]', "-", titulo).strip() or vd.name
    mp4 = fim_dir / f"{nome_mp4}.mp4"
    cfg = {"blocos": [str(b) for b in blocos], "comp": f"{titulo} - final", "aep": str(aep), "log": str(log),
           "ruido": float((config().get("video_final") or {}).get("ruido", 6))}
    (fim_dir / "montar_final.jsx").write_text(f"var CFG = {json.dumps(cfg, ensure_ascii=False)};\n{MONTAR}")
    trava = open(DADOS / "trava_after", "w")
    fcntl.flock(trava, fcntl.LOCK_EX)
    try:
        _marcar(vd, etapa=f"juntando {len(blocos)} blocos no After")
        r = _after(fim_dir / "montar_final.jsx", log, 1800)
        if not r.startswith("OK"):
            _marcar(vd, status="erro", etapa="o After não montou o projeto", erro=r or "sem resposta do After "
                    "(pode estar travado num diálogo: olhar a tela)", fim=time.strftime("%Y-%m-%d %H:%M:%S"))
            return 1
        _marcar(vd, etapa=r, aep=str(aep))
        if render:
            _marcar(vd, etapa="renderizando o vídeo final (demora: tempo parecido com a duração do vídeo)")
            rlog = fim_dir / "log_render.txt"
            prefixo = json.dumps({"aep": str(aep), "comp": cfg["comp"], "saida": str(mp4), "log": str(rlog)},
                                 ensure_ascii=False)
            (fim_dir / "render_final.jsx").write_text(f"var RENDER = {prefixo};\n"
                                                      + (MOTOR / "edicao_ae" / "renderizar.jsx").read_text())
            r = _after(fim_dir / "render_final.jsx", rlog, 4 * 3600)
            if not r.startswith("OK"):
                _marcar(vd, status="erro", etapa="o After não renderizou", erro=r or "sem resposta do After em 4 h",
                        fim=time.strftime("%Y-%m-%d %H:%M:%S"))
                return 1
            _marcar(vd, mp4=str(mp4))
    finally:
        fcntl.flock(trava, fcntl.LOCK_UN)
        trava.close()
    _marcar(vd, status="ok", etapa="pronto", fim=time.strftime("%Y-%m-%d %H:%M:%S"))
    return 0


def lancar(vd, render=False):
    """Lança o `final` solto do painel (como as rodadas): fechar o painel não para nada. Devolve o pid."""
    vd = Path(vd)
    (vd / "final").mkdir(exist_ok=True)
    log = vd / "final" / "log_final.txt"
    cmd = [sys.executable, "-m", "space_machine", "final", str(vd)] + (["--render"] if render else [])
    _marcar(vd, status="rodando", etapa="começando", render=render, erro="")
    sh = subprocess.run(["/bin/sh", "-c", '"$@" </dev/null >>"$LOG_FINAL" 2>&1 & echo $!', "sh", *cmd],
                        cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True,
                        start_new_session=True, env={**os.environ, "PYTHONUNBUFFERED": "1", "LOG_FINAL": str(log)})
    pid = sh.stdout.strip()
    (vd / "final" / "pid").write_text(pid)
    return pid


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m space_machine final", description=__doc__.split("\n")[0])
    ap.add_argument("video", help="pasta do vídeo")
    ap.add_argument("--render", action="store_true", help="também renderiza o MP4 final")
    a = ap.parse_args(argv)
    sys.exit(montar(Path(a.video).resolve(), a.render))


if __name__ == "__main__":
    main()
