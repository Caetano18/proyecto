# Figuras explicativas de la guia (anatomia de cada grafico). Las figuras de los
# ejemplos completos salen directamente de ../analisis_simple/analisis.py.
# Uso:  python hacer_figuras.py    (escribe los PNG en la carpeta figuras/)

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import control as ct

s = ct.tf("s")
AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "figuras")
os.makedirs(OUT, exist_ok=True)

AZUL, ROJO, VERDE, GRIS, NARANJA = "#1f4e79", "#b91e28", "#007346", "#5f5f5f", "#d76e00"
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3, "savefig.dpi": 200})


def fase_deg(Lw, tipo):
    f = np.degrees(np.unwrap(np.angle(Lw)))
    return f - 360*np.round((f[0] + 90*tipo)/360)


def guardar(fig, nombre):
    fig.savefig(os.path.join(OUT, nombre), bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 1. anatomia del Bode
L = 4/(s*(s + 1)*(0.1*s + 1))                    # tipo 1, Kv = 4
w = np.logspace(-2, 2.5, 3000)
Lw = L(1j*w)
mag, fas = 20*np.log10(abs(Lw)), fase_deg(Lw, 1)
gm, pm, _, w180, wc, _ = ct.stability_margins(L)
mg_db = 20*np.log10(gm)

fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(8.2, 7.2))
a1.semilogx(w, mag, AZUL, lw=2)
a2.semilogx(w, fas, AZUL, lw=2)
a1.axhline(0, color="k", lw=0.9)
a2.axhline(-180, color="k", lw=0.9)
for a in (a1, a2):
    a.axvline(wc, color=ROJO, ls=":", lw=1.4)
    a.axvline(w180, color=VERDE, ls="-.", lw=1.4)
# asintota de baja frecuencia: -20 dB/dec que corta 0 dB en w = Kv
wk = np.array([0.01, 4.0])
a1.semilogx(wk, 20*np.log10(4/wk), color=NARANJA, ls="--", lw=1.4)
a1.plot([4], [0], "o", color=NARANJA)
a1.annotate("la asíntota de $-20$ dB/dec\ncorta 0 dB en $\\omega = K_v = 4$", (4, 0), (6, 24),
            color=NARANJA, arrowprops=dict(arrowstyle="->", color=NARANJA), fontsize=9)
caja = dict(fc="white", ec="none", alpha=0.85)
# margen de ganancia
a1.annotate("", (w180, 0), (w180, -mg_db), arrowprops=dict(arrowstyle="<->", color=VERDE, lw=1.6))
a1.text(w180*1.15, 7, f"MG = {mg_db:.1f} dB", color=VERDE, va="center", bbox=caja)
# margen de fase
a2.annotate("", (wc, pm - 180), (wc, -180), arrowprops=dict(arrowstyle="<->", color=ROJO, lw=1.6))
a2.text(wc*0.88, -172, f"MF = {pm:.0f}°", color=ROJO, va="center", ha="right", bbox=caja)
a1.text(wc*0.93, 56, "$\\omega_c$ (cruce por 0 dB)", color=ROJO, ha="right", va="center", fontsize=9, bbox=caja)
a2.text(w180*0.93, -255, "$\\omega_{180}$ (la fase vale $-180°$)", color=VERDE, ha="right", va="center", fontsize=9, bbox=caja)
# pendientes
for x, y, txt in [(0.1, 20, "$-20$ dB/dec"), (1.1, -14, "$-40$ dB/dec"), (14, -72, "$-60$ dB/dec")]:
    a1.text(x, y, txt, color=GRIS, fontsize=9, ha="center", bbox=caja)
a1.text(0.012, 8, "a baja frecuencia la pendiente\ninicial dice el tipo del sistema", color=GRIS, fontsize=9, va="center")
a2.text(0.012, -120, "arranca en $-90°$\n(un integrador)", color=GRIS, fontsize=9, va="center")
a1.set_ylabel("Magnitud [dB]")
a2.set_ylabel("Fase [grados]")
a2.set_xlabel("$\\omega$ [rad/s]")
a1.set_ylim(-95, 65)
a2.set_ylim(-285, -75)
a1.set_title("$L(s) = 4/[s(s+1)(0{,}1s+1)]$")
guardar(fig, "bode_anatomia.png")

