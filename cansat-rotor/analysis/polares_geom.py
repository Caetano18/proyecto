#!/usr/bin/env python3
"""Geometría de las secciones comparadas en el capítulo de polares.

Genera coordenadas normalizadas (cuerda 1, borde de ataque en el origen, cuerda
horizontal) en el orden que espera XFOIL: borde de fuga -> extradós -> borde de
ataque -> intradós -> borde de fuga. Escribe:

  analysis/data/polares_geom_<perfil>.dat   (x y, con encabezado para pgfplots)
  <raw>/<perfil>.dat                        (formato XFOIL con nombre en la 1.a línea)

Perfiles:
  placa7   placa curvada en arco circular, flecha 7 %, espesor modelado 1,5 %
  placa4   ídem, flecha 4 %
  plana3   placa plana de 3 % de espesor
  clarky   fondo plano tipo Clark Y (ordenadas clásicas tabuladas, 11,7 %)
  naca6412, naca0012
  placa7_t11, placa7_t20   variantes de espesor (1,1 % = placa real de 0,5 mm; 2,0 %)
  placa7_le2               variante con borde de ataque más romo (r_LE doble)

Uso:  python3 analysis/polares_geom.py [directorio_raw]
"""
import os
import sys
import numpy as np
from scipy.interpolate import PchipInterpolator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "analysis", "data")
RAW = sys.argv[1] if len(sys.argv) > 1 else "/tmp/polares_xfoil"
NSIDE = 161  # puntos por cara (espaciado coseno); XFOIL vuelve a panelar con PANE


def xcos(n):
    b = np.linspace(0.0, np.pi, n)
    return 0.5 * (1.0 - np.cos(b))


def arco(x, h):
    """Línea media en arco circular de flecha relativa h: (yc, dyc/dx)."""
    if h <= 0:
        return np.zeros_like(x), np.zeros_like(x)
    Rc = (0.25 + h * h) / (2.0 * h)
    s = np.sqrt(Rc * Rc - (x - 0.5) ** 2)
    return s - (Rc - h), -(x - 0.5) / s


def espesor_placa(x, t, a_le, x_te=0.85):
    """Semiespesor de una placa de espesor t con nariz redondeada y bisel de fuga.

    Nariz: y = (t/2) sqrt(1 - exp(-x/a)); cerca de x=0 es una parábola y^2 = 2 r x
    con radio r_LE = (t/2)^2 / (2 a). Bisel: factor 1 - xi^2 desde x_te hasta 1,
    que deja un borde de fuga afilado con un ángulo de cuña finito.
    """
    f_le = np.sqrt(1.0 - np.exp(-x / a_le))
    xi = np.clip((x - x_te) / (1.0 - x_te), 0.0, 1.0)
    f_te = 1.0 - xi ** 2
    return 0.5 * t * f_le * f_te


def placa(h, t, a_rel=0.5, x_te=0.85, n=NSIDE):
    x = xcos(n)
    yc, dy = arco(x, h)
    yt = espesor_placa(x, t, a_rel * t, x_te)
    th = np.arctan(dy)
    xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th)
    xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    return junta(xu, yu, xl, yl)


def naca4(code, n=NSIDE, te_cerrado=False):
    m, p, t = int(code[0]) / 100.0, int(code[1]) / 10.0, int(code[2:]) / 100.0
    x = xcos(n)
    a4 = -0.1036 if te_cerrado else -0.1015
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2
                  + 0.2843 * x ** 3 + a4 * x ** 4)
    yc = np.zeros_like(x)
    dy = np.zeros_like(x)
    if m > 0:
        i = x < p
        yc[i] = m / p ** 2 * (2 * p * x[i] - x[i] ** 2)
        dy[i] = 2 * m / p ** 2 * (p - x[i])
        j = ~i
        yc[j] = m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x[j] - x[j] ** 2)
        dy[j] = 2 * m / (1 - p) ** 2 * (p - x[j])
    th = np.arctan(dy)
    xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th)
    xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    return junta(xu, yu, xl, yl)


# Ordenadas clásicas del Clark Y en % de cuerda, referidas al fondo plano.
CY_X = np.array([0, 1.25, 2.5, 5, 7.5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]) / 100
CY_U = np.array([3.50, 5.45, 6.50, 7.90, 8.85, 9.60, 10.68, 11.36, 11.70, 11.40, 10.52,
                 9.15, 7.35, 5.22, 2.80, 1.49, 0.12]) / 100
CY_L = np.array([3.50, 1.93, 1.47, 0.93, 0.63, 0.42, 0.15, 0.03, 0, 0, 0, 0, 0, 0, 0, 0, 0]) / 100


