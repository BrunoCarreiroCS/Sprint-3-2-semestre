"""Um teste (ou grupo) por criterio da rubrica do Sprint 4.

Cada classe corresponde a um item da avaliacao, para que seja facil mostrar
onde cada requisito e comprovado.
"""

from __future__ import annotations

import importlib
import inspect
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

import config
import database
import gemini_client
import integracao
import main
from learning_engine import comparar_e_aprender, resumo_evolucao
from validators import ValidationError, validar_inteiro

MODULOS_DO_SISTEMA = (
    "analysis_service", "config", "database", "gemini_client", "image_analyzer", "integracao",
    "learning_engine", "main", "recommendation_engine", "reports", "textos", "validators",
)

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


class BaseSessao(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temp.name)
        self.dados = self.raiz / "dados"
        database.inicializar_armazenamento(self.dados)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def sessao(self, respostas: list) -> str:
        saida = io.StringIO()
        with patch("builtins.input", side_effect=respostas), redirect_stdout(saida):
            main.main(self.dados)
        return saida.getvalue()


class Req1MenuTest(BaseSessao):
    """Menu de opcoes, retorno ao menu principal e opcao para finalizar."""

    def test_menu_lista_todas_as_funcionalidades_e_a_saida(self) -> None:
        saida = io.StringIO()
        with redirect_stdout(saida):
            main.exibir_menu({"apelido": "Ana", "nivel": "iniciante"})
        texto = saida.getvalue()
        for numero in range(1, 11):
            self.assertIn(f"{numero:>2}. ", texto)
        self.assertIn("0. Encerrar", texto)

    def test_apos_uma_funcionalidade_o_programa_volta_ao_menu(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        saida = self.sessao(["1", "1", "6", "7", "0"])
        self.assertEqual(saida.count("HUMANLY JOVI AI LENSLAB"), 3)
        self.assertIn("Sessão encerrada", saida)

    def test_opcao_zero_finaliza_a_execucao(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        saida = self.sessao(["1", "1", "0"])
        self.assertTrue(saida.rstrip().endswith("Suas fotos não foram armazenadas nos arquivos de dados."))


class Req2SubrotinasTest(unittest.TestCase):
    """Subrotinas com uso adequado de parametros e retorno."""

    def test_funcoes_publicas_declaram_tipos_de_parametros_e_retorno(self) -> None:
        sem_tipo = []
        for nome_modulo in MODULOS_DO_SISTEMA:
            modulo = importlib.import_module(nome_modulo)
            for nome, funcao in inspect.getmembers(modulo, inspect.isfunction):
                if funcao.__module__ != modulo.__name__ or nome.startswith("_"):
                    continue
                assinatura = inspect.signature(funcao)
                if assinatura.return_annotation is inspect.Signature.empty:
                    sem_tipo.append(f"{nome_modulo}.{nome} -> retorno")
                for parametro in assinatura.parameters.values():
                    if parametro.annotation is inspect.Parameter.empty:
                        sem_tipo.append(f"{nome_modulo}.{nome}({parametro.name})")
        self.assertEqual(sem_tipo, [], "Funcoes sem tipo declarado: " + ", ".join(sem_tipo))

    def test_regras_devolvem_valores_em_vez_de_imprimir(self) -> None:
        saida = io.StringIO()
        with redirect_stdout(saida):
            resultado = validar_inteiro("4", 1, 5, "opcao")
        self.assertEqual(resultado, 4)
        self.assertEqual(saida.getvalue(), "")


class Req3ValidacaoExcecoesTest(BaseSessao):
    """Validacao de entrada do usuario e tratamento de excecoes com try/except."""

    def test_opcao_invalida_e_pedida_de_novo_sem_encerrar(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        saida = self.sessao(["1", "1", "x", "11", "-1", "0"])
        self.assertEqual(saida.count("Entrada inválida"), 3)
        self.assertIn("Sessão encerrada", saida)

    def test_falha_nos_dados_durante_a_sessao_mostra_mensagem_e_continua(self) -> None:
        database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        erro = database.ArmazenamentoError("O arquivo de dados perfil_1.json esta corrompido.")
        with patch("database.listar_analises", side_effect=erro):
            saida = self.sessao(["1", "1", "6", "0"])
        self.assertIn("Operação não concluída: O arquivo de dados perfil_1.json esta corrompido.", saida)
        self.assertIn("Sessão encerrada", saida)

    def test_validador_rejeita_texto_fora_da_faixa(self) -> None:
        for valor in ("abc", "0", "6", ""):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                validar_inteiro(valor, 1, 5, "avaliacao")


class Req4PersistenciaJsonTest(BaseSessao):
    """Persistencia de dados em arquivos JSON."""

    def test_perfil_criado_em_uma_execucao_aparece_na_seguinte(self) -> None:
        self.sessao(["Lia", "1", "1", "nao", "nao", "0"])
        saida = self.sessao(["1", "1", "0"])
        self.assertIn("Perfil: Lia", saida)

    def test_arquivos_gravados_sao_json_validos(self) -> None:
        usuario = database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        database.salvar_analise_com_recomendacoes(analise_base(usuario["id"], "a" * 64, 40), [REC], self.dados)
        arquivos = list(self.dados.rglob("*.json"))
        relativos = {arquivo.relative_to(self.dados).as_posix() for arquivo in arquivos}
        self.assertEqual(relativos, {"usuarios.json", f"perfis/perfil_{usuario['id']}.json"})
        for arquivo in arquivos:
            self.assertIsInstance(json.loads(arquivo.read_text(encoding="utf-8")), dict)

    def test_consentimento_alterado_fica_gravado_no_arquivo(self) -> None:
        usuario = database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        database.atualizar_consentimento(usuario["id"], True, self.dados)
        indice = json.loads((self.dados / "usuarios.json").read_text(encoding="utf-8"))
        self.assertTrue(indice["usuarios"][0]["consentimento_api"])

    def test_aprendizado_persistido_alimenta_a_evolucao(self) -> None:
        usuario = database.criar_usuario("Ana", "iniciante", "natural", False, self.dados)
        antes = database.salvar_analise_com_recomendacoes(analise_base(usuario["id"], "a" * 64, 40), [REC], self.dados)
        depois = database.salvar_analise_com_recomendacoes(analise_base(usuario["id"], "b" * 64, 60), [REC], self.dados)
        rec_id = database.listar_recomendacoes(antes, self.dados)[0]["id"]
        comparar_e_aprender(usuario["id"], antes, depois, rec_id, 5, "ajudou", self.dados)
        resumo = resumo_evolucao(usuario["id"], self.dados)
        self.assertEqual(resumo["total_comparacoes"], 1)
        self.assertEqual(resumo["evolucao_pontuacao"], 20.0)
        self.assertEqual(resumo["principais_pesos"][0]["peso"], 1.1)

    def test_pastas_de_dados_e_integracao_sao_criadas_ao_iniciar(self) -> None:
        with patch.object(config, "DATA_DIR", self.raiz / "d"), patch.object(config, "OUTPUT_DIR", self.raiz / "o"), \
                patch.object(config, "SAMPLES_DIR", self.raiz / "s"), patch.object(config, "INTEGRACAO_DIR", self.raiz / "i"):
            config.ensure_directories()
        for nome in ("entrada", "saida", "processadas", "com_erro"):
            self.assertTrue((self.raiz / "i" / nome).is_dir())


class Req5ApiExternaTest(unittest.TestCase):
    """Consumo de pelo menos uma API externa (Google Gemini)."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.imagem = Path(self.temp.name) / "foto.jpg"
        Image.new("RGB", (640, 480), (30, 30, 30)).save(self.imagem)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_requisicao_envia_imagem_modelo_e_schema_e_devolve_dados_validados(self) -> None:
        resposta = MagicMock()
        resposta.text = json.dumps(gemini_client.analisar_com_gemini_demo("x", "retrato", "teste")["dados"])
        cliente = MagicMock()
        cliente.models.generate_content.return_value = resposta
        with patch("gemini_client.get_gemini_api_key", return_value="chave"), \
                patch("google.genai.Client", return_value=cliente) as construtor:
            resultado = gemini_client.analisar_com_gemini(self.imagem, "retrato", "teste")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(construtor.call_args.kwargs["api_key"], "chave")
        chamada = cliente.models.generate_content.call_args.kwargs
        self.assertEqual(chamada["model"], gemini_client.get_gemini_model())
        self.assertIsInstance(chamada["contents"][1], Image.Image)
        self.assertEqual(chamada["config"].response_json_schema, gemini_client._schema())

    def test_sem_chave_a_api_nao_e_chamada(self) -> None:
        with patch("gemini_client.get_gemini_api_key", return_value=None), \
                patch("google.genai.Client") as construtor:
            resultado = gemini_client.analisar_com_gemini(self.imagem, "retrato", "teste")
        self.assertEqual(resultado["erro"], "chave_ausente")
        construtor.assert_not_called()


class Req6IntegracaoTest(BaseSessao):
    """Integracao com o restante da solucao por meio de arquivos."""

    def setUp(self) -> None:
        super().setUp()
        self.base = self.raiz / "integracao"
        self.pastas = integracao.preparar_pastas(self.base)

    def cliente(self, caminho, objetivo, intencao) -> dict:
        return {"sucesso": False, "dados": None, "erro": "modo_offline"}

    def test_ciclo_completo_entre_app_e_lenslab(self) -> None:
        pedido = integracao.exemplo_solicitacao("ciclo-1")
        (self.pastas["entrada"] / "pedido.json").write_text(json.dumps(pedido), encoding="utf-8")
        integracao.processar_pendentes(self.dados, self.base, self.cliente)
        resultado = json.loads((self.pastas["saida"] / "resultado_ciclo-1.json").read_text(encoding="utf-8"))
        self.assertEqual(resultado["versao"], config.VERSAO_CONTRATO_INTEGRACAO)
        self.assertEqual(resultado["tipo"], "resultado_analise")
        self.assertIn("pontos_a_melhorar", resultado["analise"])
        usuario = database.buscar_usuario_por_apelido(pedido["perfil"]["apelido"], self.dados)
        self.assertEqual(len(database.listar_analises(usuario["id"], self.dados)), 1)

    def test_foto_com_caminho_absoluto_e_aceita(self) -> None:
        pedido = integracao.exemplo_solicitacao("abs-1")
        pedido["foto"] = str(config.SAMPLES_DIR / "exemplo_nitido.jpg")
        self.assertTrue(integracao.validar_solicitacao(pedido)["foto"].is_absolute())

    def test_arquivos_que_nao_sao_json_sao_ignorados(self) -> None:
        (self.pastas["entrada"] / "anotacao.txt").write_text("não processar", encoding="utf-8")
        self.assertEqual(integracao.processar_pendentes(self.dados, self.base, self.cliente), [])
        self.assertTrue((self.pastas["entrada"] / "anotacao.txt").exists())

    def test_falha_nos_dados_locais_nao_descarta_a_solicitacao(self) -> None:
        arquivo = self.pastas["entrada"] / "pedido.json"
        arquivo.write_text(json.dumps(integracao.exemplo_solicitacao()), encoding="utf-8")
        with patch("integracao.obter_ou_criar_perfil", side_effect=database.ArmazenamentoError("corrompido")):
            with self.assertRaises(database.ArmazenamentoError):
                integracao.processar_pendentes(self.dados, self.base, self.cliente)
        self.assertTrue(arquivo.exists())
        self.assertEqual(list(self.pastas["com_erro"].glob("*.json")), [])

    def test_exportar_perfil_inexistente_e_recusado(self) -> None:
        with self.assertRaises(ValueError):
            integracao.exportar_perfil_para_app(999, self.dados, self.base)


class Req7InterfaceTest(BaseSessao):
    """Interface intuitiva, com mensagens claras e navegacao facil."""

    def test_mensagem_de_dados_corrompidos_indica_o_arquivo(self) -> None:
        (self.dados / "usuarios.json").write_text("{", encoding="utf-8")
        saida = self.sessao(["0"])
        self.assertIn("usuarios.json", saida)
        self.assertNotIn("Traceback", saida)

    def test_primeiro_uso_leva_direto_para_criar_perfil(self) -> None:
        saida = self.sessao(["0"])
        self.assertIn("Ainda não há perfis. Vamos criar o primeiro.", saida)
        self.assertIn("CRIAR PERFIL", saida)


if __name__ == "__main__":
    unittest.main()
