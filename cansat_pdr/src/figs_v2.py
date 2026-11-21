"""Diagramas CAD del documento v2 del equipo: diseno A (monocasco PETG con mamparos pegados) y diseno B (esqueleto de
4 varillas M3 + mamparos + carena PETG de 2 mm).  Para cada uno: exterior con la carcasa y corte "tipo Sims" (se saca la
pared que mira a la camara y el interior queda entero).
Uso: [FIG_LANG=en] python3 figs_v2.py <carpeta de figuras>
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
V = ((-0.4, -1.1, 0.75), (1, 0, 0))
CUNA = (180.0, 70.0, ("carcasa", "solar", "tornillos", "adhesivo"))


def main(out):
    os.makedirs(out, exist_ok=True)
    M = {}
    for v in "AB":
        E.variante("BR" if v == "B" else v)
        YL, ZL = E.YL, E.ZL
        est = E.build("estibado")
        k = f"v2{v}"
        # ------------------------------------------------ exterior
        mk = {"cubierta": (110, 0, 45), "carcasa": (60, -42.3, -15.4), "nadir": (0, 0, -20), "tapa": (238, -40, 20),
              "bisagra": (199, -YL, ZL), "panel": (160, -41.6, -5), "ranura": (100, -YL, ZL), "pivote": (14, -YL, ZL)}
        et = [("cubierta", "Cubierta dorsal: la vela\nva plegada debajo"),
              ("carcasa", "Monocasco de PETG 2 mm\nimpreso (es la estructura)" if v == "A" else
               "Carena de PETG 2 mm\n(se desliza sobre el esqueleto)"),
              ("nadir", "Ventana de nadir Ø14"), ("tapa", "Tapa M5 de la copa\n(la libera un servo)"),
              ("panel", "Panel solar 45 × 25"),
              ("ranura", "Ranura 6 × 192 con el\nlarguero CF Ø4"), ("pivote", "Pivote del larguero")]
        if v == "A":
            et.append(("bisagra", "Bisagra de la puntera\n(la abre la tensión de la vela)"))
        if v == "B":
            mk["tornillo"] = (218, -45, 0)
            et.append(("tornillo", "Tornillos de la carena\n(3 arriba y 3 abajo)"))
        M[k + "_ext"] = viz.render(est, f"{out}/{k}_exterior.png", V, (1500, 2000), 1.25, marcas=mk)
        i, d = lados(M, k + "_ext", et)
        anotar(out, M, f"{k}_exterior", k + "_ext", izq=i, der=d, ancho=7.8, col=0.31, fs=8.0)
        # ------------------------------------------------ corte tipo Sims
        mk = {"paracaidas": (229, -22.3, 15.2), "m4": (216, -25, -20),
              "capsula": (194, -12.5, 19), "servo_ala": (15.0, 0.0, 17.0), "m3": (173, -25, -20), "gnss": (157, -9, 16),
              "antena": (143, 8.5, 17), "pcb": (135, -15, -12), "m2": (83, -25, -20), "bateria": (45.6, -20, 4.2),
              "baliza": (28, 18, 4), "camara_n": (0, 0, -20), "m1": (0, -25, 15), "vela": (110, -12.5, 40.5),
              "larguero": (100, -YL, ZL), "pivote": (14, -YL, ZL), "carcasa": (120, -15.0, -41.3)}
        et = [("paracaidas", f"Paracaídas Ø{E.D_PARA:.0f} plegado\n(copa, bahía 5)"), 
              ("m4", "M4: mamparo de cenit"), ("capsula", "Servos de la tapa y\ndel paracaídas"),
              ("m3", "M3: mamparo de aviónica"), ("gnss", "GNSS"),
              ("antena", "Antena LoRa 920 MHz"), ("pcb", "PCB principal"), ("m2", "M2: mamparo puente"),
              ("bateria", "Pack 2 × 18650"), ("baliza", "Baliza con batería propia"),
              ("camara_n", "Cámara de nadir\n(ventana Ø14)"), ("m1", "M1: fondo de nadir"),
              ("vela", "Vela Rogallo plegada\nbajo la cubierta"), ("larguero", "Larguero CF Ø4\n(ala estibada)"),
              ("pivote", "Pivote: eje M4 y manivela;\nlo mueve el servo del ala"), ("servo_ala", "Servo del ala: abre los\ndos largueros (bielas)"),
              ("carcasa", "Pared de PETG 2 mm\n(recortada para ver adentro)")]
        if v == "A":
            mk.update({"adhesivo": (172.5, -11.0, -41.1), "cancamo": (214.3, -23.3, -23.3)})
            et += [("adhesivo", "Cordón de adhesivo\nmamparo-carcasa"),
                   ("cancamo", "Cáncamos M3 en M4:\nanclaje de la brida")]
        else:
            mk.update({"varilla": (60, -23.3, 23.3)})
            et += [("varilla", "Varillas M3 de Al 6061 (×4):\nllevan la carga y la brida")]
        M[k + "_sims"] = viz.render(est, f"{out}/{k}_interior.png", V, (1500, 2000), 1.25, cuna=CUNA, marcas=mk)
        i, d = lados(M, k + "_sims", et)
        anotar(out, M, f"{k}_interior", k + "_sims", izq=i, der=d, ancho=7.8, col=0.31, fs=8.0)
    E.variante("E")
    json.dump(M, open(f"{out}/marcas_v2.json", "w"), indent=1)
    print("diagramas v2 ok")


if __name__ == "__main__":
    main(sys.argv[1])
