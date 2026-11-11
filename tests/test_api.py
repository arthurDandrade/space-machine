"""As rotas da API do painel, divididas por assunto em space_machine/api/."""
from collections import Counter

from tests.base import Caso

from space_machine import api as pacote
from space_machine.servidor import app


def rotas(lista):
    for r in lista:
        if hasattr(r, "original_router"):            # roteador incluído: as rotas estão dentro dele
            yield from rotas(r.original_router.routes)
        elif hasattr(r, "methods"):
            yield r


class Rotas(Caso):
    def test_nenhum_endereco_repetido(self):
        vistos = Counter((m, r.path) for r in rotas(app.routes) for m in r.methods)
        self.assertEqual([k for k, n in vistos.items() if n > 1], [])

    def test_todo_arquivo_de_rotas_entra_no_app(self):
        do_app = {r.endpoint for r in rotas(app.routes)}
        for nome in ("painel", "videos", "blocos", "planejamento", "canal", "sistema", "pesquisa"):
            modulo = getattr(pacote, nome)
            proprias = [r for r in modulo.api.routes if hasattr(r, "methods")]
            self.assertTrue(proprias, nome)
            self.assertTrue(all(r.endpoint in do_app for r in proprias), nome)
            self.assertTrue(all(r.path.startswith("/api/") for r in proprias), nome)

    def test_video_arquivado_existe_para_o_painel_mas_nao_para_produzir(self):
        from fastapi import HTTPException
        from space_machine import gestao, prontos
        from space_machine.api import videos
        from space_machine.api.comum import _video_dir
        vd = self.video("Video A")
        prontos.guardar(vd, self.mp4(vd / "final" / "x.mp4"))
        gestao.arquivar_video(self.c, vd.name)
        self.assertEqual(_video_dir(self.slug, vd.name), vd)
        detalhe = videos.detalhe_video(self.slug, vd.name)
        self.assertTrue(detalhe["arquivado"])
        self.assertTrue(detalhe["final"]["mp4_url"])
        with self.assertRaises(HTTPException) as erro:
            videos._producao_dir(self.slug, vd.name)
        self.assertEqual(erro.exception.status_code, 409)
        with self.assertRaises(HTTPException) as erro:
            _video_dir(self.slug, "nao-existe")
        self.assertEqual(erro.exception.status_code, 404)
