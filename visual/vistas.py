"""
Vistas de cada problema.

Cada vista lee DIRECTAMENTE los atributos de las clases de simulación
desarrolladas para la solución de consola (SimulacionFabrica, Inventario,
EstacionEnsamblaje, SimulacionCluster, ServidorTermico...), de modo que la
representación gráfica y el cálculo lógico están sincronizados.
"""
import random

import pygame

from visual.paleta import Paleta
from visual.widgets import BarraInventario, GraficaTemperatura, Lienzo, MedidorTermico


def formato_hhmm(minutos):
    """Convierte minutos simulados a texto HH:MM."""
    total = int(minutos)
    return f"{total // 60:02d}:{total % 60:02d}"


class VistaBase:
    """Elementos comunes a las dos vistas: cabecera y pie con los controles."""

    TITULO = ""
    SUBTITULO = ""

    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto

    def dibujar_cabecera(self, lienzo, estado):
        pygame.draw.rect(lienzo.sup, Paleta.PANEL, (0, 0, self.ancho, 58))
        pygame.draw.line(lienzo.sup, Paleta.BORDE, (0, 58), (self.ancho, 58), 1)
        lienzo.texto(self.TITULO, 24, 10, "titulo", Paleta.TEXTO)
        lienzo.texto(self.SUBTITULO, 24, 36, "pequena", Paleta.TEXTO_TENUE)
        lienzo.texto(f"Tiempo simulado  {formato_hhmm(estado['reloj'])} / {formato_hhmm(estado['reloj_fin'])}",
                     self.ancho - 24, 12, "normal", Paleta.TEXTO, derecha=True)
        progreso = estado["reloj"] / estado["reloj_fin"] if estado["reloj_fin"] else 0
        lienzo.barra_horizontal((self.ancho - 264, 38, 240, 8), progreso, Paleta.ACENTO)

    def dibujar_pie(self, lienzo, estado):
        y = self.alto - 30
        pygame.draw.line(lienzo.sup, Paleta.BORDE, (0, y - 10), (self.ancho, y - 10), 1)
        controles = "ESPACIO pausar animación   +/- velocidad   R reiniciar   M menú   ESC salir"
        lienzo.texto(controles, 24, y, "pequena", Paleta.TEXTO_TENUE)
        lienzo.texto(f"velocidad x{estado['velocidad']:g}  ({estado['velocidad']:g} min simulados por segundo real)",
                     self.ancho - 24, y, "pequena", Paleta.TEXTO_TENUE, derecha=True)

        # El cálculo lógico continúa aunque la animación esté en pausa
        if estado["pausada"]:
            aviso = f"ANIMACIÓN EN PAUSA — la simulación sigue calculando ({estado['pasos_logicos']} pasos)"
            render = lienzo.fuentes["normal"].render(aviso, True, Paleta.FONDO)
            fondo = render.get_rect(center=(self.ancho // 2, 70)).inflate(24, 10)
            pygame.draw.rect(lienzo.sup, Paleta.AVISO, fondo, border_radius=6)
            lienzo.sup.blit(render, render.get_rect(center=fondo.center))

        if estado["terminada"]:
            aviso = "SIMULACIÓN FINALIZADA — cierra la ventana para ver el informe de la IA"
            render = lienzo.fuentes["normal"].render(aviso, True, Paleta.FONDO)
            fondo = render.get_rect(center=(self.ancho // 2, 70)).inflate(24, 10)
            pygame.draw.rect(lienzo.sup, Paleta.OK, fondo, border_radius=6)
            lienzo.sup.blit(render, render.get_rect(center=fondo.center))

    @staticmethod
    def instantanea(simulacion):
        """Devuelve un diccionario con el estado visible de la simulación."""
        raise NotImplementedError

    def dibujar(self, lienzo, estado):
        raise NotImplementedError


class VistaFabrica(VistaBase):
    """Problema 1: cola de órdenes, estación de ensamblaje e inventario."""

    TITULO = "Problema 1 · Fábrica de laptops (eventos discretos)"
    SUBTITULO = "Llegadas Poisson 10/h · ensamblaje exponencial media 5 min · lote 50 cada 15 min"

    def __init__(self, ancho, alto):
        super().__init__(ancho, alto)
        self.rect_cola = pygame.Rect(24, 78, 330, 372)
        self.rect_estacion = pygame.Rect(372, 78, 392, 372)
        self.rect_inventario = pygame.Rect(782, 78, 314, 372)
        self.barra_stock = BarraInventario((820, 168, 64, 182))

    @staticmethod
    def instantanea(sim):
        """Lee los atributos de SimulacionFabrica, Inventario y EstacionEnsamblaje."""
        estacion = sim.estacion
        inventario = sim.inventario
        orden = estacion.orden_actual
        progreso = 0.0
        if orden is not None and estacion.t_fin_previsto:
            total = estacion.t_fin_previsto - orden.t_inicio
            if total > 0:
                progreso = max(0.0, min(1.0, (sim.reloj - orden.t_inicio) / total))
        esperas = [o.espera for o in sim.completadas]
        return {
            "reloj": sim.reloj,
            "reloj_fin": sim.t_fin_sim,
            "cola_ids": [o.id for o in sim.cola],
            "estacion_ocupada": estacion.ocupada,
            "orden_actual": orden.id if orden else None,
            "progreso": progreso,
            "stock": inventario.stock,
            "umbral": inventario.umbral,
            "pedido_pendiente": inventario.pedido_pendiente,
            "en_parada": sim.en_parada,
            "llegadas": len(sim.ordenes),
            "completadas": len(sim.completadas),
            "espera_media": sum(esperas) / len(esperas) if esperas else 0.0,
            "paradas": sim.paradas_por_stock,
            "reabastecimientos": inventario.reabastecimientos,
            "cola_maxima": sim.cola_maxima,
            "utilizacion": 100.0 * estacion.tiempo_ocupado / sim.reloj if sim.reloj > 0 else 0.0,
        }

    def dibujar(self, lienzo, estado):
        self.dibujar_cabecera(lienzo, estado)
        self._dibujar_cola(lienzo, estado)
        self._dibujar_estacion(lienzo, estado)
        self._dibujar_inventario(lienzo, estado)
        self._dibujar_hud(lienzo, estado)
        self.dibujar_pie(lienzo, estado)

    def _dibujar_cola(self, lienzo, estado):
        interior = lienzo.panel(self.rect_cola, "RECEPCIÓN · ÓRDENES EN COLA")
        ids = estado["cola_ids"]
        lienzo.texto(f"{len(ids)} en espera", interior.x, interior.y, "grande", Paleta.TEXTO)
        # Cada orden en espera se dibuja como una ficha con su número
        ancho, alto, sep = 62, 34, 8
        columnas = max(1, interior.width // (ancho + sep))
        visibles = ids[:24]
        for i, ident in enumerate(visibles):
            fila, col = divmod(i, columnas)
            x = interior.x + col * (ancho + sep)
            y = interior.y + 46 + fila * (alto + sep)
            if y + alto > interior.bottom:
                break
            rect = pygame.Rect(x, y, ancho, alto)
            color = Paleta.CRITICO if estado["en_parada"] else Paleta.ACENTO
            pygame.draw.rect(lienzo.sup, Paleta.PANEL_CLARO, rect, border_radius=4)
            pygame.draw.rect(lienzo.sup, color, rect, width=2, border_radius=4)
            lienzo.texto(f"#{ident}", rect.centerx, rect.y + 8, "pequena", Paleta.TEXTO, centrado=True)
        if len(ids) > len(visibles):
            lienzo.texto(f"+{len(ids) - len(visibles)} más", interior.x, interior.bottom - 20,
                         "pequena", Paleta.TEXTO_SEC)

    def _dibujar_estacion(self, lienzo, estado):
        interior = lienzo.panel(self.rect_estacion, "ESTACIÓN DE ENSAMBLAJE")
        ocupada = estado["estacion_ocupada"]
        if estado["en_parada"]:
            color, etiqueta = Paleta.CRITICO, "DETENIDA · SIN PROCESADORES"
        elif ocupada:
            color, etiqueta = Paleta.AVISO, "OCUPADA · ENSAMBLANDO"
        else:
            color, etiqueta = Paleta.OK, "LIBRE · ESPERANDO ÓRDENES"

        caja = pygame.Rect(interior.x + 30, interior.y + 24, interior.width - 60, 170)
        pygame.draw.rect(lienzo.sup, Paleta.mezclar(Paleta.PANEL_CLARO, color, 0.18), caja, border_radius=10)
        pygame.draw.rect(lienzo.sup, color, caja, width=3, border_radius=10)

        # Silueta simple de la laptop en ensamblaje
        centro_x, centro_y = caja.centerx, caja.centery
        base = pygame.Rect(centro_x - 62, centro_y + 6, 124, 12)
        tapa = pygame.Rect(centro_x - 54, centro_y - 56, 108, 62)
        pygame.draw.rect(lienzo.sup, color, base, border_radius=3)
        pygame.draw.rect(lienzo.sup, Paleta.PANEL, tapa, border_radius=4)
        pygame.draw.rect(lienzo.sup, color, tapa, width=2, border_radius=4)
        if ocupada:
            lienzo.texto(f"#{estado['orden_actual']}", centro_x, centro_y - 38, "grande", Paleta.TEXTO, centrado=True)

        lienzo.texto(etiqueta, interior.centerx, caja.bottom + 16, "normal", color, centrado=True)
        lienzo.texto("progreso del ensamblaje", interior.x, caja.bottom + 52, "pequena", Paleta.TEXTO_TENUE)
        lienzo.barra_horizontal((interior.x, caja.bottom + 72, interior.width, 12),
                                estado["progreso"] if ocupada else 0.0, color)
        lienzo.texto(f"{estado['progreso'] * 100:.0f}%" if ocupada else "—",
                     interior.right, caja.bottom + 52, "pequena", Paleta.TEXTO_SEC, derecha=True)

    def _dibujar_inventario(self, lienzo, estado):
        interior = lienzo.panel(self.rect_inventario, "INVENTARIO DE PROCESADORES")
        self.barra_stock.dibujar(lienzo, estado["stock"], estado["umbral"], estado["en_parada"])
        y = interior.bottom - 46
        if estado["pedido_pendiente"]:
            lienzo.texto("Lote de 50 en camino (15 min)", interior.x, y, "pequena", Paleta.ACENTO)
            # Camión de reparto avanzando hacia la fábrica
            avance = (pygame.time.get_ticks() % 2000) / 2000.0
            x = interior.x + int(avance * (interior.width - 40))
            pygame.draw.rect(lienzo.sup, Paleta.ACENTO, (x, y + 22, 28, 12), border_radius=3)
            pygame.draw.circle(lienzo.sup, Paleta.TEXTO_SEC, (x + 6, y + 36), 3)
            pygame.draw.circle(lienzo.sup, Paleta.TEXTO_SEC, (x + 22, y + 36), 3)
        else:
            lienzo.texto("Sin pedidos pendientes", interior.x, y, "pequena", Paleta.TEXTO_TENUE)

    def _dibujar_hud(self, lienzo, estado):
        interior = lienzo.panel((24, 466, 1072, 164), "INDICADORES EN TIEMPO REAL")
        columnas = [
            [("Órdenes llegadas", f"{estado['llegadas']}"),
             ("Órdenes completadas", f"{estado['completadas']}")],
            [("Espera promedio", f"{estado['espera_media']:.1f} min"),
             ("Cola máxima", f"{estado['cola_maxima']}")],
            [("Paradas por falta de stock", f"{estado['paradas']}"),
             ("Reabastecimientos", f"{estado['reabastecimientos']}")],
            [("Utilización de la estación", f"{estado['utilizacion']:.0f} %"),
             ("Stock de procesadores", f"{estado['stock']}")],
        ]
        ancho_col = interior.width // len(columnas)
        for i, columna in enumerate(columnas):
            x = interior.x + i * ancho_col
            for j, (etiqueta, valor) in enumerate(columna):
                y = interior.y + j * 58
                lienzo.texto(etiqueta, x, y, "pequena", Paleta.TEXTO_SEC)
                lienzo.texto(valor, x, y + 18, "grande", Paleta.TEXTO)


class VistaCluster(VistaBase):
    """Problema 2: nodo del servidor, medidor térmico y gráfica de temperatura."""

    TITULO = "Problema 2 · Clúster de servidores (simulación continua)"
    SUBTITULO = "Tráfico normal(3,1) Gbps · balance térmico por EDO · diseño 70 °C · eficiencia 90 %"

    def __init__(self, ancho, alto):
        super().__init__(ancho, alto)
        self.rect_nodo = pygame.Rect(24, 78, 392, 372)
        self.rect_medidor = pygame.Rect(436, 78, 208, 372)
        self.rect_grafica = pygame.Rect(664, 78, 432, 372)
        self.medidor = MedidorTermico((488, 158, 62, 250))
        self.grafica = GraficaTemperatura((706, 152, 296, 238))
        self.particulas = []  # paquetes de red que entran al clúster
        self.rng = random.Random(7)

    @staticmethod
    def instantanea(sim):
        """Lee los atributos de SimulacionCluster, ServidorTermico y ClusterRendimiento."""
        return {
            "reloj": sim.t,
            "reloj_fin": sim.horas * 60.0,
            "temperatura": sim.temperatura_actual,
            "trafico": sim.trafico_actual,
            "eficiencia": sim.eficiencia_actual,
            "estado_termico": sim.estado_actual,
            "tb_procesados": sim.tb_procesados,
            "tb_entrantes": sim.tb_entrantes,
            "episodios": sim.episodios_throttling,
            "serie": list(sim.serie_temperatura[-320:]),
            "t_equilibrio": sim.servidor.temperatura_equilibrio(sim.trafico_actual),
        }

    def dibujar(self, lienzo, estado):
        self.dibujar_cabecera(lienzo, estado)
        self._dibujar_nodo(lienzo, estado)
        self._dibujar_medidor(lienzo, estado)
        self._dibujar_grafica(lienzo, estado)
        self._dibujar_hud(lienzo, estado)
        self.dibujar_pie(lienzo, estado)

    def _dibujar_nodo(self, lienzo, estado):
        interior = lienzo.panel(self.rect_nodo, "NODO DEL CLÚSTER · TRÁFICO ENTRANTE")
        color = Paleta.color_temperatura(estado["temperatura"])

        # Paquetes de red que fluyen hacia el servidor; la densidad sigue al tráfico
        carril_y = interior.y + 40
        if self.rng.random() < estado["trafico"] / 6.0:
            self.particulas.append([interior.x, self.rng.uniform(-16, 16)])
        rack_x = interior.right - 150
        for particula in self.particulas:
            particula[0] += 3.2
            pygame.draw.circle(lienzo.sup, Paleta.ACENTO,
                               (int(particula[0]), int(carril_y + particula[1])), 3)
        self.particulas = [p for p in self.particulas if p[0] < rack_x]
        lienzo.texto(f"{estado['trafico']:.2f} Gbps", interior.x, interior.y + 66, "normal", Paleta.ACENTO)
        lienzo.barra_horizontal((interior.x, interior.y + 92, interior.width - 160, 10),
                                (estado["trafico"] - 1.0) / 4.0, Paleta.ACENTO)
        lienzo.texto("1 Gbps", interior.x, interior.y + 106, "pequena", Paleta.TEXTO_TENUE)
        lienzo.texto("5 Gbps", interior.x + interior.width - 160, interior.y + 106,
                     "pequena", Paleta.TEXTO_TENUE, derecha=True)

        # Bastidor de servidores: el color sigue la temperatura del clúster
        rack = pygame.Rect(rack_x, interior.y + 18, 138, 200)
        pygame.draw.rect(lienzo.sup, Paleta.mezclar(Paleta.PANEL_CLARO, color, 0.22), rack, border_radius=8)
        pygame.draw.rect(lienzo.sup, color, rack, width=3, border_radius=8)
        for i in range(5):
            ranura = pygame.Rect(rack.x + 12, rack.y + 14 + i * 36, rack.width - 24, 26)
            pygame.draw.rect(lienzo.sup, Paleta.PANEL, ranura, border_radius=3)
            pygame.draw.rect(lienzo.sup, color, ranura, width=1, border_radius=3)
            # Luces de actividad de cada servidor
            encendidas = int(estado["eficiencia"] / 0.9 * 5)
            for j in range(5):
                luz = Paleta.OK if j < encendidas else Paleta.BORDE
                pygame.draw.circle(lienzo.sup, luz, (ranura.right - 14 - j * 12, ranura.centery), 3)

        # Estado térmico, siempre con etiqueta de texto además del color
        etiquetas = {"NORMAL": ("OPERACIÓN NORMAL", Paleta.OK),
                     "THROTTLING": ("THROTTLING TÉRMICO", Paleta.AVISO),
                     "CRITICO": ("TEMPERATURA CRÍTICA", Paleta.CRITICO)}
        texto, color_estado = etiquetas[estado["estado_termico"]]
        lienzo.texto(texto, rack.centerx, rack.bottom + 14, "normal", color_estado, centrado=True)
        lienzo.texto(f"equilibrio para este tráfico: {estado['t_equilibrio']:.1f} °C",
                     interior.x, interior.bottom - 18, "pequena", Paleta.TEXTO_TENUE)

    def _dibujar_medidor(self, lienzo, estado):
        lienzo.panel(self.rect_medidor, "MEDIDOR TÉRMICO")
        self.medidor.dibujar(lienzo, estado["temperatura"])

    def _dibujar_grafica(self, lienzo, estado):
        lienzo.panel(self.rect_grafica, "HISTORIAL DE TEMPERATURA")
        self.grafica.dibujar(lienzo, estado["serie"], estado["reloj_fin"])

    def _dibujar_hud(self, lienzo, estado):
        interior = lienzo.panel((24, 466, 1072, 164), "INDICADORES EN TIEMPO REAL")
        columnas = [
            [("Temperatura actual", f"{estado['temperatura']:.1f} °C"),
             ("Tráfico entrante", f"{estado['trafico']:.2f} Gbps")],
            [("Eficiencia instantánea", f"{estado['eficiencia'] * 100:.0f} %"),
             ("Estado térmico", estado["estado_termico"])],
            [("Datos procesados", f"{estado['tb_procesados']:.2f} TB"),
             ("Datos entrantes", f"{estado['tb_entrantes']:.2f} TB")],
            [("Episodios de throttling", f"{estado['episodios']}"),
             ("Eficiencia global",
              f"{100.0 * estado['tb_procesados'] / estado['tb_entrantes']:.1f} %" if estado["tb_entrantes"] else "—")],
        ]
        ancho_col = interior.width // len(columnas)
        for i, columna in enumerate(columnas):
            x = interior.x + i * ancho_col
            for j, (etiqueta, valor) in enumerate(columna):
                y = interior.y + j * 58
                lienzo.texto(etiqueta, x, y, "pequena", Paleta.TEXTO_SEC)
                color = Paleta.TEXTO
                if etiqueta == "Estado térmico":
                    color = {"NORMAL": Paleta.OK, "THROTTLING": Paleta.AVISO,
                             "CRITICO": Paleta.CRITICO}[valor]
                lienzo.texto(valor, x, y + 18, "grande", color)
