#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cadena de tolerancias de la envolvente v2: pala plegada sobre el cuerpo impreso de Ø81 dentro de Ø90.
Borde de la pala: r = sqrt((rho - s + t)^2 + (c/2)^2), con rho el radio del cuerpo (más la posición radial de
la pala), s la flecha, t el espesor y c la cuerda (geometría del capítulo de arquitectura, v2_geometria.py).
Salida: analysis/data/v2_tol_env.json. Uso: python3 analysis/v2_tol_env.py"""
import os, json
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
rng = np.random.default_rng(20261018)
N = 400_000
R_ENV = 45.0
def mc(rho_nom, tol_s, tol_bow, c_nom=45.0):
    # posición radial de la pala: bisagra 0,10; pasador 0,05 unif.; asiento 0,10; arco longitudinal tol_bow; ranura 0,10; cuerpo 0,15 (3 sigma)
    rho = (rng.normal(rho_nom, 0.15/3, N) + rng.normal(0, 0.10/3, N) + rng.uniform(-0.05, 0.05, N) + rng.normal(0, 0.10/3, N)
           + rng.normal(0, tol_bow/3, N) + rng.normal(0, 0.10/3, N))
    s = rng.normal(3.15, tol_s/3, N); c = rng.normal(c_nom, 0.2/3, N); t = rng.normal(0.5, 0.05/3, N)
    r = np.sqrt((rho - s + t)**2 + (c/2)**2)
    m = R_ENV - r
    return m
out = {}
for nombre, tol_s, tol_bow in (('base', 0.30, 0.30), ('propuesta', 0.15, 0.15)):
    m = mc(40.5, tol_s, tol_bow)
    out[nombre] = dict(media=float(m.mean()), sd=float(m.std()), P_interf=float(np.mean(m < 0)), p0135=float(np.percentile(m, 0.135)),
                       sigmas=float(m.mean() / m.std()))
# peor caso lineal (suma de tolerancias) con tol propuesta
r0 = np.sqrt((40.5 - 3.15 + 0.5)**2 + 22.5**2)
out['nominal'] = dict(r_borde=float(r0), holgura=float(R_ENV - r0))
json.dump(out, open(os.path.join(D, 'v2_tol_env.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
