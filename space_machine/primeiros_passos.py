"""Primeiros passos: o que precisa estar instalado e configurado para produzir, com o que fazer quando falta.

Nada aqui gasta token: o teste de verdade do Claude é o botão "Testar o Claude" (motor_claude.checar_claude).
"""
import os
import re
import subprocess
from pathlib import Path

from . import configuracao
from . import plataforma
from .sistema import CANAIS, DADOS, MOTOR, canais, config, ler_json, whisper_cli


def _item(ok, nome, detalhe, como=""):
    return {"ok": bool(ok), "nome": nome, "detalhe": detalhe, "como": "" if ok else como}


def _versao(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0][:80]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return ""


def _prefs_after():
    """A pasta onde o After guarda as preferências desta pessoa (muda de sistema para sistema)."""
    if plataforma.WINDOWS:
        return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "Adobe" / "After Effects"
    return Path.home() / "Library/Preferences/Adobe/After Effects"


def _after():
    """(app, instalado?, permissão de scripts gravarem arquivos ligada?) do After de space_machine.json."""
    app = config().get("after_app", "Adobe After Effects 2026")
    instalado = plataforma.after_instalado(app)
    # o nome do arquivo é traduzido ("Adobe After Effects 26.5 Prefs.txt", "Preferências do Adobe After Effects
    # 26.5.txt"): vale o da versão mais nova que tiver a chave
    versoes = sorted((d for d in _prefs_after().glob("*") if d.is_dir() and re.fullmatch(r"[\d.]+", d.name)),
                     key=lambda d: [int(x) for x in re.findall(r"\d+", d.name)])
    permitido = None
    for arq in (sorted(versoes[-1].glob("*.txt"), key=lambda p: len(p.name)) if versoes else []):
        m = re.search(r'"Pref_SCRIPTING_FILE_NETWORK_SECURITY" = "?(\d+)', arq.read_text(errors="replace"))
        if m:
            permitido = bool(m.group(1).strip("0"))
            break
    return app, bool(instalado), permitido


def checar():
    """Lista de {ok, nome, detalhe, como} na ordem em que a pessoa resolve."""
    out = []
    instalador = ".\\instalar.ps1" if plataforma.WINDOWS else "./instalar.sh"
    out.append(_item(DADOS.exists() and os.access(DADOS, os.W_OK), "Pasta de dados",
                     str(DADOS), f"Crie a pasta {DADOS} (ou rode {instalador} e escolha outra)."))
    claude = plataforma.achar("claude")
    out.append(_item(claude, "Claude Code (comando claude)", _versao([claude, "--version"]) if claude else "não encontrado",
                     "Instale: npm install -g @anthropic-ai/claude-code (precisa de uma assinatura do Claude)."))
    token = configuracao.ler_env(DADOS / ".env").get("CLAUDE_CODE_OAUTH_TOKEN")
    out.append(_item(token, "Token da assinatura do Claude", "configurado" if token else "faltando",
                     # no PowerShell o claude.ps1 do npm cai na política de execução de scripts; o .cmd não
                     ("No PowerShell: claude.cmd setup-token" if plataforma.WINDOWS else "No Terminal: claude setup-token")
                     + ". Cole o token em APIs › Claude."))
    for prog in ("ffmpeg", "ffprobe"):
        p = plataforma.achar(prog)
        out.append(_item(p, prog, p or "não encontrado", plataforma.COMO_INSTALAR[prog]))
    cfg_busca = ler_json(MOTOR / "busca" / "config.json", {}) or {}
    whisper = whisper_cli(cfg_busca.get("whisper_cli"))
    out.append(_item(Path(whisper).exists(), "Transcrição (whisper-cli)", whisper,
                     plataforma.COMO_INSTALAR["whisper-cli"]))
    modelos = {Path(cfg_busca.get("whisper_modelo", "~/.cache/whisper/ggml-small.en.bin")).expanduser()}
    for c in canais().values():
        m = (ler_json(Path(c["raiz"]) / "canal.json", {}) or {}).get("busca", {}).get("whisper_modelo")
        if m:
            modelos.add(Path(m).expanduser())
    for m in sorted(modelos):
        out.append(_item(m.exists(), f"Modelo de transcrição {m.name}", str(m),
                         f"{instalador} baixa (ou: curl -L -o {m} https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{m.name})"))
    app, instalado, permitido = _after()
    onde = "Program Files\\Adobe" if plataforma.WINDOWS else "/Applications"
    out.append(_item(instalado, "After Effects", app if instalado else f"{app} não encontrado em {onde}",
                     "Instale o After Effects. Se for outra versão, troque o nome do app aqui embaixo."))
    if instalado:
        out.append(_item(permitido, "After Effects: scripts podem gravar arquivos",
                         "ligado" if permitido else "desligado ou nunca aberto",
                         ("No After: Editar › Preferências › Scripts e expressões › marque \"Permitir que scripts gravem "
                          "arquivos e acessem a rede\" (em inglês: Edit › Preferences › Scripting & Expressions › "
                          "\"Allow Scripts to Write Files and Access Network\")." if plataforma.WINDOWS else
                          "No After: Settings › Scripting & Expressions › marque \"Allow Scripts to Write Files and "
                          "Access Network\".")))
    lista = canais()
    out.append(_item(lista, "Pelo menos um canal", ", ".join(c["nome"] for c in lista.values()) or "nenhum",
                     "Crie em Canais › Novo canal."))
    for slug, c in lista.items():
        env = configuracao.ler_env(Path(c["raiz"]) / ".env")
        video = env.get("PIXABAY_API_KEY") or env.get("PEXELS_API_KEY")
        out.append(_item(video, f"{c['nome']}: banco de vídeo (Pixabay ou Pexels)", "ok" if video else "sem chave",
                         f"Chave grátis em pixabay.com/api/docs ou pexels.com/api → APIs › {c['nome']}."))
        prov = configuracao.provedor_narracao(c)
        onze = prov == "elevenlabs"
        nome_prov, site = ("ElevenLabs", "elevenlabs.io") if onze else ("Fish Audio", "fish.audio")
        pref = "ELEVENLABS" if onze else "FISH"
        tts = env.get(f"{pref}_API_KEY") and env.get(f"{pref}_VOICE_ID")
        out.append(_item(tts, f"{c['nome']}: narração ({nome_prov})", "ok" if tts else "falta chave ou voz",
                         f"Chave e id da voz em {site} → Chaves › {c['nome']}. (Ou grave a narração e ponha "
                         "narracao.mp3 em cada bloco.)"))
    return out


def falta_algo():
    try:
        return any(not i["ok"] for i in checar())
    except Exception:  # noqa: BLE001 — a página inicial nunca quebra por causa da checagem
        return True
