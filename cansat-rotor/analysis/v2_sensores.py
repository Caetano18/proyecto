#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selección de sensores y módulos: matrices ponderadas (suma ponderada y TOPSIS) con sensibilidad a los pesos.
Puntajes de 1 a 5 (más es mejor) derivados de las especificaciones de la tabla del capítulo; los costos
relativos son estimaciones. Salida: analysis/data/sensores_decision.json  Uso: python3 analysis/v2_sensores.py"""
import os, json
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
rng = np.random.default_rng(20261016)

# (subsistema) -> (criterios, pesos, {candidato: puntajes})
S = {
 'Presión y altitud': (
   ['precisión relativa', 'ruido y resolución', 'deriva térmica', 'consumo y masa', 'costo y disponibilidad', 'herencia y software', 'compatibilidad con el equipo'],
   [0.25, 0.20, 0.15, 0.05, 0.15, 0.10, 0.10],
   {'BMP280 (equipo)': [3, 3, 3, 5, 5, 5, 5], 'BMP388': [4, 5, 4, 4, 3, 4, 4], 'MS5611': [2, 4, 3, 4, 3, 5, 4], 'BME280': [3, 3, 3, 5, 5, 5, 5]}),
 'Temperatura interna (SN2)': (
   ['precisión', 'pines e integración', 'costo', 'consumo', 'herencia', 'valor adicional'],
   [0.30, 0.20, 0.20, 0.10, 0.10, 0.10],
   {'AHT20 (equipo)': [4, 5, 4, 5, 4, 4], 'SHT31': [5, 5, 3, 4, 4, 4], 'DS18B20': [3, 3, 5, 4, 5, 1], 'temperatura del BMP280': [3, 5, 5, 5, 5, 1]}),
 'Acelerómetro y giroscopio (SN5, X5)': (
   ['rango frente a S5', 'ruido', 'consumo y masa', 'costo y disponibilidad', 'software', 'compatibilidad', 'extras'],
   [0.20, 0.15, 0.05, 0.20, 0.15, 0.10, 0.15],
   {'MPU6050 (equipo)': [2, 3, 3, 5, 5, 5, 1], 'ICM-20948': [2, 4, 3, 3, 4, 3, 5], 'LSM6DSO': [2, 4, 5, 3, 4, 3, 1], 'MPU6050 + ADXL375': [5, 3, 3, 3, 4, 4, 2]}),
 'Magnetómetro': (
   ['rango y resolución', 'inmunidad a interferencias', 'costo', 'consumo', 'software', 'compatibilidad'],
   [0.25, 0.20, 0.20, 0.10, 0.15, 0.10],
   {'QMC5883L (equipo)': [3, 2, 5, 5, 4, 5], 'LIS3MDL': [4, 3, 3, 4, 4, 4], 'MMC5983MA': [5, 4, 2, 4, 3, 3], 'AK09916 (en ICM-20948)': [3, 3, 3, 4, 4, 3]}),
 'Tensión y corriente (SN3, SN8, X6)': (
   ['rango de corriente', 'resolución y precisión', 'costo', 'compatibilidad', 'software', 'funciones (alerta)'],
   [0.25, 0.25, 0.15, 0.15, 0.10, 0.10],
   {'INA219 (equipo)': [3, 3, 5, 5, 5, 2], 'INA226': [4, 5, 4, 4, 5, 5], 'ADC del ESP32 + shunt': [3, 1, 5, 4, 4, 1]}),
 'GPS (SN4, X5)': (
   ['sensibilidad y adquisición', 'consumo', 'masa', 'costo y disponibilidad', 'soporte', 'dinámica (modelo aéreo)', 'antena integrada'],
   [0.25, 0.10, 0.05, 0.20, 0.15, 0.15, 0.10],
   {'NEO-7M (equipo)': [3, 4, 3, 3, 5, 4, 4], 'NEO-M8N': [5, 3, 3, 3, 5, 5, 4], 'ATGM336H': [3, 5, 5, 5, 3, 3, 3]}),
 'Radio (X1, X2, C5)': (
   ['potencia y sensibilidad', 'banda de X1', 'integración (módulo listo)', 'consumo', 'costo', 'herencia en CanSat', 'software'],
   [0.25, 0.15, 0.20, 0.10, 0.10, 0.10, 0.10],
   {'LR2021 (equipo)': [5, 5, 2, 3, 3, 2, 3], 'RFM95W (SX1276)': [4, 5, 5, 3, 5, 5, 5], 'XBee-PRO 900HP': [5, 5, 5, 2, 1, 5, 4], 'ESP-NOW (2,4 GHz)': [2, 4, 5, 4, 5, 2, 4]}),
 'Cámaras (C6, C7, SN6, SN7)': (
   ['confiabilidad del registro', 'calidad de video', 'consumo', 'masa y tamaño', 'costo', 'integración con el sistema', 'cumple E1/E2 (sin LiPo)'],
   [0.22, 0.13, 0.18, 0.08, 0.13, 0.13, 0.13],
   {'ESP32-CAM OV2640 (equipo)': [2, 2, 4, 5, 5, 4, 5], 'ESP32-S3 con cámara (tipo XIAO Sense)': [3, 3, 3, 5, 4, 4, 5], 'Raspberry Pi Zero 2 W + cámara': [3, 4, 1, 4, 3, 3, 5], 'Microcámara de acción (LiPo interna)': [5, 5, 2, 3, 2, 3, 1]}),
 'Computadora de vuelo': (
   ['periféricos y pines', 'determinismo', 'consumo', 'costo', 'ecosistema', 'herencia', 'tamaño'],
   [0.30, 0.15, 0.10, 0.10, 0.15, 0.10, 0.10],
   {'ESP32-C3 Super Mini (equipo)': [2, 3, 4, 5, 5, 4, 5], 'ESP32-S3 mini': [4, 3, 3, 4, 5, 4, 4], 'RP2040 (Pico/Zero)': [4, 5, 4, 5, 5, 4, 4], 'STM32F411 (Black Pill)': [5, 5, 3, 3, 4, 5, 3]}),
 'Actuador de liberación': (
   ['par disponible', 'masa', 'picos de corriente', 'robustez frente a M3 (choque sobre el eje)', 'costo', 'disponibilidad'],
   [0.20, 0.10, 0.15, 0.25, 0.10, 0.20],
   {'SG90 (equipo, engranajes de plástico)': [3, 5, 3, 2, 5, 5], 'MG90S (engranajes metálicos)': [3, 4, 3, 4, 4, 5], 'Solenoide de traba': [2, 3, 1, 4, 3, 3]}),
 'Sensor de rpm y de estado de las trabas': (
   ['compatibilidad eléctrica y funcional (3,3 V, orientación de los imanes)', 'robustez', 'masa', 'costo', 'rango de rpm', 'inmunidad a la luz'],
   [0.25, 0.20, 0.10, 0.15, 0.15, 0.15],
   {'Hall interruptor (DRV5032/DRV5033)': [5, 5, 5, 4, 5, 5], 'Hall latch DRV5013 (pide imanes alternados)': [4, 5, 5, 4, 5, 5], 'Hall A3144 (4,5 V, unipolar)': [3, 5, 5, 5, 5, 5], 'Reflectivo IR (TCRT5000)': [4, 3, 4, 5, 4, 2], 'Interruptor de lámina (reed)': [5, 3, 4, 5, 3, 5]}),
 'Detección de la separación del cohete (X3)': (
   ['fiabilidad de la detección', 'independencia de la interfaz del cohete', 'robustez al choque (S4, S5)', 'hardware y pines extra', 'costo', 'falsos positivos'],
   [0.30, 0.20, 0.15, 0.10, 0.10, 0.15],
   {'Luz (panel solar de E3)': [4, 5, 5, 5, 5, 3], 'Microinterruptor de separación': [3, 2, 2, 3, 5, 2], 'Aceleración (IMU: pulso y caída libre)': [4, 5, 5, 5, 5, 3], 'Luz y aceleración combinadas': [5, 5, 5, 5, 5, 5]}),
 'Memoria no volátil y tiempo (F1, F2, F3, F5)': (
   ['resistencia a escrituras', 'seguridad ante corte de energía', 'mantiene el tiempo de misión', 'pines y hardware', 'costo', 'masa'],
   [0.20, 0.25, 0.25, 0.10, 0.10, 0.10],
   {'FRAM I2C + RTC DS3231 con pila': [5, 5, 5, 4, 3, 4], 'FRAM I2C + hora UTC del GPS': [5, 5, 3, 5, 4, 5], 'Flash interna (NVS) + hora UTC del GPS': [3, 3, 2, 5, 5, 5], 'Solo tarjeta microSD': [4, 2, 1, 4, 5, 4]}),
 'Fuente de energía (E1, E2, E7, M4)': (
   ['autonomía de E7 con margen', 'riesgo de perder video (C6, C7)', 'cabe en el presupuesto de masa (S1)', 'cumple M4 y E2', 'costo', 'simplicidad'],
   [0.28, 0.20, 0.17, 0.10, 0.10, 0.15],
   {'1 celda 18650, todo encendido': [2, 5, 5, 5, 5, 5], '1 celda 18650, cámaras al despegue': [4, 2, 5, 5, 5, 3], '2 celdas 18650 en paralelo, todo encendido': [5, 5, 2, 4, 4, 4]}),
}
EXCL = {'Cámaras (C6, C7, SN6, SN7)': {'Microcámara de acción (LiPo interna)': 'E1: batería de polímero de litio'}}
out = {}
for k, (crit, w, cands) in S.items():
    w = np.array(w, float); w = w / w.sum()
    names = list(cands); M = np.array([cands[n] for n in names], float)
    ws = M @ w
    # TOPSIS
    V = M / np.linalg.norm(M, axis=0) * w
    ideal, anti = V.max(0), V.min(0)
    dp = np.linalg.norm(V - ideal, axis=1); dm = np.linalg.norm(V - anti, axis=1)
    top = dm / (dp + dm)
    # sensibilidad a los pesos: Dirichlet centrada en w (concentración 20)
    excl = [n in EXCL.get(k, {}) for n in names]
    Wr = rng.dirichlet(w * 20, 50000)
    P = Wr @ M.T
    P[:, excl] = -1.0                              # las excluidas por un requisito no ganan
    ganador = np.argmax(P, axis=1)
    prob = [float(np.mean(ganador == i)) for i in range(len(names))]
    # sensibilidad conjunta: además de los pesos, cada puntaje cambia en +-1 con probabilidad 0,25
    Np = len(Wr)
    paso = rng.choice([-1, 0, 1], size=(Np,) + M.shape, p=[0.125, 0.75, 0.125])
    Mp = np.clip(M[None] + paso, 1, 5)
    Pp = np.einsum('nj,nij->ni', Wr, Mp)
    Pp[:, excl] = -1.0
    gp = np.argmax(Pp, axis=1)
    prob_p = [float(np.mean(gp == i)) for i in range(len(names))]
    # peso del criterio con más influencia: cambio de ranking al subir 50 % cada peso
    cambios = []
    for j in range(len(w)):
        w2 = w.copy(); w2[j] *= 1.5; w2 /= w2.sum()
        cambios.append(names[int(np.argmax(np.where(excl, -1, M @ w2)))])
    out[k] = dict(criterios=crit, pesos=w.tolist(), candidatos=names, puntajes=M.tolist(), suma=ws.tolist(), topsis=top.tolist(),
                  prob_ganador=prob, prob_ganador_pun=prob_p, ganador=names[int(np.argmax(np.where(excl, -1, ws)))], excluidas=EXCL.get(k, {}),
                  cambia_con_peso=[crit[j] for j in range(len(w)) if cambios[j] != names[int(np.argmax(np.where(excl, -1, ws)))]])
json.dump(out, open(os.path.join(D, 'sensores_decision.json'), 'w'), indent=1, ensure_ascii=False)
for k, v in out.items():
    print('==', k)
    for n, s, t, p in zip(v['candidatos'], v['suma'], v['topsis'], v['prob_ganador']):
        print('   %-34s suma %.2f  topsis %.2f  P(gana) %.2f' % (n, s, t, p))
    print('   ganador:', v['ganador'], '| criterios cuyo aumento de peso cambia al ganador:', v['cambia_con_peso'])
