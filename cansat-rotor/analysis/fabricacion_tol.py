#!/usr/bin/env python3
"""Cadenas de tolerancias del rotor: peor caso, RSS y Monte Carlo.

Cadenas:
  A. Juego axial del cubo y huelgo cubo-tapa (y entrehierro imán-sensor hall).
  B. Pala plegada dentro de la envolvente (S2): Ø90 en la versión 2, Ø95 en la 1.
  C. Alineación pestaña (ojal) - diente del anillo de traba (radial, axial, tangencial).
Convención: tolerancia simétrica +-T equivale a 3 sigma (distribución normal) salvo que
se indique uniforme.

Configuración: variable de entorno CANSAT_CFG (igual que v2_config.py).
  v2 (por defecto): envolvente R_ENV = 45,0 mm, cuerpo Ø81 (R = 40,5), pala de 206 mm.
     La pala plegada apoya en el cuerpo (huelgo nominal 0), como en el capítulo de
     arquitectura (v2_geometria.py, v2_tol_env.py). Salidas: fabricacion_tol.dat (resumen),
     fabricacion_hist_env.dat (histograma del margen de envolvente, columnas m base relajada
     adoptada) y fabricacion_env_ts.dat (margen a 3 sigma y de peor caso frente a la
     tolerancia de flecha).
  v1: envolvente R_ENV = 47,5 mm, cuerpo Ø88 (R = 44,0), pala de 156 mm. Reproduce la
     versión anterior y escribe en los mismos archivos, con el formato de entonces
     (fabricacion_hist_env.dat: m reparto cuerda44 propuesta;
      fabricacion_env_ts.dat: probabilidad de exceder Ø95 vs tolerancia de flecha).

Modelo del borde (v2). Una pala de cuerda c, flecha s y espesor t, apoyada por el centro
de su cara cóncava a un radio rho del eje, tiene el borde exterior a
    r = sqrt((rho - s + t)^2 + (c/2)^2)                       (cap. 23, ec. arq-rborde)
con margen m = R_ENV - r. El modelo de la versión 1 (arco exacto, parametrizado con el
radio de la cara exterior en el centro de la cuerda, rmo = rho + t) describe la misma
geometría y da un borde 0,02 mm mayor (se imprime como verificación); para la v2 se usa la
expresión del capítulo 23 para que esta cadena y v2_tol_env.py den los mismos números
(misma semilla y mismo orden de sorteo).
"""
import os
import numpy as np

CFG = os.environ.get('CANSAT_CFG', 'v2')
V1 = (CFG == 'v1')
R_ENV = 47.5 if V1 else 45.0      # radio de la envolvente S2 [mm]
RB_NOM = 44.0 if V1 else 40.5     # radio nominal del cuerpo impreso [mm]
L_PALA = 156 if V1 else 206       # largo de pala desde el eje de la bisagra [mm]

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
rng = np.random.default_rng(20261005)
N = 400_000
res = []

def mc_norm(nom, tol, n=N, g=None):
    return nom + (g or rng).normal(0, tol/3, n)

def mc_unif(lo, hi, n=N, g=None):
    return (g or rng).uniform(lo, hi, n)

def report(name, nom, wc_lo, wc_hi, rss, x, lim=None, sense='min'):
    p1, p99 = np.percentile(x, [0.135, 99.865])
    fail = np.nan
    if lim is not None:
        fail = np.mean(x < lim) if sense == 'min' else np.mean(x > lim)
    res.append((name, nom, wc_lo, wc_hi, rss, p1, p99, 100*fail if lim is not None else -1))
    print(f'{name:22s} nom {nom:7.3f}  WC [{wc_lo:7.3f},{wc_hi:7.3f}]  RSS +-{rss:.3f}  '
          f'MC 3s [{p1:7.3f},{p99:7.3f}]  P(falla) {100*fail if lim is not None else 0:.4f} %')

