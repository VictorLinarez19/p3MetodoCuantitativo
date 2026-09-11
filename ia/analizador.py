"""
Consumo de la API de Inteligencia Artificial (Google Gemini) para analizar las
métricas de las simulaciones y generar una conclusión y recomendación.

Si la API no está disponible (sin clave, sin red, error HTTP o tiempo agotado)
se genera una conclusión local de respaldo basada en reglas, de modo que el
programa siempre entrega un resultado.
"""
import json
import time

import requests

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

# Modelos alternativos que se prueban si el configurado ya no existe (HTTP 404).
# Google retira modelos antiguos periódicamente, por lo que conviene tener respaldo.
MODELOS_ALTERNATIVOS = ["gemini-flash-latest", "gemini-3.6-flash", "gemini-2.5-flash"]

# Códigos HTTP transitorios (servidor saturado o límite de peticiones): conviene reintentar
CODIGOS_REINTENTABLES = (429, 500, 502, 503, 504)
INTENTOS_MAXIMOS = 3
ESPERA_ENTRE_INTENTOS = 4  # segundos, se duplica en cada reintento


class AnalisisIAError(Exception):
    """Error al consumir la API de IA."""


class ClienteGemini:
    """Cliente mínimo de la API REST de Gemini usando requests."""

    def __init__(self, api_key, modelo="gemini-flash-latest", timeout=30):
        self.api_key = api_key
        self.modelo = modelo
        self.timeout = timeout

    def generar(self, prompt):
        """Envía el prompt a Gemini y devuelve el texto de la respuesta.

        Si el modelo configurado ya no está disponible (HTTP 404), reintenta
        automáticamente con los modelos alternativos conocidos.
        """
        candidatos = [self.modelo] + [m for m in MODELOS_ALTERNATIVOS if m != self.modelo]
        ultimo_error = None
        for modelo in candidatos:
            try:
                texto = self._solicitar(modelo, prompt)
            except AnalisisIAError as error:
                ultimo_error = error
                # Solo tiene sentido reintentar con otro modelo si el problema es el modelo
                if "HTTP 404" not in str(error):
                    raise
                continue
            if modelo != self.modelo:
                print(f"[AVISO] El modelo '{self.modelo}' no está disponible; se usó '{modelo}'.")
                self.modelo = modelo
            return texto
        raise ultimo_error

    def _solicitar(self, modelo, prompt):
        """Petición POST a la API de Gemini con reintentos ante errores transitorios."""
        url = URL_GEMINI.format(modelo=modelo)
        cuerpo = {"contents": [{"parts": [{"text": prompt}]}]}
        espera = ESPERA_ENTRE_INTENTOS
        for intento in range(1, INTENTOS_MAXIMOS + 1):
            try:
                respuesta = requests.post(url, params={"key": self.api_key}, json=cuerpo, timeout=self.timeout)
            except requests.RequestException as error:
                raise AnalisisIAError(f"No se pudo conectar con Gemini: {error}") from error
            if respuesta.status_code == 200:
                break
            # El servidor puede estar saturado: se espera y se reintenta
            if respuesta.status_code in CODIGOS_REINTENTABLES and intento < INTENTOS_MAXIMOS:
                print(f"[AVISO] Gemini devolvió HTTP {respuesta.status_code}; "
                      f"reintentando en {espera} s ({intento}/{INTENTOS_MAXIMOS - 1})...")
                time.sleep(espera)
                espera *= 2
                continue
            raise AnalisisIAError(f"Gemini respondió HTTP {respuesta.status_code}: {respuesta.text[:200]}")
        try:
            datos = respuesta.json()
            partes = datos["candidates"][0]["content"]["parts"]
            texto = "".join(p.get("text", "") for p in partes).strip()
        except (ValueError, KeyError, IndexError) as error:
            raise AnalisisIAError(f"Respuesta de Gemini con formato inesperado: {error}") from error
        if not texto:
            raise AnalisisIAError("Gemini devolvió una respuesta vacía")
        return texto


