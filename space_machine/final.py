"""Vídeo final: junta os blocos entregues de um vídeo num projeto do After e, se pedir, renderiza o MP4.

  python -m space_machine final <pasta do vídeo> [--render]

Monta <vídeo>/final/final.aep: os blocos entregues em sequência numa comp só, com a camada de ajuste de ruído do vídeo final (config video_final.ruido: 6% por padrão, como o primeiro vídeo final montado à mão
em 2026-10-13; 0 = sem). Com --render, renderiza <vídeo>/final/<título>.mp4.
Desde 2026-10-16 cada bloco entra pelo projeto dele (blocos/NN/edicao/bloco_NN_v2.aep, importado inteiro): o vídeo
final sai de um render só, sem comprimir de novo os MP4s dos blocos, e o que você ajustar no .aep de um bloco entra
no final. O edicao/bloco N.mp4 continua marcando o bloco como entregue (é a prévia de rascunho, em meia resolução) e
só entra na montagem quando o bloco não tem .aep.
O After roda um script de cada vez: usa a mesma trava dos blocos (<dados>/trava_after) e, como a montagem dos blocos,
fecha o projeto que estiver aberto sem salvar. O final.aep (e o MP4) de uma montagem anterior vai para final/anteriores/. O painel lança este comando solto (lancar) e acompanha por
<vídeo>/final/estado.json.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from . import estado
from . import plataforma
from .sistema import DADOS, MOTOR, config, gravar_json, ler_json

MONTAR = r"""
(function () {
    var log = [];
    try {
        app.beginSuppressDialogs();
        if (app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        app.newProject();
        var p = app.project, itens = [], total = 0, nAep = 0;
        function acharComp(pasta, nome) {
            for (var j = 1; j <= pasta.numItems; j++) {
                var x = pasta.item(j);
                if (x instanceof CompItem && x.name === nome) return x;
                if (x instanceof FolderItem) { var y = acharComp(x, nome); if (y) return y; }
            }
            return null;
        }
        for (var i = 0; i < CFG.blocos.length; i++) {
            var b = CFG.blocos[i], f = new File(b.aep || b.mp4);
            if (!f.exists) throw new Error("falta " + f.fsName);
            var it = p.importFile(new ImportOptions(f));
            if (b.aep) {
                it.name = b.nome;
                var c = acharComp(it, b.comp);
                if (!c) throw new Error("comp \"" + b.comp + "\" não está em " + f.fsName);
                it = c;
                nAep++;
            }
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
        log.push("OK " + itens.length + " blocos (" + nAep + " pelo .aep), " + total.toFixed(2) + " s");
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


def fontes(vd):
    """O que entra na montagem por bloco entregue: o projeto do bloco (aep + nome da comp) ou, sem ele, o MP4."""
    out = []
    for mp4 in entregues(vd):
        nn = f"{_numero(mp4):02d}"
        ed = Path(vd) / "blocos" / nn / "edicao"
        aep, plano = ed / f"bloco_{nn}_v2.aep", ed / f"plano_edicao_{nn}.json"
        comp = (ler_json(plano, {}) or {}).get("nome") if plano.exists() else None
        out.append({"aep": str(aep), "comp": comp, "nome": f"bloco {int(nn)}"} if aep.exists() and comp
                   else {"mp4": str(mp4)})
    return out


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
    """Roda um .jsx no After e espera o log que ele escreve (quem pede não recebe resposta útil do After)."""
    app = config().get("after_app", "Adobe After Effects 2026")
    Path(log).unlink(missing_ok=True)
    plataforma.rodar_jsx(app, script, espera_s)
    return plataforma.esperar_log(log, espera_s)


def _guardar_anterior(arq):
    """Projeto ou MP4 de uma montagem anterior (que você pode ter editado) vai para final/anteriores/, nunca é
    sobrescrito."""
    arq = Path(arq)
    if arq.exists():
        guarda = arq.parent / "anteriores"
        guarda.mkdir(exist_ok=True)
        arq.rename(guarda / f"{arq.stem}_{time.strftime('%Y%m%d-%H%M%S', time.localtime(arq.stat().st_mtime))}{arq.suffix}")


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
    cfg = {"blocos": fontes(vd), "comp": f"{titulo} - final", "aep": str(aep), "log": str(log),
           "ruido": float((config().get("video_final") or {}).get("ruido", 6))}
    (fim_dir / "montar_final.jsx").write_text(f"var CFG = {json.dumps(cfg, ensure_ascii=False)};\n{MONTAR}")
    trava = open(DADOS / "trava_after", "w")
    plataforma.travar(trava)
    try:
        _guardar_anterior(aep)
        _marcar(vd, etapa=f"juntando {len(blocos)} blocos no After")
        r = _after(fim_dir / "montar_final.jsx", log, 1800)
        if not r.startswith("OK"):
            _marcar(vd, status="erro", etapa="o After não montou o projeto", erro=r or "sem resposta do After "
                    "(pode estar travado num diálogo: olhar a tela)", fim=time.strftime("%Y-%m-%d %H:%M:%S"))
            return 1
        _marcar(vd, etapa=r, aep=str(aep))
        if render:
            _guardar_anterior(mp4)
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
        plataforma.destravar(trava)
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
    pid = plataforma.lancar_solto(cmd, log, Path(__file__).resolve().parent.parent)
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
