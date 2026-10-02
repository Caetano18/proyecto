#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AMFE (análisis de modos de falla y efectos) del sistema de descenso.

- Calcula NPR = S·O·D antes y después de las acciones.
- La ocurrencia tras las acciones (O') de los modos que corresponden a un evento
  básico del árbol de fallas se deriva de la probabilidad usada en el árbol, con
  la escala de ocurrencia del capítulo; así el AMFE y el árbol son coherentes.
- Escribe las filas LaTeX del AMFE (longtable) en el archivo indicado como
  argumento y un resumen numérico en analysis/data/confiabilidad_amfe.dat.

Valores: estimaciones del equipo antes de los ensayos.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from confiabilidad_fta import EB  # noqa: E402  (probabilidades del árbol)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Escala de ocurrencia: límite superior de probabilidad por vuelo para O = 1..10
LIM_O = [1e-4, 5e-4, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 0.1, 0.3, 1.0]


def O_de_p(p):
    for i, lim in enumerate(LIM_O):
        if p <= lim * (1 + 1e-9):
            return i + 1
    return 10


# (id, grupo, componente, modo y causa, efecto, S, O, D, acción, S', O', D', evento)
# O' = None -> se toma de la probabilidad del evento del árbol.
M = [
 # ---------------- Electrónica y software
 ("M1", "E", "Barómetro", "picos o deriva de presión (eyección, viento, sol)",
  "falso apogeo o \\SI{80}{\\percent} mal calculado", 9, 5, 5,
  "Kalman de 2 estados; bloqueo de \\SI{1}{s} tras la eyección; espuma en el puerto; HIL con registros reales",
  9, None, 3, "x18"),
 ("M2", "E", "Barómetro", "sin datos (bus, soldadura, sensor dañado)",
  "sin liberación por altitud", 9, 5, 3,
  "respaldo por tiempo con apogeo medido por la IMU; lectura verificada en \\texttt{LAUNCH\\_PAD}",
  6, None, 2, "x4"),
 ("M3", "E", "Microcontrolador", "reinicio en vuelo (caída de tensión por el servo, choque)",
  "pierde el estado: no libera o repite la secuencia", 9, 6, 5,
  "FRAM con estado, $h_{\\max}$ y traba; watchdog; servo con regulador propio; reinicio forzado en HIL",
  9, None, 3, "x2"),
 ("M4", "E", "Firmware", "error de lógica (umbral, unidades, signo de $v_z$)",
  "no libera o libera fuera de tiempo", 9, 6, 5,
  "HIL con $\\ge20$ perfiles con ruido y fallas; revisión cruzada; parámetros versionados",
  9, None, 3, "x3"),
 ("M5", "E", "Firmware", "estado residual de un ensayo en la FRAM",
  "arranca en un estado erróneo", 9, 5, 4,
  "\\texttt{CAL} reinicia estado y FRAM; la lista exige \\texttt{LAUNCH\\_PAD} y traba en 0",
  9, 1, 1, None),
 ("M6", "E", "Respaldo por tiempo", "no se activa (usa el barómetro averiado; GPS sin fijación)",
  "la redundancia es solo aparente", 6, 7, 6,
  "apogeo por choque de eyección y caída medidos por la IMU; E6 sin barómetro",
  6, None, 2, "x5"),
 ("M7", "E", "Batería 18650", "desconexión momentánea por choque (portapilas de resorte)",
  "reinicio o apagado en vuelo", 9, 5, 4,
  "lengüetas soldadas y brida (\\Req{M4}); E5 con registro de tensión",
  9, None, 2, "x1"),
 ("M8", "E", "Batería 18650", "descarga antes de liberar (\\SI{2}{h} en el cohete)",
  "sin orden de liberación ni telemetría", 9, 4, 3,
  "margen de energía $\\times2$; carga $\\ge\\SI{4.15}{V}$ en la lista; cámaras desde \\texttt{ASCENT}",
  9, 2, 1, None),
 ("M9", "E", "Regulador y cableado", "cortocircuito o conector flojo",
  "pérdida de toda la electrónica", 9, 4, 4,
  "conectores con traba; termocontraíble; prueba de tirón; inspección",
  9, None, 3, "x1"),
 ("M10", "E", "Sensor hall", "no detecta el imán (distancia $>\\SI{3}{mm}$, imán suelto)",
  "no confirma el giro; reintentos innecesarios", 5, 5, 3,
  "distancia con galga; confirmación por $|v_z|<\\SI{10}{m/s}$",
  5, 2, 2, None),
 ("M11", "E", "Radio", "pérdida del enlace",
  "telemetría incompleta (\\Req{C5}); sin comando manual", 7, 5, 4,
  "ensayo de alcance a \\SI{1.5}{km}; registro en SD",
  7, 4, 3, None),
 # ---------------- Traba
 ("M12", "T", "Servo MG90S", "no gira (motor, engranaje roto, cable cortado)",
  "el rotor no se despliega", 9, 5, 3,
  "engranajes metálicos; 20 ciclos en E1 con medición de corriente",
  9, None, 2, "x7"),
 ("M13", "T", "Servo y anillo", "atasco transitorio (fricción, frío, baja tensión)",
  "liberación demorada o fallida", 9, 7, 4,
  "margen de par $\\ge3$; holgura \\SI{0.3}{mm}; 2 reintentos",
  9, None, 3, "x8"),
 ("M14", "T", "Anillo de traba", "deformación por calor o fluencia (PETG al sol)",
  "atasco permanente", 9, 4, 5,
  "anillo de PA12 o aluminio; liberación a \\SI{50}{\\celsius}; transporte a la sombra",
  9, None, 3, "x9"),
 ("M15", "T", "Anillo de traba", "giro por choque o vibración",
  "liberación en el ascenso o dentro del cohete", 10, 3, 5,
  "dientes autorretenidos; par de retención del servo; E5 con la traba verificada",
  10, 1, 2, None),
 ("M16", "T", "Pestaña de acero", "doblada (manipulación, choque)",
  "no engancha (palas sueltas) o no suelta", 9, 4, 3,
  "gálibo pasa/no pasa de la pestaña; inspección en la lista",
  9, None, 2, "x9"),
 # ---------------- Rotor
 ("M17", "R", "Pala", "retenida contra el cuerpo (adherencia, roce)",
  "no abre o abre asimétrica", 9, 4, 4,
  "resorte de apertura; holgura $\\ge\\SI{1}{mm}$; apertura verificada en la lista",
  9, None, 2, "x10"),
 ("M18", "R", "Pala", "fisura o delaminación (golpe, aterrizaje previo)",
  "rotura en vuelo", 9, 4, 5,
  "inspección visual y por golpeteo; no reutilizar tras un impacto duro",
  9, None, 3, "x14"),
 ("M19", "R", "Pala", "curvatura fuera de \\SI{7 \\pm 1}{\\percent}",
  "rpm y $\\CR$ distintos; desbalance", 6, 5, 4,
  "molde de curvado; gálibo de flecha (ec.~\\ref{eq:flecha}); seguimiento de puntas en E2",
  6, 3, 2, None),
 ("M20", "R", "Pala y portapala", "desbalance de masa $>\\SI{0.1}{g}$",
  "vibración, video degradado", 5, 5, 2,
  "balanceo a $\\pm\\SI{0.1}{g}$; palas numeradas por posición",
  5, 2, 2, None),
 ("M21", "R", "Portapala", "paso fuera de rango (montaje invertido, impresión)",
  "no arranca ($\\theta\\ge0$)", 9, 4, 3,
  "llave de orientación; gálibo de paso; E2 con el conjunto de vuelo",
  9, None, 2, "x11"),
 ("M22", "R", "Portapala", "fisura en la raíz (capas mal orientadas)",
  "pérdida de una pala", 9, 4, 4,
  "relleno \\SI{100}{\\percent}, capas según la carga; prueba a \\SI{40}{N} ($3\\times$ la centrífuga)",
  9, None, 3, "x14"),
 ("M23", "R", "Pasador de bisagra", "se sale (sin retención)",
  "pérdida de una pala", 9, 3, 3,
  "anillo elástico o pasador remachado; inspección",
  9, None, 2, "x15"),
 ("M24", "R", "Tope de batimiento", "rotura en el arranque",
  "batimiento excesivo; toca la cuerda", 7, 3, 4,
  "$3\\times$ el momento de arranque; inspección tras E2",
  7, 2, 3, None),
 ("M25", "R", "Resorte de apertura", "perdido o sin fuerza",
  "apertura más lenta; depende del flujo", 5, 3, 2,
  "inspección; E2 verifica la apertura sin resorte",
  5, 2, 2, None),
 ("M26", "R", "Rodamientos 688ZZ", "fricción alta (suciedad, tuerca muy apretada)",
  "arranque lento o nulo", 9, 4, 3,
  "par de apriete definido; giro libre $\\ge\\SI{5}{s}$ en la lista",
  9, None, 2, "x12"),
 ("M27", "R", "Tuerca M8$\\times$0,75", "se afloja por vibración",
  "el cubo sale: pérdida del rotor", 10, 3, 4,
  "tuerca autoblocante, fijador y marca testigo",
  10, None, 2, "x16"),
 ("M28", "R", "Eje hueco", "rebaba o canto vivo en la salida",
  "corta la cuerda del drogue", 8, 3, 4,
  "chaflán y pulido; inspección pasando un hilo",
  8, 1, 2, None),
 # ---------------- Drogue y cuerda
 ("M29", "D", "Drogue", "no se abre (plegado, enredo)",
  "etapa 1 sin freno (falla \\Req{C3})", 10, 5, 5,
  "plegado normalizado con fotos; 10 despliegues de prueba",
  10, None, 3, "x19"),
 ("M30", "D", "Cuerda y anclaje", "rotura en la apertura (\\SI{23}{N}) o por roce",
  "pierde el drogue: $\\Vr$ sube a \\SI{7.8}{m/s}", 8, 4, 4,
  "aramida $\\ge\\SI{200}{N}$ (FS $\\ge8$); anclaje a la estructura",
  8, None, 2, "x20"),
 ("M31", "D", "Destorcedor", "trabado",
  "la cuerda se retuerce", 5, 3, 3,
  "destorcedor de bolas; prueba de giro",
  5, 2, 2, None),
 ("M32", "D", "Drogue", "en la estela del rotor (sin aporte)",
  "$\\Vr$ hasta \\SI{7.8}{m/s}: \\Req{C4} al límite", 8, 6, 6,
  "cuerda de \\SI{1.5}{m}; E4 con y sin drogue; criterio sin drogue",
  8, None, 3, "x17"),
 ("M33", "D", "Cuerda", "cae en el plano del rotor (floja, oscilación)",
  "el rotor se frena o corta la cuerda", 9, 5, 7,
  "tubo guía de \\SI{30}{mm} sobre el eje; video cenit en E4",
  9, None, 5, "x13"),
 # ---------------- Estructura y recuperación
 ("M34", "S", "Cuerpo PETG", "fisura en tapa o unión por choque",
  "electrónica suelta", 8, 3, 4,
  "insertos roscados; E5",
  8, 2, 2, None),
 ("M35", "S", "Cámara cenit", "tapada por la cuerda o suelta",
  "falla \\Req{C6}", 7, 4, 3,
  "soporte atornillado; encuadre verificado",
  7, 2, 2, None),
 ("M36", "S", "Baliza", "no suena (interruptor apagado, pila)",
  "recuperación difícil", 6, 5, 2,
  "encender y escuchar (\\Req{E9}); pila nueva",
  6, None, 1, "x22"),
 ("M37", "S", "Masa total", "fuera de \\SI{500 \\pm 10}{g}",
  "falla \\Req{S1}; $\\Vr$ cambia \\SI{1}{\\percent}", 6, 4, 1,
  "pesaje en la lista; lastre ajustable",
  6, 1, 1, None),
]

GRUPOS = {"E": "Electrónica y software", "T": "Mecanismo de traba", "R": "Rotor",
          "D": "Drogue y cuerda", "S": "Estructura y recuperación"}

rows = []
for (mid, grp, comp, modo, efecto, S, O, D, acc, S2, O2, D2, ev) in M:
    if ev is not None:
        O2 = O_de_p(EB[ev][0])
        assert O2 <= O, (mid, O, O2)
    rows.append(dict(id=mid, grp=grp, comp=comp, modo=modo, efecto=efecto, S=S, O=O, D=D,
                     NPR=S * O * D, acc=acc, S2=S2, O2=O2, D2=D2, NPR2=S2 * O2 * D2, ev=ev))


def tex_rows():
    out = []
    g_prev = None
    for r in rows:
        if r["grp"] != g_prev:
            out.append("\\multicolumn{12}{@{}l}{\\textbf{%s}}\\\\*" % GRUPOS[r["grp"]])
            g_prev = r["grp"]
        ev = f" [$x_{{{r['ev'][1:]}}}$]" if r["ev"] else ""
        npr = f"\\textbf{{{r['NPR']}}}" if r["NPR"] >= 100 else f"{r['NPR']}"
        npr2 = f"\\textbf{{{r['NPR2']}}}" if r["NPR2"] >= 100 else f"{r['NPR2']}"
        out.append(f"{r['id']} & \\textbf{{{r['comp']}}}: {r['modo']}{ev} & {r['efecto']} & "
                   f"{r['S']} & {r['O']} & {r['D']} & {npr} & {r['acc']} & "
                   f"{r['S2']} & {r['O2']} & {r['D2']} & {npr2}\\\\")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            f.write(tex_rows() + "\n")
    with open(os.path.join(DATA, "confiabilidad_amfe.dat"), "w") as f:
        f.write("id S O D NPR S2 O2 D2 NPR2\n")
        for r in rows:
            f.write(f"{r['id']} {r['S']} {r['O']} {r['D']} {r['NPR']} {r['S2']} {r['O2']} "
                    f"{r['D2']} {r['NPR2']}\n")
    n = len(rows)
    a = np.array([r["NPR"] for r in rows]); b = np.array([r["NPR2"] for r in rows])
    print(f"modos: {n}")
    print(f"NPR suma antes {a.sum()}  después {b.sum()}  reducción {1-b.sum()/a.sum():.1%}")
    print(f"NPR >= 100: antes {np.sum(a>=100)}  después {np.sum(b>=100)}")
    print(f"NPR máx antes {a.max()}  después {b.max()}  mediana antes {np.median(a)} después {np.median(b)}")
    print("S>=9 y O'>=4:", [r["id"] for r in rows if r["S2"] >= 9 and r["O2"] >= 4])
    print("ordenado por NPR' :")
    for r in sorted(rows, key=lambda r: -r["NPR2"])[:10]:
        print(f"  {r['id']:4s} {r['comp']:22s} NPR {r['NPR']:4d} -> {r['NPR2']:4d}  (S{r['S2']} O{r['O2']} D{r['D2']})")
    print("ordenado por NPR :")
    for r in sorted(rows, key=lambda r: -r["NPR"])[:10]:
        print(f"  {r['id']:4s} {r['comp']:22s} NPR {r['NPR']:4d}")
