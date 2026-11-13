"""Velocidad de descenso como planeador: ala delta contra avion convencional, mismo cuerpo, misma area y misma masa.
Equilibrio de fuerzas (como la nota de membrana):  1/2 rho V^2 S C_R = n m g,  C_R = sqrt(C_L^2 + C_D^2),
w = V C_D / C_R,  n = 1/cos(alabeo).   Uso: python3 planeo.py <salida.json> <figura.png>
"""
import sys, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import params as P
import polhamus as ph

G = 9.80665
S = P.S_TRI * 1e-4                    # m2, area de planta del ala (dos triangulos)
SPAN = P.SPAN * 1e-3
DB, LB = 2 * P.RB * 1e-3, P.L_G * 1e-3
AF = math.pi * DB ** 2 / 4            # area frontal del cuerpo (disco de nariz de d84)
AR_PL = SPAN ** 2 / S                 # alargamiento del ala recta de igual area y envergadura
A_PL = 2 * math.pi * AR_PL / (2 + math.sqrt(4 + AR_PL ** 2))     # pendiente de sustentacion [1/rad]
BANK = 20.0
M_PLAN = json.load(open("../fea/masas.json"))["m_planeador"] / 1000


def cuerpo(cdf, alfa):
    """Resistencia del cuerpo (disco de nariz + cilindro): termino axial + flujo cruzado con el ataque."""
    return cdf * AF / S + 1.2 * DB * LB * abs(math.sin(alfa)) ** 3 / S


def delta(alfa_deg, f=0.5, cdw=0.03, cdf=0.8, cdt=0.01):
    a = math.radians(alfa_deg)
    clp, clv = ph.cl(alfa_deg, P.NOTA["AR"], f)
    cl = float(clp + clv)
    return cl, cdw + cuerpo(cdf, a) + cdt + cl * math.tan(a)


def recta(cl, e=0.85, cdw=0.04, cdf=0.8, cdt=0.01):
    a = cl / A_PL + math.radians(-4.0) * -1 * -1        # alfa = CL/a + alfa0, con alfa0 = -4 grados
    a = cl / A_PL - math.radians(4.0)
    return cl, cdw + cuerpo(cdf, max(a, 0.0)) + cdt + cl ** 2 / (math.pi * e * AR_PL)


def sink(cl, cd, m=None, rho=1.2, bank=BANK):
    m = M_PLAN if m is None else m
    n = 1 / math.cos(math.radians(bank))
    cr = math.hypot(cl, cd)
    v = math.sqrt(2 * n * m * G / (rho * S * cr))
    return v * cd / cr, v * cl / cr, v


