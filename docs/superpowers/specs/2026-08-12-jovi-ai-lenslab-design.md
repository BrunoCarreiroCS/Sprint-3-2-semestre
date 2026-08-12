# Especificacao de Design - NextFrame JOVI AI LensLab

**Status:** aprovada em conversa, aguardando revisao do documento  
**Data:** 12/08/2026  
**Disciplina:** Computational Thinking with Python - Sprint 3  
**Equipe:** NextFrame  
**Integrantes:** Bruno Carreiro, Daniel Graciano, Gustavo Romero, Leonardo Porto e Leonardo Gomes

## 1. Resumo executivo

O NextFrame JOVI AI LensLab evolui o Camera Assistant da Sprint 2 para um tutor fotografico multimodal, explicavel e adaptativo. O sistema analisa uma fotografia com duas fontes independentes: metricas calculadas localmente em Python e interpretacao semantica fornecida pela API Gemini. Em seguida, cruza as evidencias, simula alternativas do tipo "E se?", recomenda a menor intervencao util e verifica o resultado por meio de uma nova fotografia.

O diferencial da solucao nao e apenas utilizar IA. A aplicacao audita a resposta da IA com medidas objetivas, compara o resultado antes e depois e aprende separadamente quais orientacoes funcionam para cada usuario.

## 2. Contexto da Sprint 2

A Sprint 2 possui um programa de terminal concentrado em `main.py`, com sete funcionalidades. Ele recomenda modos da camera JOVI a partir de perfil, objetivo, ambiente e nivel de experiencia, registra usos, exibe catalogo, gera diagnostico, mantem historico em memoria e apresenta um relatorio simples.

Pontos preservados:

- menu numerico e retorno ao menu principal;
- validacao de entradas;
- funcoes com parametros e retornos;
- listas e dicionarios;
- recomendacao de modos JOVI;
- interface textual clara;
- alinhamento com descoberta e uso de recursos da camera.

Limitacoes que motivam a Sprint 3:

- recomendacoes baseadas apenas em respostas manuais;
- arvore fixa de regras;
- historico perdido ao encerrar o programa;
- ausencia de perfis persistentes;
- nenhuma verificacao de que uma dica melhorou a fotografia;
- falta de distincao entre evidencia medida, inferencia e preferencia pessoal.

## 3. Objetivos

### 3.1 Objetivo geral

Construir uma aplicacao de terminal em Python que analise fotografias, explique problemas tecnicos e visuais, simule intervencoes, verifique recapturas e personalize recomendacoes por usuario.

### 3.2 Objetivos especificos

- medir caracteristicas tecnicas da fotografia localmente;
- interpretar assunto, cena, intencao e composicao com IA multimodal;
- validar o formato e a consistencia da resposta da API;
- separar fatos medidos de inferencias da IA;
- produzir ate tres alternativas contrafactuais;
- explicar beneficio, risco, esforco e confianca de cada alternativa;
- comparar fotografia original e recaptura;
- atualizar o aprendizado somente com sinais controlados;
- persistir perfis e historicos individualizados em SQLite;
- continuar funcional quando a API estiver indisponivel;
- atender explicitamente a rubrica da Sprint 3.

## 4. Fora de escopo

- captura de video ou camera ao vivo;
- treinamento de rede neural propria;
- reconhecimento da identidade de pessoas;
- armazenamento de biometria;
- avaliacao absoluta de beleza ou valor artistico;
- edicao generativa usada como prova de melhoria;
- dependencia obrigatoria de OpenAI ou de um modelo local pesado;
- sincronizacao em nuvem entre computadores;
- interface grafica nesta Sprint.

## 5. Abordagens consideradas

### 5.1 Somente regras e visao computacional local

Tem baixo risco e funciona offline, mas nao compreende bem assunto, intencao ou composicao sem modelos especializados.

### 5.2 Somente IA multimodal

Produz analises ricas rapidamente, mas terceiriza a logica principal, dificulta a avaliacao dos conceitos de Python e fica vulneravel a respostas inconsistentes e falhas de rede.

