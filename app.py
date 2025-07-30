import threading
import time
from datetime import datetime, time as dt_time, timedelta
import pytz
from config import CONFIG
from modules.short_monitor import run_short_monitor
from modules.top_gainers import run_top_gainers

def ejecutar_diariamente(func, hora_ejecucion, nombre):
    """Ejecuta una función diariamente a una hora específica en ET"""
    tz = CONFIG["MERCADO"]["ZONA_HORARIA"]
    primera_ejecucion = True
    
    while True:
        try:
            ahora_et = datetime.now(tz)
            hora_actual = ahora_et.time()
            hora_objetivo = dt_time(*hora_ejecucion)
            
            # Si es la primera ejecución, mostrar hora programada
            if primera_ejecucion:
                print(f"⏱️  Programando {nombre} a las {hora_objetivo} ET")
                primera_ejecucion = False
            
            # Calcular diferencia de tiempo
            proxima_ejecucion = ahora_et.replace(
                hour=hora_objetivo.hour,
                minute=hora_objetivo.minute,
                second=0,
                microsecond=0
            )
            
            # Si la hora ya pasó hoy, programar para mañana
            if proxima_ejecucion < ahora_et:
                proxima_ejecucion += timedelta(days=1)
            
            segundos_espera = (proxima_ejecucion - ahora_et).total_seconds()
            
            # Si es hora de ejecutar
            if segundos_espera <= 0:
                print(f"⏰ Ejecutando {nombre} a las {hora_actual} ET")
                func()
                # Esperar para evitar múltiples ejecuciones
                time.sleep(61)
                continue
                
            # Dormir hasta la próxima ejecución
            tiempo_espera = min(1800, segundos_espera)  # Máximo 30 minutos
            if tiempo_espera > 60:
                print(f"⏳ Durmiendo {tiempo_espera/60:.1f} min para {nombre}")
            time.sleep(tiempo_espera)
                
        except Exception as e:
            print(f"❌ Error en ejecución diaria ({nombre}): {str(e)}")
            time.sleep(60)

def main():
    print("🚀 Iniciando Sistema de Trading Avanzado")
    
    try:
        # Iniciar monitoreo de ventas en corto
        hilo_monitor = threading.Thread(target=run_short_monitor, daemon=True)
        hilo_monitor.name = "ShortMonitor"
        hilo_monitor.start()
        print(f"✅ Hilo {hilo_monitor.name} iniciado")
        
        # Iniciar búsqueda de top gainers por la mañana (9:45 AM ET)
        hilo_gainers_manana = threading.Thread(
            target=ejecutar_diariamente, 
            args=(run_top_gainers, (9, 45), "TopGainers (AM)"),
            daemon=True
        )
        hilo_gainers_manana.name = "TopGainersAM"
        hilo_gainers_manana.start()
        print(f"✅ Hilo {hilo_gainers_manana.name} iniciado (09:45 AM ET)")
        
        # Iniciar otra ejecución al cierre (4:30 PM ET)
        hilo_gainers_tarde = threading.Thread(
            target=ejecutar_diariamente, 
            args=(run_top_gainers, (16, 30), "TopGainers (PM)"),
            daemon=True
        )
        hilo_gainers_tarde.name = "TopGainersPM"
        hilo_gainers_tarde.start()
        print(f"✅ Hilo {hilo_gainers_tarde.name} iniciado (04:30 PM ET)")
        #print("\n⚡ Ejecutando Top Gainers manualmente para pruebas")
        #run_top_gainers()
        
        # Monitorear estado de los hilos
        while True:
            time.sleep(3600)
            print("\n📊 Estado de hilos:")
            for hilo in threading.enumerate():
                estado = "Activo ✅" if hilo.is_alive() else "Inactivo ❌"
                print(f" - {hilo.name}: {estado}")
                
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico en main: {str(e)}")

if __name__ == "__main__":
    # Verificar e instalar dependencias
    try:
        import yfinance
        import pandas
        import pytz
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "yfinance", "pandas", "pytz", "requests"])
    
    main()