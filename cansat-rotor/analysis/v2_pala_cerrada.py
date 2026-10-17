#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pala cerrada con espesor (arco 7 % y espesor NACA 8 %): rigidez y masa de primer orden con la teoría de pared delgada
(Bredt-Batho para la torsión) y las propiedades del laminado B (+-45 y 0 UD) del capítulo de estructura, con núcleo de espuma
de 32 kg/m3 sin rigidez. Compara con la pala abierta B de 0,5 mm. Estimación de primer orden: no incluye el borde de fuga
ni el pegado, y supone la piel de espesor constante. Salida: analysis/data/v2_pala_cerrada.json.
Uso: python3 analysis/v2_pala_cerrada.py"""
import os, sys, json
import numpy as np
sys.argv = [sys.argv[0]]
import estructura_seccion as SEC
import polares_geom as PG
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
C, LB = 0.045, 0.206
ab = SEC.seccion('B', 0.0)
bv = SEC.seccion('B', 0.002)
out = dict(abierta_B=dict(GJ=float(ab['GJ']), EI_flap=float(ab['EI_flap']), m_pala_g=float(ab['m'] * LB * 1e3)),
           abierta_BV=dict(GJ=float(bv['GJ']), EI_flap=float(bv['EI_flap']), m_pala_g=float(bv['m'] * LB * 1e3)))
Em, Gm, areal0, t0 = ab['Em'], ab['Gm'], ab['areal'], ab['t']
for tt in (0.08, 0.115):
    X, Y = PG.arco_naca(0.07, tt, n=400)
    x, z = X * C, Y * C
    ds = np.hypot(np.diff(x), np.diff(z)); zm = 0.5 * (z[1:] + z[:-1])
    p = ds.sum(); Am = 0.5 * abs(np.sum(x[:-1] * z[1:] - x[1:] * z[:-1])); zc = (zm * ds).sum() / p
    for esp in (0.5e-3, 0.25e-3):
        k = esp / t0                       # el mismo apilado a escala (aproximación)
        EI = Em * k * t0 * ((zm - zc)**2 * ds).sum()
        GJ = 4 * Am**2 * Gm * k * t0 / p
        m = areal0 * k * p + Am * 32.0
        out['cerrada_t%g_piel%g' % (tt * 100, esp * 1e3)] = dict(t=tt, piel_mm=esp * 1e3, GJ=float(GJ), EI_flap=float(EI),
                                                                  m_pala_g=float(m * LB * 1e3), perimetro_mm=float(p * 1e3), Am_mm2=float(Am * 1e6))
json.dump(out, open(os.path.join(D, 'v2_pala_cerrada.json'), 'w'), indent=1)
for k, v in out.items():
    print(k, {a: round(b, 4) for a, b in v.items()})
