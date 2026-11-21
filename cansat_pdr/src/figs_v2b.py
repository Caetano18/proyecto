"""Diagramas del diseno v2 B regulable: estaciones roscadas para correr el modulo de bateria (M2) y el de avionica (M3).
  v2BR_interior_anot  : corte "tipo Sims" en la posicion nominal, con las estaciones
  v2BR_detalle_anot   : detalle de la estacion de M2 (tuercas a cada lado, cuna, pack)
  v2BR_posiciones     : tres posiciones (todo abajo, nominal, todo arriba) con el CG marcado
Uso: [FIG_LANG=en] python3 figs_v2b.py <carpeta de figuras>
"""
import os
import sys
import json
import warnings
import numpy as np
import cad_e as E
import cg_v2 as CG
import viz
import idioma  # noqa: F401
from cad import box
from figs_cad import anotar
from figs_e import lados

warnings.filterwarnings("ignore")
V = ((-0.4, -1.1, 0.75), (1, 0, 0))
CUNA = (180.0, 70.0, ("carcasa", "solar", "tornillos", "adhesivo"))


def main(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Inter"
    M = {}
    # ------------------------------------------------------------ corte nominal anotado
    E.variante("BR", CG.NOM2, CG.NOM3)
    YL, ZL = E.YL, E.ZL
    est = E.build("estibado")
    x2, x3 = E.X_M2, E.X_M3
    mk = {"varilla": (130, -23.3, 23.3), "tuerca2": (x2 - 1.2, -23.3 - 2.6, 23.3), "m2": (x2 + 4, -25, -20),
          "cuna": (x2 - 23, -34.7, -8), "pack": (x2 - 33 - 4.4, -20, 4.2), "m3": (x3, -25, -20),
          "tuerca3": (x3 + 5.2, -23.3 - 2.6, 23.3), "pcb": (x3 - 38, -15, -12),
          "m1": (0, -25, 15), "m4": (216, -25, -20), "capsula": (194, -12.5, 19), "paracaidas": (229, -22.3, 15.2),
          "larguero": (100, -YL, ZL), "carcasa": (120, -15.0, -41.3)}
    et = [("varilla", "Varillas roscadas (rosca M3)\nen toda su longitud, paso 0,5 mm"),
          ("tuerca2", "Tuercas nyloc a cada lado\nde M2: se corre la estación"),
          ("m2", f"M2: estación regulable\nx = {CG.RANGO2[0]:.0f}–{CG.RANGO2[1]:.0f} mm"),
          ("cuna", "Cuna en U impresa con M2:\nel pack cuelga de M2"),
          ("pack", "Pack 2 × 18650 (92 g):\nla masa que más mueve el CG"),
          ("m3", f"M3: estación regulable\nx = {CG.RANGO3[0]:.0f}–{CG.RANGO3[1]:.0f} mm"),
          ("tuerca3", "Tuercas nyloc de\nla estación M3"), ("pcb", "Módulo de aviónica:\nlos rieles cuelgan de M3"),
          ("m1", "M1: fondo de nadir (fijo)"),
          ("m4", "M4 (fijo)"), ("capsula", "Servos (3): tapa,\nparacaídas y ala"), ("paracaidas", "Paracaídas Ø226"),
          ("larguero", "Larguero CF (ala estibada)"), ("carcasa", "Carena PETG 2 mm\n(recortada)")]
    M["int"] = viz.render(est, f"{out}/v2BR_interior.png", V, (1500, 2000), 1.25, cuna=CUNA, marcas=mk)
    i, d = lados(M, "int", et)
    anotar(out, M, "v2BR_interior", "int", izq=i, der=d, ancho=7.8, col=0.31, fs=8.0)

    # ------------------------------------------------------------ detalle de la estacion de M2
    ventana = box(x2 - 52, x2 + 14, -60, 60, -60, 60)
    det = []
    for p in est:
        if p["grupo"] in ("carcasa", "solar", "tornillos", "cubierta", "vela", "ala", "lazo", "paracaidas", "tapa"):
            continue
        if p["nombre"].startswith(("Bloque de pivote", "Camara", "Lente", "Ventana", "Baliza", "Bateria de la baliza", "Riel")):
            continue
        bb = p["shape"].BoundingBox()
        if bb.xmax < x2 - 52 or bb.xmin > x2 + 14:
            continue
        q = dict(p)
        q["shape"] = p["shape"].intersect(ventana)
        if q["shape"].Volume() > 1e-3:
            det.append(q)
    mk = {"tuerca_a": (x2 + 5.2, -23.3 - 2.6, 23.3), "tuerca_b": (x2 - 1.2, -23.3 - 2.6, 23.3),
          "varilla": (x2 - 30, -23.3 - 1.2, 23.3), "m2": (x2 + 2, -40.4, 14.7), "cuna": (x2 - 30, -36.0, -8),
          "pack": (x2 - 13, -25, 5.0)}
    et = [("tuerca_a", "Tuerca nyloc arriba"), ("tuerca_b", "Tuerca nyloc abajo"),
          ("varilla", "Varilla M3 roscada:\n1 vuelta = 0,5 mm"), ("m2", "M2 (PETG, 4 mm)"),
          ("cuna", "Pared de la cuna en U"), ("pack", "Pack 2 × 18650")]
    M["det"] = viz.render(det, f"{out}/v2BR_detalle.png", ((0.05, -1.0, 0.55), (1, 0, 0)), (1300, 1300), 1.3, marcas=mk)
    i, d = lados(M, "det", et)
    anotar(out, M, "v2BR_detalle", "det", izq=i, der=d, ancho=6.6, col=0.26, fs=8.5)

    # ------------------------------------------------------------ tres posiciones con el CG
    casos = [("Todo hacia nadir", CG.RANGO2[0], CG.RANGO3[0]), ("Nominal", CG.NOM2, CG.NOM3),
             ("Todo hacia cenit", CG.RANGO2[1], CG.RANGO3[1])]
    ims = []
    for k, (tit, a, b) in enumerate(casos):
        E.variante("BR", a, b)
        _, xcg = CG.cg(a, b)
        m_ = viz.render(E.build("estibado"), f"{out}/_v2BR_pos{k}.png", V, (1200, 1700), 1.25, cuna=CUNA,
                        marcas={"cg": (xcg, 0.0, 0.0), "base": (0.0, 0.0, 0.0), "top": (236.0, 0.0, 0.0)})
        ims.append((tit, a, b, xcg, m_))
    fig = plt.figure(figsize=(11.0, 6.4))
    for k, (tit, a, b, xcg, m_) in enumerate(ims):
        im = plt.imread(f"{out}/_v2BR_pos{k}.png")
        ax = fig.add_axes([0.01 + k * 0.33, 0.02, 0.31, 0.84])
        ax.imshow(im, interpolation="lanczos")
        ax.axis("off")
        h, w = im.shape[:2]
        px, py = m_["cg"][0] * w, m_["cg"][1] * h
        ax.plot(px, py, "o", ms=17, mfc="white", mec="#0b0b0b", mew=1.6, zorder=5)
        ax.plot(px, py, marker=(4, 0, 0), ms=0, zorder=6)
        th = np.linspace(0, 2 * np.pi, 5)
        for q in range(4):                                  # simbolo de CG: cuadrantes alternados
            a0 = q * np.pi / 2
            ang = np.linspace(a0, a0 + np.pi / 2, 12)
            if q % 2 == 0:
                ax.fill(np.r_[px, px + 13 * np.cos(ang)], np.r_[py, py - 13 * np.sin(ang)], color="#0b0b0b", zorder=6)
        ax.annotate(f"CG x = {xcg:.1f} mm".replace(".", ","), (px, py), xytext=(px + 0.30 * w, py - 0.06 * h),
                    fontsize=10, weight="bold", color="#0b0b0b", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#2f3192", lw=0.9),
                    arrowprops=dict(arrowstyle="-", color="#d62020", lw=1.0))
        me = CG.margen(xcg)
        fig.text(0.01 + k * 0.33 + 0.155, 0.985, f"{tit}\nM2 en x = {a:.0f} · M3 en x = {b:.0f}\n"
                 f"margen estático {100 * me[0]:.0f}–{100 * me[1]:.0f} %", ha="center", va="top", fontsize=10,
                 color="#1f2a44", weight="bold")
    fig.savefig(f"{out}/v2BR_posiciones.png", dpi=200)
    plt.close(fig)
    for k in range(3):
        os.remove(f"{out}/_v2BR_pos{k}.png")
    E.variante("E")
    json.dump(M, open(f"{out}/marcas_v2BR.json", "w"), indent=1)
    print("diagramas v2 BR ok")


if __name__ == "__main__":
    main(sys.argv[1])
