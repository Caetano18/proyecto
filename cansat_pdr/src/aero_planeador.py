"""Seccion de aerodinamica del planeador: calculos, figuras y texto LaTeX.
  - fragmento()  : texto LaTeX de la seccion (lo usa build_informe.py)
  - main()       : arma ademas un PDF independiente  ../Aerodinamica_Planeador.pdf
Uso: python3 aero_planeador.py
"""
import os, json, math, subprocess, shutil, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from PIL import Image
import params as P
import polhamus as ph
import planeo as pl

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIGS, FEA, BUILD = (os.path.join(BASE, d) for d in ("figs", "fea", "build"))
os.makedirs(os.path.join(BUILD, "img"), exist_ok=True)
AZ, RJ, VD, NA, GR = "#2f3192", "#c0392b", "#1a8a55", "#e67e22", "#555555"


def n(x, d=1):
    return f"{x:.{d}f}".replace(".", "{,}")


# ----------------------------------------------------------------------------- calculos
def calcular():
    MAS = json.load(open(os.path.join(FEA, "masas.json")))
    PLJ = json.load(open(os.path.join(FEA, "planeo.json")))
    PL5 = json.load(open(os.path.join(FEA, "planeo_500g.json")))
    PHJ = json.load(open(os.path.join(FEA, "polhamus.json")))
    m = MAS["m_vuelo"] / 1000
    pl.M_PLAN = m
    a20 = 20.0
    r = dict(m=m, S=pl.S, AR=P.NOTA["AR"], cr=P.D_AB, mac=2 / 3 * P.D_AB, span_aero=2 * P.D_AB, span_total=P.SPAN, DB=pl.DB, LB=pl.LB,
             AF=pl.AF, n=1 / math.cos(math.radians(pl.BANK)), bank=pl.BANK, rho=1.2)
    cl, cd = pl.delta(a20)
    w, vh, v = pl.sink(cl, cd)
    r["op"] = dict(CL=cl, CD=cd, LD=cl / cd, w=w, vh=vh, V=v, gamma=math.degrees(math.atan(cd / cl)), alcance=400 * cl / cd)
    r["control_nota"] = pl.sink(1.20, 0.50, m=0.5)[0]
    # descomposicion de la resistencia (delta y avion recto)
    ca = math.radians(a20)
    r["cd_delta"] = dict(inducida=cl * math.tan(ca), ala=0.03, cuerpo_axial=0.8 * pl.AF / pl.S,
                         cuerpo_cruzado=1.2 * pl.DB * pl.LB * math.sin(ca) ** 3 / pl.S, cola=0.01)
    clr, cdr = pl.recta(0.8)
    ar = math.radians(0.8 / pl.A_PL * 180 / math.pi - 4.0)
    r["cd_recta"] = dict(inducida=0.8 ** 2 / (math.pi * 0.85 * pl.AR_PL), ala=0.04, cuerpo_axial=0.8 * pl.AF / pl.S,
                         cuerpo_cruzado=1.2 * pl.DB * pl.LB * max(math.sin(ar), 0) ** 3 / pl.S, cola=0.01)
    cd_sin = 0.03 + 0.01 + cl * math.tan(ca)
    r["w_sin_cuerpo"] = pl.sink(cl, cd_sin)[0]
    # barridos
    r["w_alfa"] = {f"{f:g}": [(a, pl.sink(*pl.delta(a, f))[0]) for a in range(8, 31, 2)] for f in (0.0, 0.5, 1.0)}
    r["w_masa"] = {f"{f:g}": [(mg, pl.sink(*pl.delta(a20, f), m=mg / 1000)[0]) for mg in range(300, 521, 20)] for f in (0.0, 0.5, 1.0)}
    r["w_masas_tabla"] = [(mg, pl.sink(*pl.delta(a20), m=mg / 1000)[0]) for mg in (340, 368, 400, 450, 500)]
    r["w_area"] = []
    S0 = pl.S
    for k in (1.0, 1.1, 1.2, 1.3):
        pl.S = S0 * k
        r["w_area"].append((S0 * k * 1e4, pl.sink(*pl.delta(a20))[0]))
    pl.S = S0
    r["nominal"] = PLJ["nominal"]
    r["mc"] = PLJ["mc"]
    r["sens"] = PLJ["sens"]
    r["w500"] = PL5["nominal"]["cuerpo romo (disco de nariz plano)"]["delta"]["w"]
    r["polh"] = PHJ
    # ---------- estabilidad longitudinal estatica (orden de magnitud)
    d = 1.0
    clf = lambda a: float(sum(ph.cl(a, r["AR"], 0.5)))
    aw = (clf(a20 + d) - clf(a20 - d)) / math.radians(2 * d)           # pendiente local de sustentacion [1/rad]
    D = json.load(open(os.path.join(FEA, "aero_dist.json")))
    r["dist"] = D
    xA, cr = P.X_A, P.D_AB
    x_ac = (D["xnp_20"]["0"], D["xnp_20"]["1"])                        # punto neutro del ala a 20 grados, f de 0 a 1 (VLM + Polhamus)
    x_w5 = D["xnp_20"]["0.5"]
    St, lt = 80e-4, 0.217                                              # nota de cola
    ART = 2.0
    at = 2 * math.pi * ART / (2 + math.sqrt(4 + ART ** 2))
    eta = 0.9
    de = 2 * aw / (math.pi * r["AR"])
    atp = at * eta * (1 - de)
    k = atp * St / (aw * pl.S)
    x_cg = MAS["x_cg_vuelo_total"]
    x_t = x_cg + lt * 1000
    vol = math.pi * pl.DB ** 2 / 4 * pl.LB
    mac = r["mac"] / 1000
    dcm_b = [2 * dk * vol / (pl.S * mac) for dk in (0.5, 0.7)]          # Munk, por radian
    sh_b = [dc / aw * mac * 1000 for dc in dcm_b]                       # corrimiento del PN hacia la nariz [mm]
    np_lo = (x_ac[0] + k * x_t) / (1 + k) - sh_b[1]
    np_hi = (x_ac[1] + k * x_t) / (1 + k) - sh_b[0]
    mm = r["mac"]
    sh_c = 0.5 * (sh_b[0] + sh_b[1])
    np_c = (x_w5 + k * x_t) / (1 + k) - sh_c
    def k_req(xw, sh):
        T = x_cg + 0.10 * mm + sh
        return (T - xw) / (x_t - T)
    k_lo, k_c = k_req(x_ac[0], sh_b[1]), k_req(x_w5, sh_c)
    r["est"] = dict(aw=aw, x_ac=x_ac, np_c=np_c, SM_c=(np_c - x_cg) / mm, St_req_lo=80.0 * k_lo / k, St_req_c=80.0 * k_c / k, k=k, at=at, de=de, x_t=x_t, x_cg=x_cg, sh_b=sh_b, np=(np_lo, np_hi),
                    SM=((np_lo - x_cg) / mm, (np_hi - x_cg) / mm), cg_req=np_lo - 0.10 * mm, dcg=x_cg - (np_lo - 0.10 * mm),
                    dcg_bat=0.046 * 60 / m, x_centroide=MAS["x_centroide_ala"])
    return r


