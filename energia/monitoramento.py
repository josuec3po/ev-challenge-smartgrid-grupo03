"""
Monitoramento inteligente: transforma a série medida em alertas acionáveis,
no mesmo espírito dos avisos do SEMS Portal da GoodWe.
"""

from energia import config


def gerar_alertas(resultado: dict) -> list[dict]:
    serie = resultado["serie"]
    alertas = []

    def alerta(hora, nivel, tipo, mensagem, acao):
        alertas.append({"hora": hora, "nivel": nivel, "tipo": tipo, "mensagem": mensagem, "acao": acao})

    # 1) Desempenho fotovoltaico: compara a geração real com a prevista para o clima
    if resultado["estrategia"] != "convencional":
        janela = 4  # 1 hora
        em_falha = False
        for i in range(0, len(serie) - janela):
            bloco = serie[i:i + janela]
            previsto = sum(p["solar_previsto_kw"] for p in bloco)
            real = sum(p["solar_disponivel_kw"] for p in bloco)
            if previsto < 8.0:          # ignora nascer e pôr do sol
                continue
            razao = real / previsto
            if razao < 0.65 and not em_falha:
                em_falha = True
                alerta(bloco[0]["hora"], "critico", "solar",
                       f"Geração {100 * (1 - razao):.0f}% abaixo do previsto para o clima.",
                       "Verificar strings/MPPT no inversor ET e sujeira nos módulos.")
            elif razao >= 0.85:
                em_falha = False

    # 2) Demanda próxima do contrato com a distribuidora
    perto = [p for p in serie if p["rede_kw"] >= 0.95 * config.DEMANDA_CONTRATADA_KW]
    if perto:
        maior = max(perto, key=lambda p: p["rede_kw"])
        alerta(maior["hora"], "aviso", "demanda",
               f"{len(perto) * config.PASSO_MIN} min perto do limite de {config.DEMANDA_CONTRATADA_KW:.0f} kW "
               f"(máximo {maior['rede_kw']:.1f} kW às {maior['hora']}).",
               "O balanceamento segurou os HCA G2 no limite; avaliar reserva de horário pelo app.")

    # 3) Bateria baixa entrando no horário de ponta
    for p in serie:
        if p["hora"] == "18:00" and p["soc"] is not None and p["soc"] < 0.5:
            alerta(p["hora"], "aviso", "bateria",
                   f"Bateria Lynx com {100 * p['soc']:.0f}% no início da ponta.",
                   "Antecipar a recarga pela rede no fora de ponta de amanhã.")

    # 4) Exportação alta: energia vendida barato que poderia ter sido usada
    exportado = sum(max(0.0, -p["rede_kw"]) for p in serie) * config.DT_H
    if exportado > 20:
        alerta("--", "info", "solar",
               f"{exportado:.0f} kWh injetados na rede a R$ {config.TARIFA_INJECAO:.2f}/kWh.".replace(".", ",", 1),
               "Oferecer desconto para recarga no meio do dia e aproveitar o excedente.")

    # 5) Motoristas que saíram sem a carga pedida
    for s in resultado["sessoes"]:
        if s["inicio"] is None:
            alerta(_hora(s["chegada"]), "aviso", "fila",
                   f"{s['veiculo']} desistiu: todos os carregadores ocupados.",
                   "Avaliar mais um ponto HCA G2 ou reserva antecipada pelo app.")
        elif not s["concluida"]:
            falta = s["energia_solicitada_kwh"] - s["entregue_kwh"]
            alerta(_hora(s["saida"]), "info", "recarga",
                   f"{s['veiculo']} saiu faltando {falta:.1f} kWh.",
                   "Sugerir ao motorista um horário de saída mais tarde.")

    return sorted(alertas, key=lambda a: a["hora"])


def _hora(passo: int) -> str:
    minutos = passo * config.PASSO_MIN
    return f"{minutos // 60:02d}:{minutos % 60:02d}"
