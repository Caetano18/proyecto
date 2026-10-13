# Herramienta de análisis y compensación en frecuencia

Cargás tu función de transferencia y las especificaciones en **un solo archivo** (`entradas.py`) y la herramienta calcula
y grafica todo lo que se vio en el apunte y en los parciales: forma de Bode, tipo y constantes de error, estabilidad
(Nyquist numérico y Routh por barrido), márgenes de ganancia y fase (con **todos** los cruces), Nichols con contornos M,
lazo cerrado (Mr, ancho de banda, sensibilidad), respuesta temporal (Mp, tp, tr, ts, error de rampa) y el
**diseño de compensadores** (adelanto, atraso, atraso-adelanto, PI, Ziegler-Nichols) con verificación.

## Instalación

```bash
pip install -r requirements.txt        # numpy, scipy, matplotlib, control
```

## Uso rápido

```bash
python main.py                                  # analiza lo que esté en entradas.py
# (en VS Code: abrí entradas.py y apretá el botón ▶ de arriba a la derecha, hace lo mismo)
python main.py ejemplos/parcial1_nyquist_atraso.py
python main.py mi_planta.py --no-show           # solo guarda las figuras (no abre ventanas)
python main.py --lista                          # lista los ejemplos
python -m unittest discover -s tests -v         # pruebas automáticas
```

Copiá `entradas.py` con otro nombre para cada ejercicio. Los resultados quedan en la carpeta `salidas/`
(figuras `.png`, `informe.txt` y, si querés, datos `.dat` para LaTeX).

## Qué se edita (`entradas.py`)

| Bloque | Variables | Para qué |
|---|---|---|
| 1. Planta | `EXPRESION` · `NUM`/`DEN` · `POLOS_CEROS` · `FACTORES_BODE` · `ASINTOTAS_BODE`, `K`, `RETARDO`, `SENSOR` | definir G(s) de la forma que te resulte más cómoda (elegí una) |
| 2. Compensador propio | `COMPENSADOR` | analizar un Gc(s) que ya tenés |
| 3. Especificaciones | `ESPECS` (`Kp`, `Kv`, `Ka`, `MF`, `MG`, `MG_dB`, `Mp`, `ts`, `wc_min`, `BW_min`, `Mr_dB`) | lo que debe cumplir el lazo |
| 4. Diseño | `DISENO`, `PARAMS_DISENO` | `None` solo analiza; `"auto"` prueba y recomienda; o un tipo puntual |
| 5. Salidas | `SECCIONES`, `GRAFICOS`, `CASOS_K` | qué calcular y qué dibujar |
| 6. Opciones | `W_MIN`, `W_MAX`, `T_FINAL`, `MOSTRAR`, `FORMATOS`, `EXPORTAR_DAT`, … | rangos y formato |

### Formas de cargar G(s)

```python
EXPRESION = "K/(s**3 + 10*s**2 + 5*s)"; K = 100                       # texto
NUM, DEN = [1], [1, 10, 5, 0]                                         # coeficientes (G = K·NUM/DEN)
POLOS_CEROS = dict(polos=[0, -1, -2], ceros=[], K=2, forma="monica")  # raíces
FACTORES_BODE = dict(K_dB=[34, -2.41, -40], integradores=1, polos=[1.3, 100])   # lo que se lee del Bode
ASINTOTAS_BODE = dict(w_ref=0.1, mag_dB=20, pendiente_inicial=-20, quiebres=[(1.3, -20), (100, -20)])
```

`FACTORES_BODE` y `ASINTOTAS_BODE` sirven para **reconstruir G(s) desde un diagrama de Bode** (la figura
`01_descomposicion_bode.png` muestra cada factor y su suma, como en el ejercicio del parcial).

## Qué calcula (secciones del informe)

