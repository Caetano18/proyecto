#!/usr/bin/env python3
"""Dinámica de la pala en giro: Rayleigh-Ritz con rigidización centrífuga (Southwell),
diagrama de Campbell, divergencia torsional, torsión estática y flameo (p-k, Theodorsen).

Modelo de pala (x medido desde la bisagra, 0 <= x <= Lb = 0,156 m):
  - tramo de portapala 0 <= x <= 0,020 m (rígido, +2 g);
  - tramo libre de carbono 0,020 <= x <= 0,156 m con las propiedades de
    estructura_seccion.py.
Batimiento: bisagra articulada con resorte de apertura; base x^k, k>=1 (incluye el
modo rígido). Arrastre: sin bisagra; raíz con rigidez de giro k_zeta de las orejas
impresas (banda 30-150 N m/rad). Torsión: tramo libre empotrado en el portapala;
alabeo restringido (base xi^k, k>=2) o libre (k>=1), con efecto trapecio y momento de
hélice.
Uso: python3 analysis/estructura_modal.py
"""
import os
import numpy as np
from scipy.linalg import eigh, eig
from scipy.special import hankel2
import estructura_seccion as SEC

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
rho = 1.225
R, e = 0.200, 0.044
Lb = R - e
XP = 0.020             # largo del portapala
M_PP = 2.0e-3          # masa del portapala
K_BETA = 0.005         # resorte de apertura [N m/rad] (orden de magnitud)
A_LIFT = 5.7           # pendiente de sustentación [1/rad]
X_AC = 0.25            # centro aerodinámico / cuerda
OM_D = 120.1           # velocidad de giro de diseño [rad/s]
NG = 24
xg_, wg_ = np.polynomial.legendre.leggauss(NG)


def quad(a, b):
    return 0.5 * (b - a) * xg_ + 0.5 * (b + a), 0.5 * (b - a) * wg_


def blade(cfg):
    s = SEC.get(cfg)
    return s


def mass_line(s, x):
    """masa por unidad de largo a la distancia x de la bisagra."""
    return np.where(x < XP, s["m"] + M_PP / XP, s["m"])


def tension(s, x, Om):
    """N(x) = Om^2 * integral_x^Lb m(xi) (e + xi) dxi."""
    out = np.zeros_like(x)
    for i, xi in enumerate(np.atleast_1d(x)):
        segs = [(xi, XP), (XP, Lb)] if xi < XP else [(xi, Lb)]
        acc = 0.0
        for a, b in segs:
            if b <= a:
                continue
            xx, ww = quad(a, b)
            acc += (mass_line(s, xx) * (e + xx) * ww).sum()
        out[i] = Om**2 * acc
    return out


# ---------------------------------------------------------------- batimiento y arrastre
def bending_mats(s, kind, Om, nb=7, k_root=0.0):
    """Matrices de Ritz para batimiento ('flap') o arrastre ('lag')."""
    EI = s["EI_flap"] if kind == "flap" else s["EI_lag"]
    K = np.zeros((nb, nb)); M = np.zeros((nb, nb))
    ks = np.arange(1, nb + 1)
    for a, b, fac in [(0.0, XP, 20.0), (XP, Lb, 1.0)]:
        x, w = quad(a, b)
        u = x / Lb
        phi = np.array([u**k for k in ks])
        d1 = np.array([k * u**(k - 1) / Lb for k in ks])
        d2 = np.array([k * (k - 1) * u**np.maximum(k - 2, 0) / Lb**2 for k in ks])
        m = mass_line(s, x); N = tension(s, x, Om)
        K += (d2 * EI * fac * w) @ d2.T + (d1 * N * w) @ d1.T
        if kind == "lag":
            K -= Om**2 * (phi * m * w) @ phi.T
        M += (phi * m * w) @ phi.T
    # resorte en la raíz: w'(0) = q1/Lb
    K[0, 0] += k_root / Lb**2
    return K, M


