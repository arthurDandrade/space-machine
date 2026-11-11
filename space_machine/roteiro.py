"""Escrever o roteiro de um vídeo novo em segundo plano, com o painel mostrando o que está acontecendo.

Antes (até 2026-11-11) o botão "Escrever o roteiro e criar o vídeo" segurava a tela de vídeo novo por minutos, com uma
frase pequena ao lado do botão: não dava para saber se o Claude estava mesmo escrevendo, e sair da tela perdia o
aviso. Agora o vídeo nasce na hora, ainda sem capítulos, e o roteiro é escrito por um processo solto do painel (como
a thumbnail e o vídeo final: fechar o painel não para nada):

  comecar(c, título, instruções)   cria o vídeo vazio (pasta + ficha), guarda o pedido e lança o processo
  escrever(vídeo)                  o processo: pede o roteiro ao Claude (gestao.escrever_roteiro), divide em capítulos
                                   (gestao.escrever_blocos) e guarda o roteiro na ficha
  ler_estado(vídeo)                <vídeo>/_estudio/roteiro.json: status (rodando, ok, erro, parado), em que passo
                                   está, desde quando, e o motivo quando para
  parar(vídeo)                     botão Parar

O painel mostra isso na página do vídeo (painel "Acontecendo agora"), na barra lateral e no "Rodando agora" do canal;
se der errado, o vídeo aparece em "Esperando você" com o motivo e o botão de tentar de novo.

  python -m space_machine roteiro <pasta do vídeo>
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import estado, fichas, gestao
from .sistema import canais, gravar_json, ler_json


def _pasta(vd):
    return Path(vd) / "_estudio"


def marcar(vd, **campos):
    arq = _pasta(vd) / "roteiro.json"
    est = ler_json(arq, {}) or {}
    est.update(campos, atualizado=time.strftime("%Y-%m-%d %H:%M:%S"))
    gravar_json(arq, est)
    return est


def ler_estado(vd):
    """{} se este vídeo nunca teve roteiro pedido ao Claude por aqui."""
    est = ler_json(_pasta(vd) / "roteiro.json", {}) or {}
    if not est:
        return {}
    pid = _pasta(vd) / "roteiro.pid"
    est["rodando"] = pid.exists() and estado._vivo(pid.read_text().strip())
    if est.get("status") == "rodando" and not est["rodando"]:
        est.update(status="erro", erro="o processo que escrevia o roteiro foi encerrado no meio")
    return est


def comecar(c, titulo, obs=""):
    """Cria o vídeo (ainda sem capítulos) e lança a escrita do roteiro. Devolve o slug; ValueError com o motivo."""
    if not titulo.strip():
        raise ValueError("Dê um título ao vídeo.")
    slug = gestao.slug_video(titulo)
    if not slug:
        raise ValueError("O título precisa ter letras ou números.")
    vd = Path(c["producoes"]) / slug
    if vd.exists():
        raise ValueError(f"Já existe um vídeo com essa pasta ({slug}).")
    if fichas.existe(vd):
        raise ValueError(f"Já existe um vídeo arquivado com esse título ({slug}). Use outro título ou exclua o arquivado.")
    if not gestao._modelo_roteiro(c):
        raise ValueError("Este formato não escreve roteiro sozinho: cole o roteiro.")
    (vd / "edicao").mkdir(parents=True)
    gravar_json(vd / "estudio_video.json", {"titulo": titulo.strip()})
    fichas.criar(vd, titulo)
    lancar(vd, obs)
    return slug


def lancar(vd, obs=None):
    """Lança (ou relança) a escrita. obs=None repete as instruções da última vez."""
    vd = Path(vd)
    _pasta(vd).mkdir(parents=True, exist_ok=True)
    if obs is None:
        obs = (ler_json(_pasta(vd) / "roteiro.json", {}) or {}).get("obs", "")
    obs = (obs or "").strip()
    fichas.anotar(vd, instrucoes_roteiro=obs or None)
    marcar(vd, status="rodando", etapa="começando", inicio=time.strftime("%Y-%m-%d %H:%M:%S"), fim="", erro="", obs=obs)
    cmd = [sys.executable, "-m", "space_machine", "roteiro", str(vd)]
    sh = subprocess.run(["/bin/sh", "-c", '"$@" </dev/null >>"$LOG_ROTEIRO" 2>&1 & echo $!', "sh", *cmd],
                        cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True,
                        start_new_session=True,
                        env={**os.environ, "PYTHONUNBUFFERED": "1", "LOG_ROTEIRO": str(_pasta(vd) / "log_roteiro.txt")})
    pid = sh.stdout.strip()
    (_pasta(vd) / "roteiro.pid").write_text(pid)
    return pid


def parar(vd):
    vd = Path(vd)
    pid = _pasta(vd) / "roteiro.pid"
    if pid.exists():
        try:        # o processo é filho de um `sh` líder de sessão: o grupo é o do sh (como em fila.parar_rodada)
            os.killpg(os.getpgid(int(pid.read_text().strip())), signal.SIGTERM)
        except (ProcessLookupError, ValueError, PermissionError):
            pass
        pid.unlink(missing_ok=True)
    if (ler_json(_pasta(vd) / "roteiro.json", {}) or {}).get("status") == "rodando":
        marcar(vd, status="parado", erro="parado no painel", fim=time.strftime("%Y-%m-%d %H:%M:%S"))


def escrever(vd):
    """O trabalho em si (roda no processo solto). Devolve 0 se o vídeo ficou com roteiro e capítulos."""
    from .motor_claude import ErroClaude
    vd = Path(vd).resolve()
    c = canais().get(vd.parent.parent.name)
    if not c:
        marcar(vd, status="erro", erro="não achei o canal deste vídeo")
        return 1
    obs = (ler_json(_pasta(vd) / "roteiro.json", {}) or {}).get("obs", "")
    titulo = estado.titulo_video(vd)
    try:
        marcar(vd, status="rodando", etapa="o Claude está escrevendo a primeira versão")
        texto = gestao.escrever_roteiro(c, titulo, obs, avisar=lambda passo: marcar(vd, etapa=passo))
        cold_open, partes = gestao.dividir_roteiro(texto)
        if not partes:
            raise ValueError("o roteiro veio sem nenhum tópico (\"# Nome do tópico\")")
        marcar(vd, etapa=f"dividindo em {len(partes)} capítulos")
        fichas.roteiro(vd).write_text(texto.strip() + "\n")
        gestao.escrever_blocos(c, vd, cold_open, partes)
    except (ValueError, ErroClaude, OSError) as e:
        marcar(vd, status="erro", erro=str(e)[:600], fim=time.strftime("%Y-%m-%d %H:%M:%S"))
        return 1
    palavras = len(texto.split())
    marcar(vd, status="ok", etapa=f"{len(partes)} capítulos, {palavras} palavras", erro="",
           fim=time.strftime("%Y-%m-%d %H:%M:%S"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m space_machine roteiro", description=__doc__.split("\n")[0])
    ap.add_argument("video", help="pasta do vídeo (criado sem capítulos por comecar)")
    a = ap.parse_args(argv)
    sys.exit(escrever(a.video))


if __name__ == "__main__":
    main()