### 5.3 Arquitetura hibrida - escolhida

Combina medidas locais, Gemini, regras explicaveis, SQLite e verificacao antes/depois. E a opcao escolhida por equilibrar inovacao, demonstracao academica, transparencia e resiliencia.

## 6. Arquitetura

```text
Usuario e menu
      |
      v
Analise local --------> Metricas objetivas
      |                         |
      |                         v
      +----> Gemini ------> Analise semantica estruturada
                                |
                +---------------+
                v
          Motor de evidencias
                |
                v
       Simulador contrafactual
                |
                v
    Recomendacao personalizada
                |
                v
       Recaptura e comparacao
                |
                v
      Aprendizado individual
                |
                v
             SQLite
```

## 7. Componentes

### `main.py`

Exibe o menu, controla a sessao e chama os servicos. Nao contem regras extensas de analise ou SQL.

### `database.py`

Cria o banco, executa transacoes, converte registros em dicionarios e oferece funcoes para usuarios, analises, recomendacoes, comparacoes e pesos.

### `image_analyzer.py`

Valida arquivos, remove orientacao incorreta via EXIF, calcula metricas locais e cria uma copia reduzida e sem metadados para a API.

### `gemini_client.py`

Le `GEMINI_API_KEY`, envia a imagem preparada, solicita JSON estruturado, valida campos e traduz falhas externas para erros compreensiveis pelo programa.

### `recommendation_engine.py`

Cruza metricas, resposta semantica, intencao declarada e pesos do usuario. Classifica evidencias e gera o ranking de intervencoes.

### `learning_engine.py`

Compara resultado previsto e obtido, atualiza pesos dentro de limites e calcula a evolucao do usuario.

### `reports.py`

Formata historico, comparacao antes/depois, perfil fotografico e relatorio final.

### `validators.py`

Centraliza entradas numericas, texto nao vazio, confirmacoes, caminhos, formatos e limites.

## 8. Menu principal

```text
1 - Criar ou trocar perfil
2 - Analisar uma fotografia
3 - Explorar simulacoes "E se?"
4 - Comparar foto antes e depois
5 - Avaliar uma recomendacao
6 - Ver historico de analises
7 - Ver evolucao fotografica
8 - Recomendar modo sem fotografia
9 - Gerenciar meus dados
0 - Sair
```

O programa retorna ao menu apos cada funcionalidade. A opcao de analise exige um perfil ativo. Quando nao houver perfil, o programa direciona o usuario para criacao ou selecao.

## 9. Fluxos principais

### 9.1 Criacao de perfil

1. Solicitar apelido unico e nivel inicial.
2. Validar campos e consentimentos.
3. Criar pesos padrao.
4. Tornar o perfil ativo.

Nao sera exigido nome real. Um PIN fica fora do escopo inicial porque o banco e local e nao armazena fotografias; pode ser adicionado futuramente.

### 9.2 Analise de fotografia

1. Solicitar caminho do arquivo.
2. Validar existencia, formato, tamanho e leitura.
3. Perguntar objetivo, intencao e preferencia de estilo.
4. Calcular metricas locais.
5. Pedir consentimento para analise externa quando necessario.
6. Preparar copia reduzida e sem metadados.
7. Consultar Gemini ou ativar modo offline.
8. Validar resposta estruturada.
9. Cruzar evidencias.
10. Calcular pontuacao contextual.
11. Gerar ate tres intervencoes ranqueadas.
12. Persistir analise e recomendacoes.
13. Apagar arquivo temporario.

### 9.3 Simulacao "E se?"

Para cada intervencao, o sistema apresenta:

- acao;
- problema que pretende resolver;
- ganho previsto em pontos;
- risco ou efeito colateral;
- esforco: baixo, medio ou alto;
- evidencia local;
- evidencia semantica;
- confianca: baixa, media ou alta;
- motivo de nao escolher alternativas concorrentes.

As previsoes sao estimativas educacionais e sao rotuladas dessa forma.

