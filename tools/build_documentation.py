"""Gera a documentacao academica da Sprint 4 em PDF.

Trechos de codigo, exemplos de JSON, telas do terminal e a contagem de testes
sao extraidos do proprio projeto no momento da geracao, para que o documento
nunca descreva uma versao diferente do codigo entregue.

Uso: python tools/build_documentation.py
"""

from __future__ import annotations

import inspect
import io
import json
import math
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Flowable,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database  # noqa: E402
import integracao  # noqa: E402
import main  # noqa: E402
import validators  # noqa: E402
from analysis_service import analisar_fotografia  # noqa: E402
from config import SAMPLES_DIR  # noqa: E402
from reports import formatar_resumo_analise  # noqa: E402

DESTINO = ROOT / "docs" / "documentacao_nextframe_jovi_sprint4.pdf"
LARGURA_PAGINA, ALTURA_PAGINA = A4
MARGEM_X = 2.0 * cm
LARGURA_UTIL = LARGURA_PAGINA - 2 * MARGEM_X

INTEGRANTES = ["Bruno Carreiro", "Daniel Graciano", "Gustavo Romero", "Leonardo Porto", "Leonardo Gomes"]
DATA_ENTREGA = "23 de outubro de 2026"

# ---------------------------------------------------------------- identidade visual

TINTA = colors.HexColor("#1B2733")
NAVY = colors.HexColor("#0D2B45")
NAVY_2 = colors.HexColor("#173E5F")
ACENTO = colors.HexColor("#0E7C86")
ACENTO_CLARO = colors.HexColor("#E3F1F2")
CINZA = colors.HexColor("#5B6773")
CINZA_CLARO = colors.HexColor("#8A96A3")
LINHA = colors.HexColor("#D5DCE2")
FUNDO = colors.HexColor("#F4F6F8")
TERMINAL = colors.HexColor("#14212B")
TERMINAL_TEXTO = colors.HexColor("#D7E3EA")

ETIQUETAS = {
    "MEDIDO": (colors.HexColor("#175CD3"), colors.HexColor("#EAF1FD")),
    "IA": (colors.HexColor("#6941C6"), colors.HexColor("#F2EEFC")),
    "PREVISTO": (colors.HexColor("#B54708"), colors.HexColor("#FEF0E1")),
    "VERIFICADO": (colors.HexColor("#067647"), colors.HexColor("#E7F6EC")),
    "PERSONALIZADO": (ACENTO, ACENTO_CLARO),
    "USUÁRIO": (CINZA, FUNDO),
    "Removido": (colors.HexColor("#B42318"), colors.HexColor("#FDECEA")),
    "Modificado": (colors.HexColor("#B54708"), colors.HexColor("#FEF0E1")),
    "Adicionado": (colors.HexColor("#067647"), colors.HexColor("#E7F6EC")),
    "Mantido": (CINZA, FUNDO),
    "Atendido": (colors.HexColor("#067647"), colors.HexColor("#E7F6EC")),
}


def registrar_fontes() -> dict[str, str]:
    """Usa Segoe UI e Consolas quando disponiveis; senao, as fontes padrao do PDF."""
    pasta = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    arquivos = {
        "Texto": "segoeui.ttf", "TextoSemi": "seguisb.ttf", "TextoNegrito": "segoeuib.ttf",
        "TextoItalico": "segoeuii.ttf", "TextoNegritoItalico": "segoeuiz.ttf", "TextoLeve": "segoeuisl.ttf",
        "Mono": "consola.ttf", "MonoNegrito": "consolab.ttf",
    }
    if all((pasta / arquivo).exists() for arquivo in arquivos.values()):
        for nome, arquivo in arquivos.items():
            pdfmetrics.registerFont(TTFont(nome, str(pasta / arquivo)))
        pdfmetrics.registerFontFamily(
            "Texto", normal="Texto", bold="TextoNegrito", italic="TextoItalico", boldItalic="TextoNegritoItalico"
        )
        pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="MonoNegrito", italic="Mono", boldItalic="MonoNegrito")
        return {nome: nome for nome in arquivos}
    padrao = {
        "Texto": "Helvetica", "TextoSemi": "Helvetica-Bold", "TextoNegrito": "Helvetica-Bold",
        "TextoItalico": "Helvetica-Oblique", "TextoNegritoItalico": "Helvetica-BoldOblique",
        "TextoLeve": "Helvetica", "Mono": "Courier", "MonoNegrito": "Courier-Bold",
    }
    for apelido, fonte in padrao.items():  # mesmos nomes valem nas marcacoes <font face='Mono'>
        pdfmetrics.registerFont(pdfmetrics.Font(apelido, fonte, "WinAnsiEncoding"))
    return {apelido: apelido for apelido in padrao}


F = registrar_fontes()


def estilo(nome: str, **opcoes) -> ParagraphStyle:
    base = {"fontName": F["Texto"], "fontSize": 10, "leading": 15, "textColor": TINTA}
    base.update(opcoes)
    return ParagraphStyle(nome, **base)


E = {
    "corpo": estilo("corpo", spaceAfter=7),
    "corpo_meio": estilo("corpo_meio", spaceAfter=3),
    "lista": estilo("lista", leftIndent=14, bulletIndent=3, spaceAfter=3),
    "rotulo": estilo("rotulo", fontName=F["TextoSemi"], fontSize=8, leading=10, textColor=ACENTO, spaceAfter=2, spaceBefore=18,
                     keepWithNext=1),
    "h1": estilo("h1", fontName=F["TextoSemi"], fontSize=21, leading=26, textColor=NAVY, spaceAfter=10),
    "h2": estilo("h2", fontName=F["TextoSemi"], fontSize=12.5, leading=17, textColor=NAVY, spaceBefore=10, spaceAfter=5,
                 keepWithNext=1),
    "legenda": estilo("legenda", fontName=F["TextoItalico"], fontSize=8.3, leading=11, textColor=CINZA,
                      alignment=TA_CENTER, spaceBefore=4, spaceAfter=10),
    "cel": estilo("cel", fontSize=8.6, leading=11.6),
    "cel_mono": estilo("cel_mono", fontName=F["Mono"], fontSize=8, leading=11),
    "cab": estilo("cab", fontName=F["TextoSemi"], fontSize=8.4, leading=11, textColor=NAVY),
    "nota_titulo": estilo("nota_titulo", fontName=F["TextoSemi"], fontSize=8.6, leading=11, textColor=ACENTO),
    "nota": estilo("nota", fontSize=9.2, leading=13.4),
    "codigo": estilo("codigo", fontName=F["Mono"], fontSize=7.7, leading=10.2, textColor=TINTA),
    "terminal": estilo("terminal", fontName=F["Mono"], fontSize=7.7, leading=10.1, textColor=TERMINAL_TEXTO),
    "arquivo": estilo("arquivo", fontName=F["Mono"], fontSize=7.6, leading=10, textColor=CINZA),
    "toc": estilo("toc", fontSize=11, leading=21),
    "capa_kicker": estilo("capa_kicker", fontName=F["TextoSemi"], fontSize=10, leading=14,
                          textColor=colors.HexColor("#7FC8CE")),
    "capa_titulo": estilo("capa_titulo", fontName=F["TextoNegrito"], fontSize=40, leading=44, textColor=colors.white),
    "capa_sub": estilo("capa_sub", fontName=F["TextoLeve"], fontSize=13.5, leading=19,
                       textColor=colors.HexColor("#C9D8E4")),
    "capa_rotulo": estilo("capa_rotulo", fontName=F["TextoSemi"], fontSize=7.8, leading=10,
                          textColor=colors.HexColor("#7FC8CE")),
    "capa_valor": estilo("capa_valor", fontSize=10, leading=14, textColor=colors.white),
}


# ---------------------------------------------------------------- componentes de texto

class MarcaSecao(Flowable):
    """Marcador invisivel: muda o titulo exibido no cabecalho sem entrar no sumario."""

    def __init__(self, titulo: str) -> None:
        super().__init__()
        self.titulo = titulo

    def wrap(self, *_args) -> tuple[int, int]:
        return 0, 0

    def draw(self) -> None:
        pass


class Contador:
    def __init__(self) -> None:
        self.figura = 0
        self.tabela = 0


CONT = Contador()


def p(texto: str, nome: str = "corpo") -> Paragraph:
    return Paragraph(texto, E[nome])


def lista(itens: list[str]) -> list[Paragraph]:
    return [Paragraph(item, E["lista"], bulletText="•") for item in itens]


