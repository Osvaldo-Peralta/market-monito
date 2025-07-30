import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import CONFIG

def obtener_top_gainers(top_n=10, umbral_minimo=10.0):
    print("🔍 Obteniendo lista de acciones S&P500...")
    try:
        tabla = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        sp500 = tabla[0]
        tickers = sp500['Symbol'].tolist()

        print(f"📡 Consultando precios en tiempo real para {len(tickers)} acciones...")
        data = yf.download(tickers, period="1d", interval="1m", group_by="ticker", auto_adjust=True, threads=True, progress=False)

        resultados = []
        for ticker in tickers:
            try:
                df = data[ticker] if isinstance(data, dict) else data.xs(ticker, level=0, axis=1)
                if df.empty or len(df) < 2:
                    continue

                apertura = df["Open"].iloc[0]
                precio_actual = df["Close"].iloc[-1]

                if apertura > 0:
                    cambio = ((precio_actual - apertura) / apertura) * 100
                    if cambio >= umbral_minimo:
                        resultados.append((ticker, cambio, apertura, precio_actual))
            except Exception:
                continue

        resultados.sort(key=lambda x: x[1], reverse=True)
        periodo = "DÍA ACTUAL"
        return resultados[:top_n], periodo

    except Exception as e:
        print(f"❌ Error crítico en obtener_top_gainers: {str(e)}")
        return [], ""


def enviar_reporte_gainers(gainers, periodo, umbral_minimo):
    if not gainers:
        print(f"⚠️ No se encontraron acciones con ganancias > {umbral_minimo}%")
        # Mensaje alternativo cuando no hay ganadores significativos
        mensaje = (
            f"ℹ️ *REPORTE TOP GAINERS - {datetime.now().strftime('%Y-%m-%d')}*\n\n"
            f"No se encontraron acciones con ganancias superiores al {umbral_minimo}%\n"
            f"El mercado no presentó movimientos significativos en el período analizado."
        )
        enviar_telegram(mensaje)
        return
    
    fecha = datetime.now().strftime("%Y-%m-%d")
    mensaje = f"🏆 *TOP GAINERS (>{umbral_minimo}%) - {fecha} ({periodo})*\n\n"
    
    for i, (ticker, cambio, apertura, cierre) in enumerate(gainers):
        mensaje += (
            f"{i+1}. *{ticker}*: +{cambio:.2f}%\n"
            f"   • Apertura: ${apertura:.2f}\n"
            f"   • Cierre: ${cierre:.2f}\n\n"
        )
    
    mensaje += (
        f"_Estas acciones han mostrado ganancias significativas y podrían ser "
        f"candidatas para estrategias de venta en corto._\n\n"
        f"🔍 Recomendación: Analizar gráficos y fundamentales antes de operar."
    )
    
    enviar_telegram(mensaje)
    # Guardar CSV
    df_gainers = pd.DataFrame(gainers, columns=["Ticker", "Cambio(%)", "Apertura", "Cierre"])
    nombre_archivo = f"reportes/top_gainers_{fecha}.csv"
    df_gainers.to_csv(nombre_archivo, index=False)
    print(f"📁 Reporte top gainers guardado en: {nombre_archivo}")


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM']['TOKEN']}/sendMessage"
    payload = {
        "chat_id": CONFIG["TELEGRAM"]["CHAT_ID"],
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print("✅ Reporte top gainers enviado a Telegram")
        else:
            print(f"❌ Error Telegram ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {str(e)}")

def run_top_gainers():
    print("\n🔍 Buscando acciones con ganancias significativas...")
    umbral_minimo = 10.0  # Mínimo 10% de ganancia
    gainers, periodo = obtener_top_gainers(10, umbral_minimo)  # Top 10 con ganancia > 10%
    enviar_reporte_gainers(gainers, periodo, umbral_minimo)