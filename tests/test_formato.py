"""Trocar o formato de um canal e o prompt de roteiro dele."""
import json

from tests.base import Caso

from space_machine import formato_canal as fc
from space_machine import gestao, prontos


class TrocarFormato(Caso):
    formato = "bestiario"

    def test_recusa_com_video_no_meio_da_producao(self):
        vd = self.video("No Meio")
        (vd / "blocos" / "01" / "narracao.mp3").write_bytes(b"x")
        conf = fc.conferir(self.slug, "cartum")
        self.assertEqual((conf["bloqueios"], [v["slug"] for v in conf["em_producao"]]), (["producao"], [vd.name]))
        with self.assertRaises(ValueError):
            fc.trocar(self.slug, "cartum")
        self.assertEqual(self.c["formato"], "bestiario")

    def test_redivide_o_video_que_so_tem_roteiro(self):
        vd = self.video("So Roteiro")
        antes = (vd / "blocos" / "01" / "roteiro.txt").read_text()
        self.assertNotIn("fluxo", json.loads((vd / "estudio_video.json").read_text()))      # bestiário: bloco a bloco
        r = fc.trocar(self.slug, "cartum")
        self.assertEqual((self.c["formato"], r["redivididos"]), ("cartum", ["So Roteiro"]))
        depois = (vd / "blocos" / "01" / "roteiro.txt").read_text()
        self.assertNotEqual(antes, depois)
        self.assertEqual(depois, "# Primeiro\nTexto do primeiro.\n")                        # cartum: o nome é da 1ª frase
        self.assertEqual(json.loads((vd / "estudio_video.json").read_text())["fluxo"], "video")
        self.assertTrue(any("blocos/01/roteiro.txt" in f for f in self.no_lixo()), "os blocos de antes vão para o Lixo")

    def test_video_pronto_e_arquivado_nao_impedem(self):
        a, b = self.video("Pronto"), self.video("Arquivado")
        for vd in (a, b):
            prontos.guardar(vd, self.mp4(vd / "final" / "x.mp4"))
        gestao.arquivar_video(self.c, b.name)
        conf = fc.conferir(self.slug, "cartum")
        self.assertEqual((conf["bloqueios"], conf["prontos"], conf["arquivados"]), ([], 1, 1))

    def test_mesmo_formato_ou_formato_que_nao_existe(self):
        for alvo in ("bestiario", "nao-existe"):
            with self.assertRaises(ValueError):
                fc.conferir(self.slug, alvo)

    def test_avisa_da_chave_que_o_formato_novo_pede(self):
        fc.trocar(self.slug, "cartum")
        self.assertEqual(fc.conferir(self.slug, "bestiario")["chaves_faltando"], ["GEMINI_API_KEY"])
        (self.raiz / ".env").write_text("GEMINI_API_KEY=abc\n")
        self.assertEqual(fc.conferir(self.slug, "bestiario")["chaves_faltando"], [])


class PromptDeRoteiro(Caso):
    formato = "bestiario"

    def test_sem_alteracao_vale_o_do_formato(self):
        p = fc.prompt_roteiro(self.slug)
        self.assertEqual((p["origem"], p["texto"]), ("formato", gestao.modelo_roteiro_do_formato("bestiario")))
        self.assertEqual(gestao._modelo_roteiro(self.c), p["texto"])

    def test_salvar_o_seu_e_voltar_ao_do_formato(self):
        p = fc.salvar_prompt_roteiro(self.slug, "Meu prompt.\n")
        self.assertEqual((p["origem"], gestao._modelo_roteiro(self.c)), ("canal", "Meu prompt.\n"))
        fc.voltar_ao_do_formato(self.slug)
        self.assertEqual(fc.prompt_roteiro(self.slug)["origem"], "formato")
        self.assertEqual(len(list((self.raiz / "prompts" / "_lixeira").iterdir())), 1, "o seu fica guardado")

    def test_copia_igual_a_do_formato_nao_conta_como_sua(self):
        (self.raiz / "prompts").mkdir()
        (self.raiz / "prompts" / gestao.PROMPT_ROTEIRO).write_text(gestao.modelo_roteiro_do_formato("bestiario"))
        self.assertEqual(fc.prompt_roteiro(self.slug)["origem"], "formato")

    def test_troca_de_formato_tira_o_prompt_antigo_de_uso_ou_mantem_se_voce_pedir(self):
        fc.salvar_prompt_roteiro(self.slug, "Meu prompt.\n")
        r = fc.trocar(self.slug, "cartum", manter_prompt=True)
        self.assertEqual((r["prompt_saiu"], fc.prompt_roteiro(self.slug)["origem"]), (False, "canal"))
        r = fc.trocar(self.slug, "bestiario")
        self.assertEqual((r["prompt_saiu"], fc.prompt_roteiro(self.slug)["origem"]), (True, "formato"))

    def test_formato_que_nao_escreve_roteiro(self):
        fc.trocar(self.slug, "explained")
        p = fc.prompt_roteiro(self.slug)
        self.assertEqual((p["origem"], p["escreve"]), ("nenhum", False))
