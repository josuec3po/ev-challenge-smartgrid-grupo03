"""
Geração dos perfis de um dia de operação: sol, consumo da loja e chegada de VEs.

Cada perfil é determinístico para uma mesma `semente`, o que permite repetir
um cenário no vídeo, nos testes e no README e obter os mesmos números.
"""

import math
import random

from energia import config

# Mesma frota usada na API do totem (modelo, química, capacidade e potência AC)
FROTA = [
    ("BYD Dolphin", 44.9, 7.0),
    ("VW ID.4 (Pro)", 77.0, 11.0),
    ("GWM Ora 03 (Skin)", 48.0, 11.0),
    ("Volvo XC40 Recharge", 78.0, 11.0),
    ("BYD Dolphin Plus", 60.5, 7.0),
    ("BYD Seal", 82.5, 11.0),
    ("Renault Megane E-Tech", 60.0, 22.0),
    ("Porsche Taycan", 93.4, 22.0),
    ("Audi Q8 e-tron", 114.0, 22.0),
    ("Peugeot e-208 GT", 50.0, 11.0),
    ("Hyundai Ioniq 5", 77.4, 11.0),
    ("Nissan Leaf", 40.0, 6.6),
]

# Picos de chegada ao posto: manhã, almoço e fim de tarde (hora, desvio, peso)
PICOS_CHEGADA = [(8.0, 1.0, 0.30), (12.5, 1.2, 0.30), (18.0, 1.3, 0.40)]


def hora_do_passo(passo: int) -> float:
    return passo * config.DT_H


def curva_ceu_limpo(hora: float) -> float:
    """Fração (0–1) da potência pico em céu limpo, nascer 6h e pôr do sol 18h."""
    if hora <= 6 or hora >= 18:
        return 0.0
    return math.sin(math.pi * (hora - 6) / 12) ** 1.25


def gerar_solar(clima: str = "ensolarado", semente: int = 42, falha_string: bool = False) -> list[float]:
    """
    Potência fotovoltaica (kW) em cada passo de 15 minutos.
    `falha_string` derruba metade do arranjo entre 11h e 14h (string desconectada),
    para demonstrar o alerta do monitoramento.
    """
    rng = random.Random(semente)
    p = config.CLIMAS[clima]
    pico = config.SOLAR["potencia_pico_kwp"] * config.SOLAR["performance_ratio"]
    nuvem = p["fator"]
    perfil = []
    for passo in range(config.PASSOS_DIA):
        # passeio aleatório suave: nuvens não somem de um passo para o outro
        nuvem += rng.uniform(-p["variacao"], p["variacao"]) * 0.5
        nuvem = min(1.0, max(0.05, 0.7 * nuvem + 0.3 * p["fator"]))
        h = hora_do_passo(passo)
        kw = pico * curva_ceu_limpo(h) * nuvem
        if falha_string and 11 <= h < 14:
            kw *= 0.5
        perfil.append(round(min(kw, config.INVERSOR["potencia_nominal_kw"]), 3))
    return perfil


def gerar_solar_esperado(clima: str = "ensolarado") -> list[float]:
    """
    Geração esperada para o clima previsto (céu limpo x fator de nebulosidade).
    Funciona como a "previsão do tempo" do sistema e como referência para
    detectar baixo desempenho dos painéis.
    """
    pico = config.SOLAR["potencia_pico_kwp"] * config.SOLAR["performance_ratio"]
    fator = config.CLIMAS[clima]["fator"]
    return [round(pico * curva_ceu_limpo(hora_do_passo(p)) * fator, 3) for p in range(config.PASSOS_DIA)]


def gerar_carga_base(semente: int = 42) -> list[float]:
    """Consumo da loja de conveniência, iluminação e climatização (kW)."""
    rng = random.Random(semente + 1)
    perfil = []
    for passo in range(config.PASSOS_DIA):
        h = hora_do_passo(passo)
        base = 3.0
        if 7 <= h < 22:
            base += 4.0 + 2.5 * math.sin(math.pi * (h - 7) / 15)   # climatização no meio do dia
        if h >= 17.5 or h < 6:
            base += 1.5                                            # iluminação da cobertura
        perfil.append(round(base * rng.uniform(0.92, 1.08), 3))
    return perfil


def gerar_sessoes(qtd: int = 24, semente: int = 42) -> list[dict]:
    """
    Sessões de recarga do dia. Cada motorista informa (ou o app prevê) o horário
    de saída: é essa flexibilidade que o despacho inteligente aproveita.
    """
    rng = random.Random(semente + 2)
    sessoes = []
    for i in range(qtd):
        centro, desvio, _ = rng.choices(PICOS_CHEGADA, weights=[p[2] for p in PICOS_CHEGADA])[0]
        chegada_h = min(22.5, max(6.0, rng.gauss(centro, desvio)))
        permanencia_h = rng.choice([0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0])
        modelo, capacidade, p_max = rng.choice(FROTA)
        soc_ini = rng.uniform(0.15, 0.50)
        soc_alvo = rng.choice([0.80, 0.80, 0.90, 1.00])
        p_ve = min(p_max, config.CARREGADOR["potencia_max_kw"])
        # o app do posto só aceita o que é fisicamente possível no tempo de permanência
        energia = round(min(capacidade * (soc_alvo - soc_ini), p_ve * permanencia_h * 0.9), 2)

        chegada = int(chegada_h / config.DT_H)
        saida = min(config.PASSOS_DIA, chegada + max(2, int(permanencia_h / config.DT_H)))
        sessoes.append({
            "id": i + 1,
            "veiculo": modelo,
            "capacidade_kwh": capacidade,
            "potencia_max_kw": p_ve,
            "chegada": chegada,
            "saida": saida,
            "energia_solicitada_kwh": energia,
        })
    sessoes.sort(key=lambda s: s["chegada"])
    return sessoes


def alocar_carregadores(sessoes: list[dict]) -> list[dict]:
    """
    Fila FIFO dos pontos HCA G2. Quem chega com todos ocupados espera; se o
    carregador só liberar depois do horário de saída, o motorista desiste.
    A alocação é a mesma em todas as estratégias, para a comparação ser justa.
    """
    livre_em = [0] * config.CARREGADOR["quantidade"]
    for s in sessoes:
        idx = min(range(len(livre_em)), key=lambda i: livre_em[i])
        inicio = max(s["chegada"], livre_em[idx])
        if inicio >= s["saida"]:
            s["carregador"], s["inicio"] = None, None
            continue
        s["carregador"], s["inicio"] = idx + 1, inicio
        livre_em[idx] = s["saida"]
    return sessoes
