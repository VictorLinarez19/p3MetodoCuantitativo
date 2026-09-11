"""
Componentes de dibujo reutilizables para la interfaz gráfica (pygame).

Cada clase encapsula un elemento visual: paneles, barras, medidores y la
gráfica de líneas del historial de temperatura.
"""
import pygame

from visual.paleta import Paleta


class Lienzo:
    """Envuelve la superficie de pygame y ofrece primitivas de dibujo con estilo propio."""

    def __init__(self, superficie, fuentes):
        self.sup = superficie
        self.fuentes = fuentes  # diccionario de fuentes por tamaño

    # --------------------------------------------------------------- primitivas
    def texto(self, cadena, x, y, tam="normal", color=Paleta.TEXTO, centrado=False, derecha=False):
        """Dibuja una línea de texto y devuelve su rectángulo."""
        render = self.fuentes[tam].render(cadena, True, color)
        rect = render.get_rect()
        if centrado:
            rect.midtop = (x, y)
        elif derecha:
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        self.sup.blit(render, rect)
        return rect

    def panel(self, rect, titulo=None, color_borde=Paleta.BORDE):
        """Dibuja un panel con borde y título opcional; devuelve el área interior."""
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.sup, Paleta.PANEL, rect, border_radius=8)
        pygame.draw.rect(self.sup, color_borde, rect, width=1, border_radius=8)
        interior = rect.inflate(-24, -24)
        if titulo:
            self.texto(titulo, rect.x + 12, rect.y + 10, "pequena", Paleta.TEXTO_SEC)
            interior = pygame.Rect(rect.x + 12, rect.y + 34, rect.width - 24, rect.height - 46)
        return interior

    def barra_horizontal(self, rect, fraccion, color, fondo=Paleta.PANEL_CLARO):
        """Barra de progreso horizontal con extremos redondeados."""
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.sup, fondo, rect, border_radius=4)
        ancho = int(rect.width * max(0.0, min(1.0, fraccion)))
        if ancho > 0:
            pygame.draw.rect(self.sup, color, (rect.x, rect.y, max(ancho, 4), rect.height), border_radius=4)


class BarraInventario:
    """Indicador vertical del nivel de inventario de procesadores."""

    def __init__(self, rect, capacidad_visual=110):
        self.rect = pygame.Rect(rect)
        self.capacidad = capacidad_visual

    def dibujar(self, lienzo, stock, umbral, en_parada):
        rect = self.rect
        pygame.draw.rect(lienzo.sup, Paleta.PANEL_CLARO, rect, border_radius=6)

        # Color según la situación del inventario (siempre acompañado de texto)
        if stock == 0:
            color = Paleta.CRITICO
        elif stock < umbral:
            color = Paleta.AVISO
        else:
            color = Paleta.OK

        fraccion = max(0.0, min(1.0, stock / self.capacidad))
        alto = int(rect.height * fraccion)
        if alto > 0:
            relleno = pygame.Rect(rect.x, rect.bottom - alto, rect.width, alto)
            pygame.draw.rect(lienzo.sup, color, relleno, border_radius=6)

        # Línea del umbral crítico de reabastecimiento
        y_umbral = rect.bottom - int(rect.height * min(1.0, umbral / self.capacidad))
        for x in range(rect.x, rect.right, 8):
            pygame.draw.line(lienzo.sup, Paleta.TEXTO_SEC, (x, y_umbral), (x + 4, y_umbral), 1)
        lienzo.texto(f"umbral {umbral}", rect.right + 8, y_umbral - 8, "pequena", Paleta.TEXTO_SEC)

        pygame.draw.rect(lienzo.sup, Paleta.BORDE, rect, width=1, border_radius=6)
        lienzo.texto(str(stock), rect.centerx, rect.y - 34, "grande", Paleta.TEXTO, centrado=True)
        etiqueta = "SIN STOCK" if stock == 0 else ("BAJO UMBRAL" if stock < umbral else "NIVEL OK")
        lienzo.texto(etiqueta, rect.centerx, rect.bottom + 8, "pequena", color, centrado=True)


