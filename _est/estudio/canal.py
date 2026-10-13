"""Ponte entre o Estúdio e as pastas de um canal: acha o canal de um bloco e roda os scripts dele."""
import json
import subprocess
from pathlib import Path

from .motor_claude import canais


def canal_do_bloco(bloco):
    bloco = Path(bloco).resolve()
    for slug, c in canais().items():
        if str(bloco).startswith(str(Path(c["producoes"]).resolve()) + "/"):
            return slug, c
    raise SystemExit(f"{bloco} não está na pasta de produções de nenhum canal do canais.json")


def contexto(bloco):
    """{canal, video, bloco} para o registro de consumo."""
    bloco = Path(bloco).resolve()
    slug, c = canal_do_bloco(bloco)
    rel = bloco.relative_to(Path(c["producoes"]).resolve()).parts
    return {"canal": slug, "video": rel[0], "bloco": rel[-1] if len(rel) > 1 else ""}


def rodar_script(c, script, *args, timeout=7200, log=None):
    """Roda buscador_assets/scripts/<script> com o Python do canal, a partir da pasta do buscador
    (como a skill manda). Devolve (código, saída)."""
    cmd = [c["python"], str(Path(c["scripts"]) / script), *[str(a) for a in args]]
    r = subprocess.run(cmd, cwd=Path(c["scripts"]).parent, capture_output=True, text=True, timeout=timeout)
    saida = (r.stdout or "") + (r.stderr or "")
    if log:
        with open(log, "a") as f:
            f.write(f"\n$ {' '.join(cmd)}\n{saida}")
    return r.returncode, saida


def ler_json(caminho, padrao=None):
    try:
        return json.loads(Path(caminho).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def gravar_json(caminho, dados):
    caminho = Path(caminho)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1))
    tmp.replace(caminho)
