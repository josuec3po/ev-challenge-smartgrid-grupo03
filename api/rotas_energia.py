"""
Rotas de energia da Sprint 4: simulação do dia, comparação de estratégias,
monitoramento (alertas), leitura "ao vivo" e assistente virtual.
"""

import datetime
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from energia import assistente, config, despacho, kpis, monitoramento

router = APIRouter()

Estrategia = Literal["convencional", "solar_basico", "inteligente"]
Clima = Literal["ensolarado", "parcial", "nublado"]

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"


@lru_cache(maxsize=64)
def _simular(estrategia: str, clima: str, semente: int, falha_string: bool) -> dict:
    # o dia simulado é determinístico: guardar em cache deixa o dashboard instantâneo
    return despacho.simular(estrategia, clima, semente, falha_string=falha_string)


def _comparativo(clima: str, semente: int, falha_string: bool) -> dict:
    resultados = {e: _simular(e, clima, semente, falha_string) for e in despacho.ESTRATEGIAS}
    return {
        "kpis": {e: kpis.calcular_kpis(r) for e, r in resultados.items()},
        "ganhos": kpis.comparar(resultados),
    }


def leitura_atual(hora: datetime.time | None = None, clima: str = "ensolarado") -> dict:
    """
    Ponto da simulação inteligente correspondente ao horário informado. Sem
    horário, usa HORA_SIMULADA (modo demonstração, ex.: "12:30") ou o relógio.
    """
    if hora is None and os.getenv("HORA_SIMULADA"):
        hora = datetime.datetime.strptime(os.environ["HORA_SIMULADA"], "%H:%M").time()
    hora = hora or datetime.datetime.now().time()
    passo = (hora.hour * 60 + hora.minute) // config.PASSO_MIN
    ponto = _simular("inteligente", clima, 42, False)["serie"][passo]
    consumo = ponto["carga_kw"] + ponto["ve_kw"]
    solar_uso = min(ponto["solar_kw"], consumo)
    bateria_uso = max(0.0, ponto["bateria_kw"])
    return {
        **ponto,
        "fracao_solar_pct": round(100 * solar_uso / consumo, 1) if consumo else 0.0,
        "fracao_bateria_pct": round(100 * bateria_uso / consumo, 1) if consumo else 0.0,
        "fracao_rede_pct": round(100 * max(0.0, ponto["rede_kw"]) / consumo, 1) if consumo else 0.0,
    }


@router.get("/energia/configuracao")
def configuracao():
    return {
        "inversor": config.INVERSOR,
        "solar": config.SOLAR,
        "bateria": config.BATERIA,
        "carregador": config.CARREGADOR,
        "demanda_contratada_kw": config.DEMANDA_CONTRATADA_KW,
        "tarifas": config.TARIFAS,
        "fator_emissao_rede": config.FATOR_EMISSAO_REDE,
    }


@router.get("/energia/simulacao")
def simulacao(estrategia: Estrategia = "inteligente", clima: Clima = "ensolarado",
              semente: int = 42, falha_string: bool = False):
    resultado = _simular(estrategia, clima, semente, falha_string)
    return {**resultado, "kpis": kpis.calcular_kpis(resultado)}


@router.get("/energia/comparativo")
def comparativo(clima: Clima = "ensolarado", semente: int = 42, falha_string: bool = False):
    return _comparativo(clima, semente, falha_string)


@router.get("/energia/alertas")
def alertas(estrategia: Estrategia = "inteligente", clima: Clima = "ensolarado",
            semente: int = 42, falha_string: bool = False):
    return monitoramento.gerar_alertas(_simular(estrategia, clima, semente, falha_string))


@router.get("/energia/agora")
def agora(hora: str | None = None, clima: Clima = "ensolarado"):
    """Leitura instantânea. `hora` no formato HH:MM; sem ela, usa o relógio do servidor."""
    h = datetime.datetime.strptime(hora, "%H:%M").time() if hora else None
    return leitura_atual(h, clima)


class PerguntaRequest(BaseModel):
    pergunta: str
    clima: Clima = "ensolarado"
    falha_string: bool = False


@router.post("/energia/assistente")
def perguntar(dados: PerguntaRequest):
    resultado = _simular("inteligente", dados.clima, 42, dados.falha_string)
    comp = _comparativo(dados.clima, 42, dados.falha_string)
    return assistente.responder(
        dados.pergunta,
        comp["kpis"]["inteligente"],
        comp["ganhos"],
        monitoramento.gerar_alertas(resultado),
        resultado["serie"],
    )


@router.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD / "index.html")


@router.get("/dashboard/vendor/{arquivo}", include_in_schema=False)
def dashboard_vendor(arquivo: str):
    caminho = (DASHBOARD / "vendor" / arquivo).resolve()
    if caminho.parent != (DASHBOARD / "vendor").resolve() or not caminho.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(caminho)
