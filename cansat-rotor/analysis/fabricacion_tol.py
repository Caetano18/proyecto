#!/usr/bin/env python3
"""Cadenas de tolerancias del rotor: peor caso, RSS y Monte Carlo.

Cadenas:
  A. Juego axial del cubo y huelgo cubo-tapa (y entrehierro imán-sensor hall).
  B. Pala plegada dentro de la envolvente Ø95 (geometría no lineal del arco).
  C. Alineación pestaña (ojal) - diente del anillo de traba (radial, axial, tangencial).
Convención: tolerancia simétrica +-T equivale a 3 sigma (distribución normal) salvo que
se indique uniforme. Salidas: analysis/data/fabricacion_tol.dat (resumen),
fabricacion_hist_env.dat (histograma del margen de envolvente para dos asignaciones),
fabricacion_env_ts.dat (probabilidad de exceder Ø95 vs tolerancia de flecha).
"""
import os
import numpy as np

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
rng = np.random.default_rng(20261005)
N = 400_000
res = []

def mc_norm(nom, tol, n=N):
    return nom + rng.normal(0, tol/3, n)

def mc_unif(lo, hi, n=N):
    return rng.uniform(lo, hi, n)

def report(name, nom, wc_lo, wc_hi, rss, x, lim=None, sense='min'):
    p1, p99 = np.percentile(x, [0.135, 99.865])
    fail = np.nan
    if lim is not None:
        fail = np.mean(x < lim) if sense == 'min' else np.mean(x > lim)
    res.append((name, nom, wc_lo, wc_hi, rss, p1, p99, 100*fail if lim is not None else -1))
    print(f'{name:22s} nom {nom:7.3f}  WC [{wc_lo:7.3f},{wc_hi:7.3f}]  RSS +-{rss:.3f}  '
          f'MC 3s [{p1:7.3f},{p99:7.3f}]  P(falla) {100*fail if lim is not None else 0:.4f} %')

# ---------------------------------------------------------------- A. cubo
# Pila interior (fija, apretada por la tuerca): collar Lc, aro int. inferior B1,
# separador interior Lsi, aro int. superior B2.  Pila exterior (cubo): nervio Lso entre
# los aros exteriores; asiento inferior de profundidad ds desde la cara inferior del cubo.
# Juego axial j = Lsi - Lso + (desplazamiento axial interno de los 2 rodamientos).
Lsi = (3.10, 0.02)    # separador de tubo de Al 10x8 refrentado en torno
Lso = (3.00, 0.08)    # nervio impreso (eje Z, capa 0,1 mm, medido y lijado)
ax = (0.010, 0.030)   # juego axial interno 688ZZ (C0) por rodamiento: uniforme [0,01;0,03]
off = 0.010           # desalineación cara aro int./ext. (incluida en ax)
j_nom = Lsi[0] - Lso[0] + 2*np.mean(ax)
j_wc = (Lsi[0]-Lsi[1]-Lso[0]-Lso[1]+2*ax[0], Lsi[0]+Lsi[1]-Lso[0]+Lso[1]+2*ax[1])
j_rss = np.sqrt(Lsi[1]**2 + Lso[1]**2 + 2*((ax[1]-ax[0])/2)**2*3/3)
j = mc_norm(*Lsi) - mc_norm(*Lso) + mc_unif(*ax) + mc_unif(*ax)
report('A1 juego axial j', j_nom, *j_wc, j_rss, j, lim=0.0, sense='min')

# Huelgo cubo-tapa con el cubo abajo (en reposo): g = Lc + B1 - ds - planitud
Lc = (1.00, 0.03)     # collar (arandela de Al rectificada)
B1 = (4.94, 0.06)     # ancho 688: 0/-0,12 (ISO 492 normal) -> 4,94 +- 0,06
dsd = (5.30, 0.08)    # profundidad del asiento inferior del cubo
fl = (0.0, 0.10)      # planitud/inclinación de la cara superior de la tapa impresa
g_nom = Lc[0]+B1[0]-dsd[0]-fl[0]
tols = [Lc[1], B1[1], dsd[1], fl[1]]
g_wc = (g_nom - sum(tols), g_nom + sum(tols))
g = mc_norm(*Lc) + mc_norm(*B1) - mc_norm(*dsd) - mc_norm(*fl)
report('A2 huelgo cubo-tapa', g_nom, *g_wc, np.sqrt(sum(t*t for t in tols)), g, lim=0.15)
# entrehierro imán-hall: huelgo + rebaje del imán (0,3+-0,1) + tapa sobre el sensor (0,6+-0,1)
h = g + mc_norm(0.30, 0.10) + mc_norm(0.60, 0.10) + np.clip(j, 0, None)
h_nom = g_nom + 0.9 + j_nom
tols_h = tols + [0.1, 0.1]
report('A3 entrehierro hall', h_nom, h_nom-sum(tols_h)-j_wc[1], h_nom+sum(tols_h)+j_wc[1],
       np.sqrt(sum(t*t for t in tols_h)+j_rss**2), h, lim=3.0, sense='max')

