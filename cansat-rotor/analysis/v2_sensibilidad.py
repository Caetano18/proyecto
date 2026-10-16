#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estudios de sensibilidad de la configuración v2.
A. V2 de régimen (rotor solo): elasticidades, tornado, Sobol (S1, ST) y PRCC.
B. Promedio global de C4 (incluye la etapa 1 y el transitorio).
D. Autonomía (E7) frente a los consumos y rendimientos.
E. Error de la altura de liberación (80 % del apogeo).
F. Masa de la etapa 2 (S1) y su efecto en V2, por arquitectura.
G. Margen de anillo de vórtices frente a ráfagas verticales.
Salida: analysis/data/sens_*.dat y sens_resumen.json.   Uso: python3 analysis/v2_sensibilidad.py
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2_config as cfg

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
G = 9.81
res = {}
rng = np.random.default_rng(20261016)


def guardar(nombre, cab, filas, fmt='%.6g'):
    with open(os.path.join(DATA, 'sens_' + nombre + '.dat'), 'w') as f:
        f.write(' '.join(cab) + '\n')
        for fila in filas:
            f.write(' '.join(fmt % x if not isinstance(x, str) else x for x in fila) + '\n')


# ---------------------------------------------------------------- modelo rápido de la etapa 2
# C_R de la BEMT: valor base y respuestas lineales a theta, cuerda y nº de palas medidas en el barrido (R = 0,25 m)
CR0, DCR_TH, DCR_C, DCR_B = 0.963, 0.0210, 0.00170, 0.0205     # por grado, por mm, por pala
A_C = np.pi * 0.045**2


def V2f(m2, R, rho, dCR, theta, c, B, Cdc):
    CR = CR0 * (1 + dCR) + DCR_TH * (theta + 3.0) + DCR_C * (c - 45.0) + DCR_B * (B - 4.0)
    return np.sqrt(m2 * G / (0.5 * rho * (CR * np.pi * R**2 + Cdc * A_C)))


def V1f(m1, rho, Cdd, Dd=0.25, Cdc=0.8):
    return np.sqrt(m1 * G / (0.5 * rho * (Cdd * np.pi * Dd**2 / 4 + Cdc * A_C)))


def sobol(f, lows, highs, N=200000):
    """Índices de Sobol de primer orden (Saltelli 2010) y totales (Jansen), con la salida centrada."""
    k = len(lows)
    A = rng.uniform(lows, highs, (N, k)); Bm = rng.uniform(lows, highs, (N, k))
    fA, fB = f(A), f(Bm)
    mu = 0.5 * (fA.mean() + fB.mean())
    fA, fB = fA - mu, fB - mu
    var = np.var(np.concatenate([fA, fB]))
    S1, ST = [], []
    for i in range(k):
        ABi = A.copy(); ABi[:, i] = Bm[:, i]
        fAB = f(ABi) - mu
        S1.append(np.mean(fB * (fAB - fA)) / var)
        ST.append(0.5 * np.mean((fA - fAB)**2) / var)
    return np.array(S1), np.array(ST), var


def prcc(X, y):
    from scipy.stats import rankdata
    Xr = np.column_stack([rankdata(X[:, i]) for i in range(X.shape[1])]); yr = rankdata(y)
    out = []
    for i in range(X.shape[1]):
        others = np.delete(Xr, i, axis=1)
        A = np.column_stack([np.ones(len(yr)), others])
        ex = Xr[:, i] - A @ np.linalg.lstsq(A, Xr[:, i], rcond=None)[0]
        ey = yr - A @ np.linalg.lstsq(A, yr, rcond=None)[0]
        out.append(np.corrcoef(ex, ey)[0, 1])
    return np.array(out)


