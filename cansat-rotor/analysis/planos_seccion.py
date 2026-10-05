#!/usr/bin/env python3
"""Sección A-A del CanSat plegado dentro del tubo del cohete (plano 15).

Para cada dirección de desplazamiento lateral phi del cuerpo dentro del tubo
(radio interior Rt) calcula el desplazamiento máximo hasta el primer contacto y la
holgura que queda en los bordes de las palas plegadas. Compara:
  base   : palas con bordes en Ø95 (sin patines; diseño del capítulo 6)
  patin  : 4 patines Ø95 a 45° de las palas, palas desplazadas a bordes en Ø94
Salida: analysis/data/planos_seccion.dat
"""
import os
import numpy as np
from scipy.optimize import brentq

here = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(here, "data")

Rc, c = 81.9, 45.0          # radio de curvatura y cuerda de la pala [mm]
half = np.arcsin(c / 2 / Rc)  # semiángulo del arco


def blade_pts(edge_r, az, n=81):
    """Arco de la pala (cara cóncava hacia el eje) con bordes en el radio edge_r."""
    # centro del arco a distancia d del eje sobre el azimut de la pala
    f = lambda d: np.hypot(Rc * np.sin(half), d + Rc * np.cos(half)) - edge_r
    d = brentq(f, -80, 0)
    t = np.linspace(-half, half, n)
    x_loc = Rc * np.sin(t)              # tangencial
    y_loc = d + Rc * np.cos(t)          # radial
    ca, sa = np.cos(az), np.sin(az)
    return np.c_[y_loc * ca - x_loc * sa, y_loc * sa + x_loc * ca], d + Rc


def patin_pts(az, r_out=47.5, w=4.0, n=9):
    s = np.linspace(-w / 2, w / 2, n)
    ca, sa = np.cos(az), np.sin(az)
    rr = np.sqrt(r_out**2 - s**2)
    return np.c_[rr * ca - s * sa, rr * sa + s * ca]


def config(edge_r, patines):
    blades, mids = [], []
    for k in range(4):
        p, mid = blade_pts(edge_r, np.radians(90 * k))
        blades.append(p); mids.append(mid)
    B = np.vstack(blades)
    P = np.vstack([patin_pts(np.radians(45 + 90 * k)) for k in range(4)]) if patines else np.zeros((0, 2))
    return B, P, mids[0]


def sweep(B, P, Rt, phis):
    out = []
    allp = np.vstack([B, P]) if len(P) else B
    for ph in phis:
        u = np.array([np.cos(ph), np.sin(ph)])
        # |p + delta u| = Rt  ->  delta = -p.u + sqrt((p.u)^2 - |p|^2 + Rt^2)
        pu = allp @ u
        dl = -pu + np.sqrt(pu**2 - (allp**2).sum(1) + Rt**2)
        dmax = dl.min()
        rb = np.linalg.norm(B + dmax * u, axis=1)
        out.append((dmax, Rt - rb.max()))
    return np.array(out)


phis = np.radians(np.arange(0, 90.01, 0.5))
cases = {}
for Dt_lab, Rt in (("98", 49.0), ("97", 48.5)):
    Bb, Pb, midb = config(47.5, False)
    Bp, Pp, midp = config(47.0, True)
    cases["base" + Dt_lab] = sweep(Bb, Pb, Rt, phis)
    cases["pat" + Dt_lab] = sweep(Bp, Pp, Rt, phis)
print(f"base: bordes r=47,5 ; centro de pala r={midb:.2f} (holgura al cuerpo {midb-44:.2f} mm)")
print(f"patín: bordes r=47,0 ; centro de pala r={midp:.2f} (holgura al cuerpo {midp-44:.2f} mm)")
print(f"semiángulo de la pala visto desde el eje: {np.degrees(np.arctan2(22.5, 41.85)):.1f} deg (base)")
for k, v in cases.items():
    print(f"{k:7s} desplaz. lateral máx: {v[:,0].min():.2f}..{v[:,0].max():.2f} mm ; "
          f"holgura mínima en palas tras el contacto: {v[:,1].min():.3f} mm (máx {v[:,1].max():.3f})")
with open(os.path.join(DATA, "planos_seccion.dat"), "w") as f:
    f.write("phi " + " ".join(f"d_{k} g_{k}" for k in cases) + "\n")
    for i, ph in enumerate(phis):
        f.write(f"{np.degrees(ph):.1f} " + " ".join(f"{cases[k][i,0]:.4f} {cases[k][i,1]:.4f}" for k in cases) + "\n")
# frecuencia de paso de palas vista por la cámara cenit
Om = 120.1
fb = 4 * Om / (2 * np.pi)
for fps in (25, 30, 60):
    k = np.round(fb / fps)
    print(f"paso de palas {fb:.1f} Hz, cámara {fps} fps -> alias {abs(fb - k*fps):.1f} Hz")
