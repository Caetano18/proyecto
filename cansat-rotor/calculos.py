"""Cálculos del sistema de descenso de dos etapas (drogue + rotor libre).
Uso: python3 calculos.py  -> imprime todos los valores usados en el informe."""
import math as m

rho, g = 1.225, 9.81            # aire ISA nivel del mar, gravedad
M = 0.500                        # masa total CanSat + contenedor [kg]
W = M * g
# --- geometría ---
R, e, B, c = 0.20, 0.044, 4, 0.045      # radio, radio de bisagra, palas, cuerda
L = R - e                               # largo de pala
A_R = m.pi * R**2                       # área del disco
D_d, Cd_d = 0.25, 0.80                  # drogue
A_d = m.pi * D_d**2 / 4
D_c, Cd_c = 0.095, 0.80                 # cuerpo
A_c = m.pi * D_c**2 / 4
sigma = B * c / (m.pi * R)              # solidez

def P(name, val, unit="", fmt="{:.4g}"):
    print(f"{name:55s} = {fmt.format(val)} {unit}")

print("== Geometría ==")
P("largo de pala L", L*1000, "mm")
P("área del disco A_R", A_R, "m2")
P("área drogue A_d", A_d, "m2")
P("área cuerpo A_c", A_c, "m2")
P("solidez sigma", sigma)

print("\n== Etapa 1: drogue ==")
for D in (0.24, 0.25, 0.27, 0.30):
    A = m.pi*D**2/4
    V = m.sqrt(2*W/(rho*(Cd_d*A + Cd_c*A_c)))
    P(f"V drogue D={D*100:.0f} cm (con cuerpo)", V, "m/s")
V1 = m.sqrt(2*W/(rho*(Cd_d*A_d + Cd_c*A_c)))
# choque de apertura (Knacke): F = Cx * q * CdS, Cx~1.5 masa infinita
for Vdep in (15, 25, 35):
    q = 0.5*rho*Vdep**2
    P(f"choque de apertura a {Vdep} m/s (Cx=1.5)", 1.5*q*Cd_d*A_d, "N")

print("\n== Etapa 2: rotor (cantidad de movimiento) ==")
k_d = 0.5*rho*Cd_d*A_d; k_c = 0.5*rho*Cd_c*A_c
P("k drogue", k_d, "N/(m/s)^2"); P("k cuerpo", k_c, "N/(m/s)^2")
for CR in (1.0, 1.1, 1.2, 1.3):
    kR = 0.5*rho*CR*A_R
    P(f"V rotor+drogue+cuerpo C_R={CR}", m.sqrt(W/(kR+k_d+k_c)), "m/s")
    P(f"V rotor+cuerpo (drogue sin aporte) C_R={CR}", m.sqrt(W/(kR+k_c)), "m/s")
CR = 1.2
V2 = m.sqrt(W/(0.5*rho*CR*A_R + k_d + k_c))
T = W - (k_d + k_c)*V2**2
P("V2 recomendada", V2, "m/s"); P("empuje del rotor T", T, "N")
vh = m.sqrt(T/(2*rho*A_R))
P("velocidad inducida de vuelo estacionario v_h", vh, "m/s")
P("relación V2/v_h", V2/vh)
P("C_R equivalente = 4 (v_h/V)^2", 4*(vh/V2)**2)
# polinomio empírico (Leishman 2006) para -2 <= Vc/vh <= 0
kap, k1, k2, k3, k4 = 1.15, -1.125, -1.372, -1.718, -0.655
x = -V2/vh
vi = vh*(kap + k1*x + k2*x**2 + k3*x**3 + k4*x**4)
P("v_i (polinomio empírico)", vi, "m/s"); P("flujo neto por el disco Vc+v_i", -V2+vi, "m/s")
P("carga de disco T/A", T/A_R, "N/m2")

print("\n== rpm según perfil (T = B 1/2 rho Omega^2 c Cl (R^3-e^3)/3) ==")
I3 = (R**3 - e**3)/3
for name, cc, Cl in (("placa plana 3%", .035, .30), ("fondo plano", .035, .60),
                     ("curvada 7% c35", .035, .90), ("curvada 7% c45", .045, .90),
                     ("curvada 7% c50", .050, 1.0)):
    Om = m.sqrt(T/(B*0.5*rho*cc*Cl*I3))
    rpm = Om*30/m.pi; Vt = Om*R; Re = Vt*cc/1.5e-5
    print(f"  {name:18s} Omega={Om:6.1f} rad/s  rpm={rpm:6.0f}  Vpunta={Vt:5.1f} m/s  Re_punta={Re:8.0f}  Re_0.5R={Re*0.5:7.0f}")