def secao(numero: int, titulo: str) -> list:
    cabecalho = Paragraph(titulo, E["h1"])
    cabecalho.toc_nivel = 0
    cabecalho.numero = numero
    rotulo = Paragraph(f"SEÇÃO {numero:02d}", E["rotulo"])
    rotulo.eh_rotulo = True
    return [CondPageBreak(10 * cm), rotulo, cabecalho]


def h2(texto: str) -> Paragraph:
    return Paragraph(texto, E["h2"])


def legenda_figura(texto: str) -> Paragraph:
    CONT.figura += 1
    return Paragraph(f"Figura {CONT.figura} — {texto}", E["legenda"])


def legenda_tabela(texto: str) -> Paragraph:
    CONT.tabela += 1
    return Paragraph(f"Tabela {CONT.tabela} — {texto}", E["legenda"])


def etiqueta(texto: str) -> Paragraph:
    cor, fundo = ETIQUETAS[texto]
    return Paragraph(texto, estilo(
        f"tag_{texto}", fontName=F["TextoSemi"], fontSize=7.6, leading=10, textColor=cor,
        backColor=fundo, borderPadding=(2, 4, 2, 4), alignment=TA_CENTER,
    ))


def mono(texto: str, tamanho: float = 8.4) -> str:
    """Trecho de codigo dentro de um paragrafo, ja escapado."""
    return f"<font face='{F['Mono']}' size='{tamanho}'>{escape(texto)}</font>"


def celula(valor) -> Flowable:
    """Celula de tabela: etiquetas viram selos e `trechos` entre crases viram codigo."""
    if isinstance(valor, Flowable):
        return valor
    texto = str(valor)
    if texto in ETIQUETAS:
        return etiqueta(texto)
    if texto.startswith("`") and texto.endswith("`") and texto.count("`") == 2:
        return Paragraph(escape(texto[1:-1]), E["cel_mono"])
    return Paragraph(re.sub(r"`([^`]+)`", lambda achado: mono(achado.group(1), 8), texto), E["cel"])


def tabela(linhas: list[list], larguras: list[float], legenda: str | None = None) -> list:
    """Tabela no estilo 'booktabs': so linhas horizontais, cabecalho discreto."""
    dados = [[Paragraph(str(titulo), E["cab"]) for titulo in linhas[0]]]
    dados += [[celula(valor) for valor in linha] for linha in linhas[1:]]
    tab = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    tab.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEABOVE", (0, 0), (-1, 0), 1.1, NAVY),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, NAVY),
        ("LINEBELOW", (0, 1), (-1, -2), 0.35, LINHA),
        ("LINEBELOW", (0, -1), (-1, -1), 1.1, NAVY),
    ]))
    saida: list = [tab]
    if legenda:
        saida.append(legenda_tabela(legenda))
    else:
        saida.append(Spacer(1, 8))
    return saida


def nota(titulo: str, texto: str) -> KeepTogether:
    """Quadro explicativo com barra lateral, usado com moderacao."""
    caixa = Table([[Paragraph(titulo.upper(), E["nota_titulo"])], [Paragraph(texto, E["nota"])]],
                  colWidths=[LARGURA_UTIL])
    caixa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, ACENTO),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))
    return KeepTogether([caixa, Spacer(1, 8)])


COR_CODIGO = {
    "palavra": "#CF222E", "texto": "#0A3069", "comentario": "#6E7781", "numero": "#0550AE",
    "funcao": "#8250DF", "chave": "#0550AE",
}
PALAVRAS_PYTHON = (
    "def|return|if|elif|else|for|while|in|not|and|or|is|try|except|finally|raise|with|as|"
    "import|from|class|None|True|False|pass|break|continue|lambda|yield"
)
TOKEN_PYTHON = re.compile(
    r"(?P<comentario>#.*$)"
    r"|(?P<texto>[rbfRBF]{0,2}(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'))"
    r"|(?P<funcao>(?<=\bdef )\w+)"
    rf"|(?P<palavra>\b(?:{PALAVRAS_PYTHON})\b)"
    r"|(?P<numero>\b\d+(?:[._]\d+)*\b)"
)
TOKEN_JSON = re.compile(
    r"(?P<chave>\"(?:\\.|[^\"\\])*\")(?=\s*:)"
    r"|(?P<texto>\"(?:\\.|[^\"\\])*\")"
    r"|(?P<palavra>\b(?:true|false|null)\b)"
    r"|(?P<numero>-?\b\d+(?:\.\d+)?\b)"
)


def _colorir(linha: str, padrao: re.Pattern) -> str:
    saida, posicao = [], 0
    for achado in padrao.finditer(linha):
        saida.append(escape(linha[posicao:achado.start()]))
        trecho = escape(achado.group(0))
        if achado.lastgroup == "comentario":
            trecho = f"<i>{trecho}</i>"
        saida.append(f"<font color='{COR_CODIGO[achado.lastgroup]}'>{trecho}</font>")
        posicao = achado.end()
    saida.append(escape(linha[posicao:]))
    return "".join(saida)


def realcar(linhas: list[str], linguagem: str) -> str:
    """Realce simples de sintaxe para Python e JSON (cores no estilo GitHub)."""
    if linguagem == "json":
        return "\n".join(_colorir(linha, TOKEN_JSON) for linha in linhas)
    if linguagem != "python":
        return "\n".join(escape(linha) for linha in linhas)
    resultado, em_docstring = [], False
    for linha in linhas:
        aspas = linha.count('"""')
        if em_docstring or (aspas == 1 and linha.strip().startswith('"""')):
            resultado.append(f"<font color='{COR_CODIGO['texto']}'>{escape(linha)}</font>")
            if aspas == 1:
                em_docstring = not em_docstring
            continue
        resultado.append(_colorir(linha, TOKEN_PYTHON))
    return "\n".join(resultado)


def quebrar_linhas(linhas: list[str], limite: int = 106) -> list[str]:
    """Quebra linhas longas mantendo o recuo, para nao estourar a margem."""
    saida = []
    for linha in linhas:
        recuo = " " * (len(linha) - len(linha.lstrip()) + 4)
        while len(linha) > limite:
            corte = linha.rfind(" ", 0, limite)
            corte = corte if corte > len(recuo) else limite
            saida.append(linha[:corte])
            linha = recuo + linha[corte:].lstrip()
        saida.append(linha)
    return saida


def bloco_codigo(texto: str, arquivo: str | None = None, max_linhas: int | None = None,
                 linguagem: str | None = None) -> KeepTogether:
    linhas = texto.rstrip().splitlines()
    if max_linhas and len(linhas) > max_linhas:
        linhas = linhas[:max_linhas] + ["    ..."]
    if linguagem is None:
        linguagem = "json" if texto.lstrip().startswith("{") else "python" if "def " in texto else "texto"
    corpo = XPreformatted(realcar(quebrar_linhas(linhas), linguagem), E["codigo"])
    conteudo = [[Paragraph(escape(arquivo), E["arquivo"])], [corpo]] if arquivo else [[corpo]]
    caixa = Table(conteudo, colWidths=[LARGURA_UTIL])
    estilos = [
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
        ("BOX", (0, 0), (-1, -1), 0.5, LINHA),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    if arquivo:
        estilos += [("LINEBELOW", (0, 0), (-1, 0), 0.5, LINHA), ("BOTTOMPADDING", (0, 0), (-1, 0), 4)]
    caixa.setStyle(TableStyle(estilos))
    return KeepTogether([caixa, Spacer(1, 8)])


def terminal(texto: str, titulo: str) -> KeepTogether:
    barra = Table([[Paragraph(f"<font color='#8FA3B3'>•  •  •</font>&nbsp;&nbsp;&nbsp;{escape(titulo)}",
                              estilo("tb", fontName=F["Mono"], fontSize=7.4, leading=9, textColor=CINZA_CLARO))]],
                  colWidths=[LARGURA_UTIL])
    barra.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0E1820")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    corpo = Table([[Preformatted(texto.rstrip("\n"), E["terminal"])]], colWidths=[LARGURA_UTIL])
    corpo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TERMINAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return KeepTogether([barra, corpo, Spacer(1, 4)])


# ---------------------------------------------------------------- diagramas

def seta(d: Drawing, x1: float, y1: float, x2: float, y2: float, cor=CINZA, largura: float = 1.0) -> None:
    d.add(Line(x1, y1, x2, y2, strokeColor=cor, strokeWidth=largura))
    angulo = math.atan2(y2 - y1, x2 - x1)
    ponta = 5.5
    p1 = (x2 - ponta * math.cos(angulo - 0.42), y2 - ponta * math.sin(angulo - 0.42))
    p2 = (x2 - ponta * math.cos(angulo + 0.42), y2 - ponta * math.sin(angulo + 0.42))
    d.add(Polygon([x2, y2, *p1, *p2], fillColor=cor, strokeColor=cor, strokeWidth=0.4))


def caixa(d: Drawing, x: float, y: float, w: float, h: float, titulo: str, sub: str | None = None,
          fundo=colors.white, borda=NAVY_2, cor_titulo=NAVY, sub_mono: bool = False, tracejada: bool = False) -> None:
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fundo, strokeColor=borda, strokeWidth=0.8,
               strokeDashArray=[3, 2] if tracejada else None))
    if sub:
        d.add(String(x + w / 2, y + h / 2 + 2.5, titulo, fontName=F["TextoSemi"], fontSize=8.8,
                     fillColor=cor_titulo, textAnchor="middle"))
        d.add(String(x + w / 2, y + h / 2 - 9, sub, fontName=F["Mono"] if sub_mono else F["Texto"],
                     fontSize=6.3 if sub_mono else 7.2, fillColor=CINZA, textAnchor="middle"))
    else:
        d.add(String(x + w / 2, y + h / 2 - 3, titulo, fontName=F["TextoSemi"], fontSize=8.8,
                     fillColor=cor_titulo, textAnchor="middle"))


