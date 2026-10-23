# Resultados da simulação (semente 42, 24 sessões)

Gerado por `python scripts/gerar_graficos.py`.

| Clima | Estratégia | Custo (R$/dia) | Custo médio (R$/kWh) | Rede (kWh) | Rede na ponta (kWh) | Autossuficiência | Recargas completas | CO₂ rede (kg) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ensolarado | Convencional (só rede) | 592.89 | 0.834 | 711 | 144 | 0% | 16/24 | 27.4 |
| ensolarado | Solar básico | 365.94 | 0.515 | 328 | 144 | 54% | 16/24 | 12.6 |
| ensolarado | Inteligente GoodWe | 323.21 | 0.437 | 359 | 74 | 51% | 22/24 | 13.8 |
| parcial | Convencional (só rede) | 592.89 | 0.834 | 711 | 144 | 0% | 16/24 | 27.4 |
| parcial | Solar básico | 428.78 | 0.603 | 428 | 144 | 40% | 16/24 | 16.5 |
| parcial | Inteligente GoodWe | 386.24 | 0.522 | 460 | 73 | 38% | 22/24 | 17.7 |
| nublado | Convencional (só rede) | 592.89 | 0.834 | 711 | 144 | 0% | 16/24 | 27.4 |
| nublado | Solar básico | 511.47 | 0.720 | 561 | 144 | 21% | 16/24 | 21.6 |
| nublado | Inteligente GoodWe | 468.72 | 0.634 | 593 | 73 | 20% | 22/24 | 22.8 |

| Clima | Redução de custo | Redução da rede | Redução na ponta | Economia/ano |
|---|---:|---:|---:|---:|
| ensolarado | 45.5% | 49.4% | 48.7% | R$ 98.433 |
| parcial | 34.9% | 35.2% | 49.0% | R$ 75.427 |
| nublado | 20.9% | 16.6% | 49.1% | R$ 45.322 |
