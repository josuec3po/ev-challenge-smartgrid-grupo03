"""
Versao LEGADO (Sprint 2) do nucleo conversacional - mantida intacta como
referencia para o comparativo antes/depois da Sprint 03 (ver
relatorio_evolucao.pdf e eval_comparativo.py).

O UNICO ajuste em relacao ao app.py original da Sprint 2 e que a logica de
resposta foi extraida da rota Flask para a funcao `responder_legado()`, para
que o eval_comparativo.py consiga chamar exatamente a mesma logica sem subir
um servidor. Prompt, ferramentas, formato de historico e fluxo de
function-calling manual sao IDENTICOS ao codigo original.
"""

import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("ERRO: A variavel de ambiente GROQ_API_KEY nao foi configurada no arquivo .env")

client = Groq(api_key=GROQ_API_KEY)

DADOS_SESSAO = {
    "sessao_ativa": {
        "kwh_consumido": 18.4,
        "kwh_restante": 5.6,
        "potencia_atual_kw": 22.0,
        "tempo_decorrido_min": 50,
        "soc_percentual": 76
    },
    "eletroposto": {
        "nome": "Eletroposto Osasco - FIAP Hub",
        "carregadores_ativos": 3,
        "potencia_total_disponivel_kw": 88.0,
        "conectores_livres": 1,
        "modelo_carregador": "GoodWe HCA G2 (Serie Residencial Comercializada)"
    },
    "tarifa_vigente_kwh": 1.20
}


def formatar_dados_dinamicos(dados: dict) -> str:
    s = dados["sessao_ativa"]
    e = dados["eletroposto"]
    t = dados["tarifa_vigente_kwh"]
    return f"""
DADOS DA SESSAO ATUAL:
- Eletroposto: {e["nome"]}
- Equipamento: {e["modelo_carregador"]}
- Energia consumida: {s["kwh_consumido"]} kWh
- Energia restante estimada: {s["kwh_restante"]} kWh
- Potencia de entrega atual: {s["potencia_atual_kw"]} kW
- Tempo de recarga decorrido: {s["tempo_decorrido_min"]} minutos
- Estado de Carga (SoC): {s["soc_percentual"]}%

STATUS DA INFRAESTRUTURA:
- Carregadores em uso: {e["carregadores_ativos"]}
- Potencia total do barramento: {e["potencia_total_disponivel_kw"]} kW
- Vagas livres: {e["conectores_livres"]}

TARIFA COMERCIAL: R$ {t}/kWh
"""


SYSTEM_PROMPT = """
Voce e o ChargeGrid Assistant, a IA oficial do sistema ChargeGrid AI, desenvolvido para o GoodWe EV Challenge 2026.

SUA MISSAO:
Transformar carregadores residenciais GoodWe HCA G2 em uma rede de recarga comercial eficiente. Voce atende motoristas e operadores.

DIRETRIZES DE COMPORTAMENTO:
1. Responda sempre em Portugues Brasileiro.
2. Seja profissional, tecnico mas acessivel.
3. Use o CONTEXTO DINAMICO fornecido abaixo para responder perguntas sobre a recarga atual.
4. Se o usuario perguntar algo fora do escopo (ex: receitas, politica), informe educadamente que seu foco e mobilidade eletrica e a plataforma ChargeGrid.
5. Para calculos de preco, tempo ou demanda, utilize as FERRAMENTAS disponiveis. Nunca invente valores matematicos.

CONHECIMENTO ESPECIFICO:
- GoodWe HCA G2: Suporta carregamento AC, integracao com solar, e protocolo OCPP para gestao comercial.
- ChargeGrid: Nossa camada de software que adiciona tarifacao e gestao de carga a esses equipamentos.

---
CONTEXTO DINAMICO DA SESSAO:
{dados_dinamicos}
---
"""


