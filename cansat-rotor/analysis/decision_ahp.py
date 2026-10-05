#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de decisión multicriterio para la segunda etapa de descenso.

1. AHP (Saaty): matriz de criterios y siete matrices de alternativas,
   prioridades por vector propio principal, índice y razón de consistencia.
   Para los criterios medibles (K1-K5) los juicios se derivan de la métrica
   del modelo cuantitativo (decision_alternativas.py) llevándola a una escala
   1-9 y redondeando el cociente a la escala de Saaty. Para K6 y K7 los juicios
   parten de puntajes ordinales justificados en el capítulo.
2. TOPSIS (Hwang y Yoon) con las métricas crudas y los mismos pesos.
3. Sensibilidad: Monte Carlo sobre los pesos (Dirichlet concentrada en los pesos
   base, Dirichlet uniforme) y sobre los juicios (perturbación lognormal);
   probabilidad de ser la mejor, distribución de rangos; barridos de un peso
   a la vez y frontera de decisión paracaídas/autogiro.

Salida: analysis/data/decision_*.dat y resumen por pantalla.
"""
import os
import numpy as np
import decision_alternativas as alt

DATA = alt.DATA
rng = np.random.default_rng(7)

A = alt.ALT
n = len(A)
CRIT = ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
SAATY = np.array([1/9, 1/8, 1/7, 1/6, 1/5, 1/4, 1/3, 1/2, 1, 2, 3, 4, 5, 6, 7, 8, 9])


def a_saaty(x):
    """Redondea un cociente al valor más cercano de la escala 1/9 ... 9 (en log)."""
    return SAATY[np.argmin(np.abs(np.log(SAATY) - np.log(x)))]


def prioridades(M):
    """Vector propio principal normalizado, lambda_max, CI y CR."""
    w, v = np.linalg.eig(M)
    i = np.argmax(w.real)
    lam = w[i].real
    p = np.abs(v[:, i].real)
    p /= p.sum()
    k = M.shape[0]
    ci = (lam - k) / (k - 1)
    cr = ci / RI[k] if RI[k] > 0 else 0.0
    return p, lam, ci, cr


MODO = "intensidad"


def matriz_desde_puntajes(s):
    s = np.asarray(s, float)
    M = np.ones((len(s), len(s)))
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            d = s[i] - s[j]
            if MODO == "cociente":
                M[i, j] = a_saaty(s[i] / s[j])
            else:                       # intensidad: diferencia de puntajes -> 1..9
                M[i, j] = a_saaty(1.0 + d) if d >= 0 else 1.0 / a_saaty(1.0 - d)
            M[j, i] = 1.0 / M[i, j]
    return M


def escala19(u, beneficio=True):
    u = np.asarray(u, float)
    if not beneficio:
        u = -u
    return 1.0 + 8.0 * (u - u.min()) / (u.max() - u.min())


# --------------------------------------------------------------------------
# Métricas de las alternativas
# --------------------------------------------------------------------------
res = alt.resumen()
PIN = np.array([res[a]["pin"] for a in A])
ERR = np.array([res[a]["err"] for a in A])
U1 = PIN * np.clip(1.0 - ERR / 6.0, 0.02, None)          # K1: cumplimiento de C4
PF = np.array([0.03, 0.12, 0.04, 0.15, 0.08, 0.05, 0.20])  # K2: P(falla funcional), estimación
MASA = np.array(alt.MASA)                                 # K3
VOL = np.array(alt.VOL, float)                            # K4
PIEZ = np.array(alt.PIEZAS, float)                        # K5
S6 = np.array([3, 4, 6, 1, 7, 4, 3], float)               # K6: video y deriva (ordinal 1-9)
S7 = np.array([1, 4, 7, 5, 6, 2, 3], float)               # K7: valor técnico (ordinal 1-9)

PUNT = [escala19(U1), escala19(-np.log10(PF)), escala19(MASA, False),
        escala19(VOL, False), escala19(PIEZ, False), S6, S7]
MAT = [matriz_desde_puntajes(s) for s in PUNT]

# Matriz de criterios (juicio, triángulo superior)
C = np.ones((7, 7))
sup = {(0, 1): 1, (0, 2): 3, (0, 3): 4, (0, 4): 3, (0, 5): 3, (0, 6): 1,
       (1, 2): 3, (1, 3): 4, (1, 4): 2, (1, 5): 3, (1, 6): 1,
       (2, 3): 1, (2, 4): 1/2, (2, 5): 1/2, (2, 6): 1/4,
       (3, 4): 1/2, (3, 5): 1/2, (3, 6): 1/4,
       (4, 5): 1, (4, 6): 1/3,
       (5, 6): 1/3}
for (i, j), v in sup.items():
    C[i, j] = v
    C[j, i] = 1 / v

W0, LAM0, CI0, CR0 = prioridades(C)
LOC = np.array([prioridades(M)[0] for M in MAT]).T     # n x 7
CRS = [prioridades(M) for M in MAT]

# Escenarios de pesos
ESC = {
    "base": W0,
    "seguridad": None,
    "mision": None,
    "iguales": np.ones(7) / 7,
}
# Seguridad primero: riesgo y C4 dominan, valor técnico casi nulo
Cs = C.copy()
for (i, j), v in {(1, 6): 7, (0, 6): 5, (5, 6): 2, (4, 6): 2, (2, 6): 1, (3, 6): 1}.items():
    Cs[i, j] = v
    Cs[j, i] = 1 / v
ESC["seguridad"] = prioridades(Cs)[0]
CR_S = prioridades(Cs)[3]
# Misión técnica: el valor técnico y el video pesan más
Cm = C.copy()
for (i, j), v in {(0, 6): 1/2, (1, 6): 1/2, (5, 6): 1/2, (4, 6): 1/4, (0, 5): 2, (1, 5): 2}.items():
    Cm[i, j] = v
    Cm[j, i] = 1 / v
ESC["mision"] = prioridades(Cm)[0]
CR_M = prioridades(Cm)[3]


def global_ahp(w, loc=LOC):
    return loc @ w


# --------------------------------------------------------------------------
# TOPSIS con métricas crudas
# --------------------------------------------------------------------------
X = np.column_stack([U1, PF, MASA, VOL, PIEZ, S6, S7])
BEN = np.array([True, False, False, False, False, True, True])
XN = X / np.sqrt((X**2).sum(axis=0))


def topsis(w, xn=XN):
    V = xn * w
    mejor = np.where(BEN, V.max(axis=0), V.min(axis=0))
    peor = np.where(BEN, V.min(axis=0), V.max(axis=0))
    dp = np.sqrt(((V - mejor)**2).sum(axis=1))
    dn = np.sqrt(((V - peor)**2).sum(axis=1))
    return dn / (dp + dn)


def topsis_lote(Wm, xn=XN):
    """TOPSIS vectorizado: Wm es (m x 7); devuelve (m x n)."""
    V = xn[None, :, :] * Wm[:, None, :]
    mx, mn = V.max(axis=1), V.min(axis=1)
    mejor = np.where(BEN, mx, mn)[:, None, :]
    peor = np.where(BEN, mn, mx)[:, None, :]
    dp = np.sqrt(((V - mejor)**2).sum(axis=2))
    dn = np.sqrt(((V - peor)**2).sum(axis=2))
    return dn / (dp + dn)


# --------------------------------------------------------------------------
# Monte Carlo
# --------------------------------------------------------------------------
def mc(Wm, loc=None):
    g = Wm @ (LOC if loc is None else loc).T if loc is None else np.einsum("mk,mak->ma", Wm, loc)
    return g


def prob_mejor(G):
    idx = np.argmax(G, axis=1)
    return np.bincount(idx, minlength=n) / G.shape[0]


def rangos(G):
    orden = np.argsort(-G, axis=1)
    r = np.empty_like(orden)
    m = G.shape[0]
    r[np.arange(m)[:, None], orden] = np.arange(1, n + 1)[None, :]
    return r


NMC = 40_000
K_CONC = 30.0
W_conc = rng.dirichlet(K_CONC * W0, NMC)
W_unif = rng.dirichlet(np.ones(7), NMC)

# Perturbación de juicios: cada a_ij (i<j) x exp(N(0, 0,35)) y P_F con factor 2
NJ = 8000
SIG = 0.35
LOC_J = np.empty((NJ, n, 7))
for m in range(NJ):
    pf = PF * np.exp(rng.normal(0, np.log(2) / 1.645, n))
    punt = list(PUNT)
    punt[1] = escala19(-np.log10(pf))
    for k in range(7):
        Mk = matriz_desde_puntajes(punt[k])
        U = np.triu(rng.normal(0, SIG, (n, n)), 1)
        E = np.exp(U - U.T)
        LOC_J[m, :, k] = prioridades(Mk * E)[0]
W_j = rng.dirichlet(K_CONC * W0, NJ)

G_conc = W_conc @ LOC.T
G_unif = W_unif @ LOC.T
G_j = np.einsum("mk,mak->ma", W_j, LOC_J)
T_conc = topsis_lote(W_conc)
T_unif = topsis_lote(W_unif)

PB = {
    "AHPconc": prob_mejor(G_conc), "AHPunif": prob_mejor(G_unif),
    "AHPjuic": prob_mejor(G_j), "TOPconc": prob_mejor(T_conc),
    "TOPunif": prob_mejor(T_unif),
}
R_conc = rangos(G_conc)
R_unif = rangos(G_unif)


# --------------------------------------------------------------------------
# Barridos de un peso a la vez
# --------------------------------------------------------------------------
def barrido(k, w0=W0, metodo="ahp"):
    xs = np.linspace(0, 0.9, 91)
    filas = []
    for x in xs:
        w = w0 * (1 - x) / (1 - w0[k])
        w[k] = x
        g = global_ahp(w) if metodo == "ahp" else topsis(w)
        filas.append(g)
    return xs, np.array(filas)


def cruce(xs, G, i, j):
    """Primer valor de x donde G[:, i] - G[:, j] cambia de signo."""
    d = G[:, i] - G[:, j]
    s = np.where(np.sign(d[:-1]) != np.sign(d[1:]))[0]
    if len(s) == 0:
        return None
    t = s[0]
    return xs[t] - d[t] * (xs[t + 1] - xs[t]) / (d[t + 1] - d[t])


# --------------------------------------------------------------------------
# Frontera de decisión en el plano (w_K2, w_K7)
# --------------------------------------------------------------------------
def frontera():
    resto = W0.copy()
    resto[[1, 6]] = 0
    resto /= resto.sum()
    w2s = np.linspace(0.0, 0.6, 61)
    w7s = np.linspace(0.0, 0.8, 801)
    lin_ahp, lin_top = [], []
    ganadores = set()
    for w2 in w2s:
        th_a, th_t = None, None
        for w7 in w7s:
            if w2 + w7 > 0.95:
                break
            w = resto * (1 - w2 - w7)
            w[1], w[6] = w2, w7
            g = global_ahp(w)
            t = topsis(w)
            ganadores.add(A[int(np.argmax(g))])
            if th_a is None and np.argmax(g) == 2:
                th_a = w7
            if th_t is None and np.argmax(t) == 2:
                th_t = w7
        lin_ahp.append(th_a if th_a is not None else np.nan)
        lin_top.append(th_t if th_t is not None else np.nan)
    return w2s, np.array(lin_ahp), np.array(lin_top), ganadores


if __name__ == "__main__":
    np.set_printoptions(precision=3, suppress=True)
    print("== Criterios ==")
    print("W0 =", W0, f"lambda={LAM0:.3f} CI={CI0:.4f} CR={CR0:.4f}")
    for nom in ["seguridad", "mision"]:
        print(nom, ESC[nom])
    print(f"CR seguridad={CR_S:.4f} CR mision={CR_M:.4f}")
    print("== Matrices por criterio ==")
    for k in range(7):
        p, lam, ci, cr = CRS[k]
        print(CRIT[k], "punt=", np.round(PUNT[k], 2), "p=", p, f"lam={lam:.3f} CR={cr:.4f}")
    print("U1 =", U1)
    print("== Prioridades globales AHP ==")
    for nom, w in ESC.items():
        g = global_ahp(w)
        t = topsis(w)
        print(f"{nom:10s}", "AHP", g, " -> ", A[int(np.argmax(g))],
              "| TOPSIS", t, " -> ", A[int(np.argmax(t))])
    print("== P(mejor) ==")
    for k, v in PB.items():
        print(f"{k:8s}", v)
    print("Rango medio (conc):", R_conc.mean(axis=0))
    print("P(c entre las dos mejores, conc):", np.mean(R_conc[:, 2] <= 2))
    # Barridos
    cruces = {}
    for k in range(7):
        xs, G = barrido(k)
        _, T = barrido(k, metodo="topsis")
        with open(os.path.join(DATA, f"decision_barrido_{CRIT[k]}.dat"), "w") as fh:
            fh.write("w " + " ".join(A) + " " + " ".join("t" + a for a in A) + "\n")
            for i, x in enumerate(xs):
                fh.write(f"{x:.3f} " + " ".join(f"{v:.5f}" for v in G[i]) + " "
                         + " ".join(f"{v:.5f}" for v in T[i]) + "\n")
        cruces[CRIT[k]] = (cruce(xs, G, 0, 2), cruce(xs, T, 0, 2))
        win = [A[int(np.argmax(G[i]))] for i in range(len(xs))]
        cambios = [(round(xs[i], 3), win[i - 1], win[i]) for i in range(1, len(xs)) if win[i] != win[i - 1]]
        print(CRIT[k], f"w0={W0[k]:.3f} cruce a-c AHP={cruces[CRIT[k]][0]} TOPSIS={cruces[CRIT[k]][1]}",
              "cambios de ganador AHP:", cambios)
    w2s, la, lt, gan = frontera()
    print("ganadores en el plano (w2,w7):", gan)
    with open(os.path.join(DATA, "decision_frontera.dat"), "w") as fh:
        fh.write("w2 w7ahp w7top\n")
        for i in range(len(w2s)):
            fh.write(f"{w2s[i]:.3f} {la[i]:.4f} {lt[i]:.4f}\n")
    print("frontera AHP (w2, w7*):", [(round(a, 2), round(b, 3)) for a, b in zip(w2s[::10], la[::10])])
    print("frontera TOPSIS:", [(round(a, 2), round(b, 3)) for a, b in zip(w2s[::10], lt[::10])])
    # Tablas
    with open(os.path.join(DATA, "decision_pmejor.dat"), "w") as fh:
        fh.write("idx alt " + " ".join(PB.keys()) + "\n")
        for i, a in enumerate(A):
            fh.write(f"{i} {a} " + " ".join(f"{PB[k][i]:.4f}" for k in PB) + "\n")
    with open(os.path.join(DATA, "decision_global.dat"), "w") as fh:
        fh.write("idx alt " + " ".join("ahp_" + e for e in ESC) + " " + " ".join("top_" + e for e in ESC) + "\n")
        for i, a in enumerate(A):
            fh.write(f"{i} {a} " + " ".join(f"{global_ahp(w)[i]:.4f}" for w in ESC.values()) + " "
                     + " ".join(f"{topsis(w)[i]:.4f}" for w in ESC.values()) + "\n")
    with open(os.path.join(DATA, "decision_rangos.dat"), "w") as fh:
        fh.write("rango " + " ".join(A) + " " + " ".join("u" + a for a in A) + "\n")
        for r in range(1, n + 1):
            fh.write(f"{r} " + " ".join(f"{np.mean(R_conc[:, i] == r):.4f}" for i in range(n)) + " "
                     + " ".join(f"{np.mean(R_unif[:, i] == r):.4f}" for i in range(n)) + "\n")
    with open(os.path.join(DATA, "decision_locales.dat"), "w") as fh:
        fh.write("idx alt " + " ".join(CRIT) + "\n")
        for i, a in enumerate(A):
            fh.write(f"{i} {a} " + " ".join(f"{LOC[i, k]:.4f}" for k in range(7)) + "\n")
    # Matrices para el capítulo
    print("== Matriz de criterios ==")
    print(C)
    for k in range(7):
        print(CRIT[k])
        print(MAT[k])


# --------------------------------------------------------------------------
# Variantes de método (robustez frente a la técnica, no a los pesos)
# --------------------------------------------------------------------------
def variantes():
    out = {}
    # AHP modo "cociente" (juicio = cociente de puntajes)
    global MODO
    MODO = "cociente"
    locq = np.array([prioridades(matriz_desde_puntajes(s))[0] for s in PUNT]).T
    MODO = "intensidad"
    out["AHP cociente"] = locq @ W0
    # AHP modo ideal (cada columna dividida por su máximo)
    loci = LOC / LOC.max(axis=0)
    gi = loci @ W0
    out["AHP ideal"] = gi / gi.sum()
    # TOPSIS con riesgo en escala logarítmica
    X2 = X.copy()
    X2[:, 1] = -np.log10(PF)
    ben2 = BEN.copy()
    ben2[1] = True
    xn2 = X2 / np.sqrt((X2**2).sum(axis=0))
    V = xn2 * W0
    mejor = np.where(ben2, V.max(axis=0), V.min(axis=0))
    peor = np.where(ben2, V.min(axis=0), V.max(axis=0))
    dp = np.sqrt(((V - mejor)**2).sum(axis=1))
    dn = np.sqrt(((V - peor)**2).sum(axis=1))
    out["TOPSIS log riesgo"] = dn / (dp + dn)
    # TOPSIS con los puntajes 1-9 del AHP (misma información que el AHP)
    P = np.column_stack(PUNT)
    pn = P / np.sqrt((P**2).sum(axis=0))
    V = pn * W0
    dp = np.sqrt(((V - V.max(axis=0))**2).sum(axis=1))
    dn = np.sqrt(((V - V.min(axis=0))**2).sum(axis=1))
    out["TOPSIS puntajes"] = dn / (dp + dn)
    # Conjunto reducido: sin (f) y (g), que no cumplen C4
    keep = [0, 1, 2, 3, 4]
    sub = []
    for k, s in enumerate(PUNT):
        if k <= 4:
            # re-escalar la métrica en el subconjunto
            raw = [U1, -np.log10(PF), -MASA, -VOL, -PIEZ][k][keep]
            ss = escala19(raw)
        else:
            ss = np.asarray(s)[keep]
        sub.append(prioridades(matriz_desde_puntajes(ss))[0])
    locr = np.array(sub).T
    gr = np.full(n, np.nan)
    gr[keep] = locr @ W0
    out["AHP sin f,g"] = gr
    Xr = X[keep]
    xnr = Xr / np.sqrt((Xr**2).sum(axis=0))
    tr = np.full(n, np.nan)
    tr[keep] = topsis(W0, xnr)
    out["TOPSIS sin f,g"] = tr
    return out


if __name__ == "__main__":
    print("== Variantes de método (pesos base) ==")
    var = variantes()
    with open(os.path.join(DATA, "decision_variantes.dat"), "w") as fh:
        fh.write("metodo " + " ".join(A) + " ganador\n")
        for k, g in var.items():
            gan = A[int(np.nanargmax(g))]
            print(f"{k:20s}", np.round(g, 3), gan)
            fh.write(k.replace(" ", "_") + " " + " ".join(f"{v:.4f}" for v in g) + f" {gan}\n")


# --------------------------------------------------------------------------
# Umbral de riesgo del autogiro: ¿con qué P_F deja de ganar?
# --------------------------------------------------------------------------
def umbral_pf():
    pfs = np.geomspace(0.01, 0.30, 300)
    filas = []
    for p in pfs:
        pf = PF.copy()
        pf[2] = p
        punt = list(PUNT)
        punt[1] = escala19(-np.log10(pf))
        loc = np.array([prioridades(matriz_desde_puntajes(s))[0] for s in punt]).T
        x = X.copy()
        x[:, 1] = pf
        xn = x / np.sqrt((x**2).sum(axis=0))
        g_b = loc @ W0
        g_m = loc @ ESC["mision"]
        t_b = topsis(W0, xn)
        filas.append((p, g_b[2] - g_b[0], g_m[2] - g_m[0], t_b[2] - t_b[0]))
    filas = np.array(filas)
    with open(os.path.join(DATA, "decision_umbralpf.dat"), "w") as fh:
        fh.write("pf dAHPbase dAHPmision dTOPbase\n")
        for f in filas:
            fh.write(" ".join(f"{v:.5f}" for v in f) + "\n")
    for j, nom in [(1, "AHP base"), (2, "AHP mision"), (3, "TOPSIS base")]:
        d = filas[:, j]
        s = np.where(np.sign(d[:-1]) != np.sign(d[1:]))[0]
        print(f"umbral P_F autogiro ({nom}):", [round(filas[i, 0], 4) for i in s])


if __name__ == "__main__":
    umbral_pf()
