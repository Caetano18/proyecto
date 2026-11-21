"""Figuras en ingles para las laminas del PDR (diseno v2, opcion B regulable): cotas, paracaidas y planeo.
Uso: python3 figs_descenso_v2.py <carpeta de figuras>
"""
import os
import sys
import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon, FancyArrowPatch, Arc
import cg_v2 as CG

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
AZ, NA, VE, AM = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
TX, TX2, GR = "#0b0b0b", "#52514e", "#e6e6e6"
W = 0.500 * 9.80665
RHO_SITIO, RHO_MAR = 1.15, 1.225
CDA_CIL = 0.86 * math.pi * 0.09 ** 2 / 4


L_DER, L_IZQ = 350.0, 310.0      # 185 + punteras plegables de 165 / 125: lobulo izquierdo mas chico (viraje)
ANG = 60.0                        # flecha fija desde la quilla


def lobulo(L, ang=ANG, keel=190.0, ypiv=35.0, x0=14.0):
    """Area en planta de un lobulo (de la quilla al larguero) [m2]."""
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    pts = [(x0, 0.0), (x0, ypiv), (x0 + L * d[0], ypiv + L * d[1]), (x0 + keel, 0.0)]
    x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 1e6


def area_asim():
    return lobulo(L_DER) + lobulo(L_IZQ)


def area_vela(L, ang=ANG, keel=190.0, ypiv=35.0, x0=14.0):
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    pts = [(x0, ypiv), (x0 + L * d[0], ypiv + L * d[1]), (x0 + keel, 0.0), (x0 + L * d[0], -ypiv - L * d[1]), (x0, -ypiv)]
    x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 1e6, 2 * (ypiv + L * d[1])


R_ESPIRAL = 50.0          # radio de la espiral estimado por el equipo [m]


def vz(f, rho, S, R=R_ESPIRAL, solo_v=False):
    """Descenso en una espiral de radio R: el alabeo sale de R = (V cos g)^2 / (g tan phi)."""
    phi = math.radians(6.0)
    for _ in range(30):
        v_, g_ = _vz_phi(f, rho, S, phi)
        phi = math.atan((v_ * math.cos(g_)) ** 2 / (9.80665 * R))
    v_, g_ = _vz_phi(f, rho, S, phi)
    return (v_ * math.sin(g_), math.degrees(phi), v_) if solo_v else v_ * math.sin(g_)


NU = 1.6e-5            # viscosidad cinematica del aire en el sitio [m2/s]
K_TELA = 1.15          # area de tela / area en planta (embolsamiento de la vela)
CD_MEMB = 0.030        # tolerancia de forma de la membrana (embolsamiento y flameo del borde de fuga)
D_LARG, CD_CIL_LARG = 0.005, 1.0   # larguero dentro de la vaina [m] y Cd de flujo cruzado (Re_d ~ 3000)


def envergadura():
    return 2 * 35.0 + (L_DER + L_IZQ) * math.sin(math.radians(ANG))


def cd_parasito(V, S):
    """Arrastre parasito de la vela referido a S: rozamiento del ripstop (dos caras, placa plana turbulenta:
    conservador por la rugosidad del tejido) + forma de los largueros (flujo cruzado) + tolerancia de la membrana."""
    c = S / (envergadura() / 1000.0)                      # cuerda media geometrica [m]
    re = max(V * c / NU, 1e3)
    cf = 0.074 * re ** -0.2
    cd_f = cf * 2 * K_TELA
    cd_l = CD_CIL_LARG * D_LARG * (L_DER + L_IZQ) / 1000.0 * math.sin(math.radians(ANG)) ** 3 / S
    return cd_f, cd_l, CD_MEMB, re


def _vz_phi(f, rho, S, phi, detalle=False):
    """Analogia de succion del borde de ataque (Polhamus): CL = Kp sen a cos2 a + Kv cos a sen2 a; sin succion en el
    borde de ataque, el arrastre debido a la sustentacion es CL tan a."""
    a, Kp, Kv = math.radians(28), 2.2, math.pi
    CL = Kp * math.sin(a) * math.cos(a) ** 2 + f * Kv * math.cos(a) * math.sin(a) ** 2
    V = 10.0
    for _ in range(40):                                   # el rozamiento depende de V (Reynolds)
        cd_f, cd_l, cd_m, re = cd_parasito(V, S)
        CD = cd_f + cd_l + cd_m + CDA_CIL / S + CL * math.tan(a)
        g = math.atan(CD / (CL * math.cos(phi)))
        V = math.sqrt(2 * W * math.cos(g) / (rho * S * CL * math.cos(phi)))
    if detalle:
        return dict(CL=CL, cd_roz=cd_f, cd_largueros=cd_l, cd_membrana=cd_m, cd_cuerpo=CDA_CIL / S,
                    cd_sustentacion=CL * math.tan(a), CD=CD, Re=re, V=V)
    return V, g


