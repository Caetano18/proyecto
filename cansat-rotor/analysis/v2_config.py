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

# --- inercias del rotor (cap. 15 de v1: Ib = 4,35e-5 con MB = 7,4 g y LB = 0,156) escaladas por largo y masa
IB_REL = 4.35e-5 / (0.0074 * 0.156**2)       # Ib / (MB LB^2) de v1
XG_REL = 0.070 / 0.156                       # x_g / LB de v1
IB = IB_REL * MB * LB**2                     # inercia de batimiento de una pala respecto de la bisagra
XG = XG_REL * LB                             # centro de masa de la pala medido desde la bisagra
SB = MB * XG                                 # momento estático
IHUB = 5.0e-4 - 4 * (4.35e-5 + 2 * 0.0074 * 0.070 * 0.044 + 0.0074 * 0.044**2)   # cubo y herrajes (v1)


def Iz(beta, B=B_PALAS):
    """Inercia polar del rotor con las palas abiertas a la conicidad beta [rad]."""
    return IHUB + B * (IB * np.cos(beta)**2 + 2 * SB * E * np.cos(beta) + MB * E**2)
