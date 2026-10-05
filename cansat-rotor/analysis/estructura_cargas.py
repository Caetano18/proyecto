#!/usr/bin/env python3
"""Cargas, tensiones, rodamientos, fatiga e impacto (capítulo de estructura).

1. Apertura de las palas (de -90 a +10 grados) con Omega ~ 0 y V = 13,4 m/s:
   modelo de flujo cruzado, golpe contra el tope y momento en la raíz por superposición
   modal (pala con resorte de tope en la bisagra), en función de la rigidez del tope.
2. Momento en la raíz en vuelo estable, con ráfaga y contra el tope en el arranque.
3. Verificaciones de componentes (factores de seguridad) con materiales típicos.
4. Rodamientos 688ZZ (SKF 628/8-2Z): carga equivalente, L10, carga estática.
5. Fatiga 1P y 4P; 6. Impacto de aterrizaje.
Uso: python3 analysis/estructura_cargas.py
"""
import os
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import eigh
import estructura_seccion as SEC
import estructura_modal as MOD

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
rho, g = 1.225, 9.81
R, e, Lb, XP, C = MOD.R, MOD.e, MOD.Lb, MOD.XP, SEC.C
V1 = 13.4            # velocidad de la etapa 1 al liberar
OM = MOD.OM_D
T_ROTOR = 3.78       # empuje del rotor
B = 4
# materiales típicos (no medidos)
PETG_XY, PETG_Z = 45e6, 25e6       # resistencia a tracción impresa en el plano / entre capas
PETG_E = 2.0e9
AL_SY, AL_FAT = 276e6, 96e6        # 6061-T6: fluencia y resistencia a fatiga (5e8 ciclos)
ST_TY = 200e6                      # acero del pasador: fluencia en corte (conservador)
INOX_SY, INOX_TY = 215e6, 125e6    # 304 recocido


def pr(name, val, unit=""):
    print(f"  {name:58s} {val:12.4g} {unit}")


def blade_props(cfg):
    s = SEC.get(cfg)
    x, w = MOD.quad(0.0, XP); x2, w2 = MOD.quad(XP, Lb)
    xx = np.r_[x, x2]; ww = np.r_[w, w2]
    m = MOD.mass_line(s, xx)
    Ib = (m * xx**2 * ww).sum(); Sb = (m * xx * ww).sum(); mb = (m * ww).sum()
    return s, Ib, Sb, mb


# ------------------------------------------------------------------ 1. apertura
def opening(cfg, Cdc, Ms=0.005):
    s, Ib, Sb, mb = blade_props(cfg)
    xq, wq = MOD.quad(0.0, Lb)

    def rhs(t, y):
        b, bd = y
        un = V1 * np.cos(b) - bd * xq
        Ma = (0.5 * rho * Cdc * C * un * np.abs(un) * xq * wq).sum()
        return [bd, (Ma + Ms - Sb * g * np.cos(b)) / Ib]

    ev = lambda t, y: y[0] - np.radians(10.0)
    ev.terminal = True
    sol = solve_ivp(rhs, (0, 2.0), [np.radians(-89.0), 0.0], events=ev, max_step=1e-3, rtol=1e-8)
    return sol, Ib, Sb, s


def stop_impact(cfg, ks, omega_i, nb=8):
    """Momento máximo en la bisagra (tope) y en la salida del portapala tras el golpe.
    Pala con resorte de rigidez ks en la bisagra (el tope), Omega = 0."""
    s = SEC.get(cfg)
    K, M = MOD.bending_mats(s, "flap", 0.0, nb=nb, k_root=ks)
    lam, V = eigh(K, M)
    wn = np.sqrt(np.clip(lam, 1e-9, None))
    # velocidad inicial: rotación rígida w_dot = omega_i * x -> q1 = omega_i * Lb
    qd0 = np.zeros(nb); qd0[0] = omega_i * Lb
    etad0 = V.T @ M @ qd0                    # coordenadas modales (V^T M V = I)
    t = np.linspace(0, 4 * 2 * np.pi / wn[0], 4000)
    eta = (etad0 / wn)[:, None] * np.sin(wn[:, None] * t[None, :])
    q = V @ eta
    ks_ = np.arange(1, nb + 1)
    d1_0 = np.array([1.0 / Lb if k == 1 else 0.0 for k in ks_])
    uP = XP / Lb
    d2_P = np.array([k * (k - 1) * uP**max(k - 2, 0) / Lb**2 for k in ks_])
    M_hinge = ks * (d1_0 @ q)
    M_root = s["EI_flap"] * (d2_P @ q)
    i1 = t <= 2 * np.pi / wn[0] * 0.75
    return np.abs(M_hinge[i1]).max(), np.abs(M_root[i1]).max(), wn[0]