def estilo(ax):
    ax.grid(color=GR, lw=0.6)
    ax.set_axisbelow(True)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)


def cota(ax, p0, p1, txt, off=(0, 0), rot=0, fs=9, col=TX, z=2, fondo="white"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<->", mutation_scale=9, color=col, lw=0.9, zorder=z))
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], txt, ha="center", va="center", fontsize=fs,
            rotation=rot, color=col, bbox=dict(fc=fondo, ec="none", pad=0.6), zorder=z + 1)


def dimensiones(out):
    fig = plt.figure(figsize=(11.0, 5.2))
    # ---------------- corte lateral con estaciones
    ax = fig.add_axes([0.02, 0.08, 0.36, 0.86])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((-45, 0), 90, 240, fc="#eef2f8", ec=TX, lw=1.2))
    est = [("M1", 0, 4), ("M2", CG.NOM2, CG.NOM2 + 4), ("M3", CG.NOM3, CG.NOM3 + 4), ("M4", 216, 220), ("M5 lid", 236, 240)]
    for n, a, b in est:
        ax.add_patch(Rectangle((-43, a), 86, b - a, fc="#6b7280", ec="none"))
        ax.text(47, (a + b) / 2, f"{n}  x = {a:.0f}", fontsize=8.5, va="center", color=TX)
    for y in (-23.3, 23.3):
        ax.plot([y, y], [0.4, 226], color=AM, lw=1.4)
    ax.annotate("Threaded M3\nrods (× 4)", xy=(23.3, 152), xytext=(50, 152), fontsize=8.5, va="center", color=TX,
                arrowprops=dict(arrowstyle="-", color=AM, lw=1.0))
    bah = [("Bay 1: nadir camera, beacon,\nwing servo, spar pivots", 4, CG.NOM2 - 46), ("Bay 2: 2 × 18650 pack\n(hangs from M2)", CG.NOM2 - 46, CG.NOM2),
           ("Bay 3: avionics\n(hangs from M3)", CG.NOM2 + 4, CG.NOM3), ("Bay 4: zenith camera,\nlid and parachute servos", CG.NOM3 + 4, 216),
           ("Bay 5: parachute cup", 220, 236)]
    for t, a, b in bah:
        ax.text(0, (a + b) / 2, t, ha="center", va="center", fontsize=7.6, color=TX2, zorder=5,
                bbox=dict(fc="#eef2f8", ec="none", pad=0.8))
    cota(ax, (-55, 0), (-55, 240), "240", off=(-7, 0), rot=90)
    cota(ax, (-45, -9), (45, -9), "Ø90 (wall 2 mm PETG)", off=(0, -6))
    ax.set_xlim(-75, 110)
    ax.set_ylim(-22, 250)
    ax.set_title("Stowed CanSat (section, nominal stations)", fontsize=10.5, weight="bold")
    # ---------------- planta desplegada (lobulo izquierdo mas chico)
    ax = fig.add_axes([0.42, 0.08, 0.56, 0.86])
    ax.set_aspect("equal")
    ax.axis("off")
    ang = ANG
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    tD = (14 + L_DER * d[0], 35 + L_DER * d[1])        # derecha (+y)
    tI = (14 + L_IZQ * d[0], 35 + L_IZQ * d[1])        # izquierda (-y)
    # vista desde arriba con el apice arriba: derecha del vuelo a la derecha de la figura
    vela = [(14, 35), tD, (204, 0), (tI[0], -tI[1]), (14, -35)]
    ax.add_patch(Polygon([(p[1], -p[0]) for p in vela], closed=True, fc="#fde3d3", ec=NA, lw=1.2))
    ax.add_patch(Rectangle((-45, -240), 90, 240, fc="#eef2f8", ec=TX, lw=1.0, zorder=3))
    ax.plot([35, tD[1]], [-14, -tD[0]], color=TX, lw=2.4, zorder=4)
    ax.plot([-35, -tI[1]], [-14, -tI[0]], color=TX, lw=2.4, zorder=4)
    ax.plot([0, 0], [-14, -204], color=TX, lw=1.4, ls="--", zorder=4)
    b = tD[1] + tI[1]
    cota(ax, (-tI[1], 14), (tD[1], 14), f"span {b:.0f} mm", off=(0, 9))
    for xx, tt in ((tD[1], tD), (-tI[1], tI)):
        ax.plot([xx, xx], [-tt[0], 14], color=TX2, lw=0.6, ls=":")
    cota(ax, (-24, -14), (-24, -204), "keel 190", rot=90, z=5, fondo="#eef2f8")
    ax.plot([35, 35], [-14, -84], color=TX2, lw=0.7, ls=":", zorder=5)
    ax.add_patch(Arc((35, -14), 110, 110, theta1=-90, theta2=-90 + ang, color=TX, lw=1.0, zorder=5))
    am = math.radians(-90 + ang / 2)
    ax.text(35 + 72 * math.cos(am), -14 + 72 * math.sin(am), f"{ang:.0f}°", fontsize=9, ha="center", va="center",
            color=TX, zorder=6)
    ax.text(tD[1] - 20, -tD[0] - 32, f"right spar {L_DER:.0f} mm\n(185 + {L_DER - 185:.0f} folding tip)", fontsize=8.4, ha="center", va="top", color=TX)
    ax.text(-tI[1], -tI[0] - 30, f"left spar {L_IZQ:.0f} mm\n(185 + {L_IZQ - 185:.0f} folding tip)", fontsize=8.4, ha="center", va="top", color=TX)
    aD, aI = lobulo(L_DER), lobulo(L_IZQ)
    for sg, tt, aa in ((1, tD, aD), (-1, tI, aI)):           # area en el centroide de cada lobulo (fuera del cuerpo)
        q = [(sg * 35, -14), (sg * tt[1], -tt[0]), (sg * 45, -204 + 4), (sg * 45, -14)]
        cx, cy = sum(v[0] for v in q) / 4, sum(v[1] for v in q) / 4
        ax.text(cx, cy, f"{aa * 1e4:.0f} cm²", ha="center", va="center", fontsize=9, weight="bold", color=NA, zorder=6)
    ax.text(0, -247, "body Ø90 × 240", ha="center", va="top", fontsize=8.6, color=TX2, zorder=5)
    ax.text(0, 52, f"Sail area {(aD + aI):.3f} m²; left lobe {100 * (1 - aI / aD):.0f} % smaller → left turn",
            ha="center", fontsize=9.5, weight="bold", color=TX)
    ax.set_xlim(-390, 390)
    ax.set_ylim(-275, 70)
    ax.set_title("Deployed Rogallo glider (plan view, nose up)", fontsize=10.5, weight="bold", pad=14)
    fig.savefig(f"{out}/v2_dimensiones_en.png", dpi=220)
    plt.close(fig)


