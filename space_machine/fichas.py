"""A ficha de cada vídeo: <canal>/fichas/<vídeo>/, o registro do canal que não depende da pasta de produção.

  ficha.json            título, número (ordem de postar), nome do MP4 pronto, arquivado, duração e o que você
                        preenche na aba Publicação: status, título de publicação, descrição, tags, data, notas, link
  thumbnail.<ext>       a thumbnail do vídeo (+ thumbnail.json: nome original, tamanho, quando foi enviada)
  roteiro_completo.txt  o roteiro inteiro, como foi colado ou escrito

Antes (até 2026-11-11) isso ficava em três lugares: o estudio_video.json e a thumbnail dentro da pasta de produção,
e a publicação no sqlite, numa tabela por (canal, slug) que não ia junto quando a pasta do canal era copiada e ficava
órfã quando o vídeo era excluído. Agora o quadro, o calendário e a lista leem daqui, e a pasta de produção
(<canal>/producoes/<vídeo>/) guarda só o que é da produção: blocos, renders e o estudio_video.json com o título e o
fluxo. Arquivar um vídeo é mandar a pasta de produção embora; a ficha fica.

Vídeo de antes ganha a ficha sozinho na primeira vez que é lido (`garantir`): a thumbnail e o roteiro mudam de
pasta e a publicação é copiada do sqlite (a tabela videos_gestao fica lá, sem uso).
"""
import shutil
import sqlite3
import threading
import time
from pathlib import Path

from .sistema import gravar_json, ler_json

PASTA = "fichas"
GUARDADA = "_ficha"       # dentro da pasta do vídeo na lixeira: a ficha que estava em <canal>/fichas/<vídeo>/
PUBLICACAO = ("status", "titulo_pub", "descricao", "tags", "data_pub", "notas", "link", "atualizado")
DA_PRODUCAO = ("titulo", "fluxo")                     # o que continua no estudio_video.json da pasta de produção
ARQUIVOS = ("roteiro_completo.txt", "thumbnail.json", "thumbnail.png", "thumbnail.jpg", "thumbnail.jpeg", "thumbnail.webp")
_trava = threading.Lock()


def _pasta(vd):
    vd = Path(vd)
    return vd.parent.parent / PASTA / vd.name


def pasta(vd):
    """<canal>/fichas/<vídeo>/, a partir da pasta de produção do vídeo (que pode nem existir mais)."""
    garantir(vd)
    return _pasta(vd)


def existe(vd):
    return (_pasta(vd) / "ficha.json").is_file()


def ler(vd):
    garantir(vd)
    return ler_json(_pasta(vd) / "ficha.json", {}) or {}


def anotar(vd, **campos):
    """Grava campos na ficha do vídeo (None tira o campo)."""
    garantir(vd)
    with _trava:
        ficha = ler_json(_pasta(vd) / "ficha.json", {}) or {}
        for k, v in campos.items():
            if v is None:
                ficha.pop(k, None)
            else:
                ficha[k] = v
        gravar_json(_pasta(vd) / "ficha.json", ficha)
    return ficha


def roteiro(vd):
    """Onde fica o roteiro completo do vídeo (o arquivo pode não existir)."""
    return pasta(vd) / "roteiro_completo.txt"


def criar(vd, titulo, roteiro_texto=""):
    """A ficha de um vídeo novo."""
    p = _pasta(vd)
    p.mkdir(parents=True, exist_ok=True)
    if roteiro_texto.strip():
        (p / "roteiro_completo.txt").write_text(roteiro_texto.strip() + "\n")
    gravar_json(p / "ficha.json", {"titulo": titulo.strip(), "criado": time.strftime("%Y-%m-%d %H:%M")})


def so_ficha(c):
    """Os vídeos do canal que só têm ficha (arquivados: a pasta de produção não existe mais)."""
    raiz, prod = Path(c["raiz"]) / PASTA, Path(c["producoes"])
    return [prod / p.name for p in sorted(raiz.iterdir()) if (p / "ficha.json").is_file() and not (prod / p.name).is_dir()] \
        if raiz.is_dir() else []


def _publicacao_antiga(canal, slug):
    """O que estava no sqlite (tabela videos_gestao), para a ficha de um vídeo de antes."""
    from .motor_claude import _banco
    try:
        con = _banco()
        lin = con.execute(f"select {', '.join(PUBLICACAO)} from videos_gestao where canal=? and slug=?",
                          (canal, slug)).fetchone()
        con.close()
    except sqlite3.Error:
        return {}
    return {k: v for k, v in zip(PUBLICACAO, lin or ()) if v}


def garantir(vd):
    """Vídeo de antes das fichas: monta a ficha a partir do que estava na pasta de produção e no sqlite.
    Não faz nada se a ficha já existe ou se não há pasta de produção."""
    vd = Path(vd)
    p = _pasta(vd)
    if (p / "ficha.json").is_file() or not vd.is_dir() or vd.parent.name != "producoes":
        return
    from .estado import titulo_video
    with _trava:
        if (p / "ficha.json").is_file():
            return
        p.mkdir(parents=True, exist_ok=True)
        ev = ler_json(vd / "estudio_video.json", {}) or {}
        ficha = {"titulo": titulo_video(vd), **{k: v for k, v in ev.items() if k not in DA_PRODUCAO},
                 **_publicacao_antiga(vd.parent.parent.name, vd.name)}
        for nome in ARQUIVOS:
            try:
                if (vd / nome).is_file() and not (p / nome).exists():
                    shutil.move(str(vd / nome), str(p / nome))
            except OSError:
                pass            # outro processo levou no mesmo instante: já está lá
        if any(k not in DA_PRODUCAO for k in ev):
            gravar_json(vd / "estudio_video.json", {k: v for k, v in ev.items() if k in DA_PRODUCAO})
        gravar_json(p / "ficha.json", ficha)       # por último: se parar no meio, a próxima leitura termina


def para_a_lixeira(vd, destino):
    """Vídeo excluído: a ficha vai junto, em <lixeira>/_ficha/. Chame depois de mover a pasta de produção."""
    p = _pasta(vd)
    if p.is_dir():
        Path(destino).mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(Path(destino) / GUARDADA))


def da_lixeira(vd):
    """Vídeo restaurado: a ficha que estava em <vídeo>/_ficha/ volta para <canal>/fichas/<vídeo>/."""
    guardada, p = Path(vd) / GUARDADA, _pasta(vd)
    if guardada.is_dir() and not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(guardada), str(p))