def freqs(K, M):
    lam = eigh(K, M, eigvals_only=True)
    return np.sqrt(np.clip(lam, 0, None))


# ---------------------------------------------------------------- torsión
def torsion_mats(s, Om, warp="restr", nb=7, aero=0.0):
    """Matrices de torsión del tramo libre. aero: factor sobre la rigidez aerodinámica
    negativa (1 = divergencia con q local)."""
    Lf = Lb - XP
    k0 = 2 if warp == "restr" else 1
    ks = np.arange(k0, k0 + nb)
    xi, w = quad(0.0, Lf)
    x = xi + XP; r = e + x
    u = xi / Lf
    phi = np.array([u**k for k in ks])
    d1 = np.array([k * u**(k - 1) / Lf for k in ks])
    d2 = np.array([k * (k - 1) * u**np.maximum(k - 2, 0) / Lf**2 for k in ks])
    N = tension(s, x, Om)
    C = SEC.C
    e_ac = s["y_sc"] - X_AC * C
    K_s = (d1 * s["GJ"] * w) @ d1.T + (d2 * s["EGam"] * w) @ d2.T
    K_N = (d1 * N * s["kA2"] * w) @ d1.T
    K_p = Om**2 * (s["Jy"] - s["Jz"]) * (phi * w) @ phi.T
    K_a = (phi * (0.5 * rho * (Om * r)**2 * C * A_LIFT * e_ac) * w) @ phi.T
    M = (phi * s["Ith"] * w) @ phi.T
    return K_s, K_N, K_p, K_a, M, phi, w, r, u


def torsion_freq(s, Om, warp="restr", aero=False):
    K_s, K_N, K_p, K_a, M, *_ = torsion_mats(s, Om, warp)
    K = K_s + K_N + K_p - (K_a if aero else 0)
    return freqs(K, M)[0]


def divergence(s, warp="restr"):
    """Om_D^2: K_s q = Om^2 (K_a1 - K_N1 - K_p1) q, con matrices por unidad de Om^2."""
    K_s, K_N, K_p, K_a, M, *_ = torsion_mats(s, 1.0, warp)
    G = K_a - K_N - K_p
    lam = eig(K_s, G, right=False)
    lam = np.real(lam[np.isfinite(lam) & (np.abs(np.imag(lam)) < 1e-9) & (np.real(lam) > 0)])
    return np.sqrt(lam.min()) if lam.size else np.inf


def static_twist(s, Om, Cm0, Cl, theta0=np.radians(-3.0), warp="restr"):
    """Giro de punta [rad] (positivo = nariz arriba) por Cm0, Cl en el c.a. y momento de hélice."""
    K_s, K_N, K_p, K_a, M, phi, w, r, u = torsion_mats(s, Om, warp)
    C = SEC.C
    q = 0.5 * rho * (Om * r)**2
    e_ac = s["y_sc"] - X_AC * C
    mt = q * C**2 * Cm0 + q * C * Cl * e_ac - Om**2 * (s["Jy"] - s["Jz"]) * theta0
    F = (phi * mt * w).sum(axis=1)
    Kt = K_s + K_N + K_p - K_a
    qv = np.linalg.solve(Kt, F)
    return qv.sum()              # phi(1) = sum q_k


# ---------------------------------------------------------------- flameo p-k
def theodorsen(k):
    k = max(k, 1e-6)
    H1, H0 = hankel2(1, k), hankel2(0, k)
    return H1 / (H1 + 1j * H0)


