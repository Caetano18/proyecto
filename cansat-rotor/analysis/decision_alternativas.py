#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo cuantitativo de las siete alternativas para la segunda etapa de descenso.

(a) paracaídas, (b) parapente pequeño, (c) autogiro de 4 palas (diseño base),
(d) monocóptero tipo sámara, (e) dos rotores coaxiales contrarrotantes,
(f) aletas rígidas desplegables, (g) cuerpo inflable con gas almacenado.

Para cada una se calcula, dentro de la envolvente del CanSat (Ø 95 x 250 mm,
elementos rígidos desplegados con radio <= 0,20 m como el rotor):
  - la velocidad de descenso estacionaria nominal y su distribución
    (Monte Carlo sobre coeficientes, densidad, masa y aporte del drogue),
  - P(2 <= V <= 8 m/s), es decir, probabilidad de cumplir C4 si el sistema
    funciona,
  - masa y volumen interno del subsistema de etapa 2, piezas móviles,
  - deriva horizontal y movimiento angular del cuerpo (para el video).

Todos los coeficientes son ESTIMACIONES de bibliografía o de ingeniería;
ninguno viene de ensayos propios (no se hicieron).

Salida: analysis/data/decision_*.dat y un resumen por pantalla.
"""
import os
import numpy as np

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
rng = np.random.default_rng(20261005)
N = 200_000

# --------------------------------------------------------------------------
# Datos comunes (fuente única del informe)
# --------------------------------------------------------------------------
G = 9.80665
M = 0.500
W = M * G                      # 4,905 N
RHO = 1.225
NU = 1.5e-5
A_DRO = np.pi * 0.125**2       # drogue Ø 0,25 m
CD_DRO = 0.8
A_CUE = np.pi * 0.0475**2      # cuerpo Ø 95 mm
CD_CUE = 0.8
K_DRO = CD_DRO * A_DRO         # m2
K_CUE = CD_CUE * A_CUE
R_MAX = 0.200                  # radio máximo de elementos rígidos
A_R = np.pi * R_MAX**2
V_OBJ = 5.0
V_MIN, V_MAX = 2.0, 8.0
H_LIB = 0.8 * 700.0            # liberación al 80 % de un apogeo de 700 m


def v_desc(cda_total, w=W, rho=RHO):
    """Velocidad terminal para un C_D A total [m2]."""
    return np.sqrt(2.0 * w / (rho * cda_total))


# CdA total necesaria para 5 m/s
CDA_5 = 2 * W / (RHO * V_OBJ**2)
CDA_DISP = CDA_5 - K_DRO - K_CUE    # lo que debe aportar el sistema de etapa 2


def comunes(n):
    """Variables comunes: masa, densidad, Cd del drogue y fracción de su aporte."""
    m = rng.uniform(0.490, 0.510, n)
    rho = rng.uniform(1.10, 1.25, n)       # 0-700 m, 5-30 °C
    cdd = rng.uniform(0.75, 0.85, n)
    f = rng.uniform(0.0, 1.0, n)           # drogue en la estela: 0 = sin aporte
    return m * G, rho, cdd * A_DRO * f + K_CUE


# ----------------------------- (a) paracaídas -----------------------------
CD0_PAR = 0.775                          # plano circular/hexagonal, Knacke 0,75-0,80
S0_PAR = CDA_DISP / CD0_PAR
D0_PAR = np.sqrt(4 * S0_PAR / np.pi)
GRAM_TELA = 40.0                         # g/m2, ripstop de nailon ~1,1 oz/yd2


def mc_par(n):
    w, rho, k = comunes(n)
    cd0 = rng.uniform(0.70, 0.85, n)     # incluye efecto de escala y porosidad
    return v_desc(cd0 * S0_PAR + k, w, rho)


m_par = 1.3 * S0_PAR * GRAM_TELA + 8 * 1.0 * D0_PAR * 0.6 + 4 + 16 + 8
# tela con costuras +30 %, 8 líneas de ~1 D0 a 0,6 g/m, destorcedor 4 g,
# traba (servo + puerta) 16 g, alojamiento 8 g
vol_par = (1.3 * S0_PAR * GRAM_TELA + 8 * D0_PAR * 0.6) / 0.35 + 30   # cm3


# ----------------------------- (b) parapente ------------------------------
CL_PP, CD_PP = 0.65, 0.20          # ala ram-air chica de baja relación de aspecto, con líneas


def parapente(S, cl, cd, k, w=W, rho=RHO):
    """Planeo estacionario con drogue y cuerpo arrastrados por la misma línea.
    Devuelve (V total, V vertical, V horizontal)."""
    L = cl * S
    D = cd * S + k
    cr = np.sqrt(L**2 + D**2)
    V = np.sqrt(2 * w / (rho * cr))
    vz = V * D / cr
    vx = V * L / cr
    return V, vz, vx


def tam_pp(vz_obj=V_OBJ):
    lo, hi = 1e-3, 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        _, vz, _ = parapente(mid, CL_PP, CD_PP, K_DRO + K_CUE)
        if vz > vz_obj:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


S_PP = tam_pp()
_, VZ_PP, VX_PP = parapente(S_PP, CL_PP, CD_PP, K_DRO + K_CUE)
_, _, VX_PP_SIN = parapente(S_PP, CL_PP, CD_PP, K_CUE)
# Sin drogue, ¿qué área daría 5 m/s?
def tam_pp_sin():
    lo, hi = 1e-3, 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        _, vz, _ = parapente(mid, CL_PP, CD_PP, K_CUE)
        if vz > V_OBJ:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


S_PP_SIN = tam_pp_sin()
_, _, VX_PP_SIN5 = parapente(S_PP_SIN, CL_PP, CD_PP, K_CUE)


def mc_pp(n):
    w, rho, k = comunes(n)
    cl = rng.uniform(0.50, 0.80, n)
    cd = rng.uniform(0.15, 0.25, n)
    _, vz, _ = parapente(S_PP, cl, cd, k, w, rho)
    return vz


m_pp = 2.6 * S_PP * GRAM_TELA + 16 * 0.5 * 0.6 + 4 + 16 + 8
vol_pp = (2.6 * S_PP * GRAM_TELA + 16 * 0.5 * 0.6) / 0.30 + 30


# ----------------------------- (c) autogiro -------------------------------
def mc_rot(n, cr_lo=1.0, cr_hi=1.3, area=A_R):
    w, rho, k = comunes(n)
    cr = rng.uniform(cr_lo, cr_hi, n)
    return v_desc(cr * area + k, w, rho)


V_ROT = v_desc(1.2 * A_R + K_DRO + K_CUE)
m_rot = 30 + 24 + 16                    # palas, cubo y eje, traba (tab:masa)
vol_rot = 40.0


# ----------------------------- (d) monocóptero ----------------------------
# Una pala de cuerda 80 mm; gira todo el CanSat. C_R algo menor por la baja
# solidez y porque el centro de giro no coincide con el eje del cuerpo.
def mc_mono(n):
    return mc_rot(n, 0.7, 1.1)


V_MONO = v_desc(0.9 * A_R + K_DRO + K_CUE)
m_mono = 0.15 * 0.08 * 0.0005 * 1600 * 1e3 + 8 + 8 + 16
vol_mono = 30.0
# rotación del cuerpo: relación de velocidad de punta lambda = Omega R / V ~ 2-4
F_MONO = (np.array([2.0, 4.0]) * V_MONO / R_MAX) / (2 * np.pi)


# ----------------------------- (e) coaxial --------------------------------
def mc_coax(n):
    return mc_rot(n, 1.0, 1.35)         # mismo tubo de corriente; algo más de solidez


V_COAX = v_desc(1.25 * A_R + K_DRO + K_CUE)
m_coax = 2 * (30 + 24) + 16 + 10
vol_coax = 70.0


# ----------------------------- (f) aletas ---------------------------------
L_AL = R_MAX - 0.0475                   # 152,5 mm de largo radial
C_AL = 0.065                            # ancho que cabe plegado (4 x 65 mm < 276 mm)
N_AL = 4
CD_AL = 1.15                            # placa normal con interferencia del cuerpo


def mc_al(n):
    w, rho, k = comunes(n)
    cd = rng.uniform(1.0, 1.3, n)
    return v_desc(cd * N_AL * L_AL * C_AL + k, w, rho)


V_AL = v_desc(CD_AL * N_AL * L_AL * C_AL + K_DRO + K_CUE)
m_al = N_AL * L_AL * C_AL * 0.0005 * 1600 * 1e3 + 12 + 16
vol_al = 10.0
# Largo de aleta necesario para 5 m/s (con ancho 65 mm, 4 aletas)
L_AL_5 = CDA_DISP / (CD_AL * N_AL * C_AL)


# ----------------------------- (g) inflable -------------------------------
CD_ESF = 0.47
A_ESF5 = CDA_DISP / CD_ESF
D_ESF5 = np.sqrt(4 * A_ESF5 / np.pi)
VOL_ESF5 = np.pi * D_ESF5**3 / 6
RHO_CO2 = 1.87                          # kg/m3 a 1 atm y 15 °C
M_CO2_5 = VOL_ESF5 * RHO_CO2
# Lo que cabe: un cartucho de 16 g de CO2
VOL_16 = 0.016 / RHO_CO2 * 1.0          # m3 a 1 atm (sobrepresión despreciable)
D_ESF16 = (6 * VOL_16 / np.pi)**(1 / 3)
V_ESF16 = v_desc(CD_ESF * np.pi * D_ESF16**2 / 4 + K_DRO + K_CUE)
RE_ESF16 = V_ESF16 * D_ESF16 / NU
RE_ESF5 = V_OBJ * D_ESF5 / NU


def mc_inf(n):
    w, rho, k = comunes(n)
    cd = rng.uniform(0.40, 0.50, n)
    vol = VOL_16 * rng.uniform(0.85, 1.0, n)   # pérdidas y temperatura del gas
    d = (6 * vol / np.pi)**(1 / 3)
    return v_desc(cd * np.pi * d**2 / 4 + k, w, rho)


m_inf = 55 + np.pi * D_ESF16**2 * 60 + 15 + 16
vol_inf = 60.0

# --------------------------------------------------------------------------
ALT = ["a", "b", "c", "d", "e", "f", "g"]
NOM = ["Paracaidas", "Parapente", "Autogiro", "Monocoptero", "Coaxial",
       "Aletas", "Inflable"]
MCF = [mc_par, mc_pp, mc_rot, mc_mono, mc_coax, mc_al, mc_inf]
MASA = [m_par, m_pp, m_rot, m_mono, m_coax, m_al, m_inf]
VOL = [vol_par, vol_pp, vol_rot, vol_mono, vol_coax, vol_al, vol_inf]
PIEZAS = [2, 2, 7, 4, 12, 5, 3]          # piezas móviles del subsistema
# Movimiento angular del cuerpo para el video, °/s (estimación, ver capítulo)
ANG = [60, 20, 25, 4000, 10, 30, 40]
DERIVA = [0.0, VX_PP, 0.0, 0.0, 0.0, 0.0, 0.0]  # velocidad horizontal propia


def resumen():
    out = {}
    for a, f in zip(ALT, MCF):
        v = f(N)
        out[a] = dict(
            vmed=np.median(v), p5=np.percentile(v, 5), p95=np.percentile(v, 95),
            pin=np.mean((v >= V_MIN) & (v <= V_MAX)), err=np.mean(np.abs(v - V_OBJ)),
            v=v)
    return out


def curvas_tamano():
    """V de descenso frente al tamaño radial desplegado (drogue al 100 %)."""
    r = np.linspace(0.05, 0.45, 81)
    k = K_DRO + K_CUE
    v_par = v_desc(CD0_PAR * np.pi * r**2 + k)            # r = radio nominal del paracaídas
    v_rot = v_desc(1.2 * np.pi * r**2 + k)
    v_mono = v_desc(0.9 * np.pi * r**2 + k)
    v_al = v_desc(CD_AL * N_AL * np.clip(r - 0.0475, 0, None) * C_AL + k)
    v_esf = v_desc(CD_ESF * np.pi * r**2 + k)
    with open(os.path.join(DATA, "decision_tamano.dat"), "w") as fh:
        fh.write("r Vpar Vrot Vmono Val Vesf\n")
        for i in range(len(r)):
            fh.write(f"{r[i]:.4f} {v_par[i]:.4f} {v_rot[i]:.4f} {v_mono[i]:.4f} "
                     f"{v_al[i]:.4f} {v_esf[i]:.4f}\n")


def histogramas(res):
    bins = np.linspace(2.0, 14.0, 97)
    centros = 0.5 * (bins[1:] + bins[:-1])
    with open(os.path.join(DATA, "decision_vhist.dat"), "w") as fh:
        fh.write("V " + " ".join(ALT) + "\n")
        hs = [np.histogram(res[a]["v"], bins=bins, density=True)[0] for a in ALT]
        for i, c in enumerate(centros):
            fh.write(f"{c:.4f} " + " ".join(f"{h[i]:.5f}" for h in hs) + "\n")


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    res = resumen()
    curvas_tamano()
    histogramas(res)
    with open(os.path.join(DATA, "decision_alternativas.dat"), "w") as fh:
        fh.write("idx alt Vmed Vp5 Vp95 errlo errhi Pin Err masa vol piezas ang\n")
        for i, a in enumerate(ALT):
            r = res[a]
            fh.write(f"{i} {a} {r['vmed']:.3f} {r['p5']:.3f} {r['p95']:.3f} "
                     f"{r['vmed']-r['p5']:.3f} {r['p95']-r['vmed']:.3f} "
                     f"{r['pin']:.4f} {r['err']:.3f} {MASA[i]:.1f} {VOL[i]:.0f} "
                     f"{PIEZAS[i]} {ANG[i]}\n")
    print(f"CdA para 5 m/s = {CDA_5:.4f} m2; a aportar por etapa 2 = {CDA_DISP:.4f} m2")
    print(f"(a) S0 = {S0_PAR:.4f} m2, D0 = {D0_PAR:.3f} m, masa = {m_par:.1f} g, vol = {vol_par:.0f} cm3")
    print(f"(b) S = {S_PP:.4f} m2, vz = {VZ_PP:.2f}, vx = {VX_PP:.2f} m/s, deriva en {H_LIB:.0f} m = "
          f"{VX_PP*H_LIB/VZ_PP:.0f} m, L/D efectivo = {VX_PP/VZ_PP:.2f}")
    print(f"    sin drogue: S = {S_PP_SIN:.4f} m2, vx = {VX_PP_SIN5:.2f} m/s, deriva = {VX_PP_SIN5*H_LIB/5:.0f} m")
    print(f"    masa = {m_pp:.1f} g, vol = {vol_pp:.0f} cm3")
    print(f"(c) V = {V_ROT:.3f} m/s, masa = {m_rot} g")
    print(f"(d) V = {V_MONO:.3f} m/s, masa = {m_mono:.1f} g, giro del cuerpo {F_MONO[0]:.1f}-{F_MONO[1]:.1f} Hz")
    print(f"(e) V = {V_COAX:.3f} m/s, masa = {m_coax} g")
    print(f"(f) L = {L_AL*1e3:.1f} mm, CdA = {CD_AL*N_AL*L_AL*C_AL:.4f}, V = {V_AL:.3f} m/s, masa = {m_al:.1f} g,"
          f" L para 5 m/s = {L_AL_5*1e3:.0f} mm")
    print(f"(g) esfera 5 m/s: D = {D_ESF5:.3f} m, vol = {VOL_ESF5*1e3:.0f} L, CO2 = {M_CO2_5*1e3:.0f} g, Re = {RE_ESF5:.2e}")
    print(f"    cartucho 16 g: vol = {VOL_16*1e3:.2f} L, D = {D_ESF16:.3f} m, V = {V_ESF16:.2f} m/s, Re = {RE_ESF16:.2e}, masa = {m_inf:.0f} g")
    print("alt  Vmed   p5    p95   Pin    E|V-5|  masa  vol  piezas")
    for i, a in enumerate(ALT):
        r = res[a]
        print(f" {a}  {r['vmed']:5.2f} {r['p5']:5.2f} {r['p95']:5.2f} {r['pin']:.3f} {r['err']:6.2f} "
              f"{MASA[i]:6.1f} {VOL[i]:4.0f} {PIEZAS[i]:3d}")
