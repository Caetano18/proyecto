"""Capitulo de revision de la literatura (prefijo literatura).
Compara la carga de disco y la velocidad de descenso de decelerador rotativo publicados
con el diseno propio. Solo usa datos publicados (Brindejonc et al. 2007) y los datos base
del proyecto. Salida: analysis/data/literatura_curvas.dat y literatura_puntos.dat."""
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
# Frecuencia de respiracion del drogue si St = f D / V = 0,55 (Johari y Desabrais 2005)
for v in (6.4, 13.4):
    print('f_resp', v, 0.55*v/0.25)
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
