"""
O contrato que todo provedor de pagamento precisa cumprir.

É aqui que mora o "caminho já feito": trocar o provedor fake pelo
Mercado Pago não deve exigir mudança em nenhuma rota nem no totem.
"""

from typing import Protocol, runtime_checkable

from api.pagamentos.models import Cobranca, CobrancaCriar, EventoWebhook


class ErroPagamento(Exception):
    """Falha esperada de negócio. Vira HTTP 400."""


class CobrancaNaoEncontrada(ErroPagamento):
    """Vira HTTP 404."""


class TransicaoInvalida(ErroPagamento):
    """Tentativa de mudar o status para um estado não permitido. HTTP 409."""


class WebhookInvalido(ErroPagamento):
    """Assinatura não confere. HTTP 401."""


@runtime_checkable
class ProvedorPagamento(Protocol):
    """
    Quatro métodos. Qualquer gateway do mercado cabe nessa forma.

    O repositório (persistência) é responsabilidade do router, não do
    provedor — o provedor só fala com o mundo externo.
    """

    nome: str

    def criar_cobranca(self, dados: CobrancaCriar, chave_idempotencia: str) -> Cobranca:
        """Cria a cobrança no provedor. Pode voltar PENDENTE (Pix) ou já APROVADA (cartão)."""
        ...

    def consultar_cobranca(self, id_provedor: str) -> Cobranca:
        """Consulta o status direto na fonte. Usado para reconciliar."""
        ...

    def estornar_cobranca(self, id_provedor: str) -> Cobranca:
        ...

    def validar_webhook(self, corpo: bytes, assinatura: str | None) -> EventoWebhook:
        """Confere a assinatura e traduz o payload do provedor para o nosso formato."""
        ...
