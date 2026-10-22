"""Configuração pelo painel: chaves de API (do sistema e de cada canal) e criação de canais novos.

  <dados>/.env                CLAUDE_CODE_OAUTH_TOKEN                                  (motor_claude.py)
                              YOUTUBE_API_KEY (modelar.py: nome e logo dos canais a modelar)
  <dados>/canais/<slug>/.env  FISH_API_KEY/FISH_VOICE_ID/FISH_MODEL ou ELEVENLABS_* (gerar_narracao.py;
                              quem narra o canal: canal.json["narracao"]["provedor"]),
                              PEXELS_API_KEY, PIXABAY_API_KEY, SERPER_API_KEY, SI_API_KEY (fontes.py)
Os scripts do motor leem as chaves por motor/caminhos.env(). Os arquivos são gravados com permissão 600 e o painel
nunca mostra uma chave inteira (só os 4 últimos caracteres).
"""
import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import requests

from .motor_claude import ENV as ENV_SISTEMA
from .sistema import (CANAIS, FORMATO_PADRAO, PROVEDOR_NARRACAO_PADRAO, ambiente_motor, canais,
                      ficha_formato, formatos, gravar_json, ler_json)

# grupo -> (arquivo relativo à raiz do canal | None = Estudio/.env, [(chave, rótulo, secreta, ajuda)])
APIS = [
    {"id": "claude", "nome": "Claude (assinatura)", "arquivo": None, "escopo": "sistema",
     "ajuda": "Token da sua assinatura para o Space Machine chamar o Claude sem conversa. Gere no Terminal com "
              "`claude setup-token` e cole aqui.",
     "campos": [("CLAUDE_CODE_OAUTH_TOKEN", "Token", True, "")]},
    {"id": "youtube", "nome": "YouTube (nome e logo dos canais a modelar)", "arquivo": None, "escopo": "sistema",
     "ajuda": "Chave da YouTube Data API v3 (grátis em console.cloud.google.com → APIs e serviços → Credenciais). "
              "Serve só para, quando VOCÊ cola um link na tela inicial, trazer o nome e o logo daquele canal. "
              "A produção continua sem YouTube: nada busca, abre ou baixa vídeo de lá.",
     "campos": [("YOUTUBE_API_KEY", "Chave da API", True, "")]},
    {"id": "fish", "nome": "Fish Audio (narração)", "arquivo": ".env", "escopo": "canal",
     "ajuda": "Chave em fish.audio/app/developers. O crédito de API é separado do crédito da plataforma. Só é usada quando o canal está com a narração no Fish Audio (acima).",
     "campos": [("FISH_API_KEY", "Chave da API", True, ""),
                ("FISH_VOICE_ID", "Voz (reference_id)", False, "id do modelo de voz"),
                ("FISH_MODEL", "Modelo", False, "s2.1-pro (pago) ou s2.1-pro-free")]},
    {"id": "elevenlabs", "nome": "ElevenLabs (narração)", "arquivo": ".env", "escopo": "canal",
     "ajuda": "Chave em elevenlabs.io → Developers → API Keys. Copie a chave que começa com \"sk_\", mostrada só "
              "quando você cria ou gira a chave — o ID que a lista mostra depois NÃO serve. Só é usada quando o "
              "canal está com a narração no ElevenLabs (acima).",
     "campos": [("ELEVENLABS_API_KEY", "Chave da API", True, "começa com sk_"),
                ("ELEVENLABS_VOICE_ID", "Voz (voice_id)", False, "id da voz"),
                ("ELEVENLABS_MODEL", "Modelo", False, "eleven_v4 (melhor) ou eleven_v4_turbo"),
                ("ELEVENLABS_FORMAT", "Qualidade", False, "mp3_44100_128 (192 pede o plano Creator)")]},
    {"id": "pexels", "nome": "Pexels (vídeos e fotos livres)", "arquivo": ".env", "escopo": "canal",
     "ajuda": "Grátis em pexels.com/api.", "campos": [("PEXELS_API_KEY", "Chave da API", True, "")]},
    {"id": "pixabay", "nome": "Pixabay (vídeos e fotos livres)", "arquivo": ".env", "escopo": "canal",
     "ajuda": "Grátis em pixabay.com/api/docs.", "campos": [("PIXABAY_API_KEY", "Chave da API", True, "")]},
    {"id": "serper", "nome": "Serper / Google Imagens (pago)", "arquivo": ".env", "escopo": "canal",
     "ajuda": "serper.dev. Pago: o sistema só usa como última opção de imagem.",
     "campos": [("SERPER_API_KEY", "Chave da API", True, "")]},
    {"id": "smithsonian", "nome": "Smithsonian (fotos históricas)", "arquivo": ".env", "escopo": "canal",
     "ajuda": "Grátis em api.data.gov/signup. Sem a chave, o Smithsonian fica fora da busca.",
     "campos": [("SI_API_KEY", "Chave da API", True, "")]},
]


