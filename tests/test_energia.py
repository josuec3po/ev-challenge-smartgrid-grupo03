"""
Testes do módulo de energia e das rotas da API.
Execute na raiz do repositório: python -m pytest
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from energia import assistente, config, despacho, kpis, monitoramento

cliente = TestClient(app)


@pytest.fixture(scope="module")
def dia():
    return {e: despacho.simular(e, "ensolarado") for e in despacho.ESTRATEGIAS}


# ── Física e restrições ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("estrategia", despacho.ESTRATEGIAS)
def test_balanco_de_potencia_fecha(dia, estrategia):
    # solar + bateria + rede = loja + carros, em todo passo
    for p in dia[estrategia]["serie"]:
        oferta = p["solar_kw"] + p["bateria_kw"] + p["rede_kw"]
        demanda = p["carga_kw"] + p["ve_kw"]
        assert oferta == pytest.approx(demanda, abs=0.01)


@pytest.mark.parametrize("estrategia", despacho.ESTRATEGIAS)
def test_respeita_demanda_contratada(dia, estrategia):
    pico = max(p["rede_kw"] for p in dia[estrategia]["serie"])
    assert pico <= config.DEMANDA_CONTRATADA_KW + 0.01


def test_bateria_dentro_dos_limites(dia):
    socs = [p["soc"] for p in dia["inteligente"]["serie"]]
    assert min(socs) >= config.BATERIA["soc_min"] - 1e-6
    assert max(socs) <= config.BATERIA["soc_max"] + 1e-6


def test_nenhum_carro_recebe_mais_que_o_pedido(dia):
    for s in dia["inteligente"]["sessoes"]:
        assert s["entregue_kwh"] <= s["energia_solicitada_kwh"] + 0.01


def test_simulacao_e_reprodutivel():
    a = despacho.simular("inteligente", "parcial", semente=7)
    b = despacho.simular("inteligente", "parcial", semente=7)
    assert a["serie"] == b["serie"]


# ── Ganhos do algoritmo ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("clima", list(config.CLIMAS))
def test_inteligente_reduz_custo_e_ponta(clima):
    r = {e: despacho.simular(e, clima) for e in despacho.ESTRATEGIAS}
    base, basico, smart = (kpis.calcular_kpis(r[e]) for e in despacho.ESTRATEGIAS)
    assert smart["custo_medio_kwh_rs"] < basico["custo_medio_kwh_rs"] < base["custo_medio_kwh_rs"]
    assert smart["energia_rede_ponta_kwh"] < base["energia_rede_ponta_kwh"]
    assert smart["sessoes_concluidas"] >= base["sessoes_concluidas"]


def test_tarifa_branca():
    assert config.posto_tarifario(19) == "ponta"
    assert config.posto_tarifario(17.5) == "intermediario"
    assert config.posto_tarifario(21.5) == "intermediario"
    assert config.posto_tarifario(12) == "fora_ponta"


# ── Monitoramento e assistente ─────────────────────────────────────────────────────────
def test_detecta_falha_de_string():
    normal = monitoramento.gerar_alertas(despacho.simular("inteligente", "ensolarado"))
    falha = monitoramento.gerar_alertas(despacho.simular("inteligente", "ensolarado", falha_string=True))
    assert not any(a["nivel"] == "critico" for a in normal)
    assert any(a["nivel"] == "critico" and a["tipo"] == "solar" for a in falha)


@pytest.mark.parametrize("pergunta, intencao", [
    ("Quanto economizamos hoje?", "economia"),
    ("Quanto de CO2 evitamos?", "co2"),
    ("Como está a bateria?", "bateria"),
    ("Qual o melhor horário pra carregar?", "horario"),
    ("Tem algum alerta?", "alertas"),
])
def test_intencoes_do_assistente(pergunta, intencao):
    assert assistente.identificar_intencao(pergunta) == intencao


def test_formatacao_em_reais():
    assert assistente.brl(98433.2, 0) == "R$ 98.433"
    assert assistente.brl(0.62) == "R$ 0,62"


# ── API ────────────────────────────────────────────────────────────────────────────────
def test_rota_comparativo():
    r = cliente.get("/energia/comparativo", params={"clima": "ensolarado"})
    assert r.status_code == 200
    assert r.json()["ganhos"]["reducao_custo_pct"] > 30


def test_rota_assistente_sem_llm(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = cliente.post("/energia/assistente", json={"pergunta": "quanto economizamos?"})
    assert r.status_code == 200
    assert r.json()["fonte"] == "regras"
    assert "R$" in r.json()["resposta"]


def test_rota_agora_e_totem():
    assert cliente.get("/energia/agora", params={"hora": "12:00"}).json()["solar_kw"] > 0
    assert "energia_agora" in cliente.get("/detectar-veiculo").json()


def test_rotas_antigas_continuam_funcionando():
    assert cliente.get("/recalcular-potencia", params={"num_carros": 2, "potencia_max_carro": 22}).json() == {"potencia_real": 22}
    assert cliente.post("/gerar-recibo", json={"kwh_acumulado": 10}).json()["total_rs"] == pytest.approx(23.1)


def test_dashboard_e_servido():
    r = cliente.get("/dashboard")
    assert r.status_code == 200
    assert "GoodWe" in r.text
