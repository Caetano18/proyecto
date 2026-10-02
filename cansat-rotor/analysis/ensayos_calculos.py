#!/usr/bin/env python3
"""Cálculos del plan de verificación experimental (capítulo 18, prefijo ensayos).

Genera los datos de los gráficos en analysis/data/ensayos_*.dat e imprime los
números que usan las tablas del capítulo. Solo numpy y scipy.

Uso:  python3 analysis/ensayos_calculos.py
"""
import os
import numpy as np
from scipy.integrate import solve_ivp
from scipy import stats

AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(AQUI, "data")
os.makedirs(DATA, exist_ok=True)

# ---------------------------------------------------------------- datos base
rho, g = 1.225, 9.80665
m = 0.500
W = m * 9.81                      # 4,905 N como en el informe base
R, e, B, c = 0.200, 0.044, 4, 0.045
A_R = np.pi * R**2
A_d, Cd_d = np.pi * 0.25**2 / 4, 0.8
A_c, Cd_c = np.pi * 0.095**2 / 4, 0.8
k_d = 0.5 * rho * Cd_d * A_d
k_c = 0.5 * rho * Cd_c * A_c
C_R = 1.2
I_p = 5.1e-4                      # inercia polar del rotor [kg m2]
L_pala = R - e


def titulo(t):
    print("\n== " + t + " ==")


def linea(nombre, valor, unidad=""):
    print(f"{nombre:<58s} = {valor:10.4g} {unidad}")


def guardar(nombre, cab, cols):
    ruta = os.path.join(DATA, nombre)
    arr = np.column_stack(cols)
    np.savetxt(ruta, arr, fmt="%.5g", header=" ".join(cab), comments="")
    print(f"  -> {os.path.relpath(ruta, os.path.dirname(AQUI))}")


V1 = np.sqrt(W / (k_d + k_c))
V2 = np.sqrt(W / (0.5 * rho * C_R * A_R + k_d + k_c))
V2_sd = np.sqrt(W / (0.5 * rho * C_R * A_R + k_c))
T2 = W - (k_d + k_c) * V2**2
titulo("Puntos de operación")
linea("V1 (drogue + cuerpo)", V1, "m/s")
linea("V2 con drogue (C_R=1,2)", V2, "m/s")
linea("V2 sin drogue (C_R=1,2)", V2_sd, "m/s")
linea("empuje del rotor T en V2", T2, "N")
linea("empuje del rotor a 13,4 m/s si girara en equilibrio", 0.5*rho*C_R*A_R*V1**2, "N")

# ------------------------------------------------- 1. banco: chorro y ventilador
titulo("Banco vertical: chorro, bloqueo y potencia")
eta = 0.35   # eficiencia global ventilador+motor (estimación)
V = np.linspace(4, 15, 23)
q = 0.5 * rho * V**2
cols, cab = [V, q], ["V", "q"]
for Dj in (0.6, 0.8, 1.0):
    Aj = np.pi * Dj**2 / 4
    P = 0.5 * rho * Aj * V**3 / eta / 1000.0
    cols.append(P); cab.append(f"P{int(Dj*100):03d}")
    linea(f"Dj={Dj:.1f} m: A_R/A_j", A_R / Aj)
    for Vx in (6.4, 7.8, 13.4):
        linea(f"   P eléctrica a {Vx} m/s (eta={eta})", 0.5*rho*Aj*Vx**3/eta, "W")

# Maskell (cámara cerrada), theta = 2,5, C_R = 1,2, S = A_R
titulo("Corrección de Maskell en cámara cerrada (q_c/q = 1 + 2,5 C_R S/C)")
for lado in (1.0, 1.2, 1.5, 2.0):
    C = lado**2
    linea(f"sección {lado:.1f} x {lado:.1f} m: S/C", A_R / C)
    linea(f"   q_c/q", 1 + 2.5 * C_R * A_R / C)

# Pitot
titulo("Pitot y sensor diferencial SDP810-125Pa")
for Vx in (6.0, 6.4, 8.0, 14.0):
    qq = 0.5 * rho * Vx**2
    linea(f"q a {Vx} m/s", qq, "Pa")
    linea(f"   error de cero 0,08 Pa relativo a q", 0.08 / qq * 100, "%")
