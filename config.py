import pytz
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_CONFIG = {
    "TOKEN": os.getenv("BOT_TOKEN"),       # Usa dotenv o archivo separado idealmente
    "CHAT_ID": os.getenv("CHAT_ID"),
    "ENABLED": True
}

# Horarios del mercado (ET)
MERCADO_CONFIG = {
    "APERTURA": (9, 30),
    "CIERRE": (16, 0),
    "ZONA_HORARIA": pytz.timezone("US/Eastern")
}

# Intervalos de ejecución por módulo
INTERVALOS_CONFIG = {
    "SHORT_MONITOR": 120,     # segundos
    "TOP_GAINERS": 3600,
    "ANOMALY_DETECTOR": 300
}

# Posiciones en corto
POSICIONES_CORTO = {
    "VAPE": {
        "precio_apertura": 60.56,
        "acciones": 400,
        "umbral_porcentaje": 2.5
    },
    # ...
}

# Opciones del módulo AnomalyDetector
ANOMALY_CONFIG = {
    "TICKERS_WATCHLIST": [
        "AAPL", "NVDA", "AMD", "TSLA",
        "META", "MSTF", "AMZN", "LLY",
        "GOOG", "ORLY", "ETN", "LVS", "NFLX",
        "BTI", "MPWR", "GEV", "ETN", "PPIH", "GS", "AVGO"],
    "INTERVAL": "5m",               # 1m si necesitas más granularidad
    "VENTANA_MEDIA": 20,            # Promedio de 20 velas para volumen
    "THRESHOLD_VOL_MULTIPLO": 2.5,  # Si volumen actual > 2.5 * promedio
    "THRESHOLD_PRICE_DELTA": 5.0    # % de variación en 1-5 velas
}
