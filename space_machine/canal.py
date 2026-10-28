"""Ponte entre o orquestrador e as pastas de um canal: acha o canal de um bloco e roda o motor para ele."""
import subprocess
from pathlib import Path

from .sistema import ambiente_motor, canais, gravar_json, ler_json  # noqa: F401  (ler/gravar: usados por outros módulos)


def canal_do_bloco(bloco):
    bloco = Path(bloco).resolve()
    for slug, c in canais().items():
        prod = Path(c["producoes"]).resolve()
        if bloco != prod and bloco.is_relative_to(prod):     # não por texto: no Windows a barra é a outra
            return slug, c
    raise SystemExit(f"{bloco} não está na pasta de produções de nenhum canal (<dados>/canais/<canal>/producoes)")


def contexto(bloco):
    """{canal, video, bloco} para o registro de consumo."""
    bloco = Path(bloco).resolve()
    slug, c = canal_do_bloco(bloco)
    rel = bloco.relative_to(Path(c["producoes"]).resolve()).parts
    return {"canal": slug, "video": rel[0], "bloco": rel[-1] if len(rel) > 1 else ""}


def rodar_script(c, script, *args, timeout=7200, log=None):
    """Roda motor/busca/scripts/<script> com o Python do Space Machine, de dentro de motor/busca, com o canal no
    ambiente (SM_CANAL/SM_DADOS: ver motor/caminhos.py). Devolve (código, saída)."""
    cmd = [c["python"], str(Path(c["scripts"]) / script), *[str(a) for a in args]]
    r = subprocess.run(cmd, cwd=Path(c["scripts"]).parent, capture_output=True, text=True, timeout=timeout,
                       env=ambiente_motor(c))
    saida = (r.stdout or "") + (r.stderr or "")
    if log:
        with open(log, "a") as f:
            f.write(f"\n$ {' '.join(cmd)}\n{saida}")
    return r.returncode, saida
