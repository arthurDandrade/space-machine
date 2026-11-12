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


class CoresDoVideo(Caso):
    """A cor escolhida em canal › Identidade vale no vídeo dos formatos que têm visual próprio (o cartum)."""
    formato = "cartum"

    def setUp(self):
        super().setUp()
        import sys
        sys.path.insert(0, str(sistema.MOTOR))
        import caminhos
        self.caminhos = caminhos
        self.antes = os.environ.get("SM_CANAL")
        os.environ["SM_CANAL"] = str(self.raiz)

    def tearDown(self):
        os.environ.pop("SM_CANAL", None) if self.antes is None else os.environ.update(SM_CANAL=self.antes)

    def canal(self, **campos):
        import json
        (self.raiz / "canal.json").write_text(json.dumps({"nome": "x", "formato": self.formato, **campos}))

    def test_sem_identidade_vale_a_cor_medida_do_formato(self):
        self.assertEqual(self.caminhos.visual()["cor_fundo"], sistema.ficha_formato("cartum")["visual"]["cor_fundo"])

    def test_a_cor_da_identidade_entra_no_video(self):
        self.canal(identidade={"cor_fundo": "#F2E7D3", "cor_destaque": "#0B2A6F", "cor_caixa": "#123456"})
        v = self.caminhos.visual()
        self.assertEqual((v["cor_fundo"], v["cor_destaque"]), ("#F2E7D3", "#0B2A6F"))
        self.assertEqual(v["cor_texto"], sistema.ficha_formato("cartum")["visual"]["cor_texto"], "o que não foi escolhido fica o do formato")
        self.assertNotIn("cor_caixa", v, "caixa não existe no cartum")
        self.assertEqual(v["fonte"], sistema.ficha_formato("cartum")["visual"]["fonte"], "a fonte do desenho é do formato")

    def test_o_gerador_do_cartum_le_a_mesma_cor(self):
        import importlib.util
        self.canal(identidade={"cor_fundo": "#F2E7D3"})
        spec = importlib.util.spec_from_file_location("gerar_cartum", sistema.FORMATOS / "cartum" / "gerar.py")
        gerar = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gerar)
        self.assertEqual(gerar.visual()["cor_fundo"], "#F2E7D3")

    def test_canal_json_visual_ainda_manda_por_ultimo(self):
        self.canal(identidade={"cor_fundo": "#F2E7D3"}, visual={"cor_fundo": "#000000", "fonte": "Outra"})
        v = self.caminhos.visual()
        self.assertEqual((v["cor_fundo"], v["fonte"]), ("#000000", "Outra"))

    def test_cada_formato_diz_quais_cores_usa(self):
        self.assertEqual(sistema.cores_do_video("cartum"), ["cor_fundo", "cor_texto", "cor_destaque"])
        self.assertEqual(sistema.cores_do_video("bestiario"), [])
        self.assertEqual(len(sistema.cores_do_video("explained")), 5)
        self.assertEqual(sistema.formatos()["cartum"]["cores"]["cor_fundo"], sistema.ficha_formato("cartum")["visual"]["cor_fundo"])
