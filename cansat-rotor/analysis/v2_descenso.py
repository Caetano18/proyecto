#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuración v2: mapa V2(R, m2), promedio global de C4, caída libre al soltar el drogue,
presupuesto de tiempo y Monte Carlo de cumplimiento de C3/C4.
Altura: CANSAT_HLIB = altura de liberación del rotor [m] (por defecto 500); el apogeo de diseño es
H_lib/0,8 (625 m), porque C4 libera al 80 % de la altitud máxima. Con el valor por defecto se
regeneran los archivos que lee el documento. Con otro valor (p. ej. CANSAT_HLIB=400, lectura
alternativa de apogeo 500 m) solo se rehace lo que depende de la altura (tiempos y Monte Carlo) y las
salidas llevan el sufijo _H<H_lib>: no pisan las del caso base.
Salida: analysis/data/v2_*.dat y v2_resumen.json.   Uso: python3 analysis/v2_descenso.py
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bemt_modelo as b
from bemt_modelo import Rotor, equilibrio
from multiprocessing import Pool

DATA = b.DATA
G, RHO = b.G, b.RHO
V1 = b.V_ETAPA1
res = {}

HLIB = float(os.environ.get('CANSAT_HLIB', '500'))      # altura de liberación del rotor [m]
F_LIB = 0.8                                             # C4: se libera al 80 % de la altitud máxima
H_APO = HLIB / F_LIB                                    # apogeo de diseño [m]
SUF = '' if HLIB == 500.0 else '_H%g' % HLIB            # sufijo de las salidas del caso alternativo


def guardar(nombre, cab, filas, fmt='%.6g'):
    with open(os.path.join(DATA, 'v2_' + nombre + SUF + '.dat'), 'w') as f:
        f.write(' '.join(cab) + '\n')
        for fila in filas:
            f.write(' '.join('nan' if (isinstance(x, float) and np.isnan(x)) else fmt % x for x in fila) + '\n')


def prom(V1_, V2_, fr=0.2):
    """Velocidad media global: fracción fr de la altura a V1 y el resto a V2."""
    return 1.0 / (fr / V1_ + (1 - fr) / V2_)


# ---------------------------------------------------------------- 1. mapa V2(R, m2) con la BEMT
def _eq(a):
    R, m = a
    b.W, b.M = m * G, m
    rot = Rotor(B=4, c=0.045, theta=-3.0, R=R, e=b.E)
    e = equilibrio(rot, drogue=False, Vlo=2.0, Vhi=16.0)
    return (R, m, e['V'], e['rpm'], e['T'], e['CR'], e['Vvh'])


def mapa():
    Rs = (0.20, 0.23, 0.25)
    ms = (0.30, 0.33, 0.36, 0.39, 0.43, 0.49, 0.51)
    with Pool(3) as p:
        out = p.map(_eq, [(R, m) for R in Rs for m in ms])
    filas = []
    for R, m, V, rpm, T, CR, Vvh in out:
        filas.append((R, m, V, rpm, T, CR, Vvh, prom(V1, V), 0.5 * m * V**2, 0.5 * m * V**2 / (m * G)))
    guardar('mapa', ['R', 'm2', 'V2', 'rpm', 'T', 'CR', 'Vvh', 'Vglobal', 'E_imp', 'h_eq'], filas)
    # tabla ancha para pgfplots
    cab = ['m2'] + ['V_R%d' % round(R * 100) for R in Rs] + ['Vg_R%d' % round(R * 100) for R in Rs]
    f2 = []
    for m in ms:
        f = [m]
        for R in Rs:
            f.append([x for x in filas if x[0] == R and abs(x[1] - m) < 1e-9][0][2])
        for R in Rs:
            f.append([x for x in filas if x[0] == R and abs(x[1] - m) < 1e-9][0][7])
        f2.append(f)
    guardar('mapa_ancho', cab, f2)
    res['mapa'] = [dict(R=x[0], m2=x[1], V2=x[2], rpm=x[3], T=x[4], CR=x[5], Vvh=x[6], Vg=x[7], E=x[8]) for x in filas]
    b.W, b.M = b.cfg.M2 * G, b.cfg.M2
    return filas


