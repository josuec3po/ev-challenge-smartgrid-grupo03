# Roteiro do vídeo técnico (até 5 minutos)

**Formato:** gravação de tela com narração (OBS ou gravador do Windows), 1080p. Cada bloco indica quem fala, o que aparece na tela e o texto sugerido. Os tempos somam 4min45s, o que deixa 15s de folga.

**Antes de gravar:**
- `uvicorn api.main:app` rodando e o dashboard aberto em `http://127.0.0.1:8000/dashboard`, em tela cheia, com clima Ensolarado e estratégia Inteligente.
- O totem aberto (`python run.py`) numa segunda janela.
- O README aberto no GitHub numa terceira aba.
- Ensaiar uma vez com cronômetro.

---

## 1. Abertura e problema (0:00 – 0:30) · Integrante 1

**Tela:** README no GitHub (título + equipe), depois o gráfico `fluxo_convencional.png`.

> "Somos a Equipe 3 do GoodWe Challenge e este é o Totem EV Inteligente na versão final. O problema de um eletroposto é simples: os motoristas querem carregar às seis da tarde, que é justamente o horário de ponta, quando a energia custa mais que o dobro. E a rede tem um limite: seis carregadores de 22 kW somam 132 kW, mas o posto só pode puxar 50. Nesse gráfico, um posto convencional: tudo vem da rede, inclusive no pico."

## 2. Arquitetura e tecnologias GoodWe (0:30 – 1:20) · Integrante 2

**Tela:** diagrama de arquitetura do README (rolar devagar).

> "A nossa solução integra os três pilares do desafio com produtos GoodWe. Na geração, um carport solar de 66 kWp ligado a dois inversores híbridos da série ET. Escolhemos o ET porque um único equipamento faz o MPPT dos painéis, carrega a bateria e conversa com a rede: é ele que deixa o algoritmo mandar energia do sol para a bateria ou da rede para a bateria. No armazenamento, baterias Lynx de lítio ferro-fosfato, que aguentam ciclo diário e crescem em módulos. Na recarga, seis HCA G2, que modulam a potência de cada carro em vez de só ligar e desligar.
>
> No software, o backend em FastAPI tem um pacote de energia separado, com simulação, algoritmo, indicadores, alertas e assistente. O totem em Flet e o dashboard web consomem a mesma API."

## 3. Algoritmo inteligente (1:20 – 2:10) · Integrante 3

**Tela:** fluxograma do algoritmo no README, depois o dashboard com o gráfico de fluxo.

> "A cada 15 minutos o algoritmo faz quatro coisas. Primeiro, corrige a previsão solar com o que os painéis entregaram na última hora. Segundo, define a meta de chegar às 17h com a bateria cheia; se o sol previsto não basta, compra energia da rede no fora de ponta, a 62 centavos, para não pagar R$ 1,52 na ponta. Terceiro, ordena os carros por menor folga: quem vai sair primeiro recebe potência primeiro. Na ponta, cada carro recebe só o mínimo para sair com a carga pedida. Quarto, faz o balanço e nunca passa dos 50 kW contratados.
>
> No gráfico dá para ver: o amarelo é o sol cobrindo o meio do dia, o verde é a bateria carregando à tarde e descarregando 40 kW quando a ponta começa."

## 4. Demonstração ao vivo (2:10 – 3:30) · Integrante 4

**Tela:** dashboard.

1. Clicar ▶ no "Agora" e deixar o dia rodar alguns segundos (mostra solar → bateria → rede mudando).
2. Trocar a estratégia para **Convencional** e depois voltar para **Inteligente** (os KPIs mudam).
3. Trocar o clima para **Nublado**.
4. Marcar **Simular falha de string** e mostrar o alerta crítico.
5. Clicar em **Alertas** e **Economia** no assistente.
6. Alternar para o totem: **Conectar** → mostrar a linha "Agora: x% solar · y% bateria · z% rede".

> "Aqui o dia está rodando: de manhã o sol divide com a rede, à tarde sobra e a bateria carrega, e às 18h a bateria assume. Se eu trocar para o posto convencional, o custo sobe de 323 para 593 reais por dia. No nublado o ganho cai, mas a redução na ponta continua perto de 49%, porque ela depende da bateria e não do sol.
>
> Agora vou simular uma falha: metade dos painéis desliga às 11h. O monitoramento compara a geração real com a esperada para o clima e em menos de uma hora dispara um alerta crítico, mandando verificar a string no inversor ET. O próprio algoritmo percebe a queda e compra mais energia barata, e a bateria chega na ponta quase igual.
>
> O assistente responde em português com os dados do dia. E no totem o motorista vê de onde vem a energia da recarga dele."

## 5. Resultados e sustentabilidade (3:30 – 4:25) · Integrante 5

**Tela:** seção de resultados do README (tabela + gráfico comparativo).

> "Nos números, com dados simulados e reprodutíveis: no dia ensolarado, 45% menos custo com energia, 49% menos rede no horário de ponta e 22 de 24 motoristas saindo com carga completa, contra 16 no posto convencional. A margem da recarga dobra, de 317 para 636 reais por dia, e estimamos cerca de 81 mil reais de economia por ano.
>
> Em sustentabilidade, a energia de um dia roda 3.300 km elétricos e evita cerca de 550 kg de CO₂ em relação à gasolina. E tirar metade do consumo do pico alivia a rede justamente quando o sistema aciona térmicas.
>
> Também somos honestos sobre os limites: os dados são simulados, a economia anual é extrapolada, e o algoritmo às vezes carrega a bateria com rede barata, o que aumenta um pouco o CO₂ da rede em troca de custo menor."

## 6. Fechamento (4:25 – 4:45) · Integrante 6

**Tela:** estrutura do repositório e terminal com `python -m pytest` passando.

> "Todo o código, diagramas, testes automatizados e a documentação estão no repositório. Os 25 testes verificam que o balanço de energia fecha, que a rede nunca passa do limite e que o algoritmo sempre ganha do posto convencional. Esse é o Totem EV Inteligente: sol de dia, bateria na ponta e cada kW no lugar certo. Obrigado!"