def chip(d: Drawing, cx: float, y: float, texto: str) -> None:
    cor, fundo = ETIQUETAS[texto]
    largura = stringWidth(texto, F["TextoSemi"], 6.6) + 10
    d.add(Rect(cx - largura / 2, y, largura, 12, rx=6, ry=6, fillColor=fundo, strokeColor=None))
    d.add(String(cx, y + 3.4, texto, fontName=F["TextoSemi"], fontSize=6.6, fillColor=cor, textAnchor="middle"))


def pasta(d: Drawing, x: float, y: float, nome: str, w: float = 64) -> None:
    d.add(Rect(x, y + 22, 22, 6, rx=2, ry=2, fillColor=colors.HexColor("#F3D58B"), strokeColor=None))
    d.add(Rect(x, y, w, 25, rx=3, ry=3, fillColor=colors.HexColor("#FBE7B5"), strokeColor=colors.HexColor("#D9B25A"),
               strokeWidth=0.6))
    d.add(String(x + w / 2, y + 9, nome, fontName=F["Mono"], fontSize=7.2, fillColor=TINTA, textAnchor="middle"))


def diagrama_ciclo() -> Drawing:
    d = Drawing(LARGURA_UTIL, 128)
    etapas = [
        ("1  Medir", "OpenCV + Pillow", "MEDIDO"),
        ("2  Interpretar", "API Gemini", "IA"),
        ("3  Simular", "cenários “E se?”", "PREVISTO"),
        ("4  Recapturar", "nova foto", "USUÁRIO"),
        ("5  Verificar", "antes × depois", "VERIFICADO"),
        ("6  Aprender", "pesos em JSON", "PERSONALIZADO"),
    ]
    w, gap, y, h = 68, 14.8, 48, 44
    centros = []
    for indice, (titulo, sub, rotulo) in enumerate(etapas):
        x = indice * (w + gap)
        destaque = rotulo in {"VERIFICADO", "PERSONALIZADO"}
        caixa(d, x, y, w, h, titulo, sub, fundo=ACENTO_CLARO if destaque else colors.white)
        chip(d, x + w / 2, y + h + 9, rotulo)
        centros.append(x + w / 2)
        if indice:
            seta(d, x - gap + 1, y + h / 2, x - 1.5, y + h / 2)
    base = 20
    d.add(Line(centros[5], y, centros[5], base, strokeColor=ACENTO, strokeWidth=1, strokeDashArray=[3, 2]))
    d.add(Line(centros[5], base, centros[2], base, strokeColor=ACENTO, strokeWidth=1, strokeDashArray=[3, 2]))
    seta(d, centros[2], base, centros[2], y - 1.5, cor=ACENTO)
    d.add(String((centros[2] + centros[5]) / 2, base - 12, "os pesos aprendidos ajustam a próxima simulação",
                 fontName=F["TextoItalico"], fontSize=7.4, fillColor=ACENTO, textAnchor="middle"))
    return d


def diagrama_camadas() -> Drawing:
    d = Drawing(LARGURA_UTIL, 246)
    camadas = [
        ("Interface", "entrada e saída no terminal", [("main.py", "menu e navegação"), ("validators.py", "validação de entradas")]),
        ("Orquestração", "coordena um caso de uso", [("analysis_service.py", "ciclo de análise"), ("integracao.py", "troca de arquivos")]),
        ("Domínio", "regras, sem entrada/saída", [("image_analyzer.py", "métricas"), ("recommendation_engine.py", "ranking “E se?”"),
                                                   ("learning_engine.py", "aprendizado"), ("reports.py", "textos")]),
        ("Infraestrutura", "acesso ao mundo externo", [("database.py", "persistência"), ("data/*.json", "arquivos"),
                                                       ("gemini_client.py", "cliente HTTP"), ("API Gemini", "serviço externo")]),
    ]
    altura, gap, rotulo_w = 46, 14, 84
    area_x, area_w = rotulo_w + 8, LARGURA_UTIL - rotulo_w - 8
    for indice, (nome, descricao, modulos) in enumerate(camadas):
        y = 246 - (indice + 1) * altura - indice * gap
        d.add(Rect(0, y, LARGURA_UTIL, altura, rx=6, ry=6, fillColor=FUNDO, strokeColor=None))
        d.add(String(10, y + altura / 2 + 2, nome, fontName=F["TextoSemi"], fontSize=9.2, fillColor=NAVY))
        d.add(String(10, y + altura / 2 - 9, descricao, fontName=F["Texto"], fontSize=6.8, fillColor=CINZA))
        n = len(modulos)
        espaco = 7
        largura = (area_w - (n + 1) * espaco) / n
        for posicao, (arquivo, papel) in enumerate(modulos):
            x = area_x + espaco + posicao * (largura + espaco)
            externo = arquivo in {"data/*.json", "API Gemini"}
            caixa(d, x, y + 7, largura, altura - 14, papel, arquivo, sub_mono=True, tracejada=externo,
                  fundo=colors.HexColor("#FFFDF5") if externo else colors.white)
            if externo:
                seta(d, x - espaco + 0.5, y + altura / 2, x - 1, y + altura / 2, cor=ACENTO)
        if indice:
            seta(d, area_x + area_w / 2, y + altura + gap - 1, area_x + area_w / 2, y + altura + 1)
    return d


def diagrama_integracao() -> Drawing:
    d = Drawing(LARGURA_UTIL, 150)
    caixa(d, 0, 52, 104, 50, "App da câmera JOVI", "outra parte da solução")
    pasta(d, 132, 64, "entrada/")
    caixa(d, 228, 46, 112, 62, "JOVI AI LensLab", "menu 10 · integracao.py", fundo=ACENTO_CLARO, sub_mono=True)
    pasta(d, 378, 92, "saida/", w=74)
    pasta(d, 368, 36, "processadas/", w=74)
    pasta(d, 368, 1, "com_erro/", w=74)
    seta(d, 105, 77, 131, 77, cor=NAVY_2)
    d.add(String(118, 84, "1", fontName=F["TextoSemi"], fontSize=7.5, fillColor=ACENTO, textAnchor="middle"))
    seta(d, 197, 77, 227, 77, cor=NAVY_2)
    d.add(String(212, 84, "2", fontName=F["TextoSemi"], fontSize=7.5, fillColor=ACENTO, textAnchor="middle"))
    seta(d, 341, 95, 377, 104, cor=NAVY_2)
    d.add(String(356, 106, "3", fontName=F["TextoSemi"], fontSize=7.5, fillColor=ACENTO, textAnchor="middle"))
    seta(d, 341, 60, 367, 49, cor=CINZA_CLARO)
    seta(d, 300, 45, 367, 14, cor=CINZA_CLARO)
    d.add(String(352, 63, "4", fontName=F["TextoSemi"], fontSize=7.5, fillColor=ACENTO, textAnchor="middle"))
    topo = 140
    d.add(Line(415, 121, 415, topo, strokeColor=ACENTO, strokeWidth=1, strokeDashArray=[3, 2]))
    d.add(Line(415, topo, 52, topo, strokeColor=ACENTO, strokeWidth=1, strokeDashArray=[3, 2]))
    seta(d, 52, topo, 52, 103.5, cor=ACENTO)
    d.add(String(233, topo + 3, "5  o app lê resultado_<id>.json ou erro_<nome>.json",
                 fontName=F["TextoItalico"], fontSize=7.4, fillColor=ACENTO, textAnchor="middle"))
    return d


