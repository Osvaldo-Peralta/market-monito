# config.py
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

# Cargar y validar variables de entorno críticas
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_TOKEN:
    raise ValueError("La variable de entorno BOT_TOKEN no está definida.")
if not TELEGRAM_CHAT_ID:
    raise ValueError("La variable de entorno CHAT_ID no está definida.")


# Configuración unificada en CONFIG
CONFIG = {
    "TELEGRAM": {
        "TOKEN": TELEGRAM_TOKEN,
        "CHAT_ID": TELEGRAM_CHAT_ID,
        "ENABLED": os.getenv("TELEGRAM_ENABLED", "True").lower() == "true"
    },
    "MERCADO": {
        "APERTURA_HORA": 9,     # Hora de apertura (ET)
        "APERTURA_MINUTO": 30,  # Minuto de apertura (ET)
        "CIERRE_HORA": 16,      # Hora de cierre (ET)
        "CIERRE_MINUTO": 0,     # Minuto de cierre (ET)
        # Considerando un mercado que opera Lunes a Viernes
        "DIAS_HABILES": [0, 1, 2, 3, 4], # Lunes=0, Martes=1, ..., Viernes=4
        "ZONA_HORARIA": pytz.timezone(os.getenv("TIMEZONE", "US/Eastern"))
    },
    "INTERVALOS": {
        "SHORT_MONITOR": int(os.getenv("SHORT_MONITOR_INTERVAL", 120)),
        "TOP_GAINERS": 3600,
        "ANOMALY_DETECTOR": 300,
        "MOVIMIENTO_BRUSCO": int(os.getenv("MOVIMIENTO_BRUSCO_INTERVAL", 300)), # Nuevo intervalo
        # Nuevo intervalo para detección de movimiento
        "DETECCION_MOVIMIENTO": int(os.getenv("DETECCION_MOVIMIENTO_INTERVAL", 600)) # Por ejemplo, cada 10 minutos
    },
    "POSICIONES_CORTO": {
        "VAPE": {
            "precio_apertura": 60.56,
            "acciones": 400,
            "umbral_porcentaje": 2.0 # Umbral para movimiento brusco
        },
        "FSS": {
            "precio_apertura": 127.77,
            "acciones": 80,
            "umbral_porcentaje": 2.0
        },
        "APLD": {
            "precio_apertura": 13.49,
            "acciones": 500,
            "umbral_porcentaje": 2.0
        },
        "WING": {
            "precio_apertura": 378.03,
            "acciones": 110,
            "umbral_porcentaje": 2.0
        },
        "FIG": {
            "precio_apertura": 120.15,
            "acciones": 50,
            "umbral_porcentaje": 2.0
        },
        "PI": {
            "precio_apertura": 160.75,
            "acciones": 55,
            "umbral_porcentaje": 2.0
        },
        "RDDT": {
            "precio_apertura": 194.01,
            "acciones": 30,
            "umbral_porcentaje": 2.0
        },
        "WK": {
            "precio_apertura": 79.49,
            "acciones": 60,
            "umbral_porcentaje": 2.0
        }
        # Puedes cargar estas posiciones desde un archivo JSON o CSV externo
    },
    
    "DETECCION_MOVIMIENTO": {
        # Lista de tickers a monitorear para movimientos bruscos
        # Esta lista puede incluir acciones de largo plazo que quieres vigilar
        "TICKERS_WATCHLIST": [
            "AAPL", "NVDA", "AMD", "TSLA", "META", "MSFT", "AMZN", "LLY",
            "GOOG", "ORLY", "ETN", "LVS", "NFLX", "BTI", "MPWR", "GEV",
            "PPIH", "GS", "AVGO"
        ],
        # Umbral por defecto para el cambio porcentual entre intervalos
        "UMBRAL_POR_DEFECTO": 3.0,
        # Diccionario para umbrales específicos por ticker (opcional, sobreescribe el por defecto)
        "UMBRALES_POR_TICKER": {
            "TSLA": 2.5, # TSLA es muy volátil, umbral más bajo
            # "META": 2.0, # Si no está, usa UMBRAL_POR_DEFECTO
        }
    },
}

print("✅ Configuración cargada y validada.")