# narração: o cartão de chaves de cada provedor de TTS (canal.json["narracao"]["provedor"])
PROVEDOR_DA_API = {"fish": "fishaudio", "elevenlabs": "elevenlabs"}
PROVEDORES_NARRACAO = [{"id": "fishaudio", "nome": "Fish Audio", "api": "fish"},
                       {"id": "elevenlabs", "nome": "ElevenLabs", "api": "elevenlabs"}]


def provedor_narracao(canal):
    return (canal.get("narracao") or {}).get("provedor") or PROVEDOR_NARRACAO_PADRAO


def salvar_provedor_narracao(slug, provedor):
    if provedor not in {p["id"] for p in PROVEDORES_NARRACAO}:
        raise ValueError(f"não conheço o provedor de narração \"{provedor}\"")
    arq = CANAIS / slug / "canal.json"
    cj = ler_json(arq, {}) or {}
    cj["narracao"] = {**(cj.get("narracao") or {}), "provedor": provedor}
    gravar_json(arq, cj)


def _arquivo(api, canal):
    return ENV_SISTEMA if api["arquivo"] is None else Path(canal["raiz"]) / api["arquivo"]


def ler_env(arq):
    out = {}
    if Path(arq).exists():
        for linha in Path(arq).read_text().splitlines():
            k, sep, v = linha.partition("=")
            if sep and k.strip() and not k.strip().startswith("#"):
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def gravar_env(arq, valores):
    """Regrava só as chaves pedidas, mantendo as outras linhas do arquivo. valor None = apaga a chave."""
    arq = Path(arq)
    linhas = arq.read_text().splitlines() if arq.exists() else []
    feitas = set()
    novas = []
    for linha in linhas:
        k = linha.partition("=")[0].strip()
        if k in valores:
            feitas.add(k)
            if valores[k] is not None:
                novas.append(f"{k}={valores[k]}")
        else:
            novas.append(linha)
    for k, v in valores.items():
        if k not in feitas and v is not None:
            novas.append(f"{k}={v}")
    arq.write_text("\n".join(novas).strip() + "\n")
    os.chmod(arq, 0o600)


def mascara(v):
    if not v:
        return ""
    return "•" * 8 + v[-4:] if len(v) > 8 else "•" * len(v)


def _api_de_sistema(api_id):
    api = next((a for a in APIS if a["id"] == api_id), None)
    if not api or api["escopo"] != "sistema":
        raise ValueError("essa chave é de um canal")
    return api


def chave_sistema(api_id):
    """A chave de uma API que vale para todos os canais (<dados>/.env)."""
    api = _api_de_sistema(api_id)
    return ler_env(ENV_SISTEMA).get(api["campos"][0][0], "")


def salvar_chave_sistema(api_id, valor):
    """Grava (ou apaga, com valor vazio) a chave de uma API de sistema. Devolve a máscara do que ficou."""
    api = _api_de_sistema(api_id)
    valor = (valor or "").strip()
    gravar_env(ENV_SISTEMA, {api["campos"][0][0]: valor or None})
    return mascara(valor)


def estado_apis(canal):
    out = []
    for api in APIS:
        env = ler_env(_arquivo(api, canal))
        campos = [{"chave": k, "rotulo": r, "secreta": s, "dica": d, "valor": env.get(k, ""),
                   "mostrar": mascara(env.get(k, "")) if s else env.get(k, "")} for k, r, s, d in api["campos"]]
        out.append({**{k: v for k, v in api.items() if k != "campos"}, "campos": campos,
                    "configurada": bool(env.get(api["campos"][0][0])), "caminho": str(_arquivo(api, canal))})
    return out


