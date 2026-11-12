"""Parametros de diseno del CanSat ala delta (unidades: mm, g, MPa, N).

Sistema de coordenadas del vehiculo:
  x : eje del cuerpo, de la nariz (x=0) a la cola (x=200)
  y : envergadura (derecha positivo)
  z : hacia arriba
Todo el resto del proyecto (CAD, FEA, planos, PDR) lee de este archivo.
"""
import math

# ----------------------------------------------------------------- equipo
EQUIPO = "Equipo CanSat Universitario Argentina"
TEMPORADA = "2026/2027"
PRESENTADOR = "Subsistema mecánico"
REV = "A"
FECHA = "12/11/2026"

# -------------------------------------------------------------- envolvente
# Requisitos del Apendice A (CanSat Argentina Universitario - CONAE)
ENV_D = 90.0          # S2: diametro del CanSat
ENV_L = (200.0, 250.0)  # S3: largo total, incluidos los sistemas de descenso
M_TOT = 500.0         # S1: masa combinada CanSat + contenedor [g]
M_TOL = 10.0
T_WALL_MIN = 2.0      # S6: pared exterior impresa en 3D
G0 = 9.80665          # m/s2

# ------------------------------------------------------------- contenedor
CT_RO = ENV_D / 2     # 45
CT_T = 2.0            # pared (S6)
CT_RI = CT_RO - CT_T  # 43
CT_X = (-2.0, 240.0)  # borde inferior (abierto) y borde superior
CT_TOP = (211.0, 213.5)   # placa de la tapa estructural (PA12-CF nervada)
CT_CAP_H = 10.0       # altura total de la tapa (placa + nervios + faldon)
CT_CAP_SKIRT = 2.5    # espesor del faldon que pega contra el tubo
CT_CAP_RIB = 2.5      # espesor de los 6 nervios radiales
CT_CAP_BOSS = 11.5    # radio exterior del cubo central (donde nacen los nervios)
CT_CAP_FLOOR = 4.0    # espesor del fondo del cubo (asiento del aislador)
KEY_D = 5.0           # eje de la llave de bayoneta
KEY_HOLE = 6.0        # pasaje del eje en C4 y en la tapa (0,5 mm de huelgo radial)
WASH_D, WASH_T = 16.0, 1.5      # arandelas / plato de apoyo (inox)
ISO_T = 3.0           # anillo elastomerico (aislador axial)
CT_RIB_ANG = (30.0, 90.0, 150.0, 210.0, 270.0, 330.0)
CT_BRIDA_ANG = (90.0, 210.0, 330.0)   # nervios que llevan el anclaje de la brida
R_BRIDA = 33.0        # radio de los anclajes de la brida
CT_LEN = CT_X[1] - CT_X[0]

# ------------------------------------------------------- planeador: estructura
L_G = 207.0           # largo del planeador
RB = 42.0             # radio de cuadernas (1 mm de huelgo: patines de guia)
T_END = 8.0
T_MID = 4.0
X_C1 = (0.0, 8.0)
X_C2 = (60.0, 64.0)
X_C3 = (138.0, 142.0)
X_C4 = (L_G - T_END, L_G)
WEB_T = 1.6           # alma de C1 / C4
RIM_T = 2.2           # aro perimetral de C1 / C4
RIB_T = 2.8           # nervios de C1 / C4

# largueros: mismo tubo de carbono que el borde de ataque (un solo material de compra)
LON_DO, LON_DI = 5.0, 3.5
LON_Y, LON_Z = 20.5, 26.0
LON_X = (3.0, L_G - 3.0)
BOSS_D = 9.5

# paneles de G10
Y_PANEL = 27.5        # plano medio del panel lateral
T_PANEL = 0.5
T_COVER = 0.5         # tapa superior (lleva las celdas solares)
T_TRAY = 0.8
Z_TRAY = (-5.0, -4.2)
Y_BOX = Y_PANEL - T_PANEL / 2      # 27.25 semiancho interior de la caja
Y_OUT = Y_PANEL + T_PANEL / 2      # 27.75 cara exterior del panel
Z_BOX = 31.0                       # semialto de la caja
Z_BOOM = 36.5                      # eje del botalon de cola (sobre la tapa)

