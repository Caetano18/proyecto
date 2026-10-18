#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Geometría de plegado (Arq. 1), espacio anular (Arq. 2) y separación del contenedor (Arq. 2).
Salida: analysis/data/v2_geom_*.dat, v2_sabot.dat, v2_geom_resumen.json
Uso: python3 analysis/v2_geometria.py"""
import os, json
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
G, RHO = 9.81, 1.225
res = {}


def guardar(n, cab, filas):
    with open(os.path.join(D, n), 'w') as f:
        f.write(' '.join(cab) + '\n')
        for r in filas:
            f.write(' '.join('%.5g' % x for x in r) + '\n')


def flecha(c, p=0.07):
    return p * c


def r_borde(rho, c, t, p=0.07):
    """radio exterior del borde de una pala de cuerda c, flecha p*c, espesor t, apoyada por el centro sobre un
    cilindro de radio rho (cara cóncava hacia el cilindro). Longitudes en mm."""
    s = flecha(c, p)
    return np.sqrt((rho - s + t) ** 2 + (c / 2) ** 2)


# 1. radio del borde frente al radio del cuerpo (Arq. 1)
filas = []
for rho in np.arange(36, 44.01, 0.5):
    filas.append([rho] + [r_borde(rho, c, 0.5) for c in (40, 45, 50)])
guardar('v2_geom_env.dat', ['rho', 'c40', 'c45', 'c50'], filas)
res['rho_max_env45_c45'] = float(max(r for r in np.arange(30, 46, 0.01) if r_borde(r, 45, 0.5) <= 45.0))
res['r_borde_rho405_c45'] = float(r_borde(40.5, 45, 0.5))
res['rho_max_c40'] = float(max(r for r in np.arange(30, 46, 0.01) if r_borde(r, 40, 0.5) <= 45.0))
res['rho_max_c50'] = float(max(r for r in np.arange(30, 46, 0.01) if r_borde(r, 50, 0.5) <= 45.0))

# 2. espesor máximo de perfil en el espacio anular (Arq. 2): contenedor de radio interior Ri
filas = []
for rho in np.arange(30, 41.01, 0.5):
    row = [rho]
    for Ri in (44.2, 44.5):
        for c in (40, 45, 50):
            s = flecha(c)
            lim = Ri ** 2 - (c / 2) ** 2
            tmax = np.sqrt(lim) - (rho - s) if lim > 0 else 0.0
            row.append(max(tmax, 0.0))
    filas.append(row)
guardar('v2_geom_anillo.dat', ['rho', 't_c40_w08', 't_c45_w08', 't_c50_w08', 't_c40_w05', 't_c45_w05', 't_c50_w05'], filas)
res['tmax_rho36_c45_w08'] = float(np.sqrt(44.2 ** 2 - 22.5 ** 2) - (36 - 3.15))
res['tmax_rho38_c45_w08'] = float(np.sqrt(44.2 ** 2 - 22.5 ** 2) - (38 - 3.15))
res['tmax_rho34_c45_w08'] = float(np.sqrt(44.2 ** 2 - 22.5 ** 2) - (34 - 3.15))

# 3. separación del contenedor (sabot) tras soltar el pestillo
def sabot(mc=0.148, mp=0.352, Lc=0.23, V0=13.44, Cdc=0.8, Dcont=0.090, Cdd=0.8, Dd=0.25, dt=1e-4, rail_mu=0.1):
    kd = 0.5 * RHO * Cdd * np.pi * Dd ** 2 / 4
    kb = 0.5 * RHO * 0.8 * np.pi * Dcont ** 2 / 4
    vc = vp = V0
    z = 0.0                  # desplazamiento relativo del payload hacia abajo respecto del contenedor
    t = 0.0
    H = []
    while z < Lc and t < 1.0:
        ac = G - (kd * vc ** 2 + 0.5 * kb * vc ** 2) / mc            # contenedor: arrastre del drogue y de su propio tubo
        ap = G - kb * vp ** 2 / mp
        vc += ac * dt; vp += ap * dt
        z += (vp - vc) * dt
        t += dt
        H.append((t, vc, vp, z))
    return np.array(H)

H = sabot()
guardar('v2_sabot.dat', ['t', 'vc', 'vp', 'z'], H[::20])
res['sabot'] = dict(t_salida=float(H[-1, 0]), vc=float(H[-1, 1]), vp=float(H[-1, 2]), z=float(H[-1, 3]))
# sensibilidad al masa del contenedor
res['sabot_mc'] = {str(mc): float(sabot(mc=mc, mp=0.5 - mc)[-1, 0]) for mc in (0.10, 0.148, 0.178, 0.25)}
res['sabot_Lc'] = {str(L): float(sabot(Lc=L)[-1, 0]) for L in (0.21, 0.23, 0.25)}
# 4. dispositivo de liberación del drogue (Arq. 1): pasador Ø3, brazo, par
Td = 0.5 * RHO * 0.8 * np.pi * 0.25 ** 2 / 4 * 13.44 ** 2   # tensión del drogue a V1 (N)
for fapert, lab in ((1.0, 'estacionaria'), (23.0 / Td, 'apertura a 25 m/s')):
    for mu in (0.2, 0.4):
        F = Td * fapert
        Fr = mu * F                    # fuerza de extracción del pasador (lazo sobre pasador, carga normal F)
        par = Fr * 12e-3               # brazo del horn del servo 12 mm
        res['pin_%s_mu%.1f' % (lab.replace(' ', '_'), mu)] = dict(F=float(F), Fr=float(Fr), par_mNm=float(par * 1e3), margen_SG90=float(0.18 / par))
res['Td_V1'] = float(Td)
json.dump(res, open(os.path.join(D, 'v2_geom_resumen.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
