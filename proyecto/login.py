import flet as ft
import hashlib
from connector import get_connection
from registro import RegistroView
from corte_manager import abrir_corte


# -------------------------------------------------------------------
# COMPATIBILIDAD FLET
# -------------------------------------------------------------------
if not hasattr(ft, "icons") and hasattr(ft, "Icons"):
    ft.icons = ft.Icons

if not hasattr(ft, "animation"):
    ft.animation = ft

_original_container = ft.Container

def SafeContainer(*args, **kwargs):
    kwargs.pop("elevation", None)
    return _original_container(*args, **kwargs)

ft.Container = SafeContainer


# -------------------------------------------------------------------
# LOGIN PRINCIPAL
# -------------------------------------------------------------------
def LoginView(page: ft.Page):

    txt_user = ft.TextField(label="Correo o Usuario", border_radius=12)
    txt_pass = ft.TextField(label="Contraseña", password=True, border_radius=12)
    lbl_msg = ft.Text("")

    # -------------------------------------------------------------
    # INICIAR SESIÓN
    # -------------------------------------------------------------
    def login(e):
        from menu import menu_interactivo_view
        from punto_venta import punto_venta_view

        user = (txt_user.value or "").strip()
        password = (txt_pass.value or "").strip()

        if not user or not password:
            lbl_msg.value = "Ingresa usuario y contraseña"
            lbl_msg.color = "red"
            page.update()
            return

        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT IdUsuario, NombreUsuario
                FROM usuario
                WHERE NombreUsuario=%s AND (Contraseña=%s OR Contraseña=%s)
                """,
                (user, password, password_hash),
            )
            user_row = cursor.fetchone()

            if not user_row:
                lbl_msg.value = "Usuario o contraseña incorrectos"
                lbl_msg.color = "red"
                page.update()
                return

            id_usuario = user_row["IdUsuario"]

            # ¿Es empleado?
            cursor.execute(
                "SELECT IdEmpleado, Nombre FROM empleado WHERE Usuario_IdUsuario=%s",
                (id_usuario,),
            )
            emp = cursor.fetchone()

            if emp:
                id_empleado = int(emp["IdEmpleado"])
                nombre_empleado = emp.get("Nombre") or user_row.get("NombreUsuario")

                corte_id = abrir_corte(id_empleado)

                page.client_storage.set("corte_id", int(corte_id))
                page.client_storage.set("empleado", nombre_empleado)

                page.views.append(punto_venta_view(page, nombre_empleado))
                page.go("/pos")
                page.update()
                return

            # ¿Es cliente?
            cursor.execute(
                "SELECT Nombre FROM cliente WHERE Usuario_IdUsuario=%s",
                (id_usuario,),
            )
            cli = cursor.fetchone()

            if cli:
                nombre = cli.get("Nombre") or user_row.get("NombreUsuario")
                page.views.append(menu_interactivo_view(page, nombre))
                page.go("/menu")
                page.update()
                return

            lbl_msg.value = "Tu usuario no está ligado a cliente ni empleado"
            lbl_msg.color = "red"
            page.update()

        except Exception as ex:
            lbl_msg.value = f"Error al conectar con la base de datos: {ex}"
            lbl_msg.color = "red"
            page.update()

        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    # -------------------------------------------------------------
    # IR A REGISTRO
    # -------------------------------------------------------------
    def ir_registro(e):
        page.views.append(RegistroView(page, "Cliente"))
        page.go("/registro")
        page.update()

    def olvidar(e):
        lbl_msg.value = "Función próximamente disponible"
        lbl_msg.color = "blue"
        page.update()

    contenido = ft.Container(
        expand=True,
        alignment=ft.Alignment(0, 0),  # ✅ CORREGIDO (centro absoluto)
        content=ft.Column(
            [
                ft.Text("Corallie Bubble", size=36, weight=ft.FontWeight.BOLD, color="#C86DD7"),
                ft.Text("Iniciar Sesión", size=22),
                txt_user,
                txt_pass,
                ft.ElevatedButton(
                    "Iniciar sesión",
                    bgcolor="#C86DD7",
                    color="white",
                    on_click=login,
                ),
                lbl_msg,
                ft.TextButton("Registrarse", on_click=ir_registro),
                ft.TextButton("Olvidé mi contraseña", on_click=olvidar),
            ],
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # ✅ CORRECTO
        ),
    )

    return ft.View(
        route="/",
        controls=[contenido]
    )