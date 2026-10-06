#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo BEMT (elemento de pala + cantidad de movimiento) del rotor libre del CanSat
en autorrotación vertical (descenso axial).

Convención (igual que el capítulo de teoría):
  V      velocidad de descenso (>0); el aire llega al rotor desde abajo.
  a      factor de inducción axial: el flujo neto a través del anillo es V(1-a)
         (a = vi/V; a = 1 es la autorrotación ideal, flujo neto nulo).
  phi    ángulo de flujo = atan2(V(1-a), Omega r(1+a'))
  alpha  = phi + theta(r)    (theta < 0: borde de ataque hacia abajo)
  dT = B 1/2 rho U^2 c (Cl cos phi + Cd sin phi) dr      (empuje hacia arriba)
  dQ = B 1/2 rho U^2 c (Cl sin phi - Cd cos phi) r dr    (par impulsor > 0)

Cierre de cantidad de movimiento local, CT_loc = dT / (1/2 rho V^2 2 pi r dr):
  'heli'  : teoría de cantidad de movimiento (molino frenante) para a <= a_x y la
            curva empírica de helicópteros en descenso (polinomio de Leishman, ajuste a
            Castles y Gray 1951 y otros) para a > a_x, multiplicadas por F.
  'buhl'  : Glauert corregido por Buhl (2005), con F dentro de la fórmula (turbinas).
  'mom'   : solo cantidad de movimiento 4aF(1-a) (inválida para a > 0,5; referencia).
Pérdidas de punta y raíz de Prandtl: F = F_punta * F_raiz.

Solución por anillo: iteración de punto fijo en a con relajación adaptativa,
verificación del residuo y respaldo por bisección si no converge.

Uso: python3 analysis/bemt_modelo.py   (genera analysis/data/bemt_*.dat)
"""
import os, sys, time
import numpy as np
from scipy.optimize import brentq

AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(AQUI, 'data')

# ---------------------------------------------------------------- datos base
RHO, NU, G = 1.225, 1.5e-5, 9.81
M = 0.500
W = M * G
R, E = 0.200, 0.044
A_DISC = np.pi * R**2
K_DROGUE = 0.5 * RHO * 0.8 * np.pi * 0.25**2 / 4      # N/(m/s)^2
K_CUERPO = 0.5 * RHO * 0.8 * np.pi * 0.095**2 / 4
V_ETAPA1 = 13.4

# ---------------------------------------------------------------- polares
RE_LIST = [20e3, 35e3, 50e3, 75e3, 100e3]


def _load(fn):
    d = np.loadtxt(os.path.join(DATA, fn), skiprows=1)
    return d[:, 0], d[:, 1], d[:, 2]


class Polar:
    """Polar extendida (-180..180, paso 0,5 grados) interpolada linealmente en alpha
    y en log(Re) entre las tablas disponibles (fuera del rango: se congela)."""

    def __init__(self, archivos, res, cd_factor=1.0):
        cls, cds = [], []
        for fn in archivos:
            al, cl, cd = _load(fn)
            cls.append(cl); cds.append(cd)
        self.al0 = al[0]; self.dal = al[1] - al[0]; self.n = len(al)
        self.CL = np.array(cls); self.CD = np.array(cds) * cd_factor
        self.lre = np.log(np.array(res))

    def __call__(self, alpha_deg, re):
        a = (np.asarray(alpha_deg) + 180.0) % 360.0 - 180.0
        x = (a - self.al0) / self.dal
        i = np.clip(np.floor(x).astype(int), 0, self.n - 2)
        t = x - i
        if len(self.lre) == 1:
            cl = self.CL[0, i] * (1 - t) + self.CL[0, i + 1] * t
            cd = self.CD[0, i] * (1 - t) + self.CD[0, i + 1] * t
            return cl, cd
        lr = np.clip(np.log(np.maximum(re, 1.0)), self.lre[0], self.lre[-1])
        j = np.clip(np.searchsorted(self.lre, lr) - 1, 0, len(self.lre) - 2)
        u = (lr - self.lre[j]) / (self.lre[j + 1] - self.lre[j])
        def bil(T):
            v0 = T[j, i] * (1 - t) + T[j, i + 1] * t
            v1 = T[j + 1, i] * (1 - t) + T[j + 1, i + 1] * t
            return v0 * (1 - u) + v1 * u
        return bil(self.CL), bil(self.CD)


def polar_base(cd_factor=1.0):
    return Polar(['polares_ext_placa7_Re%d.dat' % int(r / 1e3) for r in RE_LIST], RE_LIST, cd_factor)


def polar_re50():
    return Polar(['polares_ext_placa7_Re50.dat'], [50e3])


def polar_2d():
    return Polar(['polares_ext_placa7_Re50_2D.dat'], [50e3])


class PolarLineal:
    """Polar sintética para validación: Cl = 2 pi (alpha - alpha0), Cd = cd0."""
    def __init__(self, cd0=0.0, alpha0=0.0):
        self.cd0, self.alpha0 = cd0, alpha0
    def __call__(self, alpha_deg, re):
        a = np.radians(np.asarray(alpha_deg) - self.alpha0)
        return 2 * np.pi * a, np.full_like(a, self.cd0)

# ---------------------------------------------------------------- inducción
KP = [1.15, -1.125, -1.372, -1.718, -0.655]   # Leishman (2006), ec. eq:poly


def _fpoly(x):
    return KP[0] + KP[1] * x + KP[2] * x**2 + KP[3] * x**3 + KP[4] * x**4


def _a_mom(s):
    return (s / 2 - np.sqrt(s * s / 4 - 1)) / s


S_X = brentq(lambda s: _a_mom(s) - _fpoly(-s) / s, 2.0, 2.2)   # cruce poli/molino
A_X = _a_mom(S_X)
_s = np.linspace(0.05, S_X, 4000)[::-1]
HELI_A = np.concatenate(([A_X], (_fpoly(-_s) / _s)[1:]))
HELI_CT = np.concatenate(([4 * A_X * (1 - A_X)], (4 / _s**2)[1:]))
assert np.all(np.diff(HELI_A) > 0) and np.all(np.diff(HELI_CT) > 0)


def ct_curve(a, F, modelo, escala=1.0):
    """CT local de cantidad de movimiento (con pérdidas F) para el factor a."""
    a = np.asarray(a, float)
    if modelo == 'mom':
        return 4 * a * F * (1 - a)
    if modelo == 'buhl':
        hi = 8 / 9 + (4 * F - 40 / 9) * a + (50 / 9 - 4 * F) * a**2
        return np.where(a <= 0.4, 4 * a * F * (1 - a), hi)
    if modelo == 'heli':
        ah = np.minimum(a, HELI_A[-1])
        hi = np.interp(ah, HELI_A, HELI_CT)
        # escala: multiplica el exceso sobre la rama de cantidad de movimiento
        hi = HELI_CT[0] + escala * (hi - HELI_CT[0])
        return F * np.where(a <= A_X, 4 * a * (1 - a), hi)
    raise ValueError(modelo)


def a_inv(ct, F, modelo, escala=1.0):
    """Inversa de ct_curve en a (rama de a creciente)."""
    ct = np.asarray(ct, float)
    if modelo == 'mom':
        q = np.clip(1 - ct / F, 0, None)
        return np.where(ct / F <= 1, (1 - np.sqrt(q)) / 2, 0.5)
    if modelo == 'buhl':
        c0 = 4 * F * 0.4 * 0.6
        lo = (1 - np.sqrt(np.clip(1 - ct / F, 0, None))) / 2
        A2 = 50 / 9 - 4 * F; A1 = 4 * F - 40 / 9; A0 = 8 / 9 - ct
        disc = np.clip(A1**2 - 4 * A2 * A0, 0, None)
        hi = (-A1 + np.sqrt(disc)) / (2 * A2)
        return np.where(ct <= c0, lo, hi)
    if modelo == 'heli':
        c = ct / F
        c0 = HELI_CT[0]
        lo = (1 - np.sqrt(np.clip(1 - c, 0, None))) / 2
        cc = c0 + (c - c0) / escala
        hi = np.interp(cc, HELI_CT, HELI_A, right=np.nan)
        # extrapolación de la rama alta (a grande, rotor casi parado: CT ~ a^2)
        ext = HELI_A[-1] * np.sqrt(np.maximum(cc, 1e-9) / HELI_CT[-1])
        hi = np.where(np.isnan(hi), ext, hi)
        return np.where(c <= c0, lo, hi)
    raise ValueError(modelo)

# ---------------------------------------------------------------- rotor


class Rotor:
    def __init__(self, B=4, c=0.045, theta=-3.0, twist=0.0, polar=None, modelo='heli',
                 escala=1.0, perdidas=True, remolino=False, N=40, R=R, e=E):
        self.B, self.c, self.theta, self.twist = B, c, theta, twist
        self.polar = polar if polar is not None else POLAR
        self.modelo, self.escala, self.perdidas, self.remolino = modelo, escala, perdidas, remolino
        self.R, self.e = R, e
        self.set_N(N)

    def set_N(self, N):
        self.N = N
        edges = np.linspace(self.e, self.R, N + 1)
        self.r = 0.5 * (edges[1:] + edges[:-1])
        self.dr = np.diff(edges)
        self.sig = self.B * self.c / (2 * np.pi * self.r)          # solidez local
        # paso referido a 0,75 R, torsión lineal en r/R
        self.th = np.radians(self.theta + self.twist * (self.r / self.R - 0.75))

    def copia(self, **kw):
        d = dict(B=self.B, c=self.c, theta=self.theta, twist=self.twist, polar=self.polar,
                 modelo=self.modelo, escala=self.escala, perdidas=self.perdidas,
                 remolino=self.remolino, N=self.N, R=self.R, e=self.e)
        d.update(kw)
        return Rotor(**d)


def _perdidas(rot, phi):
    if not rot.perdidas:
        return np.ones_like(phi)
    sp = np.maximum(np.abs(np.sin(phi)), 1e-6)
    ft = rot.B / 2 * (rot.R - rot.r) / (rot.r * sp)
    fr = rot.B / 2 * (rot.r - rot.e) / (rot.r * sp)
    Ft = 2 / np.pi * np.arccos(np.clip(np.exp(-ft), 0, 1))
    Fr = 2 / np.pi * np.arccos(np.clip(np.exp(-fr), 0, 1))
    return np.maximum(Ft * Fr, 1e-4)


def _seccion(rot, Om, V, a, ap):
    up = V * (1 - a)
    ut = Om * rot.r * (1 + ap)
    phi = np.arctan2(up, ut)
    U2 = up**2 + ut**2
    alpha = np.degrees(phi + rot.th)
    re = np.sqrt(U2) * rot.c / NU
    cl, cd = rot.polar(alpha, re)
    cn = cl * np.cos(phi) + cd * np.sin(phi)
    ctg = cl * np.sin(phi) - cd * np.cos(phi)
    return phi, U2, alpha, re, cl, cd, cn, ctg


def _residuo(rot, Om, V, a, ap):
    phi, U2, alpha, re, cl, cd, cn, ctg = _seccion(rot, Om, V, a, ap)
    F = _perdidas(rot, phi)
    ctbe = rot.sig * cn * U2 / V**2
    return ctbe - ct_curve(a, F, rot.modelo, rot.escala), ctbe, F


def bemt(rot, Om, V, a0=None, omega=0.3, tol=1e-9, itmax=200, hist=False):
    """Resuelve todos los anillos para (Omega, V). Devuelve dict con integrales y
    distribuciones. V > 0 (descenso)."""
    n = rot.N
    a = np.full(n, 0.5) if a0 is None else np.array(a0, float)
    ap = np.zeros(n)
    w = np.full(n, omega)
    H = []
    conv = np.zeros(n, bool)
    g_old = None
    lo = np.full(n, -1.0); hi = np.full(n, 4.0)      # intervalo de salvaguarda
    nbis = np.zeros(n, int)
    res_prev = np.full(n, np.inf)
    it = 0
    for it in range(1, itmax + 1):
        res, ctbe, F = _residuo(rot, Om, V, a, ap)
        ar = np.abs(res)
        if hist:
            H.append(ar.max())
        conv = ar < tol
        if conv.all():
            break
        # punto fijo: a_hat = inversa de la curva de cantidad de movimiento en CT_BE(a)
        ahat = a_inv(np.maximum(ctbe, -50), F, rot.modelo, rot.escala)
        ahat = np.where(ctbe < 0, (1 - np.sqrt(np.maximum(1 - ctbe / F, 0))) / 2, ahat)
        g = ahat - a
        # relajación dinámica de Aitken por anillo (factor acotado)
        if g_old is not None:
            dg = g - g_old
            ok = np.abs(dg) > 1e-14
            w = np.where(ok, -w * g_old * dg / np.where(ok, dg * dg, 1.0), w)
            w = np.clip(w, 1e-3, 1.0)
        g_old = g
        # salvaguarda: el residuo decrece con a; se actualiza el intervalo que contiene la raíz
        lo = np.where(res > 0, np.maximum(lo, a), lo)
        hi = np.where(res < 0, np.minimum(hi, a), hi)
        cand = a + w * g
        lento = ar > 0.7 * res_prev                    # el punto fijo no contrae: bisección
        res_prev = ar
        fuera = (cand <= lo) | (cand >= hi) | lento
        nbis += fuera & ~conv
        cand = np.where(fuera, 0.5 * (lo + hi), cand)
        a = np.where(conv, a, cand)
        if rot.remolino:
            phi, U2, alpha, re, cl, cd, cn, ctg = _seccion(rot, Om, V, a, ap)
            sp, cp = np.sin(phi), np.cos(phi)
            kk = rot.sig * ctg / (4 * F * np.where(np.abs(sp * cp) < 1e-4, 1e-4, sp * cp))
            apn = np.clip(kk / (1 - kk), -0.3, 0.3)
            ap = ap + 0.3 * (apn - ap)
    nfp = int(conv.sum()); fpok = conv.copy()
    # respaldo: bisección en los anillos no convergidos (o para verificación)
    if not conv.all():
        bad = ~conv
        lo = np.full(n, -1.0); hi = np.full(n, 4.0)
        for _ in range(55):
            mid = 0.5 * (lo + hi)
            r_, _, _ = _residuo(rot, Om, V, mid, ap)
            lo = np.where(r_ > 0, mid, lo); hi = np.where(r_ > 0, hi, mid)
        a = np.where(bad, 0.5 * (lo + hi), a)
    phi, U2, alpha, re, cl, cd, cn, ctg = _seccion(rot, Om, V, a, ap)
    F = _perdidas(rot, phi)
    q = 0.5 * RHO * U2 * rot.c * rot.B
    dT = q * cn
    dQ = q * ctg * rot.r
    T = np.sum(dT * rot.dr)
    Q = np.sum(dQ * rot.dr)
    out = dict(T=T, Q=Q, a=a, ap=ap, phi=np.degrees(phi), alpha=alpha, re=re, cl=cl, cd=cd,
               dT=dT, dQ=dQ, F=F, r=rot.r, it=it, nfp=nfp, U2=U2, fpok=fpok, nbis=nbis)
    if hist:
        out['hist'] = np.array(H)
    return out


def TQ(rot, Om, V):
    o = bemt(rot, Om, V)
    return o['T'], o['Q']

# ---------------------------------------------------------------- equilibrios


def raices_Q(rot, V, Om_max=500.0, n=40):
    """Todas las raíces de Q(Omega)=0 en (0, Om_max] para V dada; con su pendiente."""
    Oms = np.concatenate(([0.0], np.geomspace(2.0, Om_max, n)))
    Qs = np.array([TQ(rot, o, V)[1] for o in Oms])
    raices = []
    for k in range(len(Oms) - 1):
        if Qs[k] == 0 or Qs[k] * Qs[k + 1] < 0:
            o = brentq(lambda x: TQ(rot, x, V)[1], Oms[k], Oms[k + 1], xtol=1e-4)
            dq = (TQ(rot, o * 1.01, V)[1] - TQ(rot, o * 0.99, V)[1]) / (0.02 * o)
            raices.append((o, dq))
    return raices, Oms, Qs


def omega_estable(rot, V, Om_max=500.0):
    r, _, _ = raices_Q(rot, V, Om_max)
    est = [o for o, dq in r if dq < 0]
    return (max(est) if est else np.nan), r


def equilibrio(rot, drogue=True, Vlo=2.5, Vhi=16.0):
    """V y Omega de equilibrio: Q=0 (rama estable más rápida) y T + D_drogue + D_cuerpo = W."""
    k = K_CUERPO + (K_DROGUE if drogue else 0.0)
    cache = {}

    def omV(V):
        if V not in cache:
            cache[V] = omega_estable(rot, V)[0]
        return cache[V]

    def f(V):
        o = omV(V)
        if np.isnan(o):
            return -W
        return TQ(rot, o, V)[0] + k * V**2 - W
    try:
        V = brentq(f, Vlo, Vhi, xtol=1e-4)
    except ValueError:
        return None
    o = omV(V)
    out = bemt(rot, o, V)
    T = out['T']
    vh = np.sqrt(T / (2 * RHO * rot.R**2 * np.pi))
    dq = (TQ(rot, o * 1.01, V)[1] - TQ(rot, o * 0.99, V)[1]) / (0.02 * o)
    return dict(V=V, Om=o, rpm=o * 60 / (2 * np.pi), T=T, CR=T / (0.5 * RHO * V**2 * np.pi * rot.R**2),
                vh=vh, Vvh=V / vh, dQdOm=dq, out=out, mu_tip=o * rot.R / V)


POLAR = polar_base()

# ---------------------------------------------------------------- salida


def guardar(nombre, cab, filas, fmt='%.6g'):
    fn = os.path.join(DATA, 'bemt_' + nombre + '.dat')
    with open(fn, 'w') as f:
        f.write(' '.join(cab) + '\n')
        for fila in filas:
            f.write(' '.join(('nan' if (isinstance(x, float) and np.isnan(x)) else fmt % x) for x in fila) + '\n')
    return fn


def log(*a):
    print(*a); sys.stdout.flush()


if __name__ == '__main__':
    import bemt_estudios
    bemt_estudios.main()
