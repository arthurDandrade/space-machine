"""O que vai para o Lixo: a versão anterior de cada coisa, e o cache de imagens da busca."""
import hashlib
import os
import sys
import time

from tests.base import LIXO, Caso

from space_machine import capas, final, limpeza, sistema

sys.path.insert(0, str(sistema.MOTOR / "busca" / "scripts"))
import comum  # noqa: E402  (motor/busca/scripts/comum.py)
import caminhos  # noqa: E402


class VersaoAnterior(Caso):
    def test_vai_para_o_lixo_com_a_data_no_nome_e_o_caminho_do_canal(self):
        vd = self.video("Video A")
        aep = vd / "final" / "final.aep"
        self.mp4(aep, b"projeto")
        final._guardar_anterior(aep)
        self.assertFalse(aep.exists())
        (no_lixo,) = self.no_lixo()
        self.assertRegex(no_lixo, rf"^canais/{self.slug}/producoes/{vd.name}/final/final_\d{{8}}-\d{{6}}\.aep$")
        self.assertFalse((vd / "final" / "anteriores").exists())

    def test_arquivo_que_nao_existe_nao_da_erro(self):
        self.assertIsNone(limpeza.versao_anterior(self.raiz / "nada.mp4"))

    def test_trocar_e_remover_a_thumbnail_nao_deixa_copia_na_pasta(self):
        vd = self.video("Video A")
        capas.salvar_thumbnail(vd, self.imagem("blue"), "a.png")
        capas.salvar_thumbnail(vd, self.imagem("red"), "b.jpg".replace("jpg", "png"))
        capas.remover_thumbnail(vd)
        self.assertEqual(self.arquivos(self.raiz / "fichas" / vd.name), ["ficha.json", "roteiro_completo.txt"])
        self.assertEqual(len(self.no_lixo()), 2)

    def test_mandar_para_o_lixo_devolve_tamanho_e_quantidade(self):
        vd = self.video("Video A")
        self.mp4(vd / "edicao" / "previa.mp4", b"12345")
        total, n, destino = limpeza.mandar_para_o_lixo([(vd / "edicao" / "previa.mp4", "previas"), (vd / "nao-existe", "x")])
        self.assertEqual((total, n, destino), (5, 1, LIXO))


class CacheDeImagens(Caso):
    def setUp(self):
        super().setUp()
        self.img = caminhos.cache() / "img"
        self.img.mkdir(parents=True, exist_ok=True)
        for f in self.img.iterdir():
            f.unlink()
        os.environ.pop("SM_CACHE_DIAS", None)

    def guardada(self, nome, dias, dados=b"x"):
        f = self.img / nome
        f.write_bytes(dados)
        quando = time.time() - dias * 86400
        os.utime(f, (quando, quando))
        return f

    def test_o_cache_fica_dentro_da_pasta_de_teste(self):
        self.assertTrue(str(self.img).startswith(str(sistema.DADOS)))

    def test_apaga_o_que_passou_do_prazo_e_deixa_o_recente(self):
        self.guardada("velha", 8)
        self.guardada("nova", 6)
        comum.limpar_cache()
        self.assertEqual([f.name for f in self.img.iterdir()], ["nova"])

    def test_imagem_lida_do_cache_renova_a_data_e_nao_sai(self):
        url = "https://exemplo.invalid/a.png"
        usada = self.guardada(hashlib.sha1(url.encode()).hexdigest(), 20, self.imagem())
        self.assertIsNotNone(comum.baixar_imagem(url, self.raiz / "saida", 100))     # lê do cache, sem rede
        comum.limpar_cache()
        self.assertTrue(usada.exists())

    def test_prazo_vem_do_ambiente_que_o_orquestrador_monta(self):
        self.assertEqual(sistema.ambiente_motor(self.c)["SM_CACHE_DIAS"], str(sistema.config().get("cache_dias", 7)))
        os.environ["SM_CACHE_DIAS"] = "3"
        self.guardada("quatro-dias", 4)
        comum.limpar_cache()
        self.assertEqual(list(self.img.iterdir()), [])