### 9.4 Recaptura verificada

1. Selecionar uma analise anterior e uma recomendacao aplicada.
2. Informar a nova fotografia.
3. Repetir analise local e, quando autorizado, semantica.
4. Comparar metricas equivalentes e adequacao a intencao.
5. Calcular ganho real.
6. Pedir avaliacao de 1 a 5 e comentario opcional.
7. Registrar sucesso, resultado misto ou falha.
8. Atualizar o peso contextual.

### 9.5 Modo sem fotografia

Preserva a principal funcionalidade da Sprint 2. Perfil, objetivo, ambiente, movimento e nivel alimentam o mesmo motor de recomendacao, mas com confianca menor por nao haver evidencia visual.

## 10. Analise local

As metricas iniciais serao:

- brilho medio em escala de 0 a 100;
- contraste global pela dispersao de luminancia;
- nitidez aproximada pela variancia do Laplaciano;
- saturacao media;
- percentual de sombras recortadas;
- percentual de realces estourados;
- largura, altura, proporcao e quantidade de pixels;
- orientacao e metadados EXIF disponiveis;
- ISO, exposicao e distancia focal quando existentes.

O arquivo de entrada tera limite inicial de 20 MB e resolucao minima de 320 x 240 pixels. A copia temporaria enviada a API tera no maximo 1600 pixels no maior lado. Esses limites serao constantes nomeadas e cobertas por testes.

Os limiares tecnicos nao serao apresentados como verdades universais. A pontuacao sera contextual: baixa luminosidade pode ser penalizada em documento e aceita em uma intencao dramatica.

## 11. Contrato da IA

O Gemini deve responder a um esquema JSON com os seguintes grupos:

```json
{
  "assunto_principal": "pessoa",
  "tipo_cena": "retrato_noturno",
  "intencao_percebida": "registro_espontaneo",
  "movimento_percebido": true,
  "problemas": [
    {
      "codigo": "sujeito_borrado",
      "confianca": 0.88,
      "evidencia_visual": "contornos faciais pouco definidos"
    }
  ],
  "composicao": {
    "pontuacao": 71,
    "observacao": "sujeito muito centralizado"
  },
  "acoes_sugeridas": [
    "adicionar_iluminacao",
    "reduzir_exposicao",
    "evitar_zoom_digital"
  ],
  "incertezas": []
}
```

Codigos aceitos serao controlados pelo programa. Campos ausentes, tipos incorretos, confianca fora de 0 a 1 ou codigos desconhecidos nao entram diretamente no motor de decisao.

## 12. Motor de evidencias

Regras de fusao:

- afirmacoes tecnicas mensuraveis usam a metrica local como fonte primaria;
- assunto, contexto e composicao usam Gemini como fonte semantica;
- concordancia entre fontes aumenta confianca;
- conflito reduz confianca e deve ser mostrado ao usuario;
- intencao declarada pelo usuario tem prioridade sobre intencao inferida;
- nenhuma recomendacao depende apenas de uma frase livre da IA;
- modo offline substitui evidencias semanticas por perguntas adicionais.

Classificacao:

- **confirmada:** fontes compativeis e dados suficientes;
- **provavel:** uma fonte forte sem contradicao;
- **incerta:** evidencia fraca, ausente ou conflitante.

## 13. Pontuacao e simulacao

A pontuacao geral varia de 0 a 100 e e formada por dimensoes independentes: exposicao, nitidez, contraste, cor, resolucao e adequacao a intencao. O relatorio sempre exibe as dimensoes, evitando esconder o resultado em um unico numero.

Pesos iniciais, em porcentagem:

| Objetivo | Exposicao | Nitidez | Contraste | Cor | Resolucao | Intencao |
|---|---:|---:|---:|---:|---:|---:|
| Documento | 20 | 30 | 20 | 10 | 15 | 5 |
| Pessoa ou retrato | 20 | 25 | 15 | 15 | 10 | 15 |
| Paisagem | 20 | 20 | 20 | 20 | 10 | 10 |
| Produto | 25 | 25 | 20 | 15 | 10 | 5 |
| Redes sociais | 15 | 20 | 15 | 20 | 10 | 20 |
| Outro | 20 | 20 | 15 | 15 | 10 | 20 |

