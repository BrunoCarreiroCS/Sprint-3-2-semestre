"""Integracao com o restante da solucao Humanly por meio de arquivos JSON.

Contrato de troca (versao 1.0):

1. O app da camera JOVI (ou qualquer outro sistema) grava uma *solicitacao*
   em ``integracao/entrada/<nome>.json``.
2. O LensLab valida a solicitacao, analisa a foto e grava o *resultado* em
   ``integracao/saida/resultado_<id_solicitacao>.json``.
3. A solicitacao atendida e movida para ``integracao/processadas/``; uma
   solicitacao invalida vai para ``integracao/com_erro/`` e gera
   ``integracao/saida/erro_<nome>.json`` explicando o motivo.

O LensLab tambem exporta o perfil do usuario em ``integracao/saida/`` para
que o app mostre a evolucao e os conselhos aprendidos.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

import database
from analysis_service import analisar_fotografia
from config import DADOS_DIR, INTEGRACAO_DIR, ROOT_DIR, VERSAO_CONTRATO_INTEGRACAO, is_demo_mode
from gemini_client import analisar_com_gemini, analisar_com_gemini_demo
from learning_engine import resumo_evolucao
from recommendation_engine import PESOS_OBJETIVO, formatar_contexto
from reports import ERRO_IA_LEGIVEL, classificar_pontuacao, pontos_fortes_e_fracos
from textos import legivel
from validators import ValidationError, validar_caminho_imagem, validar_texto

PASTAS = ("entrada", "saida", "processadas", "com_erro")
NIVEIS = sorted(database.NIVEIS_VALIDOS)
ESTILOS = sorted(database.ESTILOS_VALIDOS)
PADRAO_ID = re.compile(r"^[A-Za-z0-9_-]{1,60}$")

ClienteIA = Callable[[str | Path, str, str], dict]


def preparar_pastas(base: str | Path = INTEGRACAO_DIR) -> dict[str, Path]:
    pastas = {nome: Path(base) / nome for nome in PASTAS}
    for pasta in pastas.values():
        pasta.mkdir(parents=True, exist_ok=True)
    return pastas


def listar_pendentes(base: str | Path = INTEGRACAO_DIR) -> list[Path]:
    entrada = preparar_pastas(base)["entrada"]
    return sorted(arquivo for arquivo in entrada.glob("*.json") if arquivo.is_file())


def cliente_ia_padrao() -> ClienteIA:
    return analisar_com_gemini_demo if is_demo_mode() else analisar_com_gemini


# ---------------------------------------------------------------- validacao

def resolver_foto(valor: object) -> Path:
    """Aceita caminho absoluto ou relativo a pasta raiz do projeto."""
    texto = validar_texto(valor, "foto", 1, 500)
    caminho = Path(texto).expanduser()
    if not caminho.is_absolute():
        caminho = ROOT_DIR / caminho
    return validar_caminho_imagem(caminho)


def validar_solicitacao(dados: object) -> dict:
    """Confere o contrato e devolve a solicitacao normalizada."""
    if not isinstance(dados, dict):
        raise ValidationError("A solicitação precisa ser um objeto JSON.")
    versao = str(dados.get("versao", ""))
    if versao.split(".")[0] != VERSAO_CONTRATO_INTEGRACAO.split(".")[0]:
        raise ValidationError(
            f"Versão de contrato '{versao or 'ausente'}' não suportada; use {VERSAO_CONTRATO_INTEGRACAO}."
        )
    id_solicitacao = str(dados.get("id_solicitacao", "")).strip()
    if not PADRAO_ID.match(id_solicitacao):
        raise ValidationError("id_solicitacao deve ter de 1 a 60 caracteres: letras, números, - ou _.")

    perfil = dados.get("perfil")
    if not isinstance(perfil, dict):
        raise ValidationError("O campo 'perfil' é obrigatório e deve ser um objeto.")
    apelido = validar_texto(perfil.get("apelido", ""), "apelido", 2, 40)
    nivel = str(perfil.get("nivel", "iniciante")).strip().lower()
    estilo = str(perfil.get("estilo", "natural")).strip().lower()
    if nivel not in NIVEIS:
        raise ValidationError(f"Nível inválido. Use: {', '.join(NIVEIS)}.")
    if estilo not in ESTILOS:
        raise ValidationError(f"Estilo inválido. Use: {', '.join(ESTILOS)}.")
    consentimento = perfil.get("consentimento_api", False)
    if not isinstance(consentimento, bool):
        raise ValidationError("consentimento_api deve ser true ou false.")

    objetivo = str(dados.get("objetivo", "")).strip().lower()
    if objetivo not in PESOS_OBJETIVO:
        raise ValidationError(f"Objetivo inválido. Use: {', '.join(sorted(PESOS_OBJETIVO))}.")
    intencao = validar_texto(dados.get("intencao", ""), "intencao", 3, 160)
    foto = resolver_foto(dados.get("foto", ""))

    return {
        "versao": versao, "id_solicitacao": id_solicitacao, "origem": str(dados.get("origem", "desconhecida"))[:60],
        "perfil": {"apelido": apelido, "nivel": nivel, "estilo": estilo, "consentimento_api": consentimento},
        "objetivo": objetivo, "intencao": intencao, "foto": foto,
    }


def ler_solicitacao(arquivo: Path) -> dict:
    try:
        with open(arquivo, encoding="utf-8-sig") as stream:
            return json.load(stream)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"JSON inválido na linha {exc.lineno}, coluna {exc.colno}.") from exc
    except UnicodeDecodeError as exc:
        raise ValidationError("O arquivo precisa estar codificado em UTF-8.") from exc


# ---------------------------------------------------------------- processamento

def obter_ou_criar_perfil(perfil: dict, pasta_dados: str | Path = DADOS_DIR) -> tuple[dict, bool]:
    """Reaproveita o perfil pelo apelido; so cria um novo se ele ainda nao existir.

    O consentimento de um perfil existente nunca e alterado por uma solicitacao
    externa: ele so muda pelo menu de privacidade do proprio LensLab.
    """
    existente = database.buscar_usuario_por_apelido(perfil["apelido"], pasta_dados)
    if existente:
        return existente, False
    novo = database.criar_usuario(
        perfil["apelido"], perfil["nivel"], perfil["estilo"], perfil["consentimento_api"], pasta_dados
    )
    return novo, True


def montar_resultado(solicitacao: dict, usuario: dict, criado: bool, analise: dict) -> dict:
    fortes, fracos = pontos_fortes_e_fracos(analise["dimensoes"])
    ia = analise.get("analise_ia")
    return {
        "versao": VERSAO_CONTRATO_INTEGRACAO,
        "tipo": "resultado_analise",
        "status": "concluido",
        "id_solicitacao": solicitacao["id_solicitacao"],
        "processado_em": database.agora_iso(),
        "perfil": {"id": usuario["id"], "apelido": usuario["apelido"], "criado_nesta_solicitacao": criado},
        "analise": {
            "id": analise["analise_id"],
            "modo_execucao": analise["modo_execucao"],
            "pontuacao_geral": analise["pontuacao_geral"],
            "classificacao": classificar_pontuacao(analise["pontuacao_geral"]),
            "dimensoes": analise["dimensoes"],
            "pontos_fortes": fortes,
            "pontos_a_melhorar": fracos,
        },
        "ia": {
            "disponivel": bool(ia),
            "motivo_indisponivel": None if ia else ERRO_IA_LEGIVEL.get(analise.get("erro_ia"), analise.get("erro_ia")),
            "assunto_principal": ia["assunto_principal"] if ia else None,
            "tipo_cena": ia["tipo_cena"] if ia else None,
        },
        "recomendacoes": [
            {
                "posicao": posicao, "codigo_acao": rec["codigo_acao"],
                "titulo": legivel(rec["codigo_acao"]),
                "ganho_previsto": rec["ganho_previsto"], "confianca": rec["confianca"],
                "esforco": rec["esforco"], "explicacao": rec["explicacao"], "risco": rec["risco"],
            }
            for posicao, rec in enumerate(analise["recomendacoes"], start=1)
        ],
    }


def _gravar_saida(arquivo: Path, dados: dict) -> Path:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo.with_name(arquivo.name + ".tmp")
    with open(temporario, "w", encoding="utf-8") as stream:
        json.dump(dados, stream, ensure_ascii=False, indent=2)
    temporario.replace(arquivo)
    return arquivo


def _arquivar(arquivo: Path, destino: Path) -> Path:
    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
    alvo = destino / f"{carimbo}_{arquivo.name}"
    shutil.move(str(arquivo), str(alvo))
    return alvo


def processar_arquivo(
    arquivo: Path,
    pasta_dados: str | Path = DADOS_DIR,
    base: str | Path = INTEGRACAO_DIR,
    cliente_ia: ClienteIA | None = None,
) -> dict:
    """Atende uma solicitacao; nunca deixa o arquivo parado na entrada."""
    pastas = preparar_pastas(base)
    try:
        solicitacao = validar_solicitacao(ler_solicitacao(arquivo))
        usuario, criado = obter_ou_criar_perfil(solicitacao["perfil"], pasta_dados)
        analise = analisar_fotografia(
            usuario, solicitacao["foto"], solicitacao["objetivo"], solicitacao["intencao"],
            usuario["estilo_preferido"], bool(usuario["consentimento_api"]), pasta_dados,
            cliente_ia or cliente_ia_padrao(),
        )
    except database.ArmazenamentoError:
        raise  # problema nos dados locais, nao na solicitacao: interrompe o lote
    except (ValueError, OSError) as exc:
        mensagem = str(exc) or type(exc).__name__
        saida = _gravar_saida(pastas["saida"] / f"erro_{arquivo.stem}.json", {
            "versao": VERSAO_CONTRATO_INTEGRACAO, "tipo": "erro_solicitacao", "status": "erro",
            "arquivo": arquivo.name, "mensagem": mensagem, "processado_em": database.agora_iso(),
        })
        _arquivar(arquivo, pastas["com_erro"])
        return {"arquivo": arquivo.name, "status": "erro", "mensagem": mensagem, "saida": saida}

    resultado = montar_resultado(solicitacao, usuario, criado, analise)
    saida = _gravar_saida(pastas["saida"] / f"resultado_{solicitacao['id_solicitacao']}.json", resultado)
    _arquivar(arquivo, pastas["processadas"])
    return {
        "arquivo": arquivo.name, "status": "concluido", "saida": saida,
        "mensagem": f"{usuario['apelido']}: nota {analise['pontuacao_geral']:.0f}/100",
    }


def processar_pendentes(
    pasta_dados: str | Path = DADOS_DIR,
    base: str | Path = INTEGRACAO_DIR,
    cliente_ia: ClienteIA | None = None,
) -> list[dict]:
    return [processar_arquivo(arquivo, pasta_dados, base, cliente_ia) for arquivo in listar_pendentes(base)]


# ---------------------------------------------------------------- exportacao e exemplo

def exportar_perfil_para_app(
    usuario_id: int, pasta_dados: str | Path = DADOS_DIR, base: str | Path = INTEGRACAO_DIR
) -> Path:
    """Gera o arquivo que o app JOVI le para mostrar a evolucao do usuario."""
    usuario = database.buscar_usuario(usuario_id, pasta_dados)
    if not usuario:
        raise ValueError("Usuário não encontrado.")
    evolucao = resumo_evolucao(usuario_id, pasta_dados)
    pendente = database.buscar_recomendacao_pendente(usuario_id, pasta_dados)
    dados = {
        "versao": VERSAO_CONTRATO_INTEGRACAO,
        "tipo": "perfil_lenslab",
        "exportado_em": database.agora_iso(),
        "perfil": {
            "id": usuario["id"], "apelido": usuario["apelido"], "nivel": usuario["nivel"],
            "estilo_preferido": usuario["estilo_preferido"], "consentimento_api": usuario["consentimento_api"],
        },
        "evolucao": {
            "total_analises": evolucao["total_analises"],
            "total_comparacoes": evolucao["total_comparacoes"],
            "ganho_medio": evolucao["ganho_medio"],
            "evolucao_pontuacao": evolucao["evolucao_pontuacao"],
            "recapturas_bem_sucedidas": evolucao["sucessos"],
        },
        "conselhos_aprendidos": [
            {
                "codigo_acao": item["codigo_acao"], "peso": item["peso"], "sucessos": item["sucessos"],
                "contexto": formatar_contexto(item["contexto_chave"]),
            }
            for item in evolucao["principais_pesos"]
        ],
        "recomendacao_pendente": (
            {"codigo_acao": pendente["codigo_acao"], "foto": pendente["nome_arquivo"]} if pendente else None
        ),
        "ultimas_analises": database.listar_analises(usuario_id, pasta_dados)[:5],
    }
    return _gravar_saida(preparar_pastas(base)["saida"] / f"perfil_{usuario_id}.json", dados)


def exemplo_solicitacao(id_solicitacao: str = "exemplo-001") -> dict:
    return {
        "versao": VERSAO_CONTRATO_INTEGRACAO,
        "origem": "app_camera_jovi",
        "id_solicitacao": id_solicitacao,
        "perfil": {"apelido": "Demo App JOVI", "nivel": "iniciante", "estilo": "natural", "consentimento_api": False},
        "foto": "samples/exemplo_escuro.jpg",
        "objetivo": "retrato",
        "intencao": "foto de perfil para rede social",
    }


def criar_solicitacao_exemplo(base: str | Path = INTEGRACAO_DIR) -> Path:
    id_solicitacao = "exemplo-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = preparar_pastas(base)["entrada"] / f"solicitacao_{id_solicitacao}.json"
    return _gravar_saida(destino, exemplo_solicitacao(id_solicitacao))
