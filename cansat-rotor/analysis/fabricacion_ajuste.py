#!/usr/bin/env python3
"""Ajuste a presión del rodamiento 688ZZ en el cubo impreso (Lamé), efecto de la
temperatura y de la relajación; balanceo (ISO 21940-11) y detección con la IMU;
desarrollo plano de la pestaña de inoxidable.
Bisagra: pasador de Ø3 (antes Ø2) y desgarro de la oreja con la fuerza centrífuga del cap. 15.
Salida: analysis/data/fabricacion_ajuste.dat y resumen por stdout.
Propiedades de catálogo, no medidas (ver texto).

Configuración: variable de entorno CANSAT_CFG (igual que v2_config.py).
  v2 (por defecto): pala de 9,5 g y R = 0,25 m (régimen 1229 rpm = 128,7 rad/s y sobrepaso del
     arranque 1553 rpm = 162,6 rad/s, cap. 13), pala plegada con la cara cóncava sobre el
     cuerpo Ø81 (r = 40,5 mm) y pestaña con el extremo interior a r = 33,8 mm.
  v1: pala de 8,2 g, rotor de 120 a 162 rad/s, pala a r_mo = 44,62 mm y ala radial de 11,5 mm.
"""
import os
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
V1 = (os.environ.get('CANSAT_CFG', 'v2') == 'v1')

d, B = 16.0, 5.0             # asiento: diámetro y ancho del aro exterior [mm]
di = 13.6                    # diámetro interior aprox. del aro exterior (pista) [mm]
Es, nus = 210e3, 0.30        # acero [MPa]
mats = {'PETG': (2000., 0.38, 68e-6, 45.), 'PA12': (1400., 0.40, 90e-6, 40.)}
Dout = 30.0                  # diámetro exterior efectivo del anillo de cubo (conservador)
mu = 0.25
a_s = 11.5e-6

def press(delta, E, nu, Do=Dout):
    Kh = ((Do**2 + d**2)/(Do**2 - d**2) + nu)/E
    Ks = ((d**2 + di**2)/(d**2 - di**2) - nus)/Es
    p = delta/(d*(Kh + Ks))
    st = p*(Do**2 + d**2)/(Do**2 - d**2)
    F = mu*p*np.pi*d*B
    return p, st, F, Ks/(Kh+Ks)

dl = np.linspace(0, 0.15, 31)
rows = [dl]
for m, (E, nu, al, Su) in mats.items():
    p, st, F, fs = press(dl, E, nu)
    rows += [p, st, F]
np.savetxt(os.path.join(D, 'fabricacion_ajuste.dat'), np.array(rows).T, fmt='%.4f',
           header='delta p_petg s_petg F_petg p_pa s_pa F_pa', comments='')

for m, (E, nu, al, Su) in mats.items():
    for dd in (0.03, 0.05, 0.08):
        p, st, F, fs = press(dd, E, nu)
        print(f'{m} delta={dd:.2f}: p={p:.2f} MPa, sigma_t={st:.2f} MPa (FS {Su/st:.1f}), '
              f'F_ax={F:.0f} N, T={F*d/2/1000:.2f} N m, flex. acero {100*fs:.1f} %')
    for dT in (-20, +25):
        dlt = -(al - a_s)*d*dT
        print(f'  {m}: dT={dT:+d} K -> cambio de interferencia {dlt:+.4f} mm')
    # sensibilidad a Dout
    for Do in (24, 30, 44):
        print(f'  {m}: Dout={Do}: p(0,05)={press(0.05, E, nu, Do)[0]:.2f} MPa')

# ---- balanceo
M_PALA = 8.2 if V1 else 9.5      # g: pala terminada con portapala, pestaña y varilla
OMS = (120., 136., 162.) if V1 else (128.7, 162.6)    # rad/s
Mrot = 4*M_PALA + 12.0 + 3.0     # g: palas con varilla y pestaña, cubo, aros exteriores
print(f'Masa que gira M = {Mrot:.1f} g')
for Om in OMS:
    for G in (6.3, 16., 40.):
        U = 1000*G*Mrot/1000/Om*1000/1000   # g mm  (U = G M / Omega)
        U = G*Mrot/Om                         # [mm/s * g / (1/s)] = g mm
        print(f'Omega={Om:.0f}: G{G}: U_per={U:.1f} g mm = {U/120:.3f} g a 120 mm')
U01 = 0.1*120
for Om in OMS:
    print(f'0,1 g a 120 mm = {U01:.0f} g mm -> G = {U01*Om/Mrot:.1f} mm/s (Omega={Om:.0f}); '
          f'F = {U01*1e-6*Om**2:.3f} N')
# respuesta del cuerpo libre (0,5 kg) a 12 g mm
Mb, Ib, h = 0.5, 0.5*0.25**2/12, 0.10
for Om in OMS[:1]:
    F = U01*1e-6*Om**2
    print(f'cuerpo: x={1e3*F/(Mb*Om**2):.4f} mm, theta={np.degrees(F*h/(Ib*Om**2)):.4f} deg')
# detección con IMU en el banco (masa suspendida 0,5 kg), ruido 200 ug/sqrtHz, 10 s
Ures = 6.0
a = Ures*1e-6*OMS[0]**2/0.5
sig = 200e-6*9.81*np.sqrt(1/(2*10))
print(f'IMU: a(U=6 g mm)={a:.3f} m/s2 = {a/9.81*1e3:.1f} mg; ruido promediado 10 s = '
      f'{sig*1e3:.2f} mm/s2; SNR = {a/sig:.0f}')
