# utils/notificaciones.py
import requests
from config import TELEGRAM_CONFIG

def enviar_telegram(mensaje: str):
    if not TELEGRAM_CONFIG.get("ENABLED", False):
        return
    token = TELEGRAM_CONFIG["TOKEN"]
    chat_id = TELEGRAM_CONFIG["CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": mensaje})
