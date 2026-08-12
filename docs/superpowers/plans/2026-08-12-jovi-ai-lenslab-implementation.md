# Plano de Implementacao - NextFrame JOVI AI LensLab

**Data:** 12/08/2026  
**Base:** `docs/superpowers/specs/2026-08-12-jovi-ai-lenslab-design.md`  
**Estado:** pronto para revisao e aprovacao  
**Estrategia:** incrementos pequenos, testes primeiro e modo offline sempre funcional

## 1. Resultado esperado

Ao final, o repositorio tera uma aplicacao Python de terminal capaz de:

- manter perfis separados em SQLite;
- analisar uma foto com Pillow e OpenCV;
- consultar Gemini quando houver consentimento, chave e internet;
- validar a resposta da IA antes de utiliza-la;
- combinar medidas, contexto e historico;
- gerar tres alternativas do tipo "E se?";
- comparar foto original e recaptura;
- aprender pesos separados por usuario;
- funcionar em modo offline;
- gerar historico e relatorio de evolucao;
- passar por testes automatizados;
- ser entregue com README, PDF e ZIP sem segredos ou dados pessoais.

## 2. Decisoes de execucao

### 2.1 Estrutura

Os modulos permanecerao na raiz para facilitar a leitura academica:

```text
main.py
config.py
validators.py
database.py
image_analyzer.py
gemini_client.py
recommendation_engine.py
learning_engine.py
reports.py
```

Os testes ficarao em `tests/` e usarao `unittest`. O codigo compartilhara dados por dicionarios simples, evitando uma arquitetura excessivamente abstrata para a disciplina.

### 2.2 Desenvolvimento orientado por testes

Para cada nucleo:

1. escrever um teste que falha pela ausencia do comportamento;
2. executar apenas esse teste e confirmar a falha esperada;
3. implementar o minimo necessario;
4. executar novamente e confirmar sucesso;
5. executar a suite completa;
6. revisar nomes, mensagens e duplicacao;
7. criar um commit pequeno.

### 2.3 Comandos padrao

Depois da criacao do ambiente virtual:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile main.py config.py validators.py database.py image_analyzer.py gemini_client.py recommendation_engine.py learning_engine.py reports.py
.\.venv\Scripts\python.exe main.py
```

O teste real da API sera separado:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gemini_live -v
```

Ele sera ignorado automaticamente quando `GEMINI_API_KEY` estiver ausente.

## 3. Marcos de entrega

| Marco | Resultado demonstravel |
|---|---|
| M1 | Projeto inicia, valida entradas e exibe menu |
| M2 | Perfis persistem e nunca misturam dados |
| M3 | Fotos sao validadas e analisadas localmente |
| M4 | Recomendacoes offline e simulacoes funcionam |
| M5 | Gemini enriquece a analise com fallback seguro |
| M6 | Recaptura comprova resultado e atualiza aprendizado |
| M7 | Historico, relatorios, privacidade e simulacoes visuais completos |
| M8 | Documentacao, demonstracao e ZIP final validados |

## 4. Tarefas detalhadas

### Tarefa 1 - Preparar a base segura do projeto

**Arquivos a criar:**

- `.gitignore`
- `.env.example`
- `requirements.txt`
- `config.py`
- `README.md`
- `tests/__init__.py`
- `tests/test_config.py`
- `data/.gitkeep`
- `output/.gitkeep`
- `samples/.gitkeep`

**Testes primeiro:**

- confirmar que `config.py` retorna caminhos absolutos dentro do projeto;
- confirmar limites de 20 MB, 320 x 240 e 1600 pixels;
- confirmar modelo padrao `gemini-2.5-flash`;
- confirmar que `GEMINI_MODEL` pode sobrescrever somente o nome do modelo;
- confirmar que a chave ausente resulta em `None`, sem excecao.

**Implementacao:**

