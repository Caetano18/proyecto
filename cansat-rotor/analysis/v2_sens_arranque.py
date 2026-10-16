#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sensibilidad del arranque (t90 y z90) a los parámetros del rotor y del entorno. Config v2.
Salida: analysis/data/sens_tornado_t90.dat, sens_tornado_z90.dat, sens_arranque.json
Uso: python3 analysis/v2_sens_arranque.py"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bemt_modelo as b
import arranque_estudios as A

DATA = b.DATA
fn = os.path.join(DATA, 'arranque_tab3_v2.npy')
if os.path.exists(fn):
    tab3 = np.load(fn)
else:
    tab3 = np.array([A.tabla(b.Rotor(theta=th)) for th in A.THT])
    np.save(fn, tab3)
M3 = A.Mapa(tab3=tab3)
M2d = A.Mapa(tab2=A.tabla(b.Rotor(theta=A.TH_REG, polar=b.polar_2d())))
fix = lambda th: (lambda o, beta: th)


def corre(**kw):
    r = A.sim(kw.pop('mp', M3), tmax=8.0, **kw)
    return r['t90'], r['z90']


base = corre()
res = dict(base=base)
casos = []


def caso(nombre, lo, hi):
    casos.append((nombre, lo, hi))


# parámetros: (nombre, función que devuelve (t90,z90) en el valor bajo y alto)
def con_inercia(f):
    sv = (A.IHUB, A.IB, A.MB, A.SB)
    A.IHUB, A.IB, A.MB, A.SB = [x * f for x in sv]
    try:
        return corre()
    finally:
        A.IHUB, A.IB, A.MB, A.SB = sv


def con_cdc(c):
    sv = A.CDC
    A.CDC = c
    try:
        return corre()
    finally:
        A.CDC = sv


filas = {
    'theta (-2 a -4 deg)': (corre(th_fun=fix(-2.0)), corre(th_fun=fix(-4.0))),
    'rozamiento Qf (1,7 a 0,34 mN m)': (corre(qf=1.7e-3), corre(qf=0.34e-3)),
    'V al abrir (10 a 16 m/s)': (corre(V0=10.0), corre(V0=16.0)),
    'inercia del rotor (+30 a -30 %)': (con_inercia(1.3), con_inercia(0.7)),
    'polar en perdida (XFOIL a 2D)': (base, corre(mp=M2d)),
    'masa m2 (0,49 a 0,36 kg)': (base, corre(m=0.36)),
    'arrastre de apertura Cdc (1,2 a 2,0)': (con_cdc(1.2), con_cdc(2.0)),
}
res['filas'] = {k: dict(lo=v[0], hi=v[1]) for k, v in filas.items()}
etq = {'theta (-2 a -4 deg)': 'theta', 'rozamiento Qf (1,7 a 0,34 mN m)': 'Qf', 'V al abrir (10 a 16 m/s)': 'V0',
       'inercia del rotor (+30 a -30 %)': 'Iz', 'polar en perdida (XFOIL a 2D)': 'polar', 'masa m2 (0,49 a 0,36 kg)': 'm2',
       'arrastre de apertura Cdc (1,2 a 2,0)': 'Cdc'}
with open(os.path.join(DATA, 'sens_tornado_t90.dat'), 'w') as f:
    f.write('param t_lo t_hi\n')
    for k, (lo, hi) in filas.items():
        f.write('%s %.4f %.4f\n' % (etq[k], lo[0], hi[0]))
with open(os.path.join(DATA, 'sens_tornado_z90.dat'), 'w') as f:
    f.write('param z_lo z_hi\n')
    for k, (lo, hi) in filas.items():
        f.write('%s %.3f %.3f\n' % (etq[k], lo[1], hi[1]))
json.dump(res, open(os.path.join(DATA, 'sens_arranque.json'), 'w'), indent=1)
print('base', base)
for k, (lo, hi) in filas.items():
    print('%-40s t90 %.2f -> %.2f   z90 %.1f -> %.1f' % (k, lo[0], hi[0], lo[1], hi[1]))
