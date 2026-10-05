#!/usr/bin/env python3
"""Lista de materiales (BOM) del CanSat con costos ORIENTATIVOS y verificación de C9.

Los precios están en dólares estadounidenses (USD) como rangos de mercado minorista
típicos de componentes de hobby/electrónica, ya con un recargo de importación; NO son
cotizaciones. Se convierten a pesos argentinos (ARS) con un tipo de cambio supuesto
TC en [TC_LO, TC_HI] ARS/USD (parámetro a actualizar). Salidas:
  analysis/data/fabricacion_bom.dat       (renglones)
  analysis/data/fabricacion_costo_sub.dat (subtotales por subsistema, ARS)
  analysis/data/fabricacion_costo_tc.dat  (total vs tipo de cambio)
"""
import os
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TC_LO, TC_HI = 1300.0, 1700.0      # ARS/USD supuesto (2026), a actualizar
IMPREV = 0.30                       # imprevistos sobre el escenario alto
LIM = 1_000_000.0                   # C9

# (subsistema, item, cantidad, masa unitaria g, USD lo, USD hi por unidad)
bom = [
 ('R', 'Tejido de carbono 3K ~100-200 g/m2 (0,25 m2)', 1, 0.0, 10, 20),
 ('R', 'Cinta UD de carbono (1 m)', 1, 0.0, 5, 10),
 ('R', 'Epoxi de laminación (kit 250 g)', 1, 0.0, 12, 25),
 ('R', 'Varilla pultruida de carbono Ø2 (1 m)', 1, 0.0, 3, 6),
 ('R', 'Consumibles de vacío (bolsa, pelable, absorbente, cinta, desmoldante)', 1, 0.0, 15, 30),
 ('R', 'Rodamiento 688ZZ (2 de vuelo + 2 de repuesto)', 4, 1.0, 2, 4),
 ('R', 'Tubo de aluminio 6061 Ø8x5 (300 mm)', 1, 0.0, 3, 6),
 ('R', 'Tuerca M8x0,75 baja y arandelas', 2, 1.5, 1, 2),
 ('R', 'Pasador de acero Ø2 m6 (varilla plata) x8', 1, 0.0, 2, 4),
 ('R', 'Chapa de inox. 0,5 mm (100x100) y alambre de piano Ø1', 1, 0.0, 3, 6),
 ('R', 'Resorte de torsión 0,005 N m (x6)', 1, 0.0, 3, 8),
 ('R', 'Imán NdFeB Ø3x1 y sensor hall', 1, 0.0, 2, 4),
 ('R', 'Micro servo MG90S (1 + 1 repuesto)', 2, 13.4, 5, 10),
 ('R', 'Adhesivos: epoxi estructural, retención, cianoacrilato', 1, 0.0, 15, 30),
 ('E', 'Filamento PETG 1 kg (todas las piezas impresas)', 1, 0.0, 18, 30),
 ('E', 'Insertos de latón M2/M2,5 y tornillería', 1, 0.0, 6, 12),
 ('E', 'Lastre de acero y espuma de aterrizaje', 1, 0.0, 2, 5),
 ('D', 'Drogue: ripstop 0,3 m2, hilo, costura', 1, 0.0, 5, 12),
 ('D', 'Cuerda Dyneema Ø1,5 (3 m) y destorcedor de bolas', 1, 0.0, 6, 15),
 ('X', 'Microcontrolador (placa de desarrollo)', 1, 0.0, 8, 25),
 ('X', 'Radio XBee de la carga (900 MHz o XBee 3)', 1, 0.0, 45, 90),
 ('X', 'Altímetro MS5611, IMU, INA219, FRAM, RTC', 1, 0.0, 15, 35),
 ('X', 'Receptor GPS con antena', 1, 0.0, 10, 30),
 ('X', 'Cámaras con grabación (cenit y nadir) y tarjetas microSD', 2, 0.0, 20, 50),
 ('X', 'Celda 18650, protección, regulador, interruptores', 1, 0.0, 10, 25),
 ('X', 'Baliza sonora con pila propia', 1, 0.0, 3, 8),
 ('X', 'Placas de circuito (fabricación, 3 placas) y conectores', 1, 0.0, 15, 40),
 ('X', 'Paneles solares pequeños (2)', 1, 0.0, 4, 10),
]
names = {'R': 'Rotor y traba', 'E': 'Estructura impresa y fijaciones',
         'D': 'Drogue y cuerda', 'X': 'Electrónica y cámaras'}