# ----------------------------------------------------------------------------- figuras
def figuras(r):
    plt.rcParams.update({"font.family": "Inter", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "0.88", "savefig.dpi": 230})
    # --- resistencia, descenso contra alfa y contra masa
    fig, axs = plt.subplots(1, 3, figsize=(11.0, 3.9))
    ax = axs[0]
    comp = [("inducida", "Inducida", AZ), ("ala", "Ala: perfil y varillas", "#7d3c98"), ("cuerpo_axial", "Cuerpo: nariz y cilindro", RJ),
            ("cuerpo_cruzado", "Cuerpo: flujo cruzado", NA), ("cola", "Cola e interferencia", GR)]
    for i, (cfg, nom) in enumerate((("cd_delta", "Delta\n20°"), ("cd_recta", "Avión recto\nC$_L$ 0,8"))):
        left = 0.0
        for key, lab, col in comp:
            v = r[cfg][key]
            ax.barh(i, v, left=left, color=col, edgecolor="w", label=lab if i == 0 else None, height=0.55)
            if v > 0.07:
                ax.text(left + v / 2, i, f"{v:.2f}".replace(".", ","), ha="center", va="center", color="w", fontsize=9, weight="bold")
            left += v
        ax.text(left + 0.01, i, f"{left:.2f}".replace(".", ","), va="center", fontsize=10, weight="bold")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Delta\n20°", "Avión recto\nC$_L$ 0,8"])
    ax.set_xlabel("Coeficiente de resistencia $C_D$")
    ax.set_xlim(0, 0.8)
    ax.set_ylim(-0.5, 3.0)
    ax.set_title("Resistencia por componente", weight="bold", fontsize=11)
    ax.legend(fontsize=7.8, loc="upper left", ncol=1, handlelength=1.2)
    ax.grid(axis="y", visible=False)
    ax = axs[1]
    for f, ls, lw in (("0", ":", 1.5), ("0.5", "-", 2.4), ("1", "--", 1.5)):
        pts = r["w_alfa"][f]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], ls=ls, lw=lw, color=AZ, label=f"f = {f}".replace(".", ","))
    ax.axvspan(25, 30, color=NA, alpha=0.10, lw=0)
    ax.text(25.3, 2.0, "fuera del\nrango ensayado", fontsize=8, color="#a0520f")
    ax.axhspan(2, 8, color=VD, alpha=0.08, lw=0)
    ax.axhline(5, color=VD, lw=1, ls="--")
    ax.set_ylim(1.5, 8.5)
    ax.set_xlabel("Ángulo de ataque [°]")
    ax.set_ylabel("Velocidad de descenso [m/s]")
    ax.set_title("Casi no depende del ataque", weight="bold", fontsize=11)
    ax.legend(fontsize=8.5, loc="upper right")
    ax = axs[2]
    for f, ls, lw in (("0", ":", 1.5), ("0.5", "-", 2.4), ("1", "--", 1.5)):
        pts = r["w_masa"][f]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], ls=ls, lw=lw, color=AZ)
    ax.axhspan(2, 8, color=VD, alpha=0.08, lw=0)
    ax.axhline(5, color=VD, lw=1, ls="--")
    ax.axvline(r["m"] * 1000, color=GR, lw=1.1)
    ax.text(r["m"] * 1000 - 4, 7.6, f"CanSat\ncompleto\n{r['m'] * 1000:.0f} g", fontsize=8.5, color=GR, ha="right", va="top")
    ax.axvline(368, color=GR, lw=0.9, ls=":")
    ax.text(364, 2.0, "solo el planeador\n368 g", fontsize=8.3, color=GR, ha="right")
    ax.set_ylim(1.5, 8.5)
    ax.set_xlabel("Masa de vuelo [g]")
    ax.set_title("Con la masa, a $S$ = %.0f cm²" % (r["S"] * 1e4), weight="bold", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "aero_resistencia.png"))
    plt.close(fig)
    # --- estabilidad: posiciones sobre el eje del cuerpo
    e = r["est"]
    fig, ax = plt.subplots(figsize=(11.0, 3.7))
    ax.add_patch(Rectangle((0, -1.2), P.L_G, 2.4, fc="#e8e8ef", ec="0.4", lw=1))
    ax.add_patch(Polygon([(P.X_A, 0), (P.X_B, -4.0), (P.X_B, 4.0)], closed=True, fc="#fbd9bd", ec=NA, lw=1))
    ax.plot([P.X_B, 336], [0, 0], color="k", lw=2)
    ax.add_patch(Polygon([(300, 0), (336, 0), (336, 3.0), (312, 3.0)], closed=True, fc="#fbd9bd", ec=NA, lw=1))
    ax.text(P.X_B + 6, 3.2, "ala (planta, esquemática)", fontsize=8.6, color="#a0520f")
    ax.text(318, -3.0, "cola", fontsize=8.6, color="#a0520f", ha="center")
    ax.barh(-6.4, e["x_ac"][1] - e["x_ac"][0], left=e["x_ac"][0], height=1.2, color="#7d3c98", alpha=0.85)
    ax.text(e["x_ac"][0] - 3, -6.4, "punto neutro del ala\n(VLM + Polhamus, f de 0 a 1)", ha="right", va="center", fontsize=8.8)
    ax.barh(-8.6, e["np"][1] - e["np"][0], left=e["np"][0], height=1.2, color=AZ, alpha=0.85)
    ax.text(e["np"][0] - 3, -8.6, "punto neutro del conjunto\n(con cola y cuerpo)", ha="right", va="center", fontsize=8.8)
    ax.axvline(e["x_cg"], color=RJ, lw=2.2)
    ax.text(e["x_cg"] + 2.5, 6.6, f"CG en vuelo\n{e['x_cg']:.0f} mm", color=RJ, fontsize=9.6, weight="bold", va="top")
    ax.axvline(e["cg_req"], color=VD, lw=1.6, ls="--")
    ax.text(e["cg_req"] - 2.5, 6.6, f"CG necesario\n{e['cg_req']:.0f} mm", color=VD, fontsize=9.6, weight="bold", ha="right", va="top")
    ax.axvspan(e["np"][0], e["np"][1], color=AZ, alpha=0.06, lw=0)
    ax.set_xlim(-130, 345)
    ax.set_ylim(-10.2, 7.0)
    ax.set_yticks([])
    ax.set_xlabel("Posición desde la nariz [mm]")
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "aero_estabilidad.png"))
    plt.close(fig)