Cada linha soma 100. Dimensoes indisponiveis sao redistribuidas proporcionalmente entre as dimensoes calculadas, e o relatorio informa a ausencia. A adequacao a intencao usa respostas estruturadas e regras controladas, nao texto livre.

Cada acao possui efeitos esperados e riscos cadastrados em dicionarios. O ganho previsto combina:

- deficit que a acao consegue tratar;
- adequacao ao contexto;
- conflito com outros objetivos;
- peso aprendido para usuario e contexto;
- confianca das evidencias.

O ranking favorece a menor intervencao com ganho relevante. "Modo Noturno" nao vence automaticamente em baixa luz quando houver movimento, pois exposicao prolongada pode aumentar o borrao.

## 14. Aprendizado individualizado

O aprendizado e uma adaptacao de pesos, nao o treinamento de uma rede neural.

Contexto resumido:

```text
objetivo + faixa de luz + movimento + nivel + estilo
```

Cada combinacao contexto/acao inicia com peso `1.00`, limitado ao intervalo `0.50` a `1.50`.

Atualizacao:

- recaptura com ganho real de pelo menos 5 pontos e avaliacao de 3 a 5: `+0.10`;
- ganho inferior a 5, mas avaliacao 4 ou 5: `+0.03`;
- piora de pelo menos 5 pontos ou avaliacao 1 ou 2: `-0.10`;
- resultado inconclusivo: nenhuma alteracao;
- uma atualizacao por comparacao.

O ganho real tem prioridade sobre a opiniao. Quando os dois sinais divergem, a alteracao e pequena ou nula. Os limites impedem que poucas interacoes dominem o sistema.

## 15. Banco de dados

Arquivo local: `data/jovi.db`.

### `usuarios`

- `id` inteiro, chave primaria;
- `apelido` texto unico;
- `nivel` texto validado;
- `estilo_preferido` texto validado;
- `consentimento_api` booleano;
- `criado_em` data/hora.

### `analises`

- `id` inteiro, chave primaria;
- `usuario_id` chave estrangeira com exclusao em cascata;
- `imagem_hash` identificador sem caminho completo;
- `nome_arquivo` apenas nome base;
- `objetivo`, `intencao` e `estilo`;
- `modo_execucao`: hibrido ou offline;
- `metricas_json`;
- `analise_ia_json`, podendo ser nulo;
- `pontuacao_geral`;
- `criado_em`.

### `recomendacoes`

- `id` inteiro, chave primaria;
- `analise_id` chave estrangeira com exclusao em cascata;
- `codigo_acao`;
- `posicao_ranking`;
- `ganho_previsto`;
- `risco`, `esforco`, `confianca` e `explicacao`;
- `selecionada` booleano.

### `comparacoes`

- `id` inteiro, chave primaria;
- `usuario_id` chave estrangeira com exclusao em cascata;
- `analise_antes_id` e `analise_depois_id`;
- `recomendacao_id`;
- `ganho_real`;
- `resultado`;
- `avaliacao` de 1 a 5;
- `comentario` opcional;
- `criado_em`.

### `pesos_aprendizado`

- `id` inteiro, chave primaria;
- `usuario_id` chave estrangeira com exclusao em cascata;
- `contexto_chave`;
- `codigo_acao`;
- `peso`;
- `sucessos`, `falhas` e `atualizado_em`;
- restricao unica por usuario, contexto e acao.

SQLite usara chaves estrangeiras, transacoes e consultas parametrizadas. Linhas consultadas serao convertidas em dicionarios para uso nas regras.

## 16. Privacidade e seguranca

