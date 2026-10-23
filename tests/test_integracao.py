from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import database
import integracao
import main
from config import ROOT_DIR
from validators import ValidationError


def cliente_offline(caminho, objetivo, intencao):
    return {"sucesso": False, "dados": None, "erro": "modo_offline"}


class IntegracaoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        raiz = Path(self.temp.name)
        self.dados = raiz / "dados"
        self.base = raiz / "integracao"
        database.inicializar_armazenamento(self.dados)
        self.pastas = integracao.preparar_pastas(self.base)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def gravar(self, nome: str, conteudo) -> Path:
        arquivo = self.pastas["entrada"] / nome
        texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo)
        arquivo.write_text(texto, encoding="utf-8")
        return arquivo

    def processar(self) -> list[dict]:
        return integracao.processar_pendentes(self.dados, self.base, cliente_offline)

    def test_solicitacao_valida_gera_resultado_e_sai_da_entrada(self) -> None:
        self.gravar("pedido.json", integracao.exemplo_solicitacao("app-42"))
        resumo = self.processar()
        self.assertEqual(resumo[0]["status"], "concluido")
        resultado = json.loads((self.pastas["saida"] / "resultado_app-42.json").read_text(encoding="utf-8"))
        self.assertEqual(resultado["status"], "concluido")
        self.assertEqual(resultado["perfil"]["apelido"], "Demo App JOVI")
        self.assertTrue(resultado["perfil"]["criado_nesta_solicitacao"])
        self.assertTrue(resultado["recomendacoes"])
        self.assertNotIn("imagem_hash", json.dumps(resultado))
        self.assertEqual(integracao.listar_pendentes(self.base), [])
        self.assertEqual(len(list(self.pastas["processadas"].glob("*.json"))), 1)

    def test_perfil_existente_e_reaproveitado_sem_mudar_consentimento(self) -> None:
        database.criar_usuario("Demo App JOVI", "avancado", "vibrante", False, self.dados)
        pedido = integracao.exemplo_solicitacao("app-43")
        pedido["perfil"]["consentimento_api"] = True
        self.gravar("pedido.json", pedido)
        self.processar()
        usuarios = database.listar_usuarios(self.dados)
        self.assertEqual(len(usuarios), 1)
        self.assertFalse(usuarios[0]["consentimento_api"])

    def test_json_malformado_vai_para_com_erro_com_explicacao(self) -> None:
        self.gravar("quebrado.json", '{"versao": "1.0",')
        resumo = self.processar()
        self.assertEqual(resumo[0]["status"], "erro")
        erro = json.loads((self.pastas["saida"] / "erro_quebrado.json").read_text(encoding="utf-8"))
        self.assertIn("JSON invalido", erro["mensagem"])
        self.assertEqual(len(list(self.pastas["com_erro"].glob("*.json"))), 1)
        self.assertEqual(integracao.listar_pendentes(self.base), [])

    def test_campos_invalidos_sao_rejeitados_com_motivo(self) -> None:
        casos = {
            "nao suportada": ("versao", "9.0"),
            "Objetivo invalido": ("objetivo", "astronomia"),
            "id_solicitacao": ("id_solicitacao", "id com espaco"),
            "nao encontrado": ("foto", "samples/nao_existe.jpg"),
        }
        for trecho, (campo, valor) in casos.items():
            with self.subTest(campo=campo):
                pedido = integracao.exemplo_solicitacao()
                pedido[campo] = valor
                with self.assertRaises(ValidationError) as contexto:
                    integracao.validar_solicitacao(pedido)
                self.assertIn(trecho, str(contexto.exception))

    def test_arquivo_salvo_com_bom_do_bloco_de_notas_e_aceito(self) -> None:
        arquivo = self.pastas["entrada"] / "bom.json"
        arquivo.write_text(json.dumps(integracao.exemplo_solicitacao("app-bom")), encoding="utf-8-sig")
        self.assertEqual(self.processar()[0]["status"], "concluido")

    def test_exemplo_versionado_no_repositorio_segue_o_contrato(self) -> None:
        exemplo = json.loads((ROOT_DIR / "integracao" / "exemplos" / "solicitacao_exemplo.json").read_text(encoding="utf-8"))
        self.assertEqual(integracao.validar_solicitacao(exemplo)["id_solicitacao"], "exemplo-001")

    def test_exportar_perfil_para_o_app(self) -> None:
        usuario = database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        destino = integracao.exportar_perfil_para_app(usuario["id"], self.dados, self.base)
        dados = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(dados["tipo"], "perfil_lenslab")
        self.assertEqual(dados["perfil"]["apelido"], "Ana")
        self.assertIn("evolucao", dados)

    def test_menu_de_integracao_processa_exemplo(self) -> None:
        usuario = database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        saida = io.StringIO()
        with patch("builtins.input", side_effect=["2"]), redirect_stdout(saida):
            main.menu_integracao(usuario, self.dados, self.base)
        with patch("builtins.input", side_effect=["1"]), redirect_stdout(saida), \
                patch("integracao.cliente_ia_padrao", return_value=cliente_offline):
            main.menu_integracao(usuario, self.dados, self.base)
        self.assertIn("[OK  ]", saida.getvalue())
        self.assertEqual(len(list(self.pastas["saida"].glob("resultado_*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