rows = []
sub = {k: [0.0, 0.0] for k in names}
for s, it, q, m, lo, hi in bom:
    a_lo, a_hi = q*lo*TC_LO, q*hi*TC_HI
    sub[s][0] += a_lo; sub[s][1] += a_hi
    rows.append((s, it, q, lo, hi, a_lo, a_hi))
tot_lo = sum(v[0] for v in sub.values()); tot_hi = sum(v[1] for v in sub.values())
usd_lo = sum(q*lo for _, _, q, _, lo, _ in bom); usd_hi = sum(q*hi for _, _, q, _, _, hi in bom)
for s, it, q, lo, hi, a, b in rows:
    print(f'{s} {q:2d} {it[:60]:60s} {q*lo:5.0f}-{q*hi:5.0f} USD  {a/1e3:6.1f}-{b/1e3:6.1f} kARS')
for k, v in sub.items():
    print(f'{names[k]:35s} {v[0]/1e3:7.1f} - {v[1]/1e3:7.1f} kARS')
print(f'TOTAL USD {usd_lo:.0f}-{usd_hi:.0f};  ARS {tot_lo:,.0f} - {tot_hi:,.0f};'
      f'  alto+{100*IMPREV:.0f}% = {tot_hi*(1+IMPREV):,.0f}')
tc_break = LIM/(usd_hi*(1+IMPREV))
tc_break_nom = LIM/(0.5*(usd_lo+usd_hi))
print(f'TC que hace alto+imprev = 1e6: {tc_break:.0f} ARS/USD; medio sin imprev: {tc_break_nom:.0f}')

with open(os.path.join(D, 'fabricacion_costo_sub.dat'), 'w') as f:
    f.write('idx lo hi\n')
    for i, k in enumerate(['R', 'E', 'D', 'X']):
        f.write(f'{i} {sub[k][0]/1e3:.1f} {sub[k][1]/1e3:.1f}\n')
with open(os.path.join(D, 'fabricacion_costo_tc.dat'), 'w') as f:
    f.write('tc lo mid hi himp\n')
    for tc in np.linspace(800, 2400, 33):
        f.write(f'{tc:.0f} {usd_lo*tc/1e3:.1f} {0.5*(usd_lo+usd_hi)*tc/1e3:.1f} '
                f'{usd_hi*tc/1e3:.1f} {usd_hi*tc*(1+IMPREV)/1e3:.1f}\n')
with open(os.path.join(D, 'fabricacion_bom.dat'), 'w') as f:
    f.write('sub q usd_lo usd_hi ars_lo ars_hi\n')
    for s, it, q, lo, hi, a, b in rows:
        f.write(f'{s} {q} {q*lo} {q*hi} {a:.0f} {b:.0f}\n')

# ---------------------------------------------------------------- masa de la cabeza del rotor
# Estimaciones geométricas (densidades nominales); no son pesadas.
rho_al, rho_st = 2.70e-3, 7.85e-3          # g/mm3
eje = np.pi/4*(8**2-5**2)*67*rho_al
nut = lambda rho: (0.866*13**2 - np.pi/4*8**2)*4*rho   # tuerca baja M8, entre caras 13, alto 4
mrot = {
 'Palas con portapala, varilla y pestaña (4)': 4*8.2,
 'Cubo con almohadillas, imán y contrapeso': 12.0,
 'Rodamientos 688ZZ (2)': 2*3.5,
 'Eje Al 6061 Ø8x5x67': eje,
 'Tuerca de retención M8x0,75 (acero)': nut(rho_st),
 'Contratuerca y tuerca de copa (aluminio)': 2*nut(rho_al),
 'Collar, separador y arandela': 1.5,
 'Pasadores Ø2 (4), resortes (4), sensor hall': 4*0.27 + 4*0.12 + 0.3,
}
tot = 0
for k, v in mrot.items():
    tot += v; print(f'{k:45s} {v:6.2f} g')
print(f'Cabeza del rotor + palas: {tot:.1f} g  (tab:masa: 30 + 24 = 54 g) -> diferencia {tot-54:+.1f} g')
with open(os.path.join(D, 'fabricacion_masa_rotor.dat'), 'w') as f:
    f.write('item masa_g\n')
    for i, (k, v) in enumerate(mrot.items()):
        f.write(f'{i} {v:.2f}\n')