# ----------------------------------------------------------------------------- LaTeX
def _tab(cols, cab, filas, cap, fs=r"\small"):
    o = [r"\begin{table}[H]\centering" + fs, r"\begin{tabular}{%s}\toprule" % cols, " & ".join(cab) + r"\\ \midrule"]
    for f_ in filas:
        o.append(r"\midrule" if f_ == "-" else " & ".join(str(c) for c in f_) + r"\\")
    o.append(r"\bottomrule\end{tabular}\caption{%s}\end{table}" % cap)
    return "\n".join(o)


def _fig(name, w, cap, lab=""):
    dst = os.path.join(BUILD, "img", os.path.splitext(name)[0] + ".jpg")
    i = Image.open(os.path.join(FIGS, name)).convert("RGB")
    if max(i.size) > 1800:
        i.thumbnail((1800, 1800), Image.LANCZOS)
    i.save(dst, quality=90)
    return (r"\begin{figure}[H]\centering\includegraphics[width=%s\linewidth]{img/%s}\caption{%s}%s\end{figure}"
            % (w, os.path.basename(dst), cap, (r"\label{%s}" % lab) if lab else ""))


def fragmento(r=None):
    r = r or calcular()
    figuras(r)
    o, E, PH = r["op"], r["est"], r["polh"]
    nom = r["nominal"]["cuerpo romo (disco de nariz plano)"]
    ojv = r["nominal"]["con ojiva en la nariz"]
    mcd, mcr = r["mc"]["delta"]["p"], r["mc"]["recta"]["p"]
    sd = sorted(r["sens"]["delta"].items(), key=lambda kv: -abs(kv[1]))
    sr = sorted(r["sens"]["recta"].items(), key=lambda kv: -abs(kv[1]))
    cdd, cdr = r["cd_delta"], r["cd_recta"]
    t_datos = _tab("lc", ["Dato", "Valor"], [
        ["Masa de vuelo (CanSat completo, S1)", "%s\\,g" % n(r["m"] * 1000, 0)],
        ["Área de las dos alas $S$", "%.0f\\,cm$^2$" % (r["S"] * 1e4)],
        ["Envergadura de las alas / con el cuerpo", "%s / %s\\,mm" % (n(r["span_aero"], 0), n(r["span_total"], 0))],
        ["Alargamiento $A=b^2/S$, flecha", "%s, 45°" % n(r["AR"], 1)],
        ["Cuerda de raíz / cuerda media aerodinámica", "%s / %s\\,mm" % (n(r["cr"]), n(r["mac"]))],
        ["Cuerpo: cilindro con disco de nariz plano", "\\diam%s $\\times$ %s\\,mm" % (n(r["DB"] * 1000, 0), n(r["LB"] * 1000, 0))],
        ["Cola (nota de cola, geometría de referencia)", "80\\,cm$^2$ a 217\\,mm del CG"],
        ["Densidad del aire / alabeo en la espiral", "%s\\,kg/m$^3$ (1{,}05 a 1{,}25) / %g° ($n=%s$)" % (n(r["rho"], 2), r["bank"], n(r["n"], 3))],
    ], "Datos de partida.")
    t_cl = _tab("lccccc", ["Hipótesis", "$f$", r"$C_L$ potencial", r"$C_L$ vórtice", "$C_L$", "$w$ [m/s]"], [
        [x["nombre"], n(x["f"]), n(x["CLp"], 2), n(x["CLv"], 2), n(x["CL"], 2), n(x["w_vuelo"], 1)] for x in PH["filas"]],
        "Sustentación a $\\alpha=20^\\circ$ y descenso del planeador según la fracción de vórtice que se cuenta.", r"\footnotesize")
    t_cd = _tab("lcc", ["Componente", "Delta, $20^\\circ$", "Avión recto, $C_L=0{,}8$"], [
        ["Inducida", "%s\\,($C_L\\tan\\alpha$)" % n(cdd["inducida"], 3), "%s\\,($C_L^2/\\pi eA$)" % n(cdr["inducida"], 3)],
        ["Ala: perfil, varillas y tela", n(cdd["ala"], 3), n(cdr["ala"], 3)],
        ["Cuerpo: nariz plana y cilindro", n(cdd["cuerpo_axial"], 3), n(cdr["cuerpo_axial"], 3)],
        ["Cuerpo: flujo cruzado con el ataque", n(cdd["cuerpo_cruzado"], 3), n(cdr["cuerpo_cruzado"], 3)],
        ["Cola e interferencia", n(cdd["cola"], 3), n(cdr["cola"], 3)], "-",
        [r"\textbf{Total} $C_D$", r"\textbf{%s}" % n(o["CD"], 3), r"\textbf{%s}" % n(nom["recta"]["CD"], 3)],
    ], "Resistencia por componente, referida al área del ala ($S=%.0f$\\,cm$^2$)." % (r["S"] * 1e4))
    t_op = _tab("lccccccc", ["Configuración", "$C_L$", "$C_D$", "L/D", "$V$ [m/s]", "$V_h$ [m/s]", "$w$ [m/s]", "Alcance desde 400\\,m"], [
        ["Delta, $\\alpha=20^\\circ$, $f=0{,}5$", n(o["CL"], 2), n(o["CD"], 2), n(o["LD"], 1), n(o["V"], 1), n(o["vh"], 1), n(o["w"], 1), "%.0f\\,m" % o["alcance"]],
        ["Avión recto, $C_L=0{,}8$", n(nom["recta"]["CL"], 2), n(nom["recta"]["CD"], 2), n(nom["recta"]["LD"], 1), n(nom["recta"]["V"], 1),
         n(nom["recta"]["V"] * math.cos(math.atan(nom["recta"]["CD"] / 0.8)), 1), n(nom["recta"]["w"], 1), "%.0f\\,m" % (400 * nom["recta"]["LD"])],
    ], "Punto de operación: delta con 20° de ataque y avión recto con $C_L=0{,}8$, mismo cuerpo, área y masa.", r"\footnotesize")
    t_masa = _tab("lccccc", ["Masa de vuelo [g]"] + [n(m_, 0) for m_, _ in r["w_masas_tabla"]], [
        ["$w$ delta [m/s]"] + [n(w_, 1) for _, w_ in r["w_masas_tabla"]],
        ["Área para $w=5{,}0$ [cm$^2$], $%s$\\,g" % n(r["m"] * 1000, 0)] + ["--"] * 5,
    ], "Descenso del delta contra la masa.").replace(r"\\ \midrule", r"\\ \midrule", 1)
    # la fila de area va aparte, en texto
    t_masa = _tab("lccccc", ["Masa de vuelo [g]"] + [n(m_, 0) for m_, _ in r["w_masas_tabla"]],
                  [["$w$ del delta [m/s]"] + [n(w_, 1) for _, w_ in r["w_masas_tabla"]]], "Descenso del delta contra la masa de vuelo ($S$ constante).")
    rank = lambda lst, nm: ", ".join("%s (%+.2f)" % (k_, v_) for k_, v_ in lst[:3]).replace(".", "{,}")
    t_mc = _tab("lccc", ["", r"$w$ 5\,\%", r"$w$ mediana", r"$w$ 95\,\%"], [
        ["Delta", n(mcd[0], 1), n(mcd[1], 1), n(mcd[2], 1)], ["Avión recto", n(mcr[0], 1), n(mcr[1], 1), n(mcr[2], 1)]],
        "Descenso [m/s] con las incertidumbres de modelo y de trim (20\\,000 casos).")
    SM = E["SM"]
    s = r"""\section{Aerodinámica del planeador}\label{sec:aero}
\que La sustentación, la resistencia y la velocidad de descenso del planeador en régimen de planeo estacionario y de espiral, y
lo que se puede decir de su estabilidad longitudinal estática. Es la parte que fija el cumplimiento de C4 ($5\pm3$\,m/s). No se
trata aquí el control lateral ni la espiral por asimetría de engranajes.
\begin{resultado}Con %s\,g y $S=%.0f$\,cm$^2$ el planeador baja a \textbf{%s\,m/s} con $V=%s$\,m/s y L/D $=%s$. Con las
incertidumbres de modelo y de trim queda entre %s y %s\,m/s: dentro de $5\pm3$\,m/s en todos los casos. El valor depende
sobre todo de cuánta sustentación de vórtice da el ala, que está fuera del rango donde el método de Polhamus se ensayó. La
estabilidad longitudinal no se puede asegurar con este nivel de modelo: el centro de gravedad cae dentro del rango de incertidumbre
del punto neutro.\end{resultado}

\subsection{Datos y planteo}
%s
\porque En régimen estacionario el empuje aerodinámico equilibra el peso, afectado por el factor de carga de la espiral:
\[\tfrac12\rho V^2 S\,C_R=n\,m\,g,\qquad C_R=\sqrt{C_L^2+C_D^2},\qquad w=V\,\frac{C_D}{C_R},\qquad V_h=V\,\frac{C_L}{C_R},\]
con $n=1/\cos(\mathrm{alabeo})$ y ángulo de planeo $\gamma=\arctan(C_D/C_L)$. La masa de vuelo es la del CanSat completo, 500\,g, el caso más desfavorable: con el contenedor separado el planeador vuela con 368\,g y baja a @@W368@@\,m/s (línea de puntos de la figura de masa).
Con los datos de la nota de membrana ($C_L=1{,}20$, $C_D=0{,}50$) este cálculo da %s\,m/s, contra 5{,}00 de la nota.

\subsection{Sustentación: analogía de succión de borde de ataque}
\que $C_L(\alpha)$ del ala delta de borde afilado con el método de Polhamus (NASA TN D-3767).
\porque
\[C_L=K_p\,\mathrm{sen}\,\alpha\cos^2\alpha+f\,K_v\cos\alpha\,\mathrm{sen}^2\alpha,\qquad C_{D,i}=C_L\tan\alpha,\]
con $K_p\approx%s$ y $K_v\approx%s$ para $A=4$ (figuras 6 y 9 del informe de NASA). El primer término es el flujo potencial sin
succión de borde de ataque y el segundo la sustentación del vórtice; $f=1$ es el método completo, $f=0{,}5$ lo que usa la nota de
membrana y $f=0$ no cuenta el vórtice.
%s
%s
\chequeo El informe de NASA valida el método con alas de alargamiento 0{,}5 a 2{,}0; esta ala tiene 4. En la de 2{,}0 la
sustentación medida cae por debajo de la teoría desde unos 18°, que el autor atribuye a separación en el borde de fuga, y eso
empeora al crecer el alargamiento. A 20° y $A=4$ hay que esperar entonces menos que el método completo, y quizá menos que el
término potencial solo ($f=0$). El método no da el momento de cabeceo y no está probado fuera del delta convencional; tampoco
contempla la panza de la membrana ni el número de Reynolds bajo ($\sim10^5$).

\subsection{Resistencia}
\que La resistencia total, con el cuerpo y la cola incluidos.
\porque La resistencia inducida es la de Polhamus, $C_L\tan\alpha$. El ala suma perfil, varillas y tela ($\approx0{,}03$) y la cola
$\approx0{,}01$. El cuerpo es un cilindro de \diam%s con un disco de nariz plano que mira de frente a la corriente: $C_D\approx0{,}8$
referido a su área frontal, más la resistencia de flujo cruzado por el ataque de 20°.
%s
\chequeo El cuerpo aporta %s de los %s de $C_D$ del delta, y sin él el descenso sería de %s\,m/s en vez de %s. La nota de
membrana no contaba esta resistencia. Con una ojiva en la nariz ($C_D\approx0{,}3$ en el cuerpo) el delta baja a %s\,m/s; no hay
lugar en el compartimento de nariz para agregarla.

\subsection{Polar y velocidad de descenso}
\que La velocidad de descenso en el punto de operación y su relación con el ángulo de ataque, la masa y el área.
%s
%s
%s
\chequeo El descenso casi no depende del ángulo de ataque ($%s$\,m/s a 12°, %s a 20°, %s a 28°): el ala es robusta al trim, pero
tampoco hay palanca para regularlo. Con la masa varía como $\sqrt{m}$. Con los 500\,g del CanSat completo el descenso
queda en %s\,m/s, a %s\,m/s del límite superior de 8. Volver a 5{,}0\,m/s exigiría unos 500\,cm$^2$ de tela (+27\,\%%), que no
entra en el cuerpo ni en el pliegue plano: se acepta el valor de %s\,m/s.

\subsection{Incertidumbre del descenso}
\que Qué parámetros mueven más el resultado.
\porque Se muestrean 20\,000 casos con: fracción de vórtice $f\in[0;1]$, ataque $20\pm2{,}5^\circ$, resistencia del ala entre 0{,}02 y
0{,}05, del cuerpo ($C_D$ frontal de 0{,}6 a 1{,}0) y de la cola (0{,}005 a 0{,}02), densidad de 1{,}05 a 1{,}25\,kg/m$^3$ y masa
$\pm15$\,g. Los rangos son juicio del autor, no datos.
%s
\chequeo Por correlación de rangos, lo que más mueve el descenso del delta es %s. Es decir: la incertidumbre de la
sustentación de vórtice domina, y es justo la que no se puede resolver con cálculo.

\subsection{Comparación con un avión de ala recta}
\que Si un avión convencional con el mismo cuerpo, área y masa bajaría más lento o más rápido.
\porque Se toma un ala recta de la misma envergadura (alargamiento %s), perfil de placa curva a Reynolds $\approx8\cdot10^4$
($C_{D0}\approx0{,}04$), eficiencia de Oswald de 0{,}85 y $C_L$ de trim 0{,}8, con el mismo cuerpo romo y la misma cola. La
tabla~\ref{tab:aero_op} ya lo incluye. Su descenso depende del trim, de modo que con el elevador se regula de %s\,m/s ($C_L=0{,}4$)
a %s\,m/s ($C_L=1{,}0$).
\chequeo El avión recto baja más lento (%s\,m/s) y llega más lejos, pero con una ojiva en la nariz baja a %s\,m/s, cerca del
límite inferior de 2\,m/s. Los dos cumplen C4 con este modelo. Su dispersión es de %s a %s\,m/s, dominada por el trim. No está
diseñado ni analizado estructuralmente: sus números son de orden de magnitud.

\subsection{Estabilidad longitudinal estática}
\que Si el centro de gravedad queda delante del punto neutro, con margen suficiente.
\porque Estimación de orden de magnitud, sin método de sustentación para el momento. El centro aerodinámico del ala se toma entre
el 25\,\%% de la cuerda media (0{,}50 de la cuerda de raíz) y el límite de ala esbelta (0{,}67); la cola de la nota de cola
(80\,cm$^2$, brazo de 217\,mm, pendiente $%s$/rad, $\eta=0{,}9$, $d\varepsilon/d\alpha=%s$) aporta el factor $k=%s$ de
la pendiente del ala ($a_w=%s$/rad); el cuerpo desestabiliza por efecto Munk ($k_2-k_1$ entre 0{,}5 y 0{,}7), lo que corre el punto
neutro %s a %s\,mm hacia la nariz.
%s
\begin{resultado}Punto neutro del conjunto: %s a %s\,mm desde la nariz. Centro de gravedad en vuelo: %s\,mm. Margen estático:
de $%s$ a $%s$ de la cuerda media. El margen puede ser negativo: no se puede asegurar la estabilidad con este modelo.
\end{resultado}
\chequeo Para tener 10\,\%% de margen aun en el peor caso el CG tendría que estar en %s\,mm, unos %s\,mm más adelante.
Mover la batería 60\,mm hacia la nariz corre el CG solo %s\,mm, de modo que hace falta más: lastre en la nariz, una cola
mayor o ambas. El centro de gravedad en vuelo supone el CanSat completo con la tela y la cola abiertas, con las masas de la nota. Lo que falta es medir
el punto neutro en una maqueta o en un túnel.

\subsection{Lo que falta}
\begin{itemize}
\item Caída de una maqueta a escala, con y sin vórtice, filmada: da $w$, el ángulo de planeo y el trim.
\item Medida del punto neutro y del momento de cabeceo: el método de Polhamus no los da.
\item Estabilidad lateral y direccional: la nota anterior halló un Dutch roll inestable a $\alpha=20^\circ$ ($\zeta\approx-0{,}27$);
no se rehízo con esta geometría.
\item Deriva por viento: con $w\approx5$\,m/s y 400\,m de altura el planeador está en el aire unos 80\,s.
\item Efecto de la panza de la membrana, del flameo y del Reynolds bajo en $C_L$ y $C_D$.
\end{itemize}
""" % (
        n(r["m"] * 1000, 0), r["S"] * 1e4, n(o["w"], 1), n(o["V"], 1), n(o["LD"], 1), n(mcd[0], 1), n(mcd[2], 1),
        t_datos, n(r["control_nota"], 2), n(PH["Kp"], 2), n(PH["Kv"], 2), t_cl,
        _fig("polhamus.png", 0.95, "Izquierda: sustentación según Polhamus para alargamiento 4. Derecha: descenso contra la fracción de vórtice."),
        n(r["DB"] * 1000, 0), t_cd,
        n(cdd["cuerpo_axial"] + cdd["cuerpo_cruzado"], 2), n(o["CD"], 2), n(r["w_sin_cuerpo"], 1), n(o["w"], 1), n(ojv["delta"]["w"], 1),
        t_op.replace(r"\caption{", r"\caption{\label{tab:aero_op}", 1),
        _fig("planeo.png", 1.0, "Izquierda: polar de velocidades. Derecha: dispersión del descenso con las incertidumbres."),
        _fig("aero_resistencia.png", 1.0, "Resistencia por componente, descenso contra el ángulo de ataque y contra la masa."),
        n(r["w_alfa"]["0.5"][2][1], 1), n(o["w"], 1), n(r["w_alfa"]["0.5"][10][1], 1), n(o["w"], 1), n(8 - o["w"], 1), n(o["w"], 1),
        t_mc, rank(sd, "delta").replace("(", "$(").replace(")", ")$"),
        n(pl.AR_PL, 1), n(7.67, 1), n(2.85, 1), n(nom["recta"]["w"], 1), n(ojv["recta"]["w"], 1), n(mcr[0], 1), n(mcr[2], 1),
        n(E["at"], 1), n(E["de"], 2), n(E["k"], 3), n(E["aw"], 1), n(E["sh_b"][0], 0), n(E["sh_b"][1], 0),
        _fig("aero_estabilidad.png", 1.0, "Posición del centro de gravedad frente al punto neutro estimado, medidas desde la nariz."),
        n(E["np"][0], 0), n(E["np"][1], 0), n(E["x_cg"], 0), "%+.0f" % (100 * SM[0]) + r"\,\%", "%+.0f" % (100 * SM[1]) + r"\,\%",
        n(E["cg_req"], 0), n(E["dcg"], 0), n(E["dcg_bat"], 1))
    D = r["dist"]
    V = D["varilla"]
    def fila(c, nom, caso):
        x = V[f"{c}_{caso}"]
        return [nom, n(x["M_apice"], 0), n(x["M_J"], 0), n(x["sigma_LE"], 0), n(x["flecha_z_punta"], 1)]
    t_val = _tab("lccc", ["Comprobación del VLM", "VLM", "Referencia", "Diferencia"], [
        ["Ala rectangular $A=6$: $dC_L/d\\alpha$ [1/rad]", n(D["valid"]["rect_AR6"], 2), "%s (Helmbold)" % n(D["valid"]["helmbold_AR6"], 2),
         "%+.1f" % (100 * (D["valid"]["rect_AR6"] / D["valid"]["helmbold_AR6"] - 1)) + r"\,\%"],
        ["Delta $A=4$: $K_p$ [1/rad]", n(D["valid"]["delta_AR4"], 2), "%s (fig. 6 de NASA)" % n(D["valid"]["paper_Kp_AR4"], 2),
         "%+.1f" % (100 * (D["valid"]["delta_AR4"] / D["valid"]["paper_Kp_AR4"] - 1)) + r"\,\%"],
    ], "Comprobación del método de red de vórtices.", r"\footnotesize")
    t_dist = _tab("lc", ["Resultado", "Valor"], [
        ["Área de la planta con el cuerpo / expuesta (membrana)", "%s / %s\\,cm$^2$" % (n(D["S_gross_cm2"], 0), n(D["S_exp_cm2"], 0))],
        ["Alargamiento de la planta completa", n(D["AR_gross"], 2)],
        ["$K_p$ de la planta real (referido al área total)", "%s\\,/rad" % n(D["Kp"], 2)],
        ["Centro aerodinámico lineal", "%s\\,mm (%s de la cuerda de raíz)" % (n(D["x_ac"], 0), n(D["x_ac_cr"], 2))],
        ["Centro de la fuerza de vórtice", "%s\\,mm (%s)" % (n(D["x_v"], 0), n(D["x_v_cr"], 2))],
        ["Fuerza normal potencial / de vórtice, en vuelo", "%s / %s\\,N" % (n(D["N_pot"], 2), n(D["N_vor"], 2))],
        ["Parte que cae sobre la membrana expuesta", "%.0f\\,\\%% (potencial), %.0f\\,\\%% (vórtice)" % (100 * D["pot_frac_exp"], 100 * D["vor_frac_exp"])],
        ["Presión uniforme equivalente sobre la membrana", "%s\\,Pa (nota: 122)" % n(D["p_unif"], 0)],
        ["Presión dinámica y velocidad de diseño", "%s\\,Pa, %s\\,m/s" % (n(D["q"], 0), n(D["V_dist"], 1))],
    ], "Distribución aerodinámica a $\\alpha=20^\\circ$ con $f=0{,}5$.", r"\footnotesize")
    t_var = _tab("lcccc", ["Caso", "$M$ ápice", "$M$ en J", r"$\sigma$ varilla", "Flecha"], [
        fila("uniforme", "Presión uniforme, vuelo", "vuelo"), fila("distribuida", "Distribuida, vuelo", "vuelo"), "-",
        fila("uniforme", "Presión uniforme, apertura (3$\\times$)", "apertura"), fila("distribuida", "Distribuida, apertura (3$\\times$)", "apertura"),
    ], "Varilla de borde de ataque: momentos en N$\\cdot$mm, tensión en MPa, flecha en mm.", r"\footnotesize")
    Eg = r["est"]
    nvA, nuA = V["distribuida_apertura"], V["uniforme_apertura"]
    wa = D["w_area"]
    nuevo = r"""\subsection{Distribución de carga sobre el ala}
\que Cómo se reparte la fuerza aerodinámica en la planta del ala, qué parte llega a la membrana y a la varilla de borde de ataque, y dónde
actúa.
\porque El ala no es el delta completo de la nota: los pivotes están a 34\,mm del eje y la planta real tiene el borde de ataque recto en
el centro, donde va el cuerpo, y 45° de flecha afuera. Su área con el cuerpo es de %s\,cm$^2$ y la de membrana de %s\,cm$^2$ (la nota usa
394). El alargamiento de la planta completa es %s, dentro de lo ensayado por Polhamus. Se calcula en dos partes:
\begin{itemize}
\item \textbf{Potencial.} Red de vórtices (VLM) de placa plana sobre la planta continuada a través del cuerpo, con %d paneles. Da la
carga $\Delta C_p(x,y)$ y se escala con $\mathrm{sen}\,\alpha\cos\alpha$, como en Polhamus.
\item \textbf{Vórtice.} La fuerza normal $f\,K_v\,q\,S\,\mathrm{sen}^2\alpha$ se reparte a lo largo del borde como en un ala esbelta,
proporcional a la semienvergadura local, y hacia adentro del borde con una huella triangular centrada en $0{,}70$ de la semienvergadura
(hipótesis del autor).
\end{itemize}
%s
%s
%s
\chequeo La presión uniforme equivalente (%s\,Pa) coincide con los 122\,Pa de la nota. El VLM es lineal: da la forma de la carga
potencial, pero no el pico de borde de ataque, que en flujo real se desprende y lo reemplaza el vórtice; la huella del vórtice es una
hipótesis, el total no. El %.0f\,\%% de la fuerza cae sobre la membrana; el resto lo toma el cuerpo. Con el área efectiva de la planta real
($%s$\,cm$^2$) el descenso baja de %s a %s\,m/s, y a %s\,m/s si el cuerpo carga todo el centro (%s\,cm$^2$): el valor de la sección anterior,
calculado con los 394\,cm$^2$ de la nota, es conservador.

\subsection{Efecto de la distribución sobre la varilla}
\que Cuánto cambian los esfuerzos de la varilla de borde de ataque al usar la carga real en lugar de la presión uniforme.
\porque La reacción de cada tira de membrana sobre la varilla se calcula con la presión local, y el pórtico de la sección del ala se
resuelve con esa carga, en vuelo y en la apertura (tres veces la de vuelo).
%s
\chequeo El momento en el ápice y la tensión casi no cambian (%+.0f\,\%% y %+.0f\,\%%); en la articulación J el momento sube %+.0f\,\%% (de %s
a %s\,N$\cdot$mm), %+.0f\,\%% sobre los 424 de la nota. El manguito trabaja a unos %s\,MPa contra 402 admisibles: el dimensionamiento no cambia.

\subsection{Centro de presión y estabilidad longitudinal estática}
\que Dónde actúa la fuerza del ala y si el centro de gravedad queda delante del punto neutro, con margen suficiente.
\porque El punto neutro del ala sale de las derivadas de las dos partes: el potencial actúa en el centro aerodinámico (%s\,mm) y el
vórtice a %s\,mm. A $\alpha=20^\circ$ el centro de presión del ala está en %s\,mm y su punto neutro en %s\,mm (de %s a %s\,mm según $f$);
el vórtice lo corre hacia atrás con el ataque. Para el conjunto se suma la cola de la nota de cola (80\,cm$^2$, brazo de 217\,mm,
pendiente $%s$/rad, $\eta=0{,}9$, $d\varepsilon/d\alpha=%s$), que aporta el factor $k=%s$ de la pendiente del ala, y el cuerpo, que desestabiliza
por efecto Munk ($k_2-k_1$ entre 0{,}5 y 0{,}7) y corre el punto neutro %s a %s\,mm hacia la nariz.
%s
%s
\begin{resultado}Punto neutro del conjunto: %s a %s\,mm desde la nariz (%s en el caso central). Centro de gravedad en vuelo: %s\,mm. Margen estático
de $%s$ a $%s$ de la cuerda media ($%s$ en el caso central): \textbf{negativo en todo el rango}. Según esta estimación el planeador sería
inestable en cabeceo con la cola de 80\,cm$^2$.\end{resultado}
\chequeo Para $10\,\%%$ de margen aun en el peor caso hace falta una cola de %s\,cm$^2$ con el mismo brazo (%s\,cm$^2$ en el caso central),
o llevar el centro de gravedad a %s\,mm, unos %s\,mm más adelante. Mover la batería 60\,mm hacia la nariz lo corre solo %s\,mm, y el lastre
necesario sería de más de 200\,g, que no hay: la solución es la cola. Es una estimación de orden de magnitud: el punto neutro de la maqueta
puede diferir de éste, y la cola de la nota de cola no se dimensionó para esta ala.

""" % (n(D["S_gross_cm2"], 0), n(D["S_exp_cm2"], 0), n(D["AR_gross"], 2), D["n_paneles"], t_val, t_dist,
       _fig("aero_distribucion.png", 1.0, "Presión de diseño en vuelo, carga en la envergadura y reacción sobre la varilla."),
       n(D["p_unif"], 0), 100 * D["share_exp"], n(wa["expuesta"]["S_cm2"], 0), n(wa["nota"]["w"], 1), n(wa["expuesta"]["w"], 1),
       n(wa["total"]["w"], 1), n(wa["total"]["S_cm2"], 0), t_var,
       100 * (nvA["M_apice"] / nuA["M_apice"] - 1), 100 * (nvA["sigma_LE"] / nuA["sigma_LE"] - 1), 100 * (nvA["M_J"] / nuA["M_J"] - 1),
       n(nuA["M_J"], 0), n(nvA["M_J"], 0), 100 * (nvA["M_J"] / 424 - 1), n(nvA["M_J"] * 4 / 167.8, 0),
       n(D["x_ac"], 0), n(D["x_v"], 0), n(D["xcp_20"]["0.5"], 0), n(D["xnp_20"]["0.5"], 0), n(D["xnp_20"]["0"], 0), n(D["xnp_20"]["1"], 0),
       n(Eg["at"], 1), n(Eg["de"], 2), n(Eg["k"], 3), n(Eg["sh_b"][0], 0), n(Eg["sh_b"][1], 0),
       _fig("aero_cp.png", 1.0, "Izquierda: centro de presión y punto neutro del ala contra el ataque. Derecha: fuerza que llega a la varilla."),
       _fig("aero_estabilidad.png", 1.0, "Posición del centro de gravedad frente al punto neutro estimado, medidas desde la nariz."),
       n(Eg["np"][0], 0), n(Eg["np"][1], 0), n(Eg["np_c"], 0), n(Eg["x_cg"], 0),
       "%+.0f" % (100 * Eg["SM"][0]) + r"\,\%", "%+.0f" % (100 * Eg["SM"][1]) + r"\,\%", "%+.0f" % (100 * Eg["SM_c"]) + r"\,\%",
       n(Eg["St_req_lo"], 0), n(Eg["St_req_c"], 0), n(Eg["cg_req"], 0), n(Eg["dcg"], 0), n(Eg["dcg_bat"], 1))
    i0 = s.index("\\subsection{Estabilidad longitudinal estática}")
    i1 = s.index("\\subsection{Lo que falta}")
    s = s[:i0] + nuevo + s[i1:]
    s = s.replace("La\nestabilidad longitudinal no se puede asegurar con este nivel de modelo: el centro de gravedad cae dentro del rango de incertidumbre\ndel punto neutro.",
                  "Según\nla estimación de la sección, con la cola de 80\\,cm$^2$ el punto neutro queda por delante del centro de gravedad: hace falta una cola mayor.")
    s = s.replace("@@W368@@", n(pl.sink(*pl.delta(20.0), m=0.3675)[0], 1))
    return s + _tab("lcc", ["Parámetro", "Delta", "Avión recto"], [
        ["Parámetro que más lo mueve", sd[0][0], sr[0][0]], ["Correlación de rangos", "%+.2f" % sd[0][1], "%+.2f" % sr[0][1]]],
        "Sensibilidad del descenso (correlación de rangos de Spearman).").replace("%+.2f", "").replace(".", "{,}") if False else s


