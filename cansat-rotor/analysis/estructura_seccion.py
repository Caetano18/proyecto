#!/usr/bin/env python3
"""Laminado y propiedades de sección de la pala curvada (capítulo de estructura).

- Teoría clásica de laminados (TCL) para dos apilados de 0,5 mm.
- Sección abierta de pared delgada: arco circular (Rc = 81,9 mm, c = 45 mm) con una
  varilla opcional en el borde de ataque, discretizada en segmentos rectos.
  Centroide ponderado por módulo, EI en batimiento y en el plano, GJ (Saint-Venant),
  centro de corte por flujo de corte, constante de alabeo (coordenada sectorial),
  masa por unidad de largo, centro de masa e inercias de masa.
Unidades SI. Uso: python3 analysis/estructura_seccion.py
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# ---------------------------------------------------------------- materiales
# Valores TÍPICOS de catálogo para carbono/epoxi (incertidumbre +-15 %); no medidos.
MAT = {
    # tejido sarga 3K, vf ~ 0,45-0,50, propiedades de la lámina (E1 = E2)
    "W":  dict(E1=55e9, E2=55e9, G12=4.0e9, nu12=0.05, rho=1500.0),
    # unidireccional clase T300/T700, vf ~ 0,55
    "UD": dict(E1=125e9, E2=8.5e9, G12=4.5e9, nu12=0.30, rho=1550.0),
}
ROD = dict(E=125e9, G=4.5e9, rho=1550.0)     # varilla pultruida de carbono
EPS_UT, EPS_UC = 0.010, 0.008                 # deformación última típica (tracción, compresión)

# ---------------------------------------------------------------- geometría
C = 0.045            # cuerda
RC = 0.0819          # radio de curvatura (arco del 7 %)
T_LAM = 0.5e-3       # espesor


def Qbar(mat, ang):
    m = MAT[mat]
    E1, E2, G12, n12 = m["E1"], m["E2"], m["G12"], m["nu12"]
    n21 = n12 * E2 / E1
    d = 1 - n12 * n21
    Q11, Q22, Q12, Q66 = E1 / d, E2 / d, n12 * E2 / d, G12
    c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    Qb = np.zeros((3, 3))
    Qb[0, 0] = Q11*c**4 + 2*(Q12 + 2*Q66)*s**2*c**2 + Q22*s**4
    Qb[1, 1] = Q11*s**4 + 2*(Q12 + 2*Q66)*s**2*c**2 + Q22*c**4
    Qb[0, 1] = Qb[1, 0] = (Q11 + Q22 - 4*Q66)*s**2*c**2 + Q12*(s**4 + c**4)
    Qb[2, 2] = (Q11 + Q22 - 2*Q12 - 2*Q66)*s**2*c**2 + Q66*(s**4 + c**4)
    Qb[0, 2] = Qb[2, 0] = (Q11 - Q12 - 2*Q66)*s*c**3 + (Q12 - Q22 + 2*Q66)*s**3*c
    Qb[1, 2] = Qb[2, 1] = (Q11 - Q12 - 2*Q66)*s**3*c + (Q12 - Q22 + 2*Q66)*s*c**3
    return Qb


def woven(ang):
    """Lámina de tejido balanceado: promedio de +ang y -ang (sin acoplamientos)."""
    return 0.5 * (Qbar("W", ang) + Qbar("W", -ang))


def clt(plies):
    """plies: lista de (Q [3x3], t, rho) de abajo hacia arriba."""
    t = sum(p[1] for p in plies)
    z = -t / 2
    A = np.zeros((3, 3)); B = np.zeros((3, 3)); D = np.zeros((3, 3)); mass = 0.0
    for Q, tk, rho in plies:
        z0, z1 = z, z + tk
        A += Q * (z1 - z0); B += Q * (z1**2 - z0**2) / 2; D += Q * (z1**3 - z0**3) / 3
        mass += rho * tk; z = z1
    a = np.linalg.inv(A); d = np.linalg.inv(D)
    return dict(t=t, A=A, B=B, D=D, Em=1 / (t * a[0, 0]), D11=1 / d[0, 0], D66=1 / d[2, 2],
                D11raw=D[0, 0], nu=-a[0, 1] / a[0, 0], Gm=1 / (t * a[2, 2]),
                Eb=12 / (d[0, 0] * t**3), Gb=12 / (d[2, 2] * t**3), areal=mass)


LAMINADOS = {
    # A: base del informe, dos capas de tejido 0/90 de 0,25 mm
    "A": [(woven(0), 0.25e-3, 1500.0), (woven(0), 0.25e-3, 1500.0)],
    # B: recomendado, [(+-45)W / 0UD / 0UD / (+-45)W], 4 x 0,125 mm
    "B": [(woven(45), 0.125e-3, 1500.0), (Qbar("UD", 0), 0.125e-3, 1550.0),
          (Qbar("UD", 0), 0.125e-3, 1550.0), (woven(45), 0.125e-3, 1500.0)],
}


def seccion(lam, d_rod=0.0, n=400):
    """Propiedades de la sección (arco + varilla opcional en el borde de ataque)."""
    L = clt(LAMINADOS[lam])
    a_half = np.arcsin(C / 2 / RC)
    sag = RC - np.sqrt(RC**2 - C**2 / 4)
    zc0 = sag - RC                                  # centro del arco
    th = np.linspace(np.pi / 2 + a_half, np.pi / 2 - a_half, n + 1)   # de BA a BF
    y = C / 2 + RC * np.cos(th); z = zc0 + RC * np.sin(th)
    dy, dz = np.diff(y), np.diff(z); ds = np.hypot(dy, dz)
    ym, zm = 0.5 * (y[1:] + y[:-1]), 0.5 * (z[1:] + z[:-1])
    psi = np.arctan2(dz, dy)
    Eref = L["Em"]; t = L["t"]
    dA = t * ds                                     # área ponderada (E = Eref)
    # varilla: tangente a la cara cóncava (inferior) en el borde de ataque
    A_r = np.pi * d_rod**2 / 4; nr = ROD["E"] / Eref
    y_r, z_r = d_rod / 2, -d_rod / 2 - t / 2 + 0.0
    Astar = dA.sum() + nr * A_r
    yc = ((dA * ym).sum() + nr * A_r * y_r) / Astar
    zc = ((dA * zm).sum() + nr * A_r * z_r) / Astar
    Izz = (dA * (zm - zc)**2).sum() + nr * A_r * (z_r - zc)**2      # batimiento
    Iyy = (dA * (ym - yc)**2).sum() + nr * A_r * (y_r - yc)**2      # en el plano
    Iyz = (dA * (ym - yc) * (zm - zc)).sum() + nr * A_r * (y_r - yc) * (z_r - zc)
    I_rod = np.pi * d_rod**4 / 64
    EI_flap = Eref * Izz + (L["D11"] * np.cos(psi)**2 * ds).sum() + ROD["E"] * I_rod
    EI_lag = Eref * Iyy + (L["D11"] * np.sin(psi)**2 * ds).sum() + ROD["E"] * I_rod
    EI_yz = Eref * Iyz
    GJ_plate = (4 * L["D66"] * ds).sum()
    GJ_rod = ROD["G"] * np.pi * d_rod**4 / 32
    GJ = GJ_plate + GJ_rod
    # ---- flujo de corte (pared abierta, desde el borde libre del BF hacia el BA)
    Dl = Izz * Iyy - Iyz**2

    def shear_flow(Sy, Sz):
        # q acumulado desde el BF (s = 0 en el BF) para que la varilla quede al final
        q = np.zeros(n)
        acc = 0.0
        for i in range(n - 1, -1, -1):
            dQy = dA[i] * (ym[i] - yc); dQz = dA[i] * (zm[i] - zc)
            # q en el segmento (valor medio del acumulado)
            q_new = acc - ((Sy * Izz - Sz * Iyz) / Dl * dQy + (Sz * Iyy - Sy * Iyz) / Dl * dQz)
            q[i] = 0.5 * (acc + q_new)
            acc = q_new
        return q          # positivo en el sentido BA -> BF (sentido de la discretización)

    def resultant(q):
        Fy = (q * dy).sum(); Fz = (q * dz).sum()
        Mx = (q * (ym * dz - zm * dy)).sum()        # momento respecto del origen
        return Fy, Fz, Mx

    qz = shear_flow(0.0, 1.0); Fy, Fz, Mx = resultant(qz)
    qz /= Fz; Mx /= Fz
    y_sc = Mx                                        # Fz=1 en y_sc: Mx = y_sc*1
    qy = shear_flow(1.0, 0.0); Fy2, Fz2, Mx2 = resultant(qy)
    qy /= Fy2; Mx2 /= Fy2
    z_sc = -Mx2                                      # Fy=1 en z_sc: Mx = -z_sc*1
    # ---- coordenada sectorial respecto del centro de corte y constante de alabeo
    w = np.zeros(n + 1)
    for i in range(n):
        ry, rz = ym[i] - y_sc, zm[i] - z_sc
        w[i + 1] = w[i] + (ry * dz[i] - rz * dy[i])
    wm = 0.5 * (w[1:] + w[:-1])
    w_mean = ((dA * wm).sum() + nr * A_r * w[0]) / Astar
    Gam = (dA * (wm - w_mean)**2).sum() + nr * A_r * (w[0] - w_mean)**2
    EGam = Eref * Gam
    # ---- masa
    rho_l = L["areal"] / t
    dm = rho_l * t * ds; m_r = ROD["rho"] * A_r
    mp = dm.sum() + m_r
    yg = ((dm * ym).sum() + m_r * y_r) / mp
    zg = ((dm * zm).sum() + m_r * z_r) / mp
    Jy = (dm * (ym - yg)**2).sum() + m_r * (y_r - yg)**2       # dispersión en cuerda
    Jz = (dm * (zm - zg)**2).sum() + m_r * (z_r - zg)**2
    Ith_sc = (dm * ((ym - y_sc)**2 + (zm - z_sc)**2)).sum() + m_r * ((y_r - y_sc)**2 + (z_r - z_sc)**2)
    kA2 = (Izz + Iyy) / Astar + (y_sc - yc)**2 + (z_sc - zc)**2   # radio polar (trapecio)
    # pliegue tipo cinta métrica (Seffen y Pellegrino): M = (1 +- nu) D alpha
    alpha_sub = 2 * a_half
    # laminado ortótropo: M = (D11 +- D12) alpha con los términos de D sin invertir
    M_opp = (L["D"][0, 0] + L["D"][0, 1]) * alpha_sub
    M_eq = (L["D"][0, 0] - L["D"][0, 1]) * alpha_sub
    zmax_c = max(abs(z.max() + t / 2 - zc), abs(z.min() - t / 2 - zc), abs(z_r - zc) if d_rod else 0)
    return dict(lam=lam, d_rod=d_rod, t=t, Em=L["Em"], Gm=L["Gm"], Eb=L["Eb"], Gb=L["Gb"],
                D11=L["D11"], D66=L["D66"], nu=L["nu"], areal=L["areal"],
                S=ds.sum(), sag=sag, a_half=a_half, yc=yc, zc=zc, EA=Eref * Astar,
                EI_flap=EI_flap, EI_lag=EI_lag, EI_yz=EI_yz, GJ=GJ, GJ_plate=GJ_plate,
                GJ_rod=GJ_rod, y_sc=y_sc, z_sc=z_sc, EGam=EGam, m=mp, yg=yg, zg=zg,
                Jy=Jy, Jz=Jz, Ith=Ith_sc, kA2=kA2, M_opp=M_opp, M_eq=M_eq,
                zmax=zmax_c, Izz=Izz, Astar=Astar)


CONFIGS = {"A": ("A", 0.0), "B": ("B", 0.0), "BV": ("B", 2.0e-3)}


def get(cfg):
    lam, d = CONFIGS[cfg]
    return seccion(lam, d)


if __name__ == "__main__":
    np.set_printoptions(precision=4)
    for lam in LAMINADOS:
        L = clt(LAMINADOS[lam])
        print(f"Laminado {lam}: t={L['t']*1e3:.2f} mm  Em={L['Em']/1e9:.1f} GPa  Gm={L['Gm']/1e9:.1f} GPa"
              f"  Eb={L['Eb']/1e9:.1f} GPa  Gb={L['Gb']/1e9:.1f} GPa  D11={L['D11']:.3f} N m"
              f"  D66={L['D66']:.4f} N m  nu={L['nu']:.3f}  masa={L['areal']*1e3:.0f} g/m2")
    rows = []
    variantes = [("A", 0.0), ("B", 0.0), ("A", 2e-3), ("B", 1.5e-3), ("B", 2e-3)]
    for lam, d in variantes:
        s = seccion(lam, d)
        rows.append(s)
        print(f"\n--- laminado {lam}, varilla {d*1e3:.1f} mm ---")
        print(f" arco S={s['S']*1e3:.2f} mm, flecha={s['sag']*1e3:.2f} mm, semiángulo={np.degrees(s['a_half']):.2f} deg")
        print(f" centroide y={s['yc']*1e3:.2f} z={s['zc']*1e3:.2f} mm ; c. corte y={s['y_sc']*1e3:.2f} z={s['z_sc']*1e3:.2f} mm ;"
              f" c. masa y={s['yg']*1e3:.2f} z={s['zg']*1e3:.2f} mm")
        print(f" EI_bat={s['EI_flap']:.3f}  EI_plano={s['EI_lag']:.1f}  EI_yz={s['EI_yz']:.3f} N m2;"
              f" GJ={s['GJ']*1e3:.2f} (placa {s['GJ_plate']*1e3:.2f}, varilla {s['GJ_rod']*1e3:.2f}) e-3 N m2;"
              f" EGam={s['EGam']:.3e} N m4")
        print(f" m'={s['m']*1e3:.2f} g/m ; I_theta={s['Ith']:.3e} kg m ; Jy={s['Jy']:.3e} Jz={s['Jz']:.3e} ; kA2={s['kA2']:.3e} m2")
        print(f" pliegue cinta: M_opuesto={s['M_opp']:.3f}  M_igual={s['M_eq']:.3f} N m ; z_max={s['zmax']*1e3:.2f} mm")
        print(f" placa plana equivalente EI={s['Em']*C*s['t']**3/12:.4f} N m2 ; relación {s['EI_flap']/(s['Em']*C*s['t']**3/12):.1f}")
        kGJ = np.sqrt(s['GJ'] / s['EGam']) if s['EGam'] > 0 else np.inf
        print(f" parámetro de alabeo k L = {kGJ*0.136:.2f} (L=0,136 m)")
    with open(os.path.join(DATA, "estructura_seccion.dat"), "w") as f:
        f.write("cfg drod_mm EIflap EIlag GJ EGam m_gpm yc_c zc_mm ysc_c zsc_mm yg_c Ith Mopp Meq\n")
        for s in rows:
            f.write(f"{s['lam']} {s['d_rod']*1e3:.1f} {s['EI_flap']:.4f} {s['EI_lag']:.2f} {s['GJ']:.5e} "
                    f"{s['EGam']:.4e} {s['m']*1e3:.3f} {s['yc']/C:.4f} {s['zc']*1e3:.3f} {s['y_sc']/C:.4f} "
                    f"{s['z_sc']*1e3:.3f} {s['yg']/C:.4f} {s['Ith']:.4e} {s['M_opp']:.4f} {s['M_eq']:.4f}\n")