# ---------------------------------------------------------------- 2. galeria de Nyquist
casos = [
    ("(a) estable", 1/(s*(s + 1)*(s + 2)), None),
    ("(b) inestable", 12/(s*(s + 1)*(s + 2)), None),
    ("(c) marginal", 6/(s*(s + 1)*(s + 2)), None),
    ("(d) lazo abierto inestable", 2*(s + 3)/(s*(s - 1)), None),
    ("(e) con retardo, estable", None, 1.0),
    ("(f) con retardo, inestable", None, 1.5),
]
fig, ejes = plt.subplots(2, 3, figsize=(11.5, 7.6))
w = np.logspace(-3, 3, 6000)
for ax, (tit, Lc, Kret) in zip(ejes.flat, casos):
    if Lc is None:                                  # retardo exacto: K e^{-0.8 s}/(s(s+1))
        Lw = Kret*np.exp(-0.8j*w)/(1j*w*(1j*w + 1))
        n_, d_ = ct.pade(0.8, 10)
        Lp = Kret*ct.tf(n_, d_)/(s*(s + 1))
        P = 0
        Z = int(np.sum(ct.poles(ct.feedback(Lp, 1)).real > 1e-9))
        N = Z - P
    else:
        Lw = Lc(1j*w)
        P = int(np.sum(ct.poles(Lc).real > 1e-9))
        N = ct.nyquist_response(Lc).count
        Z = P + N
    ax.plot(Lw.real, Lw.imag, AZUL, lw=1.8)
    ax.plot(Lw.real, -Lw.imag, AZUL, lw=1.2, ls="--")
    ax.plot(-1, 0, "x", color=ROJO, ms=9, mew=2)
    ax.axhline(0, color="k", lw=0.7)
    ax.axvline(0, color="k", lw=0.7)
    ax.set_xlim(-3, 1)
    ax.set_ylim(-2.2, 2.2)
    est = "estable" if Z == 0 else "inestable"
    if "marginal" in tit:
        est, Z = "marginal", "-"
    ax.set_title(tit, fontsize=10)
    ax.text(0.03, 0.04, f"P = {P}   N = {N}\nZ = {Z}  ({est})", transform=ax.transAxes, fontsize=9,
            bbox=dict(fc="white", ec=GRIS, alpha=0.85), va="bottom")
    ax.set_xlabel("Re L")
    ax.set_ylabel("Im L")
fig.tight_layout()
guardar(fig, "nyquist_galeria.png")

# ---------------------------------------------------------------- 3. anatomia de Nichols
L = 4/(s*(s + 1)*(0.1*s + 1))
L = 0.55*L                                       # MF ~ 45 grados
w = np.logspace(-2, 2.5, 4000)
Lw = L(1j*w)
fas, mag = fase_deg(Lw, 1), 20*np.log10(abs(Lw))
gm, pm, _, w180, wc, _ = ct.stability_margins(L)
mg_db = 20*np.log10(gm)
th = np.radians(np.linspace(-179.9, 179.9, 1441))
fig, ax = plt.subplots(figsize=(7.8, 6.4))
for Mdb in [-12, -6, -3, -1, 0, 1, 3, 6]:
    M = 10**(Mdb/20)
    T = M*np.exp(1j*th)
    Lc = T/(1 - T)
    ph = np.degrees(np.angle(Lc)) % 360 - 360          # fase en (-360, 0]
    mg = 20*np.log10(abs(Lc))
    salto = np.flatnonzero(abs(np.diff(ph)) > 180)     # cortar donde la fase da la vuelta
    ph, mg = ph.copy(), mg.copy()
    ph[salto] = np.nan
    ax.plot(ph, mg, color=GRIS, lw=0.8, alpha=0.8)
    k = np.nanargmax(np.where(np.isfinite(ph) & (ph > -265) & (ph < -75) & (mg < 36), mg, -np.inf))
    ax.text(ph[k], mg[k] + 0.6, f"{Mdb} dB", fontsize=7.5, color=GRIS, ha="center")
