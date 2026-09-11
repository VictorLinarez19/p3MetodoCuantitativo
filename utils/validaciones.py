"""
Funciones de validación de datos introducidos por el usuario.

Todas las funciones repiten la pregunta hasta obtener un valor válido y
aceptan un valor por defecto cuando el usuario solo presiona Enter.
"""


def leer_float(mensaje, defecto, minimo=None, maximo=None):
    """Lee un número real dentro de un rango. Enter devuelve el valor por defecto."""
    while True:
        try:
            entrada = input(f"{mensaje} [por defecto: {defecto}]: ").strip()
        except EOFError:
            # Sin entrada estándar (por ejemplo, ejecución automatizada): usar el defecto
            return defecto
        if entrada == "":
            return defecto
        # Se acepta coma decimal por comodidad del usuario
        entrada = entrada.replace(",", ".")
        try:
            valor = float(entrada)
        except ValueError:
            print("  Entrada inválida: debe ser un número.")
            continue
        if minimo is not None and valor < minimo:
            print(f"  Entrada inválida: debe ser mayor o igual a {minimo}.")
            continue
        if maximo is not None and valor > maximo:
            print(f"  Entrada inválida: debe ser menor o igual a {maximo}.")
            continue
        return valor


def leer_int(mensaje, defecto, minimo=None, maximo=None):
    """Lee un número entero dentro de un rango. Enter devuelve el valor por defecto."""
    while True:
        try:
            entrada = input(f"{mensaje} [por defecto: {defecto}]: ").strip()
        except EOFError:
            return defecto
        if entrada == "":
            return defecto
        try:
            valor = int(entrada)
        except ValueError:
            print("  Entrada inválida: debe ser un número entero.")
            continue
        if minimo is not None and valor < minimo:
            print(f"  Entrada inválida: debe ser mayor o igual a {minimo}.")
            continue
        if maximo is not None and valor > maximo:
            print(f"  Entrada inválida: debe ser menor o igual a {maximo}.")
            continue
        return valor


def leer_opcion(mensaje, opciones_validas):
    """Lee una opción de menú; solo acepta los valores indicados en opciones_validas."""
    opciones = [str(o) for o in opciones_validas]
    while True:
        try:
            entrada = input(mensaje).strip()
        except EOFError:
            # Sin entrada: se interpreta como salir del menú
            return opciones[-1]
        if entrada in opciones:
            return entrada
        print(f"  Opción inválida. Opciones válidas: {', '.join(opciones)}")
