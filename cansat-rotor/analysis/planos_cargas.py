#!/usr/bin/env python3
"""Recorrido de cargas, secuencia de despliegue y holguras en el tubo del cohete.

Capítulo "Planos de conjunto avanzados" (prefijo planos).
Modelo cuasiestático de barra 1D a lo largo del eje z (0 = fondo, 250 = tope de la copa).
Salida: tablas en pantalla y archivos analysis/data/planos_*.dat
"""
import os
import numpy as np

g = 9.81
rho = 1.225
m_tot = 0.500
W = m_tot * g
here = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(here, "data")

# ---------------------------------------------------------------- masas (config. A, tab:masa)
# (nombre, masa [kg], z [mm]) ; el tubo (141 g) se reparte uniforme 0..205
items = [
    ("tapa inferior",            0.013,   1.5),
    ("camara nadir",             0.010,   9.0),
    ("baliza",                   0.008,   8.0),
    ("lastre",                   0.083,  25.0),
    ("traba (anillo+servo)",     0.016,  55.0),
    ("bateria+portapila",        0.055, 105.0),
    ("cables+tornillos",         0.025, 120.0),
    ("paneles solares",          0.008, 150.0),
    ("electronica",              0.047, 158.0),
    ("travesano",                0.006, 178.0),
    ("tapa superior",            0.006, 202.0),
    ("camara cenit",             0.010, 194.0),
    ("rotor (palas+cubo)",       0.054, 213.0),   # entra al cuerpo por bisagras/cubo/eje
    ("copa",                     0.006, 237.0),
    ("drogue+cuerda",            0.012, 240.0),   # vuela fuera del cuerpo en B, C
]
n_sl = 41
zt = np.linspace(0, 205, n_sl + 1)
tube = [("tubo", 0.141 / n_sl, 0.5 * (zt[i] + zt[i + 1])) for i in range(n_sl)]
ALL = items + tube
assert abs(sum(m for _, m, _ in ALL) - m_tot) < 1e-9

# ---------------------------------------------------------------- aerodinámica base
A_d = np.pi * 0.25**2 / 4
A_b = np.pi * 0.095**2 / 4
k_d = 0.5 * rho * 0.8 * A_d
k_b = 0.5 * rho * 0.8 * A_b
V1 = np.sqrt(W / (k_d + k_b))
V2 = 6.396
T2 = W - (k_d + k_b) * V2**2

m_dro = 0.012


def axial(z, forces, n_inert, excl=()):
    """Esfuerzo axial N(z) (tracción +) en el corte z.

    forces: lista (F [N] + hacia arriba, z [mm]); n_inert: factor (g+a)/g de todas las masas.
    excl: nombres de masas que no están en el cuerpo (vuelan aparte)."""
    N = 0.0
    for F, zf in forces:
        if zf > z:
            N += F
    for name, m, zi in ALL:
        if name in excl:
            continue
        if zi > z:
            N -= m * g * n_inert
    return N


def body_mass(excl=()):
    return sum(m for nm, m, _ in ALL if nm not in excl)


cases = {}
# A) ascenso / vibración de diseño, 15 G (S4); el cohete apoya el fondo (z=0)
cases["asc15"] = dict(forces=[], n=15.0, excl=())
# B) apertura del drogue a 35 m/s (F = 44,2 N); el drogue vuela aparte
F35 = 44.2
mb = body_mass(("drogue+cuerda",))
D_b35 = k_b * 35**2
nB = (F35 + D_b35) / (mb * g)
cases["dro35"] = dict(forces=[(F35, 178.0), (D_b35, 0.0)], n=nB, excl=("drogue+cuerda",))
# B') apertura de diseño 30 G (S5): 147 N en la cuerda
F30 = 147.2
nB2 = (F30) / (mb * g)
cases["dro30G"] = dict(forces=[(F30, 178.0)], n=nB2, excl=("drogue+cuerda",))
# C) etapa 2 estable: T en el cubo, drogue en la argolla, arrastre del cuerpo en el fondo
D_d2 = k_d * V2**2 - m_dro * g
D_b2 = k_b * V2**2
cases["eta2"] = dict(forces=[(T2, 213.0), (D_d2, 178.0), (D_b2, 0.0)], n=1.0,
                     excl=("drogue+cuerda",))
# C') etapa 1 estable (antes de liberar)
D_d1 = k_d * V1**2 - m_dro * g
D_b1 = k_b * V1**2
cases["eta1"] = dict(forces=[(D_d1, 178.0), (D_b1, 0.0)], n=1.0, excl=("drogue+cuerda",))
# D) aterrizaje con espuma: 200 g (cap. estructura)
cases["ater200"] = dict(forces=[], n=200.0, excl=("drogue+cuerda",))

