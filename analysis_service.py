"""Orquestracao da analise local, Gemini, recomendacao e persistencia."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import database
from config import DB_PATH, get_gemini_api_key, is_demo_mode
from gemini_client import analisar_com_gemini
from image_analyzer import analisar_imagem, preparar_imagem_api
from recommendation_engine import (
    calcular_pontuacao,
    detectar_problemas,
    gerar_contexto_chave,
    simular_intervencoes,
)


def analisar_fotografia(
    usuario: dict,
    caminho_imagem: str | Path,
    objetivo: str,
    intencao: str,
    estilo: str,
    permitir_api: bool,
    caminho_banco: str | Path = DB_PATH,
    cliente_ia: Callable[[str | Path, str, str], dict] = analisar_com_gemini,
) -> dict:
    metricas = analisar_imagem(caminho_imagem)
    resultado_ia = {"sucesso": False, "dados": None, "erro": "modo_offline"}
    pode_usar_api = bool(
        permitir_api and usuario.get("consentimento_api") and (get_gemini_api_key() or is_demo_mode())
    )
    if pode_usar_api:
        with preparar_imagem_api(caminho_imagem) as temporaria:
            resultado_ia = cliente_ia(temporaria, objetivo, intencao)

    analise_ia = resultado_ia.get("dados") if resultado_ia.get("sucesso") else None
    movimento = bool((analise_ia or {}).get("movimento_percebido", False))
    pontuacao, dimensoes = calcular_pontuacao(metricas, objetivo, intencao, analise_ia)
    problemas = detectar_problemas(metricas, analise_ia)
    contexto = gerar_contexto_chave(objetivo, metricas, movimento, usuario["nivel"], estilo)
    pesos = database.obter_pesos(usuario["id"], contexto, caminho_banco)
    recomendacoes = simular_intervencoes(problemas, movimento, pesos)
    metricas_completas = dict(metricas)
    metricas_completas["dimensoes"] = dimensoes
    metricas_completas["contexto_chave"] = contexto
    metricas_completas["movimento"] = movimento
    analise = {
        "usuario_id": usuario["id"], "imagem_hash": metricas["imagem_hash"],
        "nome_arquivo": metricas["nome_arquivo"], "objetivo": objetivo,
        "intencao": intencao, "estilo": estilo,
        "modo_execucao": "hibrido" if analise_ia else "offline",
        "metricas": metricas_completas, "analise_ia": analise_ia,
        "pontuacao_geral": pontuacao,
    }
    analise_id = database.salvar_analise_com_recomendacoes(analise, recomendacoes, caminho_banco)
    return {
        "analise_id": analise_id, "pontuacao_geral": pontuacao,
        "dimensoes": dimensoes, "metricas": metricas_completas,
        "analise_ia": analise_ia, "problemas": problemas,
        "recomendacoes": recomendacoes, "modo_execucao": analise["modo_execucao"],
        "erro_ia": resultado_ia.get("erro"),
    }

