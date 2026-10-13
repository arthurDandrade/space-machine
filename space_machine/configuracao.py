"""Configuração pelo painel: chaves de API (por canal e do Estúdio) e criação de canais novos.

As chaves ficam nos mesmos arquivos que os scripts já leem (nada muda para eles):
  <raiz do canal>/.env.fishaudio   FISH_API_KEY, FISH_VOICE_ID, FISH_MODEL      (gerar_narracao.py)
  <raiz do canal>/.env.fontes      PEXELS_API_KEY, PIXABAY_API_KEY, SERPER_API_KEY, SI_API_KEY   (fontes.py)
  Estudio/.env                     CLAUDE_CODE_OAUTH_TOKEN                      (motor_claude.py)
Os arquivos são gravados com permissão 600 e o painel nunca mostra uma chave inteira (só os 4 últimos caracteres).
"""
import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import requests

from .motor_claude import ENV as ENV_ESTUDIO, RAIZ as RAIZ_ESTUDIO

# grupo -> (arquivo relativo à raiz do canal | None = Estudio/.env, [(chave, rótulo, secreta, ajuda)])
APIS = [
    {"id": "claude", "nome": "Claude (assinatura)", "arquivo": None, "escopo": "estudio",
     "ajuda": "Token da sua assinatura para o Estúdio chamar o Claude sem conversa. Gere no Terminal com "
              "`claude setup-token` e cole aqui.",
     "campos": [("CLAUDE_CODE_OAUTH_TOKEN", "Token", True, "")]},
    {"id": "fish", "nome": "Fish Audio (narração)", "arquivo": ".env.fishaudio", "escopo": "canal",
     "ajuda": "Chave em fish.audio/app/developers. O crédito de API é separado do crédito da plataforma.",
     "campos": [("FISH_API_KEY", "Chave da API", True, ""),
                ("FISH_VOICE_ID", "Voz (reference_id)", False, "id do modelo de voz"),
                ("FISH_MODEL", "Modelo", False, "s2.1-pro (pago) ou s2.1-pro-free")]},
    {"id": "pexels", "nome": "Pexels (vídeos e fotos livres)", "arquivo": ".env.fontes", "escopo": "canal",
     "ajuda": "Grátis em pexels.com/api.", "campos": [("PEXELS_API_KEY", "Chave da API", True, "")]},
    {"id": "pixabay", "nome": "Pixabay (vídeos e fotos livres)", "arquivo": ".env.fontes", "escopo": "canal",
     "ajuda": "Grátis em pixabay.com/api/docs.", "campos": [("PIXABAY_API_KEY", "Chave da API", True, "")]},
    {"id": "serper", "nome": "Serper / Google Imagens (pago)", "arquivo": ".env.fontes", "escopo": "canal",
     "ajuda": "serper.dev. Pago: o sistema só usa como última opção de imagem.",
     "campos": [("SERPER_API_KEY", "Chave da API", True, "")]},
    {"id": "smithsonian", "nome": "Smithsonian (fotos históricas)", "arquivo": ".env.fontes", "escopo": "canal",
     "ajuda": "Grátis em api.data.gov/signup. Sem a chave, o Smithsonian fica fora da busca.",
     "campos": [("SI_API_KEY", "Chave da API", True, "")]},
]