# ---------------------------------------------------------------- B. envolvente
def edge_and_gap(rmo, s, c, t, Rb):
    """rmo: radio de la cara exterior en media cuerda; s: flecha de la línea media."""
    rho = (c*c/4 + s*s)/(2*s)            # radio de la línea media
    ro = rho + t/2                       # radio de la cara exterior
    al = np.arcsin(c/(2*rho))
    rc = rmo - ro                        # centro del arco (sobre la línea radial)
    xe = rc + ro*np.cos(al); ye = ro*np.sin(al)
    redge = np.sqrt(xe*xe + ye*ye)
    return 47.5 - redge, (rmo - t) - Rb

def chain_B(rmo_nom, Rb_nom, tol_s, tol_bow, c_nom=45.0, n=N):
    # posición radial de la pala: bisagra (0,10), juego del pasador (0,05 unif.),
    # asiento en el portapala (0,10), arco longitudinal/alabeo (tol_bow), ranura (0,10)
    rmo = (mc_norm(rmo_nom, 0.10, n) + mc_unif(-0.05, 0.05, n) + rng.normal(0, 0.10/3, n)
           + rng.normal(0, tol_bow/3, n) + rng.normal(0, 0.10/3, n))
    s = mc_norm(3.15, tol_s, n)
    c = mc_norm(c_nom, 0.20, n)
    t = mc_norm(0.50, 0.05, n)
    Rb = mc_norm(Rb_nom, 0.15, n)
    return edge_and_gap(rmo, s, c, t, Rb)

def lin_B(rmo_nom, Rb_nom, tol_s, tol_bow, c_nom=45.0):
    global_c = c_nom
    x0 = np.array([rmo_nom, 3.15, c_nom, 0.50, Rb_nom])
    tol = np.array([np.sqrt(0.1**2+0.05**2+0.1**2+tol_bow**2+0.1**2), tol_s, 0.2, 0.05, 0.15])
    tol_wc = np.array([0.1+0.05+0.1+tol_bow+0.1, tol_s, 0.2, 0.05, 0.15])
    f0 = np.array(edge_and_gap(*x0))
    J = []
    for k in range(5):
        dx = np.zeros(5); dx[k] = 1e-4
        J.append((np.array(edge_and_gap(*(x0+dx))) - f0)/1e-4)
    J = np.array(J)                   # 5 x 2
    wc = np.abs(J).T @ tol_wc
    rss = np.sqrt((J.T**2) @ tol**2)
    return f0, wc, rss, J

configs = {
  'base':      dict(rmo_nom=44.98, Rb_nom=44.00, tol_s=0.30, tol_bow=0.30),
  'reparto':   dict(rmo_nom=44.74, Rb_nom=44.00, tol_s=0.30, tol_bow=0.30),
  'cuerda44':  dict(rmo_nom=44.80, Rb_nom=44.00, tol_s=0.15, tol_bow=0.15, c_nom=44.0),
  'propuesta': dict(rmo_nom=44.62, Rb_nom=43.60, tol_s=0.15, tol_bow=0.15),
}
hist = {}
for k, cfg in configs.items():
    env, gap = chain_B(**cfg)
    f0, wc, rss, J = lin_B(**cfg)
    if k == 'base':
        print('Derivadas (env, gap) respecto de rmo, s, c, t, Rb:\n', np.round(J, 3))
    report(f'B {k}: env', f0[0], f0[0]-wc[0], f0[0]+wc[0], rss[0], env, lim=0.0)
    report(f'B {k}: gap', f0[1], f0[1]-wc[1], f0[1]+wc[1], rss[1], gap, lim=0.0)
    hist[k] = env
edges = np.linspace(-0.8, 1.2, 81)
cent = 0.5*(edges[1:]+edges[:-1])
H = [cent]
for k in ('reparto', 'cuerda44', 'propuesta'):
    hh, _ = np.histogram(hist[k], edges, density=True); H.append(hh)
