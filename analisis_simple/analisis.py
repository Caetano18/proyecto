"""
ANÁLISIS EN FRECUENCIA — versión simple
=======================================
Uso:   1) poné tu función de transferencia en el PASO 0   2) apretá ▶   3) mirá cada paso.
Instalar (una sola vez):   pip install control numpy matplotlib
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import control as ct

# ═════════════════════════════ PASO 0: TUS DATOS ═════════════════════════════
s = ct.tf("s")                       # (no tocar) variable de Laplace

K = 100
G = K / (s**3 + 10*s**2 + 5*s)       # tu función de transferencia de lazo abierto
#   otras formas de escribirla:   G = 50 / (s*(s+1.3)*(s+100))
#                                 G = ct.tf([5], [1, 3, 2])      (coeficientes: numerador, denominador)

CTE_DESEADA = None                   # constante de error pedida (Kp, Kv o Ka según el tipo): ajusta K sola. ej: 20
H = 1                                # sensor en la realimentación (1 = realimentación unitaria)
RETARDO = 0                          # retardo puro [s] (se aproxima con Padé de orden 8)

# Compensación (opcional) — elegí UNA de las dos formas:
Gc = None                            # a) ponerlo vos, ej:  Gc = (50*s + 1) / (4700*s + 1)
DISENAR = None                       # b) que lo calcule solo:  "adelanto"  o  "atraso"
MF_DESEADO = 50                      #    margen de fase pedido [°]  (solo si DISENAR)
MG_DESEADO = None                    #    margen de ganancia pedido [dB] (opcional, ej: 10).  None = no se exige

CARPETA = "graficos"                 # acá se guardan las figuras (también se muestran en pantalla)
# ═════════════════════════════════════════════════════════════════════════════


# ───────────────────────── funciones auxiliares (no hace falta tocarlas) ─────────────────────────
def fase_grados(Lw, tipo):
    """Fase desenrollada en grados; arranca en −90°·(tipo del sistema)."""
    f = np.degrees(np.unwrap(np.angle(Lw)))
    return f - 360 * np.round((f[0] + 90 * tipo) / 360)


def poli(c):
    """Coeficientes -> texto, ej: [1, 10, 5, 0] -> 's^3 + 10 s^2 + 5 s'."""
    c = np.trim_zeros(np.round(c, 6), "f")
    n, trozos = len(c) - 1, []
    for i, a in enumerate(c):
        p = n - i
        if a != 0:
            coef = "" if (a == 1 and p > 0) else f"{a:g} "
            trozos.append(f"{a:g}" if p == 0 else f"{coef}s" if p == 1 else f"{coef}s^{p}")
    return " + ".join(trozos).replace("+ -", "- ") or "0"


def mostrar(L):
    n, d = poli(L.num[0][0]), poli(L.den[0][0])
    ancho = max(len(n), len(d)) + 2
    print(f"  {n:^{ancho}}\n  {'─' * ancho}\n  {d:^{ancho}}")


def texto_margenes(gm, pm, w180, wc):
    mf = f"MF = {pm:.2f}°  en ωc = {wc:.4g} rad/s" if np.isfinite(wc) else "MF: |L| nunca llega a 0 dB (no hay cruce de ganancia)"
    mg = (f"MG = {gm:.4g} veces = {20 * np.log10(gm):.2f} dB  en ω180 = {w180:.4g} rad/s"
          if np.isfinite(w180) and np.isfinite(gm) else "MG = ∞ (la fase nunca llega a −180°)")
    return f"  Margen de fase:     {mf}\n  Margen de ganancia: {mg}"


def margenes(L):
    gm, pm, _, w180, wc, _ = ct.stability_margins(L)
    return gm, pm, w180, wc


def cumple(Lc):
    """¿El lazo compensado Lc cumple MF_DESEADO (y MG_DESEADO si se pidió)?"""
    gm, pm, _, _ = margenes(Lc)
    return pm >= MF_DESEADO and (MG_DESEADO is None or 20 * np.log10(gm) >= MG_DESEADO)


def disenar_adelanto(L, w, MF_req):
    """Adelanto Gc = (T·s+1)/(α·T·s+1): agrega fase donde |L| = 10·log10(α)."""
    mag_dB = 20 * np.log10(np.abs(L(1j * w)))
    MF0 = margenes(L)[1]
    for delta in range(2, 60):                          # grados extra de "seguridad"
        phi = np.radians(MF_req - MF0 + delta)
        if not 0 < phi < np.radians(70):
            raise ValueError("Hace falta más de ~70° de adelanto: probá con dos etapas o con atraso.")
        alfa = (1 - np.sin(phi)) / (1 + np.sin(phi))
        wm = w[np.argmin(np.abs(mag_dB - 10 * np.log10(alfa)))]
        T = 1 / (wm * np.sqrt(alfa))
        Gc = (T * s + 1) / (alfa * T * s + 1)
        if cumple(Gc * L):
            break
    else:
        print("  ATENCIÓN: no logré cumplir todo lo pedido con una sola etapa de adelanto.")
    print(f"  adelanto: φ_extra = {delta}°, α = {alfa:.4f}, ωm = {wm:.3f} rad/s, T = {T:.4f}")
    return Gc


def disenar_atraso(L, w, MF_req):
    """Atraso Gc = (T·s+1)/(β·T·s+1): baja la ganancia hasta que el cruce caiga donde la fase da el MF."""
    Lw = L(1j * w)
    fase = fase_grados(Lw, tipo)
    for extra in range(5, 60):                          # grados de margen por el atraso que agrega Gc
        idx = np.where(fase <= -180 + MF_req + extra)[0]
        if len(idx) == 0 or idx[0] == 0:
            raise ValueError("La fase de L nunca baja a ese valor: el atraso no sirve para este sistema.")
        wc_nuevo, beta = w[idx[0]], np.abs(Lw[idx[0]])
        if beta <= 1:
            raise ValueError("Ya cumple el margen de fase: no hace falta compensar.")
        T = 10 / wc_nuevo                               # cero una década por debajo del nuevo cruce
        Gc = (T * s + 1) / (beta * T * s + 1)
        if cumple(Gc * L):
            break
    else:
        print("  ATENCIÓN: no logré cumplir todo lo pedido con un atraso.")
    print(f"  atraso: ωc nuevo = {wc_nuevo:.4f} rad/s, β = {beta:.2f}, T = {T:.3f}")
    return Gc


# ═════════════════════════ PASO 1: EL SISTEMA ═════════════════════════
print("═" * 70, "\nPASO 1 — EL SISTEMA\n" + "═" * 70)
H = ct.tf([float(H)], [1]) if np.isscalar(H) else H
if RETARDO:
    num_p, den_p = ct.pade(RETARDO, 8)
    G = G * ct.tf(num_p, den_p)

L0 = G * H                                              # lazo abierto sin compensar
polos, ceros = ct.poles(L0), ct.zeros(L0)
print("G(s)·H(s) =")
mostrar(L0)
print("Polos:", np.round(polos, 4))
print("Ceros:", np.round(ceros, 4) if len(ceros) else "(ninguno)")

# tipo del sistema = cantidad de polos en el origen; constante de error = lím s^tipo · L(s)
num, den = np.trim_zeros(L0.num[0][0], "f"), np.trim_zeros(L0.den[0][0], "f")
tipo = 0
while abs(den[-1]) < 1e-12 and len(den) > 1:
    den, tipo = den[:-1], tipo + 1
cte = np.polyval(num, 0) / np.polyval(den, 0)
nombre_cte = ["Kp", "Kv", "Ka"][tipo] if tipo <= 2 else "K"
print(f"Tipo {tipo}  →  {nombre_cte} = {cte:.4g}")
if CTE_DESEADA:
    factor = CTE_DESEADA / cte
    G, L0, K, cte = G * factor, L0 * factor, K * factor, CTE_DESEADA
    print(f"Ajusto la ganancia ×{factor:.4g} para tener {nombre_cte} = {cte:g}  →  K = {K:.4g}")
if tipo == 0:
    print(f"Error al escalón = 1/(1+Kp) = {1 / (1 + cte):.4g}")
elif tipo == 1:
    print(f"Error al escalón = 0,  a la rampa = 1/Kv = {1 / cte:.4g}")
elif tipo == 2:
    print(f"Error al escalón = 0,  a la rampa = 0,  a la parábola = 1/Ka = {1 / cte:.4g}")

# frecuencias a analizar (automáticas, según polos y ceros)
rr = np.abs(np.concatenate([polos, ceros]))
rr = rr[rr > 1e-9]
lo, hi = (np.log10(rr.min()) - 2, np.log10(rr.max()) + 2) if len(rr) else (-2, 2)
w = np.logspace(lo, hi, 4000)

# ═════════════════ PASO 2: COMPENSADOR (si lo pediste) ═════════════════
if DISENAR:
    print("═" * 70, "\nPASO 2 — DISEÑO DEL COMPENSADOR\n" + "═" * 70)
    try:
        Gc = {"adelanto": disenar_adelanto, "atraso": disenar_atraso}[DISENAR](L0, w, MF_DESEADO)
    except ValueError as error:
        raise SystemExit(f"\n✗ No se pudo diseñar el compensador: {error}")
if Gc is not None:
    print("Gc(s) =")
    mostrar(Gc)

sistemas = {"Sin compensar": G}
if Gc is not None:
    sistemas["Compensado"] = Gc * G
colores = {"Sin compensar": "tab:blue", "Compensado": "tab:red"}
BLANCO = dict(fc="white", alpha=0.7, ec="none")

# ═════════════════ PASO 3: MÁRGENES Y ESTABILIDAD (Nyquist) ═════════════════
print("═" * 70, "\nPASO 3 — MÁRGENES Y ESTABILIDAD\n" + "═" * 70)
for nombre, Gd in sistemas.items():
    L = Gd * H
    gm, pm, w180, wc = margenes(L)
    P = int(np.sum(ct.poles(L).real > 1e-9))
    N = ct.nyquist_response(L).count                    # rodeos horarios al punto −1
    Z = int(np.sum(ct.poles(ct.feedback(Gd, H)).real > 1e-9))
    print(f"[{nombre}]")
    print(texto_margenes(gm, pm, w180, wc))
    print(f"  Nyquist: P = {P}, N = {N}  →  Z = N + P = {N + P}   (raíces: {Z} polos inestables)  "
          f"→ lazo cerrado {'ESTABLE' if Z == 0 else 'INESTABLE'}")

# rango de ganancia estable: se multiplica L por κ y se miran las raíces de 1 + κ·L
print("\nRango de K estable (sobre el sistema sin compensar):")
num, den = sistemas["Sin compensar"].num[0][0] * 1.0, sistemas["Sin compensar"].den[0][0]
nL, dL = np.polymul(num, H.num[0][0]), np.polymul(den, H.den[0][0])
es_estable = lambda k: bool(np.all(np.roots(np.polyadd(dL, k * nL)).real < 0))
kappas = np.logspace(-4, 4, 4000)
estable = np.array([es_estable(k) for k in kappas])


def borde(a, b):
    """Ganancia exacta donde cambia la estabilidad (bisección entre a y b)."""
    for _ in range(50):
        m = np.sqrt(a * b)
        a, b = (m, b) if es_estable(m) == es_estable(a) else (a, m)
    return a


if estable.all():
    print("  estable para todo K > 0")
elif not estable.any():
    print("  inestable para todo K > 0")
else:
    tramos, ini = [], (0.0 if estable[0] else None)
    for i in np.flatnonzero(np.diff(estable.astype(int))):
        if estable[i + 1]:
            ini = borde(kappas[i], kappas[i + 1])
        else:
            tramos.append((ini, borde(kappas[i], kappas[i + 1])))
            ini = None
    if ini is not None:
        tramos.append((ini, np.inf))
    for a, b in tramos:
        print(f"  estable para {K * a:.4g} < K < {K * b:.4g}    (K actual = {K})")

# ═════════════════════ PASO 4: LAZO CERRADO ═════════════════════
print("═" * 70, "\nPASO 4 — LAZO CERRADO\n" + "═" * 70)
resultados = {}
for nombre, Gd in sistemas.items():
    T = ct.feedback(Gd, H)
    pc = ct.poles(T)
    Tw = np.abs(T(1j * w))
    T0 = np.abs(T(0))
    Mr = max(Tw.max() / T0, 1.0)
    bw = w[np.argmax(Tw < T0 / np.sqrt(2))] if np.any(Tw < T0 / np.sqrt(2)) else None
    print(f"[{nombre}]  polos de lazo cerrado: {np.round(pc, 4)}")
    print(f"  Mr = {20 * np.log10(Mr):.2f} dB   ancho de banda = {'—' if bw is None else f'{bw:.4g} rad/s'}")
    resultados[nombre] = T
    if np.all(pc.real < 0):
        info = ct.step_info(T)
        print(f"  Escalón: Mp = {info['Overshoot']:.2f} %,  tp = {info['PeakTime']:.3g} s,  "
              f"tr = {info['RiseTime']:.3g} s,  ts(2 %) = {info['SettlingTime']:.3g} s")

# ═════════════════════ PASO 5: GRÁFICOS ═════════════════════
CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), CARPETA)   # junto a este archivo
os.makedirs(CARPETA, exist_ok=True)

# Bode con márgenes
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 7))
for nombre, Gd in sistemas.items():
    L = Gd * H
    Lw = L(1j * w)
    gm, pm, w180, wc = margenes(L)
    c = colores[nombre]
    ax1.semilogx(w, 20 * np.log10(np.abs(Lw)), c, label=nombre)
    ax2.semilogx(w, fase_grados(Lw, tipo), c, label=nombre)
    if np.isfinite(wc):
        ax1.axvline(wc, color=c, ls=":")
        ax2.axvline(wc, color=c, ls=":")
        ax2.annotate(f"MF = {pm:.1f}°", (wc, pm - 180), color=c, xytext=(6, 8), textcoords="offset points", bbox=BLANCO)
    if np.isfinite(w180) and np.isfinite(gm):
        ax1.axvline(w180, color=c, ls="-.")
        ax1.annotate(f"MG = {20 * np.log10(gm):.1f} dB", (w180, -20 * np.log10(gm)), color=c,
                     xytext=(6, 8), textcoords="offset points", bbox=BLANCO)
ax1.axhline(0, color="k", lw=0.8)
ax2.axhline(-180, color="k", lw=0.8)
ax1.set_ylabel("Magnitud [dB]")
ax2.set_ylabel("Fase [°]")
ax2.set_xlabel("ω [rad/s]")
ax1.set_title("Diagrama de Bode")
for a in (ax1, ax2):
    a.grid(True, which="both", alpha=0.3)
    a.legend()
fig.tight_layout()
fig.savefig(f"{CARPETA}/1_bode.png", dpi=140)

# Nyquist
fig = plt.figure(figsize=(7, 7))
for nombre, Gd in sistemas.items():
    ct.nyquist_plot(Gd * H, color=colores[nombre], label=nombre, arrows=1, max_curve_magnitude=6,
                    title="")
plt.plot(-1, 0, "kx", ms=10, mew=2)
plt.xlim(-3, 1)
plt.ylim(-2, 2)
plt.title("Diagrama de Nyquist (zoom alrededor de −1)")
plt.xlabel("Re L(jω)")
plt.ylabel("Im L(jω)")
plt.grid(True, alpha=0.3)
plt.legend()
fig.savefig(f"{CARPETA}/2_nyquist.png", dpi=140)

# Nichols
fig = plt.figure(figsize=(8, 7))
for nombre, Gd in sistemas.items():
    Lw = (Gd * H)(1j * w)
    plt.plot(fase_grados(Lw, tipo), 20 * np.log10(np.abs(Lw)), colores[nombre], label=nombre)
plt.plot(-180, 0, "kx", ms=10, mew=2)
ct.nichols_grid()
plt.ylim(-40, 40)
plt.title("Carta de Nichols (curvas de M constante del lazo cerrado)")
plt.xlabel("Fase [°]")
plt.ylabel("Magnitud [dB]")
plt.legend()
fig.savefig(f"{CARPETA}/3_nichols.png", dpi=140)

# Respuesta al escalón
fig = plt.figure(figsize=(8, 5))
for nombre, T in resultados.items():
    t, y = ct.step_response(T)
    plt.plot(t, np.clip(y, -4, 4), colores[nombre], label=nombre)
plt.axhline(1, color="k", lw=0.8, ls="--")
plt.title("Respuesta al escalón en lazo cerrado")
plt.xlabel("t [s]")
plt.ylabel("y(t)")
plt.grid(True, alpha=0.3)
plt.legend()
fig.savefig(f"{CARPETA}/4_escalon.png", dpi=140)

print("═" * 70, f"\nListo. Figuras guardadas en: {CARPETA}")
plt.show()
