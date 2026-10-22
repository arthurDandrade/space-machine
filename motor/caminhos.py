"""Onde fica cada coisa no Space Machine: o motor (este repo) é um só; os dados ficam fora dele.

  SM_DADOS  pasta de dados: space_machine.json, .env (token do Claude), cache/, referencias/, canais/
  SM_CANAL  pasta de um canal: canal.json, .env (chaves do canal), identidade/, conhecimento/, producoes/

O orquestrador (space_machine) sempre passa as duas variáveis. Rodando um script à mão, elas são deduzidas do
caminho do bloco/projeto passado na linha de comando (sobe as pastas até achar um canal.json).
"""
import json
import os
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
REPO = MOTOR.parent
_CACHE_JSON = {}


def _achar_canal():
    for arg in sys.argv[1:]:
        p = Path(arg).expanduser()
        if not p.exists():
            continue
        for d in [p.resolve()] + list(p.resolve().parents):
            if (d / "canal.json").exists():
                return d
    return None


def canal():
    if os.environ.get("SM_CANAL"):
        return Path(os.environ["SM_CANAL"])
    achado = _achar_canal()
    if achado:
        os.environ["SM_CANAL"] = str(achado)
        return achado
    raise SystemExit("Não sei de qual canal é este trabalho: rode pelo Space Machine (python -m space_machine ...) "
                     "ou defina SM_CANAL=<pasta do canal>.")


def dados():
    if os.environ.get("SM_DADOS"):
        return Path(os.environ["SM_DADOS"])
    return canal().parent.parent          # <dados>/canais/<slug>


def _json(p):
    p = Path(p)
    if p not in _CACHE_JSON:
        try:
            _CACHE_JSON[p] = json.loads(p.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            _CACHE_JSON[p] = {}
    return _CACHE_JSON[p]


def canal_json():
    return _json(canal() / "canal.json")


def identidade():
    return canal_json().get("identidade", {})


def regras():
    """Regras do TEMA do canal (o que é do formato fica no código e em formatos/): ver canal.json["regras"]."""
    return canal_json().get("regras", {})


def env(nome, padrao=None):
    """Chave do canal: variável de ambiente > <canal>/.env > <dados>/.env."""
    if os.environ.get(nome):
        return os.environ[nome]
    for arq in (canal() / ".env", dados() / ".env"):
        if arq.exists():
            for linha in arq.read_text().splitlines():
                k, sep, v = linha.partition("=")
                if sep and k.strip() == nome:
                    return v.strip().strip('"').strip("'")
    return padrao


def cache():
    return dados() / "cache"


# Formato do vídeo: canal.json["formato"] aponta para formatos/<nome>/. Canal de antes de 2026-10-22 não tem
# o campo e continua no explained, o único formato que havia.
FORMATO_PADRAO = "explained"
FORMATOS = REPO / "formatos"


def nome_formato():
    return canal_json().get("formato") or FORMATO_PADRAO


def formato(nome=None):
    """formatos/<nome>/: o que é do FORMATO (conhecimento, regras do storyboard, modelo do After, medidas do QA),
    igual para todos os canais dele. Sem o nome, o formato do canal deste trabalho."""
    return FORMATOS / (nome or nome_formato())


def ficha(nome=None):
    """formatos/<nome>/formato.json: o que o código precisa saber para rodar este formato."""
    return _json(formato(nome) / "formato.json")


def do_formato(arquivo, nome=None, exigir=True):
    """Um arquivo do formato, pelo caminho que a ficha dá. `arquivo` é a chave na ficha ("storyboard.regras") ou
    o nome do arquivo direto. Erro claro quando o formato não trouxe o seu (exigir=False para quem vai gerá-lo)."""
    alvo = ficha(nome)
    for parte in arquivo.split("."):
        alvo = alvo.get(parte) if isinstance(alvo, dict) else None
    p = formato(nome) / (alvo if isinstance(alvo, str) else arquivo)
    if exigir and not p.exists():
        raise SystemExit(f"o formato \"{nome or nome_formato()}\" não tem \"{arquivo}\": falta {p} "
                         f"(ou o caminho dele em {formato(nome) / 'formato.json'})")
    return p


def formatos():
    """Todos os formatos do repo, com a ficha de cada um, para a pessoa escolher."""
    out = {}
    for d in sorted(FORMATOS.iterdir()) if FORMATOS.is_dir() else []:
        if (d / "formato.json").exists():
            f = _json(d / "formato.json")
            out[d.name] = {"nome": f.get("nome", d.name), "resumo": f.get("resumo", "")}
    return out


def referencias():
    """Vídeos de referência do formato e as detecções deles (não vão no repo: direito autoral)."""
    return dados() / "referencias" / formato().name


# Narração: qual serviço de TTS este canal usa (canal.json["narracao"]["provedor"]). Canal de antes de
# 2026-10-22 não tem o campo e continua no Fish Audio, o único que havia.
PROVEDOR_NARRACAO_PADRAO = "fishaudio"


def narracao():
    """canal.json["narracao"]: {"provedor": "fishaudio"|"elevenlabs"}."""
    n = canal_json().get("narracao") or {}
    return {"provedor": n.get("provedor") or PROVEDOR_NARRACAO_PADRAO, **n}


def config_busca():
    """Config do buscador: padrão do motor (motor/busca/config.json) com canal.json["busca"] por cima."""
    cfg = dict(_json(MOTOR / "busca" / "config.json"))
    cfg.update(canal_json().get("busca", {}))
    return cfg


def config_sistema():
    return _json(dados() / "space_machine.json")
