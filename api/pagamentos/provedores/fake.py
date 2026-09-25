"""
Provedor falso — determinístico de propósito.

O pagamento.py atual usa `random.random() > 0.1`, o que significa que
1 em cada 10 demonstrações falha na frente da banca, e que não dá para
demonstrar o caminho de recusa quando você QUER mostrar.

Aqui o resultado é decidido pelos centavos do valor, que é o mesmo truque
que os sandboxes do Stripe e do Mercado Pago usam com cartões de teste:

    valor terminado em 01  ->  recusada  ("saldo insuficiente")
    valor terminado em 02  ->  recusada  ("cartão expirado")
    valor terminado em 03  ->  fica PENDENTE e nunca confirma (timeout)
    qualquer outro valor   ->  aprovada (cartão) ou pendente (Pix)

Pix sempre nasce PENDENTE: é assim no mundo real. A confirmação chega
depois, por webhook — e é justamente esse caminho que precisa existir
antes da integração de verdade.
"""

import hashlib
import hmac
import json
import os
import uuid

from api.pagamentos.base import ErroPagamento, WebhookInvalido
from api.pagamentos.models import (
    Cobranca,
    CobrancaCriar,
    EventoWebhook,
    MetodoPagamento,
    StatusCobranca,
    agora,
)

SEGREDO_WEBHOOK = os.getenv("PAGAMENTO_WEBHOOK_SEGREDO", "segredo-de-desenvolvimento")

RECUSAS = {
    1: "Saldo insuficiente",
    2: "Cartão expirado",
}


class ProvedorFake:
    nome = "fake"

    # ------------------------------------------------------------- cobranças
    def criar_cobranca(self, dados: CobrancaCriar, chave_idempotencia: str) -> Cobranca:
        centavos = dados.valor_centavos % 100
        id_provedor = f"fake_{uuid.uuid4().hex[:16]}"
        instante = agora()

        status = StatusCobranca.PENDENTE
        motivo = None
        qr_code = None

        if centavos in RECUSAS:
            status = StatusCobranca.RECUSADA
            motivo = RECUSAS[centavos]
        elif centavos == 3:
            status = StatusCobranca.PENDENTE  # nunca confirma, simula timeout
        elif dados.metodo == MetodoPagamento.PIX:
            status = StatusCobranca.PENDENTE
            qr_code = self._payload_pix(dados.valor_centavos, id_provedor)
        else:
            status = StatusCobranca.APROVADA  # cartão responde na hora

        return Cobranca(
            id=f"cob_{uuid.uuid4().hex[:20]}",
            id_sessao=dados.id_sessao,
            valor_centavos=dados.valor_centavos,
            metodo=dados.metodo,
            status=status,
            provedor=self.nome,
            chave_idempotencia=chave_idempotencia,
            id_provedor=id_provedor,
            qr_code=qr_code,
            motivo_recusa=motivo,
            criada_em=instante,
            atualizada_em=instante,
        )

    def consultar_cobranca(self, id_provedor: str) -> Cobranca:
        # O fake não guarda estado próprio: a verdade está no nosso repositório.
        # O provedor real faria GET /v1/payments/{id} aqui.
        raise ErroPagamento(
            "O provedor fake não tem estado próprio. Use GET /pagamentos/{id}."
        )

    def estornar_cobranca(self, id_provedor: str) -> Cobranca:
        raise ErroPagamento(
            "Estorno pelo provedor fake é feito por POST /pagamentos/{id}/simular."
        )

    # -------------------------------------------------------------- webhook
    def validar_webhook(self, corpo: bytes, assinatura: str | None) -> EventoWebhook:
        if not assinatura:
            raise WebhookInvalido("Cabeçalho X-Assinatura ausente.")

        esperado = self.assinar(corpo)
        # compare_digest evita timing attack — o provedor real exige o mesmo
        if not hmac.compare_digest(esperado, assinatura):
            raise WebhookInvalido("Assinatura do webhook não confere.")

        try:
            payload = json.loads(corpo)
        except json.JSONDecodeError as erro:
            raise WebhookInvalido("Corpo do webhook não é JSON válido.") from erro

        return EventoWebhook.model_validate(payload)

    @staticmethod
    def assinar(corpo: bytes) -> str:
        """Exposto para os testes e para o script de simulação gerarem assinatura."""
        return hmac.new(SEGREDO_WEBHOOK.encode(), corpo, hashlib.sha256).hexdigest()

    # ------------------------------------------------------------- auxiliar
    @staticmethod
    def _payload_pix(valor_centavos: int, id_provedor: str) -> str:
        """
        Sequência no formato EMV do Pix, com os campos reais mas sem CRC válido.
        Serve para a tela gerar um QR de demonstração com aparência correta.
        NÃO é um Pix cobrável.
        """
        valor = f"{valor_centavos / 100:.2f}"
        return (
            "00020126580014BR.GOV.BCB.PIX"
            f"0136{id_provedor}"
            "52040000530398654"
            f"{len(valor):02d}{valor}"
            "5802BR5913GOODWE DEMO6009SAO PAULO"
            "62070503***6304DEMO"
        )
