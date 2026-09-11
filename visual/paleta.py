"""
Paleta de colores de la interfaz gráfica.

Los colores de estado (normal / aviso / crítico) están reservados para indicar
el estado del sistema y siempre se acompañan de una etiqueta de texto, para no
depender únicamente del color.
"""


class Paleta:
    """Colores de la interfaz, agrupados en un único lugar."""

    FONDO = (18, 21, 28)
    PANEL = (27, 31, 42)
    PANEL_CLARO = (35, 40, 53)
    BORDE = (44, 51, 66)
    REJILLA = (38, 44, 58)

    TEXTO = (232, 236, 244)
    TEXTO_SEC = (154, 164, 184)
    TEXTO_TENUE = (107, 116, 136)

    ACENTO = (79, 140, 255)
    OK = (53, 196, 107)
    AVISO = (240, 160, 42)
    CRITICO = (232, 69, 60)
    FRIO = (58, 160, 232)

    # Rampa térmica: azul (frío) -> verde -> naranja -> rojo (crítico)
    RAMPA_TERMICA = [
        (40.0, (58, 160, 232)),
        (60.0, (53, 196, 107)),
        (75.0, (240, 160, 42)),
        (90.0, (232, 69, 60)),
    ]

    @classmethod
    def color_temperatura(cls, temperatura):
        """Interpola el color de la rampa térmica para una temperatura dada."""
        puntos = cls.RAMPA_TERMICA
        if temperatura <= puntos[0][0]:
            return puntos[0][1]
        if temperatura >= puntos[-1][0]:
            return puntos[-1][1]
        for (t1, c1), (t2, c2) in zip(puntos, puntos[1:]):
            if t1 <= temperatura <= t2:
                f = (temperatura - t1) / (t2 - t1)
                return tuple(int(c1[i] + f * (c2[i] - c1[i])) for i in range(3))
        return puntos[-1][1]

    @staticmethod
    def mezclar(color_a, color_b, factor):
        """Mezcla dos colores; factor 0 devuelve color_a y 1 devuelve color_b."""
        factor = max(0.0, min(1.0, factor))
        return tuple(int(color_a[i] + factor * (color_b[i] - color_a[i])) for i in range(3))
