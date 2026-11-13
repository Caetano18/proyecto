"""Distribucion aerodinamica sobre el ala real (planta con cuerpo en el centro) y su efecto en la varilla.

Potencial : red de vortices (vlm.py) sobre la planta continuada a traves del cuerpo, validada contra Polhamus (K_p) y Helmbold.
Vortice   : analogia de succion de Polhamus.  Fuerza normal por unidad de x y por lado  n'(x) = 1/2 N_v s(x) / int(s dx),  con s(x)
            la semienvergadura local del borde de ataque (ley de ala esbelta, que da K_v = pi para A -> 0) y N_v = f K_v q S sen^2(a).
            K_v = 3,45 (figura 9 del informe de NASA).  Se reparte hacia adentro del borde: triangular centrada en 0,70 s, ancho 0,25 s
            (hipotesis de huella del vortice).
Uso: python3 aero_dist.py   ->  ../fea/aero_dist.json  y figuras en ../figs
"""
import os, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from matplotlib.colors import LogNorm, Normalize
import params as P
import vlm
import planeo as pl
import polhamus as ph

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIGS, FEA = os.path.join(BASE, "figs"), os.path.join(BASE, "fea")
AZ, RJ, VD, NA, GR = "#2f3192", "#c0392b", "#1a8a55", "#e67e22", "#555555"
KV = 3.45                      # figura 9 del informe de NASA (A = 4)
ALFA = 20.0
Y0, Y1 = P.Y_ROOT, P.Y_PIV    # borde del cuerpo y linea de pivotes
XA, XB = P.X_A, P.X_B
SEMI = P.SEMI_SPAN
FOOT_C, FOOT_W = 0.70, 0.25


def x_le(y):
    y = np.abs(y)
    return XA + np.maximum(y - Y1, 0.0)


def planta(ny_cuerpo=6, ny_ala=60, nx=16):
    e = np.concatenate([np.linspace(0, Y0, ny_cuerpo + 1)[:-1], [Y0, Y1], np.linspace(Y1, SEMI, ny_ala + 1)[1:]])
    ye = np.concatenate([-e[::-1][:-1], e])
    return vlm.Ala(x_le, lambda y: XB + 0.0 * np.asarray(y), ye, nx)


def s_local(x):
    """Semienvergadura del borde de ataque a la estacion x (mm)."""
    return Y1 + np.maximum(np.asarray(x) - XA, 0.0)