# ---------------------------------------------------------------- A. V2 de régimen
def parteA(arq='A1'):
    m2c = 0.490 if arq == 'A1' else 0.325
    dm = 0.010 if arq == 'A1' else 0.025
    nom = dict(m2=m2c, R=0.25, rho=1.225, dCR=0.0, theta=-3.0, c=45.0, B=4.0, Cdc=0.8)
    V0 = V2f(nom['m2'], nom['R'], nom['rho'], nom['dCR'], nom['theta'], nom['c'], nom['B'], nom['Cdc'])
    # (1) elasticidad d ln V2 / d ln x (diferencias centrales de +-1 %)
    names = ['m2', 'R', 'rho', 'dCR', 'theta', 'c', 'B', 'Cdc']
    el = {}
    for n in names:
        lo = dict(nom); hi = dict(nom)
        if n in ('dCR',):
            lo[n] = -0.01; hi[n] = 0.01; step = 0.02
        elif n == 'theta':
            lo[n] = nom[n] - 0.1; hi[n] = nom[n] + 0.1; step = 0.2 / abs(nom[n])
        else:
            lo[n] = nom[n] * 0.99; hi[n] = nom[n] * 1.01; step = 0.02
        el[n] = (np.log(V2f(**hi)) - np.log(V2f(**lo))) / step
    # (2) tornado con rangos plausibles
    rangos = dict(m2=(m2c - dm, m2c + dm), R=(0.247, 0.253), rho=(1.10, 1.25), dCR=(-0.15, 0.15),
                  theta=(-4.0, -2.0), c=(40.0, 50.0), B=(3.0, 5.0), Cdc=(0.6, 1.0))
    torn = []
    for n in names:
        lo = dict(nom); hi = dict(nom)
        lo[n], hi[n] = rangos[n]
        vl, vh = V2f(**lo), V2f(**hi)
        torn.append((n, vl, vh, abs(vh - vl)))
    torn.sort(key=lambda x: -x[3])
    guardar('tornado_V2_' + arq, ['param', 'Vlo', 'Vhi', 'ancho'], [(n, a, b_, c_) for n, a, b_, c_ in torn])
    # (3) Sobol y PRCC con los mismos rangos (distribución uniforme)
    lows = [rangos[n][0] for n in names]; highs = [rangos[n][1] for n in names]
    f = lambda X: V2f(*[X[:, i] for i in range(len(names))])
    S1, ST, var = sobol(f, lows, highs)
    X = rng.uniform(lows, highs, (20000, len(names)))
    pr = prcc(X, f(X))
    guardar('sobol_V2_' + arq, ['param', 'S1', 'ST', 'PRCC'], [(n, s1, st, p) for n, s1, st, p in zip(names, S1, ST, pr)])
    res['A_' + arq] = dict(V0=float(V0), elasticidades={k: float(v) for k, v in el.items()},
                           tornado=[(n, float(a), float(b_)) for n, a, b_, _ in torn],
                           sobol={n: dict(S1=float(s1), ST=float(st), PRCC=float(p)) for n, s1, st, p in zip(names, S1, ST, pr)},
                           sd_V2=float(np.sqrt(var)))


# ---------------------------------------------------------------- B. promedio global
def parteB(arq='A1'):
    m2c = 0.490 if arq == 'A1' else 0.325
    dm = 0.010 if arq == 'A1' else 0.025
    names = ['m1', 'Cdd', 'Dd', 'rho', 'm2', 'dCR', 'theta', 'Cdc', 'f', 'ts']
    lows = [0.490, 0.75, 0.24, 1.10, m2c - dm, -0.15, -4.0, 0.6, 0.17, 2.5]
    highs = [0.510, 0.90, 0.26, 1.25, m2c + dm, 0.15, -2.0, 1.0, 0.23, 5.0]

    def f(X):
        m1, Cdd, Dd, rho, m2, dCR, th, Cdc, fr, ts = [X[:, i] for i in range(len(names))]
        V1 = V1f(m1, rho, Cdd, Dd, Cdc)
        V2 = V2f(m2, 0.25, rho, dCR, th, 45.0, 4.0, Cdc)
        # transitorio: ts s de arranque a velocidad media (V1+V2)/2 dentro de la altura de la etapa 2
        H = 800.0
        t1 = fr * H / V1
        hr = (1 - fr) * H
        Vs = 0.5 * (V1 + V2)
        t2 = ts + (hr - Vs * ts) / V2
        return H / (t1 + t2)
    S1, ST, var = sobol(f, lows, highs)
    X = rng.uniform(lows, highs, (20000, len(names)))
    y = f(X)
    pr = prcc(X, y)
    nom = np.array([(l + h) / 2 for l, h in zip(lows, highs)])
    nom[names.index('theta')] = -3.0; nom[names.index('dCR')] = 0.0
    y0 = f(nom[None, :])[0]
    torn = []
    for i, n in enumerate(names):
        lo = nom.copy(); hi = nom.copy(); lo[i] = lows[i]; hi[i] = highs[i]
        torn.append((n, f(lo[None, :])[0], f(hi[None, :])[0]))
    torn.sort(key=lambda t: -abs(t[2] - t[1]))
    guardar('tornado_Vg_' + arq, ['param', 'Vlo', 'Vhi'], torn)
    guardar('sobol_Vg_' + arq, ['param', 'S1', 'ST', 'PRCC'], [(n, s1, st, p) for n, s1, st, p in zip(names, S1, ST, pr)])
    res['B_' + arq] = dict(Vg0=float(y0), media=float(y.mean()), sd=float(y.std()), p95=float(np.percentile(y, 95)),
                           P_gt8=float(np.mean(y > 8.0)),
                           sobol={n: dict(S1=float(s1), ST=float(st), PRCC=float(p)) for n, s1, st, p in zip(names, S1, ST, pr)})


