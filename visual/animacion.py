"""
Pregunta bonus: animación de las simulaciones con pygame.

El cálculo lógico de la simulación corre en un hilo aparte y la ventana
únicamente dibuja el estado de los objetos. Gracias a ello, la tecla ESPACIO
pausa la ANIMACIÓN sin detener el cálculo, tal como pide el enunciado.

Controles:
  ESPACIO / P   pausar o reanudar la animación (la simulación sigue calculando)
  + / -         aumentar o reducir la velocidad de la animación
  R             reiniciar la simulación
  M             volver al menú de selección de problema
  ESC / Q       salir
"""
import threading
import time

import pygame

from simulacion.continua import SimulacionCluster
from simulacion.eventos_discretos import SimulacionFabrica
from visual.paleta import Paleta
from visual.vistas import VistaCluster, VistaFabrica
from visual.widgets import Lienzo

ANCHO, ALTO = 1120, 660
FPS = 60

# Velocidad de la animación en minutos simulados por segundo real
VELOCIDADES = [5, 10, 20, 30, 60, 120, 300, 600]


class HiloSimulacion(threading.Thread):
    """Ejecuta la simulación en segundo plano y publica instantáneas de su estado.

    El hilo NO se detiene cuando la animación está en pausa: así se cumple el
    requisito de pausar la animación sin detener el cálculo lógico.
    """

    def __init__(self, simulacion, vista, velocidad):
        super().__init__(daemon=True)
        self.simulacion = simulacion
        self.vista = vista
        self.velocidad = velocidad
        self.detener = threading.Event()
        self.terminada = False
        self.pasos_logicos = 0
        self._lock = threading.Lock()
        self._instantanea = vista.instantanea(simulacion)

    def obtener_instantanea(self):
        """Devuelve la última instantánea publicada (segura entre hilos)."""
        with self._lock:
            return dict(self._instantanea), self.pasos_logicos, self.terminada

    def _publicar(self):
        with self._lock:
            self._instantanea = self.vista.instantanea(self.simulacion)

    def _avanzar(self, minutos):
        """Avanza la simulación los minutos simulados indicados."""
        raise NotImplementedError

    def run(self):
        ultimo = time.perf_counter()
        while not self.detener.is_set() and not self.terminada:
            ahora = time.perf_counter()
            transcurrido = ahora - ultimo
            ultimo = ahora
            # Minutos simulados que corresponden al tiempo real transcurrido
            self._avanzar(transcurrido * self.velocidad)
            self._publicar()
            time.sleep(1.0 / FPS)
        self._publicar()


class HiloFabrica(HiloSimulacion):
    """Avanza la simulación de eventos discretos evento a evento."""

    def __init__(self, simulacion, vista, velocidad):
        super().__init__(simulacion, vista, velocidad)
        simulacion.iniciar()
        self.reloj_visual = 0.0

    def _avanzar(self, minutos):
        self.reloj_visual = min(self.reloj_visual + minutos, self.simulacion.t_fin_sim)
        # Se procesan todos los eventos cuyo instante ya alcanzó el reloj visual
        while True:
            proximo = self.simulacion.tiempo_proximo_evento
            if proximo is None or proximo > self.reloj_visual:
                break
            if not self.simulacion.paso():
                self.terminada = True
                return
            self.pasos_logicos += 1
        if self.reloj_visual >= self.simulacion.t_fin_sim:
            self.terminada = True
        else:
            # Entre eventos el reloj avanza igual para que el progreso se vea fluido
            self.simulacion.reloj = self.reloj_visual


class HiloCluster(HiloSimulacion):
    """Avanza la simulación continua paso a paso de integración."""

    def __init__(self, simulacion, vista, velocidad):
        super().__init__(simulacion, vista, velocidad)
        simulacion.iniciar()
        self._credito = 0.0

    def _avanzar(self, minutos):
        self._credito += minutos
        while self._credito >= self.simulacion.dt:
            if not self.simulacion.paso():
                self.terminada = True
                return
            self._credito -= self.simulacion.dt
            self.pasos_logicos += 1


