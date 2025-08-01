# modules/deteccion_movimiento.py
import time
import datetime
import yfinance as yf
from config import CONFIG
from utils.notificaciones import enviar_telegram, mercado_abierto

# Diccionario para almacenar el precio anterior de cada ticker
# Se inicializa como un diccionario vacío
precios_anteriores = {}

def obtener_hora_actual_et():
    return datetime.datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])

def calcular_cambio_porcentual(precio_actual, precio_base):
    """Calcula el cambio porcentual entre dos precios."""
    if precio_base is None or precio_base == 0:
        return 0  # Evitar división por cero o valores nulos
    return ((precio_actual - precio_base) / precio_base) * 100

def run_deteccion_movimiento():
    """
    Monitorea movimientos bruscos intradiarios de una lista de acciones.
    Envía alertas cuando el cambio porcentual entre dos intervalos es significativo.
    Pensado para identificar oportunidades de entrada o salidas potenciales.
    """
    global precios_anteriores # Acceder a la variable global
    print("🚀 Iniciando módulo de Detección de Movimiento (Oportunidades)...")
    
    # Obtener la lista de tickers a monitorear desde la configuración
    tickers_a_monitorear = CONFIG["DETECCION_MOVIMIENTO"]["TICKERS_WATCHLIST"]
    
    print(f"🔍 Monitoreando movimientos de {len(tickers_a_monitorear)} acciones:")
    for ticker in tickers_a_monitorear:
        print(f" - {ticker}")
        # Inicializar el diccionario de precios anteriores si es la primera vez
        if ticker not in precios_anteriores:
            precios_anteriores[ticker] = None

    # Definir el intervalo de monitoreo (puedes usar uno específico o el de movimiento_brusco)
    intervalo_monitoreo = CONFIG["INTERVALOS"].get("DETECCION_MOVIMIENTO", CONFIG["INTERVALOS"]["MOVIMIENTO_BRUSCO"])

    while True:
        # Verificar si el mercado está abierto antes de hacer cualquier cosa
        if not mercado_abierto():
            time.sleep(intervalo_monitoreo)
            continue

        ahora = obtener_hora_actual_et()
        # print(f"\n🔍 Verificación Detección de Movimiento: {ahora.strftime('%Y-%m-%d %H:%M:%S')} ET") # Opcional: loggear cada verificación
        alertas_enviadas = [] # Para evitar enviar la misma alerta múltiples veces en una iteración
        
        for ticker in tickers_a_monitorear: # Iterar sobre la lista de tickers
            try:
                ticker_obj = yf.Ticker(ticker)
                
                # --- 1. Obtener precio actual ---
                hist_actual = ticker_obj.history(period="1d", interval="5m") # Usar 5m
                
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
                    # Si no hay precio anterior, intentar usar el precio de apertura del día
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
                precio_anterior_fmt = f"{precio_anterior:.2f}" if precio_anterior is not None else 'N/A'
                mensaje_consola = (
                    f"  {ticker}: ${precio_anterior_fmt} → ${precio_actual:.2f} | "
                    f"Cambio: {cambio_porcentual:+.2f}% | "
                    f"Umbral: {CONFIG['DETECCION_MOVIMIENTO']['UMBRALES_POR_TICKER'].get(ticker, CONFIG['DETECCION_MOVIMIENTO']['UMBRAL_POR_DEFECTO']):.1f}%"
                )
                print(f"  {mensaje_consola}")

                # --- 6. Verificar umbral para ALERTA ---
                # Obtener umbral específico o usar el por defecto
                umbral_movimiento = CONFIG['DETECCION_MOVIMIENTO']['UMBRALES_POR_TICKER'].get(ticker, CONFIG['DETECCION_MOVIMIENTO']['UMBRAL_POR_DEFECTO'])
                
                # Solo enviar alerta si el cambio porcentual es significativo 
                # Y no se ha enviado ya en esta iteración para este ticker
                # Puedes personalizar la lógica aquí: solo caídas, solo subidas, ambos
                # Por ejemplo, para solo caídas: if cambio_porcentual <= -umbral_movimiento and ticker not in alertas_enviadas:
                if abs(cambio_porcentual) >= umbral_movimiento and ticker not in alertas_enviadas:
                    
                    # --- 7. Calcular Movimiento Total del Día para la Alerta ---
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

                    # --- 8. Formar y enviar mensaje de alerta ---
                    direccion_movimiento = "📉 Caída Brusca" if cambio_porcentual < 0 else "📈 Subida Brusca"
                    
                    mensaje_alerta = (
                        f"🔔 {direccion_movimiento} en *{ticker}*:\n"
                        f"  Precio: ${precio_anterior_fmt} → ${precio_actual:.2f}\n"
                        f"  Cambio Intervalo: {cambio_porcentual:+.2f}% (Umbral: {umbral_movimiento:.1f}%)\n"
                        f"  📊 Movimiento Total Hoy: {cambio_total_dia if cambio_total_dia != 'N/A' else 'N/A'}%"
                    )
                    enviar_telegram(mensaje_alerta)
                    print(f"  🔔 Alerta de movimiento brusco enviada para {ticker}: {cambio_porcentual:+.2f}% (Total Hoy: {cambio_total_dia if cambio_total_dia != 'N/A' else 'N/A'}%)")
                    alertas_enviadas.append(ticker) # Marcar como alerta enviada
                    
            except Exception as e: # Manejo de excepciones general
                print(f"⚠️ Error general procesando {ticker} (Detección Movimiento): {str(e)}")
                # Opcional: Resetear el valor anterior en caso de error 
                # precios_anteriores[ticker] = None
                continue

        time.sleep(intervalo_monitoreo)
