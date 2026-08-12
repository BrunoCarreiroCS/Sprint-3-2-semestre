from __future__ import annotations

import unittest

from gemini_client import GeminiResponseError, validar_resposta_ia
from recommendation_engine import calcular_pontuacao, detectar_problemas, simular_intervencoes


class RecommendationAndGeminiTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
