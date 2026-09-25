"""
Modelos e máquina de estados da cobrança.

Decisão importante: dinheiro é SEMPRE inteiro em centavos, nunca float.
O database.json atual guarda 81.82650000000005 — é o erro clássico de
representar dinheiro em ponto flutuante. Num sistema de pagamento isso
vira divergência de centavos na conciliação com o provedor.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class StatusCobranca(str, Enum):
    PENDENTE = "pendente"      # criada, aguardando o pagador (caso do Pix)
    APROVADA = "aprovada"      # provedor confirmou
    RECUSADA = "recusada"      # provedor negou
    EXPIRADA = "expirada"      # passou do prazo sem pagamento
    ESTORNADA = "estornada"    # devolvida depois de aprovada


# Quem pode virar o quê. Sem isso, um webhook atrasado "aprova" uma
# cobrança já estornada e a conta fecha errado.
TRANSICOES_VALIDAS: dict[StatusCobranca, set[StatusCobranca]] = {
    StatusCobranca.PENDENTE: {
        StatusCobranca.APROVADA,
        StatusCobranca.RECUSADA,
        StatusCobranca.EXPIRADA,
    },
    StatusCobranca.APROVADA: {StatusCobranca.ESTORNADA},
    StatusCobranca.RECUSADA: set(),
    StatusCobranca.EXPIRADA: set(),
    StatusCobranca.ESTORNADA: set(),
}


def transicao_permitida(de: StatusCobranca, para: StatusCobranca) -> bool:
    return para in TRANSICOES_VALIDAS[de]


class MetodoPagamento(str, Enum):
    PIX = "pix"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"


def agora() -> datetime:
    return datetime.now(timezone.utc)


class CobrancaCriar(BaseModel):
    """Corpo do POST /pagamentos."""

    id_sessao: int = Field(description="Sessão de recarga que está sendo paga")
    valor_centavos: int = Field(gt=0, description="Valor em centavos. R$ 39,88 = 3988")
    metodo: MetodoPagamento
    descricao: str = Field(default="", max_length=200)


class Cobranca(BaseModel):
    """Uma cobrança, do jeito que fica guardada e é devolvida pela API."""

    id: str
    id_sessao: int
    valor_centavos: int
    metodo: MetodoPagamento
    status: StatusCobranca
    provedor: str
    chave_idempotencia: str
    id_provedor: str | None = None
    qr_code: str | None = None          # payload copia-e-cola do Pix
    motivo_recusa: str | None = None
    criada_em: datetime
    atualizada_em: datetime

    @property
    def valor_reais(self) -> str:
        return f"{self.valor_centavos / 100:.2f}"


class EventoWebhook(BaseModel):
    """Notificação que o provedor manda quando o status muda."""

    id_provedor: str
    status: StatusCobranca
    motivo: str | None = None
