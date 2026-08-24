# Evolução de Arquitetura: Transição para Cliente-Servidor

## 1. Visão Geral
Durante a primeira fase de desenvolvimento, o sistema operava de forma que a interface visual e regras de negócios no estavam no mesmo arquivo. Para atender às exigências de uma **aplicação comercial** baseada na tecnologia GoodWe HCA G2, a arquitetura foi refatorada para o modelo Cliente-Servidor.

## 2. Justificativas Técnicas

A separação do código base em uma API (`FastAPI`) e um Client Visual (`Flet`) trouxe os seguintes benefícios diretos:

* **Segurança Lógica e Financeira:** A lógica de cálculo de potência e o fechamento do recibo financeiro ocorrem no lado do servidor. Isso impede que o terminal físico seja adulterado para modificar o valor cobrado pela energia consumida.
* **Escalabilidade:** A centralização das regras de negócio permite expansões futuras ágeis. Se o projeto demandar um aplicativo mobile para o usuário final no futuro, este aplicativo consumirá a mesma API, sem necessidade de reescrever a lógica.
* **Otimização do Fluxo de Trabalho:** A modularização do código elimina conflitos de versão e permite que os 3 desenvolvedores da equipe trabalhem em paralelo (ex: enquanto um finaliza o design do Totem, os outros focam nos algoritmos de divisão de carga da API).

## 3. Fluxo de Dados
1. O usuário interage com o **Totem (Flet)**.
2. O Totem dispara requisições HTTP (`GET`, `POST`) de forma invisível.
3. A **API (FastAPI)** recebe, valida, processa a matemática dos circuitos virtuais e retorna um arquivo JSON.
4. O Totem lê o JSON e renderiza as atualizações na tela sem travar a interface.