"""Pontuacao contextual, fusao de evidencias e simulacoes contrafactuais."""

from __future__ import annotations

from copy import deepcopy

from image_analyzer import normalizar_nitidez


PESOS_OBJETIVO = {
    "documento": {"exposicao": 20, "nitidez": 30, "contraste": 20, "cor": 10, "resolucao": 15, "intencao": 5},
    "pessoa": {"exposicao": 20, "nitidez": 25, "contraste": 15, "cor": 15, "resolucao": 10, "intencao": 15},
    "retrato": {"exposicao": 20, "nitidez": 25, "contraste": 15, "cor": 15, "resolucao": 10, "intencao": 15},
    "paisagem": {"exposicao": 20, "nitidez": 20, "contraste": 20, "cor": 20, "resolucao": 10, "intencao": 10},
    "produto": {"exposicao": 25, "nitidez": 25, "contraste": 20, "cor": 15, "resolucao": 10, "intencao": 5},
    "redes_sociais": {"exposicao": 15, "nitidez": 20, "contraste": 15, "cor": 20, "resolucao": 10, "intencao": 20},
    "outro": {"exposicao": 20, "nitidez": 20, "contraste": 15, "cor": 15, "resolucao": 10, "intencao": 20},
}

ACOES = {
    "adicionar_iluminacao": {
        "resolve": {"pouca_luz": 1.0, "sujeito_borrado": 0.35},
        "risco": "Pode alterar a atmosfera ou criar sombras duras.", "esforco": "medio",
        "explicacao": "Adicionar luz permite uma captura mais rapida e reduz o borrao sem depender de exposicao longa.",
    },
    "modo_noturno": {
        "resolve": {"pouca_luz": 0.8, "ruido": 0.4},
        "risco": "Exposicao longa pode borrar pessoas ou objetos em movimento.", "esforco": "baixo",
        "explicacao": "O modo noturno combina exposicoes para recuperar detalhes em cenas escuras.",
    },
    "estabilizar_camera": {
        "resolve": {"desfoque": 1.0, "sujeito_borrado": 0.4, "pouca_luz": 0.25},
        "risco": "Nao corrige o movimento do assunto fotografado.", "esforco": "baixo",
        "explicacao": "Apoiar o aparelho ou usar temporizador reduz o tremor provocado pelas maos.",
    },
    "reduzir_exposicao": {
        "resolve": {"excesso_luz": 1.0, "realces_estourados": 0.9, "sujeito_borrado": 0.4},
        "risco": "A imagem pode ficar escura demais.", "esforco": "medio",
        "explicacao": "Uma captura mais curta preserva realces e pode congelar melhor o movimento.",
    },
    "ajustar_contraste": {
        "resolve": {"baixo_contraste": 1.0},
        "risco": "Contraste excessivo pode eliminar detalhes de sombras e luzes.", "esforco": "baixo",
        "explicacao": "Ajustar iluminacao ou contraste ajuda a separar o assunto do fundo.",
    },
    "reduzir_saturacao": {
        "resolve": {"saturacao_excessiva": 1.0},
        "risco": "Cores podem perder impacto visual.", "esforco": "baixo",
        "explicacao": "Reduzir saturacao recupera uma aparencia mais natural.",
    },
    "aumentar_nitidez": {
        "resolve": {"desfoque": 0.45},
        "risco": "Nitidez digital nao recupera detalhes realmente perdidos.", "esforco": "baixo",
        "explicacao": "Uma previa de nitidez evidencia contornos, mas a melhor solucao e recapturar com estabilidade.",
    },
    "evitar_zoom_digital": {
        "resolve": {"baixa_resolucao": 0.75, "zoom_digital": 1.0},
        "risco": "Pode exigir aproximacao fisica do assunto.", "esforco": "medio",
        "explicacao": "Aproximar-se preserva mais detalhes que ampliar digitalmente.",
    },
    "reposicionar_enquadramento": {
        "resolve": {"composicao_fraca": 1.0, "assunto_centralizado": 0.8},
        "risco": "O melhor enquadramento depende da intencao do fotografo.", "esforco": "medio",
        "explicacao": "Mudar posicao, angulo ou recorte pode destacar melhor o assunto principal.",
    },
}


