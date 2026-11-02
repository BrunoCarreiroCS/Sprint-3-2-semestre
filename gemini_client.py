"""Cliente Gemini isolado, validado e com falhas controladas."""

from __future__ import annotations

import json
import time
from pathlib import Path

from PIL import Image

from config import GEMINI_MAX_TENTATIVAS, GEMINI_TIMEOUT_MS, get_gemini_api_key, get_gemini_model


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
        raise GeminiResponseError("Resposta da IA não é um objeto JSON.")
    obrigatorios = {"assunto_principal", "tipo_cena", "intencao_percebida", "movimento_percebido", "problemas", "composicao", "acoes_sugeridas", "incertezas"}
    ausentes = obrigatorios - set(dados)
    if ausentes:
        raise GeminiResponseError(f"Campos ausentes: {', '.join(sorted(ausentes))}.")
    if not isinstance(dados["movimento_percebido"], bool):
        raise GeminiResponseError("movimento_percebido deve ser booleano.")
    if not isinstance(dados["problemas"], list) or not isinstance(dados["acoes_sugeridas"], list):
        raise GeminiResponseError("Problemas e ações devem ser listas.")
    problemas_validos = []
    incertezas = list(dados.get("incertezas", [])) if isinstance(dados.get("incertezas"), list) else []
    for item in dados["problemas"]:
        if not isinstance(item, dict):
            continue
        codigo = item.get("codigo")
        confianca = item.get("confianca")
        if codigo not in PROBLEMAS_PERMITIDOS:
            incertezas.append(f"Código de problema ignorado: {codigo}")
            continue
        if not isinstance(confianca, (int, float)) or not 0 <= confianca <= 1:
            raise GeminiResponseError("Confiança deve estar entre 0 e 1.")
        problemas_validos.append({
            "codigo": codigo, "confianca": float(confianca),
            "evidencia_visual": str(item.get("evidencia_visual", "")).strip()[:240],
        })
    composicao = dados["composicao"]
    if not isinstance(composicao, dict) or not isinstance(composicao.get("pontuacao"), (int, float)):
        raise GeminiResponseError("Composição inválida.")
    pontuacao = float(composicao["pontuacao"])
    if not 0 <= pontuacao <= 100:
        raise GeminiResponseError("Pontuação de composição fora do intervalo.")
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


def analisar_com_gemini_demo(caminho_imagem: str | Path, objetivo: str, intencao: str) -> dict:
    """Cliente de demonstracao: devolve uma leitura plausivel sem chamar a API real.
    Ativado por JOVI_DEMO_MODE, para apresentar o modo hibrido sem depender de rede ou chave."""
    dados = validar_resposta_ia({
        "assunto_principal": "Assunto principal em primeiro plano",
        "tipo_cena": "ambiente interno com pouca luz",
        "intencao_percebida": intencao or "registro pessoal",
        "movimento_percebido": False,
        "problemas": [
            {"codigo": "pouca_luz", "confianca": 0.82, "evidencia_visual": "Sombras profundas cobrindo parte do assunto."},
            {"codigo": "composicao_fraca", "confianca": 0.55, "evidencia_visual": "Assunto próximo da borda do quadro."},
        ],
        "composicao": {"pontuacao": 58.0, "observacao": "Enquadramento poderia centralizar melhor o assunto principal."},
        "acoes_sugeridas": ["adicionar_iluminacao", "modo_noturno", "reposicionar_enquadramento"],
        "incertezas": ["Resposta gerada em modo de demonstração (JOVI_DEMO_MODE); não reflete a foto real."],
    })
    return {"sucesso": True, "dados": dados, "erro": None}


def categorizar_erro(exc: Exception) -> str:
    """Classifica excecoes do SDK do Gemini (que variam por versao) em categorias estaveis."""
    nome = type(exc).__name__.lower()
    texto = str(exc).lower()
    if "quota" in texto or "resourceexhausted" in nome or "429" in texto:
        return "quota"
    if "auth" in nome or "401" in texto or "403" in texto or "api key" in texto:
        return "autenticacao"
    if "404" in texto or "not_found" in texto or "notfound" in nome:
        return "modelo_indisponivel"
    if "503" in texto or "504" in texto or "unavailable" in nome or "deadline" in texto:
        return "servidor_sobrecarregado"
    if "timeout" in nome or "timed out" in texto:
        return "timeout"
    if "network" in nome or "connect" in nome:
        return "rede"
    return "falha_api"


_ERROS_TRANSITORIOS = {"timeout", "servidor_sobrecarregado", "rede"}


def analisar_com_gemini(caminho_imagem: str | Path, objetivo: str, intencao: str) -> dict:
    chave = get_gemini_api_key()
    if not chave:
        return {"sucesso": False, "dados": None, "erro": "chave_ausente"}
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
    prompt = (
        "Analise esta fotografia como tutor de fotografia. Seja conservador: descreva apenas evidências visíveis. "
        f"Objetivo declarado: {objetivo}. Intenção declarada: {intencao}. "
        "Não identifique pessoas. Diferencie problema técnico de escolha artística."
    )
    erro_final = "falha_api"
    for _tentativa in range(GEMINI_MAX_TENTATIVAS):
        try:
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
            erro_final = categorizar_erro(exc)
            if erro_final not in _ERROS_TRANSITORIOS:
                break
            if _tentativa < GEMINI_MAX_TENTATIVAS - 1:
                time.sleep(2 * (_tentativa + 1))
    return {"sucesso": False, "dados": None, "erro": erro_final}