ax.plot(fas, mag, AZUL, lw=2.2)
ax.plot(-180, 0, "x", color=ROJO, ms=11, mew=2.5)
ax.text(-183, 2.5, "punto crítico\n$(-180°,\\ 0\\ \\mathrm{dB})$", color=ROJO, ha="right", fontsize=9)
ax.annotate("", (pm - 180, 0), (-180, 0), arrowprops=dict(arrowstyle="<->", color=ROJO, lw=1.6))
ax.text(pm/2 - 180, 1.6, f"MF = {pm:.0f}°", color=ROJO, ha="center", fontsize=9)
ax.annotate("", (-180, -mg_db), (-180, 0), arrowprops=dict(arrowstyle="<->", color=VERDE, lw=1.6))
ax.text(-184, -mg_db/2 - 1, f"MG = {mg_db:.1f} dB", color=VERDE, va="center", ha="right", fontsize=9,
        bbox=dict(fc="white", ec="none", alpha=0.9))
ax.annotate("al subir la frecuencia\nla curva baja", (-196, -22), (-150, -27), color=AZUL, fontsize=9,
            arrowprops=dict(arrowstyle="->", color=AZUL))
ax.annotate("baja frecuencia:\nganancia alta, fase $-90°$", (-93, 34), (-150, 34), color=AZUL, fontsize=9, ha="center", va="center",
            arrowprops=dict(arrowstyle="->", color=AZUL))
ax.set_xlim(-270, -60)
ax.set_ylim(-35, 40)
ax.set_xlabel("Fase de $L$ [grados]")
ax.set_ylabel("Magnitud de $L$ [dB]")
ax.set_title("Curvas grises: $|T|$ = M constante (dB) del lazo cerrado")
guardar(fig, "nichols_anatomia.png")

# ---------------------------------------------------------------- 4. escalon vs MF (2do orden)
zetas = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
t = np.linspace(0, 14, 1500)
for z in zetas:
    T = ct.tf([1], [1, 2*z, 1])
    tt, y = ct.step_response(T, t)
    a1.plot(tt, y, lw=1.6, label=f"$\\zeta$ = {z}")
a1.axhline(1, color="k", lw=0.7, ls="--")
a1.set_xlabel("$\\omega_n t$")
a1.set_ylabel("$y$")
a1.set_title("Escalón de $\\omega_n^2/(s^2+2\\zeta\\omega_n s+\\omega_n^2)$")
a1.legend(fontsize=8)
z = np.linspace(0.05, 1.0, 300)
MF2 = np.degrees(np.arctan(2*z/np.sqrt(np.sqrt(1 + 4*z**4) - 2*z**2)))
Mp2 = 100*np.exp(-np.pi*z/np.sqrt(1 - z**2))
Mp2[z >= 1] = 0
a2.plot(z, MF2, AZUL, lw=2, label="MF [grados]")
a2.plot(z, 100*z, AZUL, lw=1.2, ls="--", label="regla MF $\\approx 100\\zeta$")
a2.plot(z, Mp2, ROJO, lw=2, label="Mp [%]")
a2.set_xlim(0, 1)
a2.set_ylim(0, 90)
a2.set_xlabel("$\\zeta$")
a2.set_title("Margen de fase y sobreimpulso vs. amortiguamiento")
a2.legend(fontsize=8)
fig.tight_layout()
guardar(fig, "escalon_vs_MF.png")

# ---------------------------------------------------------------- 5. compensadores
def red(T, razon):
    return (T*s + 1)/(razon*T*s + 1)

alfa, T1 = 0.15, 0.5
beta, T2 = 20, 10
w = np.logspace(-3, 3, 3000)
cas = [("Adelanto $(Ts+1)/(\\alpha Ts+1)$, $\\alpha=0{,}15$", red(T1, alfa)),
       ("Atraso $(Ts+1)/(\\beta Ts+1)$, $\\beta=20$", red(T2, beta)),
       ("Atraso-adelanto (los dos en serie)", red(T1, alfa)*red(T2, beta))]
