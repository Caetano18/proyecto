"""Figuras acotadas para las laminas en ingles (plantilla de la competencia).

Las figuras del informe estan dibujadas a escala de hoja A4; en una lamina quedan con letra de 4 pt.  Estas se
dibujan para el lugar que ocupan en la lamina (unos 8,5 x 4,3 pulgadas), con letra de 11 pt y pocas cotas.
Uso: python3 figs_laminas.py <carpeta_figs>
"""
import sys
import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Arc, FancyArrowPatch
import params as P
import cad
from hlr import Lienzo
from planos import medio, f1

FS = 11.0
AZ, NAV, TEAL = "#2f3192", "#242C4F", "#138A8A"


def en(x):
    return f1(x).replace(",", ".")


class Hoja(Lienzo):
    """Lienzo con flechas y lineas de cota del tamano que pide la letra de 11 pt."""

    def _flecha(self, p, q):
        self.ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>", mutation_scale=8, lw=0.55, color="k",
                                          shrinkA=0, shrinkB=0))

    def cota_h(self, p1, p2, y, txt, dy=1.6, color="k", fs=FS, xt=None):
        for p in (p1, p2):
            s = 1 if y > p[1] else -1
            self.ax.plot([p[0], p[0]], [p[1] + s * 0.8, y + s * 1.8], color="0.3", lw=0.4)
        self._flecha((p1[0], y), (p2[0], y))
        self.ax.text(0.5 * (p1[0] + p2[0]) if xt is None else xt, y + dy, txt, ha="center",
                     va="bottom" if dy > 0 else "top", fontsize=fs, color=color)

    def cota_v(self, p1, p2, x, txt, dx=-1.6, fs=FS):
        for p in (p1, p2):
            s = 1 if x > p[0] else -1
            self.ax.plot([p[0] + s * 0.8, x + s * 1.8], [p[1], p[1]], color="0.3", lw=0.4)
        self._flecha((x, p1[1]), (x, p2[1]))
        self.ax.text(x + dx, 0.5 * (p1[1] + p2[1]), txt, ha="right" if dx < 0 else "left", va="center", fontsize=fs,
                     rotation=90)

    def llamada(self, p, q, txt, ha="left", fs=FS - 0.5):
        self.ax.annotate(txt, xy=p, xytext=q, fontsize=fs, ha=ha, va="center", color=NAV,
                         arrowprops=dict(arrowstyle="-|>", lw=0.55, color=NAV, mutation_scale=7, shrinkA=2, shrinkB=0))

    def titulo(self, x, y, t):
        self.ax.text(x, y, t, fontsize=FS, ha="center", va="top", weight="bold", color=TEAL)


def piezas(conf):
    return [p["shape"] for p in cad.build(conf) if p["grupo"] != "carenado"]


