"""Gera a narração de um bloco pela API de TTS do provedor que o canal usa (Fish Audio, ElevenLabs ou Dark Planner).

Uso:
  gerar_narracao.py --vozes [BUSCA]              lista vozes (minhas + busca por nome)
  gerar_narracao.py --modelos                    lista os modelos de TTS que a conta pode usar
  gerar_narracao.py --uso                        créditos/caracteres restantes
  gerar_narracao.py <pasta do bloco> [--voz ID] [--speed 1.0] [--modelo ...]
      lê <bloco>/roteiro.txt (ignora linhas que começam com '#' e as marcações
      de cena, linhas inteiras entre colchetes como [VISUAL: ...])
      e grava <bloco>/narracao.mp3.
  --provedor fishaudio|elevenlabs|darkplanner   usa outro provedor só nesta chamada

Quem narra o canal: canal.json["narracao"]["provedor"] (painel › canal › Chaves). Sem o campo, Fish Audio.
Chaves e voz ficam no .env do canal (painel › Chaves):
  Fish Audio   FISH_API_KEY, FISH_VOICE_ID (o reference_id do modelo de voz), FISH_MODEL (padrão s2.1-pro)
  ElevenLabs   ELEVENLABS_API_KEY (começa com "sk_"; o painel do ElevenLabs também mostra o ID da chave,
               que NÃO serve), ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL (padrão eleven_v4, o de melhor
               qualidade; até 10.000 caracteres por chamada — um bloco nosso tem ~1.700),
               ELEVENLABS_FORMAT (padrão mp3_44100_128; mp3_44100_192 pede o plano Creator ou acima)
  Dark Planner DARKPLANNER_API_KEY (começa com "dpk_"), DARKPLANNER_VOICE_ID (o id, o apelido ou o
               nome da voz: são ~1.000, veja com --vozes).
               Não tem modelo para escolher: a voz já diz tudo. Gera em fila (manda o texto, espera o job
               ficar pronto e baixa o MP3), aceita speed de 0.5 a 1.5 e pede assinatura Pro ou Plus.
Docs: https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech
      https://elevenlabs.io/docs/api-reference/text-to-speech/convert
      https://app.darkplanner.com.br/api-docs
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


class SemPermissao(Exception):
    """A chave autenticou, mas não tem permissão para esta leitura (chave restrita a TTS, p.ex.)."""
MARCACAO = re.compile(r"^\[[^\]]*\]$")  # linha inteira entre colchetes: [VISUAL: ...] e afins


def config(nome):
    return caminhos.env(nome)


def recado(corpo):
    """A frase que o serviço mandou, em vez do JSON inteiro (os dois embrulham o recado em "detail")."""
    txt = corpo.decode(errors="replace") if isinstance(corpo, bytes) else str(corpo)
    try:
        d = json.loads(txt)
    except ValueError:
        return txt[:300]
    d = d.get("detail", d) if isinstance(d, dict) else d
    if isinstance(d, dict):
        return str(d.get("message") or d.get("msg") or d.get("error") or d)[:300]
    return str(d)[:300]


def pedir(url, corpo=None, headers=None, timeout=60, metodo=None, erro_ok=None):
    """Chamada HTTP com as esperas do limite de uso. Devolve os bytes da resposta."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    h = {"Content-Type": "application/json", "User-Agent": UA, **(headers or {})}
    req = urllib.request.Request(url, data=dados, method=metodo or ("POST" if dados else "GET"), headers=h)
    for tentativa in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (erro_ok or ()):
                raise SemPermissao(recado(e.read())) from None
            if e.code in (429, 503) and tentativa < 4:
                espera = int(e.headers.get("Retry-After") or 15)
                print(f"{e.code} (limite/carga), esperando {espera}s…")
                time.sleep(espera)
                continue
            sys.exit(f"HTTP {e.code}: {recado(e.read())} ({url.split('?')[0]})")


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
    try:
        bruto = pedir(ONZE + "/v1/user/subscription", headers=onze_chave(), erro_ok=(401,))
    except SemPermissao as e:
        # chave restrita (só TTS, por exemplo): autenticou, mas não pode ler o uso
        print(f"chave aceita, mas sem permissão para ler o uso: {e}")
        return {}
    r = json.loads(bruto)
    return {k: r.get(k) for k in ("tier", "status", "character_count", "character_limit",
                                  "next_character_count_reset_unix")}


# ---------------- Dark Planner ----------------
# Gera em fila: POST /generate devolve um job_id, /status diz quando ficou pronto e /download dá a URL do MP3.
# As três legendas .srt que ele também faz ficam de fora: a transcrição do bloco é do whisper-cli.
DARK = "https://app.darkplanner.com.br/api/v1/audio"
DARK_ESPERA = 5        # as consultas aceitam no máximo 1 por segundo
DARK_LIMITE = 30 * 60  # desiste depois disso e manda ver o painel do Dark Planner
DARK_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def dark_chave():
    chave = config("DARKPLANNER_API_KEY")
    if not chave:
        sys.exit("Sem chave: defina DARKPLANNER_API_KEY no .env do canal (painel › Chaves)")
    return {"X-API-Key": chave}


def dark_catalogo():
    return json.loads(pedir(DARK + "/voices", headers=dark_chave())).get("voices") or []