def salvar_api(canal, api_id, form):
    """form: {CHAVE: valor digitado}. Campo secreto vazio = mantém; "apagar_<CHAVE>" marcado = remove."""
    api = next(a for a in APIS if a["id"] == api_id)
    valores = {}
    for k, _, secreta, _ in api["campos"]:
        if form.get(f"apagar_{k}"):
            valores[k] = None
        elif (form.get(k) or "").strip():
            valores[k] = form[k].strip()
        elif not secreta and k in form:
            valores[k] = None if not form[k].strip() else form[k].strip()
    if valores:
        gravar_env(_arquivo(api, canal), valores)
    return list(valores)


def chaves_de_outros(slug_destino):
    """Que chaves de API cada outro canal tem para copiar para este (só as do canal; a do Claude já vale para todos)."""
    out = []
    for slug, c in canais().items():
        if slug == slug_destino:
            continue
        lidos = {}
        apis = []
        for api in APIS:
            if api["escopo"] != "canal":
                continue
            arq = _arquivo(api, c)
            env = lidos.setdefault(str(arq), ler_env(arq))
            chave = api["campos"][0][0]
            if env.get(chave):
                apis.append({"id": api["id"], "nome": api["nome"], "mostrar": mascara(env[chave])})
        if apis:
            out.append({"slug": slug, "nome": c["nome"], "apis": apis})
    return out


def importar_chaves(destino, slug_origem, ids):
    """Copia para `destino` a chave de API que o canal de origem já tem. Só os campos secretos: o que é identidade
    do canal (voz, modelo) continua o daqui. Devolve os ids copiados."""
    origem = canais().get(slug_origem)
    if not origem:
        raise ValueError("canal de origem não encontrado")
    copiados = []
    for api in APIS:
        if api["id"] not in ids or api["escopo"] != "canal":
            continue
        env = ler_env(_arquivo(api, origem))
        valores = {k: env[k] for k, _, secreta, _ in api["campos"] if secreta and env.get(k)}
        if valores:
            gravar_env(_arquivo(api, destino), valores)
            copiados.append(api["id"])
    return copiados


def testar_api(canal, api_id):
    """Chamada barata para conferir se a chave funciona. Devolve (ok, mensagem)."""
    api = next(a for a in APIS if a["id"] == api_id)
    env = ler_env(_arquivo(api, canal))
    chave = env.get(api["campos"][0][0])
    if not chave:
        return False, "sem chave"
    try:
        if api_id == "pexels":
            r = requests.get("https://api.pexels.com/v1/search", params={"query": "stadium", "per_page": 1},
                             headers={"Authorization": chave}, timeout=20)
            return r.ok, "ok" if r.ok else f"HTTP {r.status_code}"
        if api_id == "pixabay":
            r = requests.get("https://pixabay.com/api/", params={"key": chave, "q": "stadium", "per_page": 3},
                             timeout=20)
            return r.ok, "ok" if r.ok else f"HTTP {r.status_code}: {r.text[:120]}"
        if api_id == "smithsonian":
            r = requests.get("https://api.si.edu/openaccess/api/v1.0/search",
                             params={"q": "stadium", "rows": 1, "api_key": chave}, timeout=20)
            return r.ok, "ok" if r.ok else f"HTTP {r.status_code}"
        if api_id in PROVEDOR_DA_API:
            r = subprocess.run([canal["python"], str(Path(canal["scripts"]) / "gerar_narracao.py"), "--uso",
                                "--provedor", PROVEDOR_DA_API[api_id]],
                               capture_output=True, text=True, timeout=60,
                               env=ambiente_motor(canal))
            return r.returncode == 0, (r.stdout or r.stderr).strip()[-300:]
        if api_id == "youtube":
            r = requests.get("https://www.googleapis.com/youtube/v3/channels",
                             params={"part": "snippet", "forHandle": "@youtube", "key": chave}, timeout=20)
            return r.ok, "ok" if r.ok else f"HTTP {r.status_code}: {r.text[:160]}"
        if api_id == "serper":
            return True, "não testado de propósito (cada busca do Serper gasta crédito pago)"
        if api_id == "claude":
            from .motor_claude import chamar
            res = chamar("teste", "Você responde só o JSON pedido.", "Responda: ok", modelo="haiku",
                         schema={"type": "object", "properties": {"resposta": {"type": "string"}}},
                         ctx={"canal": "teste"})
            return True, f"ok ({res['_uso']['equivalente']} tokens equiv.)"
    except Exception as e:  # noqa: BLE001 — mostra qualquer erro de rede/chave no painel
        return False, str(e)[:300]
    return False, "sem teste para esta API"