# ---------------------------------------------------------------- D. autonomía
def parteD():
    nom = dict(i_c3=85.0, i_sens=8.8, i_gps=35.0, i_lora=105.0, i_sd=30.0, i_led=5.0, i_cam=300.0, i_servo=20.0,
               eta_buck=0.90, eta_boost=0.85, frac_util=0.90, cap=3.4, f_cap_T=1.0)

    def horas(p, camaras=True, lora_avg=None, directo=False):
        i33 = p['i_c3'] + p['i_sens'] + p['i_gps'] + (p['i_lora'] if lora_avg is None else lora_avg) + p['i_sd'] + p['i_led']
        # topología de la planilla: batería -> elevador a 5 V -> reductor mini560 a 3,3 V (doble conversión)
        eta33 = p['eta_buck'] if directo else p['eta_buck'] * p['eta_boost']
        P33 = 3.3 * i33 / 1000 / eta33
        i5 = (2 * p['i_cam'] if camaras else 0.0) + p['i_servo']
        P5 = 5.0 * i5 / 1000 / p['eta_boost']
        E = p['cap'] * 3.6 * p['frac_util'] * p['f_cap_T']
        return E / (P33 + P5), P33 + P5
    h_all, P_all = horas(nom, True)
    h_pad, P_pad = horas(nom, False)
    h_ref, P_ref = horas(nom, False, lora_avg=20.0)
    h_dir, P_dir = horas(nom, True, directo=True)
    h_dir_pad, _ = horas(nom, False, lora_avg=20.0, directo=True)
    h_cam_aut, _ = horas(nom, True, lora_avg=20.0, directo=True)
    res['D'] = dict(h_directo_todo=h_dir, P_directo_todo=P_dir, h_directo_rampa_lora20=h_dir_pad, h_directo_cam_lora20=h_cam_aut,h_todo_encendido=h_all, P_todo=P_all, h_rampa_sin_camaras=h_pad, P_rampa=P_pad,
                    h_rampa_lora_promedio=h_ref, E_util_Wh=nom['cap'] * 3.6 * nom['frac_util'])
    rangos = dict(i_c3=(70, 200), i_sens=(8, 15), i_gps=(25, 45), i_lora=(20, 140), i_sd=(10, 60), i_led=(2, 10),
                  i_cam=(180, 330), i_servo=(10, 40), eta_buck=(0.80, 0.93), eta_boost=(0.75, 0.90),
                  frac_util=(0.80, 0.95), cap=(2.9, 3.4), f_cap_T=(0.85, 1.0))
    torn = []
    for n, (lo, hi) in rangos.items():
        a = dict(nom); a[n] = lo
        c = dict(nom); c[n] = hi
        torn.append((n, horas(a, True)[0], horas(c, True)[0]))
    torn.sort(key=lambda t: -abs(t[2] - t[1]))
    guardar('tornado_E7', ['param', 'h_lo', 'h_hi'], torn)
    # Monte Carlo del peor caso: todo encendido desde la rampa
    N = 50000
    X = {n: rng.uniform(lo, hi, N) for n, (lo, hi) in rangos.items()}
    h = np.array([horas({n: X[n][i] for n in X}, True)[0] for i in range(2000)])
    res['D']['MC_todo_encendido'] = dict(media=float(h.mean()), p5=float(np.percentile(h, 5)), min=float(h.min()),
                                          P_menor_2h=float(np.mean(h < 2.0)))


