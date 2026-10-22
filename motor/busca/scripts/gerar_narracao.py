"""Gera a narração de um bloco pela API de TTS do provedor que o canal usa (Fish Audio ou ElevenLabs).

Uso:
  gerar_narracao.py --vozes [BUSCA]              lista vozes (minhas + busca por nome)
  gerar_narracao.py --modelos                    lista os modelos de TTS que a conta pode usar
  gerar_narracao.py --uso                        créditos/caracteres restantes
  gerar_narracao.py <pasta do bloco> [--voz ID] [--speed 1.0] [--modelo ...]
      lê <bloco>/roteiro.txt (ignora linhas que começam com '#' e as marcações
      de cena, linhas inteiras entre colchetes como [VISUAL: ...])
      e grava <bloco>/narracao.mp3.
  --provedor fishaudio|elevenlabs   usa outro provedor só nesta chamada

Quem narra o canal: canal.json["narracao"]["provedor"] (painel › canal › Chaves). Sem o campo, Fish Audio.
Chaves e voz ficam no .env do canal (painel › Chaves):
  Fish Audio   FISH_API_KEY, FISH_VOICE_ID (o reference_id do modelo de voz), FISH_MODEL (padrão s2.1-pro)
  ElevenLabs   ELEVENLABS_API_KEY (começa com "sk_"; o painel do ElevenLabs também mostra o ID da chave,
               que NÃO serve), ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL (padrão eleven_v4, o de melhor
               qualidade; até 10.000 caracteres por chamada — um bloco nosso tem ~1.700),
               ELEVENLABS_FORMAT (padrão mp3_44100_128; mp3_44100_192 pede o plano Creator ou acima)
Docs: https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech
      https://elevenlabs.io/docs/api-reference/text-to-speech/convert
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import caminhos  # noqa: E402

UA = "SpaceMachine-narracao/3.0"
MARCACAO = re.compile(r"^\[[^\]]*\]$")  # linha inteira entre colchetes: [VISUAL: ...] e afins


def config(nome):
    return caminhos.env(nome)


def pedir(url, corpo=None, headers=None, timeout=60, metodo=None):
    """Chamada HTTP com as esperas do limite de uso. Devolve os bytes da resposta."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    h = {"Content-Type": "application/json", "User-Agent": UA, **(headers or {})}
    req = urllib.request.Request(url, data=dados, method=metodo or ("POST" if dados else "GET"), headers=h)
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
            sys.exit(f"HTTP {e.code} em {url}: {e.read().decode(errors='replace')[:500]}")


# ---------------- Fish Audio ----------------
FISH = "https://api.fish.audio"


def fish_chave():
    chave = config("FISH_API_KEY")
    if not chave:
        sys.exit("Sem chave: defina FISH_API_KEY no .env do canal (painel › Chaves)")
    return {"Authorization": f"Bearer {chave}"}


def fish_gerar(texto, voz, speed, modelo):
    modelo = modelo or config("FISH_MODEL") or "s2.1-pro"
    print(f"gerando {len(texto)} caracteres (Fish Audio, modelo {modelo}, voz {voz})…")
    audio = pedir(FISH + "/v1/tts",
                  {"text": texto, "reference_id": voz, "format": "mp3", "mp3_bitrate": 192,
                   "latency": "normal", "prosody": {"speed": speed}},
                  headers={**fish_chave(), "model": modelo}, timeout=600)
    return audio, {"modelo": modelo}


def fish_vozes(busca):
    consultas = [("minhas", {"self": "true", "page_size": 50})]
    if busca:
        consultas.append(("busca", {"title": busca, "page_size": 20, "sort_by": "score"}))
    for rotulo, params in consultas:
        r = json.loads(pedir(FISH + "/model?" + urllib.parse.urlencode(params), headers=fish_chave()))
        print(f"== {rotulo} ({r.get('total', 0)})")
        for v in r.get("items", []):
            print(f"{v.get('_id')}\t{v.get('title')}\t{','.join(v.get('languages') or [])}")


def fish_modelos():
    print("O Fish Audio escolhe o modelo no cabeçalho da chamada: s1, s2-pro, s2.1-pro, s2.1-pro-free.")
    print("Veja os atuais em https://docs.fish.audio.")


def fish_uso():
    return json.loads(pedir(FISH + "/wallet/self/api-credit", headers=fish_chave()))


# ---------------- ElevenLabs ----------------
ONZE = "https://api.elevenlabs.io"


def onze_chave():
    chave = config("ELEVENLABS_API_KEY")
    if not chave:
        sys.exit("Sem chave: defina ELEVENLABS_API_KEY no .env do canal (painel › Chaves)")
    return {"xi-api-key": chave}


