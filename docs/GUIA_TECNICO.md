# GoodWe SmartGrid EV — Documentação Técnica e Arquitetural

Este repositório documenta a evolução da simulação comercial do totem de recarga de veículos elétricos baseados na linha **GoodWe HCA G2**. O sistema transicionou de uma aplicação monolítica (arquivo único) para uma **Arquitetura Cliente-Servidor** descentralizada.

---

## Evolução Arquitetural: Monolito vs. Cliente-Servidor

### Arquitetura Anterior (Monolítica)
Originalmente, a interface gráfica (`Flet`), a lista de carros, os loops de simulação e as fórmulas financeiras/energéticas executavam dentro de um único arquivo Python (`flet_proposta_gw.py`).
* **Limitante:** Qualquer falha na interface travava o cálculo da bateria; dados e regras de negócio ficavam expostos no terminal local.

### Arquitetura Atual (Desacoplada)
O sistema foi dividido em duas camadas independentes que se comunicam via protocolo HTTP (REST API):

```text
┌────────────────────────────────┐        HTTP (JSON)        ┌────────────────────────────────┐
│   Totem Frontend (Flet)        │  ────── GET / POST ─────► │   Backend API (FastAPI)        │
│   - Interface Totem (UI)       │                           │   - Regras de Carga (p_real)   │
│   - Animações & Asyncio        │  ◄───── JSON Response ─── │   - Tarifação & Impostos       │
└────────────────────────────────┘                           └────────────────────────────────┘

```

---

## Detalhamento dos Conceitos e Bibliotecas

### 1. `FastAPI`, Decoradores e Roteamento HTTP (`@app.get` / `@app.post`)

Os decoradores registram funções Python comuns no roteador da API, expondo-as para chamadas de rede externa.

* **`@app.get("/rota")`:** Define que o endpoint responde a requisições de leitura (**GET**). Não altera dados no servidor; apenas processa e devolve informações (ex: consultar veículo detectado ou recalcular potência).
* **`@app.post("/rota")`:** Ocupa a rota para envio de dados no corpo da requisição (**POST**). É utilizado quando o cliente precisa submeter uma estrutura complexa para processamento no servidor (ex: enviar kWh para cálculo de recibo).
* **Sem o Decorador:** A função existirá apenas localmente dentro do arquivo `.py` e não estará acessível via HTTP (retornará erro `404 Not Found` caso seja chamada externamente).

### 2. `Pydantic` e `BaseModel` (Validação de Dados)

O `Pydantic` garante o cumprimento dos contratos de dados (*schemas*) nas requisições HTTP.

```python
class ReciboRequest(BaseModel):
    kwh_acumulado: float

```

* **Garantia de Tipagem:** Define que a API só aceitará um JSON contendo a chave `kwh_acumulado` com valor numérico contínuo (`float`).
* **Segurança e Tratamento Automatizado:** Se o Totem enviar um formato inválido (ex: `{"kwh_acumulado": "dez"}`), o FastAPI intercepta a chamada antes do código rodar, retornando um erro `422 Unprocessable Entity`.
* **Serialização:** Transforma o corpo do JSON recebido via rede em um objeto Python acessível de forma direta (ex: `dados.kwh_acumulado`).

### 3. `import asyncio` (Assincronismo e Renderização de UI)

A biblioteca `asyncio` gerencia a execução assíncrona e não-bloqueante no Python.

* **No Totem (`Flet`):** O loop de carregamento roda dentro de uma corrotina assíncrona (`async def loop_carregamento()`).
* **Utilidade:** Enquanto o loop calcula o progresso da bateria e aguarda pausas com `await asyncio.sleep(0.4)`, a thread principal da interface gráfica fica livre. Isso mantém botões, animações e o efeito de pulso da Splash Screen funcionando sem congelar a tela.
* **Execução Paralela:** No Flet, tarefas assíncronas de longa duração são disparadas via `page.run_task(...)`.

### 4. `import requests` (Comunicação HTTP do Cliente)

A biblioteca `requests` é o cliente HTTP responsável por enviar dados do Totem para a API.

#### **Requisição GET (Consulta):**

```python
resposta = requests.get("[http://127.0.0.1:8000/detectar-veiculo](http://127.0.0.1:8000/detectar-veiculo)").json()

```

* O Totem dispara uma chamada de leitura para a API.
* O método `.json()` converte a resposta em texto bruto vinda da rede diretamente em um dicionário manipulável em Python (`resposta["carro"]["modelo"]`).

#### **Requisição POST (Envio de Payload):**

```python
payload = {"kwh_acumulado": estado["acumulo"]}
recibo = requests.post("[http://127.0.0.1:8000/gerar-recibo](http://127.0.0.1:8000/gerar-recibo)", json=payload).json()

```

* O parâmetro `json=payload` converte o dicionário Python em uma string JSON formatada no corpo (*body*) da requisição HTTP e injeta o cabeçalho `Content-Type: application/json`.
* A API recebe o payload, valida via Pydantic e devolve o cálculo do recibo processado.

---

## Estrutura de Rotas da API (`api/main.py`)

| Rota | Método | Função | Entrada | Saída (JSON) |
| --- | --- | --- | --- | --- |
| `/detectar-veiculo` | `GET` | Sorteia um veículo e calcula a potência inicial. | Nenhuma | Dados do veículo, nº de carros e `potencia_real`. |
| `/recalcular-potencia` | `GET` | Recalcula a divisão de carga em caso de flutuação da rede. | Query Params: `num_carros`, `potencia_max_carro` | Nova `potencia_real`. |
| `/gerar-recibo` | `POST` | Processa valores tarifários, taxas fixas e impostos (ISS 5%). | JSON Body (`ReciboRequest`) | Valores de consumo, taxas, imposto e `total_rs`. |

---

## Como Executar

1. **Instale as dependências:**
```bash
pip install fastapi uvicorn requests pydantic flet

```


2. **Inicie a API (Terminal 1):**
```bash
cd api
uvicorn main:app --reload

```


*Documentação interativa disponível em: `http://127.0.0.1:8000/docs*`
3. **Inicie o Totem (Terminal 2):**
```bash
cd totem
flet run flet_proposta_gw.py

```



```

```