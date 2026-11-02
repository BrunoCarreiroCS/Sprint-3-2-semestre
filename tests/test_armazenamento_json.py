from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import database
import main
from learning_engine import comparar_e_aprender

REC = {
    "codigo_acao": "adicionar_iluminacao", "ganho_previsto": 18.0, "risco": "sombras",
    "esforco": "medio", "confianca": "alta", "explicacao": "adicione luz", "evidencias": ["imagem escura"],
}


def analise_base(usuario_id: int, hash_imagem: str, pontuacao: float) -> dict:
    return {
        "usuario_id": usuario_id, "imagem_hash": hash_imagem, "nome_arquivo": f"{hash_imagem[:8]}.jpg",
        "objetivo": "retrato", "intencao": "retrato natural", "estilo": "natural", "modo_execucao": "offline",
        "metricas": {"contexto_chave": "retrato|escuro|estatico|iniciante|natural", "dimensoes": {"exposicao": pontuacao}},
        "analise_ia": None, "pontuacao_geral": pontuacao,
    }


class ArmazenamentoJsonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.dados = Path(self.temp.name) / "dados"
        database.inicializar_armazenamento(self.dados)
        self.ana = database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dados_ficam_em_arquivos_json_legiveis(self) -> None:
        analise_id = database.salvar_analise_com_recomendacoes(
            analise_base(self.ana["id"], "a" * 64, 40), [REC], self.dados
        )
        indice = json.loads((self.dados / "usuarios.json").read_text(encoding="utf-8"))
        perfil = json.loads((self.dados / "perfis" / f"perfil_{self.ana['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(indice["usuarios"][0]["apelido"], "Ana")
        self.assertEqual(perfil["analises"][0]["id"], analise_id)
        self.assertEqual(perfil["recomendacoes"][0]["codigo_acao"], "adicionar_iluminacao")

    def test_gravacao_nao_deixa_arquivo_temporario(self) -> None:
        database.salvar_analise_com_recomendacoes(analise_base(self.ana["id"], "a" * 64, 40), [REC], self.dados)
        self.assertEqual(list(self.dados.rglob("*.tmp")), [])

    def test_apelido_repetido_e_recusado_sem_diferenciar_maiusculas(self) -> None:
        with self.assertRaises(database.RegistroDuplicadoError):
            database.criar_usuario("ANA", "avancado", "vibrante", True, self.dados)

    def test_nivel_ou_estilo_invalido_e_recusado(self) -> None:
        with self.assertRaises(ValueError):
            database.criar_usuario("Caio", "expert", "natural", False, self.dados)

    def test_arquivo_corrompido_gera_erro_claro(self) -> None:
        (self.dados / "usuarios.json").write_text("{ isto não e json", encoding="utf-8")
        with self.assertRaises(database.ArmazenamentoError) as contexto:
            database.listar_usuarios(self.dados)
        self.assertIn("corrompido", str(contexto.exception))

    def test_exclusao_apaga_o_arquivo_do_perfil(self) -> None:
        arquivo = self.dados / "perfis" / f"perfil_{self.ana['id']}.json"
        self.assertTrue(arquivo.exists())
        database.excluir_usuario(self.ana["id"], self.dados)
        self.assertFalse(arquivo.exists())

    def test_identificadores_sao_unicos_entre_perfis(self) -> None:
        bia = database.criar_usuario("Bia", "avancado", "vibrante", False, self.dados)
        id_ana = database.salvar_analise_com_recomendacoes(analise_base(self.ana["id"], "a" * 64, 40), [REC], self.dados)
        id_bia = database.salvar_analise_com_recomendacoes(analise_base(bia["id"], "b" * 64, 40), [REC], self.dados)
        self.assertNotEqual(id_ana, id_bia)
        self.assertEqual(database.buscar_analise(id_bia, self.dados)["usuario_id"], bia["id"])

    def test_comparacao_repetida_e_recusada(self) -> None:
        antes = database.salvar_analise_com_recomendacoes(analise_base(self.ana["id"], "a" * 64, 40), [REC], self.dados)
        depois = database.salvar_analise_com_recomendacoes(analise_base(self.ana["id"], "b" * 64, 60), [REC], self.dados)
        rec_id = database.listar_recomendacoes(antes, self.dados)[0]["id"]
        comparar_e_aprender(self.ana["id"], antes, depois, rec_id, 5, "", self.dados)
        with self.assertRaises(database.RegistroDuplicadoError):
            comparar_e_aprender(self.ana["id"], antes, depois, rec_id, 5, "", self.dados)

    def test_dados_corrompidos_na_abertura_nao_geram_traceback(self) -> None:
        (self.dados / "usuarios.json").write_text("[1, 2", encoding="utf-8")
        saida = io.StringIO()
        with patch("builtins.input", side_effect=["0"]), redirect_stdout(saida):
            main.main(self.dados)
        self.assertIn("Não foi possível abrir os dados do LensLab", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