def _clamp(valor: float, minimo: float = 0.0, maximo: float = 100.0) -> float:
    return max(minimo, min(maximo, valor))


def calcular_dimensoes(metricas: dict, objetivo: str, intencao: str, analise_ia: dict | None = None) -> dict:
    brilho = float(metricas.get("brilho", 50))
    alvo_brilho = 48 if "dram" in intencao.lower() else (62 if objetivo == "documento" else 55)
    exposicao = _clamp(100 - abs(brilho - alvo_brilho) * 2.1)
    exposicao -= min(25, float(metricas.get("realces_estourados", 0)) * 1.2)
    exposicao -= min(20, float(metricas.get("sombras_recortadas", 0)) * 0.8)
    nitidez = normalizar_nitidez(float(metricas.get("nitidez_bruta", 0)))
    contraste_raw = float(metricas.get("contraste", 0))
    contraste = _clamp(100 - abs(contraste_raw - 28) * 3.0)
    saturacao = float(metricas.get("saturacao", 0))
    alvo_cor = 52 if objetivo == "redes_sociais" else 42
    cor = _clamp(100 - abs(saturacao - alvo_cor) * 2.0)
    megapixels = float(metricas.get("megapixels", 0))
    resolucao = _clamp(megapixels / 2.0 * 100)
    composicao = (analise_ia or {}).get("composicao", {}).get("pontuacao")
    intencao_score = _clamp(float(composicao)) if isinstance(composicao, (int, float)) else 60.0
    return {
        "exposicao": round(_clamp(exposicao), 2), "nitidez": round(nitidez, 2),
        "contraste": round(contraste, 2), "cor": round(cor, 2),
        "resolucao": round(resolucao, 2), "intencao": round(intencao_score, 2),
    }


def calcular_pontuacao(metricas: dict, objetivo: str, intencao: str, analise_ia: dict | None = None) -> tuple[float, dict]:
    objetivo_normalizado = objetivo if objetivo in PESOS_OBJETIVO else "outro"
    dimensoes = calcular_dimensoes(metricas, objetivo_normalizado, intencao, analise_ia)
    pesos = PESOS_OBJETIVO[objetivo_normalizado]
    total = sum(dimensoes[nome] * peso / 100 for nome, peso in pesos.items())
    return round(_clamp(total), 2), dimensoes


def detectar_problemas(metricas: dict, analise_ia: dict | None = None) -> dict[str, dict]:
    problemas: dict[str, dict] = {}

    def add(codigo: str, severidade: float, fonte: str, evidencia: str) -> None:
        atual = problemas.get(codigo)
        if atual:
            atual["fontes"].append(fonte)
            atual["evidencias"].append(evidencia)
            atual["severidade"] = max(atual["severidade"], severidade)
            atual["estado"] = "confirmada"
        else:
            problemas[codigo] = {
                "severidade": _clamp(severidade, 0, 1), "fontes": [fonte],
                "evidencias": [evidencia], "estado": "provavel",
            }

    brilho = float(metricas.get("brilho", 50))
    if brilho < 35:
        add("pouca_luz", min(1, (35 - brilho) / 25 + 0.35), "MEDIDO", f"Brilho medido em {brilho:.1f}/100.")
    if brilho > 78:
        add("excesso_luz", min(1, (brilho - 78) / 20 + 0.35), "MEDIDO", f"Brilho medido em {brilho:.1f}/100.")
    nitidez = float(metricas.get("nitidez_bruta", 0))
    if nitidez < 120:
        add("desfoque", min(1, (120 - nitidez) / 120 + 0.25), "MEDIDO", f"Indice de nitidez bruto em {nitidez:.1f}.")
    if float(metricas.get("contraste", 0)) < 14:
        add("baixo_contraste", 0.7, "MEDIDO", "Dispersao de luminancia abaixo do intervalo de referencia.")
    if float(metricas.get("saturacao", 0)) > 72:
        add("saturacao_excessiva", 0.7, "MEDIDO", "Saturacao media elevada.")
    if float(metricas.get("realces_estourados", 0)) > 8:
        add("realces_estourados", 0.8, "MEDIDO", "Muitos pixels proximos do branco absoluto.")
    if float(metricas.get("megapixels", 0)) < 0.5:
        add("baixa_resolucao", 0.75, "MEDIDO", "Resolucao limitada para recorte ou ampliacao.")

    for problema in (analise_ia or {}).get("problemas", []):
        codigo = problema.get("codigo")
        if not codigo:
            continue
        add(
            codigo, float(problema.get("confianca", 0.5)), "IA",
            str(problema.get("evidencia_visual", "Inferencia visual sem detalhe.")),
        )
    composicao = (analise_ia or {}).get("composicao", {})
    if isinstance(composicao.get("pontuacao"), (int, float)) and composicao["pontuacao"] < 55:
        add("composicao_fraca", (55 - composicao["pontuacao"]) / 55 + 0.4, "IA", composicao.get("observacao", "Composicao pode melhorar."))
    return problemas


