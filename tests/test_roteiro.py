"""O agente de roteiro: o título e as instruções que você manda junto ao criar o vídeo."""
from unittest import mock

from tests.base import Caso

from space_machine import fichas, gestao

CURTO = "# Primeiro\nPrimeiro is a place that people left long ago.\n\n# Segundo\nSegundo is another place nobody visits now.\n"


class Instrucoes(Caso):
    formato = "cartum"        # tem agente de roteiro (formato.json › roteiro.modelo)

    def criar(self, obs):
        pedidos = []

        def claude(etapa, sistema, texto, **kw):
            pedidos.append(texto)
            return {"texto": CURTO}

        with mock.patch("space_machine.motor_claude.chamar", claude):
            slug = gestao.criar_video(self.c, "Every Lost City Explained", "", obs)
        return self.prod / slug, pedidos

    def test_as_instrucoes_vao_junto_com_o_titulo(self):
        vd, pedidos = self.criar("Só 2 tópicos. Tom leve.\nNão fale de política.")
        self.assertIn("Título do vídeo: Every Lost City Explained", pedidos[0])
        self.assertIn("Instruções de quem produz", pedidos[0])
        self.assertIn("Só 2 tópicos. Tom leve.\nNão fale de política.", pedidos[0])
        self.assertEqual(fichas.ler(vd)["instrucoes_roteiro"], "Só 2 tópicos. Tom leve.\nNão fale de política.")
        self.assertEqual(fichas.roteiro(vd).read_text(), CURTO)

    def test_a_correcao_do_molde_nao_passa_por_cima_do_que_voce_pediu(self):
        _, pedidos = self.criar("Só 2 tópicos.")
        self.assertEqual(len(pedidos), 2, "2 tópicos está fora do molde do cartum: o sistema pede uma correção")
        self.assertIn("Fora do molde", pedidos[1])
        self.assertIn("valem elas", pedidos[1])

    def test_sem_instrucoes_o_pedido_e_o_de_sempre(self):
        vd, pedidos = self.criar("")
        self.assertNotIn("Instruções de quem produz", pedidos[0])
        self.assertNotIn("valem elas", pedidos[1])
        self.assertNotIn("instrucoes_roteiro", fichas.ler(vd))

    def test_roteiro_colado_nao_chama_o_claude_nem_guarda_instrucao(self):
        with mock.patch("space_machine.motor_claude.chamar", side_effect=AssertionError("não era para chamar")):
            slug = gestao.criar_video(self.c, "Outro Video", CURTO, "isto não se aplica")
        self.assertNotIn("instrucoes_roteiro", fichas.ler(self.prod / slug))
