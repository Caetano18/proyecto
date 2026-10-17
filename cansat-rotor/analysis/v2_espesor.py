#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Efecto del espesor del perfil (placa curvada al 7 %, espesor 1,5 a 11,5 % de la cuerda) en la caída y las rpm del
rotor solo (R = 0,25 m), con XFOIL a Re = 50 000 y 75 000 y la BEMT del capítulo 12. Para un contenedor propio que deja
espesor al perfil (capítulo de arquitectura). Entradas: polares_<perfil>_Re{50,75}.dat (polares_xfoil.py).
Salida: analysis/data/v2_espesor.dat y v2_espesor.json. Uso: python3 analysis/v2_espesor.py"""
import os, sys, json
import numpy as np
sys.argv = [sys.argv[0]]
import bemt_modelo as bm
import polares_post as pp
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
PERF = [('placa7', 1.55), ('placa7_t20', 2.07), ('placa7_t50', 5.14), ('placa7_t80', 8.17), ('placa7_t115', 11.71), ('arco7_n80', 8.05)]
RES = (50, 75)
filas, js = [], {}
for p, t in PERF:
    for r in RES:
        if not os.path.exists(os.path.join(D, 'polares_ext_%s_Re%d.dat' % (p, r))):
            if pp.cargar(p, r) is None:
                print('falta', p, r); break
            pp.extendida(p, r)
    pol = bm.Polar(['polares_ext_%s_Re%d.dat' % (p, r) for r in RES], [r * 1e3 for r in RES])
    rot = bm.Rotor(polar=pol, theta=-3.0)
    res = {}
    for nombre, m2 in (('A1', 0.49), ('A2', 0.36)):
        bm.W = m2 * bm.G
        e = bm.equilibrio(rot, drogue=False)
        res[nombre] = None if e is None else dict(V=e['V'], rpm=e['rpm'], T=e['T'], CR=e['CR'], Vvh=e['Vvh'], dQ=e['dQdOm'])
    bm.W = bm.cfg.M2 * bm.G
    js[p] = dict(t=t, **res)
    a1, a2 = res['A1'], res['A2']
    filas.append((t, a1['V'], a1['rpm'], a1['CR'], a2['V'], a2['rpm']) if a1 and a2 else (t,) + (float('nan'),) * 5)
    print('%-12s t=%5.2f %%  A1: V=%.3f rpm=%.0f CR=%.3f | A2: V=%.3f rpm=%.0f' % ((p, t) + filas[-1][1:]))
with open(os.path.join(D, 'v2_espesor.dat'), 'w') as f:
    f.write('t V1 rpm1 CR1 V2 rpm2\n')
    for r in filas:
        f.write(' '.join('%.4f' % x for x in r) + '\n')
json.dump(js, open(os.path.join(D, 'v2_espesor.json'), 'w'), indent=1)
