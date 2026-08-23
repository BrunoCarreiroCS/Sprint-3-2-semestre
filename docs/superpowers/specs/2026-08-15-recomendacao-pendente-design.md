# Especificacao de Design - Atalho de Recomendacao Pendente

**Status:** aprovada pelo usuario em 15/08/2026
**Data:** 15/08/2026
**Projeto:** NextFrame JOVI AI LensLab (Sprint 3)
**Escopo:** pequena melhoria de fluxo, nao uma nova funcionalidade de produto

## 1. Problema

O sistema ja permite "marcar" uma recomendacao para testar depois, em tres pontos do codigo:

- a pergunta pos-analise "Deseja marcar uma destas recomendacoes para testar agora?";
- o menu 5, "Marcar recomendacao para testar";
- a selecao manual de recomendacao dentro de "Comparar antes e depois".

Todos os tres gravam a flag `selecionada = 1` na tabela `recomendacoes`. Essa flag nunca e lida em nenhum outro lugar do sistema: nao aparece no historico, nao influencia a evolucao, e nao e usada para pre-selecionar nada na tela de comparacao. Ou seja, marcar uma recomendacao hoje nao tem efeito observavel nenhum — e um passo que o usuario executa sem ganhar nada em troca, o que confunde mais do que ajuda.

## 2. Objetivo

Dar uma funcao real para o ato de marcar: a recomendacao marcada mais recentemente, e ainda nao verificada por uma recaptura, passa a ser oferecida como atalho na tela "Comparar antes e depois", evitando que o usuario reescolha a mesma analise e a mesma recomendacao que ja tinha escolhido minutos atras.

## 3. Comportamento novo

Ao abrir "Comparar antes e depois":

1. O sistema busca a recomendacao marcada mais recentemente pelo usuario ativo que ainda nao tem uma comparacao registrada.
2. Se existir, pergunta:
   ```
   Voce marcou 'Estabilizar Camera' na foto exemplo_escuro.jpg para testar.
   Foi essa recomendacao que voce aplicou? (sim/nao, Enter = sim):
   ```
   - Resposta afirmativa (ou Enter): pula a escolha de analise e de recomendacao, vai direto para "informe a nova foto".
   - Resposta negativa: segue o fluxo atual (escolher analise, depois escolher recomendacao manualmente).
3. Se nao existir nenhuma recomendacao pendente, o fluxo atual continua identico a hoje, sem essa pergunta.

Uma recomendacao deixa de ser "pendente" assim que uma comparacao e registrada para ela (sucesso, misto, falha ou inconclusivo — qualquer resultado fecha a pendencia).

## 4. Modelo de dados

Adicionar a coluna `marcado_em TEXT` (nullable) na tabela `recomendacoes`, preenchida em `marcar_recomendacao`. Migracao via `ALTER TABLE ... ADD COLUMN`, no mesmo padrao ja usado para `peso_aprendido` — segura para bancos existentes, sem perda de dados.

A consulta de "pendente" filtra por `usuario_id`, exige `marcado_em IS NOT NULL` e exclui recomendacoes que ja aparecem em `comparacoes.recomendacao_id`, ordenando pela marcacao mais recente.

A coluna `selecionada` e mantida como esta (sinaliza qual recomendacao foi marcada dentro de uma mesma analise); a logica de pendencia usa `marcado_em`, nao `selecionada`, porque o timestamp reflete quando a marcacao aconteceu, nao apenas se aconteceu.

## 5. Fora de escopo (YAGNI)

- Uma tela dedicada de "lista de pendencias" com todas as marcacoes simultaneas.
- Suporte a mais de uma recomendacao pendente visivel ao mesmo tempo — so a mais recente e oferecida.
- Expirar ou cancelar uma marcacao manualmente.

Se o uso real mostrar necessidade de qualquer um desses, e um incremento futuro pequeno sobre esta mesma base.

## 6. Testes

- `database.py`: nova funcao de busca da recomendacao pendente — testar que ignora recomendacoes ja comparadas, que respeita isolamento por usuario, e que retorna `None` quando nao ha nada pendente.
- `main.py` (fluxo de interface): nao coberto por teste automatizado, como o restante da camada de interface deste projeto — validado por execucao manual do programa.

## 7. Compatibilidade

Nenhuma mudanca de comportamento para quem nunca marca uma recomendacao. Nenhuma mudanca no schema alem da nova coluna nullable. Nenhum teste existente depende de `selecionada` ou `marcar_recomendacao`.