PREAMBULO = r"""\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{lmodern}
\usepackage[spanish,es-nodecimaldot,es-tabla]{babel}
\usepackage[a4paper,margin=2.2cm]{geometry}
\usepackage{graphicx,booktabs,float,amsmath,amssymb,textcomp,xcolor,fancyhdr,enumitem,caption,microtype}
\usepackage[most]{tcolorbox}
\usepackage[colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black]{hyperref}
\captionsetup{font=small,labelfont=bf}
\newcommand{\diam}{\ensuremath{\varnothing}}
\newcommand{\que}{\par\smallskip\noindent\textbf{Qué se calcula.}\ }
\newcommand{\porque}{\par\smallskip\noindent\textbf{Por qué.}\ }
\newcommand{\chequeo}{\par\smallskip\noindent\textbf{Chequeo.}\ }
\newtcolorbox{resultado}{colback=black!6,colframe=black!6,boxrule=0pt,arc=0pt,left=6pt,right=6pt,top=4pt,bottom=4pt,fontupper=\small}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small Aerodinámica del planeador de ala delta}\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}\setlength{\parindent}{1.2em}\setlist{nosep,leftmargin=1.6em}
\begin{document}
\begin{center}
{\LARGE\bfseries Aerodinámica del planeador de ala delta\par}\smallskip
{\large Sustentación, resistencia, velocidad de descenso y estabilidad longitudinal\par}
\medskip {\large %s %s · %s · revisión %s\par}
\end{center}
"""


def main():
    r = calcular()
    frag = fragmento(r)
    frag = frag.replace(r"\,\%$", r"$\,\%")
    tex = PREAMBULO % (P.EQUIPO, P.TEMPORADA, P.FECHA, P.REV) + frag + "\n\\end{document}\n"
    open(os.path.join(BUILD, "aero.tex"), "w", encoding="utf-8").write(tex)
    for _ in range(2):
        p = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "aero.tex"], cwd=BUILD, capture_output=True, text=True,
                           errors="replace")
    if p.returncode != 0:
        print(p.stdout[-2500:])
        return
    shutil.copy(os.path.join(BUILD, "aero.pdf"), os.path.join(BASE, "Aerodinamica_Planeador.pdf"))
    print("ok:", re.findall(r"Output written.*", p.stdout)[-1])
    print("overfull:", len(re.findall(r"Overfull \\hbox", p.stdout)), "undefined:", len(re.findall(r"undefined", p.stdout)))
    json.dump({k: v for k, v in r.items() if k in ("op", "est", "cd_delta", "cd_recta", "w_sin_cuerpo", "w500")},
              open(os.path.join(FEA, "aero.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
