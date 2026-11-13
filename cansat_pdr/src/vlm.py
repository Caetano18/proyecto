"""Red de vortices (VLM) de placa plana para una planta cualquiera, mas succion de borde de ataque (analogia de Polhamus).

Ejes: x hacia atras (corriente +x), y envergadura, z arriba.  Herraduras con patas hacia +x, vortice ligado al 1/4 de cada panel y
punto de control al 3/4.  Solucion lineal para un ataque pequeno; el resto (no linealidad, vortice) se escala con Polhamus.

Succion de borde de ataque: cerca del borde la carga vale  dC_p = B / sqrt(d)  (d = distancia normal al borde) y la fuerza de succion
por unidad de longitud es  S = (pi/16) rho V_n^2 B_n^2 / ...  (se verifica con una placa 2D: S = pi rho V^2 c alfa^2).
B se estima del primer panel: dC_p medio = 2 B / sqrt(dd)  =>  B = dC_p sqrt(dd) / 2.
"""
import numpy as np

RHO = 1.0


def _seg(P, A, B):
    """Velocidad inducida en P [N,3] por un segmento A->B [M,3] de circulacion unitaria.  Devuelve [N,M,3]."""
    r1 = P[:, None, :] - A[None, :, :]
    r2 = P[:, None, :] - B[None, :, :]
    r0 = (B - A)[None, :, :]
    cr = np.cross(r1, r2)
    n2 = np.sum(cr * cr, axis=-1)
    n1 = np.linalg.norm(r1, axis=-1)
    n2n = np.linalg.norm(r2, axis=-1)
    dot = np.sum(r0 * (r1 / n1[..., None] - r2 / n2n[..., None]), axis=-1)
    eps = 1e-10
    k = np.where(n2 > eps, dot / (4 * np.pi * np.maximum(n2, eps)), 0.0)
    return cr * k[..., None]


class Ala:
    def __init__(self, x_le, x_te, y_edges, nx=16):
        """x_le(|y|), x_te(|y|): funciones del borde de ataque y de fuga.  y_edges: bordes de las tiras (simetricos, crecientes)."""
        self.x_le, self.x_te = x_le, x_te
        ye = np.asarray(y_edges, float)
        self.ye, self.nx, self.ny = ye, nx, len(ye) - 1
        f = 0.5 * (1 - np.cos(np.pi * np.arange(nx + 1) / nx))          # espaciado coseno en la cuerda
        self.f = f
        A, B, CP, area, row, strip = [], [], [], [], [], []
        xa_f, xb_f, ya, yb = [], [], [], []
        for j in range(self.ny):
            y0, y1 = ye[j], ye[j + 1]
            l0, c0 = x_le(abs(y0)), x_te(abs(y0)) - x_le(abs(y0))
            l1, c1 = x_le(abs(y1)), x_te(abs(y1)) - x_le(abs(y1))
            for k in range(nx):
                fk, fk1 = f[k], f[k + 1]
                q = fk + 0.25 * (fk1 - fk)
                t = fk + 0.75 * (fk1 - fk)
                A.append((l0 + q * c0, y0, 0.0))
                B.append((l1 + q * c1, y1, 0.0))
                CP.append((0.5 * (l0 + t * c0 + l1 + t * c1), 0.5 * (y0 + y1), 0.0))
                p = [(l0 + fk * c0, y0), (l0 + fk1 * c0, y0), (l1 + fk1 * c1, y1), (l1 + fk * c1, y1)]
                area.append(0.5 * abs(sum(p[i][0] * p[(i + 1) % 4][1] - p[(i + 1) % 4][0] * p[i][1] for i in range(4))))
                row.append(k)
                strip.append(j)
        self.A, self.B, self.CP = np.array(A), np.array(B), np.array(CP)
        self.area, self.row, self.strip = np.array(area), np.array(row), np.array(strip)
        self.N = len(self.A)
        self.dy = self.B[:, 1] - self.A[:, 1]
        self.S = float(self.area.sum())

    def matriz(self):
        L = 1e7
        ex = np.array([L, 0.0, 0.0])
        M = np.zeros((self.N, self.N))
        for i0 in range(0, self.N, 400):
            P = self.CP[i0:i0 + 400]
            v = _seg(P, self.A + ex, self.A) + _seg(P, self.A, self.B) + _seg(P, self.B, self.B + ex)
            M[i0:i0 + 400] = v[..., 2]
        return M

    def resolver(self, alfa=np.radians(1.0)):
        """Circulaciones para el ataque `alfa` (V = 1).  Devuelve Gamma [N]."""
        if not hasattr(self, "_M"):
            self._M = self.matriz()
        return np.linalg.solve(self._M, -alfa * np.ones(self.N))

    def resultados(self, alfa=np.radians(1.0), Sref=None, x0=0.0):
        G = self.resolver(alfa)
        Sref = Sref or self.S
        Lp = 2 * G * self.dy                                    # fuerza por panel con rho V = 1 y q = 1/2 -> L = rho V G dy
        L = Lp                                                  # [V = 1, rho = 1]
        xq = 0.5 * (self.A[:, 0] + self.B[:, 0])
        CL = float(np.sum(L) / Sref)                            # C_L = L / (q S) con q = 1/2
        dcp = L * 1.0 / (self.area)                             # DeltaC_p = (L/area)/(q) con q = 1/2 -> L/area*2/1 ; L ya incluye el 2
        dcp = (L / self.area) / 1.0
        xcp = float(np.sum(L * xq) / np.sum(L))
        return dict(G=G, CL=CL, dcp=dcp, xcp=xcp, L=L, xq=xq, Sref=Sref, CLa=CL / alfa, CM0=float(-np.sum(L * (xq - x0)) / (Sref)))

    def succion(self, alfa=np.radians(1.0)):
        """Succion de borde de ataque por tira (primer panel): devuelve (y_medio, dl, Sprima, theta) con V = rho = 1 y q = 1/2."""
        r = self.resultados(alfa)
        dcp = r["dcp"]
        out = []
        for j in range(self.ny):
            idx = np.where((self.strip == j) & (self.row == 0))[0][0]
            y0, y1 = self.ye[j], self.ye[j + 1]
            xl0, xl1 = self.x_le(abs(y0)), self.x_le(abs(y1))
            dl = float(np.hypot(y1 - y0, xl1 - xl0))
            sin_t = abs(y1 - y0) / dl                                          # seno del angulo del borde con la corriente
            ym = 0.5 * (y0 + y1)
            c_m = self.x_te(abs(ym)) - self.x_le(abs(ym))
            dd = c_m * (self.f[1] - self.f[0]) * sin_t                          # ancho normal del primer panel
            vn2 = sin_t ** 2
            dcp_n = dcp[idx] / max(vn2, 1e-9)                                  # carga referida a q_n
            B = dcp_n * np.sqrt(dd) / 2
            Sp = (np.pi / 16) * vn2 * B ** 2 * 1.0                             # rho = 1, V = 1 -> S' = pi/16 rho V_n^2 B^2
            out.append((ym, dl, Sp, sin_t))
        return np.array(out), r


def rectangular(AR, c=1.0, ny=40, nx=16):
    b = AR * c
    ye = 0.5 * b * (-np.cos(np.pi * np.arange(ny + 1) / ny))
    return Ala(lambda y: 0.0 * y, lambda y: c + 0.0 * y, ye, nx)
