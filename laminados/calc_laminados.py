"""TP Laminados especiales - Teoria Clasica de Laminados (unidades: kN, mm)."""
import numpy as np
np.set_printoptions(precision=4, suppress=False, linewidth=150)

E1, E2, G12, n12, t = 140.0, 10.0, 5.0, 0.3, 0.125
n21 = n12 * E2 / E1
den = 1 - n12 * n21
Q = np.array([[E1/den, n12*E2/den, 0], [n12*E2/den, E2/den, 0], [0, 0, G12]])

def Qbar(th):
    c, s = np.cos(np.radians(th)), np.sin(np.radians(th))
    T = np.array([[c*c, s*s, 2*c*s], [s*s, c*c, -2*c*s], [-c*s, c*s, c*c-s*s]])
    R = np.diag([1, 1, 2])
    return np.linalg.inv(T) @ Q @ R @ T @ np.linalg.inv(R)

def abd(angles):
    n = len(angles); h = n*t
    z = -h/2 + t*np.arange(n+1)
    A = np.zeros((3,3)); B = np.zeros((3,3)); D = np.zeros((3,3))
    for k, th in enumerate(angles):
        Qb = Qbar(th)
        A += Qb*(z[k+1]-z[k]); B += Qb*(z[k+1]**2-z[k]**2)/2; D += Qb*(z[k+1]**3-z[k]**3)/3
    return A, B, D, h, z

def consts(M, h, flex):
    m = np.linalg.inv(M)
    f = 1/h if not flex else 12/h**3
    return dict(Ex=f/m[0,0], Ey=f/m[1,1], Gxy=f/m[2,2], nxy=-m[0,1]/m[0,0], nyx=-m[0,1]/m[1,1])

if __name__ == "__main__":
    print("nu21 =", n21, " Q =\n", Q)
    for th in (0, 45, -45, 90): print(th, "\n", Qbar(th))
    casos = {"P1 (0/45/-45/90)s": [0,45,-45,90,90,-45,45,0],
             "A (0/0/90/90)": [0,0,90,90], "B (0/90/0/90)": [0,90,0,90], "C (0/90)s": [0,90,90,0]}
    for name, ang in casos.items():
        A, B, D, h, z = abd(ang)
        print("\n=====", name, " h =", h, " z =", z)
        print("A =\n", A); print("B =\n", B); print("D =\n", D)
        print("membrana A^-1:", consts(A, h, False))
        print("flexion  D^-1:", consts(D, h, True))
        ABD = np.block([[A, B], [B, D]])
        if abs(B).max() > 1e-9:
            inv = np.linalg.inv(ABD); a = inv[:3,:3]; d = inv[3:,3:]
            print("acoplado: a=\n", a, "\n b=\n", inv[:3,3:], "\n d=\n", d)
            print("membrana (a completo):", dict(Ex=1/(h*a[0,0]), Ey=1/(h*a[1,1]), Gxy=1/(h*a[2,2]), nxy=-a[0,1]/a[0,0]))
            print("flexion (d completo):", dict(Ex=12/(h**3*d[0,0]), Ey=12/(h**3*d[1,1]), Gxy=12/(h**3*d[2,2]), nxy=-d[0,1]/d[0,0]))