linea("V máxima con fondo de escala 125 Pa", np.sqrt(2 * 125 / rho), "m/s")
for d in (0.003, 0.006):
    linea(f"Re de la sonda d={d*1000:.0f} mm a 6 m/s", 6 * d / 1.5e-5)

# Conicidad por video
titulo("Conicidad por video")
beta0 = np.radians(4.4)
linea("altura de la punta sobre la bisagra (beta0=4,4)", L_pala*np.sin(beta0)*1000, "mm")
for px_mm in (0.25, 0.5):
    u_z = 2 * px_mm / np.sqrt(3)        # +-2 px rectangular
    linea(f"u(beta) con {px_mm} mm/px y +-2 px", np.degrees(u_z / 1000 / L_pala), "deg")
linea("desplazamiento angular en 1/2000 s a 120 rad/s", np.degrees(120 / 2000), "deg")

# Inercia por péndulo trifilar
titulo("Péndulo trifilar para I_p")
r_hilo, Lh, m_pl = 0.10, 0.80, 0.10
# período para rotor (80 g aprox.) sobre plato de 100 g, hilos a r=0,10 m, L=0,8 m
m_rot = 0.080
I_pl = 0.5 * m_pl * 0.12**2
Tper = 2*np.pi*np.sqrt((I_p + I_pl) * Lh / ((m_rot + m_pl) * g * r_hilo**2))
linea("período del trifilar con rotor", Tper, "s")
# Par por aceleración
titulo("Par por aceleración angular")
linea("Q para dOmega/dt = 10 rad/s2", I_p * 10, "N m")

# ------------------------------------------------- 2. caída desde drone (ODE)
titulo("Caída desde drone: modelo de orden reducido")
Cd0 = 0.06                     # resistencia de perfil a C_l de trabajo (L/D ~ 15)
lam_d = 120.1 * R / V2          # relación de velocidad de punta de diseño
Om_d = 120.1
Q_p = B * 0.5 * rho * c * Cd0 * Om_d**2 * (R**4 - e**4) / 4
Q0_ref = 0.026                 # par de arranque a 13,4 m/s, paso -2 grados
Q0_V2 = Q0_ref * (V2 / 13.4)**2
kQ = 1.5
a_nom = kQ * Q_p / Q0_V2 - 1
C_s = 1.2 * B * c * L_pala / A_R   # palas abiertas y quietas
Q_f = 3e-4                     # rozamiento de rodamientos y destorcedor (estimación)
linea("lambda de diseño Omega R / V2", lam_d)
linea("par de perfil en equilibrio Q_p (Cd0=0,06)", Q_p, "N m")
linea("Q0 a V2", Q0_V2, "N m")
linea("parámetro a del modelo nominal", a_nom)
linea("x del par máximo (nominal)", (a_nom - 1) / (2 * a_nom))
linea("C_s (palas quietas, ref. A_R)", C_s)


def simular(a, con_drogue=True, t_lib=None, h_max=400.0):
    """t_lib: tiempo de liberación del rotor (None = libre desde el inicio)."""
    kd = k_d if con_drogue else 0.0

    def rhs(t, y):
        h, Vv, Om = y
        Vp = max(Vv, 0.05)
        fd = min(t / 0.5, 1.0) if con_drogue else 0.0   # inflado en 0,5 s
        libre = (t_lib is None) or (t >= t_lib)
        if libre:
            T = 0.5*rho*A_R*(C_s*Vv*abs(Vv) + (C_R - C_s)*(Om*R/lam_d)**2)
            Om_eq = lam_d * Vp / R
            x = Om / Om_eq
            Q = Q0_ref*(Vp/13.4)**2*(1 - x)*(1 + a*x) - Q_f*np.tanh(Om/2)
            dOm = Q / I_p if (Om > 0 or Q > 0) else 0.0
        else:
            T, dOm = 0.0, 0.0
        dV = (W - (fd*kd + k_c)*Vv*abs(Vv) - T) / m
        return [Vv, dV, dOm]

    ev = lambda t, y: y[0] - h_max
    ev.terminal = True
    sol = solve_ivp(rhs, (0, 120), [0, 0, 0], max_step=0.01, events=ev,
                    rtol=1e-7, atol=1e-9)
    return sol