# ------------------------------------------------------------------ 2. vuelo
def flight_moment(cfg, n_lift=1.0, Om=OM, nb=7):
    """Deflexión estática de la pala articulada y momento en la salida del portapala."""
    s = SEC.get(cfg)
    K, M = MOD.bending_mats(s, "flap", Om, nb=nb, k_root=MOD.K_BETA)
    kr = 3 * (T_ROTOR / B) / (R**3 - e**3)           # sustentación ~ r^2
    ks_ = np.arange(1, nb + 1)
    F = np.zeros(nb)
    for a, b in [(0.0, XP), (XP, Lb)]:
        x, w = MOD.quad(a, b)
        phi = np.array([(x / Lb)**k for k in ks_])
        load = n_lift * kr * (e + x)**2 - MOD.mass_line(s, x) * g
        F += (phi * load * w).sum(axis=1)
    q = np.linalg.solve(K, F)
    beta0 = q[0] / Lb
    # momento en XP por equilibrio del tramo exterior con la forma deformada
    x, w = MOD.quad(XP, Lb)
    wdef = sum(q[k - 1] * (x / Lb)**k for k in ks_)
    wP = sum(q[k - 1] * (XP / Lb)**k for k in ks_)
    load = n_lift * kr * (e + x)**2 - MOD.mass_line(s, x) * g
    Ml = (load * (x - XP) * w).sum()
    Mc = (MOD.mass_line(s, x) * Om**2 * (e + x) * (wdef - wP) * w).sum()
    N = MOD.tension(s, np.array([XP]), Om)[0]
    return beta0, Ml - Mc, N


def strain(s, M, N=0.0):
    return M * s["zmax"] / s["EI_flap"] + N / s["EA"]


