#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Confiabilidad del sistema de descenso de dos etapas (rotor libre + drogue).

1. Probabilidad de que la etapa 2 no cumpla C4 con el rotor sano (evento x17),
   por Monte Carlo sobre C_R, aporte del drogue, densidad, masa, apogeo y
   duración del arranque.
2. Árboles de fallas: "la etapa 2 no cumple C4" (TOP1) y "pérdida del CanSat"
   (TOP2). Cortes mínimos (MOCUS), probabilidad exacta, cota de cortes mínimos,
   medidas de importancia (Fussell-Vesely, Birnbaum, RAW, RRW) y propagación de
   la incertidumbre con distribuciones lognormales (factor de error EF).
3. Diagrama de bloques de la cadena de liberación con y sin redundancias.

Todas las probabilidades de eventos básicos son ESTIMACIONES DE INGENIERÍA por
vuelo, para el diseño con las acciones del AMFE aplicadas y la campaña E1-E6
aprobada. No son datos de campo.

Salida: analysis/data/confiabilidad_*.dat y un resumen por pantalla.
"""
import os
import numpy as np

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
rng = np.random.default_rng(20261002)

# ---------------------------------------------------------------------------
# 1. Rendimiento aerodinámico: P(Vmedia_etapa2 > 8 m/s | rotor sano)
# ---------------------------------------------------------------------------
g = 9.80665
A_R = np.pi * 0.200**2            # disco del rotor
A_d = np.pi * 0.125**2            # drogue Ø 0,25 m
A_c = np.pi * 0.0475**2           # cuerpo Ø 95 mm
CD_C = 0.8
P_ATM = 101325.0
R_AIRE = 287.05


def muestras_entorno(n, rng):
    """Variables comunes: masa, densidad, Cd del drogue, apogeo, t de arranque."""
    m = rng.uniform(0.490, 0.510, n)
    T = rng.uniform(278.15, 308.15, n)         # 5 a 35 °C, sitio cercano al nivel del mar
    rho = P_ATM / (R_AIRE * T)
    cd_d = rng.uniform(0.75, 0.90, n)
    hmax = rng.uniform(500.0, 1000.0, n)
    ts = rng.uniform(3.0, 6.0, n)              # arranque (cap. de dimensionamiento)
    kd = rng.uniform(0.0, 1.0, n)              # fracción del arrastre del drogue que se conserva
    return m, rho, cd_d, hmax, ts, kd


def v_media_etapa2(CR, m, rho, cd_d, hmax, ts, kd):
    W = m * g
    q = 0.5 * rho
    V1 = np.sqrt(W / (q * (cd_d * A_d + CD_C * A_c)))
    V2 = np.sqrt(W / (q * (CR * A_R + kd * cd_d * A_d + CD_C * A_c)))
    hr = 0.8 * hmax
    Vs = 0.5 * (V1 + V2)                       # velocidad media durante el arranque
    t2 = ts + (hr - Vs * ts) / V2
    return hr / t2, V2, V1


N = 400_000
m, rho, cd_d, hmax, ts, kd = muestras_entorno(N, rng)
z = rng.standard_normal(N)                     # números aleatorios comunes para C_R

mu_CR, sd_CR = 1.20, 0.10
CR = np.clip(mu_CR + sd_CR * z, 0.5, 2.0)
Vm, V2, V1 = v_media_etapa2(CR, m, rho, cd_d, hmax, ts, kd)
p_perf = float(np.mean(Vm > 8.0))
p_perf_V2 = float(np.mean(V2 > 8.0))

# Umbral de V2 estacionaria que lleva la media a 8 m/s (determinista, rho=1,225)
def umbral_V2(hmax_, ts_, V1_=13.35):
    hr = 0.8 * hmax_
    # hr / (ts + (hr - (V1+V2)/2 ts)/V2) = 8  ->  V2 (hr/8 - ts/2) = hr - V1 ts/2 ... resolver
    # hr/8 * V2 = ts V2 + hr - (V1+V2) ts/2 ->  V2 (hr/8 - ts/2) = hr - V1 ts/2
    return (hr - V1_ * ts_ / 2) / (hr / 8 - ts_ / 2)

umbrales = {(h, t): umbral_V2(h, t) for h in (500, 700, 1000) for t in (3, 6)}

# Sensibilidad a la incertidumbre de C_R
sig = np.round(np.arange(0.02, 0.2501, 0.01), 3)
sens_rows = []
for s in sig:
    row = [s]
    for mu in (1.10, 1.20, 1.30):
        CRs = np.clip(mu + s * z, 0.3, 2.5)
        row.append(np.mean(v_media_etapa2(CRs, m, rho, cd_d, hmax, ts, kd)[0] > 8.0))
    # peor caso del drogue (kd = 0) con mu = 1,20
    CRs = np.clip(1.20 + s * z, 0.3, 2.5)
    row.append(np.mean(v_media_etapa2(CRs, m, rho, cd_d, hmax, ts, 0.0 * kd)[0] > 8.0))
    sens_rows.append(row)
sens = np.array(sens_rows)
# piso para graficar en escala logarítmica
sens_plot = sens.copy()
sens_plot[:, 1:] = np.maximum(sens_plot[:, 1:], 1e-5)
np.savetxt(os.path.join(DATA, "confiabilidad_sens.dat"), sens_plot,
           header="sigma P110 P120 P130 P120kd0", comments="", fmt="%.5g")

# C_R mínimo (verdadero) con drogue sin aporte para P(Vm>8) <= 1 %
def p_falla_CR_fijo(CRv, kdv=0.0):
    return np.mean(v_media_etapa2(CRv, m, rho, cd_d, hmax, ts, kdv)[0] > 8.0)

CR_grid = np.arange(0.90, 1.30, 0.0025)
pf_grid = np.array([p_falla_CR_fijo(c) for c in CR_grid])
CR_min_1pc = float(CR_grid[np.argmax(pf_grid <= 0.01)])
# V2 estacionaria (sin drogue) que deja P(Vm>8) <= 1 % frente a apogeo y arranque
V2_grid = np.arange(7.0, 8.0, 0.005)
hr_ = 0.8 * hmax
V1_ = np.sqrt(m * g / (0.5 * rho * (cd_d * A_d + CD_C * A_c)))
pV = []
for v in V2_grid:
    Vs = 0.5 * (V1_ + v)
    pV.append(np.mean(hr_ / (ts + (hr_ - Vs * ts) / v) > 8.0))
pV = np.array(pV)
V2_max_1pc = float(V2_grid[np.argmax(pV > 0.01) - 1])

# ---------------------------------------------------------------------------
# 2. Árboles de fallas
# ---------------------------------------------------------------------------
# Eventos básicos: código -> (mediana por vuelo, factor de error EF)
EB = {
    "x1":  (2e-3, 5),    # pérdida de alimentación en vuelo
    "x2":  (1e-3, 10),   # reinicio del MCU sin recuperar el estado
    "x3":  (5e-3, 5),    # error de lógica del firmware de liberación
    "x4":  (9e-3, 3),    # falla independiente de la detección barométrica
    "x5":  (2e-2, 3),    # falla del respaldo por tiempo (apogeo por IMU)
    "x6":  (1e-3, 5),    # causa común barómetro-respaldo (beta = 0,1)
    "x7":  (3e-3, 3),    # servo con falla permanente
    "x8":  (1.8e-3, 5),  # atasco transitorio no resuelto con 2 reintentos
    "x9":  (2e-3, 5),    # atasco permanente de la traba
    "x10": (2e-3, 5),    # alguna pala no se abre (4 x 5e-4)
    "x11": (5e-4, 5),    # paso >= 0 por montaje
    "x12": (1e-3, 5),    # fricción excesiva del cubo
    "x13": (5e-3, 10),   # cuerda del drogue en el plano del rotor
    "x14": (1e-3, 10),   # rotura de pala o portapala
    "x15": (5e-4, 5),    # falla de bisagra o pasador
    "x16": (3e-4, 5),    # tuerca M8 floja, el cubo sale
    "x17": (None, 5),    # rendimiento insuficiente (Monte Carlo)
    "x18": (2e-3, 5),    # liberación fuera de la ventana del 80 %
    "x19": (1e-2, 3),    # el drogue no se abre
    "x20": (2e-3, 5),    # rotura de cuerda o anclaje del drogue
    "x21": (0.3, 2),     # impacto a ~13 m/s deja el CanSat irrecuperable (condicional)
    "x22": (1e-2, 3),    # baliza muda
    "x23": (1e-2, 3),    # cae en zona inaccesible
    "x24": (5e-2, 3),    # sin última posición GPS
    "x25": (0.3, 2),     # sin seguimiento visual
    "x26": (0.3, 2),     # palas rotas al abrir a velocidad balística (condicional)
}
EB["x17"] = (round(p_perf, 4), 5)

GATES = {
    "TOP1": ("OR", ["G1", "G2", "G3", "x17", "x18"]),
    "G1":   ("OR", ["G11", "G12", "x10"]),
    "G11":  ("OR", ["x1", "x2", "x3", "G111"]),
    "G111": ("OR", ["G112", "x6"]),
    "G112": ("AND", ["x4", "x5"]),
    "G12":  ("OR", ["x7", "x8", "x9"]),
    "G2":   ("OR", ["x11", "x12", "x13"]),
    "G3":   ("OR", ["x14", "x15", "x16"]),
    "GR":   ("OR", ["G1", "G2", "G3"]),           # el rotor no frena
    "TOP2": ("OR", ["G6", "G7", "G8", "x23"]),
    "G6":   ("AND", ["GD", "G6b"]),
    "GD":   ("OR", ["x19", "x20"]),
    "G6b":  ("OR", ["GR", "x26"]),
    "G7":   ("AND", ["GR", "x21"]),
    "G8":   ("AND", ["x22", "x24", "x25"]),
}


def prob(node, P, fixed=None):
    """Probabilidad de un nodo sin eventos repetidos (o con módulos fijados)."""
    if fixed and node in fixed:
        return fixed[node]
    if node in P:
        return P[node]
    typ, ch = GATES[node]
    vals = [prob(c, P, fixed) for c in ch]
    if typ == "AND":
        out = 1.0
        for v in vals:
            out = out * v
        return out
    out = 1.0
    for v in vals:
        out = out * (1.0 - v)
    return 1.0 - out


def p_top(top, P):
    """Exacta. TOP2 contiene el módulo GR dos veces: se condiciona sobre él."""
    if top == "TOP1":
        return prob("TOP1", P)
    pr = prob("GR", P)
    return pr * prob("TOP2", P, {"GR": 1.0}) + (1 - pr) * prob("TOP2", P, {"GR": 0.0})


def mocus(node):
    if node in EB:
        return [frozenset([node])]
    typ, ch = GATES[node]
    sub = [mocus(c) for c in ch]
    if typ == "OR":
        cs = [c for s in sub for c in s]
    else:
        cs = [frozenset()]
        for s in sub:
            cs = [a | b for a in cs for b in s]
    cs = list(set(cs))
    cs.sort(key=len)
    mini = []
    for c in cs:
        if not any(m_ <= c for m_ in mini):
            mini.append(c)
    return mini


P0 = {k: v[0] for k, v in EB.items()}
res = {}
for top in ("TOP1", "TOP2"):
    cuts = mocus(top)
    pc = [(sorted(c, key=lambda s: int(s[1:])), float(np.prod([P0[e] for e in c]))) for c in cuts]
    pc.sort(key=lambda t: -t[1])
    pe = p_top(top, P0)
    rare = sum(p for _, p in pc)
    mcub = 1 - np.prod([1 - p for _, p in pc])
    imp = {}
    for e in EB:
        P1 = dict(P0); P1[e] = 1.0
        Pz = dict(P0); Pz[e] = 0.0
        t1, tz = p_top(top, P1), p_top(top, Pz)
        if t1 - tz > 0:
            imp[e] = dict(FV=1 - tz / pe, IB=t1 - tz, RAW=t1 / pe, RRW=pe / tz)
    res[top] = dict(cuts=pc, pe=pe, rare=rare, mcub=mcub, imp=imp)

# Probabilidades de compuertas intermedias (para anotar los árboles)
gate_p = {gname: prob(gname, P0) for gname in GATES if gname not in ("TOP2",)}
gate_p["TOP2"] = res["TOP2"]["pe"]

# Propagación de incertidumbre (lognormal, mediana = estimación puntual)
NS = 100_000
Ps = {}
for e, (med, ef) in EB.items():
    s_ln = np.log(ef) / 1.645
    Ps[e] = np.minimum(med * np.exp(s_ln * rng.standard_normal(NS)), 1.0)
unc = {}
cdf_cols = []
for top in ("TOP1", "TOP2"):
    v = p_top(top, Ps)
    unc[top] = dict(mean=float(np.mean(v)), p05=float(np.percentile(v, 5)),
                    p50=float(np.percentile(v, 50)), p95=float(np.percentile(v, 95)))
    cdf_cols.append(np.sort(v))
# Escenario tras ensayos: EF = 3 para x13, x14 y x17 (E2-E4 reducen su incertidumbre)
EF_post = {"x13": 3, "x14": 3, "x17": 3}
Ps_post = dict(Ps)
for e, ef in EF_post.items():
    med, ef0 = EB[e]
    Ps_post[e] = np.minimum(med * np.exp(np.log(ef) / 1.645 *
                                         np.log(Ps[e] / med) / (np.log(ef0) / 1.645)), 1.0)
unc_post = {top: float(np.mean(p_top(top, Ps_post))) for top in ("TOP1", "TOP2")}
q = np.linspace(0.005, 0.995, 199)
idx = (q * (NS - 1)).astype(int)
np.savetxt(os.path.join(DATA, "confiabilidad_cdf.dat"),
           np.column_stack([q, cdf_cols[0][idx], cdf_cols[1][idx]]),
           header="F P1 P2", comments="", fmt="%.5g")

# Importancias para el gráfico de barras (TOP1 y TOP2, ordenadas por FV de TOP1)
codes = sorted(EB, key=lambda e: -res["TOP1"]["imp"].get(e, {"FV": 0})["FV"])
with open(os.path.join(DATA, "confiabilidad_eventos.dat"), "w") as f:
    f.write("n code P EF FV1 RAW1 FV2 RAW2\n")
    for i, e in enumerate(codes):
        i1 = res["TOP1"]["imp"].get(e, dict(FV=0, RAW=1))
        i2 = res["TOP2"]["imp"].get(e, dict(FV=0, RAW=1))
        f.write(f"{i} {e} {EB[e][0]:.4g} {EB[e][1]} {i1['FV']:.4g} {i1['RAW']:.4g} "
                f"{i2['FV']:.4g} {i2['RAW']:.4g}\n")
top_fv = [e for e in codes if res["TOP1"]["imp"].get(e, {"FV": 0})["FV"] > 0][:12]
with open(os.path.join(DATA, "confiabilidad_fv.dat"), "w") as f:
    f.write("n code FV1 FV2\n")
    for i, e in enumerate(reversed(top_fv)):
        f.write(f"{i} {e} {res['TOP1']['imp'][e]['FV']:.4g} "
                f"{res['TOP2']['imp'].get(e, dict(FV=0))['FV']:.4g}\n")
top_fv2 = sorted([e for e in res["TOP2"]["imp"] if res["TOP2"]["imp"][e]["FV"] > 0.02],
                 key=lambda e: res["TOP2"]["imp"][e]["FV"])
with open(os.path.join(DATA, "confiabilidad_fv2.dat"), "w") as f:
    f.write("n code FV2\n")
    for i, e in enumerate(top_fv2):
        f.write(f"{i} {e} {res['TOP2']['imp'][e]['FV']:.4g}\n")
with open(os.path.join(DATA, "confiabilidad_cortes.dat"), "w") as f:
    f.write("top orden cut P\n")
    for top in ("TOP1", "TOP2"):
        for c, p in res[top]["cuts"]:
            f.write(f"{top} {len(c)} {'+'.join(c)} {p:.4g}\n")

# ---------------------------------------------------------------------------
# 3. Diagrama de bloques de la cadena de liberación
# ---------------------------------------------------------------------------
def cadena(respaldo=False, beta=0.1, reintentos=0, fram=False, manual=False,
           q_manual=0.2, q_tr=0.02, q_cond=0.3):
    pb = 1e-2                                   # falla total del canal barométrico
    q_alim = EB["x1"][0]
    q_rst = EB["x2"][0] if fram else 1e-2
    q_log = EB["x3"][0]
    if respaldo:
        q_det = (1 - beta) * pb * EB["x5"][0] + beta * pb
    else:
        q_det = pb
    q_ord = 1 - (1 - q_rst) * (1 - q_log) * (1 - q_det)   # orden de liberación
    if manual:                                  # comando MEC por radio, en paralelo
        q_ord = q_ord * q_manual
    q_trans = q_tr * q_cond**reintentos
    q_trab = 1 - (1 - EB["x7"][0]) * (1 - q_trans) * (1 - EB["x9"][0])
    q_pal = 1 - (1 - 5e-4)**4
    q_arr = 1 - (1 - EB["x11"][0]) * (1 - EB["x12"][0]) * (1 - EB["x13"][0])
    bloques = dict(alim=q_alim, orden=q_ord, traba=q_trab, palas=q_pal, arranque=q_arr)
    R = np.prod([1 - v for v in bloques.values()])
    return 1 - R, bloques

configs = [
    ("A", "serie, sin redundancias", dict()),
    ("B", "+ respaldo por tiempo (beta=0,1)", dict(respaldo=True)),
    ("B0", "+ respaldo por tiempo ideal (beta=0)", dict(respaldo=True, beta=0.0)),
    ("C", "B + 2 reintentos del servo", dict(respaldo=True, reintentos=2)),
    ("D", "C + watchdog y FRAM", dict(respaldo=True, reintentos=2, fram=True)),
    ("E", "D + comando manual MEC", dict(respaldo=True, reintentos=2, fram=True, manual=True)),
]
rbd = []
for code, name, kw in configs:
    Q, bl = cadena(**kw)
    rbd.append((code, name, Q, bl))
with open(os.path.join(DATA, "confiabilidad_rbd.dat"), "w") as f:
    f.write("conf Q alim orden traba palas arranque\n")
    for code, name, Q, bl in rbd:
        f.write(f"{code} {Q:.4g} " + " ".join(f"{bl[k]:.4g}" for k in
                ("alim", "orden", "traba", "palas", "arranque")) + "\n")

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("== Rendimiento (x17) ==")
    print(f"C_R ~ N({mu_CR}, {sd_CR}); kd ~ U(0,1); T 5-35 C; hmax 500-1000 m; ts 3-6 s")
    print(f"P(Vmedia2 > 8) = {p_perf:.4f}   P(V2 estac. > 8) = {p_perf_V2:.4f}")
    print(f"V2 media muestral = {np.mean(V2):.3f}, p95 = {np.percentile(V2,95):.3f}, "
          f"Vm p95 = {np.percentile(Vm,95):.3f}, V1 media = {np.mean(V1):.3f}")
    for k, v in umbrales.items():
        print(f"  umbral V2 para media 8: hmax={k[0]} ts={k[1]} -> {v:.3f} m/s")
    print(f"C_R mínimo verdadero (kd=0) para P<=1%: {CR_min_1pc:.3f}")
    print(f"V2 estacionaria máxima (a rho de vuelo) para P<=1%: {V2_max_1pc:.3f}")
    rho_min = P_ATM / (R_AIRE * 308.15)
    print(f"rho_min = {rho_min:.4f}; factor sqrt(1.225/rho_min) = {np.sqrt(1.225/rho_min):.4f}")
    print("sens (sigma, P110, P120, P130, P120kd0):")
    for r in sens[::3]:
        print("   " + " ".join(f"{x:.4g}" for x in r))
    for top in ("TOP1", "TOP2"):
        r = res[top]
        print(f"\n== {top} ==  exacta {r['pe']:.4e}  rare {r['rare']:.4e}  MCUB {r['mcub']:.4e}")
        print(f"  cortes: {len(r['cuts'])}  (orden 1: {sum(1 for c,_ in r['cuts'] if len(c)==1)}, "
              f"orden 2: {sum(1 for c,_ in r['cuts'] if len(c)==2)}, "
              f"orden 3: {sum(1 for c,_ in r['cuts'] if len(c)==3)})")
        for c, p in r["cuts"][:12]:
            print(f"    {'·'.join(c):14s} {p:.3e}  ({p/r['pe']*100:.1f} %)")
        print("  importancia (FV, IB, RAW, RRW):")
        for e in sorted(r["imp"], key=lambda e: -r["imp"][e]["FV"])[:12]:
            d = r["imp"][e]
            print(f"    {e:4s} FV={d['FV']:.3f} IB={d['IB']:.3f} RAW={d['RAW']:.2f} RRW={d['RRW']:.3f}")
        u = unc[top]
        print(f"  incertidumbre: media {u['mean']:.3e}, p05 {u['p05']:.3e}, p50 {u['p50']:.3e}, p95 {u['p95']:.3e}")
    print(f"\n  medias con EF=3 en x13, x14, x17: TOP1 {unc_post['TOP1']:.4f}, TOP2 {unc_post['TOP2']:.4f}")
    print("\n== compuertas ==")
    for k, v in gate_p.items():
        print(f"  {k:5s} {v:.3e}")
    print("\n== Cadena de liberación ==")
    for code, name, Q, bl in rbd:
        print(f"  {code:3s} {name:40s} Q={Q:.4e} R={1-Q:.5f} " +
              " ".join(f"{k}={v:.2e}" for k, v in bl.items()))