# cerrojo de bayoneta (C4 - tapa del contenedor) y patines de guia
LATCH_D = 6.0
PAD_ANG = 14.0        # grados de arco de cada patin
PAD_POS = (45.0, 135.0, 225.0, 315.0)

# ------------------------------------------------------------------- ala
Y_PIV = 34.0          # linea de pivotes A y B
X_A = 4.2             # pivote de apice (nariz), plano z = 0
X_B = 202.8           # pivote del tirante (cola), plano z = Z_TE
Z_TE = -7.0
D_AB = X_B - X_A                      # 198.6 mm: cuerda de raiz de la nota aerodinamica
L_LE = D_AB * math.sqrt(2.0)          # 280.9 mm entre pernos A y T
L_SEG = L_LE / 2.0                    # 140.4 mm: cada tramo del borde de ataque
L_TE = D_AB                           # 198.6 mm tirante
SWEEP = 45.0
LE_DO, LE_DI = 5.0, 3.5               # varilla de borde de ataque
TE_DO, TE_DI = 3.0, 2.0               # tirante de borde de fuga
RR_DO, RR_DI = 3.0, 2.0               # varilla de raiz
Y_ROOT = 29.5
SLV_DO, SLV_DI, SLV_L = 8.0, 5.1, 32.0  # manguito de traba (Al 7075)
FOLD_OFF = 5.4                        # separacion entre tramos plegados

# puntos caracteristicos (ala derecha, desplegada)
P_A = (X_A, Y_PIV, 0.0)
P_T = (X_B, Y_PIV + D_AB, 0.0)
P_J = ((P_A[0] + P_T[0]) / 2, (P_A[1] + P_T[1]) / 2, 0.0)
P_B = (X_B, Y_PIV, Z_TE)
SEMI_SPAN = Y_PIV + D_AB              # 232.6 mm
SPAN = 2 * SEMI_SPAN                  # 465.2 mm
S_TRI = 2 * 0.5 * D_AB ** 2 / 100.0                       # cm2, dos triangulos (nota: 394)
S_WING = S_TRI + 2 * (Y_PIV - Y_ROOT) * D_AB / 100.0      # cm2 de tela, con la franja de raiz

# valores de la nota aerodinamica del equipo (ala de membrana)
NOTA = dict(c=198.6, L=280.9, S=394.0, AR=4.0, p_vuelo=122.0, p_choque=367.0,
            m_panza=0.06, T_vuelo=51.0, T_choque=152.0, sigma_LE=73.0,
            flecha_LE=4.9, R_punta=6.92, N_tirante=9.79, M_apice=680.0,
            M_medio=422.0, w=5.0, V=12.7, masa_ala=29.0, masa_cola=30.0)