def diagrama_api() -> Drawing:
    d = Drawing(LARGURA_UTIL, 118)
    etapas = [
        ("Foto original", "somente leitura"),
        ("Cópia temporária", "≤ 1600 px, sem EXIF"),
        ("API Gemini", "saída em JSON Schema"),
        ("Validação", "campos e faixas"),
        ("Leitura da IA", "vai ao diagnóstico"),
    ]
    w, gap, y, h = 84, 15.5, 62, 42
    for indice, (titulo, sub) in enumerate(etapas):
        x = indice * (w + gap)
        caixa(d, x, y, w, h, titulo, sub, fundo=ACENTO_CLARO if titulo == "API Gemini" else colors.white,
              tracejada=titulo == "API Gemini")
        if indice:
            seta(d, x - gap + 1, y + h / 2, x - 1.5, y + h / 2)
    x_api = 2 * (w + gap)
    caixa(d, x_api - 60, 4, w + 120, 34, "Falha: nova tentativa, depois modo offline",
          "o diagnóstico usa só as métricas medidas", fundo=colors.HexColor("#FEF6EE"),
          borda=colors.HexColor("#D9A066"), cor_titulo=colors.HexColor("#93370D"))
    seta(d, x_api + w / 2, y - 1, x_api + w / 2, 39, cor=colors.HexColor("#D9A066"))
    d.add(String(x_api + w / 2 + 6, 46, "timeout, 503, 404…", fontName=F["TextoItalico"], fontSize=6.8,
                 fillColor=colors.HexColor("#93370D")))
    return d


# ---------------------------------------------------------------- dados reais do projeto

def coletar_exemplos() -> dict:
    """Executa partes do proprio sistema para obter telas e JSON reais."""
    exemplos: dict = {}
    saida = io.StringIO()
    with patch("main.get_gemini_api_key", return_value="configurada"), patch("main.is_demo_mode", return_value=False), \
            redirect_stdout(saida):
        main.exibir_menu({"apelido": "Ana", "nivel": "iniciante"})
    exemplos["menu"] = saida.getvalue().strip("\n") + "\nEscolha: 2"

    def offline(*_args) -> dict:
        return {"sucesso": False, "dados": None, "erro": "modo_offline"}

    with tempfile.TemporaryDirectory() as temporaria:
        dados = Path(temporaria) / "data"
        base = Path(temporaria) / "integracao"
        database.inicializar_armazenamento(dados)
        usuario = database.criar_usuario("Ana", "iniciante", "natural", False, dados)
        analise = analisar_fotografia(usuario, SAMPLES_DIR / "exemplo_escuro.jpg", "retrato",
                                      "foto de perfil", "natural", False, dados, offline)
        exemplos["resumo"] = formatar_resumo_analise(analise).strip("\n")

        perfil = json.loads((dados / "perfis" / f"perfil_{usuario['id']}.json").read_text(encoding="utf-8"))
        primeira = perfil["analises"][0]
        exemplos["perfil_json"] = json.dumps({
            "versao": perfil["versao"], "usuario_id": perfil["usuario_id"],
            "analises": [{
                "id": primeira["id"], "nome_arquivo": primeira["nome_arquivo"], "objetivo": primeira["objetivo"],
                "modo_execucao": primeira["modo_execucao"], "pontuacao_geral": primeira["pontuacao_geral"],
                "metricas": {chave: primeira["metricas"][chave] for chave in ("brilho", "nitidez_bruta", "contexto_chave")},
                "...": "demais campos omitidos neste documento",
            }],
            "recomendacoes": [{chave: perfil["recomendacoes"][0][chave]
                               for chave in ("id", "analise_id", "codigo_acao", "ganho_previsto", "marcado_em")}],
            "comparacoes": [], "pesos_aprendizado": [],
        }, ensure_ascii=False, indent=2)
        exemplos["indice_json"] = json.dumps(
            json.loads((dados / "usuarios.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=2
        )

        solicitacao = integracao.exemplo_solicitacao()
        arquivo = integracao.preparar_pastas(base)["entrada"] / "solicitacao.json"
        arquivo.write_text(json.dumps(solicitacao), encoding="utf-8")
        integracao.processar_pendentes(dados, base, offline)
        resultado = json.loads((base / "saida" / "resultado_exemplo-001.json").read_text(encoding="utf-8"))
        resultado["processado_em"] = "2026-10-23T14:30:00+00:00"
        resultado["recomendacoes"] = resultado["recomendacoes"][:1] + [{"...": "demais recomendações omitidas"}]
        resultado["analise"]["dimensoes"] = {
            chave: resultado["analise"]["dimensoes"][chave] for chave in ("exposicao", "nitidez", "contraste")
        } | {"...": "omitidas"}
        exemplos["resultado_json"] = json.dumps(resultado, ensure_ascii=False, indent=2)

    exemplos["solicitacao_json"] = (ROOT / "integracao" / "exemplos" / "solicitacao_exemplo.json").read_text(
        encoding="utf-8")
    exemplos["codigo_gravacao"] = inspect.getsource(database._gravar_json)
    exemplos["codigo_leitura"] = inspect.getsource(database._ler_json)
    exemplos["codigo_entrada"] = inspect.getsource(validators.solicitar_validado)
    exemplos["codigo_integracao"] = inspect.getsource(integracao.processar_arquivo)
    exemplos["testes"] = contar_testes()
    return exemplos


def contar_testes() -> dict[str, int]:
    suite = unittest.TestLoader().discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    contagem: dict[str, int] = {}

    def percorrer(item) -> None:
        if isinstance(item, unittest.TestSuite):
            for filho in item:
                percorrer(filho)
        else:
            modulo = type(item).__module__.split(".")[-1]
            contagem[modulo] = contagem.get(modulo, 0) + 1

    percorrer(suite)
    return dict(sorted(contagem.items()))


# ---------------------------------------------------------------- documento

class Documento(BaseDocTemplate):
    def __init__(self, caminho: Path) -> None:
        super().__init__(
            str(caminho), pagesize=A4, leftMargin=MARGEM_X, rightMargin=MARGEM_X,
            topMargin=2.3 * cm, bottomMargin=2.0 * cm,
            title="NextFrame JOVI AI LensLab — Documentação da Sprint 4",
            author="Equipe NextFrame: " + ", ".join(INTEGRANTES),
            subject="Computational Thinking with Python — Sprint 4",
        )
        self.secao_atual = ""
        self.secao_inicio_pagina = ""
        self.titulo_da_pagina: str | None = None
        self.pagina_tem_conteudo = False
        capa = Frame(2.3 * cm, 2.2 * cm, LARGURA_PAGINA - 4.6 * cm, ALTURA_PAGINA - 4.4 * cm, id="capa",
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        conteudo = Frame(MARGEM_X, 2.0 * cm, LARGURA_UTIL, ALTURA_PAGINA - 4.3 * cm, id="conteudo",
                         leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="capa", frames=[capa], onPage=desenhar_capa),
            PageTemplate(id="conteudo", frames=[conteudo], onPage=iniciar_pagina, onPageEnd=desenhar_moldura),
        ])

    def _abrir_secao(self, titulo: str) -> None:
        if not self.pagina_tem_conteudo and self.titulo_da_pagina is None:
            self.titulo_da_pagina = titulo
        self.secao_atual = titulo

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, MarcaSecao):
            self._abrir_secao(flowable.titulo)
            return
        nivel = getattr(flowable, "toc_nivel", None)
        if nivel is None:
            if e_conteudo(flowable):
                self.pagina_tem_conteudo = True
            return
        texto = flowable.getPlainText()
        titulo = f"{flowable.numero}. {texto}"
        chave = "secao-" + re.sub(r"\W+", "-", texto.lower())
        self._abrir_secao(texto)
        self.canv.bookmarkPage(chave)
        self.canv.addOutlineEntry(titulo, chave, level=nivel, closed=False)
        self.notify("TOCEntry", (nivel, titulo, self.page, chave))