# ---- pestaña de inoxidable: desarrollo plano
t, ri, K = 0.5, 0.5, 0.33
BA = np.pi/2*(ri + K*t)
# radio de la cara exterior de la pala en el centro de la cuerda, plegada: v1 44,62 (ranura
# del portapala); v2: la cara cóncava apoya en el cuerpo (r = 40,5) y la exterior queda a +t
r_mo = 44.62 if V1 else 40.5 + 0.5
r_out = round(r_mo + 0.5 + 0.2, 1)   # cara exterior del pliegue (pala + pestaña 0,5 + adhesivo ~0,2)
r_end = 33.8           # extremo interior del ala radial: 1,8 mm por fuera del anillo (R 32)
r_wire = 36.5
L1 = 6.0                                       # ala pegada (medida exterior)
L2 = 11.5 if V1 else round(r_out - r_end, 2)   # ala radial (medida exterior)
L_flat = (L1 - (ri + t)) + (L2 - (ri + t)) + BA
print(f'Pestaña: BA={BA:.3f} mm, BD={2*(ri+t)-BA:.3f} mm, L1={L1} mm, L2={L2} mm, '
      f'largo desarrollado={L_flat:.2f} mm')
print(f'Cara exterior del pliegue a r={r_out} mm (pala r_mo={r_mo:.2f})')
x_oj = r_out - r_wire  # centro del ojal desde la cara exterior del pliegue
print(f'Ojal: a {x_oj:.2f} mm de la cara exterior; a {L2-x_oj:.2f} mm del extremo; '
      f'en el desarrollo a {L_flat-(L2-x_oj):.2f} mm del extremo pegado; '
      f'extremo interior a r={r_out-L2:.2f} mm')
print(f'Borde entre ojal (1,70) y extremo: {L2 - x_oj - 0.85:.2f} mm (3t = {3*t:.1f} mm)')
# pegado de la pestaña: 5 x 5 mm, corte admisible conservador 5 MPa
A = 5*5; print(f'Pegado: area {A} mm2, capacidad a 5 MPa = {5*A:.0f} N')

# ---- bisagra: pasador y oreja (cap. 15)
# Fuerza centrífuga por pala en la bisagra: 18,9 N a régimen, 30,2 N en el sobrepaso del arranque
# (cap. 15, estructura_cargas.py). Oreja: espesor total 3 + 2 = 5 mm, desgarro en 2 planos de
# largo e - d/2; admisible en corte entre capas 12 MPa (cap. 15). Pasador de acero: doble corte,
# 200 MPa en corte. Pasador m6 de 1 a 3 mm: +0,002/+0,008 mm (ISO 286-2, banda que incluye Ø3).
Fc, t_or, tau_or, tau_pin, rho_st = 30.2, 5.0, 12.0, 200.0, 7.85e-3
print('Bisagra: desgarro de la oreja con la centrífuga del sobrepaso (30,2 N)')
for dp, ee in ((2, 1.3), (2, 3.0), (3, 3.0), (3, 3.5), (3, 4.0)):
    lig = ee - dp/2
    tau = Fc/(2*t_or*lig)
    tau_c = Fc/(2*(t_or - 1.2)*lig)       # descontando la cajera de 1,2 mm de la oreja ancha
    print(f'  pasador Ø{dp}, e={ee:.1f}: ligamento {lig:.2f} mm, tau={tau:.2f} MPa, FS {tau_or/tau:.1f}; '
          f'con cajera (3,8 mm resistentes) tau={tau_c:.2f}, FS {tau_or/tau_c:.1f}')
for dp in (2, 3):
    Ap = np.pi*dp**2/4
    print(f'  pasador Ø{dp}x11: tau doble corte={Fc/(2*Ap):.2f} MPa (FS {tau_pin/(Fc/(2*Ap)):.0f}); '
          f'masa {Ap*11*rho_st:.3f} g; 4 pasadores {4*Ap*11*rho_st:.2f} g')
for dp in (2, 3):
    lo, hi = dp + 0.002, dp + 0.008        # m6
    ojo = (dp + 0.10, dp + 0.12)           # ojo escariado +0,02/0 sobre dp + 0,10
    print(f'  pasador Ø{dp} m6 [{lo:.3f},{hi:.3f}]: juego en el ojo {ojo[0]-hi:.3f} a {ojo[1]-lo:.3f} mm; '
          f'orejas Ø{dp-0.02:.2f}: interferencia nominal {lo-(dp-0.02):.3f} a {hi-(dp-0.02):.3f} mm')
# collar y cajera de la llave: pared del collar de 1,2 mm alrededor del ojo, juego radial 0,10-0,20
for dp in (2, 3):
    dc = dp + 0.10 + 2*1.2
    print(f'  Ø{dp}: collar Ø{dc:.1f} (0/-0,1), cajera Ø{dc+0.2:.1f} (+0,1/0): juego radial '
          f'{(dc+0.2-dc)/2:.2f} a {(dc+0.3-(dc-0.1))/2:.2f} mm; pared de la oreja hacia afuera '
          f'(e = 4,0): {4.0-(dc+0.2)/2:.2f} mm; pared del ojo (7 mm): {(7-(dp+0.1))/2:.2f} mm')