casos = {}
for nombre, a, drg, tl in [("A_nom", a_nom, True, 2.5), ("A_cons", 0.0, True, 2.5),
                           ("B_nom", a_nom, True, None), ("B_cons", 0.0, True, None),
                           ("C_nom", a_nom, False, None), ("C_cons", 0.0, False, None)]:
    s = simular(a, drg, tl)
    casos[nombre] = s
    Vt = s.y[1]
    Vss = Vt[-1]          # asíntota propia del modelo (incluye el rozamiento)
    linea(f"caso {nombre}: V estacionaria del modelo", Vss, "m/s")
    fuera = np.where(np.abs(Vt - Vss) / Vss > 0.02)[0]
    i_ss = fuera[-1] + 1 if len(fuera) else 0
    if i_ss >= len(s.t):
        linea(f"caso {nombre}: no llega al 2 % antes de", s.y[0][-1], "m")
        continue
    t_ss, h_ss = s.t[i_ss], s.y[0][i_ss]
    h_req = h_ss + 5 * Vss + 10
    linea(f"caso {nombre}: t al 2 % de V_ss", t_ss, "s")
    linea(f"   altura caída al 2 %", h_ss, "m")
    linea(f"   altura necesaria (+5 s de ventana +10 m)", h_req, "m")
    linea(f"   V mínima del transitorio", Vt[s.t > 1].min(), "m/s")
    linea(f"   rpm máxima", s.y[2].max()*60/2/np.pi, "rpm")

# serie para el gráfico: V en función de la altura caída, muestreada cada 1 m
hh = np.arange(0, 151, 1.0)
cols, cab = [hh], ["h"]
for nombre in ("A_nom", "A_cons", "B_nom", "B_cons", "C_nom"):
    s = casos[nombre]
    cols.append(np.interp(hh, s.y[0], s.y[1], right=np.nan))
    cab.append("V" + nombre.replace("_", ""))
for nombre in ("A_nom", "B_nom"):
    s = casos[nombre]
    cols.append(np.interp(hh, s.y[0], s.y[2]*60/2/np.pi, right=np.nan))
    cab.append("rpm" + nombre.replace("_", ""))
guardar("ensayos_caida.dat", cab, cols)

# ------------------------------------------------- 3. estadística de repeticiones
titulo("Repeticiones necesarias")
n = np.arange(3, 31)
cols, cab = [n], ["n"]
for s_ in (0.2, 0.3, 0.4, 0.5):
    E = stats.t.ppf(0.975, n - 1) * s_ / np.sqrt(n)
    cols.append(E); cab.append(f"s{int(s_*10):02d}")
guardar("ensayos_ic.dat", cab, cols)


def n_para(E, s_, conf=0.95):
    for k in range(2, 500):
        if stats.t.ppf(1 - (1 - conf) / 2, k - 1) * s_ / np.sqrt(k) <= E:
            return k
    return None


for s_ in (0.2, 0.3, 0.4, 0.5):
    linea(f"s={s_}: n para +-0,25 m/s (95 %)", n_para(0.25, s_))
    linea(f"s={s_}: n para +-2,5 % de V2 (C_R +-5 %)", n_para(0.025 * V2, s_))
# cota superior unilateral con n=5, s=0,4
for nn in (3, 5, 10):
    linea(f"cota sup. 95 % unilateral, n={nn}, s=0,4", V2 + stats.t.ppf(0.95, nn-1)*0.4/np.sqrt(nn), "m/s")

# ------------------------------------------------- 4. barómetro
titulo("Barómetro")
for sh in (0.1, 0.3, 0.5):
    for fs, Tw in ((50, 5), (25, 5), (50, 3)):
        N = fs * Tw
        linea(f"sigma_V regresión: sigma_h={sh} m, {fs} Hz, {Tw} s", sh*np.sqrt(12/(N*(N**2-1)))*fs*np.sqrt(1), "m/s")
