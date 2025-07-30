import yfinance as yf
import time
import pandas as pd
import requests
from datetime import datetime, time as dt_time
from config import CONFIG, POSICIONES_CORTO
import os
os.makedirs("reportes", exist_ok=True)

# Estado global
reporte_diario_enviado = False
ultimo_precios = {}
ultimo_log = {}

def obtener_precio_actual(ticker):
    try:
        accion = yf.Ticker(ticker)
        data = accion.history(period="1d", interval="1m")
        if data is None or data.empty:
            print(f"⏳ {ticker}: Sin datos todavía (probablemente muy temprano o sin volumen)")
            return None
        return data["Close"].iloc[-1]
    except Exception as e:
        print(f"❌ Error al obtener precio para {ticker}: {str(e)}")
    return None

def calcular_pnl(posicion, precio_actual):
    diferencia = posicion["precio_apertura"] - precio_actual
    pnl = diferencia * posicion["acciones"]
    porcentaje = (diferencia / posicion["precio_apertura"]) * 100
    return pnl, porcentaje

def mercado_abierto():
    ahora = datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])
    if ahora.weekday() >= 5:  # Fin de semana
        return False
    hora_actual = ahora.time()
    apertura = dt_time(*CONFIG["MERCADO"]["APERTURA"])
    cierre = dt_time(*CONFIG["MERCADO"]["CIERRE"])
    return apertura <= hora_actual <= cierre

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM']['TOKEN']}/sendMessage"
    payload = {
        "chat_id": CONFIG["TELEGRAM"]["CHAT_ID"],
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Error Telegram ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error en conexión Telegram: {str(e)}")
        return False

def enviar_reporte_diario():
    global reporte_diario_enviado
    if reporte_diario_enviado:
        return
        
    ahora = datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])
    fecha = ahora.strftime("%Y-%m-%d")
    mensaje = f"📊 *REPORTE DIARIO - {fecha}*\n\n"
    total_pnl = 0
    datos_disponibles = False
    registros = []

    for ticker, posicion in POSICIONES_CORTO.items():
        try:
            accion = yf.Ticker(ticker)
            hist = accion.history(period="1d")
            if not hist.empty:
                apertura = hist["Open"].iloc[0]
                cierre = hist["Close"].iloc[-1]
                maximo = hist["High"].max()
                minimo = hist["Low"].min()
                cambio = ((cierre - apertura) / apertura) * 100
                pnl_diario = (posicion["precio_apertura"] - cierre) * posicion["acciones"]
                total_pnl += pnl_diario
                
                mensaje += (
                    f"🔹 *{ticker}*\n"
                    f"• Apertura: ${apertura:.2f}\n"
                    f"• Cierre: ${cierre:.2f}\n"
                    f"• Cambio: {cambio:.2f}%\n"
                    f"• Rango: ${minimo:.2f}-${maximo:.2f}\n"
                    f"• P&L: ${pnl_diario:.2f}\n\n"
                )
                registros.append({
                    "Ticker": ticker,
                    "Apertura": apertura,
                    "Cierre": cierre,
                    "Maximo": maximo,
                    "Minimo": minimo,
                    "Cambio(%)": cambio,
                    "P&L": pnl_diario
                })
                datos_disponibles = True
        except Exception:
            pass
    
    if not datos_disponibles:
        return
        
    mensaje += f"💰 *TOTAL P&L DIARIO: ${total_pnl:.2f}*"
    if enviar_telegram(mensaje):
        reporte_diario_enviado = True

    # Guardar en CSV
    df_reporte = pd.DataFrame(registros)
    nombre_archivo = f"reportes/short_reporte_{fecha}.csv"
    df_reporte.to_csv(nombre_archivo, index=False)
    print(f"📁 Reporte guardado en: {nombre_archivo}")