def _arquivo(api, canal):
    return ENV_ESTUDIO if api["arquivo"] is None else Path(canal["raiz"]) / api["arquivo"]


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
                               capture_output=True, text=True, timeout=60)
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
def _slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def salvar_canais(dados):
    (RAIZ_ESTUDIO / "canais.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def registrar_canal(slug, raiz, nome, ativo=True):
    """Cadastra no canais.json uma pasta de canal no formato do motor (buscador_assets + editor_ae)."""
    raiz = Path(raiz)
    from .motor_claude import canais
    dados = canais()
    dados[slug] = {
        "nome": nome, "raiz": str(raiz),
        "python": dados.get("pro-football", {}).get("python", str(raiz / "buscador_assets/.venv/bin/python")),
        "scripts": str(raiz / "buscador_assets" / "scripts"), "editor": str(raiz / "editor_ae"),
        "producoes": str(raiz / "producoes" / "videos"), "conhecimento": str(raiz / "conhecimento" / nome),
        "ativo": ativo}
    salvar_canais(dados)
    return dados[slug]


IGNORAR = shutil.ignore_patterns("_backup*", "__pycache__", "_cache", "teste_projeto", ".DS_Store", "*.aep",
                                 "_backup_antes_*", ".venv")
NOTAS_HERDADAS = ["01 - Formato/Formato do Vídeo.md", "01 - Formato/Análise de Roteiro.md",
                  "02 - Cenas", "03 - Assets/Como Buscar Assets.md", "03 - Assets/Critérios de Escolha.md",
                  "03 - Assets/Rank de Fontes.md", "03 - Assets/Sistema Buscador de Assets.md",
                  "03 - Assets/Buscas que Funcionam.md", "04 - Edição"]


def criar_canal(nome, tema, idioma, cores, fonte_arquivo, logo=None, fundo=None, base="pro-football"):
    """Copia o motor do canal-base (sem produções, cache, backups) para /Users/arthur/Canais/<Nome>, cria
    canal.json, a pasta de conhecimento (notas do formato herdadas + log novo) e cadastra no canais.json."""
    from .motor_claude import canais
    origem = canais()[base]
    o = Path(origem["raiz"])
    slug = _slug(nome)
    destino = o.parent / re.sub(r"[^\w\- ]", "", nome).strip().replace(" ", "")
    if not slug or slug in canais():
        raise ValueError("já existe um canal com esse nome")
    if destino.exists():
        raise ValueError(f"a pasta {destino} já existe")
    destino.mkdir()
    shutil.copytree(o / "buscador_assets", destino / "buscador_assets", ignore=IGNORAR, symlinks=True)
    shutil.copytree(o / "editor_ae", destino / "editor_ae", ignore=IGNORAR)
    (destino / "buscador_assets" / "_cache").mkdir()
    (destino / "producoes" / "videos").mkdir(parents=True)
    (destino / "identidade").mkdir()
    if (o / ".claude").exists():
        shutil.copytree(o / ".claude", destino / ".claude", ignore=shutil.ignore_patterns("_backup*", "launch.json"))
    ident = {"cor_fundo": cores["fundo"], "cor_texto": cores["texto"], "cor_destaque": cores["destaque"],
             "cor_caixa": cores["caixa"], "cor_sombra": cores["sombra"], "fonte_marca": Path(fonte_arquivo).stem,
             "fonte_marca_arquivo": fonte_arquivo, "fundo_imagem": None}
    if logo:
        shutil.copy2(logo, destino / "identidade" / ("logo" + Path(logo).suffix.lower()))
    if fundo:
        shutil.copy2(fundo, destino / "identidade" / ("fundo" + Path(fundo).suffix.lower()))
        ident["fundo_imagem"] = "identidade/fundo" + Path(fundo).suffix.lower()
    (destino / "canal.json").write_text(json.dumps({
        "_sobre": "Identidade do canal (Estúdio). Lida pela edição e pelos geradores de mapa/tabela.",
        "nome": nome, "tema": tema, "idioma": idioma, "base": base, "identidade": ident},
        ensure_ascii=False, indent=2) + "\n")
    # transcrição: inglês usa o modelo .en; outros idiomas, o multilíngue
    cfg = destino / "buscador_assets" / "config.json"
    if idioma != "en" and cfg.exists():
        cfg.write_text(cfg.read_text().replace("ggml-small.en.bin", "ggml-small.bin"))
    # conhecimento: notas do formato herdadas do canal-base + log e produções novos
    k_o, k_d = Path(origem["conhecimento"]), destino / "conhecimento" / nome
    for rel in NOTAS_HERDADAS:
        src = k_o / rel
        if src.is_dir():
            shutil.copytree(src, k_d / rel)
        elif src.exists():
            (k_d / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, k_d / rel)
    (k_d / "05 - Aprendizados").mkdir(parents=True, exist_ok=True)
    (k_d / "06 - Produções").mkdir(parents=True, exist_ok=True)
    (k_d / "05 - Aprendizados" / "Log de Aprendizados.md").write_text(
        f"---\ntags: [aprendizados, log]\n---\n\n# Log de Aprendizados\n\nVoltar: [[00 - {nome} (Índice)]]\n\n"
        f"Tudo o que descobrirmos neste canal, mais recente em cima. As notas de formato, cenas, assets e edição "
        f"foram herdadas do {origem['nome']} (o Log dele fica em {k_o}).\n\n---\n")
    (k_d / f"00 - {nome} (Índice).md").write_text(
        f"# {nome} — Índice\n\nCanal no formato \"___ Explained\" sobre {tema} (idioma: {idioma}). "
        f"Criado pelo Estúdio a partir do motor do {origem['nome']}.\n\n"
        "Notas herdadas (adaptar ao tema com o tempo): 01 - Formato, 02 - Cenas, 03 - Assets, 04 - Edição.\n"
        "**Identidade Visual**: as cores, a fonte e o fundo deste canal ficam no `canal.json` da raiz.\n")
    # caminhos e nomes do canal-base nos arquivos de texto copiados
    trocas = [(str(o), str(destino)), (f"conhecimento/{origem['nome']}", f"conhecimento/{nome}")]
    for f in list(destino.rglob("*.md")) + list(destino.rglob("*.py")) + list(destino.rglob("*.sh")) + \
            list(destino.rglob("*.jsx")):
        if ".venv" in f.parts:
            continue
        try:
            t = f.read_text()
        except UnicodeDecodeError:
            continue
        n = t
        for a, b in trocas:
            n = n.replace(a, b)
        if n != t:
            f.write_text(n)
    claude_md = o / "CLAUDE.md"
    if claude_md.exists():
        t = claude_md.read_text()
        for a, b in trocas + [(origem["nome"], nome)]:
            t = t.replace(a, b)
        (destino / "CLAUDE.md").write_text(t)
    for env in (".env.fishaudio", ".env.fontes"):
        (destino / env).write_text("")
        os.chmod(destino / env, 0o600)
    registrar_canal(slug, destino, nome)
    return slug, destino
