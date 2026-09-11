"""
Problema 2 - Simulación continua.

Clúster de servidores cuyo comportamiento térmico se modela con una ecuación
diferencial de primer orden (balance de calor):

    dT/dt = k_calor * carga(t) - k_disipacion * (T - T_ambiente)

  - carga(t): tráfico entrante en Gbps, normal(3, 1) recortada a [1, 5].
  - k_calor: calor aportado por las CPUs por cada Gbps procesado (°C/min por Gbps).
  - k_disipacion: capacidad de la refrigeración líquida (1/min).

Los coeficientes se calibran para que el equilibrio térmico con el tráfico
medio (3 Gbps) sea exactamente 70 °C, la temperatura de diseño. La EDO se
integra con Runge-Kutta de 4º orden. El reloj se mide en MINUTOS.

Rendimiento: eficiencia 90 % con T <= 70 °C; por encima se activa el
estrangulamiento térmico y la eficiencia cae linealmente hasta 40 % a 85 °C.
"""
import os
import random
import statistics

# Conversión: 1 Gbps sostenido durante 1 hora = 3600 Gb = 450 GB = 0.45 TB
TB_POR_GBPS_HORA = 0.45


def formato_tiempo(minutos):
    """Convierte minutos simulados a texto HH:MM."""
    total = int(round(minutos))
    h, m = divmod(total, 60)
    return f"{h:02d}:{m:02d}"


class GeneradorTrafico:
    """Genera la tasa de tráfico entrante (Gbps) con distribución normal recortada."""

    def __init__(self, rng, media=3.0, desviacion=1.0, minimo=1.0, maximo=5.0, intervalo_min=5.0):
        self.rng = rng
        self.media = media
        self.desviacion = desviacion
        self.minimo = minimo
        self.maximo = maximo
        self.intervalo_min = intervalo_min   # cada cuántos minutos cambia la demanda
        self._t_proximo_cambio = 0.0
        self.valor_actual = media

    def obtener(self, t):
        """Devuelve el tráfico vigente en el instante t, remuestreando si toca."""
        if t >= self._t_proximo_cambio:
            muestra = self.rng.gauss(self.media, self.desviacion)
            # Recorte al rango físico permitido [1, 5] Gbps
            self.valor_actual = min(self.maximo, max(self.minimo, muestra))
            self._t_proximo_cambio = t + self.intervalo_min
        return self.valor_actual


class ServidorTermico:
    """Estado térmico del clúster gobernado por la EDO de balance de calor."""

    def __init__(self, t_inicial=70.0, t_ambiente=25.0, t_diseno=70.0, carga_media=3.0, k_disipacion=0.05):
        self.temperatura = t_inicial
        self.t_ambiente = t_ambiente
        self.t_diseno = t_diseno
        self.k_disipacion = k_disipacion
        # Calibración: en equilibrio dT/dt = 0  =>  k_calor * carga_media = k_dis * (t_diseno - t_amb)
        self.k_calor = k_disipacion * (t_diseno - t_ambiente) / carga_media

    def derivada(self, temperatura, carga):
        """Lado derecho de la EDO: calor generado menos calor disipado."""
        return self.k_calor * carga - self.k_disipacion * (temperatura - self.t_ambiente)

    def paso(self, dt, carga):
        """Avanza la temperatura un paso dt (minutos) con Runge-Kutta de 4º orden."""
        T = self.temperatura
        k1 = self.derivada(T, carga)
        k2 = self.derivada(T + 0.5 * dt * k1, carga)
        k3 = self.derivada(T + 0.5 * dt * k2, carga)
        k4 = self.derivada(T + dt * k3, carga)
        self.temperatura = T + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        return self.temperatura

    def temperatura_equilibrio(self, carga):
        """Temperatura a la que tiende el sistema si la carga se mantiene constante."""
        return self.t_ambiente + self.k_calor * carga / self.k_disipacion


class ClusterRendimiento:
    """Calcula la eficiencia de procesamiento en función de la temperatura."""

    def __init__(self, eficiencia_nominal=0.90, t_throttling=70.0, t_severa=85.0,
                 eficiencia_minima=0.40, t_critica=90.0):
        self.eficiencia_nominal = eficiencia_nominal
        self.t_throttling = t_throttling
        self.t_severa = t_severa
        self.eficiencia_minima = eficiencia_minima
        self.t_critica = t_critica

    def eficiencia(self, temperatura):
        """90 % hasta 70 °C; decae linealmente hasta 40 % en 85 °C; se mantiene en 40 % después."""
        if temperatura <= self.t_throttling:
            return self.eficiencia_nominal
        if temperatura >= self.t_severa:
            return self.eficiencia_minima
        fraccion = (temperatura - self.t_throttling) / (self.t_severa - self.t_throttling)
        return self.eficiencia_nominal - fraccion * (self.eficiencia_nominal - self.eficiencia_minima)

    def en_throttling(self, temperatura):
        return temperatura > self.t_throttling

    def en_zona_critica(self, temperatura):
        return temperatura >= self.t_critica


