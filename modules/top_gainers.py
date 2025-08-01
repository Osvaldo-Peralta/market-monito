# modules/top_gainers.py
import yfinance as yf
import datetime
import time
import csv
from config import CONFIG
from utils.notificaciones import enviar_telegram, mercado_abierto # Importar mercado_abierto

def obtener_hora_actual_et():
    return datetime.datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])

def run_top_gainers():
    # Verificar si el mercado está abierto antes de ejecutar
    if not mercado_abierto():
        print("ℹ️  Módulo Top Gainers no ejecutado: Mercado cerrado.")
        return # Salir de la función si el mercado está cerrado

    ahora = obtener_hora_actual_et()
    hoy = ahora.date()
    tz = CONFIG["MERCADO"]["ZONA_HORARIA"]
    # Crear el datetime de apertura con la zona horaria correcta
    apertura = tz.localize(datetime.datetime.combine(hoy, datetime.time(9, 30)))
    
    print(f"📈 Calculando top gainers desde apertura ({apertura.strftime('%H:%M')} ET)...")

    datos_ganadores = []
    
    for ticker in CONFIG["TOP_GAINERS_WATCHLIST"]:
        try:
            # Corregido: Uso de Ticker.history() para mayor robustez
            ticker_obj = yf.Ticker(ticker)
            # Obtener datos desde la apertura hasta ahora (intervalo 5m)
            data = ticker_obj.history(start=apertura, end=ahora, interval="5m", prepost=False) 
            
            if data.empty:
                print(f"⚠️ No hay datos para {ticker} en el rango solicitado.")
                continue
            
            # Asegurarse de que hay al menos dos puntos para calcular el cambio
            if len(data) < 2:
                print(f"⚠️ Datos insuficientes para {ticker}.")
                continue

            # Precio de apertura (primer valor disponible después de las 9:30)
            precio_apertura = data.iloc[0]['Open'] 
            # Precio actual (último cierre)
            precio_actual = data.iloc[-1]['Close'] 
            
            if precio_apertura <= 0:
                print(f"⚠️ Precio de apertura inválido para {ticker}.")
                continue

            cambio_pct = ((precio_actual - precio_apertura) / precio_apertura) * 100
            datos_ganadores.append((
                ticker,
                round(cambio_pct, 2),
                round(precio_apertura, 2),
                round(precio_actual, 2)
            ))
        except yf.YFinanceError as e: # Manejo de errores específicos de yfinance
            print(f"⚠️ Error de YFinance con {ticker}: {str(e)}")
        except Exception as e:
            print(f"⚠️ Error general con {ticker}: {str(e)}")
            continue

    # Ordenar y seleccionar top 3
    datos_ganadores.sort(key=lambda x: x[1], reverse=True)
    top_3 = datos_ganadores[:3]

    if not top_3:
        print("⚠️ No se encontraron datos para top gainers")
        return

    # Generar mensaje
    mensaje = "🏆 Top Gainers desde apertura:\n"
    for ticker, cambio, apertura, actual in top_3:
        mensaje += f"• {ticker}: {cambio:+.2f}% | ${apertura:.2f} → ${actual:.2f}\n"

    print(mensaje)
    enviar_telegram(mensaje)

    # Guardar CSV
    nombre_csv = f"reporte_top_gainers_{hoy}.csv"
    try:
        with open(nombre_csv, 'a', newline='', encoding='utf-8') as f: # Agregado encoding
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["Ticker", "Cambio %", "Apertura", "Actual", "Hora"])
            for item in top_3:
                writer.writerow([item[0], item[1], item[2], item[3], ahora.strftime("%H:%M:%S")])
        print(f"💾 Reporte Top Gainers guardado en {nombre_csv}")
    except Exception as e:
        print(f"⚠️ Error guardando CSV {nombre_csv}: {str(e)}")
