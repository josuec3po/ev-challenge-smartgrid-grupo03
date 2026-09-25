"""
Módulo de pagamentos do GoodWe SmartGrid EV.

O provedor real é escolhido por variável de ambiente, sem tocar no resto do código:

    PAGAMENTO_PROVEDOR=fake           # padrão, usado em desenvolvimento e na demo
    PAGAMENTO_PROVEDOR=mercadopago    # exige MERCADOPAGO_ACCESS_TOKEN

Ver api/pagamentos/provedores/mercadopago.py para o que falta preencher
quando a integração real entrar.
"""

from api.pagamentos.models import (
    Cobranca,
    CobrancaCriar,
    MetodoPagamento,
    StatusCobranca,
)
from api.pagamentos.base import (
    ErroPagamento,
    CobrancaNaoEncontrada,
    TransicaoInvalida,
    ProvedorPagamento,
)
from api.pagamentos.fabrica import obter_provedor

__all__ = [
    "Cobranca",
    "CobrancaCriar",
    "MetodoPagamento",
    "StatusCobranca",
    "ErroPagamento",
    "CobrancaNaoEncontrada",
    "TransicaoInvalida",
    "ProvedorPagamento",
    "obter_provedor",
]