fig, ejes = plt.subplots(2, 3, figsize=(11.5, 6.4), sharex=True)
for j, (tit, Gc) in enumerate(cas):
    Gw = Gc(1j*w)
    a1, a2 = ejes[0, j], ejes[1, j]
    a1.semilogx(w, 20*np.log10(abs(Gw)), VERDE, lw=2)
    a2.semilogx(w, np.degrees(np.angle(Gw)), VERDE, lw=2)
    a1.set_title(tit, fontsize=9.5)
    a1.set_ylabel("|Gc| [dB]")
    a2.set_ylabel("fase [grados]")
    a2.set_xlabel("$\\omega$ [rad/s]")
    a2.axhline(0, color="k", lw=0.7)
    a1.axhline(0, color="k", lw=0.7)
wm = 1/(T1*np.sqrt(alfa))
phim = np.degrees(np.arcsin((1 - alfa)/(1 + alfa)))
ejes[0, 0].axvline(1/T1, color=GRIS, ls=":")
ejes[0, 0].axvline(1/(alfa*T1), color=GRIS, ls=":")
ejes[0, 0].text(1/T1*0.9, 2, "cero\n$1/T$", ha="right", fontsize=8, color=GRIS)
ejes[0, 0].text(1/(alfa*T1)*1.1, 2, "polo\n$1/(\\alpha T)$", ha="left", fontsize=8, color=GRIS)
ejes[1, 0].plot([wm], [phim], "o", color=ROJO)
ejes[1, 0].annotate(f"$\\varphi_m$ = {phim:.0f}°\nen $\\omega_m$", (wm, phim), (wm*4, phim - 14), fontsize=9, color=ROJO,
                    arrowprops=dict(arrowstyle="->", color=ROJO))
ejes[0, 0].annotate("a $\\omega_m$ sube\n$10\\log(1/\\alpha)$ = 8,2 dB", (wm, 10*np.log10(1/alfa)), (0.003, 9), fontsize=9, color=ROJO,
                    arrowprops=dict(arrowstyle="->", color=ROJO))
ejes[0, 1].axvline(1/T2, color=GRIS, ls=":")
ejes[0, 1].axvline(1/(beta*T2), color=GRIS, ls=":")
ejes[0, 1].text(1/(beta*T2)*0.9, -24, "polo\n$1/(\\beta T)$", ha="right", fontsize=8, color=GRIS)
ejes[0, 1].text(1/T2*1.1, -24, "cero\n$1/T$", ha="left", fontsize=8, color=GRIS)
ejes[0, 1].annotate("baja $20\\log\\beta = 26$ dB\nen alta frecuencia", (50, -26), (1.5, -12), fontsize=9, color=ROJO,
                    arrowprops=dict(arrowstyle="->", color=ROJO))
ejes[1, 1].annotate("fase negativa:\nresta MF cerca de\nesa zona", (0.02, -45), (0.2, -62), fontsize=9, color=ROJO,
                    arrowprops=dict(arrowstyle="->", color=ROJO))
ejes[0, 2].set_ylim(-30, 5)
fig.tight_layout()
guardar(fig, "compensadores.png")
# ---------------------------------------------------------------- 6. escalon del ejemplo del parcial 1
G = 100/(s**3 + 10*s**2 + 5*s)
Gc = (50*s + 1)/(4700*s + 1)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
for a, tmax in ((a1, 12), (a2, 320)):
    tt = np.linspace(0, tmax, 6000)
    t1, y1 = ct.step_response(ct.feedback(G, 1), tt)
    t2, y2 = ct.step_response(ct.feedback(Gc*G, 1), tt)
    if a is a1:
        a.plot(t1, np.clip(y1, -4, 4), AZUL, lw=1.6, label="sin compensar (inestable, recortada a $\\pm4$)")
    a.plot(t2, y2, ROJO, lw=1.8, label="compensado")
    a.axhline(1, color="k", lw=0.7, ls="--")
    a.set_xlabel("t [s]")
    a.set_ylabel("y(t)")
a1.set_title("primeros 12 s")
a2.set_title("el compensado, hasta 320 s")
a2.set_ylim(0, 1.3)
a1.legend(fontsize=8, loc="upper left")
a2.legend(fontsize=8, loc="lower right")
fig.tight_layout()
guardar(fig, "p1_escalon.png")

print("listo:", sorted(os.listdir(OUT)))