# ---------------------------------------------------------------- 2. promedio global y presupuesto de tiempo
def promedio():
    # <V> frente a V2 para varios V1 (el 20 % inicial a V1)
    V2s = np.linspace(4.0, 9.0, 51)
    filas = [(v2, prom(12.0, v2), prom(13.44, v2), prom(15.0, v2), prom(18.0, v2)) for v2 in V2s]
    guardar('promedio', ['V2', 'Vg_V12', 'Vg_V134', 'Vg_V15', 'Vg_V18'], filas)
    # V2 máxima admisible para que el promedio global sea <= 8 m/s
    for V1_ in (12.0, 13.44, 15.0, 18.0):
        res['V2max_global_V1_%g' % V1_] = 0.8 / (1 / 8.0 - 0.2 / V1_)


def tiempos():
    """Tiempos de descenso en régimen (sin transitorios) según la altura de liberación H_lib: la adoptada
    (CANSAT_HLIB), 400 m (lectura alternativa: apogeo de 500 m) y 800 m (apogeo de 1000 m)."""
    res['altura'] = dict(H_lib=HLIB, H_apo=H_APO)
    filas = []
    for hl in sorted({400.0, 500.0, 800.0, HLIB}):
        H = hl / F_LIB                                   # apogeo
        for V2_ in (5.47, 6.36):
            t1 = 0.2 * H / V1; t2 = 0.8 * H / V2_
            filas.append((H, V2_, 0.8 * H, t1, t2, t1 + t2, H / (t1 + t2)))
    guardar('tiempos', ['H', 'V2', 'hlib', 't1', 't2', 'ttot', 'Vprom'], filas)


# ---------------------------------------------------------------- 3. caída libre al soltar el drogue
def caida_libre(m, V0=V1, dt=0.002, tmax=1.5, Cd=0.8, D=0.090):
    k = 0.5 * RHO * Cd * np.pi * D**2 / 4
    v, z, t = V0, 0.0, 0.0
    H = []
    while t < tmax:
        v += (G - k * v * v / m) * dt
        z += v * dt
        t += dt
        H.append((t, v, z))
    return np.array(H)


def libre():
    A = caida_libre(0.49); B_ = caida_libre(0.36)
    n = len(A)
    guardar('caidalibre', ['t', 'v_m049', 'z_m049', 'v_m036', 'z_m036'],
            [(A[i, 0], A[i, 1], A[i, 2], B_[i, 1], B_[i, 2]) for i in range(0, n, 5)])
    for dt_ in (0.1, 0.2, 0.3, 0.5, 1.0):
        i = int(round(dt_ / 0.002)) - 1
        res['libre_%g' % dt_] = dict(v049=float(A[i, 1]), z049=float(A[i, 2]), v036=float(B_[i, 1]), z036=float(B_[i, 2]),
                                    dv049=float(A[i, 1] - V1), dv036=float(B_[i, 1] - V1))
    res['Vterminal_cuerpo_049'] = float(np.sqrt(2 * 0.49 * G / (RHO * 0.8 * np.pi * 0.09**2 / 4)))
    res['Vterminal_cuerpo_036'] = float(np.sqrt(2 * 0.36 * G / (RHO * 0.8 * np.pi * 0.09**2 / 4)))


