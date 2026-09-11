"""
Problema 1 - Simulación de eventos discretos.

Fábrica de laptops con una única estación de ensamblaje y un inventario de
procesadores que se reabastece cuando cae por debajo de un umbral.

Modelo:
  - Llegadas de órdenes: proceso de Poisson con tasa 10 órdenes/hora
    (tiempo entre llegadas exponencial de media 6 minutos).
  - Tiempo de ensamblaje: exponencial con media 5 minutos.
  - Cada laptop consume 1 procesador al iniciar su ensamblaje.
  - Si el stock cae por debajo de 10 unidades se pide un lote de 50 que
    llega 15 minutos después.
  - Si no hay stock, la línea se detiene hasta que llegue el lote.

Todo el reloj de la simulación se mide en MINUTOS.
"""
import heapq
import os
import random
import statistics
from dataclasses import dataclass

# Tipos de evento del motor de simulación
LLEGADA = "LLEGADA"
FIN_ENSAMBLAJE = "FIN_ENSAMBLAJE"
LLEGADA_LOTE = "LLEGADA_LOTE"


def formato_tiempo(minutos):
    """Convierte minutos simulados a texto HH:MM:SS para las trazas."""
    total_seg = int(round(minutos * 60))
    h, resto = divmod(total_seg, 3600)
    m, s = divmod(resto, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class Orden:
    """Orden de producción de una laptop."""
    id: int
    t_llegada: float
    t_inicio: float | None = None
    t_fin: float | None = None
    retrasada_por_stock: bool = False  # True si esperó porque no había procesadores

    @property
    def espera(self):
        """Minutos que la orden esperó en cola antes de entrar a la estación."""
        return self.t_inicio - self.t_llegada

    @property
    def tiempo_sistema(self):
        """Minutos desde que llegó hasta que salió terminada."""
        return self.t_fin - self.t_llegada


class Inventario:
    """Inventario de procesadores con política de reabastecimiento por umbral."""

    def __init__(self, stock_inicial=50, umbral=10, tam_lote=50, tiempo_reabastecimiento=15.0):
        self.stock = stock_inicial
        self.umbral = umbral
        self.tam_lote = tam_lote
        self.tiempo_reabastecimiento = tiempo_reabastecimiento
        self.pedido_pendiente = False
        # Métricas de reabastecimiento
        self.reabastecimientos = 0
        self.pedidos_a_tiempo = 0           # lotes que llegaron antes de agotarse el stock
        self.agotado_durante_pedido = False  # se agotó el stock mientras esperábamos el lote

    def hay_stock(self):
        return self.stock > 0

    def consumir(self):
        """Consume un procesador. Debe comprobarse hay_stock() antes."""
        self.stock -= 1

    def necesita_pedido(self):
        """True si el stock está bajo el umbral y no hay un pedido en camino."""
        return self.stock < self.umbral and not self.pedido_pendiente

    def registrar_pedido(self):
        self.pedido_pendiente = True
        self.agotado_durante_pedido = False

    def marcar_agotado(self):
        """Se llama cuando la línea se detiene por stock cero."""
        if self.pedido_pendiente:
            self.agotado_durante_pedido = True

    def recibir_lote(self):
        """Recibe el lote del proveedor y actualiza métricas de eficiencia."""
        self.stock += self.tam_lote
        self.pedido_pendiente = False
        self.reabastecimientos += 1
        if not self.agotado_durante_pedido:
            self.pedidos_a_tiempo += 1

    @property
    def eficiencia_reabastecimiento(self):
        """Porcentaje de lotes que llegaron antes de que la línea se quedara sin stock."""
        if self.reabastecimientos == 0:
            return 100.0
        return 100.0 * self.pedidos_a_tiempo / self.reabastecimientos


class EstacionEnsamblaje:
    """Única estación de ensamblaje de la fábrica."""

    def __init__(self, media_servicio=5.0):
        self.media_servicio = media_servicio
        self.orden_actual = None
        self.tiempo_ocupado = 0.0
        self.laptops_completadas = 0
        self.t_fin_previsto = None  # instante en que terminará la orden actual (para la animación)

    @property
    def ocupada(self):
        return self.orden_actual is not None

    def iniciar(self, orden, t, duracion):
        orden.t_inicio = t
        self.orden_actual = orden
        self.t_fin_previsto = t + duracion

    def terminar(self, t):
        orden = self.orden_actual
        orden.t_fin = t
        self.tiempo_ocupado += t - orden.t_inicio
        self.laptops_completadas += 1
        self.orden_actual = None
        self.t_fin_previsto = None
        return orden


class Trazador:
    """Escribe las trazas de la simulación en consola y en un archivo de log."""

    def __init__(self, ruta_archivo, mostrar_consola=True):
        os.makedirs(os.path.dirname(ruta_archivo) or ".", exist_ok=True)
        self.archivo = open(ruta_archivo, "w", encoding="utf-8")
        self.mostrar_consola = mostrar_consola

    def registrar(self, t, evento, detalle, estado=""):
        linea = f"[t={formato_tiempo(t)}] {evento:<15} | {detalle:<45} | {estado}"
        self.archivo.write(linea + "\n")
        if self.mostrar_consola:
            print(linea)

    def cerrar(self):
        self.archivo.close()


class SimulacionFabrica:
    """Motor de simulación de eventos discretos de la fábrica de laptops."""

    def __init__(self, horas=8.0, semilla=42, stock_inicial=50, tasa_llegadas_hora=10.0,
                 media_servicio=5.0, umbral=10, tam_lote=50, tiempo_reabastecimiento=15.0,
                 ruta_traza="trazas/traza_p1.log", mostrar_consola=True):
        self.horas = horas
        self.semilla = semilla
        self.t_fin_sim = horas * 60.0
        self.rng = random.Random(semilla)
        self.tasa_llegadas_min = tasa_llegadas_hora / 60.0  # órdenes por minuto

        self.inventario = Inventario(stock_inicial, umbral, tam_lote, tiempo_reabastecimiento)
        self.estacion = EstacionEnsamblaje(media_servicio)
        self.trazador = Trazador(ruta_traza, mostrar_consola)

        self.reloj = 0.0
        self._eventos = []       # heap de (tiempo, secuencia, tipo, dato)
        self._secuencia = 0
        self.cola = []           # órdenes esperando por la estación
        self.ordenes = []        # todas las órdenes creadas
        self.completadas = []    # órdenes terminadas

        # Métricas de paradas de línea por falta de stock
        self.paradas_por_stock = 0
        self.en_parada = False
        self.t_inicio_parada = 0.0
        self.tiempo_total_parado = 0.0
        self.cola_maxima = 0

        # Tiempo para despachar un lote de producción (tam_lote laptops)
        self.t_inicio_lote_produccion = 0.0
        self.duraciones_lote = []

    # ------------------------------------------------------------------ eventos
    def _programar(self, t, tipo, dato=None):
        """Inserta un evento en la agenda ordenada por tiempo."""
        self._secuencia += 1
        heapq.heappush(self._eventos, (t, self._secuencia, tipo, dato))

    def _estado(self):
        return f"stock={self.inventario.stock:<3} cola={len(self.cola):<3} estacion={'OCUPADA' if self.estacion.ocupada else 'LIBRE'}"

    def _programar_siguiente_llegada(self):
        intervalo = self.rng.expovariate(self.tasa_llegadas_min)
        self._programar(self.reloj + intervalo, LLEGADA)

    def _evento_llegada(self):
        orden = Orden(id=len(self.ordenes) + 1, t_llegada=self.reloj)
        self.ordenes.append(orden)
        self.cola.append(orden)
        self.cola_maxima = max(self.cola_maxima, len(self.cola))
        self.trazador.registrar(self.reloj, LLEGADA, f"Orden #{orden.id} llega a recepción", self._estado())
        self._programar_siguiente_llegada()
        self._intentar_iniciar()

    def _evento_fin_ensamblaje(self):
        orden = self.estacion.terminar(self.reloj)
        self.completadas.append(orden)
        self.trazador.registrar(self.reloj, FIN_ENSAMBLAJE,
                                f"Orden #{orden.id} terminada (espera {orden.espera:.1f} min)", self._estado())
        # Cada tam_lote laptops completadas cerramos un "lote de producción"
        if len(self.completadas) % self.inventario.tam_lote == 0:
            self.duraciones_lote.append(self.reloj - self.t_inicio_lote_produccion)
            self.t_inicio_lote_produccion = self.reloj
            self.trazador.registrar(self.reloj, "LOTE_DESPACHADO",
                                    f"Lote de {self.inventario.tam_lote} laptops en {self.duraciones_lote[-1]:.1f} min",
                                    self._estado())
        self._intentar_iniciar()

    def _evento_llegada_lote(self):
        self.inventario.recibir_lote()
        self.trazador.registrar(self.reloj, LLEGADA_LOTE,
                                f"Proveedor entrega {self.inventario.tam_lote} procesadores", self._estado())
        if self.en_parada:
            # La línea vuelve a arrancar tras la parada por falta de stock
            self.en_parada = False
            self.tiempo_total_parado += self.reloj - self.t_inicio_parada
            self.trazador.registrar(self.reloj, "LINEA_REANUDA",
                                    f"Parada duró {self.reloj - self.t_inicio_parada:.1f} min", self._estado())
        self._intentar_iniciar()

    def _intentar_iniciar(self):
        """Si la estación está libre y hay órdenes en cola, intenta arrancar el ensamblaje."""
        if self.estacion.ocupada or not self.cola:
            return
        if not self.inventario.hay_stock():
            # Línea detenida: hay trabajo pero no hay procesadores
            for orden in self.cola:
                orden.retrasada_por_stock = True
            if not self.en_parada:
                self.en_parada = True
                self.t_inicio_parada = self.reloj
                self.paradas_por_stock += 1
                self.inventario.marcar_agotado()
                self.trazador.registrar(self.reloj, "LINEA_DETENIDA",
                                        "Sin procesadores: se detiene la línea", self._estado())
                self._verificar_reabastecimiento()
            return
        orden = self.cola.pop(0)
        self.inventario.consumir()
        duracion = self.rng.expovariate(1.0 / self.estacion.media_servicio)
        self.estacion.iniciar(orden, self.reloj, duracion)
        self._programar(self.reloj + duracion, FIN_ENSAMBLAJE)
        self.trazador.registrar(self.reloj, "INICIO_ENSAMBLE",
                                f"Orden #{orden.id} entra a la estación ({duracion:.1f} min)", self._estado())
        self._verificar_reabastecimiento()

    def _verificar_reabastecimiento(self):
        """Política de reabastecimiento por umbral: pide un lote si el stock es bajo y no hay pedido en camino."""
        if self.inventario.necesita_pedido():
            self.inventario.registrar_pedido()
            self._programar(self.reloj + self.inventario.tiempo_reabastecimiento, LLEGADA_LOTE)
            self.trazador.registrar(self.reloj, "PEDIDO_LOTE",
                                    f"Stock bajo umbral ({self.inventario.umbral}): pedido de {self.inventario.tam_lote}",
                                    self._estado())

    # -------------------------------------------------------------------- ciclo
    def iniciar(self):
        """Prepara la simulación: traza inicial, pedido inicial y primera llegada."""
        self.trazador.registrar(0.0, "INICIO",
                                f"Simulación de {self.horas:g} h, semilla {self.semilla}", self._estado())
        self._verificar_reabastecimiento()
        self._programar_siguiente_llegada()

    @property
    def tiempo_proximo_evento(self):
        """Instante del siguiente evento pendiente, o None si no queda ninguno."""
        return self._eventos[0][0] if self._eventos else None

    def paso(self):
        """Procesa el siguiente evento de la agenda.

        Devuelve True si se procesó un evento y False si la simulación terminó.
        Permite avanzar la simulación evento a evento desde la animación.
        """
        if not self._eventos:
            return False
        t, _, tipo, _ = heapq.heappop(self._eventos)
        if t > self.t_fin_sim:
            return False
        self.reloj = t
        if tipo == LLEGADA:
            self._evento_llegada()
        elif tipo == FIN_ENSAMBLAJE:
            self._evento_fin_ensamblaje()
        elif tipo == LLEGADA_LOTE:
            self._evento_llegada_lote()
        return True

    def finalizar(self):
        """Cierra los contadores abiertos y la traza; devuelve las métricas."""
        self.reloj = self.t_fin_sim
        if self.estacion.ocupada:
            self.estacion.tiempo_ocupado += self.reloj - self.estacion.orden_actual.t_inicio
        if self.en_parada:
            self.tiempo_total_parado += self.reloj - self.t_inicio_parada
        self.trazador.registrar(self.reloj, "FIN", "Fin del período simulado", self._estado())
        self.trazador.cerrar()
        return self.obtener_metricas()

    def ejecutar(self):
        """Ejecuta la simulación completa hasta agotar el tiempo indicado por el usuario."""
        self.iniciar()
        while self.paso():
            pass
        return self.finalizar()

    # ----------------------------------------------------------------- métricas
    def obtener_metricas(self):
        """Recopila las métricas clave de la simulación en un diccionario."""
        esperas = [o.espera for o in self.completadas]
        sistema = [o.tiempo_sistema for o in self.completadas]
        retrasadas = sum(1 for o in self.ordenes if o.retrasada_por_stock)
        return {
            "horas_simuladas": self.horas,
            "semilla": self.semilla,
            "ordenes_llegadas": len(self.ordenes),
            "ordenes_completadas": len(self.completadas),
            "ordenes_pendientes_al_final": len(self.cola) + (1 if self.estacion.ocupada else 0),
            "espera_promedio_min": round(statistics.mean(esperas), 2) if esperas else 0.0,
            "espera_maxima_min": round(max(esperas), 2) if esperas else 0.0,
            "tiempo_sistema_promedio_min": round(statistics.mean(sistema), 2) if sistema else 0.0,
            "tiempo_despacho_lote_promedio_min": round(statistics.mean(self.duraciones_lote), 2) if self.duraciones_lote else None,
            "lotes_produccion_completos": len(self.duraciones_lote),
            "paradas_por_falta_stock": self.paradas_por_stock,
            "tiempo_total_linea_detenida_min": round(self.tiempo_total_parado, 2),
            "ordenes_retrasadas_por_inventario": retrasadas,
            "reabastecimientos": self.inventario.reabastecimientos,
            "eficiencia_reabastecimiento_pct": round(self.inventario.eficiencia_reabastecimiento, 1),
            "stock_final": self.inventario.stock,
            "utilizacion_estacion_pct": round(100.0 * self.estacion.tiempo_ocupado / self.t_fin_sim, 1),
            "cola_maxima": self.cola_maxima,
        }

    def resumen_metricas(self, m=None):
        """Lista de líneas legibles con las métricas principales (para pantalla y p1.txt)."""
        m = m or self.obtener_metricas()
        lote = f"{m['tiempo_despacho_lote_promedio_min']} min" if m["tiempo_despacho_lote_promedio_min"] is not None else "no se completó ningún lote"
        return [
            f"Horas simuladas: {m['horas_simuladas']:g} (semilla {m['semilla']})",
            f"Órdenes llegadas / completadas: {m['ordenes_llegadas']} / {m['ordenes_completadas']}",
            f"Espera promedio en cola: {m['espera_promedio_min']} min (máxima {m['espera_maxima_min']} min)",
            f"Tiempo promedio en el sistema: {m['tiempo_sistema_promedio_min']} min",
            f"Tiempo para despachar un lote de 50 laptops: {lote}",
            f"Paradas de línea por falta de stock: {m['paradas_por_falta_stock']} ({m['tiempo_total_linea_detenida_min']} min detenida)",
            f"Órdenes retrasadas por inventario: {m['ordenes_retrasadas_por_inventario']}",
            f"Reabastecimientos: {m['reabastecimientos']} (eficiencia {m['eficiencia_reabastecimiento_pct']}%)",
            f"Utilización de la estación: {m['utilizacion_estacion_pct']}% | Cola máxima: {m['cola_maxima']}",
        ]

    def generar_analisis(self, m=None):
        """Interpretación breve y automática de las métricas (sin IA)."""
        m = m or self.obtener_metricas()
        lineas = []
        util = m["utilizacion_estacion_pct"]
        # Con 10 órdenes/h y 5 min de servicio la carga teórica (rho) es 0.83
        lineas.append(f"La estación trabajó al {util}% del tiempo; la carga teórica es 83% (10 órdenes/h x 5 min), "
                      f"por lo que el sistema opera cerca de su límite y las colas son sensibles a picos de llegadas.")
        lineas.append(f"La espera promedio fue {m['espera_promedio_min']} min con cola máxima de {m['cola_maxima']} órdenes; "
                      f"la espera se debe principalmente a la capacidad de la única estación.")
        if m["paradas_por_falta_stock"] == 0:
            lineas.append("La política de inventario (umbral 10, lote 50, entrega 15 min) evitó todas las paradas: "
                          "el umbral cubre la demanda esperada durante la entrega (~2.5 órdenes en 15 min).")
        else:
            lineas.append(f"Hubo {m['paradas_por_falta_stock']} parada(s) por falta de stock que retrasaron "
                          f"{m['ordenes_retrasadas_por_inventario']} órdenes; el umbral de 10 unidades resultó insuficiente.")
        return lineas