def calcular():
    w = planta()
    a1 = math.radians(1.0)
    r = w.resultados(a1, x0=0.0)
    Sg = w.S * 1e-6
    # --- areas
    S_exp = 2 * sum(0.5 * (XB - x_le(y)) * 0 for y in [0])           # (se calcula abajo)
    ya = np.abs(w.CP[:, 1])
    area_exp = float(np.sum(w.area[ya > Y0])) * 1e-6
    Kp = r["CLa"]
    xp = r["xcp"]
    res = dict(S_gross_cm2=Sg * 1e4, S_exp_cm2=area_exp * 1e4, AR_gross=P.SPAN ** 2 * 1e-6 / Sg, Kp=Kp, x_ac=xp, x_ac_cr=(xp - XA) / P.D_AB,
               n_paneles=int(w.N), panel_exp_frac=float(np.sum(r["L"][ya > Y0]) / np.sum(r["L"])))
    # --- validacion del VLM
    helm = 2 * math.pi * 6.0 / (2 + math.sqrt(4 + 36.0))
    wd_ = vlm.Ala(lambda y: np.abs(y), lambda y: 1.0 + 0 * y, np.linspace(-1, 1, 81), 16)
    res["valid"] = dict(rect_AR6=vlm.rectangular(6.0, ny=40, nx=12).resultados(a1)["CLa"], helmbold_AR6=helm,
                        delta_AR4=wd_.resultados(a1)["CLa"], paper_Kp_AR4=3.35)
    # --- centroide de la fuerza de vortice (ley esbelta): int x s dx / int s dx
    xs = np.linspace(XA, XB, 4001)
    sx = s_local(xs)
    xv = float(np.trapezoid(xs * sx, xs) / np.trapezoid(sx, xs))
    ints = float(np.trapezoid(sx, xs))                                    # int s dx [mm2] por lado
    res["x_v"], res["x_v_cr"] = xv, (xv - XA) / P.D_AB
    # --- punto de operacion (equilibrio con el planeo del informe)
    f = 0.5
    cl, cd = pl.delta(ALFA, f)
    wv, vh, V = pl.sink(cl, cd)
    gam = math.atan(cd / cl)
    n = 1 / math.cos(math.radians(pl.BANK))
    Lreq = n * pl.M_PLAN * pl.G * math.cos(gam)
    a = math.radians(ALFA)
    CNp = Kp * math.sin(a) * math.cos(a)
    CNv = f * KV * math.sin(a) ** 2
    q = Lreq / (Sg * (CNp + CNv) * math.cos(a))
    res.update(alfa=ALFA, f=f, CNp=CNp, CNv=CNv, q=q, V_dist=math.sqrt(2 * q / 1.2), Lreq=Lreq, CLtot=(CNp + CNv) * math.cos(a), gam=math.degrees(gam))
    # --- distribuciones dimensionales
    sp = math.sin(a) * math.cos(a) / a1
    p_pot = q * r["dcp"] * sp                                         # [Pa] por panel
    F_pot = p_pot * w.area * 1e-6                                     # [N] por panel
    Nv = CNv * q * Sg                                                 # [N] total, dos lados
    res["N_pot"], res["N_vor"] = float(F_pot.sum()), float(Nv)
    # --- reparto del vortice por x y por y (lado y > 0)
    nb = 40
    xe = np.linspace(XA, XB, nb + 1)
    xm = 0.5 * (xe[1:] + xe[:-1])
    dx = xe[1] - xe[0]
    nside = 0.5 * Nv * s_local(xm) / ints                              # [N/mm] por lado
    # perfil triangular en y: centro FOOT_C s, semiancho FOOT_W s
    yy = np.linspace(0, SEMI, 1400)
    def tri(y, s):
        c, h = FOOT_C * s, FOOT_W * s
        return np.maximum(0.0, 1 - np.abs(y - c) / h) / h
    Fv_cuerpo = 0.0
    Rvor = np.zeros(nb)
    Rpot = np.zeros(nb)
    mapa_v = np.zeros((nb, len(yy)))
    for i in range(nb):
        s = s_local(xm[i])
        d = tri(yy, s) * nside[i] * dx                                 # [N/mm de y] reparto en y
        mapa_v[i] = d / dx                                             # N/mm2
        yl = s
        ell = yl - Y0
        m_exp = yy > Y0
        share = np.where(m_exp, (yy - Y0) / ell, 0.0)
        Rvor[i] = np.trapezoid(d * share, yy) / dx                        # [N/mm de x] hacia la varilla de borde de ataque
        Fv_cuerpo += np.trapezoid(d * (~m_exp), yy)
    res["vor_frac_exp"] = float(1 - Fv_cuerpo / (nside * dx).sum())
    # potencial: cada panel aporta a la varilla segun su posicion en la tira
    side = w.CP[:, 1] > 0
    for k in np.where(side)[0]:
        xc, yc = w.CP[k, 0], w.CP[k, 1]
        if yc < Y0:
            continue
        yl = s_local(xc)
        sh = (yc - Y0) / (yl - Y0)
        i = min(int((xc - XA) / dx), nb - 1)
        Rpot[i] += F_pot[k] * sh / dx
    res["pot_frac_exp"] = float(F_pot[np.abs(w.CP[:, 1]) > Y0].sum() / F_pot.sum())
    share = (res["pot_frac_exp"] * F_pot.sum() + res["vor_frac_exp"] * Nv) / (F_pot.sum() + Nv)
    res["share_exp"] = float(share)
    S0 = pl.S
    res["w_area"] = {}
    for nombre, Sx in (("nota", S0), ("expuesta", share * Sg), ("total", Sg)):
        pl.S = Sx
        res["w_area"][nombre] = dict(S_cm2=Sx * 1e4, w=float(pl.sink(*pl.delta(ALFA, 0.5))[0]))
    pl.S = S0
    k5 = np.ones(5) / 5.0
    Rpot = np.convolve(np.pad(Rpot, 2, mode="edge"), k5, mode="valid")
    Rtot = Rpot + Rvor
    res["R"] = dict(x=xm.tolist(), pot=Rpot.tolist(), vor=Rvor.tolist(), tot=Rtot.tolist(), unif=None)
    # --- referencia uniforme (como la nota): p = N / area expuesta, R = p * l / 2
    p_u = (F_pot.sum() + Nv) / (area_exp * 1.0)                        # N/m2 sobre el area expuesta
    ell = np.maximum(s_local(xm) - Y0, 0.0)
    Runi = p_u * 1e-6 * ell / 2
    res["R"]["unif"] = Runi.tolist()
    res["p_unif"] = float(p_u)
    # --- centro de presion y punto neutro del ala (normal, sin cola ni cuerpo)
    def xcp_np(al_deg, ff):
        al = math.radians(al_deg)
        Np, Nvv = Kp * math.sin(al) * math.cos(al), ff * KV * math.sin(al) ** 2
        xcp = (Np * xp + Nvv * xv) / (Np + Nvv)
        dNp, dNv = Kp * math.cos(2 * al), ff * KV * math.sin(2 * al)
        xnp = (dNp * xp + dNv * xv) / (dNp + dNv)
        return xcp, xnp, Np + Nvv
    res["curva"] = {f"{ff:g}": [(al_, *xcp_np(al_, ff)) for al_ in range(2, 31, 2)] for ff in (0.0, 0.5, 1.0)}
    res["xcp_20"] = {f"{ff:g}": xcp_np(ALFA, ff)[0] for ff in (0.0, 0.5, 1.0)}
    res["xnp_20"] = {f"{ff:g}": xcp_np(ALFA, ff)[1] for ff in (0.0, 0.5, 1.0)}
    res["_w"], res["_r"], res["_p_pot"], res["_Rvor"], res["_Rpot"], res["_mapa_v"], res["_yy"], res["_xm"] = w, r, p_pot, Rvor, Rpot, mapa_v, yy, xm
    return res


