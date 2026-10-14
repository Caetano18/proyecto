"""Capítulo 13: arranque del rotor en autorrotación.

Reutiliza bemt_modelo.py (sin modificarlo). Genera analysis/data/arranque_*.dat.
Uso: python3 arranque_estudios.py
"""
import os
import sys
import numpy as np
from scipy.interpolate import RegularGridInterpolator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bemt_modelo as b  # noqa: E402

DATA = b.DATA
QF = 0.73e-3                       # rozamiento de rodamientos [N.m] (cap. 14)
TH_REG = -3.0
# inercias (cap. 15): I_b alrededor de la bisagra, inercia polar con palas abiertas ~5e-4
IB, MB, XG, E, LB = 4.35e-5, 0.0074, 0.070, b.E, 0.156
SB = MB * XG
B = 4
IHUB = 5.0e-4 - B * (IB + 2 * SB * E + MB * E**2)
BETA_TOPE = np.radians(15.0)
CDC, MR = 1.2, 0.005


def guardar(nombre, cab, filas, fmt='%.6g'):
    fn = os.path.join(DATA, 'arranque_' + nombre + '.dat')
    with open(fn, 'w') as f:
        f.write(' '.join(cab) + '\n')
        for fila in filas:
            f.write(' '.join('nan' if (isinstance(x, float) and np.isnan(x)) else fmt % x for x in fila) + '\n')


def log(*a):
    print(*a)
    sys.stdout.flush()


def Iz(beta):
    return IHUB + B * (IB * np.cos(beta)**2 + 2 * SB * E * np.cos(beta) + MB * E**2)


def Q_(rot, o, V):
    return b.bemt(rot, o, V)['Q']


# ------------------------------------------------------------------ 1. física
def fisica():
    rot = b.Rotor(theta=TH_REG)
    idx = [int(round((x * b.R - b.E) / (b.R - b.E) * rot.N - 0.5)) for x in (0.3, 0.5, 0.75, 0.95)]
    filas = []
    for o in np.r_[0:40:2, 40:260:5]:
        out = b.bemt(rot, o, 13.4)
        filas.append([o] + [out['alpha'][i] for i in idx] + [out['phi'][idx[2]], out['Q'] * 1e3,
                                                              out['cl'][idx[2]], out['cd'][idx[2]]])
    guardar('alfa', ['Om', 'a30', 'a50', 'a75', 'a95', 'phi75', 'Q', 'cl75', 'cd75'], filas)
    # curvas Q(Omega)
    Om = np.r_[-40:0:4, 0:60:3, 60:420:10]
    cols, filas = ['Om'], []
    casos = [('V4', TH_REG, 4.0, None), ('V694', TH_REG, 6.94, None), ('V10', TH_REG, 10.0, None),
             ('V134', TH_REG, 13.4, None), ('V16', TH_REG, 16.0, None),
             ('t0', 0.0, 13.4, None), ('t1', 1.0, 13.4, None), ('t1V5', 1.0, 5.0, None),
             ('tm3_2D', TH_REG, 13.4, b.polar_2d())]
    res = {}
    for nm, th, V, pol in casos:
        rot = b.Rotor(theta=th, polar=pol)
        res[nm] = [Q_(rot, o, V) * 1e3 for o in Om]
        cols.append(nm)
    for k, o in enumerate(Om):
        filas.append([o] + [res[nm][k] for nm in cols[1:]])
    guardar('qomega', cols, filas)
    # Q0 frente a V y paso (base y 2D)
    filas = []
    for V in np.arange(3, 17.1, 1.0):
        fila = [V]
        for th in (-6, -4, -3, -2, -1):
            fila.append(Q_(b.Rotor(theta=th), 0.0, V) * 1e3)
        fila.append(Q_(b.Rotor(theta=-3, polar=b.polar_2d()), 0.0, V) * 1e3)
        filas.append(fila)
    guardar('q0', ['V', 'tm6', 'tm4', 'tm3', 'tm2', 'tm1', 'tm3_2D'], filas)
    log('Q0(13.4, -3)=%.2f  Q0(6.94,-3)=%.2f' % (filas[10][3], Q_(b.Rotor(theta=-3), 0, 6.94) * 1e3))


