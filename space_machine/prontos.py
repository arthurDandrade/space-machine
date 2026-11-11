"""Vídeos prontos do canal: <canal>/videos/NN - Título.mp4, todos numa pasta só, numerados na ordem de postar.

Toda entrega de vídeo inteiro (rodar_video.entregar e final.py) termina aqui: o MP4 sai de <vídeo>/final/ e vai para
a pasta do canal, com a thumbnail do vídeo ao lado, no mesmo nome. Um vídeo tem UM arquivo aqui; entregar de novo
troca o arquivo (o anterior vai para o Lixo do Mac: limpeza.versao_anterior).

O número é do vídeo e não muda: é dado na primeira entrega, em sequência dentro do canal, e fica em
estudio_video.json › numero (junto de `pronto`, o nome do arquivo na pasta). Vídeo excluído leva o número com ele,
então restaurar não embaralha a ordem.
"""
import re
import shutil
from pathlib import Path

from .sistema import gravar_json, ler_json

PASTA = "videos"
CAPAS = (".png", ".jpg", ".jpeg", ".webp")
GUARDADO = "_pronto"      # dentro da pasta do vídeo na lixeira: o MP4 e a capa que estavam em <canal>/videos/


def pasta(vd):
    """<canal>/videos, a partir da pasta do vídeo (<canal>/producoes/<vídeo>)."""
    return Path(vd).parent.parent / PASTA


def _info(vd):
    return ler_json(Path(vd) / "estudio_video.json", {}) or {}


def anotar(vd, **campos):
    """Grava campos no estudio_video.json do vídeo (None tira o campo)."""
    info = _info(vd)
    for k, v in campos.items():
        if v is None:
            info.pop(k, None)
        else:
            info[k] = v
    gravar_json(Path(vd) / "estudio_video.json", info)


def arquivado(vd):
    """Quando o vídeo foi arquivado (gestao.arquivar_video: só a ficha ficou), ou ""."""
    return _info(vd).get("arquivado") or ""


def numero(vd, dar=True):
    """O número do vídeo no canal. Sem número ainda e dar=True: o próximo da sequência, já gravado."""
    vd = Path(vd)
    n = _info(vd).get("numero")
    if n or not dar:
        return n
    prod = vd.parent
    outros = [p for p in prod.iterdir() if p.is_dir()] + [p for p in (prod / "_lixeira").glob("*") if p.is_dir()]
    usados = [int(_info(p).get("numero") or 0) for p in outros]
    usados += [int(m.group(1)) for f in pasta(vd).glob("*") if (m := re.match(r"(\d+) - ", f.name))]
    n = max(usados, default=0) + 1
    anotar(vd, numero=n)
    return n


def nome(vd):
    """"07 - Título do vídeo": o nome do arquivo na pasta do canal, sem a extensão."""
    from .estado import titulo_video
    titulo = re.sub(r'[/:"\\]', "-", titulo_video(vd)).strip() or Path(vd).name
    return f"{numero(vd):02d} - {titulo}"


def atual(vd):
    """O MP4 pronto deste vídeo na pasta do canal, ou None."""
    n = _info(vd).get("pronto")
    f = pasta(vd) / n if n else None
    return f if f and f.is_file() else None


def _capas(mp4):
    return [f for ext in CAPAS if (f := Path(mp4).with_suffix(ext)).is_file()]


def capa(vd):
    """A thumbnail do vídeo ao lado do MP4 pronto, com o mesmo nome (é uma cópia: a que vale continua na pasta do
    vídeo). Sem MP4 pronto, não faz nada."""
    from . import capas
    mp4 = atual(vd)
    if not mp4:
        return None
    for f in _capas(mp4):
        f.unlink()
    t = capas.thumbnail(vd)
    if not t:
        return None
    destino = mp4.with_suffix(t.suffix.lower())
    shutil.copy2(t, destino)
    return destino


def guardar(vd, mp4):
    """O MP4 que acabou de ser entregue vai para a pasta do canal com o nome numerado. Devolve onde ficou."""
    from .limpeza import versao_anterior
    vd, mp4 = Path(vd), Path(mp4)
    destino = pasta(vd) / f"{nome(vd)}.mp4"
    destino.parent.mkdir(exist_ok=True)
    antigo = atual(vd)
    if antigo and antigo != mp4:
        for f in _capas(antigo):
            f.unlink()
        versao_anterior(antigo)
    if destino.exists() and destino != mp4:      # um arquivo com este nome que não era deste vídeo: vai para o Lixo
        versao_anterior(destino)
    if mp4 != destino:
        shutil.move(str(mp4), str(destino))
    anotar(vd, pronto=destino.name)
    capa(vd)
    return destino


def para_a_lixeira(vd, destino):
    """Vídeo excluído: o MP4 pronto e a capa saem da pasta do canal e vão junto, em <lixeira>/_pronto/.
    Chame antes de mover a pasta do vídeo (`destino` é para onde ela vai)."""
    mp4 = atual(vd)
    if not mp4:
        return []
    return [(f, Path(destino) / GUARDADO / f.name) for f in [mp4] + _capas(mp4)]


def da_lixeira(vd):
    """Vídeo restaurado: o que estava em <vídeo>/_pronto/ volta para a pasta do canal."""
    guardado = Path(vd) / GUARDADO
    if not guardado.is_dir():
        return
    pasta(vd).mkdir(exist_ok=True)
    for f in sorted(guardado.iterdir()):
        alvo = pasta(vd) / f.name
        if not alvo.exists():
            shutil.move(str(f), str(alvo))
    shutil.rmtree(guardado, ignore_errors=True)


def do_canal(c):
    """Os MP4 prontos do canal, na ordem do número: [{numero, nome, arquivo, tamanho}]."""
    p = Path(c["raiz"]) / PASTA
    out = []
    for f in sorted(p.glob("*.mp4")) if p.is_dir() else []:
        m = re.match(r"(\d+) - ", f.name)
        out.append({"numero": int(m.group(1)) if m else 0, "nome": f.stem, "arquivo": str(f), "tamanho": f.stat().st_size})
    return sorted(out, key=lambda v: (v["numero"], v["nome"]))
