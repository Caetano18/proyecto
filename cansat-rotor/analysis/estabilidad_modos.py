"""Estabilidad del conjunto rotor-cuerpo-drogue (cap. 14).
Modelos linealizados; todas las entradas marcadas 'est.' son estimaciones."""
import numpy as np
from scipy.linalg import eig
D = 'analysis/data/'
rho, g = 1.225, 9.81
m, W = 0.500, 0.500*9.81
R, e, B, c = 0.200, 0.044, 4, 0.045
A = np.pi*R**2
Om0, V0, T0 = 157.6, 6.94, 3.58          # BEMT con drogue
Vnd = 7.91                               # sin drogue
gam, Ib, mb, xg = 11.5, 4.35e-5, 7.4e-3, 0.059
Sb = mb*xg
Db = 0.5*rho*0.8*0.00709                 # cuerpo, coef. de V^2
out = {}
# ---------------- 1. anillo de vortices ----------------
vh = np.sqrt(T0/(2*rho*A)); out['vh'] = vh; out['V/vh'] = V0/vh
vhn = np.sqrt(W/(2*rho*A)); out['V/vh sin drogue'] = Vnd/vhn
tr = np.loadtxt(D+'bemt_transitorio.dat', skiprows=1)
with open(D+'estabilidad_vrs.dat', 'w') as f:
    f.write('t V vh r\n')
    for t, Om, V, rpm, T in tr[::4]:
        if T > 0.05:
            v = np.sqrt(T/(2*rho*A)); f.write(f'{t:.3f} {V:.3f} {v:.3f} {V/v:.3f}\n')
for lim in (1.5, 2.0):
    out[f'rafaga a {lim}'] = V0 - lim*vh
# ---------------- 2. modos de pendulo ----------------
Ip = B*(Ib + 2*e*Sb + mb*e**2) + 0.5*0.015*0.022**2
Hhub = 0.5*0.015*0.022**2
def modos(h=0.15, Om=Om0, L=1.5, kH=1.0, drogue=True, It=3.0e-3, fin=0.0, lf=0.10):
    V = V0 if drogue else Vnd
    T = T0*(Om/Om0)**2 if drogue else W
    N = max(W - T - Db*V**2, 0) if drogue else 0.0
    md = 0.015
    ha = h + 0.03
    cr = kH*T/V
    Kh = B/2*e*Sb*Om**2
    cq = Kh*16/(gam*Om)
    Heff = Hhub + Kh/Om
    cd = 2*N/V if N > 0 else 0
    cf = fin                       # amortig. lateral de aletas [N s/m] a lf bajo el CG
    # x = [X, th, Y]
    M = np.diag([m, It, md]).astype(complex)
    C = np.zeros((3, 3), complex); K = np.zeros((3, 3), complex)
    C[0, 0] = cr + cf; C[0, 1] = cr*h - cf*lf
    C[1, 0] = cr*h - cf*lf; C[1, 1] = cr*h**2 + cq - 1j*Heff + cf*lf**2
    C[2, 2] = cd
    K[0, 1] = -(1-kH)*T + cf*V*0   # fuerza por inclinacion
    K[1, 1] = kH*T*h + cf*V*lf
    K[0, 1] += -cf*V
    if N > 0:
        k = N/L
        Kt = np.array([[k, k*ha, -k], [k*ha, k*ha**2 + N*ha, -k*ha], [-k, -k*ha, k]])
        K += Kt
    Z = np.zeros((3, 3)); I = np.eye(3)
    Mi = np.linalg.inv(M)
    Aa = np.block([[Z, I], [-Mi@K, -Mi@C]])
    lam = np.linalg.eigvals(Aa)
    return lam[np.argsort(-lam.real)]
lam0 = modos(); out['modos nominal'] = lam0[abs(lam0)>1e-6]
out['modos sin drogue'] = [l for l in modos(drogue=False) if abs(l)>1e-6]
out['modos h=0.05'] = modos(h=0.05)[1:]
out['modos con aletas'] = modos(fin=0.5*rho*V0*2.6*0.0016*4/2)[1:]
def barrido(name, par, vals, **kw):
    with open(D+f'estabilidad_rl_{name}.dat', 'w') as f:
        f.write('p re im\n')
        for v in vals:
            for l in modos(**{par: v}, **kw):
                if abs(l) > 1e-6: f.write(f'{v:.4f} {l.real:.4f} {l.imag:.4f}\n')
