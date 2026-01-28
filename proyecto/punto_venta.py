import flet as ft

# Sidebar unificado (animación, perfil, confirmación de cierre)
from sidebar import build_sidebar


def punto_venta_view(page: ft.Page, nombre: str) -> ft.View:
    """Vista principal del Punto de Venta (dashboard para EMPLEADO)."""

    # ------------------------------------------------------------------
    # NAVEGACIÓN
    # ------------------------------------------------------------------
    def ir_inicio(e=None):
        # Ya estamos en POS, pero se deja por consistencia con el sidebar.
        page.go("/pos")
        page.update()

    def ir_inventario(e=None):
        from inventario import inventario_view

        page.views.append(inventario_view(page, nombre))
        page.go("/inventario")
        page.update()

    def ir_movimientos(e=None):
        from movimientos import movimientos_view

        page.views.append(movimientos_view(page, nombre))
        page.go("/movimientos")
        page.update()

    def ir_caja_chica(e=None):
        from caja_chica import caja_chica_view

        page.views.append(caja_chica_view(page, nombre))
        page.go("/caja_chica")
        page.update()

    def ir_reportes(e=None):
        from generar_reportes import generar_reportes_view

        page.views.append(generar_reportes_view(page, nombre))
        page.go("/generar_reportes")
        page.update()

    def cerrar_sesion(e=None):
        from login import LoginView  # import local para evitar ciclos

        page.views.clear()
        page.views.append(LoginView(page))
        page.go("/")
        page.update()

    # ------------------------------------------------------------------
    # COMPONENTES (tarjetas)
    # ------------------------------------------------------------------
    def crear_tarjeta(titulo: str, descripcion: str, on_click):
        card = ft.Container(
            bgcolor="#FFFFFF",
            border_radius=24,
            padding=20,
            col={"xs": 12, "sm": 6, "md": 6, "lg": 3},
            content=ft.Column(
                [
                    ft.Text(titulo, size=18, weight="bold", color="#333333"),
                    ft.Text(descripcion, size=13, color="#666666"),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "Ingresar",
                        bgcolor="#C86DD7",
                        color="white",
                        on_click=on_click,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=20),
                            padding=20,
                        ),
                    ),
                ],
                alignment="spaceBetween",
                spacing=10,
            ),
            animate_scale=ft.Animation(300, "easeOut"),
            animate_opacity=300,
        )

        # Importante: evita AssertionError cuando el hover se dispara al cambiar de vista.
        def on_hover(e):
            if getattr(card, "page", None) is None:
                return
            card.scale = 1.03 if e.data == "true" else 1.0
            card.opacity = 1.0 if e.data == "true" else 0.95
            try:
                card.update()
            except AssertionError:
                # Puede ocurrir si el control se desmonta justo al navegar
                return

        card.on_hover = on_hover
        return card

    # ------------------------------------------------------------------
    # SIDEBAR (nuevo)
    # ------------------------------------------------------------------
    sidebar = build_sidebar(
        page=page,
        nombre=nombre,
        ir_inicio=ir_inicio,
        ir_inventario=ir_inventario,
        ir_movimientos=ir_movimientos,
        ir_caja_chica=ir_caja_chica,
        ir_reportes=ir_reportes,
        cerrar_sesion_real=cerrar_sesion,
    )

    # ------------------------------------------------------------------
    # CONTENIDO PRINCIPAL
    # ------------------------------------------------------------------
    tarjetas = ft.ResponsiveRow(
        [
            crear_tarjeta(
                "Ver Inventario",
                "Consulta todos los productos disponibles.",
                ir_inventario,
            ),
            crear_tarjeta(
                "Entradas y Salidas",
                "Registra compras a proveedores y ventas.",
                ir_movimientos,
            ),
            crear_tarjeta(
                "Caja Chica",
                "Controla los movimientos de efectivo del día.",
                ir_caja_chica,
            ),
            crear_tarjeta(
                "Generar Reportes",
                "Visualiza el resumen de ventas y movimientos.",
                ir_reportes,
            ),
        ],
        run_spacing=20,
        spacing=20,
    )

    main_content = ft.Container(
        expand=True,
        bgcolor="#F9F6FB",
        padding=20,
        content=ft.Column(
            [
                ft.Text(
                    f"Bienvenido, {nombre}",
                    size=18,
                    weight="bold",
                    color="#C86DD7",
                ),
                ft.Container(height=10),
                tarjetas,
            ],
            spacing=10,
        ),
    )

    layout = ft.Row([sidebar, main_content], expand=True)

    appbar = ft.AppBar(
        title=ft.Text("Punto de Venta"),
        center_title=False,
        bgcolor="#C86DD7",
        color="white",
    )

    return ft.View("/pos", controls=[layout], appbar=appbar)
