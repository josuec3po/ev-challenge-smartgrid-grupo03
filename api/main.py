from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI(title="GoodWe API - SmartGrid EV")

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

# BASE MODEL ---------------------------------------------------------------------
# A biblioteca Pydantic usa o BaseModel para definir o contrato e esquema de dados que a API aceita receber via JSON.
# --------------------------------------------------------------------------------
# 1. Validação de Tipos: Se o Flet enviar uma string ("cem") ou esquecer o campo, 
# o FastAPI rejeita a requisição imediatamente com um erro 422 Unprocessable Entity. 
# Isso impede que o seu código Python quebre com exceções não tratadas no meio da execução
# --------------------------------------------------------------------------------
# 2. Conversão Automática (Parsing): Transforma o JSON bruto que chega pela 
# rede em um objeto Python manipulável. Em vez de fazer filtros manuais, 
# você acessa o valor diretamente com dados.kwh_acumulado.
# --------------------------------------------------------------------------------
# 3. Auto-documentação: O Pydantic alimenta a documentação interativa em /docs. 
# É por causa desse modelo que o Swagger sabe exatamente qual estrutura de JSON mostrar 
# como exemplo para testes

class ReciboRequest(BaseModel):
    kwh_acumulado: float

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