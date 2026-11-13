"""Informe del PDR mecanico en LaTeX (articulo, estilo de las notas tecnicas del equipo).
Uso: python3 build_informe.py     -> ../PDR_Mecanica_CanSat_AlaDelta.pdf
"""
import os, json, math, subprocess, shutil
from PIL import Image
import params as P
import fe_model as F
import aero_planeador as AP

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIGS, FEA, PLANOS, BUILD = (os.path.join(BASE, d) for d in ("figs", "fea", "planos", "build"))
os.makedirs(os.path.join(BUILD, "img"), exist_ok=True)
R = json.load(open(os.path.join(FEA, "resultados_fea.json")))
RIG = json.load(open(os.path.join(FEA, "iteracion_rigida.json")))
MAS = json.load(open(os.path.join(FEA, "masas.json")))
ALA = json.load(open(os.path.join(FEA, "ala_desplegada.json")))
VER = json.load(open(os.path.join(FEA, "verificacion_viga.json")))
PL500 = json.load(open(os.path.join(FEA, "planeo_500g.json")))
EJES = "xyz"
MT = P.MAT


def n(x, d=1):
    return f"{x:.{d}f}".replace(".", "{,}")


def ms(x):
    s = f"{x:+.2f}".replace(".", "{,}").replace("+", "$+$").replace("-", "$-$")
    return r"\textbf{\color{red!70!black}" + s + "}" if x < 0 else s


def fig(name, w=1.0, cap="", lab="", src=FIGS, maxpx=1700):
    dst = os.path.join(BUILD, "img", os.path.splitext(name)[0] + ".jpg")
    i = Image.open(os.path.join(src, name)).convert("RGB")
    if max(i.size) > maxpx:
        i.thumbnail((maxpx, maxpx), Image.LANCZOS)
    i.save(dst, quality=90)
    return (r"\begin{figure}[H]\centering\includegraphics[width=%s\linewidth]{img/%s}" % (w, os.path.basename(dst))
            + (r"\caption{%s}" % cap if cap else "") + (r"\label{%s}" % lab if lab else "") + r"\end{figure}")


def fig2(a, b, cap, wa=0.48, wb=0.48):
    out = [r"\begin{figure}[H]\centering"]
    for name, w in ((a, wa), (b, wb)):
        dst = os.path.join(BUILD, "img", os.path.splitext(name)[0] + ".jpg")
        i = Image.open(os.path.join(FIGS, name)).convert("RGB")
        i.thumbnail((1500, 1500), Image.LANCZOS)
        i.save(dst, quality=90)
        out.append(r"\includegraphics[width=%s\linewidth]{img/%s}\hfill" % (w, os.path.basename(dst)))
    out.append(r"\caption{%s}\end{figure}" % cap)
    return "".join(out)


def tab(cols, cab, filas, cap=None, fs=r"\small"):
    o = [r"\begin{table}[H]\centering" + fs, r"\begin{tabular}{%s}\toprule" % cols, " & ".join(cab) + r"\\ \midrule"]
    for f_ in filas:
        o.append(r"\midrule" if f_ == "-" else " & ".join(str(c) for c in f_) + r"\\")
    o.append(r"\bottomrule\end{tabular}")
    if cap:
        o.append(r"\caption{%s}" % cap)
    o.append(r"\end{table}")
    return "\n".join(o)


def caja(t):
    return r"\begin{resultado}" + t + r"\end{resultado}"


def M_(caso, eje=None):
    return (R[caso] if eje is None else R[caso][eje])["margenes"]


def peor(caso, clave, res=R):
    best = None
    for e in ([None] if caso == "paracaidas" else list(EJES)):
        d = (res[caso] if e is None else res[caso][e])["margenes"]
        for k, v in d.items():
            g, c = [s.strip() for s in k.split("|")]
            if g.startswith(clave) and (best is None or v["MS"] < best[0]):
                best = (v["MS"], v["sigma"], e or "x", c, v)
    return best


GRUPOS = ["Contenedor: tubo", "Contenedor: tapa", "Cuadernas", "Paneles y bandeja", "Largueros", "PCB", "Soportes de equipos",
          "Llave de bayoneta"]
GNOM = {"Contenedor: tubo": "Tubo del contenedor (LW-PLA)", "Contenedor: tapa": "Tapa nervada (PA12-CF)",
        "Cuadernas": "Cuadernas, cunas y guías (PA12-CF)", "Paneles y bandeja": "Paneles y bandeja (G10)",
        "Largueros": "Largueros (CFRP)", "PCB": "Placas (FR-4)", "Soportes de equipos": "Separadores y sillas (PA12-CF)",
        "Llave de bayoneta": "Llave de bayoneta (A2-70)"}
CNOM = {"von Mises": "von Mises", "sigma_x entre capas": r"$\sigma_x$ entre capas", "sigma_x fibra": r"$\sigma_x$ de fibra",
        "corte interlaminar": "corte interl."}

# ------------------------------------------------------------------ datos derivados
G0 = P.G0
m_plan, m_cont = MAS["m_planeador"], MAS["m_contenedor"]
F_ret = m_plan / 1000 * 30 * G0 * 1.8
F_par = 0.5 * 30 * G0 * 1.8
f, zm, fel, mef = R["freq"], R["zeta_modal"], R["f_elast"], R["m_eff"]


def modo_dom(d):
    i = max(range(len(f)), key=lambda k: mef[k][d])
    return i, f[i], mef[i][d] / R["masa_g"] * 100


def desc(i):
    fr = [mef[i][d] / R["masa_g"] * 100 for d in range(3)]
    return "local" if max(fr) < 2 else ["axial $x$", "lateral $y$", "lateral $z$"][fr.index(max(fr))]


ix, fx, mx = modo_dom(0)
iy, fy, my = modo_dom(1)
iz, fz, mz = modo_dom(2)
pt, nt = ALA["portico"], ALA["nota"]
leg = F_par / (3 * math.cos(math.radians(35)))
sb_brida = leg / (3.0 * P.CT_CAP_RIB)
tau_tapa = F_par / (math.pi * 2 * P.CT_RI * P.CT_CAP_H)
tau_pas = F_ret / (2 * math.pi * 1.5 ** 2)
sig_llave = F_ret / (math.pi * (P.KEY_D / 2) ** 2)
A_iso = math.pi * (P.WASH_D ** 2 - P.KEY_HOLE ** 2) / 4
Ec_iso = F.elastico("ELAST_X")[1]["E1"]
k_iso = Ec_iso * A_iso / P.ISO_T
sb_cubo = F_ret / A_iso
tau_lon = (F_ret / 4) / (math.pi * P.LON_DO * 5.0)
F_perno = nt["M_apice"] / 8.0
sig_slv = nt["M_J"] * (P.SLV_DO / 2) / (math.pi * (P.SLV_DO ** 4 - P.SLV_DI ** 4) / 64)
ms_all = [(peor(c, g)[0], g, c) for g in GRUPOS for c in ("cuasi15", "armonico", "choque", "paracaidas")]
ms_min = min(ms_all)
neg = sorted(x for x in ms_all if x[0] < 0)
CASO = {"cuasi15": "casi-estático de 15\,G", "armonico": "respuesta en frecuencia a 15\,G", "choque": "choque de 30\,G",
        "paracaidas": "tirón del paracaídas"}
tubo_m = next(x["masa"] for x in MAS["filas"] if "Tubo" in x["item"])
tapa_m = next(x["masa"] for x in MAS["filas"] if "Tapa nervada" in x["item"])
est_m = MAS["sub"]["Estructura del planeador"]["masa"]
ms_arm = min(peor("armonico", g)[0] for g in GRUPOS)
ms_ch = min(min(peor("choque", g)[0], peor("paracaidas", g)[0]) for g in GRUPOS)
ms_ce = min(peor("cuasi15", g)[0] for g in GRUPOS)
if neg:
    txt_neg = ("Quedan %d combinaciones con margen negativo: %s. Se detallan, con su corrección, en la sección de márgenes." % (
        len(neg), "; ".join("%s en el caso %s (%s)" % (GNOM[g], CASO[c], ms(v)) for v, g, c in neg[:4])))
