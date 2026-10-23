# NextFrame JOVI AI LensLab - Sprint 4

O JOVI AI LensLab transforma a recomendação genérica da Sprint 2 em um laboratório fotográfico individual. O sistema mede uma foto localmente, usa o Gemini (quando autorizado), cria alternativas contrafactuais do tipo “E se?”, compara uma recaptura real e aprende quais orientações funcionam melhor para cada perfil.

Na Sprint 4 a solução foi finalizada com **persistência em arquivos JSON** e **integração com o restante da solução NextFrame por troca de arquivos JSON** (o app da câmera JOVI envia uma solicitação e recebe de volta o diagnóstico e as recomendações).

## Por que a solução é inovadora

O diferencial não é apenas “usar IA”. O ciclo completo é:

1. **Medir:** OpenCV e Pillow calculam brilho, contraste, nitidez, saturação, recortes de sombras/realces e resolução.
2. **Interpretar:** Gemini identifica assunto, cena, composição e movimento com saída JSON limitada por schema.
3. **Simular:** o motor estima o ganho, risco e esforço de alternativas como adicionar luz, estabilizar ou usar modo noturno.
4. **Verificar:** o usuário refaz a foto e o sistema compara antes/depois no mesmo objetivo e intenção.
5. **Aprender:** os pesos são ajustados e gravados no arquivo JSON daquele usuário, por ação e contexto.

As mensagens sempre identificam o que foi **MEDIDO**, **inferido pela IA**, **PREVISTO** e **VERIFICADO**. A simulação nunca é apresentada como recaptura real.

## Experiência no terminal

- **Resumo primeiro, técnico por opção:** cada análise e cada recaptura mostram um resultado curto em linguagem simples (nota, o que está bom, o que pode melhorar, a dica principal). Os termos técnicos (Exposição, Nitidez, MEDIDO/IA/PREVISTO/VERIFICADO, pesos) só aparecem se você pedir "ver detalhes completos".
- **Tour guiado:** ao criar um perfil, o programa oferece rodar automaticamente uma análise de exemplo, sem pedir nenhuma entrada extra.
- **Explorador de arquivos do Windows:** ao pedir uma foto, o programa já sugere abrir o explorador nativo (basta apertar Enter); as fotos em `samples/` também aparecem numeradas, e ainda é possível digitar outro caminho manualmente. Requer `tkinter` (já incluso na instalação padrão do Python para Windows).
- **Enter repete o último valor:** o objetivo mais usado na sessão aparece marcado e pode ser reaproveitado só com Enter.
- **Cancelar em qualquer etapa:** todo fluxo com várias perguntas aceita `0` para voltar sem perder o que já foi salvo.
- **Próximo passo sugerido:** depois de analisar uma foto, o programa já pergunta se você quer marcar uma recomendação para testar.
- **Marcação com função real:** a recomendação marcada mais recentemente (e ainda não verificada) vira um atalho em "Comparar antes e depois" — confirma com Enter em vez de escolher de novo a análise e a recomendação do zero.
- **Barra de pontuação e cores:** a pontuação geral e cada dimensão têm uma barra ASCII; os rótulos MEDIDO/IA/PREVISTO/VERIFICADO usam cor (via `colorama`) quando o terminal suporta.
- **Contexto legível:** em "Ver evolução", os pesos aprendidos aparecem com o contexto por extenso (ex.: "Retrato, ambiente escuro, assunto parado") em vez do código interno.

## Requisitos da Sprint 4 atendidos

| Requisito | Onde está |
|---|---|
| Menu de opções, retorno ao menu e opção de encerrar | `main.py` — opções 1 a 10 e 0 |
| Funções com parâmetros e retorno | todos os módulos; regras puras separadas da interface |
| Validação de entrada e `try/except` | `validators.py`, `main.py`, `database.py`, `integracao.py` |
| Persistência em arquivos JSON | `database.py` — `data/usuarios.json` e `data/perfis/perfil_<id>.json` |
| Consumo de API externa | `gemini_client.py` — Google Gemini com saída validada por JSON Schema |
| Integração com o restante da solução | `integracao.py` — troca de arquivos JSON na pasta `integracao/` |
| Boas práticas | constantes centrais, type hints, gravação atômica, 84 testes automatizados |
| Interface intuitiva | resumo em linguagem simples, explorador de arquivos, cancelamento com `0` |

## Estrutura

```text
main.py                    menu e fluxos de interação
analysis_service.py        orquestra análise local, IA, ranking e persistência
image_analyzer.py          métricas técnicas e prévias educativas
gemini_client.py           API Gemini e validação de JSON
recommendation_engine.py   pontuação contextual e cenários “E se?”
learning_engine.py         comparação real e aprendizado individual
database.py                persistência em arquivos JSON
integracao.py              contrato de integração por arquivos JSON
validators.py              validações puras e entradas seguras
reports.py                 diagnóstico, evolução e exportação
integracao/                pastas de troca com o app JOVI + exemplo do contrato
samples/                   imagens artificiais para demonstração
tests/                     testes automatizados
```

## Persistência em JSON

```text
data/
  usuarios.json              perfis, consentimento e contadores de identificadores
  perfis/perfil_<id>.json    análises, recomendações, comparações e pesos de UM perfil
```

- Cada perfil tem o seu próprio arquivo: excluir o perfil apaga só o arquivo dele.
- Toda gravação é feita em um arquivo temporário e depois movida (`os.replace`), para que uma falha no meio não corrompa os dados.
- Se um arquivo estiver corrompido, o programa mostra qual é e não encerra com erro técnico.
- Os arquivos **não armazenam as fotografias**, localização GPS nem a chave da API.

