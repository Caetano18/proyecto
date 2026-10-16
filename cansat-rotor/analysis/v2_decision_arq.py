#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Matriz de decisión Arquitectura 1 frente a Arquitectura 2, con sensibilidad a los pesos.
Salida: analysis/data/v2_decision.json y v2_decision_w.dat. Uso: python3 analysis/v2_decision_arq.py"""
import os, json
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
crit = ['C4 con margen', 'Riesgo normativo (consulta)', 'Complejidad mecánica', 'Masa y energía de aterrizaje',
        'Robustez ante falla de liberación', 'Fabricabilidad y costo', 'Integración con antenas', 'Validación y ensayos']
w0 = np.array([0.25, 0.15, 0.10, 0.10, 0.15, 0.10, 0.05, 0.10])
A1 = np.array([3, 5, 3, 2, 4, 3, 4, 3], float)
A2 = np.array([5, 2, 4, 5, 3, 4, 3, 3], float)
res = dict(crit=crit, w0=w0.tolist(), A1=A1.tolist(), A2=A2.tolist(), S1=float(w0 @ A1), S2=float(w0 @ A2))
rng = np.random.default_rng(7)
# pesos de Dirichlet centrados en w0 (concentración 20)
W = rng.dirichlet(w0 * 20, 100000)
d = W @ (A2 - A1)
res['P_A2_mejor'] = float(np.mean(d > 0))
# pesos totalmente al azar
W2 = rng.dirichlet(np.ones(8), 100000)
res['P_A2_mejor_uniforme'] = float(np.mean(W2 @ (A2 - A1) > 0))
# peso del riesgo normativo para el que empatan, repartiendo el resto proporcionalmente
filas = []
for wn in np.linspace(0, 0.8, 41):
    w = w0 * (1 - wn) / (1 - w0[1]); w[1] = wn
    filas.append((wn, float(w @ A1), float(w @ A2)))
with open(os.path.join(D, 'v2_decision_w.dat'), 'w') as f:
    f.write('wn S1 S2\n')
    for r in filas: f.write('%.3f %.4f %.4f\n' % r)
emp = [r[0] for r in filas if r[2] <= r[1]]
res['w_norm_empate'] = float(emp[0]) if emp else None
# efecto de cada criterio: cuánto cambia la diferencia al subir un 50 % el peso
base = w0 @ (A2 - A1)
res['dif_base'] = float(base)
res['efecto_peso'] = {c: float(((w0 + 0.5 * w0[i] * (np.arange(8) == i)) / (1 + 0.5 * w0[i])) @ (A2 - A1) - base) for i, c in enumerate(crit)}
json.dump(res, open(os.path.join(D, 'v2_decision.json'), 'w'), indent=1)
print(json.dumps(res, indent=1, ensure_ascii=False))