# ---------------- canais ----------------
def slug_de(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def salvar_canal(slug, **campos):
    """Muda campos do canal.json (ex.: nome, ativo, identidade, regras)."""
    arq = CANAIS / slug / "canal.json"
    cj = ler_json(arq, {}) or {}
    cj.update(campos)
    gravar_json(arq, cj)


def criar_canal(nome, tema, idioma, cores, fonte_arquivo, logo=None, fundo=None, formato=None, regras=None):
    """Cria <dados>/canais/<slug>/ (canal.json, .env vazio, identidade/, conhecimento/, producoes/).
    O motor é um só: nada de código é copiado."""
    slug = slug_de(nome)
    if not slug:
        raise ValueError("dê um nome ao canal")
    if slug in canais():
        raise ValueError("já existe um canal com esse nome")
    formato = formato or FORMATO_PADRAO
    if formato not in formatos():
        raise ValueError(f"não existe o formato \"{formato}\" (formatos/{formato}/formato.json)")
    d = CANAIS / slug
    if d.exists():
        raise ValueError(f"a pasta {d} já existe")
    for sub in ("identidade", "producoes", "conhecimento/05 - Aprendizados", "conhecimento/06 - Produções"):
        (d / sub).mkdir(parents=True)
    ident = {"cor_fundo": cores["fundo"], "cor_texto": cores["texto"], "cor_destaque": cores["destaque"],
             "cor_caixa": cores["caixa"], "cor_sombra": cores["sombra"], "fonte_marca": Path(fonte_arquivo).stem,
             "fonte_marca_arquivo": fonte_arquivo, "fundo_imagem": None}
    if logo:
        shutil.copy2(logo, d / "identidade" / ("logo" + Path(logo).suffix.lower()))
    if fundo:
        shutil.copy2(fundo, d / "identidade" / ("fundo" + Path(fundo).suffix.lower()))
        ident["fundo_imagem"] = "identidade/fundo" + Path(fundo).suffix.lower()
    cj = {"_sobre": "Canal do Space Machine: identidade (edição, mapas, tabelas) e regras do TEMA (busca, escolha, "
                    "storyboard, QA).",
          "nome": nome, "tema": tema, "idioma": idioma, "formato": formato, "ativo": True, "identidade": ident,
          "regras": regras or {"escolha": [], "storyboard": [], "busca": {}, "qa": {}}}
    # transcrição: inglês usa o modelo .en (padrão do motor); outros idiomas, o multilíngue
    if idioma != "en":
        cj["busca"] = {"whisper_modelo": "~/.cache/whisper/ggml-small.bin"}
    gravar_json(d / "canal.json", cj)
    (d / ".env").write_text("")
    os.chmod(d / ".env", 0o600)
    (d / "conhecimento" / "05 - Aprendizados" / "Log de Aprendizados.md").write_text(
        f"---\ntags: [aprendizados, log]\n---\n\n# Log de Aprendizados\n\nVoltar: [[00 - {nome} (Índice)]]\n\n"
        "Tudo o que descobrirmos neste canal, mais recente em cima. As 4 entradas do topo vão junto no storyboard. "
        "O que vale para todos os canais do formato fica em formatos/<formato>/conhecimento/ no Space Machine.\n\n---\n")
    (d / "conhecimento" / f"00 - {nome} (Índice).md").write_text(
        f"# {nome} — Índice\n\nCanal no formato \"{ficha_formato(formato).get('nome', formato)}\" sobre {tema} "
        f"(idioma: {idioma}).\n\n"
        "- Identidade (cores, fonte, fundo) e regras do tema: `canal.json` na pasta do canal (editável no painel).\n"
        "- Aprendizados: [[Log de Aprendizados]] · Produções: `06 - Produções/`.\n")
    return slug, d


# ---------------- identidade e regras do canal ----------------
FONTES_DIRS = ["/System/Library/Fonts/Supplemental", "/Library/Fonts", str(Path.home() / "Library/Fonts")]
COR = re.compile(r"#[0-9A-Fa-f]{6}")


def fontes():
    """Fontes instaladas no Mac que o After consegue usar nos títulos."""
    out = []
    for d in FONTES_DIRS:
        for f in sorted(Path(d).glob("*.tt[fc]")) + sorted(Path(d).glob("*.otf")):
            out.append(str(f))
    return out


def salvar_identidade(slug, cores, fonte):
    """cores: {cor_fundo, cor_texto, cor_destaque, cor_caixa, cor_sombra} em #RRGGBB; fonte: caminho de fontes()."""
    arq = CANAIS / slug / "canal.json"
    cj = ler_json(arq, {}) or {}
    ident = cj.setdefault("identidade", {})
    for k in ("cor_fundo", "cor_texto", "cor_destaque", "cor_caixa", "cor_sombra"):
        if COR.fullmatch(cores.get(k) or ""):
            ident[k] = cores[k].upper()
    if fonte in fontes():
        ident["fonte_marca_arquivo"], ident["fonte_marca"] = fonte, Path(fonte).stem
    gravar_json(arq, cj)


def _linhas(txt):
    return [l.strip() for l in (txt or "").splitlines() if l.strip()]


def salvar_regras(slug, escolha="", storyboard="", genericas="", genericas_hist="", proibidos="", permitido_se="",
                  trocas=""):
    """Regras do TEMA do canal (canal.json › regras). ValueError se as trocas (JSON) ou a expressão não valem."""
    try:
        trocas_l = json.loads(trocas) if trocas.strip() else []
        assert isinstance(trocas_l, list) and all({"padrao", "por"} <= set(x) for x in trocas_l)
        for x in trocas_l + ([{"padrao": permitido_se}] if permitido_se.strip() else []):
            re.compile(x["padrao"])
    except (ValueError, AssertionError, TypeError, re.error) as e:
        raise ValueError(f"Regras não salvas: trocas/expressão inválidas ({e})")
    genericas_d = {"outros": _linhas(genericas)}
    if _linhas(genericas_hist):
        genericas_d["historica"] = _linhas(genericas_hist)
    salvar_canal(slug, regras={
        "escolha": _linhas(escolha), "storyboard": _linhas(storyboard),
        "busca": {"trocar_termos": trocas_l, "genericas": genericas_d},
        "qa": {"termos_proibidos": [x.strip().lower() for x in proibidos.split(",") if x.strip()],
               "permitido_se": permitido_se.strip()}})


def regras_em_texto(regras):
    """As regras do canal.json no formato dos campos do painel (uma por linha, vírgulas, JSON)."""
    busca, qa = regras.get("busca", {}) or {}, regras.get("qa", {}) or {}
    gen = busca.get("genericas", {}) or {}
    return {"escolha": "\n".join(regras.get("escolha", [])), "storyboard": "\n".join(regras.get("storyboard", [])),
            "genericas": "\n".join(gen.get("outros", [])), "genericas_hist": "\n".join(gen.get("historica", [])),
            "proibidos": ", ".join(qa.get("termos_proibidos", [])), "permitido_se": qa.get("permitido_se", ""),
            "trocas": json.dumps(busca.get("trocar_termos"), ensure_ascii=False) if busca.get("trocar_termos") else ""}


def sugerir_regras(c, slug):
    """O Claude propõe as regras do tema a partir do nome, tema e idioma (nada é salvo). ErroClaude se falhar."""
    from .motor_claude import chamar
    from .sistema import arquivo_formato, config
    schema = {"type": "object", "additionalProperties": False,
              "required": ["escolha", "storyboard", "genericas", "genericas_hist", "proibidos", "permitido_se", "trocas"],
              "properties": {"escolha": {"type": "array", "items": {"type": "string"}},
                             "storyboard": {"type": "array", "items": {"type": "string"}},
                             "genericas": {"type": "array", "items": {"type": "string"}},
                             "genericas_hist": {"type": "array", "items": {"type": "string"}},
                             "proibidos": {"type": "array", "items": {"type": "string"}},
                             "permitido_se": {"type": "string"},
                             "trocas": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                        "required": ["padrao", "por", "exceto"],
                                        "properties": {"padrao": {"type": "string"}, "por": {"type": "string"},
                                                       "exceto": {"type": "string"}}}}}}
    r = chamar("regras", arquivo_formato("prompts/regras_tema.md", c.get("formato")).read_text(),
               f"Canal: {c['nome']}\nTema: {c['tema']}\nIdioma da narração: {c['idioma']}", schema=schema,
               modelo=config()["modelos"].get("storyboard"), ctx={"canal": slug})
    r.pop("_uso", None)
    if r.get("permitido_se", "").strip() in ('""', "''"):       # o modelo às vezes devolve as aspas do exemplo
        r["permitido_se"] = ""
    return {"escolha": "\n".join(r["escolha"]), "storyboard": "\n".join(r["storyboard"]),
            "genericas": "\n".join(r["genericas"]), "genericas_hist": "\n".join(r["genericas_hist"]),
            "proibidos": ", ".join(r["proibidos"]), "permitido_se": r["permitido_se"],
            "trocas": json.dumps(r["trocas"], ensure_ascii=False) if r["trocas"] else ""}