def varilla(res):
    """Cargas sobre el portico de la varilla de borde de ataque con la distribucion (apertura = 3 x vuelo) y con la uniforme."""
    import wing_frame as wf
    out = {}
    xm = np.array(res["R"]["x"])
    for nombre, clave in (("distribuida", "tot"), ("uniforme", "unif")):
        R = np.array(res["R"][clave])
        ala = wf.Ala()
        c = P.D_AB
        def carga(fac):
            F = np.zeros(ala.K.shape[0])
            th = math.atan(4 * P.NOTA["m_panza"])
            phi = math.radians(45.0)
            n_pl = np.array([math.sin(phi), -math.cos(phi), 0.0])
            for i in range(ala.nle - 1):
                s0, s1 = ala.s_le[i], ala.s_le[i + 1]
                xa, xb = XA + s0 * math.cos(phi), XA + s1 * math.cos(phi)
                dxs = xb - xa
                Rm = float(np.interp(0.5 * (xa + xb), xm, R)) * fac
                Fz = Rm * dxs
                Fp = Rm / (4 * P.NOTA["m_panza"]) * math.cos(th) * math.cos(phi) * dxs
                for node, wgt in ((i, 0.5), (i + 1, 0.5)):
                    F[ala.dof[node, 2]] += Fz * wgt
                    F[ala.dof[node, 0:3]] += Fp * wgt * n_pl
            return F
        for caso, fac in (("vuelo", 1.0), ("apertura", 3.0)):
            u = ala.estatico(carga(fac))
            out[f"{nombre}_{caso}"] = wf.resumen_caso(ala, u, f"{nombre} {caso}")
    return out


