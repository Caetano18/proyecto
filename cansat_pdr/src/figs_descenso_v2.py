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
from matplotlib.patches import Circle, Rectangle, Polygon, FancyArrowPatch
import cg_v2 as CG

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
AZ, NA, VE, AM = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
TX, TX2, GR = "#0b0b0b", "#52514e", "#e6e6e6"
W = 0.500 * 9.80665
RHO_SITIO, RHO_MAR = 1.15, 1.225
CDA_CIL = 0.86 * math.pi * 0.09 ** 2 / 4


def area_vela(L, ang=52.0, keel=190.0, ypiv=35.0, x0=14.0):
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    pts = [(x0, ypiv), (x0 + L * d[0], ypiv + L * d[1]), (x0 + keel, 0.0), (x0 + L * d[0], -ypiv - L * d[1]), (x0, -ypiv)]
    x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 1e6, 2 * (ypiv + L * d[1])


def vz(f, rho, S):
    phi, a, Kp, Kv, CD0 = math.radians(25), math.radians(28), 2.2, math.pi, 0.080
    CL = Kp * math.sin(a) * math.cos(a) ** 2 + f * Kv * math.cos(a) * math.sin(a) ** 2
    CD = CD0 + CDA_CIL / S + CL * math.tan(a)
    g = math.atan(CD / (CL * math.cos(phi)))
    V = math.sqrt(2 * W * math.cos(g) / (rho * S * CL * math.cos(phi)))
    return V * math.sin(g)


def estilo(ax):
    ax.grid(color=GR, lw=0.6)
    ax.set_axisbelow(True)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)


def cota(ax, p0, p1, txt, off=(0, 0), rot=0, fs=9, col=TX):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<->", mutation_scale=9, color=col, lw=0.9))
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], txt, ha="center", va="center", fontsize=fs,
            rotation=rot, color=col, bbox=dict(fc="white", ec="none", pad=0.6))


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
    bah = [("Bay 1: nadir camera, beacon,\nspar pivots", 4, CG.NOM2 - 46), ("Bay 2: 2 × 18650 pack\n(hangs from M2)", CG.NOM2 - 46, CG.NOM2),
           ("Bay 3: avionics\n(hangs from M3)", CG.NOM2 + 4, CG.NOM3), ("Bay 4: zenith camera,\nnichrome capsule", CG.NOM3 + 4, 216),
           ("Bay 5: parachute cup", 220, 236)]
    for t, a, b in bah:
        ax.text(0, (a + b) / 2, t, ha="center", va="center", fontsize=7.6, color=TX2)
    cota(ax, (-55, 0), (-55, 240), "240", off=(-7, 0), rot=90)
    cota(ax, (-45, -9), (45, -9), "Ø90 (wall 2 mm PETG)", off=(0, -6))
    ax.set_xlim(-75, 110)
    ax.set_ylim(-22, 250)
    ax.set_title("Stowed CanSat (section, nominal stations)", fontsize=10.5, weight="bold")
    # ---------------- planta desplegada
    ax = fig.add_axes([0.42, 0.08, 0.56, 0.86])
    ax.set_aspect("equal")
    ax.axis("off")
    L, ang = 225.0, 52.0
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    tip = (14 + L * d[0], 35 + L * d[1])
    vela = [(14, 35), tip, (204, 0), (tip[0], -tip[1]), (14, -35)]
    ax.add_patch(Polygon([(p[1], -p[0]) for p in vela], closed=True, fc="#fde3d3", ec=NA, lw=1.2))
    ax.add_patch(Rectangle((-45, -240), 90, 240, fc="#eef2f8", ec=TX, lw=1.0, zorder=3))
    for s in (1, -1):
        ax.plot([s * 35, s * tip[1]], [-14, -tip[0]], color=TX, lw=2.4, zorder=4)
    ax.plot([0, 0], [-14, -204], color=TX, lw=1.4, ls="--", zorder=4)
    S, b = area_vela(L, ang)
    cota(ax, (-tip[1], 14), (tip[1], 14), f"span {b:.0f} mm", off=(0, 9))
    for s_ in (1, -1):
        ax.plot([s_ * tip[1], s_ * tip[1]], [-tip[0], 14], color=TX2, lw=0.6, ls=":")
    cota(ax, (60, -14), (60, -204), "keel 190", off=(14, 0), rot=90)
    rot = math.degrees(math.atan2(L * d[0], L * d[1]))
    ax.text(-35 - 0.5 * L * d[1] - 18, -14 - 0.5 * L * d[0] + 22, f"spar CF Ø4/2, {L:.0f} mm\n(185 + 40 folding tip)",
            fontsize=8.6, ha="center", va="center", rotation=rot, color=TX)
    ax.text(tip[1] * 0.62, -60, f"{ang:.0f}° from the keel", fontsize=8.6, color=TX)
    ax.text(0, -232, "body Ø90 × 240", ha="center", fontsize=8.6, color=TX2, zorder=5)
    ax.text(0, 52, f"Planform area {S:.3f} m² (v2 uses 0.067 m²)", ha="center", fontsize=9.5, weight="bold", color=TX)
    ax.set_xlim(-250, 250)
    ax.set_ylim(-260, 70)
    ax.set_title("Deployed Rogallo glider (plan view)", fontsize=10.5, weight="bold", pad=14)
    fig.savefig(f"{out}/v2_dimensiones_en.png", dpi=220)
    plt.close(fig)


