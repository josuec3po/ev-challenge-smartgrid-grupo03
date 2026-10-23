"""
Indicadores de eficiência, custo e sustentabilidade de um dia simulado.
"""

from energia import config


def calcular_kpis(resultado: dict) -> dict:
    serie = resultado["serie"]
    sessoes = resultado["sessoes"]
    dt = config.DT_H

    solar = sum(p["solar_kw"] for p in serie) * dt
    importado = sum(max(0.0, p["rede_kw"]) for p in serie) * dt
    exportado = sum(max(0.0, -p["rede_kw"]) for p in serie) * dt
    ponta = sum(max(0.0, p["rede_kw"]) for p in serie if p["posto"] == "ponta") * dt
    consumo = sum(p["carga_kw"] + p["ve_kw"] for p in serie) * dt
    ve = sum(s["entregue_kwh"] for s in sessoes)
    ve_solar = sum(s["entregue_solar_kwh"] for s in sessoes)
    solicitado = sum(s["energia_solicitada_kwh"] for s in sessoes)

    custo_rede = sum(max(0.0, p["rede_kw"]) * p["tarifa"] for p in serie) * dt
    credito = exportado * config.TARIFA_INJECAO
    # energia que sobrou (ou faltou) na bateria em relação ao início do dia,
    # valorizada a tarifa fora de ponta, para não distorcer a comparação
    soc_final = resultado["bateria"]["soc_final"]
    delta_bat = 0.0
    if soc_final is not None:
        delta_bat = (soc_final - config.BATERIA["soc_inicial"]) * config.BATERIA["capacidade_kwh"]
    ajuste_bat = delta_bat * config.TARIFAS["fora_ponta"]
    custo_liquido = custo_rede - credito - ajuste_bat
    receita = ve * config.PRECO_VENDA_RECARGA

    km = ve / config.CONSUMO_VE_KWH_KM
    co2_rede = importado * config.FATOR_EMISSAO_REDE
    co2_gasolina = km * config.EMISSAO_GASOLINA_KG_KM
    co2_evitado = co2_gasolina - co2_rede

    concluidas = sum(1 for s in sessoes if s["concluida"])
    atendidas = sum(1 for s in sessoes if s["inicio"] is not None)

    return {
        "energia_solar_kwh": round(solar, 1),
        "energia_rede_kwh": round(importado, 1),
        "energia_exportada_kwh": round(exportado, 1),
        "energia_rede_ponta_kwh": round(ponta, 1),
        "consumo_total_kwh": round(consumo, 1),
        "energia_ve_kwh": round(ve, 1),
        "energia_ve_solar_kwh": round(ve_solar, 1),
        "atendimento_demanda_pct": round(100 * ve / solicitado, 1) if solicitado else 0.0,
        "sessoes_total": len(sessoes),
        "sessoes_atendidas": atendidas,
        "sessoes_concluidas": concluidas,
        "autoconsumo_solar_pct": round(100 * (solar - exportado) / solar, 1) if solar else 0.0,
        "autossuficiencia_pct": round(100 * (1 - importado / consumo), 1) if consumo else 0.0,
        "pico_demanda_kw": round(max(p["rede_kw"] for p in serie), 1),
        "custo_energia_rs": round(custo_liquido, 2),
        "custo_medio_kwh_rs": round(custo_liquido / consumo, 3) if consumo else 0.0,
        "receita_recarga_rs": round(receita, 2),
        "margem_rs": round(receita - custo_liquido, 2),
        "km_eletricos": round(km),
        "co2_rede_kg": round(co2_rede, 1),
        "co2_evitado_kg": round(co2_evitado, 1),
        "arvores_equivalentes_ano": round(co2_evitado * 365 / config.CO2_POR_ARVORE_KG_ANO),
        "ciclos_bateria": round(resultado["bateria"]["throughput_kwh"] / (2 * config.BATERIA["capacidade_kwh"]), 2),
    }


def comparar(resultados: dict[str, dict]) -> dict:
    """Ganhos da estratégia inteligente sobre a convencional (só rede)."""
    base = calcular_kpis(resultados["convencional"])
    smart = calcular_kpis(resultados["inteligente"])

    def reducao(chave):
        return round(100 * (base[chave] - smart[chave]) / base[chave], 1) if base[chave] else 0.0

    economia_dia = base["custo_energia_rs"] - smart["custo_energia_rs"]
    return {
        "reducao_custo_pct": reducao("custo_energia_rs"),
        "reducao_rede_pct": reducao("energia_rede_kwh"),
        "reducao_ponta_pct": reducao("energia_rede_ponta_kwh"),
        "reducao_co2_rede_pct": reducao("co2_rede_kg"),
        "economia_dia_rs": round(economia_dia, 2),
        "economia_ano_rs": round(economia_dia * 365, 2),
        "co2_rede_evitado_ano_kg": round((base["co2_rede_kg"] - smart["co2_rede_kg"]) * 365, 1),
    }