if __name__ == "__main__":
    out = {}
    print("== 1. Apertura y golpe contra el tope ==")
    with open(os.path.join(DATA, "estructura_apertura.dat"), "w") as f:
        sol, Ib, Sb, s = opening("A", 1.2)
        sol2, *_ = opening("A", 2.0)
        n = 200
        f.write("t beta12 beta20\n")
        t1, t2 = sol.t, sol2.t
        tt = np.linspace(0, max(t1[-1], t2[-1]), n)
        b1 = np.interp(tt, t1, np.degrees(sol.y[0]), right=np.nan)
        b2 = np.interp(tt, t2, np.degrees(sol2.y[0]), right=np.nan)
        for a, b_, c_ in zip(tt, b1, b2):
            f.write(f"{a*1e3:.2f} {b_:.2f} {c_:.2f}\n")
    for cfg in ("A", "BV"):
        print(f" -- configuración {cfg}")
        for Cdc in (1.2, 2.0):
            sol, Ib, Sb, s = opening(cfg, Cdc)
            wi = sol.y[1, -1]
            pr(f"Cdc={Cdc}: tiempo de apertura", sol.t[-1] * 1e3, "ms")
            pr(f"Cdc={Cdc}: velocidad angular en el tope", wi, "rad/s")
            pr(f"Cdc={Cdc}: energía en el golpe", 0.5 * Ib * wi**2, "J")
            out[(cfg, Cdc)] = wi
        pr("I_b (bisagra)", Ib, "kg m2"); pr("S_b", Sb, "kg m")
    # barrido de rigidez del tope
    with open(os.path.join(DATA, "estructura_tope.dat"), "w") as f:
        f.write("ks MhA MrA MhBV MrBV\n")
        for ks in np.logspace(-0.5, 3, 36):
            row = [ks]
            for cfg in ("A", "BV"):
                Mh, Mr, w1 = stop_impact(cfg, ks, out[(cfg, 2.0)])
                row += [Mh, Mr]
            f.write(" ".join(f"{v:.4g}" for v in row) + "\n")
    for cfg in ("A", "BV"):
        for ks in (2.0, 10.0, 250.0):
            Mh, Mr, w1 = stop_impact(cfg, ks, out[(cfg, 2.0)])
            s = SEC.get(cfg)
            eps = strain(s, Mr)
            pr(f"{cfg} tope k={ks:g} N m/rad: M bisagra / M raíz [N m], eps raíz", Mh, f"{Mr:.3f}  eps={eps*100:.3f} %")
            if ks == 2.0:
                th = out[(cfg, 2.0)] * np.sqrt(blade_props(cfg)[1] / ks)
                pr(f"   recorrido del tope blando", np.degrees(th), "grados")

    print("\n== 2. Momento en la raíz en vuelo ==")
    for cfg in ("A", "BV"):
        s = SEC.get(cfg)
        for n_l in (1.0, 1.5):
            b0, Mr, N = flight_moment(cfg, n_l)
            pr(f"{cfg} n={n_l}: conicidad / M raíz / N / eps", np.degrees(b0),
               f"deg  M={Mr:.4f} N m  N={N:.2f} N  eps={strain(s, Mr, N)*100:.4f} %")
        # arranque contra el tope, estático: Omega=0, V=13,4, Cdc=2
        q = 0.5 * rho * V1**2
        Mh = q * 2.0 * C * Lb**2 / 2
        Mr = q * 2.0 * C * (Lb - XP)**2 / 2
        pr(f"{cfg} tope estático (Cdc=2): M bisagra / M raíz / eps", Mh, f"{Mr:.4f}  eps={strain(s, Mr)*100:.4f} %")
        pr(f"{cfg} pliegue cinta: M opuesto / M igual", s["M_opp"], f"{s['M_eq']:.3f} N m")

    print("\n== 3. Componentes ==")
    sA = SEC.get("A")
    Fc = MOD.tension(sA, np.array([0.0]), OM)[0] * 13.1 / 13.1
    Fc_max = MOD.tension(sA, np.array([0.0]), 1500 * np.pi / 30)[0]
    pr("fuerza centrífuga en la bisagra a 1150 / 1500 rpm", Fc, f"/ {Fc_max:.2f} N")
    d = 2e-3; Apin = np.pi * d**2 / 4
    # brazo del tope (plano 4) y golpe
    a_s, a_s2 = 4e-3, 10e-3
    Mh_rig = stop_impact("A", 250.0, out[("A", 2.0)])[0]
    Mh_soft = stop_impact("A", 10.0, out[("A", 2.0)])[0]
    Mh_stat = 0.5 * rho * V1**2 * 2.0 * C * Lb**2 / 2
    for lab, Mh in (("tope estático", Mh_stat), ("golpe tope rígido", Mh_rig), ("golpe tope blando k=10", Mh_soft)):
        for a in (a_s, a_s2):
            Fs = Mh / a
            Fpin = np.hypot(Fs, Fc)
            tau = Fpin / (2 * Apin)
            Mpin = Fpin * (2 * 8.5e-3 - 6e-3) / 8
            sig_pin = 32 * Mpin / (np.pi * d**3)
            # oreja: aplastamiento contra el pasador, espesor total 5 mm; ligamento en Z
            sb = Fpin / (d * 5e-3)
            # tope: contacto 4 x 2 mm
            sc = Fs / (4e-3 * 2e-3)
            pr(f"{lab}, brazo {a*1e3:.0f} mm: F tope", Fs, f"N ; tau pasador {tau/1e6:.1f} MPa ; sigma flex pasador {sig_pin/1e6:.0f} MPa ;"
               f" aplast. oreja {sb/1e6:.1f} MPa ; contacto tope {sc/1e6:.1f} MPa")
    # brazo del cubo: 8 mm alto x 10 mm ancho, largo 22 mm
    Zarm = 10e-3 * 8e-3**2 / 6
    for lab, Mh in (("estático", Mh_stat), ("golpe rígido", Mh_rig), ("golpe blando", Mh_soft)):
        pr(f"brazo del cubo, {lab}: sigma (XY)", 1.2 * Mh / Zarm / 1e6, "MPa")
    pr("brazo del cubo, centrífuga: sigma tracción", Fc / (10e-3 * 8e-3) / 1e6, "MPa")
    # oreja: desgarro por la fuerza centrífuga. e = distancia del CENTRO del agujero al
    # borde (plano 4: 1,3 mm; propuesta: 3 mm). Ligamento = e - d/2; área de corte
    # 2 x (espesor total 5 mm) x ligamento.
    for el in (1.3e-3, 3.0e-3):
        lig = el - d / 2
        tau_so = Fc / (2 * 5e-3 * lig)
        pr(f"oreja, desgarro centrífugo, e={el*1e3:.1f} mm (ligamento {lig*1e3:.1f} mm)", tau_so / 1e6,
           f"MPa ; FS {12e6/tau_so:.1f} (admisible en corte Z 12 MPa)")
    # portapala: cuello 6 x 8 mm (plano 6)
    Zpp = 6e-3 * 8e-3**2 / 6
    pr("portapala, cuello 6x8: sigma con golpe rígido / blando / estático", Mh_rig / Zpp / 1e6,
       f"/ {Mh_soft/Zpp/1e6:.1f} / {Mh_stat/Zpp/1e6:.2f} MPa")
    # cubo con rodamientos a presión (Lamé), PETG D=44, d=16, ancho 2 x 5 mm
    D, dd, wfit, mu = 44e-3, 16e-3, 10e-3, 0.3
    for delta in (0.02e-3, 0.05e-3, 0.10e-3):
        kk = (D**2 + dd**2) / (D**2 - dd**2)
        p = delta / (dd * ((kk + 0.38) / PETG_E + (1 - 0.3) / 200e9))
        sh = p * kk
        Fax = mu * p * np.pi * dd * wfit
        Tq = Fax * dd / 2
        pr(f"ajuste delta={delta*1e3:.2f} mm: p / sigma_theta / F axial / par", p / 1e6,
           f"MPa  {sh/1e6:.1f} MPa  {Fax:.0f} N  {Tq:.2f} N m")
    # eje Al Ø8x5
    Z8 = np.pi * (8e-3**4 - 5e-3**4) / (32 * 8e-3)
    Zth = np.pi * (7.19e-3**4 - 5e-3**4) / (32 * 7.19e-3)
    S_b = blade_props("A")[2]
    Mhub = (B / 2) * e * OM**2 * S_b * np.radians(5.0)
    pr("momento de cubo por inclinación de 5 grados del disco", Mhub, "N m")
    for lab, F_u in (("0,1 g", 0.1e-3 * 0.12 * OM**2), ("1 g", 1e-3 * 0.12 * OM**2)):
        M = Mhub + F_u * 8.5e-3
        pr(f"eje en la tapa, desbalance {lab} + cubo: sigma", M / Z8 / 1e6, "MPa")
    for Tc, lab in ((23.0, "apertura 25 m/s"), (44.0, "apertura 35 m/s"), (147.0, "30 G")):
        Fl = Tc * np.sin(np.radians(30))
        s_cap = Fl * 44e-3 / Z8 * 1.5
        s_th = Fl * 25.5e-3 / Zth * 2.5
        pr(f"eje, cuerda a 30 grados, {lab}: sigma tapa (Kt 1,5) / rosca (Kt 2,5)", s_cap / 1e6,
           f"/ {s_th/1e6:.0f} MPa ; FS {AL_SY/max(s_cap, s_th):.1f}")
    # pestaña de inoxidable y diente
    mbA = blade_props("A")[3]
    for G_, lab in ((30, "30 G"), (15, "15 G")):
        F = mbA * G_ * g
        sig_net = F / ((3e-3 - 1.5e-3) * 0.5e-3)
        tau_to = F / (2 * 1.0e-3 * 0.5e-3)
        sig_tooth = 6 * F * 1.0e-3 / (1.2e-3 * 0.8e-3**2)
        pr(f"pestaña/diente {lab}: F", F, f"N ; sigma neta {sig_net/1e6:.1f} ; desgarro {tau_to/1e6:.1f} ; diente {sig_tooth/1e6:.1f} MPa")
    # tubo
    At = np.pi * 86e-3 * 2e-3
    F30 = 0.5 * 30 * g
    s_ax = F30 / At
    s_cr = PETG_E * 2e-3 / (43e-3 * np.sqrt(3 * (1 - 0.38**2)))
    pr("tubo: sigma axial 30 G / con Kt=3", s_ax / 1e6, f"/ {3*s_ax/1e6:.2f} MPa")
    pr("tubo: pandeo clásico / x0,3 / x0,3 x0,5 (aberturas)", s_cr / 1e6, f"/ {0.3*s_cr/1e6:.1f} / {0.15*s_cr/1e6:.1f} MPa")
    pr("tubo: parámetro de Starnes r/sqrt(R t) para Ø8", 4e-3 / np.sqrt(43e-3 * 2e-3))

    print("\n== 4. Rodamientos 628/8-2Z ==")
    Cdyn, C0 = 1330.0, 570.0
    F_u = 0.1e-3 * 0.12 * OM**2
    Fr_couple = Mhub / 8e-3
    for lab, Fa, Fr in (("vuelo", T_ROTOR, F_u / 2 + Fr_couple), ("ráfaga 1,5", 1.5 * T_ROTOR, F_u / 2 + 1.5 * Fr_couple)):
        ratio = Fa / C0
        e_ = 0.19 if ratio <= 0.014 else 0.22
        Y = 2.30 if ratio <= 0.014 else 1.99
        P = (0.56 * Fr + Y * Fa) if Fa / Fr > e_ else Fr
        L10 = (Cdyn / P)**3
        hrs = L10 * 1e6 / (1150 * 60)
        pr(f"{lab}: Fa={Fa:.2f} N Fr={Fr:.2f} N -> P", P, f"N ; L10={L10:.3g} Mrev = {hrs:.3g} h")
    for lab, acc in (("30 G", 30), ("aterrizaje 150 g", 150), ("aterrizaje 500 g", 500)):
        Fa = 0.075 * acc * g
        P0 = max(0.5 * Fa, Fa * 0.5)
        pr(f"carga estática {lab}: Fa", Fa, f"N ; s0 = {C0/P0:.1f}")
    pr("n / n_lim", 1150 / 45000 * 100, "%")

    print("\n== 5. Fatiga ==")
    N_life = 1e6
    eps_steady = strain(SEC.get("A"), flight_moment("A")[1], flight_moment("A")[2])
    pr("pala A: eps medio", eps_steady * 100, "%")
    pr("pala: admisible en fatiga a 1e6 (1 - 0,07 log N) x 1,0 %", (1 - 0.07 * 6) * 1.0, "%")
    Mcyc = Fc * np.radians(5.0) * 22e-3
    pr("brazo PETG: sigma alternante 1P (inclinación 5 grados)", Mcyc / Zarm / 1e6, "MPa")
    pr("eje: sigma alternante 1P con desbalance 1 g", 1e-3 * 0.12 * OM**2 * 8.5e-3 / Z8 / 1e6, "MPa")
    print("  revoluciones por vuelo (90 s):", 1150 * 1.5, " campaña de ensayos estimada:", 1150 * 60 * 1.0)

    print("\n== 6. Impacto ==")
    for V in (6.4, 7.8):
        E = 0.5 * 0.5 * V**2
        pr(f"V={V}: energía", E, "J")
        for s_, lab in ((2e-3, "suelo duro, sin amortiguador"), (10e-3, "suelo blando"),
                        (17.5e-3, "espuma 25 mm"), (27.5e-3, "espuma + suelo blando")):
            a = V**2 / (2 * s_ * 0.8)
            pr(f"   {lab} (s={s_*1e3:.1f} mm): a", a / g, "g")
    sp = 0.5 * 7.8**2 / (0.8 * 17.5e-3) * 0.5 / (np.pi / 4 * (88e-3**2 - 58e-3**2))
    pr("tensión de meseta necesaria (7,8 m/s, anillo 88/58)", sp / 1e6, "MPa")
    for acc in (150, 200):
        pr(f"a {acc} g: batería 55 g / rotor 54 g / lastre 83 g [N]", 0.055 * acc * g,
           f"/ {0.054*acc*g:.0f} / {0.083*acc*g:.0f}")
    pr("energía del rotor a 1150 rpm", 0.5 * 5.13e-4 * OM**2, "J")
