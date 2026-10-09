# Rubrica manual — fallback do RAGAS

Usada quando o RAGAS não roda (sem chave do juiz, limite de requisições, erro de
biblioteca) ou para conferir uma amostra do RAGAS. Aplica-se ao **mesmo eval set**
(`evals/eval_set_rag.json`) e às **mesmas respostas** gravadas em
`evals/resultados/<iteracao>.json`, nos casos com documento esperado.

Cada resposta recebe duas notas de 0 a 1, em passos de 0,25.

## Faithfulness (fidelidade aos trechos)

Mesma definição do RAGAS: fração das afirmações da resposta que estão sustentadas
pelos trechos recuperados. A linha "Fontes:" não conta como afirmação.

| Nota | Critério |
|---:|---|
| 1,00 | Toda afirmação está nos trechos (paráfrase e tradução do manual em inglês valem). |
| 0,75 | Uma afirmação secundária não está nos trechos, mas não contradiz nada. |
| 0,50 | Metade das afirmações não tem apoio nos trechos. |
| 0,25 | Só uma afirmação tem apoio; o resto vem de fora. |
| 0,00 | Nenhuma afirmação tem apoio, ou alguma contradiz os trechos (número trocado, especificação inventada). |

Resposta que recusa ("Não encontrei essa informação...") num caso que tinha resposta
na base recebe faithfulness 1 (não afirmou nada falso) e answer relevancy 0 (a pergunta
ficou sem resposta). Essa regra é aplicada em código, igual para todas as versões, sem
passar pelo juiz.

## Answer relevancy (resposta trata do que foi perguntado)

| Nota | Critério |
|---:|---|
| 1,00 | Responde diretamente a pergunta, com o dado pedido. |
| 0,75 | Responde, mas com rodeio ou informação que não foi pedida. |
| 0,50 | Responde só parte da pergunta. |
| 0,25 | Fala do assunto, mas não responde o que foi perguntado. |
| 0,00 | Não responde (recusa indevida, outro assunto). |

## Por que é equivalente ao RAGAS

- **Faithfulness:** o RAGAS quebra a resposta em afirmações e verifica cada uma
  contra os trechos; a rubrica faz a mesma contagem, à mão, em faixas de 25%.
- **Answer relevancy:** o RAGAS gera perguntas a partir da resposta e mede a
  similaridade com a pergunta original. Uma resposta que não responde gera perguntas
  diferentes. A rubrica avalia diretamente se a pergunta foi respondida, que é o
  que essa similaridade aproxima.
- **Mesma base de comparação:** mesmos casos, mesmos trechos e mesma regra (só
  casos com documento esperado) nas duas formas, então os números das iterações
  continuam comparáveis entre si.

## Como aplicar

```bash
python -m evals.fallback_manual exportar --resultado iter3      # gera evals/fallback/planilha_iter3.csv
# preencher as colunas faithfulness_manual e answer_relevancy_manual
python -m evals.fallback_manual consolidar --resultado iter3    # grava as médias no JSON da iteração
```
