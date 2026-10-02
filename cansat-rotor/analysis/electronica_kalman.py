#!/usr/bin/env python3
"""Estimador altura-velocidad (filtro de Kalman) y lógica de decisión del CanSat.

Simula un perfil sintético (plataforma, motor, planeo balístico, expulsión, drogue y
rotor), los sensores (barómetro e IMU con sus errores) y tres algoritmos de decisión:
  A  barómetro crudo con umbrales (implementación ingenua),
  B  media móvil exponencial (EMA) y derivada filtrada,
  C  filtro de Kalman con la IMU como entrada, compuerta de innovación, votación y
     bloqueos por tiempo (propuesta del capítulo).
Salidas en analysis/data/electronica_kalman_*.dat y un resumen por consola.

Uso: python3 analysis/electronica_kalman.py   (≈ 10 s)
Todas las cantidades en SI. Altura positiva hacia arriba, relativa al suelo.
"""
import os
import numpy as np
from scipy.linalg import solve_discrete_are

G = 9.80665
RHO = 1.225
DT = 0.02                     # 50 Hz: barómetro e IMU
AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(AQUI, "data")

# ---------------------------------------------------------------- perfil base
T_PAD = 5.0                   # s en la plataforma antes del encendido
T_BURN = 1.6                  # s de motor
A_BOOST = 80.0                # m/s2 de aceleración neta nominal
K_R0 = 5.26e-4                # 1/m: arrastre del cohete (apogeo nominal 700 m)
V_BODY = 37.6                 # m/s: velocidad límite del cuerpo solo (Ø95, Cd 0,8)
T_DROGUE = 0.5                # s de apertura del drogue después de la expulsión
V1_NOM, V2_NOM = 13.4, 6.4    # m/s: etapa 1 (drogue) y etapa 2 (rotor + drogue)
TAU_ROTOR = 1.5               # s: constante de tiempo del arranque del rotor
T_SERVO = 0.15                # s: giro del anillo de traba

# ---------------------------------------------------------------- filtro (sintonía)
SIG_A = 0.5                   # m/s2: ruido de proceso efectivo (planeo y descenso)
SIG_A_BOOST = 5.0             # m/s2: durante el motor (vibración, saturación)
SIG_B = 0.3                   # m: ruido efectivo del barómetro en vuelo (supuesto)
GATE = 25.0                   # compuerta chi2 de 1 g.l. (5 sigma)
N_REANCLA = 50                # muestras rechazadas seguidas antes de re-anclar (1 s)
T_LOCK = 4.0                  # s tras el despegue: bloqueo de apogeo
T_PERSIST = 0.2               # s de persistencia de las condiciones
V_LIM = 40.0                  # m/s: cota física de descenso para el tiempo mínimo
V_TIMER = 10.0                # m/s: velocidad mínima supuesta para el temporizador
ALPHA_EMA = 0.08              # algoritmo B


def apogeo_cohete(a_b, k_r):
    """Tiempo (desde el encendido) y altura del apogeo balístico del cohete."""
    v = a_b * T_BURN
    h = 0.5 * a_b * T_BURN**2
    t = np.full_like(v, T_BURN)
    activo = v > 0
    while activo.any():
        a = -G - k_r * v * np.abs(v)
        v = np.where(activo, v + a * DT, v)
        h = np.where(activo, h + v * DT, h)
        t = np.where(activo, t + DT, t)
        activo &= v > 0
    return t, h


