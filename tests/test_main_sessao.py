from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import database
import main


class MainSessaoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.dados = Path(self.temp.name) / "dados"
        database.inicializar_armazenamento(self.dados)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def executar(self, respostas: list) -> str:
        saida = io.StringIO()
        with patch("builtins.input", side_effect=respostas), redirect_stdout(saida):
            main.main(self.dados)
        return saida.getvalue()

    def test_excluir_unico_perfil_em_uso_encerra_sessao(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        saida = self.executar(["1", "1", "1", "3", "1", "EXCLUIR Ana", "0"])
        self.assertIn("este é o perfil em uso", saida)
        self.assertIn("Nenhum perfil ativo. Até logo!", saida)
        self.assertEqual(database.listar_usuarios(self.dados), [])

    def test_excluir_perfil_em_uso_exige_outro_perfil(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        database.criar_usuario("Bia", "avancado", "vibrante", False, self.dados)
        saida = self.executar(["1", "1", "1", "3", "1", "EXCLUIR Ana", "0", "1", "1", "0"])
        self.assertIn("O perfil em uso foi excluído", saida)
        ultimo_cabecalho = saida.rsplit("Perfil: ", 1)[1]
        self.assertTrue(ultimo_cabecalho.startswith("Bia"))

    def test_cancelar_troca_mantem_perfil_atual(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        saida = self.executar(["1", "1", "1", "0", "0"])
        self.assertTrue(saida.rsplit("Perfil: ", 1)[1].startswith("Ana"))

    def test_ctrl_c_encerra_sem_traceback(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        saida = self.executar(["1", "1", KeyboardInterrupt()])
        self.assertIn("Sessão encerrada", saida)

    def test_fim_da_entrada_encerra_sem_traceback(self) -> None:
        saida = self.executar(["Caio", EOFError()])
        self.assertIn("Sessão encerrada", saida)


if __name__ == "__main__":
    unittest.main()