def desenhar_capa(canv, _doc) -> None:
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, 0, LARGURA_PAGINA, ALTURA_PAGINA, fill=1, stroke=0)
    cx, cy = LARGURA_PAGINA - 3.6 * cm, ALTURA_PAGINA - 5.0 * cm
    for indice, raio in enumerate((6.0, 5.0, 4.1, 3.3, 2.5, 1.8)):
        tom = 0.14 + indice * 0.045
        canv.setStrokeColor(colors.Color(tom, tom + 0.18, tom + 0.28))
        canv.setLineWidth(1.1 if indice % 2 else 0.6)
        canv.circle(cx, cy, raio * cm, stroke=1, fill=0)
    canv.setFillColor(ACENTO)
    canv.circle(cx, cy, 1.0 * cm, stroke=0, fill=1)
    canv.setFillColor(NAVY)
    canv.circle(cx, cy, 0.45 * cm, stroke=0, fill=1)
    canv.setFillColor(ACENTO)
    canv.rect(0, 0, LARGURA_PAGINA, 0.32 * cm, fill=1, stroke=0)
    canv.restoreState()


def e_conteudo(flowable) -> bool:
    """Diz se o elemento ocupa a pagina como conteudo (rotulos e titulos de secao nao contam)."""
    if isinstance(flowable, KeepTogether):
        return any(e_conteudo(item) for item in getattr(flowable, "_content", []))
    if getattr(flowable, "eh_rotulo", False) or getattr(flowable, "toc_nivel", None) is not None:
        return False
    return isinstance(flowable, (Paragraph, Table, XPreformatted, Preformatted, Drawing))


def iniciar_pagina(_canv, doc) -> None:
    doc.secao_inicio_pagina = doc.secao_atual
    doc.titulo_da_pagina = None
    doc.pagina_tem_conteudo = False


def desenhar_moldura(canv, doc) -> None:
    """Cabecalho mostra a secao que abre a pagina; se ela comecar no meio, a que vinha antes."""
    canv.saveState()
    topo = ALTURA_PAGINA - 1.35 * cm
    canv.setFont(F["TextoSemi"], 7.8)
    canv.setFillColor(NAVY)
    canv.drawString(MARGEM_X, topo, "NextFrame  ·  JOVI AI LensLab")
    canv.setFont(F["Texto"], 7.8)
    canv.setFillColor(CINZA)
    canv.drawRightString(LARGURA_PAGINA - MARGEM_X, topo, doc.titulo_da_pagina or doc.secao_inicio_pagina)
    canv.setStrokeColor(LINHA)
    canv.setLineWidth(0.5)
    canv.line(MARGEM_X, topo - 6, LARGURA_PAGINA - MARGEM_X, topo - 6)
    canv.setFont(F["Texto"], 7.6)
    canv.drawString(MARGEM_X, 1.15 * cm, "Computational Thinking with Python  ·  Sprint 4")
    canv.setFont(F["TextoSemi"], 7.8)
    canv.setFillColor(NAVY)
    canv.drawRightString(LARGURA_PAGINA - MARGEM_X, 1.15 * cm, str(doc.page))
    canv.restoreState()


def montar_capa() -> list:
    info = [
        ("DISCIPLINA", "Computational Thinking with Python"),
        ("ENTREGA", "Sprint 4 — implementação final"),
        ("INTEGRANTES", "<br/>".join(INTEGRANTES)),
        ("DATA", DATA_ENTREGA),
    ]
    tabela_info = Table(
        [[Paragraph(rotulo, E["capa_rotulo"]), Paragraph(valor, E["capa_valor"])] for rotulo, valor in info],
        colWidths=[3.2 * cm, 9.5 * cm], hAlign="LEFT",
    )
    tabela_info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor("#3D6585")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#25496A")),
    ]))
    return [
        Spacer(1, 6.4 * cm),
        Paragraph("NEXTFRAME  ·  CHALLENGE JOVI 2026", E["capa_kicker"]),
        Spacer(1, 4),
        Paragraph("JOVI AI LensLab", E["capa_titulo"]),
        Spacer(1, 4),
        Paragraph("Laboratório fotográfico que mede a foto, explica o que pode melhorar, "
                  "verifica a nova captura e aprende com cada usuário.", E["capa_sub"]),
        Spacer(1, 1.2 * cm),
        Paragraph("DOCUMENTAÇÃO TÉCNICA", E["capa_kicker"]),
        Spacer(1, 3.2 * cm),
        tabela_info,
        NextPageTemplate("conteudo"),
        PageBreak(),
    ]


def montar_sumario() -> list:
    toc = TableOfContents(dotsMinLevel=0)
    toc.levelStyles = [estilo("toc0", fontSize=10.5, leading=20, leftIndent=0, firstLineIndent=0)]
    return [
        MarcaSecao("Sumário"),
        Paragraph("Sumário", E["h1"]),
        p("O documento segue a ordem dos critérios de avaliação: descrição do projeto, funcionalidades, "
          "requisitos técnicos da Sprint 4, alterações em relação à Sprint 3 e evidências de testes.", "corpo"),
        Spacer(1, 6),
        toc,
        PageBreak(),
    ]


