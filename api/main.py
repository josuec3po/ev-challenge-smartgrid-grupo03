from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum
from api.pagamento import process_payment, PaymentError
import random
import datetime
import json
import os
import uuid
import io
import base64
import qrcode
import time
from api.sessoes import (
    SessaoRecarga, CAMPOS_ORDENAVEIS,
    carregar_sessoes, salvar_sessoes,
    busca_linear_por_id, busca_linear_por_veiculo,
    insertion_sort, merge_sort,
    calcular_estatisticas, gerar_relatorio_texto,
)

app = FastAPI(title="GoodWe API - SmartGrid EV")

# Chave Pix fictícia usada apenas para a simulação do projeto
CHAVE_PIX_POSTO = "posto-goodwe@exemplo.com"
NOME_RECEBEDOR  = "POSTO GOODWE"
CIDADE_RECEBEDOR = "SAO PAULO"

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

class MetodoPagamento(str, Enum):
    credito = "credito"
    debito = "debito"
    pix = "pix"

class PagamentoRequest(BaseModel):
    amount: float
    method: MetodoPagamento

class PixRequest(BaseModel):
    amount: float

# Novo feature
class BancoDadosRequest(BaseModel):
    id_sessao: int
    veiculo: str
    tipo_carregador: str
    energia_kWh: float
    tempo_min: int
    custo_total: float
    status: str
    

def _tlv(id_campo: str, valor: str) -> str:
    """Monta um campo no formato TLV (ID + Tamanho + Valor) usado no padrão EMV do Pix."""
    tamanho = str(len(valor)).zfill(2)
    return f"{id_campo}{tamanho}{valor}"


def _calcular_crc16(payload: str) -> str:
    """CRC16-CCITT (falso), exigido no final de todo BR Code Pix."""
    polinomio = 0x1021
    resultado = 0xFFFF
    for byte in payload.encode("utf-8"):
        resultado ^= byte << 8
        for _ in range(8):
            if resultado & 0x8000:
                resultado = (resultado << 1) ^ polinomio
            else:
                resultado <<= 1
            resultado &= 0xFFFF
    return format(resultado, "04X")


def gerar_payload_pix(valor: float, id_transacao: str) -> str:
    """
    Monta o 'Pix Copia e Cola' (BR Code) seguindo o padrão EMV do Banco Central.
    Isso é o que vira o QR Code — qualquer app de banco consegue ler essa string.
    """
    merchant_account = _tlv("26", _tlv("00", "br.gov.bcb.pix") + _tlv("01", CHAVE_PIX_POSTO))

    payload_sem_crc = (
        _tlv("00", "01")                                   # Payload Format Indicator
        + merchant_account                                  # Dados da chave Pix
        + _tlv("52", "0000")                                 # Merchant Category Code
        + _tlv("53", "986")                                  # Moeda: Real (BRL)
        + _tlv("54", f"{valor:.2f}")                          # Valor da cobrança
        + _tlv("58", "BR")                                   # País
        + _tlv("59", NOME_RECEBEDOR[:25])                    # Nome do recebedor
        + _tlv("60", CIDADE_RECEBEDOR[:15])                  # Cidade do recebedor
        + _tlv("62", _tlv("05", id_transacao[:25]))           # Identificador da transação (txid)
        + "6304"                                             # ID + tamanho do campo de CRC
    )
    crc = _calcular_crc16(payload_sem_crc)
    return payload_sem_crc + crc


@app.post("/gerar-pix")
def gerar_pix(dados: PixRequest):
    if dados.amount <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido para gerar cobrança Pix.")

    id_transacao = str(uuid.uuid4())[:8].upper()
    payload = gerar_payload_pix(dados.amount, id_transacao)

    # Gera a imagem do QR Code em memória (sem salvar em disco) e converte para base64,
    # já pronta pra ser exibida direto num ft.Image no Flet.
    qr_img = qrcode.make(payload)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "payload": payload,
        "qr_code_base64": qr_base64,
        "id_transacao": id_transacao,
        "amount": dados.amount,
    }


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