else:
    txt_neg = "Todos los márgenes son positivos."

# ------------------------------------------------------------------ tablas
t_req = tab(r"lp{6.3cm}p{6.6cm}", ["N.º", "Requisito", "Cómo lo cumple el diseño"], [
    ["C1--C3", "El contenedor va dentro del fuselaje, sale con la carga de expulsión y baja a $15\\pm3$\,m/s con paracaídas.",
     "Contenedor cilíndrico liso; paracaídas alojado sobre la tapa, brida de tres puntos."],
    ["C4", "Al 80\,\\% de la altitud máxima se libera otro sistema de descenso: $5\\pm3$\,m/s.",
     "Planeador de ala delta; estimado %s\,m/s con %s\,g en vuelo." % (n(MAS["w_estimado"]), n(MAS["m_vuelo"], 0))],
    ["S1", "Masa de CanSat y contenedor: $500\\pm10$\,g.", "Presupuesto de 500\,g con %s\,g de lastre." % n(MAS["lastre"], 0)],
    ["S2, S3", "Diámetro 90\,mm; largo total de 200 a 250\,mm.", "Contenedor de \\diam90 $\\times$ %g\,mm." % P.CT_LEN],
    ["S4", "Soportar vibraciones de 15\,G.", "Casi-estático y barrido senoidal de 15\,G en tres ejes (FEA)."],
    ["S5", "Soportar un choque de 30\,G.", "Semiseno de 30\,G en tres ejes y tirón del paracaídas (FEA)."],
    ["S6", "Pared exterior de al menos 2\,mm si es impresa; rígida.", "Tubo impreso con pared de 2{,}0\,mm."],
    ["S7", "El cilindro puede retener piezas desplegables y debe deslizar libre.", "La pared retiene las alas plegadas; exterior sin salientes."],
    ["S8, S9", "Montaje fijo; materiales no contaminantes.", "Tornillos con inserto, separadores y epoxi; LW-PLA y PA12-CF."],
    ["M1--M4", "Sin pirotecnia ni calor expuesto; los mecanismos mantienen su estado; sin contactos de resorte en baterías.",
     "Un servo y resortes. La carga de retención no pasa por el servo. Celda con lengüetas soldadas."],
    ["E3--E6", "Paneles solares; interruptor accesible; orificios de hasta 10\,mm; indicador.",
     "Celdas sobre la tapa del planeador; orificios de \\diam8 y \\diam5 en la pared."],
], "Requisitos del Apéndice A que tocan al subsistema mecánico.", r"\footnotesize")

t_conf = tab(r"p{4.6cm}p{4.9cm}p{4.9cm}", ["Criterio", "A: cuerpo integral con ranuras", "B: contenedor + planeador"], [
    ["Pared exterior rígida de 2\,mm (S6)", "Parcial: pared cortada en dos tejas", "Cumple: tubo cerrado"],
    ["Deslizamiento libre (S7)", "Riesgo: varillas contra el fuselaje", "Cumple: exterior liso"],
    ["Orificios de hasta 10\,mm (E5)", "No cumple: ranuras de $16\\times200$", "Cumple: \\diam8 y \\diam5"],
    ["Despliegue del ala", "Activo: trabas y servo", "Pasivo: resortes"],
    ["Masa que vuela con el ala", "500\,g", "%s\,g si el contenedor se separa; 500\,g si no" % n(m_plan, 0)],
    ["Velocidad de descenso estimada", "%s\,m/s (500\,g)" % n(MAS["w_estimado"]), "%s\,m/s (368\,g) o %s\,m/s (500\,g)" % (n(MAS["w_planeador_solo"]), n(MAS["w_estimado"]))],
    ["Objetos que descienden", "Uno", "Dos (el contenedor baja con su paracaídas)"],
], "Comparación de las dos configuraciones de sistema.")

t_mat = tab("lccccp{5.2cm}", ["Material", r"$\rho$ [g/cm$^3$]", "$E$ [GPa]", "Resist. [MPa]", "Entre capas", "Uso"], [
    ["PLA+ impreso", n(MT["PLA"]["rho"], 2), n(MT["PLA"]["E"] / 1e3), "%d" % MT["PLA"]["Sut"], "%d" % MT["PLA"]["Sut_z"], "Descartado: frágil, ablanda a 55\,°C"],
    ["PETG impreso", n(MT["PETG"]["rho"], 2), n(MT["PETG"]["E"] / 1e3), "%d" % MT["PETG"]["Sut"], "%d" % MT["PETG"]["Sut_z"], "Descartado: pesado y poco rígido"],
    ["PA12-CF impreso", n(MT["PA12CF"]["rho"], 2), n(MT["PA12CF"]["E"] / 1e3), "%d" % MT["PA12CF"]["Sut"], "%d" % MT["PA12CF"]["Sut_z"], "Cuadernas, cunas y tapa del contenedor"],
    ["LW-PLA espumado", n(MT["LWPLA"]["rho"], 2), n(MT["LWPLA"]["E"] / 1e3), "%d" % MT["LWPLA"]["Sut"], "%d" % MT["LWPLA"]["Sut_z"], "Tubo del contenedor (pared de 2\,mm)"],
    ["G10 / FR-4", n(MT["G10"]["rho"], 2), n(MT["G10"]["E"] / 1e3, 0), "%d" % MT["G10"]["Sut"], "--", "Paneles de 0{,}5 y bandeja de 0{,}8\,mm"],
    ["CFRP pultruido", n(MT["CFRP"]["rho"], 2), n(MT["CFRP"]["E"] / 1e3, 0), "%d (compr.)" % MT["CFRP"]["Suc"], "50 (corte)", "Largueros y varillas del ala"],
    ["Aluminio 7075-T6", n(MT["AL7075"]["rho"], 2), n(MT["AL7075"]["E"] / 1e3, 0), "%d (fl.)" % MT["AL7075"]["Sy"], "--", "Manguito y herrajes del ala"],
    ["Inoxidable A2-70", n(MT["A2-70"]["rho"], 2), n(MT["A2-70"]["E"] / 1e3, 0), "%d (fl.)" % MT["A2-70"]["Sy"], "--", "Llave de bayoneta y pernos"],
    ["Elastómero 55 Sh A", n(MT["ELAST"]["rho"], 2), n(MT["ELAST"]["E"] / 1e3, 3), "--", "--", r"Aislador y patines ($\eta=%s$)" % n(MT["ELAST"]["eta"], 2)],
], "Materiales considerados. Valores típicos de hoja de datos; los de piezas impresas se confirman con probetas.", r"\footnotesize")

nm_t = min(10, len(f))
t_modal = tab("cccccl", ["Modo", "$f$ [Hz]", "Masa efectiva $x/y/z$ [\\%]", r"$\zeta$ [\%]", "Energía en elastómero [\\%]", "Tipo"], [
    [i + 1, n(f[i]), " / ".join("%.0f" % (mef[i][d] / R["masa_g"] * 100) for d in range(3)), n(zm[i] * 100), "%.0f" % (fel[i] * 100), desc(i)]
    for i in range(nm_t)], "Primeros modos de la configuración de lanzamiento.")