barrido('h', 'h', np.linspace(0.05, 0.22, 18))
barrido('om', 'Om', np.linspace(0.5, 1.2, 15)*Om0)
barrido('L', 'L', np.linspace(0.5, 3.0, 11))
barrido('kH', 'kH', np.linspace(0.3, 1.5, 13))
out['peor Re (barridos)'] = max(max(modos(h=h, kH=k, L=L).real) for h in (0.05, 0.22) for k in (0.3, 1.5) for L in (0.5, 3))
# ---------------- 3. giro del cuerpo ----------------
# rodamiento: M = Mrod(vel. relativa) (Palmgren + SKF simplificado), dos rodamientos
dm, P, mu = 12.0, 12.1, 0.0015
def Mrod(dn, f0=1.5, nu=25.0):
    n = abs(dn)*60/(2*np.pi)
    M0 = 1e-7*f0*(nu*n)**(2/3)*dm**3*1e-3 if nu*n >= 2000 else 160e-7*f0*dm**3*1e-3
    return 2*(M0 + 0.5*mu*P*8e-3)*np.sign(dn)
Mf = Mrod(Om0); out['Mrod nominal [N m]'] = Mf
out['Mrod rango'] = (Mrod(Om0, 0.7, 15), Mrod(Om0, 2.0, 70))
Iz = 4.0e-4                                    # est.
Rb, Lb = 0.0475, 0.25
cb = (1.33/np.sqrt(V0*Lb/1.5e-5))*0.5*rho*V0*Rb**2*2*np.pi*Rb*Lb
out['c cuerpo'] = cb
def cfin(n, s, l, rf0=0.044):
    S = s*l; AR = 2*s/l
    a = 2*np.pi*AR/(2 + np.sqrt(AR**2 + 4))
    rf = rf0 + s/2
    return n*0.5*rho*V0*a*S*rf**2, n*0.5*rho*V0**2*a*S*rf, a
def simula(cdamp, Mcant=0.0, tend=40.0, dt=0.01):
    w = 0.0; res = []
    for k in range(int(tend/dt)+1):
        t = k*dt
        res.append((t, w))
        dw = (Mrod(Om0 - w) - cdamp*w - Mcant)/Iz
        w += dw*dt
    return np.array(res)
s0 = simula(cb); cf44, tq44, a44 = cfin(4, 0.040, 0.040)
s1 = simula(cb + cf44)
cf46, tq46, _ = cfin(4, 0.060, 0.050)
s2 = simula(cb + cf46)
with open(D+'estabilidad_giro.dat', 'w') as f:
    f.write('t w0 w1 w2\n')
    for i in range(0, len(s0), 50):
        f.write(f'{s0[i,0]:.2f} {s0[i,1]*30/np.pi:.2f} {s1[i,1]*30/np.pi:.2f} {s2[i,1]*30/np.pi:.2f}\n')
out['giro sin aletas a 10,20,40 s [rpm]'] = [s0[int(t/0.01), 1]*30/np.pi for t in (10, 20, 40)]
out['aletas 4x40x40: c, torque/rad, w_eq [rad/s]'] = (cf44, tq44, Mf/(cb+cf44))
out['aletas 4x60x50: c, torque/rad, w_eq'] = (cf46, tq46, Mf/(cb+cf46))
out['cant para anular Mf 40x40 [deg]'] = np.degrees(Mf/tq44)
with open(D+'estabilidad_aletas.dat', 'w') as f:
    f.write('s w1 w2 cant\n')
    for s in np.linspace(0.01, 0.08, 15):
        cfx, tqx, _ = cfin(4, s, 0.040)
        cfy, _, _ = cfin(4, s, 0.060)
        f.write(f'{s*1000:.1f} {Mf/(cb+cfx):.3f} {Mf/(cb+cfy):.3f} {np.degrees(Mf/tqx):.3f}\n')