# ------------------------------------------------------------- materiales
# E en MPa, rho en g/cm3, resistencias en MPa.  Valores tipicos de hoja de
# datos; los de piezas impresas hay que confirmarlos con probetas del lote.
MAT = {
    "CFRP": dict(nombre="Carbono pultruido UD (tubo)", rho=1.60, E=130e3, nu=0.28,
                 E2=8.0e3, G12=4.5e3, G23=2.9e3, nu23=0.40,
                 Sut=1500.0, Suc=900.0, Sflex=600.0, FS=1.5),
    "G10": dict(nombre="G10 / FR-4 (laminado vidrio-epoxi)", rho=1.85, E=22e3, nu=0.15,
                Sut=280.0, Sflex=380.0, FS=1.5),
    "PA12CF": dict(nombre="PA12-CF impreso (FDM, 100 %)", rho=1.06, E=3.5e3, nu=0.38,
                   Sut=65.0, Sut_z=35.0, FS=2.0),
    "PETG": dict(nombre="PETG impreso", rho=1.27, E=2.0e3, nu=0.38, Sut=45.0, Sut_z=25.0, FS=2.0),
    "PLA": dict(nombre="PLA+ impreso", rho=1.24, E=3.3e3, nu=0.36, Sut=55.0, Sut_z=28.0, FS=2.0),
    "AL6061": dict(nombre="Aluminio 6061-T6", rho=2.70, E=68.9e3, nu=0.33, Sy=276.0, Sut=310.0, FS=1.25),
    "AL7075": dict(nombre="Aluminio 7075-T6", rho=2.81, E=71.7e3, nu=0.33, Sy=503.0, Sut=572.0, FS=1.25),
    "A2-70": dict(nombre="Acero inox A2-70", rho=7.90, E=193e3, nu=0.29, Sy=450.0, Sut=700.0, FS=1.25),
    "FR4": dict(nombre="PCB FR-4 1,6 mm", rho=1.85, E=22e3, nu=0.15, Sut=280.0, FS=1.5),
    "EPOXI": dict(nombre="Adhesivo epoxi estructural", rho=1.10, E=2.0e3, nu=0.38, tau=18.0, FS=2.0),
    "LWPLA": dict(nombre="LW-PLA espumado impreso (contenedor)", rho=0.65, E=1.2e3, nu=0.35,
                  Sut=14.0, Sut_z=8.0, FS=2.0),
    "ASALW": dict(nombre="ASA-LW espumado impreso", rho=0.60, E=0.97e3, nu=0.35, Sut=9.0, Sut_z=6.0, FS=2.0),
    "PC": dict(nombre="Policarbonato en lamina 0,25 mm", rho=1.20, E=2.3e3, nu=0.37, Sut=60.0, FS=1.5),
    "RIPSTOP": dict(nombre="Nailon ripstop 40 g/m2", rho_a=40.0, T_rot=4000.0),
    # elastomero de los aisladores (caucho butilo / poliuretano viscoelastico, 55 Shore A)
    "ELAST": dict(nombre="Elastomero 55 Shore A (butilo)", rho=1.20, E=3.0, G=1.0, eta=0.30, eps_adm=0.20),
    "PTFE": dict(nombre="PTFE", rho=2.2, E=500.0, nu=0.4),
}

# --------------------------------------------- masas no estructurales [g]
# Asignaciones de los demas subsistemas (a confirmar por cada responsable).
# El lastre de centrado absorbe el resto hasta M_TOT (caso mas desfavorable).
M_EQ = dict(
    bateria=46.0,          # 1 celda 18650 Li-ion (E1/E2: envase metalico)
    porta_bateria=5.0,
    pcb_principal=25.0,    # placa 64 x 50 con componentes
    pcb_radio=20.0,        # radio + GNSS, 46 x 40
    servo_lib=9.0,         # servo del cerrojo de bayoneta
    servo_cola=9.0,
    cola=21.0,             # botalon + cola en V (nota de cola: 30 g con servo)
    ala_por_lado=14.5,     # nota de membrana: 29 g las dos alas
    camaras=16.0,          # 2 camaras (cenit y nadir, C6/C7)
    baliza=8.0,            # baliza + pila boton (C8, E8)
    solar=6.0,             # celdas solares sobre la tapa (E3)
    cableado_tornillos=18.0,
    cubierta_inf=3.0,      # lamina de PC inferior
    paracaidas=15.0,       # paracaidas de 15 m/s plegado (va en el contenedor)
    brida_herrajes=5.0,    # brida de 3 puntos, eslabon giratorio
)

# ------------------------------------------------------ ambiente de cargas
N_VIB = 15.0          # g, amplitud senoidal / cuasi-estatica
N_SHOCK = 30.0        # g, pico de semiseno
ZETA = 0.02           # amortiguamiento estructural de base (Q = 25); los aisladores suman por energia modal
F_SWEEP = (5.0, 2000.0)
TAU_SHOCK = 0.011     # s, duracion nominal del semiseno