# ------------------------------------------------------------------ 2. mapa
OM_MAPA = np.r_[0, 3, 6, 10, 15, 20, 26, 33, 40, 50, 60, 75, 90, 110, 135, 165, 200, 250, 320, 420]


def arranca(rot, V, qf):
    q = np.array([Q_(rot, o, V) for o in OM_MAPA]) - qf
    if q[0] <= 0:
        return False
    s = np.sign(q)
    return np.count_nonzero(np.diff(s)) <= 1


def th_critico(V, qf, twist=0.0, pol=None, lo=-10.0, hi=4.0):
    if not arranca(b.Rotor(theta=lo, twist=twist, polar=pol), V, qf):
        return np.nan
    if arranca(b.Rotor(theta=hi, twist=twist, polar=pol), V, qf):
        return hi
    for _ in range(7):
        m = 0.5 * (lo + hi)
        if arranca(b.Rotor(theta=m, twist=twist, polar=pol), V, qf):
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def mapa():
    p2d = b.polar_2d()
    confs = [('f073', QF, 0, None), ('f034', 0.34e-3, 0, None), ('f17', 1.7e-3, 0, None),
             ('f5', 5e-3, 0, None), ('tw10', QF, 10, None), ('tw20', QF, 20, None), ('p2D', QF, 0, p2d)]
    filas = []
    for V in (4, 5, 6.94, 9, 11, 13.4, 16):
        fila = [V] + [th_critico(V, qf, tw, pol) for _, qf, tw, pol in confs]
        filas.append(fila)
        log('mapa V=%.2f' % V, ['%.2f' % x for x in fila[1:]])
    guardar('mapa', ['V'] + [c[0] for c in confs], filas)


# ------------------------------------------------------------------ 3. tablas y dinámica
OMT = np.array([-40, -25, -15, -8, -4, 0, 4, 8, 12, 16, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100,
                115, 130, 145, 160, 180, 200, 230, 260, 300, 350], float)
VT = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13.4, 15, 17], float)
THT = np.array([-10, -8, -6, -5, -4, -3, -2, -1, 0, 1], float)


def tabla(rot):
    out = np.zeros((len(OMT), len(VT), 2))
    for i, o in enumerate(OMT):
        for j, V in enumerate(VT):
            r = b.bemt(rot, o, V)
            out[i, j] = r['T'], r['Q']
    return out


class Mapa:
    """Interpolador de (T, Q) en (theta, Omega, V) o en (Omega, V) para un rotor fijo."""

    def __init__(self, tab3=None, tab2=None):
        if tab3 is not None:
            self.f = RegularGridInterpolator((THT, OMT, VT), tab3, bounds_error=False, fill_value=None)
            self.d3 = True
        else:
            self.f = RegularGridInterpolator((OMT, VT), tab2, bounds_error=False, fill_value=None)
            self.d3 = False

    def __call__(self, th, o, V):
        o = min(max(o, OMT[0]), OMT[-1]); V = min(max(V, VT[0]), VT[-1])
        if self.d3:
            th = min(max(th, THT[0]), THT[-1])
            return self.f([[th, o, V]])[0]
        return self.f([[o, V]])[0]


def beta_cono(T, o):
    """Conicidad cuasiestática (calibrada a 4,4 grados en el punto de diseño), limitada por el tope."""
    if o < 1:
        return BETA_TOPE
    bc = 0.80 * (T / B * 0.70 * LB - SB * b.G) / (IB * o * o + 1e-12)
    return float(np.clip(bc, 0.0, BETA_TOPE))


