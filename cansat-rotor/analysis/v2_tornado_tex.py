#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera figuras TikZ de tornado (barras horizontales) a partir de analysis/data/sens_tornado_*.dat
Salida: figuras/tornado_<nombre>.tex  (se incluyen con \\input{figuras/tornado_<nombre>}).
Altura: CANSAT_HLIB = altura de liberación del rotor [m] (por defecto 500, apogeo de 625 m). Con otro valor
(p. ej. 400) lee los datos de v2_sensibilidad.py con sufijo _H<H_lib> y escribe tornado_<nombre>_H<H_lib>.tex;
los tornados de t90 y z90 (arranque) no dependen de la altura y solo se rehacen en el caso base."""
import os
AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(AQUI, 'data'); FIG = os.path.join(AQUI, '..', 'figuras')
HLIB = float(os.environ.get('CANSAT_HLIB', '500'))      # altura de liberación del rotor [m]
SUF = '' if HLIB == 500.0 else '_H%g' % HLIB            # sufijo de las salidas del caso alternativo
ETQ = {'m2': r'masa de la etapa 2', 'R': r'radio $R$ (\textpm\,3\,mm)', 'rho': r'densidad del aire', 'dCR': r'modelo: $C_R$ (\textpm\,15\,\%)',
       'theta': r'paso $\theta$ (\ang{-4} a \ang{-2})', 'c': r'cuerda (40 a 50\,mm)', 'B': r'palas (3 a 5)', 'Cdc': r'$C_D$ del cuerpo',
       'm1': r'masa en etapa 1', 'Cdd': r'$C_D$ del drogue', 'Dd': r'diámetro del drogue', 'f': r'fracción a $V_1$ (disparo)', 'ts': r'transición $V_1\to V_2$ (2,5 a 5\,s)',
       'i_c3': 'MCU', 'i_sens': 'sensores', 'i_gps': 'GPS', 'i_lora': 'radio (LoRa)', 'i_sd': 'microSD', 'i_led': 'LED', 'i_cam': 'cámaras (c/u)',
       'i_servo': 'servos en reposo', 'eta_buck': r'rendimiento reductor', 'eta_boost': r'rendimiento elevador', 'frac_util': 'fracción útil de la celda',
       'cap': 'capacidad de la celda', 'f_cap_T': 'efecto de la temperatura',
       'Qf': r'rozamiento $Q_f$ (0,34 a 1,7\,mN.m)', 'V0': r'$V$ al abrir (10 a 16\,m/s)', 'Iz': r'inercia del rotor (\textpm\,30\,\%)',
       'polar': 'polar en pérdida (XFOIL o 2D)', 'Cdc': r'arrastre de apertura $C_{dc}$'}
ETQ['theta'] = r'paso $\theta$ (\ang{-4} a \ang{-2})'
ETQ['m2'] = r'masa de la etapa 2'


def tornado(nombre, archivo, titulo_x, nominal, cols=(1, 2), unidad='', cota=None, sort=True):
    filas = []
    for l in open(os.path.join(DATA, archivo)).read().strip().split('\n')[1:]:
        t = l.split()
        filas.append((t[0], float(t[cols[0]]), float(t[cols[1]])))
    if sort:
        filas.sort(key=lambda r: -abs(r[2] - r[1]))
    filas = filas[:9]
    lo = min(min(a, b) for _, a, b in filas); hi = max(max(a, b) for _, a, b in filas)
    pad = 0.08 * (hi - lo)
    lo -= pad; hi += pad
    W = 8.2; esc = W / (hi - lo)
    x = lambda v: (v - lo) * esc
    L = []
    L.append(r'\begin{tikzpicture}[font=\footnotesize]')
    n = len(filas)
    for i, (k, a, b) in enumerate(filas):
        y = -(i * 0.62)
        xa, xb = sorted([a, b])
        L.append(r'\fill[cfijo!70] (%.3f,%.3f) rectangle (%.3f,%.3f);' % (x(xa), y - 0.22, x(nominal) if xa < nominal else x(xa), y + 0.22))
        L.append(r'\fill[crot!80] (%.3f,%.3f) rectangle (%.3f,%.3f);' % (x(nominal) if xb > nominal else x(xb), y - 0.22, x(xb), y + 0.22))
        L.append(r'\node[anchor=east] at (-0.15,%.3f) {%s};' % (y, ETQ.get(k, k)))
        L.append(r'\node[anchor=east, font=\scriptsize] at (%.3f,%.3f) {%.2f};' % (x(xa) - 0.05, y, xa))
        L.append(r'\node[anchor=west, font=\scriptsize] at (%.3f,%.3f) {%.2f};' % (x(xb) + 0.05, y, xb))
    L.append(r'\draw[cfreno, dashed, line width=0.6pt] (%.3f,0.45) -- (%.3f,%.3f);' % (x(nominal), x(nominal), -(n - 1) * 0.62 - 0.45))
    if cota is not None:
        L.append(r'\draw[cgris, dotted, line width=0.8pt] (%.3f,0.45) -- (%.3f,%.3f) node[below, font=\scriptsize, cgris] {%s};' % (x(cota[0]), x(cota[0]), -(n - 1) * 0.62 - 0.45, cota[1]))
    L.append(r'\node[font=\footnotesize] at (%.3f,%.3f) {%s};' % (W / 2, -(n - 1) * 0.62 - 1.15, titulo_x))
    L.append(r'\end{tikzpicture}')
    open(os.path.join(FIG, 'tornado_%s%s.tex' % (nombre, SUF)), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    os.makedirs(FIG, exist_ok=True)
    tornado('V2_A1', 'sens_tornado_V2_A1.dat', r'$V_2$ [m/s]', 6.357, (1, 2), cota=(8.0, r'límite 8')) if False else None
    import json
    R = json.load(open(os.path.join(DATA, 'sens_resumen%s.json' % SUF)))
    tornado('V2_A1', 'sens_tornado_V2_A1%s.dat' % SUF, r'$V_2$ de régimen [m/s] (Arq.~1)', R['A_A1']['V0'])
    tornado('V2_A2', 'sens_tornado_V2_A2%s.dat' % SUF, r'$V_2$ de régimen [m/s] (Arq.~2)', R['A_A2']['V0'])
    tornado('Vg_A1', 'sens_tornado_Vg_A1%s.dat' % SUF, r'velocidad media global [m/s] (Arq.~1)', R['B_A1']['Vg0'], cota=(8.0, r'límite 8'))
    tornado('Vg_A2', 'sens_tornado_Vg_A2%s.dat' % SUF, r'velocidad media global [m/s] (Arq.~2)', R['B_A2']['Vg0'], cota=(8.0, r'límite 8'))
    if not SUF:      # el arranque (t90, z90) no depende de la altura; sus datos no llevan sufijo
        tornado('t90', 'sens_tornado_t90.dat', r'$t_{90}$ del arranque [s]', 1.552)
        tornado('z90', 'sens_tornado_z90.dat', r'caída hasta $t_{90}$ [m]', 21.66)
    tornado('E7', 'sens_tornado_E7%s.dat' % SUF, r'autonomía con todo encendido [h]', R['D']['h_todo_encendido'], cota=(2.0, r'E7: 2 h'))
