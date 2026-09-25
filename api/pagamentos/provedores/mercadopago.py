"""
Esqueleto do provedor real — o "caminho já feito".

NADA aqui faz chamada de rede ainda. Cada método tem, em comentário, o
endpoint e o corpo exatos que o Mercado Pago espera, e o mapeamento de
status deles para os nossos. Para ligar de verdade:

  1. pip install mercadopago  (ou use httpx direto, já é dependência)
  2. export MERCADOPAGO_ACCESS_TOKEN=APP_USR-...
  3. export PAGAMENTO_PROVEDOR=mercadopago
  4. troque os `raise NotImplementedError` pelas chamadas comentadas
  5. cadastre a URL do webhook no painel: POST /pagamentos/webhook

Nenhuma rota, nenhum modelo e nenhuma linha do totem muda nesse processo.
Escolhemos o Mercado Pago por ser o que tem Pix mais simples no Brasil;
Pagar.me e Stripe cabem no mesmo contrato, só mudam os nomes dos campos.
"""

import os

from api.pagamentos.base import ErroPagamento, WebhookInvalido
from api.pagamentos.models import (
    Cobranca,
    CobrancaCriar,
    EventoWebhook,
    StatusCobranca,
)

BASE_URL = "https://api.mercadopago.com"
ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")

# De/para entre o vocabulário deles e o nosso.
# Fonte: https://www.mercadopago.com.br/developers/pt/reference/payments/_payments/post
STATUS_MERCADOPAGO = {
    "pending": StatusCobranca.PENDENTE,
    "in_process": StatusCobranca.PENDENTE,
    "authorized": StatusCobranca.PENDENTE,
    "approved": StatusCobranca.APROVADA,
    "rejected": StatusCobranca.RECUSADA,
    "cancelled": StatusCobranca.EXPIRADA,
    "refunded": StatusCobranca.ESTORNADA,
    "charged_back": StatusCobranca.ESTORNADA,
}

METODO_MERCADOPAGO = {
    "pix": "pix",
    "cartao_credito": "credit_card",
    "cartao_debito": "debit_card",
}


class ProvedorMercadoPago:
    nome = "mercadopago"

    def __init__(self) -> None:
        if not ACCESS_TOKEN:
            raise ErroPagamento(
                "MERCADOPAGO_ACCESS_TOKEN não configurado. "
                "Use PAGAMENTO_PROVEDOR=fake para desenvolvimento."
            )

    def criar_cobranca(self, dados: CobrancaCriar, chave_idempotencia: str) -> Cobranca:
        """
        POST /v1/payments
        Headers: Authorization: Bearer <token>
                 X-Idempotency-Key: <chave_idempotencia>   <- já temos, é o mesmo valor
        Body: {
            "transaction_amount": dados.valor_centavos / 100,
            "payment_method_id": METODO_MERCADOPAGO[dados.metodo.value],
            "description": dados.descricao,
            "external_reference": str(dados.id_sessao),
            "notification_url": "<base pública>/pagamentos/webhook",
            "payer": {"email": "..."}
        }
        Resposta -> Cobranca(
            id_provedor = str(resposta["id"]),
            status      = STATUS_MERCADOPAGO[resposta["status"]],
            qr_code     = resposta["point_of_interaction"]["transaction_data"]["qr_code"],
        )
        """
        raise NotImplementedError("Integração real pendente — ver docstring.")

    def consultar_cobranca(self, id_provedor: str) -> Cobranca:
        """GET /v1/payments/{id_provedor} — usado na rotina de reconciliação."""
        raise NotImplementedError("Integração real pendente — ver docstring.")

    def estornar_cobranca(self, id_provedor: str) -> Cobranca:
        """POST /v1/payments/{id_provedor}/refunds com corpo vazio estorna o total."""
        raise NotImplementedError("Integração real pendente — ver docstring.")

    def validar_webhook(self, corpo: bytes, assinatura: str | None) -> EventoWebhook:
        """
        O Mercado Pago manda os cabeçalhos `x-signature` e `x-request-id`.
        O manifesto a assinar é "id:<data.id>;request-id:<x-request-id>;ts:<ts>;"
        com HMAC-SHA256 da chave secreta do webhook.

        O corpo chega como {"action": "payment.updated", "data": {"id": "123"}} —
        repare que ele NÃO traz o status. É preciso fazer GET /v1/payments/{id}
        para saber o que mudou. Por isso consultar_cobranca existe no contrato.
        """
        raise NotImplementedError("Integração real pendente — ver docstring.")
