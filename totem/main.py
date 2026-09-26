import flet as ft
import random
import asyncio
import requests # <- Nova dependência para conversar com a API
from api.pagamento import process_payment, PaymentError

# ========================================================================================
# PALETA GOODWE (Lógica de carros e preços foi movida para a API)
# ========================================================================================
COR_BG        = "#FFFFFF"
COR_CARD      = "#FFFFFFFF"
COR_BORDA     = "#B3B3B3"
COR_GW        = "#E50012" 
COR_GW_ESCURO = "#9E000D" 
COR_GW_CLARO  = "#FF4D5A" 
COR_VERDE     = "#4CAF50"
COR_PAUSA     = "#FFC107"
COR_ALERTA    = "#EF5350"
COR_TEXTO     = "#000000"
COR_SUBTEXTO  = "#1B1B1B"
COR_BARRA_BG  = "#B8B8B8"
BARRA_W       = 390

# ========================================================================================
# APP PRINCIPAL
# ========================================================================================
async def main(page: ft.Page):
    page.title = "GoodWe — Posto de Recarga"
    page.bgcolor = COR_BG
    page.padding = 0
    page.window.width     = 500
    page.window.height    = 820
    page.window.resizable = False
    page.fonts = {
        "Mono": "https://fonts.gstatic.com/s/spacemono/v13/i7dPIFZifjKcF5UAWdDRYEF8RQ.woff2"
    }

    estado = {
        "veiculo_atual": "",
        "tipo_carregador_atual": "",
        "capacidade_atual": 0.0,
        "potencia_max_atual": 0.0,
        "numero_carros": 1,
        "estado_carga":  0.0,
        "acumulo":       0.0,
        "p_real_val":    0,
        "rodando":       False,
        "pausado":       False,
        "valor_total":   0.0,
    }

    # ── Textos reativos ──────────────────────────────────────────────────────────────────
    txt_modelo       = ft.Text("—", size=15, color=COR_TEXTO,    weight=ft.FontWeight.BOLD, font_family="Mono")
    txt_tipo         = ft.Text("—", size=13, color=COR_SUBTEXTO, font_family="Mono")
    txt_capacidade   = ft.Text("—", size=13, color=COR_SUBTEXTO, font_family="Mono")
    txt_potencia_max = ft.Text("—", size=13, color=COR_SUBTEXTO, font_family="Mono")
    txt_carros       = ft.Text("—", size=13, color=COR_GW,       font_family="Mono")
    txt_p_real       = ft.Text("—", size=13, color=COR_GW,       font_family="Mono")
    txt_pct          = ft.Text("0%",      size=34, color=COR_GW,      weight=ft.FontWeight.BOLD, font_family="Mono")
    txt_kwh          = ft.Text("0.00 kWh", size=12, color=COR_SUBTEXTO, font_family="Mono")
    txt_status_log   = ft.Text("Aguardando conexão...", size=12, color=COR_SUBTEXTO, font_family="Mono")
    txt_consumo      = ft.Text("", size=13, color=COR_TEXTO, font_family="Mono")
    txt_taxa         = ft.Text("", size=13, color=COR_TEXTO, font_family="Mono")
    txt_imposto      = ft.Text("", size=13, color=COR_TEXTO, font_family="Mono")
    txt_total        = ft.Text("", size=15, color=COR_GW,    weight=ft.FontWeight.BOLD, font_family="Mono")
    txt_pagamento_status = ft.Text("", size=13, color=COR_TEXTO, font_family="Mono")

    # ── Pagamento via Pix ────────────────────────────────────────────────────────────────
    img_pix_qr = ft.Image(src="", width=200, height=200, visible=False, fit=ft.BoxFit.CONTAIN)
    txt_pix_copia_cola = ft.TextField(
        label="Pix Copia e Cola", value="", read_only=True, visible=False,
        multiline=True, min_lines=2, max_lines=3, text_size=10, text_style=ft.TextStyle(font_family="Mono"),
    )

    # ── Tela de pagamento (estilo maquininha) ───────────────────────────────────────────
    txt_pagamento_valor = ft.Text("R$ 0,00", size=42, color=COR_GW, weight=ft.FontWeight.BOLD, font_family="Mono")
    txt_cartao_status    = ft.Text("Insira, aproxime ou passe o cartão", size=14, color=COR_TEXTO, font_family="Mono")
    anel_cartao          = ft.ProgressRing(width=46, height=46, color=COR_GW, stroke_width=4, visible=False)
    icone_resultado      = ft.Icon(ft.Icons.CHECK_CIRCLE, color=COR_VERDE, size=64)
    txt_resultado_titulo = ft.Text("", size=20, weight=ft.FontWeight.BOLD, font_family="Mono")
    txt_resultado_detalhe = ft.Text("", size=13, color=COR_SUBTEXTO, font_family="Mono", text_align=ft.TextAlign.CENTER)

    btn_metodo_credito   = ft.Ref[ft.FilledButton]()
    btn_metodo_debito    = ft.Ref[ft.FilledButton]()
    btn_metodo_pix       = ft.Ref[ft.FilledButton]()
    btn_tentar_novamente = ft.Ref[ft.FilledButton]()
    btn_cancelar_pagamento = ft.Ref[ft.FilledButton]()

    barra_fundo = ft.Container(width=BARRA_W, height=20, bgcolor=COR_BARRA_BG, border_radius=10)
    barra_fill  = ft.Container(width=0, height=20, bgcolor=COR_GW, border_radius=10,
                               shadow=ft.BoxShadow(blur_radius=10, color=COR_GW_ESCURO, spread_radius=1))
    barra_stack = ft.Stack(controls=[barra_fundo, barra_fill], width=BARRA_W, height=20)

    btn_confirmar_pix = ft.Ref[ft.FilledButton]()
    btn_copiar_pix = ft.Ref[ft.FilledButton]()
    btn_conectar  = ft.Ref[ft.FilledButton]()
    btn_iniciar   = ft.Ref[ft.FilledButton]()
    btn_pausar    = ft.Ref[ft.FilledButton]()
    btn_parar     = ft.Ref[ft.FilledButton]()
    btn_cancelar  = ft.Ref[ft.FilledButton]()
    recibo_card = ft.Container(visible=False)

    def log(msg, cor=COR_SUBTEXTO):
        txt_status_log.value = msg
        txt_status_log.color = cor

    # --- COMUNICAÇÃO COM A API ---
    def detectar_carro():
        try:
            # Consulta a API para descobrir o carro e a potência
            resposta = requests.get("http://127.0.0.1:8000/detectar-veiculo").json()
            carro = resposta["carro"]
            
            estado["numero_carros"] = resposta["numero_carros"]
            estado["p_real_val"] = resposta["potencia_real"]
            estado["capacidade_atual"] = carro["capacidade_kwh"]
            estado["potencia_max_atual"] = carro["potencia_max_ac"]
            
            txt_modelo.value       = carro["modelo"]
            txt_tipo.value         = f'Bateria: {carro["tipo"]}'
            txt_capacidade.value   = f'Capacidade: {carro["capacidade_kwh"]} kWh'
            txt_potencia_max.value = f'Pot. máx AC: {carro["potencia_max_ac"]} kW'
            txt_carros.value       = f'{estado["numero_carros"]} carro(s) simultâneo(s)'
            txt_p_real.value       = f'Potência real: {estado["p_real_val"]} kW'

            estado["veiculo_atual"] = carro["modelo"]
        except Exception as e:
            log("Erro: Ligue a API primeiro!", COR_ALERTA)

    def atualizar_barra(pct: float):
        nova_w = max(20, BARRA_W * pct / 100)
        cor    = COR_VERDE if pct >= 100 else (COR_GW_CLARO if pct >= 70 else COR_GW)
        barra_fill.width   = nova_w
        barra_fill.bgcolor = cor
        barra_fill.shadow  = ft.BoxShadow(blur_radius=10, color=cor, spread_radius=1)

    async def finalizar_recibo(parcial: bool = False):
        btn_pausar.current.visible   = False
        btn_parar.current.visible    = False
        btn_cancelar.current.visible = False

        try:
            # 1. Envia o consumo para a API calcular o preço em R$
            payload = {"kwh_acumulado": estado["acumulo"]}
            resp = await asyncio.to_thread(requests.post, "http://127.0.0.1:8000/gerar-recibo", json=payload)
            recibo = resp.json()

            estado["valor_total"] = recibo['total_rs']

            # 2. Atualiza os textos do recibo (usados dentro da tela de pagamento)
            txt_consumo.value = f"Consumo ({estado['acumulo']:.2f} kWh):   R$ {recibo['consumo_rs']:>6.2f}"
            txt_taxa.value    = f"Taxa fixa:              R$ {recibo['taxa_rs']:>6.2f}"
            txt_imposto.value = f"ISS (5%):               R$ {recibo['imposto_rs']:>6.2f}"
            txt_total.value   = f"TOTAL:                  R$ {recibo['total_rs']:>6.2f}"
            recibo_card.visible = True
            txt_pagamento_valor.value = f"R$ {recibo['total_rs']:.2f}"

            # =================================================================
            # 3. Salva a sessão no histórico (database.json via API)
            # =================================================================
            dados_para_salvar = {
                "id_sessao": random.randint(10000, 99999),
                "veiculo": txt_modelo.value,
                "tipo_carregador": txt_potencia_max.value,
                "energia_kWh": round(estado["acumulo"], 2),
                "tempo_min": estado.get("tempo_simulado_min", 0),
                "custo_total": f"{recibo['total_rs']:.2f}",
                "status": "PARCIAL" if parcial else "CONCLUIDO"
            }
            await asyncio.to_thread(
                requests.post, "http://127.0.0.1:8000/salvar-historico", json=dados_para_salvar
            )
            # =================================================================

            # 4. Abre a tela de pagamento (estilo maquininha) já com o valor calculado
            resetar_tela_pagamento()
            switcher.content = tela_pagamento

        except Exception as e:
            log(f"Erro ao processar recibo/banco de dados: {e}", COR_ALERTA)

        page.update()

    async def loop_carregamento():
        capacidade = estado["capacidade_atual"]
        passo = 0.1
        carga = float(random.randint(10, 50))
        estado["estado_carga"] = carga
        estado["acumulo"] = 0.0

        while carga < 100 and estado["rodando"]:
            if estado["pausado"]:
                await asyncio.sleep(0.2)
                continue

            if random.random() < 0.15: 
                acao = random.choice(["entra", "sai"])
                if acao == "entra" and estado["numero_carros"] < 5:
                    estado["numero_carros"] += 1
                    log(f"Novo carro na rede! Divisão de carga: {estado['numero_carros']} un.", COR_ALERTA)
                elif acao == "sai" and estado["numero_carros"] > 1:
                    estado["numero_carros"] -= 1
                    log(f"Veículo saiu. Carga liberada: {estado['numero_carros']} un.", COR_VERDE)
                
                try:
                    # Pergunta para a API a nova potência real devido ao tráfego
                    url = f"http://127.0.0.1:8000/recalcular-potencia?num_carros={estado['numero_carros']}&potencia_max_carro={estado['potencia_max_atual']}"
                    nova_p = requests.get(url).json()
                    estado["p_real_val"] = nova_p["potencia_real"]
                except:
                    pass

                txt_carros.value = f'{estado["numero_carros"]} carro(s) simultâneo(s)'
                txt_p_real.value = f'Potência real: {estado["p_real_val"]} kW'
                page.update()

            p = estado["p_real_val"]
            estado["acumulo"] += p * passo
            carga += (p * passo / capacidade) * 100
            
            if carga > 100: carga = 100
            
            estado["estado_carga"] = carga
            txt_pct.value = f"{carga:.1f}%"
            txt_kwh.value = f"{estado['acumulo']:.2f} kWh acumulado"
            atualizar_barra(carga)
            page.update()
            await asyncio.sleep(0.4)

        if estado["rodando"]:
            estado["rodando"] = False
            await finalizar_recibo(parcial=False)
            
    async def on_conectar(e):
        btn_conectar.current.disabled = True
        log("Cabo conectado...", COR_GW)
        page.update()
        await asyncio.sleep(0.6)

        log("Detectando veículo...", COR_GW)
        detectar_carro()
        page.update()
        await asyncio.sleep(0.4)

        btn_iniciar.current.disabled  = False
        btn_cancelar.current.disabled = False
        log("Veículo identificado — pronto para carregar", COR_VERDE)
        page.update()

    async def on_iniciar(e):
        btn_iniciar.current.disabled = True
        btn_cancelar.current.visible = False
        btn_pausar.current.visible   = True
        btn_parar.current.visible    = True
        estado["rodando"] = True
        estado["pausado"] = False
        log("Iniciando sessão de recarga...", COR_GW)
        page.update()
        page.run_task(loop_carregamento)

    def on_pausar(e):
        if not estado["pausado"]:
            estado["pausado"] = True
            btn_pausar.current.content = ft.Text("Retomar", font_family="Mono", size=12, weight=ft.FontWeight.BOLD)
            btn_pausar.current.style.bgcolor = {ft.ControlState.DEFAULT: COR_VERDE, ft.ControlState.DISABLED: COR_BORDA, ft.ControlState.HOVERED: "#66BB6A"}
            log("Recarga pausada", COR_PAUSA)
        else:
            estado["pausado"] = False
            btn_pausar.current.content = ft.Text("Pausar", font_family="Mono", size=12, weight=ft.FontWeight.BOLD)
            btn_pausar.current.style.bgcolor = {ft.ControlState.DEFAULT: COR_PAUSA, ft.ControlState.DISABLED: COR_BORDA, ft.ControlState.HOVERED: "#FFD54F"}
            log(f"Retomando... {estado['p_real_val']} kW", COR_GW)
        page.update()

    async def on_parar(e):
        if not estado["rodando"] and not estado["pausado"]:
            return
        estado["rodando"] = False
        estado["pausado"] = False
        log("Parando recarga...", COR_ALERTA)
        page.update()
        await finalizar_recibo(parcial=True)

    def on_cancelar(e):
        btn_cancelar.current.disabled = True
        btn_iniciar.current.disabled  = True
        btn_conectar.current.disabled = False
        txt_modelo.value = txt_tipo.value = txt_capacidade.value = "—"
        txt_potencia_max.value = txt_carros.value = txt_p_real.value = "—"
        log("Cabo desconectado.", COR_SUBTEXTO)
        page.update()

    def resetar_tela_pagamento():
        """Volta a tela de pagamento pro estado inicial: só a seleção de método visível."""
        bloco_selecao_metodo.visible = True
        bloco_cartao_lendo.visible   = False
        bloco_pix.visible            = False
        bloco_resultado.visible      = False

        anel_cartao.visible = False
        img_pix_qr.visible = False
        img_pix_qr.src = ""
        txt_pix_copia_cola.visible = False
        txt_pix_copia_cola.value = ""
        btn_copiar_pix.current.visible = False
        btn_confirmar_pix.current.visible = False
        btn_confirmar_pix.current.disabled = False

        for ref in (btn_metodo_credito, btn_metodo_debito, btn_metodo_pix):
            ref.current.disabled = False

        txt_pagamento_status.value = ""

    async def mostrar_resultado_pagamento(sucesso: bool, titulo: str, detalhe: str):
        """Tela final de aprovado/recusado. Se aprovado, volta sozinha pro início depois de alguns segundos."""
        bloco_selecao_metodo.visible = False
        bloco_cartao_lendo.visible   = False
        bloco_pix.visible            = False
        bloco_resultado.visible      = True

        icone_resultado.name  = ft.Icons.CHECK_CIRCLE if sucesso else ft.Icons.CANCEL
        icone_resultado.color = COR_VERDE if sucesso else COR_ALERTA
        txt_resultado_titulo.value = titulo
        txt_resultado_titulo.color = COR_VERDE if sucesso else COR_ALERTA
        txt_resultado_detalhe.value = detalhe
        btn_tentar_novamente.current.visible = not sucesso
        page.update()

        if sucesso:
            await asyncio.sleep(3.5)  # dá tempo da pessoa ler "aprovado" antes de voltar
            on_reiniciar(None)
            switcher.content = tela_splash
            page.update()

    def on_tentar_novamente(e):
        resetar_tela_pagamento()
        page.update()

    def on_cancelar_pagamento(e):
        on_reiniciar(None)
        switcher.content = tela_splash
        page.update()

    async def on_selecionar_metodo(e, metodo: str):
        # metodo: "credito" ou "debito" — mesma rota /pagamento, só muda o rótulo mostrado
        bloco_selecao_metodo.visible = False
        bloco_cartao_lendo.visible   = True
        anel_cartao.visible = False
        txt_cartao_status.value = "Insira, aproxime ou passe o cartão"
        txt_cartao_status.color = COR_TEXTO
        page.update()

        await asyncio.sleep(1.8)  # simula o tempo de leitura do cartão na maquininha real

        anel_cartao.visible = True
        txt_cartao_status.value = "Processando pagamento..."
        page.update()

        rotulo = "Cartão de Crédito" if metodo == "credito" else "Cartão de Débito"
        try:
            resp = await asyncio.to_thread(
                requests.post,
                "http://127.0.0.1:8000/pagamento",
                json={"amount": estado["valor_total"], "method": metodo},
            )
            resp.raise_for_status()
            resultado = resp.json()
            await mostrar_resultado_pagamento(
                True, "Pagamento Aprovado",
                f"{rotulo}\nID: {resultado['transaction_id'][:8]}...",
            )
        except requests.exceptions.HTTPError as err:
            detail = err.response.json().get("detail", "Pagamento recusado")
            await mostrar_resultado_pagamento(False, "Pagamento Recusado", f"{rotulo}\n{detail}")
        except requests.exceptions.RequestException:
            await mostrar_resultado_pagamento(False, "Falha na conexão", "Não foi possível falar com a API.")

    async def on_pagar_pix(e):
        bloco_selecao_metodo.visible = False
        bloco_pix.visible = True
        txt_pagamento_status.value = "Gerando QR Code Pix..."
        txt_pagamento_status.color = COR_GW
        page.update()

        try:
            resp = await asyncio.to_thread(
                requests.post,
                "http://127.0.0.1:8000/gerar-pix",
                json={"amount": estado["valor_total"]},
            )
            resp.raise_for_status()
            dados = resp.json()

            # No Flet 1.0 o Image não tem mais "src_base64" — o próprio "src" aceita
            # URL, caminho de asset ou uma string base64 diretamente.
            img_pix_qr.src = dados["qr_code_base64"]
            img_pix_qr.visible = True
            txt_pix_copia_cola.value = dados["payload"]
            txt_pix_copia_cola.visible = True
            btn_copiar_pix.current.visible = True
            btn_confirmar_pix.current.visible = True

            txt_pagamento_status.value = "Escaneie o QR Code ou copie o código Pix"
            txt_pagamento_status.color = COR_SUBTEXTO
        except requests.exceptions.RequestException:
            txt_pagamento_status.value = "Não foi possível gerar a cobrança Pix."
            txt_pagamento_status.color = COR_ALERTA
            bloco_pix.visible = False
            bloco_selecao_metodo.visible = True

        page.update()

    async def on_copiar_pix(e):
        # page.set_clipboard() foi removido no Flet 1.0 — clipboard virou um "service".
        await ft.Clipboard().set(txt_pix_copia_cola.value)
        txt_pagamento_status.value = "Código Pix copiado!"
        txt_pagamento_status.color = COR_VERDE
        page.update()

    async def on_confirmar_pix(e):
        # Simula a confirmação do pagamento depois que o "cliente" escaneou o QR.
        # Numa integração real, isso viria de um webhook do banco — aqui simulamos o clique.
        btn_confirmar_pix.current.disabled = True
        txt_pagamento_status.value = "Confirmando pagamento Pix..."
        txt_pagamento_status.color = COR_GW
        page.update()

        try:
            resp = await asyncio.to_thread(
                requests.post,
                "http://127.0.0.1:8000/pagamento",
                json={"amount": estado["valor_total"], "method": "pix"},
            )
            resp.raise_for_status()
            resultado = resp.json()
            await mostrar_resultado_pagamento(
                True, "Pagamento Aprovado", f"Pix\nID: {resultado['transaction_id'][:8]}...",
            )
        except requests.exceptions.HTTPError as err:
            detail = err.response.json().get("detail", "Pix recusado")
            txt_pagamento_status.value = detail
            txt_pagamento_status.color = COR_ALERTA
            btn_confirmar_pix.current.disabled = False  # deixa tentar de novo sem gerar outro QR
        except requests.exceptions.RequestException:
            txt_pagamento_status.value = "Não foi possível conectar à API."
            txt_pagamento_status.color = COR_ALERTA
            btn_confirmar_pix.current.disabled = False

        page.update()

    def on_reiniciar(e):
        estado.update({"rodando": False, "pausado": False, "acumulo": 0.0, "estado_carga": 0.0, "valor_total": 0.0})
        txt_modelo.value = txt_tipo.value = txt_capacidade.value = "—"
        txt_potencia_max.value = txt_carros.value = txt_p_real.value = "—"
        txt_pct.value = "0%"
        txt_kwh.value = "0.00 kWh"
        recibo_card.visible = False
        btn_pausar.current.content = ft.Text("Pausar", font_family="Mono", size=12, weight=ft.FontWeight.BOLD)
        btn_pausar.current.style.bgcolor = {ft.ControlState.DEFAULT: COR_PAUSA, ft.ControlState.DISABLED: COR_BORDA, ft.ControlState.HOVERED: "#FFD54F"}
        btn_pausar.current.visible    = False
        btn_parar.current.visible     = False
        btn_cancelar.current.visible  = True
        btn_cancelar.current.disabled = True
        btn_conectar.current.disabled = False
        btn_iniciar.current.disabled  = True
        btn_iniciar.current.visible   = True
        resetar_tela_pagamento()
        atualizar_barra(0)
        log("Aguardando conexão...")
        page.update()

    def botao(texto, handler, cor, ref, desabilitado=False, visivel=True):
        return ft.FilledButton(
            ref=ref,
            content=ft.Text(texto, font_family="Mono", size=12, weight=ft.FontWeight.BOLD),
            disabled=desabilitado, visible=visivel, on_click=handler,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: cor, ft.ControlState.DISABLED: COR_BORDA, ft.ControlState.HOVERED: COR_GW_CLARO},
                color={ft.ControlState.DEFAULT: "#1A1A1A", ft.ControlState.DISABLED: COR_SUBTEXTO},
                shape=ft.RoundedRectangleBorder(radius=8), elevation={"pressed": 0, "": 3},
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            ),
        )

    def secao(titulo, *controles):
        return ft.Container(
            padding=ft.Padding.all(16), margin=ft.Margin.symmetric(horizontal=16, vertical=5),
            bgcolor=COR_CARD, border_radius=10, border=ft.Border.all(1, COR_BORDA),
            content=ft.Column(spacing=8, controls=[
                ft.Text(titulo, size=10, color=COR_GW, style=ft.TextStyle(weight=ft.FontWeight.BOLD, font_family="Mono", letter_spacing=2)),
                ft.Divider(height=1, color=COR_BORDA), *controles,
            ]),
        )

    recibo_card = ft.Container(
        visible=False, padding=ft.Padding.all(16), margin=ft.Margin.symmetric(horizontal=16, vertical=5),
        bgcolor=COR_CARD, border_radius=10, border=ft.Border.all(1, COR_GW),
        shadow=ft.BoxShadow(blur_radius=18, color=COR_GW_ESCURO, spread_radius=2),
        content=ft.Column(spacing=6, controls=[
            ft.Text("RECIBO GOODWE", size=10, color=COR_GW, style=ft.TextStyle(weight=ft.FontWeight.BOLD, font_family="Mono", letter_spacing=2)),
            ft.Divider(height=1, color=COR_GW), txt_consumo, txt_taxa, txt_imposto, ft.Divider(height=1, color=COR_BORDA), txt_total,
        ]),
    )

    tela_principal = ft.Container(
        key="principal", expand=True, bgcolor=COR_BG,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO, spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=24, right=24, top=28, bottom=14),
                    content=ft.Column(spacing=2, controls=[
                        ft.Row(controls=[ft.Icon(ft.Icons.BOLT, color=COR_GW, size=30), ft.Text("GoodWe", size=24, color=COR_GW, weight=ft.FontWeight.BOLD, font_family="Mono")]),
                        ft.Text("POSTO DE RECARGA — SIMULAÇÃO", size=10, color=COR_SUBTEXTO, style=ft.TextStyle(font_family="Mono", letter_spacing=3)),
                    ]),
                ),
                secao("VEÍCULO DETECTADO", txt_modelo, ft.Row(spacing=16, controls=[txt_tipo, txt_capacidade]), txt_potencia_max),
                secao("REDE / BALANCEAMENTO", txt_carros, txt_p_real),
                ft.Container(
                    padding=ft.Padding.all(16), margin=ft.Margin.symmetric(horizontal=16, vertical=5),
                    bgcolor=COR_CARD, border_radius=10, border=ft.Border.all(1, COR_BORDA),
                    content=ft.Column(spacing=10, controls=[
                        ft.Text("ESTADO DE CARGA", size=10, color=COR_GW, style=ft.TextStyle(weight=ft.FontWeight.BOLD, font_family="Mono", letter_spacing=2)),
                        ft.Divider(height=1, color=COR_BORDA),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[txt_pct, txt_kwh]), barra_stack,
                    ]),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=24, vertical=6),
                    content=ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.TERMINAL, color=COR_SUBTEXTO, size=13), txt_status_log]),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                    content=ft.Row(spacing=8, wrap=True, controls=[
                        botao("Conectar", on_conectar, COR_GW, btn_conectar),
                        botao("Iniciar", on_iniciar, COR_VERDE, btn_iniciar, desabilitado=True),
                        botao("Pausar", on_pausar, COR_PAUSA, btn_pausar, visivel=False),
                        botao("Parar", on_parar, COR_ALERTA, btn_parar, visivel=False),
                        botao("Cancelar cabo", on_cancelar, "#555555", btn_cancelar, desabilitado=True),
                    ]),
                ),
            ],
        ),
    )

    # ── Blocos internos da tela de pagamento ────────────────────────────────────────────
    bloco_selecao_metodo = ft.Container(
        visible=True,
        content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Text("Escolha a forma de pagamento", size=13, color=COR_SUBTEXTO, font_family="Mono"),
            ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER, wrap=True, controls=[
                botao("💳 Crédito", lambda e: page.run_task(on_selecionar_metodo, e, "credito"), COR_GW, btn_metodo_credito),
                botao("💳 Débito", lambda e: page.run_task(on_selecionar_metodo, e, "debito"), COR_GW_ESCURO, btn_metodo_debito),
                botao("Pix", on_pagar_pix, COR_VERDE, btn_metodo_pix),
            ]),
        ]),
    )

    bloco_cartao_lendo = ft.Container(
        visible=False,
        content=ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Icon(ft.Icons.CREDIT_CARD, color=COR_GW, size=56),
            txt_cartao_status,
            anel_cartao,
        ]),
    )

    bloco_pix = ft.Container(
        visible=False,
        content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            img_pix_qr,
            txt_pix_copia_cola,
            ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER, controls=[
                botao("Copiar código", on_copiar_pix, "#555555", btn_copiar_pix, visivel=False),
                botao("Confirmar Pix", on_confirmar_pix, COR_VERDE, btn_confirmar_pix, visivel=False),
            ]),
        ]),
    )

    bloco_resultado = ft.Container(
        visible=False,
        content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            icone_resultado, txt_resultado_titulo, txt_resultado_detalhe,
            botao("Tentar novamente", on_tentar_novamente, COR_GW, btn_tentar_novamente, visivel=False),
        ]),
    )

    tela_pagamento = ft.Container(
        key="pagamento", expand=True, bgcolor=COR_BG,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO, spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=24, right=24, top=28, bottom=6),
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.BOLT, color=COR_GW, size=26),
                        ft.Text("GoodWe — Pagamento", size=18, color=COR_GW, weight=ft.FontWeight.BOLD, font_family="Mono"),
                    ]),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=14),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Text("VALOR A PAGAR", size=11, color=COR_SUBTEXTO, style=ft.TextStyle(font_family="Mono", letter_spacing=2)),
                        txt_pagamento_valor,
                    ]),
                ),
                recibo_card,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=16),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        bloco_selecao_metodo, bloco_cartao_lendo, bloco_pix, bloco_resultado,
                    ]),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=2),
                    alignment=ft.Alignment.CENTER,
                    content=txt_pagamento_status,
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                    alignment=ft.Alignment.CENTER,
                    content=botao("Cancelar", on_cancelar_pagamento, "#555555", btn_cancelar_pagamento),
                ),
            ],
        ),
    )

    logo_icon = ft.Container(opacity=0, animate_opacity=ft.Animation(duration=1200, curve=ft.AnimationCurve.EASE_IN_OUT), content=ft.Icon(ft.Icons.BOLT, color=COR_GW, size=80))
    logo_texto = ft.Container(opacity=0, animate_opacity=ft.Animation(duration=1200, curve=ft.AnimationCurve.EASE_IN_OUT), content=ft.Text("GoodWe", size=52, color=COR_GW, weight=ft.FontWeight.BOLD, font_family="Mono"))
    logo_sub = ft.Container(opacity=0, animate_opacity=ft.Animation(duration=1000, curve=ft.AnimationCurve.EASE_IN_OUT), content=ft.Text("POSTO DE RECARGA", size=11, color=COR_SUBTEXTO, style=ft.TextStyle(font_family="Mono", letter_spacing=4)))
    
    toque_hint = ft.Container(
        opacity=0, animate_opacity=ft.Animation(duration=900, curve=ft.AnimationCurve.EASE_IN_OUT),
        padding=ft.Padding.symmetric(horizontal=32, vertical=16), border_radius=30, border=ft.Border.all(1, COR_GW),
        content=ft.Row(
            spacing=10, alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.TOUCH_APP, color=COR_GW, size=20),
                ft.Text("TOQUE PARA COMEÇAR", size=13, color=COR_GW, style=ft.TextStyle(font_family="Mono", weight=ft.FontWeight.BOLD, letter_spacing=2)),
            ],
        )
    )

    tela_splash = ft.Container(
        key="splash", expand=True, bgcolor=COR_BG,
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
            controls=[
                ft.Container(height=80), logo_icon, ft.Container(height=16), logo_texto, ft.Container(height=8), logo_sub, ft.Container(height=80),
                ft.GestureDetector(on_tap=lambda e: page.run_task(entrar_na_tela_principal), content=toque_hint),
                ft.Container(height=40), ft.Text("v1.0 — SPRINT 2", size=10, color=COR_BORDA, style=ft.TextStyle(font_family="Mono", letter_spacing=1)),
            ],
        ),
    )

    switcher = ft.AnimatedSwitcher(content=tela_splash, transition=ft.AnimatedSwitcherTransition.FADE, duration=600, reverse_duration=400, expand=True)
    page.add(switcher)

    async def animar_splash():
        await asyncio.sleep(0.3); logo_icon.opacity = 1; page.update()
        await asyncio.sleep(0.5); logo_texto.opacity = 1; page.update()
        await asyncio.sleep(0.4); logo_sub.opacity = 1; page.update()
        await asyncio.sleep(0.6); page.run_task(pulsar_botao)

    async def pulsar_botao():
        while switcher.content.key == "splash":
            toque_hint.opacity = 1.0; page.update(); await asyncio.sleep(1.0)
            toque_hint.opacity = 0.3; page.update(); await asyncio.sleep(0.8)

    async def entrar_na_tela_principal(e=None):
        switcher.content = tela_principal; page.update()

    page.run_task(animar_splash)

ft.run(main)