t_acc = tab("lcccccc", ["Punto", "$x$ [G]", "a [Hz]", "$y$ [G]", "a [Hz]", "$z$ [G]", "a [Hz]"], [
    [k] + sum([["%.0f" % (15 * R["armonico"][e]["trans_max"][k]), "%.0f" % R["armonico"][e]["f_trans_max"][k]] for e in EJES], [])
    for k in R["armonico"]["x"]["trans_max"]], "Pico de aceleración de respuesta para una entrada senoidal de 15\,G en la base.")


def fila_caso(caso, extra):
    out = []
    for g in GRUPOS:
        p = peor(caso, g)
        out.append([GNOM[g], CNOM[p[3]], n(p[1]), extra(p), ms(p[0])])
    return out


t_arm = tab("llccc", ["Grupo", "Criterio", r"$\sigma$ [MPa]", "$f$ crítica [Hz] (eje)", "MS"],
            fila_caso("armonico", lambda p: "%.0f (%s)" % (p[4]["f_crit"], p[2])),
            "Respuesta en frecuencia a 15\,G: peor resonancia de cada grupo.")
t_ch = tab("llccc", ["Grupo", "Criterio", r"$\sigma$ [MPa]", "Duración crítica (eje)", "MS"],
           fila_caso("choque", lambda p: "%.0f\,ms (%s)" % (p[4]["tau_crit"] * 1e3, p[2])),
           "Choque semiseno de 30\,G: peor duración y eje de cada grupo.")


def celda(caso, g):
    p = peor(caso, g)
    return ms(p[0])


t_ms = tab("lcccc", ["Grupo de piezas", "CE-15", "RF-15", "CH-30", "PA-30"],
           [[GNOM[g]] + [celda(c, g) for c in ("cuasi15", "armonico", "choque", "paracaidas")] for g in GRUPOS] + ["-",
            ["Varilla de borde de ataque", "--", "--", ms(400 / max(ALA["choque"][e]["sigma"] for e in EJES) - 1), ms(400 / pt["sigma_LE"] - 1) + " (apertura)"],
            ["Tirante (pandeo, $P_{cr}/N$)", "--", "--", "--", n(ALA["tirante"]["coef"])]],
           "Márgenes de seguridad mínimos sobre los tres ejes. CE: casi-estático; RF: resonancia; CH: choque; PA: paracaídas.")

t_un = tab("p{5.2cm}cccc", ["Unión", "Carga", "Tensión", "Admisible", "MS"], [
    ["Llave \\diam5, tracción", "%.0f N" % F_ret, n(sig_llave) + " MPa", "360 MPa", ms(360 / sig_llave - 1)],
    ["Pasador \\diam3 de la llave, corte doble", "%.0f N" % F_ret, n(tau_pas) + " MPa", "216 MPa", ms(216 / tau_pas - 1)],
    ["Asiento del aislador en la tapa", "%.0f N" % F_ret, n(sb_cubo, 2) + " MPa", "17{,}5 MPa", ms(17.5 / sb_cubo - 1)],
    ["Anclaje de brida en el nervio", "%.0f N" % leg, n(sb_brida) + " MPa", "32{,}5 MPa", ms(32.5 / sb_brida - 1)],
    ["Pegado tapa--tubo", "%.0f N" % F_par, n(tau_tapa, 2) + " MPa", "2{,}0 MPa", ms(2.0 / tau_tapa - 1)],
    ["Pegado de cada larguero en su buje", "%.0f N" % (F_ret / 4), n(tau_lon, 2) + " MPa", "9{,}0 MPa", ms(9.0 / tau_lon - 1)],
    ["Manguito \\diam8/5{,}1, flexión", "%.0f N$\\cdot$mm" % nt["M_J"], n(sig_slv) + " MPa", "402 MPa", ms(402 / sig_slv - 1)],
    ["Perno de pivote A \\diam2{,}5, corte", "%.0f N" % F_perno, n(F_perno / 4.91) + " MPa", "216 MPa", ms(216 / (F_perno / 4.91) - 1)],
    ["Oreja de C1, aplastamiento", "%.0f N" % F_perno, n(F_perno / 20) + " MPa", "32{,}5 MPa", ms(32.5 / (F_perno / 20) - 1)],
], "Verificación manual de uniones con la carga de diseño ($30\,\\mathrm{G}\\times1{,}8$).")

filas_m = []
for s_ in MAS["sub"]:
    filas_m.append([r"\textbf{%s}" % s_.replace("Avionica", "Aviónica"), "", "", "", ""])
    for x in MAS["filas"]:
        if x["sub"] == s_:
            filas_m.append([r"\quad " + x["item"].replace("avionica", "aviónica").replace("elastomerico", "elastomérico").replace("elastomero", "elastómero")
                            .replace("Bateria", "Batería").replace("bateria", "batería").replace("Camaras", "Cámaras").replace("Paracaidas", "Paracaídas")
                            .replace("eslabon", "eslabón").replace("Guias", "Guías").replace("botalon", "botalón").replace("Botalon", "Botalón")
                            .replace("x 201", r"$\times$ 201").replace("x 242", r"$\times$ 242").replace("d5/", r"\diam5/").replace("d90", r"\diam90"),
                            x["cant"], n(x["masa"]), r"$\pm$" + n(x["inc"]), x["fuente"].replace("Asignacion", "Asignación")])
    filas_m.append([r"\quad\emph{Subtotal}", "", r"\emph{%s}" % n(MAS["sub"][s_]["masa"]), r"$\pm$" + n(MAS["sub"][s_]["inc"]), ""])
    filas_m.append("-")
filas_m.append([r"\textbf{Total}", "", r"\textbf{%s}" % n(MAS["total"]), r"$\pm$" + n(MAS["inc_rss"]), "suma cuadrática"])
t_masa = tab("lcccl", ["Componente", "Cant.", "Masa [g]", "Incert. [g]", "Fuente"], filas_m, "Presupuesto de masa.", r"\footnotesize")

e1 = lambda a, b: ("%+.1f" % (100 * (a / b - 1))).replace(".", "{,}") + r"\,\%"
t_ver = tab("lccc", ["Magnitud", "Este método", "Analítico", "Diferencia"], [
    ["1.ª frecuencia de flexión [Hz]", n(VER["f_fem"][0]), n(VER["f_analitico"][0]), e1(VER["f_fem"][0], VER["f_analitico"][0])],
    ["2.ª frecuencia de flexión [Hz]", n(VER["f_fem"][1]), n(VER["f_analitico"][1]), e1(VER["f_fem"][1], VER["f_analitico"][1])],
    ["Flecha de punta a 1\,G [$\\mu$m]", n(VER["flecha_1g_fem"] * 1e3, 2), n(VER["flecha_1g_analitico"] * 1e3, 2), e1(VER["flecha_1g_fem"], VER["flecha_1g_analitico"])],
    ["Tensión en la raíz a 1\,G [MPa]", n(VER["sigma_raiz_fem"], 3), n(VER["sigma_raiz_analitico"], 3), e1(VER["sigma_raiz_fem"], VER["sigma_raiz_analitico"])],
    ["Punta en resonancia, 15\,G, $\\zeta=2\\,\\%$ [mm]", n(VER["arm_punta_fem"], 2), n(VER["arm_punta_analitico"], 2), e1(VER["arm_punta_fem"], VER["arm_punta_analitico"])],
    ["Punta bajo semiseno de 30\,G, 11\,ms [mm]", n(VER["choque_punta_fem"], 3), n(VER["choque_punta_1gdl"], 3), e1(VER["choque_punta_fem"], VER["choque_punta_1gdl"])],
], "Viga en voladizo de aluminio de $12\\times8\\times200$\,mm: la cadena de cálculo contra la solución analítica.")

