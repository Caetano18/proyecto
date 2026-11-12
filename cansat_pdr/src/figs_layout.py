"""Figuras acotadas y esquemas para las laminas del PDR.  Uso: python3 figs_layout.py <carpeta_figs>"""
import os, sys, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch, Arc, FancyBboxPatch
import cadquery as cq
import params as P
import cad, viz
from hlr import Lienzo
from planos import medio, f1

AZ, VD, NAR, GR = "#2f3192", "#1a8a55", "#e67e22", "#555555"
FS = 8.5


def lanzamiento(out):
    lan = cad.build("lanzamiento")
    todo = [p["shape"] for p in lan if p["grupo"] != "carenado"]
    x0 = P.CT_X[0]
    h = Lienzo(392, 150)
    T = h.vista(medio(todo, "y", 1), "lateral", (26, 82), 1.0, ref=(x0, 0, 0), lw=0.55)
    yb, yt = T((0, 0, -45))[1], T((0, 0, 45))[1]
    h.cota_h(T((x0, 0, -45)), T((P.CT_X[1], 0, -45)), yb - 17, txt=f"{P.CT_LEN:g}  (S3: 200 a 250)", fs=FS)
    h.cota_h(T((0, 0, -45)), T((P.L_G, 0, -45)), yb - 8, txt=f"{P.L_G:g}  planeador", fs=FS)
    h.cota_h(T((x0, 0, 45)), T((P.CT_TOP[0], 0, 45)), yt + 7, txt=f"{P.CT_TOP[0] - x0:g}", fs=FS)
    h.cota_h(T((P.CT_TOP[0], 0, 45)), T((P.CT_TOP[0] + P.CT_CAP_H, 0, 45)), yt + 7, txt=f"{P.CT_CAP_H:g}", fs=FS)
    h.cota_h(T((P.CT_TOP[0] + P.CT_CAP_H, 0, 45)), T((P.CT_X[1], 0, 45)), yt + 7,
             txt=f"{P.CT_X[1] - P.CT_TOP[0] - P.CT_CAP_H:g}", fs=FS)
    xl = T((x0, 0, 0))[0]
    h.cota_v(T((x0, 0, -45)), T((x0, 0, 45)), xl - 8, txt="Ø90  (S2)", fs=FS)
    h.cota_v(T((x0, 0, -43)), T((x0, 0, 43)), xl - 17, txt="Ø86", fs=FS)
    h.eje(T((x0 - 4, 0, 0)), T((P.CT_X[1] + 4, 0, 0)))
    xr = T((P.CT_X[1], 0, 0))[0]
    h.llamada(T((232, 0, 20)), (xr + 3, yt + 12), "Paracaídas (15 m/s)", fs=FS)
    h.llamada(T((216, 0, -30)), (xr + 3, yb - 6), "Tapa nervada", fs=FS)
    h.texto(T((120, 0, 0))[0], yb - 28, "CORTE LONGITUDINAL (plano y = 0)  ·  boca abierta a la izquierda (nariz)", fs=FS, ha="center",
            weight="bold")
    T3 = h.vista(todo, "frontal", (xr + 70, 82), 1.0, lw=0.55)
    h.cota_h(T3((0, -45, 0)), T3((0, 45, 0)), T3((0, 0, 45))[1] + 7, txt="Ø90", fs=FS)
    h.cota_h(T3((0, -P.RB, 0)), T3((0, P.RB, 0)), T3((0, 0, -45))[1] - 8, txt=f"Ø{2 * P.RB:g} planeador", fs=FS, dy=-1.6)
    h.texto(xr + 70, yb - 28, "VISTA DESDE LA BOCA", fs=FS, ha="center", weight="bold")
    h.guardar(f"{out}/lay_lanzamiento.png")