def calcular_preco(kwh_consumido: float, tarifa: float) -> dict:
    custo = round(float(kwh_consumido) * float(tarifa), 2)
    return {"resultado": f"O custo atual da sessao e de R$ {custo:.2f}."}


def calcular_demanda(carregadores_ativos: int, potencia_total: float) -> dict:
    potencia_media = round(float(potencia_total) / int(carregadores_ativos), 2)
    return {"resultado": f"Atualmente temos {carregadores_ativos} carregadores dividindo {potencia_total} kW, resultando em uma media de {potencia_media} kW por veiculo."}


def calcular_estimativa(kwh_restante: float, potencia_disponivel: float) -> dict:
    minutos = round((float(kwh_restante) / float(potencia_disponivel)) * 60)
    return {"resultado": f"Estimativa de {minutos} minutos para completar a carga."}


FUNCOES_DISPONIVEIS = {
    "calcular_preco": calcular_preco,
    "calcular_demanda": calcular_demanda,
    "calcular_estimativa": calcular_estimativa,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calcular_preco",
            "description": "Calcula o custo financeiro da recarga com base no consumo e tarifa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kwh_consumido": {"type": "number"},
                    "tarifa": {"type": "number"}
                },
                "required": ["kwh_consumido", "tarifa"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_demanda",
            "description": "Analisa a distribuicao de carga no eletroposto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "carregadores_ativos": {"type": "integer"},
                    "potencia_total": {"type": "number"}
                },
                "required": ["carregadores_ativos", "potencia_total"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_estimativa",
            "description": "Calcula o tempo restante para carga total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kwh_restante": {"type": "number"},
                    "potencia_disponivel": {"type": "number"}
                },
                "required": ["kwh_restante", "potencia_disponivel"]
            }
        }
    }
]


def novo_historico(model_name: str) -> list:
    dados_texto = formatar_dados_dinamicos(DADOS_SESSAO)
    return [{"role": "system", "content": SYSTEM_PROMPT.format(dados_dinamicos=dados_texto)}]


def responder_legado(mensagem_usuario: str, historico: list, model_name: str) -> dict:
    """Reproduz exatamente o fluxo manual de function-calling da Sprint 2.
    Recebe e devolve o `historico` (lista de mensagens), para permitir
    conversas multi-turno chamando a funcao repetidamente com o mesmo
    historico (equivalente ao `historico_conversa` global do app.py original).
    Retorna {"response": str, "tokens_prompt": int, "tokens_completion": int, "latencia_s": float}.
    """
    historico.append({"role": "user", "content": mensagem_usuario})

    t0 = time.perf_counter()
    tokens_prompt = 0
    tokens_completion = 0

    response = client.chat.completions.create(
        model=model_name,
        messages=historico,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.3,
        top_p=0.9,
        max_tokens=900,
    )
    if response.usage:
        tokens_prompt += response.usage.prompt_tokens
        tokens_completion += response.usage.completion_tokens

    mensagem = response.choices[0].message

    if mensagem.tool_calls:
        historico.append(mensagem)
        for tool_call in mensagem.tool_calls:
            func_name = tool_call.function.name
            func = FUNCOES_DISPONIVEIS.get(func_name)
            args = json.loads(tool_call.function.arguments)
            resultado = func(**args)
            historico.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(resultado)
            })

        response_final = client.chat.completions.create(
            model=model_name,
            messages=historico,
            temperature=0.3,
            top_p=0.9,
            max_tokens=900,
        )
        if response_final.usage:
            tokens_prompt += response_final.usage.prompt_tokens
            tokens_completion += response_final.usage.completion_tokens

        final_content = response_final.choices[0].message.content
        historico.append({"role": "assistant", "content": final_content})
        latencia = time.perf_counter() - t0
        return {
            "response": final_content,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "latencia_s": round(latencia, 2),
        }

    historico.append({"role": "assistant", "content": mensagem.content})
    latencia = time.perf_counter() - t0
    return {
        "response": mensagem.content,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "latencia_s": round(latencia, 2),
    }
