# app.py
import threading
import time
from datetime import datetime, time as dt_time, timedelta
from config import CONFIG
from modules.short_monitor import run_short_monitor
from modules.top_gainers import run_top_gainers
# Importar el nuevo módulo
from modules.movimiento_brusco import run_movimiento_brusco
from modules.deteccion_movimiento import run_deteccion_movimiento
from modules.reporte_diario import generar_reporte_diario

def ejecutar_diariamente(func, hora_ejecucion, nombre):
    tz = CONFIG["MERCADO"]["ZONA_HORARIA"]
    primera_ejecucion = True
    while True:
        ahora_et = datetime.now(tz)
        hora_objetivo = dt_time(*hora_ejecucion)
        # Asegurarse de que la fecha y hora combinadas tengan la zona horaria correcta
        proxima_ejecucion = tz.localize(datetime.combine(ahora_et.date(), hora_objetivo))
        
        # Si la hora programada ya pasó hoy, programarla para mañana
        if proxima_ejecucion <= ahora_et:
            proxima_ejecucion += timedelta(days=1)

        segundos_espera = (proxima_ejecucion - ahora_et).total_seconds()
        
        if primera_ejecucion:
            print(f"⏱️  Programando {nombre} a las {hora_objetivo} ET")
            primera_ejecucion = False

        # Si es hora de ejecutar
        if segundos_espera <= 0:
            print(f"⏰ Ejecutando {nombre} a las {ahora_et.strftime('%H:%M:%S')} ET")
            try:
                func() # Ejecutar la función directamente
            except Exception as e:
                print(f"❌ Error en {nombre}: {str(e)}")
            
            # Dormir un minuto para evitar ejecuciones múltiples si el reloj se ajusta
            time.sleep(61) 
            continue # Volver al inicio del bucle para recalcular la próxima ejecución

        # Esperar en intervalos, no todo el tiempo restante
        tiempo_espera = min(1800, segundos_espera) # Máximo 30 minutos
        if tiempo_espera > 60:
            print(f"⏳ Durmiendo {tiempo_espera/60:.1f} min para {nombre}")
        time.sleep(tiempo_espera)

# main.py (agregar después de la función ejecutar_diariamente)

def ejecutar_al_cierre(func, hora_cierre, nombre):
    """
    Ejecuta una función una vez al día al cierre del mercado.
    """
    tz = CONFIG["MERCADO"]["ZONA_HORARIA"]
    primera_ejecucion = True
    ejecutado_hoy = False # Bandera para evitar ejecuciones múltiples el mismo día
    
    while True:
        ahora_et = datetime.now(tz)
        hora_objetivo = dt_time(*hora_cierre)
        proxima_ejecucion = tz.localize(datetime.combine(ahora_et.date(), hora_objetivo))
        
        # Si la hora programada ya pasó hoy, programarla para mañana
        if proxima_ejecucion <= ahora_et:
            proxima_ejecucion += timedelta(days=1)
            ejecutado_hoy = False # Resetear bandera para el próximo día

        segundos_espera = (proxima_ejecucion - ahora_et).total_seconds()
        
        if primera_ejecucion:
            print(f"⏱️  Programando {nombre} para {hora_objetivo} ET (al cierre)")
            primera_ejecucion = False

        # Si es hora de ejecutar y no se ha ejecutado hoy
        if segundos_espera <= 0 and not ejecutado_hoy:
            print(f"⏰ Ejecutando {nombre} a las {ahora_et.strftime('%H:%M:%S')} ET")
            try:
                func() # Ejecutar la función directamente
                ejecutado_hoy = True # Marcar como ejecutado hoy
                print(f"✅ {nombre} ejecutado.")
            except Exception as e:
                print(f"❌ Error en {nombre}: {str(e)}")
            
            # Dormir un minuto para evitar ejecuciones múltiples si el reloj se ajusta
            time.sleep(61) 
            continue # Volver al inicio del bucle para recalcular la próxima ejecución

        # Esperar en intervalos, no todo el tiempo restante
        tiempo_espera = min(1800, segundos_espera) # Máximo 30 minutos
        if tiempo_espera > 60 and segundos_espera > 60: # Solo mostrar si hay más de 1 minuto
            print(f"⏳ Durmiendo {tiempo_espera/60:.1f} min para {nombre}")
        time.sleep(tiempo_espera)


def main():
    print("🚀 Iniciando Sistema de Trading Avanzado")
    try:
        # Hilo para REPORTES de cortos
        hilo_monitor = threading.Thread(
            target=run_short_monitor,
            daemon=True,
            name="ShortMonitor"
        )
        hilo_monitor.start()
        print(f"✅ Hilo ShortMonitor (Reportes) iniciado")

        # --- NUEVO HILO: Monitoreo de Movimiento Brusco ---
        hilo_movimiento = threading.Thread(
            target=run_movimiento_brusco,
            daemon=True,
            name="MovimientoBrusco"
        )
        hilo_movimiento.start()
        print(f"✅ Hilo MovimientoBrusco iniciado")

        # Hilo para top gainers (mañana)
        hilo_am = threading.Thread(
            target=ejecutar_diariamente,
            args=(run_top_gainers, (9, 45), "TopGainersAM"),
            daemon=True,
            name="TopGainersAM"
        )
        hilo_am.start()
        print(f"✅ Hilo TopGainersAM iniciado (09:45 AM ET)")

        # --- NUEVO HILO: Detección de Movimiento ---
        hilo_deteccion = threading.Thread(
            target=run_deteccion_movimiento,
            daemon=True,
            name="DeteccionMovimiento"
        )
        hilo_deteccion.start()
        print(f"✅ Hilo DeteccionMovimiento iniciado")

        # --- NUEVO HILO: Reporte Diario al Cierre ---
        # Programar para 5 minutos después del cierre del mercado (16:05 ET)
        hilo_reporte = threading.Thread(
            target=ejecutar_al_cierre,
            args=(generar_reporte_diario, (16, 30), "ReporteDiario"),
            daemon=True,
            name="ReporteDiario"
        )
        hilo_reporte.start()
        print(f"✅ Hilo ReporteDiario programado para 16:05 ET")

        # Monitor de estado
        estado_mercado_anterior = None
        ultimo_reporte_hilos = 0
        while True:
            time.sleep(300) # Dormir 5 minutos
            
            # Verificar estado del mercado
            from utils.notificaciones import mercado_abierto # Importar aquí
            estado_mercado_actual = mercado_abierto()
            
            if estado_mercado_actual != estado_mercado_anterior:
                estado_str = "ABIERTO" if estado_mercado_actual else "CERRADO"
                print(f"\n📊 Estado del Mercado: {estado_str}")
                estado_mercado_anterior = estado_mercado_actual

            # Mostrar estado de hilos aproximadamente cada hora
            tiempo_actual = time.time()
            if tiempo_actual - ultimo_reporte_hilos > 3300: # Cada ~55 minutos
                print("\n📊 Estado de hilos:")
                for hilo in threading.enumerate():
                    print(f" - {hilo.name}: {'✅ Activo' if hilo.is_alive() else '❌ Inactivo'}")
                ultimo_reporte_hilos = tiempo_actual

    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico en main: {str(e)}")

if __name__ == "__main__":
    # Verificar e instalar dependencias si faltan (opcional)
    try:
        import yfinance
        import pytz
        import requests
        import dotenv
    except ImportError as e:
        print(f"Faltan dependencias: {e}")
        import sys
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "pytz", "requests", "python-dotenv"])
        print("Dependencias instaladas. Por favor, reinicie el script.")
        sys.exit(0) # Salir después de instalar

    main()
