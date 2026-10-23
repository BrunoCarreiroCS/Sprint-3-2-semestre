from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

import database
from analysis_service import analisar_fotografia


class AnalysisServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        pasta = Path(self.temp.name)
        self.dados = pasta / "dados"
        self.image = pasta / "cena.jpg"
        imagem = Image.new("RGB", (800, 600), (20, 20, 25))
        ImageDraw.Draw(imagem).rectangle((300, 170, 500, 520), fill=(90, 80, 70))
        imagem.save(self.image)
        database.inicializar_armazenamento(self.dados)
        self.usuario = database.criar_usuario("Teste", "iniciante", "natural", True, self.dados)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_sem_chave_cai_para_offline_e_persiste(self) -> None:
        with patch("analysis_service.get_gemini_api_key", return_value=None):
            resultado = analisar_fotografia(
                self.usuario, self.image, "retrato", "destacar pessoa", "natural", True, self.dados
            )
        self.assertEqual(resultado["modo_execucao"], "offline")
        self.assertEqual(resultado["erro_ia"], "modo_offline")
        self.assertTrue(database.buscar_analise(resultado["analise_id"], self.dados))

    def test_cliente_injetado_ativa_modo_hibrido(self) -> None:
        def cliente_falso(caminho, objetivo, intencao):
            return {
                "sucesso": True,
                "erro": None,
                "dados": {
                    "assunto_principal": "pessoa", "tipo_cena": "retrato",
                    "intencao_percebida": intencao, "movimento_percebido": False,
                    "problemas": [{"codigo": "pouca_luz", "confianca": 0.9, "evidencia_visual": "fundo escuro"}],
                    "composicao": {"pontuacao": 72, "observacao": "boa"},
                    "acoes_sugeridas": ["adicionar_iluminacao"], "incertezas": [],
                },
            }

        with patch("analysis_service.get_gemini_api_key", return_value="chave-de-teste"):
            resultado = analisar_fotografia(
                self.usuario, self.image, "retrato", "destacar pessoa", "natural", True,
                self.dados, cliente_ia=cliente_falso,
            )
        self.assertEqual(resultado["modo_execucao"], "hibrido")
        self.assertEqual(resultado["analise_ia"]["assunto_principal"], "pessoa")


if __name__ == "__main__":
    unittest.main()