def parametros(N, rng, escenario, nominal):
    """Parámetros aleatorios de cada corrida (o los nominales)."""
    p = {}
    if nominal:
        p["a_b"] = np.full(N, A_BOOST)
        p["k_r"] = np.full(N, K_R0)
        p["V1"] = np.full(N, V1_NOM)
        p["sig_b"] = np.full(N, SIG_B)
        p["bias"] = np.full(N, 0.05)
        p["th0"] = np.full(N, np.radians(10.0))
        p["fp"] = np.full(N, 0.5)
        p["de"] = np.full(N, 0.5)
        p["shock"] = np.full(N, 25.0)
    else:
        p["a_b"] = rng.uniform(65, 95, N)
        p["k_r"] = K_R0 * rng.uniform(0.6, 1.6, N)
        p["V1"] = np.clip(rng.normal(V1_NOM, 0.7, N), 11.5, 15.5)
        p["sig_b"] = rng.uniform(0.1, 0.5, N)
        p["bias"] = rng.normal(0.0, 0.1, N)
        p["th0"] = np.radians(rng.uniform(0, 15, N))
        p["fp"] = rng.uniform(0.3, 0.8, N)
        p["de"] = rng.uniform(-1.0, 2.0, N)   # expulsión respecto del apogeo [s]
        p["shock"] = rng.uniform(3.0, 30.0, N)  # pico de aceleración en la expulsión [g]
    if escenario == 2:
        p["dP"] = np.full(N, 2500.0) if nominal else rng.uniform(1000, 4000, N)
        p["dur"] = np.full(N, 0.15) if nominal else rng.uniform(0.05, 0.30, N)
        p["kq"] = np.full(N, 0.01) if nominal else rng.uniform(0, 0.02, N)
    else:
        p["dP"] = np.zeros(N); p["dur"] = np.zeros(N); p["kq"] = np.zeros(N)
    p["p_out"] = 0.002          # probabilidad de valor atípico por muestra
    t_apo_r, _ = apogeo_cohete(p["a_b"], p["k_r"])
    p["t_ej"] = T_PAD + t_apo_r + p["de"]
    return p


