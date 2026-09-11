"""
Parcial III - Simulación. Trabajo práctico.
Universidad José Antonio Páez - Ingeniería en Computación.

Programa principal: menú de opciones para ejecutar las simulaciones,
enviar las métricas a la API de IA (Gemini) y generar los informes
p1.txt y p2.txt con el análisis y la conclusión.

Ejecución:  python main.py
"""
from datetime import datetime

from ia.analizador import AnalizadorIA
from simulacion.continua import SimulacionCluster
from simulacion.eventos_discretos import SimulacionFabrica
from utils import config
from utils.validaciones import leer_float, leer_int, leer_opcion

# Valores por defecto para pruebas
HORAS_DEFECTO_P1 = 8.0
HORAS_DEFECTO_P2 = 24.0
SEMILLA_DEFECTO = 42
STOCK_INICIAL_DEFECTO = 50
DT_DEFECTO_MIN = 1.0

SEPARADOR = "=" * 78


def escribir_informe(ruta, titulo, lineas_metricas, lineas_analisis, conclusion, fuente):
    """Escribe el archivo de texto corto y conciso con métricas, análisis y conclusión."""
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(f"{titulo}\n")
        archivo.write(f"Generado: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
        archivo.write("--- Métricas ---\n")
        for linea in lineas_metricas:
            archivo.write(f"{linea}\n")
        archivo.write("\n--- Análisis ---\n")
        for linea in lineas_analisis:
            archivo.write(f"{linea}\n")
        archivo.write(f"\n--- Conclusión y recomendación (fuente: {fuente}) ---\n")
        archivo.write(conclusion.strip() + "\n")
    print(f"\nInforme guardado en: {ruta}")


def mostrar_resultados(titulo, lineas_metricas, lineas_analisis, conclusion, fuente):
    """Muestra por pantalla el resumen de métricas, el análisis y la conclusión de la IA."""
    print(f"\n{SEPARADOR}\n{titulo}\n{SEPARADOR}")
    print("MÉTRICAS:")
    for linea in lineas_metricas:
        print(f"  {linea}")
    print("\nANÁLISIS:")
    for linea in lineas_analisis:
        print(f"  {linea}")
    print(f"\nCONCLUSIÓN Y RECOMENDACIÓN ({fuente}):")
    print(conclusion)
    print(SEPARADOR)


def ejecutar_problema_1(analizador):
    """Problema 1: simulación de eventos discretos de la fábrica de laptops."""
    print("\n--- Problema 1: Fábrica de laptops (eventos discretos) ---")
    horas = leer_float("Horas a simular", HORAS_DEFECTO_P1, minimo=0.1, maximo=1000)
    semilla = leer_int("Semilla aleatoria", SEMILLA_DEFECTO, minimo=0)
    stock = leer_int("Stock inicial de procesadores", STOCK_INICIAL_DEFECTO, minimo=0, maximo=10000)

    print("\nTRAZA DE EVENTOS:")
    simulacion = SimulacionFabrica(horas=horas, semilla=semilla, stock_inicial=stock)
    metricas = simulacion.ejecutar()

    print("\nEnviando métricas a la IA para su análisis...")
    conclusion, fuente = analizador.analizar("p1", metricas)
    titulo = "PROBLEMA 1 - Simulación de eventos discretos (fábrica de laptops)"
    resumen = simulacion.resumen_metricas(metricas)
    analisis = simulacion.generar_analisis(metricas)
    mostrar_resultados(titulo, resumen, analisis, conclusion, fuente)
    escribir_informe("p1.txt", titulo, resumen, analisis, conclusion, fuente)
    print("Traza completa en: trazas/traza_p1.log")


def generar_informe_desde_metricas(analizador, problema, metricas, simulacion):
    """Reutiliza el flujo de IA e informe a partir de unas métricas ya calculadas."""
    print("\nEnviando métricas a la IA para su análisis...")
    conclusion, fuente = analizador.analizar(problema, metricas)
    titulos = {"p1": "PROBLEMA 1 - Simulación de eventos discretos (fábrica de laptops)",
               "p2": "PROBLEMA 2 - Simulación continua (clúster de servidores)"}
    titulo = titulos[problema]
    resumen = simulacion.resumen_metricas(metricas)
    analisis = simulacion.generar_analisis(metricas)
    mostrar_resultados(titulo, resumen, analisis, conclusion, fuente)
    escribir_informe(f"{problema}.txt", titulo, resumen, analisis, conclusion, fuente)


def ejecutar_animacion(analizador):
    """Pregunta bonus: animación de las simulaciones con pygame."""
    print("\n--- Animación de las simulaciones (pygame) ---")
    try:
        from visual.animacion import MotorAnimacion
    except ImportError:
        print("No se encontró pygame. Instálalo con:  pip install pygame")
        print("Si tu sistema bloquea la instalación, usa un entorno virtual:")
        print("  python3 -m venv --system-site-packages .venv && .venv/bin/pip install pygame")
        print("  .venv/bin/python main.py")
        return

    horas_p1 = leer_float("Horas a simular en el problema 1", HORAS_DEFECTO_P1, minimo=0.1, maximo=1000)
    horas_p2 = leer_float("Horas a simular en el problema 2", HORAS_DEFECTO_P2, minimo=0.1, maximo=1000)
    semilla = leer_int("Semilla aleatoria", SEMILLA_DEFECTO, minimo=0)
    stock = leer_int("Stock inicial de procesadores", STOCK_INICIAL_DEFECTO, minimo=0, maximo=10000)

    print("\nAbriendo la ventana de la animación...")
    print("  En la ventana: pulsa 1 o 2 para elegir el problema a visualizar.")
    print("  Controles: ESPACIO pausa la animación (la simulación sigue calculando),")
    print("             +/- velocidad, R reiniciar, M menú, ESC salir.")
    motor = MotorAnimacion(horas_p1=horas_p1, horas_p2=horas_p2, semilla=semilla, stock_inicial=stock)
    resultados = motor.ejecutar()

    if not resultados:
        print("\nNinguna simulación llegó a completarse: no se generó informe.")
        return
    # Las simulaciones completadas en la animación generan su informe igual que en consola
    for problema, metricas in resultados.items():
        if problema == "p1":
            plantilla = SimulacionFabrica(horas=metricas["horas_simuladas"], ruta_traza="trazas/traza_p1.log")
            plantilla.trazador.cerrar()
        else:
            plantilla = SimulacionCluster(horas=metricas["horas_simuladas"], ruta_traza="trazas/traza_p2.log")
        generar_informe_desde_metricas(analizador, problema, metricas, plantilla)


def ejecutar_problema_2(analizador):
    """Problema 2: simulación continua del clúster de servidores."""
    print("\n--- Problema 2: Clúster de servidores (simulación continua) ---")
    horas = leer_float("Horas a simular", HORAS_DEFECTO_P2, minimo=0.1, maximo=1000)
    dt = leer_float("Paso de integración en minutos", DT_DEFECTO_MIN, minimo=0.01, maximo=60)
    semilla = leer_int("Semilla aleatoria", SEMILLA_DEFECTO, minimo=0)

    print("\nTRAZA (resumen cada 30 min simulados; la traza completa va al archivo):")
    simulacion = SimulacionCluster(horas=horas, dt_min=dt, semilla=semilla)
    metricas = simulacion.ejecutar()

    print("\nEnviando métricas a la IA para su análisis...")
    conclusion, fuente = analizador.analizar("p2", metricas)
    titulo = "PROBLEMA 2 - Simulación continua (clúster de servidores)"
    resumen = simulacion.resumen_metricas(metricas)
    analisis = simulacion.generar_analisis(metricas)
    mostrar_resultados(titulo, resumen, analisis, conclusion, fuente)
    escribir_informe("p2.txt", titulo, resumen, analisis, conclusion, fuente)
    print("Traza completa en: trazas/traza_p2.log")


def menu():
    """Menú principal del programa."""
    config.cargar_env()
    api_key = config.obtener_api_key()
    modelo = config.obtener_modelo()
    analizador = AnalizadorIA(api_key, modelo)

    print(SEPARADOR)
    print("  PARCIAL III - SIMULACIÓN (Python POO)")
    print(SEPARADOR)
    if analizador.disponible:
        print(f"IA configurada: Gemini ({modelo})")
    else:
        print("IA NO configurada: crea un archivo .env con GEMINI_API_KEY (ver .env.example).")
        print("Se usará una conclusión local de respaldo.")

    while True:
        print("\nMENÚ DE OPCIONES")
        print("  1) Problema 1 - Simulación de eventos discretos (fábrica de laptops)")
        print("  2) Problema 2 - Simulación continua (clúster de servidores)")
        print("  3) Ejecutar ambos problemas")
        print("  4) Animación de las simulaciones con pygame (pregunta bonus)")
        print("  0) Salir")
        opcion = leer_opcion("Seleccione una opción: ", ["1", "2", "3", "4", "0"])
        if opcion == "1":
            ejecutar_problema_1(analizador)
        elif opcion == "2":
            ejecutar_problema_2(analizador)
        elif opcion == "3":
            ejecutar_problema_1(analizador)
            ejecutar_problema_2(analizador)
        elif opcion == "4":
            ejecutar_animacion(analizador)
        else:
            print("Hasta luego.")
            break


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\nEjecución interrumpida por el usuario.")
