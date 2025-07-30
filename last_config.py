# Configuración compartida para todo el sistema
import pytz

# Configuración general
CONFIG = {
    "TELEGRAM": {
        "TOKEN": "8357187463:AAFQGR6GCuoThW6y_HgUJAeoMWl4bwQY178",
        "CHAT_ID": "-1002796158748"
    },
    "MERCADO": {
        "APERTURA": (9, 30),   # 9:30 AM ET
        "CIERRE": (16, 0),     # 4:00 PM ET
        "ZONA_HORARIA": pytz.timezone('US/Eastern')
    },
    "INTERVALOS": {
        "MONITOREO": 120,        # 60 segundos, 5 minutos
        "TOP_GAINERS": 3600    # 24 horas = 86400, 1 Hora 3600
    },
    "NOTIFICACIONES": {
        "TELEGRAM": True  # ✅ Esto faltaba
    }
}

# Posiciones en corto (ejemplo)
POSICIONES_CORTO = {
    "VAPE": {
        "precio_apertura": 60.56,
        "acciones": 400,
        "umbral_porcentaje": 2.5
    },
    "FTAI": {
        "precio_apertura": 141.48,
        "acciones": 145,
        "umbral_porcentaje": 2.5
    },
    "FSS": {
        "precio_apertura": 127.77,
        "acciones": 80,
        "umbral_porcentaje": 2.3
    },
    "WING": {
        "precio_apertura": 364.14,
        "acciones": 62,
        "umbral_porcentaje": 2.5
    }    
}