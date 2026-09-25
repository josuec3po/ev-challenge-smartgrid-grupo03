"""Escolhe o provedor pela variável de ambiente. Um lugar só."""

import os
from functools import lru_cache

from api.pagamentos.base import ErroPagamento, ProvedorPagamento
from api.pagamentos.provedores.fake import ProvedorFake

PROVEDOR = os.getenv("PAGAMENTO_PROVEDOR", "fake").lower()


@lru_cache(maxsize=1)
def obter_provedor() -> ProvedorPagamento:
    if PROVEDOR == "fake":
        return ProvedorFake()

    if PROVEDOR == "mercadopago":
        from api.pagamentos.provedores.mercadopago import ProvedorMercadoPago

        return ProvedorMercadoPago()

    raise ErroPagamento(
        f"PAGAMENTO_PROVEDOR='{PROVEDOR}' desconhecido. Use 'fake' ou 'mercadopago'."
    )
