#!/usr/bin/env python3
"""Sensibilidad del rotor a errores de fabricación de la pala (flecha y paso).

Modelo: elemento de pala con flujo neto uniforme u (hacia arriba) por el disco,
autorrotación estacionaria Q(Omega,u)=0 y empuje T(Omega,u)=T_req.
Polar lineal: Cl = a (alpha - alpha_L0), alpha_L0 = -2 eta f/c (teoría de perfil
delgado con eta=1; eta<1 calibrado con las polares XFOIL placa 4 % y 7 %),
Cd = cd0 + k Cl^2 (ajuste a XFOIL placa 7 %).
Uso del modelo: SOLO derivadas relativas (dOmega/ds, track, fuerza 1P). Los valores
absolutos de Omega dependen del modelo de flujo y no reemplazan a los del cap. 5.

Salidas: analysis/data/fabricacion_camber.dat, fabricacion_pitch.dat,
         fabricacion_track.dat, fabricacion_trackpitch.dat, y resumen por stdout.
"""
import os
import numpy as np
from scipy.optimize import fsolve

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
rho, B, c, R, e, r0 = 1.225, 4, 0.045, 0.200, 0.044, 0.064
Treq = 3.779
fc0, th0 = 0.07, np.radians(-3.0)
a = 2*np.pi*0.80            # pendiente de sustentación [1/rad] (baja Re, placa delgada)
Clmax = 1.30

def load(f):
    d = np.loadtxt(os.path.join(D, f), skiprows=1, usecols=(0, 1, 2))
    return d[np.argsort(d[:, 0])]

# --- calibración con XFOIL: dCl/d(f/c) a igual alfa (rango 4,5-6,5 grados)
dcl = []
for Re in (35, 50, 75):
    p4, p7 = load(f'polares_placa4_Re{Re}.dat'), load(f'polares_placa7_Re{Re}.dat')
    al = np.arange(4.5, 6.51, 0.25)
    d = (np.interp(al, p7[:, 0], p7[:, 1]) - np.interp(al, p4[:, 0], p4[:, 1]))/0.03
    dcl.append(d.mean())
dcl_xf = float(np.mean(dcl))
eta_xf = dcl_xf/(2*a)
eta_lo = min(dcl)/(2*a)
CASES = (('tat', 1.0), ('xf', eta_lo))
# --- ajuste de resistencia placa 7 %, Re 50k
p7 = load('polares_placa7_Re50.dat')
m = (p7[:, 1] > 0.3) & (p7[:, 0] <= 7.0)   # rama sin pérdida
A = np.vstack([np.ones(m.sum()), p7[m, 1]**2]).T
cd0, kcd = np.linalg.lstsq(A, p7[m, 2], rcond=None)[0]

r = np.linspace(r0, R, 400)
dr = r[1]-r[0]
w = np.full_like(r, dr); w[0] = w[-1] = dr/2

def polar(alpha, fc, eta):
    cl = np.clip(a*(alpha + 2*eta*fc), -Clmax, Clmax)
    return cl, cd0 + kcd*cl**2

def loads(Om, u, fc, th, eta):
    UT = Om*r; phi = np.arctan2(u, UT); W2 = UT**2 + u**2
    cl, cd = polar(th + phi, fc, eta)
    q = 0.5*rho*W2*c
    dL, dD = q*cl, q*cd
    dTz = dL*np.cos(phi) + dD*np.sin(phi)          # vertical
    dFt = dL*np.sin(phi) - dD*np.cos(phi)          # tangencial (impulsora +)
    return dL, dTz, dFt, phi, cl

def solve(fc, th, eta, x0=(150., 1.0)):
    def F(x):
        Om, u = x
        _, dTz, dFt, _, _ = loads(Om, u, fc, th, eta)
        return [B*np.sum(dTz*w) - Treq, B*np.sum(dFt*r*w)*100]
    sol, info, ier, msg = fsolve(F, x0, full_output=True)
    if ier != 1:
        raise RuntimeError(msg)
    return sol

# masa de pala: placa 5,4 g uniforme e..R + 2 g de portapala a e+10 mm
mp, mr, rr = 5.4e-3, 2.0e-3, e + 0.010
rb = np.linspace(e, R, 400)
Sb = np.trapezoid(mp/(R-e)*rb*(rb-e), rb) + mr*rr*(rr-e)        # int m r (r-e)
mb = mp + mr
rg = (np.trapezoid(mp/(R-e)*rb, rb) + mr*rr)/mb

out = {}
for lab, eta in CASES:
    Om0, u0 = solve(fc0, th0, eta)
    out[lab] = (Om0, u0)

def rpm(Om): return Om*60/(2*np.pi)

# --- barrido de flecha (todas las palas iguales)
s_list = np.linspace(2.55, 3.75, 25)
rows = []
for s in s_list:
    fc = s/45.0
    row = [s, 100*fc]
    for lab, eta in CASES:
        Om, u = solve(fc, th0, eta, out[lab])
        row += [rpm(Om)]
    rows.append(row)
