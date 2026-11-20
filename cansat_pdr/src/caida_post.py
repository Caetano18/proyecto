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


def figuras(res, campos, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from figs_fea import malla_pv, cortar, vtk, panel, barra_util, CM_U, CLIM, SIN_MARGEN
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5})
    tmp = os.path.join(out, "_tmp_int")
    os.makedirs(tmp, exist_ok=True)
    fig = plt.figure(figsize=(11.0, 4.9))
    nom = {"A": "A: monocasco pegado", "B": "B: esqueleto de varillas M3"}
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
        panel(fig.add_axes([0.01 + 0.5 * c, 0.24, 0.48, 0.64]), f"{tmp}/caida_{c}.png",
              f"{nom[r['var']]}\nmáx. a 30 G (p99,9) = {coma(30 / p[1]['G_rot_p999'], 2)} "
              f"({'pegado de ' + p[0].split()[-1] if p[0].startswith('Adhesivo') else 'mamparo ' + p[0][:2]})")
    cb = barra_util(fig, [0.22, 0.13, 0.56, 0.03])
    cb.set_label("Fracción de la rotura a 30 G:  σ / σ$_{rotura}$  (sin factor de seguridad; escala logarítmica; "
                 "magenta: rompe)", fontsize=10)
    fig.savefig(f"{out}/v2_caida_mapas.png", dpi=200)
    plt.close(fig)

    # G de rotura por pieza (barras horizontales, escala logaritmica)
    grupos = [("Pared de PETG", ("CT1",)), ("Mamparo M1", ("M1",)), ("Mamparo M2", ("M2",)), ("Mamparo M3", ("M3",)),
              ("Mamparo M4 (brida)", ("M4",)), ("Pegado mamparo-pared", ("Adhesivo",)),
              ("Varillas M3 / cáncamos", ("Varilla", "Cancamo"))]
    COL = {"A": "#2a78d6", "B": "#eb6834"}
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    yl, hechos = [], set()
    for gi, (gn, pref) in enumerate(grupos):
        yl.append(gn)
        for vi, r in enumerate(res):
            vals = [v["G_rot_p999"] for n, v in r["piezas"].items() if n.startswith(pref)]
            if not vals:
                continue
            g_ = min(vals)
            y = gi + (vi - 0.5) * 0.36
            lab = nom[r["var"]] if r["var"] not in hechos else None
            hechos.add(r["var"])
            ax.barh(y, g_, height=0.32, color=COL[r["var"]], label=lab)
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
    ax.legend(h, l_, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=9.5, frameon=False)
    ax.set_xlim(20, 6000)
    fig.tight_layout()
    fig.savefig(f"{out}/v2_caida_rotura.png", dpi=220)
    plt.close(fig)


def coma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def main(wa, wb, out, m_real=524.0):
    res, campos = [], []
    for wd, v in ((wa, "A"), (wb, "B")):
        r, F_ = analizar(wd, v, m_real)
        res.append(r)
        campos.append(F_)
        print(f"\n=== Opción {v}: modo axial {r['f_axial']:.0f} Hz ({100 * r['meff_axial']:.0f} % de la masa), "
              f"pulso {r['T_pulso_ms']:.0f} ms -> DAF {r['DAF']:.2f} (peor duración {r['DAF_peor']:.2f}); "
              f"masa {r['masa_real']:.0f} g")
        for n, p in sorted(r["piezas"].items(), key=lambda kv: kv[1]["G_rot_p999"]):
            print(f"  {n:34s} {p['criterio']:22s} G_rot p99,9 = {p['G_rot_p999']:8.0f}   peor elem. = "
                  f"{p['G_rot_max']:8.0f}   (peor pulso {p['G_rot_p999_peor']:6.0f})   x = {p['x_max']:.0f}")
    json.dump(res, open(os.path.join(out, "..", "fea", "caida_v2_AB.json"), "w"), indent=1)
    figuras(res, campos, out)
    print("figuras de la caida ok")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], *(float(x) for x in a[4:5]))
