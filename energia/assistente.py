"""
Assistente virtual do eletroposto.

Responde em português perguntas do operador ou do motorista usando os dados
da simulação. Funciona offline por regras (intenções por palavra-chave). Se a
variável GROQ_API_KEY existir, a pergunta e os indicadores do dia são enviados
ao mesmo provedor de LLM usado no chatbot ChargeGrid AI (disciplina de IA),
que redige a resposta; se a chamada falhar, volta para as regras.
"""

import json
import os
import unicodedata

import requests

from energia import config

URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"
MODELO_GROQ = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def brl(valor: float, casas: int = 2) -> str:
    """Formata em reais no padrão brasileiro: R$ 1.234,56."""
    texto = f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


INTENCOES = {
    "economia": ["econom", "custo", "gasto", "dinheiro", "conta", "r$", "reais", "margem", "lucro"],
    "co2": ["co2", "carbono", "emiss", "sustent", "ambient", "arvore", "verde"],
    "bateria": ["bateria", "lynx", "soc", "armazen"],
    "solar": ["solar", "sol", "painel", "paineis", "geracao", "gerou", "inversor"],
    "horario": ["horario", "hora", "quando", "barato", "melhor momento", "tarifa"],
    "alertas": ["alerta", "problema", "falha", "erro", "aviso", "manutencao"],
    "recarga": ["carro", "veiculo", "recarga", "sessao", "sessoes", "fila", "carregador"],
}


def identificar_intencao(pergunta: str) -> str:
    texto = _normalizar(pergunta)
    pontos = {nome: sum(1 for p in palavras if p in texto) for nome, palavras in INTENCOES.items()}
    melhor = max(pontos, key=pontos.get)
    return melhor if pontos[melhor] > 0 else "ajuda"


def responder_por_regras(intencao: str, kpis: dict, comparacao: dict, alertas: list[dict], serie: list[dict]) -> str:
    if intencao == "economia":
        return (f"Hoje a energia custou {brl(kpis['custo_energia_rs'])} ({brl(kpis['custo_medio_kwh_rs'])}/kWh). "
                f"Com o gerenciamento GoodWe a conta ficou {comparacao['reducao_custo_pct']:.0f}% menor que a de "
                f"um posto só com a rede, cerca de {brl(comparacao['economia_ano_rs'], 0)} por ano.")
    if intencao == "co2":
        return (f"Os {kpis['km_eletricos']} km rodados com a energia de hoje evitaram "
                f"{kpis['co2_evitado_kg']:.0f} kg de CO2 em relação a carros a gasolina. "
                f"Mantido o ano todo, equivale ao que {kpis['arvores_equivalentes_ano']} árvores absorvem.")
    if intencao == "bateria":
        socs = [p["soc"] for p in serie if p["soc"] is not None]
        if not socs:
            return "Esse cenário não tem bateria: é o posto convencional, só com a rede."
        return (f"A bateria Lynx terminou o dia com {100 * socs[-1]:.0f}% e chegou a "
                f"{100 * max(socs):.0f}% antes da ponta. Ela fez {kpis['ciclos_bateria']} ciclo(s) "
                f"e cobriu a maior parte da loja entre 18h e 21h.")
    if intencao == "solar":
        return (f"Os painéis geraram {kpis['energia_solar_kwh']:.0f} kWh, "
                f"{kpis['autoconsumo_solar_pct']:.0f}% consumidos no próprio posto. "
                f"{kpis['energia_ve_solar_kwh']:.0f} kWh foram direto para os carros.")
    if intencao == "horario":
        return (f"O mais barato é carregar entre 22h e 17h (fora de ponta, {brl(config.TARIFAS['fora_ponta'])}/kWh), "
                f"principalmente entre 10h e 15h, quando sobra energia solar. Evite 18h–21h: a rede custa "
                f"{brl(config.TARIFAS['ponta'])}/kWh.")
    if intencao == "alertas":
        if not alertas:
            return "Nenhum alerta hoje: geração, bateria e demanda dentro do esperado."
        criticos = [a for a in alertas if a["nivel"] == "critico"]
        principal = (criticos or alertas)[0]
        return (f"Há {len(alertas)} alerta(s), {len(criticos)} crítico(s). O principal às {principal['hora']}: "
                f"{principal['mensagem']} Sugestão: {principal['acao']}")
    if intencao == "recarga":
        return (f"{kpis['sessoes_atendidas']} de {kpis['sessoes_total']} motoristas foram atendidos e "
                f"{kpis['sessoes_concluidas']} saíram com a carga completa. Foram entregues "
                f"{kpis['energia_ve_kwh']:.0f} kWh ({kpis['atendimento_demanda_pct']:.0f}% do pedido).")
    return ("Posso falar sobre economia, CO2 evitado, bateria, geração solar, melhor horário para carregar, "
            "alertas e sessões de recarga. Experimente: \"quanto economizamos hoje?\"")


def _responder_llm(pergunta: str, contexto: dict) -> str | None:
    chave = os.getenv("GROQ_API_KEY")
    if not chave:
        return None
    sistema = ("Você é o assistente do eletroposto GoodWe (inversor ET, bateria Lynx, carregadores HCA G2). "
               "Responda em português, em até 3 frases, usando SOMENTE os dados do JSON. "
               "Se o dado não estiver no JSON, diga que não sabe.")
    try:
        resp = requests.post(URL_GROQ, timeout=15, headers={"Authorization": f"Bearer {chave}"}, json={
            "model": MODELO_GROQ,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": f"Dados: {json.dumps(contexto, ensure_ascii=False)}\n\nPergunta: {pergunta}"},
            ],
        })
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError):
        return None


def responder(pergunta: str, kpis: dict, comparacao: dict, alertas: list[dict], serie: list[dict]) -> dict:
    intencao = identificar_intencao(pergunta)
    contexto = {"kpis": kpis, "comparacao": comparacao, "alertas": alertas[:5]}
    texto = _responder_llm(pergunta, contexto)
    fonte = "llm"
    if texto is None:
        texto = responder_por_regras(intencao, kpis, comparacao, alertas, serie)
        fonte = "regras"
    return {"pergunta": pergunta, "intencao": intencao, "resposta": texto, "fonte": fonte}
