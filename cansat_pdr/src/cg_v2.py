"""Centro de gravedad del diseno v2 B regulable (estaciones roscadas).

x se mide desde el fondo de nadir (x = 0) hacia la tapa de cenit (x = 240), como en el documento v2.
Los modulos que se corren sobre las varillas son:
  - modulo de bateria: M2 + cuna en U + pack 2 x 18650 (+ sus tuercas); x_m2 = cara inferior de M2 (nominal 83)
  - modulo de avionica: M3 + rieles + PCB principal + radio + GNSS (+ sus tuercas); x_m3 = cara inferior de M3 (nominal 173)
Masas: documento v2, con la carena recalculada (163 g) y las tuercas de las estaciones.
Punto neutro de la vela: 55 a 67 % de la quilla de 190 mm desde el apice (x = 14): 119 a 141 mm.
"""
import json
import os
import numpy as np
import idioma  # noqa: F401

NOM2, NOM3 = 83.0, 173.0
RANGO2 = (66.0, 90.0)          # limites por la baliza / la cuna (abajo) y los rieles de la avionica (arriba)
RANGO3 = (156.0, 177.0)        # limites por los rieles (abajo) y la capsula de nicrom (arriba)
XPN = (14 + 0.55 * 190, 14 + 0.67 * 190)
CR = 190.0

# Masas del documento v2 con la carena recalculada, y los cambios para quedar debajo de 500 g (PESO_V2 guarda el valor
# original de cada item cambiado, para la tabla de reduccion de masa).
FIJOS = [  # (item, masa g, x mm)
    ("Carena PETG 2 mm (240 mm, ranuras y canal)", 163.0, 118.0),
    ("M1 fondo de nadir (25 % de relleno)", 9.7, 2.0), ("M4 mamparo de cenit (25 % de relleno)", 9.7, 218.0),
    ("M5 tapa de la copa (2 mm con nervios)", 7.0, 238.0),
    ("Varillas roscadas M3 Al 6061 (4)", 13.6, 113.0), ("Tuercas de los extremos (8, Al 7075)", 1.6, 111.5),
    ("Tuercas de M1 y M4 (8, Al 7075)", 1.6, 110.0),
    ("Paracaídas Ø226 ripstop + líneas", 8.0, 229.0), ("Horquilla y pasador de liberación", 2.0, 225.0),
    ("Servo de la tapa SG90 + traba", 9.5, 199.0),
    ("Vela Rogallo plegada", 11.5, 110.0), ("Largueros CF + bisagras", 11.0, 103.0),
    ("Pivotes: ejes M4 de Al 7075, manivelas y bloques", 5.0, 14.0),
    ("Servo de liberación del paracaídas SG90 + varilla", 9.5, 200.0),
    ("Servo del ala SG90 + bocina y 2 bielas", 10.5, 11.0),
    ("Panel solar (1)", 4.5, 160.0), ("Baliza piezo + pila propia", 10.0, 12.0),
    ("Cámara de nadir", 11.5, 10.0), ("Cámara de cenit", 11.5, 203.0), ("Cableado y conectores (arnés corto)", 15.0, 120.0),
]
BATERIA = [("Pack 2 × 18650 (2200 mAh)", 89.0, -23.0), ("Cuna en U (PETG, paredes de 2 mm)", 7.0, -23.0),
           ("M2 (25 % de relleno)", 9.7, 2.0), ("Tuercas de M2 (8, Al 7075)", 1.6, 2.0)]
AVIONICA = [("PCB principal", 28.0, -41.0), ("Radio LoRa RFM95W 920 MHz + antena", 4.0, -45.0), ("GNSS u-blox NEO-7M + antena", 12.0, -16.0),
            ("Rieles de las placas", 8.0, -39.0), ("M3 (25 % de relleno)", 9.7, 2.0), ("Tuercas de M3 (8, Al 7075)", 1.6, 2.0)]
