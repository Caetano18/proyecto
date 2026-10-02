#!/usr/bin/env python3
"""Presupuesto de enlace del CanSat a 915 MHz y 2,4 GHz.

Modelo de Friis en espacio libre con el diagrama de un dipolo de media onda vertical en
el CanSat y una antena directiva apuntada en tierra; cerca del suelo, modelo de dos rayos
con coeficiente de reflexión -1 (incidencia rasante). Datos de radio de las hojas de
datos (XBee-PRO 900HP y XBee 3 PRO); antenas y pérdidas son valores representativos.
Uso: python3 analysis/electronica_enlace.py
"""
import os
import numpy as np

C0 = 299_792_458.0
AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(AQUI, "data")

BANDAS = {
    #        f [Hz],  Pt [dBm], S [dBm], G tierra [dBi], L cable tierra [dB]
    "915": dict(f=915e6, Pt=24.0, S=-101.0, Gg=8.0, Lg=1.0),
    "2400": dict(f=2.44e9, Pt=19.0, S=-103.0, Gg=10.0, Lg=1.5),
}
L_CANSAT = 0.5     # dB, cable y conector a bordo
L_POL = 1.0        # dB, oscilación de +-20 grados entre polarizaciones lineales
L_CUERPO = 3.0     # dB, sombra del cuerpo, cables y palas de carbono (supuesto)
H_GS = 1.5         # m, altura de la antena de tierra
M_FADING = 10.0    # dB, margen de desvanecimiento exigido
H_SUELO = 0.3      # m, antena del CanSat ya aterrizado


def fspl(d, f):
    return 20 * np.log10(4 * np.pi * d * f / C0)


def g_dipolo(theta):
    """Ganancia [dBi] de un dipolo de media onda; theta medido desde su eje."""
    s = np.sin(theta)
    g = 1.64 * (np.cos(np.pi / 2 * np.cos(theta)) / np.maximum(s, 1e-6))**2
    return np.maximum(10 * np.log10(np.maximum(g, 1e-12)), -20.0)


def margen(x, h, b, dos_rayos=False):
    p = BANDAS[b]
    r = np.hypot(x, h - H_GS)
    theta = np.arctan2(x, h - H_GS)       # eje del CanSat vertical
    m = (p["Pt"] + g_dipolo(theta) + p["Gg"] - L_CANSAT - p["Lg"] - L_POL - L_CUERPO
         - fspl(r, p["f"]) - p["S"])
    if dos_rayos:
        k = 2 * np.pi * p["f"] / C0
        d1 = np.hypot(x, h - H_GS); d2 = np.hypot(x, h + H_GS)
        fac = np.abs(1 - (d1 / d2) * np.exp(-1j * k * (d2 - d1)))
        m = m + 20 * np.log10(np.maximum(fac, 1e-3))
    return m


def main():
    x = np.arange(10.0, 2505.0, 5.0)
    with open(os.path.join(DATA, "electronica_enlace.dat"), "w") as fo:
        fo.write("x m915a m2400a m915b m2400b\n")
        for xi in x:
            fo.write(f"{xi/1000:.3f} {margen(xi,560,'915'):.2f} {margen(xi,560,'2400'):.2f} "
                     f"{margen(xi,H_SUELO,'915',True):.2f} {margen(xi,H_SUELO,'2400',True):.2f}\n")
    for b, p in BANDAS.items():
        lam = C0 / p["f"]
        print(f"== {b} MHz: lambda = {lam*100:.1f} cm, dipolo = {lam/2*100:.1f} cm, "
              f"cuarto de onda = {lam/4*100:.1f} cm")
        for d in (1000.0, 2000.0):
            print(f"  FSPL {d/1000:.0f} km = {fspl(d, p['f']):.1f} dB; "
                  f"Fresnel r1 (punto medio) = {0.5*np.sqrt(lam*d):.1f} m")
            for h in (560.0,):
                xh = np.sqrt(max(d**2 - (h - H_GS)**2, 0))
                th = np.degrees(np.arctan2(xh, h - H_GS))
                print(f"  oblicua {d:.0f} m, h={h:.0f}: x={xh:.0f} m, theta={th:.0f} grados, "
                      f"G dipolo={g_dipolo(np.radians(th)):.2f} dBi, margen={margen(xh,h,b):.1f} dB")
        print(f"  punto de quiebre 4 h_t h_r / lambda con h_t=20 m: {4*20*H_GS/lam:.0f} m")
        for hh in (20.0, H_SUELO):
            mb = margen(x, hh, b, True)
            ok10 = x[mb >= M_FADING]; ok0 = x[mb >= 0]
            print(f"  h={hh} m: margen>=10 dB hasta {ok10.max() if ok10.size else 0:.0f} m, "
                  f">=0 dB hasta {ok0.max() if ok0.size else 0:.0f} m; a 1 km "
                  f"{margen(1000.,hh,b,True):.1f} dB, 2 km {margen(2000.,hh,b,True):.1f} dB")
        ma = margen(x, 560, b)
        print(f"  h=560 m: margen mínimo {ma.min():.1f} dB en x={x[ma.argmin()]:.0f} m; "
              f"a 2,5 km {ma[-1]:.1f} dB")
        # alcance en espacio libre con margen de 10 dB, antena en el máximo
        eirp = p["Pt"] + 2.15 + p["Gg"] - L_CANSAT - p["Lg"] - L_POL - L_CUERPO
        Lmax = eirp - p["S"] - M_FADING
        dmax = C0 / (4 * np.pi * p["f"]) * 10**(Lmax / 20)
        print(f"  pérdida admisible {Lmax:.1f} dB -> alcance en espacio libre {dmax/1000:.1f} km")
    # tasa de datos necesaria
    paquete = 200 * 10   # bits (200 caracteres con arranque y parada)
    print(f"telemetría: {paquete} bit/s a 1 Hz = {paquete/1000:.1f} kbit/s")


if __name__ == "__main__":
    main()