def pk_damping(s, Om, x_cg=None, r_ref=0.75 * R):
    """Amortiguamiento (parte real/|imag|) de los modos aeroelásticos de la sección típica."""
    C = SEC.C; b = C / 2
    U = Om * r_ref
    m = s["m"]
    yg = s["yg"] if x_cg is None else x_cg * C
    # inercia polar respecto del c.c. corregida si se mueve el c.m. con masa en el BA
    a = (s["y_sc"] - b) / b
    xa = (yg - s["y_sc"]) / b
    Ia = s["Ith"] + m * ((yg - s["y_sc"])**2 - (s["yg"] - s["y_sc"])**2)
    # frecuencias en vacío a Om
    wh = np.sqrt((1 + 1.5 * e / Lb) * Om**2 + K_BETA / 6.0e-5)
    wa = torsion_freq(s, Om, "restr")
    kh, ka = m * wh**2, Ia * wa**2
    Ms = np.array([[m, m * b * xa], [m * b * xa, Ia]])
    Ks = np.diag([kh, ka])
    out = []
    for p0 in (wh, wa):
        p = 1j * p0
        for _ in range(60):
            k = abs(p.imag) * b / U
            Ck = theodorsen(k)
            # fuerzas aerodinámicas (h positivo hacia abajo, alfa nariz arriba)
            Ma = np.pi * rho * b**2 * np.array([[1, -b * a], [-b * a, b**2 * (1 / 8 + a**2)]])
            Da = np.array([[0, np.pi * rho * b**2 * U], [0, np.pi * rho * b**3 * U * (0.5 - a)]])
            Ka = np.zeros((2, 2))
            cc = 2 * np.pi * rho * U * b * Ck
            Da = Da + np.array([[cc, cc * b * (0.5 - a)],
                                [-cc * b * (a + 0.5), -cc * b**2 * (a + 0.5) * (0.5 - a)]])
            Ka = np.array([[0, cc * U], [0, -cc * b * (a + 0.5) * U]])
            MM, DD, KK = Ms + Ma, Da, Ks + Ka
            A = np.block([[np.zeros((2, 2)), np.eye(2)],
                          [-np.linalg.solve(MM, KK), -np.linalg.solve(MM, DD)]])
            ev = np.linalg.eigvals(A)
            ev = ev[ev.imag > 0]
            pn = ev[np.argmin(np.abs(ev - p))]
            if abs(pn - p) < 1e-6 * abs(p):
                p = pn
                break
            p = pn
        out.append(p.real / abs(p.imag))
    return out


def flutter_speed(s, x_cg=None, Om_max=600.0):
    Oms = np.linspace(20, Om_max, 300)
    prev = None
    for Om in Oms:
        g = max(pk_damping(s, Om, x_cg))
        if g > 0:
            return Om
    return np.inf