def dimensiones(out, lan, est, des):
    h = Hoja(250, 86)
    x0 = P.CT_X[0]
    s = 0.48
    # --- corte de la configuracion de lanzamiento
    T = h.vista(medio(lan, "y", 1), "lateral", (24, 49), s, ref=(x0, 0, 0), lw=0.5)
    yb, yt = T((0, 0, -45))[1], T((0, 0, 45))[1]
    h.cota_h(T((0, 0, -45)), T((P.L_G, 0, -45)), yb - 6, f"{P.L_G:g} payload")
    h.cota_h(T((x0, 0, -45)), T((P.CT_X[1], 0, -45)), yb - 15, f"{P.CT_LEN:g} container (S3: 200–250)")
    xp = P.CT_TOP[0] + P.CT_CAP_H
    h.cota_h(T((xp, 0, 45)), T((P.CT_X[1], 0, 45)), yt + 5, f"{P.CT_X[1] - xp:g}")
    h.ax.text(T((xp, 0, 45))[0] - 2, yt + 6.6, "parachute space", fontsize=FS - 1, ha="right", va="bottom", color=NAV)
    xl = T((x0, 0, 0))[0]
    h.cota_v(T((x0, 0, -45)), T((x0, 0, 45)), xl - 6, "Ø90 (S2)")
    h.titulo(T((120, 0, 0))[0], yb - 22, "Launch configuration (section)")
    # --- vista frontal del planeador estibado
    s2 = 0.55
    corte = []
    for sh in est:                                   # corte a media eslora, visto desde la nariz
        try:
            c = sh.intersect(cad.box(100, 400, -400, 400, -400, 400))
            if c.isValid() and c.Volume() > 1e-6:
                corte.append(c)
        except Exception:
            pass
    T3 = h.vista(corte, ((-1, 0, 0), (0, -1, 0)), (212, 49), s2, lw=0.5)     # z hacia arriba
    h.cota_h(T3((0, -P.Y_OUT, P.Z_BOX)), T3((0, P.Y_OUT, P.Z_BOX)), T3((0, 0, P.RB))[1] + 5, f"{en(2 * P.Y_OUT)} box")
    h.cota_v(T3((0, -P.Y_OUT, -P.Z_BOX)), T3((0, -P.Y_OUT, P.Z_BOX + P.T_COVER)), T3((0, -P.RB, 0))[0] + 5,
             f"{en(2 * P.Z_BOX + P.T_COVER)}", dx=1.6)
    h.cota_h(T3((0, -P.RB, 0)), T3((0, P.RB, 0)), T3((0, 0, -P.RB))[1] - 6, f"Ø{2 * P.RB:g} bulkheads", dy=-1.6)
    h.titulo(212, T3((0, 0, -P.RB))[1] - 13, "Payload stowed (mid-length section)")
    h.guardar(f"{out}/lam_dimensiones.png", dpi=220)

    # --- planta del planeador desplegado (figura aparte)
    g = Hoja(150, 128)
    e = 0.3
    Tp = g.vista(des, ((0, 0, 1), (0, 1, 0)), (75, 122), e, lw=0.45)
    A, B, Tt = (P.X_A, P.Y_PIV, 0), (P.X_B, P.Y_PIV, 0), (P.X_B, P.Y_PIV + P.D_AB, 0)
    ybp = Tp(B)[1]
    g.cota_h(Tp((P.X_B, -P.SEMI_SPAN, 0)), Tp((P.X_B, P.SEMI_SPAN, 0)), ybp - 8, f"{en(P.SPAN)} span", dy=-1.6, xt=Tp((0, -P.SEMI_SPAN / 2, 0))[0])
    xr = Tp((0, P.SEMI_SPAN, 0))[0] + 4
    g.cota_v(Tp((P.X_A, P.SEMI_SPAN, 0)), Tp((P.X_B, P.SEMI_SPAN, 0)), xr, f"{en(P.D_AB)} root chord", dx=1.6)
    g.ax.text(Tp(A)[0] + 13, Tp(A)[1] - 6, "45°", fontsize=FS, ha="left", va="center")
    g.ax.add_patch(Arc(Tp(A), 30, 30, theta1=-90, theta2=-45, lw=0.5))
    pa, pt = Tp(A), Tp(Tt)
    g.ax.text(0.5 * (pa[0] + pt[0]) + 5, 0.5 * (pa[1] + pt[1]) + 5, f"LE {en(P.L_LE)}\n(2 × {en(P.L_SEG)})", fontsize=FS - 1,
              ha="left", va="bottom", color=NAV)
    g.ax.text(2, 126, "Payload deployed (plan)", fontsize=FS, ha="left", va="top", weight="bold", color=TEAL)
    g.guardar(f"{out}/lam_planta.png", dpi=220)


def lanzamiento(out, lan):
    h = Hoja(150, 128)
    x0 = P.CT_X[0]
    s = 0.47
    # vertical: boca abajo (como esta en el cohete) -> vista lateral girada: se dibuja con x hacia arriba
    T = h.vista(medio(lan, "y", -1), ((0, 1, 0), (0, 0, 1)), (72, 8), s, ref=(x0, 0, 0), lw=0.5)
    L = lambda p, q, t, ha="left": h.llamada(T(p), q, t, ha=ha)
    xr, xl = T((0, 0, 45))[0], T((0, 0, -45))[0]
    xR, xL = max(xr, xl) + 8, min(xr, xl) - 8
    L((P.CT_X[1] - 8, 0, 25), (xR, T((236, 0, 0))[1]), "Parachute (folded)")
    L((P.CT_TOP[0] + 5, 0, 32), (xR, T((214, 0, 0))[1] - 3), "Ribbed cap (PA12-CF)")
    L((P.CT_TOP[0] - 2, 0, 3), (xL, T((222, 0, 0))[1]), "Bayonet key", ha="right")
    L((209, 0, -19), (xL, T((198, 0, 0))[1]), "C4 collar + sleeve", ha="right")
    L((120, 0, -44), (xL, T((120, 0, 0))[1]), "LW-ASA tube, 2 mm", ha="right")
    L((100, 0, 31), (xR, T((110, 0, 0))[1]), "Glider frame")
    L((4, 0, 34), (xR, T((18, 0, 0))[1]), "C1 on 4 PTFE pads")
    L((x0, 0, -20), (xL, T((-8, 0, 0))[1] + 2), "Open end (exit)", ha="right")
    ys = T((x0, 0, 0))[1]
    h.ax.fill_between([T((0, 0, -47))[0], T((0, 0, 47))[0]], ys - 3.2, ys - 0.4, color="0.75", lw=0)
    h.ax.text(T((0, 0, 0))[0], ys - 4.2, "rocket support", fontsize=FS - 1.5, ha="center", va="top", color="0.35")
    h.guardar(f"{out}/lam_lanzamiento.png", dpi=220)


