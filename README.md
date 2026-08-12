# NextFrame JOVI AI LensLab - Sprint 3

O JOVI AI LensLab transforma a recomendação genérica da Sprint 2 em um laboratório fotográfico individual. O sistema mede uma foto localmente, usa o Gemini (quando autorizado), cria alternativas contrafactuais do tipo “E se?”, compara uma recaptura real e aprende quais orientações funcionam melhor para cada perfil.

## Por que a solução é inovadora

O diferencial não é apenas “usar IA”. O ciclo completo é:

1. **Medir:** OpenCV e Pillow calculam brilho, contraste, nitidez, saturação, recortes de sombras/realces e resolução.
2. **Interpretar:** Gemini identifica assunto, cena, composição e movimento com saída JSON limitada por schema.
3. **Simular:** o motor estima o ganho, risco e esforço de alternativas como adicionar luz, estabilizar ou usar modo noturno.
4. **Verificar:** o usuário refaz a foto e o sistema compara antes/depois no mesmo objetivo e intenção.
5. **Aprender:** o SQLite ajusta pesos apenas para aquele usuário, ação e contexto.

As mensagens sempre identificam o que foi **MEDIDO**, **inferido pela IA**, **PREVISTO** e **VERIFICADO**. A simulação nunca é apresentada como recaptura real.

## Requisitos atendidos

- Menu com 9 funcionalidades e opção de saída.
- Retorno automático ao menu principal.
- Organização em funções e módulos com parâmetros e retornos.
- Validação de opções, textos, formatos, tamanho, resolução e integridade das imagens.
- Uso extensivo de listas e dicionários no motor de análise e recomendação.
- Persistência individualizada em SQLite.
- API/IA com consentimento, validação estrutural e fallback offline.
- Interface textual clara e mensagens de erro controladas.

## Estrutura

```text
main.py                    menu e fluxos de interação
analysis_service.py        orquestra análise local, IA, ranking e banco
image_analyzer.py          métricas técnicas e prévias educativas
gemini_client.py           integração Gemini e validação de JSON
recommendation_engine.py   pontuação contextual e cenários “E se?”
learning_engine.py         comparação real e aprendizado individual
database.py                schema e operações SQLite
validators.py              validações puras e entradas seguras
reports.py                 diagnóstico, evolução e exportação
samples/                   imagens artificiais para demonstração
tests/                     testes automatizados
```

O banco armazena perfis, métricas, diagnósticos, recomendações, comparações e pesos. Ele **não armazena as fotografias**, localização GPS ou a chave da API.

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
GEMINI_MODEL=gemini-2.5-flash
```

O `.env` está ignorado pelo Git e não entra no ZIP. Não cole a chave no código, no PDF ou em capturas de tela.

## Demonstração sugerida

1. Crie o perfil “Demo”, nível iniciante, estilo natural.
2. Analise `samples/exemplo_escuro.jpg` como retrato.
3. Mostre as métricas, o modo de execução e as três alternativas.
4. Gere uma prévia de “adicionar iluminação”, se aparecer no ranking.
5. Analise `samples/exemplo_nitido.jpg` como recaptura, avalie a orientação e mostre a evolução.
6. Troque de perfil para demonstrar que o peso aprendido não é compartilhado.

## Testes

```powershell
python -m unittest discover -v
```

Os testes verificam validações, métricas locais, remoção da cópia temporária, preservação da foto original, filtro do JSON da IA, fallback offline, persistência, exclusão em cascata, comparação e isolamento do aprendizado.

## Privacidade e limites

- A chamada externa só ocorre quando há consentimento no perfil **e** chave configurada.
- Para a API é criada uma cópia JPEG temporária, reduzida e sem EXIF; ela é removida ao terminar.
- Fotos originais e coordenadas GPS não entram no banco.
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

## Equipe

- Bruno Carreiro
- Daniel Graciano
- Gustavo Romero
- Leonardo Porto
- Leonardo Gomes

Projeto acadêmico FIAP - Sprint 3, Computational Thinking with Python.
