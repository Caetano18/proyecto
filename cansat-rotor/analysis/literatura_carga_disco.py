"""Capitulo de revision de la literatura (prefijo literatura).
Compara la carga de disco y la velocidad de descenso de decelerador rotativo publicados
con el diseno propio. Solo usa datos publicados (Brindejonc et al. 2007) y los datos base
del proyecto. Salidas: analysis/data/literatura_{curvas,puntos,ct_a,ct_leish,energia}.dat."""
import numpy as np, os
rho = 1.225; g = 9.81
out = os.path.join(os.path.dirname(__file__), 'data')

def V(DL, C):
    return np.sqrt(2*DL/(rho*C))

DL = np.logspace(np.log10(5), np.log10(120), 60)
with open(os.path.join(out, 'literatura_curvas.dat'), 'w') as f:
    f.write('DL C08 C10 C12 C15 C18\n')
    for d in DL:
        f.write(f'{d:.4f} ' + ' '.join(f'{V(d,c):.4f}' for c in (0.8,1.0,1.2,1.5,1.8)) + '\n')

pts = []
# Brindejonc, Sirohi y Chopra (2007): 4 palas, D = 4 ft, m = 2,27 kg
A = np.pi*(4*0.3048/2)**2; W = 2.27*g; DLb = W/A
for name, v in (('autobody_req', 4.57), ('autobody_med', 4.11)):
    pts.append((name, DLb, v, 2*DLb/(rho*v**2)))
# Diseno propio (datos base): A_R = 0,1257 m2
AR = 0.1257; Wp = 0.500*g
pts.append(('propio_rotor', 3.78/AR, 6.4, 2*(3.78/AR)/(rho*6.4**2)))     # empuje del rotor con drogue
pts.append(('propio_peor', Wp/AR, 7.8, 2*(Wp/AR)/(rho*7.8**2)))         # sin aporte del drogue
pts.append(('propio_c4', Wp/AR, 5.0, 2*(Wp/AR)/(rho*5.0**2)))           # C necesario para 5 m/s sin drogue
with open(os.path.join(out, 'literatura_puntos.dat'), 'w') as f:
    f.write('caso DL V Ceq\n')
    for p in pts:
        f.write(f'{p[0]} {p[1]:.3f} {p[2]:.3f} {p[3]:.3f}\n')
for p in pts: print(p)
# Frecuencia de respiracion del drogue si St = f D_p / V = 0,55 (Johari y Desabrais 2005).
# Johari usa el diametro PROYECTADO medio de la campana. 0,25 m es el diametro nominal
# (Cd = 0,8 referido a el); para un paracaidas plano circular D_p/D_0 ~ 0,67-0,70 (Knacke).
for v in (6.4, 13.4):
    print('f_resp', v, 'D0:', 0.55*v/0.25, 'Dp=0,68 D0:', 0.55*v/(0.68*0.25))
# Numero de Reynolds de Laitone (20 000 - 70 000) frente al rotor propio
print('Re punta', 24*0.045/1.5e-5, 'Re medio', 12*0.045/1.5e-5)

# ---- Curvas CT(a): cantidad de movimiento, Buhl (2005) y polinomio de Leishman convertido
def buhl(a, F=1.0):
    ac = 0.4
    return np.where(a <= ac, 4*a*F*(1-a), 8/9 + (4*F - 40/9)*a + (50/9 - 4*F)*a**2)
a = np.linspace(0, 1.0, 101)
with open(os.path.join(out, 'literatura_ct_a.dat'), 'w') as f:
    f.write('a CTmom CTbuhl CTbuhl09\n')
    for ai in a:
        f.write(f'{ai:.3f} {4*ai*(1-ai):.4f} {float(buhl(ai)):.4f} {float(buhl(ai,0.9)):.4f}\n')
kap, k1, k2, k3, k4 = 1.15, -1.125, -1.372, -1.718, -0.655
with open(os.path.join(out, 'literatura_ct_leish.dat'), 'w') as f:
    f.write('x a CT\n')
    for x in np.linspace(-2.0, -1.3, 36):
        vi = kap + k1*x + k2*x**2 + k3*x**3 + k4*x**4
        f.write(f'{x:.3f} {vi/(-x):.4f} {4/x**2:.4f}\n')
x = -1.83; vi = kap + k1*x + k2*x**2 + k3*x**3 + k4*x**4
print('Leishman x=-1.83: vi/vh', vi, 'a', vi/1.83, 'CT', 4/1.83**2)
from scipy.optimize import brentq
for C in (1.0, 1.2):
    print('Buhl a para CT', C, brentq(lambda t: float(buhl(t)) - C, 0.4, 1.0))

# ---- Cierre por balance de energia (revision): en autorrotacion T (V - v_i) = P0 (potencia de
# perfil). Con Omega fijo en la estimacion base (120 rad/s) y C_d medio de la pala como
# parametro, se obtiene el flujo neto por el disco w = V - v_i, el factor a = 1 - w/V, y la
# velocidad de equilibrio V que da cada curva empirica (Leishman o Buhl), con el drogue y el
# cuerpo en corriente libre (T = W - D_drogue - D_cuerpo). Es una estimacion de orden.
Wt = 0.500*g; AR = 0.1257; R = 0.200; e = 0.044; B = 4; c = 0.045; Om = 120.0
def vi_l(x): return kap + k1*x + k2*x**2 + k3*x**3 + k4*x**4
def buhl_a(CT):
    if CT <= 0.96: return 0.5*(1 - np.sqrt(1 - CT))
    return brentq(lambda t: float(buhl(t)) - CT, 0.4, 1.05)
def T_of_V(V): return Wt - 0.5*rho*V**2*0.8*(0.0491 + 0.00709)
with open(os.path.join(out, 'literatura_energia.dat'), 'w') as f:
    f.write('Cd P0 w a phi75 VL CRL VB CRB\n')
    for Cd in (0.03, 0.045, 0.06, 0.075, 0.09):
        P0 = B*0.5*rho*c*Cd*Om**3*(R**4 - e**4)/4
        w = P0/3.78; a_ = 1 - w/6.4
        phi = np.degrees(np.arctan(w/(Om*0.75*R)))
        def fL(V):
            T = T_of_V(V); vh = np.sqrt(T/(2*rho*AR))
            return V - vi_l(-V/vh)*vh - P0/T
        def fB(V):
            T = T_of_V(V); CT = T/(0.5*rho*V**2*AR)
            return V*(1 - buhl_a(min(CT, 2.0))) - P0/T
        VL = brentq(fL, 5.0, 7.5); VB = brentq(fB, 4.0, 7.5)
        CRL = T_of_V(VL)/(0.5*rho*VL**2*AR); CRB = T_of_V(VB)/(0.5*rho*VB**2*AR)
        f.write(f'{Cd:.3f} {P0:.3f} {w:.3f} {a_:.3f} {phi:.2f} {VL:.3f} {CRL:.3f} {VB:.3f} {CRB:.3f}\n')
        print(f'energia Cd={Cd} P0={P0:.2f} W w={w:.2f} m/s a={a_:.3f} phi75={phi:.1f} | '
              f'Leishman V={VL:.2f} CR={CRL:.2f} | Buhl V={VB:.2f} CR={CRB:.2f}')
