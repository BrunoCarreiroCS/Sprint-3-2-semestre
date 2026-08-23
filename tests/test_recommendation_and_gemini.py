from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

import gemini_client
from gemini_client import GeminiResponseError, analisar_com_gemini_demo, categorizar_erro, validar_resposta_ia
from recommendation_engine import calcular_pontuacao, detectar_problemas, simular_intervencoes


class RecommendationAndGeminiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.image = Path(self.temp.name) / "foto.png"
        Image.new("RGB", (640, 480), (28, 36, 48)).save(self.image)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_score_depende_do_objetivo(self) -> None:
        metricas = {
            "brilho": 55, "nitidez_bruta": 80, "contraste": 28,
            "saturacao": 42, "megapixels": 2, "realces_estourados": 0,
            "sombras_recortadas": 0,
        }
        documento, _ = calcular_pontuacao(metricas, "documento", "texto legivel")
        redes, _ = calcular_pontuacao(metricas, "redes_sociais", "impacto visual")
        self.assertNotEqual(documento, redes)

    def test_movimento_rebaixa_modo_noturno(self) -> None:
        problemas = {
            "pouca_luz": {
                "severidade": 1.0, "fontes": ["MEDIDO"],
                "evidencias": ["escura"], "estado": "provavel",
            }
        }
        sem_movimento = simular_intervencoes(problemas, False, limite=9)
        com_movimento = simular_intervencoes(problemas, True, limite=9)
        ganho_sem = next(r["ganho_previsto"] for r in sem_movimento if r["codigo_acao"] == "modo_noturno")
        ganho_com = next(r["ganho_previsto"] for r in com_movimento if r["codigo_acao"] == "modo_noturno")
        self.assertLess(ganho_com, ganho_sem)

    def test_deteccao_local_produz_evidencia_medida(self) -> None:
        problemas = detectar_problemas({
            "brilho": 10, "nitidez_bruta": 20, "contraste": 5,
            "saturacao": 20, "realces_estourados": 0, "megapixels": 2,
        })
        self.assertIn("pouca_luz", problemas)
        self.assertIn("MEDIDO", problemas["pouca_luz"]["fontes"])

    def test_resposta_gemini_e_filtrada(self) -> None:
        dados = validar_resposta_ia({
            "assunto_principal": "pessoa",
            "tipo_cena": "retrato",
            "intencao_percebida": "destacar rosto",
            "movimento_percebido": False,
            "problemas": [
                {"codigo": "pouca_luz", "confianca": 0.9, "evidencia_visual": "rosto escuro"},
                {"codigo": "inventado", "confianca": 0.9, "evidencia_visual": "x"},
            ],
            "composicao": {"pontuacao": 70, "observacao": "equilibrada"},
            "acoes_sugeridas": ["adicionar_iluminacao", "acao_inventada"],
            "incertezas": [],
        })
        self.assertEqual(len(dados["problemas"]), 1)
        self.assertEqual(dados["acoes_sugeridas"], ["adicionar_iluminacao"])
        self.assertTrue(dados["incertezas"])

    def test_resposta_incompleta_e_rejeitada(self) -> None:
        with self.assertRaises(GeminiResponseError):
            validar_resposta_ia({"assunto_principal": "algo"})

    def test_cliente_demo_produz_resposta_valida_sem_rede(self) -> None:
        resultado = analisar_com_gemini_demo("foto.jpg", "retrato", "destacar pessoa")
        self.assertTrue(resultado["sucesso"])
        self.assertIn("pouca_luz", [p["codigo"] for p in resultado["dados"]["problemas"]])

    def test_categoriza_erro_de_modelo_descontinuado(self) -> None:
        erro = Exception(
            "404 NOT_FOUND. {'error': {'message': 'This model is no longer available to new users'}}"
        )
        self.assertEqual(categorizar_erro(erro), "modelo_indisponivel")

    def test_categoriza_erro_de_servidor_sobrecarregado(self) -> None:
        erro = Exception("503 UNAVAILABLE. This model is currently experiencing high demand")
        self.assertEqual(categorizar_erro(erro), "servidor_sobrecarregado")

    def test_categoriza_erro_de_quota_e_autenticacao(self) -> None:
        self.assertEqual(categorizar_erro(Exception("429 RESOURCE_EXHAUSTED quota")), "quota")
        self.assertEqual(categorizar_erro(Exception("401 invalid api key")), "autenticacao")

    def test_tenta_novamente_apos_erro_transitorio(self) -> None:
        resposta_ok = MagicMock()
        resposta_ok.text = (
            '{"assunto_principal":"x","tipo_cena":"y","intencao_percebida":"z",'
            '"movimento_percebido":false,"problemas":[],'
            '"composicao":{"pontuacao":50,"observacao":""},'
            '"acoes_sugeridas":[],"incertezas":[]}'
        )
        cliente_falso = MagicMock()
        cliente_falso.models.generate_content.side_effect = [
            Exception("503 UNAVAILABLE high demand"),
            resposta_ok,
        ]
        with patch("gemini_client.get_gemini_api_key", return_value="chave-teste"), \
             patch("google.genai.Client", return_value=cliente_falso), \
             patch("gemini_client.time.sleep"):
            resultado = gemini_client.analisar_com_gemini(self.image, "retrato", "teste")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(cliente_falso.models.generate_content.call_count, 2)

    def test_nao_tenta_novamente_apos_erro_permanente(self) -> None:
        cliente_falso = MagicMock()
        cliente_falso.models.generate_content.side_effect = Exception(
            "404 NOT_FOUND model no longer available to new users"
        )
        with patch("gemini_client.get_gemini_api_key", return_value="chave-teste"), \
             patch("google.genai.Client", return_value=cliente_falso):
            resultado = gemini_client.analisar_com_gemini(self.image, "retrato", "teste")
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["erro"], "modelo_indisponivel")
        self.assertEqual(cliente_falso.models.generate_content.call_count, 1)

    def test_peso_aprendido_e_exposto_na_recomendacao(self) -> None:
        problemas = {
            "pouca_luz": {
                "severidade": 1.0, "fontes": ["MEDIDO"],
                "evidencias": ["escura"], "estado": "provavel",
            }
        }
        recomendacoes = simular_intervencoes(problemas, False, pesos_aprendidos={"adicionar_iluminacao": 1.3})
        item = next(r for r in recomendacoes if r["codigo_acao"] == "adicionar_iluminacao")
        self.assertEqual(item["peso_aprendido"], 1.3)


if __name__ == "__main__":
    unittest.main()
