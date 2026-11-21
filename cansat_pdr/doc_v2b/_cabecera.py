"""Funciones y preambulo LaTeX compartidos con la memoria v3."""
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
\usepackage{amsmath,amssymb,textcomp,array,tabularx,longtable,booktabs,enumitem,microtype,fancyhdr,titlesec,graphicx,float,caption}
\usepackage[table]{xcolor}
\usepackage[most]{tcolorbox}
\usepackage[colorlinks=true,linkcolor=azul,urlcolor=azul]{hyperref}
\definecolor{azul}{HTML}{1F4E79}\definecolor{celeste}{HTML}{DCE6F2}\definecolor{rojo}{HTML}{C00000}
\definecolor{rosa}{HTML}{FBE9E9}\definecolor{gris}{HTML}{595959}\definecolor{fondoec}{HTML}{F3F6FA}
\newcommand{\diam}{\ensuremath{\varnothing}}
\graphicspath{{../figs/}}
\captionsetup{font=small,labelfont={bf,color=azul}}
\newcommand{\fig}[3]{\begin{figure}[H]\centering\includegraphics[width=#1\linewidth]{#2}\caption{#3}\end{figure}}
\newcommand{\figdos}[5]{\begin{figure}[H]\centering\includegraphics[width=#1\linewidth]{#2}\hfill\includegraphics[width=#3\linewidth]{#4}\caption{#5}\end{figure}}
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
\pagestyle{fancy}\fancyhf{}\fancyfoot[R]{\small\color{gris}PDR-STR-REC-2026-v2B · Equipo Hermes · página \thepage}
\renewcommand{\headrulewidth}{0pt}\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}\setlist{nosep,leftmargin=1.4em}
\begin{document}
""")

