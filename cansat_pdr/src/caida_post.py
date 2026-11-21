"""Post-proceso de la prueba de caida (caida.py): G de rotura de cada pieza para las opciones A y B del documento v2.

Rotura = sin factor de seguridad.  Criterios por material (tension en el centro del elemento):
  PETG impreso (pared, capas perpendiculares al eje): max(von Mises / 45, traccion entre capas sigma_x / 25)
  PETG 40 % (mamparos):                               max(von Mises / 20, traccion entre capas sigma_x / 11)
  Al 6061-T6 (varillas M3): von Mises / 310;  acero A2-70 (cancamos): von Mises / 700
  Adhesivo sobre PETG: tension de corte equivalente (von Mises / raiz 3) / 4 MPa (adherencia a PETG, rango 2 a 6 MPa)
Pulso: semiseno; el factor dinamico (DAF) sale del modo axial con el apoyo en la brida.  La cuerda de 61 cm frena al
CanSat (3,46 m/s) en unos 37 ms si el pico es de 30 G; tambien se da el peor caso de cualquier duracion.
G de rotura = 1 / (u por G * DAF * escala de masa); se informa al percentil 99,9 de la pieza y en el peor elemento.
Uso: python3 caida_post.py <carpeta A> <carpeta B> <carpeta de figuras> [masa real en g]
"""
import os
import sys
import json
import math
import numpy as np
from scipy.signal import lsim, lti
import params as P
import fe_post as FP
import caida as C
import idioma  # noqa: F401

G0 = 9.80665
ZETA = P.ZETA
V_CAIDA = math.sqrt(2 * G0 * 0.61)                 # 3,46 m/s al tensarse la cuerda
T_PULSO = math.pi * V_CAIDA / (30 * G0)           # semiseno de 30 G que frena y devuelve (cuerda elastica): ~37 ms
CRIT = {"PETG": [("von Mises", "vm", 45.0), ("tracción entre capas", "sx", 25.0)],
        "PETG40": [("von Mises", "vm", 20.0), ("tracción entre capas", "sx", 11.0)],
        "AL6061": [("von Mises", "vm", 310.0)], "A2-70": [("von Mises", "vm", 700.0)],
        "ADH": [("corte del pegado", "tau", 4.0)]}


def daf(fn, T, z=ZETA):
    """Pseudo-aceleracion maxima / pico del semiseno de base (espectro de choque, desplazamiento relativo)."""
    wn = 2 * math.pi * fn
    dt = min(T / 300, 1 / (fn * 60))
    t = np.arange(0, T + 8 / fn, dt)
    a = np.where(t < T, np.sin(np.pi * t / T), 0.0)
    _, zr, _ = lsim(lti([-1.0], [1.0, 2 * z * wn, wn * wn]), a, t)
    return float(np.abs(zr).max() * wn * wn)


