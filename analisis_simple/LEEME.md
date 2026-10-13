# Análisis en frecuencia — versión simple

Un solo archivo: `analisis.py`.

1. Abrilo y cambiá el **PASO 0** (tu `G(s)`, `K`, y si querés compensación).
2. Apretá ▶ (o `python analisis.py`).
3. Mirá lo que sale en el terminal y las 4 figuras (se guardan en `graficos/`).

Instalar una vez: `pip install control numpy matplotlib`

Qué hace, en orden: sistema (polos, ceros, tipo, constante de error) → compensador (si lo pedís) →
márgenes y estabilidad por Nyquist (verificada con las raíces) → rango de K estable →
lazo cerrado (polos, Mr, ancho de banda, escalón) → gráficos (Bode, Nyquist, Nichols, escalón).

La versión completa, con más diseños e informe, está en `../herramienta_control/`.
