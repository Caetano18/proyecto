"""Diagramas de la memoria v3 (diseno combinado).  Uso: python3 figs_v3.py <carpeta de figuras>

Paleta: series en orden fijo (azul = rev. E, naranja = v2, aguamarina = tercera serie, siempre con rotulo directo);
estados reservados (pasa / en la banda / falla) siempre acompanados de texto; bandas de requisito en gris claro.
"""
import sys
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from scipy.signal import lsim, lti

AZUL, NARANJA, AGUA, AMAR, MAG = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
BIEN, AVISO, MAL = "#0ca30c", "#fab219", "#d03b3b"
TXT, TXT2, GRILLA, BANDA = "#0b0b0b", "#52514e", "#e6e5e1", "#ecebe7"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": TXT2, "axes.labelcolor": TXT,
                     "xtick.color": TXT2, "ytick.color": TXT2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRILLA, "grid.linewidth": 0.7, "axes.axisbelow": True,
                     "legend.frameon": False, "lines.linewidth": 2.0})
G = 9.81
W = 0.5 * G


def coma(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def evolucion(out):
    filas = [  # (nombre, modo lateral [Hz], estado, texto)
        ("Rev. B · contenedor LW-ASA 2 mm (impreso)", 117, "mal", "falla: MS −0,66"),
        ("Rev. C · + patines en C2 y C3", 119, "mal", "falla: no sube el modo"),
        ("Rev. D1 · tubo de vidrio 0,6 mm", 228, "aviso", "dentro de la banda de la lijadora"),
        ("Rev. D · carbono + vidrio, patines rígidos", 307, "bien", "pasa: MS mín. +0,43"),
        ("v2 tal cual · integral, carcasa PETG 2 mm", 161, "mal", "falla: MS −0,55"),
        ("Rev. E · integral, carcasa laminada", 349, "bien", "pasa: MS mín. +4,3"),
    ]
    col = {"mal": MAL, "aviso": AVISO, "bien": BIEN}
    fig, ax = plt.subplots(figsize=(9.6, 3.9))
    ax.axvspan(0, 233, color=BANDA, lw=0, zorder=0)
    ax.axvspan(200, 233, color="#d9d7d0", lw=0, zorder=0)
    ax.text(116, len(filas) - 0.35, "barrido de arranque y frenado (0–233 Hz)", ha="center", va="bottom", color=TXT2, fontsize=9)
    ax.text(216, -0.75, "marcha\n200–233", ha="center", va="top", color=TXT2, fontsize=8.5)
    for i, (n, f, e, t) in enumerate(filas[::-1]):
        ax.barh(i, f, height=0.52, color=col[e], edgecolor="white", linewidth=2, zorder=3)
        ax.text(f + 6, i, f"{f} Hz · {t}", va="center", fontsize=9.5, color=TXT, zorder=4)
    ax.set_yticks(range(len(filas)))
    ax.set_yticklabels([n for n, *_ in filas[::-1]], fontsize=9.5)
    ax.set_xlim(0, 560)
    ax.set_ylim(-1.3, len(filas) - 0.1)
    ax.set_xlabel("Primer modo lateral con el CanSat parado y fijo en la base [Hz]")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(f"{out}/v3_evolucion.png", dpi=220)
    plt.close(fig)


def lijadora(out):
    f = np.linspace(1, 400, 1200)
    A = np.where(f <= 233, 29 * (f / 233) ** 2, np.nan)
    z = 0.02
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    ax.axvspan(200, 233, color=BANDA, lw=0)
    ax.text(216.5, 0.6, "marcha\n200–233 Hz", ha="center", va="bottom", fontsize=8.5, color=TXT2)
    ax.plot(f, A, color=TXT2, lw=1.4, ls="--", label="Excitación del plato: 29 G·(f/233)²")
    for fn, c, nom, aeq, fpk in ((161.0, NARANJA, "v2 · PETG (modo de 161 Hz)", 331, 166),
                                 (349.0, AZUL, "Rev. E · laminado (modo de 349 Hz)", 48, 233)):
        r = f / fn
        H = np.sqrt(1 + (2 * z * r) ** 2) / np.sqrt((1 - r ** 2) ** 2 + (2 * z * r) ** 2)
        ax.plot(f, A * H, color=c, label=f"{nom}: respuesta estacionaria")
        ax.plot([fpk], [aeq], "o", ms=8, color=c, mec="white", mew=2, zorder=5)
        ax.annotate(f"{aeq} G", (fpk, aeq), xytext=(10, 6), textcoords="offset points", fontsize=9.5, color=TXT)
    ax.set_yscale("log")
    ax.set_ylim(0.5, 1000)
    ax.set_xlim(0, 400)
    ax.set_xlabel("Frecuencia de la lijadora [Hz]")
    ax.set_ylabel("Aceleración en el CanSat [G]")
    ax.legend(loc="upper left", fontsize=8.8)
    fig.tight_layout()
    fig.savefig(f"{out}/v3_lijadora.png", dpi=220)
    plt.close(fig)


def paracaidas(out):
    CdA_cil = 0.86 * math.pi * 0.09 ** 2 / 4
    D = np.linspace(0.15, 0.35, 300)
    S0 = math.pi / 4 * (D ** 2 - 0.04 ** 2)
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    ax.axhspan(12, 18, color=BANDA, lw=0)
    ax.text(0.348e3, 17.7, "C3: 15 ± 3 m/s", ha="right", va="top", fontsize=9, color=TXT2)
    v = lambda rho, cd: np.sqrt(2 * W / (rho * (cd * S0 + CdA_cil)))
    ax.fill_between(D * 1e3, v(1.15, 0.78 * 1.1), v(1.15, 0.78 * 0.9), color=AZUL, alpha=0.15, lw=0)
    ax.plot(D * 1e3, v(1.15, 0.78), color=AZUL, label="ρ = 1,15 kg/m³ (sitio; banda: C_d0 ± 10 %)")
    ax.plot(D * 1e3, v(1.225, 0.78), color=NARANJA, label="ρ = 1,225 kg/m³ (nivel del mar, v2)")
    for d, c, t, dx in ((0.226, NARANJA, "v2: Ø226 → 15,4 m/s en el sitio", -150), (0.233, AZUL, "Rev. E: Ø233 → 15,0 m/s", 12)):
        S = math.pi / 4 * (d ** 2 - 0.04 ** 2)
        vv = math.sqrt(2 * W / (1.15 * (0.78 * S + CdA_cil)))
        ax.plot([d * 1e3], [vv], "o", ms=8, color=c, mec="white", mew=2, zorder=5)
        ax.annotate(t, (d * 1e3, vv), xytext=(dx, 14 if dx > 0 else -22), textcoords="offset points", fontsize=9, color=TXT)
    ax.set_xlim(150, 350)
    ax.set_ylim(8, 30)
    ax.set_xlabel("Diámetro exterior del paracaídas plano (ventana Ø40 mm) [mm]")
    ax.set_ylabel("Descenso con 500 g [m/s]")
    ax.legend(loc="upper right", fontsize=8.8, bbox_to_anchor=(1.0, 0.86))
    fig.tight_layout()
    fig.savefig(f"{out}/v3_paracaidas.png", dpi=220)
    plt.close(fig)


def planeo(out):
    Sw, phi, a, Kp, Kv, CD0 = 0.067, math.radians(25), math.radians(28), 2.2, math.pi, 0.080
    CdA_cil = 0.86 * math.pi * 0.09 ** 2 / 4

    def vz(f, rho):
        CL = Kp * math.sin(a) * math.cos(a) ** 2 + f * Kv * math.cos(a) * math.sin(a) ** 2
        CD = CD0 + CdA_cil / Sw + CL * math.tan(a)
        gam = math.atan(CD / (CL * math.cos(phi)))
        V = math.sqrt(2 * W * math.cos(gam) / (rho * Sw * CL * math.cos(phi)))
        return V * math.sin(gam)
    f = np.linspace(0.2, 1.0, 100)
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    ax.axhspan(2, 8, color=BANDA, lw=0)
    ax.text(0.205, 7.85, "C4: 5 ± 3 m/s", va="top", fontsize=9, color=TXT2)
    ax.plot(f, [vz(x, 1.15) for x in f], color=AZUL, label="ρ = 1,15 kg/m³ (sitio)")
    ax.plot(f, [vz(x, 1.225) for x in f], color=NARANJA, label="ρ = 1,225 kg/m³ (nivel del mar)")
    for x, t, dy in ((1.0, "v2: sustentación de vórtice completa", -22), (0.5, "rev. D: la mitad", 12)):
        y = vz(x, 1.15)
        ax.plot([x], [y], "o", ms=8, color=AZUL, mec="white", mew=2, zorder=5)
        ax.annotate(f"{t}: {coma(y, 1)} m/s", (x, y), xytext=(-10 if x == 1.0 else 6, dy), textcoords="offset points",
                    fontsize=9, ha="right" if x == 1.0 else "left", color=TXT)
    ax.set_xlim(0.2, 1.02)
    ax.set_ylim(0, 9)
    ax.set_xlabel("Fracción de la sustentación de vórtice de Polhamus que genera la vela, f")
    ax.set_ylabel("Descenso de la vela Rogallo [m/s]")
    ax.legend(loc="lower left", fontsize=8.8)
    fig.tight_layout()
    fig.savefig(f"{out}/v3_planeo.png", dpi=220)
    plt.close(fig)


def esquema(out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.0, 4.6), gridspec_kw=dict(width_ratios=[1.25, 1]))
    for a in (a1, a2):
        a.set_aspect("equal")
        a.axis("off")
    # ---- corte longitudinal (nadir a la izquierda)
    R = 45
    a1.add_patch(Rectangle((0, -R), 130, 3, color="#38383d"))
    a1.add_patch(Rectangle((0, R - 3), 130, 3, color="#38383d"))
    a1.add_patch(Rectangle((130, -R), 110, 3, color="#9fd4a8"))
    a1.add_patch(Rectangle((130, R - 3), 110, 3, color="#9fd4a8"))
    a1.add_patch(Rectangle((14, R - 4), 192, 5, fill=False, ec=MAL, lw=1.0, ls="--"))
    a1.text(110, R + 3.5, "ranura del larguero 6 × 192 (pasante)", ha="center", fontsize=8, color=TXT2)
    for x0, nom in ((0, "M1"), (83, "M2"), (173, "M3"), (216, "M4"), (236, "M5")):
        a1.add_patch(Rectangle((x0, -R + 3), 4, 2 * R - 6, color="#717a8c"))
        a1.text(x0 + 2, -R - 6, nom, ha="center", fontsize=8.5, color=TXT)
    for y in (-23, 23):
        a1.plot([0, 240], [y, y], color="#9a9aa0", lw=1.6)
    bah = ((2, 35, "Bahía 1\ncámara nadir\nbaliza"), (35, 105, "Bahía 2\n2 × 18650"), (105, 175, "Bahía 3\nPCB, GNSS,\nradio"),
           (175, 220, "Bahía 4\ncámara cenit\nnicrom"), (220, 240, "B5\nparac."))
    for x0, x1, t in bah:
        a1.text((x0 + x1) / 2, 0, t, ha="center", va="center", fontsize=7.6, color=TXT)
    a1.annotate("", (240, -R - 17), (135, -R - 17), arrowprops=dict(arrowstyle="<->", color=AZUL, lw=1.2))
    a1.text(187, -R - 15, "antenas: x > 135 (vidrio)", ha="center", va="bottom", fontsize=8, color=TXT)
    a1.text(65, R + 11, "carbono-epoxi 0,8 mm", ha="center", fontsize=8.5, color=TXT)
    a1.text(185, R + 11, "vidrio-epoxi 0,6 mm", ha="center", fontsize=8.5, color=TXT)
    a1.set_xlim(-10, 250)
    a1.set_ylim(-R - 28, R + 18)
    a1.set_title("Corte longitudinal (x desde la cara de nadir, mm)", fontsize=10, color=TXT)
    # ---- planta desplegada
    xa, yp = 14.0, 35.0
    L, lam = 225.0, math.radians(52)
    xt, yt = xa + L * math.cos(lam), yp + L * math.sin(lam)
    xk = xa + 190
    for s in (1, -1):
        a2.add_patch(Polygon([(xa, s * yp), (xt, s * yt), (xk, 0)], closed=True, fc="#fde3d6", ec=NARANJA, lw=1.4))
        a2.plot([xa, xt], [s * yp, s * yt], color="#38383d", lw=2.4)
    a2.add_patch(Rectangle((0, -R), 240, 2 * R, fill=False, ec="#717a8c", lw=1.2))
    a2.plot([xa, xk], [0, 0], color="#38383d", lw=1.6)
    for x0, x1, c, t, y in ((119, 141, AZUL, "punto neutro 119–141", -R - 16), (95, 105, NARANJA, "CG 95–105", -R - 30)):
        a2.add_patch(Rectangle((x0, y), x1 - x0, 6, color=c))
        a2.text(x1 + 4, y + 3, t, va="center", fontsize=8.5, color=TXT)
    a2.text(xt, yt + 8, f"envergadura 425 mm\nflecha 52°", ha="center", fontsize=8.5, color=TXT)
    a2.text(xa - 3, 0, "ápice\nx = 14", ha="right", va="center", fontsize=8, color=TXT2)
    a2.set_xlim(-30, 260)
    a2.set_ylim(-yt - 12, yt + 30)
    a2.set_title("Vela desplegada, vista superior (vuelo hacia la izquierda)", fontsize=10, color=TXT)
    fig.tight_layout()
    fig.savefig(f"{out}/v3_esquema.png", dpi=220)
    plt.close(fig)


