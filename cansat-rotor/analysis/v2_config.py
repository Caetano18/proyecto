"""Configuración de diseño de referencia (fuente única para los scripts).

CANSAT_CFG=v2 (por defecto): anexo A v2 (S2 = Ø90 mm), drogue soltado antes de abrir el rotor
(etapa 2 con el rotor solo), R = 0,25 m.
CANSAT_CFG=v1: configuración anterior (Ø95, drogue atado, R = 0,20 m) para comparar.
"""
import os
import numpy as np

CFG = os.environ.get('CANSAT_CFG', 'v2')
RHO, NU, G = 1.225, 1.5e-5, 9.81

if CFG == 'v1':
    M1, M_DROGUE = 0.500, 0.0       # masa en la etapa 1 y masa que se suelta
    R, E = 0.200, 0.044
    D_ENV, D_CUERPO = 0.095, 0.088   # envolvente (S2) y cuerpo
    DROGUE_ATADO = True
    LB = 0.156
    MB = 0.0074
else:
    M1, M_DROGUE = 0.500, 0.010
    R, E = 0.250, 0.044
    D_ENV, D_CUERPO = 0.090, 0.083
    DROGUE_ATADO = False
    LB = R - E                       # 0,206 m
    MB = 0.0095                      # pala + portapala (escalada por largo)

M2 = M1 - M_DROGUE                   # masa en la etapa 2
D_DROGUE, CD_DROGUE, CD_CUERPO = 0.25, 0.8, 0.8
B_PALAS, CUERDA, THETA = 4, 0.045, -3.0
