from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from api.pagamento import process_payment, PaymentError
from api.pagamentos.router import router as router_pagamentos
import random
import datetime
import json
import os

app = FastAPI(title="GoodWe API - SmartGrid EV")

# Módulo de pagamentos: POST /pagamentos, GET /pagamentos/{id}, webhook.
# A rota antiga POST /pagamento continua funcionando (ver mais abaixo),
# mas está marcada como deprecated.
app.include_router(router_pagamentos)

# Constantes de Negócio
GW22K = 22
VALOR_ENERGIA = 1.70

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

class ReciboRequest(BaseModel):
    kwh_acumulado: float

class PagamentoRequest(BaseModel):
    amount: float
    method: str = "credit_card"

# Novo feature
class BancoDadosRequest(BaseModel):
    id_sessao: int
    veiculo: str
    tipo_carregador: str
    energia_kWh: float
    tempo_min: int
    custo_total: float
    status: str
    

@app.get("/detectar-veiculo")
def detectar_veiculo():
    carro = random.choice(CARROS)
    num_carros = random.randint(1, 4)
    p_max = carro["potencia_max_ac"]
    
    # Lógica de balanceamento extraída do seu código original
    p_real = min(GW22K, int(p_max), 50 // num_carros)
    
    return {
        "carro": carro,
        "numero_carros": num_carros,
        "potencia_real": p_real
    }

@app.get("/recalcular-potencia")
def recalcular_potencia(num_carros: int, potencia_max_carro: float):
    if num_carros == 0:
        num_carros = 1
    p_real = min(GW22K, int(potencia_max_carro), 50 // num_carros)
    return {"potencia_real": p_real}

@app.post("/gerar-recibo")
def gerar_recibo(dados: ReciboRequest):
    custo = dados.kwh_acumulado * VALOR_ENERGIA
    taxa = 5.0
    subtotal = custo + taxa
    imposto = subtotal * 0.05
    total = subtotal + imposto
    
    return {
        "consumo_rs": custo,
        "taxa_rs": taxa,
        "imposto_rs": imposto,
        "total_rs": total
    }

@app.post("/pagamento", deprecated=True)
def gerar_pagamento(dados: PagamentoRequest):
    """
    OBSOLETA — mantida só para não quebrar o totem durante a migração.

    Problemas desta rota, resolvidos em POST /pagamentos:
      - sem idempotência: dois cliques cobram duas vezes
      - resultado aleatório (10% de falha), impossível de demonstrar
      - valor em float, sem vínculo com a sessão, sem persistência
      - síncrona: não comporta Pix, que confirma por webhook

    Migre o totem para POST /pagamentos e remova esta rota.
    """
    try:
        return process_payment(dados.amount, dados.method)
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 2. A Rota de Persistência
@app.post("/salvar-historico")
def salvar_historico(dados: BancoDadosRequest):
    
    
    hora_agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Converte o objeto Pydantic para um dicionário Python
    novo_registro = dados.model_dump() # Se usar uma versão mais antiga do Pydantic, troque por dados.dict()
    novo_registro["data_hora"] = hora_agora # Injeta a data gerada pela API
    
    caminho_arquivo = "database.json"
    historico_atual = []
    
    # Evita crash se o arquivo não existir ou estiver vazio)
    if os.path.exists(caminho_arquivo):
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                historico_atual = json.load(f)
        except json.JSONDecodeError:
            historico_atual = [] # Se o JSON estiver corrompido, força uma nova lista
            
    # Passo C: Atualização da lista na memória RAM
    historico_atual.append(novo_registro)
    
    # Sobrescreve arquivo com a lista nova, formatada e indentada)
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(historico_atual, f, indent=4, ensure_ascii=False)
        
    return {"mensagem": "Sessão salva com sucesso!", "total_registros": len(historico_atual)}