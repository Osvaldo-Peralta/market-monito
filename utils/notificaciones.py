# utils/notificaciones.py
import requests
import datetime
from config import CONFIG

def mercado_abierto():
    """
    Verifica si el mercado está actualmente abierto según la configuración.
    Considera días hábiles (Lun-Vie) y horario de mercado.
    Compatible con el config.py actual que usa claves separadas para hora/minuto.
    """
    tz_mercado = CONFIG["MERCADO"]["ZONA_HORARIA"]
    ahora_et = datetime.datetime.now(tz_mercado)
    dia_semana = ahora_et.weekday() # Lunes=0, Domingo=6
    hora_actual = ahora_et.time()

    # Verificar si es un día hábil
    if dia_semana not in CONFIG["MERCADO"]["DIAS_HABILES"]:
        # print(f"ℹ️  Mercado cerrado: Es fin de semana o festivo ({ahora_et.strftime('%A')}).")
        return False

    # Crear objetos time para comparar usando las claves correctas de config.py
    apertura = datetime.time(CONFIG["MERCADO"]["APERTURA_HORA"], CONFIG["MERCADO"]["APERTURA_MINUTO"])
    cierre = datetime.time(CONFIG["MERCADO"]["CIERRE_HORA"], CONFIG["MERCADO"]["CIERRE_MINUTO"])

    # Verificar si la hora actual está dentro del horario de mercado
    if apertura <= hora_actual <= cierre:
        return True
    else:
        # print(f"ℹ️  Mercado cerrado: Hora actual {hora_actual.strftime('%H:%M')} fuera de horario ({apertura.strftime('%H:%M')}-{cierre.strftime('%H:%M')} ET).")
        return False

def enviar_telegram(mensaje: str):
    """
    Envía un mensaje por Telegram si las notificaciones están habilitadas.
    La verificación de mercado abierto se hace en el módulo que llama a esta función.
    """
    # 1. Verificar si Telegram está habilitado
    if not CONFIG["TELEGRAM"].get("ENABLED", False):
        print(f"Telegram deshabilitado. Mensaje no enviado: {mensaje[:50]}...")
        return

    # 2. Si está habilitado, enviar el mensaje
    token = CONFIG["TELEGRAM"]["TOKEN"]
    chat_id = CONFIG["TELEGRAM"]["CHAT_ID"]
    # Corregido: Eliminar el espacio en la URL
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": mensaje,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        response.raise_for_status() # Lanza una excepción para códigos de error HTTP
        # print(f"✅ Mensaje enviado a Telegram: {mensaje[:50]}...")
        print(f"✅ Mensaje enviado a Telegram")
    except requests.exceptions.RequestException as e: # Manejo de errores de red más específico
        print(f"⚠️ Error de red enviando Telegram: {str(e)}")
    except Exception as e:
        print(f"⚠️ Error inesperado enviando Telegram: {str(e)}")
