"""Fila de produção de um vídeo: roda todos os blocos ainda não entregues, no máximo N ao mesmo tempo.

  python -m estudio fila <pasta do vídeo> [--max 3]

O painel (botão "Produzir todos" na página do vídeo) lança este processo solto, como as rodadas.
Regras:
- conta no limite também os blocos que já estavam rodando (iniciados à mão);
- bloco "parado" (esperando o Arthur: conferir, decisão, erro) não entra: precisa de gente;
- cada bloco é lançado no máximo uma vez por fila (se parar, fica para o Arthur);
- parado por limite/erro passageiro do Claude volta para a fila (não precisa de gente);
- "limite de uso" do Claude → a fila pausa, testa a cada 10 min e continua sozinha quando liberar;
- estado em <vídeo>/_estudio/fila.json; "Parar fila" só impede novos lançamentos (os que rodam continuam).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import estado
from .motor_claude import CHECAGEM, RAIZ, ErroClaude, checar_claude, config as motor_cfg, eh_limite

INTERVALO_S = 15
ESPERA_LIMITE_S = 600


def _retentavel(parado):
    """Parou por limite ou erro passageiro do Claude (vale tentar de novo), não por decisão do Arthur."""
    m = str(parado.get("motivo", ""))
    # "busca falhou"/"erro inesperado" = erro de programa ou de rede (ex.: vídeo gigante do Archive derrubava
    # a busca, 2026-10-12): vale uma nova tentativa por fila depois da correção
    # "assets sem arquivo": desde o resgate automático (2026-10-12) a nova rodada resolve sozinha
    return (eh_limite(m) or m.startswith(("erro do Claude", "busca falhou", "erro inesperado", "assets sem arquivo"))
            or parado.get("etapa") == "checagem do Claude")


def lancar_rodada(b, de="", ate="", obs=""):
    """Lança `python -m estudio rodar` SOLTO (adotado pelo launchd, stdin em /dev/null). Devolve o pid.

    Filha do painel, a rodada morria quando o terminal do painel era fechado (bloco 01, 2026-10-11)."""
    from .rodar import ETAPAS
    b = Path(b)
    cmd = [sys.executable, "-m", "estudio", "rodar", str(b)]
    if de in ETAPAS:
        cmd += ["--de", de]
    if ate in ETAPAS:
        cmd += ["--ate", ate]
    if obs.strip():
        cmd += ["--obs", obs.strip()]
    (b / "_estudio").mkdir(exist_ok=True)
    log = b / "_estudio" / "log_rodar.txt"
    with open(log, "a") as f:
        f.write(f"\n===== {estado.quando(time.time())} · {' '.join(cmd[3:])}\n")
    sh = subprocess.run(["/bin/sh", "-c", '"$@" </dev/null >>"$LOG_RODAR" 2>&1 & echo $!', "sh", *cmd],
                        cwd=RAIZ, capture_output=True, text=True, start_new_session=True,
                        env={**os.environ, "PYTHONUNBUFFERED": "1", "LOG_RODAR": str(log)})
    pid = sh.stdout.strip()
    (b / "_estudio" / "pid").write_text(pid)
    return pid


def arquivo_fila(video_dir):
    return Path(video_dir) / "_estudio" / "fila.json"


def ler_fila(video_dir):
    """Estado da fila para o painel ({} se nunca rodou). "ativa" confere se o processo está vivo."""
    arq = arquivo_fila(video_dir)
    try:
        f = json.loads(arq.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    f["ativa"] = f.get("status") in ("rodando", "pausada") and estado._vivo(f.get("pid", ""))
    return f


def lancar_fila(video_dir, maximo=3):
    """Lança o processo da fila solto do painel. Devolve o pid."""
    video_dir = Path(video_dir)
    (video_dir / "_estudio").mkdir(exist_ok=True)
    log = video_dir / "_estudio" / "log_fila.txt"
    cmd = [sys.executable, "-m", "estudio", "fila", str(video_dir), "--max", str(maximo)]
    sh = subprocess.run(["/bin/sh", "-c", '"$@" </dev/null >>"$LOG_FILA" 2>&1 & echo $!', "sh", *cmd],
                        cwd=RAIZ, capture_output=True, text=True, start_new_session=True,
                        env={**os.environ, "PYTHONUNBUFFERED": "1", "LOG_FILA": str(log)})
    pid = sh.stdout.strip()
    # Mac acordado enquanto a fila existir (o Mac do Arthur dorme com 1 min parado e a fila congelava);
    # o caffeinate termina sozinho junto com a fila
    if pid:
        subprocess.run(["/bin/sh", "-c", 'caffeinate -i -s -w "$1" </dev/null >/dev/null 2>&1 &', "sh", pid])
    return pid


def parar_fila(video_dir):
    f = ler_fila(video_dir)
    if f.get("ativa"):
        try:
            os.kill(int(f["pid"]), 15)
        except (ProcessLookupError, ValueError, PermissionError):
            pass
    if f:
        f.update(status="parada", fim=time.strftime("%Y-%m-%d %H:%M:%S"),
                 motivo="parada pelo Arthur no painel (os blocos que já rodavam continuam)")
        f.pop("ativa", None)
        arquivo_fila(video_dir).write_text(json.dumps(f, ensure_ascii=False, indent=1))


def rodar_fila(video_dir, maximo=3):
    video_dir = Path(video_dir).resolve()
    arq = arquivo_fila(video_dir)
    arq.parent.mkdir(exist_ok=True)
    meu = str(os.getpid())
    atual = ler_fila(video_dir)
    if atual.get("ativa") and str(atual.get("pid")) != meu:
        print(f"já tem uma fila rodando neste vídeo (pid {atual['pid']})")
        return
    f = {"pid": meu, "status": "rodando", "max": maximo, "inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
         "lancados": [], "rodando": [], "esperando": [], "parados": [], "motivo": ""}

    def gravar():
        arq.write_text(json.dumps(f, ensure_ascii=False, indent=1))

    def log(msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    log(f"fila iniciada: até {maximo} blocos ao mesmo tempo")
    while True:
        blocos = estado.blocos_do_video(video_dir)
        rodando = [b["nn"] for b in blocos if b["rodando"]]
        pendentes = [b for b in blocos if not b["feito"]["entregue"]]
        # sem a trava do "conferir" (desligada em 2026-10-12): bloco que parou só por ela é entregue direto
        if not motor_cfg().get("travar_conferir"):
            for b in pendentes:
                p = b["parado"] or {}
                if not b["rodando"] and p.get("etapa") == "entregar" and "para conferir" in str(p.get("motivo")) \
                        and b["nn"] not in f.setdefault("reentregues", []):
                    lancar_rodada(video_dir / "blocos" / b["nn"], de="entregar", ate="entregar")
                    f["reentregues"].append(b["nn"])
                    b["parado"] = None
                    rodando.append(b["nn"])
                    log(f"bloco {b['nn']} parado só pelo conferir: entregando")
        livres = [b for b in pendentes if not b["rodando"] and b["nn"] not in rodando]
        # parado por limite/erro passageiro do Claude volta para a fila; parado por decisão fica para o Arthur
        parados = [b["nn"] for b in livres if b["parado"] and not _retentavel(b["parado"])]
        esperando = [b["nn"] for b in livres if (not b["parado"] or _retentavel(b["parado"]))
                     and b["nn"] not in f["lancados"]]
        limite = [b for b in livres if b["nn"] in f["lancados"] and b["parado"]
                  and eh_limite(b["parado"].get("motivo", ""))]
        f.update(rodando=rodando, esperando=esperando, parados=parados, atualizado=time.strftime("%H:%M:%S"))
        if limite:
            # o Claude bateu no limite: não lança nada novo (antes a fila queimou 15 blocos em 5 min) e espera
            # o reset testando a cada 10 min; quando volta, os blocos parados pelo limite entram de novo
            reset = re.search(r"resets? ([^()·]+)", str(limite[0]["parado"].get("motivo", "")))
            f.update(status="pausada", motivo="limite de uso do Claude" + (f" (libera {reset.group(1).strip()})"
                     if reset else "") + ": volto sozinha quando liberar")
            log(f["motivo"])
            gravar()
            while True:
                time.sleep(ESPERA_LIMITE_S)
                CHECAGEM.unlink(missing_ok=True)     # testa de verdade: a checagem guardada não sabe do limite
                try:
                    checar_claude(["storyboard", "escolher", "editar"])
                    break
                except ErroClaude as e:
                    f["atualizado"] = time.strftime("%H:%M:%S")
                    gravar()
                    log(f"ainda no limite: {str(e)[:120]}")
            # todos os parados por limite voltam (não só os da 1ª conta): antes a fila pausava de novo na hora
            parados_lim = [b["nn"] for b in estado.blocos_do_video(video_dir)
                           if b["parado"] and eh_limite(b["parado"].get("motivo", ""))]
            f["lancados"] = [n for n in f["lancados"] if n not in parados_lim]
            f.update(status="rodando", motivo="")
            log("limite liberado: continuando")
            continue
        while len(rodando) < maximo and esperando:
            nn = esperando.pop(0)
            pid = lancar_rodada(video_dir / "blocos" / nn)
            f["lancados"].append(nn)
            rodando.append(nn)
            log(f"bloco {nn} lançado (pid {pid}) · rodando: {', '.join(rodando)}")
            time.sleep(2)       # o pid do bloco aparece antes da próxima conta
        f.update(rodando=rodando, esperando=esperando)
        if not rodando and not esperando:
            f.update(status="terminada",
                     motivo=("todos entregues" if not parados else
                             f"nada mais a lançar; esperando você: {', '.join(parados)}"))
            log(f["motivo"])
            break
        gravar()
        time.sleep(INTERVALO_S)
    f["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
    gravar()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="estudio fila")
    ap.add_argument("video")
    ap.add_argument("--max", type=int, default=3)
    a = ap.parse_args(argv)
    rodar_fila(a.video, max(1, a.max))


if __name__ == "__main__":
    main()
