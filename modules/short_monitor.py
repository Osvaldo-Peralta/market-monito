# modules/short_monitor.py
import time
import datetime
import yfinance as yf
from config import CONFIG
from utils.notificaciones import mercado_abierto # Ya no envía Telegram directamente para alertas

def obtener_hora_actual_et():
    return datetime.datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])

def calcular_cambio_porcentual(precio_actual, precio_base):
    """Calcula el cambio porcentual entre dos precios."""
    if precio_base is None or precio_base == 0:
        return 0  # Evitar división por cero o valores nulos
    return ((precio_actual - precio_base) / precio_base) * 100

def run_short_monitor():
    """
    Monitorea periódicamente el estado de las posiciones cortas.
    Calcula P&L y muestra en consola. No envía alertas de movimiento brusco.
    """
    print("🚀 Iniciando módulo de ventas en corto (Reportes)...")
    posiciones = CONFIG["POSICIONES_CORTO"]
    print(f"🔍 Generando reportes para {len(posiciones)} posiciones:")
    for ticker in posiciones:
        print(f" - {ticker}")

    while True:
        # Verificar si el mercado está abierto
        if not mercado_abierto():
            time.sleep(CONFIG["INTERVALOS"]["SHORT_MONITOR"])
            continue

        ahora = obtener_hora_actual_et()
        print(f"\n📊 Reporte Shorts: {ahora.strftime('%Y-%m-%d %H:%M:%S')} ET")
        
        for ticker, datos in posiciones.items():
            try:
                ticker_obj = yf.Ticker(ticker)
                
                # --- Obtener precio actual ---
                # Mejorado: Uso de history para obtener datos más confiables
                hist = ticker_obj.history(period="1d", interval="5m") 
                
                if hist.empty:
                    raise ValueError("No se pudieron obtener datos históricos")
                
                precio_actual = hist['Close'].iloc[-1] 
                
                if precio_actual is None or precio_actual <= 0:
                    raise ValueError("Precio actual no disponible o inválido")

                # --- Calcular P&L ---
                pnl = (datos["precio_apertura"] - precio_actual) * datos["acciones"]
                pnl = round(pnl, 2)
                pnl_pct = calcular_cambio_porcentual(
                    datos["precio_apertura"], # Base para P&L es tu precio de venta
                    precio_actual
                )
                pnl_pct = round(pnl_pct, 2)
                
                # --- Obtener precio de apertura del día para movimiento total ---
                hist_diario = ticker_obj.history(period="1d", interval="1d")
                if hist_diario.empty:
                    raise ValueError("No se pudieron obtener datos diarios")
                precio_apertura_hoy = hist_diario['Open'].iloc[-1]
                if precio_apertura_hoy is None or precio_apertura_hoy <= 0:
                    precio_apertura_hoy = hist['Open'].iloc[0]
                    if precio_apertura_hoy is None or precio_apertura_hoy <= 0:
                        raise ValueError("Precio de apertura del día no disponible")     
                # --- Calcular cambio porcentual intradiario (movimiento total del día) ---
                cambio_pct_intradiario = calcular_cambio_porcentual(precio_actual, precio_apertura_hoy)
                cambio_pct_intradiario = round(cambio_pct_intradiario, 2)
                
                mensaje = (
                    f"⌚ Ultimo monitoreo: {ahora.strftime('%m-%d %H:%M')}\n"
                    f"📢 ALERTA {"**"+ticker+"**"} {'🟢' if pnl >= 0 else '🔴'}\n"
                    f"📊 Precio actual: ${precio_actual:.2f}\n"
                    f"💵 P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)\n"
                    f"📈 Movimiento Hoy: {cambio_pct_intradiario:+.2f}%\n"
                    f"⚖️ Umbral: {datos['umbral_porcentaje']:.1f}%"
                )
                print(f"  {mensaje}")
                
            except yf.YFinanceError as e:
                print(f"⚠️ Error de YFinance al procesar {ticker}: {str(e)}")
            except Exception as e:
                print(f"⚠️ Error general procesando {ticker}: {str(e)}")
                continue

        time.sleep(CONFIG["INTERVALOS"]["SHORT_MONITOR"])
