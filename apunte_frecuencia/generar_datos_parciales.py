"""Genera los datos de las figuras de resolucion_parciales.tex (carpeta datos/).

Requiere: numpy, control  (pip install numpy control)
Uso:      python3 generar_datos_parciales.py
"""
import os
import numpy as np
import control as ct

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "datos")
os.makedirs(DATOS, exist_ok=True)
s = ct.tf("s")


def guardar(nombre, columnas):
    claves = list(columnas)
    M = np.column_stack([np.asarray(columnas[k], dtype=float) for k in claves])
    with open(os.path.join(DATOS, nombre), "w") as f:
        f.write(" ".join(claves) + "\n")
        for fila in M:
            f.write(" ".join(f"{v:.6g}" for v in fila) + "\n")


def mag_db(G, w):
    return 20 * np.log10(np.abs(G(1j * w)))


def fase(G, w):
    return np.degrees(np.unwrap(np.angle(G(1j * w))))


def escalon(G, tf, n=1500):
    t = np.linspace(0, tf, n)
    _, y = ct.step_response(G, t)
    return t, y


# ------------------------------------------------------------ Ejercicio 1
# G = K / (s^3 + 10 s^2 + 5 s). Kv = K/5 -> K = 100 para Kv = 20.
G1_sin = 100 / (s**3 + 10 * s**2 + 5 * s)
Gc1 = (50 * s + 1) / (4700 * s + 1)
L1 = G1_sin * Gc1

# Nyquist: K = 10 (estable) y K = 100 (inestable), omega > 0 y espejo
w = np.logspace(-1.5, 2, 3000)
for K in [10, 100]:
    z = K / ((1j * w) * ((1j * w) ** 2 + 10 * (1j * w) + 5))
    ok = (np.abs(z.imag) < 6) & (np.abs(z.real) < 6)
    guardar(f"parc1_nyq_k{K}.dat", {"re": z.real[ok], "im": z.imag[ok], "imn": -z.imag[ok]})

# Escalones para K = 10, 30 y 50 (sostenida)
for K in [10, 30, 50]:
    t, y = escalon(ct.feedback(K * G1_sin / 100, 1), 40)
    guardar(f"parc1_step_k{K}.dat", {"t": t, "y": y})

# Bode: sin compensar (K=100) y compensada
w = np.logspace(-2, 2, 800)
guardar("parc1_bode.dat", {
    "w": w,
    "ms": mag_db(G1_sin, w), "fs": fase(G1_sin, w),
    "mc": mag_db(L1, w), "fc": fase(L1, w),
    "mg": mag_db(Gc1, w), "fg": fase(Gc1, w),
})

# Nichols (datos de L): sin compensar y compensada
w = np.logspace(-2, 1.6, 2500)
guardar("parc1_nichols_sin.dat", {"fase": fase(G1_sin, w), "mag": mag_db(G1_sin, w)})
guardar("parc1_nichols_comp.dat", {"fase": fase(L1, w), "mag": mag_db(L1, w)})

# Escalones de lazo cerrado: compensada vs K = 20 (referencia estable sin compensar)
t, y1 = escalon(ct.feedback(L1, 1), 60)
G1_k20 = 20 / (s**3 + 10 * s**2 + 5 * s)
_, y20 = escalon(ct.feedback(G1_k20, 1), 60)
guardar("parc1_step_comp.dat", {"t": t, "yc": y1, "yk20": y20})


# ------------------------------------------------------------ Ejercicio 2
# Factores leidos del Bode: G1 = 34 dB (K1), G2 = 1/s, G3 = -2,41 dB con polo en 1,3,
# G4 = -40 dB con polo en 100.
K1 = 10 ** (34 / 20)
K3 = 10 ** (-2.41 / 20)
K4 = 10 ** (-40 / 20)
Kt = K1 * K3 * K4                       # ~0,38 (ver texto: 34 - 2,41 - 40 = -8,41 dB)
G2sin = Kt / (s * (1 + s / 1.3) * (1 + s / 100))

w = np.logspace(-1, 3, 800)
f1 = np.full_like(w, 20 * np.log10(K1))
f2 = -20 * np.log10(w)
f3 = 20 * np.log10(K3) - 10 * np.log10(1 + (w / 1.3) ** 2)
f4 = 20 * np.log10(K4) - 10 * np.log10(1 + (w / 100) ** 2)
asin3 = np.where(w < 1.3, 20 * np.log10(K3), 20 * np.log10(K3) - 20 * np.log10(w / 1.3))
asin4 = np.where(w < 100, 20 * np.log10(K4), 20 * np.log10(K4) - 20 * np.log10(w / 100))
guardar("parc2_factores.dat", {"w": w, "g1": f1, "g2": f2, "g3": f3, "g4": f4,
                               "a3": asin3, "a4": asin4})

# Compensador de atraso para Kv = 20: G20 = 20/(s(1+s/1.3)(1+s/100))
G20 = 20 / (s * (1 + s / 1.3) * (1 + s / 100))
Gc2 = (20 * s + 1) / (800 * s + 1)      # beta = 40, T = 20 s
L2 = G20 * Gc2

w = np.logspace(-3, 2, 800)
guardar("parc2_bode.dat", {
    "w": w,
    "ms": mag_db(G2sin, w), "fs": fase(G2sin, w),
    "m20": mag_db(G20, w), "f20": fase(G20, w),
    "mc": mag_db(L2, w), "fc": fase(L2, w),
    "mg": mag_db(Gc2, w), "fg": fase(Gc2, w),
})

w = np.logspace(-3, 1.6, 3000)
guardar("parc2_nichols_sin.dat", {"fase": fase(G2sin, w), "mag": mag_db(G2sin, w)})
guardar("parc2_nichols_comp.dat", {"fase": fase(L2, w), "mag": mag_db(L2, w)})

t, ys = escalon(ct.feedback(G2sin, 1), 60)
_, yc = escalon(ct.feedback(L2, 1), 60)
guardar("parc2_step.dat", {"t": t, "ys": ys, "yc": yc})


def resumen(nombre, L):
    gm, pm, wpc, wgc = ct.margin(L)
    cl = ct.feedback(L, 1)
    est = np.all(ct.poles(cl).real < 0)
    txt = f"{nombre:28s} GM={20*np.log10(gm) if np.isfinite(gm) else np.inf:7.2f} dB  MF={pm:7.2f}  wc={wgc:7.4f}  w180={wpc:7.3f}"
    if est:
        i = ct.step_info(cl, T=np.linspace(0, 400, 400001))
        txt += f"  Mp={i['Overshoot']:6.2f}%  ts={i['SettlingTime']:6.2f}"
    else:
        txt += "  INESTABLE"
    print(txt)


if __name__ == "__main__":
    print(f"K total ejercicio 2 = {Kt:.4f} ({20*np.log10(Kt):.2f} dB)")
    resumen("ej1 sin comp K=100", G1_sin)
    resumen("ej1 compensada", L1)
    resumen("ej2 sin comp K=0.38", G2sin)
    resumen("ej2 K=20 sin atraso", G20)
    resumen("ej2 compensada", L2)
