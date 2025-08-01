# modules/movimiento_brusco.py
import time
import datetime
import yfinance as yf
from config import CONFIG
from utils.notificaciones import enviar_telegram, mercado_abierto

# Diccionario para almacenar el precio anterior de cada ticker
precios_anteriores = {}

def obtener_hora_actual_et():
    return datetime.datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])

def calcular_cambio_porcentual(precio_actual, precio_base):
    """Calcula el cambio porcentual entre dos precios."""
    if precio_base is None or precio_base == 0:
        return 0  # Evitar división por cero o valores nulos
    return ((precio_actual - precio_base) / precio_base) * 100

def run_movimiento_brusco():
    """
    Monitorea el movimiento brusco intradiario de las posiciones cortas.
    Envía alertas cuando el cambio porcentual entre dos intervalos es significativo.
    """
    global precios_anteriores
    print("🚀 Iniciando módulo de detección de Movimiento Brusco...")
    posiciones = CONFIG["POSICIONES_CORTO"]
    print(f"🔍 Monitoreando movimiento brusco de {len(posiciones)} posiciones:")
    for ticker in posiciones:
        print(f" - {ticker}")
        if ticker not in precios_anteriores:
            precios_anteriores[ticker] = None

    while True:
        if not mercado_abierto():
            tiempo_intervalo = CONFIG["INTERVALOS"].get("MOVIMIENTO_BRUSCO", CONFIG["INTERVALOS"]["SHORT_MONITOR"])
            time.sleep(tiempo_intervalo)
            continue

        ahora = obtener_hora_actual_et()
        alertas_enviadas = []
        
        for ticker, datos in posiciones.items():
            try:
                ticker_obj = yf.Ticker(ticker)
                
                # --- 1. Obtener precio actual ---
                hist_actual = ticker_obj.history(period="1d", interval="5m")
                
                if hist_actual.empty:
                    raise ValueError("No se pudieron obtener datos históricos recientes (5m)")
                
                precio_actual = hist_actual['Close'].iloc[-1]
                
                if precio_actual is None or precio_actual <= 0:
                    raise ValueError("Precio actual no disponible o inválido")

                # --- 2. Obtener el precio ANTERIOR ---
                precio_anterior = precios_anteriores.get(ticker)
                
                # --- 3. Calcular el CAMBIO PORCENTUAL entre intervalos ---
                cambio_porcentual = 0.0
                if precio_anterior is not None and precio_anterior > 0:
                    cambio_porcentual = calcular_cambio_porcentual(precio_actual, precio_anterior)
                    cambio_porcentual = round(cambio_porcentual, 2)
                else:
                    if precio_anterior is None:
                        hist_diario = ticker_obj.history(period="1d", interval="1d")
                        if not hist_diario.empty:
                            precio_apertura_hoy = hist_diario['Open'].iloc[-1]
                            if precio_apertura_hoy is not None and precio_apertura_hoy > 0:
                                cambio_porcentual = calcular_cambio_porcentual(precio_actual, precio_apertura_hoy)
                                cambio_porcentual = round(cambio_porcentual, 2)
                                print(f"  ℹ️  {ticker}: Usando precio de apertura (${precio_apertura_hoy:.2f}) para primera comparación.")
                            else:
                                print(f"  ⚠️  {ticker}: Precio de apertura no disponible para primera comparación.")
                        else:
                            print(f"  ⚠️  {ticker}: Datos diarios no disponibles para primera comparación.")

                # --- 4. Actualizar el precio anterior para la próxima iteración ---
                precios_anteriores[ticker] = precio_actual

                # --- 5. Formar mensaje informativo (opcional para consola) ---
                mensaje_consola = (
                    f"  {ticker}: ${precio_anterior if precio_anterior else 'N/A'} → ${precio_actual:.2f} | "
                    f"Cambio: {cambio_porcentual:+.2f}% | "
                    f"Umbral: {datos.get('umbral_porcentaje', 2.0):.1f}%"
                )
                print(f"  {mensaje_consola}")

                # --- 6. Calcular P&L y Movimiento Total del Día para la Alerta ---
                pnl = (datos["precio_apertura"] - precio_actual) * datos["acciones"]
                pnl = round(pnl, 2)
                pnl_pct = calcular_cambio_porcentual(datos["precio_apertura"], precio_actual)
                pnl_pct = round(pnl_pct, 2)
                
                # Obtener movimiento total del día para incluir en la alerta
                cambio_total_dia = "N/A"
                try:
                    hist_diario_alerta = ticker_obj.history(period="1d", interval="1d")
                    if not hist_diario_alerta.empty:
                        precio_apertura_hoy_alerta = hist_diario_alerta['Open'].iloc[-1]
                        if precio_apertura_hoy_alerta is not None and precio_apertura_hoy_alerta > 0:
                            cambio_total_dia = calcular_cambio_porcentual(precio_actual, precio_apertura_hoy_alerta)
                            cambio_total_dia = round(cambio_total_dia, 2)
                except Exception:
                    pass # cambio_total_dia ya es "N/A"

                # --- 7. Verificar umbral para ALERTA ---
                umbral_movimiento = datos.get('umbral_porcentaje', 2.0) 
                
                if abs(cambio_porcentual) >= umbral_movimiento and ticker not in alertas_enviadas:
                    
                    # --- CORRECCIÓN: Formatear precio_anterior correctamente ---
                    precio_anterior_fmt = f"{precio_anterior:.2f}" if precio_anterior is not None else 'N/A'
                    
                    mensaje_alerta = (
                        f"⌚ Ultimo monitoreo: {ahora.strftime('%m-%d %H:%M')}\n"
                        f"📢 ALERTA en *{ticker}*:\n"
                        f"📊 Precio: ${precio_anterior_fmt} → ${precio_actual:.2f}\n"
                        f"📈 Cambio Brusco: {cambio_porcentual:+.2f}%\n"
                        f"⚖️ Umbral: {umbral_movimiento:.1f}%\n"
                        f"💵 P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)\n"
                        f"📊 Movimiento Total Hoy: {cambio_total_dia if cambio_total_dia != 'N/A' else 'N/A'}%"
                    )
                    enviar_telegram(mensaje_alerta)
                    print(f"  🔔 Alerta de movimiento brusco enviada para {ticker}: {cambio_porcentual:+.2f}% (Total Hoy: {cambio_total_dia if cambio_total_dia != 'N/A' else 'N/A'}%)")
                    alertas_enviadas.append(ticker)
                    
            # --- CORRECCIÓN: Manejo de excepciones más general ---
            except Exception as e: # En lugar de yf.YFinanceError
                print(f"⚠️ Error general procesando {ticker} (Movimiento Brusco): {str(e)}")
                continue

        tiempo_intervalo = CONFIG["INTERVALOS"].get("MOVIMIENTO_BRUSCO", CONFIG["INTERVALOS"]["SHORT_MONITOR"])
        time.sleep(tiempo_intervalo)

