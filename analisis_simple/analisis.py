# Analisis en frecuencia: Bode, Nyquist, Nichols, margenes, lazo cerrado y compensacion.
# Se cambian los datos de abajo y se ejecuta.   Instalar:  pip install control numpy matplotlib

import os
import numpy as np
import matplotlib.pyplot as plt
import control as ct

s = ct.tf("s")

# ------------------------------------------------------------------ datos
K = 100
G = K / (s**3 + 10*s**2 + 5*s)      # funcion de transferencia de lazo abierto
# otras formas:  G = 50/(s*(s+1.3)*(s+100))     G = ct.tf([5], [1, 3, 2])

H = 1                               # sensor (1 = realimentacion unitaria)
retardo = 0                         # retardo puro en segundos (se aproxima con Pade)
cte_pedida = None                   # Kp, Kv o Ka pedido (segun el tipo); ajusta K. Ej: 20

# compensacion
diseno = None                       # "adelanto", "atraso" o "atraso_adelanto" (None = sin compensar)
mf_pedido = 50                      # margen de fase pedido, en grados
mg_pedido = None                    # margen de ganancia pedido, en dB (opcional)
wc_nueva = None                     # frecuencia de cruce que se quiere, en rad/s (opcional)
Gc = None                           # o el compensador a mano. Ej: Gc = (50*s + 1)/(4700*s + 1)

carpeta = "graficos"                # donde se guardan las figuras
# ------------------------------------------------------------------


def fase(Lw, tipo):
    # fase en grados sin saltos, empezando en -90*tipo
    f = np.degrees(np.unwrap(np.angle(Lw)))
    return f - 360*np.round((f[0] + 90*tipo)/360)


def tipo_y_cte(L):
    # tipo = cantidad de integradores; cte = limite de s^tipo * L(s)
    num = np.trim_zeros(L.num[0][0], "f")
    den = np.trim_zeros(L.den[0][0], "f")
    tipo = 0
    while abs(den[-1]) < 1e-12 and len(den) > 1:
        den = den[:-1]
        tipo += 1
    return tipo, np.polyval(num, 0)/np.polyval(den, 0)


def margenes(L):
    gm, pm, _, w180, wc, _ = ct.stability_margins(L)
    return gm, pm, w180, wc


def cumple(L):
    gm, pm, _, _ = margenes(L)
    return pm >= mf_pedido and (mg_pedido is None or 20*np.log10(gm) >= mg_pedido)


def red(T, razon):
    # (T s + 1)/(razon T s + 1): razon < 1 adelanto, razon > 1 atraso
    return (T*s + 1)/(razon*T*s + 1)


def coef(c):
    return np.array2string(np.array(c), precision=5, suppress_small=True)


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, str):
        return v
    return "inf" if np.isinf(v) else f"{v:.4g}"


# ------------------------------------------------------------------ compensadores
def adelanto(L, w):
    mag = 20*np.log10(abs(L(1j*w)))
    mf0 = margenes(L)[1]
    if not np.isfinite(mf0):
        raise ValueError("L no cruza 0 dB, no hay margen de fase para corregir (revisar K)")
    print(f"MF sin compensar = {mf0:.2f} grados, falta {mf_pedido - mf0:.2f} para llegar a {mf_pedido}")
    for extra in range(2, 60):              # colchon, porque al subir wc la fase de L baja
        phi = np.radians(mf_pedido - mf0 + extra)
        if not 0 < phi < np.radians(70):
            raise ValueError("hace falta mas de 70 grados de adelanto, probar con atraso o atraso_adelanto")
        alfa = (1 - np.sin(phi))/(1 + np.sin(phi))
        wm = w[np.argmin(abs(mag - 10*np.log10(alfa)))]
        T = 1/(wm*np.sqrt(alfa))
        Gc = red(T, alfa)
        if cumple(Gc*L):
            break
    else:
        print("no se llego a cumplir lo pedido con una sola etapa")
    print(f"fase a agregar: phi_m = {mf_pedido} - ({mf0:.2f}) + {extra} (colchon) = {np.degrees(phi):.2f} grados")
    print(f"alfa = (1 - sen phi_m)/(1 + sen phi_m) = {alfa:.4f}")
    print(f"wm = {wm:.4g} rad/s (ahi |L| = {10*np.log10(alfa):.2f} dB, el adelanto sube {-10*np.log10(alfa):.2f} dB)")
    print(f"T = 1/(wm*raiz(alfa)) = {T:.4g}   cero en {1/T:.4g}, polo en {1/(alfa*T):.4g} rad/s")
    return Gc