def simular(N, seed, escenario, nominal=False, lazo_cerrado=False, guardar=False):
    rng = np.random.default_rng(seed)
    p = parametros(N, rng, escenario, nominal)
    t_fin = p["t_ej"].max() + (40.0 if not lazo_cerrado else 160.0)
    nT = int(t_fin / DT)

    # estado verdadero
    h = np.zeros(N); v = np.zeros(N)
    fase = np.zeros(N, int)          # 0 pad 1 motor 2 planeo 3 cuerpo 4 drogue 5 rotor 6 suelo
    t_rel_real = np.full(N, np.inf)
    hmax_v = np.zeros(N); t_apo_v = np.full(N, np.nan); t80_v = np.full(N, np.nan)

    # despegue (común a los tres algoritmos)
    cnt_lo = np.zeros(N, int); t_lo = np.full(N, np.inf)

    # A: crudo
    hmA = np.full(N, -np.inf); cA = np.zeros(N, int)
    apoA = np.full(N, np.nan); relA = np.full(N, np.nan)
    hrelA = np.full(N, np.nan); hmaxA = np.full(N, np.nan); vapoA = np.full(N, np.nan)
    # B: EMA
    e = np.zeros(N); e_prev = np.zeros(N); vb = np.zeros(N); cB = np.zeros(N, int)
    hmB = np.full(N, -np.inf)
    apoB = np.full(N, np.nan); relB = np.full(N, np.nan)
    hrelB = np.full(N, np.nan); hmaxB = np.full(N, np.nan); vapoB = np.full(N, np.nan)
    # C: Kalman
    xh = np.zeros(N); xv = np.zeros(N)
    P00 = np.full(N, 1.0); P01 = np.zeros(N); P11 = np.full(N, 0.1)
    u_ult = np.zeros(N); nrech = np.zeros(N, int)
    choque = np.zeros(N, bool); t_v1 = np.full(N, np.inf); t_v2 = np.full(N, np.inf)
    hmC = np.full(N, -np.inf)
    apoC = np.full(N, np.nan); relC = np.full(N, np.nan); por_timer = np.zeros(N, bool)
    hrelC = np.full(N, np.nan); hmaxC = np.full(N, np.nan); vapoC = np.full(N, np.nan)
    t_cond = np.full(N, np.inf)
    quieto = np.full(N, np.inf); t_land_det = np.full(N, np.nan)
    err_h = []; err_v = []          # errores en descenso (etapa 1)

    k1 = G / p["V1"]**2
    k_body = G / V_BODY**2
    hist = [] if guardar else None

    for i in range(nT):
        t = i * DT
        # ------------------------------------------------ dinámica verdadera
        fase = np.where((fase == 0) & (t >= T_PAD), 1, fase)
        fase = np.where((fase == 1) & (t >= T_PAD + T_BURN), 2, fase)
        fase = np.where((fase == 2) & (t >= p["t_ej"]), 3, fase)
        fase = np.where((fase == 3) & (t >= p["t_ej"] + T_DROGUE), 4, fase)
        fase = np.where((fase == 4) & (t >= t_rel_real), 5, fase)
        a = np.zeros(N)
        a = np.where(fase == 1, p["a_b"], a)
        a = np.where(fase == 2, -G - p["k_r"] * v * np.abs(v), a)
        a = np.where(fase == 3, -G - k_body * v * np.abs(v), a)
        a = np.where(fase == 4, -G - k1 * v * np.abs(v), a)
        if lazo_cerrado:
            Veff = V2_NOM + (p["V1"] - V2_NOM) * np.exp(-np.maximum(t - t_rel_real, 0) / TAU_ROTOR)
            a = np.where(fase == 5, -G - G / Veff**2 * v * np.abs(v), a)
        v = v + a * DT
        h = h + v * DT
        tierra = (fase >= 3) & (h <= 0)
        fase = np.where(tierra, 6, fase)
        h = np.where(fase == 6, 0.0, h); v = np.where(fase == 6, 0.0, v)
        a = np.where(fase == 6, 0.0, a)
        # apogeo y 80 % verdaderos
        nuevo = (fase >= 1) & np.isnan(t_apo_v) & (v <= 0) & (t > T_PAD + T_BURN)
        t_apo_v = np.where(nuevo, t, t_apo_v)
        hmax_v = np.maximum(hmax_v, h)
        c80 = ~np.isnan(t_apo_v) & np.isnan(t80_v) & (h <= 0.8 * hmax_v)
        t80_v = np.where(c80, t, t80_v)

        # ------------------------------------------------ sensores
        f = a + G                                        # fuerza específica vertical
        th = p["th0"] * np.sin(2 * np.pi * p["fp"] * t) * (fase >= 3) * (fase < 6)
        fm = f * np.cos(th) + p["bias"] + rng.normal(0, 0.05, N)
        fm += np.where(fase == 1, rng.normal(0, 3.0, N), 0.0)          # vibración del motor
        fm += np.where((t >= p["t_ej"]) & (t < p["t_ej"] + DT), p["shock"] * G, 0.0)  # choque
        fm = np.clip(fm, -16 * G, 16 * G)                               # saturación
        z = h + rng.normal(0, 1, N) * p["sig_b"]
        atip = rng.random(N) < p["p_out"]
        z += np.where(atip, rng.choice([-1, 1], N) * rng.uniform(5, 30, N), 0.0)
        z += np.where(fase <= 2, p["kq"] * v**2 / (2 * G), 0.0)        # presión dinámica
        pico = (t >= p["t_ej"]) & (t < p["t_ej"] + p["dur"])
        z -= np.where(pico, p["dP"] / (RHO * G), 0.0)                  # expulsión

        # ------------------------------------------------ despegue (acelerómetro)
        cnt_lo = np.where(fm > 2 * G, cnt_lo + 1, 0)
        t_lo = np.where(np.isinf(t_lo) & (cnt_lo >= 5), t, t_lo)
        vuelo = t >= t_lo

        # ------------------------------------------------ A: barómetro crudo
        actA = vuelo & np.isnan(apoA)
        hmA = np.where(actA, np.maximum(hmA, z), hmA)
        cA = np.where(actA & (z < hmA - 1.0), cA + 1, 0)
        dA = actA & (cA >= 5)
        apoA = np.where(dA, t, apoA); hmaxA = np.where(dA, hmA, hmaxA)
        vapoA = np.where(dA, v, vapoA)
        rA = ~np.isnan(apoA) & np.isnan(relA) & (z <= 0.8 * hmaxA)
        relA = np.where(rA, t, relA); hrelA = np.where(rA, h, hrelA)

        # ------------------------------------------------ B: EMA
        e_prev = e.copy()
        e = np.where(i == 0, z, e + ALPHA_EMA * (z - e))
        vb = vb + ALPHA_EMA * ((e - e_prev) / DT - vb)
        actB = vuelo & np.isnan(apoB)
        hmB = np.where(actB, np.maximum(hmB, e), hmB)
        cB = np.where(actB & (vb < 0), cB + 1, 0)
        dB = actB & (cB >= 5)
        apoB = np.where(dB, t, apoB); hmaxB = np.where(dB, hmB, hmaxB)
        vapoB = np.where(dB, v, vapoB)
        rB = ~np.isnan(apoB) & np.isnan(relB) & (e <= 0.8 * hmaxB)
        relB = np.where(rB, t, relB); hrelB = np.where(rB, h, hrelB)

        # ------------------------------------------------ C: Kalman
        es_choque = vuelo & (t - t_lo > T_LOCK) & (np.abs(fm) > 6 * G)
        choque |= es_choque
        u = np.where(es_choque, u_ult, fm - G)
        u_ult = u
        sa = np.where(vuelo & (t - t_lo < T_BURN + 1.0), SIG_A_BOOST, SIG_A)
        sa = np.where(es_choque, 10.0, sa)
        q = sa**2
        # predicción
        xh = xh + xv * DT + 0.5 * u * DT**2
        xv = xv + u * DT
        P00n = P00 + 2 * DT * P01 + DT**2 * P11 + q * DT**4 / 4
        P01n = P01 + DT * P11 + q * DT**3 / 2
        P11n = P11 + q * DT**2
        P00, P01, P11 = P00n, P01n, P11n
        # actualización con compuerta de innovación
        nu = z - xh
        S = P00 + SIG_B**2
        ok = nu**2 <= GATE * S
        nrech = np.where(ok, 0, nrech + 1)
        rean = nrech >= N_REANCLA
        P00 = np.where(rean, P00 + nu**2, P00)
        S = P00 + SIG_B**2
        usar = ok | rean
        nrech = np.where(rean, 0, nrech)
        K0 = P00 / S; K1 = P01 / S
        xh = np.where(usar, xh + K0 * nu, xh)
        xv = np.where(usar, xv + K1 * nu, xv)
        P00u = (1 - K0) * P00; P01u = (1 - K0) * P01; P11u = P11 - K1 * P01
        P00 = np.where(usar, P00u, P00); P01 = np.where(usar, P01u, P01)
        P11 = np.where(usar, P11u, P11)
        # votación de apogeo (2 de 3) con bloqueo por tiempo
        actC = vuelo & np.isnan(apoC)
        hmC = np.where(actC, np.maximum(hmC, xh), hmC)
        t_v1 = np.where(actC & (xv < -1.0), np.minimum(t_v1, t), np.inf)
        voto1 = (t - t_v1) >= T_PERSIST
        voto2 = (hmC - xh) > 3.0
        voto3 = choque
        votos = voto1.astype(int) + voto2.astype(int) + voto3.astype(int)
        dC = actC & (t - t_lo > T_LOCK) & ((votos >= 2) | (t - t_lo > 40.0))
        apoC = np.where(dC, t, apoC); hmaxC = np.where(dC, hmC, hmaxC)
        vapoC = np.where(dC, v, vapoC)
        # liberación al 80 %: anticipación, persistencia, tiempo mínimo y temporizador
        desc = ~np.isnan(apoC) & np.isnan(relC)
        cond = desc & (xh + xv * T_PERSIST <= 0.8 * hmaxC)
        t_cond = np.where(cond, np.minimum(t_cond, t), np.inf)
        t_min = 0.2 * hmaxC / V_LIM
        t_tim = 0.2 * hmaxC / V_TIMER + V_TIMER / G * np.log(2)
        baro = desc & ((t - t_cond) >= T_PERSIST) & ((t - apoC) >= t_min)
        timer = desc & ((t - apoC) >= t_tim)
        rC = baro | timer
        por_timer = np.where(rC & ~baro, True, por_timer)
        relC = np.where(rC, t, relC); hrelC = np.where(rC, h, hrelC)
        if lazo_cerrado:
            t_rel_real = np.where(rC & np.isinf(t_rel_real), t + T_SERVO, t_rel_real)
        # aterrizaje (solo informativo)
        land = ~np.isnan(relC) & (np.abs(xv) < 0.5)
        quieto = np.where(land, np.minimum(quieto, t), np.inf)
        t_land_det = np.where(np.isnan(t_land_det) & (t - quieto >= 5.0), t, t_land_det)
        # errores de estimación en la etapa 1, lejos de los eventos
        sel = (fase == 4) & (t > p["t_ej"] + 3.0) & np.isnan(relC)
        if sel.any():
            err_h.append((xh - h)[sel]); err_v.append((xv - v)[sel])

        if guardar:
            hist.append((t, h[0], z[0], e[0], xh[0], v[0], vb[0], xv[0], fase[0], fm[0]))

    res = dict(p=p, t_apo_v=t_apo_v, hmax_v=hmax_v, t80_v=t80_v, t_lo=t_lo,
               A=dict(apo=apoA, rel=relA, hrel=hrelA, hmax=hmaxA, vapo=vapoA),
               B=dict(apo=apoB, rel=relB, hrel=hrelB, hmax=hmaxB, vapo=vapoB),
               C=dict(apo=apoC, rel=relC, hrel=hrelC, hmax=hmaxC, vapo=vapoC,
                      timer=por_timer),
               t_land_det=t_land_det,
               err_h=np.concatenate(err_h) if err_h else np.array([]),
               err_v=np.concatenate(err_v) if err_v else np.array([]),
               hist=np.array(hist) if guardar else None, t_rel_real=t_rel_real)
    return res