# ---------------------------------------------------------------- 4. Monte Carlo
def mc_calc(H_apo, n=200_000, seed=20261016, hist=None):
    """Monte Carlo de C3/C4 con el apogeo fijo en H_apo [m]. Devuelve (resultados por caso, filas de v2_mc).
    Si hist es un dict, guarda en él los histogramas de V2 y <V> de los casos que se grafican."""
    rng = np.random.default_rng(seed)
    filas = []
    resmc = {}
    for nombre, mu_m, sd_m, R in (('A1_R25', 0.490, 0.006, 0.25), ('A1_R23', 0.490, 0.006, 0.23), ('A1_R20', 0.490, 0.006, 0.20),
                                  ('A2_R25', 0.360, 0.015, 0.25), ('A2_R23', 0.360, 0.015, 0.23), ('A2_R20', 0.360, 0.015, 0.20)):
        m2 = rng.normal(mu_m, sd_m, n)
        m1 = rng.uniform(0.490, 0.510, n)                    # masa de pesaje S1
        T = rng.uniform(278.15, 308.15, n)                   # 5 a 35 grados C
        h_sitio = rng.uniform(0.0, 800.0, n)                 # altitud del sitio sobre el mar
        P = 101325.0 * (1 - 2.25577e-5 * h_sitio)**5.25588
        rho = P / (287.05 * T)
        cdd = rng.uniform(0.75, 0.90, n)
        # C_R de la BEMT con incertidumbre (+-15 % en V2 equivale a ~ +-30 % en C_R ... se usa sd relativa 12 %)
        CR0 = {0.25: 0.963, 0.23: 0.966, 0.20: 0.973}[R]
        CR = CR0 * rng.normal(1.0, 0.12, n)
        Ad = np.pi * 0.125**2; Ac = np.pi * 0.045**2; AR = np.pi * R**2
        V1_ = np.sqrt(m1 * G / (0.5 * rho * (cdd * Ad + 0.8 * Ac)))
        V2_ = np.sqrt(m2 * G / (0.5 * rho * (CR * AR + 0.8 * Ac)))
        # tiempo de transición de V1 a V2 tras la liberación: 2,5 a 5 s a la velocidad media (V1+V2)/2 (la simulación
        # del cap. de arranque deja V a menos del 2 % de V2 en 2,6 s; el t90 = 1,55 s de ese capítulo es el giro del rotor)
        ts = rng.uniform(2.5, 5.0, n)
        _ = rng.uniform(500.0, 1000.0, n)                    # sorteo original del apogeo: se descarta, pero se hace la
        H = np.full(n, float(H_apo))                         # llamada para no desplazar la secuencia de los casos siguientes
        hr = 0.8 * H
        Vs = 0.5 * (V1_ + V2_)
        t1 = 0.2 * H / V1_
        t2 = ts + (hr - Vs * ts) / V2_
        Vg = H / (t1 + t2)
        # lectura (i): V2 de régimen; lectura (ii): promedio global
        p_c3 = np.mean((V1_ >= 12.0) & (V1_ <= 18.0))
        p_i = np.mean((V2_ >= 2.0) & (V2_ <= 8.0))
        p_ii = np.mean((Vg >= 2.0) & (Vg <= 8.0))
        resmc[nombre] = dict(R=R, V1_mu=float(V1_.mean()), V1_sd=float(V1_.std()), V2_mu=float(V2_.mean()), V2_sd=float(V2_.std()),
                             V2_p95=float(np.percentile(V2_, 95)), V2_p99=float(np.percentile(V2_, 99.5)),
                             Vg_mu=float(Vg.mean()), Vg_p95=float(np.percentile(Vg, 95)), Vg_p99=float(np.percentile(Vg, 99.5)),
                             P_C3=float(p_c3), P_C4_regimen=float(p_i), P_C4_global=float(p_ii),
                             Eimp_mu=float((0.5 * m2 * V2_**2).mean()), Eimp_p95=float(np.percentile(0.5 * m2 * V2_**2, 95)))
        filas.append((R, mu_m, resmc[nombre]['V2_mu'], resmc[nombre]['V2_p95'], resmc[nombre]['Vg_mu'], resmc[nombre]['Vg_p95'],
                      1 - p_i, 1 - p_ii))
        if hist is not None and nombre in ('A1_R25', 'A2_R25', 'A2_R20'):
            h, ed = np.histogram(V2_, bins=np.arange(3.0, 10.01, 0.1), density=True)
            hg, _ = np.histogram(Vg, bins=np.arange(3.0, 10.01, 0.1), density=True)
            hist[nombre] = [(0.5 * (ed[i] + ed[i + 1]), h[i], hg[i]) for i in range(len(h))]
    return resmc, filas


def mc(n=200_000, seed=20261016):
    """Monte Carlo con el apogeo de diseño H_APO = H_lib/0,8 (625 m por defecto)."""
    hist = {}
    resmc, filas = mc_calc(H_APO, n, seed, hist)
    for nombre, f in hist.items():
        guardar('hist_' + nombre, ['V', 'pdf_V2', 'pdf_Vg'], f)
    guardar('mc', ['R', 'm2', 'V2mu', 'V2p95', 'Vgmu', 'Vgp95', 'Pfalla_regimen', 'Pfalla_global'], filas)
    res['mc'] = resmc


if __name__ == '__main__':
    if not SUF:                       # lo que no depende de la altura se rehace solo en el caso base
        mapa(); promedio(); libre()
    tiempos(); mc()
    json.dump(res, open(os.path.join(DATA, 'v2_resumen' + SUF + '.json'), 'w'), indent=1)
    for k, v in res.items():
        if k != 'mapa':
            print(k, json.dumps(v)[:600])