# ---------------------------------------------------------------- A. cubo
# Disposición fijo-libre (corregida en la revisión): el rodamiento INFERIOR es el fijo
# (aro exterior con interferencia y adhesivo, apoyado contra la cara inferior del nervio;
# aro interior apretado entre collar y separador). El SUPERIOR es libre: aro exterior
# deslizante en su asiento, sin adhesivo; aro interior apretado entre separador y tuerca.
# Con los dos aros exteriores fijos al cubo y los dos interiores apretados por la tuerca el
# conjunto sería hiperestático: cualquier diferencia Lsi-Lso mayor que el juego interno
# precargaría los rodamientos (ver texto). Con el aro superior libre:
#   juego axial del cubo      j = juego axial interno del rodamiento fijo (a1)
#   luz nervio - aro libre    u = Lsi - Lso +- (a1+a2)/2   (u<0: el aro libre desliza, sin daño)
#   huelgo cubo-tapa          g = Lc + B1 - ds - planitud -+ a1/2
# (el cubo, los rodamientos y la tapa no cambian entre v1 y v2: esta cadena no depende del
# tamaño de la pala)
Lsi = (3.10, 0.02)    # separador de tubo de Al 10x8 refrentado en torno
Lso = (3.00, 0.08)    # nervio impreso (eje Z, capa 0,12 mm, medido y lijado)
ax = (0.010, 0.050)   # juego axial interno 688ZZ por rodamiento: uniforme (valor supuesto)
a1 = mc_unif(*ax); a2 = mc_unif(*ax)
report('A1 juego axial j', np.mean(ax), ax[0], ax[1], (ax[1]-ax[0])/2, a1, lim=0.0, sense='min')
u_nom = Lsi[0] - Lso[0]
u_t = Lsi[1] + Lso[1] + ax[1]
u = (mc_norm(*Lsi) - mc_norm(*Lso) + rng.uniform(-1, 1, N)*a1/2 + rng.uniform(-1, 1, N)*a2/2)
report('A1b luz nervio-aro libre', u_nom, u_nom-u_t, u_nom+u_t,
       np.sqrt(Lsi[1]**2+Lso[1]**2), u, lim=0.0, sense='min')

# Huelgo cubo-tapa (cubo sobre el rodamiento fijo): g = Lc + B1 - ds - planitud -+ a1/2
Lc = (1.00, 0.03)     # collar (arandela de Al rectificada)
B1 = (4.94, 0.06)     # ancho 688: 0/-0,12 (ISO 492 normal) -> 4,94 +- 0,06
dsd = (5.30, 0.08)    # profundidad del asiento inferior del cubo
fl = (0.0, 0.10)      # planitud/inclinación de la cara superior de la tapa impresa
g_nom = Lc[0]+B1[0]-dsd[0]-fl[0]
tols = [Lc[1], B1[1], dsd[1], fl[1]]
g_wc = (g_nom - sum(tols) - ax[1]/2, g_nom + sum(tols) + ax[1]/2)
g = (mc_norm(*Lc) + mc_norm(*B1) - mc_norm(*dsd) - mc_norm(*fl)
     + rng.uniform(-1, 1, N)*a1/2)
report('A2 huelgo cubo-tapa', g_nom, *g_wc, np.sqrt(sum(t*t for t in tols)), g, lim=0.15)
# entrehierro imán-hall: huelgo + rebaje del imán (0,3+-0,1) + tapa sobre el sensor (0,6+-0,1)
h = g + mc_norm(0.30, 0.10) + mc_norm(0.60, 0.10)
h_nom = g_nom + 0.9
tols_h = tols + [0.1, 0.1]
report('A3 entrehierro hall', h_nom, h_nom-sum(tols_h)-ax[1]/2, h_nom+sum(tols_h)+ax[1]/2,
       np.sqrt(sum(t*t for t in tols_h)), h, lim=3.0, sense='max')

# ---------------------------------------------------------------- B. envolvente
def edge_radius(rmo, s, c, t):
    """Modelo de la versión 1 (arco exacto). rmo: radio de la cara exterior en el centro de
    la cuerda; s: flecha de la línea media."""
    rho = (c*c/4 + s*s)/(2*s)            # radio de la línea media
    ro = rho + t/2                       # radio de la cara exterior
    al = np.arcsin(c/(2*rho))
    rc = rmo - ro                        # centro del arco (sobre la línea radial)
    xe = rc + ro*np.cos(al); ye = ro*np.sin(al)
    return np.sqrt(xe*xe + ye*ye)

