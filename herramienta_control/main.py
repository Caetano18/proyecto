#!/usr/bin/env python3
"""Herramienta de análisis y compensación en frecuencia.

Uso:
    python main.py                          # lee entradas.py (en esta carpeta)
    python main.py ejemplos/parcial1_nyquist_atraso.py
    python main.py mi_planta.py --no-show   # guarda las figuras sin abrir ventanas
    python main.py --lista                  # muestra los ejemplos disponibles

Todo lo que se configura está en el archivo de entradas (ver entradas.py).
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import warnings

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from controlfreq.pipeline import cargar_entradas, ejecutar   # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Análisis y compensación en frecuencia (Bode, Nyquist, Nichols, márgenes, lazo cerrado).")
    ap.add_argument("entradas", nargs="?", default=None, help="archivo de entradas (por defecto: entradas.py)")
    ap.add_argument("--no-show", action="store_true", help="no abrir ventanas de gráficos (solo guardar los archivos)")
    ap.add_argument("--salida", default=None, help="carpeta de salida (por defecto: la de CARPETA_SALIDA)")
    ap.add_argument("--sin-graficos", action="store_true", help="solo calcular y escribir el informe")
    ap.add_argument("--silencioso", action="store_true", help="no imprimir el informe en pantalla")
    ap.add_argument("--lista", action="store_true", help="listar los ejemplos de la carpeta ejemplos/")
    a = ap.parse_args(argv)

    if a.lista:
        print("Ejemplos disponibles (python main.py ejemplos/<archivo>):")
        for f in sorted(glob.glob(os.path.join(AQUI, "ejemplos", "*.py"))):
            primera = ""
            with open(f, encoding="utf-8") as fh:
                for linea in fh:
                    if linea.startswith("# TITULO:"):
                        primera = linea.split(":", 1)[1].strip()
                        break
            print(f"  ejemplos/{os.path.basename(f):42s} {primera}")
        return 0

    warnings.filterwarnings("ignore")        # avisos numéricos de control/scipy que no aportan al usuario
    try:
        ent = cargar_entradas(a.entradas)
    except Exception as exc:
        print(f"Error al leer las entradas: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    mostrar = False if (a.no_show or a.sin_graficos) else None
    try:
        ejecutar(ent, mostrar=mostrar, salida=a.salida, imprimir=not a.silencioso, guardar_graficos=not a.sin_graficos)
    except Exception as exc:
        print(f"\nError: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
