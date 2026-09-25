"""
Testes do módulo de pagamentos.

Rodar:  pytest -q
"""

import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ["PAGAMENTO_PROVEDOR"] = "fake"
os.environ["PAGAMENTOS_DB"] = "data/pagamentos_teste.json"

from api.main import app  # noqa: E402
from api.pagamentos.provedores.fake import ProvedorFake  # noqa: E402
from api.pagamentos.repositorio import CAMINHO_PADRAO  # noqa: E402

cliente = TestClient(app)


@pytest.fixture(autouse=True)
def banco_limpo():
    if CAMINHO_PADRAO.exists():
        CAMINHO_PADRAO.unlink()
    yield
    if CAMINHO_PADRAO.exists():
        CAMINHO_PADRAO.unlink()


def criar(valor_centavos=3988, metodo="cartao_credito", chave=None, id_sessao=1):
    chave = chave or str(uuid.uuid4())
    return cliente.post(
        "/pagamentos",
        json={
            "id_sessao": id_sessao,
            "valor_centavos": valor_centavos,
            "metodo": metodo,
            "descricao": "Recarga GoodWe",
        },
        headers={"Idempotency-Key": chave},
    )


# ------------------------------------------------------------------ básico
def test_cartao_aprova_na_hora():
    r = criar(valor_centavos=3988)
    assert r.status_code == 201
    assert r.json()["status"] == "aprovada"
    assert r.json()["valor_centavos"] == 3988


def test_pix_nasce_pendente_com_qr():
    r = criar(valor_centavos=3988, metodo="pix")
    corpo = r.json()
    assert corpo["status"] == "pendente"
    assert corpo["qr_code"].startswith("00020126")


def test_centavos_01_recusa_por_saldo():
    r = criar(valor_centavos=3901)
    assert r.json()["status"] == "recusada"
    assert r.json()["motivo_recusa"] == "Saldo insuficiente"


def test_centavos_02_recusa_por_cartao_expirado():
    assert criar(valor_centavos=3902).json()["motivo_recusa"] == "Cartão expirado"


def test_valor_zero_ou_negativo_e_rejeitado():
    assert criar(valor_centavos=0).status_code == 422
    assert criar(valor_centavos=-100).status_code == 422


# ------------------------------------------------------------ idempotência
def test_idempotency_key_obrigatoria():
    r = cliente.post(
        "/pagamentos",
        json={"id_sessao": 1, "valor_centavos": 1000, "metodo": "pix"},
    )
    assert r.status_code == 400
    assert "Idempotency-Key" in r.json()["detail"]


def test_mesma_chave_nao_cobra_duas_vezes():
    chave = str(uuid.uuid4())
    primeira = criar(chave=chave)
    segunda = criar(chave=chave)

    assert primeira.status_code == 201
    assert segunda.status_code == 200          # 200, não 201: nada foi criado
    assert primeira.json()["id"] == segunda.json()["id"]
    assert len(cliente.get("/pagamentos").json()) == 1


# ----------------------------------------------------------------- webhook
def assinar_e_enviar(id_provedor, status, motivo=None, assinatura=None):
    corpo = json.dumps(
        {"id_provedor": id_provedor, "status": status, "motivo": motivo}
    ).encode()
    return cliente.post(
        "/pagamentos/webhook",
        content=corpo,
        headers={"X-Assinatura": assinatura or ProvedorFake.assinar(corpo)},
    )


def test_webhook_confirma_pix_pendente():
    cobranca = criar(metodo="pix").json()
    assert cobranca["status"] == "pendente"

    assert assinar_e_enviar(cobranca["id_provedor"], "aprovada").status_code == 204
    assert cliente.get(f"/pagamentos/{cobranca['id']}").json()["status"] == "aprovada"


def test_webhook_com_assinatura_errada_e_401():
    cobranca = criar(metodo="pix").json()
    r = assinar_e_enviar(cobranca["id_provedor"], "aprovada", assinatura="0" * 64)
    assert r.status_code == 401


def test_webhook_sem_assinatura_e_401():
    cobranca = criar(metodo="pix").json()
    corpo = json.dumps({"id_provedor": cobranca["id_provedor"], "status": "aprovada"}).encode()
    assert cliente.post("/pagamentos/webhook", content=corpo).status_code == 401


def test_webhook_reenviado_nao_quebra():
    cobranca = criar(metodo="pix").json()
    assert assinar_e_enviar(cobranca["id_provedor"], "aprovada").status_code == 204
    assert assinar_e_enviar(cobranca["id_provedor"], "aprovada").status_code == 204


def test_webhook_de_cobranca_desconhecida_devolve_204():
    assert assinar_e_enviar("fake_inexistente", "aprovada").status_code == 204


# --------------------------------------------------------- máquina de estados
def test_nao_aprova_cobranca_ja_recusada():
    cobranca = criar(valor_centavos=3901).json()      # nasce recusada
    r = assinar_e_enviar(cobranca["id_provedor"], "aprovada")
    assert r.status_code == 409


def test_estorno_so_depois_de_aprovada():
    cobranca = criar(metodo="pix").json()             # pendente
    r = cliente.post(f"/pagamentos/{cobranca['id']}/simular", params={"novo_status": "estornada"})
    assert r.status_code == 409

    assinar_e_enviar(cobranca["id_provedor"], "aprovada")
    r = cliente.post(f"/pagamentos/{cobranca['id']}/simular", params={"novo_status": "estornada"})
    assert r.status_code == 200
    assert r.json()["status"] == "estornada"


# ------------------------------------------------------------------ consulta
def test_consulta_por_sessao():
    criar(id_sessao=42)
    criar(id_sessao=42)
    criar(id_sessao=99)
    assert len(cliente.get("/pagamentos", params={"id_sessao": 42}).json()) == 2


def test_cobranca_inexistente_e_404():
    assert cliente.get("/pagamentos/cob_naoexiste").status_code == 404