def atraso(L, w):
    Lw = L(1j*w)
    f = fase(Lw, tipo_y_cte(L)[0])
    print(f"MF sin compensar = {margenes(L)[1]:.2f} grados (pedido {mf_pedido})")
    for extra in ([None] if wc_nueva else range(5, 60)):   # colchon por la fase que resta el atraso
        if extra is None:
            i = np.argmin(abs(w - wc_nueva))
        else:
            idx = np.where(f <= -180 + mf_pedido + extra)[0]
            if len(idx) == 0 or idx[0] == 0:
                raise ValueError("la fase de L nunca llega a ese valor, el atraso no sirve")
            i = idx[0]
        wn, beta = w[i], abs(Lw[i])
        if beta <= 1:
            raise ValueError("ya cumple el margen de fase, no hace falta compensar")
        T = 10/wn
        Gc = red(T, beta)
        if cumple(Gc*L):
            break
    else:
        print("no se llego a cumplir lo pedido con un atraso")
    print(f"nuevo cruce wc' = {wn:.4g} rad/s (ahi la fase de L es {f[i]:.1f} grados)")
    print(f"beta = |L(jwc')| = {beta:.3f} ({20*np.log10(beta):.1f} dB de atenuacion)")
    print(f"T = 10/wc' = {T:.4g}   cero en {1/T:.4g}, polo en {1/(beta*T):.4g} rad/s")
    return Gc


def atraso_adelanto(L, w):
    wn = wc_nueva or margenes(L)[2]         # por defecto, la frecuencia donde la fase vale -180
    if not np.isfinite(wn):
        raise ValueError("L no cruza -180 grados, indicar wc_nueva")
    A0 = abs(L(1j*wn))
    mf_disp = 180 + np.interp(wn, w, fase(L(1j*w), tipo_y_cte(L)[0]))
    print(f"wc' = {wn:.4g} rad/s, |L(jwc')| = {20*np.log10(A0):.2f} dB")
    print(f"margen de fase disponible en wc' = 180 + fase de L = {mf_disp:.2f} grados (pedido {mf_pedido})")
    for extra in range(2, 40):
        phi = max(mf_pedido - mf_disp + extra, 0)
        if phi >= 70:
            raise ValueError("hace falta mas de 70 grados de adelanto en esa frecuencia, probar otra wc_nueva")
        alfa = (1 - np.sin(np.radians(phi)))/(1 + np.sin(np.radians(phi)))
        T1 = 1/(wn*np.sqrt(alfa))
        A = A0/np.sqrt(alfa)                # |L| despues del adelanto, en wc'
        Gc = red(T1, alfa)
        beta = None
        if A > 1:                           # el atraso baja |L| a 0 dB justo en wc'
            T2 = 10/wn
            x = wn*T2
            beta = np.sqrt((1 + x**2)*A**2 - 1)/x
            Gc = Gc*red(T2, beta)
        if cumple(Gc*L):
            break
    else:
        print("no se llego a cumplir lo pedido (probar otra wc_nueva)")
    print(f"adelanto: phi_m = {mf_pedido} - {mf_disp:.2f} + {extra} = {phi:.2f} grados, alfa = {alfa:.4f}")
    print(f"          T1 = {T1:.4g}   cero en {1/T1:.4g}, polo en {1/(alfa*T1):.4g} rad/s")
    if beta:
        print(f"atraso:   sobran {20*np.log10(A):.2f} dB en wc', beta = {beta:.3f}, T2 = 10/wc' = {T2:.4g}")
        print(f"          cero en {1/T2:.4g}, polo en {1/(beta*T2):.4g} rad/s")
    else:
        print("con el adelanto alcanza, no hace falta el atraso")
    return Gc