def metricas(r, alg):
    d = r[alg]
    hm = r["hmax_v"]
    det = ~np.isnan(d["apo"])
    retardo = (d["apo"] - r["t_apo_v"])[det]
    falso_apo = det & (d["vapo"] > 5.0)
    frac = d["hrel"] / hm
    sin_rel = np.isnan(d["rel"])
    prem = ~sin_rel & (frac > 0.85)
    tard = sin_rel | (~sin_rel & (frac < 0.75))
    err = (d["hrel"] - 0.8 * hm)[~sin_rel]
    return dict(ret_med=np.median(retardo), ret_p95=np.percentile(retardo, 95),
                ehmax=np.median(np.abs(d["hmax"] - hm)[det]),
                falso_apo=100 * falso_apo.mean(),
                err_med=np.median(err) if err.size else np.nan,
                err_p95=np.percentile(np.abs(err), 95) if err.size else np.nan,
                prem=100 * prem.mean(), tard=100 * tard.mean())


def main():
    os.makedirs(DATA, exist_ok=True)
    print("== Sintonía y análisis en régimen permanente ==")
    F = np.array([[1, DT], [0, 1]]); Gm = np.array([[DT**2 / 2], [DT]])
    Q = Gm @ Gm.T * SIG_A**2; Hm = np.array([[1.0, 0.0]]); R = np.array([[SIG_B**2]])
    Pp = solve_discrete_are(F.T, Hm.T, Q, R)
    K = Pp @ Hm.T / (Pp[0, 0] + SIG_B**2)
    Pu = (np.eye(2) - K @ Hm) @ Pp
    wn = np.sqrt(SIG_A / SIG_B)
    print(f"ganancias K = [{K[0,0]:.4f}, {K[1,0]:.4f} 1/s]")
    print(f"sigma_h = {np.sqrt(Pu[0,0]):.3f} m, sigma_v = {np.sqrt(Pu[1,1]):.3f} m/s (filtro)")
    print(f"continuo: wn = sqrt(sa/sb) = {wn:.3f} rad/s, f = {wn/2/np.pi:.3f} Hz, zeta = 0.707")
    sh_c = np.sqrt(np.sqrt(2) * np.sqrt(SIG_A) * SIG_B**1.5 * DT)
    sv_c = np.sqrt(np.sqrt(2) * SIG_A**1.5 * np.sqrt(SIG_B) * DT)
    print(f"Kalman-Bucy: sigma_h = {sh_c:.3f} m, sigma_v = {sv_c:.3f} m/s")

    print("\n== Vuelo nominal en lazo cerrado (escenario 2) ==")
    r = simular(1, 7, escenario=2, nominal=True, lazo_cerrado=True, guardar=True)
    H = r["hist"]
    ta, hm = r["t_apo_v"][0], r["hmax_v"][0]
    print(f"apogeo real {hm:.1f} m a t = {ta:.2f} s; expulsión a {r['p']['t_ej'][0]:.2f} s")
    for alg in "ABC":
        d = r[alg]
        print(f"{alg}: apogeo det {d['apo'][0]-ta:+.2f} s, hmax est {d['hmax'][0]:.1f} m, "
              f"liberación a t={d['rel'][0]:.2f} s con h real {d['hrel'][0]:.1f} m "
              f"({100*d['hrel'][0]/hm:.1f} %)")
    print(f"80 % real a t = {r['t80_v'][0]:.2f} s; aterrizaje detectado a "
          f"{r['t_land_det'][0]:.1f} s")
    t_suelo = H[np.argmax((H[:, 8] == 6)), 0]
    print(f"llegada al suelo t = {t_suelo:.1f} s")
    # serie completa a 10 Hz
    with open(os.path.join(DATA, "electronica_kalman_vuelo.dat"), "w") as fo:
        fo.write("t h zb hk v vk eh ev\n")
        for row in H[::5]:
            if row[0] > t_suelo + 8: break
            fo.write(f"{row[0]:.2f} {row[1]:.2f} {row[2]:.2f} {row[4]:.2f} {row[5]:.3f} "
                     f"{row[7]:.3f} {row[4]-row[1]:.3f} {row[7]-row[5]:.3f}\n")
    # ventana del apogeo a 50 Hz
    with open(os.path.join(DATA, "electronica_kalman_apogeo.dat"), "w") as fo:
        fo.write("tr h zb he hk v ve vk\n")
        for row in H:
            if ta - 2.5 <= row[0] <= ta + 4.5:
                fo.write(f"{row[0]-ta:.2f} {row[1]:.2f} {row[2]:.2f} {row[3]:.2f} "
                         f"{row[4]:.2f} {row[5]:.3f} {row[6]:.3f} {row[7]:.3f}\n")
    # sensores a 50 Hz para la prueba del firmware en PC (software en el lazo)
    with open(os.path.join(DATA, "electronica_kalman_sensores.dat"), "w") as fo:
        fo.write("t p_Pa acc_z\n")       # acc_z en ejes del anexo (+Z hacia el nadir)
        for row in H:
            if row[0] > t_suelo + 20: break
            p_pa = 101325.0 * (1 - 2.25577e-5 * row[2])**5.25588
            fo.write(f"{row[0]:.2f} {p_pa:.2f} {-row[9]:.3f}\n")
    with open(os.path.join(DATA, "electronica_kalman_eventos.dat"), "w") as fo:
        fo.write("evento t\n")
        fo.write(f"apogeo_real {ta:.2f}\nexpulsion {r['p']['t_ej'][0]:.2f}\n")
        fo.write(f"apogeo_C {r['C']['apo'][0]:.2f}\nliberacion_C {r['C']['rel'][0]:.2f}\n")
        fo.write(f"ochenta_real {r['t80_v'][0]:.2f}\nsuelo {t_suelo:.2f}\n")
        fo.write(f"aterrizaje_C {r['t_land_det'][0]:.2f}\n")

    print("\n== Monte Carlo (lazo abierto, etapa 1 hasta el suelo) ==")
    N = 2000
    tabla = []
    for esc in (1, 2):
        r = simular(N, 100 + esc, escenario=esc)
        print(f"-- escenario {esc}: apogeo real {np.percentile(r['hmax_v'],5):.0f}--"
              f"{np.percentile(r['hmax_v'],95):.0f} m (p5--p95)")
        for alg in "ABC":
            m = metricas(r, alg)
            tabla.append((esc, alg, m))
            print(f"{alg}: retardo apogeo med {m['ret_med']:+.2f} s p95 {m['ret_p95']:+.2f} s | "
                  f"|e hmax| med {m['ehmax']:.2f} m | falso apogeo {m['falso_apo']:.1f} % | "
                  f"e liberación med {m['err_med']:+.1f} m p95|e| {m['err_p95']:.1f} m | "
                  f"prematura {m['prem']:.1f} % tardía/sin {m['tard']:.1f} %")
        print(f"C liberadas por temporizador: {100*r['C']['timer'].mean():.1f} %")
        if esc == 1:
            eh, ev = r["err_h"], r["err_v"]
            print(f"errores C en etapa 1: rms h {np.sqrt(np.mean(eh**2)):.3f} m, "
                  f"rms v {np.sqrt(np.mean(ev**2)):.3f} m/s, media v {ev.mean():+.3f} m/s")
    with open(os.path.join(DATA, "electronica_kalman_mc.dat"), "w") as fo:
        fo.write("esc alg ret_med ret_p95 ehmax falso_apo err_med err_p95 prem tard\n")
        for esc, alg, m in tabla:
            fo.write(f"{esc} {alg} {m['ret_med']:.2f} {m['ret_p95']:.2f} {m['ehmax']:.2f} "
                     f"{m['falso_apo']:.1f} {m['err_med']:.1f} {m['err_p95']:.1f} "
                     f"{m['prem']:.1f} {m['tard']:.1f}\n")

    print("\n== Fallo de barómetro tras el apogeo: liberación por temporizador ==")
    for hmx in (500, 700, 1000):
        for V1 in (12.0, 13.4, 15.0):
            tt = 0.2 * hmx / V_TIMER + V_TIMER / G * np.log(2)
            caida = V1**2 / G * np.log(np.cosh(G * tt / V1))   # caída desde el reposo
            print(f"hmax {hmx} V1 {V1}: t_tim {tt:.1f} s, liberación a "
                  f"{100*(hmx-caida)/hmx:.1f} % de hmax")


if __name__ == "__main__":
    main()