def estibado(out):
    est = cad.build("estibado")
    sh = [p["shape"] for p in est if p["grupo"] != "carenado"]
    h = Lienzo(300, 175)
    T = h.vista(sh, "lateral", (24, 128), 1.0, lw=0.5)
    yb = T((0, 0, -P.RB))[1]
    xs = [0, P.X_C1[1], P.X_C2[0], P.X_C2[1], P.X_C3[0], P.X_C3[1], P.X_C4[0], P.L_G]
    for a, b in zip(xs[:-1], xs[1:]):
        h.cota_h(T((a, 0, -P.RB)), T((b, 0, -P.RB)), yb - 6, txt=f"{b - a:g}", fs=7)
    h.cota_h(T((0, 0, -P.RB)), T((P.L_G, 0, -P.RB)), yb - 14, valor=P.L_G, fs=FS)
    h.cota_v(T((0, 0, -P.RB)), T((0, 0, P.RB)), T((0, 0, 0))[0] - 8, txt=f"Ø{2 * P.RB:g}", fs=FS)
    for nm, x in (("C1", 4), ("C2", 62), ("C3", 140), ("C4", 203)):
        h.texto(T((x, 0, 0))[0], T((0, 0, P.RB))[1] + 2.5, nm, fs=FS, ha="center", weight="bold", color=AZ)
    h.texto(T((103, 0, 0))[0], yb - 22, "VISTA LATERAL", fs=FS, ha="center", weight="bold")
    T2 = h.vista(sh, "superior", (24, 42), 1.0, lw=0.5)
    yt = T2((0, P.RB, 0))[1]
    h.cota_h(T2((P.X_A, P.RB, 0)), T2((P.X_B, P.RB, 0)), yt + 5, txt=f"{f1(P.D_AB)}  entre pivotes A y B", fs=FS)
    h.cota_v(T2((0, -P.Y_OUT, 0)), T2((0, P.Y_OUT, 0)), T2((0, 0, 0))[0] - 8, txt=f1(2 * P.Y_OUT), fs=FS)
    h.texto(T2((103, 0, 0))[0], T2((0, -P.RB, 0))[1] - 6, "VISTA SUPERIOR", fs=FS, ha="center", weight="bold")
    T3 = h.vista(sh, "frontal", (258, 128), 1.0, lw=0.5)
    h.cota_h(T3((0, -P.Y_PIV, 0)), T3((0, P.Y_PIV, 0)), T3((0, 0, P.RB))[1] + 5, txt=f"{2 * P.Y_PIV:g}", fs=FS)
    h.cota_v(T3((0, P.RB, -P.Z_BOX)), T3((0, P.RB, P.Z_BOX + P.T_COVER)), T3((0, P.RB, 0))[0] + 6,
             txt=f1(2 * P.Z_BOX + P.T_COVER), fs=FS, dx=1.4)
    h.texto(258, yb - 22, "VISTA FRONTAL", fs=FS, ha="center", weight="bold")
    h.guardar(f"{out}/lay_estibado.png")


def desplegado(out):
    des = cad.build("desplegado")
    sh = [p["shape"] for p in des if p["grupo"] != "carenado"]
    e = 0.5
    h = Lienzo(280, 205)
    T = h.vista(sh, ((0, 0, 1), (0, 1, 0)), (140, 190), e, lw=0.5)
    A, B, Tp = (P.X_A, P.Y_PIV, 0), (P.X_B, P.Y_PIV, 0), (P.X_B, P.Y_PIV + P.D_AB, 0)
    yb = T(B)[1]
    h.cota_h(T((P.X_B, -P.SEMI_SPAN, 0)), T((P.X_B, P.SEMI_SPAN, 0)), yb - 17, txt=f"{f1(P.SPAN)}  envergadura", fs=FS, dy=-1.8)
    h.cota_h(T(B), T(Tp), yb - 8, txt=f"{f1(P.L_TE)}  tirante", fs=FS, dy=-1.8)
    h.cota_al(T(A), T(Tp), 9, f"{f1(P.L_LE)}  borde de ataque (2 × {f1(P.L_SEG)})", fs=FS)
    xr = T((0, P.SEMI_SPAN, 0))[0] + 10
    h.cota_v(T((P.X_A, P.SEMI_SPAN, 0)), T((P.X_B, P.SEMI_SPAN, 0)), xr, txt=f"{f1(P.D_AB)}  cuerda de raíz", fs=FS, dx=1.6)
    xl = T((0, -P.SEMI_SPAN, 0))[0] - 10
    h.cota_v(T((0, -P.SEMI_SPAN, 0)), T((336, -P.SEMI_SPAN, 0)), xl, txt="336  largo en vuelo", fs=FS)
    aa = T(A)
    h.ax.add_patch(Arc(aa, 40, 40, theta1=-90, theta2=-45, lw=0.4))
    h.texto(aa[0] + 7, aa[1] - 26, "45°", fs=FS)
    for nm, p, dx, dy in (("A", A, -5, 3), ("J", P.P_J, 5, 3), ("T", Tp, 4, 2), ("B", B, 5, -6)):
        q = T(p)
        h.texto(q[0] + dx, q[1] + dy, nm, fs=10, weight="bold", color=AZ, ha="center")
    h.guardar(f"{out}/lay_desplegado.png")