REDUCCION = [  # (cambio, g antes, g despues)
    ("Mamparos M1–M4 al 25 % de relleno (v2: 40 %)", 4 * 13.2, 4 * 9.7),
    ("Tapa M5 de 2 mm con nervios (v2: 4 mm)", 13.2, 7.0),
    ("Un panel solar (despiece del equipo; E3 pide uno o más)", 9.0, 4.5),
    ("Baliza piezo con pila propia más chica", 15.0, 10.0),
    ("Arnés de cables más corto", 20.0, 15.0),
    ("Cuna de la batería con paredes de 2 mm", 10.0, 7.0),
    ("Tuercas de los extremos de Al 7075", 4.4, 1.6),
    ("Ejes de los pivotes de Al 7075", 4.2, 1.5),
]


def items(x_m2=NOM2, x_m3=NOM3):
    return (FIJOS + [(n, m, x_m2 + d) for n, m, d in BATERIA] + [(n, m, x_m3 + d) for n, m, d in AVIONICA])


def cg(x_m2=NOM2, x_m3=NOM3):
    it = items(x_m2, x_m3)
    m = sum(t[1] for t in it)
    return m, sum(t[1] * t[2] for t in it) / m


def margen(xcg):
    return [(xp - xcg) / CR for xp in XPN]


def resumen():
    m, xn = cg()
    casos = {"nominal": (NOM2, NOM3), "bateria abajo": (RANGO2[0], NOM3), "bateria arriba": (RANGO2[1], NOM3),
             "todo abajo": (RANGO2[0], RANGO3[0]), "todo arriba": (RANGO2[1], RANGO3[1])}
    out = dict(masa=m, m_bateria=sum(t[1] for t in BATERIA), m_avionica=sum(t[1] for t in AVIONICA), casos={})
    for k, (a, b) in casos.items():
        _, x = cg(a, b)
        out["casos"][k] = dict(x_m2=a, x_m3=b, x_cg=x, ME=margen(x))
    return out


def figura(out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    d = np.linspace(RANGO2[0] - NOM2, RANGO2[1] - NOM2, 200)
    solo = [cg(NOM2 + v, NOM3)[1] for v in d]
    junto = [cg(NOM2 + v, float(np.clip(NOM3 + v, *RANGO3)))[1] for v in d]
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.axhspan(95, 105, color="#e8f1fb", lw=0)
    ax.text(d[0] + 0.4, 95.4, "CG objetivo de v2: 95–105 mm", fontsize=8.8, color="#52514e", va="bottom")
    ax.axhline(XPN[0], color="#d03b3b", lw=1.2, ls="--")
    ax.text(d[-1], XPN[0] + 0.35, f"punto neutro (estimación baja): {XPN[0]:.0f} mm — margen estático 0",
            fontsize=8.8, color="#d03b3b", va="bottom", ha="right")
    ax.plot(d, solo, color="#2a78d6", lw=2, label="se corre solo el módulo de batería (M2)")
    ax.plot(d, junto, color="#eb6834", lw=2, label="se corren batería y aviónica juntas (M2 y M3)")
    m, xn = cg()
    ax.plot([0], [xn], "o", ms=8, color="#0b0b0b", mec="white", mew=1.5, zorder=5)
    ax.annotate(f"nominal: {xn:.1f} mm".replace(".", ","), (0, xn), xytext=(-10, 12), textcoords="offset points", fontsize=9,
                ha="right")
    for v, y in ((d[0], junto[0]), (d[-1], junto[-1])):
        ax.annotate(f"{y:.1f}".replace(".", ","), (v, y), xytext=(0, -14 if v < 0 else 6), textcoords="offset points",
                    fontsize=8.8, ha="center", color="#eb6834")
    ax.set_xlabel("Corrimiento del módulo de batería desde la estación nominal [mm]  (− = hacia nadir)")
    ax.set_ylabel("CG desde el fondo de nadir [mm]")
    ax.set_ylim(94, 122)
    ax.grid(color="#e6e6e6", lw=0.6)
    ax.set_axisbelow(True)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.legend(loc="lower right", fontsize=8.8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "v2BR_cg.png"), dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    R = resumen()
    print(json.dumps(R, indent=1))
    if len(sys.argv) > 1:
        json.dump(R, open(os.path.join(sys.argv[1], "..", "fea", "cg_v2BR.json"), "w"), indent=1)
        figura(sys.argv[1])