def sim(mp, th_fun=lambda o, beta: TH_REG, V0=13.4, Om0=0.0, qf=QF, apertura=True, tmax=8.0,
        dt=0.002, Qextra=lambda t, o: 0.0, guardar_hist=None):
    """Integra (I Omega)' = f Q - Qf + Qextra ; m V' = W - f T - k V^2 ; batimiento de apertura."""
    k = b.K_DROGUE + b.K_CUERPO
    xs = np.linspace(0, LB, 12)[1:] - LB / 22
    o, V, z = Om0, V0, 0.0
    beta, bdot = (np.radians(-89.0), 0.0) if apertura else (np.radians(4.4), 0.0)
    abierta = not apertura
    H, t = [], 0.0
    L = Iz(beta) * o
    while t < tmax - 1e-9:
        th = th_fun(o, beta)
        T, Q = mp(th, o, V)
        f = np.cos(beta)**2 if beta < 0 else 1.0
        qfr = qf * np.sign(o) if abs(o) > 1e-3 else np.clip(f * Q, -qf, qf)
        if not abierta:
            un = V * np.cos(beta) - bdot * (xs + 0)
            Ma = np.sum(0.5 * b.RHO * CDC * 0.045 * un * np.abs(un) * (xs + 0)) * (LB / 11)
            Mc = -o * o * np.sin(beta) * (IB * np.cos(beta) + SB * E)
            bdd = (Ma + Mc + MR - SB * b.G * np.cos(beta)) / IB
            bdot += bdd * dt
            beta += bdot * dt
            bc = beta_cono(T, o)
            if beta >= bc:
                abierta = True
                beta = bc
        else:
            beta = beta_cono(T, o)
        L += (f * Q - qfr + Qextra(t, o)) * dt
        o = L / Iz(beta)
        V += (b.W - f * T - k * V * V) / b.M * dt
        z += V * dt
        t += dt
        H.append((t, o, V, z, np.degrees(beta), th, f * Q * 1e3))
    H = np.array(H)
    of = H[-1, 1]
    i90 = np.argmax(H[:, 1] > 0.9 * of) if of > 20 else -1
    t90 = H[i90, 0] if i90 >= 0 and of > 20 else np.nan
    z90 = H[i90, 3] if i90 >= 0 and of > 20 else np.nan
    ia = np.argmax(H[:, 4] > 0) if apertura else 0
    if guardar_hist:
        guardar('hist_' + guardar_hist, ['t', 'Om', 'V', 'z', 'beta', 'th', 'Q'], H[::10])
    return dict(t90=t90, z90=z90, Of=of, Vf=H[-1, 2], tap=H[ia, 0], H=H)