zz = np.arange(0.0, 250.1, 1.0)
cols = {}
for key, c in cases.items():
    cols[key] = np.array([axial(z, c["forces"], c["n"], c["excl"]) for z in zz])
    # cierre del equilibrio: N(0-) debe igualar la reacción en el apoyo
with open(os.path.join(DATA, "planos_axial.dat"), "w") as f:
    f.write("z " + " ".join(cols.keys()) + "\n")
    for i, z in enumerate(zz):
        f.write(f"{z:.1f} " + " ".join(f"{cols[k][i]:.4f}" for k in cols) + "\n")

print("== Equilibrio etapa 1 y 2 ==")
print(f"V1 = {V1:.2f} m/s ; D_drogue(neto) = {D_d1:.3f} N ; D_cuerpo = {D_b1:.3f} N")
print(f"V2 = {V2:.2f} m/s ; T = {T2:.3f} N ; D_drogue(neto) = {D_d2:.3f} N ; D_cuerpo = {D_b2:.3f} N")
print(f"apertura 35 m/s: F = {F35} N, D_cuerpo = {D_b35:.2f} N, n = {nB:.2f}")
print(f"apertura 30 G: F = {F30} N, n = {nB2:.2f}")
for k in cols:
    v = cols[k]
    print(f"{k:8s} N(0+) = {v[1]:8.2f}  N(100) = {v[100]:8.2f}  N(190) = {v[190]:8.2f}  "
          f"N(205) = {v[205]:8.2f}  max = {v.max():8.2f}  min = {v.min():8.2f}")

# ---------------------------------------------------------------- cargas por interfaz
mpala = 0.0074
Om = 120.1
rcg = 0.044 + 0.156 * 0.5  # centro de la pala (mismo supuesto que calculos.py)
Fc = mpala * Om**2 * rcg
m_rot = 0.054
m_head = m_rot + 0.006  # rotor + copa (sobre el eje)
m_bat = 0.055
m_las = 0.083
print("\n== Cargas por interfaz [N] ==")
rows = []
def row(name, *vals):
    rows.append((name,) + vals)
    print(f"{name:36s} " + " ".join(f"{v:8.2f}" for v in vals))
print(f"{'':36s} {'asc15':>8s} {'dro35':>8s} {'dro30G':>8s} {'eta2':>8s} {'ater200':>8s}")
m_trav = 0.006
row("I1 cuerda-argolla", 0.0, F35, F30, D_d2, 0.0)
row("I2 travesano-pared", (m_head + m_dro + m_trav) * g * 15,
    F35 - (m_head + m_trav) * g * nB, F30 - (m_head + m_trav) * g * nB2,
    D_d2 + T2 - (m_head + m_trav) * g, (m_head + m_trav) * g * 200)
# I3: carga a lo largo de la pala. Plegada (15 G, apertura) la inercia va según la
# envergadura; desplegada (etapa 2, aterrizaje) la carga axial es la centrífuga y la
# inercia del aterrizaje es TRANSVERSAL a la pala (batimiento), no axial.
row("I3 pasador, axial por pala", mpala * g * 15, mpala * g * nB, mpala * g * nB2, Fc, Fc)
row("I3' pasador, transversal por pala", 0.0, 0.0, 0.0, T2 / 4, mpala * g * 200)
row("I4 cubo-rodamientos (axial)", m_rot * g * 15, m_rot * g * nB, m_rot * g * nB2, T2 - m_rot * g, m_rot * g * 200)
row("I8 bateria-brida", m_bat * g * 15, m_bat * g * nB, m_bat * g * nB2, m_bat * g, m_bat * g * 200)
row("I9 lastre-tapa inf.", m_las * g * 15, m_las * g * nB, m_las * g * nB2, m_las * g, m_las * g * 200)
row("I10 pared, maximo |N|", *[abs(cols[k]).max() for k in ("asc15", "dro35", "dro30G", "eta2", "ater200")])
row("I11 apoyo inferior", m_tot * g * 15, 0.0, 0.0, 0.0, body_mass(("drogue+cuerda",)) * g * 200)
print(f"\nFc por pala a 120 rad/s, r_cg={rcg*1000:.1f} mm: {Fc:.2f} N")
# par de fricción de rodamientos (modelo simple de catálogo, mu=0.0015)
Mfr = 0.5 * 0.0015 * T2 * 0.008
print(f"par de fricción 688ZZ (mu=0,0015, d=8 mm): {Mfr:.2e} N m (por par)")

