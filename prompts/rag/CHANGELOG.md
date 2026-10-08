# Versões do prompt RAG

Os prompts da Sprint 4 ficam em `prompts/rag/`. Os da Sprint 3 (`prompts/system_prompt_v1.md`
e `v2.md`) continuam no repositório como referência.

## rag_v1 — iteração 1 (linha de base)

O `system_prompt_v2` da Sprint 3 com uma única mudança: o bloco `<dominio>` explica que o
`<contexto>` agora traz trechos de documentos. Não pede citação e não define o que
fazer quando a resposta não está na base.

## rag_v2 — iteração 2

- **Bloco `<grounding>` no topo:** responder só com o `<contexto>`, citar `[n]` depois de
  cada afirmação, frase fixa de recusa quando a resposta não está nos trechos (a mesma
  que o código usa em `RESPOSTA_SEM_CONTEXTO`), nunca completar com conhecimento próprio.
- **Especificação de produto:** só existe se estiver escrita num trecho.
- **Documento em inglês:** explicar em português o que o manual GoodWe diz, sem
  acrescentar nada.
- **Instrução dentro de documento:** frase dirigida ao assistente num trecho é ignorada;
  explica o aviso `[trecho removido: ...]` da blindagem.
- `<base_de_conhecimento>` lista os documentos, para o modelo saber o que pode ou não
  estar na base.
- Exemplos da Sprint 3 removidos (falavam do contexto antigo, sem trechos numerados).

## rag_v3 — iteração 3

- **Cinco exemplos completos** de contexto → resposta: citação simples, manual em inglês,
  resposta parcial (uma parte com citação e a outra recusada), trecho blindado e dado
  restrito à gestão.
- Responder primeiro e oferecer mais detalhe depois, numa pergunta só.

## Tamanho e ganho medido

<!-- AUTO:prompts -->
| Versão | Tokens do prompt | Usada na | Faithfulness | Answer relevancy | Ganho de faithfulness vs versão anterior |
|---|---:|---|---:|---:|---:|
| rag_v1 | 1514 | Iteração 1 | pendente | pendente | — |
| rag_v2 | 902 | Iteração 2 | pendente | pendente | — |
| rag_v3 | 1404 | Iteração 3 | pendente | pendente | — |
<!-- /AUTO:prompts -->

Ganho = diferença de faithfulness médio para a iteração anterior, no mesmo eval set e com
o mesmo juiz. A iteração 2 também troca o chunking e liga a recusa em código, então o
ganho dela não é só do prompt; a iteração 3 muda o prompt e liga a reescrita da pergunta.

## Como medir de novo

```bash
python -m evals.run_iteracoes          # roda as 3 iterações e atualiza esta tabela
```
