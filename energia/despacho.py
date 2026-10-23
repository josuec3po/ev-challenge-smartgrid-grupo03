"""
Despacho de energia do eletroposto: decide, a cada 15 minutos, quanto cada VE
recebe, quando a bateria carrega ou descarrega e quanto vem (ou vai) para a rede.

Três estratégias são comparadas sobre o MESMO dia (mesmo sol, mesma loja,
mesmos carros):

- convencional: só rede elétrica, carga dividida igualmente (lógica da Sprint 3)
- solar_basico: painéis + bateria GoodWe, mas sem inteligência (autoconsumo guloso)
- inteligente:  painéis + bateria + algoritmo com previsão solar, tarifa branca,
                prioridade por prazo de saída (menor folga primeiro) e peak shaving
"""

import copy

from energia import config, perfis

ESTRATEGIAS = ("convencional", "solar_basico", "inteligente")


# ========================================================================================
# BATERIA
# ========================================================================================
class Bateria:
    def __init__(self, soc: float | None = None):
        b = config.BATERIA
        self.cap = b["capacidade_kwh"]
        self.p_max = b["potencia_max_kw"]
        self.energia = self.cap * (b["soc_inicial"] if soc is None else soc)
        self.throughput = 0.0

    @property
    def soc(self) -> float:
        return self.energia / self.cap

    def max_carga_kw(self) -> float:
        espaco = self.cap * config.BATERIA["soc_max"] - self.energia
        return max(0.0, min(self.p_max, espaco / (config.DT_H * config.BATERIA["eficiencia_carga"])))

    def max_descarga_kw(self) -> float:
        disponivel = self.energia - self.cap * config.BATERIA["soc_min"]
        return max(0.0, min(self.p_max, disponivel * config.BATERIA["eficiencia_descarga"] / config.DT_H))

    def carregar(self, kw: float) -> float:
        kw = min(kw, self.max_carga_kw())
        self.energia += kw * config.DT_H * config.BATERIA["eficiencia_carga"]
        self.throughput += kw * config.DT_H
        return kw

    def descarregar(self, kw: float) -> float:
        kw = min(kw, self.max_descarga_kw())
        self.energia -= kw * config.DT_H / config.BATERIA["eficiencia_descarga"]
        self.throughput += kw * config.DT_H
        return kw


# ========================================================================================
# PREVISÃO SOLAR
# ========================================================================================
def prever_solar(passo: int, solar_real: list[float], solar_previsto: list[float]) -> list[float]:
    """
    Corrige a previsão do tempo com o que os painéis realmente entregaram na
    última hora (persistência de nebulosidade). Devolve a previsão do passo
    atual até o fim do dia.
    """
    janela = range(max(0, passo - 4), passo)
    real = sum(solar_real[i] for i in janela)
    prev = sum(solar_previsto[i] for i in janela)
    correcao = min(1.3, max(0.3, real / prev)) if prev > 1.0 else 1.0
    return [p * correcao for p in solar_previsto[passo:]]


def sobra_solar_prevista_kwh(passo: int, previsao: list[float], carga: list[float]) -> float:
    """Sol previsto que ainda vai sobrar até as 17h depois de atender a loja."""
    limite = 17 * 60 // config.PASSO_MIN
    return sum(max(0.0, previsao[i] - carga[passo + i]) for i in range(len(previsao)) if passo + i < limite) * config.DT_H


# ========================================================================================
# ALOCAÇÃO DOS VEÍCULOS
# ========================================================================================
def _restante(s, t):
    return s["energia_solicitada_kwh"] - s["entregue_kwh"]


def _conectados(sessoes, t):
    return [s for s in sessoes if s["inicio"] is not None and s["inicio"] <= t < s["saida"] and _restante(s, t) > 1e-6]


def _limite_veiculo(s, t):
    return min(s["potencia_max_kw"], _restante(s, t) / config.DT_H)


def alocar_igual(conectados, t, disponivel_kw):
    """Regra da Sprint 3: divide a potência disponível igualmente entre os carros."""
    alocacao = {}
    restantes = list(conectados)
    while restantes and disponivel_kw > 1e-6:
        fatia = disponivel_kw / len(restantes)
        satisfeitos = [s for s in restantes if _limite_veiculo(s, t) <= fatia]
        if not satisfeitos:
            for s in restantes:
                alocacao[s["id"]] = fatia
            break
        for s in satisfeitos:
            alocacao[s["id"]] = _limite_veiculo(s, t)
            disponivel_kw -= alocacao[s["id"]]
            restantes.remove(s)
    return alocacao


def alocar_inteligente(conectados, t, posto, disponivel_kw, sobra_solar_kw):
    """
    1) Potência base, por ordem de menor folga (Least Laxity First):
       - fora de ponta: ritmo uniforme até o horário de saída;
       - ponta/intermediário: só o obrigatório para o carro não sair sem a carga
         (com margem de 20%, supondo que no futuro ele receba 80% do máximo).
    2) Potência extra: em fora de ponta, completa até o máximo do carro; em
       ponta/intermediário, só com sobra solar.
    """
    alocacao = {}
    ordem = sorted(conectados, key=lambda s: (s["saida"] - t) * config.DT_H - _restante(s, t) / s["potencia_max_kw"])

    for s in ordem:
        passos_rest = s["saida"] - t
        if posto == "fora_ponta":
            alvo = _restante(s, t) / (passos_rest * config.DT_H)
        else:
            futuro = 0.8 * s["potencia_max_kw"] * (passos_rest - 1) * config.DT_H
            alvo = max(_restante(s, t) - futuro, 0.0) / config.DT_H
        base = min(_limite_veiculo(s, t), alvo, disponivel_kw)
        alocacao[s["id"]] = base
        disponivel_kw -= base

    extra = disponivel_kw if posto == "fora_ponta" else min(disponivel_kw, max(0.0, sobra_solar_kw - sum(alocacao.values())))
    for s in ordem:
        if extra <= 1e-6:
            break
        add = min(_limite_veiculo(s, t) - alocacao[s["id"]], extra)
        alocacao[s["id"]] += add
        extra -= add
    return alocacao


