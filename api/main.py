from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random
import uuid

app = FastAPI(title="GoodWe API - SmartGrid EV")

# ============================================================================
# Constantes de Negócio
# ============================================================================
GW22K = 22
VALOR_ENERGIA = 1.70
PASSO_SIMULACAO = 0.1  # incremento de tempo simulado a cada /tick

CARROS = [
    {"modelo": "BYD Dolphin (Entrada)",        "tipo": "LFP", "capacidade_kwh": 44.9,  "potencia_max_ac": 7.0},
    {"modelo": "VW ID.4 (Pro)",                "tipo": "NMC", "capacidade_kwh": 77.0,  "potencia_max_ac": 11.0},
    {"modelo": "GWM Ora 03 (Skin)",            "tipo": "LFP", "capacidade_kwh": 48.0,  "potencia_max_ac": 11.0},
    {"modelo": "Volvo XC40 Recharge",          "tipo": "NMC", "capacidade_kwh": 78.0,  "potencia_max_ac": 11.0},
    {"modelo": "BYD Dolphin Plus",             "tipo": "LFP", "capacidade_kwh": 60.5,  "potencia_max_ac": 7.0},
    {"modelo": "BYD Seal",                     "tipo": "LFP", "capacidade_kwh": 82.5,  "potencia_max_ac": 11.0},
    {"modelo": "GWM Ora 03 (GT)",              "tipo": "NMC", "capacidade_kwh": 63.0,  "potencia_max_ac": 11.0},
    {"modelo": "Renault Megane E-Tech",        "tipo": "NMC", "capacidade_kwh": 60.0,  "potencia_max_ac": 22.0},
    {"modelo": "Porsche Taycan (Perf. Plus)",  "tipo": "NMC", "capacidade_kwh": 93.4,  "potencia_max_ac": 22.0},
    {"modelo": "Audi Q8 e-tron (55)",          "tipo": "NMC", "capacidade_kwh": 114.0, "potencia_max_ac": 22.0},
    {"modelo": "Peugeot e-208 GT",             "tipo": "NMC", "capacidade_kwh": 50.0,  "potencia_max_ac": 11.0},
    {"modelo": "Hyundai Ioniq 5 (Top)",        "tipo": "NMC", "capacidade_kwh": 77.4,  "potencia_max_ac": 11.0},
    {"modelo": "BMW iX3 (M Sport)",            "tipo": "NMC", "capacidade_kwh": 80.0,  "potencia_max_ac": 11.0},
    {"modelo": "Nissan Leaf (Tekna)",          "tipo": "NMC", "capacidade_kwh": 40.0,  "potencia_max_ac": 6.6},
]

# ============================================================================
# Estado das sessões de carregamento (em memória — protótipo/simulação)
# ============================================================================
SESSOES: dict[str, dict] = {}


class ReciboRequest(BaseModel):
    kwh_acumulado: float


# ============================================================================
# Funções auxiliares de negócio (reutilizadas pelas rotas utilitárias e
# pelas rotas de sessão)
# ============================================================================
def _sortear_carro() -> dict:
    return random.choice(CARROS)


