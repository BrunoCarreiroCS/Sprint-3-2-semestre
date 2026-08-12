"""Formatacao de resultados e exportacao sem dados sensiveis."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import database
from config import DB_PATH, OUTPUT_DIR
from learning_engine import resumo_evolucao


ROTULOS = {
    "exposicao": "Exposicao", "nitidez": "Nitidez", "contraste": "Contraste",
    "cor": "Cor", "resolucao": "Resolucao", "intencao": "Adequacao a intencao",
}


def formatar_analise(resultado: dict) -> str:
    linhas = [
        "\n" + "=" * 64,
        "DIAGNOSTICO JOVI AI LENSLAB",
        "=" * 64,
        f"Modo: {resultado['modo_execucao'].upper()}",
        f"Pontuacao contextual: {resultado['pontuacao_geral']:.1f}/100",
        "\n[MEDIDO] Dimensoes tecnicas e contextuais:",
    ]
    for chave, valor in resultado["dimensoes"].items():
        linhas.append(f"  - {ROTULOS.get(chave, chave)}: {valor:.1f}/100")
    if resultado.get("analise_ia"):
        ia = resultado["analise_ia"]
        linhas.extend([
            "\n[IA] Leitura semantica validada:",
            f"  - Assunto: {ia['assunto_principal']}",
            f"  - Cena: {ia['tipo_cena']}",
            f"  - Composicao: {ia['composicao']['pontuacao']}/100",
        ])
    else:
        linhas.append(f"\n[IA] Indisponivel; analise offline ativada ({resultado.get('erro_ia')}).")
    linhas.append("\n[PREVISTO] Alternativas 'E se?':")
    for indice, rec in enumerate(resultado["recomendacoes"], 1):
        linhas.extend([
            f"\n  {indice}. {rec['codigo_acao'].replace('_', ' ').title()}",
            f"     Ganho previsto: +{rec['ganho_previsto']:.1f} | Confianca: {rec['confianca']} | Esforco: {rec['esforco']}",
            f"     Por que: {rec['explicacao']}",
            f"     Risco: {rec['risco']}",
        ])
        for evidencia in rec.get("evidencias", []):
            linhas.append(f"     Evidencia: {evidencia}")
    return "\n".join(linhas)


def formatar_comparacao(resultado: dict) -> str:
    linhas = [
        "\n" + "=" * 64, "RECAPTURA VERIFICADA", "=" * 64,
        f"Acao aplicada: {resultado['codigo_acao'].replace('_', ' ').title()}",
        f"Ganho real: {resultado['ganho_real']:+.1f} pontos",
        f"Resultado: {resultado['resultado'].upper()}",
        f"Peso personalizado: {resultado['peso_anterior']:.2f} -> {resultado['novo_peso']:.2f}",
        "\n[VERIFICADO] Mudancas por dimensao:",
    ]
    for chave, delta in resultado["deltas"].items():
        linhas.append(f"  - {ROTULOS.get(chave, chave)}: {delta:+.1f}")
    return "\n".join(linhas)


def formatar_evolucao(usuario_id: int, caminho_banco: str | Path = DB_PATH) -> str:
    resumo = resumo_evolucao(usuario_id, caminho_banco)
    linhas = [
        "\n" + "=" * 64, "EVOLUCAO FOTOGRAFICA", "=" * 64,
        f"Analises realizadas: {resumo['total_analises']}",
        f"Recapturas verificadas: {resumo['total_comparacoes']}",
        f"Ganho medio por recaptura: {resumo['ganho_medio']:+.1f}",
        f"Evolucao entre primeira e ultima analise: {resumo['evolucao_pontuacao']:+.1f}",
        f"Recapturas bem-sucedidas: {resumo['sucessos']}",
    ]
    if resumo["melhor_acao"]:
        linhas.append(f"Conselho mais eficaz: {resumo['melhor_acao']['codigo_acao'].replace('_', ' ').title()}")
    else:
        linhas.append("Conselho mais eficaz: ainda nao ha dados suficientes.")
    return "\n".join(linhas)


def exportar_resumo(usuario_id: int, caminho_banco: str | Path = DB_PATH) -> Path:
    usuario = database.buscar_usuario(usuario_id, caminho_banco)
    if not usuario:
        raise ValueError("Usuario nao encontrado.")
    analises = database.listar_analises(usuario_id, caminho_banco)
    resumo = resumo_evolucao(usuario_id, caminho_banco)
    payload = {
        "perfil": {"apelido": usuario["apelido"], "nivel": usuario["nivel"], "estilo": usuario["estilo_preferido"]},
        "resumo": resumo,
        "analises": [{k: v for k, v in item.items() if k not in {"imagem_hash"}} for item in analises],
        "exportado_em": datetime.now().isoformat(timespec="seconds"),
    }
    destino_dir = OUTPUT_DIR / "exportacoes"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"resumo_usuario_{usuario_id}.json"
    destino.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino

