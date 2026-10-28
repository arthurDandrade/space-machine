"""Atualizar o Space Machine: traz o código novo do GitHub e deixa tudo pronto para rodar.

  python -m space_machine atualizar [--conferir] [--sim]

A instalação é um clone deste repo (README › Instalar), então atualizar é:
  git fetch → git pull --ff-only → Python (requirements.txt, se mudou) → painel (npm, se mudou) → reiniciar o painel.
A pasta de dados não é tocada: canais, produções, chaves e cache ficam fora do código (sistema.py).

Não atualiza, e diz por quê, quando: não é um clone do git (baixou o ZIP), você tem mudanças ou commits seus aqui,
a branch saiu da linha do GitHub, ou tem bloco/fila produzindo agora (o reinício mataria a produção).
A conferida guarda a resposta em <dados>/cache/atualizacao.json por 6 h: o painel pergunta de graça, e só vai à rede
quando o prazo passa ou você clica em Conferir.
"""
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import estado
from . import plataforma
from .sistema import DADOS, REPO, canais, gravar_json, ler_json

CACHE = DADOS / "cache" / "atualizacao.json"
VALIDADE = 6 * 3600           # quanto tempo a conferida vale antes de ir à rede de novo
SEP = "\x1f"


def _prog(nome):
    return plataforma.achar(nome)