linea("dp/dh al nivel del mar", rho * g, "Pa/m")
linea("error de escala por 10 K de temperatura", 10 / 288.15 * 100, "%")
q1, q2 = 0.5*rho*V1**2, 0.5*rho*V2**2
linea("q en etapa 1", q1, "Pa"); linea("q en etapa 2", q2, "Pa")
for Cp in (0.3, 0.6):
    linea(f"salto aparente de altura al pasar de V1 a V2, Cp={Cp}", Cp*(q1-q2)/(rho*g), "m")
linea("deriva meteorológica 1 hPa/3 h en 20 s", 100/(3*3600)*20/(rho*g), "m")

# ------------------------------------------------- 5. presupuestos GUM
titulo("GUM: C_R en el banco (C_R = F_b T / (K q_ref A_R))")
T0, q0 = T2, 0.5 * rho * V2**2
CR0 = T0 / (q0 * A_R)
# (nombre, valor, u absoluta, coef. de sensibilidad relativo, gdl)
filas = [
    ("T: calibración celda", T0, 0.003*T0, 1, 50),
    ("T: ruido promediado", T0, 0.004, 1, 30),
    ("T: tara cubo y vástago", T0, 0.005, 1, 10),
    ("q: sensor calibrado", q0, 0.005*q0, -1, 50),
    ("q: cero", q0, 0.08/np.sqrt(3), -1, 1e6),
    ("q: fluctuación temporal", q0, 0.003*q0, -1, 30),
    ("K: no uniformidad", 1.0, 0.010, -1, 12),
    ("A_R: radio +-0,5 mm", A_R, 2*0.5e-3/np.sqrt(3)/R*A_R, -1, 1e6),
    ("F_b: bloqueo/chorro", 1.0, 0.03/np.sqrt(3), 1, 8),
    ("repetibilidad (5 corridas)", CR0, 0.01*CR0/np.sqrt(5), 1, 4),
]
suma, ws = 0, 0
for nom, val, u, cs, nu in filas:
    ur = abs(cs) * u / val
    suma += ur**2
    ws += ur**4 / nu
    print(f"  {nom:<32s} val={val:9.4g} u={u:9.3g}  u_rel*c={ur*100:6.3f} %  nu={nu:g}")
uc = np.sqrt(suma)
nu_eff = uc**4 / ws
k = stats.t.ppf(0.975, nu_eff)
linea("C_R nominal", CR0)
linea("u_c relativa", uc*100, "%")
linea("nu_eff", nu_eff)
linea("k (95 %)", k)
linea("U expandida absoluta", k*uc*CR0)

titulo("GUM: V2 en caída desde drone (con drogue)")
s_rep, n_rep = 0.35, 10
filasV = [
    ("tipo A: dispersión entre caídas", s_rep/np.sqrt(n_rep), n_rep-1),
    ("viento vertical medio de la campaña", 0.10, 8),
    ("escala barométrica (T local, +-1 K)", V2*1/288/np.sqrt(3)*np.sqrt(3), 1e6),
    ("ganancia del sensor de presión", V2*0.005/np.sqrt(3), 1e6),
    ("transitorio residual en la ventana", 0.03, 8),
    ("presión estática de la toma", 0.02, 8),
    ("normalización a densidad ISA", V2*0.5*0.003, 1e6),
    ("masa +-1 g", V2*0.5*0.001/np.sqrt(3), 1e6),
]
suma, ws = 0, 0
for nom, u, nu in filasV:
    suma += u**2; ws += u**4/nu
    print(f"  {nom:<40s} u={u:8.4f} m/s  nu={nu:g}")
ucV = np.sqrt(suma); nuV = ucV**4/ws; kV = stats.t.ppf(0.975, nuV)
linea("u_c(V2)", ucV, "m/s"); linea("nu_eff", nuV); linea("k", kV)
linea("U(V2) 95 %", kV*ucV, "m/s")

