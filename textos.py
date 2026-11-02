"""Rotulos legiveis, com acentuacao, para os codigos internos exibidos ao usuario."""

from __future__ import annotations

ACENTOS = {
    "analise": "análise", "avancado": "avançado", "camera": "câmera", "composicao": "composição",
    "configuracao": "configuração", "evolucao": "evolução", "exposicao": "exposição", "hibrido": "híbrido", "iluminacao": "iluminação",
    "intencao": "intenção", "intermediario": "intermediário", "recomendacao": "recomendação",
    "resolucao": "resolução", "ruido": "ruído", "saturacao": "saturação", "simulacao": "simulação",
}


def legivel(codigo: str) -> str:
    """Transforma um codigo como ``adicionar_iluminacao`` em ``Adicionar Iluminação``."""
    palavras = str(codigo).replace("_", " ").split()
    return " ".join(ACENTOS.get(palavra.lower(), palavra.lower()).capitalize() for palavra in palavras)