def main(out_json, out_fig, masa_g=None):
    global M_PLAN
    if masa_g:
        M_PLAN = float(masa_g) / 1000
    res = {"masa_g": M_PLAN * 1000}
    # control: reproduce la nota de membrana (500 g, S = 394 cm2, CL = 1,20, CD = 0,50)
    res["control_nota"] = sink(1.20, 0.50, m=0.5)[0]
    nom = {}
    for nombre, cdf in (("cuerpo romo (disco de nariz plano)", 0.8), ("con ojiva en la nariz", 0.3)):
        d = sink(*delta(20.0, cdf=cdf))
        r = sink(*recta(0.8, cdf=cdf))
        nom[nombre] = dict(delta=dict(CL=delta(20.0, cdf=cdf)[0], CD=delta(20.0, cdf=cdf)[1], LD=delta(20.0, cdf=cdf)[0] / delta(20.0, cdf=cdf)[1], w=d[0], V=d[2]),
                           recta=dict(CL=0.8, CD=recta(0.8, cdf=cdf)[1], LD=0.8 / recta(0.8, cdf=cdf)[1], w=r[0], V=r[2]))
    res["nominal"] = nom
    res["Atrim_recta"] = dict(AR=AR_PL, a=A_PL)
    # Monte Carlo: incertidumbre de modelo y de trim
    rng = np.random.default_rng(7)
    N = 20000
    rho = rng.uniform(1.05, 1.25, N)
    m = M_PLAN + rng.uniform(-0.015, 0.015, N)
    cdf = rng.uniform(0.6, 1.0, N)
    cdt = rng.uniform(0.005, 0.02, N)
    f = rng.uniform(0.0, 1.0, N)
    alfa = np.clip(rng.normal(20.0, 2.5, N), 12.0, 28.0)
    cdw_d = rng.uniform(0.02, 0.05, N)
    cl_t = np.clip(rng.normal(0.8, 0.15, N), 0.3, 1.0)
    e = rng.uniform(0.7, 0.9, N)
    cdw_r = rng.uniform(0.03, 0.06, N)
    wd = np.array([sink(*delta(alfa[i], f[i], cdw_d[i], cdf[i], cdt[i]), m[i], rho[i])[0] for i in range(N)])
    wr = np.array([sink(*recta(cl_t[i], e[i], cdw_r[i], cdf[i], cdt[i]), m[i], rho[i])[0] for i in range(N)])
    q = lambda x: [float(np.percentile(x, p)) for p in (5, 50, 95)]
    res["mc"] = dict(delta=dict(p=q(wd), dentro=float(np.mean((wd > 2) & (wd < 8)))),
                     recta=dict(p=q(wr), dentro=float(np.mean((wr > 2) & (wr < 8)))))
    # sensibilidad: que parametro mueve mas el descenso (correlacion de rangos)
    from scipy.stats import spearmanr
    sd = {k: float(spearmanr(x, wd)[0]) for k, x in (("f (vórtice)", f), ("ángulo de ataque", alfa), ("CD0 ala", cdw_d), ("CD cuerpo", cdf),
                                                     ("CD cola", cdt), ("densidad", rho), ("masa", m))}
    sr = {k: float(spearmanr(x, wr)[0]) for k, x in (("CL de trim", cl_t), ("e", e), ("CD0 ala", cdw_r), ("CD cuerpo", cdf),
                                                     ("CD cola", cdt), ("densidad", rho), ("masa", m))}
    res["sens"] = dict(delta=sd, recta=sr)
    json.dump(res, open(out_json, "w"), indent=1)
    # ------------------------------------------------------------- figura
    plt.rcParams.update({"font.family": "Inter", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "0.88"})
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 4.4))
    ax = axs[0]
    al = np.linspace(4, 34, 90)
    for f_, ls in ((0.0, ":"), (0.5, "-"), (1.0, "--")):
        pts = np.array([sink(*delta(a_, f_))[:2] for a_ in al])
        ax.plot(pts[:, 1], pts[:, 0], ls=ls, color="#2f3192", lw=2.2 if f_ == 0.5 else 1.4,
                label=f"Delta, f = {f_:g}".replace(".", ",") + (" (nota)" if f_ == 0.5 else ""))
    cls = np.linspace(0.2, 1.1, 80)
    pr = np.array([sink(*recta(c_))[:2] for c_ in cls])
    ax.plot(pr[:, 1], pr[:, 0], color="#c0392b", lw=2.2, label="Avión recto, mismo cuerpo")
    pr2 = np.array([sink(*recta(c_, cdf=0.3))[:2] for c_ in cls])
    ax.plot(pr2[:, 1], pr2[:, 0], color="#c0392b", lw=1.3, ls="--", label="Avión recto con ojiva")
    for c_, mk, pt_ in (("#2f3192", "o", sink(*delta(20.0))), ("#c0392b", "o", sink(*recta(0.8)))):
        ax.plot([pt_[1]], [pt_[0]], mk, color=c_, ms=8, mec="w", mew=1.2, zorder=5)
    ax.axhspan(2, 8, color="#1a8a55", alpha=0.09, lw=0)
    ax.axhline(5, color="#1a8a55", lw=1, ls="--")
    ax.text(0.4, 7.35, "requisito C4: 5 ± 3 m/s", fontsize=9, color="#1a8a55")
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 11)
    ax.set_xlabel("Velocidad horizontal [m/s]")
    ax.set_ylabel("Velocidad de descenso [m/s]")
    ax.set_title(f"Polar de velocidades, {M_PLAN * 1000:.0f} g y {S * 1e4:.0f} cm²", fontsize=11, weight="bold")
    ax.legend(fontsize=8.4, loc="upper right")
    ax = axs[1]
    b = np.linspace(0, 12, 49)
    ax.hist(wd, bins=b, color="#2f3192", alpha=0.55, label=f"Delta: {res['mc']['delta']['p'][0]:.1f} a {res['mc']['delta']['p'][2]:.1f} m/s".replace(".", ","))
    ax.hist(wr, bins=b, color="#c0392b", alpha=0.55, label=f"Avión recto: {res['mc']['recta']['p'][0]:.1f} a {res['mc']['recta']['p'][2]:.1f} m/s".replace(".", ","))
    ax.axvspan(2, 8, color="#1a8a55", alpha=0.09, lw=0)
    ax.set_xlabel("Velocidad de descenso [m/s]")
    ax.set_ylabel("Casos (20 000)")
    ax.set_title("Con las incertidumbres de modelo y de trim", fontsize=11, weight="bold")
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    fig.savefig(out_fig, dpi=230)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