t_ala = tab("lcccccc", ["Caso (367\,Pa, panza 6\,\\%)", "$M$ ápice", r"$\sigma$ varilla", "Flecha", "$M$ en J", "$N$ tirante", r"$\sigma$ tirante"], [
    ["Nota de membrana (publicado)", "680", "73", "4{,}9", "422", "9{,}79", "--"],
    ["Este modelo, hipótesis de la nota", "%.0f" % nt["M_apice"], "%.0f" % nt["sigma_LE"], n(nt["flecha_z_punta"]), "%.0f" % nt["M_J"], n(-nt["N_tirante"], 2), "--"],
    ["Este diseño (el tirante sostiene la punta)", "%.0f" % pt["M_apice"], "%.0f" % pt["sigma_LE"], n(pt["flecha_z_punta"]), "%.0f" % pt["M_J"], n(-pt["N_tirante"], 2), "%.0f" % pt["sigma_TE"]],
], "Varilla de borde de ataque bajo la presión de apertura. Momentos en N$\\cdot$mm, tensiones en MPa, flecha en mm, fuerza en N.", r"\footnotesize")

eje_arm = min(EJES, key=lambda e: min(v["MS"] for v in M_("armonico", e).values()))
eje_ch = min(EJES, key=lambda e: min(v["MS"] for v in M_("choque", e).values()))
rig_tapa = next(v for k, v in RIG["armonico"]["x"]["margenes"].items() if k.startswith("Contenedor: tapa") and "entre capas" in k)