@app.post("/pagamento")
def gerar_pagamento(dados: PagamentoRequest):
    try:
        return process_payment(dados.amount, dados.method.value)
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 2. A Rota de Persistência
# ─────────────────────────────────────────────────────────────────────────────
# SESSÕES: armazenamento, busca, ordenação, estatísticas e relatório
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/salvar-historico")
def salvar_historico(dados: BancoDadosRequest):
    print(f"[API] POST /salvar-historico -> sessão {dados.id_sessao}")
    sessoes = carregar_sessoes()
    nova = SessaoRecarga(
        **dados.model_dump(),
        data_hora=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    sessoes.append(nova)          # append -> O(1)
    salvar_sessoes(sessoes)
    return {"mensagem": "Sessão salva com sucesso!", "total_registros": len(sessoes)}


@app.get("/sessoes")
def listar_sessoes():
    print("[API] GET /sessoes -> listagem")
    sessoes = carregar_sessoes()
    return {"total": len(sessoes), "sessoes": [s.to_dict() for s in sessoes]}


@app.get("/sessoes/busca")
def buscar_sessao(id_sessao: int | None = None, veiculo: str | None = None):
    print(f"[API] GET /sessoes/busca -> id={id_sessao} veiculo={veiculo}")
    sessoes = carregar_sessoes()
    if id_sessao is not None:
        sessao, comparacoes = busca_linear_por_id(sessoes, id_sessao)
        achadas = [sessao] if sessao else []
    elif veiculo:
        achadas, comparacoes = busca_linear_por_veiculo(sessoes, veiculo)
    else:
        raise HTTPException(status_code=400, detail="Informe id_sessao ou veiculo.")
    return {
        "algoritmo": "Busca Linear", "complexidade": "O(n)",
        "comparacoes": comparacoes, "total_sessoes": len(sessoes),
        "sessoes": [s.to_dict() for s in achadas],
    }


@app.get("/sessoes/ordenar")
def ordenar_sessoes(campo: str = "energia_kWh", ordem: str = "asc", algoritmo: str = "insertion"):
    if campo not in CAMPOS_ORDENAVEIS:
        raise HTTPException(status_code=400, detail=f"Campo inválido. Use: {CAMPOS_ORDENAVEIS}")
    if algoritmo not in ("insertion", "merge"):
        raise HTTPException(status_code=400, detail="Algoritmo inválido (insertion ou merge).")

    print(f"[API] GET /sessoes/ordenar -> {algoritmo} por {campo} ({ordem})")
    sessoes = carregar_sessoes()
    if algoritmo == "insertion":
        func, nome, big_o = insertion_sort, "Insertion Sort", "O(n²)"
    else:
        func, nome, big_o = merge_sort, "Merge Sort", "O(n log n)"

    inicio = time.perf_counter()
    ordenadas, comparacoes = func(sessoes, campo, ordem == "desc")
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 3)

    return {
        "algoritmo": nome, "complexidade": big_o, "campo": campo, "ordem": ordem,
        "comparacoes": comparacoes, "tempo_ms": tempo_ms, "total_sessoes": len(sessoes),
        "sessoes": [s.to_dict() for s in ordenadas],
    }


@app.get("/estatisticas")
def estatisticas():
    print("[API] GET /estatisticas")
    return calcular_estatisticas(carregar_sessoes())


@app.get("/relatorio")
def relatorio():
    print("[API] GET /relatorio")
    return {"texto": gerar_relatorio_texto(carregar_sessoes())}


@app.post("/sessoes/popular")
def popular_sessoes(qtd: int = 8):
    """Gera sessões fictícias para agilizar a demonstração."""
    print(f"[API] POST /sessoes/popular -> {qtd} sessões")
    sessoes = carregar_sessoes()
    for _ in range(qtd):
        carro = random.choice(CARROS)
        energia = round(random.uniform(5, carro["capacidade_kwh"]), 2)
        potencia = min(GW22K, carro["potencia_max_ac"])
        tempo = max(1, int(energia / potencia * 60))
        total = round((energia * VALOR_ENERGIA + 5.0) * 1.05, 2)
        data = datetime.datetime.now() - datetime.timedelta(
            days=random.randint(0, 30), hours=random.randint(0, 23)
        )
        sessoes.append(SessaoRecarga(
            id_sessao=random.randint(10000, 99999),
            veiculo=carro["modelo"],
            tipo_carregador=f'{carro["potencia_max_ac"]} kW AC',
            energia_kWh=energia, tempo_min=tempo, custo_total=total,
            status=random.choice(["CONCLUIDO", "CONCLUIDO", "PARCIAL"]),
            data_hora=data.strftime("%d/%m/%Y %H:%M"),
        ))
    salvar_sessoes(sessoes)
    return {"mensagem": f"{qtd} sessões geradas.", "total_registros": len(sessoes)}