def gerar_contexto_chave(objetivo: str, metricas: dict, movimento: bool, nivel: str, estilo: str) -> str:
    brilho = float(metricas.get("brilho", 50))
    faixa = "escuro" if brilho < 35 else "claro" if brilho > 75 else "equilibrado"
    return f"{objetivo}|{faixa}|{'movimento' if movimento else 'estatico'}|{nivel}|{estilo}"


def simular_intervencoes(
    problemas: dict[str, dict],
    movimento: bool,
    pesos_aprendidos: dict[str, float] | None = None,
    limite: int = 3,
) -> list[dict]:
    pesos_aprendidos = pesos_aprendidos or {}
    alternativas: list[dict] = []
    for codigo, definicao in ACOES.items():
        contribuicoes = []
        ganho = 0.0
        for problema, eficacia in definicao["resolve"].items():
            if problema in problemas:
                item = problemas[problema]
                contribuicao = 28 * float(item["severidade"]) * eficacia
                ganho += contribuicao
                contribuicoes.extend(item["evidencias"])
        if ganho <= 0:
            continue
        if codigo == "modo_noturno" and movimento:
            ganho *= 0.45
            contribuicoes.append("Movimento detectado reduz a utilidade de exposicao prolongada.")
        peso = _clamp(float(pesos_aprendidos.get(codigo, 1.0)), 0.5, 1.5)
        ganho = _clamp(ganho * peso, 0, 35)
        fontes = {fonte for problema in problemas.values() for fonte in problema["fontes"] if any(e in contribuicoes for e in problema["evidencias"])}
        confianca = "alta" if {"MEDIDO", "IA"}.issubset(fontes) else "media" if fontes else "baixa"
        alternativas.append({
            "codigo_acao": codigo,
            "ganho_previsto": round(ganho, 1),
            "risco": definicao["risco"], "esforco": definicao["esforco"],
            "confianca": confianca, "explicacao": definicao["explicacao"],
            "evidencias": list(dict.fromkeys(contribuicoes))[:4],
        })
    alternativas.sort(key=lambda item: (-item["ganho_previsto"], item["esforco"], item["codigo_acao"]))
    if not alternativas:
        alternativas.append({
            "codigo_acao": "manter_configuracao", "ganho_previsto": 0.0,
            "risco": "Nenhum problema tecnico relevante foi confirmado.", "esforco": "baixo",
            "confianca": "media", "explicacao": "A fotografia esta equilibrada para os indicadores avaliados.",
            "evidencias": ["Metricas dentro dos intervalos de referencia."],
        })
    return deepcopy(alternativas[:limite])


def recomendar_sem_foto(perfil: dict, objetivo: str, ambiente: str, movimento: bool) -> list[dict]:
    metricas = {
        "brilho": 25 if ambiente == "escuro" else 82 if ambiente == "muito_claro" else 55,
        "contraste": 24, "nitidez_bruta": 100 if movimento else 180,
        "saturacao": 42, "realces_estourados": 0, "sombras_recortadas": 0,
        "megapixels": 2,
    }
    problemas = detectar_problemas(metricas)
    if movimento:
        problemas["sujeito_borrado"] = {
            "severidade": 0.7, "fontes": ["USUARIO"],
            "evidencias": ["O usuario informou que o assunto esta em movimento."], "estado": "provavel",
        }
    return simular_intervencoes(problemas, movimento)