class MotorAnimacion:
    """Ventana de pygame: menú de selección, bucle de dibujo y controles."""

    def __init__(self, horas_p1=8.0, horas_p2=24.0, semilla=42, stock_inicial=50, dt_min=1.0):
        self.horas_p1 = horas_p1
        self.horas_p2 = horas_p2
        self.semilla = semilla
        self.stock_inicial = stock_inicial
        self.dt_min = dt_min

        pygame.init()
        pygame.display.set_caption("Parcial III · Simulación · Animación")
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self.reloj = pygame.time.Clock()
        self.fuentes = self._cargar_fuentes()
        self.lienzo = Lienzo(self.pantalla, self.fuentes)

        self.problema = None       # "p1" o "p2"
        self.vista = None
        self.hilo = None
        self.simulacion = None
        self.indice_velocidad = 3
        self.pausada = False
        self.ultimo_estado = None
        self.resultados = {}       # métricas de las simulaciones completadas

    @staticmethod
    def _cargar_fuentes():
        """Carga las fuentes del sistema con alternativas si no están disponibles."""
        familias = "dejavusans,liberationsans,freesans,arial"
        return {
            "titulo": pygame.font.SysFont(familias, 20, bold=True),
            "grande": pygame.font.SysFont(familias, 24, bold=True),
            "normal": pygame.font.SysFont(familias, 15),
            "pequena": pygame.font.SysFont(familias, 12),
        }

    # ------------------------------------------------------------------ control
    def _crear_simulacion(self, problema):
        """Crea la simulación y su hilo según el problema elegido."""
        self._cerrar_hilo()
        velocidad = VELOCIDADES[self.indice_velocidad]
        if problema == "p1":
            self.simulacion = SimulacionFabrica(horas=self.horas_p1, semilla=self.semilla,
                                                stock_inicial=self.stock_inicial,
                                                mostrar_consola=False)
            self.vista = VistaFabrica(ANCHO, ALTO)
            self.hilo = HiloFabrica(self.simulacion, self.vista, velocidad)
        else:
            self.simulacion = SimulacionCluster(horas=self.horas_p2, dt_min=self.dt_min,
                                                semilla=self.semilla, mostrar_consola=False)
            self.vista = VistaCluster(ANCHO, ALTO)
            self.hilo = HiloCluster(self.simulacion, self.vista, velocidad)
        self.problema = problema
        self.pausada = False
        self.ultimo_estado = None
        self.hilo.start()

    def _cerrar_hilo(self):
        """Detiene el hilo en curso y cierra la traza de la simulación anterior."""
        if self.hilo is not None:
            self.hilo.detener.set()
            self.hilo.join(timeout=2.0)
            metricas = self.simulacion.finalizar()
            if self.hilo.terminada:
                self.resultados[self.problema] = metricas
            self.hilo = None

    def _cambiar_velocidad(self, delta):
        self.indice_velocidad = max(0, min(len(VELOCIDADES) - 1, self.indice_velocidad + delta))
        if self.hilo is not None:
            self.hilo.velocidad = VELOCIDADES[self.indice_velocidad]

    def _procesar_eventos(self):
        """Gestiona el teclado y el cierre de la ventana. Devuelve False para salir."""
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return False
            if evento.type != pygame.KEYDOWN:
                continue
            tecla = evento.key
            if tecla in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if self.problema is None:
                # Menú de selección de problema
                if tecla in (pygame.K_1, pygame.K_KP1):
                    self._crear_simulacion("p1")
                elif tecla in (pygame.K_2, pygame.K_KP2):
                    self._crear_simulacion("p2")
                continue
            if tecla in (pygame.K_SPACE, pygame.K_p):
                # Pausa solo la animación: el hilo de cálculo sigue trabajando
                self.pausada = not self.pausada
            elif tecla in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self._cambiar_velocidad(1)
            elif tecla in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self._cambiar_velocidad(-1)
            elif tecla == pygame.K_r:
                self._crear_simulacion(self.problema)
            elif tecla == pygame.K_m:
                self._cerrar_hilo()
                self.problema = None
        return True

    # ------------------------------------------------------------------- dibujo
    def _dibujar_menu(self):
        self.pantalla.fill(Paleta.FONDO)
        self.lienzo.texto("PARCIAL III · SIMULACIÓN", ANCHO // 2, 120, "titulo", Paleta.TEXTO_SEC, centrado=True)
        self.lienzo.texto("Animación de las simulaciones", ANCHO // 2, 150, "grande", Paleta.TEXTO, centrado=True)

        opciones = [
            ("1", "Problema 1 · Fábrica de laptops", f"Eventos discretos · {self.horas_p1:g} h simuladas", Paleta.ACENTO),
            ("2", "Problema 2 · Clúster de servidores", f"Simulación continua · {self.horas_p2:g} h simuladas", Paleta.OK),
        ]
        for i, (tecla, titulo, detalle, color) in enumerate(opciones):
            rect = pygame.Rect(ANCHO // 2 - 300, 230 + i * 110, 600, 88)
            pygame.draw.rect(self.pantalla, Paleta.PANEL, rect, border_radius=10)
            pygame.draw.rect(self.pantalla, color, rect, width=2, border_radius=10)
            caja = pygame.Rect(rect.x + 20, rect.y + 22, 44, 44)
            pygame.draw.rect(self.pantalla, color, caja, border_radius=8)
            self.lienzo.texto(tecla, caja.centerx, caja.y + 8, "grande", Paleta.FONDO, centrado=True)
            self.lienzo.texto(titulo, rect.x + 84, rect.y + 22, "normal", Paleta.TEXTO)
            self.lienzo.texto(detalle, rect.x + 84, rect.y + 46, "pequena", Paleta.TEXTO_SEC)
            if self.resultados.get("p1" if tecla == "1" else "p2"):
                self.lienzo.texto("completada", rect.right - 20, rect.y + 22, "pequena", Paleta.OK, derecha=True)

        self.lienzo.texto("Pulsa 1 o 2 para comenzar · ESC para salir",
                          ANCHO // 2, 470, "normal", Paleta.TEXTO_SEC, centrado=True)

    def _dibujar_simulacion(self):
        instantanea, pasos, terminada = self.hilo.obtener_instantanea()
        # Con la animación en pausa se sigue mostrando la última imagen capturada
        if not self.pausada or self.ultimo_estado is None:
            self.ultimo_estado = instantanea
        estado = dict(self.ultimo_estado)
        estado["pausada"] = self.pausada
        estado["terminada"] = terminada
        estado["pasos_logicos"] = pasos
        estado["velocidad"] = VELOCIDADES[self.indice_velocidad]
        self.pantalla.fill(Paleta.FONDO)
        self.vista.dibujar(self.lienzo, estado)

    def ejecutar(self):
        """Bucle principal de la ventana. Devuelve las métricas de lo simulado."""
        activo = True
        while activo:
            activo = self._procesar_eventos()
            if self.problema is None:
                self._dibujar_menu()
            else:
                self._dibujar_simulacion()
            pygame.display.flip()
            self.reloj.tick(FPS)
        self._cerrar_hilo()
        pygame.quit()
        return self.resultados
