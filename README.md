## Arquitetura do Sistema

O projeto adota uma arquitetura desacoplada **Cliente-Servidor**:
- **Backend (API):** FastAPI gerenciando lógica de negócios, balanceamento de potência e cobrança.
- **Frontend (Totem):** Flet (Python/Flutter) operando em Modo Totem.

**[Ler a Documentação Arquitetural Completa](docs/ARQUITETURA.md)**

## Como Executar o Projeto

**Pré-requisitos:** Instale as dependências executando `pip install fastapi uvicorn requests pydantic flet`.

1. **Inicie a API:** Em um terminal, acesse a pasta `api/` e rode:
    ```bash
    uvicorn main:app --reload
    ```
2. **Inicie o Totem:** Em um segundo terminal, acesse a pasta totem/ e rode:
    ```bash
    flet run flet_proposta_gw.py
    ```     
