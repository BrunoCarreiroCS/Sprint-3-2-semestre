from __future__ import annotations

import unittest

from reports import ERRO_IA_LEGIVEL, formatar_analise, formatar_resumo_analise, formatar_resumo_comparacao


def resultado_base(pontuacao: float, dimensoes: dict, analise_ia: dict | None = None) -> dict:
    return {
        "modo_execucao": "hibrido" if analise_ia else "offline",
        "pontuacao_geral": pontuacao,
        "dimensoes": dimensoes,
        "analise_ia": analise_ia,
        "erro_ia": None if analise_ia else "servidor_sobrecarregado",
        "recomendacoes": [
            {
                "codigo_acao": "estabilizar_camera",
                "ganho_previsto": 30.0,
                "explicacao": "Apoie o aparelho para reduzir o tremor.",
                "risco": "Não corrige o movimento do assunto.",
                "confianca": "alta",
                "esforco": "baixo",
                "evidencias": [],
                "peso_aprendido": 1.0,
            },
            {
                "codigo_acao": "adicionar_iluminacao",
                "ganho_previsto": 10.0,
                "explicacao": "Adicione luz.",
                "risco": "Pode criar sombras.",
                "confianca": "media",
                "esforco": "medio",
                "evidencias": [],
                "peso_aprendido": 1.0,
            },
        ],
    }


class ReportsTest(unittest.TestCase):
    def test_resumo_analise_lista_pontos_fortes_e_fracos_em_linguagem_simples(self) -> None:
        resultado = resultado_base(
            70.0,
            {"exposicao": 80.0, "nitidez": 30.0, "contraste": 55.0, "cor": 60.0, "resolucao": 70.0, "intencao": 60.0},
        )
        texto = formatar_resumo_analise(resultado)
        self.assertIn("O que está bom", texto)
        self.assertIn("boa exposição de luz".capitalize(), texto)
        self.assertIn("O que pode melhorar", texto)
        self.assertIn("está desfocada".capitalize(), texto)
        self.assertNotIn("Nitidez", texto)  # termo tecnico nao deve aparecer no resumo

    def test_resumo_analise_destaca_principal_recomendacao_e_conta_extras(self) -> None:
        resultado = resultado_base(
            50.0,
            {"exposicao": 50.0, "nitidez": 50.0, "contraste": 50.0, "cor": 50.0, "resolucao": 50.0, "intencao": 50.0},
        )
        texto = formatar_resumo_analise(resultado)
        self.assertIn("Estabilizar Câmera", texto)
        self.assertIn("+ 1 outra(s)", texto)

    def test_resumo_analise_avisa_quando_ia_indisponivel_sem_expor_codigo_cru(self) -> None:
        resultado = resultado_base(
            50.0, {"exposicao": 50.0, "nitidez": 50.0, "contraste": 50.0, "cor": 50.0, "resolucao": 50.0, "intencao": 50.0}
        )
        texto = formatar_resumo_analise(resultado)
        self.assertIn("leitura extra por IA", texto)
        self.assertNotIn("servidor_sobrecarregado", texto)

    def test_resumo_comparacao_traduz_resultado_em_veredito_legivel(self) -> None:
        comparacao = {
            "codigo_acao": "estabilizar_camera",
            "ganho_real": 33.7,
            "resultado": "sucesso",
        }
        texto = formatar_resumo_comparacao(comparacao)
        self.assertIn("Funcionou", texto)
        self.assertIn("melhorou 34 pontos", texto)

    def test_resumo_comparacao_veredito_de_falha(self) -> None:
        comparacao = {"codigo_acao": "modo_noturno", "ganho_real": -8.0, "resultado": "falha"}
        texto = formatar_resumo_comparacao(comparacao)
        self.assertIn("Não ajudou", texto)
        self.assertIn("piorou 8 pontos", texto)

    def test_detalhe_analise_nunca_expoe_codigo_de_erro_cru(self) -> None:
        resultado = resultado_base(
            50.0, {"exposicao": 50.0, "nitidez": 50.0, "contraste": 50.0, "cor": 50.0, "resolucao": 50.0, "intencao": 50.0}
        )
        for codigo in ERRO_IA_LEGIVEL:
            resultado["erro_ia"] = codigo
            texto = formatar_analise(resultado)
            self.assertNotIn(codigo, texto, f"código cru '{codigo}' vazou no relatorio detalhado")

    def test_falha_api_generica_tem_mensagem_legivel(self) -> None:
        self.assertIn("falha_api", ERRO_IA_LEGIVEL)
        self.assertNotEqual(ERRO_IA_LEGIVEL["falha_api"], "falha_api")


if __name__ == "__main__":
    unittest.main()