def masa(out):
    cats = ("Estructura", "Descenso y mecanismos", "Potencia y baliza", "Aviónica", "Lastre y margen")
    cols = (AZUL, NARANJA, AGUA, AMAR, MAG)
    barras = (("v2, según su memoria", (223.0, 43.5, 116.0, 97.5, 20.0)),
              ("v2, recalculado", (261.3, 50.5, 121.0, 99.5, 0.0)),
              ("Rev. E (carcasa laminada)", (177.1, 51.0, 121.0, 99.5, 51.4)))
    fig, ax = plt.subplots(figsize=(9.6, 3.2))
    ax.axvspan(490, 510, color=BANDA, lw=0)
    ax.text(500, 2.62, "S1: 500 ± 10 g", ha="center", va="bottom", fontsize=8.5, color=TXT2)
    for i, (nom, v) in enumerate(barras[::-1]):
        x = 0
        for k, m in enumerate(v):
            if m <= 0:
                continue
            ax.barh(i, m, left=x, height=0.55, color=cols[k], edgecolor="white", linewidth=2)
            if m > 40:
                ax.text(x + m / 2, i, coma(m), ha="center", va="center", fontsize=8.5, color="white" if k in (0,) else TXT)
            x += m
        tot = sum(v)
        ax.text(x + 6, i, f"{coma(tot, 1)} g" + ("  ·  22 g sobre el límite" if tot > 510 else ""), va="center", fontsize=9,
                color=MAL if tot > 510 else TXT)
    ax.set_yticks(range(len(barras)))
    ax.set_yticklabels([n for n, _ in barras[::-1]], fontsize=9.5)
    ax.set_xlim(0, 640)
    ax.set_xlabel("Masa [g]")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[Rectangle((0, 0), 1, 1, color=c) for c in cols], labels=cats, ncol=5, loc="upper center",
              bbox_to_anchor=(0.45, -0.32), fontsize=8.5)
    fig.tight_layout()
    fig.savefig(f"{out}/v3_masa.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    o = sys.argv[1]
    evolucion(o)
    lijadora(o)
    paracaidas(o)
    planeo(o)
    esquema(o)
    masa(o)
    print("diagramas v3 ok")