# ========================================================================================
# SIMULAÇÃO DO DIA
# ========================================================================================
def simular(estrategia: str = "inteligente", clima: str = "ensolarado", semente: int = 42,
            qtd_sessoes: int = 24, falha_string: bool = False) -> dict:
    if estrategia not in ESTRATEGIAS:
        raise ValueError(f"Estratégia inválida: {estrategia}")

    solar = perfis.gerar_solar(clima, semente, falha_string)
    previsto = perfis.gerar_solar_esperado(clima)
    carga = perfis.gerar_carga_base(semente)
    sessoes = perfis.alocar_carregadores(perfis.gerar_sessoes(qtd_sessoes, semente))
    sessoes = copy.deepcopy(sessoes)
    for s in sessoes:
        s["entregue_kwh"] = 0.0
        s["entregue_solar_kwh"] = 0.0

    tem_gw = estrategia != "convencional"
    bateria = Bateria()
    limite = config.DEMANDA_CONTRATADA_KW
    serie = []

    for t in range(config.PASSOS_DIA):
        hora = t * config.DT_H
        posto = config.posto_tarifario(hora)
        pv = solar[t] if tem_gw else 0.0
        conectados = _conectados(sessoes, t)
        carga_bat_rede = 0.0

        if estrategia == "inteligente":
            previsao = prever_solar(t, solar, previsto)
            if posto == "fora_ponta" and hora < 17:
                # chegar às 17h com a bateria cheia: primeiro com o sol previsto,
                # o que faltar vem da rede no preço fora de ponta (R$ 0,62 → evita R$ 1,52)
                meta = bateria.cap * config.BATERIA["soc_max"]
                sobra = sobra_solar_prevista_kwh(t, previsao, carga) * config.FATOR_SOL_PARA_BATERIA
                deficit = meta - bateria.energia - sobra * config.BATERIA["eficiencia_carga"]
                passos_ate_17 = 17 * 60 // config.PASSO_MIN - t
                carga_bat_rede = min(bateria.max_carga_kw(), max(0.0, deficit) / (passos_ate_17 * config.DT_H))
            if posto == "fora_ponta":
                disponivel = limite + pv - carga[t] - carga_bat_rede
            else:
                disponivel = limite + pv - carga[t] + bateria.max_descarga_kw()
            alocacao = alocar_inteligente(conectados, t, posto, max(0.0, disponivel), pv - carga[t])
        else:
            disponivel = limite - carga[t]
            alocacao = alocar_igual(conectados, t, max(0.0, disponivel))

        ev = sum(alocacao.values())
        liquido = carga[t] + ev - pv          # >0 falta energia, <0 sobra solar
        bat_kw = 0.0                           # >0 descarga, <0 carga

        if estrategia == "solar_basico":
            # autoconsumo simples: guarda toda sobra, descarrega sempre que falta
            bat_kw = -bateria.carregar(-liquido) if liquido < 0 else bateria.descarregar(liquido)
        elif estrategia == "inteligente":
            if liquido < 0:
                bat_kw = -bateria.carregar(-liquido)
            elif posto == "ponta":
                bat_kw = bateria.descarregar(liquido)
            elif posto == "intermediario" and hora >= 21:
                # depois da ponta, o que sobrou na bateria ainda vale mais que a rede
                bat_kw = bateria.descarregar(liquido)
            elif liquido > limite:
                bat_kw = bateria.descarregar(liquido - limite)    # peak shaving
            if carga_bat_rede > 0 and carga_bat_rede > -bat_kw:
                bat_kw -= bateria.carregar(carga_bat_rede + bat_kw)

        rede = liquido - bat_kw
        # fração solar da recarga: o sol atende primeiro a loja, depois os carros
        frac_solar_ev = min(1.0, max(0.0, pv - carga[t]) / ev) if ev > 0 else 0.0
        for s in conectados:
            kwh = alocacao.get(s["id"], 0.0) * config.DT_H
            s["entregue_kwh"] += kwh
            s["entregue_solar_kwh"] += kwh * frac_solar_ev

        serie.append({
            "passo": t,
            "hora": f"{int(hora):02d}:{int(round((hora % 1) * 60)):02d}",
            "posto": posto,
            "tarifa": config.TARIFAS[posto],
            "solar_kw": round(pv, 3),
            "solar_previsto_kw": round(previsto[t], 3),
            "solar_disponivel_kw": round(solar[t], 3),
            "carga_kw": round(carga[t], 3),
            "ve_kw": round(ev, 3),
            "bateria_kw": round(bat_kw, 3),
            "rede_kw": round(rede, 3),
            "soc": round(bateria.soc, 4) if tem_gw else None,
            "ve_conectados": len(conectados),
        })

    for s in sessoes:
        s["entregue_kwh"] = round(s["entregue_kwh"], 3)
        s["entregue_solar_kwh"] = round(s["entregue_solar_kwh"], 3)
        s["concluida"] = s["inicio"] is not None and s["entregue_kwh"] >= s["energia_solicitada_kwh"] * 0.98

    return {
        "estrategia": estrategia,
        "clima": clima,
        "semente": semente,
        "serie": serie,
        "sessoes": sessoes,
        "bateria": {
            "soc_final": round(bateria.soc, 4) if tem_gw else None,
            "throughput_kwh": round(bateria.throughput, 2),
        },
    }