Om = m.sqrt(T/(B*0.5*rho*c*0.9*I3)); rpm = Om*30/m.pi
P("Omega diseño", Om, "rad/s"); P("rpm diseño", rpm, "rpm")
print("\n== Pala ==")
t_c = 0.0005; rho_cf = 1550
mb = L*c*t_c*rho_cf + 0.0020          # placa + portapala/raíz
P("masa de pala (placa 0.5 mm + 2 g raíz)", mb*1000, "g")
rg = e + L/2
Fc = mb*rg*Om**2
P("fuerza centrífuga por pala", Fc, "N")
P("tensión de corte pasador Ø2 doble corte", Fc/(2*m.pi*0.001**2)/1e6, "MPa")
# conicidad: beta = M_L / (m Omega^2 <r(r-e)>)
Lb = T/B; arm = 0.75*R - e
ML = Lb*arm
avg = e*L/2 + L**2/3
Kc = mb*Om**2*avg
MG = mb*g*L/2
beta = (ML - MG)/Kc
P("sustentación por pala", Lb, "N"); P("momento de sustentación en bisagra", ML, "N m")
P("rigidez centrífuga de batimiento", Kc, "N m/rad")
P("conicidad de equilibrio beta0", m.degrees(beta), "deg")
Ib = mb*L**2/3
a = 2*m.pi*0.9
gam = rho*a*c*R**4/Ib
P("momento de inercia de batimiento I_b", Ib, "kg m2")
P("número de Lock gamma", gam)
P("frecuencia de batimiento nu_beta/Omega", m.sqrt(1 + 1.5*e/L))
# Inercia del rotor y arranque
I_rot = B*mb*(e**2 + e*R + R**2)/3 + 1.0e-5
P("inercia polar del rotor", I_rot, "kg m2")
P("energía cinética de giro", 0.5*I_rot*Om**2, "J")
for Q in (0.005, 0.01, 0.02):
    t = I_rot*Om/Q
    P(f"tiempo de arranque con Q={Q} N m", t, "s")
# desbalance
for dm in (0.0001, 0.0005, 0.001):
    P(f"fuerza por desbalance {dm*1000:.1f} g a 0.12 m", dm*0.12*Om**2, "N")

print("\n== Estructura ==")
for G in (15, 30):
    F = M*G*g; A = m.pi*0.093*0.002
    P(f"esfuerzo axial pared 2 mm a {G} G", F/A/1e6, "MPa")
E_petg, nu = 2.0e9, 0.38; t, Rm = 0.002, 0.0465
scr = 0.3*E_petg*t/(Rm*m.sqrt(3*(1-nu**2)))
P("tensión crítica de pandeo (knockdown 0.3)", scr/1e6, "MPa")
P("carga por pala en choque 30 G", mb*30*g, "N")
P("choque en cuerda del drogue 30 G sobre 0.5 kg", M*30*g, "N")

print("\n== Transición y tiempos ==")
h0 = 700.0
for hmax in (500, 700, 1000):
    h80 = 0.8*hmax
    t1 = (hmax - h80)/V1; t2 = h80/V2
    Vavg = hmax/(t1+t2)
    print(f"  apogeo {hmax} m: etapa1 {t1:5.1f} s, etapa2 {t2:5.1f} s, total {t1+t2:5.1f} s, V media total {Vavg:4.2f} m/s, V media etapa2 {V2:.2f}")
P("V etapa 1 (drogue 25 cm + cuerpo)", V1, "m/s")
for Cd in (0.75, 0.9):
    P(f"V etapa 1 con Cd={Cd}", m.sqrt(2*W/(rho*(Cd*A_d + Cd_c*A_c))), "m/s")
print("\n== Par de arranque (Omega=0, flujo a 90 grados) ==")
for th in (-6, -4, -2, 0, 2):
    al = m.radians(90 + th); Cn = 2*m.sin(al); Cl0 = Cn*m.cos(al)
    Q0 = B*0.5*rho*V1**2*Cl0*c*(R**2 - e**2)/2
    P(f"par de arranque, paso {th:+d} grados", Q0, "N m")