# ---------------------------------------------------------------- E. error de la altura de liberación
def parteE(N=200000):
    rho = 1.225
    H = rng.uniform(500, 1000, N)
    # fuentes (m): ruido del barómetro filtrado, retardo del filtro x V1, puerto estático (Cp q), deriva térmica del
    # offset, deriva meteorológica en la rampa, pico de ruido al buscar el máximo
    ruido = rng.normal(0, 0.15, N)
    retardo = rng.uniform(0.2, 0.8, N) * 13.4
    Cp = rng.uniform(-0.3, 0.6, N)
    puerto = Cp * 0.5 * rho * 13.4**2 / (rho * G)
    deriva_T = rng.uniform(-15, 5, N) * 1.5 / (rho * G)
    meteo = rng.normal(0, 0.4, N)
    pico = np.abs(rng.normal(0, 0.15, N)) * 2.0
    escala = rng.normal(0, 0.04, N) * 0.0       # el error de escala ISA se cancela al ser relativo al mismo sensor
    dh = ruido + retardo + puerto + deriva_T + meteo - pico
    df = dh / H
    res['E'] = dict(dh_media=float(dh.mean()), dh_sd=float(dh.std()), dh_p95=float(np.percentile(np.abs(dh), 95)),
                    df_p95=float(np.percentile(np.abs(df), 95)),
                    contrib={n: float(np.std(v)) for n, v in dict(ruido=ruido, retardo=retardo, puerto=puerto,
                                                                  deriva_T=deriva_T, meteo=meteo, pico=pico).items()})
    # efecto de la escala ISA si el umbral fuera ABSOLUTO (comparación): error de +-4 % en h
    err_abs = rng.normal(0, 0.04, N) * H
    res['E']['escala_absoluta_sd'] = float(err_abs.std())
    # sensibilidad de V_global a la fracción de liberación
    for fr in (0.17, 0.20, 0.23):
        res['E']['Vg_f_%g' % fr] = 1 / (fr / 13.44 + (1 - fr) / 6.36)


# ---------------------------------------------------------------- F. masa de la etapa 2
def presupuestos():
    """(nombre, masa [g], desviación estándar [g], grupo). 'sale' = se va con el drogue/contenedor."""
    comunes = [
        ('Electrónica real (planilla), sin panel', 140.0, 6.0, 'electronica'),
        ('Panel solar (planilla 37 g; típico 6 g)', 37.0, 15.0, 'electronica'),
        ('Palas (4 de 206 mm con portapala)', 38.0, 3.0, 'rotor'),
        ('Cubo, eje, rodamientos, tope y resortes', 26.0, 2.5, 'rotor'),
        ('Cableado, tornillos, insertos y placas', 37.0, 7.0, 'varios'),
        ('Anillo amortiguador de aterrizaje', 8.0, 1.0, 'varios'),
    ]
    a1 = comunes + [
        ('Cuerpo PETG Ø81, pared 2 mm', 130.0, 8.0, 'estructura'),
        ('Tapas y anillos internos', 25.0, 3.0, 'estructura'),
        ('Traba (anillo y pestañas)', 8.0, 1.5, 'mecanismo'),
        ('Copa y pasador del drogue', 8.0, 1.5, 'mecanismo'),
        ('Drogue, cuerda y destorcedor (se suelta)', 10.0, 2.0, 'sale'),
    ]
    a2 = comunes + [
        ('Chasis (esqueleto) de la carga útil', 30.0, 4.0, 'estructura'),
        ('Pestillo y guías', 6.0, 1.5, 'mecanismo'),
        ('Contenedor (tubo de aluminio 0,8 mm Ø90) y tapa (se suelta)', 157.0, 10.0, 'sale'),
        ('Drogue, cuerda y destorcedor (se suelta)', 10.0, 2.0, 'sale'),
    ]
    return a1, a2