1. **Sistema**: polinomios, polos/ceros, forma de Bode, tipo, `Kp/Kv/Ka`, errores en régimen, quiebres y pendientes por tramo.
2. **Estabilidad**: Nyquist numérico (`P`, `N`, `Z = N + P`, verificado contra las raíces), rango de `K` estable, ganancias críticas
   y casos de `K` de distinta naturaleza (estable oscilatorio, marginal, inestable, `K<0`).
3. **Respuesta en frecuencia**: márgenes (todos los cruces, margen de retardo), `Mr`, ancho de banda, sensibilidad `Ms`,
   y la estimación del sobreimpulso desde Nichols/margen de fase **comparada con la simulación**.
4. **Respuesta temporal**: escalón (Mp, tp, tr, ts 2 % y 5 %) y rampa (error en régimen).
5. **Compensación**: diseño paso a paso con las recetas del apunte (con la tabla de iteraciones), verificación contra `ESPECS`
   y comparación de candidatos.
6. **Sistema compensado elegido** y 7. **comparación sin compensar vs compensado**.

## Figuras (`salidas/`)

`01_descomposicion_bode` · `02_bode` (con asíntotas, MF y MG anotados) · `03_nyquist` (con `N`, `P`, `Z` y zoom en −1) ·
`04_nichols` (contornos M y contorno `Mr`) · `05_temporal` (escalón, rampa, error) · `06_polos_ceros` · `07_estabilidad_K`
(polos al variar K y escalones por caso) · `08_sensibilidad` · `09_compensacion_<tipo>` · `10_comparacion_candidatos`.

## Usarla como librería

```python
from controlfreq.sistema import Sistema, tf_desde_expresion
from controlfreq.frecuencia import margenes, nyquist_conteo
from controlfreq.compensacion import disenar

S = Sistema(tf_desde_expresion("K/(s**3+10*s**2+5*s)", K=100))
print(margenes(S).MF, nyquist_conteo(S).Z)
candidatos, recomendado, msgs = disenar(S, dict(Kv=20, MF=50, MG=5), ("atraso", "atraso_adelanto"))
print(recomendado.tipo, recomendado.Gc)
```

## Estructura

```
entradas.py            <- lo único que se edita
main.py                <- ejecuta (CLI)
controlfreq/
  sistema.py           planta, constructores de G(s), forma de Bode, tipo, constantes de error
  frecuencia.py        Bode, márgenes, Nyquist (conteo), Nichols, lazo cerrado en frecuencia
  temporal.py          escalón, rampa y métricas
  estabilidad.py       rangos de K, casos, K para un MF / MG / Mr
  metricas.py          métricas completas y verificación de especificaciones
  compensacion.py      adelanto, atraso, atraso-adelanto, PI, Ziegler-Nichols, selector automático
  graficos.py          todas las figuras
  informe.py           informe de texto
  exportar.py          .dat (pgfplots) y .csv
  pipeline.py          orquestador
ejemplos/              entradas listas (parciales, apunte, aeronave, retardo, tipo 2, P≠0, ...)
tests/                 pruebas con los valores verificados del apunte
```

## Notas y límites

* El margen de ganancia se pide **en veces** (`MG`) o **en dB** (`MG_dB`); si el enunciado no aclara, probá con ambos.
* El retardo es exacto en frecuencia (Bode, Nyquist, márgenes) y se aproxima con Padé (`ORDEN_PADE`) en el dominio del tiempo.
* Con varios cruces de 0 dB o de −180° el informe los lista todos; los valores principales son los de menor |margen|.
  En lazos condicionalmente estables o con `P ≠ 0`, confiá en el conteo de Nyquist (`Z`), no solo en los márgenes.
* Las fórmulas de sobreimpulso por `Mr` y `MF` son de segundo orden: con polos lentos (dipolo del atraso) pueden diferir de la simulación.
* El ejemplo `ejemplos/parcial2_reconstruir_bode.py` usa `wc_nuevo=0.5` para reproducir la resolución del PDF.
