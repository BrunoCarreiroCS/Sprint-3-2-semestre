"""Comparacao de recapturas e atualizacao controlada do aprendizado."""

from __future__ import annotations

from pathlib import Path

import database
from config import DADOS_DIR


def calcular_ajuste_peso(ganho_real: float, avaliacao: int) -> float:
    if ganho_real >= 5 and avaliacao >= 3:
        return 0.10
    if ganho_real < -5 or avaliacao <= 2:
        if ganho_real >= 5 and avaliacao <= 2:
            return 0.0
        if ganho_real < -5 and avaliacao >= 4:
            return -0.03
        return -0.10
    if -5 <= ganho_real < 5 and avaliacao >= 4:
        return 0.03
    return 0.0


def calcular_fator_confianca(amostras_anteriores: int) -> float:
    """Reduz o efeito de cada nova comparacao conforme mais evidencia se acumula
    naquele contexto, para que poucos exemplos nao dominem o peso aprendido."""
    return round(max(0.3, 1.0 - amostras_anteriores * 0.07), 2)


def classificar_resultado(ganho_real: float, avaliacao: int) -> str:
    if ganho_real >= 5 and avaliacao >= 3:
        return "sucesso"
    if ganho_real < -5 or avaliacao <= 2:
        return "falha"
    if abs(ganho_real) < 2 and avaliacao == 3:
        return "inconclusivo"
    return "misto"


def comparar_e_aprender(
    usuario_id: int,
    analise_antes_id: int,
    analise_depois_id: int,
    recomendacao_id: int,
    avaliacao: int,
    comentario: str = "",
    pasta_dados: str | Path = DADOS_DIR,
) -> dict:
    antes = database.buscar_analise(analise_antes_id, pasta_dados)
    depois = database.buscar_analise(analise_depois_id, pasta_dados)
    if not antes or not depois:
        raise ValueError("Análise original ou recaptura não encontrada.")
    if antes["usuario_id"] != usuario_id or depois["usuario_id"] != usuario_id:
        raise ValueError("As análises devem pertencer ao usuário ativo.")
    if antes.get("eh_simulacao") or depois.get("eh_simulacao"):
        raise ValueError("Simulações não podem ser usadas como recaptura.")
    if antes["imagem_hash"] == depois["imagem_hash"]:
        raise ValueError("A recaptura precisa ser uma foto diferente da original.")
    recomendacoes = database.listar_recomendacoes(analise_antes_id, pasta_dados)
    rec = next((item for item in recomendacoes if item["id"] == recomendacao_id), None)
    if rec is None:
        raise ValueError("A recomendação não pertence à análise original.")
    if not 1 <= avaliacao <= 5:
        raise ValueError("A avaliação deve estar entre 1 e 5.")

    ganho = round(float(depois["pontuacao_geral"]) - float(antes["pontuacao_geral"]), 2)
    ajuste = calcular_ajuste_peso(ganho, avaliacao)
    resultado = classificar_resultado(ganho, avaliacao)
    contexto = antes["metricas"].get("contexto_chave", "contexto_desconhecido")

    atual = database.obter_registro_peso(usuario_id, contexto, rec["codigo_acao"], pasta_dados)
    peso_anterior = float(atual["peso"]) if atual else 1.0
    amostras_anteriores = int(atual["sucessos"] + atual["falhas"]) if atual else 0
    fator_confianca = calcular_fator_confianca(amostras_anteriores)
    ajuste_aplicado = round(ajuste * fator_confianca, 4)
    novo_peso = round(max(0.5, min(1.5, peso_anterior + ajuste_aplicado)), 2)
    comparacao_id = database.registrar_comparacao(
        usuario_id,
        {
            "analise_antes_id": analise_antes_id, "analise_depois_id": analise_depois_id,
            "recomendacao_id": recomendacao_id, "codigo_acao": rec["codigo_acao"],
            "ganho_real": ganho, "resultado": resultado, "avaliacao": avaliacao, "comentario": comentario,
        },
        contexto,
        novo_peso,
        sucesso=ajuste_aplicado > 0,
        falha=ajuste_aplicado < 0,
        pasta=pasta_dados,
    )

    dimensoes_antes = antes["metricas"].get("dimensoes", {})
    dimensoes_depois = depois["metricas"].get("dimensoes", {})
    deltas = {
        chave: round(float(dimensoes_depois.get(chave, 0)) - float(valor), 2)
        for chave, valor in dimensoes_antes.items()
    }
    return {
        "comparacao_id": comparacao_id, "ganho_real": ganho, "resultado": resultado,
        "peso_anterior": peso_anterior, "novo_peso": novo_peso, "ajuste": ajuste,
        "ajuste_aplicado": ajuste_aplicado, "fator_confianca": fator_confianca,
        "amostras_anteriores": amostras_anteriores,
        "deltas": deltas, "codigo_acao": rec["codigo_acao"],
    }


def resumo_evolucao(usuario_id: int, pasta_dados: str | Path = DADOS_DIR) -> dict:
    comparacoes = database.listar_comparacoes(usuario_id, pasta_dados)
    pesos = database.listar_pesos(usuario_id, pasta_dados)
    analises = list(reversed(database.listar_analises(usuario_id, pasta_dados)))
    ganhos = [float(item["ganho_real"]) for item in comparacoes]
    media = round(sum(ganhos) / len(ganhos), 2) if ganhos else 0.0
    melhor = dict(pesos[0]) if pesos else None
    principais_pesos = [dict(item) for item in pesos[:3]]
    inicial = float(analises[0]["pontuacao_geral"]) if analises else 0.0
    recente = float(analises[-1]["pontuacao_geral"]) if analises else 0.0
    return {
        "total_analises": len(analises), "total_comparacoes": len(comparacoes),
        "ganho_medio": media, "evolucao_pontuacao": round(recente - inicial, 2) if len(analises) > 1 else 0.0,
        "melhor_acao": melhor, "principais_pesos": principais_pesos,
        "sucessos": sum(1 for item in comparacoes if item["resultado"] == "sucesso"),
    }

