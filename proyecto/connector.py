import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",   # mejor que localhost
        user="root",
        password="",       # ✅ VACÍO en XAMPP
        database="ing_software",
        port=3306,
        connection_timeout=5
    )