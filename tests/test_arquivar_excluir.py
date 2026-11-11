"""Arquivar (a produção sai, a ficha fica), excluir (lixeira do canal) e restaurar."""
import json

from tests.base import Caso

from space_machine import capas, estado, fichas, gestao, prontos


class Arquivar(Caso):
    def pronto(self, titulo="Video A"):
        vd = self.video(titulo)
        prontos.guardar(vd, self.mp4(vd / "final" / "x.mp4"))
        capas.salvar_thumbnail(vd, self.imagem(), "capa.png")
        gestao.salvar_video(self.slug, vd.name, status="publicado", data_pub="2026-10-20", link="http://x")
        return vd

    def test_arquivar_tira_a_producao_e_mantem_o_video_no_canal(self):
        vd = self.pronto()
        r = gestao.arquivar_video(self.c, vd.name)
        self.assertTrue(r["mp4"])
        self.assertFalse(vd.exists(), "a pasta de produção vai inteira para o Lixo")
        self.assertTrue(any("blocos/01/roteiro.txt" in f for f in self.no_lixo()))
        v = estado.videos(self.slug)[0]
        g = gestao.dados_video(self.slug, vd.name)
        self.assertEqual((v["slug"], v["titulo"], v["numero"], bool(v["arquivado"])), (vd.name, "Video A", 1, True))
        self.assertEqual((g["status"], g["data_pub"], g["link"]), ("publicado", "2026-10-20", "http://x"))
        self.assertEqual(gestao.coluna_do_video(v, g), "publicado")
        self.assertTrue(capas.thumbnail(vd))
        self.assertEqual(self.arquivos(self.raiz / "videos"), ["01 - Video A.mp4", "01 - Video A.png"])

    def test_arquivado_ainda_aceita_publicacao_e_thumbnail(self):
        vd = self.pronto()
        gestao.arquivar_video(self.c, vd.name)
        gestao.salvar_video(self.slug, vd.name, link="http://novo")
        capas.salvar_thumbnail(vd, self.imagem("red"), "outra.png")
        self.assertEqual(gestao.dados_video(self.slug, vd.name)["link"], "http://novo")
        self.assertEqual(capas.info_thumbnail(vd)["nome"], "outra.png")
        self.assertFalse(vd.exists(), "mexer na ficha não recria a pasta de produção")

    def test_arquivar_com_mp4_manda_o_video_pronto_junto(self):
        vd = self.pronto()
        gestao.arquivar_video(self.c, vd.name, com_mp4=True)
        self.assertEqual(self.arquivos(self.raiz / "videos"), [])
        self.assertIsNone(prontos.atual(vd))
        self.assertEqual(estado.video(self.slug, vd.name)["numero"], 1, "o número continua sendo do vídeo")

    def test_arquivar_video_antigo_leva_o_mp4_de_final_para_a_pasta_do_canal(self):
        vd = self.video("Video Antigo")
        self.mp4(vd / "final" / "Video Antigo.mp4")
        gestao.arquivar_video(self.c, vd.name)
        self.assertEqual(self.arquivos(self.raiz / "videos"), ["01 - Video Antigo.mp4"])

    def test_pasta_copiada_a_mao_nao_leva_o_mp4_do_video_de_origem(self):
        origem, copia = self.video("Origem"), self.video("Copia")
        mp4 = self.mp4(origem / "final" / "Origem.mp4")
        (copia / "final").mkdir()
        (copia / "final" / "estado.json").write_text(json.dumps({"mp4": str(mp4)}))    # como numa pasta duplicada
        gestao.arquivar_video(self.c, copia.name)
        self.assertTrue(mp4.exists(), "o MP4 do outro vídeo fica onde está")
        self.assertIsNone(prontos.atual(copia))

    def test_nao_arquiva_duas_vezes_nem_cria_video_com_titulo_de_arquivado(self):
        vd = self.pronto()
        gestao.arquivar_video(self.c, vd.name)
        with self.assertRaises(ValueError):
            gestao.arquivar_video(self.c, vd.name)
        with self.assertRaises(ValueError):
            self.video("Video A")

    def test_nao_arquiva_com_producao_rodando(self):
        import os
        vd = self.pronto()
        (vd / "blocos" / "01" / "_estudio").mkdir()
        (vd / "blocos" / "01" / "_estudio" / "pid").write_text(str(os.getpid()))      # um processo vivo
        with self.assertRaises(ValueError):
            gestao.arquivar_video(self.c, vd.name)
        self.assertTrue(vd.exists())


class Excluir(Caso):
    pronto = Arquivar.pronto

    def test_excluir_leva_producao_ficha_e_mp4_e_restaurar_devolve(self):
        vd = self.pronto()
        nome = gestao.excluir_video(self.c, vd.name)
        self.assertEqual(estado.videos(self.slug), [])
        self.assertEqual(self.arquivos(self.raiz / "videos"), [])
        self.assertFalse((self.raiz / "fichas" / vd.name).exists())
        self.assertEqual(self.no_lixo(), [], "excluir vai para a lixeira do canal, não para o Lixo do Mac")
        self.assertEqual([(i["titulo"], i["tipo"]) for i in gestao.lixeira(self.c)], [("Video A", "video")])
        gestao.restaurar_video(self.c, nome)
        v = estado.videos(self.slug)[0]
        self.assertEqual((v["numero"], prontos.atual(vd).name), (1, "01 - Video A.mp4"))
        self.assertEqual(gestao.dados_video(self.slug, vd.name)["data_pub"], "2026-10-20")
        self.assertTrue(capas.thumbnail(vd))
        self.assertTrue((vd / "blocos" / "01" / "roteiro.txt").exists())

    def test_excluir_e_restaurar_um_arquivado(self):
        vd = self.pronto()
        gestao.arquivar_video(self.c, vd.name)
        nome = gestao.excluir_video(self.c, vd.name)
        self.assertEqual(estado.videos(self.slug), [])
        gestao.restaurar_video(self.c, nome)
        v = estado.videos(self.slug)[0]
        self.assertTrue(v["arquivado"])
        self.assertFalse(vd.exists(), "arquivado restaurado volta só com a ficha e o MP4")
        self.assertEqual(prontos.atual(vd).name, "01 - Video A.mp4")
        self.assertTrue(fichas.roteiro(vd).is_file())

    def test_limpar_bloco_deixa_so_o_roteiro(self):
        vd = self.video("Video A")
        b = vd / "blocos" / "01"
        (b / "narracao.mp3").write_bytes(b"x")
        self.mp4(vd / "edicao" / "bloco 1.mp4")
        r = gestao.limpar_bloco(self.c, vd.name, "01")
        self.assertEqual(r["quantos"], 2)
        self.assertEqual(self.arquivos(b), ["roteiro.txt"])
        self.assertFalse((vd / "edicao" / "bloco 1.mp4").exists())

    def test_excluir_bloco_e_restaurar(self):
        vd = self.video("Video A")
        self.mp4(vd / "edicao" / "bloco 1.mp4")
        r = gestao.excluir_bloco(self.c, vd.name, "01")
        self.assertFalse((vd / "blocos" / "01").exists())
        self.assertFalse((vd / "edicao" / "bloco 1.mp4").exists())
        gestao.restaurar_video(self.c, r["lixeira"])
        self.assertTrue((vd / "blocos" / "01" / "roteiro.txt").exists())
        self.assertTrue((vd / "edicao" / "bloco 1.mp4").exists())