# ---------------------------------------------------------------- arranque (estimación lineal)
Ip = 5.133e-4
Q0 = 0.026
tau = Ip * Om / Q0
print(f"\n== Arranque: tau = I*Omega/Q0 = {tau:.2f} s ; t(90%) = {tau*np.log(10):.2f} s")
E_rot = 0.5 * Ip * Om**2
print(f"energía de giro final = {E_rot:.2f} J")

# ---------------------------------------------------------------- holguras en el tubo
alpha = {"PETG": 6.8e-5, "fibra de vidrio": 1.5e-5, "cartón fenólico": 2.5e-5, "aluminio": 2.3e-5}
D_c = 95.0
tol_imp = 0.20   # +- en diámetro de la pieza impresa (radio de patines)
oval = 0.30      # ovalización del cuerpo impreso, diametral
tol_tubo = 0.25  # +- en el diámetro interior del tubo
dT_hot = 25.0    # 20 -> 45 C (sol en la rampa)
dT_cold = -15.0  # 20 -> 5 C

def clearance(Dt, mat, dT, worst=True):
    Dc = D_c * (1 + alpha["PETG"] * dT)
    Dtt = Dt * (1 + alpha[mat] * dT)
    if worst:
        return (Dtt - tol_tubo) - (Dc + tol_imp + oval)
    return Dtt - Dc

print("\n== Holgura diametral en el tubo (Dt nominal 98 mm) ==")
for mat in ["fibra de vidrio", "cartón fenólico", "aluminio"]:
    for dT in (dT_cold, 0.0, dT_hot):
        print(f"{mat:16s} dT={dT:+5.0f}  nominal={clearance(98, mat, dT, False):.3f}  peor={clearance(98, mat, dT):.3f}")
Dts = np.linspace(95.0, 100.0, 51)
with open(os.path.join(DATA, "planos_holgura.dat"), "w") as f:
    f.write("Dt nom fv_cal fv_frio al_cal carton_cal\n")
    for Dt in Dts:
        f.write(f"{Dt:.2f} {clearance(Dt,'fibra de vidrio',0,False):.4f} "
                f"{clearance(Dt,'fibra de vidrio',dT_hot):.4f} {clearance(Dt,'fibra de vidrio',dT_cold):.4f} "
                f"{clearance(Dt,'aluminio',dT_hot):.4f} {clearance(Dt,'cartón fenólico',dT_hot):.4f}\n")
# Dt mínimo para holgura peor caso >= 1,0 mm
for mat in ["fibra de vidrio", "aluminio", "cartón fenólico"]:
    for Dt in np.arange(95, 101, 0.01):
        if clearance(Dt, mat, dT_hot) >= 1.0:
            print(f"Dt mínimo ({mat}, caliente) para holgura peor >= 1 mm: {Dt:.2f} mm")
            break

# inclinación máxima dentro del tubo (contacto en diagonal): L sin t + D cos t = Dt
L = 250.0
for Dt in (96.0, 97.0, 98.0, 99.0):
    from scipy.optimize import brentq
    f_ = lambda t: L * np.sin(t) + D_c * np.cos(t) - Dt
    t = brentq(f_, 0, 0.3)
    print(f"Dt={Dt}: inclinación máx = {np.degrees(t):.3f} deg")
# regla del cajón: atasco si 2*mu*a > L  ->  a_crit = L/(2 mu)
for mu in (0.3, 0.5):
    print(f"mu={mu}: excentricidad crítica del empuje a = {L/(2*mu):.0f} mm (> radio 47,5: sin atasco)")

# fricción de extracción con el peso apoyado en la pared. Cerca del apogeo el cohete
# está en vuelo balístico (peso aparente ~0); como cota se toma el caso estático con el
# tubo inclinado 5 deg respecto de la vertical y el caso más desfavorable, tubo horizontal.
for mu in (0.3, 0.5):
    print(f"fricción, mu={mu}: tubo a 5 deg de la vertical {mu*W*np.sin(np.radians(5)):.3f} N ; "
          f"tubo horizontal {mu*W:.2f} N")
F15 = 0.5 * rho * 0.8 * A_d * 15**2
print(f"tirón del drogue abierto a 15 m/s (sin factor de choque): {F15:.2f} N")
print(f"masa del CanSat sin drogue (vuelo): {body_mass(('drogue+cuerda',))*1000:.0f} g ; "
      f"peso {body_mass(('drogue+cuerda',))*g:.3f} N ; z_cg = "
      f"{sum(m*z for n,m,z in ALL if n!='drogue+cuerda')/body_mass(('drogue+cuerda',)):.1f} mm")