def edge_and_gap(rmo, s, c, t, Rb):
    """v1: margen de envolvente y huelgo entre la cara cóncava y el cuerpo."""
    return R_ENV - edge_radius(rmo, s, c, t), (rmo - t) - Rb

def edge_v2(rho, s, c, t):
    """v2: radio del borde (cap. 23, ec. arq-rborde); rho: radio de la cara cóncava en el
    centro de la cuerda (cuerpo + posición de la pala)."""
    return np.sqrt((rho - s + t)**2 + (c/2)**2)

# tolerancias de posición radial de la pala (3 sigma): bisagra, pasador (U), asiento en el
# portapala, ranura; el alabeo longitudinal (T_a) y, en v2, el radio del cuerpo se suman aparte
T_BIS, T_PAS, T_ASI, T_RAN = 0.10, 0.05, 0.10, 0.10
T_CUERPO = 0.15        # radio del cuerpo: Ø81 +-0,3 -> +-0,15 (v2)

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

def chain_B2(tol_s, tol_bow, g, c_nom=45.0, n=N):
    """v2: margen de envolvente m = R_ENV - r_borde y posición libre de la pala h respecto
    del cuerpo (h > 0: separada; h < 0: la pala quedaría dentro del cuerpo). El orden de
    sorteo es el de v2_tol_env.py (cuerpo, bisagra, pasador, asiento, alabeo, ranura,
    flecha, cuerda, espesor)."""
    Rb = g.normal(RB_NOM, T_CUERPO/3, n)
    h = (g.normal(0, T_BIS/3, n) + g.uniform(-T_PAS, T_PAS, n) + g.normal(0, T_ASI/3, n)
         + g.normal(0, tol_bow/3, n) + g.normal(0, T_RAN/3, n))
    s = g.normal(3.15, tol_s/3, n)
    c = g.normal(c_nom, 0.20/3, n)
    t = g.normal(0.50, 0.05/3, n)
    m = R_ENV - edge_v2(Rb + h, s, c, t)
    m_ap = R_ENV - edge_v2(Rb + np.maximum(h, 0.0), s, c, t)   # si el cuerpo detiene a la pala
    return m, m_ap, h

def lin_B2(tol_s, tol_bow, c_nom=45.0):
    """Peor caso (suma lineal) y RSS del margen v2, con derivadas numéricas en
    x = (rho, s, c, t); rho suma las tolerancias de posición y del cuerpo."""
    x0 = np.array([RB_NOM, 3.15, c_nom, 0.50])
    f = lambda x: R_ENV - edge_v2(*x)
    f0 = f(x0)
    J = np.array([(f(x0 + 1e-5*np.eye(4)[k]) - f0)/1e-5 for k in range(4)])
    t_rho = [T_CUERPO, T_BIS, T_PAS, T_ASI, tol_bow, T_RAN]
    tol_wc = np.array([sum(t_rho), tol_s, 0.20, 0.05])
    tol_rss = np.array([np.sqrt(sum(t*t for t in t_rho)), tol_s, 0.20, 0.05])
    return f0, np.abs(J) @ tol_wc, np.sqrt((J**2) @ tol_rss**2), J