def paracaidas(out):
    fig = plt.figure(figsize=(11.0, 4.4))
    # esquemas
    ax = fig.add_axes([0.01, 0.06, 0.40, 0.86])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((-150, 0), 113, fc="#fde3d3", ec=NA, lw=1.3))
    ax.add_patch(Circle((-150, 0), 20, fc="white", ec=NA, lw=1.0))
    cota(ax, (-263, -128), (-37, -128), "Ø226", off=(0, -10))
    ax.text(-150, 0, "vent\nØ40", ha="center", va="center", fontsize=8)
    ax.text(-150, 132, "1A: flat circular with vent", ha="center", fontsize=9.5, weight="bold")
    w = 94.1
    for cx, cy in ((0, 0), (w, 0), (-w, 0), (0, w), (0, -w)):
        ax.add_patch(Rectangle((150 + cx - w / 2, cy - w / 2), w, w, fc="#dbe8f7", ec=AZ, lw=1.1))
    cota(ax, (150 - 1.5 * w, -1.5 * w - 14), (150 + 1.5 * w, -1.5 * w - 14), "282", off=(0, -10))
    ax.text(150, 1.5 * w + 18, "1B: cruciform (L/W = 3)", ha="center", fontsize=9.5, weight="bold")
    ax.set_xlim(-275, 300)
    ax.set_ylim(-180, 175)
    # velocidad contra area
    ax = fig.add_axes([0.50, 0.15, 0.47, 0.74])
    S0 = np.linspace(0.025, 0.06, 200)
    for cd, col, lab in ((0.78, NA, "1A flat with vent, Cd0 = 0.78"), (0.68, AZ, "1B cruciform, Cd0 = 0.68")):
        v = np.sqrt(2 * W / (RHO_SITIO * (cd * S0 + CDA_CIL)))
        ax.plot(S0 * 1e4, v, color=col, lw=2, label=lab)
    ax.axhspan(12, 18, color="#e8f1fb", lw=0)
    ax.text(253, 17.6, "C3: 15 ± 3 m/s", fontsize=8.8, color=TX2, va="top")
    for s0, cd, col in ((0.03862, 0.78, NA), (0.04430, 0.68, AZ)):
        v = math.sqrt(2 * W / (RHO_SITIO * (cd * s0 + CDA_CIL)))
        ax.plot(s0 * 1e4, v, "o", ms=8, color=col, mec="white", mew=1.5, zorder=5)
        ax.annotate(f"{v:.1f} m/s", (s0 * 1e4, v), xytext=(6, 6), textcoords="offset points", fontsize=8.8)
    ax.set_xlabel("Canopy area S0 [cm²]")
    ax.set_ylabel("Descent rate at the site [m/s]")
    ax.set_title("Phase 1, 500 g, site density 1.15 kg/m³ (body drag included)", fontsize=10)
    ax.legend(loc="upper right", fontsize=8.8, frameon=False)
    estilo(ax)
    fig.savefig(f"{out}/v2_paracaidas_en.png", dpi=220)
    plt.close(fig)


def planeo(out):
    S_v2 = 0.067
    S_real, _ = area_vela(225.0)
    # largo de larguero para 0,068 m2 con la misma quilla y el mismo angulo
    Ls = np.linspace(225, 400, 500)
    L_req = float(Ls[np.argmin([abs(area_vela(L)[0] - 0.068) for L in Ls])])
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    f = np.linspace(0.2, 1.0, 100)
    ax.axhspan(2, 8, color="#e8f1fb", lw=0)
    ax.text(0.205, 7.9, "C4: 5 ± 3 m/s", fontsize=8.8, color=TX2, va="top")
    for S, col, lab in ((S_v2, AZ, f"S = {S_v2:.3f} m² (v2 value)"), (S_real, NA, f"S = {S_real:.3f} m² (actual planform)"),
                        (0.068, VE, f"S = 0.068 m² (spars of {L_req:.0f} mm)")):
        ax.plot(f, [vz(x, RHO_SITIO, S) for x in f], color=col, lw=2, label=lab)
    ax.set_xlim(0.2, 1.0)
    ax.set_ylim(0, 10)
    ax.set_xlabel("Fraction of Polhamus vortex lift developed by the sail, f")
    ax.set_ylabel("Glide descent rate at the site [m/s]")
    ax.legend(loc="lower left", fontsize=8.6, frameon=False)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(f"{out}/v2_planeo_en.png", dpi=220)
    plt.close(fig)
    out_d = dict(S_v2=S_v2, S_real=S_real, L_req=L_req,
                 vz={k: {str(fr): vz(fr, RHO_SITIO, S) for fr in (1.0, 0.5, 0.3)} for k, S in
                     (("v2", S_v2), ("real", S_real), ("068", 0.068))})
    return out_d


if __name__ == "__main__":
    o = sys.argv[1]
    dimensiones(o)
    paracaidas(o)
    D = planeo(o)
    json.dump(D, open(os.path.join(o, "..", "fea", "descenso_v2.json"), "w"), indent=1)
    print(json.dumps(D, indent=1))
