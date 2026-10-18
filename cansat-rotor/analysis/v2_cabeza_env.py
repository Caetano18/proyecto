#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cabeza del rotor dentro de la envolvente de Ø90: el pasador de Ø3 de la bisagra a e del eje y la oreja con
borde e_o >= 3 mm dejan la oreja en r = e + e_o. Con e = 44 mm queda en r = 47 a 48 mm (Ø94 a 96), fuera de Ø90;
para cerrar hace falta e + e_o <= 45 mm. Se mide con la BEMT (solo cambian las entradas e y el largo de pala R - e)
cuánto cuesta bajar la bisagra. Salida: analysis/data/v2_cabeza_env.json y .dat. Uso: python3 analysis/v2_cabeza_env.py"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bemt_modelo as b
from bemt_modelo import Rotor, equilibrio
D = b.DATA
G = b.G
filas, res = [], []
for m in (0.49, 0.36):
    b.W, b.M = m * G, m
    for e in (0.044, 0.042, 0.041, 0.040):
        rot = Rotor(B=4, c=0.045, theta=-3.0, R=0.25, e=e)
        q = equilibrio(rot, drogue=False, Vlo=2.0, Vhi=16.0)
        filas.append((m, e * 1e3, (0.25 - e) * 1e3, q['V'], q['rpm'], q['T'], q['CR']))
        res.append(dict(m2=m, e_mm=e * 1e3, Lb_mm=(0.25 - e) * 1e3, V2=float(q['V']), rpm=float(q['rpm']), T=float(q['T']), CR=float(q['CR'])))
        print('m2=%.2f e=%.0f mm  Lb=%.0f mm  V2=%.3f m/s  rpm=%.0f  CR=%.3f' % (m, e * 1e3, (0.25 - e) * 1e3, q['V'], q['rpm'], q['CR']))
with open(os.path.join(D, 'v2_cabeza_env.dat'), 'w') as f:
    f.write('m2 e Lb V2 rpm T CR\n')
    for r in filas:
        f.write(' '.join('%.6g' % x for x in r) + '\n')
json.dump(res, open(os.path.join(D, 'v2_cabeza_env.json'), 'w'), indent=1)