# ------------------------------------------------------------------ documento
TEX = r"""\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{lmodern}
\usepackage[spanish,es-nodecimaldot,es-tabla]{babel}
\usepackage[a4paper,margin=2.2cm]{geometry}
\usepackage{graphicx,booktabs,float,amsmath,amssymb,textcomp,xcolor,fancyhdr,pdfpages,enumitem,caption,microtype}
\usepackage[most]{tcolorbox}
\usepackage[colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black]{hyperref}
\captionsetup{font=small,labelfont=bf}
\newcommand{\diam}{\ensuremath{\varnothing}}
\newcommand{\que}{\par\smallskip\noindent\textbf{Qué se calcula.}\ }
\newcommand{\porque}{\par\smallskip\noindent\textbf{Por qué.}\ }
\newcommand{\chequeo}{\par\smallskip\noindent\textbf{Chequeo.}\ }
\newtcolorbox{resultado}{colback=black!6,colframe=black!6,boxrule=0pt,arc=0pt,left=6pt,right=6pt,top=4pt,bottom=4pt,fontupper=\small}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small PDR del subsistema mecánico: CanSat de ala delta}\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}\setlength{\parindent}{1.2em}\setlist{nosep,leftmargin=1.6em}
\begin{document}
\begin{center}
{\LARGE\bfseries Subsistema mecánico y estructural del CanSat de ala delta\par}\smallskip
{\large Revisión preliminar de diseño (PDR): estructura, materiales, mecanismos, respuesta en frecuencia a 15\,G y choque de 30\,G\par}
\bigskip {\large <<EQUIPO>> <<TEMPORADA>>\par}\medskip {\large <<FECHA>> · revisión <<REV>>\par}
\end{center}
\begin{abstract}\noindent
Se diseña la estructura de un CanSat de 500\,g y \diam90\,mm cuyo segundo sistema de descenso es un planeador de ala delta de
membrana. La configuración elegida es un contenedor cilíndrico cerrado, de pared de 2\,mm, del que el planeador sale por la boca
inferior al 80\,\% de la altitud; la pared retiene las alas plegadas y el despliegue es pasivo. El planeador es un bastidor de
cuatro largueros de carbono, cuatro cuadernas impresas y paneles de G10 (<<EST_M>>\,g); el ala es un cuadrilátero articulado que
pliega plano y conserva la cuerda de raíz de 198{,}6\,mm de la nota de membrana. Un modelo de elementos finitos de
<<NEL>>~tetraedros cuadráticos da el primer modo en <<F1>>\,Hz. La primera versión, con la llave de retención unida rígidamente,
amplificaba <<RIG_T>>~veces el modo axial y dejaba la tapa sin margen en resonancia; con un anillo elastomérico bajo la llave el
amortiguamiento de ese modo sube a <<ZAX>>\,\% y la amplificación baja a <<T_AX>>. Los márgenes mínimos son <<MS_CE>> en
casi-estático a 15\,G, <<MS_ARM>> en resonancia a 15\,G y <<MS_CH>> en choque de 30\,G y tirón del paracaídas. <<TXT_NEG>>
El resultado de resonancia depende del amortiguamiento del elastómero, que es lo primero que hay que medir.
\end{abstract}
\tableofcontents

\section{Alcance y requisitos}
\que Qué exige el Apéndice~A al subsistema mecánico y cómo se interpretan los dos requisitos de carga.
\porque La tabla~\ref{tab:req} resume los requisitos y la respuesta del diseño. S4 y S5 dicen «15\,G» y «30\,G» sin definir cómo
se aplican. Se tomó la lectura más exigente: 15\,G como aceleración casi-estática \emph{y} como amplitud de un barrido senoidal de
5 a 1000\,Hz en la base; 30\,G como pulso semiseno en la base, con la duración barrida de 1 a 20\,ms, \emph{y} como tirón del
paracaídas con un factor de amplificación dinámica de 1{,}8.
<<T_REQ>>
\chequeo Factores de seguridad: 1{,}25 a fluencia en metales, 1{,}5 en laminados y 2{,}0 en piezas impresas. El margen se define
como $MS=\sigma_{adm}/(FS\,\sigma)-1$ y se pide $MS\ge0$. Conviene confirmar con la organización el procedimiento de ensayo de
vibración y de choque.

\section{Configuración del sistema}
\que Cómo se reparte el CanSat entre contenedor y carga útil.
\porque Hay dos formas de alojar un ala desplegable en un cilindro de \diam90. En la primera el cilindro es el fuselaje y las alas
salen por ranuras laterales. En la segunda el cilindro es un contenedor cerrado y el planeador sale entero por la boca
(tabla~\ref{tab:conf}).
<<T_CONF>>
<<FIG_CONF>>
\chequeo Se elige B. Es la única que cumple S6, S7 y E5 al pie de la letra, el ala se abre sola al salir del cilindro y la carga
alar baja. El costo es que el contenedor (<<M_CONT>>\,g con paracaídas) no vuela con el ala. Si el equipo prefiere A, el bastidor
y el ala de este informe valen igual; hay que rehacer el análisis del tubo ranurado.
\begin{resultado}\textbf{Masa de vuelo.} El CanSat completo (contenedor, paracaídas y planeador) suma 500\,g y nada queda fuera del
presupuesto (sección~\ref{sec:masa}). En esta configuración el contenedor (<<M_CONT>>\,g) se separa y el planeador vuela con <<MPLAN>>\,g:
baja a <<W368>>\,m/s. Si todo el CanSat bajara con el ala (500\,g) serían <<W>>\,m/s; la aerodinámica de la sección~\ref{sec:aero} se
calculó con esos 500\,g, el caso más desfavorable. Los dos valores cumplen C4 ($5\pm3$\,m/s). El Apéndice A no dice si el contenedor
baja con el ala; si el equipo lo exige, la configuración B no sirve como está dibujada y hay que pasar al cuerpo integral (opción A).
\end{resultado}
<<FIG_CONOPS>>

\section{Dimensiones}
\que Las medidas principales en lanzamiento, estibado y en vuelo.
\porque S3 admite hasta 250\,mm de largo. Eso permite un planeador de <<LG>>\,mm, que deja lugar a los pernos de pivote a 4{,}2\,mm
de cada extremo sin recortar el ala: la distancia entre pivotes A y B es de <<DAB>>\,mm, la cuerda de raíz de la nota de membrana.
<<FIG_LAN>>
<<FIG_EST>>
<<FIG_DES>>
\begin{resultado}Contenedor: \diam90 $\times$ <<CTL>>\,mm, pared 2{,}0\,mm. Planeador estibado: \diam<<DPL>> $\times$ <<LG>>\,mm
(1\,mm de huelgo radial). En vuelo: envergadura <<SPAN>>\,mm, borde de ataque <<LLE>>\,mm en dos tramos de <<LSEG>>\,mm, flecha
45°, área <<STRI>>\,cm$^2$ (dos triángulos) y <<SWING>>\,cm$^2$ de tela contando la franja de raíz.\end{resultado}

\section{Materiales}
\que Con qué se hace cada pieza.
\porque S6 fija en 2\,mm la pared del contenedor si es impresa, de modo que su masa depende solo de la densidad: <<TUBO_M>>\,g en
LW-PLA contra <<TUBO_PETG>>\,g en PETG. Las piezas con cargas concentradas (cuadernas, tapa) van en PA12-CF, y las almas de la caja en
G10, que es rígido en lámina fina y transparente a la radiofrecuencia.
<<T_MAT>>
\chequeo Las piezas impresas son anisótropas. Los márgenes usan la resistencia entre capas cuando la tensión cruza las capas
($\sigma_x$ en cuadernas y tubo). El LW-PLA ablanda a unos 55\,°C: el contenedor va en blanco y a la sombra.

\section{Estructura del planeador}
\que La arquitectura del bastidor y por dónde pasa la carga.
\porque El ala necesita los dos gajos laterales del cilindro abiertos. Un monocasco impreso habría que ranurarlo; varillas
roscadas con discos dan poca rigidez. Se elige una caja de paneles finos con largueros en las aristas (figura~\ref{fig:bast}):
\begin{itemize}
\item cuatro largueros de tubo de carbono \diam5/3{,}5, el mismo material de compra que el borde de ataque;
\item cuadernas extremas C1 y C4 de 8\,mm, con alma de 1{,}6\,mm, aro y nervios, que alojan los pernos de pivote del ala dentro
de su propio espesor;
\item marcos intermedios C2 y C3 de 4\,mm;
\item dos paneles laterales y una tapa superior de G10 de 0{,}5\,mm, y una bandeja de 0{,}8\,mm que lleva toda la electrónica.
\end{itemize}
<<FIG_BAST>>
\chequeo Masa de la estructura primaria: <<EST_M>>\,g por CAD. Las cuadernas extremas pesan 22\,g cada una y son el primer lugar
donde aligerar. La carga axial entra por la llave en C4 y baja por largueros y paneles; la lateral sale por los patines de C1 y C4
contra la pared del contenedor.

\section{Contenedor, anclaje y liberación}
\que El tubo, la tapa, cómo cuelga del paracaídas y cómo suelta al planeador.
\porque El tubo es una pieza de LW-PLA con dos orificios, de \diam8 para el interruptor y \diam5 para el indicador. La tapa es una
pieza aparte de PA12-CF con seis nervios radiales. La brida del paracaídas, de tres ramales de Kevlar, se anuda a tres de esos
nervios, de modo que el tirón pasa de la tapa a la llave sin cargar el tubo.

La retención es una llave de bayoneta: un eje de acero inoxidable de \diam5 atraviesa C4 y la tapa; un pasador transversal apoya
sobre un plato, y el plato sobre un anillo de elastómero asentado en el cubo de la tapa (figura~\ref{fig:cerr}). Un microservo en
el planeador gira el eje 90° y el pasador pasa por el ojo de cerradura.
<<FIG_CERR>>
\begin{resultado}Carga de retención: $<<MPLAN>>\,\mathrm{g}\times30\,\mathrm{G}\times1{,}8=<<FRET>>$\,N. Tirón en la brida:
<<FPAR>>\,N. Par para girar la llave colgando a 1\,G: 0{,}06\,kg$\cdot$cm contra 1{,}8\,kg$\cdot$cm del servo. Rigidez del
aislador: <<KISO>>\,N/mm.\end{resultado}
\chequeo El servo no está en el camino de carga, así que M3 se cumple por geometría. Con arandela interior en C4 y plato de apoyo
en la tapa, las dos piezas impresas trabajan a compresión bajo la llave.

\section{Ala}
\subsection{Estiba y despliegue}
\que Cómo entra un borde de ataque de <<LLE>>\,mm en un cuerpo de <<LG>>\,mm y cómo se abre.
\porque La varilla se parte en dos. Si la articulación J queda justo al medio y el tirante mide lo mismo que la distancia entre
pivotes ($AJ=JT$, $BT=AB$), el cuadrilátero A--J--T--B pliega plano: la punta T cae sobre el ápice A y todas las barras quedan
alineadas sobre el costado del cuerpo (figura~\ref{fig:mec}). Es un mecanismo de un solo grado de libertad. La nota de membrana
proponía llevar la unión a 190\,mm para bajar el momento; eso rompe el pliegue, porque el tirante dejaría de llegar a la punta.
<<FIG_MEC>>
\chequeo El despliegue es pasivo: la pared del contenedor sostiene las varillas y, al salir, un resorte de torsión en B abre el
tirante. Abierta, A--J--T queda alineada, que es un punto muerto: sin traba la tensión de la tela la cerraría. Un manguito de
aluminio corre empujado por su resorte y cubre la articulación.

\subsection{Dimensionamiento}
\que Tensiones y flechas de las varillas con las cargas de la nota de membrana.
\porque Se modela el ala como un pórtico de vigas con las cargas del modelo de tiras (presión de apertura de 367\,Pa, panza de
6\,\%). Con las hipótesis de la nota el modelo la reproduce; con el tirante unido a la punta por horquilla, parte de la flexión
fuera del plano pasa al tirante.
<<T_ALA>>
<<FIG_ALA>>
\chequeo Varilla: $MS=<<MS_LE>>$ con 400\,MPa admisibles. Pandeo del tirante: $P_{cr}/N=<<PCR>>$. El manguito se dimensiona para
<<MJ>>\,N$\cdot$mm. El primer modo del ala abierta está en <<FALA>>\,Hz (sin contar la rigidez que da la tensión de la tela).

<<AERO>>

\section{Análisis estructural}
\subsection{Modelo y verificación}
\que Con qué modelo se calculan las tensiones y cuánto se le puede creer.
\porque La geometría del CAD se malla con tetraedros cuadráticos en Gmsh y se resuelve en CalculiX: <<NEL>> elementos y <<NNOD>>
nodos. Las piezas van pegadas entre sí con malla conforme. Batería, servos y lastre son sólidos con su masa; las placas, FR-4 con
la masa de componentes repartida; el ala plegada, masa en sus cuatro apoyos. El contenedor apoya en su borde inferior y el
fuselaje del cohete guía lateralmente el borde superior. La respuesta dinámica se arma por superposición de <<NMOD>> modos con
corrección estática, usando las tensiones de CalculiX en los puntos de integración.
<<FIG_MALLA>>
El amortiguamiento de cada modo sale de la energía de deformación: $\zeta_i=\zeta_0(1-f_i)+\tfrac{\eta}{2}f_i$, con
$\zeta_0=2\,\%$ para la estructura, $\eta=<<ETA>>$ para el elastómero y $f_i$ la fracción de energía del modo $i$ que queda en el
elastómero.
<<T_VER>>
\chequeo La misma cadena reproduce una viga en voladizo dentro del 3\,\%. En el modelo del CanSat la suma modal recupera el
desplazamiento estático y los <<NMOD>> modos reúnen el <<MEFX>>/<<MEFY>>/<<MEFZ>>\,\% de la masa en $x/y/z$. Se descartaron
<<NFILT>> elementos de <<NEVER>> por nodos medios fuera de equilibrio en el autovector, un artefacto numérico. Las tensiones de
pico en aristas pegadas dependen de la malla; falta un segundo nivel de malla para confirmarlas.

\subsection{Modos propios}
<<T_MODAL>>
<<FIG_MODOS>>
\begin{resultado}Primer modo: <<F1>>\,Hz. Modo axial principal: <<FX>>\,Hz con el <<MX>>\,\% de la masa y $\zeta=<<ZAX>>\,\%$.
Laterales principales: <<FY>>\,Hz ($y$) y <<FZ>>\,Hz ($z$). <<TXT_LIBRE>>\end{resultado}

\subsection{Evolución del diseño}
\que Qué cambió el análisis en el diseño.
\porque Tres iteraciones. (1)~Tapa de LW-PLA de 3\,mm y contenedor en voladizo: primer modo a 140\,Hz y tapa sin margen; se pasó a
una tapa nervada de PA12-CF. (2)~Llave unida rígidamente: modo axial a <<RIG_F>>\,Hz con el <<RIG_M>>\,\% de la masa, amplificación
de <<RIG_T>> en resonancia y $\sigma_x=<<RIG_S>>$\,MPa en la tapa ($MS=<<RIG_MS>>$). (3)~Llave como perno pasante con arandelas y
anillo elastomérico, y patines de elastómero con cara de PTFE.
\chequeo Con unión rígida un barrido de 15\,G excita el modo axial con $Q=25$: casi 400\,G sobre el planeador. Ninguna pieza
impresa liviana aguanta eso con margen. La salida no es reforzar sino aislar el único punto por donde pasa la carga axial.

\subsection{Respuesta en frecuencia a 15\,G}
\que Aceleraciones y tensiones para una entrada senoidal de 15\,G en la base, de 5 a 1000\,Hz, en cada eje.
<<FIG_RESP>>
<<T_ACC>>
<<FIG_UTIL>>
<<T_ARM>>
<<FIG_ARMMAP>>
\chequeo El índice de utilización es $FS\,\sigma/\sigma_{adm}$: por debajo de 1 hay margen. Margen mínimo en resonancia:
<<MS_ARM>>. Las aceleraciones de la tabla son el dato de entrada para calificar la electrónica.

\subsection{Choque de 30\,G}
\que La respuesta a un pulso semiseno de 30\,G en la base y al tirón del paracaídas.
\porque La duración real del golpe de eyección no se conoce: se calcula con 11\,ms y se barre de 1 a 20\,ms, tomando la peor.
El tirón del paracaídas es un caso aparte, estático, con el CanSat colgado de la brida y 30\,G multiplicados por 1{,}8, que es el
máximo del espectro de respuesta de un semiseno.
<<FIG_CHP>>
<<T_CH>>
<<FIG_CHMAP>>
\chequeo Margen mínimo en choque y tirón: <<MS_CH>>.

\subsection{Resumen de márgenes}
<<T_MS>>
\chequeo Margen mínimo global: <<MS_MIN>> en «<<G_MIN>>», caso <<C_MIN>>. <<TXT_NEG>>

<<ACCIONES>>

\subsection{Uniones}
\que Las uniones que el modelo pegado no representa.
<<T_UN>>
\chequeo Deformación del aislador: <<EPS15>>\,\% a 15\,G y <<EPSCH>>\,\% en el tirón (admisible 20\,\% y 30\,\%). La varilla
plegada entre apoyos tiene su primer modo local cerca de 1{,}2\,kHz y 2\,MPa a 30\,G.

\section{Masa y centro de gravedad}\label{sec:masa}
<<T_MASA>>
\begin{resultado}Total: 500\,g con <<LASTRE>>\,g de lastre, que es a la vez el margen. Incertidumbre: $\pm<<INC>>$\,g, mayor que
la tolerancia de S1, así que la masa se ajusta en la pesada final. Masa de vuelo: 500\,g (el CanSat completo); carga alar <<WS>>\,N/m$^2$;
velocidad de descenso estimada <<W>>\,m/s (sección~\ref{sec:aero}). Centro de gravedad desde la nariz: <<XLAN>>\,mm en lanzamiento
y <<XVUE>>\,mm en vuelo, con el CanSat completo y el ala y la cola abiertas; el centroide del ala está en <<XALA>>\,mm.\end{resultado}
\chequeo Las masas de electrónica, cola y paracaídas son asignaciones a confirmar por cada subsistema. La nota de membrana supone
500\,g en vuelo, igual que aquí; la diferencia con su 5{,}0\,m/s es la resistencia del cuerpo, que la nota no contaba.

\section{Ensayos, riesgos y pendientes}
\begin{table}[H]\centering\footnotesize\begin{tabular}{p{3.2cm}p{1.6cm}p{5.6cm}p{4.2cm}}\toprule
Ensayo & Requisito & Método & Criterio \\ \midrule
Calibre y deslizamiento & S2, S3, S7 & Tubo calibre \diam90{,}5; el CanSat armado sale por su peso & 10 de 10 sin trabarse \\
Masa y CG & S1 & Balanza de 0{,}1\,g; CG sobre filo & $500\pm10$\,g \\
Probetas de impresión & S4, S5 & Tracción en el plano y entre capas, PA12-CF y LW-PLA & Resistencia $\ge$ la usada aquí \\
Amortiguamiento & S4 & Golpe con martillo y acelerómetro; ancho de banda & $\zeta$ axial $\ge$ 10\,\% \\
Vibración & S4 & Dentro de un tramo de fuselaje, sobre mesa vibrante o lijadora orbital, tres ejes & Sin daño; el ala no se abre \\
Choque & S5 & Caída colgado de la brida con cuerda no elástica de 61\,cm & Sin daño; sigue trabado \\
Tracción de la llave & M3 & <<FRET15>>\,N entre planeador y tapa & Sin fluencia ni fisuras \\
Liberación y despliegue & C4, S7 & Contenedor colgado, comando, video a 240\,cps & 20 de 20: sale, abre y traba \\
Carga del ala & C4 & Arena sobre la membrana hasta tres veces la carga de vuelo & Flecha de punta $\le$ 5\,mm \\
Temperatura & S6 & 30\,min a 50\,°C & Sin deformación; desliza \\ \bottomrule
\end{tabular}\caption{Plan de ensayos.}\end{table}
\begin{table}[H]\centering\footnotesize\begin{tabular}{p{4.4cm}p{4.6cm}p{5.8cm}}\toprule
Riesgo & Causa & Mitigación \\ \midrule
El amortiguamiento real es menor & Propiedades del elastómero supuestas ($E=3$\,MPa, $\eta=<<ETA>>$) & Ensayo de martillo en el primer prototipo; elegir el compuesto por hoja de datos y repetir el análisis \\
Las piezas impresas rinden menos & Humedad del PA12; espumado irregular & Probetas del mismo lote; ya se usa la resistencia entre capas y $FS=2$ \\
El ala no traba al abrir & Fricción del manguito; tela enganchada & 20 aperturas filmadas; el manguito es la primera pieza a prototipar \\
El planeador no sale & Interferencia de patines; tela pellizcada & Cara de PTFE; huelgo de 1\,mm; ensayo en frío y en caliente \\
Otra interpretación de S4 y S5 & El Apéndice~A no define espectro ni duración & Consultar el procedimiento de ensayo \\
Las cámaras no ven el paracaídas & Dentro del contenedor no hay visual (C6, C7) & Definir ventana en la tapa o cámara en el contenedor \\
Masa fuera de tolerancia & Incertidumbre de $\pm<<INC>>$\,g & Lastre ajustable y pesadas parciales \\ \bottomrule
\end{tabular}\caption{Riesgos principales.}\end{table}
\noindent\textbf{Pendientes para el CDR.} Nota de cola (botalón y su mecanismo); resorte de torsión del ala; bujes e insertos de
las cuadernas; modelo de membrana en 3D; segundo nivel de malla; propiedades medidas de impresos y elastómero; ubicación de las
cámaras durante la fase de paracaídas.

\section{Archivos}
Todo sale de un único modelo paramétrico, \texttt{src/params.py}. \texttt{cad.py} genera el CAD (archivos STEP en \texttt{cad/});
\texttt{planos.py}, los siete planos A3; \texttt{fe\_model.py} y \texttt{fe\_analisis.py}, la malla, las corridas de CalculiX y
la respuesta dinámica; \texttt{wing\_frame.py}, el pórtico del ala; \texttt{masas.py}, el presupuesto de masa; y
\texttt{build\_informe.py}, este documento. \texttt{make} regenera todo.

\includepdf[pages=-,landscape=true,pagecommand={\thispagestyle{fancy}},addtotoc={1,section,1,Anexo: planos,anexo}]{<<PLANOS>>}
\end{document}
"""

