"""Reels 9:16 de um bloco: o mesmo plano do bloco montado de novo em 1080x1920 e renderizado.

  python -m space_machine reels <pasta do bloco>

gerar_ae2.py --vertical monta o blocos/NN/edicao/bloco_NN_vertical.aep (cards em coluna ou grade, card único quadrado
na largura da tela, rótulo e citação embaixo do card, frase longa em linhas, sem o botão de inscrição do CTA) e o
After renderiza <vídeo>/reels/bloco N.mp4. Escolhido em 2026-10-17 entre dois testes: o bloco 16:9 inteiro numa
moldura vertical deixava a imagem pequena. O Reels anterior vai para reels/anteriores/.
Usa a trava do After (<dados>/trava_after) como os blocos e o vídeo final. O painel lança solto (lancar) e acompanha
por <vídeo>/reels/estado_NN.json.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import estado
from . import plataforma
from .canal import canal_do_bloco
from .final import _after, _guardar_anterior
from .sistema import DADOS, MOTOR, ambiente_motor, gravar_json, ler_json


def _pasta(b):
    return Path(b).parent.parent / "reels"


def mp4(b):
    return _pasta(b) / f"bloco {int(Path(b).name)}.mp4"


def ler_estado(b):
    pasta, nn = _pasta(b), Path(b).name
    est = ler_json(pasta / f"estado_{nn}.json", {}) or {}
    pid = pasta / f"pid_{nn}"
    est["rodando"] = pid.exists() and estado._vivo(pid.read_text().strip())
    if est.get("status") == "rodando" and pid.exists() and not est["rodando"]:
        est.update(status="erro", etapa="parou no meio (processo encerrado)")
    return est


def _marcar(b, **campos):
    arq = _pasta(b) / f"estado_{Path(b).name}.json"
    est = ler_json(arq, {}) or {}
    est.update(campos, atualizado=time.strftime("%Y-%m-%d %H:%M:%S"))
    gravar_json(arq, est)


def fazer(b):
    b = Path(b).resolve()
    nn = b.name
    _, c = canal_do_bloco(b)
    ed = b / "edicao"
    pasta = _pasta(b)
    pasta.mkdir(exist_ok=True)
    plano = ler_json(ed / f"plano_edicao_{nn}.json")
    if not plano:
        _marcar(b, status="erro", etapa="o bloco ainda não tem plano de edição (rode até a edição antes)")
        return 1
    _marcar(b, status="rodando", etapa="montando o plano na vertical", inicio=time.strftime("%Y-%m-%d %H:%M:%S"),
            fim="", erro="")
    r = subprocess.run([sys.executable, str(MOTOR / "edicao_ae" / "gerar_ae2.py"), str(b), "--item", nn, "--vertical"],
                       capture_output=True, text=True, env=ambiente_motor(c), cwd=MOTOR / "edicao_ae")
    if r.returncode:
        erro = (r.stderr.strip().splitlines() or ["?"])[-1]
        _marcar(b, status="erro", etapa="a montagem deu erro antes de abrir o After", erro=erro[:300])
        return 1
    trava = open(DADOS / "trava_after", "w")
    _marcar(b, etapa="esperando a vez no After")
    plataforma.travar(trava)
    try:
        _marcar(b, etapa="montando no After")
        r = _after(ed / f"montar_{nn}_vertical.jsx", ed / f"log_{nn}_vertical.txt", 1800)
        if "OK comp=" not in r:
            _marcar(b, status="erro", etapa="o After não montou o projeto", erro=r[-300:] or "sem resposta do After "
                    "(pode estar travado num diálogo: olhar a tela)", fim=time.strftime("%Y-%m-%d %H:%M:%S"))
            return 1
        saida = mp4(b)
        _guardar_anterior(saida)
        _marcar(b, etapa="renderizando (demora mais ou menos o tempo do bloco)")
        rlog = pasta / f"log_render_{nn}.txt"
        cfg = json.dumps({"aep": str(ed / f"bloco_{nn}_vertical.aep"), "comp": plano["nome"] + " (vertical)",
                          "saida": str(saida), "log": str(rlog)}, ensure_ascii=False)
        (pasta / f"render_{nn}.jsx").write_text(f"var RENDER = {cfg};\n"
                                                + (MOTOR / "edicao_ae" / "renderizar.jsx").read_text())
        r = _after(pasta / f"render_{nn}.jsx", rlog, 3600)
        if not r.startswith("OK"):
            _marcar(b, status="erro", etapa="o After não renderizou", erro=r or "sem resposta do After em 1 h",
                    fim=time.strftime("%Y-%m-%d %H:%M:%S"))
            return 1
    finally:
        plataforma.destravar(trava)
        trava.close()
    _marcar(b, status="ok", etapa="pronto", mp4=str(saida), fim=time.strftime("%Y-%m-%d %H:%M:%S"))
    return 0


def lancar(b):
    """Lança o `reels` solto do painel (como o vídeo final): fechar o painel não para nada. Devolve o pid."""
    b = Path(b)
    pasta, nn = _pasta(b), b.name
    pasta.mkdir(exist_ok=True)
    cmd = [sys.executable, "-m", "space_machine", "reels", str(b)]
    _marcar(b, status="rodando", etapa="começando", erro="")
    pid = plataforma.lancar_solto(cmd, pasta / f"log_reels_{nn}.txt", Path(__file__).resolve().parent.parent)
    (pasta / f"pid_{nn}").write_text(pid)
    return pid


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m space_machine reels", description=__doc__.split("\n")[0])
    ap.add_argument("bloco", help="pasta do bloco")
    a = ap.parse_args(argv)
    sys.exit(fazer(a.bloco))


if __name__ == "__main__":
    main()