def clarky(n=NSIDE):
    """Interpola las ordenadas en la variable u = sqrt(x), en la que la nariz es suave."""
    u = np.sqrt(CY_X)
    fu = PchipInterpolator(u, CY_U)
    fl = PchipInterpolator(u, CY_L)
    x = xcos(n)
    xu, yu = x.copy(), fu(np.sqrt(x))
    xl, yl = x.copy(), fl(np.sqrt(x))
    # Llevar la cuerda (BA -> punto medio del BF) a la horizontal y a longitud 1.
    xte, yte = 1.0, 0.5 * (yu[-1] + yl[-1])
    ang = np.arctan2(yte - yu[0], xte - xu[0])
    c, s = np.cos(-ang), np.sin(-ang)
    x0, y0 = xu[0], yu[0]
    def rot(xx, yy):
        xx, yy = xx - x0, yy - y0
        return (c * xx - s * yy), (s * xx + c * yy)
    xu, yu = rot(xu, yu)
    xl, yl = rot(xl, yl)
    L = xu[-1]
    return junta(xu / L, yu / L, xl / L, yl / L), np.degrees(ang)


def junta(xu, yu, xl, yl):
    X = np.concatenate([xu[::-1], xl[1:]])
    Y = np.concatenate([yu[::-1], yl[1:]])
    return X, Y


def propiedades(X, Y):
    """Espesor y flecha máximos, radio de borde de ataque (ajuste de círculo)."""
    i0 = int(np.argmin(X))
    xu, yu = X[:i0 + 1][::-1], Y[:i0 + 1][::-1]
    xl, yl = X[i0:], Y[i0:]
    xs = np.linspace(0.002, 0.998, 2000)
    yus = np.interp(xs, xu, yu)
    yls = np.interp(xs, xl, yl)
    t = yus - yls
    cm = 0.5 * (yus + yls)
    # radio de nariz: círculo por el BA y los 2 puntos vecinos de cada cara
    pts = np.array([[X[i0 - 2], Y[i0 - 2]], [X[i0], Y[i0]], [X[i0 + 2], Y[i0 + 2]]])
    (x1, y1), (x2, y2), (x3, y3) = pts
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    rle = np.hypot(x1 - ux, y1 - uy)
    return dict(tmax=t.max(), xt=xs[np.argmax(t)], fmax=cm.max(), xf=xs[np.argmax(cm)],
                rle=rle, te=Y[0] - Y[-1])


PERFILES = {
    "placa7": ("Placa curvada 7 % (t 1,5 %)", lambda: placa(0.07, 0.015)),
    "placa4": ("Placa curvada 4 % (t 1,5 %)", lambda: placa(0.04, 0.015)),
    "plana3": ("Placa plana 3 %", lambda: placa(0.0, 0.03)),
    "clarky": ("Fondo plano tipo Clark Y", lambda: clarky()[0]),
    "naca6412": ("NACA 6412", lambda: naca4("6412")),
    "naca0012": ("NACA 0012", lambda: naca4("0012")),
    "placa7_t11": ("Placa curvada 7 % (t 1,1 %)", lambda: placa(0.07, 0.011)),
    "placa7_t20": ("Placa curvada 7 % (t 2,0 %)", lambda: placa(0.07, 0.020)),
    "placa7_le2": ("Placa curvada 7 % (t 1,5 %, nariz roma)", lambda: placa(0.07, 0.015, a_rel=0.25)),
}


def main():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    filas = []
    for k, (nombre, fn) in PERFILES.items():
        X, Y = fn()
        with open(os.path.join(RAW, k + ".dat"), "w") as f:
            f.write(k + "\n")
            for x, y in zip(X, Y):
                f.write(f"{x:12.8f} {y:12.8f}\n")
        if not k.startswith("placa7_"):
            with open(os.path.join(DATA, f"polares_geom_{k}.dat"), "w") as f:
                f.write("x y\n")
                for x, y in zip(X, Y):
                    f.write(f"{x:.6f} {y:.6f}\n")
        p = propiedades(X, Y)
        filas.append((k, nombre, p))
    _, ang = clarky()
    with open(os.path.join(DATA, "polares_geom_resumen.dat"), "w") as f:
        f.write("perfil tmax xt fmax xf rle te\n")
        for k, nombre, p in filas:
            f.write(f"{k} {p['tmax']:.5f} {p['xt']:.3f} {p['fmax']:.5f} {p['xf']:.3f} "
                    f"{p['rle']:.5f} {p['te']:.5f}\n")
    for k, nombre, p in filas:
        print(f"{k:12s} t={100*p['tmax']:5.2f}% @x={p['xt']:.2f}  f={100*p['fmax']:5.2f}% @x={p['xf']:.2f}"
              f"  rLE={100*p['rle']:.3f}%  BF={100*p['te']:.3f}%")
    print(f"Clark Y: giro de la cuerda respecto del fondo plano = {ang:.2f} grados")
    # Zoom del borde de ataque de la placa 7 % (para la figura de detalle)
    X, Y = placa(0.07, 0.015)
    i = X < 0.08
    with open(os.path.join(DATA, "polares_geom_placa7_ba.dat"), "w") as f:
        f.write("x y\n")
        for x, y in zip(X[i], Y[i]):
            f.write(f"{x:.6f} {y:.6f}\n")
    X, Y = placa(0.07, 0.015)
    i = X > 0.80
    with open(os.path.join(DATA, "polares_geom_placa7_bf.dat"), "w") as f:
        f.write("x y\n")
        for x, y in zip(X[i], Y[i]):
            f.write(f"{x:.6f} {y:.6f}\n")


if __name__ == "__main__":
    main()