def montar_conteudo(ex: dict) -> list:
    W = LARGURA_UTIL
    total_testes = sum(ex["testes"].values())
    s: list = []

    # 1 ---------------------------------------------------------------
    s += secao(1, "Visão geral do projeto")
    s += [
        h2("Problema"),
        p("Os smartphones da linha JOVI oferecem modos avançados de câmera, como Noturno, Retrato e HDR, mas "
          "o usuário raramente sabe quando cada recurso ajuda, que efeito colateral ele traz e se a mudança "
          "realmente melhorou a foto. Recomendações fixas, como as da Sprint 2, ignoram a foto real, a "
          "intenção de quem fotografa e o histórico de cada pessoa."),
        h2("Proposta"),
        p("O <b>JOVI AI LensLab</b> é um programa de terminal em Python que trata a fotografia como um "
          "experimento. Ele mede a foto, interpreta a cena, simula alternativas, pede uma nova captura, "
          "verifica o resultado e ajusta as próximas recomendações para aquele usuário. O programa não "
          "edita a imagem: ele ensina o usuário a fotografar melhor."),
        diagrama_ciclo(),
        legenda_figura("Ciclo de uso. Cada etapa produz um tipo de informação identificado na interface."),
        h2("Como ler os rótulos da interface"),
        p("A interface sempre separa o que foi calculado, o que foi inferido e o que foi comprovado. "
          "Essa separação evita apresentar uma estimativa como se fosse um fato.", "corpo_meio"),
    ]
    s += tabela([
        ["Rótulo", "Origem", "Significado"],
        ["MEDIDO", "Cálculo local", "Valores obtidos dos pixels: brilho, contraste, nitidez, saturação, recortes e resolução."],
        ["IA", "API Gemini", "Interpretação da cena (assunto, composição, movimento), aceita só depois de validada."],
        ["PREVISTO", "Motor de cenários", "Ganho estimado antes de o usuário agir; é uma hipótese."],
        ["VERIFICADO", "Recaptura", "Diferença real entre a foto original e a nova foto, no mesmo contexto."],
    ], [2.6 * cm, 3.0 * cm, W - 5.6 * cm], "Rótulos usados nos diagnósticos.")

    # 2 ---------------------------------------------------------------
    s += secao(2, "Objetivos e justificativa")
    s += [
        h2("Objetivo geral"),
        p("Desenvolver em Python uma ferramenta que combine análise técnica local, interpretação por IA e "
          "verificação por recaptura para produzir recomendações fotográficas explicáveis e personalizadas, "
          "com dados persistidos em arquivos JSON e integração com o restante da solução NextFrame."),
        h2("Objetivos específicos"),
        *lista([
            "Medir indicadores técnicos da foto sem depender de internet.",
            "Interpretar a cena com a API Gemini apenas quando o usuário consentir.",
            "Apresentar até três alternativas com ganho previsto, esforço, risco, confiança e evidências.",
            "Comparar a foto original com uma recaptura no mesmo objetivo e intenção.",
            "Ajustar as recomendações de cada usuário com base nos resultados verificados.",
            "Persistir perfis, histórico e aprendizado em arquivos JSON, um por perfil.",
            "Trocar arquivos JSON com o app da câmera JOVI, que representa o restante da solução.",
            "Continuar funcionando, com mensagens claras, quando a API ou os arquivos falharem.",
        ]),
        h2("Justificativa"),
        p("Dizer apenas qual modo usar não ensina. Ao mostrar o motivo de cada sugestão, o risco envolvido e o "
          "resultado medido depois, o usuário entende o efeito de cada recurso e passa a escolher sozinho. "
          "Para a JOVI, isso aumenta o uso consciente dos recursos avançados da câmera. A verificação por "
          "recaptura também protege contra o principal limite da IA: uma interpretação errada nunca é "
          "tratada como prova de melhoria."),
    ]

    # 3 ---------------------------------------------------------------
    s += secao(3, "Funcionalidades implementadas")
    s += [
        p("O programa abre com a seleção de perfil e, em seguida, mostra o menu principal. Toda opção volta "
          "ao menu ao terminar, e a opção 0 encerra a execução. A tela abaixo foi capturada do próprio "
          "programa durante a geração deste documento."),
        terminal(ex["menu"], "python main.py"),
        legenda_figura("Menu principal real do programa."),
    ]
    s += tabela([
        ["Opção", "Funcionalidade", "O que faz"],
        ["1", "Trocar ou criar perfil", "Seleciona, cria ou exclui perfis; o primeiro perfil recebe um tour guiado com foto de exemplo."],
        ["2", "Analisar fotografia", "Abre o explorador de arquivos, mede a foto, consulta a IA se autorizado e mostra um resumo em linguagem simples."],
        ["3", "Explorar simulação “E se?”", "Gera uma prévia visual da recomendação sem alterar a foto original."],
        ["4", "Comparar antes e depois", "Analisa a recaptura no mesmo contexto, registra a nota do usuário e atualiza o aprendizado."],
        ["5", "Marcar recomendação", "Guarda a dica que será testada; ela é sugerida automaticamente na opção 4."],
        ["6", "Ver histórico", "Lista as análises do perfil ativo."],
        ["7", "Ver evolução", "Mostra ganho médio, recapturas bem-sucedidas e os conselhos que mais funcionaram."],
        ["8", "Orientação sem foto", "Recomenda com base no ambiente descrito pelo usuário (herança da Sprint 2)."],
        ["9", "Privacidade e dados", "Altera o consentimento, exporta um resumo ou exclui o perfil e seus arquivos."],
        ["10", "Integração com o app JOVI", "Processa solicitações JSON recebidas e exporta o perfil para o app."],
        ["0", "Encerrar", "Finaliza a execução; Ctrl+C também encerra sem mensagem de erro técnico."],
    ], [1.4 * cm, 4.0 * cm, W - 5.4 * cm], "Funcionalidades do menu principal.")
    s += [
        h2("Exemplo de resultado para o usuário"),
        p("O diagnóstico aparece primeiro em linguagem simples; os detalhes técnicos só são exibidos se o "
          "usuário pedir. Saída real para a foto " + mono("samples/exemplo_escuro.jpg") + ":"),
        terminal(ex["resumo"], "opção 2 — analisar fotografia"),
        legenda_figura("Resumo da análise exibido ao usuário."),
    ]

    # 4 ---------------------------------------------------------------
    s += secao(4, "Arquitetura da solução")
    s += [
        p("O código é dividido em camadas. Cada camada só conversa com a de baixo, e as regras de negócio "
          "ficam em funções que recebem parâmetros e devolvem valores, sem ler o teclado nem imprimir na tela. "
          "Isso permite testar as regras isoladamente e trocar a forma de armazenamento sem mexer no resto."),
        diagrama_camadas(),
        legenda_figura("Camadas e módulos. Caixas tracejadas representam recursos fora do código."),
    ]
    s += tabela([
        ["Módulo", "Responsabilidade", "Exemplo de função (assinatura)"],
        ["main.py", "Menu, perguntas e navegação", "`menu_integracao(usuario, pasta_dados, base) -> None`"],
        ["validators.py", "Validação de entradas do usuário", "`validar_inteiro(valor, minimo, maximo, nome) -> int`"],
        ["analysis_service.py", "Ciclo de análise completo", "`analisar_fotografia(usuario, caminho_imagem, ...) -> dict`"],
        ["integracao.py", "Contrato de troca de arquivos", "`validar_solicitacao(dados) -> dict`"],
        ["image_analyzer.py", "Métricas e cópia segura para a API", "`analisar_imagem(caminho) -> dict`"],
        ["recommendation_engine.py", "Pontuação e cenários “E se?”", "`simular_intervencoes(problemas, movimento, ...) -> list[dict]`"],
        ["learning_engine.py", "Comparação e ajuste de pesos", "`calcular_ajuste_peso(ganho_real, avaliacao) -> float`"],
        ["database.py", "Persistência em arquivos JSON", "`salvar_analise_com_recomendacoes(analise, ...) -> int`"],
        ["gemini_client.py", "Cliente da API externa", "`analisar_com_gemini(caminho_imagem, objetivo, intencao) -> dict`"],
        ["reports.py", "Textos e relatórios", "`formatar_resumo_analise(resultado) -> str`"],
    ], [4.5 * cm, 4.1 * cm, W - 8.6 * cm], "Módulos e uma função representativa de cada um.")
    s += [nota("Decisão técnica",
               "A IA é injetada como parâmetro (<font face='Mono' size='8.5'>cliente_ia</font>) em "
               "<font face='Mono' size='8.5'>analisar_fotografia</font>. Com isso, os testes usam um cliente "
               "falso, sem rede, e o modo de demonstração usa respostas simuladas pela mesma interface.")]

    # 5 ---------------------------------------------------------------
    s += secao(5, "Persistência em arquivos JSON")
    s += [
        p("Todos os dados ficam em arquivos JSON legíveis, criados automaticamente. Há um índice com os perfis "
          "e um arquivo para cada perfil, o que deixa o isolamento entre usuários visível na própria estrutura "
          "de pastas: excluir um perfil apaga apenas o arquivo dele."),
        bloco_codigo("data/\n"
                     "├── usuarios.json            perfis, consentimento e contadores de identificadores\n"
                     "└── perfis/\n"
                     "    ├── perfil_1.json        análises, recomendações, comparações e pesos do perfil 1\n"
                     "    └── perfil_2.json        ... de outro usuário, sem mistura de dados",
                     "estrutura de pastas"),
        h2("Conteúdo de um arquivo de perfil"),
        p("Trecho real gerado pelo programa após uma análise (campos repetitivos omitidos):", "corpo_meio"),
        bloco_codigo(ex["perfil_json"], "data/perfis/perfil_1.json", max_linhas=40),
        h2("Gravação segura"),
        p("Se o programa fosse interrompido no meio de uma gravação, o arquivo poderia ficar pela metade. "
          "Por isso o conteúdo é escrito primeiro em um arquivo temporário e só depois substitui o original "
          "com <font face='Mono' size='8.5'>os.replace</font>, que troca o arquivo de uma vez só."),
        bloco_codigo(ex["codigo_gravacao"], "database.py — _gravar_json"),
        h2("Leitura com tratamento de erros"),
        p("Na leitura, um arquivo inexistente vira uma estrutura vazia, e um arquivo corrompido gera uma "
          "mensagem que indica qual arquivo restaurar, em vez de encerrar o programa com erro técnico."),
        bloco_codigo(ex["codigo_leitura"], "database.py — _ler_json"),
        h2("Regras que antes eram do banco de dados"),
    ]
    s += tabela([
        ["Regra", "Onde é garantida"],
        ["Apelido único (sem diferenciar maiúsculas)", "`database.criar_usuario` → RegistroDuplicadoError"],
        ["Nível e estilo dentro das opções válidas", "`database.criar_usuario`"],
        ["Pontuação entre 0 e 100", "`database.salvar_analise_com_recomendacoes`"],
        ["Avaliação de 1 a 5 e peso entre 0,50 e 1,50", "`database.registrar_comparacao`"],
        ["Mesma comparação não é registrada duas vezes", "`database.registrar_comparacao` → RegistroDuplicadoError"],
        ["Identificadores únicos entre perfis", "contadores em `usuarios.json`"],
    ], [7.6 * cm, W - 7.6 * cm], "Validações que substituem as restrições do SQLite da Sprint 3.")

    # 6 ---------------------------------------------------------------
    s += secao(6, "Integração com o restante da solução")
    s += [
        p("A Sprint 4 pede integração por arquivos ou API. O LensLab usa <b>troca de arquivos JSON</b> com o "
          "app da câmera JOVI: o app deixa um pedido numa pasta e o LensLab devolve o resultado em outra. "
          "Os dois lados só precisam combinar o formato dos arquivos, documentado abaixo."),
        diagrama_integracao(),
        legenda_figura("Fluxo da integração: (1) o app grava o pedido, (2) o LensLab lê, (3) grava o resultado, "
                       "(4) arquiva o pedido e (5) o app lê a resposta."),
        h2("Contrato da solicitação (versão 1.0)"),
    ]
    s += tabela([
        ["Campo", "Tipo", "Regra de validação"],
        ["`versao`", "texto", "Precisa ser da versão 1.x do contrato."],
        ["`id_solicitacao`", "texto", "1 a 60 caracteres: letras, números, hífen ou sublinhado. Dá nome ao resultado."],
        ["`perfil`", "objeto", "apelido (2 a 40 caracteres), nível, estilo e consentimento (true/false)."],
        ["`foto`", "texto", "Caminho absoluto ou relativo à raiz do projeto; o arquivo precisa existir e ser imagem válida."],
        ["`objetivo`", "texto", "documento, pessoa, retrato, paisagem, produto, redes_sociais ou outro."],
        ["`intencao`", "texto", "3 a 160 caracteres descrevendo o que o usuário queria com a foto."],
    ], [3.4 * cm, 1.8 * cm, W - 5.2 * cm], "Campos da solicitação enviada pelo app.")
    s += [
        bloco_codigo(ex["solicitacao_json"], "integracao/exemplos/solicitacao_exemplo.json"),
        h2("Resultado devolvido ao app"),
        p("Trecho real do arquivo gerado para a solicitação acima. O resultado não inclui o hash da foto, "
          "metadados nem localização.", "corpo_meio"),
        bloco_codigo(ex["resultado_json"], "integracao/saida/resultado_exemplo-001.json", max_linhas=46),
        h2("Tratamento de falhas"),
    ]
    s += tabela([
        ["Situação", "O que acontece"],
        ["JSON malformado ou com acento salvo fora de UTF-8", "Pedido vai para `com_erro/` e `saida/erro_<nome>.json` explica a linha e a coluna."],
        ["Campo ausente ou fora da regra", "Mesmo tratamento, com a mensagem da regra violada."],
        ["Foto inexistente ou corrompida", "Mesmo tratamento; nenhuma análise é gravada."],
        ["Perfil já existente", "Perfil é reaproveitado; o consentimento dele não pode ser alterado pelo app."],
        ["Arquivo de dados local corrompido", "O lote é interrompido e o pedido permanece na entrada para ser reprocessado."],
    ], [5.6 * cm, W - 5.6 * cm], "Comportamento da integração em cada falha prevista.")
    s += [bloco_codigo(ex["codigo_integracao"], "integracao.py — processar_arquivo", max_linhas=48)]

    # 7 ---------------------------------------------------------------
    s += secao(7, "Consumo de API externa")
    s += [
        p("A API externa consumida é a <b>Google Gemini</b>, acessada pelo SDK oficial "
          "<font face='Mono' size='8.5'>google-genai</font>. Ela interpreta o conteúdo da foto, o que as métricas "
          "de pixels não conseguem: qual é o assunto, se há movimento e como está a composição."),
        diagrama_api(),
        legenda_figura("Caminho de uma foto até a API e o tratamento de falhas."),
    ]
    s += tabela([
        ["Aspecto", "Implementação"],
        ["Quando é chamada", "Somente com consentimento no perfil e chave em GEMINI_API_KEY (variável de ambiente ou .env)."],
        ["Modelo", "`gemini-flash-latest`, configurável em GEMINI_MODEL."],
        ["Formato da resposta", "JSON obrigatório, descrito por JSON Schema; campos e códigos fora da lista são descartados."],
        ["Tempo limite e repetição", "30 s por chamada; uma nova tentativa com espera em falhas temporárias (timeout, 503, 504)."],
        ["Falhas definitivas", "Chave inválida, cota esgotada ou modelo indisponível: nenhuma nova tentativa; segue offline."],
        ["Privacidade", "Envia uma cópia reduzida e sem EXIF/GPS, apagada ao final; a original nunca é alterada."],
        ["Sem chave", "O programa funciona offline. JOVI_DEMO_MODE=1 simula a resposta para apresentações."],
    ], [4.2 * cm, W - 4.2 * cm], "Como a API é consumida.")

    # 8 ---------------------------------------------------------------
    s += secao(8, "Validação de entradas e tratamento de exceções")
    s += [
        p("Toda entrada do usuário passa por uma função de validação. Quando a resposta é inválida, a mesma "
          "pergunta é repetida com uma explicação, sem recursão e sem encerrar o programa. O valor 0 cancela "
          "fluxos com várias perguntas."),
        bloco_codigo(ex["codigo_entrada"], "validators.py — solicitar_validado"),
    ]
    s += tabela([
        ["Onde", "O que é validado ou tratado", "Exceções capturadas"],
        ["validators.py", "Números em faixa, sim/não, tamanho de textos, caminho, formato e tamanho da imagem", "ValidationError, ValueError, OSError"],
        ["image_analyzer.py", "Imagem corrompida, renomeada ou abaixo de 320 × 240", "UnidentifiedImageError, OSError"],
        ["gemini_client.py", "Resposta da API fora do schema; erros de rede, cota e autenticação", "GeminiResponseError, JSONDecodeError, Exception do SDK"],
        ["database.py", "Arquivo de dados ilegível ou corrompido; falha ao gravar", "JSONDecodeError, OSError → ArmazenamentoError"],
        ["integracao.py", "Pedido malformado, codificação errada, campos inválidos", "JSONDecodeError, UnicodeDecodeError, ValueError"],
        ["main.py", "Falhas durante a sessão, Ctrl+C e fim da entrada", "ValueError, OSError, KeyboardInterrupt, EOFError"],
    ], [3.2 * cm, 7.6 * cm, W - 10.8 * cm], "Pontos de validação e tratamento de exceções.")

    # 9 ---------------------------------------------------------------
    s += secao(9, "Aprendizado individualizado")
    s += [
        p("Depois de cada recaptura, o peso da recomendação usada é ajustado apenas para aquele usuário e "
          "para aquele contexto. O contexto é uma chave formada por cinco partes:"),
        bloco_codigo("objetivo | faixa de luz | movimento | nível | estilo\n"
                     "retrato  | escuro      | estatico  | iniciante | natural", "chave de contexto"),
        p("Assim, uma dica que funcionou num retrato escuro não altera as sugestões para um documento bem "
          "iluminado, nem as de outro usuário."),
    ]
    s += tabela([
        ["Ganho real", "Nota do usuário (1 a 5)", "Leitura dos sinais", "Ajuste no peso"],
        ["≥ +5 pontos", "≥ 3", "concordam: funcionou", "+0,10"],
        ["abaixo de −5 pontos", "≤ 3", "concordam: não funcionou", "−0,10"],
        ["abaixo de +5 pontos", "≤ 2", "concordam: não funcionou", "−0,10"],
        ["≥ +5 pontos", "≤ 2", "conflitam", "0,00"],
        ["abaixo de −5 pontos", "≥ 4", "conflitam", "−0,03"],
        ["entre −5 e +5 pontos", "≥ 4", "preferência pessoal", "+0,03"],
        ["demais combinações", "—", "inconclusivo", "0,00"],
    ], [4.3 * cm, 3.9 * cm, 4.6 * cm, W - 12.8 * cm], "Regra de ajuste do peso aprendido (learning_engine.calcular_ajuste_peso).")
    s += [p("O peso fica limitado ao intervalo de 0,50 a 1,50 e cada novo ajuste no mesmo contexto é "
            "multiplicado por um fator que diminui com o número de comparações já feitas (mínimo de 0,30). "
            "Isso impede que poucos exemplos dominem as recomendações.")]

    # 10 --------------------------------------------------------------
    s += secao(10, "Alterações em relação à Sprint 3")
    s += [p("A tabela resume o que foi removido, modificado e adicionado, com a justificativa de cada mudança. "
            "O ciclo principal do sistema e as regras de recomendação continuam iguais; a Sprint 4 muda onde os "
            "dados ficam e acrescenta a ligação com o app da câmera.")]
    s += tabela([
        ["Tipo", "Sprint 3", "Sprint 4", "Justificativa"],
        ["Removido", "Banco SQLite (data/jovi.db) com tabelas e SQL", "Sem banco relacional", "A Sprint 4 exige persistência em arquivos de texto ou JSON."],
        ["Modificado", "Persistência em SQLite", "usuarios.json + um arquivo JSON por perfil", "Dados legíveis e isolamento por usuário visível nos arquivos."],
        ["Modificado", "Integridade garantida por transações SQL", "Gravação atômica e validações em database.py", "Mesma proteção contra dados pela metade, sem banco."],
        ["Modificado", "SQL escrito dentro do motor de aprendizado", "Funções de persistência com parâmetros e retorno", "Separação de responsabilidades e testes mais simples."],
        ["Modificado", "Menu com 9 opções", "Menu com 10 opções", "Nova opção de integração."],
        ["Adicionado", "—", "Integração com o app JOVI por arquivos JSON", "Requisito de integração com o restante da solução."],
        ["Adicionado", "—", "Contrato versionado com exemplo em integracao/exemplos/", "Outra parte da solução consegue gerar pedidos válidos."],
        ["Adicionado", "—", "Exportação do perfil para o app", "O app exibe evolução e conselhos aprendidos."],
        ["Adicionado", "—", "Mensagem clara para arquivo de dados corrompido", "Falha previsível tratada com try/except."],
        ["Adicionado", "—", "Sessão segura ao excluir o perfil em uso; Ctrl+C sem traceback", "Robustez da interface."],
        ["Mantido", "Ciclo medir, interpretar, simular, recapturar e aprender", "Inalterado", "É o núcleo da proposta."],
        ["Mantido", "API Gemini com schema e modo offline", "Inalterado", "Requisito de API externa já atendido."],
    ], [2.4 * cm, 4.4 * cm, 4.7 * cm, W - 11.5 * cm], "Alterações da Sprint 3 para a Sprint 4.")

    # 11 --------------------------------------------------------------
    s += secao(11, "Atendimento aos critérios e testes")
    s += tabela([
        ["Critério da Sprint 4", "Evidência", "Situação"],
        ["Menu, retorno ao menu e opção de encerrar", "Seção 3 · `main.executar_sessao`", "Atendido"],
        ["Funcionalidades de acordo com a proposta", "Seções 1 e 3", "Atendido"],
        ["Subrotinas com parâmetros e retorno", "Seção 4 · tipos verificados por teste", "Atendido"],
        ["Validação de entradas e try/except", "Seção 8", "Atendido"],
        ["Persistência em arquivos JSON", "Seção 5", "Atendido"],
        ["Consumo de API externa", "Seção 7", "Atendido"],
        ["Integração com o restante da solução", "Seção 6", "Atendido"],
        ["Boas práticas de programação", "Seção 4 · testes automatizados", "Atendido"],
        ["Interface intuitiva e mensagens claras", "Seção 3", "Atendido"],
    ], [7.0 * cm, W - 9.4 * cm, 2.4 * cm], "Mapa entre os critérios de avaliação e o projeto.")
    s += [
        h2("Testes automatizados"),
        p(f"A suíte tem <b>{total_testes} testes</b> escritos com a biblioteca padrão "
          "<font face='Mono' size='8.5'>unittest</font>. Eles usam pastas temporárias e um cliente de IA falso, "
          "então não dependem de internet, chave de API nem dos dados do usuário. O arquivo "
          "<font face='Mono' size='8.5'>test_requisitos_sprint4.py</font> tem um grupo de testes para cada "
          "critério da tabela acima."),
    ]
    descricoes = {
        "test_analysis_service": "Modo offline e modo híbrido com cliente de IA controlado",
        "test_armazenamento_json": "Arquivos JSON, gravação atômica, arquivo corrompido, exclusão, duplicidades",
        "test_database_and_learning": "Isolamento por usuário, comparação, pesos e recomendação pendente",
        "test_integracao": "Contrato de integração, pedidos inválidos e exportação de perfil",
        "test_main_sessao": "Exclusão do perfil em uso, Ctrl+C e fim da entrada",
        "test_recommendation_and_gemini": "Pontuação, cenários, validação da resposta da IA e repetição em falhas",
        "test_reports": "Textos em linguagem simples, sem códigos internos",
        "test_requisitos_sprint4": "Um grupo de testes por critério da Sprint 4",
        "test_validators_and_images": "Validações, métricas, EXIF, cópia temporária e preservação do original",
    }
    linhas_testes = [["Arquivo", "Testes", "O que cobre"]]
    linhas_testes += [[f"`{nome}.py`", str(qtd), descricoes.get(nome, "")] for nome, qtd in ex["testes"].items()]
    linhas_testes += [["Total", f"<b>{total_testes}</b>", "Todos passando na versão entregue"]]
    s += tabela(linhas_testes, [5.8 * cm, 1.5 * cm, W - 7.3 * cm], "Distribuição dos testes automatizados.")

    # 12 --------------------------------------------------------------
    s += secao(12, "Como executar e demonstrar")
    s += [
        h2("Instalação e execução"),
        bloco_codigo("python -m venv .venv\n"
                     ".\\.venv\\Scripts\\Activate.ps1\n"
                     "python -m pip install -r requirements.txt\n"
                     "python main.py", "PowerShell (Windows, Python 3.11 ou superior)"),
        h2("API Gemini (opcional)"),
        p("Crie um arquivo <font face='Mono' size='8.5'>.env</font> na raiz, a partir do "
          "<font face='Mono' size='8.5'>.env.example</font>, com GEMINI_API_KEY e GEMINI_MODEL. "
          "O arquivo não entra no repositório nem no ZIP. Sem ele, o programa funciona em modo offline."),
        h2("Executar os testes"),
        bloco_codigo("python -m unittest discover -s tests -v\n"
                     "python -m unittest tests.test_requisitos_sprint4 -v   # apenas os critérios da Sprint 4",
                     "PowerShell"),
        h2("Roteiro de demonstração"),
    ]
    s += tabela([
        ["Passo", "Ação", "O que mostrar"],
        ["1", "Criar o perfil e aceitar o tour guiado", "Diagnóstico completo de uma foto de exemplo"],
        ["2", "Opção 2 com samples/exemplo_escuro.jpg", "Resumo simples e as três alternativas"],
        ["3", "Opção 4 com samples/exemplo_nitido.jpg", "Ganho real, nota do usuário e peso atualizado"],
        ["4", "Opção 10: criar e processar solicitação", "Arquivo de resultado em integracao/saida/"],
        ["5", "Abrir data/perfis/perfil_1.json", "Persistência em JSON, isolada por perfil"],
        ["6", "Trocar de perfil e abrir a opção 7", "O aprendizado não é compartilhado entre usuários"],
    ], [1.4 * cm, 6.6 * cm, W - 8.0 * cm], "Sugestão de roteiro para a apresentação.")

    # 13 --------------------------------------------------------------
    s += secao(13, "Limitações, referências e conclusão")
    s += [
        h2("Limitações conhecidas"),
        *lista([
            "Os limiares das métricas são heurísticos e precisariam de calibração com mais fotos reais.",
            "A pontuação depende do objetivo informado e não mede valor artístico.",
            "A IA pode errar; por isso sua resposta é validada, rotulada e nunca tratada como prova.",
            "A integração usa pastas locais compartilhadas; em produção, uma API HTTP seria mais adequada.",
            "O programa roda no terminal e não controla diretamente o hardware da câmera.",
        ]),
        h2("Referências"),
        *lista([
            "Google AI for Developers. <i>Image understanding</i>. ai.google.dev/gemini-api/docs/image-understanding",
            "Google AI for Developers. <i>Structured output</i>. ai.google.dev/gemini-api/docs/structured-output",
            "Android Developers. <i>Camera extensions</i>. developer.android.com/media/camera/camera-extensions",
            "Python Software Foundation. <i>json</i>, <i>os.replace</i> e <i>unittest</i>. docs.python.org/3",
            "OpenCV. <i>Image processing documentation</i>. docs.opencv.org",
        ]),
        h2("Conclusão"),
        p("A Sprint 4 entrega a versão final do JOVI AI LensLab. O programa mantém o ciclo de medir, "
          "interpretar, simular, verificar e aprender, agora com persistência em arquivos JSON, consumo da API "
          "Gemini com tratamento de falhas e integração por arquivos com o app da câmera JOVI. Cada critério da "
          "avaliação é comprovado por testes automatizados que acompanham o código entregue."),
    ]
    return s


def construir() -> Path:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    exemplos = coletar_exemplos()
    CONT.figura = CONT.tabela = 0
    historia = montar_capa() + montar_sumario() + montar_conteudo(exemplos)
    Documento(DESTINO).multiBuild(historia)
    return DESTINO


if __name__ == "__main__":
    print(construir())
