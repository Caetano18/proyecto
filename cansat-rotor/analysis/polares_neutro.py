#!/usr/bin/env python3
"""Sección neutra en autorrotación a partir de las polares XFOIL.

Una sección no aporta par cuando tan(phi) = Cd/Cl (ec. eq:autorrot). Con el paso
de cuerda theta (negativo = borde de ataque hacia abajo) el ángulo de ataque es
alpha = phi + theta. Para cada theta se buscan TODAS las soluciones de
    g(alpha) = alpha - theta - atan(Cd/Cl)(alpha) = 0
sobre la polar fusionada (puede haber más de una por la histéresis de la burbuja).
Con el Cl de la solución se reestima la velocidad de giro con la ec. eq:omega,
Omega = Omega_ref * sqrt(Cl_ref / Cl), con Omega_ref = 120 rad/s y Cl_ref = 0,9.

Es un modelo de sección representativa (r_T = 0,78 R), no una BEMT: sirve para ver
qué zona de la polar usa el rotor y cuánto cambia con el perfil y con Ncrit.

Salidas (analysis/data):
  polares_neutro.dat         theta, alpha, cl, ld, phi, rpm por polar (rama principal);
                             salto = 1 si la solución cae dentro de un salto de Cl
                             (cl_inf, cl_sup: valores a ambos lados)
  polares_neutro_phi_<caso>.dat   curva phi_n(alpha) = atan(Cd/Cl) para la figura
"""
import os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "analysis", "data")
OMEGA_REF, CL_REF = 120.0, 0.9
CASOS = [("placa7", 50, ""), ("placa7", 50, "_N5"), ("placa7", 75, ""), ("placa7", 75, "_N5"),
         ("placa4", 50, ""), ("plana3", 50, ""), ("naca6412", 50, ""), ("naca6412", 50, "_N5")]
THETAS = np.arange(-6.0, 0.01, 0.5)
SALTO = 0.10          # salto de Cl entre ángulos consecutivos (paso 0,25 grados)


def cargar(p, r, s):
    D = np.loadtxt(os.path.join(DATA, f"polares_{p}_Re{r}{s}.dat"), skiprows=1, ndmin=2)
    return D[:, 0], D[:, 1], D[:, 2]


def soluciones(a, cl, cd, theta):
    ok = cl > 0.02
    a, cl, cd = a[ok], cl[ok], cd[ok]
    phi = np.degrees(np.arctan2(cd, cl))
    g = a - theta - phi
    sol = []
    for k in range(len(a) - 1):
        if a[k + 1] - a[k] > 0.6:          # no se cruza un hueco de XFOIL
            continue
        if g[k] == 0 or g[k] * g[k + 1] < 0:
            f = g[k] / (g[k] - g[k + 1])
            al = a[k] + f * (a[k + 1] - a[k])
            c_l = cl[k] + f * (cl[k + 1] - cl[k])
            c_d = cd[k] + f * (cd[k + 1] - cd[k])
            # solución dentro de un salto de la polar (|dCl| > SALTO entre dos ángulos
            # consecutivos): el cruce es un artificio de la interpolación lineal; la
            # sección queda "clavada" en la discontinuidad y su Cl está indeterminado
            # entre cl[k] y cl[k+1]
            en_salto = abs(cl[k + 1] - cl[k]) > SALTO
            sol.append((al, c_l, c_l / c_d, al - theta, en_salto, cl[k], cl[k + 1]))
    return sol


def main():
    filas = []
    for p, r, s in CASOS:
        a, cl, cd = cargar(p, r, s)
        nom = f"{p}_Re{r}{s}"
        with open(os.path.join(DATA, f"polares_neutro_phi_{nom}.dat"), "w") as f:
            f.write("alpha phin\n")
            prev = None
            for x, y, z in zip(a, cl, cd):
                if prev is not None and x - prev > 0.3:
                    f.write("nan nan\n")
                prev = x
                f.write(f"{x:.2f} " + (f"{np.degrees(np.arctan2(z, y)):.3f}" if y > 0.05 else "nan") + "\n")
        for th in THETAS:
            S = soluciones(a, cl, cd, th)
            # rama principal: la de menor alpha (la que alcanza un rotor que acelera
            # desde el arranque, con alpha decreciente); se informa cuántas hay
            if S:
                al, c, ld, ph, sal, c_a, c_b = S[0]
                rpm = OMEGA_REF * np.sqrt(CL_REF / c) * 60 / (2 * np.pi) if c > 0.05 else np.nan
                filas.append((nom, th, al, c, ld, ph, rpm, len(S),
                              S[-1][0] if len(S) > 1 else np.nan, S[-1][1] if len(S) > 1 else np.nan,
                              int(sal), c_a if sal else np.nan, c_b if sal else np.nan))
            else:
                filas.append((nom, th) + (np.nan,) * 5 + (0, np.nan, np.nan, 0, np.nan, np.nan))
    with open(os.path.join(DATA, "polares_neutro.dat"), "w") as f:
        f.write("caso theta alpha cl ld phi rpm nsol alpha_alt cl_alt salto cl_inf cl_sup\n")
        for fi in filas:
            f.write(f"{fi[0]} {fi[1]:.1f} " + " ".join(
                "nan" if (isinstance(v, float) and np.isnan(v)) else (f"{v:.3f}" if isinstance(v, float) else str(v))
                for v in fi[2:]) + "\n")
    # tabla ancha para pgfplots: theta y Cl / rpm de cada caso
    noms = [f"{p}_Re{r}{s}" for p, r, s in CASOS]
    with open(os.path.join(DATA, "polares_neutro_ancho.dat"), "w") as f:
        f.write("theta " + " ".join(f"cl_{n} rpm_{n} a_{n} sal_{n}" for n in noms) + "\n")
        for th in THETAS:
            v = []
            for n in noms:
                fi = [x for x in filas if x[0] == n and abs(x[1] - th) < 1e-6][0]
                # sal_<caso>: Cl solo si la solución cae dentro de un salto (para marcarla)
                v += [fi[3], fi[6], fi[2], fi[3] if fi[10] else np.nan]
            f.write(f"{th:.1f} " + " ".join("nan" if np.isnan(x) else f"{x:.3f}" for x in v) + "\n")
    for fi in filas:
        if abs(fi[1] % 1) < 1e-6:
            print(" ".join(str(round(v, 3)) if isinstance(v, float) else str(v) for v in fi))


if __name__ == "__main__":
    main()