- a chave e lida apenas de `GEMINI_API_KEY`;
- `.env` e ignorado pelo Git e nunca entra no ZIP;
- `.env.example` contem somente o nome da variavel;
- a foto original nao e modificada;
- a copia enviada e reduzida, reprocessada e sem EXIF/GPS;
- arquivos temporarios sao removidos mesmo apos erro;
- o banco nao guarda a fotografia;
- o usuario pode revogar consentimento, exportar resumo e excluir perfil;
- exclusao de perfil remove registros relacionados em transacao;
- mensagens e logs nunca exibem a chave;
- somente fotografias de teste nao sensiveis devem ser usadas na apresentacao.

## 17. Tratamento de erros

### Arquivo

Validar existencia, permissao, extensao JPG/JPEG/PNG/WEBP, tamanho maximo configuravel, resolucao minima e integridade. O erro nao encerra a aplicacao.

### API

Tratar chave ausente, autenticacao, quota, timeout, rede, bloqueio de seguranca, resposta vazia e JSON invalido. Apos uma tentativa curta, ativar modo offline; nao repetir chamadas indefinidamente.

### Banco

Usar transacoes, rollback em falhas e mensagens claras. A inicializacao cria tabelas ausentes. Corrupcao ou versao desconhecida nao deve sobrescrever dados silenciosamente.

### Aprendizado

Ignorar comparacoes pertencentes a outro usuario, recomendacoes nao relacionadas e duplicidade. Validar limites antes de atualizar pesos.

## 18. Simulacoes visuais

Pillow e OpenCV podem gerar copias demonstrativas de brilho, contraste, saturacao e nitidez, alem de sobreposicoes de recorte e enquadramento. Todas recebem marca visual de "SIMULACAO" e nome diferente. A fotografia original nunca e sobrescrita.

Essas imagens ajudam o usuario a entender uma intervencao, mas nao sao utilizadas como recaptura valida nem como prova de ganho.

## 19. Dependencias

- Python 3.11 ou superior;
- `Pillow` para leitura, EXIF e simulacoes;
- `opencv-python` para metricas e processamento;
- SDK oficial `google-genai` para Gemini;
- `sqlite3`, `json`, `hashlib`, `pathlib`, `tempfile`, `datetime` e `unittest` da biblioteca padrao.

Versoes serao fixadas em `requirements.txt`. O modelo padrao sera `gemini-2.5-flash`, selecionado por aceitar imagens e estar disponivel na camada gratuita consultada em agosto de 2026. A variavel opcional `GEMINI_MODEL` permitira troca sem alteracao do codigo caso a disponibilidade da conta mude.

## 20. Testes

### Unitarios

- validadores;
- metricas com imagens controladas;
- pontuacao por objetivo;
- fusao de evidencias;
- ranking contrafactual;
- atualizacao e limites dos pesos;
- separacao entre usuarios;
- conversao de registros em dicionarios;
- validacao do JSON da IA.

### Integracao

- banco temporario completo;
- analise com resposta Gemini simulada;
- timeout e fallback offline;
- fluxo antes/depois;
- exclusao de perfil em cascata;
- limpeza de arquivo temporario.

### Teste real opcional

Uma fotografia de demonstracao consulta a API quando `GEMINI_API_KEY` estiver disponivel. Esse teste nao integra a suite automatica padrao e nao e necessario para validar o modo offline.

### Imagens de teste

O repositorio tera imagens controladas ou geradas para representar cena clara, escura, desfocada, baixo contraste, saturacao excessiva e referencia equilibrada. Elas nao conterao dados pessoais.

## 21. Criterios de aceite

- menu possui as funcionalidades planejadas e opcao de saida;
- toda funcionalidade retorna ao menu;
- entradas invalidas sao repetidas ou canceladas sem encerrar o programa;
- dois perfis nao compartilham historico nem pesos;
- analise local funciona sem internet e sem chave;
- resposta da IA e validada antes de afetar recomendacoes;
- conflitos entre metrica e IA sao visiveis;
- cada simulacao apresenta ganho, risco, esforco e confianca;
- comparacao antes/depois atualiza somente o peso correto;
- nenhuma simulacao editada e aceita como recaptura;
- exclusao de perfil remove seus registros;
- chave e fotos pessoais nao aparecem no repositorio ou ZIP;
- testes automatizados principais passam;
- documentacao distingue medicao, inferencia e previsao;
- PDF explica o que foi removido, modificado e adicionado desde a Sprint 2.

