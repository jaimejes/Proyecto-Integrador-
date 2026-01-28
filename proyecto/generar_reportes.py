import flet as ft
from connector import get_connection
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


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


def generar_reportes_view(page: ft.Page, nombre_usuario: str = "Empleado"):

    # -----------------------------
    # Navegación base
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
        # Si tienes una vista "menu" o "punto_venta" úsala.
        # Aquí regresamos a la vista anterior como "inicio seguro".
        volver_pos()

    def ir_inventario(e=None):
        from inventario import inventario_view
        page.views.append(inventario_view(page, nombre_usuario))
        page.go("/inventario")
        page.update()

    def ir_movimientos(e=None):
        from movimientos import movimientos_view
        page.views.append(movimientos_view(page, nombre_usuario))
        page.go("/movimientos")
        page.update()

    def ir_caja_chica(e=None):
        from caja_chica import caja_chica_view
        page.views.append(caja_chica_view(page, nombre_usuario))
        page.go("/caja_chica")
        page.update()

    def ir_reportes(e=None):
        page.go("/reportes")
        page.update()

    # -----------------------------
    # Overlay helpers
    # -----------------------------
    def open_dialog(dlg: ft.AlertDialog):
        if hasattr(page, "open"):
            page.open(dlg)
        else:
            page.dialog = dlg
            dlg.open = True
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
    # CAMPOS REPORTE
    # -----------------------------
    txt_inicio = ft.TextField(label="Fecha inicio (YYYY-MM-DD)", width=250)
    txt_fin = ft.TextField(label="Fecha fin (YYYY-MM-DD)", width=250)

    lbl_total = ft.Text("", weight="bold")
    lbl_msg = ft.Text("")

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Hora")),
            ft.DataColumn(ft.Text("Detalle")),
            ft.DataColumn(ft.Text("Subtotal")),
            ft.DataColumn(ft.Text("Impuesto")),
            ft.DataColumn(ft.Text("Total")),
        ],
        rows=[],
        expand=True
    )

    ultimo_reporte = {"data": [], "total": 0.0, "inicio": "", "fin": ""}

    # --------------------------
    # VALIDAR FECHA
    # --------------------------
    def validar_fecha(fecha_str: str) -> bool:
        try:
            datetime.strptime(fecha_str, "%Y-%m-%d")
            return True
        except:
            return False

    # --------------------------
    # CONSULTA
    # --------------------------
    def consultar_reporte(inicio: str, fin: str):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                v.IdVentas,
                v.FechaVenta,
                v.Hora,
                v.DetalleVenta,
                d.Subtotal,
                d.Impuesto,
                d.Total
            FROM ventas v
            JOIN detalleventas d ON v.IdVentas = d.Ventas_IdVentas
            WHERE v.FechaVenta BETWEEN %s AND %s
            ORDER BY v.FechaVenta, v.Hora;
        """, (inicio, fin))

        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data

    # --------------------------
    # CARGAR EN PANTALLA
    # --------------------------
    def generar_en_pantalla(e):
        inicio = (txt_inicio.value or "").strip()
        fin = (txt_fin.value or "").strip()

        lbl_msg.value = ""
        lbl_msg.color = "red"
        lbl_total.value = ""
        tabla.rows.clear()

        if not inicio or not fin:
            lbl_msg.value = "Debes ingresar ambas fechas."
            page.update()
            return

        if not validar_fecha(inicio) or not validar_fecha(fin):
            lbl_msg.value = "Formato inválido. Usa YYYY-MM-DD."
            page.update()
            return

        data = consultar_reporte(inicio, fin)

        total_general = 0.0
        for row in data:
            total_general += float(row["Total"])

            tabla.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(row["IdVentas"]))),
                    ft.DataCell(ft.Text(str(row["FechaVenta"]))),
                    ft.DataCell(ft.Text(str(row["Hora"]))),
                    ft.DataCell(ft.Text(str(row["DetalleVenta"]))),
                    ft.DataCell(ft.Text(f'{float(row["Subtotal"]):.2f}')),
                    ft.DataCell(ft.Text(f'{float(row["Impuesto"]):.2f}')),
                    ft.DataCell(ft.Text(f'{float(row["Total"]):.2f}')),
                ])
            )

        lbl_total.value = f"Total vendido en el rango: $ {total_general:.2f}"

        ultimo_reporte["data"] = data
        ultimo_reporte["total"] = total_general
        ultimo_reporte["inicio"] = inicio
        ultimo_reporte["fin"] = fin

        page.update()

    # --------------------------
    # GENERAR PDF
    # --------------------------
    def crear_pdf(path_archivo: str, data: list, total: float, inicio: str, fin: str):
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(path_archivo, pagesize=letter)

        elements = []
        elements.append(Paragraph("Corallie Bubble - Reporte de Ventas", styles["Title"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Generado por: {nombre_usuario}", styles["Normal"]))
        elements.append(Paragraph(f"Rango: {inicio} a {fin}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        table_data = [
            ["ID", "Fecha", "Hora", "Detalle", "Subtotal", "Impuesto", "Total"]
        ]

        for r in data:
            table_data.append([
                str(r["IdVentas"]),
                str(r["FechaVenta"]),
                str(r["Hora"]),
                str(r["DetalleVenta"]),
                f'{float(r["Subtotal"]):.2f}',
                f'{float(r["Impuesto"]):.2f}',
                f'{float(r["Total"]):.2f}',
            ])

        table_data.append(["", "", "", "TOTAL GENERAL", "", "", f"{total:.2f}"])

        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))

        elements.append(t)
        doc.build(elements)

    # --------------------------
    # FILE PICKER (guardar PDF)
    # --------------------------
    def on_guardar_pdf_result(e: ft.FilePickerResultEvent):
        if not e.path:
            return

        if not ultimo_reporte["data"]:
            show_snack("Primero genera el reporte en pantalla.")
            return

        try:
            crear_pdf(
                e.path,
                ultimo_reporte["data"],
                ultimo_reporte["total"],
                ultimo_reporte["inicio"],
                ultimo_reporte["fin"]
            )
            show_snack(f"PDF guardado en: {e.path}")
        except Exception as ex:
            show_snack(f"Error al generar PDF: {ex}")

    file_picker = ft.FilePicker(on_result=on_guardar_pdf_result)
    page.overlay.append(file_picker)

    def descargar_pdf(e):
        if not ultimo_reporte["data"]:
            show_snack("Primero genera el reporte en pantalla.")
            return

        nombre = f"reporte_ventas_{ultimo_reporte['inicio']}_a_{ultimo_reporte['fin']}.pdf".replace(":", "-")
        file_picker.save_file(file_name=nombre, allowed_extensions=["pdf"])

    # -----------------------------
    # Sidebar animado (MISMO QUE INVENTARIO)
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
        content=ft.Text((nombre_usuario[:1] or "U").upper(), weight="bold", color="#6C2BD9"),
    )

    user_name = ft.Text(
        nombre_usuario,
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
    # UI principal (contenido reportes)
    # -----------------------------
    header = ft.Row(
        [
            ft.Text("Generar Reportes", size=22, weight="bold", color="#C86DD7"),
            ft.Container(expand=True),
        ],
        alignment="center",
    )

    acciones = ft.Row(
        [
            ft.ElevatedButton("Generar reporte", on_click=generar_en_pantalla),
            ft.ElevatedButton("Descargar PDF", on_click=descargar_pdf),
        ],
        wrap=True
    )

    tabla_responsiva = ft.Row(
        controls=[ft.Container(padding=6, content=tabla)],
        scroll=ft.ScrollMode.AUTO,
    )

    main_content = ft.Container(
        expand=True,
        bgcolor="#F9F6FB",
        padding=20,
        content=ft.Column(
            [
                header,
                ft.Text("Reporte de ventas por rango de fechas", size=14, color="black54"),
                ft.Container(height=8),
                ft.Row([txt_inicio, txt_fin], wrap=True),
                acciones,
                lbl_msg,
                lbl_total,
                ft.Container(
                    expand=True,
                    bgcolor="white",
                    border_radius=18,
                    padding=12,
                    content=ft.ListView(expand=True, controls=[tabla_responsiva]),
                ),
            ],
            expand=True
        )
    )

    layout = ft.Row([sidebar, main_content], expand=True)

    appbar = ft.AppBar(
        title=ft.Text("Corallie Bubble - Punto de Venta"),
        bgcolor="#C86DD7",
        color="white",
    )

    return ft.View("/reportes", controls=[layout], appbar=appbar)
