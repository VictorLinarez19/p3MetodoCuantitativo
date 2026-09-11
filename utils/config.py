"""
Carga de configuración desde un archivo .env (sin dependencias externas).

Variables reconocidas:
  GEMINI_API_KEY  clave de Google AI Studio para consumir la API de Gemini
  GEMINI_MODEL    nombre del modelo (por defecto gemini-2.5-flash)
"""
import os

# Alias estable: apunta siempre al modelo Flash vigente en la API
MODELO_POR_DEFECTO = "gemini-flash-latest"


def cargar_env(ruta=".env"):
    """Lee un archivo .env con líneas CLAVE=VALOR y las carga en os.environ.

    No sobreescribe variables que ya existan en el entorno del sistema.
    Ignora líneas vacías y comentarios que empiecen con '#'.
    """
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if clave and clave not in os.environ:
                os.environ[clave] = valor


def obtener_api_key():
    """Devuelve la clave de Gemini o None si no está configurada."""
    clave = os.environ.get("GEMINI_API_KEY", "").strip()
    return clave or None


def obtener_modelo():
    """Devuelve el nombre del modelo de Gemini a utilizar."""
    return os.environ.get("GEMINI_MODEL", "").strip() or MODELO_POR_DEFECTO
