"""O que muda de um sistema para o outro (macOS × Windows), num lugar só.

O Space Machine nasceu no Mac. O que o Windows faz de outro jeito:
  - a trava de arquivo que garante um bloco por vez no After (flock × msvcrt);
  - como se pede um script ao After Effects (osascript × AfterFX.exe -r);
  - onde se procuram os programas que o sistema chama (Homebrew × PATH do Windows);
  - processos soltos do painel: lançar, saber se estão vivos, parar (sh/kill × Popen/taskkill);
  - abrir uma pasta ou um arquivo para você (open × explorer).

Quem precisa de qualquer uma delas chama daqui, nunca escreve o caminho na mão.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

WINDOWS = os.name == "nt"

def _path_windows():
    """O PATH desta sessão mais o salvo no registro (do sistema e seu): o que o winget e o npm instalaram depois que
    o processo que abriu o painel começou só está no registro."""
    partes = os.environ.get("PATH", "").split(";")
    import winreg
    for raiz, chave in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                        (winreg.HKEY_CURRENT_USER, "Environment")):
        try:
            with winreg.OpenKey(raiz, chave) as k:
                partes += os.path.expandvars(winreg.QueryValueEx(k, "Path")[0]).split(";")
        except OSError:
            pass
    vistos = set()
    return ";".join(p for p in partes if p and not (p.lower() in vistos or vistos.add(p.lower())))


# Onde procurar ffmpeg, claude e whisper. No Mac o app aberto pelo Finder recebe um PATH curto demais
# (sem o Homebrew); no Windows, o da sessão mais o do registro.
CAMINHO_SISTEMA = _path_windows() if WINDOWS else "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

# O mínimo que um processo filho precisa herdar para funcionar (o resto fica de fora: o claude filho não
# herda proxy nem sessão de quem chamou).
VARIAVEIS_BASE = (("USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT",
                   "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP", "PATHEXT", "COMSPEC", "LANG",
                   "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE")
                  if WINDOWS else ("HOME", "USER", "LANG", "TMPDIR", "SHELL"))

COMO_INSTALAR = {
    "ffmpeg": "winget install Gyan.FFmpeg" if WINDOWS else "brew install ffmpeg",
    "ffprobe": ("vem junto com o ffmpeg: winget install Gyan.FFmpeg" if WINDOWS
                else "vem junto com o ffmpeg: brew install ffmpeg"),
    "whisper-cli": ("baixe o whisper.cpp para Windows (instalar.ps1 baixa)" if WINDOWS
                    else "brew install whisper-cpp"),
}


def achar(programa):
    """O caminho de um programa instalado (claude, ffmpeg, ffprobe...), ou None."""
    return shutil.which(programa, path=CAMINHO_SISTEMA) or shutil.which(programa)


def claude():
    """Como chamar o Claude Code. No Windows o npm instala um claude.cmd, que o subprocess não acha pelo nome e que
    passaria os argumentos pelo cmd.exe (corta em quebra de linha e em 8191 caracteres): vai direto no claude.exe."""
    if not WINDOWS:
        return "claude"
    achado = achar("claude")
    if achado and achado.lower().endswith(".cmd"):
        exe = Path(achado).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if exe.exists():
            return str(exe)
    return achado or "claude"


# ----- trava: um script por vez no After (ele trava com dois) -----
def travar(arquivo):
    """Trava exclusiva no arquivo aberto; espera a vez."""
    arquivo.seek(0)
    if not WINDOWS:
        import fcntl
        fcntl.flock(arquivo, fcntl.LOCK_EX)
        return
    import msvcrt
    while True:                       # LK_LOCK desiste depois de 10 s: aqui a espera é sem prazo
        try:
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_LOCK, 1)
            return
        except OSError:
            time.sleep(1)


def destravar(arquivo):
    if not WINDOWS:
        import fcntl
        fcntl.flock(arquivo, fcntl.LOCK_UN)
        return
    import msvcrt
    try:
        arquivo.seek(0)
        msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:                   # já solta ao fechar o arquivo
        pass


# ----- After Effects -----
def after_instalado(app):
    """Onde o After Effects está, ou None. `app` é o nome configurado ("Adobe After Effects 2026")."""
    if not WINDOWS:
        caminho = Path("/Applications") / app / f"{app}.app"
        return caminho if caminho.exists() else None
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramW6432", r"C:\Program Files")):
        exe = Path(base) / "Adobe" / app / "Support Files" / "AfterFX.exe"
        if exe.exists():
            return exe
    return None


def rodar_jsx(app, script, espera_s):
    """Pede ao After Effects que rode um .jsx.

    Não espera o fim: quem espera é sempre o log que o próprio .jsx grava (o DoScript do After não
    devolve nada útil, e um After travado num diálogo seguraria a fila inteira)."""
    script = str(script)
    if WINDOWS:
        exe = after_instalado(app)
        if not exe:
            raise FileNotFoundError(f"não achei o After Effects ({app}) em Program Files\\Adobe — "
                                    "se for outra versão, troque o nome em Primeiros passos")
        # -r roda o script na instância aberta do After (ou abre uma). Pelo `start` do cmd o After não fica na árvore
        # da rodada: o Parar do painel (encerrar com arvore) não fecha o After junto
        subprocess.Popen(["cmd", "/c", "start", "", str(exe), "-r", script], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        return
    subprocess.run(["osascript", "-e", f"with timeout of {espera_s} seconds",
                    "-e", f'tell application "{app}" to DoScriptFile "{script}"', "-e", "end timeout"],
                   capture_output=True, timeout=espera_s + 60)


def esperar_log(log, espera_s, passo_s=3):
    """Espera o .jsx gravar o log dele. Devolve o texto, ou "" se o After não respondeu."""
    log = Path(log)
    for _ in range(max(1, espera_s // passo_s)):
        if log.exists():
            return log.read_text(errors="replace").strip()
        time.sleep(passo_s)
    return ""


def abrir_no_after(app, arquivo):
    """Abre um .aep no After Effects, na tela."""
    if WINDOWS:
        exe = after_instalado(app)
        if exe:
            subprocess.Popen(["cmd", "/c", "start", "", str(exe), str(arquivo)], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.startfile(str(arquivo))
        return
    subprocess.run(["open", "-a", app, str(arquivo)], check=False)


# ----- processos soltos (rodadas, fila, vídeo final, Reels) -----
def lancar_solto(cmd, log, cwd):
    """Lança cmd sem prender ao painel (fechar o painel ou o terminal não para nada), com a saída no fim do log.
    Devolve o pid (texto)."""
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    if WINDOWS:
        # já em UTF-8: sem isso o __main__ se relança, e o pid que voltou daqui não é mais o pai de quem roda
        env["PYTHONUTF8"] = "1"
        env["PATH"] = CAMINHO_SISTEMA
        with open(log, "a") as saida:
            p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=saida,
                                 stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
        return str(p.pid)
    # filho do painel, a rodada morria quando o terminal do painel era fechado: o sh solta e o launchd adota
    sh = subprocess.run(["/bin/sh", "-c", '"$@" </dev/null >>"$LOG_SOLTO" 2>&1 & echo $!', "sh", *cmd],
                        cwd=cwd, capture_output=True, text=True, start_new_session=True,
                        env={**env, "LOG_SOLTO": str(log)})
    return sh.stdout.strip()


def meus_pids():
    """Os pids que contam como este processo. No Windows o python.exe do .venv é um lançador que roda o Python de
    verdade como filho: quem lançou guardou o pid do lançador (o pai), e o processo se vê com o pid dele."""
    pids = {str(os.getpid())}
    if WINDOWS:
        pids.add(str(os.getppid()))
    return pids


def vivo(pid):
    """O processo ainda existe?"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if WINDOWS:
        # os.kill(pid, 0) no Windows não testa nada: o sinal 0 é o Ctrl+C, mandado para o grupo do processo
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            codigo = ctypes.c_ulong()
            return bool(k.GetExitCodeProcess(h, ctypes.byref(codigo))) and codigo.value == 259   # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def encerrar(pid, arvore=False):
    """Encerra o processo. Com arvore, também o que ele lançou (a rodada e o claude/After que ela chamou)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return
    if WINDOWS:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"] + (["/T"] if arvore else []), capture_output=True)
        return
    import signal
    try:
        if arvore:
            # o processo é filho de um `sh` líder de sessão (lancar_solto): o grupo é o do sh, não o pid dele
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def manter_acordado(pid):
    """Computador acordado enquanto o processo pid existir (a fila congelava com o Mac dormindo)."""
    if WINDOWS:
        return       # no Windows quem pede é a própria fila (acordado_enquanto_roda)
    subprocess.run(["/bin/sh", "-c", 'caffeinate -i -s -w "$1" </dev/null >/dev/null 2>&1 &', "sh", str(pid)])


def acordado_enquanto_roda():
    """Chamado pelo próprio processo: o Windows não dorme enquanto ele estiver vivo."""
    if WINDOWS:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # CONTINUOUS | SYSTEM_REQUIRED


# ----- mostrar para você -----
def abrir(caminho):
    """Abre uma pasta (ou arquivo) na tela: Finder no Mac, Explorador no Windows."""
    if WINDOWS:
        os.startfile(str(caminho))
        return
    subprocess.run(["open", str(caminho)], check=False)