if V1:
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
else:
    # --- v2: cuerpo Ø81 dentro de Ø90. Tres asignaciones de (T_s, T_a): la base de la versión 1
    # (0,30; 0,30), la flecha relajada (0,30; 0,15) y la adoptada (0,15; 0,15).
    rng_b = np.random.default_rng(20261018)       # semilla de v2_tol_env.py
    # (el orden base, adoptada, relajada reproduce la secuencia de sorteos de v2_tol_env.py,
    # que corre 'base' y 'propuesta' = adoptada; la relajada va al final)
    configs = {
      'base':     dict(tol_s=0.30, tol_bow=0.30),
      'adoptada': dict(tol_s=0.15, tol_bow=0.15),
      'relajada': dict(tol_s=0.30, tol_bow=0.15),
    }
    f0, wc0, rss0, J0 = lin_B2(0.15, 0.15)
    print(f'Borde nominal v2 (rho = {RB_NOM}, s = 3,15, c = 45, t = 0,5): '
          f'{R_ENV - f0:.3f} mm -> margen {f0:.3f} mm')
    r_arco = edge_radius(RB_NOM + 0.5, 3.15, 45.0, 0.50)
    print(f'  verificación con el arco exacto de v1: borde {r_arco:.3f} mm (margen {R_ENV - r_arco:.3f})')
    print('Derivadas del margen respecto de rho, s, c, t:', np.round(J0, 3))
    hist = {}
    stats = {}
    for k, cfg in configs.items():
        m, m_ap, hlib = chain_B2(g=rng_b, **cfg)
        f0, wc, rss, J = lin_B2(**cfg)
        report(f'B {k}: m', f0, f0-wc, f0+wc, rss, m, lim=0.0)
        hist[k] = m
        stats[k] = dict(mean=m.mean(), sd=m.std(), k=m.mean()/m.std(), p0135=np.percentile(m, 0.135),
                        mean_ap=m_ap.mean(), sd_ap=m_ap.std(), k_ap=m_ap.mean()/m_ap.std(),
                        h3=3*hlib.std(), pneg=np.mean(hlib < 0), wc=f0-wc, rss=rss)
        st = stats[k]
        print(f'   media {st["mean"]:.4f}  sd {st["sd"]:.4f}  k = {st["k"]:.1f} sigma  '
              f'peor caso {st["wc"]:+.3f}  RSS +-{st["rss"]:.3f}')
        print(f'   si el cuerpo detiene a la pala (h >= 0): media {st["mean_ap"]:.4f}  '
              f'sd {st["sd_ap"]:.4f}  k = {st["k_ap"]:.1f} sigma; posición libre h: +-{st["h3"]:.3f} (3 sigma), '
              f'P(h<0) = {100*st["pneg"]:.1f} %')
    edges = np.linspace(0.30, 1.60, 66)
    cent = 0.5*(edges[1:]+edges[:-1])
    H = [cent]
    for k in ('base', 'relajada', 'adoptada'):
        hh, _ = np.histogram(hist[k], edges, density=True); H.append(hh)
    np.savetxt(os.path.join(D, 'fabricacion_hist_env.dat'), np.array(H).T, fmt='%.5f',
               header='m base relajada adoptada', comments='')
    # margen a 3 sigma (percentil 0,135) y de peor caso frente a la tolerancia de flecha, para
    # alabeo de 0,15 y de 0,30; probabilidad de interferencia
    rng_ts = np.random.default_rng(20261019)
    rows = []
    for ts in np.linspace(0.05, 0.50, 19):
        row = [ts]
        for ta in (0.15, 0.30):
            m, _, _ = chain_B2(ts, ta, rng_ts, n=200_000)
            f0, wc, rss, J = lin_B2(ts, ta)
            row += [np.percentile(m, 0.135), f0 - wc, 100*np.mean(m < 0)]
        rows.append(row)
    np.savetxt(os.path.join(D, 'fabricacion_env_ts.dat'), np.array(rows), fmt='%.4f',
               header='ts m3_a15 mwc_a15 P_a15 m3_a30 mwc_a30 P_a30', comments='')
    print('Barrido de T_s (alabeo 0,15 / 0,30): margen 3 sigma, peor caso, P [%]')
    for r_ in rows[::3]:
        print('  ', ' '.join(f'{v:8.4f}' for v in r_))
    # tolerancia de flecha máxima con la que el peor caso (suma lineal) todavía cierra (m >= 0)
    for ta in (0.15, 0.30):
        lo, hi = 0.0, 2.0
        for _ in range(60):
            mid = 0.5*(lo+hi)
            f0_, wc_, _, _ = lin_B2(mid, ta)
            lo, hi = (mid, hi) if f0_ - wc_ >= 0 else (lo, mid)
        print(f'T_s máxima con cierre en peor caso, alabeo +-{ta}: +-{lo:.3f} mm')

