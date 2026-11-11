"""Base dos testes: uma pasta de dados de mentira, nunca a de verdade, e nada vai para o Lixo do Mac.

Rodar tudo:  .venv/bin/python -m unittest discover -s tests -t .

A pasta de dados (SM_DADOS) é lida quando o space_machine é importado, então ela é trocada AQUI, antes de qualquer
import do pacote: todo teste importa deste arquivo primeiro. Cada teste ganha um canal só dele.
"""
import atexit
import json
import os
import shutil
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

_DADOS = Path(tempfile.mkdtemp(prefix="space_machine_testes_")).resolve()
os.environ["SM_DADOS"] = str(_DADOS)
atexit.register(shutil.rmtree, _DADOS, ignore_errors=True)

from space_machine import limpeza, sistema  # noqa: E402

assert sistema.DADOS == _DADOS, "os testes não podem rodar em cima da pasta de dados de verdade"
LIXO = _DADOS / "LIXO"


def _lixo_de_teste():
    LIXO.mkdir(exist_ok=True)
    return LIXO


limpeza._destino_lixo = _lixo_de_teste        # o Lixo do Mac de quem roda os testes não é tocado

ROTEIRO = "Abertura antes do primeiro tópico.\n\n# Primeiro\nTexto do primeiro.\n\n# Segundo\nTexto do segundo.\n"


class Caso(unittest.TestCase):
    formato = "explained"

    def setUp(self):
        self.slug = self.id().split(".")[-1].replace("_", "-")[:60]
        self.raiz = sistema.CANAIS / self.slug
        shutil.rmtree(self.raiz, ignore_errors=True)
        shutil.rmtree(LIXO, ignore_errors=True)
        (self.raiz / "producoes").mkdir(parents=True)
        (self.raiz / "canal.json").write_text(json.dumps({"nome": self.slug, "formato": self.formato}))
        (self.raiz / ".env").write_text("")
        self.prod = self.raiz / "producoes"

    @property
    def c(self):
        return sistema.canais()[self.slug]

    def video(self, titulo="Um Video", roteiro=ROTEIRO):
        """Cria um vídeo pelo mesmo caminho do painel e devolve a pasta de produção dele."""
        from space_machine import gestao
        return self.prod / gestao.criar_video(self.c, titulo, roteiro)

    def mp4(self, arq, conteudo=b"mp4 de mentira"):
        arq = Path(arq)
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_bytes(conteudo)
        return arq

    def imagem(self, cor="blue"):
        from PIL import Image
        b = BytesIO()
        Image.new("RGB", (1280, 720), cor).save(b, "PNG")
        return b.getvalue()

    def arquivos(self, pasta):
        pasta = Path(pasta)
        return sorted(str(f.relative_to(pasta)) for f in pasta.rglob("*") if f.is_file() and f.name != ".DS_Store")

    def no_lixo(self):
        return self.arquivos(LIXO) if LIXO.is_dir() else []
