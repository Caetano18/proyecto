"""Genera las tablas de datos (datos/*.dat) que usan las figuras de apunte.tex.

Requiere: numpy, scipy, matplotlib, control  (pip install numpy scipy matplotlib control)
Uso:      python3 generar_datos.py
"""
import os
import numpy as np
import control as ct
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
os.makedirs(DATOS, exist_ok=True)
s = ct.tf("s")


def guardar(nombre, columnas):
    """columnas: dict nombre -> array (todas del mismo largo)."""
    claves = list(columnas)
    M = np.column_stack([np.asarray(columnas[k], dtype=float) for k in claves])
    with open(os.path.join(DATOS, nombre), "w") as f:
        f.write(" ".join(claves) + "\n")
        for fila in M:
            f.write(" ".join(f"{v:.6g}" for v in fila) + "\n")


def mag_db(G, w):
    return 20 * np.log10(np.abs(G(1j * w)))


def fase(G, w):
    """Fase continua en grados (desenrollada desde baja frecuencia)."""
    return np.degrees(np.unwrap(np.angle(G(1j * w))))


def escalon(G, tf, n=400):
    t = np.linspace(0, tf, n)
    _, y = ct.step_response(G, t)
    return t, y


def asint(w, k_bode, n_int, ceros=(), polos=(), pares=()):
    """Magnitud asintotica en dB."""
    m = 20 * np.log10(k_bode) - 20 * n_int * np.log10(w)
    for z in ceros:
        m += 20 * np.log10(np.maximum(w / z, 1))
    for p in polos:
        m -= 20 * np.log10(np.maximum(w / p, 1))
    for wn in pares:
        m -= 40 * np.log10(np.maximum(w / wn, 1))
    return m


# ---------------------------------------------------------------- Parte I
# 1. Primer orden normalizado 1/(1+ju)
u = np.logspace(-2, 2, 300)
G1 = 1 / (s + 1)
fa = np.where(u < 0.1, 0, np.where(u > 10, -90, -45 * (np.log10(u) + 1)))
guardar("primer_orden.dat", {"u": u, "mag": mag_db(G1, u), "asin": asint(u, 1, 0, polos=[1]),
                             "fase": fase(G1, u), "fasin": fa})

# 2. Segundo orden normalizado 1/(1 - u^2 + j 2 zeta u)
u = np.logspace(-1, 1, 801)
cols = {"u": u, "asin": asint(u, 1, 0, pares=[1])}
for z in [0.05, 0.1, 0.2, 0.3, 0.5, 0.707, 1.0]:
    G2 = 1 / (s**2 + 2 * z * s + 1)
    tag = f"{z:g}".replace(".", "")
    cols["m" + tag] = mag_db(G2, u)
    cols["f" + tag] = fase(G2, u)
guardar("segundo_orden.dat", cols)

# 3. Ejemplo de trazado: G = 16000 (s+1) / (s (s+5) (s^2+16 s+1600))
Gej = 16000 * (s + 1) / (s * (s + 5) * (s**2 + 16 * s + 1600))
w = np.logspace(-2, 3, 600)
guardar("bode_ejemplo.dat", {"w": w, "mag": mag_db(Gej, w),
                             "asin": asint(w, 2, 1, ceros=[1], polos=[5], pares=[40]),
                             "fase": fase(Gej, w)})

# 4. Formas polares tipicas (tipo 0, 1 y 2)
w = np.logspace(-2.5, 2, 800)
for nombre, G in [("polar_t0.dat", 1 / ((s + 1) * (0.5 * s + 1) * (0.2 * s + 1))),
                  ("polar_t1.dat", 1 / (s * (s + 1) * (0.5 * s + 1))),
                  ("polar_t2.dat", 1 / (s**2 * (s + 1)))]:
    z = G(1j * w)
    ok = (np.abs(z.imag) < 4) & (np.abs(z.real) < 4)
    guardar(nombre, {"re": z.real[ok], "im": z.imag[ok]})

