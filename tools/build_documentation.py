"""Gera a documentação acadêmica da Sprint 4 em PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "docs" / "documentacao_nextframe_jovi_sprint4.pdf"

AZUL = colors.HexColor("#092A4A")
CIANO = colors.HexColor("#00A9C6")
AZUL_CLARO = colors.HexColor("#EAF7FA")
CINZA = colors.HexColor("#526170")
CINZA_CLARO = colors.HexColor("#F2F5F7")
VERDE = colors.HexColor("#16856B")
LARANJA = colors.HexColor("#D56A1A")


class Documento(BaseDocTemplate):
    def __init__(self, caminho: Path):
        super().__init__(
            str(caminho), pagesize=A4, leftMargin=1.65 * cm, rightMargin=1.65 * cm,
            topMargin=1.75 * cm, bottomMargin=1.55 * cm,
            title="NextFrame JOVI AI LensLab - Sprint 4",
            author="Equipe NextFrame",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="conteudo")
        self.addPageTemplates([
            PageTemplate(id="padrao", frames=frame, onPage=desenhar_pagina),
        ])


def desenhar_pagina(canvas, doc) -> None:
    canvas.saveState()
    largura, altura = A4
    if doc.page == 1:
        canvas.setFillColor(AZUL)
        canvas.rect(0, 0, largura, altura, fill=1, stroke=0)
        canvas.setFillColor(CIANO)
        canvas.rect(0, altura - 0.48 * cm, largura, 0.48 * cm, fill=1, stroke=0)
        canvas.circle(largura - 1.4 * cm, 1.4 * cm, 2.7 * cm, fill=1, stroke=0)
    else:
        canvas.setStrokeColor(colors.HexColor("#D9E2E8"))
        canvas.line(1.65 * cm, altura - 1.15 * cm, largura - 1.65 * cm, altura - 1.15 * cm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(AZUL)
        canvas.drawString(1.65 * cm, altura - 0.88 * cm, "NEXTFRAME | JOVI AI LENSLAB")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(CINZA)
        pagina = f"Sprint 4  |  Página {doc.page}"
        canvas.drawRightString(largura - 1.65 * cm, 0.75 * cm, pagina)
    canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CapaKicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10,
    leading=14, textColor=CIANO, spaceAfter=10, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="CapaTitulo", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=31,
    leading=34, textColor=colors.white, spaceAfter=16, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="CapaSub", parent=styles["Normal"], fontName="Helvetica", fontSize=13,
    leading=19, textColor=colors.HexColor("#DCEAF3"), spaceAfter=10,
))
styles.add(ParagraphStyle(
    name="H1Jovi", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20,
    leading=24, textColor=AZUL, spaceBefore=2, spaceAfter=12,
))
styles.add(ParagraphStyle(
    name="H2Jovi", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12.5,
    leading=16, textColor=CIANO, spaceBefore=9, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="BodyJovi", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.3,
    leading=13.7, textColor=colors.HexColor("#263642"), spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="SmallJovi", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.8,
    leading=10.6, textColor=colors.HexColor("#334653"),
))
styles.add(ParagraphStyle(
    name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10,
    leading=14, textColor=AZUL, leftIndent=10, rightIndent=10, spaceBefore=5, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="Sumario", parent=styles["BodyText"], fontName="Helvetica", fontSize=10,
    leading=17, textColor=AZUL,
))


def p(texto: str, estilo: str = "BodyJovi") -> Paragraph:
    return Paragraph(texto, styles[estilo])


def secao(numero: str, titulo: str) -> Paragraph:
    return p(f"{numero}. {titulo}", "H1Jovi")


def h2(texto: str) -> Paragraph:
    return p(texto, "H2Jovi")


def bullet(texto: str) -> Paragraph:
    return Paragraph(f"- {texto}", ParagraphStyle(
        "bullet_temp", parent=styles["BodyJovi"], leftIndent=12, firstLineIndent=-8, spaceAfter=4
    ))


def tabela(dados, larguras, cabecalho=True, tamanho=7.6) -> Table:
    estilo_cabecalho = ParagraphStyle(
        "cab", parent=styles["SmallJovi"], textColor=colors.white, fontName="Helvetica-Bold"
    )
    convertidos = []
    for indice, linha in enumerate(dados):
        if cabecalho and indice == 0:
            convertidos.append([Paragraph(str(celula), estilo_cabecalho) for celula in linha])
        else:
            convertidos.append([p(str(celula), "SmallJovi") for celula in linha])
    tab = Table(convertidos, colWidths=larguras, repeatRows=1 if cabecalho else 0, hAlign="LEFT")
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CAD6DE")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
    ]
    if cabecalho:
        estilo.extend([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ])
    for linha in range(2, len(dados), 2):
        estilo.append(("BACKGROUND", (0, linha), (-1, linha), CINZA_CLARO))
    tab.setStyle(TableStyle(estilo))
    return tab


def callout(texto: str, cor=AZUL_CLARO) -> Table:
    box = Table([[p(texto, "Callout")]], colWidths=[17.6 * cm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cor),
        ("BOX", (0, 0), (-1, -1), 0.7, CIANO),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return box


def construir() -> Path:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    story = []

    # Capa
    story.extend([
        Spacer(1, 2.5 * cm),
        p("FIAP | COMPUTATIONAL THINKING WITH PYTHON | SPRINT 4", "CapaKicker"),
        p("NextFrame JOVI<br/>AI LensLab", "CapaTitulo"),
        p("Sistema híbrido de análise fotográfica, simulação contrafactual e aprendizado individualizado.", "CapaSub"),
        Spacer(1, 1.0 * cm),
        callout("Da recomendação genérica à experimentação verificável: medir, interpretar, simular, recapturar e aprender.", colors.HexColor("#D8F5F8")),
        Spacer(1, 1.25 * cm),
        p("<b>Equipe NextFrame</b>", "CapaSub"),
        p("Bruno Carreiro  |  Daniel Graciano  |  Gustavo Romero<br/>Leonardo Porto  |  Leonardo Gomes", "CapaSub"),
        Spacer(1, 1.0 * cm),
        p("Documentação técnica e acadêmica<br/>23 de outubro de 2026", "CapaSub"),
        PageBreak(),
    ])

    # Sumário
    story.extend([
        secao("0", "Sumário"),
        p("A organização abaixo acompanha os critérios de avaliação e separa proposta, implementação, mudanças e validação.", "BodyJovi"),
        Spacer(1, 0.3 * cm),
    ])
    sumario = [
        ("1", "Resumo executivo", "3"), ("2", "Objetivos e justificativa", "3"),
        ("3", "Inovação e experiência proposta", "4"), ("4", "Funcionalidades implementadas", "5"),
        ("5", "Arquitetura técnica", "6"), ("6", "Persistência em JSON e integração", "7"),
        ("7", "Métricas, IA e recomendações", "8"), ("8", "Privacidade, segurança e robustez", "9"),
        ("9", "Alterações em relação à Sprint 3", "10"), ("10", "Atendimento à rubrica e testes", "11"),
        ("11", "Execução e roteiro de demonstração", "12"), ("12", "Pesquisa, limitações e conclusão", "13"),
    ]
    story.append(tabela([["Seção", "Conteúdo", "Página"], *sumario], [1.7 * cm, 13.6 * cm, 2.3 * cm]))
    story.extend([
        Spacer(1, 0.5 * cm),
        callout("Escopo da entrega: código-fonte Python, testes, imagens artificiais de demonstração, documentação em PDF e arquivo ZIP único."),
        PageBreak(),
    ])

    # 1 e 2
    story.extend([
        secao("1", "Resumo executivo"),
        p("O NextFrame JOVI AI LensLab dá continuidade ao Camera Assistant da Sprint 2. Na Sprint 3 ele passou a analisar fotografias, explicar evidências, propor alternativas comparáveis, verificar recapturas e aprender individualmente com os resultados. A Sprint 4 entrega a implementação final: os dados passam a ser persistidos em arquivos JSON, um por perfil, e o LensLab se integra ao restante da solução NextFrame trocando arquivos JSON com o app da câmera JOVI."),
        callout("Resultado principal: um tutor fotográfico transparente que não se limita a dizer qual modo usar; ele mostra o motivo, o risco, o ganho estimado e aprende com o resultado real."),
        h2("Problema central"),
        p("Usuários de smartphone conhecem modos como Retrato, Noturno e HDR, mas nem sempre sabem quando eles ajudam, quais riscos introduzem ou como avaliar se a orientação melhorou a foto. Uma recomendação fixa também ignora intenção artística, contexto e preferências individuais."),
        secao("2", "Objetivos e justificativa"),
        h2("Objetivo geral"),
        p("Desenvolver em Python um laboratório de fotografia capaz de combinar análise técnica local, interpretação multimodal opcional e feedback do usuário para produzir recomendações contextuais, testáveis e progressivamente personalizadas."),
        h2("Objetivos específicos"),
        bullet("Medir brilho, contraste, nitidez, saturação, resolução e recortes de luz sem depender da internet."),
        bullet("Interpretar assunto, composição e movimento com Gemini somente após consentimento."),
        bullet("Apresentar três alternativas 'E se?' com ganho previsto, esforço, risco, confiança e evidências."),
        bullet("Comparar uma recaptura real usando o mesmo objetivo e intenção da foto original."),
        bullet("Guardar histórico e pesos de aprendizado isolados por perfil."),
        bullet("Manter operação offline quando a API estiver ausente ou falhar."),
        bullet("Persistir os dados em arquivos JSON legíveis e integrar-se ao app JOVI por troca de arquivos."),
        h2("Justificativa"),
        p("A solução desloca o foco de uma escolha automática para um processo educativo. Essa abordagem é adequada ao desafio JOVI porque amplia a descoberta de recursos avançados, reduz decisões opacas e cria uma experiência de melhoria contínua sem exigir conhecimento técnico prévio."),
        PageBreak(),
    ])

    # 3
    story.extend([
        secao("3", "Inovação e experiência proposta"),
        p("A inovação está na combinação de cinco etapas em um ciclo fechado. Nenhuma delas, isoladamente, é apresentada como prova absoluta de qualidade."),
        Spacer(1, 0.2 * cm),
        tabela([
            ["Etapa", "Origem", "O que entrega", "Rótulo na interface"],
            ["1. Medir", "OpenCV + Pillow", "Indicadores técnicos reproduzíveis", "MEDIDO"],
            ["2. Interpretar", "Gemini opcional", "Assunto, cena, composição e movimento", "IA"],
            ["3. Simular", "Motor contrafactual", "Ranking de ações, ganhos e riscos", "PREVISTO"],
            ["4. Verificar", "Foto antes/depois", "Delta real da pontuação e dimensões", "VERIFICADO"],
            ["5. Aprender", "Arquivos JSON", "Peso por usuário, contexto e ação", "PERSONALIZADO"],
        ], [2.5 * cm, 3.4 * cm, 7.4 * cm, 4.3 * cm]),
        h2("Cenários contrafactuais"),
        p("Para cada problema detectado, o motor pergunta implicitamente: 'E se o usuário adicionar luz?', 'E se estabilizar a câmera?' ou 'E se reduzir a exposição?'. A estimativa combina severidade, eficácia da ação e peso aprendido. O sistema também informa riscos, por exemplo: modo noturno recupera luz, porém pode borrar assuntos em movimento."),
        h2("Pontuação contextual, não estética"),
        p("A mesma fotografia pode receber pesos diferentes para documento, retrato, produto, paisagem ou redes sociais. Uma imagem escura pode ser defeito em um documento e escolha válida em um retrato dramático. A pontuação orienta comparação no mesmo contexto; ela não define se uma obra é artisticamente boa."),
        h2("Inspiração prática"),
        p("O Camera Coach do Pixel demonstra a relevância de orientar enquadramento e captura no contexto. As Camera Extensions do Android mostram que Night, HDR, Auto e Bokeh possuem benefícios e limitações diferentes. Fóruns de fotografia reforçam que Night Mode não elimina limites físicos e que usuários valorizam controle e explicações."),
        callout("Diferencial defendido: o LensLab mede o resultado posterior e usa a combinação de ganho real + avaliação humana para ajustar recomendações futuras."),
        PageBreak(),
    ])

    # 4
    story.extend([
        secao("4", "Funcionalidades implementadas"),
        tabela([
            ["Menu", "Funcionalidade", "Descrição e validações"],
            ["1", "Perfis", "Cria, seleciona ou exclui perfil com apelido único, nível, estilo e consentimento; oferece um tour guiado ao criar o primeiro perfil."],
            ["2", "Analisar fotografia", "Seleciona a foto pelo explorador de arquivos ou por lista; mede indicadores, consulta IA quando permitido e mostra um resumo em linguagem simples (detalhes técnicos são opcionais)."],
            ["3", "Explorar 'E se?'", "Gera prévia educativa para ações simuláveis sem sobrescrever o original."],
            ["4", "Comparar antes/depois", "Repete o contexto, mede recaptura, registra avaliação e atualiza peso; sugere automaticamente a última recomendação marcada como atalho."],
            ["5", "Marcar recomendação", "Marca um conselho como pendente de teste; ele vira o atalho oferecido no menu 4 até ser verificado."],
            ["6", "Histórico", "Lista análises persistidas do perfil ativo."],
            ["7", "Evolução", "Mostra total, ganho médio, sucessos e conselho mais eficaz."],
            ["8", "Orientação sem foto", "Mantém a recomendação guiada da Sprint 2 para uso rápido."],
            ["9", "Privacidade e dados", "Altera consentimento, exporta resumo ou exclui o perfil e o arquivo JSON dele."],
            ["10", "Integração com o app JOVI", "Processa solicitações JSON da pasta integracao/entrada, devolve resultados em integracao/saida e exporta o perfil para o app."],
            ["0", "Encerrar", "Finaliza com segurança (inclusive com Ctrl+C); toda função retorna ao menu."],
        ], [1.2 * cm, 4.2 * cm, 12.2 * cm]),
        h2("Interface e navegabilidade"),
        p("As escolhas numéricas são repetidas até receber valor válido, o valor 0 cancela fluxos longos e as exceções previsíveis são convertidas em mensagens claras. O diagnóstico mostra explicitamente o modo HÍBRIDO ou OFFLINE. A pontuação usa barra ASCII e os rótulos MEDIDO/IA/PREVISTO/VERIFICADO recebem cor quando o terminal suporta. Enter reaproveita o último objetivo escolhido na sessão."),
        h2("Entradas validadas"),
        bullet("Extensões JPG, JPEG, PNG e WEBP; até 20 MB; resolução mínima 320 x 240."),
        bullet("Decodificação real da imagem para impedir arquivos renomeados ou corrompidos."),
        bullet("Faixas numéricas, respostas sim/não e limites de tamanho de texto."),
        bullet("Associação entre usuário, análise, recomendação e recaptura antes do aprendizado."),
        PageBreak(),
    ])

    # 5
    story.extend([
        secao("5", "Arquitetura técnica"),
        p("A solução foi dividida em módulos pequenos, testáveis e com responsabilidades explícitas."),
        tabela([
            ["Módulo", "Responsabilidade", "Principais retornos"],
            ["main.py", "Menu, coleta de dados e navegação", "Fluxos de usuário"],
            ["validators.py", "Validação pura e repetição de entradas", "Valores normalizados ou erro"],
            ["image_analyzer.py", "Métricas, hash, cópia da API e prévias", "Dicionário de métricas / caminho"],
            ["gemini_client.py", "Prompt, schema, chamada e filtro", "Resultado categorizado"],
            ["recommendation_engine.py", "Pontuação e contrafactuais", "Dimensões / ranking"],
            ["analysis_service.py", "Orquestração híbrida e persistência", "Diagnóstico completo"],
            ["database.py", "Persistência em arquivos JSON, gravação atômica", "Perfis e registros"],
            ["integracao.py", "Contrato de troca de arquivos com o app JOVI", "Resultado / erro em JSON"],
            ["learning_engine.py", "Comparação e atualização de pesos", "Ganho e evolução"],
            ["reports.py", "Formatação e exportação", "Texto / JSON"],
        ], [4.1 * cm, 8.1 * cm, 5.4 * cm]),
        h2("Fluxo principal"),
        tabela([
            ["Entrada", "Processamento", "Decisão", "Saída"],
            ["Foto + objetivo + intenção", "Métricas locais", "Consentimento e chave?", "Offline ou chamada Gemini"],
            ["Métricas + IA validada", "Detecção de problemas", "Peso individual do contexto", "3 recomendações ranqueadas"],
            ["Recaptura + nota 1-5", "Nova análise no mesmo contexto", "Sinais concordam?", "Comparação + peso atualizado"],
        ], [3.7 * cm, 4.8 * cm, 4.5 * cm, 4.6 * cm]),
        h2("Boas práticas"),
        bullet("Funções com parâmetros e retornos, constantes centrais e type hints."),
        bullet("Gravação atômica em JSON (arquivo temporário + os.replace) e try/except para arquivo corrompido."),
        bullet("Arquivos originais tratados como somente leitura; saídas usam diretório próprio."),
        bullet("Dependências declaradas e testes baseados na biblioteca unittest."),
        PageBreak(),
    ])

    # 6
    story.extend([
        secao("6", "Persistência em JSON e integração"),
        p("Os dados ficam em arquivos JSON legíveis, criados automaticamente na pasta data/. Cada perfil tem um arquivo próprio, o que torna o isolamento entre usuários explícito: excluir um perfil apaga apenas o arquivo dele."),
        tabela([
            ["Arquivo", "Conteúdo"],
            ["data/usuarios.json", "Perfis (apelido, nível, estilo, consentimento) e contadores de identificadores únicos"],
            ["data/perfis/perfil_&lt;id&gt;.json", "Análises (métricas e IA), recomendações, comparações e pesos aprendidos de um único perfil"],
        ], [5.4 * cm, 12.2 * cm]),
        p("Toda gravação é escrita em um arquivo temporário e só depois movida para o lugar definitivo (os.replace), de modo que uma falha no meio não corrompe os dados. Um arquivo ilegível é tratado com try/except e gera uma mensagem indicando qual arquivo restaurar, sem encerrar o programa com erro técnico."),
        h2("Integração com o app JOVI por arquivos"),
        tabela([
            ["Etapa", "Pasta", "Formato"],
            ["App envia solicitação", "integracao/entrada/", "versao, id_solicitacao, perfil, foto, objetivo, intencao"],
            ["LensLab devolve resultado", "integracao/saida/resultado_&lt;id&gt;.json", "nota, classificação, pontos fortes e a melhorar, recomendações, status da IA"],
            ["Solicitação inválida", "integracao/com_erro/ + saida/erro_&lt;nome&gt;.json", "motivo legível (JSON malformado, campo ausente, foto inexistente)"],
            ["Exportação de perfil", "integracao/saida/perfil_&lt;id&gt;.json", "evolução, conselhos aprendidos e recomendação pendente"],
        ], [4.0 * cm, 5.6 * cm, 8.0 * cm]),
        p("Uma solicitação nunca fica parada na entrada: é movida para processadas/ ou com_erro/. Um perfil existente é reaproveitado pelo apelido e o consentimento dele não pode ser alterado por um sistema externo."),
        h2("Aprendizado individualizado"),
        p("A chave de contexto (objetivo | faixa de luz | movimento | nível | estilo) separa o que foi aprendido. O ajuste é +0,10 quando ganho real e avaliação concordam positivamente, -0,10 quando concordam negativamente e menor ou nulo quando os sinais conflitam. O peso fica limitado a 0,50-1,50 e cada nova comparação no mesmo contexto pesa um pouco menos, para que poucos exemplos não dominem o ranking."),
        PageBreak(),
    ])

    # 7
    story.extend([
        secao("7", "Métricas, IA e recomendações"),
        h2("Análise local"),
        tabela([
            ["Indicador", "Cálculo", "Uso"],
            ["Brilho", "Média de luminância normalizada", "Pouca luz / excesso de luz"],
            ["Contraste", "Desvio padrão da luminância", "Separação visual do assunto"],
            ["Nitidez", "Variância do Laplaciano", "Probabilidade de desfoque"],
            ["Saturação", "Média do canal S em HSV", "Cores excessivas ou fracas"],
            ["Sombras / realces", "Percentual perto de 0 / 255", "Perda de detalhe tonal"],
            ["Resolução", "Largura x altura", "Margem para recorte/ampliação"],
        ], [3.2 * cm, 7.1 * cm, 7.3 * cm]),
        h2("Papel do Gemini"),
        p("O modelo gemini-flash-latest (alias mantido pela Google para o Flash recomendado no momento, evitando quebra quando uma versão específica é descontinuada) recebe o objetivo, a intenção e uma cópia reduzida da foto. A resposta deve obedecer a um JSON Schema: assunto, tipo de cena, intenção percebida, movimento, problemas, composição, ações e incertezas. Códigos fora de listas permitidas são descartados e todas as faixas numéricas são verificadas. Falhas transitórias (sobrecarga, timeout) acionam uma nova tentativa automática antes de cair para o modo offline."),
        h2("Fusão e confiança"),
        p("Problemas locais recebem fonte MEDIDO; interpretações visuais recebem fonte IA. Quando as duas fontes sustentam a mesma hipótese, ela é confirmada e a recomendação pode ganhar confiança alta. Se a IA falhar, o conjunto local continua suficiente para produzir alternativas."),
        h2("Estimativa contrafactual"),
        p("Para cada ação, o ganho base é a soma de severidade do problema x eficácia cadastrada x 28. Depois aplica-se o peso individual e limites de segurança. Em assuntos com movimento, a previsão do modo noturno é reduzida porque a exposição prolongada pode aumentar o borrão."),
        callout("A saída é explicável: ação + ganho previsto + risco + esforço + confiança + evidência."),
        PageBreak(),
    ])

    # 8
    story.extend([
        secao("8", "Privacidade, segurança e robustez"),
        h2("Privacidade por construção"),
        bullet("Consentimento fica no perfil e pode ser revogado pelo menu."),
        bullet("A chave é lida de variável de ambiente ou .env ignorado; nunca é impressa nem gravada nos arquivos de dados."),
        bullet("A cópia enviada é convertida para JPEG, redimensionada para até 1600 px e salva sem EXIF."),
        bullet("A cópia temporária é removida em bloco finally, inclusive em caso de erro."),
        bullet("Os arquivos JSON guardam hash e nome do arquivo, não pixels da fotografia nem GPS; o resultado de integração nem o hash inclui."),
        bullet("O usuário pode exportar um resumo ou excluir seu perfil, o que apaga o arquivo JSON inteiro dele."),
        h2("Falhas controladas"),
        tabela([
            ["Falha", "Comportamento"],
            ["Sem chave ou sem consentimento", "Modo offline sem tentativa de chamada"],
            ["Timeout / rede", "Mensagem categorizada e análise local preservada"],
            ["Autenticação / cota", "Fallback sem expor detalhes sensíveis"],
            ["JSON inválido", "Resposta descartada; IA não contamina o ranking"],
            ["Modelo indisponível / servidor sobrecarregado", "Erro categorizado; nova tentativa automática antes do fallback offline"],
            ["Imagem corrompida ou pequena", "Validação bloqueia antes do processamento"],
            ["Recaptura de outro usuário ou idêntica à original", "Comparação recusada"],
            ["Arquivo de dados JSON corrompido", "Mensagem indicando o arquivo; o programa não encerra com erro técnico"],
            ["Solicitação de integração inválida", "Movida para com_erro/ com erro_&lt;nome&gt;.json explicando o motivo"],
            ["Ctrl+C ou fim da entrada", "Encerramento amigável, sem traceback"],
        ], [5.2 * cm, 12.4 * cm]),
        h2("Modelo de ameaça acadêmico"),
        p("A solução reduz vazamento acidental de chave, metadados e fotos, mas continua sendo um protótipo local. Em produção seriam necessários cofre de segredos, criptografia dos arquivos de dados, autenticação real, política de retenção, telemetria com consentimento e revisão jurídica da API."),
        PageBreak(),
    ])

    # 9
    story.extend([
        secao("9", "Alterações em relação à Sprint 3"),
        p("A evolução foi rastreada conforme solicitado na rubrica: o que foi removido, modificado e adicionado."),
        tabela([
            ["Situação", "Sprint 3", "Sprint 4", "Justificativa"],
            ["Removido", "Banco SQLite (data/jovi.db) com tabelas e SQL", "Sem banco relacional", "Requisito de persistência em arquivos de texto ou JSON"],
            ["Modificado", "Persistência em SQLite", "Arquivos JSON: usuarios.json + um arquivo por perfil", "Dados legíveis, isolamento explícito por usuário"],
            ["Modificado", "Integridade garantida por transação SQL", "Gravação atômica (temporário + os.replace) e validações no código", "Mesma proteção contra dados pela metade, sem SQLite"],
            ["Modificado", "SQL direto no motor de aprendizado", "Funções de persistência com parâmetros e retorno", "Separação de responsabilidades"],
            ["Modificado", "Menu com 9 opções", "Menu com 10 opções", "Nova opção de integração"],
            ["Adicionado", "Exportação JSON avulsa", "Integração por arquivos com o app JOVI (entrada, saída, processadas, com_erro)", "Integrar com o restante da solução NextFrame"],
            ["Adicionado", "-", "Contrato versionado e exemplo em integracao/exemplos/", "Outra equipe/sistema consegue gerar solicitações válidas"],
            ["Adicionado", "-", "Tratamento de arquivo de dados corrompido", "Falha previsível vira mensagem clara (try/except)"],
            ["Adicionado", "-", "Sessão segura ao excluir o perfil em uso; Ctrl+C sem traceback", "Robustez da interface"],
            ["Mantido", "Ciclo medir, interpretar, simular, recapturar, aprender", "Inalterado", "Núcleo da proposta de valor"],
            ["Mantido", "API Gemini com schema e fallback offline", "Inalterado", "Requisito de API externa já atendido"],
        ], [2.1 * cm, 4.6 * cm, 5.4 * cm, 5.5 * cm]),
        h2("Compatibilidade com a proposta anterior"),
        p("O projeto continua sendo um assistente de câmera JOVI em terminal, com o mesmo ciclo e as mesmas regras de recomendação e aprendizado. A Sprint 4 muda onde e como os dados são guardados e acrescenta a ponte com o app da câmera; nenhuma funcionalidade da Sprint 3 foi perdida."),
        PageBreak(),
    ])

    # 10
    story.extend([
        secao("10", "Atendimento à rubrica e testes"),
        tabela([
            ["Critério da Sprint 4", "Evidência na solução", "Status"],
            ["Menu, retorno ao menu e opção de sair", "main.py: opções 1-10 e 0; toda função volta ao loop", "Atendido"],
            ["Funcionalidades de acordo com a proposta", "Ciclo completo do LensLab + integração com o app JOVI", "Atendido"],
            ["Subrotinas com parâmetros e retorno", "Módulos por responsabilidade; regras puras separadas da interface", "Atendido"],
            ["Validação de entrada e try/except", "validators.py, database.py (arquivo corrompido), integracao.py (contrato)", "Atendido"],
            ["Persistência em arquivos JSON", "data/usuarios.json e data/perfis/perfil_&lt;id&gt;.json", "Atendido"],
            ["Consumo de API externa", "Google Gemini (gemini_client.py) com JSON Schema e fallback", "Atendido"],
            ["Integração com o restante da solução", "Troca de arquivos JSON em integracao/ (integracao.py)", "Atendido"],
            ["Boas práticas", "Constantes, type hints, gravação atômica, 84 testes", "Atendido"],
            ["Interface intuitiva", "Resumo em linguagem simples, explorador de arquivos, cancelamento com 0", "Atendido"],
        ], [5.2 * cm, 9.6 * cm, 2.8 * cm]),
        h2("Validação automatizada"),
        p("Foram implementados 84 testes unitários e de integração com imagens artificiais. A suíte usa apenas pastas temporárias para não depender de dados pessoais ou dos arquivos de demonstração."),
        tabela([
            ["Grupo", "Cobertura"],
            ["Entradas e imagens", "Faixas, sim/não, caminho, métricas, EXIF (incluindo Sub-IFD), temporário, original e seletor de arquivo"],
            ["Persistência JSON", "Arquivos legíveis, gravação sem temporário residual, arquivo corrompido, exclusão, IDs únicos, duplicidades"],
            ["Integração", "Solicitação válida, JSON malformado, campos inválidos, BOM do Bloco de Notas, exportação de perfil, menu 10"],
            ["Perfis e sessão", "Isolamento, exclusão do perfil em uso, recomendação pendente, Ctrl+C e fim de entrada"],
            ["Requisitos do Sprint 4", "tests/test_requisitos_sprint4.py: um grupo de testes por critério da rubrica (menu, subrotinas tipadas, try/except, JSON, API, integração, interface)"],
            ["Recomendação", "Peso por objetivo, evidência, peso aprendido exposto e penalidade de movimento"],
            ["Gemini", "Campos obrigatórios, códigos permitidos, resposta inválida, categorização de erro e nova tentativa em falha transitória"],
            ["Serviço", "Fallback offline e execução híbrida com cliente controlado"],
            ["Aprendizado", "Ganho, nota, sinais conflitantes, decaimento do ajuste e isolamento do peso"],
            ["Relatórios", "Resumo em linguagem simples e tradução do veredito da recaptura"],
        ], [5.2 * cm, 12.4 * cm]),
        callout("Resultado da execução final: 84 testes concluídos com sucesso, além de teste manual do menu, incluindo a integração por arquivos."),
        PageBreak(),
    ])

    # 11
    story.extend([
        secao("11", "Execução e roteiro de demonstração"),
        h2("Instalação"),
        callout("python -m venv .venv<br/>.\\.venv\\Scripts\\Activate.ps1<br/>python -m pip install -r requirements.txt<br/>python main.py", CINZA_CLARO),
        h2("Configuração opcional do Gemini"),
        p("Criar .env na raiz com GEMINI_API_KEY=SUA_CHAVE_AQUI e GEMINI_MODEL=gemini-flash-latest. O arquivo está no .gitignore e não deve ser enviado. Sem configuração, o modo offline permanece totalmente funcional. Definir JOVI_DEMO_MODE=1 no .env ativa respostas Gemini simuladas (mesma validação de schema) para apresentar o modo híbrido sem depender de rede ou chave real."),
        h2("Roteiro de apresentação em 5 minutos"),
        tabela([
            ["Tempo", "Ação", "Mensagem-chave"],
            ["0:00-0:40", "Apresentar problema e ciclo", "Não é só IA: mede, prevê, verifica e aprende"],
            ["0:40-1:10", "Criar perfil", "Consentimento e histórico são individuais"],
            ["1:10-2:10", "Analisar exemplo_escuro.jpg", "Resumo simples e três alternativas"],
            ["2:10-3:10", "Comparar foto posterior", "Ganho real + avaliação alteram o peso"],
            ["3:10-4:10", "Menu 10: criar e processar solicitação", "Integração por arquivos com o app JOVI"],
            ["4:10-5:00", "Abrir data/perfis/perfil_&lt;id&gt;.json", "Persistência em JSON, isolada por perfil"],
        ], [2.0 * cm, 6.2 * cm, 9.4 * cm]),
        h2("Arquivos de demonstração"),
        bullet("samples/exemplo_escuro.jpg: provoca recomendações de luz, estabilidade e modo noturno."),
        bullet("samples/exemplo_borrado.jpg: evidencia perda de nitidez."),
        bullet("samples/exemplo_nitido.jpg: serve como cenário de recaptura melhorada."),
        bullet("integracao/exemplos/solicitacao_exemplo.json: modelo de solicitação que o app JOVI envia."),
        h2("Comando de teste"),
        callout("python -m unittest discover -s tests -v", CINZA_CLARO),
        PageBreak(),
    ])

    # 12
    story.extend([
        secao("12", "Pesquisa, limitações e conclusão"),
        h2("Fontes consultadas"),
        bullet('<link href="https://ai.google.dev/gemini-api/docs/image-understanding">Google AI - Gemini Image Understanding</link>: entrada multimodal e limitações.'),
        bullet('<link href="https://ai.google.dev/gemini-api/docs/structured-output">Google AI - Structured Outputs</link>: respostas guiadas por JSON Schema.'),
        bullet('<link href="https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash">Google AI - Gemini 2.5 Flash</link>: ficha da familia Flash que motivou a escolha (o projeto usa o alias gemini-flash-latest para acompanhar a versão recomendada atual).'),
        bullet('<link href="https://developer.android.com/media/camera/camera-extensions">Android Developers - Camera Extensions</link>: modos Auto, Night, HDR e Bokeh.'),
        bullet('<link href="https://support.google.com/pixelcamera/answer/2838995">Pixel Camera Help - Camera Coach</link>: orientação contextual e dependência de rede.'),
        bullet('<link href="https://www.reddit.com/r/photography/comments/jeysrk">r/photography - limites do Night Mode</link>: expectativas e restrições físicas.'),
        bullet('<link href="https://www.reddit.com/r/GalaxyS21/comments/qxj2g3">r/GalaxyS21 - sugestões de câmera</link>: demanda comunitária por controles e automação.'),
        h2("Limitações conhecidas"),
        bullet("Limiares de imagem são heurísticos e devem ser calibrados com um conjunto maior de fotos."),
        bullet("A pontuação depende do contexto informado e não representa valor artístico universal."),
        bullet("O Gemini pode produzir inferências incorretas; por isso sua resposta é opcional e filtrada."),
        bullet("As prévias não simulam fenômenos ópticos complexos nem substituem uma nova captura."),
        bullet("O protótipo roda no terminal e não controla diretamente o hardware de câmera JOVI."),
        h2("Próximos passos"),
        p("Uma evolução comercial poderia levar o motor para o aplicativo da câmera, usar CameraX para consultar extensões disponíveis, exibir orientações no visor, coletar feedback com consentimento e aplicar aprendizado federado ou sincronização criptografada."),
        h2("Conclusão"),
        p("O JOVI AI LensLab cumpre os requisitos da Sprint 4: persiste os dados em arquivos JSON, consome a API Gemini, valida entradas e trata exceções, e se integra ao restante da solução NextFrame trocando arquivos JSON com o app da câmera. A inovação continua defensável: recomendações fotográficas explicáveis, testadas por recaptura e personalizadas com aprendizado isolado por usuário."),
        Spacer(1, 0.4 * cm),
        callout("Síntese: a Sprint 2 dizia qual modo experimentar. A Sprint 3 mostrou por que experimentar e aprendeu com o resultado. A Sprint 4 guarda esse aprendizado em JSON e o entrega ao app da câmera."),
    ])

    doc = Documento(DESTINO)
    doc.build(story)
    return DESTINO


if __name__ == "__main__":
    print(construir())
