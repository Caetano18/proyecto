"""Estabilidad longitudinal con los datos de NASA TN D-1957, figura 13(a) (ala de 40 grados de flecha, la mas parecida
a la nuestra).  Valores leidos de la figura cada 5 grados de alfa.  El informe da Cm con el CG a 0,75 largos de quilla
debajo de la quilla y en x/lk = 0,550 a 0,635 desde el apice; aca se trasladan los momentos a otro punto (x, z):
    Cm(x, z) = Cm(x0, z0) + CN (x - x0) + CA (z - z0)
con CN = CL cos a + CD sen a (normal a la quilla) y CA = CD cos a - CL sen a (a lo largo de la quilla, hacia atras).
"""
import math
import numpy as np

ALFA = np.array([15.0, 20.0, 25.0, 30.0])
CL = np.array([0.323, 0.596, 0.858, 1.11])
CD = np.array([0.083, 0.111, 0.195, 0.303])
LD_FIG = np.array([None, 5.35, 4.45, None], dtype=object)       # curva L/D de la figura (control de la lectura)
X0, Z0 = 0.575, 0.75
CM_FIG = np.array([0.028, 0.002, -0.035, -0.048])                # curva x/lk = 0,575
CM_FIG_600 = np.array([0.035, 0.013, -0.012, -0.027])            # curva x/lk = 0,600 (control)
A = np.radians(ALFA)
CN = CL * np.cos(A) + CD * np.sin(A)
CA = CD * np.cos(A) - CL * np.sin(A)


def cm(x, z):
    return CM_FIG + CN * (x - X0) + CA * (z - Z0)


def trim(x, z):
    """alfa de trim (Cm = 0) y pendiente dCm/dCL ahi; None si no trima entre 15 y 30 grados."""
    a_f = np.linspace(15, 30, 301)
    c = np.interp(a_f, ALFA, cm(x, z))
    cl = np.interp(a_f, ALFA, CL)
    s = np.where(np.diff(np.sign(c)) != 0)[0]
    if not len(s):
        return None
    i = s[0]
    return a_f[i], cl[i], (c[i + 5] - c[i - 5]) / (cl[i + 5] - cl[i - 5]) if 5 <= i < len(a_f) - 5 else float("nan")


if __name__ == "__main__":
    print("control de lectura: L/D = CL/CD ->", np.round(CL / CD, 2), "(figura: ~5,35 a 20 y ~4,45 a 25)")
    print("control del traslado: x/lk 0,600 predicho", np.round(cm(0.600, Z0), 3), "leido", CM_FIG_600)
    for z in (0.75, 0.50, 0.40, 0.30, 0.21):
        filas = []
        for x in np.arange(0.40, 0.66, 0.025):
            t = trim(x, z)
            if t:
                filas.append(f"x {x:.3f}: a {t[0]:.1f}, CL {t[1]:.2f}, margen {-100 * t[2]:+.0f} %")
        print(f"z/lk = {z:.2f}:", " | ".join(filas) if filas else "no trima entre 15 y 30 grados")
