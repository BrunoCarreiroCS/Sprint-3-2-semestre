from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import database
from learning_engine import calcular_ajuste_peso, calcular_fator_confianca, comparar_e_aprender


def analise_base(usuario_id: int, hash_imagem: str, pontuacao: float) -> dict:
    return {
        "usuario_id": usuario_id,
        "imagem_hash": hash_imagem,
        "nome_arquivo": f"{hash_imagem}.jpg",
        "objetivo": "retrato",
        "intencao": "retrato natural",
        "estilo": "natural",
        "modo_execucao": "offline",
        "metricas": {
            "contexto_chave": "retrato|escuro|estatico|iniciante|natural",
            "dimensoes": {"exposicao": pontuacao, "nitidez": pontuacao},
        },
        "analise_ia": None,
        "pontuacao_geral": pontuacao,
    }


REC = {
    "codigo_acao": "adicionar_iluminacao",
    "ganho_previsto": 18.0,
    "risco": "sombras",
    "esforco": "medio",
    "confianca": "alta",
    "explicacao": "adicione luz",
    "evidencias": ["imagem escura"],
}


class DatabaseAndLearningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "teste.db"
        database.inicializar_banco(self.db)
        self.ana = database.criar_usuario("Ana", "iniciante", "natural", False, self.db)
        self.bia = database.criar_usuario("Bia", "avancado", "vibrante", True, self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_historico_fica_isolado_por_usuario(self) -> None:
        database.salvar_analise_com_recomendacoes(analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db)
        self.assertEqual(len(database.listar_analises(self.ana["id"], self.db)), 1)
        self.assertEqual(database.listar_analises(self.bia["id"], self.db), [])

    def test_exclusao_em_cascata_remove_dados_do_perfil(self) -> None:
        database.salvar_analise_com_recomendacoes(analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db)
        database.excluir_usuario(self.ana["id"], self.db)
        self.assertIsNone(database.buscar_usuario(self.ana["id"], self.db))
        self.assertEqual(database.listar_analises(self.ana["id"], self.db), [])

    def test_comparacao_aprende_so_no_contexto_e_usuario_corretos(self) -> None:
        antes_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db
        )
        depois_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "b" * 64, 55), [REC], self.db
        )
        rec_id = database.listar_recomendacoes(antes_id, self.db)[0]["id"]
        resultado = comparar_e_aprender(self.ana["id"], antes_id, depois_id, rec_id, 5, "ajudou", self.db)
        self.assertEqual(resultado["resultado"], "sucesso")
        self.assertEqual(resultado["novo_peso"], 1.1)
        pesos_ana = database.obter_pesos(
            self.ana["id"], "retrato|escuro|estatico|iniciante|natural", self.db
        )
        pesos_bia = database.obter_pesos(
            self.bia["id"], "retrato|escuro|estatico|iniciante|natural", self.db
        )
        self.assertEqual(pesos_ana["adicionar_iluminacao"], 1.1)
        self.assertEqual(pesos_bia, {})

    def test_ajuste_respeita_sinais_conflitantes(self) -> None:
        self.assertEqual(calcular_ajuste_peso(8, 1), 0.0)
        self.assertEqual(calcular_ajuste_peso(-8, 5), -0.03)

    def test_recaptura_identica_a_original_e_recusada(self) -> None:
        antes_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db
        )
        depois_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "a" * 64, 55), [REC], self.db
        )
        rec_id = database.listar_recomendacoes(antes_id, self.db)[0]["id"]
        with self.assertRaises(ValueError):
            comparar_e_aprender(self.ana["id"], antes_id, depois_id, rec_id, 5, "", self.db)

    def test_fator_confianca_diminui_com_mais_amostras(self) -> None:
        self.assertEqual(calcular_fator_confianca(0), 1.0)
        self.assertLess(calcular_fator_confianca(5), calcular_fator_confianca(0))
        self.assertEqual(calcular_fator_confianca(100), 0.3)

    def test_nenhuma_pendente_quando_nada_foi_marcado(self) -> None:
        database.salvar_analise_com_recomendacoes(analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db)
        self.assertIsNone(database.buscar_recomendacao_pendente(self.ana["id"], self.db))

    def test_pendente_retorna_recomendacao_marcada_mais_recente(self) -> None:
        antes_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db
        )
        rec_id = database.listar_recomendacoes(antes_id, self.db)[0]["id"]
        database.marcar_recomendacao(rec_id, antes_id, self.db)
        pendente = database.buscar_recomendacao_pendente(self.ana["id"], self.db)
        self.assertIsNotNone(pendente)
        self.assertEqual(pendente["id"], rec_id)
        self.assertEqual(pendente["analise_id"], antes_id)
        self.assertEqual(pendente["nome_arquivo"], "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg")

    def test_pendente_some_apos_comparacao_registrada(self) -> None:
        antes_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db
        )
        depois_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "b" * 64, 55), [REC], self.db
        )
        rec_id = database.listar_recomendacoes(antes_id, self.db)[0]["id"]
        database.marcar_recomendacao(rec_id, antes_id, self.db)
        self.assertIsNotNone(database.buscar_recomendacao_pendente(self.ana["id"], self.db))
        comparar_e_aprender(self.ana["id"], antes_id, depois_id, rec_id, 5, "", self.db)
        self.assertIsNone(database.buscar_recomendacao_pendente(self.ana["id"], self.db))

    def test_pendente_isolada_por_usuario(self) -> None:
        antes_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "a" * 64, 40), [REC], self.db
        )
        rec_id = database.listar_recomendacoes(antes_id, self.db)[0]["id"]
        database.marcar_recomendacao(rec_id, antes_id, self.db)
        self.assertIsNotNone(database.buscar_recomendacao_pendente(self.ana["id"], self.db))
        self.assertIsNone(database.buscar_recomendacao_pendente(self.bia["id"], self.db))

    def test_ajuste_encolhe_conforme_historico_cresce_no_mesmo_contexto(self) -> None:
        primeiro_ajuste = None
        for indice in range(3):
            antes_id = database.salvar_analise_com_recomendacoes(
                analise_base(self.ana["id"], f"{indice}a".rjust(64, "0"), 40), [REC], self.db
            )
            depois_id = database.salvar_analise_com_recomendacoes(
                analise_base(self.ana["id"], f"{indice}b".rjust(64, "0"), 60), [REC], self.db
            )
            rec_id = database.listar_recomendacoes(antes_id, self.db)[0]["id"]
            resultado = comparar_e_aprender(self.ana["id"], antes_id, depois_id, rec_id, 5, "", self.db)
            if indice == 0:
                primeiro_ajuste = resultado["ajuste_aplicado"]
            else:
                self.assertLess(resultado["ajuste_aplicado"], primeiro_ajuste)


if __name__ == "__main__":
    unittest.main()
