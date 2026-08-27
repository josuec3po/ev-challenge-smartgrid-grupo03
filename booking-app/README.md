# GoodWe EV Charging — App do motorista

Protótipo navegável da interface mobile do motorista, complementar ao Totem (`totem/`) e consumindo o mesmo domínio de negócio da API (`api/`).

É um **único arquivo HTML sem build**: `index.html`. Não há dependências instaláveis — só a fonte via Google Fonts.

## Como abrir

```bash
# opção 1 — abrir direto no navegador
xdg-open booking-app/index.html      # Linux
open booking-app/index.html          # macOS
start booking-app\index.html         # Windows

# opção 2 — servir localmente (recomendado, evita restrições de file://)
python -m http.server 8080
# depois acesse http://localhost:8080/booking-app/
```

## O que está implementado

| Aba | Conteúdo |
|---|---|
| **Início** | Barra de bateria com autonomia em km, mapa com pins por disponibilidade (verde/amarelo/vermelho), lista de estações com preço, potência e vagas. Banner de alerta automático quando a bateria cai a ≤ 20%. |
| **Reservar** | Fluxo de 3 etapas: estação → data + conector (CCS2, CHAdeMO, Type 2 AC, GB/T) + horário → confirmação com QR, código de liberação e política de cancelamento. |
| **Sessões** | Sessão ativa com barra de progresso animada (kWh, potência real e custo parcial em tempo real), resumo mensal e histórico. |
| **SOS — Resgate Elétrico** | Botão pulsante → contagem regressiva de 5 s com cancelamento → rastreio do guincho no mapa com ETA → fase de carregamento → comprovante. |

O painel lateral (fora do celular) traz um **simulador de bateria** e atalhos para cada tela — é ferramenta de demonstração, não faz parte do app.

## Modelo de carga do resgate

Na fase de carregamento o app mostra três medidores simultâneos, que é o diferencial do fluxo SOS:

1. **Carga entregue ao carro** — 0 → 6,0 kWh; a bateria sobe de 2% para 12%.
2. **Orçamento de quilometragem** (barra empilhada) — trajeto até o posto `3,2 km` + reserva para trânsito parado `7,0 km` + margem de segurança `2,0 km` = **12,2 km mínimos**. O guincho entrega **37 km, 3,0× o necessário**.
3. **Bateria do guincho GW-07** — cai de 62% para 55%, indicando quantos resgates o pack de 82 kWh ainda atende.

A carga extra existe porque o tempo de trajeto depende do trânsito: 12 min para 3,2 km na Av. Paulista no horário de pico. O app dimensiona a entrega pelo pior caso, não pela distância em linha reta.

## Integração pendente com a API

Hoje os dados são estáticos, no bloco `STATIONS` / `HISTORY` do `index.html`. Para plugar na API FastAPI (`api/main.py`):

| Tela | Rota sugerida | Já existe? |
|---|---|---|
| Sessão ativa (potência real) | `GET /recalcular-potencia` | sim |
| Encerramento de sessão | `POST /gerar-recibo` | sim |
| Lista de estações | `GET /estacoes` | não — a criar |
| Reserva | `POST /reservas` | não — a criar |
| Chamado de resgate | `POST /resgates` | não — a criar |

## Design

Cores e tipografia herdadas de `totem/main.py` — ver [`docs/DESIGN_SYSTEM.md`](../docs/DESIGN_SYSTEM.md).

Arquivo Figma com os tokens e as primeiras telas: https://www.figma.com/design/0Ae2aWfJUsSFODYTOiONwT
