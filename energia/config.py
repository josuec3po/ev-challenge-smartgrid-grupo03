"""
Parâmetros do eletroposto GoodWe simulado.

Todos os valores ficam centralizados aqui para que a simulação, a API e os
testes usem exatamente a mesma "planta". Os números de equipamentos seguem as
classes de produto da GoodWe usadas no desafio; tarifas e fatores de emissão
são valores de referência públicos (ver README, seção Referências).
"""

# ========================================================================================
# EQUIPAMENTOS GOODWE
# ========================================================================================
# Inversor híbrido trifásico (série ET): faz a ponte entre painéis, bateria e rede
INVERSOR = {
    "modelo": "GoodWe série ET (híbrido trifásico)",
    "quantidade": 2,
    "potencia_nominal_kw": 60.0,    # 2 x 30 kW em paralelo
    "eficiencia": 0.97,
}

# Arranjo fotovoltaico ligado ao inversor ET
SOLAR = {
    "potencia_pico_kwp": 66.0,      # 120 módulos de 550 Wp na cobertura das vagas (carport solar)
    "performance_ratio": 0.82,      # perdas de temperatura, sujeira, cabos
}

# Banco de baterias de alta tensão (família Lynx)
BATERIA = {
    "modelo": "GoodWe Lynx (alta tensão, LFP)",
    "capacidade_kwh": 65.6,         # 4 torres de 16,4 kWh (2 por inversor)
    "potencia_max_kw": 40.0,        # limitada pelos inversores ET
    "soc_min": 0.10,                # reserva para não degradar as células
    "soc_max": 0.95,
    "soc_inicial": 0.40,
    "eficiencia_carga": 0.96,
    "eficiencia_descarga": 0.96,
}

# Carregadores AC GoodWe HCA G2 (mesma constante GW22K da API)
CARREGADOR = {
    "modelo": "GoodWe HCA G2",
    "potencia_max_kw": 22.0,
    "quantidade": 6,
}

# Limite da instalação junto à distribuidora (mesmo limite de 50 kW da Sprint 3)
DEMANDA_CONTRATADA_KW = 50.0

# ========================================================================================
# TARIFA BRANCA (estrutura ANEEL, valores de referência em R$/kWh)
# ========================================================================================
TARIFAS = {
    "fora_ponta": 0.62,
    "intermediario": 0.98,
    "ponta": 1.52,
}
TARIFA_INJECAO = 0.42               # crédito por kWh exportado (SCEE / Lei 14.300)
PRECO_VENDA_RECARGA = 1.70          # mesmo VALOR_ENERGIA cobrado no totem


def posto_tarifario(hora: float) -> str:
    """Posto tarifário da Tarifa Branca para uma hora do dia (dias úteis)."""
    if 18 <= hora < 21:
        return "ponta"
    if 17 <= hora < 18 or 21 <= hora < 22:
        return "intermediario"
    return "fora_ponta"


# ========================================================================================
# SUSTENTABILIDADE
# ========================================================================================
FATOR_EMISSAO_REDE = 0.0385         # kg CO2/kWh — média anual do SIN (MCTI)
CONSUMO_VE_KWH_KM = 0.17            # consumo médio de um VE compacto/SUV
EMISSAO_GASOLINA_KG_KM = 0.170      # carro flex a gasolina C (~12 km/L, ~2,0 kg CO2/L)
CO2_POR_ARVORE_KG_ANO = 15.6        # absorção média de uma árvore de Mata Atlântica

# ========================================================================================
# SIMULAÇÃO
# ========================================================================================
PASSO_MIN = 15                      # resolução de 15 minutos (padrão de medição)
PASSOS_DIA = 24 * 60 // PASSO_MIN
DT_H = PASSO_MIN / 60

# parte da sobra solar prevista que o algoritmo conta como "vai para a bateria"
# (o resto tende a ir para os carros que chegam no meio do dia)
FATOR_SOL_PARA_BATERIA = 0.6

CLIMAS = {
    # fator médio de nebulosidade e variabilidade das nuvens
    "ensolarado": {"fator": 0.95, "variacao": 0.05},
    "parcial": {"fator": 0.70, "variacao": 0.25},
    "nublado": {"fator": 0.35, "variacao": 0.15},
}