## 22. Estrutura planejada da entrega

```text
jovi-ai-lenslab/
|-- main.py
|-- database.py
|-- image_analyzer.py
|-- gemini_client.py
|-- recommendation_engine.py
|-- learning_engine.py
|-- reports.py
|-- validators.py
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
|-- data/
|-- output/
|-- tests/
|-- docs/
|   `-- documentacao_sprint3.pdf
`-- samples/
```

O ZIP final tera codigo-fonte, PDF, README, dependencias e amostras nao sensiveis. Nao tera ambiente virtual, cache, banco pessoal, chave ou fotografias privadas.

## 23. Mudancas em relacao a Sprint 2

### Mantido

- proposta NextFrame/JOVI;
- uso pelo terminal;
- recomendacao de modos;
- menu, validacoes, funcoes, listas e dicionarios;
- modo sem fotografia como continuidade funcional.

### Modificado

- historico temporario passa a ser persistente e individualizado;
- regras fixas passam a integrar pontuacao contextual e evidencias;
- relatorio simples passa a mostrar evolucao verificavel;
- diagnostico por questionario passa a combinar fotografia e intencao;
- codigo monolitico passa a ser dividido por responsabilidade.

### Adicionado

- analise tecnica real;
- Gemini multimodal;
- validacao estruturada da IA;
- simulador contrafactual;
- comparacao antes/depois;
- aprendizado por usuario;
- SQLite;
- privacidade e modo offline;
- testes automatizados;
- simulacoes visuais educativas.

### Removido

- armazenamento exclusivamente em memoria;
- conclusoes tecnicas baseadas apenas em perguntas;
- recomendacao automatica de Modo Noturno somente porque o ambiente e escuro;
- catalogo local duplicado dentro de uma funcao unica.

## 24. Evidencias externas que orientam o design

- Android Camera Extensions: modos automaticos, HDR, Bokeh e Night: <https://developer.android.com/media/camera/camera-extensions>
- Google Pixel Camera Coach: orientacao contextual de fotografia: <https://blog.google/products-and-platforms/devices/pixel/how-to-use-camera-coach/>
- Google Guided Frame: enquadramento assistido e acessibilidade: <https://support.google.com/pixelcamera/answer/14110054?hl=en>
- Samsung Shot Suggestions: orientacao de composicao: <https://www.samsung.com/uk/support/mobile-devices/how-to-use-shot-suggestions/>
- Gemini Image Understanding: <https://ai.google.dev/gemini-api/docs/image-understanding>
- Gemini Structured Outputs: <https://ai.google.dev/gemini-api/docs/generate-content/structured-output>
- Pillow ImageStat: <https://pillow.readthedocs.io/en/stable/reference/ImageStat.html>
- OpenCV Laplacian: <https://docs.opencv.org/4.12.0/d5/db5/tutorial_laplace_operator.html>
- Counterfactual Explainable Recommendation: <https://arxiv.org/abs/2108.10539>
- User-Controllable Recommendation via Counterfactual Explanations: <https://arxiv.org/abs/2308.00894>

## 25. Sequencia de implementacao em alto nivel

1. Base do projeto, configuracao e validadores.
2. SQLite e perfis.
3. Analise local e imagens controladas.
4. Motor de pontuacao e modo offline.
5. Integracao Gemini e contrato estruturado.
6. Fusao de evidencias e simulacoes.
7. Comparacao antes/depois e aprendizado.
8. Relatorios e gestao de dados.
9. Testes, refinamento da interface e documentacao.

O detalhamento em tarefas pequenas, arquivos, testes e comandos sera criado em um plano de implementacao separado somente apos a revisao desta especificacao.
