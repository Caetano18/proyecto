"""Memoria PDR: estructura v2 opcion B con estaciones roscadas para ajustar el CG (diseno y diagramas, sin FEM).
Uso: python3 generar_v2b_tex.py salida.tex      (lee ../fea/cg_v2BR.json)
"""
import os
import sys
import json

AQUI = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(AQUI, "_cabecera.py"), encoding="utf-8").read())
sys.path.insert(0, os.path.join(AQUI, "..", "src"))
import cg_v2 as CG  # noqa: E402

FEA = os.path.join(AQUI, "..", "fea")
CGR = json.load(open(os.path.join(FEA, "cg_v2BR.json")))


def g0(x):
    return f"{x:,.0f}".replace(",", ".")


def minimo(r):
    n, p = min(r["piezas"].items(), key=lambda kv: kv[1]["G_rot_p999"])
    return n, p


def nombre_pieza(n):
    if n.startswith("Adhesivo"):
        return "pegado de " + n.split()[-1] + " a la pared"
    if n.startswith("CT1"):
        return "pared de PETG"
    if n.startswith("Cuna"):
        return "cuna de la batería"
    if n.startswith(("Varilla", "Cancamo")):
        return "varillas" if n.startswith("Varilla") else "cáncamos"
    return "mamparo " + n[:2]


cas = CGR["casos"]
nom, tod_ab, tod_ar = cas["nominal"], cas["todo abajo"], cas["todo arriba"]

# ------------------------------------------------------------------ portada
A(r"""\begin{tcolorbox}[colback=celeste,colframe=azul,boxrule=0.6pt,arc=0pt]
{\large\bfseries\color{azul} Estructura v2, opción B regulable: estaciones roscadas para ajustar el CG\par}\smallskip
{\bfseries Diseño y ajuste del centro de gravedad con la batería ---
CanSat Argentina Universitario 2026\par}
\end{tcolorbox}""")
A(tabla(["Dato", "Valor", "Dato", "Valor"], [
    [r"\bfseries Código", "PDR-STR-REC-2026-v2B", r"\bfseries Base", "Documento v2 del equipo, diseño B (esqueleto)"],
    [r"\bfseries Masa", f"{f1(CGR['masa'])}\\,g (recalculada)", r"\bfseries Envolvente", r"\diam\,90 $\times$ 240\,mm"],
    [r"\bfseries CG nominal", f"{f1(nom['x_cg'])}\\,mm desde nadir", r"\bfseries Rango del CG",
     f"{f1(tod_ab['x_cg'])}--{f1(tod_ar['x_cg'])}\\,mm"],
    [r"\bfseries Recorrido de M2", f"{CG.RANGO2[0]:.0f}--{CG.RANGO2[1]:.0f}\\,mm (0,5\\,mm por vuelta)", r"\bfseries Fecha", "21/11/2026"],
], r"P{2.8cm}LP{2.8cm}L", col0=False))

A(r"""\section*{Resumen}
\begin{itemize}
\item \textbf{Propuesta:} las cuatro varillas M3 son roscadas en toda su longitud y cada mamparo queda apretado entre dos
tuercas nyloc. Girando las tuercas se corre la estación: \textbf{0,5\,mm por vuelta}. Se hacen regulables las dos estaciones
que llevan masa: \textbf{M2 con el módulo de batería} (""" + f1(CGR["m_bateria"]) + r"""\,g) y \textbf{M3 con el módulo de
aviónica} (""" + f1(CGR["m_avionica"]) + r"""\,g).
\item \textbf{Centro de gravedad:} nominal en """ + f1(nom["x_cg"]) + r"""\,mm desde el fondo de nadir. Corriendo los dos
módulos se mueve entre """ + f1(tod_ab["x_cg"]) + r" y " + f1(tod_ar["x_cg"]) + r"""\,mm. El margen estático de la vela
queda positivo en todo el rango.
\item \textbf{Pendientes que no resuelve este cambio:} la masa (""" + f1(CGR["masa"]) + r"""\,g, sobre el máximo de 510\,g),
y el área real de la vela (sección 4).
\end{itemize}
""")

# ------------------------------------------------------------------ 1
A(r"""\section{Las dos opciones de v2 y por qué se sigue con B}
El documento v2 compara dos arquitecturas: \textbf{A}, un monocasco de PETG impreso con los mamparos pegados a la pared, y
\textbf{B}, un esqueleto de cuatro varillas M3 con mamparos y una carena de 2\,mm que se desliza por encima. v2 eligió B por
la resistencia a la delaminación y el acceso a la electrónica. Además, solo B permite correr los mamparos.
""")
A(r"\figdos{0.49}{v2A_interior_anot.png}{0.49}{v2B_interior_anot.png}{Opciones A (izquierda) y B (derecha) del documento v2, "
  r"en corte: la pared que mira a la cámara está recortada y el interior queda entero.}")
