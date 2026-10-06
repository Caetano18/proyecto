#!/usr/bin/env python3
"""Sección A-A del CanSat plegado dentro del tubo del cohete (plano 15).

Para cada dirección de desplazamiento lateral phi del cuerpo dentro del tubo
(radio interior Rt) calcula el desplazamiento máximo hasta el primer contacto y la
holgura que queda en los bordes de las palas plegadas. Compara:
  base   : palas con bordes en Ø95 (sin patines; diseño del capítulo 6, cuerpo Ø88)
  patin  : 4 patines Ø95 a 45° de las palas, palas con bordes en Ø94 y cuerpo Ø87
  alt8   : 8 patines Ø95 junto a los bordes de pala (±33° del centro de la pala),
           palas con bordes en Ø94,5 y cuerpo Ø88
Convención (igual que la sección "Plegado dentro de Ø95" del cap. 5): el arco de radio
Rc es la cara EXTERIOR de la pala; la cara interior está 0,5 mm (espesor) más adentro.
Revisión: la versión anterior proponía bordes en Ø94 con cuerpo Ø88, lo que no es
posible: la cara interior de la pala quedaría 0,08 mm dentro de la pared del cuerpo.
Salida: analysis/data/planos_seccion.dat
"""
import os
import numpy as np
from scipy.optimize import brentq

here = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(here, "data")

Rc, c = 81.9, 45.0          # radio de curvatura y cuerda de la pala [mm]
t_pala = 0.5                # espesor de la placa [mm]
half = np.arcsin(c / 2 / Rc)  # semiángulo del arco
s_fl = Rc - np.sqrt(Rc**2 - (c / 2)**2)  # flecha del arco (3,15 mm)


def mid_r(edge_r):
    """Radio de la cara exterior en el centro de la cuerda, dados los bordes en edge_r."""
    return np.sqrt(edge_r**2 - (c / 2)**2) + s_fl


def edge_from_gap(gap, r_body):
    """Radio de los bordes si la cara interior queda a 'gap' de un cuerpo de radio r_body."""
    return np.hypot(r_body + t_pala + gap - s_fl, c / 2)


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


def config(edge_r, pat_az):
    """pat_az: azimuts de los patines en grados (lista vacía = sin patines)."""
    blades, mids = [], []
    for k in range(4):
        p, mid = blade_pts(edge_r, np.radians(90 * k))
        blades.append(p); mids.append(mid)
    B = np.vstack(blades)
    P = np.vstack([patin_pts(np.radians(a)) for a in pat_az]) if len(pat_az) else np.zeros((0, 2))
    return B, P, mids[0]


PAT4 = [45 + 90 * k for k in range(4)]
PAT8 = [a + 90 * k for k in range(4) for a in (33, 57)]


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
R_88, R_87 = 44.0, 43.5
# ---- verificación de factibilidad (cara interior de la pala frente al cuerpo)
print("== Cara interior de la pala frente al cuerpo (espesor 0,5 mm) ==")
for lab, edge, rb in (("base: bordes Ø95, cuerpo Ø88", 47.5, R_88),
                      ("propuesta original: bordes Ø94, cuerpo Ø88", 47.0, R_88),
                      ("patin: bordes Ø94, cuerpo Ø87", 47.0, R_87)):
    gap = mid_r(edge) - t_pala - rb
    print(f"{lab:46s} cara ext. al centro r={mid_r(edge):.2f}  juego al cuerpo {gap:+.2f} mm")
edge_alt = edge_from_gap(0.2, R_88)
print(f"alt8: juego 0,2 mm con cuerpo Ø88 -> bordes en r={edge_alt:.2f} (Ø{2*edge_alt:.1f})")
for edge in (47.5, 47.0, 47.25):
    print(f"bordes r={edge}: semiángulo de la pala visto desde el eje {np.degrees(np.arcsin(22.5/edge)):.1f} deg")

cases = {}
for Dt_lab, Rt in (("98", 49.0), ("97", 48.5)):
    Bb, Pb, _ = config(47.5, [])
    Bp, Pp, _ = config(47.0, PAT4)
    Ba, Pa, _ = config(edge_alt, PAT8)
    Bo, Po, _ = config(edge_alt, PAT4)
    cases["base" + Dt_lab] = sweep(Bb, Pb, Rt, phis)
    cases["pat" + Dt_lab] = sweep(Bp, Pp, Rt, phis)
    cases["alt" + Dt_lab] = sweep(Ba, Pa, Rt, phis)
    cases["p4e" + Dt_lab] = sweep(Bo, Po, Rt, phis)   # 4 patines a 45° con bordes Ø94,5
print("\n== Juego lateral y holgura en los bordes de pala ==")
for k, v in cases.items():
    print(f"{k:7s} desplaz. lateral máx: {v[:,0].min():.2f}..{v[:,0].max():.2f} mm ; "
          f"holgura mínima en palas tras el contacto: {v[:,1].min():.3f} mm (máx {v[:,1].max():.3f})")
with open(os.path.join(DATA, "planos_seccion.dat"), "w") as f:
    f.write("phi " + " ".join(f"d_{k} g_{k}" for k in cases) + "\n")
    for i, ph in enumerate(phis):
        f.write(f"{np.degrees(ph):.1f} " + " ".join(f"{cases[k][i,0]:.4f} {cases[k][i,1]:.4f}" for k in cases) + "\n")
# masa de los patines (PETG macizo, 1,27 g/cm3); alto radial = 47,5 - radio del cuerpo
for lab, n, h, L in (("patin (cuerpo Ø87)", 4, 4.0, 205), ("patin, tacos 2 x 20 mm", 4, 4.0, 40),
                     ("alt8 (cuerpo Ø88)", 8, 3.5, 205), ("alt8, tacos 2 x 20 mm", 8, 3.5, 40)):
    print(f"{lab:24s} {n} x (4 x {h} x {L} mm): {n * 4 * h * L * 1.27e-3:.1f} g")
# frecuencia de paso de palas vista por la cámara cenit
Om = 120.1
fb = 4 * Om / (2 * np.pi)
for fps in (25, 30, 60):
    k = np.round(fb / fps)
    print(f"paso de palas {fb:.1f} Hz, cámara {fps} fps -> alias {abs(fb - k*fps):.1f} Hz")
