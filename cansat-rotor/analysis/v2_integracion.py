#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integración de la Arquitectura 1: aletas antigiro en el tramo inferior, volumen de la copa del drogue y presupuesto de masa
con los cambios de electrónica (capítulo de sensores), las aletas y la masa corregida de la cabeza del rotor.
Salida: analysis/data/v2_integracion.json. Uso: python3 analysis/v2_integracion.py"""
import os, json, math
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
rng = np.random.default_rng(20261018)
RHO, V = 1.225, 6.36
res = {}

# ---------------------------------------------------------------- A. aletas: 40 x 40 (capítulo 14) contra 40 de envergadura x 25 de cuerda
def aleta(s, l, Rc=0.045, n=4, Mf=0.65e-3):
    A = 2 * s / l
    af = 2 * math.pi * A / (2 + math.sqrt(A * A + 4))
    S = s * l; rf = Rc + s / 2
    c = n * 0.5 * RHO * V * af * S * rf**2                 # amortiguamiento [N m s]
    Md = n * 0.5 * RHO * V**2 * af * S * rf                 # par por radián de calaje [N m/rad]
    return dict(s_mm=s * 1e3, l_mm=l * 1e3, AR=A, af=af, S_mm2=S * 1e6, c=c, w_sin_calaje=Mf / c, calaje_deg=math.degrees(Mf / Md))
res['aletas'] = {'40x40': aleta(0.040, 0.040), '40x25': aleta(0.040, 0.025), '50x25': aleta(0.050, 0.025)}
res['aletas_masa_g'] = dict(placa=0.040 * 0.025 * 0.5e-3 * 1550 * 1e3, por_aleta=1.6, total=4 * 1.6 + 0.4)

# ---------------------------------------------------------------- B. volumen de la copa aplanada del drogue (Ø75 x 10 mm)
cup_total = math.pi / 4 * 7.5**2 * 1.0
cup_util = math.pi / 4 * 7.2**2 * 0.9                      # paredes de 1,5 mm y fondo de 1 mm
tela = math.pi * 0.125**2 * 1.3 * 40.0                       # g: ripstop de 40 g/m2 con costuras (+30 %)
vol_tela = (tela + 8 * 0.25 * 0.6) / 0.35                    # empaquetado a 0,35 g/cm3
vol_destorcedor, vol_carro = 3.0, 8.0
res['copa'] = dict(vol_total_cm3=cup_total, vol_util_cm3=cup_util, tela_g=tela, vol_tela_cm3=vol_tela,
                   vol_destorcedor_cm3=vol_destorcedor, vol_carro_cm3=vol_carro,
                   llenado=(vol_tela + vol_destorcedor + vol_carro) / cup_util)

# ---------------------------------------------------------------- C. presupuesto de masa (Arq. 1 y 2) con los cambios
def mc(items, N=200000, pesaje=(490.0, 510.0)):
    mu = np.array([i[1] for i in items]); sd = np.array([i[2] for i in items])
    X = rng.normal(mu, sd, (N, len(items)))
    sin = X.sum(axis=1)
    pes = rng.uniform(*pesaje, N)
    lastre = pes - sin
    return dict(sin_lastre_mu=float(sin.mean()), sin_lastre_sd=float(sin.std()), lastre_mu=float(lastre.mean()),
                lastre_p5=float(np.percentile(lastre, 5)), lastre_p95=float(np.percentile(lastre, 95)),
                P_sobrepeso=float(np.mean(lastre < 0)), P_lastre_menor_10=float(np.mean(lastre < 10)))
def a1(panel=(37.0, 15.0), extra=(), nuevos=True):
    it = [('Electrónica de la planilla, sin panel', 140.0, 6.0), ('Panel solar', *panel), ('Palas (4 de 206 mm con portapala)', 38.0, 3.0),
          ('Cubo, eje, rodamientos, tope y resortes', 26.0, 2.5), ('Cableado, tornillos, insertos y placas', 37.0, 7.0),
          ('Anillo amortiguador de aterrizaje', 8.0, 1.0), ('Cuerpo PETG Ø81, pared 2 mm', 130.0, 8.0), ('Tapas y anillos internos', 25.0, 3.0),
          ('Traba (anillo y pestañas)', 8.0, 1.5), ('Copa y pasador del drogue', 8.0, 1.5), ('Drogue, cuerda y destorcedor', 10.0, 2.0)]
    if nuevos:
        it += [('Cambios de electrónica del capítulo de sensores', 16.0, 3.0), ('Corrección de la masa de la cabeza del rotor (71 g contra 64 g)', 7.0, 3.0),
               ('Aletas antigiro (4) con resortes y dientes de la traba', 7.0, 1.0)]
    return it + list(extra)
res['masa_A1'] = {
    'tabla_actual (sin cambios)': mc(a1(nuevos=False)),
    'con cambios, panel de la planilla (37 g)': mc(a1()),
    'con cambios, panel de 8 g (a pesar)': mc(a1(panel=(8.0, 2.0))),
    'con cambios y 2.a celda, panel de la planilla': mc(a1(extra=[('2.a celda 18650', 48.0, 1.0)])),
    'con cambios y 2.a celda, panel de 8 g': mc(a1(panel=(8.0, 2.0), extra=[('2.a celda 18650', 48.0, 1.0)])),
}
res['masa_A1_tabla'] = dict(subtotal_tabla=467.0, cambios_electronica=16.0, cabeza_rotor=7.0, aletas=7.0, subtotal_nuevo=467.0 + 16 + 7 + 7)
json.dump(res, open(os.path.join(D, 'v2_integracion.json'), 'w'), indent=1)
for k, v in res['aletas'].items(): print(k, {a: round(b, 4) for a, b in v.items()})
print('copa', {a: round(b, 3) for a, b in res['copa'].items()})
for k, v in res['masa_A1'].items(): print('%-48s sin lastre %.1f ± %.1f | lastre %.1f [%.1f, %.1f] P(sobrepeso)=%.3f P(<10 g)=%.3f' % ((k, v['sin_lastre_mu'], v['sin_lastre_sd'], v['lastre_mu'], v['lastre_p5'], v['lastre_p95'], v['P_sobrepeso'], v['P_lastre_menor_10'])))