def dinamica():
    log('tablas...')
    tab3 = np.array([tabla(b.Rotor(theta=th)) for th in THT])
    M3 = Mapa(tab3=tab3)
    M_tw10 = Mapa(tab2=tabla(b.Rotor(theta=TH_REG, twist=10)))
    M_tw20 = Mapa(tab2=tabla(b.Rotor(theta=-1.0, twist=20)))
    M_2d = Mapa(tab2=tabla(b.Rotor(theta=TH_REG, polar=b.polar_2d())))
    # flap/pestaña de borde de fuga: -4 grados efectivos en la mitad externa (sólo arranque)
    rf = b.Rotor(theta=TH_REG)
    rf.th = rf.th + np.radians(np.where(rf.r > 0.5 * (b.R + b.E), -4.0, 0.0))
    M_flap = Mapa(tab2=tabla(rf))
    filas, res = [], {}

    def caso(nombre, desc, *a, **kw):
        r = sim(*a, **kw)
        res[nombre] = r
        filas.append((len(filas) + 1, r['t90'], r['z90'], r['Of'], r['Vf'], r['tap']))
        log('%2d %-10s %-45s t90=%5.2f z90=%5.1f Of=%6.1f Vf=%5.2f tap=%.3f' %
            (len(filas), nombre, desc, r['t90'], r['z90'], r['Of'], r['Vf'], r['tap']))

    fix = lambda th: (lambda o, beta: th)
    caso('base', 'th=-3, apertura, Qf=0,73', M3, guardar_hist='base')
    caso('qs', 'th=-3 sin apertura (cuasiest. cap 12)', M3, apertura=False, guardar_hist='qs')
    caso('tm2', 'th=-2', M3, th_fun=fix(-2))
    caso('tm4', 'th=-4', M3, th_fun=fix(-4))
    caso('tm5', 'th=-5', M3, th_fun=fix(-5), guardar_hist='tm5')
    caso('tm6', 'th=-6', M3, th_fun=fix(-6))
    caso('tw10', 'th=-3 torsion +10 (raiz -8,3)', M_tw10)
    caso('tw20', 'th=-1 torsion +20', M_tw20)
    caso('flap', 'flap -4 en mitad externa (equivalente)', M_flap)
    caso('2D', 'polar 2D (CDmax 1,98)', M_2d)
    caso('f034', 'Qf=0,34', M3, qf=0.34e-3)
    caso('f17', 'Qf=1,7', M3, qf=1.7e-3)
    caso('V16', 'liberacion a 16 m/s', M3, V0=16.0)
    caso('V10', 'liberacion a 10 m/s', M3, V0=10.0)
    caso('V7', 'liberacion a 6,94 m/s', M3, V0=6.94)
    # paso colectivo variable pasivo: -8 a Omega=0 -> -3 por encima de 80 rad/s
    var = lambda o, beta: TH_REG + (-8 - TH_REG) * max(0.0, 1 - (max(o, 0) / 80.0)**2)
    caso('var', 'paso variable -8 -> -3 (Om_s=80)', M3, th_fun=var, guardar_hist='var')
    # delta-3: theta = -3 - tan(d3) (beta - 4,4)
    for d3 in (30, 45):
        d3f = (lambda d: (lambda o, beta: TH_REG - np.tan(np.radians(d)) * (np.degrees(max(beta, 0.0)) - 4.4)))(d3)
        caso('d3_%d' % d3, 'delta-3 = %d grados' % d3, M3, th_fun=d3f, guardar_hist='d3_%d' % d3)
    # motor pequeño: 3 mN.m durante 1 s
    caso('motor', 'motor 3 mN.m durante 1 s', M3, Qextra=lambda t, o: 3e-3 if t < 1.0 else 0.0)
    # pre-rotacion (resorte) para th=-3 y th=+1, aplicada con palas abiertas (sin apertura)
    for Om0 in (20, 40, 80):
        caso('res%d' % Om0, 'resorte Om0=%d th=-3' % Om0, M3, apertura=False, Om0=float(Om0))
    caso('t1', 'th=+1 sin ayuda', M3, th_fun=fix(1.0), guardar_hist='t1')
    caso('t0', 'th=0 sin ayuda', M3, th_fun=fix(0.0))
    guardar('casos', ['n', 't90', 'z90', 'Of', 'Vf', 'tap'], filas)
    # Omega0 mínimo para th=+1 y th=0 (palas abiertas al soltar el resorte) a varias V
    filas = []
    for V0 in (6.94, 10.0, 13.4, 16.0):
        fila = [V0]
        for th in (0.0, 1.0):
            lo, hi = 0.0, 150.0
            if sim(M3, th_fun=fix(th), V0=V0, Om0=hi, apertura=False, tmax=4)['Of'] < 50:
                fila.append(np.nan); continue
            for _ in range(9):
                m = 0.5 * (lo + hi)
                if sim(M3, th_fun=fix(th), V0=V0, Om0=m, apertura=False, tmax=4)['Of'] > 50:
                    hi = m
                else:
                    lo = m
            fila.append(hi)
        filas.append(fila)
        log('Om0 min V0=%.2f' % V0, fila[1:])
    guardar('om0min', ['V0', 't0', 't1'], filas)
    # t90 frente a Om0 (resorte) para th=-3 con apertura despues del resorte (palas abiertas)
    filas = []
    for Om0 in (0, 10, 20, 30, 40, 60, 80, 100, 120):
        r = sim(M3, Om0=float(Om0), apertura=False, tmax=6)
        filas.append((Om0, r['t90'], r['z90'], 0.5 * 5e-4 * Om0**2))
    guardar('resorte', ['Om0', 't90', 'z90', 'E'], filas)
    log('resorte', filas)
    # t90 frente al paso (fijo)
    filas = []
    for th in (-10, -8, -6, -5, -4, -3, -2, -1, -0.5):
        r = sim(M3, th_fun=fix(th), tmax=10)
        filas.append((th, r['t90'], r['z90'], r['Of'], r['Vf']))
    guardar('tpaso', ['th', 't90', 'z90', 'Of', 'Vf'], filas)
    log('tpaso', filas)


if __name__ == '__main__':
    et = sys.argv[1:] or ['fisica', 'mapa', 'dinamica']
    for e in et:
        globals()[e]()
