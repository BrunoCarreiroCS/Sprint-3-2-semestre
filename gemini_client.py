"""Cliente Gemini isolado, validado e com falhas controladas."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from config import get_gemini_api_key, get_gemini_model


PROBLEMAS_PERMITIDOS = {
    "pouca_luz", "excesso_luz", "desfoque", "sujeito_borrado", "ruido",
    "baixo_contraste", "saturacao_excessiva", "realces_estourados",
    "baixa_resolucao", "zoom_digital", "composicao_fraca", "assunto_centralizado",
}
ACOES_PERMITIDAS = {
    "adicionar_iluminacao", "modo_noturno", "estabilizar_camera", "reduzir_exposicao",
    "ajustar_contraste", "reduzir_saturacao", "aumentar_nitidez", "evitar_zoom_digital",
    "reposicionar_enquadramento",
}


class GeminiResponseError(ValueError):
    pass


def validar_resposta_ia(dados: dict) -> dict:
    if not isinstance(dados, dict):
        raise GeminiResponseError("Resposta da IA nao e um objeto JSON.")
    obrigatorios = {"assunto_principal", "tipo_cena", "intencao_percebida", "movimento_percebido", "problemas", "composicao", "acoes_sugeridas", "incertezas"}
    ausentes = obrigatorios - set(dados)
    if ausentes:
        raise GeminiResponseError(f"Campos ausentes: {', '.join(sorted(ausentes))}.")
    if not isinstance(dados["movimento_percebido"], bool):
        raise GeminiResponseError("movimento_percebido deve ser booleano.")
    if not isinstance(dados["problemas"], list) or not isinstance(dados["acoes_sugeridas"], list):
        raise GeminiResponseError("Problemas e acoes devem ser listas.")
    problemas_validos = []
    incertezas = list(dados.get("incertezas", [])) if isinstance(dados.get("incertezas"), list) else []
    for item in dados["problemas"]:
        if not isinstance(item, dict):
            continue
        codigo = item.get("codigo")
        confianca = item.get("confianca")
        if codigo not in PROBLEMAS_PERMITIDOS:
            incertezas.append(f"Codigo de problema ignorado: {codigo}")
            continue
        if not isinstance(confianca, (int, float)) or not 0 <= confianca <= 1:
            raise GeminiResponseError("Confianca deve estar entre 0 e 1.")
        problemas_validos.append({
            "codigo": codigo, "confianca": float(confianca),
            "evidencia_visual": str(item.get("evidencia_visual", "")).strip()[:240],
        })
    composicao = dados["composicao"]
    if not isinstance(composicao, dict) or not isinstance(composicao.get("pontuacao"), (int, float)):
        raise GeminiResponseError("Composicao invalida.")
    pontuacao = float(composicao["pontuacao"])
    if not 0 <= pontuacao <= 100:
        raise GeminiResponseError("Pontuacao de composicao fora do intervalo.")
    acoes = [acao for acao in dados["acoes_sugeridas"] if acao in ACOES_PERMITIDAS]
    return {
        "assunto_principal": str(dados["assunto_principal"])[:80],
        "tipo_cena": str(dados["tipo_cena"])[:80],
        "intencao_percebida": str(dados["intencao_percebida"])[:160],
        "movimento_percebido": dados["movimento_percebido"],
        "problemas": problemas_validos,
        "composicao": {"pontuacao": round(pontuacao, 1), "observacao": str(composicao.get("observacao", ""))[:240]},
        "acoes_sugeridas": acoes,
        "incertezas": [str(item)[:240] for item in incertezas],
    }


def _schema() -> dict:
    return {
        "type": "object",
        "required": ["assunto_principal", "tipo_cena", "intencao_percebida", "movimento_percebido", "problemas", "composicao", "acoes_sugeridas", "incertezas"],
        "properties": {
            "assunto_principal": {"type": "string"}, "tipo_cena": {"type": "string"},
            "intencao_percebida": {"type": "string"}, "movimento_percebido": {"type": "boolean"},
            "problemas": {"type": "array", "items": {"type": "object", "required": ["codigo", "confianca", "evidencia_visual"], "properties": {"codigo": {"type": "string", "enum": sorted(PROBLEMAS_PERMITIDOS)}, "confianca": {"type": "number", "minimum": 0, "maximum": 1}, "evidencia_visual": {"type": "string"}}}},
            "composicao": {"type": "object", "required": ["pontuacao", "observacao"], "properties": {"pontuacao": {"type": "number", "minimum": 0, "maximum": 100}, "observacao": {"type": "string"}}},
            "acoes_sugeridas": {"type": "array", "items": {"type": "string", "enum": sorted(ACOES_PERMITIDAS)}},
            "incertezas": {"type": "array", "items": {"type": "string"}},
        },
    }


def analisar_com_gemini(caminho_imagem: str | Path, objetivo: str, intencao: str) -> dict:
    chave = get_gemini_api_key()
    if not chave:
        return {"sucesso": False, "dados": None, "erro": "chave_ausente"}
    try:
        from google import genai
        from google.genai import types

        cliente = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=20_000))
        prompt = (
            "Analise esta fotografia como tutor de fotografia. Seja conservador: descreva apenas evidencias visiveis. "
            f"Objetivo declarado: {objetivo}. Intencao declarada: {intencao}. "
            "Nao identifique pessoas. Diferencie problema tecnico de escolha artistica."
        )
        with Image.open(caminho_imagem) as imagem:
            resposta = cliente.models.generate_content(
                model=get_gemini_model(),
                contents=[prompt, imagem],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=_schema(),
                    temperature=0.2,
                ),
            )
        texto = getattr(resposta, "text", None)
        if not texto:
            return {"sucesso": False, "dados": None, "erro": "resposta_vazia"}
        dados = validar_resposta_ia(json.loads(texto))
        return {"sucesso": True, "dados": dados, "erro": None}
    except GeminiResponseError:
        return {"sucesso": False, "dados": None, "erro": "resposta_invalida"}
    except json.JSONDecodeError:
        return {"sucesso": False, "dados": None, "erro": "json_invalido"}
    except Exception as exc:  # SDK possui varias classes de erro por versao.
        nome = type(exc).__name__.lower()
        texto = str(exc).lower()
        if "quota" in texto or "resourceexhausted" in nome or "429" in texto:
            categoria = "quota"
        elif "auth" in nome or "401" in texto or "403" in texto or "api key" in texto:
            categoria = "autenticacao"
        elif "timeout" in nome or "timed out" in texto:
            categoria = "timeout"
        elif "network" in nome or "connect" in nome:
            categoria = "rede"
        else:
            categoria = "falha_api"
        return {"sucesso": False, "dados": None, "erro": categoria}

