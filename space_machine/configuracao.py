"""Configuração pelo painel: chaves de API (do sistema e de cada canal) e criação de canais novos.

  <dados>/.env                CLAUDE_CODE_OAUTH_TOKEN                                  (motor_claude.py)
  <dados>/canais/<slug>/.env  FISH_API_KEY, FISH_VOICE_ID, FISH_MODEL (gerar_narracao.py),
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
from .sistema import CANAIS, ambiente_motor, canais, gravar_json, ler_json

# grupo -> (arquivo relativo à raiz do canal | None = Estudio/.env, [(chave, rótulo, secreta, ajuda)])
APIS = [
    {"id": "claude", "nome": "Claude (assinatura)", "arquivo": None, "escopo": "sistema",
     "ajuda": "Token da sua assinatura para o Space Machine chamar o Claude sem conversa. Gere no Terminal com "
              "`claude setup-token` e cole aqui.",
     "campos": [("CLAUDE_CODE_OAUTH_TOKEN", "Token", True, "")]},
    {"id": "fish", "nome": "Fish Audio (narração)", "arquivo": ".env", "escopo": "canal",
     "ajuda": "Chave em fish.audio/app/developers. O crédito de API é separado do crédito da plataforma.",
     "campos": [("FISH_API_KEY", "Chave da API", True, ""),
                ("FISH_VOICE_ID", "Voz (reference_id)", False, "id do modelo de voz"),
                ("FISH_MODEL", "Modelo", False, "s2.1-pro (pago) ou s2.1-pro-free")]},
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
        if api_id == "fish":
            r = subprocess.run([canal["python"], str(Path(canal["scripts"]) / "gerar_narracao.py"), "--uso"],
                               capture_output=True, text=True, timeout=60,
                               env=ambiente_motor(canal))
            return r.returncode == 0, (r.stdout or r.stderr).strip()[-300:]
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


def criar_canal(nome, tema, idioma, cores, fonte_arquivo, logo=None, fundo=None, formato="explained", regras=None):
    """Cria <dados>/canais/<slug>/ (canal.json, .env vazio, identidade/, conhecimento/, producoes/).
    O motor é um só: nada de código é copiado."""
    slug = slug_de(nome)
    if not slug:
        raise ValueError("dê um nome ao canal")
    if slug in canais():
        raise ValueError("já existe um canal com esse nome")
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
        f"# {nome} — Índice\n\nCanal no formato \"___ Explained\" sobre {tema} (idioma: {idioma}).\n\n"
        "- Identidade (cores, fonte, fundo) e regras do tema: `canal.json` na pasta do canal (editável no painel).\n"
        "- Aprendizados: [[Log de Aprendizados]] · Produções: `06 - Produções/`.\n")
    return slug, d