def _rodar(cmd, timeout=120, cwd=REPO):
    """(deu certo?, saída) — nunca levanta: quem chama mostra a saída para a pessoa."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"})
        return r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def _git(*args, timeout=60):
    git = _prog("git")
    if not git:
        return False, "git não encontrado"
    return _rodar([git, *args], timeout=timeout)


def estado_local():
    """O que dá para saber sem rede: é um clone?, branch, commit, data e se tem coisa sua por cima."""
    if not (REPO / ".git").exists():
        return {"git": False, "branch": "", "commit": "", "data": "", "sujo": False, "upstream": "", "versao": ""}
    ok, info = _git("log", "-1", f"--format=%h{SEP}%cI{SEP}%s")
    commit, data, titulo = (info.split(SEP) + ["", "", ""])[:3] if ok else ("", "", "")
    _, branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    tem_upstream, upstream = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    _, sujo = _git("status", "--porcelain", "--untracked-files=no")
    tem_tag, tag = _git("describe", "--tags", "--abbrev=0")
    return {"git": True, "branch": branch, "commit": commit, "data": data, "titulo": titulo,
            "sujo": bool(sujo.strip()), "upstream": upstream if tem_upstream else "", "versao": tag if tem_tag else ""}


def producao_rodando():
    """Blocos e filas vivos agora: atualizar reinicia o painel, e o reinício mataria o que está produzindo."""
    ocupado = []
    for slug, c in canais().items():
        prod = Path(c["producoes"])
        if not prod.exists():
            continue
        for pid in prod.glob("*/blocos/*/_estudio/pid"):
            if estado._vivo(pid.read_text().strip() or "0"):
                ocupado.append(f"{c['nome']} › {pid.parents[3].name} › bloco {pid.parents[1].name}")
        for arq in prod.glob("*/_estudio/fila.json"):
            f = ler_json(arq, {}) or {}
            if f.get("status") in ("rodando", "pausada") and estado._vivo(f.get("pid", "")):
                ocupado.append(f"{c['nome']} › {arq.parents[1].name} › fila")
    return ocupado


def _commits_novos(limite=40):
    ok, saida = _git("log", f"--format=%h{SEP}%cI{SEP}%s", f"-{limite}", "HEAD..@{u}")
    if not ok:
        return []
    out = []
    for linha in saida.splitlines():
        p = linha.split(SEP)
        if len(p) == 3:
            out.append({"commit": p[0], "data": p[1], "titulo": p[2]})
    return out


def conferir(forcar=False):
    """Tem versão nova no GitHub? Vai à rede no máximo a cada 6 h (ou sempre, com forcar)."""
    guardado = ler_json(CACHE, {}) or {}
    if not forcar and time.time() - guardado.get("quando", 0) < VALIDADE:
        return guardado
    loc = estado_local()
    r = {"quando": time.time(), "atrasado": 0, "adiante": 0, "commits": [], "erro": ""}
    if not loc["git"]:
        r["erro"] = "sem_git"
    elif not loc["upstream"]:
        r["erro"] = "sem_upstream"
    else:
        ok, saida = _git("fetch", "--quiet", timeout=90)
        if not ok:
            r["erro"] = "rede"
            r["detalhe"] = saida[-300:]
        else:
            ok, contas = _git("rev-list", "--left-right", "--count", "HEAD...@{u}")
            adiante, atrasado = (contas.split() + ["0", "0"])[:2] if ok else ("0", "0")
            r.update(adiante=int(adiante), atrasado=int(atrasado), commits=_commits_novos())
    gravar_json(CACHE, r)
    return r


def aviso():
    """Para o topo do painel: quantos commits de atraso a última conferida viu (sem ir à rede)."""
    return (ler_json(CACHE, {}) or {}).get("atrasado", 0)


def conferir_atras_das_cortinas():
    """Se a conferida está velha, atualiza o cache numa thread: o pedido do painel não espera a rede."""
    if time.time() - (ler_json(CACHE, {}) or {}).get("quando", 0) < VALIDADE:
        return
    threading.Thread(target=lambda: conferir(forcar=True), daemon=True).start()


def impedimento():
    """Por que não dá para atualizar agora ("" quer dizer que dá), com o detalhe para a pessoa."""
    loc = estado_local()
    if not loc["git"]:
        return "sem_git", str(REPO)
    if not _prog("git"):
        return "sem_programa", "git"
    if loc["sujo"]:
        _, sujo = _git("status", "--short", "--untracked-files=no")
        return "sujo", sujo[:500]
    if not loc["upstream"]:
        return "sem_upstream", loc["branch"]
    ok, contas = _git("rev-list", "--left-right", "--count", "HEAD...@{u}")
    adiante, atrasado = (contas.split() + ["0", "0"])[:2] if ok else ("0", "0")
    # commits seus e commits do GitHub ao mesmo tempo: o pull --ff-only recusa, e passar por cima apagaria os seus
    if int(adiante) and int(atrasado):
        return "divergiu", f"{adiante} commit(s) seus e {atrasado} do GitHub na branch {loc['branch']}"
    rodando = producao_rodando()
    if rodando:
        return "produzindo", ", ".join(rodando[:4])
    return "", ""


def _mudou(antes, depois, prefixos):
    ok, saida = _git("diff", "--name-only", f"{antes}..{depois}")
    return ok and any(l.startswith(prefixos) for l in saida.splitlines())


def aplicar():
    """git pull e o que mais ficou para trás. Devolve {ok, impedimento, detalhe, passos, de, para, reiniciar}."""
    motivo, detalhe = impedimento()
    if motivo:
        return {"ok": False, "impedimento": motivo, "detalhe": detalhe, "passos": []}
    antes = estado_local()["commit"]
    passos = []

    def passo(nome, ok, saida=""):
        passos.append({"passo": nome, "ok": bool(ok), "saida": (saida or "")[-1500:]})
        return ok

    ok, saida = _git("pull", "--ff-only", timeout=180)
    if not passo("git pull", ok, saida):
        return {"ok": False, "impedimento": "pull", "detalhe": saida[-500:], "passos": passos}
    depois = estado_local()["commit"]
    if depois == antes:
        return {"ok": True, "passos": passos, "de": antes, "para": depois, "nada": True, "reiniciar": False}

    if _mudou(antes, depois, ("requirements.txt",)):
        uv = _prog("uv")
        cmd = ([uv, "pip", "install", "-q", "-p", sys.executable, "-r", "requirements.txt"] if uv
               else [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"])
        ok, saida = _rodar(cmd, timeout=600)
        passo("Python (requirements.txt)", ok, saida)

    if _mudou(antes, depois, ("painel/",)):
        npm = _prog("npm")
        if not npm:
            passo("painel (npm)", False, "Falta o Node: brew install node")
        else:
            if _mudou(antes, depois, ("painel/package-lock.json", "painel/package.json")):
                ok, saida = _rodar([npm, "ci", "--no-audit", "--no-fund", "--loglevel=error"],
                                   timeout=900, cwd=REPO / "painel")
                passo("painel (npm ci)", ok, saida)
            ok, saida = _rodar([npm, "run", "build"], timeout=900, cwd=REPO / "painel")
            passo("painel (build)", ok, saida)

    for f in ("spacemachine", "instalar.sh", "motor/edicao_ae/editar_bloco.sh"):
        alvo = REPO / f
        if alvo.exists() and not plataforma.WINDOWS:
            alvo.chmod(alvo.stat().st_mode | 0o111)
    CACHE.unlink(missing_ok=True)
    return {"ok": all(p["ok"] for p in passos), "passos": passos, "de": antes, "para": depois,
            "nada": False, "reiniciar": True}


def reiniciar_painel(espera=1.0):
    """Troca este processo pelo painel do código novo (mesmo pid, mesma porta, mesmo log)."""
    from . import servidor
    porta = getattr(servidor, "PORTA", 8765)

    def trocar():
        time.sleep(espera)
        os.execv(sys.executable, [sys.executable, "-m", "space_machine", "painel", "--porta", str(porta)])

    threading.Thread(target=trocar, daemon=True).start()


def pedir_reinicio_do_painel(porta=8765):
    """Depois de atualizar pela linha de comando: se o painel desta instalação está ligado, ele se reinicia no
    código novo. Manda qual é o repo: um painel de outra instalação na mesma porta recusa em vez de reiniciar."""
    import json
    import urllib.error
    import urllib.request
    try:
        corpo = json.dumps({"repo": str(REPO)}).encode()
        pedido = urllib.request.Request(f"http://127.0.0.1:{porta}/api/atualizacao/reiniciar", data=corpo,
                                        headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(pedido, timeout=5) as r:
            return bool(json.loads(r.read() or b"{}").get("ok"))
    except (urllib.error.URLError, OSError, ValueError):
        return False


IMPEDIMENTOS = {
    "sem_git": "Esta pasta não é um clone do git (você baixou o ZIP?). Para atualizar sozinho, instale com:\n"
               "  git clone <repo> SpaceMachine && cd SpaceMachine && ./instalar.sh",
    "sem_programa": "Falta o git: instale com  brew install git",
    "sujo": "Você tem mudanças não commitadas aqui. Guarde ou descarte antes de atualizar:",
    "sem_upstream": "A branch não acompanha nenhuma branch do GitHub:",
    "divergiu": "Você tem commits seus e o GitHub tem outros: junte à mão (git pull --rebase) para não "
                "perder os seus.",
    "produzindo": "Tem produção rodando agora (atualizar reinicia o painel e pararia o trabalho):",
    "pull": "O git pull não deu certo:",
}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="python -m space_machine atualizar", description=__doc__.split("\n")[0])
    ap.add_argument("--conferir", action="store_true", help="só olha se tem versão nova, não atualiza")
    ap.add_argument("--sim", action="store_true", help="atualiza sem perguntar")
    a = ap.parse_args(argv)

    loc = estado_local()
    if not loc["git"]:
        print(IMPEDIMENTOS["sem_git"])
        sys.exit(1)
    print(f"Sua versão: {loc['commit']} de {loc['data'][:10]} ({loc['branch']})  {loc['titulo'][:60]}")
    print("Conferindo o GitHub...")
    r = conferir(forcar=True)
    if r.get("erro"):
        print(f"Não consegui conferir ({r['erro']}): {r.get('detalhe', '')}")
        sys.exit(1)
    if not r["atrasado"]:
        print("Você já está na versão mais nova.")
        return
    print(f"\n{r['atrasado']} atualização(ões) esperando:")
    for c in r["commits"]:
        print(f"  {c['data'][:10]}  {c['titulo'][:80]}")
    if a.conferir:
        print("\nPara atualizar:  ./spacemachine atualizar")
        return
    motivo, detalhe = impedimento()
    if motivo:
        print(f"\n{IMPEDIMENTOS.get(motivo, motivo)}\n{detalhe}")
        sys.exit(1)
    if not a.sim and sys.stdin.isatty():
        if (input("\nAtualizar agora? [S/n] ") or "s").lower()[0] != "s":
            return
    print("\nAtualizando...")
    res = aplicar()
    for p in res["passos"]:
        print(f"  {'ok  ' if p['ok'] else 'FALHOU'} {p['passo']}")
        if not p["ok"] and p["saida"]:
            print("    " + p["saida"].replace("\n", "\n    "))
    if res.get("impedimento"):
        print(f"\n{IMPEDIMENTOS.get(res['impedimento'], res['impedimento'])}\n{res.get('detalhe', '')}")
        sys.exit(1)
    novo = estado_local()
    print(f"\nPronto: {novo['commit']} de {novo['data'][:10]}  {novo['titulo'][:60]}")
    if pedir_reinicio_do_painel():
        print("O painel está se reiniciando com o código novo (atualize a página no navegador).")
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