rows = np.array(rows)
np.savetxt(os.path.join(D, 'fabricacion_camber.dat'), rows, fmt='%.4f',
           header='s fc rpm_tat rpm_xf', comments='')

# --- barrido de paso
th_list = np.radians(np.linspace(-6, 0, 25))
rows2 = []
for th in th_list:
    row = [np.degrees(th)]
    for lab, eta in CASES:
        Om, u = solve(fc0, th, eta, out[lab])
        row += [rpm(Om)]
    rows2.append(row)
rows2 = np.array(rows2)
np.savetxt(os.path.join(D, 'fabricacion_pitch.dat'), rows2, fmt='%.4f',
           header='theta rpm_tat rpm_xf', comments='')

# --- pala desigual: una pala con flecha s0+ds (o paso th0+dth), rotor en su punto
def blade_diff(dfc, dth, eta, Om, u):
    dL0, _, dFt0, _, _ = loads(Om, u, fc0, th0, eta)
    dL1, _, dFt1, _, _ = loads(Om, u, fc0 + dfc, th0 + dth, eta)
    dM = np.sum((dL1 - dL0)*(r - e)*w)          # momento de batimiento
    dF = np.sum((dFt1 - dFt0)*w)                # fuerza tangencial 1P
    Kb = Om**2*Sb
    dbeta = dM/Kb
    return np.degrees(dbeta), 1e3*(R - e)*dbeta, abs(dF), np.sum((dL1-dL0)*w)

ds_list = np.linspace(0, 0.5, 11)
rows3 = []
for ds in ds_list:
    row = [ds]
    for lab, eta in CASES:
        Om, u = out[lab]
        db, dz, dF, dLt = blade_diff(ds/45.0, 0.0, eta, Om, u)
        row += [dz, dF, 100*dLt/(Treq/B)]
    rows3.append(row)
rows3 = np.array(rows3)
np.savetxt(os.path.join(D, 'fabricacion_track.dat'), rows3, fmt='%.5f',
           header='ds dz_tat F_tat dL_tat dz_xf F_xf dL_xf', comments='')

dth_list = np.linspace(0, 1.0, 11)
rows4 = []
for dt in dth_list:
    row = [dt]
    for lab, eta in CASES:
        Om, u = out[lab]
        db, dz, dF, dLt = blade_diff(0.0, np.radians(dt), eta, Om, u)
        row += [dz, dF, 100*dLt/(Treq/B)]
    rows4.append(row)
rows4 = np.array(rows4)
np.savetxt(os.path.join(D, 'fabricacion_trackpitch.dat'), rows4, fmt='%.5f',
           header='dth dz_tat F_tat dL_tat dz_xf F_xf dL_xf', comments='')

# ------------------------------------------------------------- resumen
print(f'dCl/d(f/c) XFOIL por Re 35/50/75: {[round(x,2) for x in dcl]} -> media {dcl_xf:.2f}'
      f' (TAT: {2*a:.2f}); eta_xf = {eta_xf:.3f}')
print(f'Ajuste Cd = {cd0:.4f} + {kcd:.4f} Cl^2')
print(f'Masa de pala {1e3*mb:.2f} g, r_g = {1e3*rg:.1f} mm, S_beta = {Sb:.3e} kg m2')
for lab in out:
    Om, u = out[lab]
    dL, dTz, dFt, phi, cl = loads(Om, u, fc0, th0, dict(CASES)[lab])
    i75 = np.argmin(abs(r-0.75*R))
    print(f'[{lab}] Omega={Om:.1f} rad/s ({rpm(Om):.0f} rpm), u={u:.2f} m/s, '
          f'alpha75={np.degrees(th0+phi[i75]):.2f} deg, Cl75={cl[i75]:.2f}, '
          f'Clmed={np.sum(cl*r**2*w)/np.sum(r**2*w):.2f}, K_beta={Om**2*Sb:.3f} N m/rad')
for lab, col in (('tat', 2), ('xf', 3)):
    s, y = rows[:, 0], rows[:, col]
    k = np.gradient(y, s)[np.argmin(abs(s-3.15))]
    print(f'[{lab}] drpm/ds = {k:.1f} rpm/mm ({100*k/np.interp(3.15,s,y):.2f} %/mm)')
for lab, col in (('tat', 1), ('xf', 2)):
    k = np.gradient(rows2[:, col], rows2[:, 0])[np.argmin(abs(rows2[:, 0]+3))]
    print(f'[{lab}] drpm/dtheta = {k:.1f} rpm/deg; rpm(-6,-4,-2,0) = '
          f'{[round(float(np.interp(t, rows2[:,0], rows2[:,col]))) for t in (-6,-4,-2,0)]}')
np.set_printoptions(precision=4, suppress=True)
print('pala desigual ds=0,1/0,2/0,3 mm: ', rows3[[2, 4, 6]])
print('pala desigual dth=0,2/0,5/1,0 deg: ', rows4[[2, 5, 10]])
for lab in out:
    Om = out[lab][0]
    print(f'[{lab}] fuerza por 0,1 g a r_g: {1e-4*rg*Om**2:.3f} N')
