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


class EmSegundoPlano(Caso):
    """roteiro.py: o vídeo nasce na hora e o roteiro é escrito por um processo solto, com o estado num arquivo."""
    formato = "cartum"

    def comecar(self, pid, obs="Só 2 tópicos."):
        import subprocess
        from space_machine import roteiro
        falso = subprocess.CompletedProcess([], 0, stdout=f"{pid}\n", stderr="")
        with mock.patch("space_machine.roteiro.subprocess.run", return_value=falso) as lancou:
            slug = roteiro.comecar(self.c, "Every Lost City Explained", obs)
        return self.prod / slug, lancou

    def test_o_video_nasce_na_hora_sem_capitulos_e_conta_como_rodando(self):
        import os
        from space_machine import estado, roteiro
        from space_machine.api.comum import _video
        vd, lancou = self.comecar(os.getpid())            # um processo vivo faz as vezes do que escreve
        self.assertIn("roteiro", lancou.call_args.args[0])
        self.assertTrue(vd.is_dir())
        self.assertEqual(estado.blocos_do_video(vd), [])
        est = roteiro.ler_estado(vd)
        self.assertEqual((est["status"], est["rodando"], est["obs"]), ("rodando", True, "Só 2 tópicos."))
        resumo = _video(self.slug, estado.video(self.slug, vd.name))
        self.assertEqual((resumo["escrevendo"], resumo["rodando"], resumo["coluna"]), (True, 1, "roteiro"))
        with self.assertRaises(ValueError):               # enquanto escreve, o vídeo não pode ser excluído
            gestao.excluir_video(self.c, vd.name)

    def test_escrever_cria_os_capitulos_e_guarda_o_roteiro(self):
        from space_machine import estado, roteiro
        vd, _ = self.comecar(1)
        passos = []
        marcar = roteiro.marcar
        with mock.patch("space_machine.motor_claude.chamar", return_value={"texto": CURTO}), \
             mock.patch("space_machine.roteiro.marcar", side_effect=lambda v, **c: passos.append(c.get("etapa")) or marcar(v, **c)):
            self.assertEqual(roteiro.escrever(vd), 0)
        self.assertEqual([b["nn"] for b in estado.blocos_do_video(vd)], ["01", "02"])
        self.assertEqual(fichas.roteiro(vd).read_text(), CURTO)
        self.assertEqual(roteiro.ler_estado(vd)["status"], "ok")
        self.assertTrue(any("conferindo o molde" in (p or "") for p in passos), passos)
        self.assertTrue(any("reescrevendo" in (p or "") for p in passos), passos)

    def test_quando_o_claude_falha_o_video_espera_voce_com_o_motivo(self):
        from space_machine import estado, roteiro
        from space_machine.api.comum import _video
        from space_machine.motor_claude import ErroClaude
        vd, _ = self.comecar(1)
        with mock.patch("space_machine.motor_claude.chamar", side_effect=ErroClaude("limite da assinatura")):
            self.assertEqual(roteiro.escrever(vd), 1)
        est = roteiro.ler_estado(vd)
        self.assertEqual(est["status"], "erro")
        self.assertIn("limite da assinatura", est["erro"])
        resumo = _video(self.slug, estado.video(self.slug, vd.name))
        self.assertEqual((resumo["escrevendo"], resumo["rodando"], resumo["esperando"]), (False, 0, 1))

    def test_processo_que_morreu_nao_fica_escrevendo_para_sempre(self):
        from space_machine import roteiro
        vd, _ = self.comecar(1)                           # pid 1 não é nosso: conta como encerrado? não — é o launchd
        (vd / "_estudio" / "roteiro.pid").write_text("999999")
        est = roteiro.ler_estado(vd)
        self.assertEqual((est["status"], est["rodando"]), ("erro", False))

    def test_parar_marca_como_parado(self):
        from space_machine import roteiro
        vd, _ = self.comecar(999999)
        roteiro.marcar(vd, status="rodando")
        roteiro.parar(vd)
        self.assertEqual(roteiro.ler_estado(vd)["status"], "parado")
        self.assertFalse((vd / "_estudio" / "roteiro.pid").exists())

    def test_titulo_repetido_ou_formato_sem_agente_e_recusado_antes_de_criar(self):
        from space_machine import roteiro
        self.comecar(1)
        with self.assertRaises(ValueError):
            self.comecar(1)
        (self.raiz / "canal.json").write_text('{"nome": "x", "formato": "explained"}')
        with self.assertRaises(ValueError):
            roteiro.comecar(self.c, "Outro Titulo", "")
        self.assertFalse((self.prod / "outro-titulo").exists())