disenos = {"adelanto": adelanto, "atraso": atraso, "atraso_adelanto": atraso_adelanto}

# ------------------------------------------------------------------ 1. sistema
print("\n--- 1. sistema ---")
if np.isscalar(H):
    H = ct.tf([float(H)], [1])
if retardo:
    n, d = ct.pade(retardo, 8)
    G = G*ct.tf(n, d)

L0 = G*H
polos, ceros = ct.poles(L0), ct.zeros(L0)
print("numerador:  ", coef(L0.num[0][0]))
print("denominador:", coef(L0.den[0][0]))
print("polos:", np.round(polos, 4))
print("ceros:", np.round(ceros, 4) if len(ceros) else "ninguno")

tipo, cte = tipo_y_cte(L0)
nombre_cte = ["Kp", "Kv", "Ka"][min(tipo, 2)]
print(f"tipo {tipo}, {nombre_cte} = {cte:.4g}")
if cte_pedida:
    factor = cte_pedida/cte
    G, L0, K, cte = G*factor, L0*factor, K*factor, cte_pedida
    print(f"se multiplica la ganancia por {factor:.4g} para tener {nombre_cte} = {cte:g}  (K = {K:.4g})")
if tipo == 0:
    print(f"error al escalon = 1/(1+Kp) = {1/(1 + cte):.4g}")
elif tipo == 1:
    print(f"error al escalon = 0, a la rampa = 1/Kv = {1/cte:.4g}")
elif tipo == 2:
    print(f"error al escalon y a la rampa = 0, a la parabola = 1/Ka = {1/cte:.4g}")

# frecuencias para los graficos y las cuentas, segun donde estan los polos y ceros
r = abs(np.concatenate([polos, ceros]))
r = r[r > 1e-9]
w = np.logspace(np.log10(r.min()) - 2, np.log10(r.max()) + 2, 4000) if len(r) else np.logspace(-2, 2, 4000)

# ------------------------------------------------------------------ 2. compensador
if diseno:
    if diseno not in disenos:
        raise SystemExit(f"diseno = {diseno!r} no existe, opciones: {', '.join(disenos)} (o None)")
    print(f"\n--- 2. compensador ({diseno}) ---")
    try:
        Gc = disenos[diseno](L0, w)
    except ValueError as e:
        raise SystemExit(f"\nno se pudo disenar el compensador: {e}")
if Gc is not None:
    print("Gc(s):  numerador", coef(Gc.num[0][0]), "  denominador", coef(Gc.den[0][0]))

sistemas = {"Sin compensar": G}
if Gc is not None:
    sistemas["Compensado"] = Gc*G
tipos = {n: tipo_y_cte(Gd*H)[0] for n, Gd in sistemas.items()}
colores = {"Sin compensar": "tab:blue", "Compensado": "tab:red"}
resumen = {}

# ------------------------------------------------------------------ 3. margenes y estabilidad
print("\n--- 3. margenes y estabilidad ---")
for nombre, Gd in sistemas.items():
    L = Gd*H
    gm, pm, w180, wc = margenes(L)
    P = int(np.sum(ct.poles(L).real > 1e-9))                 # polos de L en el semiplano derecho
    N = ct.nyquist_response(L).count                          # rodeos horarios a -1
    Z = int(np.sum(ct.poles(ct.feedback(Gd, H)).real > 1e-9))
    mg_db = 20*np.log10(gm) if np.isfinite(gm) else np.inf
    print(f"[{nombre}]")
    print(f"  MF = {pm:.2f} grados en wc = {wc:.4g} rad/s" if np.isfinite(wc) else "  MF: |L| nunca llega a 0 dB")
    print(f"  MG = {gm:.4g} ({mg_db:.2f} dB) en w180 = {w180:.4g} rad/s" if np.isfinite(w180) else "  MG: infinito (la fase nunca llega a -180)")
    print(f"  Nyquist: P = {P}, N = {N}, Z = N + P = {N + P}   (por raices: {Z})  ->  lazo cerrado {'estable' if Z == 0 else 'INESTABLE'}")
    tt, kk = tipo_y_cte(L)
    resumen[nombre] = {"cte. de error": f"{['Kp', 'Kv', 'Ka'][min(tt, 2)]} = {kk:.4g}", "MF [grados]": pm, "wc [rad/s]": wc, "MG [dB]": mg_db}