def _calcular_potencia_real(num_carros: int, potencia_max_carro: float) -> int:
    if num_carros <= 0:
        num_carros = 1
    return min(GW22K, int(potencia_max_carro), 50 // num_carros)


def _calcular_recibo(kwh_acumulado: float) -> dict:
    custo = kwh_acumulado * VALOR_ENERGIA
    taxa = 5.0
    subtotal = custo + taxa
    imposto = subtotal * 0.05
    total = subtotal + imposto

    return {
        "consumo_rs": custo,
        "taxa_rs": taxa,
        "imposto_rs": imposto,
        "total_rs": total,
    }


def _obter_sessao(sessao_id: str) -> dict:
    sessao = SESSOES.get(sessao_id)
    if sessao is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return sessao


def _sessao_publica(sessao: dict) -> dict:
    """Estado da sessão devolvido ao cliente (sem campos internos)."""
    return {
        "sessao_id": sessao["sessao_id"],
        "carro": sessao["carro"],
        "numero_carros": sessao["numero_carros"],
        "potencia_max_atual": sessao["potencia_max_atual"],
        "capacidade_atual": sessao["capacidade_atual"],
        "potencia_real": sessao["p_real_val"],
        "estado_carga": sessao["estado_carga"],
        "acumulo": sessao["acumulo"],
        "rodando": sessao["rodando"],
        "pausado": sessao["pausado"],
        "finalizado": sessao["finalizado"],
        "log_msg": sessao["log_msg"],
        "log_cor": sessao["log_cor"],
        "completo": sessao["finalizado"] and not sessao.get("parcial", False),
        "parcial": sessao.get("parcial", False),
        "recibo": sessao.get("recibo"),
    }


# ============================================================================
# Rotas utilitárias (mantidas por compatibilidade — GUIA_TECNICO.md)
# ============================================================================
@app.get("/detectar-veiculo")
def detectar_veiculo():
    carro = _sortear_carro()
    num_carros = random.randint(1, 4)
    p_real = _calcular_potencia_real(num_carros, carro["potencia_max_ac"])

    return {
        "carro": carro,
        "numero_carros": num_carros,
        "potencia_real": p_real,
    }


@app.get("/recalcular-potencia")
def recalcular_potencia(num_carros: int, potencia_max_carro: float):
    p_real = _calcular_potencia_real(num_carros, potencia_max_carro)
    return {"potencia_real": p_real}


@app.post("/gerar-recibo")
def gerar_recibo(dados: ReciboRequest):
    return _calcular_recibo(dados.kwh_acumulado)


# ============================================================================
# Rotas de sessão — toda a lógica do "loop de carregamento" que antes vivia
# no Totem agora é dona do estado e decide tudo aqui.
# ============================================================================
@app.post("/sessao/iniciar")
def iniciar_sessao():
    carro = _sortear_carro()
    num_carros = random.randint(1, 4)
    p_real = _calcular_potencia_real(num_carros, carro["potencia_max_ac"])

    sessao_id = str(uuid.uuid4())
    sessao = {
        "sessao_id": sessao_id,
        "carro": carro,
        "numero_carros": num_carros,
        "potencia_max_atual": carro["potencia_max_ac"],
        "capacidade_atual": carro["capacidade_kwh"],
        "p_real_val": p_real,
        "estado_carga": 0.0,
        "acumulo": 0.0,
        "rodando": False,
        "pausado": False,
        "finalizado": False,
        "parcial": False,
        "log_msg": "Veículo identificado — pronto para carregar",
        "log_cor": "verde",
        "recibo": None,
    }
    SESSOES[sessao_id] = sessao
    return _sessao_publica(sessao)


@app.get("/sessao/{sessao_id}")
def obter_sessao(sessao_id: str):
    return _sessao_publica(_obter_sessao(sessao_id))


@app.post("/sessao/{sessao_id}/iniciar-carga")
def iniciar_carga(sessao_id: str):
    sessao = _obter_sessao(sessao_id)
    sessao["estado_carga"] = float(random.randint(10, 50))
    sessao["acumulo"] = 0.0
    sessao["rodando"] = True
    sessao["pausado"] = False
    sessao["finalizado"] = False
    sessao["parcial"] = False
    sessao["recibo"] = None
    sessao["log_msg"] = "Iniciando sessão de recarga..."
    sessao["log_cor"] = "gw"
    return _sessao_publica(sessao)


@app.post("/sessao/{sessao_id}/tick")
def tick(sessao_id: str):
    sessao = _obter_sessao(sessao_id)

    if not sessao["rodando"] or sessao["finalizado"]:
        return _sessao_publica(sessao)

    if sessao["pausado"]:
        return _sessao_publica(sessao)

    # Flutuação de rede: com 15% de chance, um carro entra ou sai.
    if random.random() < 0.15:
        acao = random.choice(["entra", "sai"])
        if acao == "entra" and sessao["numero_carros"] < 5:
            sessao["numero_carros"] += 1
            sessao["log_msg"] = f'Novo carro na rede! Divisão de carga: {sessao["numero_carros"]} un.'
            sessao["log_cor"] = "alerta"
        elif acao == "sai" and sessao["numero_carros"] > 1:
            sessao["numero_carros"] -= 1
            sessao["log_msg"] = f'Veículo saiu. Carga liberada: {sessao["numero_carros"]} un.'
            sessao["log_cor"] = "verde"

        sessao["p_real_val"] = _calcular_potencia_real(
            sessao["numero_carros"], sessao["potencia_max_atual"]
        )

    p = sessao["p_real_val"]
    capacidade = sessao["capacidade_atual"]
    sessao["acumulo"] += p * PASSO_SIMULACAO
    sessao["estado_carga"] += (p * PASSO_SIMULACAO / capacidade) * 100

    if sessao["estado_carga"] >= 100:
        sessao["estado_carga"] = 100.0
        sessao["rodando"] = False
        sessao["finalizado"] = True
        sessao["parcial"] = False
        sessao["recibo"] = _calcular_recibo(sessao["acumulo"])
        sessao["log_msg"] = "Bateria 100% — recibo emitido"
        sessao["log_cor"] = "verde"

    return _sessao_publica(sessao)


@app.post("/sessao/{sessao_id}/pausar-retomar")
def pausar_retomar(sessao_id: str):
    sessao = _obter_sessao(sessao_id)
    sessao["pausado"] = not sessao["pausado"]
    if sessao["pausado"]:
        sessao["log_msg"] = "Recarga pausada"
        sessao["log_cor"] = "pausa"
    else:
        sessao["log_msg"] = f'Retomando... {sessao["p_real_val"]} kW'
        sessao["log_cor"] = "gw"
    return _sessao_publica(sessao)


@app.post("/sessao/{sessao_id}/parar")
def parar(sessao_id: str):
    sessao = _obter_sessao(sessao_id)
    sessao["rodando"] = False
    sessao["pausado"] = False
    sessao["finalizado"] = True
    sessao["parcial"] = True
    sessao["recibo"] = _calcular_recibo(sessao["acumulo"])
    sessao["log_msg"] = f'Interrompido em {sessao["estado_carga"]:.1f}% — recibo parcial'
    sessao["log_cor"] = "pausa"
    return _sessao_publica(sessao)


@app.post("/sessao/{sessao_id}/cancelar")
def cancelar(sessao_id: str):
    SESSOES.pop(sessao_id, None)
    return {"ok": True}