# ---------------------------------------------------------------- C. traba
# Radial (solo para insertar sin forzar): ojal de 1,70 con alambre Ø1,00 -> 0,35 por lado.
# Posición radial del ojal: radio de la pala (cadena B, 0,19 RSS), plegado de la
# pestaña (0,15), ojal respecto del pliegue (0,05, punzonado con plantilla),
# radio del alambre en el anillo (0,10), excentricidad/juego del anillo en su asiento (0,15).
# Corrección de la revisión: el peor caso usa la suma lineal de la cadena de posición
# de la pala (bisagra 0,10 + pasador 0,05 + asiento 0,10 + ranura 0,10 = 0,35), no su RSS.
# (la cadena C usa su propio generador en las dos configuraciones: la física no cambia entre
# v1 y v2 y los resultados son idénticos)
rng_c = np.random.default_rng(20261020)
cl_r = (1.70 - 1.00)/2
tr = [0.10, 0.10, 0.10, 0.15, 0.05, 0.10, 0.15]   # normales (3 sigma)
xr = sum(mc_norm(0, t, g=rng_c) for t in tr) + mc_unif(-0.05, 0.05, g=rng_c)   # + juego del pasador
wc_r = sum(tr) + 0.05
report('C1 radial (desvío)', 0.0, -wc_r, wc_r, np.sqrt(sum(t*t for t in tr) + 0.05**2),
       np.abs(xr), lim=cl_r, sense='max')
# Axial: ojal colisado 2,6 con alambre Ø1,0 -> 0,80 por lado.
# Largo de pala (156 en v1, 206 en v2; recorte con plantilla, 0,20 en ambos casos),
# pegado de la pestaña con plantilla referida al pasador (0,15),
# posición axial de la bisagra en el cubo (0,10), del anillo en el cuerpo (0,15),
# alambre en el anillo (0,10).
cl_z = (2.60 - 1.00)/2
tz_sin = [0.20, 0.15, 0.10, 0.15, 0.10, 0.30]   # 0,30: pegado libre a ojo
tz_con = [0.20, 0.15, 0.10, 0.15, 0.10]
print(f'(C2: largo de pala {L_PALA} mm con tolerancia de recorte de 0,20 mm)')
for lab, tz in (('sin plantilla', tz_sin), ('con plantilla', tz_con)):
    xz = sum(mc_norm(0, t, g=rng_c) for t in tz)
    report(f'C2 axial {lab}', 0.0, -sum(tz), sum(tz), np.sqrt(sum(t*t for t in tz)), np.abs(xz),
           lim=cl_z, sense='max')
# Tangencial: enganche nominal 2,5 mm de alambre más allá de la pestaña.
# Azimut de la pestaña: ranura 1,2 con pestaña 0,5 (+-0,35 uniforme), azimut de la
# ranura (0,10), posición del alambre en el anillo (0,10), tope mecánico del anillo (0,10).
eng_nom = 2.5
xt = mc_unif(-0.35, 0.35, g=rng_c) + mc_norm(0, 0.10, g=rng_c) + mc_norm(0, 0.10, g=rng_c) + mc_norm(0, 0.10, g=rng_c)
eng = eng_nom - np.abs(xt)
report('C3 enganche tang.', eng_nom, eng_nom-0.65, eng_nom, np.sqrt(0.35**2+3*0.1**2), eng,
       lim=1.5)
# con tope fijado solo por el servo (resolución +-1 grado a r=36,5 mm = +-0,64 mm)
xt2 = xt + mc_unif(-0.64, 0.64, g=rng_c)
eng2 = eng_nom - np.abs(xt2)
report('C3b enganche (servo)', eng_nom, eng_nom-1.29, eng_nom, np.sqrt(0.35**2+3*0.1**2+0.64**2),
       eng2, lim=1.5)

with open(os.path.join(D, 'fabricacion_tol.dat'), 'w') as f:
    f.write('cadena nom wc_lo wc_hi rss mc_lo mc_hi pfalla\n')
    for r in res:
        f.write(r[0].replace(' ', '_') + ' ' + ' '.join(f'{v:.4f}' for v in r[1:]) + '\n')
