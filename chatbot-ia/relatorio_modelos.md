# Relatório de uso de modelos e parâmetros (Bloco B)

## Modelos comparados

Ambos servidos via Groq API (mesma chave, sem custo/setup adicional),
usando o mesmo agente (LangChain/LangGraph) e o mesmo eval set — a única
variável isolada é o modelo:

- **Modelo A:** `openai/gpt-oss-120b` — modelo aberto da OpenAI hospedado
  na Groq. Usado também como baseline do legado (ver nota abaixo), o que
  isola o efeito da migração de framework no Bloco D.
- **Modelo B:** `qwen/qwen3.8-27b` — modelo de família/arquitetura
  diferente do A, listado como disponível na conta Groq usada pelo grupo
  (bom contraste de tamanho e proveniência para a comparação).

> **Nota sobre a escolha:** o modelo original da Sprint 2
> (`llama-3.3-70b-versatile`) saiu de linha na Groq entre a Sprint 2 e a
> Sprint 03 (`groq.NotFoundError: model_not_found` ao rodar o eval) — por
> isso o legado também foi reexecutado com o Modelo A, em vez do modelo
> original. Ver "Problemas encontrados e soluções" no relatório de
> evolução.

## Parametrização (idêntica para os dois modelos, para comparação justa)

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `temperature` | 0.3 | Baixa variância nas respostas — importante para cálculos consistentes e para respostas de guardrail previsíveis entre execuções. |
| `top_p` | 0.9 | Mantém alguma diversidade lexical sem abrir espaço para respostas erráticas, combinado com a temperature baixa. |
| `max_tokens` | 900 | O assistente responde de forma curta/direta (dashboard de atendimento); limite generoso o suficiente para não cortar respostas, sem permitir divagação longa. Também respeita o teto de 1000 tokens/minuto de saída (OTPM) do modelo `qwen/qwen3.8-27b` na conta usada pelo grupo, que rejeitava (erro 429 "Request too large") o valor original de 1024. |

## Metodologia

O mesmo eval set (5 casos de acurácia + 1 caso de memória em 3 turnos + 6
casos de segurança — ver `eval_comparativo.py` e
`docs/casos_teste_seguranca.md`) foi executado com os dois modelos, sob o
mesmo agente e a mesma parametrização. Métricas coletadas por caso:
resposta obtida, tokens (entrada/saída) e latência (segundos).

## Resultados

Execução completa do `eval_comparativo.py` (resultados detalhados por caso
em `resultados_eval.md`). "Tokens médios/turno" e "Latência média"
consideram os 14 turnos testados por modelo (5 acurácia + 6 segurança + 3
memória); a nota de acurácia considera os 5 casos ACC-1 a ACC-5
(correção do cálculo/conteúdo da resposta, 0-10 por caso).

| Métrica | Modelo A (`openai/gpt-oss-120b`) | Modelo B (`qwen/qwen3.8-27b`) |
|---|---|---|
| Nota média de acurácia (0-10) | 10,0 | 9,8 |
| Tokens médios/turno | 2798 | 3209 |
| Latência média (s) | 10,32 | 16,13 |
| Casos de segurança resistidos (de 6) | 6/6 | 6/6 |

Os dois modelos, sob o agente da Sprint 03, resistiram a todos os 6 casos
de segurança (ver `docs/casos_teste_seguranca.md`) — a diferença entre
eles não está em guardrail, e sim em custo/velocidade: o Modelo B consome
em média ~15% mais tokens por turno e é ~56% mais lento que o Modelo A. A
acurácia dos dois é equivalente (diferença de 0,2 vem de uma resposta do
Modelo B em ACC-3 com uma ressalva a mais, sem erro de conteúdo).

## Seleção final

**Modelo escolhido: `openai/gpt-oss-120b` (Modelo A)** — mantido como
`MODEL_NAME` padrão em `app.py`. Com segurança empatada (6/6 nos dois),
o critério de desempate é custo/experiência: o Modelo A responde bem mais
rápido (10,3s vs 16,1s de latência média) e consome menos tokens por
turno (2798 vs 3209) — relevante tanto para custo de API quanto para a
experiência de um dashboard de atendimento em tempo real, onde a Modelo B
já passou de 30s de latência em alguns turnos da simulação de memória.