A(tabla(["Criterio", "A: monocasco pegado", "B: esqueleto de varillas"], [
    ["Camino de la carga", "Por los pegados de los mamparos a la pared", "Por las varillas, hasta la brida"],
    ["Fabricación", "Impresión larga; delaminación entre capas", "Mamparos chicos; la carena no lleva la carga"],
    ["Acceso a la electrónica", "Cerrado al pegar", "El esqueleto sale entero al sacar 6 tornillos"],
    ["Ajuste del CG", "No (mamparos pegados)", "Sí, con estaciones roscadas (esta memoria)"],
    ["Incertidumbre principal", "Adherencia sobre PETG (2--6\\,MPa)", "Aflojamiento de tuercas (nyloc + marca)"],
], r"P{3.6cm}LL", sel=2, tam=r"\footnotesize"))

# ------------------------------------------------------------------ 2
r2, r3 = CG.RANGO2, CG.RANGO3
A(r"""\section{Estaciones roscadas}
\subsection{Concepto}
Las varillas M3 de Al 6061 ya eran roscadas en v2; el cambio es usar la rosca en toda la longitud. Cada mamparo queda
apretado entre dos tuercas nyloc con arandela plana, así que su posición se fija en cualquier punto de la varilla.
\textbf{Por qué tuercas y no mamparos roscados:} un mamparo con agujeros roscados no puede girar sobre cuatro varillas
paralelas a la vez (giraría alrededor del eje del CanSat, no de cada varilla). Con tuercas, cada una gira sola sobre su
varilla y el mamparo baja o sube sin girar.
\begin{itemize}
\item \textbf{Módulo de batería:} M2 se imprime con una cuna en U de la que cuelga el pack 2 $\times$ 18650. Se mueve
entero con M2. Las paredes de la cuna contienen las celdas en los costados (carga lateral de la lijadora).
\item \textbf{Módulo de aviónica:} los rieles de las placas cuelgan solo de M3 (en v2 iban de M2 a M3), así que el módulo
se mueve con M3 sin depender de M2.
\item \textbf{Fijos:} M1 (fondo de nadir, ventana de la cámara y pivotes de los largueros) y M4 (copa del paracaídas y
anclaje de la brida). La baliza baja a $x$ = 6--20\,mm para dar recorrido al módulo de batería.
\item \textbf{Herrajes:} ocho tuercas por varilla (32 en total). Las de los extremos son de acero (anclaje de la brida y
apriete del conjunto); las de las estaciones intermedias, nyloc de Al 7075 (0,2\,g). Agregan unos 5\,g respecto de v2.
\end{itemize}
""")
A(r"\fig{0.74}{v2BR_interior_anot.png}{Opción B regulable en la posición nominal (corte). M2 y M3 son estaciones regulables "
  r"sobre las varillas roscadas; M1 y M4 quedan fijos.}")
A(r"\fig{0.72}{v2BR_detalle_anot.png}{Detalle de la estación de M2: el mamparo queda apretado entre dos tuercas nyloc y la "
  r"cuna en U, impresa con M2, lleva el pack. Una vuelta de las tuercas corre el módulo 0,5\,mm.}")
A(r"\subsection{Recorrido de cada módulo}")
A(tabla(["Módulo", "Masa", "Nominal", "Recorrido", "Límite hacia nadir", "Límite hacia cenit"], [
    ["Batería (M2)", f"{f1(CGR['m_bateria'])}\\,g", f"{CG.NOM2:.0f}\\,mm", f"{r2[0]:.0f}--{r2[1]:.0f}\\,mm",
     "La cuna llega a la baliza ($x$ = 20)", "Las tuercas de M2 llegan a los rieles de la aviónica"],
    ["Aviónica (M3)", f"{f1(CGR['m_avionica'])}\\,g", f"{CG.NOM3:.0f}\\,mm", f"{r3[0]:.0f}--{r3[1]:.0f}\\,mm",
     "Los rieles llegan a M2 (hace falta $x_{M3} \\geq x_{M2} + 86$)", "Las tuercas de M3 llegan a la cápsula de nicrom"],
], r"P{2.0cm}P{1.1cm}P{1.2cm}P{1.6cm}LL", tam=r"\footnotesize"))
A(r"""\subsection{Procedimiento de ajuste}
\begin{enumerate}
\item Integrar todo con las estaciones nominales y cerrar la carena.
\item Medir la masa y el CG (sobre un filo o con dos balanzas).
\item Calcular el corrimiento del módulo:
\begin{ecu}
\begin{equation}
\Delta x_\text{módulo} = \frac{m_\text{total}}{m_\text{módulo}}\,\Delta x_\text{CG}\qquad\Rightarrow\qquad
\text{batería: } \frac{""" + f1(CGR["masa"]) + "}{" + f1(CGR["m_bateria"]) + r"""} = """ + f1(CGR["masa"] / CGR["m_bateria"], 2) +
  r"""\ \text{mm de módulo por mm de CG}
\end{equation}
\end{ecu}
\item Sacar la carena, aflojar las tuercas del módulo y girarlas: 2 vueltas = 1\,mm. Apretar con torque bajo (arandela plana
\diam7 para no marcar el PETG) y marcar la posición con pintura.
\item Volver a medir el CG.
\end{enumerate}
""")

