"""Comparacao de recapturas e atualizacao controlada do aprendizado."""

from __future__ import annotations

from pathlib import Path

import database
from config import DB_PATH


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
    caminho_banco: str | Path = DB_PATH,
) -> dict:
    antes = database.buscar_analise(analise_antes_id, caminho_banco)
    depois = database.buscar_analise(analise_depois_id, caminho_banco)
    if not antes or not depois:
        raise ValueError("Analise original ou recaptura nao encontrada.")
    if antes["usuario_id"] != usuario_id or depois["usuario_id"] != usuario_id:
        raise ValueError("As analises devem pertencer ao usuario ativo.")
    if antes.get("eh_simulacao") or depois.get("eh_simulacao"):
        raise ValueError("Simulacoes nao podem ser usadas como recaptura.")
    recomendacoes = database.listar_recomendacoes(analise_antes_id, caminho_banco)
    rec = next((item for item in recomendacoes if item["id"] == recomendacao_id), None)
    if rec is None:
        raise ValueError("A recomendacao nao pertence a analise original.")
    if not 1 <= avaliacao <= 5:
        raise ValueError("A avaliacao deve estar entre 1 e 5.")

    ganho = round(float(depois["pontuacao_geral"]) - float(antes["pontuacao_geral"]), 2)
    ajuste = calcular_ajuste_peso(ganho, avaliacao)
    resultado = classificar_resultado(ganho, avaliacao)
    contexto = antes["metricas"].get("contexto_chave", "contexto_desconhecido")

    with database.transacao(caminho_banco) as conn:
        cursor = conn.execute(
            """INSERT INTO comparacoes(
                usuario_id,analise_antes_id,analise_depois_id,recomendacao_id,ganho_real,
                resultado,avaliacao,comentario,peso_aplicado,criado_em
            ) VALUES(?,?,?,?,?,?,?,?,1,?)""",
            (usuario_id, analise_antes_id, analise_depois_id, recomendacao_id, ganho, resultado, avaliacao, comentario[:500], database.agora_iso()),
        )
        atual = conn.execute(
            "SELECT * FROM pesos_aprendizado WHERE usuario_id=? AND contexto_chave=? AND codigo_acao=?",
            (usuario_id, contexto, rec["codigo_acao"]),
        ).fetchone()
        peso_anterior = float(atual["peso"]) if atual else 1.0
        novo_peso = round(max(0.5, min(1.5, peso_anterior + ajuste)), 2)
        sucesso = 1 if ajuste > 0 else 0
        falha = 1 if ajuste < 0 else 0
        conn.execute(
            """INSERT INTO pesos_aprendizado(usuario_id,contexto_chave,codigo_acao,peso,sucessos,falhas,atualizado_em)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(usuario_id,contexto_chave,codigo_acao) DO UPDATE SET
                peso=excluded.peso,
                sucessos=pesos_aprendizado.sucessos + excluded.sucessos,
                falhas=pesos_aprendizado.falhas + excluded.falhas,
                atualizado_em=excluded.atualizado_em""",
            (usuario_id, contexto, rec["codigo_acao"], novo_peso, sucesso, falha, database.agora_iso()),
        )
        comparacao_id = int(cursor.lastrowid)

    dimensoes_antes = antes["metricas"].get("dimensoes", {})
    dimensoes_depois = depois["metricas"].get("dimensoes", {})
    deltas = {
        chave: round(float(dimensoes_depois.get(chave, 0)) - float(valor), 2)
        for chave, valor in dimensoes_antes.items()
    }
    return {
        "comparacao_id": comparacao_id, "ganho_real": ganho, "resultado": resultado,
        "peso_anterior": peso_anterior, "novo_peso": novo_peso, "ajuste": ajuste,
        "deltas": deltas, "codigo_acao": rec["codigo_acao"],
    }


def resumo_evolucao(usuario_id: int, caminho_banco: str | Path = DB_PATH) -> dict:
    with database.conectar(caminho_banco) as conn:
        comparacoes = conn.execute(
            "SELECT ganho_real,resultado,recomendacao_id FROM comparacoes WHERE usuario_id=? ORDER BY id",
            (usuario_id,),
        ).fetchall()
        pesos = conn.execute(
            "SELECT codigo_acao,peso,sucessos,falhas FROM pesos_aprendizado WHERE usuario_id=? ORDER BY peso DESC,sucessos DESC",
            (usuario_id,),
        ).fetchall()
        analises = conn.execute(
            "SELECT pontuacao_geral FROM analises WHERE usuario_id=? ORDER BY id",
            (usuario_id,),
        ).fetchall()
    ganhos = [float(item["ganho_real"]) for item in comparacoes]
    media = round(sum(ganhos) / len(ganhos), 2) if ganhos else 0.0
    melhor = dict(pesos[0]) if pesos else None
    inicial = float(analises[0]["pontuacao_geral"]) if analises else 0.0
    recente = float(analises[-1]["pontuacao_geral"]) if analises else 0.0
    return {
        "total_analises": len(analises), "total_comparacoes": len(comparacoes),
        "ganho_medio": media, "evolucao_pontuacao": round(recente - inicial, 2) if len(analises) > 1 else 0.0,
        "melhor_acao": melhor, "sucessos": sum(1 for item in comparacoes if item["resultado"] == "sucesso"),
    }

