"""Onde ficam os dados do Space Machine e o que tem neles (config, canais).

O código (este repo) é o mesmo para todo mundo. Tudo o que é de quem usa fica na pasta de dados:
  space_machine.json   paralelo, app do After, limpeza (padrões em config_padrao.json)
  .env                 CLAUDE_CODE_OAUTH_TOKEN
  space_machine.sqlite consumo das chamadas e gestão (ideias, publicação)
  cache/  logs/  referencias/<formato>/
  canais/<slug>/       canal.json, .env, identidade/, conhecimento/, producoes/

A pasta de dados vem de SM_DADOS; senão, do arquivo ~/.config/spacemachine/dados (gravado pelo instalar.sh);
senão, ~/SpaceMachine-dados.
"""
import json
import os
import sys
from pathlib import Path

PACOTE = Path(__file__).resolve().parent
REPO = PACOTE.parent
MOTOR = REPO / "motor"
FORMATOS = REPO / "formatos"
APONTADOR = Path.home() / ".config" / "spacemachine" / "dados"

# quem sabe onde fica cada coisa de um formato é o motor (motor/caminhos.py), usado também pelos scripts dele
sys.path.insert(0, str(MOTOR))
import caminhos as _caminhos  # noqa: E402

FORMATO_PADRAO = _caminhos.FORMATO_PADRAO
PROVEDOR_NARRACAO_PADRAO = _caminhos.PROVEDOR_NARRACAO_PADRAO


def formatos():
    """Os formatos de vídeo do repo ({slug: {nome, resumo}}), para a pessoa escolher o do canal."""
    return _caminhos.formatos()


def ficha_formato(nome):
    """formatos/<nome>/formato.json."""
    return _caminhos.ficha(nome)


def arquivo_formato(arquivo, formato=None):
    """Um arquivo da pasta do formato ("prompts/storyboard.md"), com erro claro se o formato não trouxer o seu."""
    return _caminhos.do_formato(arquivo, formato or FORMATO_PADRAO)


def _pasta_dados():
    if os.environ.get("SM_DADOS"):
        return Path(os.environ["SM_DADOS"]).expanduser()
    try:
        return Path(APONTADOR.read_text().strip()).expanduser()
    except OSError:
        return Path.home() / "SpaceMachine-dados"


DADOS = _pasta_dados()
CANAIS = DADOS / "canais"


def ler_json(caminho, padrao=None):
    try:
        return json.loads(Path(caminho).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def gravar_json(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1))
    tmp.replace(caminho)


def config():
    """config_padrao.json do repo com space_machine.json da pasta de dados por cima (um nível de dicionário)."""
    cfg = ler_json(PACOTE / "config_padrao.json", {})
    for k, v in (ler_json(DADOS / "space_machine.json", {}) or {}).items():
        cfg[k] = {**cfg[k], **v} if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    return cfg


def salvar_config(mudancas):
    """Grava só o que mudou em space_machine.json (o resto continua vindo do padrão)."""
    atual = ler_json(DADOS / "space_machine.json", {}) or {}
    for k, v in mudancas.items():
        atual[k] = {**atual.get(k, {}), **v} if isinstance(v, dict) else v
    gravar_json(DADOS / "space_machine.json", atual)


def _canal(pasta):
    cj = ler_json(pasta / "canal.json", {}) or {}
    return {
        "nome": cj.get("nome", pasta.name), "raiz": str(pasta), "ativo": cj.get("ativo", True),
        "formato": cj.get("formato") or FORMATO_PADRAO, "narracao": cj.get("narracao") or {},
        "idioma": cj.get("idioma", "en"), "tema": cj.get("tema", ""),
        "producoes": str(pasta / "producoes"), "conhecimento": str(pasta / "conhecimento"),
        # o motor é um só para todos os canais
        "python": sys.executable, "scripts": str(MOTOR / "busca" / "scripts"), "editor": str(MOTOR / "edicao_ae"),
    }


def config_canal(c):
    """config() com os modelos e o esforço do Claude DESTE canal por cima (canal.json › modelos/esforco).

    Que modelo o Claude usa em cada etapa é escolha de cada canal (painel › canal › Modelos do Claude):
    o config_padrao.json só diz com o que um canal começa, enquanto ninguém escolheu."""
    cfg = config()
    cj = ler_json(Path(c["raiz"]) / "canal.json", {}) or {}
    for chave in ("modelos", "esforco"):
        if isinstance(cj.get(chave), dict):
            cfg[chave] = {**cfg.get(chave, {}), **cj[chave]}
    return cfg


def canais():
    """Canal = pasta <dados>/canais/<slug>/ com canal.json."""
    if not CANAIS.exists():
        return {}
    return {p.name: _canal(p) for p in sorted(CANAIS.iterdir()) if (p / "canal.json").exists()}


def ambiente_motor(c):
    """Variáveis que os scripts do motor usam para achar o canal e os dados (motor/caminhos.py)."""
    return {**os.environ, "SM_CANAL": c["raiz"], "SM_DADOS": str(DADOS), "SM_PYTHON": sys.executable,
            "SM_AFTER": config().get("after_app", "Adobe After Effects 2026"), "PYTHONUNBUFFERED": "1"}
