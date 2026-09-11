# Parcial III - Simulación (Python POO)

Simulación de dos problemas con menú de opciones, trazas analizables y
conclusión automática generada por una API de IA (Google Gemini).

- **Problema 1**: simulación de eventos discretos de una fábrica de laptops
  (llegadas Poisson 10/h, ensamblaje exponencial media 5 min, inventario con
  umbral 10, lote 50 y entrega en 15 min).
- **Problema 2**: simulación continua de un clúster de servidores (balance
  térmico con EDO de primer orden integrada por Runge-Kutta 4, tráfico
  normal(3,1) Gbps recortado a [1,5], throttling por encima de 70 °C).
- **Bonus**: animación interactiva de ambas simulaciones con pygame.

## Requisitos

```bash
pip install -r requirements.txt
```

Si el sistema bloquea la instalación (error de *externally managed environment*),
usa un entorno virtual:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

## Configurar la API de IA

Copiar `.env.example` como `.env` y colocar la clave de Google AI Studio:

```
GEMINI_API_KEY=tu_clave
GEMINI_MODEL=gemini-flash-latest
```

Si no hay clave o la API falla, el programa lo avisa y usa una conclusión
local de respaldo basada en reglas.

## Ejecutar

```bash
python main.py
```

El menú permite ejecutar cada problema por separado, los dos seguidos, o la
animación con pygame. Todas las preguntas tienen un valor por defecto
(presionar Enter): 8 h para el problema 1, 24 h para el problema 2, semilla 42.

## Animación con pygame (pregunta bonus)

Opción 4 del menú. Abre una ventana donde se elige el problema a visualizar.

- **Problema 1**: cola de órdenes entrantes como fichas numeradas, estación de
  ensamblaje que cambia de color según su estado (verde libre, naranja ocupada,
  rojo detenida) con barra de progreso, y barra de inventario de procesadores
  con su línea de umbral y el camión del lote en camino.
- **Problema 2**: nodo del clúster cuyo color sigue la temperatura, paquetes de
  red entrando según el tráfico, medidor térmico de azul a rojo crítico y
  gráfica del historial de temperatura con las líneas de 70 °C y 90 °C.

| Tecla | Acción |
|-------|--------|
| `ESPACIO` o `P` | Pausa o reanuda la **animación**; la simulación sigue calculando |
| `+` / `-` | Aumenta o reduce la velocidad de la animación |
| `R` | Reinicia la simulación en curso |
| `M` | Vuelve al menú de selección |
| `ESC` o `Q` | Cierra la ventana |

La representación visual lee directamente los atributos de las clases de la
solución de consola, por lo que una simulación animada produce exactamente las
mismas métricas que la ejecutada por consola con la misma semilla. Al terminar
una simulación en la ventana, se genera su informe con la IA igual que en el
modo consola.

## Salidas

| Archivo               | Contenido                                             |
|-----------------------|-------------------------------------------------------|
| `p1.txt` / `p2.txt`   | Métricas, análisis y conclusión/recomendación de la IA |
| `trazas/traza_p1.log` | Traza de eventos del problema 1                        |
| `trazas/traza_p2.log` | Traza paso a paso (1 min) del problema 2               |

## Estructura

```
main.py                         menú, informes p1.txt / p2.txt
simulacion/eventos_discretos.py Orden, Inventario, EstacionEnsamblaje, SimulacionFabrica
simulacion/continua.py          GeneradorTrafico, ServidorTermico, ClusterRendimiento, SimulacionCluster
ia/analizador.py                ClienteGemini, ConclusionRespaldo, AnalizadorIA
utils/validaciones.py           validación de entradas del usuario
utils/config.py                 carga de .env
visual/animacion.py             MotorAnimacion, HiloSimulacion (pregunta bonus)
visual/vistas.py                VistaFabrica, VistaCluster
visual/widgets.py               BarraInventario, MedidorTermico, GraficaTemperatura
visual/paleta.py                colores de la interfaz
```
