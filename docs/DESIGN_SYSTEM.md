# Design System GoodWe — Totem e App

Fonte da verdade: o bloco `PALETA GOODWE` de [`totem/main.py`](../totem/main.py). O app (`app/index.html`) e o arquivo Figma usam exatamente os mesmos valores, com nomes de token para facilitar a manutenção.

## Cores

| Token | Hex | Constante no totem | Uso |
|---|---|---|---|
| `brand/gw` | `#E50012` | `COR_GW` | Ação primária, marca, barra de carga |
| `brand/gw-dark` | `#9E000D` | `COR_GW_ESCURO` | Sombras, gradiente do botão SOS |
| `brand/gw-light` | `#FF4D5A` | `COR_GW_CLARO` | Realce, hover |
| `status/green` | `#4CAF50` | `COR_VERDE` | Estação livre, sessão concluída, sucesso |
| `status/amber` | `#FFC107` | `COR_PAUSA` | Fila curta, pausa, aviso de trânsito |
| `status/alert` | `#EF5350` | `COR_ALERTA` | Estação lotada, bateria crítica, erro |
| `bar/track` | `#B8B8B8` | `COR_BARRA_BG` | Trilho das barras de progresso |
| `border/default` | `#B3B3B3` | `COR_BORDA` | Bordas e divisores |
| `text/primary` | `#000000` | `COR_TEXTO` | Texto principal |
| `text/secondary` | `#1B1B1B` | `COR_SUBTEXTO` | Texto de apoio |
| `bg/base` | `#FFFFFF` | `COR_BG` | Fundo |

O app acrescenta apenas dois tokens que o totem não precisava, por operar em tela pequena com hierarquia mais densa:

| Token | Hex | Uso |
|---|---|---|
| `bg/subtle` | `#F4F5F7` | Fundo de campos, chips e cards secundários |
| `text/muted` | `#6E7175` | Rótulos, unidades e metadados |

### Semântica de disponibilidade

O mesmo trio de cores governa pins do mapa, o ponto ao lado do nome da estação e a pílula de status:

- verde `#4CAF50` — **livre**
- âmbar `#FFC107` — **fila curta**
- vermelho `#EF5350` — **lotada** (botão "Reservar" desabilitado)

## Tipografia

| Papel | Família | Onde |
|---|---|---|
| Dados, rótulos, números, unidades | **Space Mono** (400 / 700) | Mesma do totem. kWh, km, R$, percentuais, códigos, eyebrows |
| Interface e títulos | **Archivo** (400 / 500 / 600 / 700) | Nomes de estação, títulos de tela, texto corrido |

O wordmark "GoodWe" usa **Archivo Bold**, não Space Mono: em corpo grande o `W` monoespaçado invade as letras vizinhas, porque a largura do glifo excede o avanço da fonte.

Números que se alinham em coluna usam `font-variant-numeric: tabular-nums`.

## Layout do app

Cada tela segue o mesmo esqueleto de três camadas:

```
┌─────────────────────────┐
│ status bar (fixa)       │
├─────────────────────────┤
│                         │
│ conteúdo (rolável)      │
│                         │
├─────────────────────────┤
│ CTA de rodapé (opcional)│
│ tab bar (fixa)          │
└─────────────────────────┘
```

Viewport de referência: **390 × 844** (iPhone 14). Raio de canto padrão: 13–15 px em cards, 20–26 px em botões pílula, 50% em avatares e pins.

## Tema escuro

O app responde a `prefers-color-scheme` e ao atributo `data-theme`. No escuro o vermelho da marca sobe para `#FF2B3C` para manter contraste sobre fundo `#131417` — o `#E50012` original não passa em texto pequeno sobre escuro.
