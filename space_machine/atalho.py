"""Ícone do Space Machine e o atalho na área de trabalho.

  python -m space_machine atalho [--pasta ~/Desktop]   cria (ou refaz) "Space Machine.app" (Mac) ou "Space Machine.lnk"
                                                        (Windows): abre o painel no navegador e, se ele não estiver
                                                        ligado, liga em segundo plano
  python -m space_machine atalho --favicons            refaz os tamanhos pequenos do ícone usados pelo painel

O ícone mestre é painel/public/icone.png (1024×1024). No Mac o app é um pacote mínimo (Info.plist + um script + o
.icns), criado no próprio Mac: não precisa de assinatura nem de Xcode. No Windows é um atalho comum para o
spacemachine.ps1 abrir, com o ícone em .ico.
"""
import argparse
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import plataforma
from .sistema import DADOS, REPO

ICONE = REPO / "painel" / "public" / "icone.png"
NOME = "Space Machine"
# tamanhos do .iconset do macOS: (nome, lado em px)
ICONSET = [("16x16", 16), ("16x16@2x", 32), ("32x32", 32), ("32x32@2x", 64), ("128x128", 128),
           ("128x128@2x", 256), ("256x256", 256), ("256x256@2x", 512), ("512x512", 512), ("512x512@2x", 1024)]


def _redimensionar(origem, lado, destino):
    if plataforma.WINDOWS:            # sem o sips do Mac: o Pillow faz o mesmo
        from PIL import Image
        Image.open(origem).convert("RGBA").resize((lado, lado), Image.LANCZOS).save(destino)
        return
    subprocess.run(["sips", "-z", str(lado), str(lado), str(origem), "--out", str(destino)],
                   check=True, capture_output=True)


def gerar_favicons():
    """Tamanhos pequenos que o painel usa (aba do navegador, marca no topo, atalho do iPhone/iPad)."""
    pub = ICONE.parent
    for nome, lado in (("favicon-16.png", 16), ("favicon-32.png", 32), ("icone-128.png", 128),
                       ("apple-touch-icon.png", 180)):
        _redimensionar(ICONE, lado, pub / nome)
    return pub


def _icone_mac(destino):
    """O ícone mestre na grade dos ícones do macOS: corpo de 824 px no quadro de 1024, com sombra suave (sem isso
    o atalho fica maior que os outros apps no Dock e no Finder)."""
    from PIL import Image, ImageFilter
    corpo = Image.open(ICONE).convert("RGBA").resize((824, 824), Image.LANCZOS)
    sombra = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    sombra.paste((0, 0, 0, 255), (100, 112), mask=corpo.getchannel("A").point(lambda v: int(v * 0.32)))
    quadro = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    quadro.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(16)))
    quadro.alpha_composite(corpo, (100, 100))
    quadro.save(destino)


def _icns(destino):
    with tempfile.TemporaryDirectory() as tmp:
        conjunto = Path(tmp) / "icone.iconset"
        conjunto.mkdir()
        mac = Path(tmp) / "icone_mac.png"
        _icone_mac(mac)
        for nome, lado in ICONSET:
            _redimensionar(mac, lado, conjunto / f"icon_{nome}.png")
        subprocess.run(["iconutil", "-c", "icns", str(conjunto), "-o", str(destino)], check=True, capture_output=True)


def _area_de_trabalho():
    """A área de trabalho de verdade (no Windows ela pode estar no OneDrive)."""
    if plataforma.WINDOWS:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                           capture_output=True, text=True)
        if r.stdout.strip():
            return Path(r.stdout.strip())
    return Path.home() / "Desktop"


def criar_windows(pasta):
    """Cria <pasta>/Space Machine.lnk: roda o spacemachine.ps1 abrir sem janela de terminal."""
    lnk = Path(pasta).expanduser() / f"{NOME}.lnk"
    ico = DADOS / "cache" / "icone.ico"      # gerado: fica nos dados, não no repo
    ico.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.open(ICONE).convert("RGBA").save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    ps1 = REPO / "spacemachine.ps1"
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SM_LNK);"
        "$s.TargetPath = 'powershell.exe';"
        "$s.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"' + $env:SM_PS1 + '\" abrir';"
        "$s.WorkingDirectory = $env:SM_REPO; $s.IconLocation = $env:SM_ICO; $s.WindowStyle = 7;"
        "$s.Description = 'Abre o painel do Space Machine'; $s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True,
                   env={**os.environ, "SM_LNK": str(lnk), "SM_PS1": str(ps1), "SM_REPO": str(REPO), "SM_ICO": str(ico)})
    return lnk


def criar(pasta=None):
    """Cria o atalho na área de trabalho. No Mac, <pasta>/Space Machine.app: o script do app usa o shell de login
    (zsh -l) para ter o PATH do Homebrew (ffmpeg, whisper, claude), porque app aberto pelo Finder recebe um PATH
    mínimo."""
    pasta = Path(pasta).expanduser() if pasta else _area_de_trabalho()
    if plataforma.WINDOWS:
        return criar_windows(pasta)
    app = Path(pasta).expanduser() / f"{NOME}.app"
    if app.exists():
        shutil.rmtree(app)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    lancador = app / "Contents" / "MacOS" / "abrir"
    lancador.write_text(f"#!/bin/zsh\nexec /bin/zsh -lc {_aspas(str(REPO / 'spacemachine') + ' abrir')}\n")
    lancador.chmod(0o755)
    _icns(app / "Contents" / "Resources" / "icone.icns")
    with open(app / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleName": NOME, "CFBundleDisplayName": NOME, "CFBundleIdentifier": "app.spacemachine.painel",
                       "CFBundleExecutable": "abrir", "CFBundleIconFile": "icone", "CFBundlePackageType": "APPL",
                       "CFBundleShortVersionString": "1.0", "LSUIElement": True}, f)
    # o Finder guarda o ícone antigo em cache: avisar que o pacote mudou
    subprocess.run(["touch", str(app)])
    lsregister = Path("/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework"
                      "/Support/lsregister")
    if lsregister.exists():
        subprocess.run([str(lsregister), "-f", str(app)], capture_output=True)
    return app


def _aspas(s):
    return "'" + s.replace("'", "'\\''") + "'"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m space_machine atalho", description=__doc__.split("\n")[0])
    ap.add_argument("--pasta", default=None, help="onde criar o atalho (padrão: área de trabalho)")
    ap.add_argument("--favicons", action="store_true", help="só refaz os tamanhos pequenos do ícone do painel")
    a = ap.parse_args(argv)
    if not ICONE.exists():
        sys.exit(f"falta o ícone mestre: {ICONE}")
    if a.favicons:
        print(f"ok: {gerar_favicons()}")
        return
    print(f"ok: {criar(a.pasta)}")


if __name__ == "__main__":
    main()