def dark_voz(voz):
    """Na hora de gerar o Dark Planner só aceita o id; aqui o apelido ("clark") e o nome também servem."""
    if DARK_UUID.match(voz):
        return voz
    v = voz.strip().lower()
    vozes = dark_catalogo()
    achadas = ([x for x in vozes if v in ((x.get("slug") or "").lower(), (x.get("name") or "").lower())]
               or [x for x in vozes if v in f"{x.get('slug', '')} {x.get('name', '')}".lower()])
    if not achadas:
        sys.exit(f"Não achei a voz \"{voz}\" na sua conta do Dark Planner (veja as suas com --vozes)")
    if len(achadas) > 1:
        nomes = ", ".join(x.get("name", "") for x in achadas[:5])
        sys.exit(f"\"{voz}\" serve para {len(achadas)} vozes ({nomes}…): ponha o id ou o apelido inteiro "
                 "(veja com --vozes)")
    print(f"voz \"{voz}\" = {achadas[0].get('name')} ({achadas[0].get('id')})")
    return achadas[0]["id"]


def dark_estado(job):
    return json.loads(pedir(f"{DARK}/status/{urllib.parse.quote(job)}", headers=dark_chave()))


def dark_esperar(job):
    """Pergunta o status até o job ficar pronto. Devolve quando terminar; sai com o motivo se falhar."""
    fim = time.time() + DARK_LIMITE
    visto = None
    while time.time() < fim:
        r = dark_estado(job)
        estado = r.get("status")
        if estado == "completed":
            return
        if estado in ("failed", "blocked", "not_found"):
            motivo = r.get("error_message") or estado
            if estado == "blocked":
                motivo = f"a moderação da voz barrou o texto ({motivo})"
            sys.exit(f"O Dark Planner não gerou o áudio: {motivo}")
        if estado != visto:
            print(f"job {job}: {estado}…")
            visto = estado
        time.sleep(DARK_ESPERA)
    sys.exit(f"O job {job} não ficou pronto em {DARK_LIMITE // 60} min "
             f"(veja em app.darkplanner.com.br e, se tiver saído, rode de novo)")


def dark_baixar(job):
    r = json.loads(pedir(f"{DARK}/download/{urllib.parse.quote(job)}", headers=dark_chave()))
    url = r.get("audio_url")
    if not url:
        sys.exit(f"O Dark Planner não devolveu a URL do áudio: {str(r)[:300]}")
    return pedir(urllib.parse.urljoin(DARK + "/", url), timeout=600)


def dark_gerar(texto, voz, speed, modelo):
    if modelo:
        print("O Dark Planner não escolhe modelo: ignorando --modelo.")
    voz = dark_voz(voz)
    print(f"gerando {len(texto)} caracteres (Dark Planner, voz {voz})…")
    r = json.loads(pedir(DARK + "/generate", {"text": texto, "voice_id": voz, "speed": speed},
                         headers=dark_chave(), timeout=120))
    job = r.get("job_id")
    if not job:
        sys.exit(f"O Dark Planner não devolveu job_id: {str(r)[:300]}")
    dark_esperar(job)
    return dark_baixar(job), {"job_id": job}


def dark_vozes(busca):
    vozes = dark_catalogo()
    if busca:
        b = busca.lower()
        vozes = [v for v in vozes if b in f"{v.get('name', '')} {v.get('slug', '')}".lower()]
    print(f"== vozes ({len(vozes)})  id\tapelido\tnome")
    for v in vozes:
        print(f"{v.get('id')}\t{v.get('slug', '')}\t{v.get('name')}\t{v.get('gender', '')}")


def dark_modelos():
    print("O Dark Planner não tem modelo para escolher: a voz já define o motor. Veja as vozes com --vozes.")


def dark_uso():
    return json.loads(pedir(DARK + "/usage", headers=dark_chave()))


PROVEDORES = {
    "fishaudio": {"nome": "Fish Audio", "voz_env": "FISH_VOICE_ID",
                  "gerar": fish_gerar, "vozes": fish_vozes, "uso": fish_uso, "modelos": fish_modelos},
    "elevenlabs": {"nome": "ElevenLabs", "voz_env": "ELEVENLABS_VOICE_ID",
                   "gerar": onze_gerar, "vozes": onze_vozes, "uso": onze_uso, "modelos": onze_modelos},
    "darkplanner": {"nome": "Dark Planner", "voz_env": "DARKPLANNER_VOICE_ID",
                    "gerar": dark_gerar, "vozes": dark_vozes, "uso": dark_uso, "modelos": dark_modelos},
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
        u = prov["uso"]()
        if u:                      # vazio = o provedor já explicou por que não deu para ler
            print(json.dumps(u, indent=2))
        return
    if not a.bloco:
        ap.error("informe a pasta do bloco, --vozes, --modelos ou --uso")
    voz = a.voz or config(prov["voz_env"])
    if not voz:
        sys.exit(f"Sem voz: use --voz ID ou {prov['voz_env']} no .env do canal (veja --vozes)")
    gerar(Path(a.bloco).resolve(), nome_prov, prov, voz, a.speed, a.modelo)


if __name__ == "__main__":
    main()
