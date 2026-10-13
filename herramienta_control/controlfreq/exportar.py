"""Exportación de datos para otros programas: archivos .dat (pgfplots / LaTeX) y .csv."""
from __future__ import annotations

import csv
import os

import numpy as np

from .sistema import Sistema
from .frecuencia import bode_datos, rejilla
from .temporal import respuesta_escalon


def _guardar_dat(ruta: str, columnas: dict) -> str:
    claves = list(columnas)
    M = np.column_stack([np.asarray(columnas[k], dtype=float) for k in claves])
    with open(ruta, "w") as f:
        f.write(" ".join(claves) + "\n")
        for fila in M:
            f.write(" ".join(f"{v:.6g}" for v in fila) + "\n")
    return ruta


def exportar_dat(sistemas, carpeta: str = "salidas/datos", prefijo: str = "sis", orden_pade: int = 8, n: int = 700) -> list[str]:
    """Para cada (etiqueta, Sistema) escribe  <prefijo>_<i>_bode.dat (w mag fase),  _nichols.dat (fase mag),
    _nyquist.dat (re im imn)  y  _step.dat (t y).  Se leen en LaTeX con  table[x=w,y=mag]{archivo}."""
    os.makedirs(carpeta, exist_ok=True)
    rutas = []
    for i, (lab, sis) in enumerate(sistemas):
        base = os.path.join(carpeta, f"{prefijo}_{i}")
        w = rejilla(sis, n=n)
        mag, fase = bode_datos(sis, w)
        rutas.append(_guardar_dat(base + "_bode.dat", {"w": w, "mag": mag, "fase": fase}))
        rutas.append(_guardar_dat(base + "_nichols.dat", {"fase": fase, "mag": mag}))
        L = sis.respuesta(w)
        ok = np.isfinite(L) & (np.abs(L) < 50)
        rutas.append(_guardar_dat(base + "_nyquist.dat", {"re": L.real[ok], "im": L.imag[ok], "imn": -L.imag[ok]}))
        r = respuesta_escalon(sis, orden_pade=orden_pade)
        k = max(len(r.t) // 1500, 1)
        rutas.append(_guardar_dat(base + "_step.dat", {"t": r.t[::k], "y": np.clip(r.y[::k], -1e3, 1e3)}))
    return rutas


def exportar_csv_resumen(filas: list[tuple[str, dict]], ruta: str) -> str:
    """Una fila por sistema con las métricas principales."""
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    claves = ["sistema"] + list(filas[0][1].keys())
    with open(ruta, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(claves)
        for nombre, d in filas:
            wr.writerow([nombre] + [("" if v is None else v) for v in d.values()])
    return ruta
