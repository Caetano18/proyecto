"""Renders anotados del diseno combinado (rev. E).  Uso: [FIG_LANG=en] python3 figs_e.py <carpeta de figuras>

Salidas: e_exterior, e_corte, e_esqueleto, e_desplegado, e_fase1 (+ _anot) y e_secuencia.
"""
import os
import sys
import json
import warnings
import numpy as np
import cad_e as E
import viz
import idioma  # noqa: F401
from figs_cad import anotar

warnings.filterwarnings("ignore")
YL, ZL = E.YL, E.ZL
V_VERT = ((-0.4, -1.1, 0.75), (1, 0, 0))
V_CORTE = ((-0.45, -1.3, 0.35), (1, 0, 0))
V_DES = ((-1.0, -0.9, 0.55), (0, 0, 1))
V_F1 = ((-0.35, -1.3, 0.45), (1, 0, 0))


def lados(M, key, etiquetas):
    """Reparte las llamadas a izquierda o derecha segun donde cae la marca en la imagen."""
    izq, der = [], []
    for k, t in etiquetas:
        (izq if M[key][k][0] < 0.5 else der).append((k, t))
    return izq, der


def main(out):
    os.makedirs(out, exist_ok=True)
    est, des, f1 = E.build("estibado"), E.build("desplegado"), E.build("fase1")
    r = viz.render
    M = {}

    # ---------------------------------------------------------------- exterior en lanzamiento
    M["ext"] = r(est, f"{out}/e_exterior.png", V_VERT, (1500, 2000), 1.25, marcas={
        "cubierta": (110, 0, 45), "vidrio": (215, -42.3, -15.4), "carbono": (60, -42.3, -15.4), "nadir": (0, 0, -20),
        "tapa": (238, -40, 20), "bisagra": (199, -YL, ZL), "panel": (160, -41.6, -5), "ranura": (100, -YL, ZL),
        "pivote": (14, -YL, ZL)})
    et = [("cubierta", "Cubierta dorsal: la vela\nva plegada debajo"),
          ("vidrio", "Tramo superior: vidrio-epoxi\n0,6 mm (deja pasar la radio)"),
          ("carbono", "Tramo inferior:\ncarbono-epoxi 0,8 mm"), ("nadir", "Ventana de nadir Ø14"),
          ("tapa", "Tapa M5 de la copa\n(la expulsa un resorte)"), ("bisagra", "Bisagra de la puntera\n(retenida por el lazo)"),
          ("panel", "Panel solar 50 × 30\n(embutido en el flanco)"), ("ranura", "Ranura 6 × 192 con el\nlarguero CF Ø4/2"),
          ("pivote", "Pivote del larguero\n(x = 14 mm)")]
    i, d = lados(M, "ext", et)
    anotar(out, M, "e_exterior", "ext", izq=i, der=d, ancho=7.0, col=0.30)

    # ---------------------------------------------------------------- corte longitudinal
    M["corte"] = r(est, f"{out}/e_corte.png", V_CORTE, (1500, 2000), 1.25, clip=((0, -1, 0), (0, 0, 0)),
                   sin_corte=("equipo",), marcas={
        "paracaidas": (229, 1, 16), "tapa": (238, 1, -32), "pasador": (225, -6, 0), "m4": (218, 1, -36),
        "capsula": (194, -8, 20), "camara_c": (210.2, 22.3, 0), "m3": (175, 1, -36), "gnss": (157, -9, 16),
        "antena": (143, 8, 26), "pcb": (135, -15, -12), "m2": (85, 1, -36), "lastre": (75, 17.8, 23.3),
        "bateria": (42.7, -20, 1.7), "vela": (110, 0.5, 41.6), "larguero": (60, YL, ZL + 1.9), "pivote": (15, 25.9, 27.8),
        "baliza": (21, 18, -1), "camara_n": (10, -11, -20), "m1": (2, 1, -36)})
    et = [("paracaidas", "Paracaídas Ø233 plegado\n(copa, bahía 5)"), ("tapa", "Tapa M5 y resorte expulsor"),
          ("pasador", "Pasador de liberación Ø3\n(corte doble)"), ("m4", "M4: mamparo de cenit"),
          ("capsula", "Cápsula de nicrom (PTFE)\ny lazo de Dyneema"), ("camara_c", "Cámara de cenit\n(35° sobre el flanco)"),
          ("m3", "M3: mamparo de aviónica"), ("gnss", "GNSS con antena cerámica"),
          ("antena", "Antena 915 MHz\n(x > 135, bajo el vidrio)"), ("pcb", "PCB principal: MCU, IMU,\nbarómetro, INA219"),
          ("m2", "M2: mamparo puente"), ("lastre", "Lastre: arandelas\nen las varillas"),
          ("bateria", "Pack 2 × 18650\n(transversal)"), ("vela", "Vela Rogallo plegada\nen el canal dorsal"),
          ("larguero", "Larguero CF Ø4/2\nen la ranura"), ("pivote", "Pivote: perno M4 y\n2 resortes de torsión"),
          ("baliza", "Baliza con batería propia\n(orificio ≤ 10 mm)"), ("camara_n", "Cámara de nadir\n(ventana Ø14)"),
          ("m1", "M1: fondo de nadir")]
    i, d = lados(M, "corte", et)
    anotar(out, M, "e_corte", "corte", izq=i, der=d, ancho=7.6, col=0.30, fs=8.0)

    # ---------------------------------------------------------------- esqueleto y equipos (sin carcasa)
    oc = ("carcasa", "cubierta", "vela", "tapa", "solar")
    M["esq"] = r(est, f"{out}/e_esqueleto.png", "iso", (2000, 1500), 1.35, hide=oc, marcas={
        "m1": (0, -15, 30), "m2": (83, -20, 38), "m3": (173, -20, 38), "m4": (216, -30, 25),
        "varilla": (40, -23.3, -24.5), "lastre": (75, -28.8, 23.3), "bateria": (42.6, -20, 1.6), "pcb": (150, -22, -12.8),
        "antena": (143, 11, 31), "gnss": (157, -9, 16), "capsula": (194, -8, 20), "larguero": (110, -YL, ZL),
        "pivote": (14, -YL - 3, ZL - 6), "resorte": (228, -38.5, -6)})
    et = [("m1", "M1 (fondo de nadir)"), ("m2", "M2 puente (x = 85)"), ("m3", "M3 (x = 175)"), ("m4", "M4 (x = 218)"),
          ("varilla", "Varillas M3 de Al 6061 (×4)"), ("lastre", "Lastre: arandelas (51 g)"),
          ("bateria", "Pack 2 × 18650"), ("pcb", "PCB principal"), ("antena", "Antena 915 MHz"),
          ("gnss", "GNSS"), ("capsula", "Cápsula de nicrom y lazo"), ("larguero", "Larguero CF estibado"),
          ("pivote", "Bloque de pivote"), ("resorte", "Resorte expulsor\ny paracaídas")]
    i, d = lados(M, "esq", et)
    anotar(out, M, "e_esqueleto", "esq", izq=i, der=d, ancho=9.0, col=0.20)

    # ---------------------------------------------------------------- planeador desplegado (fase 2)
    M["des"] = r(des, f"{out}/e_desplegado.png", V_DES, (2000, 1500), 1.3, marcas={
        "apice": (16, 0, 41), "pivote": (14, -YL, ZL), "larguero": E.larguero_punto(-1, 110),
        "bisagra": E.larguero_punto(-1, 185), "vela": E.vela_punto(1, 0.55, 0.55), "fuga": E.vela_punto(-1, 1.0, 0.45),
        "holgura": E.vela_punto(-1, 0.62, 0.5), "cuerpo": (60, -42.3, -15.4), "nadir": (0, 0, -20)})
    et = [("apice", "Ápice: la quilla va en el\ncanal dorsal (190 mm)"),
          ("pivote", "Pivote: perno M4, 2 resortes,\ntope y trinquete a 52°"),
          ("larguero", "Larguero CF Ø4/2 × 225,\nflecha 52°"), ("bisagra", "Bisagra de la puntera (40 mm)"),
          ("vela", "Vela Rogallo de ripstop\n(S = 0,067 m², b = 425 mm)"), ("fuga", "Borde de fuga libre"),
          ("holgura", "Holgura de la tela:\ninflado de 31 mm"), ("cuerpo", "Cuerpo laminado\n(carbono / vidrio)"),
          ("nadir", "Ventana de nadir")]
    i, d = lados(M, "des", et)
    anotar(out, M, "e_desplegado", "des", izq=i, der=d, ancho=9.0, col=0.20)

    # ---------------------------------------------------------------- fase 1: bajo el paracaidas
    _, info = E.paracaidas_abierto()
    xa = info["x_apex"]
    M["f1"] = r(f1, f"{out}/e_fase1.png", V_F1, (1100, 2400), 1.15, ssao=False, marcas={
        "tela": E.paracaidas_punto(0.55, 165),
        "ventana": (xa, 0, 0), "lineas": (info["x_sw"] + 0.55 * (info["x_skirt"] - info["x_sw"]),
                                          -0.55 * info["rp"] * 0.707, 0.55 * info["rp"] * 0.707),
        "destorcedor": (info["x_conf"] + 5, 0, 0), "pasador": (info["x_conf"] - 3, -5, 0),
        "brida": (250, -0.5 * 23.3, 0.5 * 23.3), "cansat": (120, -42.3, 15.4)})
    et = [("tela", "Paracaídas plano Ø233\n(gajos de ripstop)"), ("ventana", "Ventana central Ø40"),
          ("lineas", "8 líneas de Kevlar\n(282 mm)"), ("destorcedor", "Destorcedor"),
          ("pasador", "Pasador de liberación:\nlo retiene el lazo"), ("brida", "Brida de 4 ramales\na las varillas"),
          ("cansat", "CanSat: 15 m/s,\nala todavía plegada")]
    i = [x for x in et if x[0] in ("lineas", "pasador", "brida", "cansat")]
    d = [x for x in et if x[0] in ("ventana", "tela", "destorcedor")]
    anotar(out, M, "e_fase1", "f1", izq=i, der=d, ancho=6.4, col=0.32,
           pos={"ventana": 0.06, "tela": 0.22, "destorcedor": 0.50, "lineas": 0.30, "pasador": 0.47, "brida": 0.58,
                "cansat": 0.80})
    json.dump(M, open(f"{out}/marcas_e.json", "w"), indent=1)

    # ---------------------------------------------------------------- secuencia de la mision
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Inter"
    ims = [plt.imread(f"{out}/{n}.png") for n in ("e_exterior", "e_fase1", "e_desplegado")]
    tit = ["1. Lanzamiento: Ø90 × 240,\nala y paracaídas guardados", "2. Fase 1: paracaídas,\n15 m/s",
           "3. Fase 2 (80 % del apogeo): vela\nRogallo en espiral, 5 m/s"]
    fig = plt.figure(figsize=(11.0, 5.4))
    pos = [[0.0, 0.0, 0.2, 0.86], [0.2, 0.0, 0.22, 0.86], [0.43, 0.08, 0.57, 0.70]]
    for k in range(3):
        ax = fig.add_axes(pos[k])
        ax.imshow(ims[k], interpolation="lanczos")
        ax.axis("off")
        fig.text(pos[k][0] + pos[k][2] / 2, 0.985, tit[k], ha="center", va="top", fontsize=10.5, color="#1f2a44",
                 weight="bold")
    fig.savefig(f"{out}/e_secuencia.png", dpi=220)
    plt.close(fig)
    print("renders rev. E ok")


if __name__ == "__main__":
    main(sys.argv[1])
