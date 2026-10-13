# =============================================================================
#  ENTRADAS — editá SOLO este archivo y ejecutá:   python main.py
#  (o copialo con otro nombre y ejecutá:           python main.py mi_archivo.py)
# =============================================================================
#  El lazo es   L(s) = C(s) · G(s) · H(s) · e^(-RETARDO·s)   con realimentación negativa.
#  G = planta  |  C = compensador  |  H = sensor (None = realimentación unitaria).
#  Frecuencias en rad/s, tiempos en s, ángulos en grados.
# =============================================================================

NOMBRE = "Parcial 1: K/(s³+10s²+5s)"

# -----------------------------------------------------------------------------
#  1) PLANTA G(s) — elegí UNA forma (las demás déjalas en None)
# -----------------------------------------------------------------------------
# (a) Expresión de texto con 's' y 'K'  (se pueden usar ** o ^ para potencias):
EXPRESION = "K/(s**3 + 10*s**2 + 5*s)"

# (b) Coeficientes (potencias decrecientes de s). G = K · NUM/DEN :
NUM = None            # ej: [1]
DEN = None            # ej: [1, 10, 5, 0]

# (c) Polos y ceros (negativos = semiplano izquierdo). forma: "monica" -> K·Π(s-z)/Π(s-p)
#     o "bode" -> K·Π(1-s/z)/Π(1-s/p) (K = ganancia de Bode; un polo en 0 es un integrador):
POLOS_CEROS = None    # ej: dict(polos=[0, -1, -2], ceros=[], K=2, forma="monica")

# (d) Factores leídos del diagrama de Bode (forma de constantes de tiempo).
#     K_dB puede ser una LISTA que se suma (curvas G1, G3, G4 del enunciado). 'polos'/'ceros'
#     son frecuencias de quiebre; pares_polos = [(wn, zeta)]; *_spd = semiplano derecho:
FACTORES_BODE = None  # ej: dict(K_dB=[34, -2.41, -40], integradores=1, polos=[1.3, 100])

# (e) Asíntotas del Bode: un punto sobre la asíntota inicial, su pendiente y los quiebres
#     (frecuencia, cambio de pendiente [, zeta]):
ASINTOTAS_BODE = None # ej: dict(w_ref=0.1, mag_dB=20, pendiente_inicial=-20, quiebres=[(1.3, -20), (100, -20)])

K = 100.0             # ganancia. En (a) es la variable 'K' de la expresión; en las demás multiplica a G.
RETARDO = 0.0         # retardo puro [s] (exacto en frecuencia; Padé en el tiempo)
SENSOR = None         # H(s): None = unitaria. ej: "1/(0.1*s+1)"  o  ([1], [0.1, 1])

# -----------------------------------------------------------------------------
#  2) COMPENSADOR PROPIO (opcional): si ya tenés un Gc(s), analizalo acá.
#     Texto con 's', o dict(num=[..], den=[..]), o dict(polos=[..], ceros=[..], K=..).
# -----------------------------------------------------------------------------
COMPENSADOR = None    # ej: "50*(20*s+1)/(800*s+1)"

# -----------------------------------------------------------------------------
#  3) ESPECIFICACIONES (None = no se exige)
# -----------------------------------------------------------------------------
ESPECS = dict(
    Kp=None,          # constante de error de posición (planta tipo 0)
    Kv=20,            # constante de error de velocidad [1/s] (planta tipo 1)
    Ka=None,          # constante de error de aceleración (tipo 2)
    MF=50,            # margen de fase mínimo [°]
    MG=5,             # margen de ganancia mínimo, en VECES (ej: 5)      ┐ usar uno u otro;
    MG_dB=None,       # margen de ganancia mínimo, en dB (ej: 14)        ┘ si da los dos, se exigen ambos
    Mp=None,          # sobreimpulso máximo [%]
    ts=None,          # tiempo de establecimiento máximo (2 %) [s]
    wc_min=None,      # frecuencia de cruce mínima [rad/s]
    BW_min=None,      # ancho de banda mínimo [rad/s]
    Mr_dB=None,       # pico de resonancia máximo [dB]
)

# -----------------------------------------------------------------------------
#  4) DISEÑO DEL COMPENSADOR
#     None -> solo analiza | "auto" -> prueba solo-ganancia, adelanto, atraso y atraso-adelanto y recomienda
#     o un nombre / lista: "adelanto", "atraso", "atraso_adelanto", "PI", "PID_ZN", "solo_ganancia"
#     ej: DISENO = ["atraso", "atraso_adelanto"]
# -----------------------------------------------------------------------------
DISENO = "auto"

PARAMS_DISENO = dict(
    delta_adelanto=5,        # reserva inicial de fase del adelanto [°] (se itera hasta cumplir)
    delta_max=30,            # reserva máxima que se prueba [°]
    delta_atraso=6,          # reserva de fase del atraso [°]
    razon_cero_atraso=10,    # cero del atraso en wc'/razón (10 = una década antes)
    wc_nuevo=None,           # fuerza el nuevo cruce del atraso / atraso-adelanto [rad/s] (ej: 0.5)
    etapas_adelanto="auto",  # 1, 2 o "auto" (2 etapas si hace falta más de 60° de fase)
    redondear=True,          # redondear los parámetros del compensador a pocas cifras
    cifras=2,                # cifras significativas del redondeo (atraso); el adelanto usa cifras+1
    N_derivativo=10,         # filtro de la derivada en el PID
)

# -----------------------------------------------------------------------------
#  5) QUÉ CALCULAR Y QUÉ GRAFICAR (True / False)
# -----------------------------------------------------------------------------
SECCIONES = dict(sistema=True, estabilidad=True, frecuencia=True, temporal=True, compensacion=True)
GRAFICOS = dict(descomposicion=True, bode=True, nyquist=True, nichols=True, temporal=True, polos=True,
                estabilidad_K=True, sensibilidad=True, compensacion=True, comparacion=True)

CASOS_K = None        # lista de K a analizar en la sección de estabilidad (None = automático). ej: [10, 30, 50, 100, -20]

# -----------------------------------------------------------------------------
#  6) OPCIONES
# -----------------------------------------------------------------------------
W_MIN = None          # rango de frecuencias [rad/s]; None = automático según polos y ceros
W_MAX = None
N_PUNTOS = 4000
T_FINAL = None        # duración de la simulación [s]; None = automática
ORDEN_PADE = 8        # orden de la aproximación de Padé del retardo (solo dominio del tiempo)
MOSTRAR = True        # abrir ventanas con los gráficos
CARPETA_SALIDA = "salidas"
FORMATOS = ("png",)   # ej: ("png", "pdf")
DPI = 140
EXPORTAR_DAT = False  # True: escribe también archivos .dat (para pgfplots/LaTeX) y un resumen.csv