def paracaidas(out):
    fig = plt.figure(figsize=(9.0, 5.0))
    # esquemas
    ax = fig.add_axes([0.01, 0.06, 0.40, 0.86])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((-150, 0), 113, fc="#fde3d3", ec=NA, lw=1.3))
    ax.add_patch(Circle((-150, 0), 20, fc="white", ec=NA, lw=1.0))
    cota(ax, (-263, -128), (-37, -128), "Ø226", off=(0, -10))
    ax.annotate("vent Ø40", xy=(-150, -20), xytext=(-150, -62), fontsize=8.5, ha="center", va="center",
                arrowprops=dict(arrowstyle="-", color=TX, lw=0.8))
    ax.text(-150, 1.5 * 94.1 + 18, "1A: flat circular\nwith vent", ha="center", va="bottom", fontsize=9.5, weight="bold")
    w = 94.1
    for cx, cy in ((0, 0), (w, 0), (-w, 0), (0, w), (0, -w)):
        ax.add_patch(Rectangle((150 + cx - w / 2, cy - w / 2), w, w, fc="#dbe8f7", ec=AZ, lw=1.1))
    cota(ax, (150 - 1.5 * w, -1.5 * w - 14), (150 + 1.5 * w, -1.5 * w - 14), "282", off=(0, -10))
    ax.text(150, 1.5 * w + 18, "1B: cruciform\n(L/W = 3)", ha="center", va="bottom", fontsize=9.5, weight="bold")
    ax.set_xlim(-275, 300)
    ax.set_ylim(-180, 215)
    # velocidad contra area
    ax = fig.add_axes([0.50, 0.15, 0.47, 0.74])
    S0 = np.linspace(0.025, 0.06, 200)
    for cd, col, lab in ((0.78, NA, "1A flat with vent, Cd0 = 0.78"), (0.68, AZ, "1B cruciform, Cd0 = 0.68")):
        v = np.sqrt(2 * W / (RHO_SITIO * (cd * S0 + CDA_CIL)))
        ax.plot(S0 * 1e4, v, color=col, lw=2, label=lab)
    ax.axhspan(12, 18, color="#e8f1fb", lw=0)
    ax.text(253, 12.15, "C3: 15 ± 3 m/s", fontsize=8.8, color=TX2, va="bottom")
    for s0, cd, col in ((0.03862, 0.78, NA), (0.04430, 0.68, AZ)):
        v = math.sqrt(2 * W / (RHO_SITIO * (cd * s0 + CDA_CIL)))
        ax.plot(s0 * 1e4, v, "o", ms=8, color=col, mec="white", mew=1.5, zorder=5)
        ax.annotate(f"{v:.1f} m/s", (s0 * 1e4, v), xytext=(-10, -16) if col == NA else (8, 8), textcoords="offset points",
                    fontsize=8.8, ha="right" if col == NA else "left")
    ax.set_xlabel("Canopy area S0 [cm²]")
    ax.set_ylabel("Descent rate at the site [m/s]")
    ax.set_title("Phase 1, 500 g, site density 1.15 kg/m³ (body drag included)", fontsize=10)
    ax.legend(loc="upper right", fontsize=8.8, frameon=False)
    estilo(ax)
    fig.savefig(f"{out}/v2_paracaidas_en.png", dpi=220)
    plt.close(fig)