# 5. Nyquist de K/(s(s+1)(s+2)) para K = 2 y K = 8
w = np.logspace(-1.5, 2, 1500)
for K in [2, 8]:
    z = K / ((1j * w) * (1j * w + 1) * (1j * w + 2))
    ok = (np.abs(z.imag) < 3.2) & (z.real > -3.2)
    guardar(f"nyquist_k{K}.dat", {"re": z.real[ok], "im": z.imag[ok], "imneg": -z.imag[ok]})

# 6. Margenes sobre Bode: L = 2/(s(s+1)(s+2))
Lm = 2 / (s * (s + 1) * (s + 2))
w = np.logspace(-1, 1.5, 400)
guardar("margenes.dat", {"w": w, "mag": mag_db(Lm, w), "fase": fase(Lm, w)})
guardar("circulo.dat", {"x": np.cos(np.linspace(0, 2 * np.pi, 200)),
                        "y": np.sin(np.linspace(0, 2 * np.pi, 200))})

# 7. Nichols de L = 2/(s(s+1)(s+2)) con contornos M
w = np.logspace(-1, 1.3, 400)
guardar("nichols_L.dat", {"fase": fase(Lm, w), "mag": mag_db(Lm, w)})
ph = np.linspace(-359.5, -0.5, 700)
db = np.linspace(-40, 40, 700)
PH, DB = np.meshgrid(ph, db)
Lg = 10 ** (DB / 20) * np.exp(1j * np.radians(PH))
Tdb = 20 * np.log10(np.abs(Lg / (1 + Lg)))
niveles = [-12, -6, -3, -1, 0, 1, 3, 6, 12]
cs = plt.contour(PH, DB, Tdb, levels=niveles)
with open(os.path.join(DATOS, "nichols_M.dat"), "w") as f:
    f.write("fase mag\n")
    for nivel, segs in zip(cs.levels, cs.allsegs):
        for seg in segs:
            for x, y in seg:
                f.write(f"{x:.3f} {y:.3f}\n")
            f.write("\n")
plt.close("all")
# etiquetas de los contornos M dentro de la ventana que se grafica
with open(os.path.join(DATOS, "nichols_lab.dat"), "w") as f:
    f.write("fase mag lab\n")
    for nivel, segs in zip(cs.levels, cs.allsegs):
        pts = np.vstack(segs)
        ok = (pts[:, 0] > -262) & (pts[:, 0] < -98) & (pts[:, 1] > -28) & (pts[:, 1] < 22)
        pts = pts[ok]
        if len(pts) == 0:
            continue
        if nivel > 0:
            x, y = pts[np.argmax(pts[:, 1])]
        else:
            x, y = pts[np.argmin(np.abs(pts[:, 0] + 105))]
        f.write(f"{x:.2f} {y:.2f} {nivel:g}\n")

# 8. Correlacion MF - zeta, Mp - zeta, Mr - zeta
z = np.linspace(0.02, 1.0, 200)
mf = np.degrees(np.arctan(2 * z / np.sqrt(np.sqrt(1 + 4 * z**4) - 2 * z**2)))
mp = 100 * np.exp(-np.pi * z / np.sqrt(1 - np.minimum(z, 0.9999)**2))
guardar("correlacion.dat", {"z": z, "mf": mf, "aprox": 100 * z, "mp": mp})

# ---------------------------------------------------------------- Parte II
# 9. Adelanto normalizado (jwT+1)/(jw alfa T+1)
x = np.logspace(-2, 3, 500)
cols = {"x": x}
for a in [0.5, 0.25, 0.1]:
    Gc = (s + 1) / (a * s + 1)
    tag = f"{a:g}".replace(".", "")
    cols["m" + tag] = mag_db(Gc, x)
    cols["f" + tag] = fase(Gc, x)
guardar("adelanto_norm.dat", cols)
a = np.linspace(0.02, 1, 200)
guardar("phim_alfa.dat", {"a": a, "phim": np.degrees(np.arcsin((1 - a) / (1 + a)))})

# 10. Atraso normalizado (jwT+1)/(jw beta T+1), beta = 10
x = np.logspace(-3, 2, 500)
Gc = (s + 1) / (10 * s + 1)
guardar("atraso_norm.dat", {"x": x, "mag": mag_db(Gc, x), "fase": fase(Gc, x)})

