"""Formatacao de resultados e exportacao sem dados sensiveis."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import database
from config import DADOS_DIR, OUTPUT_DIR
from learning_engine import resumo_evolucao
from recommendation_engine import formatar_contexto
from textos import legivel

try:
    from colorama import Fore, Style, init as _colorama_init

    _colorama_init(autoreset=False)
except ImportError:  # colorama e opcional; sem ela o texto fica sem cor.
    class _SemCor:
        def __getattr__(self, _nome: str) -> str:
            return ""

    Fore = Style = _SemCor()  # type: ignore[assignment]

_COR_ROTULO = {"MEDIDO": Fore.CYAN, "IA": Fore.MAGENTA, "PREVISTO": Fore.YELLOW, "VERIFICADO": Fore.GREEN}


def _rotulo(nome: str) -> str:
    return f"{_COR_ROTULO.get(nome, '')}[{nome}]{Style.RESET_ALL}"


def _barra(valor: float, largura: int = 20) -> str:
    """Barra ASCII (sem caracteres especiais, segura em qualquer console Windows)."""
    preenchido = max(0, min(largura, round((valor / 100) * largura)))
    return "#" * preenchido + "-" * (largura - preenchido)


ERRO_IA_LEGIVEL = {
    "modo_offline": "consentimento ou chave não configurados",
    "chave_ausente": "GEMINI_API_KEY não configurada",
    "modelo_indisponivel": "o modelo configurado (GEMINI_MODEL) não está disponível para esta chave",
    "servidor_sobrecarregado": "servidor do Gemini sobrecarregado; tente novamente em instantes",
    "quota": "cota da API excedida",
    "autenticacao": "chave de API inválida ou sem permissão",
    "timeout": "tempo de resposta da API esgotado",
    "rede": "falha de conexão com a API",
    "resposta_vazia": "a API respondeu sem conteúdo",
    "resposta_invalida": "a resposta da API não passou na validação de schema",
    "json_invalido": "a resposta da API não era um JSON válido",
    "falha_api": "falha inesperada ao chamar a API do Gemini",
}


ROTULOS = {
    "exposicao": "Exposição", "nitidez": "Nitidez", "contraste": "Contraste",
    "cor": "Cor", "resolucao": "Resolução", "intencao": "Adequação à intenção",
}

FAIXAS_PONTUACAO = [
    (80, "Ótima"),
    (65, "Boa, mas dá pra melhorar"),
    (45, "Regular, tem bastante espaço pra melhorar"),
    (0, "Precisa de ajustes importantes"),
]

DIMENSOES_PLAIN = {
    "exposicao": ("boa exposição de luz", "está muito escura ou muito clara"),
    "nitidez": ("está nítida", "está desfocada"),
    "contraste": ("bom contraste entre luz e sombra", "contraste baixo, a imagem fica meio 'lavada'"),
    "cor": ("cores naturais e equilibradas", "cores muito saturadas ou meio desbotadas"),
    "resolucao": ("boa resolução pra recortar ou ampliar", "resolução baixa, pouco espaço pra recortar"),
    "intencao": ("bom enquadramento pro que você queria", "o enquadramento pode melhorar"),
}


def classificar_pontuacao(pontuacao: float) -> str:
    for limite, texto in FAIXAS_PONTUACAO:
        if pontuacao >= limite:
            return texto
    return FAIXAS_PONTUACAO[-1][1]


def pontos_fortes_e_fracos(dimensoes: dict) -> tuple[list[str], list[str]]:
    fortes, fracos = [], []
    for chave, valor in dimensoes.items():
        textos = DIMENSOES_PLAIN.get(chave)
        if not textos:
            continue
        if valor >= 65:
            fortes.append(textos[0])
        elif valor < 45:
            fracos.append(textos[1])
    return fortes, fracos


def _classificar_ganho(ganho: float) -> str:
    if ganho >= 25:
        return "melhoria grande esperada"
    if ganho >= 12:
        return "melhoria moderada esperada"
    return "melhoria pequena esperada"


def formatar_resumo_analise(resultado: dict) -> str:
    """Versao curta e em linguagem simples do diagnostico, mostrada por padrao."""
    pontuacao = resultado["pontuacao_geral"]
    fortes, fracos = pontos_fortes_e_fracos(resultado["dimensoes"])
    linhas = [
        "\n" + "=" * 64,
        "RESULTADO DA SUA FOTO",
        "=" * 64,
        f"Nota geral: {pontuacao:.0f}/100  [{_barra(pontuacao)}]  - {classificar_pontuacao(pontuacao)}",
    ]
    if fortes:
        linhas.append("\nO que está bom:")
        linhas.extend(f"  + {item.capitalize()}" for item in fortes[:3])
    if fracos:
        linhas.append("\nO que pode melhorar:")
        linhas.extend(f"  - {item.capitalize()}" for item in fracos[:3])
    recomendacoes = resultado.get("recomendacoes", [])
    if recomendacoes and recomendacoes[0]["codigo_acao"] != "manter_configuracao":
        principal = recomendacoes[0]
        linhas.extend([
            f"\nNossa principal dica: {legivel(principal['codigo_acao'])}",
            f"  {principal['explicacao']}",
            f"  ({_classificar_ganho(principal['ganho_previsto'])})",
        ])
        extras = len(recomendacoes) - 1
        if extras > 0:
            linhas.append(f"  (+ {extras} outra(s) sugestão(ões) nos detalhes completos)")
    elif recomendacoes:
        linhas.append(f"\n{recomendacoes[0]['explicacao']}")
    if not resultado.get("analise_ia"):
        linhas.append("\nObs: a leitura extra por IA não estava disponível agora; usamos só as medidas da foto.")
    return "\n".join(linhas)


VEREDITO_COMPARACAO = {
    "sucesso": "Funcionou! A dica ajudou de verdade.",
    "misto": "Ajudou em parte, mas o resultado não foi só positivo.",
    "falha": "Não ajudou nessa recaptura.",
    "inconclusivo": "Resultado neutro; difícil dizer se ajudou.",
}


def formatar_resumo_comparacao(resultado: dict) -> str:
    """Versao curta do resultado da recaptura, mostrada por padrao."""
    ganho = resultado["ganho_real"]
    if ganho > 0:
        direcao = f"sua foto melhorou {ganho:.0f} pontos"
    elif ganho < 0:
        direcao = f"sua foto piorou {abs(ganho):.0f} pontos"
    else:
        direcao = "a pontuação ficou igual"
    veredito = VEREDITO_COMPARACAO.get(resultado["resultado"], resultado["resultado"])
    return "\n".join([
        "\n" + "=" * 64, "RESULTADO DA RECAPTURA", "=" * 64,
        f"{veredito}",
        f"Com a dica de {legivel(resultado['codigo_acao'])}, {direcao}.",
    ])


def formatar_analise(resultado: dict) -> str:
    linhas = [
        "\n" + "=" * 64,
        "DIAGNÓSTICO JOVI AI LENSLAB",
        "=" * 64,
        f"Modo: {legivel(resultado['modo_execucao']).upper()}",
        f"Pontuação contextual: {resultado['pontuacao_geral']:.1f}/100  [{_barra(resultado['pontuacao_geral'])}]",
        f"\n{_rotulo('MEDIDO')} Dimensões técnicas e contextuais:",
    ]
    for chave, valor in resultado["dimensoes"].items():
        linhas.append(f"  - {ROTULOS.get(chave, chave):22s} [{_barra(valor, 10)}] {valor:.1f}/100")
    if resultado.get("analise_ia"):
        ia = resultado["analise_ia"]
        linhas.extend([
            f"\n{_rotulo('IA')} Leitura semântica validada:",
            f"  - Assunto: {ia['assunto_principal']}",
            f"  - Cena: {ia['tipo_cena']}",
            f"  - Composição: {ia['composicao']['pontuacao']}/100",
        ])
    else:
        codigo_erro = resultado.get("erro_ia")
        motivo = ERRO_IA_LEGIVEL.get(codigo_erro, codigo_erro)
        linhas.append(f"\n{_rotulo('IA')} Indisponível; análise offline ativada ({motivo}).")
    linhas.append(f"\n{_rotulo('PREVISTO')} Alternativas 'E se?':")
    for indice, rec in enumerate(resultado["recomendacoes"], 1):
        linhas.extend([
            f"\n  {indice}. {legivel(rec['codigo_acao'])}",
            f"     Ganho previsto: +{rec['ganho_previsto']:.1f} | Confiança: {rec['confianca']} | Esforço: {rec['esforco']}",
            f"     Por que: {rec['explicacao']}",
            f"     Risco: {rec['risco']}",
        ])
        for evidencia in rec.get("evidencias", []):
            linhas.append(f"     Evidência: {evidencia}")
        peso = rec.get("peso_aprendido", 1.0)
        if abs(peso - 1.0) > 0.01:
            direcao = "acima" if peso > 1.0 else "abaixo"
            linhas.append(f"     Ajustado pelo seu histórico: peso {peso:.2f} ({direcao} da média padrão)")
    return "\n".join(linhas)


def formatar_comparacao(resultado: dict) -> str:
    linhas = [
        "\n" + "=" * 64, "RECAPTURA VERIFICADA", "=" * 64,
        f"Ação aplicada: {legivel(resultado['codigo_acao'])}",
        f"Ganho real: {resultado['ganho_real']:+.1f} pontos",
        f"Resultado: {resultado['resultado'].upper()}",
        f"Peso personalizado: {resultado['peso_anterior']:.2f} -> {resultado['novo_peso']:.2f}",
        f"Fator de confiança aplicado: {resultado['fator_confianca']:.2f} "
        f"(baseado em {resultado['amostras_anteriores']} comparação(ões) anteriores neste contexto)",
        f"\n{_rotulo('VERIFICADO')} Mudanças por dimensão:",
    ]
    for chave, delta in resultado["deltas"].items():
        linhas.append(f"  - {ROTULOS.get(chave, chave)}: {delta:+.1f}")
    return "\n".join(linhas)


def formatar_evolucao(usuario_id: int, pasta_dados: str | Path = DADOS_DIR) -> str:
    resumo = resumo_evolucao(usuario_id, pasta_dados)
    linhas = [
        "\n" + "=" * 64, "EVOLUÇÃO FOTOGRÁFICA", "=" * 64,
        f"Análises realizadas: {resumo['total_analises']}",
        f"Recapturas verificadas: {resumo['total_comparacoes']}",
        f"Ganho médio por recaptura: {resumo['ganho_medio']:+.1f}",
        f"Evolução entre primeira e última análise: {resumo['evolucao_pontuacao']:+.1f}",
        f"Recapturas bem-sucedidas: {resumo['sucessos']}",
    ]
    if resumo["principais_pesos"]:
        linhas.append("\nConselhos com melhor desempenho no seu perfil:")
        for item in resumo["principais_pesos"]:
            linhas.append(
                f"  - {legivel(item['codigo_acao'])} "
                f"(peso {item['peso']:.2f}, {item['sucessos']} sucesso(s)) em: {formatar_contexto(item['contexto_chave'])}"
            )
    else:
        linhas.append("\nConselhos com melhor desempenho: ainda não há dados suficientes.")
    return "\n".join(linhas)


def exportar_resumo(usuario_id: int, pasta_dados: str | Path = DADOS_DIR) -> Path:
    usuario = database.buscar_usuario(usuario_id, pasta_dados)
    if not usuario:
        raise ValueError("Usuário não encontrado.")
    analises = database.listar_analises(usuario_id, pasta_dados)
    resumo = resumo_evolucao(usuario_id, pasta_dados)
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