def analizar(wd, var, m_real):
    C.materiales()
    z = np.load(os.path.join(wd, f"malla_{var}.npz"))
    xyz, els, ep = z["xyz"], z["els"], z["epart"]
    partes = json.load(open(os.path.join(wd, f"partes_{var}.json")))
    R = json.load(open(os.path.join(wd, f"resumen_{var}.json")))
    ever, S = FP.leer_dat_S(os.path.join(wd, f"estat_{var}.dat"))
    s = S[0].mean(axis=1)                                          # 1 G hacia nadir, centro del elemento
    xx, yy, zz, xy, yz, zx = [s[:, k] for k in range(6)]
    vm = np.sqrt(0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3 * (xy ** 2 + yz ** 2 + zx ** 2))
    pe = ep[ever]
    cen = xyz[els[ever][:, :4]].mean(axis=1)
    anc = xyz[C.nodos_anclaje(xyz)]
    lejos = np.ones(len(ever), bool)
    for a in anc[::max(1, len(anc) // 40)]:
        lejos &= np.linalg.norm(cen - a, axis=1) > 4.0              # introduccion de la carga en el anclaje
    m_mod = R["masa"]
    esc = m_real / m_mod
    mt = m_mod / 1e6
    modos = R["modos"]
    ax = max(modos, key=lambda m: m["meff"][0])
    f_ax = ax["f"]
    d_est, d_max = daf(f_ax, T_PULSO), max(daf(f_ax, T) for T in np.geomspace(0.5e-3, 0.05, 60))
    out = dict(var=var, masa_modelo=m_mod, masa_real=m_real, f_axial=f_ax, meff_axial=ax["meff"][0] / mt,
               T_pulso_ms=1e3 * T_PULSO, DAF=d_est, DAF_peor=d_max, piezas={})
    u = np.full(len(ever), np.nan)
    for pi, p in enumerate(partes):
        k = (pe == pi) & lejos
        if not k.any():
            continue
        crit = CRIT[p["mat"]]
        us = []
        for nom, c, sr in crit:
            val = {"vm": vm, "sx": np.clip(xx, 0, None), "tau": vm / math.sqrt(3)}[c][k] / sr
            us.append((nom, val))
        ui = np.max([v for _, v in us], axis=0)
        u[k] = ui
        manda = max(us, key=lambda t: np.percentile(t[1], 99.9))[0]
        imax = int(np.argmax(ui))
        out["piezas"][p["nombre"]] = dict(
            mat=p["mat"], criterio=manda, u1G_p999=float(np.percentile(ui, 99.9)), u1G_max=float(ui.max()),
            x_max=float(cen[k][imax, 0]),
            G_rot_p999=float(1 / (np.percentile(ui, 99.9) * d_est * esc)), G_rot_max=float(1 / (ui.max() * d_est * esc)),
            G_rot_p999_peor=float(1 / (np.percentile(ui, 99.9) * d_max * esc)))
    return out, dict(xyz=xyz, els=els, ever=ever, u30=u * 30 * d_est * esc)


def corto(n):
    if n.startswith("Adhesivo"):
        return "pegado de " + n.split()[-1]
    if n.startswith("CT1"):
        return "pared"
    if n.startswith("Cuna"):
        return "cuna de la batería"
    if n.startswith("Varilla"):
        return "varillas"
    if n.startswith("Cancamo"):
        return "cáncamos"
    return "mamparo " + n[:2]


NOM = {"A": "A: monocasco pegado", "B": "B: esqueleto de varillas M3", "BR": "B regulable (estaciones roscadas)"}
COLV = {"A": "#2a78d6", "B": "#eb6834", "BR": "#1baf7a"}


def figuras(res, campos, out, sufijo=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from figs_fea import malla_pv, cortar, vtk, panel, barra_util, CM_U, CLIM, SIN_MARGEN
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5})
    tmp = os.path.join(out, "_tmp_int")
    os.makedirs(tmp, exist_ok=True)
    nv = len(res)
    fig = plt.figure(figsize=(11.0 if nv < 3 else 13.0, 4.9))
    nom = NOM
    for c, (r, F) in enumerate(zip(res, campos)):
        g = malla_pv(F["xyz"], F["els"], F["ever"])
        ok = np.isfinite(F["u30"])
        g.cell_data["u"] = np.clip(np.where(ok, F["u30"], CLIM[0]), CLIM[0] * 1.001, None)
        capas = [dict(grid=cortar(g.extract_cells(np.where(ok)[0]).cell_data_to_point_data()), scalars="u", cmap=CM_U,
                      clim=CLIM, log=True, above=SIN_MARGEN)]
        if (~ok).any():
            capas.append(dict(grid=cortar(g.extract_cells(np.where(~ok)[0])), color=(0.80, 0.80, 0.80), lineas=False))
        vtk(f"{tmp}/caida_{c}.png", capas, size=(1800, 1250))
        p = min(r["piezas"].items(), key=lambda kv: kv[1]["G_rot_p999"])
        panel(fig.add_axes([0.01 + c / nv, 0.24, 1 / nv - 0.02, 0.64]), f"{tmp}/caida_{c}.png",
              f"{nom[r['var']]}\nmáx. a 30 G (p99,9) = {coma(30 / p[1]['G_rot_p999'], 2)} "
              f"({corto(p[0])})")
    cb = barra_util(fig, [0.22, 0.13, 0.56, 0.03])
    cb.set_label("Fracción de la rotura a 30 G:  σ / σ$_{rotura}$  (sin factor de seguridad; escala logarítmica; "
                 "magenta: rompe)", fontsize=10)
    fig.savefig(f"{out}/v2_caida_mapas{sufijo}.png", dpi=200)
    plt.close(fig)

    # G de rotura por pieza (barras horizontales, escala logaritmica)
    grupos = [("Pared de PETG", ("CT1",)), ("Mamparo M1", ("M1",)), ("Mamparo M2", ("M2",)), ("Mamparo M3", ("M3",)),
              ("Mamparo M4 (brida)", ("M4",)), ("Pegado mamparo-pared", ("Adhesivo",)),
              ("Varillas M3 / cáncamos", ("Varilla", "Cancamo")), ("Cuna de la batería", ("Cuna",))]
    COL = COLV
    grupos = [g_ for g_ in grupos if any(n.startswith(g_[1]) for r in res for n in r["piezas"])]
    fig, ax = plt.subplots(figsize=(8.6, 4.4 if nv < 3 else 5.4))
    hb = 0.72 / nv
    yl, hechos = [], set()
    for gi, (gn, pref) in enumerate(grupos):
        yl.append(gn)
        for vi, r in enumerate(res):
            vals = [v["G_rot_p999"] for n, v in r["piezas"].items() if n.startswith(pref)]
            if not vals:
                continue
            g_ = min(vals)
            y = gi + (vi - (nv - 1) / 2) * hb
            lab = nom[r["var"]] if r["var"] not in hechos else None
            hechos.add(r["var"])
            ax.barh(y, g_, height=hb * 0.9, color=COL[r["var"]], label=lab)
            ax.text(g_ * 1.06, y, f"{g_:,.0f} G".replace(",", "."), va="center", fontsize=8.6, color="#0b0b0b")
    ax.axvline(30, color="#0b0b0b", lw=1.2, ls="--")
    ax.text(31, -0.62, "prueba de caída: 30 G", fontsize=8.6, color="#52514e", va="bottom")
    ax.set_xscale("log")
    ax.set_yticks(range(len(grupos)), yl)
    ax.invert_yaxis()
    ax.set_xlabel("Pico del pulso que rompe la pieza [G]  (percentil 99,9; pulso de la cuerda, ~37 ms)")
    ax.grid(axis="x", color="#e6e6e6", lw=0.6)
    ax.set_axisbelow(True)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    h, l_ = ax.get_legend_handles_labels()
    ax.legend(h, l_, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=min(nv, 3), fontsize=9.2, frameon=False)
    ax.set_xlim(20, 6000)
    fig.tight_layout()
    fig.savefig(f"{out}/v2_caida_rotura{sufijo}.png", dpi=220)
    plt.close(fig)


def coma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def main(pares, out, m_real=524.0, sufijo=""):
    """pares: lista de (carpeta, variante)."""
    res, campos = [], []
    for wd, v in pares:
        r, F_ = analizar(wd, v, m_real)
        res.append(r)
        campos.append(F_)
        print(f"\n=== Opción {v}: modo axial {r['f_axial']:.0f} Hz ({100 * r['meff_axial']:.0f} % de la masa), "
              f"pulso {r['T_pulso_ms']:.0f} ms -> DAF {r['DAF']:.2f} (peor duración {r['DAF_peor']:.2f}); "
              f"masa {r['masa_real']:.0f} g")
        for n, p in sorted(r["piezas"].items(), key=lambda kv: kv[1]["G_rot_p999"]):
            print(f"  {n:34s} {p['criterio']:22s} G_rot p99,9 = {p['G_rot_p999']:8.0f}   peor elem. = "
                  f"{p['G_rot_max']:8.0f}   (peor pulso {p['G_rot_p999_peor']:6.0f})   x = {p['x_max']:.0f}")
    json.dump(res, open(os.path.join(out, "..", "fea", f"caida_v2_{''.join(v for _, v in pares)}.json"), "w"), indent=1)
    figuras(res, campos, out, sufijo)
    print("figuras de la caida ok")


if __name__ == "__main__":
    # uso: python3 caida_post.py <figs> <masa g> <sufijo|-> VAR:carpeta [VAR:carpeta ...]
    a = sys.argv
    main([(p.split(":", 1)[1], p.split(":", 1)[0]) for p in a[4:]], a[1], float(a[2]), "" if a[3] == "-" else a[3])


def figura_modelo(wd, var, out, f_ax=None):
    """Modelo FEM de la prueba de caida: malla por material, anclajes de la brida, carga de 30 G y el pulso."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, FancyArrowPatch
    import pyvista as pv
    from figs_fea import malla_pv, cortar, vtk
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    C.materiales()
    z = np.load(os.path.join(wd, f"malla_{var}.npz"))
    xyz, els, ep = z["xyz"], z["els"], z["epart"]
    partes = json.load(open(os.path.join(wd, f"partes_{var}.json")))
    COLM = {"PETG": (0.80, 0.84, 0.90), "PETG40": (0.42, 0.47, 0.58), "AL6061": (0.93, 0.62, 0.10),
            "A2-70": (0.55, 0.57, 0.62), "ADH": (0.86, 0.62, 0.18)}
    NOMM = {"PETG": "Carena PETG 2 mm", "PETG40": "Mamparos y cuna (PETG 40 %)", "AL6061": "Varillas M3 Al 6061",
            "A2-70": "Cáncamos M3 (A2-70)", "ADH": "Adhesivo"}
    mat = np.array([p["mat"] for p in partes])[ep]
    g = malla_pv(xyz, els)
    g.cell_data["rgb"] = (np.array([COLM[m] for m in mat]) * 255).astype(np.uint8)
    anc = xyz[C.nodos_anclaje(xyz)]
    esf = pv.PolyData(anc).glyph(geom=pv.Sphere(radius=1.6), scale=False, orient=False)
    tmp = os.path.join(out, "_tmp_int")
    os.makedirs(tmp, exist_ok=True)
    cam = ((-0.35, -1.0, 0.5), (1, 0, 0))
    marcas = vtk(f"{tmp}/modelo_{var}.png", [dict(grid=cortar(g), rgb=True, edges=True, lineas=False),
                                           dict(grid=esf, color=(0.82, 0.08, 0.08), lineas=False)],
                 cam=cam, size=(1300, 1800), marcas={"anc": tuple(anc.mean(axis=0)), "cg": (100.0, 0.0, 0.0)})
    fig = plt.figure(figsize=(11.0, 6.2))
    ax = fig.add_axes([0.0, 0.10, 0.42, 0.86])
    im = plt.imread(f"{tmp}/modelo_{var}.png")
    ax.imshow(im, interpolation="lanczos")
    ax.axis("off")
    h, w = im.shape[:2]
    pa = (marcas["anc"][0] * w, marcas["anc"][1] * h)
    ax.annotate("Anclajes de la brida (fijos):\nextremos de las 4 varillas", pa, xytext=(0.62 * w, 0.03 * h), fontsize=9,
                ha="left", va="top", arrowprops=dict(arrowstyle="-", color="#d03b3b", lw=1.0),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#d03b3b", lw=0.9))
    pc = (marcas["cg"][0] * w, marcas["cg"][1] * h)
    ax.add_patch(FancyArrowPatch((0.80 * w, 0.30 * h), (0.80 * w, 0.62 * h), arrowstyle="-|>", mutation_scale=22,
                                 color="#0b0b0b", lw=2.2))
    ax.text(0.83 * w, 0.46 * h, "Inercia\nde 30 G\nhacia\nnadir", ha="left", va="center", fontsize=9.5, weight="bold")
    mats = [m for m in ("PETG", "PETG40", "AL6061", "A2-70", "ADH") if m in set(mat)]
    ax.legend(handles=[Patch(fc=COLM[m], ec="0.3", label=NOMM[m]) for m in mats], loc="lower center",
              bbox_to_anchor=(0.5, -0.11), ncol=2, fontsize=8.6, frameon=False)
    ax.set_title(f"Modelo: {len(xyz) // 1000} k nodos, {len(els) // 1000} k tetraedros cuadráticos (C3D10)",
                 fontsize=9.5, pad=2)
    # pulso
    T = T_PULSO
    a1 = fig.add_axes([0.53, 0.60, 0.44, 0.31])
    t = np.linspace(-0.005, 0.05, 600)
    a1.plot(1e3 * t, np.where((t > 0) & (t < T), 30 * np.sin(np.pi * t / T), 0.0), color="#2a78d6", lw=2)
    a1.set_xlabel("Tiempo [ms]")
    a1.set_ylabel("Aceleración [G]")
    a1.set_title(f"Pulso de la cuerda: semiseno de 30 G, {1e3 * T:.0f} ms", fontsize=10)
    a1.text(1e3 * T / 2, 15, f"Δv = {2 * V_CAIDA:.1f} m/s".replace(".", ",") + "\n(caída de 61 cm y rebote)", ha="center",
            fontsize=8.6, color="#52514e")
    # factor dinamico
    a2 = fig.add_axes([0.53, 0.12, 0.44, 0.33])
    Ts = np.geomspace(0.5e-3, 0.06, 80)
    for fa, lab, col in (f_ax or []):
        a2.plot(1e3 * Ts, [daf(fa, x) for x in Ts], color=col, lw=2, label=f"{lab}: modo axial {fa:.0f} Hz")
    a2.axvline(1e3 * T, color="#0b0b0b", ls="--", lw=1)
    a2.text(1e3 * T * 0.95, 1.78, "pulso real", ha="right", fontsize=8.6, va="top")
    a2.set_xscale("log")
    a2.set_ylim(0, 1.9)
    a2.set_xlabel("Duración del pulso [ms]")
    a2.set_ylabel("Factor dinámico")
    a2.set_title("Amplificación según la duración (espectro de choque, ζ = 2 %)", fontsize=10)
    a2.legend(loc="lower left", fontsize=8.4, frameon=False)
    for a_ in (a1, a2):
        a_.grid(color="#e6e6e6", lw=0.6)
        a_.set_axisbelow(True)
        for s_ in ("top", "right"):
            a_.spines[s_].set_visible(False)
    fig.savefig(f"{out}/v2{var}_fem_modelo.png", dpi=200)
    plt.close(fig)
    print("figura del modelo ok")
