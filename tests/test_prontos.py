"""A pasta de vídeos prontos do canal: numeração, um arquivo por vídeo, capa ao lado."""
from tests.base import Caso

from space_machine import capas, gestao, prontos


class Prontos(Caso):
    def test_numera_na_ordem_da_entrega(self):
        a, b = self.video("Video A"), self.video("Video B")
        pa = prontos.guardar(a, self.mp4(a / "final" / "x.mp4"))
        pb = prontos.guardar(b, self.mp4(b / "final" / "x.mp4"))
        self.assertEqual([pa.name, pb.name], ["01 - Video A.mp4", "02 - Video B.mp4"])
        self.assertEqual(pa.parent, self.raiz / "videos")
        self.assertFalse((a / "final" / "x.mp4").exists(), "o MP4 muda de pasta, não é copiado")

    def test_entregar_de_novo_deixa_uma_versao_so(self):
        a = self.video("Video A")
        prontos.guardar(a, self.mp4(a / "final" / "x.mp4", b"primeira"))
        prontos.guardar(a, self.mp4(a / "final" / "x.mp4", b"segunda"))
        self.assertEqual(self.arquivos(self.raiz / "videos"), ["01 - Video A.mp4"])
        self.assertEqual(prontos.atual(a).read_bytes(), b"segunda")
        self.assertEqual(len(self.no_lixo()), 1, "a versão anterior vai para o Lixo, não some")
        self.assertFalse((a / "final" / "anteriores").exists())

    def test_o_numero_nao_muda_e_nao_e_reaproveitado(self):
        a, b = self.video("Video A"), self.video("Video B")
        prontos.guardar(a, self.mp4(a / "final" / "x.mp4"))
        prontos.guardar(b, self.mp4(b / "final" / "x.mp4"))
        gestao.excluir_video(self.c, b.name)                       # o 02 vai para a lixeira com o número dele
        c = self.video("Video C")
        self.assertEqual(prontos.guardar(c, self.mp4(c / "final" / "x.mp4")).name, "03 - Video C.mp4")
        prontos.guardar(a, self.mp4(a / "final" / "x.mp4"))
        self.assertEqual(prontos.numero(a), 1)

    def test_thumbnail_fica_ao_lado_do_mp4(self):
        a = self.video("Video A")
        prontos.guardar(a, self.mp4(a / "final" / "x.mp4"))
        capas.salvar_thumbnail(a, self.imagem(), "capa.png")
        self.assertEqual(self.arquivos(self.raiz / "videos"), ["01 - Video A.mp4", "01 - Video A.png"])
        capas.remover_thumbnail(a)
        self.assertEqual(self.arquivos(self.raiz / "videos"), ["01 - Video A.mp4"])

    def test_titulo_com_caractere_proibido_vira_nome_de_arquivo(self):
        a = self.video('Isto: "e" aquilo/outro')
        nome = prontos.guardar(a, self.mp4(a / "final" / "x.mp4")).name
        self.assertFalse(set('/:"\\') & set(nome), nome)
