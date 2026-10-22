"""Prompts do canal: arquivos .md em <dados>/canais/<canal>/prompts/ (ex.: o prompt de fazer roteiros).

O nome do arquivo é o título do prompt ("Roteiro do vídeo.md"), para ficar legível no Finder e na pasta de
conhecimento. Apagar no painel move para prompts/_lixeira/ (nada se perde). Não confundir com formatos/<formato>/prompts/,
que são os prompts das etapas do motor.
"""
import re
import time
from pathlib import Path

from .sistema import CANAIS

EXTENSOES = (".md", ".txt", ".markdown")
LIMITE = 2 * 1024 * 1024


def pasta(slug, criar=True):
    """A pasta só nasce quando um prompt é salvo ou importado (abrir a aba não cria nada)."""
    p = CANAIS / slug / "prompts"
    if criar:
        p.mkdir(parents=True, exist_ok=True)
    return p


def nome_de(titulo):
    """Título → nome de arquivo seguro (sem barras nem caracteres que o Finder recusa)."""
    t = re.sub(r'[/\\:*?"<>|\x00-\x1f]', " ", (titulo or "").strip())
    t = re.sub(r"\s+", " ", t).strip(" .")[:120]
    if not t:
        raise ValueError("Dê um título ao prompt.")
    return t + ".md"


def _arquivo(slug, nome):
    if not nome or "/" in nome or "\\" in nome or nome.startswith(".") or not nome.endswith(".md"):
        raise ValueError("prompt não encontrado")
    return pasta(slug, criar=False) / nome


def _resumo(arq):
    texto = arq.read_text(errors="replace")
    corpo = "\n".join(l for l in texto.splitlines() if l.strip() and not l.startswith("#"))
    return {"nome": arq.name, "titulo": arq.stem, "palavras": len(texto.split()), "mudou": arq.stat().st_mtime,
            "previa": re.sub(r"\s+", " ", re.sub(r"[*_`>#-]", "", corpo)).strip()[:160]}


def listar(slug):
    return sorted((_resumo(f) for f in pasta(slug, criar=False).glob("*.md") if f.is_file()), key=lambda p: -p["mudou"])


def ler(slug, nome):
    arq = _arquivo(slug, nome)
    if not arq.is_file():
        raise ValueError("prompt não encontrado")
    return {**_resumo(arq), "texto": arq.read_text(errors="replace")}


def salvar(slug, titulo, texto, nome_antigo=""):
    """Cria ou atualiza. Mudar o título renomeia o arquivo. ValueError se já existe outro com o mesmo título."""
    novo = pasta(slug) / nome_de(titulo)
    antigo = _arquivo(slug, nome_antigo) if nome_antigo else None
    if novo.exists() and (not antigo or novo.name.lower() != antigo.name.lower()):
        raise ValueError(f"Já existe um prompt chamado \"{novo.stem}\".")
    if antigo and antigo.exists() and antigo.name != novo.name:
        antigo.rename(novo)
    tmp = novo.with_name(f".{novo.name}.tmp")
    tmp.write_text(texto if texto.endswith("\n") or not texto else texto + "\n")
    tmp.replace(novo)
    return novo.name


def importar(slug, nome_arquivo, dados):
    """Um .md (ou .txt) que você já tem. Se o nome já existe, ganha " (2)", " (3)"..."""
    nome_arquivo = Path(nome_arquivo or "").name
    if Path(nome_arquivo).suffix.lower() not in EXTENSOES:
        raise ValueError(f"{nome_arquivo}: envie arquivos .md ou .txt")
    if len(dados) > LIMITE:
        raise ValueError(f"{nome_arquivo}: grande demais para um prompt (máx. 2 MB)")
    try:
        texto = dados.decode("utf-8")
    except UnicodeDecodeError:
        texto = dados.decode("latin-1")
    base = nome_de(Path(nome_arquivo).stem)[:-3]
    alvo, n = pasta(slug) / f"{base}.md", 2
    while alvo.exists():
        alvo, n = pasta(slug) / f"{base} ({n}).md", n + 1
    alvo.write_text(texto)
    return alvo.name


def apagar(slug, nome):
    arq = _arquivo(slug, nome)
    if not arq.is_file():
        raise ValueError("prompt não encontrado")
    lixeira = pasta(slug) / "_lixeira"
    lixeira.mkdir(exist_ok=True)
    arq.rename(lixeira / f"{arq.stem} ({time.strftime('%Y%m%d-%H%M%S')}).md")