np.savetxt(os.path.join(D, 'fabricacion_hist_env.dat'), np.array(H).T, fmt='%.5f',
           header='m reparto cuerda44 propuesta', comments='')
# probabilidad de exceder Ø95 vs tolerancia de flecha (propuesta)
rows = []
for ts in np.linspace(0.05, 0.50, 19):
    e1, g1 = chain_B(44.62, 43.60, ts, 0.15, n=200_000)
    e2, g2 = chain_B(44.74, 44.00, ts, 0.30, n=200_000)
    e3, g3 = chain_B(44.80, 44.00, ts, 0.15, c_nom=44.0, n=200_000)
    rows.append([ts, 100*np.mean(e1 < 0), 100*np.mean(g1 < 0), 100*np.mean(e2 < 0), 100*np.mean(g2 < 0),
                 100*np.mean((e3 < 0) | (g3 < 0)), 100*np.mean((e1 < 0) | (g1 < 0))])
np.savetxt(os.path.join(D, 'fabricacion_env_ts.dat'), np.array(rows), fmt='%.4f',
           header='ts Penv_prop Pgap_prop Penv_rep Pgap_rep Pany_c44 Pany_prop', comments='')

# ---------------------------------------------------------------- C. traba
# Radial (solo para insertar sin forzar): ojal de 1,70 con alambre Ø1,00 -> 0,35 por lado.
# Posición radial del ojal: radio de la pala (cadena B, 0,19 RSS), plegado de la
# pestaña (0,15), ojal respecto del pliegue (0,05, punzonado con plantilla),
# radio del alambre en el anillo (0,10), excentricidad/juego del anillo en su asiento (0,15).
cl_r = (1.70 - 1.00)/2
tr = [0.19, 0.15, 0.05, 0.10, 0.15]
xr = sum(mc_norm(0, t) for t in tr)
report('C1 radial (desvío)', 0.0, -sum(tr), sum(tr), np.sqrt(sum(t*t for t in tr)), np.abs(xr),
       lim=cl_r, sense='max')
# Axial: ojal colisado 2,6 con alambre Ø1,0 -> 0,80 por lado.
# Largo de pala 156 (0,20), pegado de la pestaña con plantilla referida al pasador (0,15),
# posición axial de la bisagra en el cubo (0,10), del anillo en el cuerpo (0,15),
# alambre en el anillo (0,10).
cl_z = (2.60 - 1.00)/2
tz_sin = [0.20, 0.15, 0.10, 0.15, 0.10, 0.30]   # 0,30: pegado libre a ojo
tz_con = [0.20, 0.15, 0.10, 0.15, 0.10]
for lab, tz in (('sin plantilla', tz_sin), ('con plantilla', tz_con)):
    xz = sum(mc_norm(0, t) for t in tz)
    report(f'C2 axial {lab}', 0.0, -sum(tz), sum(tz), np.sqrt(sum(t*t for t in tz)), np.abs(xz),
           lim=cl_z, sense='max')
# Tangencial: enganche nominal 2,5 mm de alambre más allá de la pestaña.
# Azimut de la pestaña: ranura 1,2 con pestaña 0,5 (+-0,35 uniforme), azimut de la
# ranura (0,10), posición del alambre en el anillo (0,10), tope mecánico del anillo (0,10).
eng_nom = 2.5
xt = mc_unif(-0.35, 0.35) + mc_norm(0, 0.10) + mc_norm(0, 0.10) + mc_norm(0, 0.10)
eng = eng_nom - np.abs(xt)
report('C3 enganche tang.', eng_nom, eng_nom-0.65, eng_nom, np.sqrt(0.35**2+3*0.1**2), eng,
       lim=1.5)
# con tope fijado solo por el servo (resolución +-1 grado a r=36,5 mm = +-0,64 mm)
xt2 = xt + mc_unif(-0.64, 0.64)
eng2 = eng_nom - np.abs(xt2)
report('C3b enganche (servo)', eng_nom, eng_nom-1.29, eng_nom, np.sqrt(0.35**2+3*0.1**2+0.64**2),
       eng2, lim=1.5)

with open(os.path.join(D, 'fabricacion_tol.dat'), 'w') as f:
    f.write('cadena nom wc_lo wc_hi rss mc_lo mc_hi pfalla\n')
    for r in res:
        f.write(r[0].replace(' ', '_') + ' ' + ' '.join(f'{v:.4f}' for v in r[1:]) + '\n')
