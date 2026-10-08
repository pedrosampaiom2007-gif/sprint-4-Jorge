# Interface — como executar

Requer Python 3.11 a 3.13 e as chaves no `.env` (veja o README da raiz).

```bash
pip install -r requirements.txt
python -m src.rag.vector_store     # indexa a base no ChromaDB (uma vez; repete só se a base mudar)
python -m app.web                  # http://localhost:7860
```

`python -m app.web --share` gera um link público temporário do Gradio.

## Abas

| Aba | O que faz |
|---|---|
| 💬 Chat | Conversa com o assistente. Cada resposta termina com a linha **Fontes:** e o painel ao lado mostra os trechos usados: documento, seção ou página, relevância, link de origem e se o trecho foi citado. Dá para trocar o perfil (motorista ou gestão), o modelo e a versão do prompt. |
| ⚖️ Comparar modelos | A mesma pergunta respondida por mais de um provedor, modelo e versão de prompt, com os mesmos trechos. |
| 📚 Base de conhecimento | Lista os documentos indexados e reindexa a base. |
| 📊 Avaliação | Scores do RAGAS por iteração (`evals/historico_scores.md`). |

## No terminal

```bash
python -m app.cli           # conversa livre ("sair" encerra)
python -m app.cli --demo    # 3 turnos encadeados mostrando a memória e a reescrita da pergunta
```
