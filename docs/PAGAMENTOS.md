# Módulo de Pagamentos

Pagamento simulado, com o caminho pronto para a integração real. Nenhuma
chamada de rede a gateway acontece hoje.

## Como rodar

```bash
pip install -r requirements.txt
export PAGAMENTO_PROVEDOR=fake        # padrão
uvicorn api.main:app --reload
pytest -q                             # 16 testes
```

Documentação interativa em `http://127.0.0.1:8000/docs`.

## Rotas

| Método | Rota | Para quê |
|---|---|---|
| `POST` | `/pagamentos` | Cria a cobrança. Exige `Idempotency-Key`. |
| `GET` | `/pagamentos/{id}` | Consulta o status. O totem faz polling aqui. |
| `GET` | `/pagamentos?id_sessao=` | Cobranças de uma sessão. |
| `POST` | `/pagamentos/webhook` | O provedor avisa quando o status muda. |
| `POST` | `/pagamentos/{id}/simular` | Só com provedor `fake`: força status na demo. |
| `POST` | `/pagamento` | **Obsoleta.** Mantida para não quebrar o totem. |

## Decisões que valem explicar na banca

**Dinheiro é inteiro em centavos.** O `database.json` guarda
`81.82650000000005` — float não representa dinheiro. `R$ 39,88` é `3988`.

**Idempotência obrigatória.** Sem `Idempotency-Key`, dois cliques no botão
Pagar cobram duas vezes. Com ela, a segunda chamada devolve a mesma cobrança
com HTTP 200 em vez de 201. Todo gateway sério exige isso.

**Máquina de estados explícita.** `pendente → aprovada | recusada | expirada`,
`aprovada → estornada`. Um webhook atrasado não consegue "aprovar" uma
cobrança já estornada — a transição é recusada com HTTP 409.

**Assíncrono desde o começo.** Pix não confirma na resposta do POST: nasce
`pendente`, o cliente paga, e o provedor avisa por webhook. Uma API que só
sabe responder na hora não comporta Pix. Por isso o webhook existe antes da
integração real.

**Webhook assinado.** HMAC-SHA256 com `compare_digest`, para não aceitar
confirmação de pagamento forjada e para não vazar a chave por timing.

## Provedor fake: resultado determinístico

O `api/pagamento.py` antigo sorteava `random.random() > 0.1` — 1 em 10
demonstrações falhava sozinha, e não dava para mostrar a recusa de propósito.
Aqui o resultado vem dos centavos do valor, como nos sandboxes de mercado:

| Valor termina em | Resultado |
|---|---|
| `01` | recusada — saldo insuficiente |
| `02` | recusada — cartão expirado |
| `03` | fica pendente para sempre (simula timeout) |
| outro, cartão | aprovada na hora |
| outro, Pix | pendente + QR de demonstração |

O QR do Pix segue o formato EMV real mas **não tem CRC válido**: serve para
a tela desenhar um QR de aparência correta, não é cobrável.

## Fluxo completo do Pix

```
POST /pagamentos  {id_sessao, valor_centavos, metodo:"pix"}
  Idempotency-Key: <uuid>
      -> 201 {id, status:"pendente", qr_code:"000201265800..."}

GET /pagamentos/{id}   (totem faz polling a cada 2 s)
      -> {status:"pendente"}

POST /pagamentos/webhook            (o provedor chama; na demo, use o simular)
  X-Assinatura: <hmac sha256 do corpo>
  {"id_provedor":"fake_...", "status":"aprovada"}
      -> 204

GET /pagamentos/{id}
      -> {status:"aprovada"}
```

Na apresentação, em vez do webhook use:
`POST /pagamentos/{id}/simular?novo_status=aprovada`

## Ligando o provedor real

`api/pagamentos/provedores/mercadopago.py` já tem a estrutura. Cada método
traz, em docstring, o endpoint, o corpo e o mapeamento de status do
Mercado Pago. Para ativar:

1. `export MERCADOPAGO_ACCESS_TOKEN=APP_USR-...`
2. `export PAGAMENTO_PROVEDOR=mercadopago`
3. Trocar os `raise NotImplementedError` pelas chamadas das docstrings
4. Cadastrar a URL pública do webhook no painel do Mercado Pago

**Nenhuma rota, nenhum modelo e nenhuma linha do totem muda.** É esse o
ponto da interface `ProvedorPagamento` em `api/pagamentos/base.py`.

Detalhe do Mercado Pago: o webhook deles **não traz o status**, só
`{"data": {"id": "123"}}`. É preciso consultar `GET /v1/payments/{id}` para
saber o que mudou — por isso `consultar_cobranca` faz parte do contrato.

## O que ainda falta para produção

- Banco de verdade no lugar do JSON (trocar só `repositorio.py`)
- Autenticação nas rotas — hoje qualquer um cria cobrança
- Rotina de reconciliação: varrer cobranças `pendente` antigas e consultar
  o provedor, porque webhook se perde
- Expiração automática do Pix (hoje `expirada` existe no enum mas nada a dispara)
- Log de auditoria de cada transição de status
