import flet as ft
from datetime import date
from connector import get_connection


# ------------------------------------------------------------
# PARCHES COMPATIBILIDAD FLET
# ------------------------------------------------------------
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

if not hasattr(ft, "animation"):
    ft.animation = ft

_original_container = ft.Container
def SafeContainer(*args, **kwargs):
    kwargs.pop("elevation", None)
    kwargs.pop("shadow", None)
    kwargs.pop("blur", None)
    return _original_container(*args, **kwargs)
ft.Container = SafeContainer


def movimientos_view(page: ft.Page, nombre: str) -> ft.View:
    # -----------------------------
    # Navegación
    # -----------------------------
    def volver_pos(e=None):
        if len(page.views) > 1:
            page.views.pop()
        page.update()

    def cerrar_sesion(e):
        from login import LoginView
        page.views.clear()
        page.views.append(LoginView(page))
        page.go("/")
        page.update()

    def ir_inicio(e=None):
        volver_pos()

    def ir_inventario(e=None):
        from inventario import inventario_view
        page.views.append(inventario_view(page, nombre))
        page.go("/inventario")
        page.update()

    def ir_movimientos(e=None):
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
        page.go("/reportes")
        page.update()

    # -----------------------------
    # Helpers UI compatibles
    # -----------------------------
    def open_overlay(ctrl):
        if hasattr(page, "open"):
            page.open(ctrl)
        else:
            page.dialog = ctrl
            ctrl.open = True
            page.update()

    def show_snack(texto: str):
        sb = ft.SnackBar(content=ft.Text(texto))
        if hasattr(page, "open"):
            page.open(sb)
        else:
            page.snack_bar = sb
            sb.open = True
            page.update()

    # -----------------------------
    # BD
    # -----------------------------
    def db_listar_productosstock():
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT IdProductosStock, Nombre, Cantidad
                FROM productosstock
                ORDER BY Nombre ASC
                """
            )
            return cur.fetchall() or []
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except Exception:
                pass

    def db_listar_movimientos(limit=100):
        """
        Une entradas + salidas y las devuelve ordenadas.
        Guardamos producto dentro de Descripcion/Detalle como: ID|NOMBRE|DESC
        """
        conn = None
        cur = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                f"""
                SELECT
                    'Entrada' AS Tipo,
                    Fecha AS FechaMov,
                    Cantidad AS Cant,
                    Descripcion AS Texto
                FROM entradasproductos
                UNION ALL
                SELECT
                    'Salida' AS Tipo,
                    FechaSalida AS FechaMov,
                    CAST(Cantidad AS DECIMAL(10,2)) AS Cant,
                    Detalle AS Texto
                FROM salidasproductos
                ORDER BY FechaMov DESC
                LIMIT {int(limit)}
                """
            )
            return cur.fetchall() or []
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except Exception:
                pass

    def db_registrar_movimiento(tipo: str, id_prod: int, nombre_prod: str, cantidad: float, descripcion: str):
        """
        Regla clave:
        - Entrada: suma stock y registra en entradasproductos
        - Salida: valida stock suficiente, resta stock y registra en salidasproductos
        Todo en una transacción (commit/rollback).
        """
        conn = None
        cur = None
        try:
            conn = get_connection()
            conn.start_transaction()
            cur = conn.cursor(dictionary=True)

            # 1) stock actual
            cur.execute(
                "SELECT Cantidad FROM productosstock WHERE IdProductosStock=%s FOR UPDATE",
                (id_prod,),
            )
            row = cur.fetchone()
            if not row:
                raise Exception("El producto ya no existe en inventario.")

            stock_actual = float(row["Cantidad"])

            if tipo == "Salida":
                if cantidad > stock_actual:
                    raise Exception(f"No puedes sacar {cantidad} porque solo hay {stock_actual} en stock.")

            # 2) actualizar stock
            if tipo == "Entrada":
                nuevo_stock = stock_actual + cantidad
            else:
                nuevo_stock = stock_actual - cantidad

            cur.execute(
                "UPDATE productosstock SET Cantidad=%s WHERE IdProductosStock=%s",
                (nuevo_stock, id_prod),
            )

            # 3) registrar movimiento (guardando producto dentro del texto)
            texto = f"{id_prod}|{nombre_prod}|{descripcion}".strip()

            if tipo == "Entrada":
                cur.execute(
                    """
                    INSERT INTO entradasproductos (Cantidad, Fecha, Descripcion, CorteCaja_idCorteCaja)
                    VALUES (%s, %s, %s, 1)
                    """,
                    (int(cantidad), date.today(), texto),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO salidasproductos (FechaSalida, Detalle, Cantidad, CorteCaja_idCorteCaja)
                    VALUES (%s, %s, %s, 1)
                    """,
                    (date.today(), texto, str(float(cantidad))),
                )

            conn.commit()
            return nuevo_stock

        except Exception:
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except Exception:
                pass

    # -----------------------------
    # UI Formulario
    # -----------------------------
    productos = db_listar_productosstock()

    def build_dropdown_options():
        return [
            ft.dropdown.Option(
                key=str(p["IdProductosStock"]),
                text=f'{p["Nombre"]} (Stock: {p["Cantidad"]})',
            )
            for p in productos
        ]

    dd_producto = ft.Dropdown(
        label="Producto",
        options=build_dropdown_options(),
        border_radius=12,
        width=420,
    )

    dd_tipo = ft.Dropdown(
        label="Tipo de movimiento",
        options=[ft.dropdown.Option("Entrada"), ft.dropdown.Option("Salida")],
        value="Entrada",
        border_radius=12,
        width=220,
    )

    txt_cantidad = ft.TextField(
        label="Cantidad",
        border_radius=12,
        width=220,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    txt_desc = ft.TextField(
        label="Descripción (motivo)",
        border_radius=12,
        width=420,
        multiline=True,
        min_lines=2,
        max_lines=3,
    )

    # -----------------------------
    # Tabla movimientos
    # -----------------------------
    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cantidad")),
            ft.DataColumn(ft.Text("Descripción")),
        ],
        rows=[],
        border_radius=12,
        heading_row_color="#F3E9F7",
        data_row_min_height=52,
        data_row_max_height=80,
    )

    def parse_texto(texto: str):
        # Espera: ID|NOMBRE|DESC
        try:
            parts = (texto or "").split("|", 2)
            if len(parts) == 3:
                return parts[0].strip(), parts[1].strip(), parts[2].strip()
        except Exception:
            pass
        return "", "Desconocido", (texto or "")

    def recargar_tabla():
        movimientos = db_listar_movimientos(limit=150)
        tabla.rows = []
        for m in movimientos:
            _pid, pnom, desc = parse_texto(m.get("Texto"))
            tabla.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(m.get("FechaMov")))),
                        ft.DataCell(ft.Text(str(m.get("Tipo")))),
                        ft.DataCell(ft.Text(f"{pnom}")),
                        ft.DataCell(ft.Text(str(m.get("Cant")))),
                        ft.DataCell(ft.Text(desc)),
                    ]
                )
            )
        page.update()

    def recargar_dropdown_productos():
        nonlocal productos
        productos = db_listar_productosstock()
        dd_producto.options = build_dropdown_options()
        page.update()

    def validar_form():
        ok = True
        dd_producto.error_text = None
        txt_cantidad.error_text = None
        txt_desc.error_text = None

        if not dd_producto.value:
            dd_producto.error_text = "Selecciona un producto"
            ok = False

        c_raw = (txt_cantidad.value or "").strip()
        try:
            c = float(c_raw)
        except Exception:
            c = -1

        if c <= 0:
            txt_cantidad.error_text = "Ingresa una cantidad válida (> 0)"
            ok = False

        d = (txt_desc.value or "").strip()
        if not d:
            txt_desc.error_text = "Escribe una descripción"
            ok = False

        page.update()
        return ok, c, d

    def guardar_movimiento(e):
        ok, c, d = validar_form()
        if not ok:
            return

        tipo = dd_tipo.value
        id_prod = int(dd_producto.value)

        # tomar nombre del producto (buscar en lista)
        nombre_prod = None
        for p in productos:
            if int(p["IdProductosStock"]) == id_prod:
                nombre_prod = str(p["Nombre"])
                break
        if not nombre_prod:
            show_snack("Producto no encontrado. Recarga e intenta de nuevo.")
            return

        try:
            nuevo_stock = db_registrar_movimiento(tipo, id_prod, nombre_prod, c, d)
            txt_cantidad.value = ""
            txt_desc.value = ""
            page.update()

            recargar_dropdown_productos()
            recargar_tabla()
            show_snack(f"{tipo} registrada ✅ Nuevo stock: {nuevo_stock}")
        except Exception as ex:
            open_overlay(ft.AlertDialog(title=ft.Text("No se pudo registrar"), content=ft.Text(str(ex))))

    recargar_tabla()

    # -----------------------------
    # Sidebar animado (MISMO)
    # -----------------------------
    sidebar_state = {"collapsed": False}
    nav_items_refs = []

    title = ft.Text("Corallie Bubble", size=18, weight="bold", color="white")
    subtitle = ft.Text("Punto de Venta", size=12, color="white70")

    avatar = ft.Container(
        width=44,
        height=44,
        border_radius=16,
        bgcolor="#FFE0F0",
        alignment=ft.alignment.center,
        content=ft.Text((nombre[:1] or "U").upper(), weight="bold", color="#6C2BD9"),
    )

    user_name = ft.Text(
        nombre,
        color="white",
        weight="bold",
        size=13,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    user_role = ft.Text("Empleado", size=11, color="white70")
    user_info = ft.Column([user_name, user_role], spacing=1, expand=True)

    user_header = ft.Container(
        padding=12,
        border_radius=18,
        bgcolor="rgba(255,255,255,0.12)",
        content=ft.Row([avatar, user_info], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    def nav_item(icon, text, on_click):
        icon_ctrl = ft.Icon(icon, color="white", size=22)
        text_ctrl = ft.Text(text, color="white", size=13, weight="w600", visible=True)
        nav_items_refs.append((icon_ctrl, text_ctrl))

        return ft.Container(
            height=44,
            padding=ft.padding.symmetric(horizontal=10),
            border_radius=16,
            ink=True,
            tooltip=text,
            on_click=on_click,
            content=ft.Row(
                [icon_ctrl, text_ctrl],
                spacing=10,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_hover=lambda e: (
                setattr(e.control, "bgcolor", "rgba(255,255,255,0.15)" if e.data == "true" else None),
                e.control.update(),
            ),
        )

    def apply_sidebar_state():
        collapsed = sidebar_state["collapsed"]

        sidebar.width = 76 if collapsed else 230
        title.visible = not collapsed
        subtitle.visible = not collapsed

        user_info.visible = not collapsed
        user_header.content = (
            ft.Column([avatar], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            if collapsed
            else ft.Row([avatar, user_info], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        for _icon_ctrl, text_ctrl in nav_items_refs:
            text_ctrl.visible = not collapsed

        for item in nav_column.controls + [logout_btn]:
            if isinstance(item.content, ft.Row):
                item.content.alignment = ft.MainAxisAlignment.CENTER if collapsed else ft.MainAxisAlignment.START
                item.padding = ft.padding.symmetric(horizontal=0 if collapsed else 10)

        page.update()

    def toggle_sidebar(e=None):
        sidebar_state["collapsed"] = not sidebar_state["collapsed"]
        apply_sidebar_state()

    nav_column = ft.Column(
        controls=[
            nav_item(ft.icons.HOME, "Inicio", ir_inicio),
            nav_item(ft.icons.INVENTORY_2, "Inventario", ir_inventario),
            nav_item(ft.icons.SWAP_HORIZ, "Entradas y salidas", ir_movimientos),
            nav_item(ft.icons.ACCOUNT_BALANCE_WALLET, "Caja chica", ir_caja_chica),
            nav_item(ft.icons.ASSESSMENT, "Reportes", ir_reportes),
        ],
        spacing=8,
    )

    logout_btn = nav_item(ft.icons.LOGOUT, "Cerrar sesión", cerrar_sesion)

    sidebar = ft.Container(
        width=230,
        bgcolor="#C86DD7",
        padding=16,
        animate=ft.animation.Animation(220, ft.AnimationCurve.EASE_OUT),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(icon=ft.icons.MENU, icon_color="white", on_click=toggle_sidebar),
                        ft.Container(expand=True, content=ft.Column([title, subtitle], spacing=0)),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=12),
                user_header,
                ft.Container(height=16),
                nav_column,
                ft.Container(expand=True),
                logout_btn,
            ],
            spacing=6,
        ),
    )

    apply_sidebar_state()

    # -----------------------------
    # Layout principal
    # -----------------------------
    header = ft.Row(
        [
            ft.Text("Entradas y Salidas", size=22, weight="bold", color="#C86DD7"),
            ft.Container(expand=True),
        ]
    )

    formulario = ft.Container(
        bgcolor="white",
        border_radius=18,
        padding=15,
        content=ft.Column(
            [
                ft.Text("Registrar movimiento", size=16, weight="bold"),
                ft.Row([dd_tipo, txt_cantidad], spacing=12),
                dd_producto,
                txt_desc,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Guardar",
                            bgcolor="#C86DD7",
                            color="white",
                            on_click=guardar_movimiento,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=18),
                        ),
                        ft.TextButton("Recargar tabla", on_click=lambda e: recargar_tabla()),
                    ],
                    spacing=12,
                ),
            ],
            spacing=10,
        ),
    )

    listado = ft.Container(
        expand=True,
        bgcolor="white",
        border_radius=18,
        padding=15,
        content=ft.Column(
            [
                ft.Text("Historial de movimientos", size=16, weight="bold"),
                ft.Container(expand=True, content=ft.ListView(expand=True, controls=[tabla])),
            ],
            expand=True,
        ),
    )

    main_content = ft.Container(
        expand=True,
        bgcolor="#F9F6FB",
        padding=20,
        content=ft.Column(
            [
                header,
                ft.Container(height=10),
                formulario,
                ft.Container(height=10),
                listado,
            ],
            expand=True,
        ),
    )

    layout = ft.Row([sidebar, main_content], expand=True)

    appbar = ft.AppBar(
        title=ft.Text("Corallie Bubble - Punto de Venta"),
        bgcolor="#C86DD7",
        color="white",
    )

    return ft.View("/movimientos", controls=[layout], appbar=appbar)