# ---------------- modelos do Claude por etapa ----------------
MODELOS = [("claude-opus-5-5", "Opus 5.5"), ("claude-sonnet-5-5", "Sonnet 5.5"), ("claude-haiku-5-5", "Haiku 5.5"),
           ("claude-fable-5-1", "Fable 5.1")]
ESFORCOS = ["low", "medium", "high", "xhigh", "max"]
ETAPAS_CLAUDE = [
    ("storyboard", "Storyboard", "Planeja as cenas do bloco e corrige até passar nas regras (a etapa mais cara)."),
    ("escolher_imagem", "Escolher imagem", "Escolhe 1 foto/recorte/logo por asset olhando a folha de contato."),
    ("escolher_video", "Escolher vídeo", "Escolhe o vídeo e o início do trecho pelas folhas de quadros."),
    ("confirmar_trecho", "Confirmar trecho", "2ª olhada num vídeo com quadros a cada 0,5 s para acertar o início."),
    ("conferir", "Conferir download", "Olha 1–2 quadros de cada vídeo/recorte baixado (texto por cima, tarja, cena errada)."),
    ("qa", "Corrigir QA", "Quando o QA reprova, corrige o cenas.json uma vez antes de parar."),
    ("descricao", "Descrição do YouTube", "Botão Gerar da publicação: escreve o resumo e o convite para se inscrever "
     "(os capítulos com minutagem saem das durações dos blocos, sem o Claude)."),
]


