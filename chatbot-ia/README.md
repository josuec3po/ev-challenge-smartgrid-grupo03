> **Nota (integração futura):** este é o agente conversacional (ChargeGrid Assistant) construído
> na disciplina "Prompt and Artificial Intelligence" (Sprint 03), trazido para este repositório
> como módulo isolado — ainda **não integrado** com a API/Totem deste projeto. A ideia é usá-lo
> futuramente como feature (ex: assistente de IA dentro do fluxo do totem). Requer `GROQ_API_KEY`
> própria em um `.env` local (não incluso). Código-fonte original e histórico de commits:
> https://github.com/enrico1604/sprint2-IA
>
> ---
>
# ChargeGrid Intelligence AI - Sprint 03
**GoodWe EV Challenge 2026 | FIAP - Prompt and Artificial Intelligence | 1º ano Ciência da Computação - 2026.2**

Evolução do chatbot ChargeGrid (Sprints 1 e 2): o núcleo conversacional foi
reconstruído com um **framework de desenvolvimento de agentes**
(LangChain + LangGraph), com memória de sessão gerenciada nativamente pelo
framework, guardrails de segurança dedicados e comparação entre 2 modelos
de LLM.

## 🚀 Tecnologias utilizadas
- **Linguagem:** Python 3.10+
- **Framework Web:** Flask (backend API) — inalterado, mesma interface
  (`index.html`) da Sprint 2
- **Framework de agentes:** LangChain (`create_agent`) + LangGraph
  (`InMemorySaver` como checkpointer)
- **IA:** Groq API — comparação entre `openai/gpt-oss-120b` e
  `qwen/qwen3.8-27b` (ver `relatorio_modelos.md`)
- **Gestão de dependências:** `pip` e `python-dotenv`

## 🧠 Por que LangChain/LangGraph

Escolhemos LangChain/LangGraph por já termos experiência validada com o
framework em outro checkpoint da disciplina (agente com tools + memória),
o que reduziu o risco técnico da migração dentro do prazo da sprint, e por
seu `create_agent` já entregar um agente ReAct completo (decisão de uso de
tool, execução, resposta final) sem precisarmos reescrever esse loop à mão
— era exatamente o que o núcleo manual da Sprint 2 fazia via `while`/`if`
com `tool_calls`.

## 🔁 O que mudou da Sprint 2 para a Sprint 03

| | Sprint 1/2 (legado) | Sprint 03 (framework de agentes) |
|---|---|---|
| Orquestração do agente | `while`/`if` manual sobre `tool_calls` do client Groq | `create_agent` (LangChain/LangGraph) |
| Memória de conversa | Lista Python global (`historico_conversa`) | Checkpointer nativo (`InMemorySaver`), indexado por `thread_id` |
| Tools | JSON schema manual + dispatch por nome | `@tool` do LangChain, docstring como especificação |
| Guardrails | Escopo + "não invente valores matemáticos" | + sigilo/blindagem contra prompt injection, proibição de inventar especificações de produto, recusa de aconselhamento jurídico/financeiro/segurança elétrica |

Comparativo completo (qualidade, tokens, latência, segurança) em
`relatorio_evolucao.pdf`.

## 🛠️ Configuração e instalação

### 1. Pré-requisitos
- Python instalado.
- Uma chave de API da [Groq](https://console.groq.com/).

### 2. Instalação de dependências
```bash
pip install -r requirements.txt
```

### 3. Variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto (nunca comitado — está no `.gitignore`):
```env
GROQ_API_KEY=sua_chave_aqui_sem_aspas
```

### 4. Execução
```bash
python app.py
```
Servidor em `http://localhost:5000`. Abra `index.html` no navegador.

### 5. Rodar a avaliação comparativa (legado x agente x 2 modelos)
```bash
python eval_comparativo.py
```
Gera `resultados_eval.md` com todas as respostas, tokens e latências.

## 🧪 Casos de teste

- Acurácia (5 casos, herdados da Sprint 2) + memória de 3 turnos: ver
  `eval_comparativo.py`.
- Segurança/guardrails (6 casos): ver `docs/casos_teste_seguranca.md`.

## 👥 Integrantes

- **Josué Franco Braga** - RM569174 - Turma 1CCPZ
- **Andrei Henrique Santos** - RM569440 - Turma 1CCPZ
- **Heitor Maxímus Mucha** - RM571407 - Turma 1CCPZ
- **Enrico Marinho de Aquino** - RM569338 - Turma 1CCPZ
- **Fernando Lobato Rodrigues** - RM569377 - Turma 1CCPZ
- **Manoel da Silva Ferreira** - RM572045 - Turma 1CCPZ

## 📄 Entrega

- Repositório público (este) com histórico de commits.
- `relatorio_evolucao.pdf` (até 5 páginas) — obrigatório, incluído neste repositório.
- `relatorio_modelos.md` — comparativo de modelos e parâmetros.
- `entrega.txt` — nome, RM e turma dos integrantes (anexado junto do link do repositório).