def run_short_monitor():
    global reporte_diario_enviado, ultimo_precios, ultimo_log
    print("🚀 Iniciando módulo de ventas en corto...")
    
    # Inicializar últimos precios
    for ticker in POSICIONES_CORTO:
        ultimo_precios[ticker] = None
        ultimo_log[ticker] = ""

    print(f"🔍 Monitoreando {len(POSICIONES_CORTO)} posiciones:")
    for ticker in POSICIONES_CORTO:
        print(f" - {ticker}")
    
    while True:
        try:
            ahora_et = datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])
            timestamp = ahora_et.strftime("%Y-%m-%d %H:%M:%S")
            
            if mercado_abierto():
                print(f"\n🔍 Verificación Shorts Actions: {timestamp} ET")
                
                for ticker, posicion in POSICIONES_CORTO.items():
                    print(f"🔁 Revisando {ticker}")
                    precio_actual = obtener_precio_actual(ticker)
                    if precio_actual is None:
                        print(f"  ⚠️ {ticker}: No se pudo obtener precio")
                        continue

                    # Obtener apertura y cierre anterior para cálculo del cambio
                    try:
                        data_hoy = yf.Ticker(ticker).history(period="1d", interval="1m")
                        apertura_dia = data_hoy["Open"].iloc[0] if not data_hoy.empty else None
                    except Exception:
                        apertura_dia = None

                    try:
                        data_ayer = yf.Ticker(ticker).history(period="2d")
                        cierre_ayer = data_ayer["Close"].iloc[-2] if len(data_ayer) > 1 else None
                    except Exception:
                        cierre_ayer = None

                    # Cálculos de cambio
                    cambio_desde_apertura = ((precio_actual - apertura_dia) / apertura_dia) * 100 if apertura_dia else None
                    cambio_desde_cierre_ayer = ((precio_actual - cierre_ayer) / cierre_ayer) * 100 if cierre_ayer else None
                    
                    pnl, pct = calcular_pnl(posicion, precio_actual)
                    estado = "GANANCIA" if pnl > 0 else "PÉRDIDA"
                    cambio_significativo = abs(pct) >= posicion["umbral_porcentaje"]

                    # Verificar cambio de precio significativo
                    precio_cambio_significativo = True
                    if ultimo_precios[ticker] is not None:
                        cambio = abs((precio_actual - ultimo_precios[ticker]) / ultimo_precios[ticker]) * 100
                        precio_cambio_significativo = cambio > 0.5
                    
                    ultimo_precios[ticker] = precio_actual

                    simbolo = "🟢" if pnl > 0 else "🔴"
                    log_linea = (
                        f"  {simbolo} {ticker}: ${precio_actual:.2f} | "
                        f"P&L: ${pnl:+.2f} ({pct:+.2f}%) | "
                        f"Umbral: {posicion['umbral_porcentaje']}%"
                    )
                    
                    if log_linea != ultimo_log[ticker] or precio_cambio_significativo:
                        print(log_linea)
                        ultimo_log[ticker] = log_linea
                    
                    if cambio_significativo and precio_cambio_significativo:
                        alerta = (
                            f"🚨 *ALERTA {ticker}*\n"
                            f"📊 *Precio*: ${precio_actual:.2f}\n"
                            f"💰 *{estado}*: ${abs(pnl):.2f} ({abs(pct):.2f}%)\n"
                            f"📈 *Cambio desde apertura*: {cambio_desde_apertura:+.2f}%\n" if cambio_desde_apertura is not None else ""
                            f"📈 *Cambio desde cierre ayer*: {cambio_desde_cierre_ayer:+.2f}%\n" if cambio_desde_cierre_ayer is not None else ""
                            f"🎯 *Umbral*: {posicion['umbral_porcentaje']}%\n"
                            f"🕒 *Hora*: {timestamp} ET"
                        )
                        if CONFIG["NOTIFICACIONES"]["TELEGRAM"]:
                            if enviar_telegram(alerta):
                                print(f"  🔔 Alerta enviada para {ticker}")
                            time.sleep(1)  # Retardo entre mensajes
            else:
                hora_actual = ahora_et.time()
                cierre = dt_time(*CONFIG["MERCADO"]["CIERRE"])
                if not reporte_diario_enviado and hora_actual > cierre:
                    enviar_reporte_diario()
                if ahora_et.hour < 6:
                    reporte_diario_enviado = False
                    print(f"\n🔴 Mercado CERRADO | {timestamp} ET")
        
        except Exception as e:
            print(f"❌ Error en short_monitor: {str(e)}")
        
        time.sleep(CONFIG["INTERVALOS"]["MONITOREO"])
