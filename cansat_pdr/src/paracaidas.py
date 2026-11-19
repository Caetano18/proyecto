"""Paracaidas del contenedor (primera etapa, C3: 15 +/- 3 m/s con el CanSat completo).

Equilibrio de descenso: m g = 1/2 rho V^2 Cd0 S0  ->  S0 = 2 m g / (rho V^2 Cd0)
Cd0 referido al area nominal de tela S0 (Knacke, Parachute Recovery Systems Design Manual, tabla 5-1):
  plano circular  0,75-0,80   oscilacion +-10 a 40 grados
  cruz            0,60-0,85   oscilacion 0 a +-3 grados
  hemisferico     0,62-0,77   oscilacion +-10 a 15 grados
Uso: python3 paracaidas.py <salida.json> <figura_en.png>
"""
import sys, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import params as P

RHO = 1.15            # kg/m3: atmosfera estandar a unos 700 m (sitio + altura de apertura)
V_OBJ, V_MIN, V_MAX = 15.0, 12.0, 18.0
G = P.G0
TEX = 40.0 * 1.3      # g/m2 de ripstop con costuras
DISENOS = [
    dict(clave="plano", nombre="Flat circular (hexagonal, 15 % spill hole)", cd=0.75, osc="±10 to 40°", fab="6 gores, spill hole"),
    dict(clave="cruz", nombre="Cross (cruciform, 5 squares)", cd=0.70, osc="0 to ±3°", fab="flat cloth, no gores"),
    dict(clave="hemi", nombre="Hemispherical", cd=0.70, osc="±10 to 15°", fab="8 to 12 shaped gores"),
]


def area(m, cd, v=V_OBJ, rho=RHO):
    return 2 * m * G / (rho * v ** 2 * cd)


def vel(m, cd, s0, rho=RHO):
    return math.sqrt(2 * m * G / (rho * cd * s0))


def main(out_json, out_fig):
    mas = json.load(open("../fea/masas.json"))
    m_tot = mas["total"] / 1000
    m_cont = mas["m_contenedor"] / 1000
    filas = []
    for d in DISENOS:
        s0 = area(m_tot, d["cd"])
        if d["clave"] == "plano":
            geo = dict(D0_mm=1000 * math.sqrt(4 * s0 / math.pi))
            txt = "D0 = %.0f mm" % geo["D0_mm"]
        elif d["clave"] == "cruz":
            w = math.sqrt(s0 / 5)
            geo = dict(brazo_mm=1000 * w, envergadura_mm=3000 * w)
            txt = "arm width %.0f mm, span %.0f mm" % (1000 * w, 3000 * w)
        else:
            r = math.sqrt(s0 / (2 * math.pi))
            geo = dict(D_proyectado_mm=2000 * r)
            txt = "projected D = %.0f mm" % (2000 * r)
        m_tela = s0 * TEX
        filas.append(dict(d, S0_cm2=1e4 * s0, geo=geo, geo_txt=txt, m_tela_g=m_tela,
                          v_rango=[vel(m_tot, d["cd"] * 1.10, s0), vel(m_tot, d["cd"] * 0.90, s0)],
                          v_contenedor=vel(m_cont, d["cd"], s0)))
    # borrador del equipo: paracaidas plano de 45 cm
    s45 = math.pi * 0.45 ** 2 / 4
    res = dict(rho=RHO, m_total_g=1000 * m_tot, m_contenedor_g=1000 * m_cont, v_obj=V_OBJ, disenos=filas,
               plano_45cm=dict(S0_cm2=1e4 * s45, v=vel(m_tot, 0.75, s45)))
    json.dump(res, open(out_json, "w"), indent=1)
    # ---------------- figura (ingles: va a las laminas)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=230)
    s = np.linspace(150, 2000, 400) * 1e-4
    ax.axhspan(V_MIN, V_MAX, color="#138A8A", alpha=0.10, lw=0)
    ax.text(1960, 17.6, "C3: 15 ± 3 m/s", ha="right", va="top", color="#138A8A", fontsize=10, weight="bold")
    cols = {"plano": "#242C4F", "cruz": "#138A8A", "hemi": "#138A8A"}
    vistos = set()
    for f in filas:
        if f["cd"] in vistos and f["clave"] == "hemi":
            continue
        vistos.add(f["cd"])
        lab = "Cd0 = %.2f (%s)" % (f["cd"], "flat circular" if f["clave"] == "plano" else "cross / hemispherical")
        ax.plot(1e4 * s, [vel(m_tot, f["cd"], x) for x in s], color=cols[f["clave"]], lw=2.0, label=lab)
    for f in filas:
        ax.plot(f["S0_cm2"], V_OBJ, "o", color=cols[f["clave"]], ms=7, zorder=5)
    ax.plot(res["plano_45cm"]["S0_cm2"], res["plano_45cm"]["v"], "s", color="#B23A2E", ms=7, zorder=5)
    ax.annotate("45 cm flat canopy\n(draft): %.1f m/s" % res["plano_45cm"]["v"], (res["plano_45cm"]["S0_cm2"], res["plano_45cm"]["v"]),
                (1180, 5.2), fontsize=9, color="#B23A2E", arrowprops=dict(arrowstyle="-", color="#B23A2E", lw=0.8))
    ax.set_xlim(150, 2000)
    ax.set_ylim(4, 32)
    ax.set_xlabel("Canopy nominal area S0 [cm²]")
    ax.set_ylabel("Descent rate, %.0f g [m/s]" % (1000 * m_tot))
    ax.grid(color="0.88", lw=0.6)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.93), fontsize=9)
    fig.tight_layout()
    fig.savefig(out_fig)
    for f in filas:
        print(f"{f['nombre']:45s} S0 = {f['S0_cm2']:6.0f} cm2  {f['geo_txt']:34s} tela {f['m_tela_g']:.1f} g  "
              f"V {f['v_rango'][0]:.1f}-{f['v_rango'][1]:.1f}  contenedor solo {f['v_contenedor']:.1f} m/s")
    print("plano de 45 cm: %.1f m/s" % res["plano_45cm"]["v"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