def _ms(caso, g):
    return peor(caso, g)[0]


acc = []
if _ms("armonico", "Contenedor: tubo") < 0 or _ms("choque", "Contenedor: tubo") < 0:
    p = peor("armonico", "Contenedor: tubo")
    acc.append(r"\item \textbf{Tubo del contenedor} ($MS=%s$ en resonancia lateral a %s\,Hz y %s en choque lateral). Es flexión local de la "
               r"pared de 2\,mm entre los patines de C4 y la tapa, donde la pared pasa de libre a empotrada en 4\,mm; el resto del tubo "
               r"tiene margen (casi-estático: %s). Corrección: prolongar 10\,mm el faldón de la tapa hacia la boca y apoyar ahí los patines "
               r"de C4. La pared pasa a 4{,}5\,mm (LW-PLA más PA12-CF) y la tensión en el LW-PLA baja unas cinco veces."
               % (ms(p[0]), n(p[4]["f_crit"], 0), ms(_ms("choque", "Contenedor: tubo")), ms(_ms("cuasi15", "Contenedor: tubo"))))
if _ms("armonico", "Soportes de equipos") < 0:
    p = peor("armonico", "Soportes de equipos")
    acc.append(r"\item \textbf{Sillas de la batería} ($MS=%s$ a %s\,Hz): la batería amplifica %s veces sobre sus dos sillas. "
               r"Corrección: tercera silla al centro y almohadilla de espuma bajo la cincha; con tres apoyos la tensión baja un tercio."
               % (ms(p[0]), n(p[4]["f_crit"], 0), n(max(R["armonico"][e]["trans_max"]["Bateria"] for e in EJES), 0)))