# ------------------------------------------------------------------ 3
A(r"\section{Centro de gravedad}")
filas = []
for n, m, x in CG.items():
    filas.append([esc(n), f1(m), f"{x:.0f}", f1(m * x / 1000.0, 2)])
filas.append([r"\bfseries Total (posición nominal)", r"\bfseries " + f1(CGR["masa"]), r"\bfseries " + f1(nom["x_cg"]), ""])
A(tabla(["Ítem", "Masa [g]", "$x$ [mm]", "$m\\,x$ [kg\\,mm]"], filas, r"P{9.6cm}P{1.5cm}P{1.4cm}P{2.0cm}", sub=(len(filas) - 1,),
        tam=r"\footnotesize", larga=True))
A(r"\nota{Masas del documento v2, con la carena recalculada (163\,g para 240\,mm con el canal y las ranuras) y las tuercas de "
  r"las estaciones. $x$ desde el fondo de nadir. Los módulos de batería y de aviónica están en su posición nominal.}")
A(tabla(["Posición", "$x$ de M2", "$x$ de M3", "CG [mm]", "Margen estático"], [
    [esc(k.capitalize()), f"{v['x_m2']:.0f}", f"{v['x_m3']:.0f}", f1(v["x_cg"]),
     f"{100 * v['ME'][0]:.0f}--{100 * v['ME'][1]:.0f}\\,\\%"] for k, v in cas.items()
], r"LCCCC", tam=r"\small"))
A(r"\fig{0.84}{v2BR_cg.png}{CG según el corrimiento de los módulos. Correr también la aviónica casi duplica el efecto. La "
  r"línea roja es la estimación baja del punto neutro de la vela: el CG tiene que quedar debajo.}")
A(r"\fig{1.0}{v2BR_posiciones.png}{Las dos posiciones extremas y la nominal, con el CG marcado.}")
A(r"""El margen estático se calcula con el punto neutro entre el 55 y el 67\,\% de la quilla (190\,mm) desde el ápice en
$x = 14$\,mm, es decir $x_\mathrm{PN}$ = """ + f"{CG.XPN[0]:.0f}--{CG.XPN[1]:.0f}" + r"""\,mm, y
$\mathrm{ME} = (x_\mathrm{PN} - x_\mathrm{CG})/c_r$.

\pend{Lo que muestra la cuenta:} v2 pide el CG entre 95 y 105\,mm, pero con las masas recalculadas el nominal queda en
""" + f1(nom["x_cg"]) + r"""\,mm. Solo con los dos módulos hacia nadir se llega a """ + f1(tod_ab["x_cg"]) + r"""\,mm. El
margen estático es positivo en todo el rango, pero es chico con la estimación baja del punto neutro. Correr los módulos
hacia nadir siempre lo aumenta. Para ir más abajo hace falta lastre en M1 (10\,g en $x = 2$ bajan el CG unos 2\,mm), pero
el CanSat ya está pasado de masa.
""")

# ------------------------------------------------------------------ 5
A(r"\section{Pendientes}")
A(tabla(["Pendiente", "Por qué", "Cómo se cierra"], [
    ["Masa (S1)", f"{f1(CGR['masa'])}\\,g recalculados, sobre el máximo de 510\\,g", "Bajar el relleno de los mamparos, acortar la carena, revisar la electrónica"],
    ["Área de la vela", "Con la quilla de 190\\,mm y los largueros de 225\\,mm a 52\\textdegree{} el área es 0,045\\,m², no 0,067", "Redimensionar la vela o verificar la definición de área de v2"],
    ["CG en el rango de v2", f"Nominal {f1(nom['x_cg'])}\\,mm; con los módulos hacia nadir, {f1(tod_ab['x_cg'])}\\,mm", "Medir el CG real y ajustar; ensayos de planeo"],
    ["Tuercas que se aflojan", "Vibración de la lijadora y del vuelo", "Nyloc + marca de pintura; inspección después de cada ensayo"],
    ["Prueba térmica (60\\,\\textdegree C)", "El PETG pierde rigidez cerca de 60\\,\\textdegree C", "Ensayo de 2\\,h con la estructura integrada"],
], r"P{3.0cm}LL", tam=r"\footnotesize"))

A(r"\end{document}")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(T) + "\n")
print("ok", sys.argv[1])
