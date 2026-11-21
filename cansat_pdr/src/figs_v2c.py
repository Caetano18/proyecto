"""Vistas desplegadas del diseno v2 B regulable (carena de PETG): fase 1 bajo el paracaidas, fase 2 planeando y secuencia.
Uso: [FIG_LANG=en] python3 figs_v2c.py <carpeta de figuras>
"""
import os
import sys
import json
import warnings
import cad_e as E
import viz
import idioma  # noqa: F401
from figs_cad import anotar
from figs_e import lados

warnings.filterwarnings("ignore")
V_VERT = ((-0.4, -1.1, 0.75), (1, 0, 0))
V_DES = ((-1.0, -0.9, 0.55), (0, 0, 1))
V_F1 = ((-0.35, -1.3, 0.45), (1, 0, 0))


def main(out):
    E.variante("BR")
    YL, ZL = E.YL, E.ZL
    des, f1 = E.build("desplegado"), E.build("fase1")
    M = {}
    M["des"] = viz.render(des, f"{out}/v2BR_desplegado.png", V_DES, (2000, 1500), 1.3, marcas={
        "apice": (16, 0, 41), "pivote": (14, -YL, ZL), "larguero": E.larguero_punto(-1, 110),
        "bisagra": E.larguero_punto(-1, 260), "vela": E.vela_punto(1, 0.55, 0.55), "fuga": E.vela_punto(-1, 1.0, 0.45),
        "holgura": E.vela_punto(-1, 0.62, 0.5), "cuerpo": (60, -43.0, -10.0), "nadir": (0, 0, -20)})
    et = [("apice", "Ápice: la quilla va en el\ncanal dorsal (190 mm)"),
          ("pivote", "Pivote: eje M4; la biela del\nservo lo lleva al tope de 60°"),
          ("larguero", "Larguero CF Ø4/3,\n60° de la quilla"),
          ("bisagra", "Larguero izquierdo de 310 mm\n(puntera más corta): lóbulo\nmás chico → vira"),
          ("vela", "Vela Rogallo de ripstop\n(espiral pasiva)"), ("fuga", "Borde de fuga libre"),
          ("holgura", "Holgura de la tela:\ninflado de 31 mm"), ("cuerpo", "Cuerpo: carena PETG 2 mm"),
          ("nadir", "Ventana de nadir")]
    i, d = lados(M, "des", et)
    anotar(out, M, "v2BR_desplegado", "des", izq=i, der=d, ancho=9.0, col=0.20)
    _, info = E.paracaidas_abierto()
    xa = info["x_apex"]
    M["f1"] = viz.render(f1, f"{out}/v2BR_fase1.png", V_F1, (1100, 2400), 1.15, ssao=False, marcas={
        "tela": E.paracaidas_punto(0.55, 165), "ventana": (xa, 0, 0),
        "lineas": (info["x_sw"] + 0.55 * (info["x_skirt"] - info["x_sw"]), -0.55 * info["rp"] * 0.707,
                   0.55 * info["rp"] * 0.707),
        "destorcedor": (info["x_conf"] + 5, 0, 0), "elevador": (252.0, 0.0, 0.0), "cansat": (120, -43.0, 10.0)})
    et = [("tela", "Paracaídas plano Ø226\n(gajos de ripstop)"), ("ventana", "Ventana central Ø40"),
          ("lineas", "8 líneas de Kevlar\n(282 mm)"), ("destorcedor", "Destorcedor"),
          ("elevador", "Elevador: sale de la copa.\nAdentro, brida a las varillas\ny liberación de 2 anillos;\nun servo retira el pasador"),
          ("cansat", "CanSat: 15 m/s,\nala todavía plegada")]
    i = [x for x in et if x[0] in ("lineas", "elevador", "cansat")]
    d = [x for x in et if x[0] in ("ventana", "tela", "destorcedor")]
    anotar(out, M, "v2BR_fase1", "f1", izq=i, der=d, ancho=6.4, col=0.32)
    est = E.build("estibado")
    viz.render(est, f"{out}/v2BR_exterior.png", V_VERT, (1500, 2000), 1.25)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Inter"
    ims = [plt.imread(f"{out}/{n}.png") for n in ("v2BR_exterior", "v2BR_fase1", "v2BR_desplegado")]
    tit = ["1. Lanzamiento: Ø90 × 240,\nala y paracaídas guardados", "2. Fase 1: paracaídas,\n15 m/s",
           "3. Fase 2 (80 % del apogeo): vela\nRogallo en espiral, ≈5,5 m/s"]
    fig = plt.figure(figsize=(11.0, 5.4))
    pos = [[0.0, 0.0, 0.2, 0.86], [0.2, 0.0, 0.22, 0.86], [0.43, 0.08, 0.57, 0.70]]
    for k in range(3):
        ax = fig.add_axes(pos[k])
        ax.imshow(ims[k], interpolation="lanczos")
        ax.axis("off")
        fig.text(pos[k][0] + pos[k][2] / 2, 0.985, tit[k], ha="center", va="top", fontsize=10.5, color="#1f2a44",
                 weight="bold")
    fig.savefig(f"{out}/v2BR_secuencia.png", dpi=220)
    plt.close(fig)
    E.variante("E")
    json.dump(M, open(f"{out}/marcas_v2BR_des.json", "w"), indent=1)
    print("vistas desplegadas v2 BR ok")


if __name__ == "__main__":
    main(sys.argv[1])