if __name__ == "__main__":
    rpm = np.linspace(0, 1500, 61)
    Oms = rpm * np.pi / 30
    cfgs = ["A", "B", "BV"]
    S = {c: blade(c) for c in cfgs}
    for c in cfgs:
        s = S[c]
        mb = s["m"] * Lb + M_PP
        print(f"\n===== configuración {c}: m_pala = {mb*1e3:.2f} g")
        Kf, Mf = bending_mats(s, "flap", OM_D, k_root=K_BETA)
        wf = freqs(Kf, Mf)
        print(" batimiento a 1150 rpm [/rev]:", np.round(wf[:3] / OM_D, 2), " Hz:", np.round(wf[:3] / 2 / np.pi, 1))
        Kf0, Mf0 = bending_mats(s, "flap", 0.0, k_root=K_BETA)
        print(" batimiento a 0 rpm [Hz]:", np.round(freqs(Kf0, Mf0)[:3] / 2 / np.pi, 1))
        for kz in (30.0, 150.0):
            Kl, Ml = bending_mats(s, "lag", OM_D, k_root=kz)
            wl = freqs(Kl, Ml)
            print(f" arrastre k_zeta={kz:.0f}: [/rev] {np.round(wl[:2]/OM_D,2)}  Hz {np.round(wl[:2]/2/np.pi,1)}")
        for wp in ("restr", "libre"):
            w0 = torsion_freq(s, 0.0, wp); w1 = torsion_freq(s, OM_D, wp); w1a = torsion_freq(s, OM_D, wp, aero=True)
            print(f" torsión ({wp}): 0 rpm {w0/2/np.pi:.1f} Hz ; 1150 rpm {w1/2/np.pi:.1f} Hz = {w1/OM_D:.2f}/rev ;"
                  f" con rigidez aero {w1a/2/np.pi:.1f} Hz = {w1a/OM_D:.2f}/rev")
            OmD = divergence(s, wp)
            print(f"   divergencia: Om_D = {OmD:.1f} rad/s = {OmD*30/np.pi:.0f} rpm ; Om_D/Om = {OmD/OM_D:.2f}")
        # contribuciones a la rigidez torsional a 1150 rpm (primer modo, restringido)
        K_s, K_N, K_p, K_a, M, *_ = torsion_mats(s, OM_D, "restr")
        lam, vec = eigh(K_s + K_N + K_p, M)
        v = vec[:, 0]
        print("   energía del 1.er modo: elástica %.3f, trapecio %.3f, hélice %.3f, aero(-) %.3f"
              % tuple(float(v @ X @ v) for X in (K_s, K_N, K_p, K_a)))
        for Cm0 in (-0.10, -0.13, -0.23):
            tw = static_twist(s, OM_D, Cm0, 0.9)
            print(f"   giro estático de punta, Cm0={Cm0:+.2f}, Cl=0,9: {np.degrees(tw):+.2f} grados")
        # tensión centrífuga en la raíz del tramo libre y en la bisagra
        print("   tracción centrífuga: bisagra %.2f N ; salida del portapala %.2f N"
              % (tension(s, np.array([0.0]), OM_D)[0], tension(s, np.array([XP]), OM_D)[0]))
        gmax = max(pk_damping(s, OM_D))
        OmF = flutter_speed(s)
        print(f"   flameo p-k: amortiguamiento máx. a 1150 rpm = {gmax:.3f} ; Om_F = {OmF:.0f} rad/s")
    # ---- Campbell
    with open(os.path.join(DATA, "estructura_campbell.dat"), "w") as f:
        f.write("rpm bat bat1 lag30 lag150 torA torAl torB torBV torBVl\n")
        for r_, Om in zip(rpm, Oms):
            sA = S["A"]
            Kf, Mf = bending_mats(sA, "flap", Om, k_root=K_BETA); wf = freqs(Kf, Mf)
            Kl, Ml = bending_mats(sA, "lag", Om, k_root=30.0); wl30 = freqs(Kl, Ml)[0]
            Kl, Ml = bending_mats(sA, "lag", Om, k_root=150.0); wl150 = freqs(Kl, Ml)[0]
            tA = torsion_freq(sA, Om, "restr"); tAl = torsion_freq(sA, Om, "libre")
            tB = torsion_freq(S["B"], Om, "restr")
            tBV = torsion_freq(S["BV"], Om, "restr"); tBVl = torsion_freq(S["BV"], Om, "libre")
            hz = lambda v: v / 2 / np.pi
            f.write(f"{r_:.0f} {hz(wf[0]):.3f} {hz(wf[1]):.2f} {hz(wl30):.2f} {hz(wl150):.2f} "
                    f"{hz(tA):.2f} {hz(tAl):.2f} {hz(tB):.2f} {hz(tBV):.2f} {hz(tBVl):.2f}\n")
    # ---- flameo frente a la posición del c.m. (configuraciones A y BV)
    with open(os.path.join(DATA, "estructura_flameo.dat"), "w") as f:
        f.write("xcg OmF_A OmF_BV\n")
        for xcg in np.arange(0.30, 0.701, 0.025):
            fa = flutter_speed(S["A"], xcg, 800.0)
            fb = flutter_speed(S["BV"], xcg, 800.0)
            # sin flameo hasta 800 rad/s -> nan (pgfplots corta la curva)
            fs = lambda v: "nan" if not np.isfinite(v) else f"{v*30/np.pi:.0f}"
            f.write(f"{xcg:.3f} {fs(fa)} {fs(fb)}\n")
            print(f" x_cg/c={xcg:.3f}: rpm de flameo A={fa*30/np.pi:.0f}  BV={fb*30/np.pi:.0f}")
