"""
Paquete de la interfaz gráfica (pregunta bonus).

Se silencia el mensaje de bienvenida de pygame y el aviso de compilación sin
AVX2 antes de importar la librería, para que la salida por consola del
programa quede limpia. Ninguno de los dos mensajes indica un error.
"""
import os
import warnings

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", message=".*avx2.*", category=RuntimeWarning)