# ---------------- 4. batimiento y delta-3 ----------------
nu2 = 1 + e*Sb/Ib + 0.005/(Ib*Om0**2); out['nu_beta'] = np.sqrt(nu2)
z = gam/(16*np.sqrt(nu2)); out['zeta_beta'] = z
out['s/Om batimiento'] = -z*np.sqrt(nu2) + 1j*np.sqrt(nu2)*np.sqrt(1-z**2)
with open(D+'estabilidad_d3.dat', 'w') as f:
    f.write('d3 nu zeta beta0 dth\n')
    for d3 in np.linspace(-30, 45, 16):
        Kp = np.tan(np.radians(d3))
        ne2 = nu2 + gam/8*Kp
        b0 = 6.1*nu2/ne2
        f.write(f'{d3:.1f} {np.sqrt(ne2):.4f} {gam/(16*np.sqrt(ne2)):.4f} {b0:.3f} {-Kp*b0:.3f}\n')
# ---------------- 5. flameo cuasiestacionario 2 GDL ----------------
Lp = 0.156
def flutter(mu_l, Ith, ycc, ycg, GJ, a=5.7):
    b = c/2
    r = 0.75*R
    xa = (ycg - ycc)*c         # c.m. detras del eje elastico
    xac = (ycc - 0.25)*c       # c.a. delante del eje
    wth0 = np.pi/(2*Lp)*np.sqrt(GJ/Ith)
    def lam(Om):
        U = Om*r; q = 0.5*rho*U**2
        wh2 = nu2*Om**2; wa2 = wth0**2 + Om**2
        S = mu_l*xa; Ia = Ith
        Mm = np.array([[mu_l, S], [S, Ia]])
        La = q*c*a                       # dL/dalpha
        K = np.array([[mu_l*wh2, La], [0, Ia*wa2 - La*xac]])
        Cc = np.array([[La/U, La*(0.75*c - ycc*c)/U], [-La*xac/U, -La*xac*(0.75*c-ycc*c)/U + np.pi*rho*b**3*U*(0.5-(ycc-0.5)*2)]])
        Mi = np.linalg.inv(Mm)
        Aa = np.block([[np.zeros((2, 2)), np.eye(2)], [-Mi@K, -Mi@Cc]])
        return np.linalg.eigvals(Aa)
    Oms = np.linspace(50, 1200, 1151)
    crit = None; div = None
    for O in Oms:
        l = lam(O)
        unst = l[l.real > 1e-6]
        if len(unst):
            crit = O; div = bool(np.any(abs(unst.imag) < 1e-6)); break
    return crit, div, wth0
for nm, p in {'A': (0.0342, 5.96e-6, 0.500, 0.500, 7.6e-3), 'BV': (0.0396, 8.21e-6, 0.428, 0.441, 51.7e-3)}.items():
    cr_, dv, wt = flutter(*p)
    out[f'flameo {nm}: Omc [rad/s], es divergencia, wth0'] = (cr_, dv, wt, (cr_/Om0) if cr_ else None)
with open(D+'estabilidad_flameo.dat', 'w') as f:
    f.write('ycg OmA OmBV\n')
    for yc in np.linspace(0.30, 0.60, 13):
        a_, _, _ = flutter(0.0342, 5.96e-6, 0.500, yc, 7.6e-3)
        b_, _, _ = flutter(0.0396, 8.21e-6, 0.428, yc, 51.7e-3)
        f.write(f'{yc:.3f} {(a_ or 1200)/Om0:.3f} {(b_ or 1200)/Om0:.3f}\n')
# ---------------- 6. drogue ----------------
zexit, ztip = 0.030, (R-e)*np.sin(np.radians(6.1))
out['angulo cuerda para tocar puntas [deg]'] = 90 - np.degrees(np.arctan((zexit-ztip)/R))
Nn = W - T0 - Db*V0**2; out['tension drogue N'] = Nn
for O in (0.5*Om0, Om0): print('Kh, Heff, Ip*Om', B/2*e*Sb*O**2, Hhub+B/2*e*Sb*O, Ip*O)
for k, v in out.items(): print(k, ':', v)