titulo("C_R deducido de caídas sin drogue")
uV = np.sqrt((0.35/np.sqrt(10))**2 + 0.10**2 + 0.03**2 + 0.02**2 + (V2_sd*0.005/np.sqrt(3))**2)
num = 2*W/(rho*V2_sd**2) - Cd_c*A_c
CRd = num / A_R
dCR_dV = -4*W/(rho*V2_sd**3)/A_R
u_cd = 0.15*A_c/A_R          # Cd del cuerpo con incertidumbre 0,15
u_rho = 2*W/(rho**2*V2_sd**2)*0.003*rho/A_R
uCR = np.sqrt((dCR_dV*uV)**2 + u_cd**2 + u_rho**2 + (CRd*2*0.29/200)**2)
linea("V2 sin drogue", V2_sd, "m/s"); linea("u(V)", uV, "m/s")
linea("C_R deducido", CRd); linea("u(C_R)", uCR); linea("u relativa", uCR/CRd*100, "%")

# ------------------------------------------------- 6. choque con cuerda
titulo("Choque por caída con cuerda (L = 0,61 m)")
L = 0.61
kk = np.logspace(np.log10(500), np.log10(5e5), 60)
mg = m * g
delta = (mg + np.sqrt(mg**2 + 2*kk*mg*L)) / kk
G = kk * delta / mg
tpulso = np.pi * np.sqrt(m / kk) * 1000
guardar("ensayos_choque.dat", ["k", "G", "tms"], [kk, G, tpulso])
k30 = ((30 - 1)**2 - 1) * mg / (2 * L)
linea("rigidez equivalente para 30 G", k30, "N/m")
linea("   EA equivalente de 0,61 m", k30 * L, "N")
linea("   duración del pulso", np.pi*np.sqrt(m/k30)*1000, "ms")
EA_kev = 70e9 * 3.5e-6
linea("cuerda de Kevlar 1/8 in: EA aprox.", EA_kev, "N")
kkv = EA_kev / L
dk = (mg + np.sqrt(mg**2 + 2*kkv*mg*L)) / kkv
linea("   G ideal con cuerda de Kevlar sola", kkv*dk/mg)
linea("velocidad al tensarse la cuerda", np.sqrt(2*g*L), "m/s")

# ------------------------------------------------- 7. vibración
titulo("Vibración 15 G")
for f in (20, 50, 100, 200, 500):
    linea(f"amplitud de desplazamiento a {f} Hz (15 g pico)", 15*g/(2*np.pi*f)**2*1000, "mm")
m_mov = 0.5 + 0.4 + 0.2
linea("fuerza pico (CanSat+fijación+armadura 1,1 kg)", m_mov*15*g, "N")
# frecuencia de la pala plegada
E_cf, rho_cf, t = 50e9, 1550, 0.5e-3
s_f = 0.0
Rc = 0.0819
s_f = Rc - np.sqrt(Rc**2 - c**2/4)
I_sec = c*t*4*s_f**2/45
mu = rho_cf*c*t*1.03
for nombre, cte in (("apoyada-apoyada", np.pi**2), ("voladizo", 1.875**2)):
    f1 = cte/(2*np.pi*L_pala**2)*np.sqrt(E_cf*I_sec/mu)
    linea(f"f1 pala plegada ({nombre})", f1, "Hz")
linea("flecha de la sección", s_f*1000, "mm")

# ------------------------------------------------- 8. radio
titulo("Enlace de radio")
for f_MHz in (915, 2440):
    for d_km in (1.0, 2.0, 3.0):
        fspl = 20*np.log10(d_km) + 20*np.log10(f_MHz) + 32.44
        linea(f"FSPL {f_MHz} MHz a {d_km} km", fspl, "dB")
lam = 3e8/915e6
linea("radio de la 1.a zona de Fresnel en el medio, 2 km, 915 MHz", np.sqrt(lam*2000/4), "m")
linea("atenuación equivalente de 200 m a 2 km", 20*np.log10(2000/200), "dB")

# ------------------------------------------------- 9. energía
titulo("Autonomía")
E_Wh = 3.0*3.6*0.85
for P in (2.5, 0.7):
    linea(f"autonomía a {P} W", E_Wh/P, "h")