class MedidorTermico:
    """Medidor vertical de temperatura con zonas de throttling y crítica."""

    def __init__(self, rect, t_min=40.0, t_max=100.0, t_throttling=70.0, t_critica=90.0):
        self.rect = pygame.Rect(rect)
        self.t_min = t_min
        self.t_max = t_max
        self.t_throttling = t_throttling
        self.t_critica = t_critica

    def _y(self, temperatura):
        """Convierte una temperatura en la coordenada vertical del medidor."""
        f = (temperatura - self.t_min) / (self.t_max - self.t_min)
        f = max(0.0, min(1.0, f))
        return self.rect.bottom - int(self.rect.height * f)

    def dibujar(self, lienzo, temperatura):
        rect = self.rect
        pygame.draw.rect(lienzo.sup, Paleta.PANEL_CLARO, rect, border_radius=6)

        # Relleno con degradado térmico hasta la temperatura actual
        y_actual = self._y(temperatura)
        for y in range(y_actual, rect.bottom):
            f = (rect.bottom - y) / rect.height
            t = self.t_min + f * (self.t_max - self.t_min)
            pygame.draw.line(lienzo.sup, Paleta.color_temperatura(t), (rect.x + 1, y), (rect.right - 2, y))

        # Marcas de referencia: umbral de throttling y zona crítica
        for valor, etiqueta, color in ((self.t_throttling, "70 °C throttling", Paleta.AVISO),
                                       (self.t_critica, "90 °C crítico", Paleta.CRITICO)):
            y = self._y(valor)
            pygame.draw.line(lienzo.sup, color, (rect.x - 4, y), (rect.right + 4, y), 1)
            lienzo.texto(etiqueta, rect.right + 10, y - 8, "pequena", color)

        pygame.draw.rect(lienzo.sup, Paleta.BORDE, rect, width=1, border_radius=6)
        # Indicador de la lectura actual
        pygame.draw.line(lienzo.sup, Paleta.TEXTO, (rect.x - 6, y_actual), (rect.right + 6, y_actual), 2)
        lienzo.texto(f"{temperatura:.1f} °C", rect.centerx, rect.y - 36, "grande",
                     Paleta.color_temperatura(temperatura), centrado=True)


class GraficaTemperatura:
    """Gráfica de líneas del historial de temperatura (una sola serie)."""

    def __init__(self, rect, t_min=40.0, t_max=100.0, muestras=320):
        self.rect = pygame.Rect(rect)
        self.t_min = t_min
        self.t_max = t_max
        self.muestras = muestras

    def _y(self, temperatura):
        f = (temperatura - self.t_min) / (self.t_max - self.t_min)
        f = max(0.0, min(1.0, f))
        return self.rect.bottom - self.rect.height * f

    def dibujar(self, lienzo, serie, minutos_totales):
        rect = self.rect

        # Rejilla recesiva y escala vertical
        for valor in (40, 55, 70, 85, 100):
            y = int(self._y(valor))
            pygame.draw.line(lienzo.sup, Paleta.REJILLA, (rect.x, y), (rect.right, y), 1)
            lienzo.texto(f"{valor}", rect.x - 8, y - 8, "pequena", Paleta.TEXTO_TENUE, derecha=True)

        # Líneas de umbral, etiquetadas directamente
        for valor, etiqueta, color in ((70, "throttling", Paleta.AVISO), (90, "crítico", Paleta.CRITICO)):
            y = int(self._y(valor))
            for x in range(rect.x, rect.right, 10):
                pygame.draw.line(lienzo.sup, color, (x, y), (x + 5, y), 1)
            lienzo.texto(etiqueta, rect.right + 8, y - 7, "pequena", color)

        if len(serie) >= 2:
            # Se muestran las últimas muestras para que la gráfica avance en tiempo real
            datos = serie[-self.muestras:]
            paso_x = rect.width / max(1, len(datos) - 1)
            puntos = [(rect.x + i * paso_x, self._y(v)) for i, v in enumerate(datos)]
            pygame.draw.lines(lienzo.sup, Paleta.ACENTO, False, puntos, 2)
            # Se etiqueta solo el valor actual, no cada punto
            ultimo = puntos[-1]
            pygame.draw.circle(lienzo.sup, Paleta.PANEL, ultimo, 6)
            pygame.draw.circle(lienzo.sup, Paleta.color_temperatura(datos[-1]), ultimo, 4)

        pygame.draw.rect(lienzo.sup, Paleta.BORDE, rect, width=1)
        lienzo.texto(f"°C · últimos {min(len(serie), self.muestras)} de {int(minutos_totales)} min simulados",
                     rect.x, rect.bottom + 10, "pequena", Paleta.TEXTO_TENUE)
