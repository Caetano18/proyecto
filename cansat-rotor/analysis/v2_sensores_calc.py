#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cálculos de apoyo del capítulo de sensores: (A) tiempo en el aire y margen del enlace LoRa, (B) autonomía con una o
dos celdas, (C) campo del imán del sensor de rpm sobre el magnetómetro, (D) presupuesto de pines.
Altura del enlace: CANSAT_HLIB = altura de liberación del rotor [m] (por defecto 500; apogeo de diseño H_lib/0,8 = 625 m).
El CanSat se evalúa a la altura de liberación, como analysis/electronica_enlace.py; con otro valor las salidas
llevan el sufijo _H<H_lib>.
Salida: analysis/data/sensores_calc.json y sensores_lora.dat. Uso: python3 analysis/v2_sensores_calc.py"""
import os, json, math
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
rng = np.random.default_rng(20261017)
res = {}
HLIB = float(os.environ.get('CANSAT_HLIB', '500'))      # altura de liberación del rotor [m]
SUF = '' if HLIB == 500.0 else '_H%g' % HLIB            # sufijo de las salidas del caso alternativo
H_APO = HLIB / 0.8                                      # apogeo de diseño [m]
H_GS = 1.5                                              # altura de la antena de tierra [m] (electronica_enlace.py)

# ------------------------------------------------------------------ A. LoRa
def airtime(PL, SF, BW, CR=1, npre=8, crc=1, ih=0):
    Ts = 2.0**SF / BW
    de = 1 if Ts > 16e-3 else 0
    nsym = 8 + max(math.ceil((8*PL - 4*SF + 28 + 16*crc - 20*ih) / (4*(SF - 2*de))) * (CR + 4), 0)
    return (npre + 4.25) * Ts + nsym * Ts
# sensibilidad SX1276 a BW 125 kHz (hoja de datos / AN1200.22) [dBm]; a otro BW se corrige 10 log(BW/125)
SENS125 = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}
filas = []
for SF in range(7, 13):
    for BW in (125e3, 250e3, 500e3):
        S = SENS125[SF] + 10*math.log10(BW/125e3)
        filas.append((SF, BW/1e3, airtime(56, SF, BW), airtime(140, SF, BW), S))
with open(os.path.join(D, 'sensores_lora%s.dat' % SUF), 'w') as f:
    f.write('SF BW_kHz t56_s t140_s S_dBm\n')
    for r in filas:
        f.write('%d %g %.4f %.4f %.1f\n' % r)
res['lora_airtime'] = {'SF%d_BW%g' % (r[0], r[1]): dict(t56=r[2], t140=r[3], S=r[4]) for r in filas}
# margen a 2 km oblicuos (misma geometría que el cap. de electrónica): Pt, ganancias y pérdidas
lam = 299792458.0 / 915e6
def fspl(d):
    return 20*math.log10(4*math.pi*d/lam)
def g_cansat(h, d=2000.0):
    """Ganancia [dBi] del dipolo de media onda vertical del CanSat a la altura h, con la estación a d de distancia oblicua."""
    th = math.atan2(math.sqrt(d**2 - (h - H_GS)**2), h - H_GS)       # ángulo desde el eje del dipolo
    return max(10*math.log10(1.64*(math.cos(math.pi/2*math.cos(th))/math.sin(th))**2), -20.0), math.degrees(th)
Gc, theta_deg = g_cansat(HLIB)
Gc_apogeo, theta_apogeo = g_cansat(H_APO)       # peor caso: más alto, más cerca del nulo del dipolo
Pt, Gt, cab, pol, cuerpo = 20.0, 8.0, -1.5, -1.0, -3.0
G = Gc + Gt + cab + pol + cuerpo
Pr2k = Pt + G - fspl(2000.0)
Pr_nulo = Pt + (-20.0) + Gt + cab + pol + cuerpo - fspl(2000.0)
res['enlace'] = dict(h_cansat=HLIB, theta_deg=theta_deg, Gc_dBi=Gc, h_apogeo=H_APO, theta_apogeo_deg=theta_apogeo, Gc_apogeo_dBi=Gc_apogeo,
                     fspl_2km=fspl(2000.0), Pr_2km=Pr2k, Pr_nulo=Pr_nulo, G_total=G,
                     margen_SF7=Pr2k - SENS125[7], margen_SF9=Pr2k - SENS125[9], margen_SF12=Pr2k - SENS125[12],
                     margen_nulo_SF7=Pr_nulo - SENS125[7], margen_nulo_SF9=Pr_nulo - SENS125[9])
# alcance sobre el suelo (dos rayos, h_c = 0,3 m; h_t = 1,5 m) con 10 dB de reserva. No depende de la altura de
# vuelo: se mantiene la ganancia de diseño anterior (1,6 dBi); en tierra el dipolo da unos 2,15 dBi (pendiente de
# unificar con el cap. de electrónica).
GC_SUELO = 1.6
G_SUELO = GC_SUELO + Gt + cab + pol + cuerpo
def alcance_suelo(S, reserva=10.0, hc=0.3, ht=1.5):
    perd = Pt + G_SUELO - S - reserva
    return 10**((perd + 20*math.log10(hc*ht)) / 40.0)
res['alcance_suelo_m'] = {('SF%d' % sf): alcance_suelo(SENS125[sf]) for sf in (7, 9, 10, 12)}
res['alcance_libre_km'] = {('SF%d' % sf): 10**((Pt + G_SUELO - SENS125[sf] - 10 + 20*math.log10(lam/(4*math.pi)))/(-20.0))/1000 * 1.0 for sf in (7, 9, 12)}
# (la última línea se invierte: d = lam/(4 pi) 10^((Pt+G-S-reserva)/20))
res['alcance_libre_km'] = {('SF%d' % sf): lam/(4*math.pi) * 10**((Pt + G_SUELO - SENS125[sf] - 10)/20.0)/1000 for sf in (7, 9, 12)}

# ------------------------------------------------------------------ B. Autonomía con 1 o 2 celdas
nom = dict(i_c3=85.0, i_sens=8.8, i_gps=35.0, i_lora=105.0, i_sd=30.0, i_led=5.0, i_cam=300.0, i_servo=20.0,
           eta_buck=0.90, eta_boost=0.85, frac_util=0.90, cap=3.4, f_cap_T=1.0)
def horas(p):
    i33 = p['i_c3'] + p['i_sens'] + p['i_gps'] + p['i_lora'] + p['i_sd'] + p['i_led']
    P33 = 3.3 * i33 / 1000 / (p['eta_buck'] * p['eta_boost'])
    P5 = 5.0 * (2 * p['i_cam'] + p['i_servo']) / 1000 / p['eta_boost']
    return p['cap'] * 3.6 * p['frac_util'] * p['f_cap_T'] / (P33 + P5)
rangos = dict(i_c3=(70, 200), i_sens=(8, 15), i_gps=(25, 45), i_lora=(20, 140), i_sd=(10, 60), i_led=(2, 10),
              i_cam=(180, 330), i_servo=(10, 40), eta_buck=(0.80, 0.93), eta_boost=(0.75, 0.90),
              frac_util=(0.80, 0.95), f_cap_T=(0.85, 1.0))
def mc(cap_lo, cap_hi, N=20000, i_cam=None):
    r = dict(rangos)
    if i_cam: r['i_cam'] = i_cam
    X = {n: rng.uniform(lo, hi, N) for n, (lo, hi) in r.items()}
    X['cap'] = rng.uniform(cap_lo, cap_hi, N)
    h = np.array([horas({n: X[n][i] for n in X}) for i in range(N)])
    return dict(media=float(h.mean()), p5=float(np.percentile(h, 5)), P_menor_2h=float(np.mean(h < 2.0)))
res['energia'] = dict(una_celda=mc(2.9, 3.4), dos_celdas=mc(5.8, 6.8), una_celda_cam180=mc(2.9, 3.4, i_cam=(150, 220)),
                      una_celda_cam250=mc(2.9, 3.4, i_cam=(200, 280)),
                      h_nominal_1=horas(dict(nom)), h_nominal_2=horas(dict(nom, cap=6.8)))
res['energia']['h_cam180_lora45'] = horas(dict(nom, i_cam=180, i_lora=45))
res['energia']['h_cam180_lora45_2c'] = horas(dict(nom, i_cam=180, i_lora=45, cap=6.8))
# aunque la capacidad mínima del fabricante (3350 mAh) fuera la real
res['energia']['una_celda_3350'] = horas(dict(nom, cap=3.35))

# ------------------------------------------------------------------ C. imán del sensor de rpm y magnetómetro
mu0 = 4e-7*math.pi
def dipolo(Br, d_mm, h_mm, r_m):
    V = math.pi*(d_mm/2e3)**2 * h_mm/1e3
    m = Br*V/mu0
    ax = mu0/(4*math.pi) * 2*m/r_m**3 * 1e6      # µT sobre el eje
    return m, ax, ax/2
BE_total, BE_h = 25.0, 20.0                       # µT, orden de magnitud para el centro de Argentina (WMM)
mag = []
for nombre, Br, d, h in (('Ø4×1,5 N42', 1.3, 4, 1.5), ('Ø6×2 N42', 1.3, 6, 2.0)):
    for r in (0.05, 0.10, 0.15, 0.20, 0.30):
        m, ax, ec = dipolo(Br, d, h, r)
        mag.append(dict(iman=nombre, r_mm=r*1e3, B_eje_uT=ax, B_ecuador_uT=ec, err_rumbo_peor_deg=math.degrees(math.asin(min(1, ax/BE_h)))))
res['iman'] = mag

# ------------------------------------------------------------------ D. presupuesto de pines (ESP32-C3 Super Mini)
pines = [('I2C (SDA, SCL): BMP280, AHT20, MPU6050, QMC5883L, INA219, FRAM, RTC', 2), ('UART del GPS (RX, TX)', 2),
         ('SPI compartido (SCK, MOSI, MISO): LoRa y microSD', 3), ('LoRa: NSS, BUSY, NRESET, IRQ', 4), ('microSD: CS', 1),
         ('Servos (2 PWM)', 2), ('Habilitación de las cámaras (MOSFET)', 1), ('Sensor Hall de rpm', 1),
         ('Estado de las trabas (2 microinterruptores)', 2), ('Panel solar (ADC)', 1)]
res['pines'] = dict(lista=pines, total=sum(p[1] for p in pines))
json.dump(res, open(os.path.join(D, 'sensores_calc%s.json' % SUF), 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: res[k] for k in ('enlace', 'alcance_suelo_m', 'alcance_libre_km', 'energia')}, indent=1))
for r in filas:
    if r[1] == 125: print('SF%d BW%g  t56=%.3f s  t140=%.3f s  S=%.1f' % r)
for m in mag: print(m)
print('pines', res['pines']['total'])
