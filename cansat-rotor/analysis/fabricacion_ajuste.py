#!/usr/bin/env python3
"""Ajuste a presión del rodamiento 688ZZ en el cubo impreso (Lamé), efecto de la
temperatura y de la relajación; balanceo (ISO 21940-11) y detección con la IMU;
desarrollo plano de la pestaña de inoxidable.
Salida: analysis/data/fabricacion_ajuste.dat y resumen por stdout.
Propiedades de catálogo, no medidas (ver texto)."""
import os
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

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
Mrot = 4*8.2 + 12.0 + 3.0        # g: palas con varilla y pestaña, cubo, aros exteriores
for Om in (120., 136., 162.):
    for G in (6.3, 16., 40.):
        U = 1000*G*Mrot/1000/Om*1000/1000   # g mm  (U = G M / Omega)
        U = G*Mrot/Om                         # [mm/s * g / (1/s)] = g mm
        print(f'Omega={Om:.0f}: G{G}: U_per={U:.1f} g mm = {U/120:.3f} g a 120 mm')
U01 = 0.1*120
for Om in (120., 136., 162.):
    print(f'0,1 g a 120 mm = {U01:.0f} g mm -> G = {U01*Om/Mrot:.1f} mm/s (Omega={Om:.0f}); '
          f'F = {U01*1e-6*Om**2:.3f} N')
# respuesta del cuerpo libre (0,5 kg) a 12 g mm
Mb, Ib, h = 0.5, 0.5*0.25**2/12, 0.10
for Om in (120.,):
    F = U01*1e-6*Om**2
    print(f'cuerpo: x={1e3*F/(Mb*Om**2):.4f} mm, theta={np.degrees(F*h/(Ib*Om**2)):.4f} deg')
# detección con IMU en el banco (masa suspendida 0,5 kg), ruido 200 ug/sqrtHz, 10 s
Ures = 6.0
a = Ures*1e-6*120**2/0.5
sig = 200e-6*9.81*np.sqrt(1/(2*10))
print(f'IMU: a(U=6 g mm)={a:.3f} m/s2 = {a/9.81*1e3:.1f} mg; ruido promediado 10 s = '
      f'{sig*1e3:.2f} mm/s2; SNR = {a/sig:.0f}')
# ---- pestaña de inoxidable: desarrollo plano
t, ri, K = 0.5, 0.5, 0.33
BA = np.pi/2*(ri + K*t)
L1, L2 = 6.0, 11.5      # alas exteriores (medidas exteriores) pegada / radial
L_flat = (L1 - (ri + t)) + (L2 - (ri + t)) + BA
print(f'Pestaña: BA={BA:.3f} mm, BD={2*(ri+t)-BA:.3f} mm, largo desarrollado={L_flat:.2f} mm')
r_out = 45.3           # cara exterior del pliegue (pala r_mo=44,62 + 0,5 + adhesivo ~0,2)
r_wire = 36.5
x_oj = r_out - r_wire  # centro del ojal desde la cara exterior del pliegue
print(f'Ojal: a {x_oj:.2f} mm de la cara exterior; a {L2-x_oj:.2f} mm del extremo; '
      f'en el desarrollo a {L_flat-(L2-x_oj):.2f} mm del extremo pegado; '
      f'extremo interior a r={r_out-L2:.2f} mm')
# pegado de la pestaña: 5 x 5 mm, corte admisible conservador 5 MPa
A = 5*5; print(f'Pegado: area {A} mm2, capacidad a 5 MPa = {5*A:.0f} N')
