import flet as ft
from login import LoginView


def main(page: ft.Page):
    page.title = "Corallie Bubble - Punto de Venta"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F9F6FB"
    page.padding = 0

    # Función para regresar vista
    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            page.update()

    page.on_view_pop = view_pop

    # Cargar Login como primera vista
    page.views.clear()
    page.views.append(LoginView(page))
    page.update()


# ✅ NUEVA FORMA (Flet 0.80+)
ft.run(main)