def estado_modelos():
    """Modelo e esforço de cada etapa, com a média de tokens por chamada e o último modelo usado."""
    from .motor_claude import _banco, config as cfg_motor
    cfg = cfg_motor()
    con = _banco()
    medias = {e: (n, eq) for e, n, eq in con.execute(
        "select etapa, count(*), avg(equivalente) from chamadas where ok=1 group by etapa")}
    ultimos = {e: m for e, m in con.execute(
        "select etapa, modelo from chamadas where ok=1 and id in (select max(id) from chamadas group by etapa)")}
    con.close()
    linhas = [{"id": i, "nome": n, "ajuda": a, "modelo": cfg["modelos"].get(i, ""), "esforco": cfg["esforco"].get(i, "low"),
               "chamadas": medias.get(i, (0, 0))[0], "media": round(medias.get(i, (0, 0))[1] or 0),
               "ultimo": ultimos.get(i, "")} for i, n, a in ETAPAS_CLAUDE]
    return {"linhas": linhas, "modelos": [{"id": m, "nome": n} for m, n in MODELOS], "esforcos": ESFORCOS,
            "after_app": cfg.get("after_app", "")}


def salvar_modelos(modelos, esforco, after_app=""):
    """modelos/esforco: {etapa: valor}; valores fora da lista são ignorados."""
    from .sistema import salvar_config
    validos = {m for m, _ in MODELOS}
    etapas = {e for e, _, _ in ETAPAS_CLAUDE}
    mud = {"modelos": {e: m for e, m in (modelos or {}).items() if e in etapas and m in validos},
           "esforco": {e: x for e, x in (esforco or {}).items() if e in etapas and x in ESFORCOS}}
    if after_app.strip() and re.fullmatch(r"[\w .-]+", after_app.strip()):
        mud["after_app"] = after_app.strip()
    salvar_config(mud)