def vz_placa(S, a_deg=28.0, rho=RHO_SITIO):
    """Cota conservadora: placa plana con fuerza normal (Hoerner; ajuste de alargamiento finito), sin sustentacion de
    vortice.  Mismo rozamiento, largueros, membrana y cuerpo que el modelo principal."""
    AR = (envergadura() / 1000.0) ** 2 / S
    a = math.radians(a_deg)
    cd90 = 1.98 - 0.81 * (1 - math.exp(-20 / AR))
    CN = cd90 * math.sin(a) / (0.56 + 0.44 * math.sin(a))
    CL, CDn = CN * math.cos(a), CN * math.sin(a)
    V = 10.0
    for _ in range(40):
        cd_f, cd_l, cd_m, _ = cd_parasito(V, S)
        CD = CDn + cd_f + cd_l + cd_m + CDA_CIL / S
        g = math.atan(CD / CL)
        V = math.sqrt(2 * W * math.cos(g) / (rho * S * CL))
    return V * math.sin(g)


def planeo(out):
    S = area_asim()
    f = np.linspace(0.2, 1.0, 100)
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.axhspan(2, 8, color="#e8f1fb", lw=0)
    ax.text(0.205, 2.15, "C4: 5 ± 3 m/s", fontsize=8.8, color=TX2, va="bottom")
    ax.plot(f, [vz(x, RHO_SITIO, S) for x in f], color=NA, lw=2.2, label=f"vortex-lift model (Polhamus form), sail {S:.3f} m², spiral {R_ESPIRAL:.0f} m")
    for fr in (1.0, 0.5, 0.3):
        v = vz(fr, RHO_SITIO, S)
        ax.plot(fr, v, "o", ms=7, color=NA, mec="white", mew=1.5, zorder=5)
        ax.annotate(f"{v:.1f} m/s", (fr, v), xytext=(4, 7), textcoords="offset points", fontsize=8.8)
    ax.set_xlim(0.2, 1.02)
    ax.set_ylim(0, 10)
    ax.set_xlabel("Fraction of the vortex lift developed by the sail, f")
    ax.set_ylabel("Glide descent rate at the site [m/s]")
    vp = vz_placa(S)
    ax.axhline(vp, color=TX2, lw=1.4, ls="--", label="flat plate, no vortex lift (conservative bound)")
    ax.annotate(f"{vp:.1f} m/s", (0.205, vp), xytext=(0, 5), textcoords="offset points", fontsize=8.8, color=TX2)
    ax.legend(loc="lower left", fontsize=8.8, frameon=False)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(f"{out}/v2_planeo_en.png", dpi=220)
    plt.close(fig)
    vz5, phi5, v5 = vz(0.5, RHO_SITIO, S, solo_v=True)
    det = _vz_phi(0.5, RHO_SITIO, S, math.radians(phi5), detalle=True)
    return dict(S=S, lob_der=lobulo(L_DER), lob_izq=lobulo(L_IZQ), R=R_ESPIRAL, phi_deg=phi5, V=v5, arrastre=det,
                vz_placa=vz_placa(S), AR=(envergadura() / 1000.0) ** 2 / S, carga_alar=W / 9.80665 / S,
                vz={str(fr): vz(fr, RHO_SITIO, S) for fr in (1.0, 0.5, 0.3)},
                vueltas_s=2 * math.pi * R_ESPIRAL / (v5 * math.cos(math.atan(vz5 / v5))))


if __name__ == "__main__":
    o = sys.argv[1]
    dimensiones(o)
    paracaidas(o)
    D = planeo(o)
    json.dump(D, open(os.path.join(o, "..", "fea", "descenso_v2.json"), "w"), indent=1)
    print(json.dumps(D, indent=1))
