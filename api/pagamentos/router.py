"""
Rotas de pagamento.

Duas coisas que o /pagamento atual não tem e que todo gateway real exige:

  1. Idempotência. Sem o cabeçalho Idempotency-Key, apertar "Pagar" duas
     vezes cobra duas vezes. Com ele, a segunda chamada devolve a MESMA
     cobrança, com HTTP 200 em vez de 201.
  2. Assincronismo. Pix não confirma na resposta do POST. O totem cria a
     cobrança, mostra o QR e faz polling em GET /pagamentos/{id} até mudar
     de status — que é o que acontece quando o webhook chega.
"""

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from api.pagamentos.base import (
    CobrancaNaoEncontrada,
    ErroPagamento,
    TransicaoInvalida,
    WebhookInvalido,
)
from api.pagamentos.fabrica import obter_provedor
from api.pagamentos.models import (
    Cobranca,
    CobrancaCriar,
    StatusCobranca,
    agora,
    transicao_permitida,
)
from api.pagamentos.repositorio import RepositorioCobrancas

router = APIRouter(prefix="/pagamentos", tags=["pagamentos"])
repositorio = RepositorioCobrancas()


# --------------------------------------------------------------- criar
@router.post("", response_model=Cobranca, status_code=status.HTTP_201_CREATED)
def criar_cobranca(
    dados: CobrancaCriar,
    resposta: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Cabeçalho Idempotency-Key é obrigatório. "
                   "Gere um UUID por tentativa de pagamento e reenvie o mesmo em retries.",
        )

    ja_existe = repositorio.buscar_por_idempotencia(idempotency_key)
    if ja_existe:
        # Mesma chave, mesma cobrança. Não cria outra, não cobra de novo.
        resposta.status_code = status.HTTP_200_OK
        return ja_existe

    provedor = obter_provedor()
    try:
        cobranca = provedor.criar_cobranca(dados, idempotency_key)
    except ErroPagamento as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    return repositorio.salvar(cobranca)


# -------------------------------------------------------------- consultar
@router.get("/{id_cobranca}", response_model=Cobranca)
def consultar_cobranca(id_cobranca: str):
    cobranca = repositorio.buscar(id_cobranca)
    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada.")
    return cobranca


@router.get("", response_model=list[Cobranca])
def listar_cobrancas(id_sessao: int | None = None):
    if id_sessao is not None:
        return repositorio.listar_por_sessao(id_sessao)
    return repositorio.listar()


# ---------------------------------------------------------------- webhook
@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def receber_webhook(
    request: Request,
    x_assinatura: str | None = Header(default=None, alias="X-Assinatura"),
):
    """
    Endpoint que o provedor chama quando o status muda.

    Precisa ser idempotente também: gateways reenviam o mesmo evento se
    não receberem 2xx rápido. Por isso repetir um evento já aplicado
    devolve 204 em silêncio em vez de erro.
    """
    corpo = await request.body()
    provedor = obter_provedor()

    try:
        evento = provedor.validar_webhook(corpo, x_assinatura)
    except WebhookInvalido as erro:
        raise HTTPException(status_code=401, detail=str(erro)) from erro
    except ErroPagamento as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    cobranca = repositorio.buscar_por_id_provedor(evento.id_provedor)
    if not cobranca:
        # 200 mesmo assim: se devolvermos erro, o provedor fica reenviando
        # para sempre um evento de uma cobrança que não é nossa.
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if cobranca.status == evento.status:
        return Response(status_code=status.HTTP_204_NO_CONTENT)  # reenvio

    if not transicao_permitida(cobranca.status, evento.status):
        raise HTTPException(
            status_code=409,
            detail=f"Transição inválida: {cobranca.status.value} -> {evento.status.value}.",
        )

    cobranca.status = evento.status
    cobranca.motivo_recusa = evento.motivo
    cobranca.atualizada_em = agora()
    repositorio.salvar(cobranca)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------- simulação (só no fake)
@router.post("/{id_cobranca}/simular", response_model=Cobranca)
def simular_mudanca(id_cobranca: str, novo_status: StatusCobranca, motivo: str | None = None):
    """
    Atalho de demonstração: força a mudança de status sem passar pelo webhook.

    Existe para a apresentação — apertar "confirmar Pix" na hora certa em
    vez de esperar. Some quando PAGAMENTO_PROVEDOR != fake.
    """
    provedor = obter_provedor()
    if provedor.nome != "fake":
        raise HTTPException(
            status_code=403,
            detail="Simulação disponível apenas com PAGAMENTO_PROVEDOR=fake.",
        )

    cobranca = repositorio.buscar(id_cobranca)
    if not cobranca:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada.")

    if not transicao_permitida(cobranca.status, novo_status):
        raise HTTPException(
            status_code=409,
            detail=f"Transição inválida: {cobranca.status.value} -> {novo_status.value}.",
        )

    cobranca.status = novo_status
    cobranca.motivo_recusa = motivo
    cobranca.atualizada_em = agora()
    return repositorio.salvar(cobranca)