class ConclusionRespaldo:
    """Conclusión basada en reglas cuando la IA no está disponible."""

    def generar(self, nombre_problema, metricas):
        if nombre_problema == "p1":
            return self._fabrica(metricas)
        return self._cluster(metricas)

    @staticmethod
    def _fabrica(m):
        lineas = ["CONCLUSIÓN:"]
        if m["paradas_por_falta_stock"] == 0:
            lineas.append("- La gestión de inventario fue efectiva: no hubo paradas de línea por falta de procesadores.")
        else:
            lineas.append(f"- Se registraron {m['paradas_por_falta_stock']} paradas por falta de stock; "
                          "el umbral de reabastecimiento es insuficiente.")
        lineas.append(f"- La espera promedio de {m['espera_promedio_min']} min con utilización del "
                      f"{m['utilizacion_estacion_pct']}% indica que la estación única es el cuello de botella.")
        lineas.append("RECOMENDACIÓN:")
        if m["utilizacion_estacion_pct"] > 75:
            lineas.append("- Evaluar una segunda estación o reducir el tiempo medio de ensamblaje para bajar las colas.")
        else:
            lineas.append("- La capacidad actual es adecuada; mantener la configuración y vigilar picos de demanda.")
        if m["paradas_por_falta_stock"] > 0:
            lineas.append("- Subir el umbral de reabastecimiento (p. ej. a 15 unidades) o negociar entregas más rápidas.")
        else:
            lineas.append("- Mantener la política de inventario (umbral 10, lote 50, entrega en 15 min).")
        return "\n".join(lineas)

    @staticmethod
    def _cluster(m):
        lineas = ["CONCLUSIÓN:"]
        lineas.append(f"- Se procesaron {m['tb_procesados']} TB con eficiencia global del {m['eficiencia_global_pct']}%; "
                      f"el throttling actuó el {m['pct_tiempo_throttling']}% del tiempo.")
        lineas.append(f"- Temperatura media {m['temperatura_promedio_c']} °C con máxima de {m['temperatura_maxima_c']} °C. "
                      f"{m['veredicto_viabilidad']}.")
        lineas.append("RECOMENDACIÓN:")
        if m["pct_tiempo_critico"] > 0:
            lineas.append("- Aumentar la capacidad de refrigeración de inmediato o limitar el tráfico admitido por encima de 4 Gbps.")
        elif m["pct_tiempo_throttling"] > 25:
            lineas.append("- Mejorar la disipación (bajar el punto de equilibrio a ~60 °C) para absorber picos de tráfico sin throttling.")
        else:
            lineas.append("- La operación continua es viable; mantener monitoreo de temperatura y alertas por encima de 80 °C.")
        return "\n".join(lineas)


class AnalizadorIA:
    """Fachada: intenta usar Gemini y, si falla, recurre a la conclusión de respaldo."""

    NOMBRES = {
        "p1": "Simulación de eventos discretos: fábrica de laptops con una estación de ensamblaje "
              "(llegadas Poisson 10/h, servicio exponencial media 5 min, inventario de procesadores con "
              "umbral 10, lote 50 y entrega en 15 min)",
        "p2": "Simulación continua: clúster de servidores con balance térmico (EDO de primer orden), "
              "tráfico normal(3,1) Gbps recortado a [1,5], diseño a 70 °C, eficiencia 90 % y throttling por encima de 70 °C",
    }

    def __init__(self, api_key=None, modelo="gemini-flash-latest"):
        self.cliente = ClienteGemini(api_key, modelo) if api_key else None
        self.respaldo = ConclusionRespaldo()
        self.modelo = modelo

    @property
    def disponible(self):
        return self.cliente is not None

    def construir_prompt(self, nombre_problema, metricas):
        """Prompt en español con las métricas en JSON para que la IA las analice."""
        return (
            "Eres un analista experto en simulación de sistemas. A continuación tienes las métricas "
            f"obtenidas de una {self.NOMBRES[nombre_problema]}.\n\n"
            f"Métricas (JSON):\n{json.dumps(metricas, ensure_ascii=False, indent=2)}\n\n"
            "Redacta en español, de forma corta y concisa (máximo 8 líneas, sin formato markdown), "
            "una CONCLUSIÓN sobre el desempeño del sistema y una RECOMENDACIÓN concreta para mejorarlo. "
            "Cita los valores numéricos más relevantes."
        )

    def analizar(self, nombre_problema, metricas):
        """Devuelve (texto_conclusion, fuente) donde fuente es 'Gemini (<modelo>)' o 'respaldo local'."""
        if self.cliente is not None:
            try:
                texto = self.cliente.generar(self.construir_prompt(nombre_problema, metricas))
                # El cliente puede haber cambiado de modelo si el configurado no existía
                self.modelo = self.cliente.modelo
                return texto, f"Gemini ({self.modelo})"
            except AnalisisIAError as error:
                print(f"\n[AVISO] {error}\n[AVISO] Usando conclusión local de respaldo.")
        else:
            print("\n[AVISO] No hay GEMINI_API_KEY configurada. Usando conclusión local de respaldo.")
        return self.respaldo.generar(nombre_problema, metricas), "respaldo local (sin IA)"