- criar o ambiente com `python -m venv .venv`;
- atualizar `pip` dentro do ambiente;
- instalar Pillow, OpenCV e `google-genai` somente no ambiente virtual;
- centralizar constantes e caminhos em `config.py`;
- criar pastas com `Path.mkdir(..., exist_ok=True)` na inicializacao;
- adicionar ao `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `data/*.db`, `output/*`, temporarios e caches;
- manter `.gitkeep` permitido;
- documentar a criacao do ambiente virtual sem incluir chave real;
- instalar dependencias e fixar as versoes realmente verificadas.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_config -v
git diff --check
```

**Criterio de conclusao:** configuracao importavel, nenhum segredo versionado e teste verde.

---

### Tarefa 2 - Criar validadores reutilizaveis

**Arquivos:**

- criar `validators.py`
- criar `tests/test_validators.py`

**Testes primeiro:**

- `validar_texto` rejeita vazio e remove espacos;
- `validar_escolha` aceita apenas opcoes cadastradas;
- `validar_inteiro` respeita limites inclusivos;
- `normalizar_sim_nao` aceita variacoes previstas e rejeita outras;
- `validar_caminho_imagem` rejeita inexistente, pasta, extensao invalida e arquivo acima do limite;
- funcoes puras retornam valor ou erro claro, sem chamar `input()` internamente;
- um adaptador interativo repete a pergunta sem recursao.

**Implementacao:**

- separar validacao pura da coleta com `input()`;
- utilizar parametros e retornos em todas as funcoes;
- manter listas de opcoes e mensagens em estruturas explicitas;
- permitir cancelamento com `0` nos fluxos longos.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_validators -v
```

**Criterio de conclusao:** entradas invalidas nao causam encerramento nem loop sem saida.

---

### Tarefa 3 - Implementar SQLite e isolamento de perfis

**Arquivos:**

- criar `database.py`
- criar `tests/test_database.py`

**Testes primeiro:**

- inicializacao cria as cinco tabelas e seus indices;
- `PRAGMA foreign_keys = ON` esta ativo em toda conexao;
- apelido duplicado e rejeitado;
- criar, listar, buscar e atualizar usuario;
- registrar analise com dicionarios serializados em JSON;
- registrar varias recomendacoes em uma unica transacao;
- buscar historico retorna apenas o usuario solicitado;
- excluir perfil remove dados relacionados em cascata;
- consultas usam parametros;
- falha no meio da transacao executa rollback;
- linha SQLite e convertida para dicionario.

**Implementacao:**

- criar funcao `conectar(caminho_banco)` com `sqlite3.Row`;
- criar `inicializar_banco` idempotente;
- implementar operacoes por responsabilidade, sem SQL no menu;
- serializar JSON com UTF-8 preservado;
- criar restricao unica em `(usuario_id, contexto_chave, codigo_acao)`;
- criar campo de controle para impedir atualizacao duplicada de uma comparacao;
- verificar que analises antes/depois e recomendacao pertencem ao mesmo usuario antes de gravar comparacao.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_database -v
```

**Criterio de conclusao:** dois usuarios com dados semelhantes continuam totalmente isolados.

---

### Tarefa 4 - Analisar imagens localmente

**Arquivos:**

- criar `image_analyzer.py`
- criar `tests/test_image_analyzer.py`
- criar `tests/fixtures.py`
- gerar amostras controladas em `samples/`

**Testes primeiro:**

- imagem clara tem brilho maior que imagem escura;
- imagem desfocada tem nitidez menor que referencia;
- baixo contraste tem dispersao menor;
- saturacao forte tem indice maior;
- sombras e realces estourados sao contados corretamente;
- resolucao e proporcao sao retornadas;
- EXIF ausente nao causa erro;
- imagem pequena e corrompida sao rejeitadas;
- hash e estavel para o mesmo arquivo;
- copia para API respeita 1600 pixels, remove EXIF e usa pasta temporaria;
- arquivo temporario e apagado mesmo quando ocorre excecao.

**Implementacao:**

- abrir e verificar com Pillow;
- aplicar `ImageOps.exif_transpose`;
- converter para matrizes OpenCV;
- calcular brilho, contraste, nitidez, saturacao, clipping e dimensoes;
- normalizar indicadores para dicionario serializavel;
- extrair somente EXIF tecnico permitido: ISO, exposicao e distancia focal;
- nunca extrair nem persistir GPS;
- gerar `sha256` do conteudo apenas para identificacao;
- usar gerenciador de contexto para copia segura da API.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_image_analyzer -v
```

**Criterio de conclusao:** todas as imagens controladas produzem ordenacoes coerentes e repetiveis.

---

### Tarefa 5 - Construir pontuacao contextual e modo offline

**Arquivos:**

- criar `recommendation_engine.py`
- criar `tests/test_recommendation_engine.py`

**Testes primeiro:**

- cada linha de pesos por objetivo soma 100;
- pontuacoes ficam entre 0 e 100;
- dimensao ausente redistribui peso corretamente;
- documento prioriza nitidez e contraste;
- intencao dramatica reduz penalidade de pouca luz;
- baixa luz com sujeito parado pode recomendar Modo Noturno;
- baixa luz com movimento penaliza exposicao prolongada;
- tres alternativas tem codigos diferentes e ranking deterministico;
- cada alternativa possui ganho, risco, esforco, confianca e evidencias;
- peso individual altera ranking sem ultrapassar limites;
- modo sem foto retorna confianca menor;
- conflito entre evidencias reduz confianca.

**Implementacao:**

- cadastrar pesos por objetivo em dicionarios;
- cadastrar acoes, efeitos e riscos em dicionarios de dominio;
- criar funcoes puras para pontuar dimensoes;
- criar `fundir_evidencias` com estados confirmada, provavel e incerta;
- criar `gerar_contexto_chave` com valores normalizados;
- criar `simular_intervencoes` e limitar saida a tres alternativas;
- adicionar explicacao de "por que esta" e "por que nao a outra";
- preservar a recomendacao manual da Sprint 2 por meio do mesmo motor.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_recommendation_engine -v
```

**Criterio de conclusao:** o modo offline entrega uma recomendacao completa, explicavel e sem API.

---

### Tarefa 6 - Integrar Gemini com contrato rigoroso

**Arquivos:**

- criar `gemini_client.py`
- criar `tests/test_gemini_client.py`
- criar `tests/test_gemini_live.py`

**Testes primeiro, usando cliente falso:**

- chave ausente retorna estado offline controlado;
- JSON valido e convertido em dicionario normalizado;
- campo obrigatorio ausente e rejeitado;
- confianca fora de 0 a 1 e rejeitada;
- codigo desconhecido e filtrado e registrado como incerteza;
- texto adicional fora do JSON nao e aceito;
- timeout, autenticacao, quota e bloqueio sao convertidos em categorias de erro;
- mensagem de erro nunca contem chave;
- apenas uma tentativa e realizada por analise;
- arquivo temporario e fechado e removido.

**Implementacao:**

- encapsular SDK `google-genai` em uma unica classe ou conjunto de funcoes;
- construir prompt com intencao declarada e pedido de evidencias observaveis;
- definir JSON Schema com codigos controlados;
- usar modelo configurado por `GEMINI_MODEL` ou `gemini-2.5-flash`;
- manter timeout curto e sem repeticao automatica ilimitada;
- retornar uma estrutura `sucesso/dados/erro`, em vez de imprimir dentro do cliente;
- registrar somente categoria e momento do erro;
- criar teste ao vivo marcado e ignorado sem chave.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gemini_client -v
.\.venv\Scripts\python.exe -m unittest tests.test_gemini_live -v
```

**Criterio de conclusao:** a aplicacao recebe dados previsiveis e cai para offline em qualquer falha externa.

---

### Tarefa 7 - Orquestrar a analise hibrida

**Arquivos:**

- criar `analysis_service.py`
- criar `tests/test_analysis_service.py`
- atualizar a estrutura documentada para incluir este servico

**Justificativa:** este modulo impede que `main.py` concentre validacao, imagem, API, recomendacao e persistencia.

**Testes primeiro:**

- fluxo com consentimento e API valida usa modo hibrido;
- sem consentimento nao chama cliente externo;
- sem chave nao chama API e usa offline;
- falha Gemini preserva metricas locais e gera recomendacao;
- analise e recomendacoes sao salvas atomicamente;
- o nome salvo nao contem caminho completo;
- dados da IA brutos invalidos nao chegam ao banco;
- temporario e removido em sucesso e falha.

**Implementacao:**

- criar `analisar_fotografia(...)` recebendo dependencias por parametro;
- executar analise local primeiro;
- preparar e consultar API somente se permitido;
- fundir evidencias, pontuar e simular;
- persistir resultado completo;
- retornar dicionario pronto para exibicao.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_analysis_service -v
```

**Criterio de conclusao:** uma unica chamada de servico executa o fluxo completo sem depender do terminal.

---

### Tarefa 8 - Implementar recaptura e aprendizado individual

**Arquivos:**

- criar `learning_engine.py`
- criar `tests/test_learning_engine.py`

**Testes primeiro:**

- ganho `>= 5` e avaliacao `3..5` aumenta `0.10`;
- ganho pequeno com avaliacao `4..5` aumenta `0.03`;
- piora `>= 5` reduz `0.10`;
- avaliacao `1..2` reduz conforme regra;
- sinais divergentes produzem alteracao pequena ou nula;
- peso nunca sai de `0.50..1.50`;
- comparacao duplicada nao atualiza duas vezes;
- usuario diferente e rejeitado;
- simulacao marcada nao pode ser recaptura;
- sucesso, misto, falha e inconclusivo sao classificados;
- progresso agrega somente dados do perfil ativo.

**Implementacao:**

- calcular deltas por dimensao e ganho geral;
- validar vinculo entre usuario, analise e recomendacao;
- aplicar regra de atualizacao em funcao pura;
- gravar comparacao e peso na mesma transacao;
- armazenar contadores de sucessos e falhas;
- gerar resumo de pontos fortes, dificuldade e acao mais eficaz.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_learning_engine -v
```

**Criterio de conclusao:** a mesma situacao pode produzir rankings diferentes para usuarios com historicos diferentes.

---

### Tarefa 9 - Criar simulacoes visuais educativas

**Arquivos:**

- ampliar `image_analyzer.py`
- criar `tests/test_simulations.py`

**Testes primeiro:**

- simulacao nunca usa o mesmo caminho da original;
- original permanece byte a byte igual;
- saida contem marca `SIMULACAO` visivel;
- brilho, contraste, saturacao e nitidez mudam apenas a copia;
- overlay de recorte nao altera proporcao sem solicitacao;
- metadado interno ou padrao de nome identifica a imagem como nao elegivel para recaptura;
- diretorio de saida e criado com seguranca.

**Implementacao:**

- usar Pillow para ajustes e texto;
- usar OpenCV apenas quando agregar valor ao overlay;
- salvar em `output/simulacoes/<usuario_id>/` com identificador seguro;
- manter um manifesto no banco ou nome controlado para impedir uso como recaptura;
- rotular previsao como educativa.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_simulations -v
```

**Criterio de conclusao:** usuario consegue visualizar a ideia sem confundir edicao com resultado real.

---

### Tarefa 10 - Construir relatorios e gestao de dados

**Arquivos:**

- criar `reports.py`
- criar `tests/test_reports.py`

**Testes primeiro:**

- historico vazio mostra mensagem apropriada;
- historico lista somente perfil ativo;
- relatorio distingue medida, IA e previsao;
- evolucao calcula medias sem divisao por zero;
- comparacao apresenta dimensoes antes/depois e delta;
- exportacao omite chave e caminhos completos;
- exclusao pede confirmacao textual forte e remove tudo em transacao;
- revogacao de consentimento impede chamadas futuras.

**Implementacao:**

- retornar linhas/texto de relatorio em funcoes puras;
- criar exportacao JSON de resumo em `output/exportacoes/`;
- criar gestao de consentimento;
- criar exclusao de perfil e seus artefatos gerados;
- formatar tabelas ASCII de largura controlada.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_reports -v
```

**Criterio de conclusao:** usuario entende historico e pode controlar seus dados.

---

### Tarefa 11 - Montar menu e experiencia completa

**Arquivos:**

- criar `main.py`
- criar `tests/test_main.py`

**Testes primeiro:**

- menu possui opcoes `0..9`;
- opcao invalida repete;
- toda funcionalidade retorna ao menu;
- `0` encerra com mensagem;
- analise sem perfil orienta criacao/selecao;
- troca de perfil altera contexto ativo;
- excecao conhecida vira mensagem clara;
- segredo e stack trace nao aparecem na interface;
- `main()` nao executa durante importacao.

**Implementacao:**

- criar uma funcao por fluxo de menu;
- manter sessao com `usuario_ativo` simples;
- injetar conexao/servicos quando possivel para testar;
- exibir etiquetas `MEDIDO`, `IA`, `PREVISTO` e `VERIFICADO`;
- usar navegacao numerica consistente;
- oferecer cancelamento antes de API, exclusao e operacoes longas;
- preservar linguagem clara em portugues.

**Teste manual obrigatorio:**

```text
criar Bruno -> analisar offline -> ver simulacoes -> criar Daniel
-> confirmar historico vazio -> voltar Bruno -> confirmar historico existente
-> sair -> abrir programa -> confirmar persistencia
```

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_main -v
.\.venv\Scripts\python.exe main.py
```

**Criterio de conclusao:** todos os fluxos principais podem ser demonstrados sem editar arquivos manualmente.

---

### Tarefa 12 - Endurecer privacidade e resiliencia

**Arquivos:**

- criar `tests/test_privacy.py`
- criar `tests/test_offline_flow.py`
- revisar todos os modulos

**Testes primeiro:**

- busca no repositorio nao encontra formato de chave Gemini;
- banco nao contem GPS nem caminho absoluto;
- copia de API nao contem EXIF;
- erro de API nao revela cabecalhos ou chave;
- desligar rede simulada nao interrompe fluxo;
- banco bloqueado executa rollback e mensagem segura;
- exclusao de perfil nao afeta outro perfil;
- arquivos temporarios nao permanecem apos suite.

**Implementacao:**

- revisar todas as mensagens de erro;
- aplicar `try/finally` em recursos temporarios;
- garantir timeouts;
- revisar consultas parametrizadas;
- adicionar verificacao de ambiente no inicio sem revelar valores;
- criar comando/checklist de auditoria antes do ZIP.

**Validacao:**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_privacy tests.test_offline_flow -v
rg -n "AIza[0-9A-Za-z_-]{20,}|GEMINI_API_KEY\s*=\s*[^<]" -g "!*implementation.md" .
```

**Criterio de conclusao:** falhas externas degradam funcionalidades, mas nao derrubam a aplicacao nem expõem dados.

---

### Tarefa 13 - Validacao integral e qualidade do codigo

**Arquivos:** todos os arquivos Python e testes.

**Acoes:**

- executar suite completa;
- executar compilacao de todos os modulos;
- executar fluxo offline do inicio ao fim;
- executar uma chamada Gemini com foto de teste;
- conferir que o resultado hibrido fica no banco;
- comparar antes/depois com duas imagens controladas;
- conferir aprendizado e isolamento;
- revisar funcoes muito longas e duplicacao;
- confirmar uso visivel de funcoes, parametros, retornos, listas e dicionarios;
- executar `git diff --check`.

**Comandos:**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile main.py config.py validators.py database.py image_analyzer.py gemini_client.py recommendation_engine.py analysis_service.py learning_engine.py reports.py
git diff --check
git status --short
```

**Criterio de conclusao:** zero testes falhando, zero erro de compilacao e demonstracao offline/hibrida concluida.

---

### Tarefa 14 - Produzir documentacao academica e PDF

**Arquivos:**

- ampliar `README.md`
- criar fonte da documentacao em `docs/`
- gerar `docs/documentacao_sprint3.pdf`
- criar testes ou verificacoes de conteudo da entrega

**Conteudo obrigatorio do PDF:**

- capa com projeto e integrantes;
- sumario;
- objetivo e justificativa;
- problema e publico;
- funcionalidades implementadas;
- arquitetura e fluxo;
- banco de dados;
- uso de Python na rubrica;
- Gemini, limites e modo offline;
- privacidade;
- testes;
- fontes externas;
- secao detalhada: mantido, modificado, adicionado e removido;
- conclusao.

**Acoes de qualidade:**

- gerar o PDF com ReportLab;
- renderizar todas as paginas em PNG;
- inspecionar visualmente pagina por pagina;
- corrigir cortes, sobreposicoes, fontes e tabelas;
- extrair texto e verificar os headings obrigatorios;
- conferir numeracao, cabecalho e rodape.

**README:**

- explicar instalacao;
- explicar `GEMINI_API_KEY` sem mostrar valor;
- explicar modo offline;
- fornecer roteiro curto de demonstracao;
- explicar como executar testes;
- listar formatos suportados e limites;
- explicar como apagar os dados.

**Criterio de conclusao:** PDF atende aos 25 pontos documentais e README permite reproduzir a demonstracao.

---

### Tarefa 15 - Preparar demonstracao e ZIP final

**Arquivos:**

- criar `CHECKLIST_ENTREGA.md`
- criar ZIP final na raiz ou em `dist/`

**Roteiro de demonstracao sugerido:**

1. selecionar um perfil;
2. analisar uma foto escura/desfocada;
3. mostrar `MEDIDO` versus `IA`;
4. apresentar tres cenarios "E se?";
5. selecionar uma recomendacao;
6. comparar com a recaptura controlada;
7. mostrar ganho real e peso atualizado;
8. trocar de usuario e provar isolamento;
9. retirar a chave temporariamente e provar modo offline;
10. mostrar historico e evolucao.

**Auditoria do ZIP:**

- incluir `.py`, `requirements.txt`, README, PDF e amostras permitidas;
- excluir `.env`, `.venv`, `__pycache__`, banco pessoal, `output/`, caches e temporarios;
- listar conteudo do ZIP e revisar;
- extrair em pasta temporaria;
- instalar dependencias em ambiente limpo quando viavel;
- executar testes e iniciar programa extraido;
- verificar novamente ausencia de segredos.

**Criterio de conclusao:** um unico ZIP reproduz a entrega sem conter dados privados.

## 5. Ordem de commits sugerida

```text
chore: prepara estrutura e configuracao segura
test: cobre validacoes de entrada
feat: adiciona validadores reutilizaveis
test: cobre persistencia e isolamento de perfis
feat: adiciona banco SQLite
test: cobre metricas de imagem
feat: adiciona analise fotografica local
test: cobre recomendacoes contrafactuais
feat: adiciona motor offline explicavel
test: cobre contrato e falhas do Gemini
feat: integra analise multimodal Gemini
feat: orquestra analise hibrida
test: cobre recaptura e aprendizado
feat: adiciona aprendizado individualizado
feat: adiciona simulacoes e relatorios
feat: conclui menu do JOVI AI LensLab
test: cobre privacidade e fluxo offline
docs: atualiza guia e documentacao da Sprint 3
chore: prepara pacote final de entrega
```

Commits de teste e implementacao podem ser unidos quando a mudanca for muito pequena, mas cada marco deve permanecer revisavel.

## 6. Dependencias e riscos

| Risco | Mitigacao |
|---|---|
| Gemini mudar modelo ou quota | `GEMINI_MODEL` configuravel e modo offline |
| Chave vazar | variavel de ambiente, `.gitignore` e busca automatica |
| IA retornar afirmacao errada | contrato JSON, codigos controlados e auditoria local |
| Metricas variarem por imagem | fixtures controladas e limiares documentados |
| OpenCV dificultar instalacao | versao fixada e teste em ambiente limpo |
| Projeto ficar grande para a disciplina | modulos simples, dicionarios e funcoes explicitas |
| Demo depender de internet | roteiro offline e respostas simuladas nos testes |
| Banco misturar perfis | FKs, filtros por usuario e testes de isolamento |
| Usuario tratar previsao como fato | etiquetas MEDIDO/IA/PREVISTO/VERIFICADO |
| Simulacao ser usada como recaptura | identificacao persistente e validacao |

## 7. Definicao global de pronto

O projeto so sera considerado terminado quando:

- todos os criterios da especificacao estiverem implementados;
- suite automatizada estiver verde;
- teste offline completo funcionar;
- teste Gemini real funcionar ou houver evidencia clara de limitacao externa;
- dois usuarios estiverem comprovadamente isolados;
- arquivos temporarios forem limpos;
- nenhuma chave estiver versionada;
- documentacao PDF passar por inspecao visual;
- ZIP for inspecionado e testado apos extracao;
- codigo e PDF explicarem claramente a evolucao da Sprint 2;
- a equipe tiver um roteiro de demonstracao reproduzivel.

## 8. Proximo gate

Este plano nao autoriza ainda a implementacao. Depois da aprovacao do usuario, a execucao comecara pela Tarefa 1 e seguira os marcos em ordem. Mudancas de escopo durante a implementacao devem atualizar primeiro a especificacao e este plano.