if _ms("armonico", "Paneles y bandeja") < 0:
    p = peor("armonico", "Paneles y bandeja")
    acc.append(r"\item \textbf{Paneles de G10} ($MS=%s$ a %s\,Hz): pico en un solo punto, en la esquina del panel contra C2 y en el modo "
               r"más alto de la base modal; con el percentil 99{,}9 de las tensiones el margen es %s. Se confirma con una malla más fina."
               % (ms(p[0]), n(p[4]["f_crit"], 0), ms(p[4]["MS_p999"])))
ACC = ""
if acc:
    ACC = (r"\subsection{Márgenes negativos y corrección}" "\n" r"\que Dónde no alcanza el diseño y qué se cambia." "\n"
           r"\porque Los casos casi-estático de 15\,G y el tirón del paracaídas tienen margen en todas las piezas. Quedan sin margen:"
           "\n" r"\begin{itemize}" + "\n".join(acc) + r"\end{itemize}" "\n"
           r"\chequeo Las tres correcciones son locales y no cambian la arquitectura ni la masa en más de 3\,g. No se volvió a correr "
           r"el modelo con ellas: quedan como primera tarea de la próxima iteración.")

PH = json.load(open(os.path.join(FEA, "polhamus.json")))
t_polh = tab("lccccccc", ["Hipótesis", "$f$", "$C_L$ potencial", "$C_L$ vórtice", "$C_L$", "$C_D$", "$w$ con 500\\,g", "$w$ con %s\\,g" % n(PH["m_vuelo"], 0)],
             [[r_["nombre"], n(r_["f"]), n(r_["CLp"], 2), n(r_["CLv"], 2), n(r_["CL"], 2), n(r_["CD"], 2), n(r_["w500"], 2), n(r_["w_vuelo"], 2)]
              for r_ in PH["filas"]],
             "Sustentación a $\\alpha=20$° y velocidad de descenso [m/s] según la fracción de sustentación de vórtice.", r"\footnotesize")

PL = json.load(open(os.path.join(FEA, "planeo.json")))
PL500 = json.load(open(os.path.join(FEA, "planeo_500g.json")))
_nom = PL["nominal"]["cuerpo romo (disco de nariz plano)"]
_omo = PL["nominal"]["con ojiva en la nariz"]
t_planeo = tab("lcccccc", ["Configuración", "$C_L$", "$C_D$", "L/D", r"$w$ nominal", r"$w$ 5--95\,\%", r"Alcance desde 400\,m"], [
    [r"Delta, $\alpha=20^\circ$, $f=0{,}5$", n(_nom["delta"]["CL"], 2), n(_nom["delta"]["CD"], 2), n(_nom["delta"]["LD"], 1), n(_nom["delta"]["w"], 1),
     "%s a %s" % (n(PL["mc"]["delta"]["p"][0], 1), n(PL["mc"]["delta"]["p"][2], 1)), "%.0f\\,m" % (400 * _nom["delta"]["LD"])],
    ["Avión recto, $C_L=0{,}8$", n(_nom["recta"]["CL"], 2), n(_nom["recta"]["CD"], 2), n(_nom["recta"]["LD"], 1), n(_nom["recta"]["w"], 1),
     "%s a %s" % (n(PL["mc"]["recta"]["p"][0], 1), n(PL["mc"]["recta"]["p"][2], 1)), "%.0f\\,m" % (400 * _nom["recta"]["LD"])],
], "Descenso [m/s] del planeador de %s\\,g con $S=%.0f$\\,cm$^2$ y el cuerpo romo del diseño." % (n(PL["masa_g"], 0), P.S_TRI), r"\footnotesize")

