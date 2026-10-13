# Analisis en frecuencia

Un solo archivo: `analisis.py`.

Se cambian los datos al principio del archivo (la funcion de transferencia `G`, `K`, y si se quiere
compensar, `diseno`) y se ejecuta (`python analisis.py`, o el boton de play en VS Code).

Instalar una vez: `pip install control numpy matplotlib`

Hace, en orden: polos, ceros, tipo y constante de error / compensador / margenes y Nyquist / rango de K
estable / lazo cerrado y escalon / resumen y graficos (quedan en la carpeta `graficos`).

Compensadores (`diseno = ...`): `"adelanto"`, `"atraso"`, `"atraso_adelanto"`, `"PI"`.
Datos que usa: `mf_pedido`, `mg_pedido` (opcional, en dB), `wc_nueva` (opcional), `cte_pedida` (opcional).
Si ya se tiene el compensador: `diseno = None` y `Gc = (50*s + 1)/(4700*s + 1)`.

Limitaciones: si hay varios cruces por 0 dB o por -180 grados, MF y MG son los del cruce principal;
el retardo se aproxima con Pade de orden 8.
