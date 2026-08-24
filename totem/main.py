import flet as ft
import asyncio
import requests # <- Cliente HTTP: toda a lógica de negócio vive na API

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

    API_URL = "http://127.0.0.1:8000"

    estado = {
        "sessao_id":     None,
        "capacidade_atual": 0.0,
        "potencia_max_atual": 0.0,
        "numero_carros": 1,
        "estado_carga":  0.0,
        "acumulo":       0.0,
        "p_real_val":    0,
        "rodando":       False,
        "pausado":       False,
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

    barra_fundo = ft.Container(width=BARRA_W, height=20, bgcolor=COR_BARRA_BG, border_radius=10)
    barra_fill  = ft.Container(width=0, height=20, bgcolor=COR_GW, border_radius=10,
                               shadow=ft.BoxShadow(blur_radius=10, color=COR_GW_ESCURO, spread_radius=1))
    barra_stack = ft.Stack(controls=[barra_fundo, barra_fill], width=BARRA_W, height=20)

    btn_conectar  = ft.Ref[ft.FilledButton]()
    btn_iniciar   = ft.Ref[ft.FilledButton]()
    btn_pausar    = ft.Ref[ft.FilledButton]()
    btn_parar     = ft.Ref[ft.FilledButton]()
    btn_cancelar  = ft.Ref[ft.FilledButton]()
    btn_reiniciar = ft.Ref[ft.FilledButton]()
    recibo_card = ft.Container(visible=False)

    def log(msg, cor=COR_SUBTEXTO):
        txt_status_log.value = msg
        txt_status_log.color = cor

    # --- COMUNICAÇÃO COM A API ---
    # Toda a lógica de negócio (sorteio de veículo, balanceamento de carga,
    # loop de recarga e cálculo do recibo) vive na API. O Totem só chama os
    # endpoints de sessão e renderiza o estado devolvido.
    def detectar_carro():
        try:
            # Cria a sessão de carregamento na API (sorteia o veículo lá)
            resposta = requests.post(f"{API_URL}/sessao/iniciar").json()
            carro = resposta["carro"]

            estado["sessao_id"] = resposta["sessao_id"]
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
        except Exception as e:
            log("Erro: Ligue a API primeiro!", COR_ALERTA)

    def atualizar_barra(pct: float):
        nova_w = max(20, BARRA_W * pct / 100)
        cor    = COR_VERDE if pct >= 100 else (COR_GW_CLARO if pct >= 70 else COR_GW)
        barra_fill.width   = nova_w
        barra_fill.bgcolor = cor
        barra_fill.shadow  = ft.BoxShadow(blur_radius=10, color=cor, spread_radius=1)

    def finalizar_recibo(recibo: dict, parcial: bool = False):
        """Recebe o recibo já calculado pela API (a partir do kWh que o
        próprio servidor acumulou) e só renderiza — o Totem nunca calcula
        nem envia o consumo, evitando adulteração no terminal físico."""
        btn_pausar.current.visible   = False
        btn_parar.current.visible    = False
        btn_cancelar.current.visible = False

        if recibo:
            txt_consumo.value = f"Consumo ({estado['acumulo']:.2f} kWh):   R$ {recibo['consumo_rs']:>6.2f}"
            txt_taxa.value    = f"Taxa fixa:              R$ {recibo['taxa_rs']:>6.2f}"
            txt_imposto.value = f"ISS (5%):               R$ {recibo['imposto_rs']:>6.2f}"
            txt_total.value   = f"TOTAL:                  R$ {recibo['total_rs']:>6.2f}"

            recibo_card.visible = True
            btn_reiniciar.current.visible = True
        else:
            log("Erro ao processar pagamento via API", COR_ALERTA)
            page.update()
            return

        if parcial:
            log(f"Interrompido em {estado['estado_carga']:.1f}% — recibo parcial", COR_PAUSA)
        else:
            log("Bateria 100% — recibo emitido", COR_VERDE)
        page.update()

    CORES_LOG = {
        "gw": COR_GW, "verde": COR_VERDE, "pausa": COR_PAUSA,
        "alerta": COR_ALERTA, "subtexto": COR_SUBTEXTO,
    }

    async def loop_carregamento():
        # O loop só dispara requisições de "tick" — toda a matemática da
        # carga, a flutuação de rede e a detecção de 100% acontecem na API.
        while estado["rodando"]:
            if estado["pausado"]:
                await asyncio.sleep(0.2)
                continue

            try:
                resp = requests.post(f"{API_URL}/sessao/{estado['sessao_id']}/tick").json()
            except Exception:
                log("Erro de comunicação com a API", COR_ALERTA)
                await asyncio.sleep(0.4)
                continue

            estado["numero_carros"] = resp["numero_carros"]
            estado["p_real_val"]    = resp["potencia_real"]
            estado["estado_carga"]  = resp["estado_carga"]
            estado["acumulo"]       = resp["acumulo"]

            txt_carros.value = f'{estado["numero_carros"]} carro(s) simultâneo(s)'
            txt_p_real.value = f'Potência real: {estado["p_real_val"]} kW'
            txt_pct.value    = f"{estado['estado_carga']:.1f}%"
            txt_kwh.value    = f"{estado['acumulo']:.2f} kWh acumulado"
            atualizar_barra(estado["estado_carga"])

            if resp.get("log_msg"):
                log(resp["log_msg"], CORES_LOG.get(resp.get("log_cor"), COR_SUBTEXTO))

            page.update()

            if resp.get("completo"):
                estado["rodando"] = False
                finalizar_recibo(resp.get("recibo"), parcial=False)
                break

            await asyncio.sleep(0.4)

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
        log("Iniciando sessão de recarga...", COR_GW)
        page.update()

        try:
            # A API sorteia a carga inicial e zera o acumulado da sessão
            resp = requests.post(f"{API_URL}/sessao/{estado['sessao_id']}/iniciar-carga").json()
            estado["estado_carga"] = resp["estado_carga"]
            estado["acumulo"] = resp["acumulo"]
        except Exception:
            log("Erro ao iniciar sessão via API", COR_ALERTA)
            return

        estado["rodando"] = True
        estado["pausado"] = False
        page.run_task(loop_carregamento)

    def on_pausar(e):
        try:
            resp = requests.post(f"{API_URL}/sessao/{estado['sessao_id']}/pausar-retomar").json()
            estado["pausado"] = resp["pausado"]
        except Exception:
            log("Erro de comunicação com a API", COR_ALERTA)
            page.update()
            return

        if estado["pausado"]:
            btn_pausar.current.content = ft.Text("Retomar", font_family="Mono", size=12, weight=ft.FontWeight.BOLD)
            btn_pausar.current.style.bgcolor = {ft.ControlState.DEFAULT: COR_VERDE, ft.ControlState.DISABLED: COR_BORDA, ft.ControlState.HOVERED: "#66BB6A"}
        else:
            btn_pausar.current.content = ft.Text("Pausar", font_family="Mono", size=12, weight=ft.FontWeight.BOLD)
            btn_pausar.current.style.bgcolor = {ft.ControlState.DEFAULT: COR_PAUSA, ft.ControlState.DISABLED: COR_BORDA, ft.ControlState.HOVERED: "#FFD54F"}
        log(resp.get("log_msg", ""), CORES_LOG.get(resp.get("log_cor"), COR_SUBTEXTO))
        page.update()

    def on_parar(e):
        if not estado["rodando"] and not estado["pausado"]:
            return
        estado["rodando"] = False
        estado["pausado"] = False
        log("Parando recarga...", COR_ALERTA)
        page.update()

        try:
            resp = requests.post(f"{API_URL}/sessao/{estado['sessao_id']}/parar").json()
            estado["estado_carga"] = resp["estado_carga"]
            estado["acumulo"] = resp["acumulo"]
            finalizar_recibo(resp.get("recibo"), parcial=True)
        except Exception:
            log("Erro ao processar pagamento via API", COR_ALERTA)
            page.update()

    def on_cancelar(e):
        try:
            if estado["sessao_id"]:
                requests.post(f"{API_URL}/sessao/{estado['sessao_id']}/cancelar")
        except Exception:
            pass  # cancelamento é best-effort — a UI não deve travar por isso

        btn_cancelar.current.disabled = True
        btn_iniciar.current.disabled  = True
        btn_conectar.current.disabled = False
        txt_modelo.value = txt_tipo.value = txt_capacidade.value = "—"
        txt_potencia_max.value = txt_carros.value = txt_p_real.value = "—"
        log("Cabo desconectado.", COR_SUBTEXTO)
        page.update()

    def on_reiniciar(e):
        estado.update({"rodando": False, "pausado": False, "acumulo": 0.0, "estado_carga": 0.0})
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
        btn_reiniciar.current.visible = False
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
                recibo_card,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=4),
                    content=botao("Nova Sessão", on_reiniciar, COR_SUBTEXTO, btn_reiniciar, visivel=False),
                ),
                ft.Container(height=24),
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
