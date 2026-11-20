"""Memoria PDR v3 en LaTeX (misma memoria que generar_v3.js).  Uso: python3 generar_v3_tex.py datos_v3.json salida.tex"""
import sys
import json
import math

D = json.load(open(sys.argv[1], encoding="utf-8"))


def esc(s):
    """Texto plano -> LaTeX (caracteres de los datos)."""
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("Ø", r"\diam{}"),
                 ("×", r"$\times$"), ("±", r"$\pm$"), ("°", r"\textdegree{}"), ("²", r"$^2$"), ("³", r"$^3$"),
                 ("≥", r"$\geq$"), ("≤", r"$\leq$"), ("≈", r"$\approx$"), ("→", r"$\rightarrow$"), ("−", r"$-$")):
        s = s.replace(a, b)
    return s


def f1(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def ms(x):
    t = ("+" if x >= 0 else "$-$") + f"{abs(x):.2f}".replace(".", ",")
    return t


def msr(par):
    """MS al percentil 99,9 (rojo si es negativo) y, entre parentesis, el pico de un elemento."""
    a = ms(par[0])
    if par[0] < 0:
        a = r"\textcolor{rojo}{\bfseries " + a + "}"
    return f"{a} ({ms(par[1])})"


def tabla(cab, filas, spec, sel=None, sub=(), col0=True, tam=r"\small", larga=False):
    """cab y filas ya en LaTeX.  spec: columnas (tabularx).  sel: columna elegida (encabezado rojo, celdas rosadas)."""
    L = []
    hdr = " & ".join((r"\cellcolor{rojo}" if j == sel else "") + r"\color{white}\bfseries " + c for j, c in enumerate(cab)) + r" \\"
    if larga:
        L.append(r"\par{" + tam + r"\begin{longtable}{" + spec + "}")
        L.append(r"\rowcolor{azul}" + hdr + r" \endfirsthead")
        L.append(r"\rowcolor{azul}" + hdr + r" \endhead")
    else:
        L.append(r"\par{" + tam + r"\noindent\begin{tabularx}{\linewidth}{" + spec + "}")
        L.append(r"\rowcolor{azul}" + hdr)
    for i, f in enumerate(filas):
        cel = []
        for j, c in enumerate(f):
            pre = ""
            if i in sub:
                pre = r"\cellcolor{celeste}\bfseries "
            elif j == 0 and col0:
                pre = r"\cellcolor{celeste}\bfseries "
            elif j == sel:
                pre = r"\cellcolor{rosa}"
            cel.append(pre + c)
        fin = r" \\*" if (larga and i >= len(filas) - 4 and i < len(filas) - 1) else r" \\"   # sin corte de pagina al final
        L.append(" & ".join(cel) + fin)
    L.append(r"\end{longtable}}" if larga else r"\end{tabularx}}")
    L.append(r"\par\medskip")
    return "\n".join(L)


T = []
A = T.append

A(r"""\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{lmodern}
\usepackage[spanish,es-nodecimaldot,es-tabla]{babel}
\usepackage[a4paper,margin=2cm]{geometry}
\usepackage{amsmath,amssymb,textcomp,array,tabularx,longtable,booktabs,enumitem,microtype,fancyhdr,titlesec}
\usepackage[table]{xcolor}
\usepackage[most]{tcolorbox}
\usepackage[colorlinks=true,linkcolor=azul,urlcolor=azul]{hyperref}
\definecolor{azul}{HTML}{1F4E79}\definecolor{celeste}{HTML}{DCE6F2}\definecolor{rojo}{HTML}{C00000}
\definecolor{rosa}{HTML}{FBE9E9}\definecolor{gris}{HTML}{595959}\definecolor{fondoec}{HTML}{F3F6FA}
\newcommand{\diam}{\ensuremath{\varnothing}}
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\newcolumntype{C}{>{\centering\arraybackslash}X}
\newcolumntype{R}{>{\raggedleft\arraybackslash}X}
\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}
\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.25}\arrayrulecolor{azul!45}
\titleformat{\section}{\large\bfseries\color{azul}}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries\color{azul}}{\thesubsection}{0.5em}{}
\newtcolorbox{ecu}{colback=fondoec,colframe=azul!45,boxrule=0.4pt,arc=0pt,left=6pt,right=6pt,top=2pt,bottom=2pt}
\newcommand{\pend}[1]{\textcolor{rojo}{\bfseries #1}}
\newcommand{\nota}[1]{{\par\small\itshape\color{gris}#1\par}\medskip}
\pagestyle{fancy}\fancyhf{}\fancyfoot[R]{\small\color{gris}PDR-STR-REC-2026-v3 · Equipo Hermes · página \thepage}
\renewcommand{\headrulewidth}{0pt}\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}\setlist{nosep,leftmargin=1.4em}
\begin{document}
""")

# ------------------------------------------------------------------ portada
A(r"""\begin{tcolorbox}[colback=celeste,colframe=azul,boxrule=0.6pt,arc=0pt]
{\large\bfseries\color{azul} Memoria de cálculo y diseño preliminar (PDR) --- Edición combinada v3\par}\smallskip
{\bfseries Control de descenso (fases 1 y 2), estructura primaria, mecanismos de liberación y presupuesto de masa ---
CanSat Argentina Universitario 2026\par}
\end{tcolorbox}""")
A(tabla(["Dato", "Valor", "Dato", "Valor"], [
    [r"\bfseries Código", "PDR-STR-REC-2026-v3", r"\bfseries Base", r"v2 del equipo + revisión D (verificación estructural)"],
    [r"\bfseries Masa (S1)", r"500,0 $\pm$ 10 g ($W$ = 4,905 N)", r"\bfseries Envolvente (S2, S3)", r"\diam\,90,0 $\times$ 240,0 mm"],
    [r"\bfseries Descenso fase 1 (C3)", r"14,3--15,9 m/s, paracaídas plano \diam233 mm", r"\bfseries Descenso fase 2 (C4)",
     r"5,1--6,5 m/s, vela Rogallo en espiral"],
    [r"\bfseries Carcasa", r"Laminado carbono 0,8 mm + vidrio 0,6 mm", r"\bfseries Fecha", r"20/11/2026"],
], r"P{3.0cm}LP{3.0cm}L", col0=False))

# ------------------------------------------------------------------ 0
A(r"""\section*{0. Qué combina esta edición}
Esta memoria une los dos trabajos del subsistema mecánico. De la \textbf{memoria v2} del equipo se toma el concepto: cuerpo
integral (todo el CanSat baja junto), vela Rogallo con espiral pasiva, liberación por nicrom encapsulado, cámaras que ven hacia
afuera y la electrónica de 2 celdas. De la \textbf{revisión D} se toma la verificación: modelo de elementos finitos, ensayo de la
lijadora con el CanSat parado, carga del ensayo de caída sobre el anclaje del paracaídas y presupuesto de masa por fuente.

Al verificar el diseño v2 con el modelo de elementos finitos apareció un problema: con la carcasa de PETG de 2\,mm el primer modo
lateral queda en 161--172\,Hz y \textbf{no pasa el ensayo de la lijadora} (MS $= -0{,}55$ en la carcasa). Además, la carcasa pesa
163\,g y no 139\,g, y el CanSat suma 503\,g sin lastre. La revisión E conserva todo el concepto v2 y cambia la carcasa por la
carcasa laminada de la revisión D: el modo lateral sube a 349--370\,Hz, todos los márgenes son positivos y quedan 51\,g de margen
de masa.
""")
A(tabla(["Tema", "Origen", "Decisión de la revisión E", "Motivo"], [
    ["Concepto de vuelo", "v2", "Cuerpo integral: el paracaídas se suelta al 80\\,\\% del apogeo y el mismo cuerpo planea",
     "Una sola pieza a recuperar; cámaras al exterior; el Apéndice A no exige separar payload y contenedor"],
    ["2.º sistema de descenso", "v2", "Vela Rogallo de 670\\,cm², flecha 52\\textdegree, espiral pasiva de 25\\textdegree",
     "Sin cola ni servos: unos 30\\,g menos y ningún mecanismo activo en vuelo"],
    ["Liberación", "v2", "Lazo de Dyneema cortado por nicrom dentro de una cápsula de PTFE (M1)",
     "Un solo actuador; si falla, el CanSat sigue bajando con el paracaídas"],
    ["Paracaídas", "v2 + rev.\\ D", "Plano con ventana, \\diam233\\,mm (densidad del sitio 1,15\\,kg/m³)",
     "Con la densidad a nivel del mar, el \\diam226 de v2 da 15,4\\,m/s en el sitio"],
    ["Carcasa", "rev.\\ D", "Laminado: carbono-epoxi 0,8\\,mm ($x < 130$\\,mm) + vidrio-epoxi 0,6\\,mm (arriba)",
     "PETG 2\\,mm: 161\\,Hz, lijadora $-0{,}55$. Laminado: 349\\,Hz, $+15$; 87\\,g más liviana"],
    ["Esqueleto interno", "v2", "5 mamparos de PETG + 4 varillas roscadas M3 de aluminio",
     "Pasa todos los casos con amplio margen; la bandeja sale entera"],
    ["Anclaje del paracaídas", "rev.\\ D", "Brida de 3 ramales a los extremos superiores de las varillas",
     "Ensayo de caída: 265\\,N; el lazo de Dyneema queda fuera del camino de carga"],
    ["Verificación", "rev.\\ D", "FEM modal y estático + factores dinámicos de la lijadora y del choque",
     "v2 no verificaba la vibración (S4)"],
    ["Presupuesto de masa", "v2 + rev.\\ D", "Ítems que faltaban; incertidumbre por fuente",
     "La carcasa estaba subestimada y faltaban unos 29\\,g"],
    ["Energía", "v2 (equipo)", "2 celdas 18650 (2S1P)", "Coincide con el subsistema eléctrico y entra con margen"],
], r"P{2.4cm}P{1.4cm}LL", tam=r"\footnotesize"))
A(r"\nota{De la revisión D quedan como alternativa ---si los organizadores exigieran que el payload se separe del contenedor--- "
  r"el contenedor separado, el bastidor de carbono y G10, la cola en V con servo y la llave de bayoneta. Toda esa verificación "
  r"está en el repositorio.}")

# ------------------------------------------------------------------ 1
A(r"\section{Marco normativo y condiciones de contorno}")
A(tabla(["Req.", "Requisito", "Especificación", "Impacto en el diseño (rev.\\ E)"], [
    ["C1 / C2", "Integración y eyección", "Dentro del cohete; sale con la carga de eyección",
     "Cilindro liso \\diam90\\,mm, sin salientes; ranuras de los largueros enrasadas"],
    ["C3", "Fase 1 (paracaídas)", "Despliegue automático, $15 \\pm 3$\\,m/s",
     "Paracaídas plano \\diam233\\,mm con ventana \\diam40\\,mm en la copa superior"],
    ["C4", "Fase 2 (80\\,\\% del apogeo)", "Otro sistema de descenso, $5 \\pm 3$\\,m/s",
     "Se suelta el paracaídas y se abre la vela Rogallo; espiral pasiva"],
    ["C6 / C7", "Video cenit y nadir", "Toda la secuencia de descenso",
     "Ventana de nadir \\diam14 en M1; cámara de cenit inclinada 35\\textdegree{} en M4"],
    ["C8 / E8 / E9", "Baliza", "Audible, batería e interruptor propios", "Bahía 1, acceso por orificio $\\leq 10$\\,mm"],
    ["S1", "Masa", "$500 \\pm 10$\\,g", "448,6\\,g secos + 51,4\\,g de lastre y margen"],
    ["S2 / S3", "Dimensiones", "\\diam\\,90\\,mm; largo 200--250\\,mm", "\\diam\\,90 $\\times$ 240\\,mm (cuerpo de 220\\,mm + copa de 20\\,mm)"],
    ["S4 / S5", "Vibración y choque", "15\\,G; 30\\,G",
     "Verificado por FEM: lijadora con el CanSat parado, 15\\,G cuasi-estático y choque de 30\\,G"],
    ["S6", "Pared exterior", "$\\geq 2$\\,mm si es impresa; no debe flexionar",
     "La carcasa es laminada, no impresa: la regla de 2\\,mm no aplica. La rigidez se verifica por FEM"],
    ["S7", "Deslizamiento", "Debe salir libremente del cohete", "Superficie lisa; largueros dentro de la envolvente"],
    ["M1 / M2", "Mecanismos", "Sin calor expuesto; mantener la configuración",
     "Nicrom dentro de una cápsula cerrada; trinquete de bloqueo de los largueros"],
], r"P{1.7cm}P{2.6cm}P{3.6cm}L", tam=r"\footnotesize"))
A(r"\nota{Corrección respecto de v2: el Apéndice A solo tiene M1 y M2 (v2 cita M1--M3).}")

# ------------------------------------------------------------------ 2
A(r"""\section{Fase 1: paracaídas primario (C3)}
Se mantienen las ecuaciones de v2 para la caída libre axial del cilindro ($C_{d,\mathrm{cil}} = 0{,}86$ según Hoerner para
$L/D = 2{,}44$; $v_\mathrm{libre} = 38{,}3$\,m/s; $Re_D$ entre $9\times10^4$ y $2{,}3\times10^5$). Lo que cambia es la
\textbf{densidad de diseño}: v2 usa la atmósfera estándar a nivel del mar ($\rho = 1{,}225$\,kg/m³). En el sitio, sumando la
altura de apertura (unos 700\,m), es $\rho = 1{,}15$\,kg/m³, y con menos densidad se baja más rápido.
\begin{ecu}
\begin{align}
(C_d A)_\mathrm{tot} &= \frac{2W}{\rho\,v^2} = \frac{2\cdot 4{,}905}{1{,}15\cdot 15{,}0^2} = 0{,}03791~\mathrm{m^2}\\
(C_d A)_\mathrm{para} &= (C_d A)_\mathrm{tot} - (C_d A)_\mathrm{cil} = 0{,}03791 - 0{,}00547 = 0{,}03244~\mathrm{m^2}
\quad\Rightarrow\quad S_0 = \frac{0{,}03244}{0{,}78} = 0{,}0416~\mathrm{m^2}\\
D_\mathrm{ext} &= \sqrt{\frac{4\,(S_0 + A_\mathrm{ventana})}{\pi}} = 234~\mathrm{mm}
\quad\Rightarrow\quad \text{se adopta } D_\mathrm{ext} = 233~\mathrm{mm} \text{ con ventana } \varnothing 40~\mathrm{mm}
\end{align}
\end{ecu}
""")
A(tabla(["Caso", "$C_{d0}$", "Masa", "Velocidad [m/s]"], [
    ["Nominal en el sitio ($\\rho = 1{,}15$)", "0,78", "500\\,g", "15,0"],
    ["Banda de diseño", "0,70--0,86 ($\\pm$10\\,\\%)", "490--510\\,g", "14,3--15,9"],
    ["A nivel del mar ($\\rho = 1{,}225$)", "0,78", "500\\,g", "14,6"],
    ["Paracaídas de v2 (\\diam226) en el sitio", "0,78", "500\\,g", "15,4"],
], r"LP{3.2cm}P{2.0cm}P{2.6cm}"))
A(r"""Se mantiene la elección de v2: \textbf{paracaídas plano con ventana central}. La ventana reduce el balanceo a menos de
$\pm 8^\circ$, y el cruciforme tiene más riesgo de enredo en una eyección rápida. Masa de 8,5\,g (tela de 1,5\,g, líneas y
giratorio).

\subsection{Cargas sobre el anclaje}
v2 calcula la carga de apertura en 12,2\,N (20\,m/s, factor de choque 1,4), lo cual está bien para el vuelo. Pero el
\textbf{ensayo de caída} de la competencia (cuerda atada al punto de anclaje del paracaídas, caída de 61\,cm) carga ese anclaje con
unos 30\,G. La carga de diseño es:
\begin{ecu}
\begin{align}
F_\mathrm{caída} &= m\cdot 30\,g\cdot \mathrm{FAD} = 0{,}500\cdot 30\cdot 9{,}81\cdot 1{,}8 = 265~\mathrm{N}\\
\sigma_\mathrm{M3} &= \frac{F_\mathrm{caída}/4}{A_s} = \frac{66}{5{,}03} = 13{,}2~\mathrm{MPa}\quad(\mathrm{MS} = +13)\\
\tau_\mathrm{pasador} &= \frac{F_\mathrm{caída}}{2\,\pi\,r^2} = \frac{265}{2\,\pi\,1{,}5^2} = 18{,}7~\mathrm{MPa}\quad(\mathrm{MS} = +10)
\end{align}
\end{ecu}
La brida de 3 ramales va a los extremos superiores de las 4 varillas M3, y el pasador de liberación es de acero, \diam3\,mm,
trabajando a corte doble.

\pend{Condición de diseño:} el lazo de Dyneema (180\,N de rotura) \textbf{no puede estar en el camino de carga}. Con 265\,N se
cortaría en el ensayo de caída. El lazo solo retiene el pasador, que trabaja a corte; la brida va a las varillas, no a la tapa M5.
""")

# ------------------------------------------------------------------ 3
A(r"""\section{Fase 2: planeador de vela Rogallo (C4)}
Se mantienen la geometría y las ecuaciones de planeo helicoidal de v2: quilla de 190\,mm sobre el lomo del cilindro, largueros de
225\,mm con flecha de $52^\circ$, envergadura de 425\,mm, $S = 0{,}0670$\,m², alargamiento 2,69, holgura de la tela (billow) del
8,2\,\% y altura de inflado de 31\,mm. Las ecuaciones de equilibrio en la espiral son:
\begin{ecu}
\begin{gather}
\tan\gamma = \frac{C_{D,\mathrm{tot}}}{C_L\cos\phi},\qquad
V = \sqrt{\frac{2\,W\cos\gamma}{\rho\,S\,C_L\cos\phi}},\qquad V_z = V\sin\gamma,\qquad R = \frac{(V\cos\gamma)^2}{g\tan\phi}\\
C_L(\alpha) = K_p\sin\alpha\cos^2\alpha + f\,K_v\cos\alpha\sin^2\alpha,\qquad C_{D,i} = C_L\tan\alpha,\qquad
C_{D,\mathrm{tot}} = C_{D0} + \frac{(C_d A)_\mathrm{cil}}{S} + C_{D,i}
\end{gather}
\end{ecu}
Las cuentas de v2 son correctas: $V = 8{,}71$\,m/s, $V_z = 5{,}03$\,m/s y $R = 11{,}0$\,m. La revisión E agrega la
\textbf{incertidumbre}. v2 usa toda la sustentación de vórtice de Polhamus ($f = 1$, $K_v = \pi$) con $\alpha = 28^\circ$, en una
vela flexible de $52^\circ$ de flecha, cerca del ángulo en que el vórtice se rompe. Por eso se repite el cálculo con una fracción
$f$ de la sustentación de vórtice ($K_p = 2{,}2$, $C_{D0} = 0{,}080$, $\phi = 25^\circ$) y con las dos densidades:
""")
A(tabla(["Fracción de vórtice $f$", "$C_L$", "$C_D$", "$\\gamma$", "$V_z$, $\\rho = 1{,}225$", "$V_z$, $\\rho = 1{,}15$",
         "Radio de la espiral"], [
    ["1,0 (v2)", "1,42", "0,91", "35,5\\textdegree", "5,05\\,m/s", "5,22\\,m/s", "11,0--11,7\\,m"],
    ["0,5 (rev.\\ D)", "1,11", "0,75", "36,8\\textdegree", "5,84\\,m/s", "6,02\\,m/s", "13,3--14,2\\,m"],
    ["0,3 (pesimista)", "0,99", "0,69", "37,5\\textdegree", "6,26\\,m/s", "6,46\\,m/s", "14,6--15,5\\,m"],
], r"LCCCCCC"))
A(r"""En todos los casos el descenso queda dentro de $5 \pm 3$\,m/s: \textbf{entre 5,1 y 6,5\,m/s}. El margen hacia el límite de
8\,m/s es de 1,5\,m/s en el peor caso.

\subsection{Estabilidad en cabeceo (no estaba calculada en v2)}
v2 afirma una estabilidad pendular pasiva, pero el centro de gravedad queda apenas unos 45\,mm debajo de la quilla: casi no hay
efecto péndulo, y sin cola la estabilidad depende de dónde quede el centro de gravedad respecto del punto neutro. En un ala delta
esbelta, el punto neutro está entre el 55\,\% y el 67\,\% de la quilla desde el ápice. Con el ápice en $x = 14$\,mm:
\begin{ecu}
\begin{equation}
x_\mathrm{PN} = 14 + (0{,}55\ldots0{,}67)\cdot 190 = 119\ldots141~\mathrm{mm},\qquad
\mathrm{ME} = \frac{x_\mathrm{PN} - x_\mathrm{CG}}{c_r} = \frac{(119\ldots141) - 100}{190} = 10\ldots21~\%
\end{equation}
\end{ecu}
Con el centro de gravedad de diseño de v2 (95--105\,mm), el ala es \textbf{estáticamente estable}.

\pend{Pendiente:} sin cola, el ángulo de equilibrio ($\alpha \approx 28^\circ$) depende de la posición del centro de gravedad y de
la holgura de la tela. Se fija con ensayos de lanzamiento de la vela, moviendo el lastre. Los 51\,g de margen de masa alcanzan
para correr el centro de gravedad unos 10\,mm.

Guiado: se mantiene el de v2, totalmente pasivo. La espiral de $25^\circ$ se induce con 4\,mm de holgura extra en el lóbulo
izquierdo o con topes asimétricos de $53^\circ$ y $51^\circ$.
""")

# ------------------------------------------------------------------ 4
fp, fl = D["f_petg"], D["f_lam"]
A(r"\section{Estructura primaria y verificación}")
A(r"\subsection{Estudio de compromiso}")
A(tabla(["Criterio", "A · Monocasco impreso", "B · Esqueleto M3 + carcasa PETG 2\\,mm (v2)",
         "C · Esqueleto M3 + carcasa laminada (rev.\\ E)"], [
    ["Modo lateral, CanSat parado", "$\\approx 120$\\,Hz (rev.\\ B, impreso)", f"{fp['z']:.0f} / {fp['y']:.0f}\\,Hz",
     f"{fl['z']:.0f} / {fl['y']:.0f}\\,Hz"],
    ["Ensayo de la lijadora (200--233\\,Hz)", "Falla", r"\textcolor{rojo}{\bfseries Falla: MS $-0{,}55$}", "Pasa: MS $+15$"],
    ["Masa de la carcasa", "$\\approx 160$\\,g", "163\\,g (v2 decía 139\\,g)", "75\\,g"],
    ["Masa sin lastre del CanSat", "---", f"{f1(D['masa_v2_petg_sin_lastre'])}\\,g (no cierra en 500\\,g)",
     f"{f1(D['seco'])}\\,g (51\\,g de margen)"],
    ["Requisito S6", "Cumple", "Cumple", "No es impresa: la regla de 2\\,mm no aplica; la rigidez se verifica por FEM"],
    ["Radio y GNSS", "Transparente", "Transparente", "Vidrio arriba ($x > 130$\\,mm) transparente; el carbono de abajo es conductor"],
    ["Fabricación", "Una impresión larga", "Impresión + ranuras",
     "Laminado manual sobre mandril de \\diam88 + post-curado $> 60$\\,\\textdegree C; ranuras cortadas y reforzadas"],
], r"P{3.0cm}P{2.6cm}LL", sel=3, tam=r"\footnotesize"))
A(r"\subsection{Zonificación interna (v2, con una regla nueva)}")
A(tabla(["Estación $x$", "Bahía / mamparo", "Contenido"], [
    ["0--35\\,mm", "Bahía 1 (nadir) + M1 (fondo)", "Cámara de nadir con ventana \\diam14 + lente; baliza con batería e interruptor propios"],
    ["35--105\\,mm", "Bahía 2 + M2 puente ($x = 85$)", "Pack 2 $\\times$ 18650 con lengüetas soldadas; encastre de los largueros y topes"],
    ["105--175\\,mm", "Bahía 3 (aviónica) + M3", "PCB principal, GNSS, radio de 915\\,MHz, interruptor general"],
    ["175--220\\,mm", "Bahía 4 (cenit) + M4", "Cámara de cenit inclinada 35\\textdegree; cápsula de nicrom; paneles solares en el lomo"],
    ["220--240\\,mm", "Bahía 5 (copa) + M5 (tapa)", "Paracaídas \\diam233\\,mm; resorte expulsor de la tapa; brida a las varillas"],
], r"P{2.0cm}P{4.2cm}L", tam=r"\footnotesize"))
A(r"""\pend{Regla nueva:} las antenas de radio y GNSS van por \textbf{encima de $x = 135$\,mm}, bajo el tramo de vidrio. El tramo
de carbono ($x < 130$\,mm) es conductor y las taparía.

\subsection{Modelo de elementos finitos}
Se usa el mismo procedimiento que en la revisión D, con CalculiX y tetraedros cuadráticos. El modelo incluye:
\begin{itemize}
\item Carcasa \diam90 $\times$ 240\,mm con las dos ranuras pasantes de 6 $\times$ 192\,mm para los largueros.
\item Mamparos M1--M5 de PETG con 40\,\% de relleno (rigidez y densidad efectivas).
\item 4 varillas M3 de aluminio 6061 pasantes.
\item Los equipos como masa repartida en el mamparo o la carcasa que los sostiene. Total: 500\,g.
\item Laminados ortótropos en ejes cilíndricos: carbono-epoxi $[0/90,\pm45,0/90]$ y vidrio-epoxi 0/90.
\end{itemize}
Apoyo: base fija, como en el ensayo de la lijadora, con el CanSat parado y sujeto por la base. Malla gruesa (unos 260\,000 nodos)
para comparar variantes; antes del CDR se repite con malla fina.
""")
A(tabla(["Variante", "Modo 1", "Modo 2", "Modo 3", "Primer modo axial"], [
    ["B · carcasa PETG 2\\,mm (v2)", "161\\,Hz (lateral $z$, 61\\,\\%)", "172\\,Hz (lateral $y$, 58\\,\\%)", "400\\,Hz (torsión)", "$> 550$\\,Hz"],
    ["C · carcasa laminada (rev.\\ E)", "349\\,Hz (lateral $z$, 54\\,\\%)", "370\\,Hz (lateral $y$, 52\\,\\%)", "489\\,Hz (axial, 15\\,\\%)", "489\\,Hz"],
], r"P{3.6cm}CCCC", tam=r"\footnotesize"))
A(r"\subsection{Casos de carga y método}")
A(tabla(["Caso", "Carga", "Requisito"], [
    ["CE-15", "15\\,G cuasi-estático en $x$, $y$, $z$", "S4"],
    ["Lijadora (parado)", "Plato orbital $a(f) = 29\\,\\mathrm{G}\\,(f/233)^2$. Si el modo lateral queda debajo de 233\\,Hz, el arranque y "
     "el frenado lo cruzan (respuesta transitoria, $\\zeta = 2$\\,\\%); si queda encima, marcha sostenida a 233\\,Hz. Axial: 29\\,G",
     "S4 (ensayo de la competencia)"],
    ["CH-30", "Semiseno de 30\\,G, factor de espectro de choque 1,7 (51\\,G) en $x$, $y$, $z$", "S5"],
    ["Caída 61\\,cm", "265\\,N sobre el anclaje del paracaídas (sección 2.1)", "S5 (ensayo de la competencia)"],
], r"P{2.6cm}LP{3.0cm}", tam=r"\footnotesize"))
A(r"""Método: tensiones de 1\,G del modelo en cada eje $\times$ aceleración equivalente del caso,
\begin{ecu}
\begin{equation}
\mathrm{MS} = \frac{\sigma_\mathrm{adm}}{\mathrm{FS}\cdot\sigma} - 1,\qquad
\mathrm{FS} = 2{,}0~\text{(impresos, entre capas)},\quad 1{,}5~\text{(laminados)},\quad 1{,}25~\text{(metales)}
\end{equation}
\end{ecu}
Se informa el percentil 99,9 de cada pieza y, entre paréntesis, el pico de un solo elemento. """
  + f"Aceleración equivalente de la lijadora: con PETG, {D['aeq_petg']['y']:.0f}\\,G (pasa por la resonancia); con el laminado, "
  + f"{D['aeq_lam']['y']:.0f}\\,G (por encima de la resonancia).\n")
A(r"\subsection{Márgenes de seguridad}")
A(r"\textbf{C · Revisión E (carcasa laminada):} todos los márgenes son positivos.")
A(tabla(["Pieza", "CE-15", "Lijadora (parado)", "CH-30"], [[esc(f[0]), msr(f[1]), msr(f[2]), msr(f[3])] for f in D["lam"]],
        r"LCCC"))
A(r"\textbf{B · v2 (carcasa PETG de 2\,mm):} no pasa el ensayo de la lijadora.")
A(tabla(["Pieza", "CE-15", "Lijadora (parado)", "CH-30"], [[esc(f[0]), msr(f[1]), msr(f[2]), msr(f[3])] for f in D["petg"]],
        r"LCCC"))
A(r"""\subsection{Cálculos manuales de v2, revisados}
\begin{itemize}
\item \textbf{Varillas M3 a 30\,G} (v2: 7,3\,MPa, FS 32,8): correcto. El FEM también da márgenes amplios ($+28$ en CH-30).
\item \textbf{Mamparo M2 a 30\,G} (v2: 17,4\,MPa, FS 2,59): v2 usa 45\,MPa, la resistencia del PETG macizo, pero el mamparo tiene
40\,\% de relleno (unos 20\,MPa efectivos). Con la viga simplemente apoyada de v2, el FS bajaría a 1,15. El FEM, que lo apoya en las
varillas y en la carcasa como es en realidad, da MS $= +4{,}3$ en CH-30: la viga de v2 era muy conservadora en el apoyo pero
optimista en el material.
\item \textbf{Viga puente y largueros de carbono del ala} (v2: FS 5,8 y 7,1): correctos; no cambian.
\item \textbf{Carcasa a compresión} (v2: 0,27\,MPa): irrelevante; lo que dimensiona la carcasa es la flexión en la resonancia
lateral, que v2 no calculaba.
\end{itemize}
""")

# ------------------------------------------------------------------ 5
A(r"""\section{Mecanismos de estiba, retención y despliegue (M1, M2)}
Se mantiene el diseño de v2 con un solo cambio en el camino de carga del paracaídas:
\begin{itemize}
\item \textbf{Estiba:} largueros de carbono plegados en las ranuras laterales, dentro de \diam90\,mm (S7). La vela va plegada en
acordeón bajo una cubierta dorsal retenida por el mismo lazo.
\item \textbf{Liberación:} lazo de Dyneema \diam0,40\,mm (180\,N de rotura) que retiene las puntas de los largueros y el pasador de
liberación del paracaídas. Lo funde un nicrom AWG\,30 de 3 espiras dentro de una cápsula cerrada de PTFE (pulso de 3,7\,V,
2,2\,A durante 0,7\,s, comandado por MOSFET al detectar el 80\,\% del apogeo).
\item \textbf{Resortes de torsión:} dos por larguero, AISI\,302 de 1,8\,mm, diámetro medio de 10\,mm, 16,4 espiras.
\end{itemize}
\begin{ecu}
\begin{gather}
M_\mathrm{abierto} = 1{,}5\cdot 268 = 405~\mathrm{N\,mm},\qquad M_\mathrm{cerrado} = 6{,}75\cdot 112^\circ = 756~\mathrm{N\,mm},\qquad
T_\mathrm{hilo} = \frac{756}{175} = 4{,}32~\mathrm{N}\\
\sigma_b = K_b\,\frac{32\,M}{\pi d^3} = 1{,}152\cdot\frac{32\cdot 378}{\pi\cdot 1{,}8^3} = 762~\mathrm{MPa}\ (\mathrm{FS}\ 1{,}44),\qquad
N_a = \frac{E\,d^4\,\pi}{64\,D_m\,k\cdot 180} = 16{,}4
\end{gather}
\end{ecu}
\begin{itemize}
\item \textbf{Tope y trinquete:} hombro en M2 a 14\,mm del eje, aplastamiento de 2,0\,MPa; trinquete elástico que impide el cierre (M2).
\item \textbf{Cambio de la revisión E:} la brida del paracaídas va a los extremos de las varillas, y el lazo de Dyneema solo retiene
el pasador (sección 2.1).
\end{itemize}
""")

# ------------------------------------------------------------------ 6
A(r"\section{Presupuesto de masa (S1)}")
filas, sub = [], []
for cat, items in D["masa"]:
    m, u2 = 0.0, 0.0
    for it, n_, mm, u, src in items:
        filas.append([esc(it), str(n_), f1(mm), "$\\pm$" + f1(u), esc(src)])
        m += mm
        u2 += u * u
    sub.append(len(filas))
    filas.append([esc(cat) + " --- subtotal", "", f1(m), "$\\pm$" + f1(math.sqrt(u2)), ""])
sub.append(len(filas))
filas.append(["Masa seca", "", f1(D["seco"]), "$\\pm$" + f1(D["rss"]) + " (RSS)", ""])
filas.append(["Lastre y margen de ajuste (arandelas sobre las varillas en M1/M2)", "", f1(D["lastre"]), "", "Cierre a 500\\,g"])
sub.append(len(filas))
filas.append(["TOTAL (S1: $500 \\pm 10$\\,g)", "", "500,0", "", "Cumple"])
A(tabla(["Componente", "Cant.", "Masa [g]", "Incert. [g]", "Fuente"], filas,
        r">{\raggedright\arraybackslash}p{6.6cm}>{\centering\arraybackslash}p{0.8cm}>{\raggedleft\arraybackslash}p{1.3cm}"
        r">{\raggedleft\arraybackslash}p{1.9cm}>{\raggedright\arraybackslash}p{4.1cm}",
        sub=sub, col0=False, tam=r"\footnotesize", larga=True))
A(f"""Correcciones respecto de v2: la carcasa de PETG de 240\\,mm pesa 163\\,g (v2: 139\\,g); faltaban la tapa con su resorte, la
cubierta de la vela, los tornillos y el adhesivo, las sillas de las celdas y la lente de nadir (unos 29\\,g en total); y las
incertidumbres de $\\pm$3\\,\\% eran optimistas para piezas impresas y laminadas. Con la carcasa laminada, la masa seca es
{f1(D['seco'])}\\,g $\\pm$ {f1(D['rss'])}\\,g (RSS; $\\pm${f1(D['lineal'])}\\,g en el peor caso lineal).

\\textbf{{Métodos de corrección:}}
\\begin{{itemize}}
\\item Si la masa medida es menor de 495\\,g: agregar arandelas de acero sobre las varillas en M1 y M2. Corren el centro de gravedad
hacia la nariz, lo que también ayuda a la estabilidad (sección 3.1).
\\item Si es mayor de 505\\,g: reducir el lastre. Si no alcanza, bajar el relleno de los mamparos del 40\\,\\% al 25\\,\\% ($-14$\\,g) y
acortar los arneses ($-5$\\,g).
\\item No se toca la carcasa: su espesor sale del ensayo de la lijadora, no de la masa.
\\end{{itemize}}
""")

# ------------------------------------------------------------------ 7
A(r"\section{Pendientes y ensayos antes del CDR}")
A(tabla(["Pendiente", "Por qué", "Cómo se cierra"], [
    ["Propiedades del laminado", "El modo de 349\\,Hz depende del módulo real de carbono y vidrio con laminado manual",
     "Probetas y un tubo de prueba: medir espesor, módulo y masa; post-curado $> 60$\\,\\textdegree C (ensayo térmico)"],
    ["Bordes de las ranuras", "Concentración de tensiones en los extremos de las ranuras de 192\\,mm",
     "Cinta de vidrio en los bordes; FEM con malla fina"],
    ["Modo y amortiguamiento reales", "El ensayo se analizó con $\\zeta = 2$\\,\\%",
     "Ensayo con la lijadora sobre el prototipo con acelerómetro: verificar que no haya resonancia por debajo de 233\\,Hz"],
    ["Anclaje del paracaídas", "265\\,N en el ensayo de caída", "Ensayo de caída de 61\\,cm; confirmar que el lazo de Dyneema no carga"],
    ["Equilibrio y estabilidad de la vela", "Sin cola, el ángulo de equilibrio depende del centro de gravedad y de la holgura de la tela",
     "Lanzamientos de la vela con lastre móvil; medir la velocidad de descenso"],
    ["Cámaras en las dos fases", "En planeo el eje del cuerpo queda casi horizontal",
     "Verificar los campos de visión a cenit y nadir con la actitud de planeo ($\\gamma \\approx 36^\\circ$)"],
    ["Masa de la electrónica", "Asignaciones de EPS y C\\&DH", "Pesar las placas reales; actualizar el lastre"],
], r"P{3.2cm}LL", tam=r"\footnotesize"))

A(r"\end{document}")
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(T) + "\n")
print("ok", sys.argv[2])
