"""A ficha do vídeo: o registro do canal que não depende da pasta de produção."""
import json

from tests.base import Caso

from space_machine import capas, estado, fichas, gestao, prontos
from space_machine.motor_claude import _banco


class Fichas(Caso):
    def test_video_novo_nasce_com_ficha_e_producao_separadas(self):
        vd = self.video("Video Novo")
        self.assertEqual(self.arquivos(self.raiz / "fichas" / vd.name), ["ficha.json", "roteiro_completo.txt"])
        self.assertEqual(set(json.loads((vd / "estudio_video.json").read_text())), {"titulo", "fluxo"})
        self.assertFalse((vd / "roteiro_completo.txt").exists())

    def test_publicacao_e_thumbnail_ficam_na_ficha(self):
        vd = self.video("Video Novo")
        gestao.salvar_video(self.slug, vd.name, status="agendado", data_pub="2026-12-01", descricao=" texto ")
        capas.salvar_thumbnail(vd, self.imagem(), "capa.png")
        g = gestao.dados_video(self.slug, vd.name)
        self.assertEqual((g["status"], g["data_pub"], g["descricao"]), ("agendado", "2026-12-01", "texto"))
        self.assertEqual(capas.thumbnail(vd).parent, self.raiz / "fichas" / vd.name)
        self.assertFalse(list(vd.glob("thumbnail*")))
        semanas, _ = gestao.calendario(self.slug, 2026, 12)
        self.assertEqual([v["v"]["slug"] for s in semanas for d in s for v in d["videos"]], [vd.name])

    def test_video_de_antes_ganha_a_ficha_sozinho(self):
        vd = self.prod / "video-velho"
        (vd / "blocos" / "01").mkdir(parents=True)
        (vd / "blocos" / "01" / "roteiro.txt").write_text("# Um\nTexto.\n")
        (vd / "estudio_video.json").write_text(json.dumps({"titulo": "Video Velho", "fluxo": "video", "numero": 4,
                                                            "pronto": "04 - Video Velho.mp4"}))
        (vd / "roteiro_completo.txt").write_text("# Um\nTexto.\n")
        (vd / "thumbnail.png").write_bytes(self.imagem())
        (vd / "thumbnail.json").write_text('{"nome": "t.png"}')
        self.mp4(self.raiz / "videos" / "04 - Video Velho.mp4")
        con = _banco()
        con.execute("create table if not exists videos_gestao (canal text, slug text, status text, titulo_pub text, "
                    "descricao text, tags text, data_pub text, notas text, link text, atualizado text, "
                    "primary key (canal, slug))")
        con.execute("insert or replace into videos_gestao values (?, 'video-velho', 'publicado', 'Titulo Pub', 'desc', "
                    "'a,b', '2026-10-20', 'nota', 'http://x', '2026-10-21')", (self.slug,))
        con.commit()
        con.close()

        v = estado.videos(self.slug)[0]                       # ler o canal é o que migra
        g = gestao.dados_video(self.slug, "video-velho")
        self.assertEqual((v["titulo"], v["numero"], v["fluxo"]), ("Video Velho", 4, "video"))
        self.assertEqual((g["status"], g["titulo_pub"], g["data_pub"], g["link"]), ("publicado", "Titulo Pub", "2026-10-20", "http://x"))
        self.assertEqual(self.arquivos(self.raiz / "fichas" / "video-velho"),
                         ["ficha.json", "roteiro_completo.txt", "thumbnail.json", "thumbnail.png"])
        self.assertEqual(self.arquivos(vd), ["blocos/01/roteiro.txt", "estudio_video.json"])
        self.assertEqual(json.loads((vd / "estudio_video.json").read_text()), {"titulo": "Video Velho", "fluxo": "video"})
        self.assertEqual(prontos.atual(vd).name, "04 - Video Velho.mp4")
        self.assertEqual(gestao.coluna_do_video(v, g), "publicado")

    def test_migrar_duas_vezes_nao_muda_nada(self):
        vd = self.video("Video Novo")
        antes = fichas.ler(vd)
        fichas.garantir(vd)
        fichas.garantir(vd)
        self.assertEqual(fichas.ler(vd), antes)
