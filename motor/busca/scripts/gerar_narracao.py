"""Gera a narração de um bloco pela API de TTS do Fish Audio.

Uso:
  gerar_narracao.py --vozes [BUSCA]              lista vozes (minhas + busca pública por nome)
  gerar_narracao.py --uso                        créditos de API restantes
  gerar_narracao.py <pasta do bloco> [--voz ID] [--speed 1.0] [--modelo s2.1-pro]
      lê <bloco>/roteiro.txt (ignora linhas que começam com '#' e as marcações
      de cena, linhas inteiras entre colchetes como [VISUAL: ...])
      e grava <bloco>/narracao.mp3.

Chave: variável FISH_API_KEY ou .env do canal (FISH_API_KEY, FISH_VOICE_ID, FISH_MODEL)
(linha FISH_API_KEY=...). Voz padrão: FISH_VOICE_ID (o reference_id do modelo de voz);
modelo padrão: FISH_MODEL (s1, s2-pro, s2.1-pro...; sem nada usa s2.1-pro).
Docs: https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import caminhos  # noqa: E402

BASE = "https://api.fish.audio"
UA = "SpaceMachine-narracao/2.0"
MARCACAO = re.compile(r"^\[[^\]]*\]$")  # linha inteira entre colchetes: [VISUAL: ...] e afins


def config(nome):
    return caminhos.env(nome)


def chamar(metodo, caminho, corpo=None, headers=None, timeout=60):
    chave = config("FISH_API_KEY")
    if not chave:
        sys.exit("Sem chave: defina FISH_API_KEY no .env do canal (painel › APIs)")
    dados = json.dumps(corpo).encode() if corpo is not None else None
    h = {"Authorization": f"Bearer {chave}", "Content-Type": "application/json", "User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(BASE + caminho, data=dados, method=metodo, headers=h)
    for tentativa in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and tentativa < 4:
                espera = int(e.headers.get("Retry-After") or 15)
                print(f"{e.code} (limite/carga), esperando {espera}s…")
                time.sleep(espera)
                continue
            sys.exit(f"HTTP {e.code} em {caminho}: {e.read().decode(errors='replace')[:500]}")


def narrar(linha):
    """Linha que vira voz: fora os títulos ('#') e as marcações de cena ('[VISUAL: ...]')."""
    l = linha.strip()
    return not l.startswith("#") and not MARCACAO.match(l)


def texto_do_roteiro(bloco):
    linhas = (bloco / "roteiro.txt").read_text().splitlines()
    return "\n".join(l for l in linhas if narrar(l)).strip()


def gerar(bloco, voz, speed, modelo):
    texto = texto_do_roteiro(bloco)
    destino = bloco / "narracao.mp3"
    print(f"gerando {len(texto)} caracteres (modelo {modelo}, voz {voz})…")
    audio = chamar("POST", "/v1/tts",
                   {"text": texto, "reference_id": voz, "format": "mp3", "mp3_bitrate": 192,
                    "latency": "normal", "prosody": {"speed": speed}},
                   headers={"model": modelo}, timeout=600)
    if not audio or len(audio) < 1000:
        sys.exit(f"Resposta vazia/curta demais ({len(audio or b'')} bytes)")
    if destino.exists():
        antigo = destino.with_name(f"narracao_antiga_{time.strftime('%Y%m%d_%H%M%S')}.mp3")
        destino.rename(antigo)
        print(f"narracao.mp3 existente guardada como {antigo.name}")
    destino.write_bytes(audio)
    (bloco / "_work").mkdir(exist_ok=True)
    (bloco / "_work" / "narracao_job.json").write_text(json.dumps(
        {"provedor": "fishaudio", "modelo": modelo, "voice_id": voz, "speed": speed,
         "caracteres": len(texto), "gerado_em": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2))
    print(f"ok → {destino}")


def listar_vozes(busca):
    consultas = [("minhas", {"self": "true", "page_size": 50})]
    if busca:
        consultas.append(("busca", {"title": busca, "page_size": 20, "sort_by": "score"}))
    for rotulo, params in consultas:
        r = json.loads(chamar("GET", "/model?" + urllib.parse.urlencode(params)))
        print(f"== {rotulo} ({r.get('total', 0)})")
        for v in r.get("items", []):
            print(f"{v.get('_id')}\t{v.get('title')}\t{','.join(v.get('languages') or [])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bloco", nargs="?")
    ap.add_argument("--vozes", nargs="?", const="", metavar="BUSCA")
    ap.add_argument("--uso", action="store_true")
    ap.add_argument("--voz")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--modelo")
    a = ap.parse_args()
    if a.vozes is not None:
        listar_vozes(a.vozes)
        return
    if a.uso:
        print(json.dumps(json.loads(chamar("GET", "/wallet/self/api-credit")), indent=2))
        return
    if not a.bloco:
        ap.error("informe a pasta do bloco, --vozes ou --uso")
    voz = a.voz or config("FISH_VOICE_ID")
    if not voz:
        sys.exit("Sem voz: use --voz ID ou FISH_VOICE_ID no .env do canal (veja --vozes)")
    gerar(Path(a.bloco).resolve(), voz, a.speed, a.modelo or config("FISH_MODEL") or "s2.1-pro")


if __name__ == "__main__":
    main()
