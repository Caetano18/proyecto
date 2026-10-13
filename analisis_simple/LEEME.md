# Análisis en frecuencia — versión simple

Un solo archivo: `analisis.py`.

1. Abrilo y cambiá el **PASO 0** (tu `G(s)`, `K` y, si querés, la compensación).
2. Apretá ▶ (o `python analisis.py`).
3. Mirá lo que sale en el terminal y las figuras (se guardan en `graficos/`).

Instalar una vez: `pip install control numpy matplotlib`

## Qué hace, en orden
1. Sistema: polos, ceros, tipo, constante de error (y ajusta K si pedís `CTE_DESEADA`).
2. **Compensación** (si pedís `DISENAR`): la calcula paso a paso, imprimiendo cada cuenta.
3. Márgenes y estabilidad por Nyquist (verificada con las raíces) + rango de K estable.
4. Lazo cerrado: polos, Mr, ancho de banda, escalón.
5. Resumen sin compensar vs compensado + gráficos (Bode, Nyquist, Nichols, escalón, Bode de Gc).

## Compensación
| `DISENAR =` | Qué hace |
|---|---|
| `"adelanto"` | φm, α, ωm, T: sube fase y velocidad |
| `"atraso"` | busca ωc' por la fase, β = \|L(jωc')\|, T = 10/ωc' |
| `"atraso_adelanto"` | adelanto centrado en ωc' (por defecto ω180) + atraso que baja la ganancia |
| `"PI"` | agrega un integrador; cero bien por debajo de ωc |

Datos que pide: `MF_DESEADO`, `MG_DESEADO` (opcional, dB), `WC_NUEVO` (opcional), `CTE_DESEADA` (opcional).
Si ya tenés el compensador: `DISENAR = None` y `Gc = (50*s + 1) / (4700*s + 1)`.

La versión completa, con más diseños e informe, está en `../herramienta_control/`.