# rango de K: se multiplica L por k y se mira si 1 + k*L tiene raices en el semiplano derecho
print("\nrango de K estable (sin compensar):")
nL = np.polymul(G.num[0][0], H.num[0][0])
dL = np.polymul(G.den[0][0], H.den[0][0])


def estable(k):
    return bool(np.all(np.roots(np.polyadd(dL, k*nL)).real < 0))


def borde(a, b):
    # biseccion entre a y b, donde cambia la estabilidad
    for _ in range(50):
        m = np.sqrt(a*b)
        a, b = (m, b) if estable(m) == estable(a) else (a, m)
    return a


ks = np.logspace(-4, 4, 4000)
ok = np.array([estable(k) for k in ks])
if ok.all():
    print("  estable para todo K > 0")
elif not ok.any():
    print("  inestable para todo K > 0")
else:
    desde = 0.0 if ok[0] else None
    tramos = []
    for i in np.flatnonzero(np.diff(ok.astype(int))):
        if ok[i + 1]:
            desde = borde(ks[i], ks[i + 1])
        else:
            tramos.append((desde, borde(ks[i], ks[i + 1])))
            desde = None
    if desde is not None:
        tramos.append((desde, np.inf))
    for a, b in tramos:
        print(f"  estable para {K*a:.4g} < K < {K*b:.4g}   (K actual = {K:.4g})")

# ------------------------------------------------------------------ 4. lazo cerrado
print("\n--- 4. lazo cerrado ---")
cerrados = {}
for nombre, Gd in sistemas.items():
    T = ct.feedback(Gd, H)
    pc = ct.poles(T)
    Tw, T0 = abs(T(1j*w)), abs(T(0))
    Mr = max(Tw.max()/T0, 1)
    bajo = np.flatnonzero(Tw < T0/np.sqrt(2))
    bw = w[bajo[0]] if len(bajo) else None
    print(f"[{nombre}] polos: {np.round(pc, 4)}")
    print(f"  Mr = {20*np.log10(Mr):.2f} dB, ancho de banda = {'-' if bw is None else f'{bw:.4g} rad/s'}")
    cerrados[nombre] = T
    resumen[nombre].update({"Mr [dB]": 20*np.log10(Mr), "BW [rad/s]": bw})
    if np.all(pc.real < 0):
        info = ct.step_info(T)
        print(f"  escalon: Mp = {info['Overshoot']:.2f} %, tp = {info['PeakTime']:.3g} s, "
              f"tr = {info['RiseTime']:.3g} s, ts(2%) = {info['SettlingTime']:.3g} s")
        resumen[nombre].update({"Mp [%]": info["Overshoot"], "ts 2% [s]": info["SettlingTime"]})

print("\n--- resumen ---")
print(" "*14 + "".join(f"{n:>16s}" for n in resumen))
for k in {k: 0 for res in resumen.values() for k in res}:
    print(f"{k:14s}" + "".join(f"{fmt(res.get(k)):>16s}" for res in resumen.values()))

# ------------------------------------------------------------------ 5. graficos
carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), carpeta)
os.makedirs(carpeta, exist_ok=True)
caja = dict(fc="white", alpha=0.7, ec="none")

