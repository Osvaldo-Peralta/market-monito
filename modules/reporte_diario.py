# modules/reporte_diario.py
import datetime
import yfinance as yf
import csv
import os
from config import CONFIG
from utils.notificaciones import enviar_telegram, mercado_abierto

def obtener_hora_actual_et():
    return datetime.datetime.now(CONFIG["MERCADO"]["ZONA_HORARIA"])

def calcular_cambio_porcentual(precio_actual, precio_base):
    """Calcula el cambio porcentual entre dos precios."""
    if precio_base is None or precio_base == 0:
        return 0  # Evitar división por cero o valores nulos
    return ((precio_actual - precio_base) / precio_base) * 100

def generar_reporte_diario():
    """
    Genera un reporte diario de las posiciones cortas al cierre del mercado.
    Calcula P&L total del día y acumulado, guarda en CSV y envía por Telegram.
    """
    print("📊 Iniciando generación de Reporte Diario...")
    
    # Verificar si el mercado está cerrado para generar el reporte
    # (aunque este módulo se llame al cierre, es bueno verificar)
    if mercado_abierto():
        print("ℹ️  Mercado aún abierto. El reporte diario se genera al cierre.")
        return

    ahora = obtener_hora_actual_et()
    fecha_str = ahora.strftime('%Y-%m-%d')
    print(f"📅 Generando reporte para {fecha_str}")
    
    posiciones = CONFIG["POSICIONES_CORTO"]
    datos_reporte = []
    pnl_total_dia = 0.0
    pnl_total_acumulado = 0.0
    
    for ticker, datos in posiciones.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            
            # --- 1. Obtener precio de cierre del día ---
            # Usar history con periodo 1d e intervalo 1d para obtener el resumen del día
            hist_diario = ticker_obj.history(period="1d", interval="1d")
            
            if hist_diario.empty:
                print(f"⚠️ No se pudieron obtener datos diarios para {ticker}")
                # Usar precio actual como fallback si no hay datos diarios (aunque el mercado está cerrado)
                hist_actual = ticker_obj.history(period="1d", interval="1m")
                if not hist_actual.empty:
                    precio_cierre = hist_actual['Close'].iloc[-1]
                    print(f"  ℹ️  Usando último precio disponible para {ticker}: ${precio_cierre:.2f}")
                else:
                    print(f"  ⚠️  No se pudo obtener ningún precio para {ticker}. Saltando.")
                    continue
            else:
                # Obtener el precio de cierre del día
                precio_cierre = hist_diario['Close'].iloc[-1]
            
            if precio_cierre is None or precio_cierre <= 0:
                print(f"  ⚠️  Precio de cierre inválido para {ticker}. Saltando.")
                continue

            # --- 2. Calcular P&L del día ---
            # Asumimos que el precio de apertura para el P&L del día es el precio de venta en corto
            # Si tienes un precio de apertura real diferente, se podría ajustar aquí.
            # Para un P&L "del día", necesitaríamos el precio de apertura del día.
            # Pero como ya lo tienes configurado como precio de venta, calculamos P&L vs ese precio.
            
            # P&L Acumulado (desde la venta en corto)
            pnl_acumulado = (datos["precio_apertura"] - precio_cierre) * datos["acciones"]
            pnl_acumulado = round(pnl_acumulado, 2)
            pnl_pct_acumulado = calcular_cambio_porcentual(datos["precio_apertura"], precio_cierre)
            pnl_pct_acumulado = round(pnl_pct_acumulado, 2)
            
            # Para P&L del día, necesitamos el precio de apertura de HOY.
            try:
                precio_apertura_hoy = hist_diario['Open'].iloc[-1]
                if precio_apertura_hoy is not None and precio_apertura_hoy > 0:
                    pnl_dia = (precio_apertura_hoy - precio_cierre) * datos["acciones"]
                    pnl_dia = round(pnl_dia, 2)
                    pnl_pct_dia = calcular_cambio_porcentual(precio_apertura_hoy, precio_cierre)
                    pnl_pct_dia = round(pnl_pct_dia, 2)
                else:
                    # Si no hay precio de apertura válido, P&L del día es 0
                    pnl_dia = 0.0
                    pnl_pct_dia = 0.0
                    print(f"  ⚠️  Precio de apertura no disponible para {ticker}. P&L del día = $0.00.")
            except Exception as e:
                pnl_dia = 0.0
                pnl_pct_dia = 0.0
                print(f"  ⚠️  Error obteniendo precio de apertura para {ticker}: {e}. P&L del día = $0.00.")

            # --- 3. Agregar datos al reporte ---
            datos_reporte.append({
                "Fecha": fecha_str,
                "Ticker": ticker,
                "Precio Apertura Venta": datos["precio_apertura"], # Precio venta en corto
                "Precio Apertura Hoy": precio_apertura_hoy if 'precio_apertura_hoy' in locals() and precio_apertura_hoy else 'N/A',
                "Precio Cierre": precio_cierre,
                "P&L Día ($)": pnl_dia,
                "P&L Día (%)": pnl_pct_dia,
                "P&L Acumulado ($)": pnl_acumulado,
                "P&L Acumulado (%)": pnl_pct_acumulado,
                "Acciones": datos["acciones"]
            })
            
            # Sumar al total
            pnl_total_dia += pnl_dia
            pnl_total_acumulado += pnl_acumulado
            
            print(f"  {ticker}: Cierre ${precio_cierre:.2f} | P&L Día: ${pnl_dia:.2f} ({pnl_pct_dia:+.2f}%) | P&L Acum: ${pnl_acumulado:.2f} ({pnl_pct_acumulado:+.2f}%)")
            
        except Exception as e:
            print(f"⚠️ Error procesando {ticker} para reporte diario: {str(e)}")
            continue

    if not datos_reporte:
        print("⚠️ No se generó reporte: No hay datos para posiciones.")
        return

    # --- 4. Guardar reporte en CSV ---
    nombre_csv = f"reporte_posiciones_cortas_{fecha_str}.csv"
    try:
        # Verificar si el archivo ya existe para no sobrescribir encabezados
        archivo_existe = os.path.isfile(nombre_csv)
        
        with open(nombre_csv, 'a', newline='', encoding='utf-8') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=datos_reporte[0].keys())
            if not archivo_existe or os.path.getsize(nombre_csv) == 0:
                writer.writeheader()
            writer.writerows(datos_reporte)
        print(f"💾 Reporte diario guardado en {nombre_csv}")
    except Exception as e:
        print(f"⚠️ Error guardando CSV {nombre_csv}: {str(e)}")
        # Si falla guardar el CSV, continuamos con el envío de Telegram

    # --- 5. Enviar reporte por Telegram ---
    try:
        mensaje_telegram = (
            f"📊 *Reporte Diario de Posiciones Cortas* - {fecha_str}\n"
            f"--------------------\n"
        )
        for item in datos_reporte:
            mensaje_telegram += (
                f"📌 *{item['Ticker']}*\n"
                f"💵 Precio Cierre: ${item['Precio Cierre']:.2f}\n"
                f"📊 P&L Día: ${item['P&L Día ($)']:.2f} ({item['P&L Día (%)']:+.2f}%)\n"
                f"📈 P&L Acum: ${item['P&L Acumulado ($)']:.2f} ({item['P&L Acumulado (%)']:+.2f}%)\n\n"
            )
        
        mensaje_telegram += (
            f"💰*Resumen Total*\n"
            f"📈 P&L Día Total: ${pnl_total_dia:.2f}\n"
            f"💵 P&L Acumulado Total: ${pnl_total_acumulado:.2f}\n"
        )
        
        # Agregar emoji según el signo del P&L total
        if pnl_total_dia >= 0:
            mensaje_telegram += "📈 ¡Buen día para las cortas!\n"
        else:
            mensaje_telegram += "📉 Día difícil para las cortas.\n"

        enviar_telegram(mensaje_telegram)
        print("✅ Reporte diario enviado por Telegram.")
        
    except Exception as e:
        print(f"⚠️ Error enviando reporte por Telegram: {str(e)}")

    print("✅ Generación de Reporte Diario finalizada.")
