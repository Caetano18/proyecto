#!/usr/bin/env python3
"""Presupuesto de potencia por estado, autonomía y caída de tensión del CanSat.

Corrientes típicas: las del XBee-PRO 900HP son de su hoja de datos; el resto son valores
representativos de componentes de la clase indicada (a medir con el prototipo).
Las duraciones de las fases de vuelo salen del vuelo nominal simulado (altura de liberación
CANSAT_HLIB, por defecto 500 m, apogeo 625 m): electronica_kalman.py (eventos) y
electronica_sil.cpp (instantes de los estados). Correr antes esos dos.
Uso: python3 analysis/electronica_potencia.py
"""
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
HLIB = float(os.environ.get("CANSAT_HLIB", "500"))   # m: altura de liberación del rotor
SUF = "" if HLIB == 500.0 else f"_H{HLIB:.0f}"
EV = {}                              # instantes del vuelo nominal simulado [s]
with open(os.path.join(AQUI, "data", f"electronica_kalman_eventos{SUF}.dat")) as f:
    next(f)
    for linea in f:
        k, v = linea.split()
        EV[k] = float(v)
# prueba del firmware en la PC (electronica_sil.cpp): ASCENT a 5,08 s; APOGEE dura 1,0 s
# hasta DESCENT; PAYLOAD_RELEASE llega 1,92 s después de la orden de liberación
T_ASCENT, T_APOGEE, T_GIRO = 5.08, 1.0, 1.92
D_ASCENT = round(EV["apogeo_C"] + T_APOGEE - T_ASCENT)               # ASCENT + APOGEE
D_DESCENT = round(EV["liberacion_C"] - (EV["apogeo_C"] + T_APOGEE))  # etapa 1 (drogue)
D_PAYLOAD = round(EV["aterrizaje_C"] - (EV["liberacion_C"] + T_GIRO))  # hasta LANDED

ETA_33, ETA_5 = 0.90, 0.88          # rendimiento del buck-boost 3,3 V y del boost 5 V

# consumo en el riel de 3,3 V [mA]
R33 = {
    "MCU (Cortex-M4/M7)": 90.0,
    "Barómetro + IMU": 2.3,
    "GPS": 30.0,
    "SD (promedio)": 10.0,
    "INA219 + FRAM + RTC": 1.3,
    "Sensor hall": 5.0,
    "LED de encendido": 2.0,
}
# radio XBee-PRO 900HP (hoja de datos): RX 29 mA, TX 215 mA a 24 dBm
RX, TX, T_AIRE = 29.0, 215.0, 0.020  # s en el aire por paquete (200 B a 200 kbit/s + cabeceras)
RADIO = RX + T_AIRE * 1.0 * (TX - RX)
# riel de 5 V [mA]
SERVO_REPOSO, SERVO_MOV, SERVO_BLOQ = 10.0, 200.0, 700.0
CAMARAS = 2 * 180.0

def p_entrada(i33, i5):
    return 3.3 * i33 / 1000 / ETA_33 + 5.0 * i5 / 1000 / ETA_5

base33 = sum(R33.values()) + RADIO
estados = [
    # nombre, duración [s], i33 [mA], i5 [mA]
    ("LAUNCH_PAD (2 h, cámaras apagadas)", 7200, base33, SERVO_REPOSO),
    ("ASCENT + APOGEE", D_ASCENT, base33, SERVO_REPOSO + CAMARAS),
    ("DESCENT", D_DESCENT, base33, SERVO_REPOSO + CAMARAS),
    ("PROBE_RELEASE (servo en movimiento 0,3 s)", 3, base33, SERVO_REPOSO + CAMARAS
     + (SERVO_MOV - SERVO_REPOSO) * 0.3 / 3),
    ("PAYLOAD_RELEASE", D_PAYLOAD, base33, SERVO_REPOSO + CAMARAS),
    ("LANDED (1 h, cámaras 60 s)", 3600, base33, SERVO_REPOSO + CAMARAS * 60 / 3600),
]

print(f"radio promedio = {RADIO:.1f} mA; riel 3,3 V = {base33:.1f} mA")
E = 0.0
for n, d, i33, i5 in estados:
    P = p_entrada(i33, i5)
    E += P * d / 3600
    print(f"{n:45s} P = {P:.3f} W  t = {d:5d} s  E = {P*d/3600*1000:7.1f} mWh")
E_disp = 3.0 * 3.6 * 0.80
print(f"energía total {E:.2f} Wh; disponible (3000 mAh, 3,6 V, 80 %) {E_disp:.2f} Wh; "
      f"factor {E_disp/E:.1f}")
P_pad = p_entrada(base33, SERVO_REPOSO); P_all = p_entrada(base33, SERVO_REPOSO + CAMARAS)
print(f"autonomía modo plataforma {E_disp/P_pad:.1f} h; todo encendido {E_disp/P_all:.1f} h")
E_cam = E - P_pad * 7200 / 3600 + P_all * 7200 / 3600   # cámaras encendidas desde la plataforma
print(f"con las cámaras encendidas desde la plataforma: {E_cam:.2f} Wh, factor {E_disp/E_cam:.1f}")

print("\n== Caída de tensión con el servo bloqueado ==")
for nombre, Rtot in (("celda nueva, 25 °C", 0.17), ("celda envejecida o fría", 0.25)):
    for Voc in (4.2, 3.6, 3.4):
        P = p_entrada(base33, SERVO_BLOQ + CAMARAS)
        # resolver V = Voc - I R con I = P / V
        V = (Voc + (Voc**2 - 4 * Rtot * P)**0.5) / 2
        print(f"{nombre:25s} Voc={Voc:.1f} V: P={P:.2f} W, I={P/V:.2f} A, "
              f"caída={Voc-V:.2f} V, V_bat={V:.2f} V")

print("\n== Condensador del riel de 5 V ==")
for C in (220e-6, 470e-6, 1000e-6):
    for dt in (50e-6, 100e-6):
        dV = SERVO_BLOQ / 1000 * dt / C + SERVO_BLOQ / 1000 * 0.03
        print(f"C={C*1e6:.0f} uF, t_resp={dt*1e6:.0f} us: dV = {dV*1000:.0f} mV")