# Bode
fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(9, 7))
for nombre, Gd in sistemas.items():
    L = Gd*H
    Lw = L(1j*w)
    gm, pm, w180, wc = margenes(L)
    c = colores[nombre]
    a1.semilogx(w, 20*np.log10(abs(Lw)), c, label=nombre)
    a2.semilogx(w, fase(Lw, tipos[nombre]), c, label=nombre)
    if np.isfinite(wc):
        a1.axvline(wc, color=c, ls=":")
        a2.axvline(wc, color=c, ls=":")
        a2.annotate(f"MF = {pm:.1f}", (wc, pm - 180), color=c, xytext=(6, 8), textcoords="offset points", bbox=caja)
    if np.isfinite(w180) and np.isfinite(gm):
        a1.axvline(w180, color=c, ls="-.")
        a1.annotate(f"MG = {20*np.log10(gm):.1f} dB", (w180, -20*np.log10(gm)), color=c,
                    xytext=(6, 8), textcoords="offset points", bbox=caja)
a1.axhline(0, color="k", lw=0.8)
a2.axhline(-180, color="k", lw=0.8)
a1.set_ylabel("Magnitud [dB]")
a2.set_ylabel("Fase [grados]")
a2.set_xlabel("w [rad/s]")
a1.set_title("Bode")
for a in (a1, a2):
    a.grid(True, which="both", alpha=0.3)
    a.legend()
fig.tight_layout()
fig.savefig(f"{carpeta}/1_bode.png", dpi=140)

# Nyquist
fig = plt.figure(figsize=(7, 7))
for nombre, Gd in sistemas.items():
    ct.nyquist_plot(Gd*H, color=colores[nombre], label=nombre, arrows=1, max_curve_magnitude=6, title="")
plt.plot(-1, 0, "kx", ms=10, mew=2)
th = np.linspace(0, 2*np.pi, 300)
plt.plot(np.cos(th), np.sin(th), "k:", lw=0.8)      # circulo |L| = 1
plt.xlim(-3, 1)
plt.ylim(-2, 2)
plt.title("Nyquist (zoom alrededor de -1, el circulo es |L| = 1)")
plt.xlabel("Re L(jw)")
plt.ylabel("Im L(jw)")
plt.grid(True, alpha=0.3)
plt.legend()
fig.savefig(f"{carpeta}/2_nyquist.png", dpi=140)

# Nichols
fig = plt.figure(figsize=(8, 7))
for nombre, Gd in sistemas.items():
    Lw = (Gd*H)(1j*w)
    plt.plot(fase(Lw, tipos[nombre]), 20*np.log10(abs(Lw)), colores[nombre], label=nombre)
plt.plot(-180, 0, "kx", ms=10, mew=2)
ct.nichols_grid()
plt.ylim(-40, 40)
plt.title("Nichols")
plt.xlabel("Fase [grados]")
plt.ylabel("Magnitud [dB]")
plt.legend()
fig.savefig(f"{carpeta}/3_nichols.png", dpi=140)

# escalon
fig = plt.figure(figsize=(8, 5))
for nombre, T in cerrados.items():
    t, y = ct.step_response(T)
    plt.plot(t, np.clip(y, -4, 4), colores[nombre], label=nombre)
plt.axhline(1, color="k", lw=0.8, ls="--")
plt.title("Respuesta al escalon")
plt.xlabel("t [s]")
plt.ylabel("y(t)")
plt.grid(True, alpha=0.3)
plt.legend()
fig.savefig(f"{carpeta}/4_escalon.png", dpi=140)

# Bode del compensador
if Gc is not None:
    fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))
    Gw = Gc(1j*w)
    a1.semilogx(w, 20*np.log10(abs(Gw)), "tab:green")
    a2.semilogx(w, fase(Gw, tipo_y_cte(Gc)[0]), "tab:green")
    a1.set_ylabel("|Gc| [dB]")
    a2.set_ylabel("fase de Gc [grados]")
    a2.set_xlabel("w [rad/s]")
    a1.set_title("Bode del compensador")
    for a in (a1, a2):
        a.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{carpeta}/5_compensador.png", dpi=140)

print(f"\nfiguras guardadas en {carpeta}")
plt.show()