# 11. Ejemplo adelanto: G = 1/(s(s+1)(0.05 s+1)), Kv = 10, MF >= 45
G = 1 / (s * (s + 1) * (0.05 * s + 1))
L0 = 10 * G
alfa, wm = 0.15, 4.96
T = 1 / (wm * np.sqrt(alfa))
Gc = 10 * (T * s + 1) / (alfa * T * s + 1)
L1 = Gc * G
w = np.logspace(-1, 2.5, 500)
guardar("adelanto_ej.dat", {"w": w, "m0": mag_db(L0, w), "f0": fase(L0, w), "m1": mag_db(L1, w),
                            "f1": fase(L1, w), "mc": mag_db(Gc / 10, w), "fc": fase(Gc, w)})
t, y0 = escalon(ct.feedback(L0, 1), 8)
_, y1 = escalon(ct.feedback(L1, 1), 8)
guardar("adelanto_ej_step.dat", {"t": t, "y0": y0, "y1": y1})

# 12. Ejemplo atraso: G = 1/(s(s+2)(s+5)), Kv = 10, MF >= 45
G = 1 / (s * (s + 2) * (s + 5))
L0 = 100 * G
beta = 9.0
Gc = 100 * (10 * s + 1) / (beta * 10 * s + 1)
L1 = Gc * G
Kg = 14.66                      # solo ganancia, MF = 45
w = np.logspace(-3, 2, 500)
guardar("atraso_ej.dat", {"w": w, "m0": mag_db(L0, w), "f0": fase(L0, w), "m1": mag_db(L1, w),
                          "f1": fase(L1, w), "mc": mag_db(Gc / 100, w), "fc": fase(Gc, w)})
t, y1 = escalon(ct.feedback(L1, 1), 25)
_, yg = escalon(ct.feedback(Kg * G, 1), 25)
guardar("atraso_ej_step.dat", {"t": t, "y1": y1, "yg": yg})
tr = np.linspace(0, 25, 400)
_, r1 = ct.forced_response(ct.feedback(L1, 1), tr, tr)
_, rg = ct.forced_response(ct.feedback(Kg * G, 1), tr, tr)
guardar("atraso_ej_rampa.dat", {"t": tr, "e1": tr - r1, "eg": tr - rg})

# 13. Ejemplo atraso-adelanto: G = 1/(s(s+1)(s+4)), Kv = 10, MF >= 50
G = 1 / (s * (s + 1) * (s + 4))
L0 = 40 * G
Glead = (s / 0.611 + 1) / (s / 6.54 + 1)
Glag = (s / 0.2 + 1) / (s / 0.0306 + 1)
L1 = L0 * Glead * Glag
w = np.logspace(-3, 2, 500)
guardar("ad_at_ej.dat", {"w": w, "m0": mag_db(L0, w), "f0": fase(L0, w), "m1": mag_db(L1, w),
                         "f1": fase(L1, w), "mc": mag_db(Glead * Glag, w),
                         "fc": fase(Glead * Glag, w)})
t, y1 = escalon(ct.feedback(L1, 1), 20)
guardar("ad_at_ej_step.dat", {"t": t, "y1": y1})

# 14. Comparacion adelanto vs atraso sobre G = 1/(s(s+1)), Kv = 10, MF >= 45
G = 1 / (s * (s + 1))
L0 = 10 * G
Tl = 1 / 2.321
Lad = 10 * (Tl * s + 1) / (0.3068 * Tl * s + 1) * G
Tg = 1 / 0.081
Lat = 10 * (Tg * s + 1) / (9.6 * Tg * s + 1) * G
w = np.logspace(-3, 2, 500)
guardar("comparacion.dat", {"w": w, "m0": mag_db(L0, w), "mad": mag_db(Lad, w),
                            "mat": mag_db(Lat, w)})