def figuras(res):
    plt.rcParams.update({"font.family": "Inter", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "0.88", "savefig.dpi": 230})
    w, r = res["_w"], res["_r"]
    p_pot = res["_p_pot"]
    xm, yy, mapa_v = res["_xm"], res["_yy"], res["_mapa_v"]
    # ---------------- mapa de presiones (lado derecho y espejo)
    fig = plt.figure(figsize=(11.0, 4.4))
    ax = fig.add_axes([0.04, 0.12, 0.40, 0.78])
    ax.set_aspect("equal")
    tri = Triangulation(w.CP[:, 1], w.CP[:, 0])
    # recortar a la planta: quitar triangulos con baricentro fuera
    ok = np.array([(abs(w.CP[t, 1].mean()) <= s_local(w.CP[t, 0].mean()) + 0.5) for t in tri.triangles])
    tri.set_mask(~ok)
    # grilla del vortice interpolada a la misma triangulacion
    ptot = p_pot.copy()
    from scipy.interpolate import RegularGridInterpolator
    I = RegularGridInterpolator((xm, yy), mapa_v, bounds_error=False, fill_value=0.0)
    pv = np.array([I((w.CP[k, 0], abs(w.CP[k, 1]))) * 1e6 for k in range(w.N)])      # N/mm2 -> Pa
    ptot = p_pot + pv
    cs = ax.tricontourf(tri, ptot, levels=np.linspace(0, 300, 16), cmap="turbo", extend="max")
    ax.plot([-SEMI, -Y1, Y1, SEMI], [XB, XA, XA, XB], color="k", lw=1.2)
    ax.plot([-SEMI, SEMI], [XB, XB], color="k", lw=1.2)
    ax.axvspan(-Y0, Y0, color="0.85", alpha=0.9, zorder=3)
    ax.text(0, 100, "cuerpo", ha="center", fontsize=9, zorder=4)
    ax.set_ylim(XB + 8, XA - 8)
    ax.set_xlim(-SEMI - 8, SEMI + 8)
    ax.set_xlabel("y [mm]")
    ax.set_ylabel("x desde la nariz [mm]")
    ax.set_title("Presión de diseño en vuelo (α = 20°)", weight="bold", fontsize=11)
    cb = fig.colorbar(cs, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("p [Pa] (escala cortada en 300)")
    ax.grid(False)
    # ---------------- distribucion en la envergadura
    ax = fig.add_axes([0.57, 0.64, 0.41, 0.28])
    ys = 0.5 * (w.ye[1:] + w.ye[:-1])
    dyv = np.diff(w.ye)
    Lp_strip = np.array([np.sum(p_pot[w.strip == j] * w.area[w.strip == j]) for j in range(w.ny)]) * 1e-6
    lp = Lp_strip / (dyv * 1e-3)
    Lv_strip = np.array([np.sum(pv[w.strip == j] * w.area[w.strip == j]) for j in range(w.ny)]) * 1e-6
    lv = Lv_strip / (dyv * 1e-3)
    ax.fill_between(ys, 0, lp, color=AZ, alpha=0.55, step="mid", label="potencial (VLM)")
    ax.fill_between(ys, lp, lp + lv, color=NA, alpha=0.6, step="mid", label="vórtice de borde de ataque")
    ax.axvspan(-Y0, Y0, color="0.8", alpha=0.7)
    ax.set_xlabel("y [mm]")
    ax.set_ylabel("Fuerza normal [N/m]")
    ax.set_title("Carga en la envergadura", weight="bold", fontsize=11)
    ax.legend(fontsize=8.5, loc="upper right")
    # ---------------- distribucion en la cuerda (promedio de la envergadura expuesta)
    ax = fig.add_axes([0.57, 0.12, 0.41, 0.28])
    xs_ = res["R"]["x"]
    ax.plot(xs_, np.array(res["R"]["pot"]), color=AZ, lw=2, label="potencial")
    ax.plot(xs_, np.array(res["R"]["vor"]), color=NA, lw=2, label="vórtice")
    ax.plot(xs_, np.array(res["R"]["tot"]), color="k", lw=2.2, label="total sobre la varilla")
    ax.plot(xs_, np.array(res["R"]["unif"]), color=GR, lw=1.6, ls="--", label="presión uniforme (nota)")
    ax.set_xlabel("x desde la nariz [mm]")
    ax.set_ylabel("N/mm de x")
    ax.set_title("Reacción de la membrana sobre la varilla", weight="bold", fontsize=11)
    ax.legend(fontsize=8.3, loc="upper left")
    fig.savefig(os.path.join(FIGS, "aero_distribucion.png"))
    plt.close(fig)
    # ---------------- centro de presion, punto neutro y curva de momento
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 3.8))
    ax = axs[0]
    for ff, ls, lw in (("0", ":", 1.5), ("0.5", "-", 2.4), ("1", "--", 1.5)):
        c = np.array(res["curva"][ff])
        ax.plot(c[:, 0], c[:, 1], color=AZ, ls=ls, lw=lw, label=f"centro de presión, f = {ff}".replace(".", ","))
        ax.plot(c[:, 0], c[:, 2], color=RJ, ls=ls, lw=lw, label=f"punto neutro del ala, f = {ff}".replace(".", ","))
    ax.axhline(res["x_ac"], color=GR, lw=0.9)
    ax.text(3, res["x_ac"] + 0.6, "centro aerodinámico (lineal)", fontsize=8.4, color=GR, ha="left", va="bottom")
    ax.axvline(ALFA, color="0.7", lw=0.9)
    ax.set_xlabel("Ángulo de ataque [°]")
    ax.set_ylabel("Posición desde la nariz [mm]")
    ax.set_title("El centro de presión del ala se corre hacia atrás con el ataque", weight="bold", fontsize=10.5)
    ax.legend(fontsize=7.4, ncol=2, loc="upper left")
    ax = axs[1]
    for k, (nombre, col, ls) in enumerate((("distribuida", "k", "-"), ("uniforme", GR, "--"))):
        R = np.array(res["R"]["tot" if nombre == "distribuida" else "unif"])
        ax.plot(np.array(res["R"]["x"]), np.cumsum(R) * (res["R"]["x"][1] - res["R"]["x"][0]), color=col, ls=ls, lw=2.2 if k == 0 else 1.6,
                label=f"{nombre}: {R.sum() * (res['R']['x'][1] - res['R']['x'][0]):.2f} N")
    ax.set_xlabel("x desde la nariz [mm]")
    ax.set_ylabel("Fuerza acumulada sobre la varilla [N]")
    ax.set_title("Fuerza que llega a la varilla (por ala, en vuelo)", weight="bold", fontsize=10.5)
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "aero_cp.png"))
    plt.close(fig)


def main():
    res = calcular()
    res["varilla"] = varilla(res)
    figuras(res)
    out = {k: v for k, v in res.items() if not k.startswith("_")}
    json.dump(out, open(os.path.join(FEA, "aero_dist.json"), "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in out.items() if k not in ("R", "curva")}, indent=1, default=float, ensure_ascii=False)[:3800])


if __name__ == "__main__":
    main()
