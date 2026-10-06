#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estudios con el modelo BEMT (ver bemt_modelo.py). Genera analysis/data/bemt_*.dat.
Uso: python3 analysis/bemt_estudios.py [etapa ...]
  etapas: curvas valid barrido modelos dist qomega torsion mapa locus transitorio
"""
import os, sys, json, time
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bemt_modelo as b
from bemt_modelo import Rotor, bemt, TQ, equilibrio, raices_Q, guardar, log

THETA_REC = -3.0          # paso recomendado (se fija tras el barrido)
THETAS = list(range(-8, 3))
CACHE = os.path.join(b.DATA, 'bemt_cache.json')


def resumen(e, rot):
    if e is None:
        return None
    o = e['out']
    w = o['dT'] * rot.dr
    i75 = np.argmin(np.abs(o['r'] - 0.75 * rot.R))
    zona_imp = o['r'][o['dQ'] > 0]
    return dict(V=e['V'], rpm=e['rpm'], Om=e['Om'], CR=e['CR'], Vvh=e['Vvh'], T=e['T'],
                vh=e['vh'], dQdOm=e['dQdOm'], alpha75=float(o['alpha'][i75]),
                cl75=float(o['cl'][i75]), re75=float(o['re'][i75]),
                clT=float(np.sum(o['cl'] * w) / np.sum(w)), a_med=float(np.sum(o['a'] * w) / np.sum(w)),
                vtip=e['Om'] * rot.R, imp_ini=float(zona_imp.min()) if len(zona_imp) else np.nan,
                imp_fin=float(zona_imp.max()) if len(zona_imp) else np.nan,
                nfp=int(o['nfp']))


def arranque(rot, V=b.V_ETAPA1):
    """Par a Omega=0, y diagnóstico de rama lenta: raíces de Q(Omega) a V dada."""
    raices, Oms, Qs = raices_Q(rot, V)
    est = [o for o, dq in raices if dq < 0]
    ines = [o for o, dq in raices if dq > 0]
    Q0 = Qs[0]
    # el rotor arranca solo si Q(0) > 0; queda trabado si la primera raíz es estable y
    # hay otra estable más rápida (rama lenta), o si Q(0) <= 0.
    if Q0 <= 0:
        estado = 'no arranca'
    elif est and min(est) < max(est) - 1:
        estado = 'rama lenta'
    elif est:
        estado = 'arranca'
    else:
        estado = 'sin equilibrio'
    lim = min(est) if est else Oms[-1]
    Qmin = float(Qs[Oms <= lim].min())
    return dict(Q0=float(Q0), Qmin=Qmin, estado=estado,
                raices=[(float(o), float(d)) for o, d in raices], Om13=max(est) if est else np.nan)


def _caso(args):
    th, c, B, extra = args
    rot = Rotor(theta=th, c=c, B=B, **extra.get('rotor', {}))
    if extra.get('polar') == 'cd12':
        rot.polar = b.polar_base(1.2)
    elif extra.get('polar') == 're50':
        rot.polar = b.polar_re50()
    elif extra.get('polar') == '2d':
        rot.polar = b.polar_2d()
    out = {}
    e = equilibrio(rot, drogue=True)
    out['con'] = resumen(e, rot)
    if extra.get('sin', False):
        out['sin'] = resumen(equilibrio(rot, drogue=False), rot)
    if extra.get('arr', True):
        out['arr'] = arranque(rot)
    return (th, c, B, extra.get('tag', 'base')), out


def cargar_cache():
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    return {}


def guardar_cache(C):
    json.dump(C, open(CACHE, 'w'), indent=0)


def correr(casos, C):
    pend = [x for x in casos if json.dumps(x[:3] + (x[3].get('tag', 'base'),)) not in C]
    log('casos pendientes:', len(pend))
    t = time.time()
    with Pool(3) as p:
        for k, out in p.imap_unordered(_caso, pend):
            C[json.dumps(k)] = out
            log(k, out['con']['V'] if out['con'] else None, '%.0fs' % (time.time() - t))
            guardar_cache(C)
    return C


def get(C, th, c, B, tag='base'):
    return C.get(json.dumps((th, c, B, tag)))

# ----------------------------------------------------------------------------- etapas


def et_curvas():
    a = np.linspace(-0.2, 1.6, 361)
    ctm = 4 * a * (1 - a)
    glau = np.where(a <= 0.4, ctm, 0.889 - (0.0203 - (a - 0.143)**2) / 0.6427)
    filas = []
    for ai, m, g in zip(a, ctm, glau):
        filas.append((ai, m, g, float(b.ct_curve(ai, 1.0, 'buhl')), float(b.ct_curve(ai, 1.0, 'heli')),
                      float(b.ct_curve(ai, 0.9, 'buhl')), float(b.ct_curve(ai, 0.9, 'heli'))))
    guardar('curvas', ['a', 'CTmom', 'CTglauert', 'CTbuhl', 'CTheli', 'CTbuhl09', 'CTheli09'], filas)
    log('a_x =', b.A_X, 'S_X =', b.S_X, 'CT(a_x)=', b.HELI_CT[0])
    for aa in [0.5, 0.6, 0.8, 1.0, 1.2]:
        log('a=%.1f  heli %.3f  buhl %.3f' % (aa, b.ct_curve(aa, 1, 'heli'), b.ct_curve(aa, 1, 'buhl')))


def et_valid():
    res = {}
    # (1) caso analítico: polar lineal, sin pérdidas, solo cantidad de movimiento (molino frenante, a < 0,4)
    from scipy.optimize import brentq
    rot = Rotor(B=2, c=0.020, theta=-4.0, polar=b.PolarLineal(0.0), modelo='mom', perdidas=False, N=40)
    V, Om = 8.0, 250.0
    o = bemt(rot, Om, V)
    lam_inf = V / (Om * rot.R)
    sa = rot.B * rot.c / (np.pi * rot.R) * 2 * np.pi
    x = rot.r / rot.R
    th = rot.th
    bq = (lam_inf - sa / 8)
    lam = (bq + np.sqrt(bq**2 - sa * th * x / 2)) / 2          # ángulos pequeños
    a_an = 1 - lam / lam_inf
    dT_an = 4 * np.pi * rot.r * b.RHO * V**2 * a_an * (1 - a_an)
    # solución exacta independiente (escalar, sin la rutina vectorial)
    a_ex = []
    for k in range(rot.N):
        def g(aa):
            up, ut = V * (1 - aa), Om * rot.r[k]
            ph = np.arctan2(up, ut)
            cl = 2 * np.pi * (ph + rot.th[k])
            return rot.sig[k] * cl * np.cos(ph) * (up**2 + ut**2) / V**2 - 4 * aa * (1 - aa)
        a_ex.append(brentq(g, 0.0, 0.5, xtol=1e-14))
    a_ex = np.array(a_ex)
    dT_ex = 4 * np.pi * rot.r * b.RHO * V**2 * a_ex * (1 - a_ex)
    filas = [(xi, ai, an, ae, dTi, dTa, dTe) for xi, ai, an, ae, dTi, dTa, dTe in zip(x, o['a'], a_an, a_ex, o['dT'], dT_an, dT_ex)]
    guardar('valid_lineal', ['x', 'a_bemt', 'a_anal', 'a_exac', 'dT_bemt', 'dT_anal', 'dT_exac'], filas)
    res['lineal'] = dict(T_bemt=o['T'], T_anal=float(np.sum(dT_an * rot.dr)), T_exac=float(np.sum(dT_ex * rot.dr)),
                         err_a_exac=float(np.max(np.abs(o['a'] - a_ex))), err_a_anal=float(np.max(np.abs(o['a'] - a_an))),
                         amin=float(o['a'].min()), amax=float(o['a'].max()), phimax=float(o['phi'].max()))
    # (2) autorrotación ideal: Cd = 0, sin pérdidas, curva de helicópteros
    rot2 = Rotor(theta=-3.0, polar=b.PolarLineal(0.0, -6.0), modelo='heli', perdidas=False, N=40)
    V = 6.5
    rr, _, _ = raices_Q(rot2, V, Om_max=2000)
    Omq = max(o for o, d in rr if d < 0)
    o2 = bemt(rot2, Omq, V)
    guardar('valid_ideal', ['x', 'a', 'phi', 'dQ'], [(o2['r'][k] / b.R, o2['a'][k], o2['phi'][k], o2['dQ'][k] * 1e3) for k in range(rot2.N)])
    res['ideal'] = dict(Om=Omq, CR=o2['T'] / (0.5 * b.RHO * V**2 * b.A_DISC),
                        a_min=float(o2['a'].min()), a_max=float(o2['a'].max()),
                        CR_teo=float(4 / b.brentq(lambda s: b._fpoly(-s) - s, 1.5, 2)**2))
    # (3) convergencia en número de anillos y (4) historia de iteración, punto base
    rot3 = Rotor(theta=THETA_REC)
    e = equilibrio(rot3)
    filas = []
    for N in [5, 10, 20, 40, 80, 160, 320]:
        r = rot3.copia(N=N)
        T, Q = TQ(r, e['Om'], e['V'])
        filas.append((N, T, Q * 1e3))
    guardar('malla', ['N', 'T', 'Qmili'], filas)
    o3 = bemt(rot3, e['Om'], e['V'], hist=True, itmax=200)
    guardar('hist', ['it', 'res'], [(i + 1, h) for i, h in enumerate(o3['hist'])])
    o4 = bemt(rot3.copia(modelo='buhl'), e['Om'], e['V'], hist=True, itmax=200)
    guardar('hist_buhl', ['it', 'res'], [(i + 1, h) for i, h in enumerate(o4['hist'])])
    res['malla'] = filas
    res['hist'] = dict(it=int(o3['it']), nfp=int(o3['nfp']), it_buhl=int(o4['it']), nfp_buhl=int(o4['nfp']))
    # verificación independiente: bisección pura
    lo = np.full(rot3.N, -1.0); hi = np.full(rot3.N, 4.0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        rr, _, _ = b._residuo(rot3, e['Om'], e['V'], mid, np.zeros(rot3.N))
        lo = np.where(rr > 0, mid, lo); hi = np.where(rr > 0, hi, mid)
    o5 = bemt(rot3, e['Om'], e['V'])
    res['verif_biseccion'] = float(np.max(np.abs(0.5 * (lo + hi) - o5['a'])))
    # unicidad de raíces por anillo (barrido fino de a)
    A = np.linspace(-0.9, 3.9, 4801)
    nraices = []
    for k in range(rot3.N):
        aa = np.tile(o5['a'], (len(A), 1)); aa[:, k] = A
        rr = np.array([b._residuo(rot3, e['Om'], e['V'], aa[j], np.zeros(rot3.N))[0][k] for j in range(0, len(A), 4)])
        nraices.append(int(np.sum(np.sign(rr[1:]) != np.sign(rr[:-1]))))
    res['nraices'] = nraices
    json.dump(res, open(os.path.join(b.DATA, 'bemt_valid.json'), 'w'), indent=1)
    log(json.dumps(res, indent=1))


def et_barrido():
    C = cargar_cache()
    casos = []
    for th in THETAS:
        for c in [0.035, 0.045, 0.055]:
            for B in [3, 4, 5]:
                casos.append((th, c, B, dict(sin=(c == 0.045 and B == 4))))
    C = correr(casos, C)
    # tablas anchas para pgfplots
    def tabla(nombre, var, pares):
        filas = []
        cab = ['theta']
        for lab, _, _ in pares:
            cab += ['V_' + lab, 'rpm_' + lab, 'CR_' + lab, 'Q0_' + lab, 'Vvh_' + lab]
        for th in THETAS:
            fila = [th]
            for lab, c, B in pares:
                d = get(C, th, c, B)
                q = d['con'] if d else None
                fila += [q['V'] if q else np.nan, q['rpm'] if q else np.nan, q['CR'] if q else np.nan,
                         d['arr']['Q0'] * 1e3 if d else np.nan, q['Vvh'] if q else np.nan]
            filas.append(fila)
        guardar(nombre, cab, filas)
    tabla('theta_c', 'c', [('c35', 0.035, 4), ('c45', 0.045, 4), ('c55', 0.055, 4)])
    tabla('theta_B', 'B', [('B3', 0.045, 3), ('B4', 0.045, 4), ('B5', 0.045, 5)])
    filas = []
    for th in THETAS:
        d = get(C, th, 0.045, 4)
        s = d.get('sin')
        filas.append((th, s['V'] if s else np.nan, s['rpm'] if s else np.nan, s['CR'] if s else np.nan))
    guardar('theta_sin', ['theta', 'V', 'rpm', 'CR'], filas)
    # tabla larga completa
    filas = []
    for th in THETAS:
        for c in [0.035, 0.045, 0.055]:
            for B in [3, 4, 5]:
                d = get(C, th, c, B)
                q = d['con']
                est = {'arranca': 1, 'rama lenta': 2, 'no arranca': 0, 'sin equilibrio': -1}[d['arr']['estado']]
                if q:
                    filas.append((th, c * 1e3, B, q['V'], q['rpm'], q['CR'], q['Vvh'], q['T'], q['alpha75'],
                                  q['cl75'], q['clT'], q['re75'], q['vtip'], q['a_med'], d['arr']['Q0'] * 1e3, est))
                else:
                    filas.append((th, c * 1e3, B) + (np.nan,) * 11 + (d['arr']['Q0'] * 1e3, est))
    guardar('barrido', ['theta', 'c', 'B', 'V', 'rpm', 'CR', 'Vvh', 'T', 'alpha75', 'cl75', 'clT', 're75',
                        'vtip', 'amed', 'Q0mili', 'arranque'], filas)


MODELOS = {
    'buhl': dict(rotor=dict(modelo='buhl')),
    'heli09': dict(rotor=dict(escala=0.8)),
    'heli11': dict(rotor=dict(escala=1.2)),
    'sinperd': dict(rotor=dict(perdidas=False)),
    'remolino': dict(rotor=dict(remolino=True)),
    're50': dict(polar='re50'),
    'cd12': dict(polar='cd12'),
    '2d': dict(polar='2d'),
}


def et_modelos():
    C = cargar_cache()
    casos = []
    for tag, ex in MODELOS.items():
        ths = THETAS if tag in ('buhl', 'cd12') else [-6, -4, -3, -2, -1, 0]
        for th in ths:
            d = dict(ex); d['tag'] = tag; d['sin'] = tag in ('buhl',)
            casos.append((th, 0.045, 4, d))
    C = correr(casos, C)
    filas = []
    for th in THETAS:
        fila = [th]
        for tag in ['base'] + list(MODELOS):
            d = get(C, th, 0.045, 4, tag)
            q = d['con'] if d else None
            fila += [q['V'] if q else np.nan, q['rpm'] if q else np.nan, q['CR'] if q else np.nan]
        filas.append(fila)
    cab = ['theta']
    for tag in ['base'] + list(MODELOS):
        cab += ['V_' + tag, 'rpm_' + tag, 'CR_' + tag]
    guardar('modelos', cab, filas)


def et_dist():
    for tag, mod in [('heli', 'heli'), ('buhl', 'buhl')]:
        rot = Rotor(theta=THETA_REC, modelo=mod, N=80)
        e = equilibrio(rot)
        o = e['out']
        zona = np.where(o['alpha'] > 7.5, 2, np.where(o['dQ'] > 0, 1, 0))
        filas = [(o['r'][k], o['r'][k] / rot.R, o['a'][k], o['phi'][k], o['alpha'][k], o['cl'][k], o['cd'][k],
                  o['re'][k] / 1e3, o['dT'][k], o['dQ'][k] * 1e3, o['F'][k], zona[k],
                  o['cl'][k] / max(o['cd'][k], 1e-6)) for k in range(rot.N)]
        guardar('dist_' + tag, ['r', 'x', 'a', 'phi', 'alpha', 'cl', 'cd', 'rek', 'dT', 'dQmili', 'F', 'zona', 'LD'], filas)
        log(tag, {k: v for k, v in e.items() if k != 'out'})
    # distribución a otros pasos (heli)
    filas = {}
    for th in [-6, -3, 0]:
        rot = Rotor(theta=th, N=80)
        e = equilibrio(rot)
        if e:
            filas[th] = e['out']
    r = rot.r
    guardar('dist_pasos', ['x', 'alpha_m6', 'alpha_m3', 'alpha_0', 'dQ_m6', 'dQ_m3', 'dQ_0'],
            [(r[k] / b.R,) + tuple(filas[t]['alpha'][k] for t in (-6, -3, 0)) +
             tuple(filas[t]['dQ'][k] * 1e3 for t in (-6, -3, 0)) for k in range(len(r))])


def et_qomega():
    rot = Rotor(theta=THETA_REC)
    Oms = np.linspace(0, 400, 81)
    Vs = [4.0, 6.0, 8.0, 10.0, 13.4, 16.0]
    filas = []
    for Om in Oms:
        fila = [Om]
        for V in Vs:
            fila.append(TQ(rot, Om, V)[1] * 1e3)
        filas.append(fila)
    guardar('qomega_V', ['Om'] + ['Q_V%s' % str(v).replace('.', 'p') for v in Vs], filas)
    ths = [-8, -6, -4, -3, -2, -1, 0, 1, 2]
    filas = []
    for Om in Oms:
        fila = [Om]
        for th in ths:
            fila.append(TQ(rot.copia(theta=th), Om, 13.4)[1] * 1e3)
        fila.append(TQ(Rotor(theta=THETA_REC, polar=b.polar_2d()), Om, 13.4)[1] * 1e3)
        filas.append(fila)
    guardar('qomega_th', ['Om'] + ['Q_t%d' % t if t >= 0 else 'Q_tm%d' % -t for t in ths] + ['Q_2d'], filas)
    # par a Omega = 0 frente al paso: BEMT y ecuación simplificada eq:Q0
    filas = []
    for th in np.arange(-8, 2.01, 0.5):
        Qb = TQ(rot.copia(theta=th), 0.0, 13.4)[1]
        Qb2 = TQ(Rotor(theta=th, polar=b.polar_2d()), 0.0, 13.4)[1]
        Qs = 4 * 0.5 * b.RHO * 13.4**2 * 0.045 * (-np.sin(2 * np.radians(th))) * (b.R**2 - b.E**2) / 2
        filas.append((th, Qb * 1e3, Qb2 * 1e3, Qs * 1e3))
    guardar('q0', ['theta', 'Q0', 'Q0_2d', 'Q0_simple'], filas)


def et_torsion():
    C = cargar_cache()
    casos = []
    for th in [-4, -3, -2]:
        for tw in range(-8, 9, 2):
            casos.append((th, 0.045, 4, dict(rotor=dict(twist=float(tw)), tag='tw%d' % tw)))
    C = correr(casos, C)
    filas = []
    for tw in range(-8, 9, 2):
        fila = [tw]
        for th in [-4, -3, -2]:
            d = get(C, th, 0.045, 4, 'tw%d' % tw)
            q = d['con']
            fila += [q['V'] if q else np.nan, q['rpm'] if q else np.nan, q['CR'] if q else np.nan,
                     d['arr']['Q0'] * 1e3, d['arr']['Qmin'] * 1e3]
        filas.append(fila)
    cab = ['tw']
    for th in [-4, -3, -2]:
        s = 'm%d' % -th
        cab += ['V_' + s, 'rpm_' + s, 'CR_' + s, 'Q0_' + s, 'Qmin_' + s]
    guardar('torsion', cab, filas)


def _mapa_fila(args):
    th, Om = args
    rot = Rotor(theta=th)
    return [(Om, V, *TQ(rot, Om, V)) for V in np.arange(2.0, 16.001, 0.5)]


def et_mapa():
    Oms = np.arange(0, 200.001, 5.0)
    with Pool(3) as p:
        filas = sum(p.map(_mapa_fila, [(THETA_REC, o) for o in Oms]), [])
    filas.sort(key=lambda f: (f[0], f[1]))
    fn = os.path.join(b.DATA, 'bemt_mapa.dat')
    with open(fn, 'w') as f:
        f.write('Omega V T Q\n')
        for fila in filas:
            f.write('%.1f %.2f %.6f %.7f\n' % fila)
    log('mapa', len(filas))


def et_locus():
    """Lugar Q=0 en el plano (Omega, V) para varios pasos y curva de equilibrio vertical."""
    Vs = np.arange(3.0, 16.01, 0.5)
    out = {}
    for th in [-6, THETA_REC, -1, 0, 1]:
        rot = Rotor(theta=th)
        rows = []
        for V in Vs:
            r, _, _ = raices_Q(rot, V, Om_max=700)
            rows.append([(o, d) for o, d in r])
        out[th] = rows
        log(th, [(V, [round(o) for o, _ in r]) for V, r in zip(Vs, rows)])
    for th, rows in out.items():
        filas = []
        for V, r in zip(Vs, rows):
            est = sorted([o for o, d in r if d < 0]); ine = sorted([o for o, d in r if d > 0])
            filas.append((V, est[-1] if est else np.nan, est[0] if len(est) > 1 else np.nan,
                          ine[0] if ine else np.nan))
        guardar('locus_t%s' % (('m%d' % -th) if th < 0 else str(int(th))), ['V', 'Om_est', 'Om_lento', 'Om_inest'], filas)


def et_transitorio():
    """Integración cuasi estacionaria del arranque con el mapa (I dOm/dt = Q, m dV/dt = W - T - kV^2)."""
    from scipy.interpolate import RegularGridInterpolator
    from scipy.integrate import solve_ivp
    d = np.loadtxt(os.path.join(b.DATA, 'bemt_mapa.dat'), skiprows=1)
    Om = np.unique(d[:, 0]); V = np.unique(d[:, 1])
    Tm = d[:, 2].reshape(len(Om), len(V)); Qm = d[:, 3].reshape(len(Om), len(V))
    fT = RegularGridInterpolator((Om, V), Tm, bounds_error=False, fill_value=None)
    fQ = RegularGridInterpolator((Om, V), Qm, bounds_error=False, fill_value=None)
    I = 5.1e-4
    k = b.K_DROGUE + b.K_CUERPO
    def rhs(t, y):
        o, v = y
        p = [[min(max(o, 0), 200), min(max(v, 2), 16)]]
        return [fQ(p)[0] / I, (b.W - fT(p)[0] - k * v * v) / b.M]
    sol = solve_ivp(rhs, (0, 6), [0.0, 13.4], max_step=0.01, dense_output=True)
    t = np.linspace(0, 6, 241)
    y = sol.sol(t)
    T = [fT([[min(max(o, 0), 200), v]])[0] for o, v in zip(*y)]
    guardar('transitorio', ['t', 'Om', 'V', 'rpm', 'T'], [(ti, o, v, o * 30 / np.pi, Ti) for ti, o, v, Ti in zip(t, y[0], y[1], T)])
    i90 = np.argmax(y[0] > 0.9 * y[0][-1])
    log('transitorio: Om final %.1f V final %.2f t90 %.2f s' % (y[0][-1], y[1][-1], t[i90]))


ETAPAS = dict(curvas=et_curvas, valid=et_valid, barrido=et_barrido, modelos=et_modelos, dist=et_dist,
              qomega=et_qomega, torsion=et_torsion, mapa=et_mapa, locus=et_locus, transitorio=et_transitorio)


def main():
    et = sys.argv[1:] or list(ETAPAS)
    for e in et:
        t = time.time()
        log('=== etapa', e)
        ETAPAS[e]()
        log('=== fin', e, '%.0f s' % (time.time() - t))


if __name__ == '__main__':
    main()