## Integração com o app JOVI (arquivos JSON)

A opção **10** do menu troca arquivos com o app da câmera JOVI (ou qualquer outra parte da solução NextFrame):

1. O app grava uma solicitação em `integracao/entrada/` — o formato está em [`integracao/exemplos/solicitacao_exemplo.json`](integracao/exemplos/solicitacao_exemplo.json).
2. O LensLab valida, analisa a foto e grava `integracao/saida/resultado_<id_solicitacao>.json` com nota, pontos fortes, pontos a melhorar e recomendações.
3. A solicitação atendida vai para `integracao/processadas/`. Uma solicitação inválida vai para `integracao/com_erro/` e gera `integracao/saida/erro_<nome>.json` com o motivo.
4. O LensLab também exporta o perfil (`integracao/saida/perfil_<id>.json`) com a evolução e os conselhos aprendidos, para o app exibir.

Campos da solicitação: `versao` (`"1.0"`), `id_solicitacao`, `origem`, `perfil` (`apelido`, `nivel`, `estilo`, `consentimento_api`), `foto` (caminho absoluto ou relativo à raiz do projeto), `objetivo` e `intencao`. Um perfil que já existe é reaproveitado, e o consentimento dele nunca é alterado por uma solicitação externa.

## Como executar no Windows

Recomendado: Python 3.11 ou mais recente.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

O programa funciona sem internet. Para habilitar a análise semântica do Gemini, crie na raiz um arquivo `.env` baseado em `.env.example`:

```text
GEMINI_API_KEY=SUA_CHAVE_AQUI
GEMINI_MODEL=gemini-flash-latest
```

O `.env` está ignorado pelo Git e não entra no ZIP. Não cole a chave no código, no PDF ou em capturas de tela.

Para apresentar o modo híbrido sem depender de internet ou de uma chave real, defina `JOVI_DEMO_MODE=1` no `.env`. Nesse modo o cliente Gemini é substituído por respostas simuladas (mesma validação de schema), e o menu mostra "Gemini: chave demo".

## Demonstração sugerida

1. Crie o perfil “Demo”, nível iniciante, estilo natural.
2. Analise `samples/exemplo_escuro.jpg` como retrato.
3. Mostre as métricas, o modo de execução e as três alternativas.
4. Gere uma prévia de “adicionar iluminação”, se aparecer no ranking.
5. Analise `samples/exemplo_nitido.jpg` como recaptura, avalie a orientação e mostre a evolução.
6. Troque de perfil para demonstrar que o peso aprendido não é compartilhado.
7. Abra a opção 10, crie uma solicitação de exemplo, processe-a e mostre o `resultado_*.json` gerado em `integracao/saida/`.
8. Mostre os arquivos `data/usuarios.json` e `data/perfis/perfil_<id>.json` para evidenciar a persistência em JSON.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Os 84 testes verificam validações, métricas locais, remoção da cópia temporária, preservação da foto original, filtro do JSON da IA, fallback offline, persistência em JSON (arquivo corrompido, gravação atômica, exclusão, identificadores únicos), comparação, isolamento do aprendizado e o contrato de integração (solicitação válida, JSON malformado, campos inválidos, exportação de perfil).

O arquivo `tests/test_requisitos_sprint4.py` organiza os testes por critério da rubrica do Sprint 4 (uma classe por item: menu, subrotinas, validação e exceções, persistência JSON, API externa, integração e interface). Para rodar só ele:

```powershell
python -m unittest tests.test_requisitos_sprint4 -v
```

## Privacidade e limites

- A chamada externa só ocorre quando há consentimento no perfil **e** chave configurada.
- Para a API é criada uma cópia JPEG temporária, reduzida e sem EXIF; ela é removida ao terminar.
- Fotos originais e coordenadas GPS não entram nos arquivos de dados nem nos resultados de integração.
- Falhas de rede, autenticação, cota, timeout ou JSON inválido acionam o modo offline.
- A pontuação é contextual e educativa, não uma medida universal de qualidade artística.
- A IA pode errar; por isso sua saída é filtrada, rotulada e combinada com métricas locais.
- Prévia digital é hipótese; apenas a recaptura é evidência de melhoria.

## Fundamentação e pesquisa

- A documentação oficial do [Gemini Image Understanding](https://ai.google.dev/gemini-api/docs/image-understanding) confirma suporte a compreensão multimodal de imagens e alerta para a necessidade de pós-processamento e avaliação humana.
- [Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output) fundamenta o uso de JSON Schema para uma resposta previsível e validável.
- A ficha oficial do [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash) registra entrada de imagens e suporte a saída estruturada.
- As [Camera Extensions do Android](https://developer.android.com/media/camera/camera-extensions) descrevem Auto, Bokeh, HDR e Night e observam que captura noturna leva tempo e exige estabilidade.
- O [Camera Coach do Pixel](https://support.google.com/pixelcamera/answer/2838995) evidencia a tendência de orientação fotográfica contextual, além da necessidade de fallback quando não há conexão.
- Discussões da comunidade sobre [limites e expectativas do Night Mode](https://www.reddit.com/r/photography/comments/jeysrk) e [sugestões para câmera de smartphone](https://www.reddit.com/r/GalaxyS21/comments/qxj2g3) ajudaram a priorizar explicações de risco, alternativas comparáveis e transparência sobre limitações.

## Equipe — turma 1ESPI

| Integrante | RM |
|---|---|
| Eduardo Bechara Medeiros Craveiro | 571081 |
| Gustavo Moita de Lima | 569180 |
| Bruno Carreiro Dos Santos | 569423 |

Projeto acadêmico FIAP - Sprint 4, Computational Thinking with Python.