t, y0 = escalon(ct.feedback(L0, 1), 15, 600)
_, yad = escalon(ct.feedback(Lad, 1), 15, 600)
_, yat = escalon(ct.feedback(Lat, 1), 15, 600)
guardar("comparacion_step.dat", {"t": t, "y0": y0, "yad": yad, "yat": yat})


# 15. Nyquist de L = 2(s+3)/(s(s-1)) (lazo abierto inestable, ejercicio 6)
w = np.logspace(-1.2, 2.5, 1500)
z = 2 * (1j * w + 3) / ((1j * w) * (1j * w - 1))
ok = (np.abs(z.imag) < 4.2) & (z.real > -9)
guardar("nyquist_inest.dat", {"re": z.real[ok], "im": z.imag[ok], "imneg": -z.imag[ok]})

# 16. Problema integrador: aeronave de la UT05 con K = 2
Ga = 50 / (s + 50)
Gt = 18 * (s + 1) / (s * (s**2 + 4.2 * s + 9))
Gf = 400 / (s**2 + s + 400)
Gav = Ga * Gt * Gf
L0 = 2 * Gav
Llead = L0 * (s / 4.99 + 1) / (s / 15.7 + 1)
Llag = L0 * (4 * s + 1) / (14.48 * s + 1)
w = np.logspace(-1, 2, 1500)
guardar("avion.dat", {"w": w, "m1": mag_db(Gav, w), "m0": mag_db(L0, w), "mlead": mag_db(Llead, w),
                      "mlag": mag_db(Llag, w)})

# 17. Estabilidad condicional: L = 200 (1+s)^2 / (s (1+10s)^2 (1+0.1s)^2)
Lcond = 200 * (1 + s)**2 / (s * (1 + 10 * s)**2 * (1 + 0.1 * s)**2)
w = np.logspace(-2, 2, 800)
guardar("condicional.dat", {"w": w, "mag": mag_db(Lcond, w), "fase": fase(Lcond, w)})

# 18. Bode "impreso" para el ejercicio de lectura: G = 5/(s(1+s/2)(1+s/20))
Gimp = 5 / (s * (1 + s / 2) * (1 + s / 20))
w = np.logspace(-1, 2, 600)
guardar("bode_impreso.dat", {"w": w, "mag": mag_db(Gimp, w), "fase": fase(Gimp, w)})

# ---------------------------------------------------------------- resumen
def resumen(nombre, L):
    gm, pm, wpc, wgc = ct.margin(L)
    cl = ct.feedback(L, 1)
    est = np.all(ct.poles(cl).real < 0)
    txt = f"{nombre:28s} MF={pm:7.2f}  wc={wgc:7.3f}  MG={20*np.log10(gm):7.2f} dB  w180={wpc:7.3f}"
    if est:
        i = ct.step_info(cl)
        txt += f"  Mp={i['Overshoot']:5.1f}%  ts={i['SettlingTime']:6.2f}  BW={ct.bandwidth(cl):6.2f}"
    else:
        txt += "  INESTABLE"
    print(txt)


if __name__ == "__main__":
    resumen("ejemplo Bode", Gej)
    resumen("margenes K=2", Lm)
    resumen("adelanto sin comp", 10 / (s * (s + 1) * (0.05 * s + 1)))
    T = 1 / (4.96 * np.sqrt(0.15))
    resumen("adelanto con comp", 10 * (T * s + 1) / (0.15 * T * s + 1) / (s * (s + 1) * (0.05 * s + 1)))
    resumen("atraso sin comp", 100 / (s * (s + 2) * (s + 5)))
    resumen("atraso con comp", 100 * (10 * s + 1) / (90 * s + 1) / (s * (s + 2) * (s + 5)))
    resumen("atraso-adelanto sin comp", 40 / (s * (s + 1) * (s + 4)))
    resumen("atraso-adelanto con comp", L1)
    resumen("comparacion adelanto", Lad)
    resumen("comparacion atraso", Lat)
    resumen("avion K=1", Gav)
    resumen("avion K=2", L0)
    resumen("avion adelanto", Llead)
    resumen("avion atraso", Llag)
    resumen("condicional K=200", Lcond)
    resumen("Bode impreso", Gimp)