def ala(out):
    """Despliegue del ala en tres pasos (version de lamina de figs_layout.mecanismo)."""
    import math
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon, Circle
    AZL, VDL = "#2f3192", "#1a8a55"
    fig = plt.figure(figsize=(8.0, 3.05))
    a = fig.add_axes([0, 0, 1, 1])
    a.set_xlim(0, 380)
    a.set_ylim(-19, 131)
    a.set_aspect("equal")
    a.axis("off")
    e, c, seg = 0.5, P.D_AB, P.L_SEG

    def barras(ox, oy, th_deg, titulo, tela=False, manguito=False):
        th = math.radians(th_deg)
        A, B = np.array([0.0, 0.0]), np.array([c, 0.0])
        Tt = B + c * np.array([math.cos(th), math.sin(th)])
        d = np.linalg.norm(Tt - A)
        hh = math.sqrt(max(seg ** 2 - (d / 2) ** 2, 0.0))
        nn = np.array([(Tt - A)[1], -(Tt - A)[0]]) / max(d, 1e-9)
        J = (A + Tt) / 2 + nn * hh
        o = np.array([ox, oy])
        pA, pB, pT, pJ = (o + e * p for p in (A, B, Tt, J))
        a.add_patch(Rectangle((ox - 2, oy - 16), 207 * e, 14, fc="0.9", ec="0.55", lw=0.6))
        a.text(ox + 50, oy - 9, "glider body", fontsize=9, color="0.4", ha="center", va="center")
        if tela:
            a.add_patch(Polygon([pA, pT, pB], closed=True, fc=(1, 0.85, 0.7), ec="none"))
        a.plot(*zip(pA, pJ, pT), color=AZL, lw=2.6, solid_capstyle="round")
        a.plot(*zip(pB, pT), color=VDL, lw=1.8, solid_capstyle="round")
        if manguito:
            u = (pT - pA) / np.linalg.norm(pT - pA)
            a.plot(*zip(pJ - u * 8, pJ + u * 8), color="0.6", lw=6, solid_capstyle="butt", zorder=4)
        for p, nm, dx, dy in ((pA, "A", -6, 2), (pB, "B", 5, 2), (pT, "T", 4, 3), (pJ, "J", -5, 5)):
            a.add_patch(Circle(p, 1.4, fc="white", ec="k", lw=0.8, zorder=5))
            a.text(p[0] + dx, p[1] + dy, nm, fontsize=11, weight="bold", ha="center")
        a.text(ox + 50, oy - 22, titulo, fontsize=FS, weight="bold", ha="center", va="top", color=NAV)
        return pA, pB, pT, pJ
    barras(10, 40, 178.5, "1. Stowed: the wall\nholds the rods")
    barras(130, 40, 138.0, "2. Spring at B opens\nthe strut (1 DOF)")
    pA, pB, pT, pJ = barras(262, 16, 90.0, "", tela=True, manguito=True)
    a.text(pA[0] + 50, -3, "3. Deployed: sleeve locks J", fontsize=FS, weight="bold", ha="center", va="top", color=NAV)
    for x1 in (113, 244):
        a.annotate("", xy=(x1 + 9, 50), xytext=(x1 - 5, 50), arrowprops=dict(arrowstyle="-|>", color="0.3", lw=1.5))
    a.text(pA[0] + 33, pA[1] + 52, f"AJ = JT = {en(seg)}", fontsize=FS - 1, rotation=45, ha="center", color=AZL)
    a.text(pB[0] + 5, pB[1] + 50, f"BT = AB = {en(c)}", fontsize=FS - 1, rotation=90, va="center", color=VDL)
    a.text(8, 128, "Blue: leading-edge rod, two segments (CFRP Ø5/3.5).  Green: strut (CFRP Ø3/2).", fontsize=FS - 1.5,
           color="0.25", va="top")
    fig.savefig(f"{out}/lam_ala.png", dpi=230)
    plt.close(fig)


def main(out):
    lan = piezas("lanzamiento")
    est = piezas("estibado")
    des = piezas("desplegado")
    dimensiones(out, lan, est, des)
    lanzamiento(out, lan)
    ala(out)


if __name__ == "__main__":
    main(sys.argv[1])