def mecanismo(out):
    fig = plt.figure(figsize=(11.4, 4.3))
    a = fig.add_axes([0, 0, 1, 1])
    a.set_xlim(0, 380)
    a.set_ylim(0, 143)
    a.set_aspect("equal")
    a.axis("off")
    e, c, seg = 0.5, P.D_AB, P.L_SEG

    def barras(ox, oy, th_deg, titulo, tela=False, manguito=False):
        th = math.radians(th_deg)
        A, B = np.array([0.0, 0.0]), np.array([c, 0.0])
        Tt = B + c * np.array([math.cos(th), math.sin(th)])
        d = np.linalg.norm(Tt - A)
        hh = math.sqrt(max(seg ** 2 - (d / 2) ** 2, 0.0))
        n = np.array([(Tt - A)[1], -(Tt - A)[0]]) / max(d, 1e-9)
        J = (A + Tt) / 2 + n * hh
        o = np.array([ox, oy])
        pA, pB, pT, pJ = (o + e * p for p in (A, B, Tt, J))
        a.add_patch(Rectangle((ox - 2, oy - 20), 207 * e, 18, fc="0.9", ec="0.55", lw=0.6))
        a.text(ox + 50, oy - 11, "cuerpo del planeador", fontsize=7.5, color="0.4", ha="center", va="center")
        if tela:
            a.add_patch(Polygon([pA, pT, pB], closed=True, fc=(1, 0.85, 0.7), ec="none"))
        a.plot(*zip(pA, pJ, pT), color=AZ, lw=2.6, solid_capstyle="round")
        a.plot(*zip(pB, pT), color=VD, lw=1.8, solid_capstyle="round")
        if manguito:
            u = (pT - pA) / np.linalg.norm(pT - pA)
            a.plot(*zip(pJ - u * 8, pJ + u * 8), color="0.6", lw=6, solid_capstyle="butt", zorder=4)
        for p, nm, dx, dy in ((pA, "A", -5, 2), (pB, "B", 4, 2), (pT, "T", 3, 4), (pJ, "J", -4, 5)):
            a.add_patch(Circle(p, 1.3, fc="white", ec="k", lw=0.8, zorder=5))
            a.text(p[0] + dx, p[1] + dy, nm, fontsize=10, weight="bold", ha="center")
        a.text(ox + 50, oy - 28, titulo, fontsize=9.5, weight="bold", ha="center")
        return pA, pB, pT, pJ
    barras(10, 60, 178.5, "1. Estibada: la pared del contenedor\nretiene las varillas")
    barras(128, 60, 138.0, "2. Apertura: resorte de torsión en B\n(un solo grado de libertad)")
    pA, pB, pT, pJ = barras(262, 36, 90.0, "3. Desplegada: A-J-T alineados,\nel manguito cubre y traba J", tela=True, manguito=True)
    a.annotate("", xy=(118, 70), xytext=(104, 70), arrowprops=dict(arrowstyle="-|>", color="0.3", lw=1.5))
    a.annotate("", xy=(252, 70), xytext=(238, 70), arrowprops=dict(arrowstyle="-|>", color="0.3", lw=1.5))
    a.text(pA[0] + 40, pA[1] + 50, f"AJ = JT = {f1(seg)}", fontsize=8.5, rotation=45, ha="center", color=AZ)
    a.text(pB[0] + 4, pB[1] + 50, f"BT = {f1(c)}", fontsize=8.5, rotation=90, va="center", color=VD)
    a.text(pA[0] + 50, pA[1] - 4.5, f"AB = {f1(c)}", fontsize=8.5, ha="center", va="top")
    a.text(10, 136, "Azul: varilla de borde de ataque en dos tramos (tubo CFRP Ø5/3,5).   Verde: tirante de borde de fuga (tubo CFRP Ø3/2).",
           fontsize=8.5, color="0.25")
    fig.savefig(f"{out}/ala_mecanismo.png", dpi=240)
    plt.close(fig)


