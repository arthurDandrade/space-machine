"""O que é do Space Machine inteiro: o Mac acordado durante uma produção."""
import os
from unittest import mock

from tests.base import Caso

from space_machine import sistema


class ManterAcordado(Caso):
    def test_liga_o_caffeinate_preso_a_este_processo(self):
        with mock.patch("shutil.which", return_value="/usr/bin/caffeinate"), mock.patch("subprocess.Popen") as abrir:
            self.assertIsNotNone(sistema.manter_acordado())
        cmd = abrir.call_args.args[0]
        self.assertEqual(cmd, ["caffeinate", "-i", "-w", str(os.getpid())])

    def test_desligado_na_configuracao_nao_liga(self):
        with mock.patch.object(sistema, "config", return_value={"manter_acordado": False}), \
             mock.patch("shutil.which", return_value="/usr/bin/caffeinate"), mock.patch("subprocess.Popen") as abrir:
            self.assertIsNone(sistema.manter_acordado())
        abrir.assert_not_called()

    def test_fora_do_mac_nao_quebra(self):
        with mock.patch("shutil.which", return_value=None), mock.patch("subprocess.Popen") as abrir:
            self.assertIsNone(sistema.manter_acordado())
        abrir.assert_not_called()

    def test_os_comandos_de_producao_seguram_o_mac(self):
        from space_machine import __main__ as cli
        for cmd in ("rodar", "fila", "final", "thumb", "roteiro", "reels"):
            self.assertIn(cmd, cli.DEMORADOS)
        for cmd in ("painel", "checar", "limpar", "atualizar"):
            self.assertNotIn(cmd, cli.DEMORADOS)
