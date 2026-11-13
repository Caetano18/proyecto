"""Sustentacion del ala delta por la analogia de succion de borde de ataque de Polhamus (NASA TN D-3767, 1966).
    C_L = Kp sen(a) cos^2(a) + f Kv cos(a) sen^2(a)        C_Di = C_L tan(a)
Kp y Kv leidos de las figuras 6 y 9 del informe.  f = fraccion de la sustentacion de vortice que se cuenta.
Uso: python3 polhamus.py <salida.json> <figura.png>
"""
import sys, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import params as P

AR_KP = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
KP = [0.0, 0.75, 1.33, 1.80, 2.20, 2.85, 3.35]        # figura 6
KV0, KV4 = 3.14, 3.45                                  # figura 9 y texto: 3,14 en A = 0, unos 3,45 en A = 4
ALFA, BANK = 20.0, 20.0


def cl(alfa_deg, AR, f):
    a = np.radians(alfa_deg)
    kp = np.interp(AR, AR_KP, KP)
    kv = KV0 + (KV4 - KV0) * AR / 4.0
    return kp * np.sin(a) * np.cos(a) ** 2, f * kv * np.cos(a) * np.sin(a) ** 2


def main(out_json, out_fig, m_vuelo_g):
    N = P.NOTA
    AR = N["AR"]
    a = math.radians(ALFA)
    # resto de la resistencia (parasita + cuerpo), de la nota de membrana: C_D = 0,50 con C_L = 1,20
    cd_resto = 0.50 - 1.20 * math.tan(a)
    k_w = N["w"] / (0.50 / math.hypot(1.20, 0.50) ** 1.5)          # w = k C_D / C_R^1,5 a masa y area fijas
    filas = []
    for f, nombre in ((0.0, "Sin sustentación de vórtice"), (0.5, "Nota de membrana"), (1.0, "Polhamus completo")):
        clp, clv = cl(ALFA, AR, f)
        c_l = float(clp + clv)
        c_d = cd_resto + c_l * math.tan(a)
        w500 = k_w * c_d / math.hypot(c_l, c_d) ** 1.5
        filas.append(dict(f=f, nombre=nombre, CLp=float(clp), CLv=float(clv), CL=c_l, CD=c_d, LD=c_l / c_d, w500=w500,
                          w_vuelo=w500 * math.sqrt(m_vuelo_g / 500.0)))
    res = dict(AR=AR, alfa=ALFA, Kp=float(np.interp(AR, AR_KP, KP)), Kv=KV4, cd_resto=cd_resto, filas=filas, m_vuelo=m_vuelo_g)
    json.dump(res, open(out_json, "w"), indent=1)
    plt.rcParams.update({"font.family": "Inter", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "0.88"})
    al = np.linspace(0, 30, 121)
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.9))
    ax = axs[0]
    p4, v4 = cl(al, AR, 1.0)
    ax.fill_between(al, p4, p4 + v4, color="#2f3192", alpha=0.13, lw=0)
    ax.plot(al, p4 + v4, color="#2f3192", lw=2, label="Polhamus completo (f = 1)")
    ax.plot(al, p4 + 0.5 * v4, color="#c0392b", lw=2, label="Nota de membrana (f = 0,5)")
    ax.plot(al, p4, color="#555555", lw=2, ls="--", label="Solo término potencial (f = 0)")
    ax.axvline(ALFA, color="0.6", lw=0.9)
    ax.plot([ALFA], [filas[1]["CL"]], "o", color="#c0392b", ms=7)
    ax.axvspan(18, 30, color="#e67e22", alpha=0.10, lw=0)
    ax.text(18.4, 0.08, "el ala de AR 2 del informe\nya pierde sustentación", fontsize=8.6, color="#a0520f")
    ax.set_xlabel("Ángulo de ataque [°]")
    ax.set_ylabel("$C_L$")
    ax.set_title(f"Ala delta de AR = {AR:g} (fuera del rango ensayado: 0,5 a 2)", fontsize=11, weight="bold")
    ax.legend(fontsize=8.8, loc="upper left")
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 2.0)
    ax = axs[1]
    fs = np.linspace(0, 1, 41)
    for m, c, lab in ((500.0, "#555555", "500 g (nota de membrana)"), (m_vuelo_g, "#2f3192", f"{m_vuelo_g:.0f} g (este diseño)")):
        ws = []
        for f in fs:
            clp, clv = cl(ALFA, AR, f)
            c_l = clp + clv
            c_d = cd_resto + c_l * math.tan(a)
            ws.append(k_w * c_d / math.hypot(c_l, c_d) ** 1.5 * math.sqrt(m / 500.0))
        ax.plot(fs, ws, color=c, lw=2, label=lab)
    ax.axhspan(2, 8, color="#1a8a55", alpha=0.08, lw=0)
    ax.axhline(5, color="#1a8a55", lw=1, ls="--")
    ax.text(0.02, 7.45, "requisito C4: 5 ± 3 m/s", fontsize=9, color="#1a8a55")
    ax.set_xlabel("Fracción de sustentación de vórtice que se cuenta, f")
    ax.set_ylabel("Velocidad de descenso [m/s]")
    ax.set_title(f"Descenso a α = {ALFA:g}° con alabeo de {BANK:g}°", fontsize=11, weight="bold")
    ax.set_ylim(1.5, 8.5)
    ax.legend(fontsize=9, loc="lower left")
    fig.tight_layout()
    fig.savefig(out_fig, dpi=230)
    for r in filas:
        print(f"f={r['f']:.1f}  CL={r['CL']:.2f} (pot {r['CLp']:.2f} + vort {r['CLv']:.2f})  CD={r['CD']:.2f}  L/D={r['LD']:.2f}  "
              f"w500={r['w500']:.2f}  w_vuelo={r['w_vuelo']:.2f}")


if __name__ == "__main__":
    m = json.load(open("../fea/masas.json"))["m_planeador"]
    main(sys.argv[1], sys.argv[2], m)