def conops(out):
    fig = plt.figure(figsize=(11.6, 4.6))
    a = fig.add_axes([0, 0, 1, 1])
    a.set_xlim(0, 116)
    a.set_ylim(0, 46)
    a.axis("off")
    t = np.linspace(0, 1, 200)
    # trayectoria
    x1 = 6 + 22 * t
    y1 = 5 + 33 * np.sin(np.pi / 2 * t)
    a.plot(x1, y1, color="0.6", lw=1.2, ls="--")
    xs = [28, 36, 44]
    ys = [38, 33.5, 29]
    a.plot(xs, ys, color=AZ, lw=1.6)
    x3 = np.linspace(44, 106, 100)
    y3 = 29 - 24.5 * (x3 - 44) / 62 + 1.2 * np.sin((x3 - 44) / 62 * 6 * np.pi)
    a.plot(x3, y3, color=NAR, lw=1.6)
    a.plot([0, 116], [4.2, 4.2], color="0.3", lw=1)

    def paso(x, y, n, titulo, texto, dx=0, dy=0, ancho=21):
        a.add_patch(Circle((x, y), 1.5, fc=AZ, ec="none", zorder=5))
        a.text(x, y, str(n), color="w", fontsize=9, weight="bold", ha="center", va="center", zorder=6)
        a.text(x + dx, y + dy, titulo, fontsize=8.6, weight="bold", va="top", color=AZ)
        a.text(x + dx, y + dy - 2.2, texto, fontsize=7.4, va="top", color="0.15", linespacing=1.25)
    paso(8, 7, 1, "Lanzamiento", "CanSat dentro del fuselaje.\nCarga axial de hasta 15 G:\nplaneador colgado de la llave.", 2.4, 13.5)
    paso(28, 38, 2, "Eyección (apogeo)", "La carga de expulsión saca el\ncontenedor. Choque de 30 G.", -9, 7.5)
    paso(36, 33.5, 3, "Paracaídas: 15 ± 3 m/s", "El contenedor cuelga de la brida\nde 3 puntos; el planeador va\nadentro, nariz abajo, alas retenidas\npor la pared (S7).", 2.6, 10.5)
    paso(44, 29, 4, "80 % de la altitud máxima", "El servo gira la llave 90°:\nel planeador cae por la boca.", -25, -1.5)
    paso(57, 23.8, 5, "Despliegue pasivo", "Al salir del cilindro los resortes\nabren el ala (4 barras) y el manguito\nla traba. Sale el botalón de cola.", 1.5, 12.5)
    paso(80, 16.3, 6, "Planeo en espiral: 5 ± 3 m/s", "Ala delta de membrana, 394 cm².\nCámaras a cenit y nadir, celda solar\nhacia arriba.", 1.5, 11.8)
    paso(106, 4.6, 7, "Aterrizaje", "Baliza sonora.\nContenedor con\nparacaídas aparte.", -9.5, 12.5)
    fig.savefig(f"{out}/conops.png", dpi=240)
    plt.close(fig)


def opcion_a(out):
    """Render ilustrativo de la alternativa descartada: cuerpo integral con ranuras laterales."""
    des = cad.build("desplegado")
    tubo = cad.disc(0, P.L_G, 45).cut(cad.disc(-1, P.L_G + 1, 43))
    for s in (1, -1):
        ya, yb = sorted((s * 30, s * 50))
        tubo = tubo.cut(cad.box(2, P.L_G - 2, ya, yb, -11, 5))
    partes = [p for p in des if p["grupo"] in ("ala", "cola")]
    partes.append(dict(nombre="cuerpo", shape=tubo, mat="PETG", color=(0.93, 0.93, 0.9), grupo="x", masa=0))
    partes.append(dict(nombre="t1", shape=cad.disc(0, 2, 45), mat="PETG", color=(0.93, 0.93, 0.9), grupo="x", masa=0))
    viz.render(partes, f"{out}/opcion_a.png", ((-1.0, -1.1, 0.85), (0, 0, 1)), (2000, 1500), 1.3)


def main(out):
    lanzamiento(out)
    estibado(out)
    desplegado(out)
    mecanismo(out)
    conops(out)
    opcion_a(out)
    print("figuras de layout ok")


if __name__ == "__main__":
    main(sys.argv[1])
