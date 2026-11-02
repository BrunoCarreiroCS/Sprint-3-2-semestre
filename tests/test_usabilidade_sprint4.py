"""Correcoes de usabilidade apontadas na avaliacao heuristica da Sprint 4 (P02, P12, P13, P16, P18, P26, P30)."""
from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import database
import main
from image_analyzer import calcular_hash


def recomendacao(codigo: str) -> dict:
    return {
        "codigo_acao": codigo, "ganho_previsto": 10.0, "risco": "baixo", "esforco": "baixo",
        "confianca": "media", "explicacao": "teste", "evidencias": [],
    }


class UsabilidadeSprint4Test(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.dados = Path(self.temp.name) / "dados"
        database.inicializar_armazenamento(self.dados)
        self.ana = database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        self.foto = Path(self.temp.name) / "praia.jpg"
        Image.new("RGB", (64, 48), (90, 120, 160)).save(self.foto)
        main.FOTOS_DA_SESSAO.clear()

    def tearDown(self) -> None:
        main.FOTOS_DA_SESSAO.clear()
        self.temp.cleanup()

    def salvar_analise(self, codigos: list[str]) -> dict:
        analise_id = database.salvar_analise_com_recomendacoes({
            "usuario_id": self.ana["id"], "imagem_hash": calcular_hash(self.foto), "nome_arquivo": self.foto.name,
            "objetivo": "paisagem", "intencao": "", "estilo": "natural", "modo_execucao": "offline",
            "metricas": {}, "analise_ia": None, "pontuacao_geral": 50.0,
        }, [recomendacao(c) for c in codigos], self.dados)
        return database.buscar_analise(analise_id, self.dados)

    def rodar(self, funcao, respostas: list, *args) -> tuple[object, str]:
        saida = io.StringIO()
        fila = iter(respostas)

        def responder(pergunta: str = "") -> str:
            print(pergunta)
            return next(fila)

        with patch("builtins.input", side_effect=responder), redirect_stdout(saida):
            retorno = funcao(*args)
        return retorno, saida.getvalue()

    def test_p16_simulacao_lista_so_dicas_com_previa(self) -> None:
        self.salvar_analise(["usar_tripe", "adicionar_iluminacao", "limpar_lente"])
        main.FOTOS_DA_SESSAO[1] = self.foto
        with patch.object(main, "gerar_simulacao", return_value=Path("previa.jpg")) as gerar:
            _, saida = self.rodar(main.explorar_simulacao, ["1", "1", ""], self.ana, self.dados)
        self.assertIn("1. Adicionar Iluminação", saida)
        self.assertNotIn("Tripé", saida)
        self.assertNotIn("Limpar", saida)
        gerar.assert_called_once_with(self.foto, "adicionar_iluminacao", self.ana["id"])

    def test_p16_sem_dica_simulavel_avisa_antes_de_pedir_escolha(self) -> None:
        self.salvar_analise(["usar_tripe"])
        _, saida = self.rodar(main.explorar_simulacao, ["1"], self.ana, self.dados)
        self.assertIn("Nenhuma dica desta análise tem prévia digital", saida)

    def test_p18_reaproveita_foto_da_analise_com_enter(self) -> None:
        analise = self.salvar_analise(["adicionar_iluminacao"])
        main.FOTOS_DA_SESSAO[analise["id"]] = self.foto
        caminho, saida = self.rodar(main.foto_da_analise, [""], analise)
        self.assertEqual(caminho, self.foto)
        self.assertIn("Usar a mesma foto da análise (praia.jpg)?", saida)

    def test_p18_foto_alterada_nao_e_reaproveitada(self) -> None:
        analise = self.salvar_analise(["adicionar_iluminacao"])
        main.FOTOS_DA_SESSAO[analise["id"]] = self.foto
        Image.new("RGB", (64, 48), (0, 0, 0)).save(self.foto)
        caminho, saida = self.rodar(main.foto_da_analise, ["0"], analise)
        self.assertIsNone(caminho)
        self.assertNotIn("Usar a mesma foto", saida)
        self.assertIn("Selecione a foto original (praia.jpg)", saida)

    def test_p18_caminho_da_foto_nao_vai_para_os_arquivos(self) -> None:
        self.salvar_analise(["adicionar_iluminacao"])
        main.FOTOS_DA_SESSAO[1] = self.foto
        for arquivo in self.dados.rglob("*.json"):
            self.assertNotIn(str(self.foto.parent), arquivo.read_text(encoding="utf-8"))

    def test_p02_cabecalho_mostra_estado_da_ia(self) -> None:
        self.assertEqual(main.estado_ia({"consentimento_api": False}), "desligada (você não autorizou)")
        with patch.object(main, "is_demo_mode", return_value=False), patch.object(main, "get_gemini_api_key", return_value=""):
            self.assertEqual(main.estado_ia({"consentimento_api": True}), "sem chave configurada (modo offline)")
        with patch.object(main, "is_demo_mode", return_value=True):
            self.assertEqual(main.estado_ia({"consentimento_api": True}), "ligada (modo demonstração)")

    def test_p13_p30_titulos_iguais_ao_menu(self) -> None:
        _, menu = self.rodar(main.exibir_menu, [], self.ana)
        self.assertIn("10. Trocar dados com o app da câmera", menu)
        self.assertNotIn("JSON", menu)
        _, tela = self.rodar(main.recomendacao_sem_foto, ["0"], self.ana)
        self.assertIn("RECEBER ORIENTAÇÃO SEM FOTO", tela)

    def test_p26_exclusao_cancelada_explica_o_motivo(self) -> None:
        _, saida = self.rodar(main.excluir_perfil, ["1", "excluir ana"], [self.ana], self.dados)
        self.assertIn("O texto não confere (digite exatamente EXCLUIR Ana). Nada foi apagado.", saida)
        self.assertEqual(len(database.listar_usuarios(self.dados)), 1)


if __name__ == "__main__":
    unittest.main()