class SimulacionCluster:
    """Simulación continua del clúster: integra la EDO y acumula datos procesados."""

    def __init__(self, horas=24.0, dt_min=1.0, semilla=42, ruta_traza="trazas/traza_p2.log",
                 mostrar_consola=True, intervalo_resumen_min=30.0):
        self.horas = horas
        self.dt = dt_min
        self.semilla = semilla
        self.rng = random.Random(semilla)
        self.trafico = GeneradorTrafico(self.rng)
        self.servidor = ServidorTermico()
        self.cluster = ClusterRendimiento()
        self.mostrar_consola = mostrar_consola
        self.intervalo_resumen = intervalo_resumen_min

        os.makedirs(os.path.dirname(ruta_traza) or ".", exist_ok=True)
        self.ruta_traza = ruta_traza

        # Series temporales para el análisis
        self.tiempos = []
        self.serie_trafico = []
        self.serie_temperatura = []
        self.serie_eficiencia = []
        self.tb_procesados = 0.0
        self.tb_entrantes = 0.0
        self.episodios_throttling = 0
        self.pasos_throttling = 0
        self.pasos_criticos = 0

        # Estado instantáneo (lo consulta la animación en tiempo real)
        self.t = 0.0                 # reloj de simulación en minutos
        self.trafico_actual = 0.0    # Gbps entrantes en este instante
        self.temperatura_actual = self.servidor.temperatura
        self.eficiencia_actual = self.cluster.eficiencia_nominal
        self.estado_actual = "NORMAL"
        self._archivo = None
        self._pasos_restantes = 0
        self._proximo_resumen = 0.0
        self._en_throttling = False

    def iniciar(self):
        """Abre la traza y prepara el bucle de integración."""
        self._archivo = open(self.ruta_traza, "w", encoding="utf-8")
        self._archivo.write(f"# Simulación continua: {self.horas:g} h, dt={self.dt:g} min, semilla={self.semilla}\n")
        self._archivo.write("# t(min) | trafico(Gbps) | temperatura(C) | eficiencia | TB_acumulados | estado\n")
        self.t = 0.0
        self._pasos_restantes = int(round(self.horas * 60.0 / self.dt))
        self._proximo_resumen = 0.0
        self._en_throttling = False

    def paso(self):
        """Avanza un paso de integración dt.

        Devuelve True si se avanzó y False si ya se agotó el tiempo simulado.
        Permite animar la simulación paso a paso desde la interfaz gráfica.
        """
        if self._pasos_restantes <= 0:
            return False
        dt_horas = self.dt / 60.0
        carga = self.trafico.obtener(self.t)
        # Integramos la EDO manteniendo la carga constante durante el paso
        temperatura = self.servidor.paso(self.dt, carga)
        eficiencia = self.cluster.eficiencia(temperatura)
        # Datos procesados en este paso (TB)
        entrante = carga * dt_horas * TB_POR_GBPS_HORA
        self.tb_entrantes += entrante
        self.tb_procesados += entrante * eficiencia
        self.t += self.dt

        # Registro de series y estado térmico
        self.tiempos.append(self.t)
        self.serie_trafico.append(carga)
        self.serie_temperatura.append(temperatura)
        self.serie_eficiencia.append(eficiencia)
        estado = "NORMAL"
        if self.cluster.en_throttling(temperatura):
            self.pasos_throttling += 1
            estado = "THROTTLING"
            if not self._en_throttling:
                self.episodios_throttling += 1
                self._en_throttling = True
        else:
            self._en_throttling = False
        if self.cluster.en_zona_critica(temperatura):
            self.pasos_criticos += 1
            estado = "CRITICO"

        # Estado instantáneo para la animación
        self.trafico_actual = carga
        self.temperatura_actual = temperatura
        self.eficiencia_actual = eficiencia
        self.estado_actual = estado

        linea = (f"[t={formato_tiempo(self.t)}] trafico={carga:5.2f} Gbps | T={temperatura:6.2f} C | "
                 f"ef={eficiencia:4.2f} | TB={self.tb_procesados:8.3f} | {estado}")
        self._archivo.write(linea + "\n")
        # Por pantalla solo se muestra un resumen periódico para no saturar la consola
        if self.mostrar_consola and self.t >= self._proximo_resumen:
            print(linea)
            self._proximo_resumen += self.intervalo_resumen
        self._pasos_restantes -= 1
        return True

    def finalizar(self):
        """Cierra la traza y devuelve las métricas."""
        if self._archivo is not None:
            self._archivo.close()
            self._archivo = None
        return self.obtener_metricas()

    def ejecutar(self):
        """Ejecuta la simulación completa (bucle de integración en el tiempo)."""
        self.iniciar()
        while self.paso():
            pass
        return self.finalizar()

    # ----------------------------------------------------------------- métricas
    def obtener_metricas(self):
        temps = self.serie_temperatura
        n = len(temps) or 1
        pct_throttling = 100.0 * self.pasos_throttling / n
        pct_critico = 100.0 * self.pasos_criticos / n
        if self.pasos_criticos > 0:
            veredicto = "NO VIABLE: la temperatura alcanzó la zona crítica (>= 90 °C)"
        elif pct_throttling > 40:
            veredicto = "VIABLE CON RIESGO: throttling frecuente, la refrigeración va justa"
        else:
            veredicto = "VIABLE: temperatura controlada y throttling ocasional"
        return {
            "horas_simuladas": self.horas,
            "paso_min": self.dt,
            "semilla": self.semilla,
            "tb_entrantes": round(self.tb_entrantes, 3),
            "tb_procesados": round(self.tb_procesados, 3),
            "eficiencia_global_pct": round(100.0 * self.tb_procesados / self.tb_entrantes, 2) if self.tb_entrantes else 0.0,
            "trafico_promedio_gbps": round(statistics.mean(self.serie_trafico), 3) if self.serie_trafico else 0.0,
            "temperatura_promedio_c": round(statistics.mean(temps), 2) if temps else 0.0,
            "temperatura_minima_c": round(min(temps), 2) if temps else 0.0,
            "temperatura_maxima_c": round(max(temps), 2) if temps else 0.0,
            "temperatura_desviacion_c": round(statistics.pstdev(temps), 2) if len(temps) > 1 else 0.0,
            "pct_tiempo_throttling": round(pct_throttling, 1),
            "episodios_throttling": self.episodios_throttling,
            "pct_tiempo_critico": round(pct_critico, 1),
            "veredicto_viabilidad": veredicto,
        }

    def resumen_metricas(self, m=None):
        """Líneas legibles con las métricas principales (para pantalla y p2.txt)."""
        m = m or self.obtener_metricas()
        return [
            f"Horas simuladas: {m['horas_simuladas']:g} (paso {m['paso_min']:g} min, semilla {m['semilla']})",
            f"Datos entrantes / procesados: {m['tb_entrantes']} TB / {m['tb_procesados']} TB",
            f"Eficiencia global de la red: {m['eficiencia_global_pct']}% (nominal 90%)",
            f"Tráfico promedio: {m['trafico_promedio_gbps']} Gbps",
            f"Temperatura promedio: {m['temperatura_promedio_c']} °C (mín {m['temperatura_minima_c']}, máx {m['temperatura_maxima_c']}, desv. {m['temperatura_desviacion_c']})",
            f"Tiempo en throttling (>70 °C): {m['pct_tiempo_throttling']}% en {m['episodios_throttling']} episodios",
            f"Tiempo en zona crítica (>=90 °C): {m['pct_tiempo_critico']}%",
            f"Veredicto: {m['veredicto_viabilidad']}",
        ]

    def generar_analisis(self, m=None):
        """Interpretación breve y automática de las métricas (sin IA)."""
        m = m or self.obtener_metricas()
        perdida = round(m["tb_entrantes"] * 0.9 - m["tb_procesados"], 3)
        return [
            f"El clúster procesó {m['tb_procesados']} TB de {m['tb_entrantes']} TB entrantes; frente al 90% nominal "
            f"se perdieron {max(perdida, 0.0)} TB por estrangulamiento térmico.",
            f"La temperatura osciló entre {m['temperatura_minima_c']} y {m['temperatura_maxima_c']} °C "
            f"(desviación {m['temperatura_desviacion_c']} °C): cada cambio de tráfico desplaza el punto de equilibrio "
            f"(40 °C con 1 Gbps, 100 °C con 5 Gbps) y la inercia térmica no alcanza a compensarlo.",
            f"Al estar el punto de diseño (70 °C) justo en el tráfico medio, cualquier demanda superior a 3 Gbps "
            f"activa el throttling ({m['pct_tiempo_throttling']}% del tiempo).",
        ]