def onze_gerar(texto, voz, speed, modelo):
    modelo = modelo or config("ELEVENLABS_MODEL") or "eleven_v4"
    formato = config("ELEVENLABS_FORMAT") or "mp3_44100_128"
    print(f"gerando {len(texto)} caracteres (ElevenLabs, modelo {modelo}, voz {voz}, {formato})…")
    corpo = {"text": texto, "model_id": modelo}
    if speed != 1.0:   # sem isto, a voz usa as configurações que ela já tem salvas
        corpo["voice_settings"] = {"speed": speed}
    audio = pedir(f"{ONZE}/v1/text-to-speech/{urllib.parse.quote(voz)}?"
                  + urllib.parse.urlencode({"output_format": formato}),
                  corpo, headers=onze_chave(), timeout=600)
    return audio, {"modelo": modelo, "formato": formato}


def onze_vozes(busca):
    params = {"page_size": 50 if not busca else 20, "include_total_count": "true"}
    if busca:
        params["search"] = busca
    r = json.loads(pedir(f"{ONZE}/v2/voices?" + urllib.parse.urlencode(params), headers=onze_chave()))
    print(f"== vozes ({r.get('total_count', len(r.get('voices') or []))})")
    for v in r.get("voices") or []:
        idiomas = ",".join(sorted({x.get("language", "") for x in (v.get("verified_languages") or [])} - {""}))
        print(f"{v.get('voice_id')}\t{v.get('name')}\t{v.get('category', '')}\t{idiomas}")


def onze_modelos():
    for m in json.loads(pedir(ONZE + "/v1/models", headers=onze_chave())):
        if m.get("can_do_text_to_speech"):
            lim = (m.get("maximum_text_length_per_request") or "?")
            print(f"{m.get('model_id')}\t{m.get('name', '')}\taté {lim} caracteres")


def onze_uso():
    r = json.loads(pedir(ONZE + "/v1/user/subscription", headers=onze_chave()))
    return {k: r.get(k) for k in ("tier", "status", "character_count", "character_limit",
                                  "next_character_count_reset_unix")}


PROVEDORES = {
    "fishaudio": {"nome": "Fish Audio", "voz_env": "FISH_VOICE_ID",
                  "gerar": fish_gerar, "vozes": fish_vozes, "uso": fish_uso, "modelos": fish_modelos},
    "elevenlabs": {"nome": "ElevenLabs", "voz_env": "ELEVENLABS_VOICE_ID",
                   "gerar": onze_gerar, "vozes": onze_vozes, "uso": onze_uso, "modelos": onze_modelos},
}


def provedor(nome=None):
    nome = nome or caminhos.narracao()["provedor"]
    if nome not in PROVEDORES:
        sys.exit(f"Não conheço o provedor de narração \"{nome}\": use {' ou '.join(PROVEDORES)}")
    return nome, PROVEDORES[nome]


# ---------------- o que vale para os dois ----------------
def narrar(linha):
    """Linha que vira voz: fora os títulos ('#') e as marcações de cena ('[VISUAL: ...]')."""
    l = linha.strip()
    return not l.startswith("#") and not MARCACAO.match(l)


def texto_do_roteiro(bloco):
    linhas = (bloco / "roteiro.txt").read_text().splitlines()
    return "\n".join(l for l in linhas if narrar(l)).strip()


def gerar(bloco, nome_prov, prov, voz, speed, modelo):
    texto = texto_do_roteiro(bloco)
    destino = bloco / "narracao.mp3"
    audio, extra = prov["gerar"](texto, voz, speed, modelo)
    if not audio or len(audio) < 1000:
        sys.exit(f"Resposta vazia/curta demais ({len(audio or b'')} bytes)")
    if destino.exists():
        antigo = destino.with_name(f"narracao_antiga_{time.strftime('%Y%m%d_%H%M%S')}.mp3")
        destino.rename(antigo)
        print(f"narracao.mp3 existente guardada como {antigo.name}")
    destino.write_bytes(audio)
    (bloco / "_work").mkdir(exist_ok=True)
    (bloco / "_work" / "narracao_job.json").write_text(json.dumps(
        {"provedor": nome_prov, **extra, "voice_id": voz, "speed": speed,
         "caracteres": len(texto), "gerado_em": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2))
    print(f"ok → {destino}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bloco", nargs="?")
    ap.add_argument("--vozes", nargs="?", const="", metavar="BUSCA")
    ap.add_argument("--modelos", action="store_true")
    ap.add_argument("--uso", action="store_true")
    ap.add_argument("--voz")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--modelo")
    ap.add_argument("--provedor", choices=sorted(PROVEDORES))
    a = ap.parse_args()
    nome_prov, prov = provedor(a.provedor)
    if a.vozes is not None:
        prov["vozes"](a.vozes)
        return
    if a.modelos:
        prov["modelos"]()
        return
    if a.uso:
        print(json.dumps(prov["uso"](), indent=2))
        return
    if not a.bloco:
        ap.error("informe a pasta do bloco, --vozes, --modelos ou --uso")
    voz = a.voz or config(prov["voz_env"])
    if not voz:
        sys.exit(f"Sem voz: use --voz ID ou {prov['voz_env']} no .env do canal (veja --vozes)")
    gerar(Path(a.bloco).resolve(), nome_prov, prov, voz, a.speed, a.modelo)


if __name__ == "__main__":
    main()