def parteF(N=200000):
    out = {}
    for nombre, items in (('A1', presupuestos()[0]), ('A2', presupuestos()[1])):
        mu = np.array([i[1] for i in items]); sd = np.array([i[2] for i in items])
        sale = np.array([i[3] == 'sale' for i in items])
        X = rng.normal(mu, sd, (N, len(items)))
        sin_lastre = X.sum(axis=1)                                 # masa antes de agregar lastre
        masa_pesaje = rng.uniform(490.0, 510.0, N)                 # el lastre se ajusta para llegar a ~500 +- 10
        lastre = masa_pesaje - sin_lastre                          # lastre necesario (g); <0 = sobrepeso
        lastre_sale = (nombre == 'A2')                             # en la Arq. 2 el lastre extra va en el contenedor
        sale_m = X[:, sale].sum(axis=1) + (np.maximum(lastre, 0.0) if lastre_sale else 0.0)
        m2 = (masa_pesaje - sale_m) / 1000.0
        V2 = V2f(m2, 0.25, 1.225, 0.0, -3.0, 45.0, 4.0, 0.8)
        var_pay = np.where(sale, 0.0, sd**2)
        share = var_pay / var_pay.sum()
        out[nombre] = dict(sin_lastre_mu=float(sin_lastre.mean()), sin_lastre_sd=float(sin_lastre.std()),
                           lastre_mu=float(lastre.mean()), lastre_p5=float(np.percentile(lastre, 5)),
                           lastre_p95=float(np.percentile(lastre, 95)), P_sobrepeso=float(np.mean(lastre < 0)),
                           P_lastre_mayor_60=float(np.mean(lastre > 60)),
                           m2_mu=float(m2.mean()), m2_sd=float(m2.std()), V2_mu=float(V2.mean()), V2_sd=float(V2.std()),
                           V2_p95=float(np.percentile(V2, 95)),
                           items=[dict(n=i[0], mu=i[1], sd=i[2], grupo=i[3], share=float(sh)) for i, sh in zip(items, share)])
        with open(os.path.join(DATA, 'sens_masa_%s.dat' % nombre), 'w') as f:
            f.write('item mu sd share\n')
            for k in range(len(items)):
                f.write('%d %.2f %.2f %.4f\n' % (k + 1, mu[k], sd[k], share[k]))
    res['F'] = out


# ---------------------------------------------------------------- G. ráfagas verticales y anillo de vórtices
def parteG():
    out = []
    for arq, m2 in (('A1', 0.490), ('A2', 0.325)):
        V2 = V2f(m2, 0.25, 1.225, 0.0, -3.0, 45.0, 4.0, 0.8)
        T = m2 * G - 0.5 * 1.225 * 0.8 * A_C * V2**2
        vh = np.sqrt(T / (2 * 1.225 * np.pi * 0.25**2))
        for w in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
            out.append((arq, w, (V2 - w) / vh))
        res['G_' + arq] = dict(V2=float(V2), vh=float(vh), V_vh=float(V2 / vh),
                               w_hasta_1p7=float((V2 / vh - 1.7) * vh), w_hasta_1p5=float((V2 / vh - 1.5) * vh))
    with open(os.path.join(DATA, 'sens_gust.dat'), 'w') as f:
        f.write('arq w Vvh\n')
        for a, w, r in out:
            f.write('%s %.2f %.4f\n' % (a, w, r))


if __name__ == '__main__':
    for arq in ('A1', 'A2'):
        parteA(arq); parteB(arq)
    parteD(); parteE(); parteF(); parteG()
    json.dump(res, open(os.path.join(DATA, 'sens_resumen.json'), 'w'), indent=1)
    for k, v in res.items():
        print(k, json.dumps(v)[:900])