fl = R.get("freq_libre")
V = {
    "AERO": AP.fragmento(), "ACCIONES": ACC, "EQUIPO": P.EQUIPO, "T_POLH": t_polh, "PH_KP": n(PH["Kp"], 2), "PH_KV": n(PH["Kv"], 2),
    "PH_CD0": n(PH["cd_cuerpo"], 2), "PH_CDA": n(PH["cd_ala"], 2), "PH_CDC": n(PH["cd_cola"], 2),
    "T_PLANEO": t_planeo,
    "FIG_PLANEO": fig("planeo.png", 1.0, "Izquierda: polar de velocidades. Derecha: dispersión del descenso con las incertidumbres de modelo y de trim."),
    "PL_WD": n(_nom["delta"]["w"], 1), "PL_WDO": n(_omo["delta"]["w"], 1), "PL_WRO": n(_omo["recta"]["w"], 1),
    "PL_R40": n(7.67, 1), "PL_R100": n(2.85, 1), "PL5_WD": n(PL500["nominal"]["cuerpo romo (disco de nariz plano)"]["delta"]["w"], 1),
    "FIG_POLH": fig("polhamus.png", 0.95, "Izquierda: sustentación según Polhamus para alargamiento 4. Derecha: velocidad de descenso contra la fracción de vórtice."), "TEMPORADA": P.TEMPORADA, "FECHA": P.FECHA, "REV": P.REV,
    "EST_M": n(est_m, 0), "NEL": f"{R['elementos']:,}".replace(",", "\\,"), "NNOD": f"{R['nodos']:,}".replace(",", "\\,"),
    "F1": n(f[0], 0), "RIG_T": n(RIG["armonico"]["x"]["trans_max"]["Bateria"], 0), "ZAX": n(zm[ix] * 100, 0),
    "T_AX": n(R["armonico"]["x"]["trans_max"]["Bateria"]), "MS_CE": ms(ms_ce), "MS_ARM": ms(ms_arm), "MS_CH": ms(ms_ch),
    "TXT_NEG": txt_neg, "T_REQ": t_req.replace(r"\caption{", r"\caption{\label{tab:req}"),
    "T_CONF": t_conf.replace(r"\caption{", r"\caption{\label{tab:conf}"),
    "FIG_CONF": fig2("lan_corte_anot.png", "des_iso_anot.png", "Configuración elegida. Izquierda: lanzamiento, cortado por el plano medio. Derecha: planeador en vuelo.", 0.40, 0.58),
    "FIG_CONOPS": fig("conops.png", 1.0, "Secuencia de operación y carga que dimensiona cada fase."),
    "M_CONT": n(m_cont, 0), "LG": "%g" % P.L_G, "DAB": n(P.D_AB), "CTL": "%g" % P.CT_LEN, "DPL": "%g" % (2 * P.RB),
    "FIG_LAN": fig("lay_lanzamiento.png", 1.0, "Configuración de lanzamiento. Cotas en mm."),
    "FIG_EST": fig("lay_estibado.png", 0.92, "Planeador estibado.") + fig("est_iso_anot.png", 0.86, "Planeador estibado: el ala plegada ocupa el gajo lateral."),
    "FIG_DES": fig("lay_desplegado.png", 0.70, "Planeador desplegado (escala 1:2)."),
    "SPAN": n(P.SPAN), "LLE": n(P.L_LE), "LSEG": n(P.L_SEG), "STRI": n(P.S_TRI, 0), "SWING": n(P.S_WING, 0),
    "TUBO_M": n(tubo_m, 0), "TUBO_PETG": n(tubo_m / MT["LWPLA"]["rho"] * MT["PETG"]["rho"], 0), "T_MAT": t_mat,
    "FIG_BAST": fig("bastidor_explotado_anot.png", 0.88, r"\label{fig:bast}Estructura primaria en despiece.")
                + fig("equipos_anot.png", 0.88, "Equipos sobre la bandeja (sin el panel izquierdo ni la tapa superior)."),
    "FIG_CERR": fig("cerrojo_anot.png", 0.80, r"\label{fig:cerr}Llave de bayoneta, tapa nervada y cuaderna C4, cortadas por el plano medio."),
    "MPLAN": n(m_plan, 0), "FRET": n(F_ret, 0), "FPAR": n(F_par, 0), "KISO": n(k_iso, 0),
    "FIG_MEC": fig("ala_mecanismo.png", 1.0, r"\label{fig:mec}Mecanismo del ala en planta."),
    "T_ALA": t_ala, "FIG_ALA": fig("ala_esfuerzos.png", 1.0, "Momentos, deformada y respuesta al choque de la varilla de borde de ataque."),
    "MS_LE": ms(400 / pt["sigma_LE"] - 1), "PCR": n(ALA["tirante"]["coef"]), "MJ": n(nt["M_J"], 0), "FALA": n(ALA["modal"]["freq"][0], 0),
    "NMOD": str(len(f)), "FIG_MALLA": fig("fea_malla.png", 1.0, "Malla cortada por el plano $y=0$, coloreada por material."),
    "ETA": n(R["eta_elast"], 2), "T_VER": t_ver, "MEFX": "%.0f" % (100 * R["m_eff_frac"][-1][0]),
    "MEFY": "%.0f" % (100 * R["m_eff_frac"][-1][1]), "MEFZ": "%.0f" % (100 * R["m_eff_frac"][-1][2]),
    "NFILT": str(R["n_filtrados"]), "NEVER": f"{R['n_ever']:,}".replace(",", "\\,"), "T_MODAL": t_modal,
    "FIG_MODOS": fig("fea_modos.png", 1.0, "Primeros cuatro modos, modelo cortado por el plano medio."),
    "FX": n(fx, 0), "MX": n(mx, 0), "FY": n(fy, 0), "FZ": n(fz, 0),
    "TXT_LIBRE": ("Sin la guía del fuselaje el primer modo baja a %s\,Hz." % n(fl[0], 0)) if fl else "",
    "RIG_F": n(RIG["freq"][0], 0), "RIG_M": n(RIG["m_eff"][0][0] / 5, 0), "RIG_S": n(rig_tapa["sigma"], 0), "RIG_MS": ms(rig_tapa["MS"]),
    "FIG_RESP": fig("fea_respuesta_g.png", 0.80, "Aceleración de respuesta en ocho puntos para 15\,G de entrada."),
    "T_ACC": t_acc, "FIG_UTIL": fig("fea_util_frecuencia.png", 0.80, "Índice de utilización de cada grupo contra la frecuencia de excitación."),
    "T_ARM": t_arm, "FIG_ARMMAP": fig("fea_arm_mapas.png", 1.0, "Respuesta en frecuencia a 15\\,G: envolvente del índice de utilización en las resonancias, pieza más cargada y peor caso de cada grupo."),
    "FIG_CHP": fig("fea_choque_pulso.png", 1.0, "Pulso, espectro de respuesta y aceleraciones bajo el choque axial."),
    "T_CH": t_ch, "FIG_CHMAP": fig("fea_choque_mapas.png", 1.0, "Choque de 30\\,G: envolvente del índice de utilización, pieza más cargada y peor caso de cada grupo.")
                           + fig("fea_choque_duracion.png", 1.0, "Sensibilidad a la duración del pulso.")
                           + fig("fea_parac_mapas.png", 1.0, "Tirón del paracaídas."),
    "T_MS": t_ms, "MS_MIN": ms(ms_min[0]), "G_MIN": GNOM[ms_min[1]], "C_MIN": CASO[ms_min[2]], "T_UN": t_un,
    "EPS15": n(100 * (m_plan / 1000 * 15 * G0 / A_iso) / Ec_iso, 0), "EPSCH": n(100 * (F_ret / A_iso) / Ec_iso, 0),
    "T_MASA": t_masa, "LASTRE": n(MAS["lastre"], 0), "INC": n(MAS["inc_rss"], 0), "WS": n(MAS["carga_alar"], 0),
    "W": n(MAS["w_estimado"]), "W368": n(MAS["w_planeador_solo"]), "XLAN": n(MAS["x_cg_lanzamiento"], 0), "XEST": n(MAS["x_cg_planeador_estibado"], 0),
    "XVUE": n(MAS["x_cg_vuelo_total"], 0), "XALA": n(MAS["x_centroide_ala"], 0), "FRET15": n(1.5 * F_ret, 0),
    "PLANOS": os.path.join(PLANOS, "Planos_CanSat_AlaDelta.pdf"),
}
for _ in range(2):
    for k, v in V.items():
        TEX = TEX.replace("<<%s>>" % k, str(v))
TEX = TEX.replace(r"\,\%$", r"$\,\%")
assert "<<" not in TEX, TEX[TEX.index("<<"):TEX.index("<<") + 40]
open(os.path.join(BUILD, "informe.tex"), "w", encoding="utf-8").write(TEX)
for _ in range(2):
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "informe.tex"], cwd=BUILD, capture_output=True,
                       text=True, errors="replace")
if r.returncode != 0:
    print(r.stdout[-2500:])
else:
    shutil.copy(os.path.join(BUILD, "informe.pdf"), os.path.join(BASE, "PDR_Mecanica_CanSat_AlaDelta.pdf"))
    import re
    print("ok:", re.findall(r"Output written.*", r.stdout)[-1])
    print("overfull:", len(re.findall(r"Overfull \\hbox", r.stdout)), "undefined:", len(re.findall(r"undefined", r.stdout)))
