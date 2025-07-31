# modules/short_monitor.py
import time
import datetime
import yfinance as yf
import csv
from config import CONFIG
from utils.notificaciones import enviar_telegram, mercado_abierto # Importar mercado_abierto

def obtener_hora_actual_et():
    return datetime.datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])

def calcular_cambio_porcentual(precio_actual, precio_base):
    """Calcula el cambio porcentual entre dos precios."""
    if precio_base == 0:
        return 0  # Evitar división por cero
    return ((precio_actual - precio_base) / precio_base) * 100

def run_short_monitor():
    print("🚀 Iniciando módulo de ventas en corto...")
    posiciones = CONFIG["POSICIONES_CORTO"]
    print(f"🔍 Monitoreando {len(posiciones)} posiciones:")
    for ticker in posiciones:
        print(f" - {ticker}")

    while True:
        # Verificar si el mercado está abierto antes de hacer cualquier cosa
        if not mercado_abierto():
            # print("⏳ Mercado cerrado. Esperando para reanudar monitoreo de Shorts...")
            time.sleep(CONFIG["INTERVALOS"]["SHORT_MONITOR"]) # Esperar el intervalo normal
            continue # Volver al inicio del bucle

        ahora = obtener_hora_actual_et()
        print(f"\n🔍 Verificación Shorts Actions: {ahora.strftime('%Y-%m-%d %H:%M:%S')} ET")
        
        for ticker, datos in posiciones.items():
            try:
                ticker_obj = yf.Ticker(ticker)
                
                # --- 1. Obtener precio actual ---
                # Mejorado: Uso de history para obtener datos más confiables
                hist = ticker_obj.history(period="1d", interval="1m") 
                
                if hist.empty:
                    raise ValueError("No se pudieron obtener datos históricos recientes")
                
                precio_actual = hist['Close'].iloc[-1] # Último precio de cierre
                
                if precio_actual is None or precio_actual <= 0:
                    raise ValueError("Precio actual no disponible o inválido")

                # --- 2. Calcular P&L y su porcentaje (basado en tu precio de venta en corto) ---
                pnl = (datos["precio_apertura"] - precio_actual) * datos["acciones"]
                pnl = round(pnl, 2)
                pnl_pct = calcular_cambio_porcentual(datos["precio_apertura"], precio_actual) # Nota: invertido para P&L
                pnl_pct = round(pnl_pct, 2) # Este es el -53.42% en tu ejemplo

                # --- 3. Obtener precio de apertura del día actual ---
                # Usamos el primer precio disponible del día
                precio_apertura_hoy = hist['Open'].iloc[0] 
                
                if precio_apertura_hoy is None or precio_apertura_hoy <= 0:
                    raise ValueError("Precio de apertura del día no disponible")

                # --- 4. Calcular cambio porcentual intradiario ---
                # Este es el porcentaje que quieres usar para el umbral (-20.51% en tu ejemplo)
                cambio_pct_intradiario = calcular_cambio_porcentual(precio_actual, precio_apertura_hoy)
                cambio_pct_intradiario = round(cambio_pct_intradiario, 2)

                # --- 5. Formar mensaje y verificar umbral ---
                mensaje = (
                    f"{'🟢' if pnl >= 0 else '🔴'} {ticker}: ${precio_actual:.2f} | "
                    f"P&L: ${pnl:.2f} ({pnl_pct:+.2f}%) | " # Mostrar P&L %
                    f"Movimiento Hoy: {cambio_pct_intradiario:+.2f}% | " # Mostrar movimiento intradiario
                    f"Umbral: {datos['umbral_porcentaje']:.1f}%"
                )
                print(f"  {mensaje}")
                
                # Comparar el cambio intradiario con el umbral
                if abs(cambio_pct_intradiario) >= datos["umbral_porcentaje"]:
                    enviar_telegram(f"🔔 Alerta SHORT: {mensaje}")
                    print(f"  🔔 Alerta enviada para {ticker} (Umbral {datos['umbral_porcentaje']}% alcanzado)")
                
            except yf.YFinanceError as e: # Manejo de errores específicos de yfinance
                print(f"⚠️ Error de YFinance al procesar {ticker}: {str(e)}")
            except Exception as e:
                print(f"⚠️ Error general procesando {ticker}: {str(e)}")
                continue # Continuar con el siguiente ticker

        time.sleep(CONFIG["INTERVALOS"]["SHORT_MONITOR"])
