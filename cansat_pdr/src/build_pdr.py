"""Arma el PDR del subsistema mecanico (laminas 4:3, 720 x 540 pt) como HTML y lo imprime a PDF con Chromium.
Uso: python3 build_pdr.py            (lee ../fea/*.json, ../figs, ../planos)
"""
import os, sys, json, math, subprocess, html
from PIL import Image
import params as P

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIGS, FEA, PLANOS, BUILD = (os.path.join(BASE, d) for d in ("figs", "fea", "planos", "build"))
PDF = os.path.join(BASE, "PDR_Mecanica_Laminas.pdf")
os.makedirs(os.path.join(BUILD, "img"), exist_ok=True)

R = json.load(open(os.path.join(FEA, "resultados_fea.json")))
PL = json.load(open(os.path.join(FEA, "planeo.json")))
PL500 = json.load(open(os.path.join(FEA, "planeo_500g.json")))
POLH = json.load(open(os.path.join(FEA, "polhamus.json")))
MAS = json.load(open(os.path.join(FEA, "masas.json")))
ALA = json.load(open(os.path.join(FEA, "ala_desplegada.json")))
VER = json.load(open(os.path.join(FEA, "verificacion_viga.json")))
MARCAS = json.load(open(os.path.join(FIGS, "marcas.json")))
EJES = "xyz"
slides = []


# ------------------------------------------------------------------ utilidades
def n(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def ms(x):
    c = "ok" if x >= 0 else "bad"
    return f'<span class="{c}">{x:+.2f}</span>'.replace(".", ",")


def im(name, src_dir=FIGS, maxpx=1500, q=88):
    """Copia la imagen (reducida, JPEG) a build/img y devuelve (ruta relativa, ancho, alto)."""
    src = os.path.join(src_dir, name)
    dst = os.path.join(BUILD, "img", os.path.splitext(name)[0] + ".jpg")
    i = Image.open(src).convert("RGB")
    w0, h0 = i.size
    if max(i.size) > maxpx:
        i.thumbnail((maxpx, maxpx), Image.LANCZOS)
    i.save(dst, quality=q)
    return "img/" + os.path.basename(dst), w0, h0


def img(name, w=None, h=None, cap=None, src_dir=FIGS, maxpx=1500, style=""):
    p, w0, h0 = im(name, src_dir, maxpx)
    dim = (f"width:{w}pt;" if w else "") + (f"height:{h}pt;" if h else "")
    c = f'<div class="cap">{cap}</div>' if cap else ""
    return f'<div class="fig" style="{style}"><img src="{p}" style="{dim}">{c}</div>'


def anot(name, key, wi, izq=(), der=(), lw=118, fs=8.2, src_dir=FIGS, recorte=None):
    """Imagen con llamadas: izq/der = [(marca, texto)].  Flechas rojas y recuadros azules."""
    p, w0, h0 = im(name, src_dir)
    hi = wi * h0 / w0
    M = MARCAS[key]
    lwl = lw if izq else 0
    lwr = lw if der else 0
    W = lwl + wi + lwr
    out = [f'<svg class="anot" width="{W}pt" height="{hi}pt" viewBox="0 0 {W} {hi}">',
           f'<image href="{p}" x="{lwl}" y="0" width="{wi}" height="{hi}"/>']
    for lado, labs in (("i", izq), ("d", der)):
        labs = sorted(labs, key=lambda t: M[t[0]][1])
        k = len(labs)
        for j, (mk, txt) in enumerate(labs):
            lines = txt.split("\n")
            bh = 6 + len(lines) * (fs + 1.6)
            yc = hi * (j + 0.5) / k
            bx = 1 if lado == "i" else lwl + wi + 4
            bw = lw - 6
            px, py = lwl + M[mk][0] * wi, M[mk][1] * hi
            x1 = bx + bw if lado == "i" else bx
            out.append(f'<line x1="{x1}" y1="{yc}" x2="{px}" y2="{py}" stroke="#e02020" stroke-width="1.1"/>')
            out.append(f'<circle cx="{px}" cy="{py}" r="1.9" fill="#e02020"/>')
            out.append(f'<rect x="{bx}" y="{yc - bh / 2}" width="{bw}" height="{bh}" fill="#fff" stroke="#2f3192" stroke-width="1.2"/>')
            for li, t in enumerate(lines):
                ty = yc - bh / 2 + 3 + (li + 0.8) * (fs + 1.6)
                out.append(f'<text x="{bx + bw / 2}" y="{ty}" font-size="{fs}" text-anchor="middle">{html.escape(t)}</text>')
    out.append("</svg>")
    return "".join(out)


def tabla(cab, filas, anchos=None, cls="", fs=None, alin=None):
    st = f' style="font-size:{fs}pt"' if fs else ""
    o = [f'<table class="t {cls}"{st}>']
    if anchos:
        o.append("<colgroup>" + "".join(f'<col style="width:{a}pt">' for a in anchos) + "</colgroup>")
    if cab:
        o.append("<tr>" + "".join(f"<th>{c}</th>" for c in cab) + "</tr>")
    for f in filas:
        cl = ""
        if isinstance(f, dict):
            cl, f = f.get("cls", ""), f["f"]
        tds = []
        for j, c in enumerate(f):
            a = f' class="{alin[j]}"' if alin and alin[j] else ""
            tds.append(f"<td{a}>{c}</td>")
        o.append(f'<tr class="{cl}">' + "".join(tds) + "</tr>")
    o.append("</table>")
    return "".join(o)


def ul(items, cls=""):
    return f'<ul class="{cls}">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def cols(*c, gap=14, w=None, align="flex-start"):
    w = w or [None] * len(c)
    return (f'<div class="cols" style="gap:{gap}pt;align-items:{align}">'
            + "".join(f'<div style="{"flex:0 0 %spt" % wi if wi else "flex:1"}">{x}</div>' for x, wi in zip(c, w)) + "</div>")


def caja(titulo, cuerpo, cls=""):
    return f'<div class="caja {cls}"><div class="ct">{titulo}</div><div class="cc">{cuerpo}</div></div>'


def nota(t):
    return f'<div class="nota">{t}</div>'


LOGO = ('<svg width="54" height="54" viewBox="0 0 54 54"><rect x="1" y="1" width="52" height="52" rx="9" fill="#1d2046"/>'
        '<polygon points="27,9 46,40 27,33 8,40" fill="#e67e22"/><polygon points="27,9 30,34 27,33 24,34" fill="#fff"/>'
        '<text x="27" y="49" font-size="6.6" fill="#fff" text-anchor="middle" font-weight="700">ALA DELTA</text></svg>')
COMP = ('<div class="comp"><div class="c1">CANSAT</div><div class="c2">ARGENTINA</div>'
        '<div class="c3">UNIVERSITARIO 2026/27</div></div>')


def slide(titulo, cuerpo, cls=""):
    slides.append((titulo, cuerpo, cls))


def separador(titulo, sub=""):
    slides.append((None, f'<div class="sep"><div class="st">{titulo}</div><div class="ss">{sub}</div></div>', "sepslide"))


def M_(caso, eje=None):
    d = R[caso] if eje is None else R[caso][eje]
    return d["margenes"]


def peor(caso, clave_grupo, crit=None):
    """MS minimo sobre los ejes (y criterios) de un grupo. Devuelve (MS, sigma, eje, criterio, extra)."""
    best = None
    ejes = [None] if caso == "paracaidas" else list(EJES)
    for e in ejes:
        for k, v in M_(caso, e).items():
            g, c = [s.strip() for s in k.split("|")]
            if not g.startswith(clave_grupo) or (crit and c != crit):
                continue
            if best is None or v["MS"] < best[0]:
                best = (v["MS"], v["sigma"], e or "x", c, v)
    return best


GRUPOS = ["Contenedor: tubo", "Contenedor: tapa", "Cuadernas", "Paneles y bandeja", "Largueros", "PCB", "Soportes de equipos",
          "Llave de bayoneta"]
GNOM = {"Contenedor: tubo": "Tubo del contenedor (LW-PLA)", "Contenedor: tapa": "Tapa nervada (PA12-CF)",
        "Cuadernas": "Cuadernas, cunas y guías (PA12-CF)", "Paneles y bandeja": "Paneles y bandeja (G10)",
        "Largueros": "Largueros (CFRP)", "PCB": "PCB (FR-4)", "Soportes de equipos": "Separadores y sillas (PA12-CF)",
        "Llave de bayoneta": "Llave de bayoneta (A2-70)"}
CNOM = {"von Mises": "von Mises", "sigma_x entre capas": "σx entre capas", "sigma_x fibra": "σx de fibra",
        "corte interlaminar": "corte interlaminar"}


# ======================================================================= datos derivados
G0 = P.G0
m_plan = MAS["m_planeador"]
m_cont = MAS["m_contenedor"]
F_ret = m_plan / 1000 * P.N_SHOCK * G0 * 1.8            # N, retencion del planeador (30 g x FAD)
F_par = P.M_TOT / 1000 * P.N_SHOCK * G0 * 1.8           # N, tiron del paracaidas sobre todo el CanSat
f = R["freq"]
zeta = R["zeta"]
Q = 1 / (2 * zeta)
mef = R["m_eff"]


def modo_dom(d):
    i = max(range(len(f)), key=lambda k: mef[k][d])
    return i, f[i], mef[i][d] / R["masa_g"] * 100


def desc_modo(i):
    fr = [mef[i][d] / R["masa_g"] * 100 for d in range(3)]
    if max(fr) < 2:
        return "local / torsión"
    d = fr.index(max(fr))
    return ["axial X", "lateral Y", "lateral Z"][d]


# ======================================================================= laminas
slides.append((None, f'''
<div class="portada">
 <div class="p0">{LOGO.replace('width="54" height="54"', 'width="92" height="92"')}</div>
 <div class="p1">CanSat Argentina Universitario {P.TEMPORADA}</div>
 <div class="p2">Revisión Preliminar de Diseño (PDR)</div>
 <div class="p3">Subsistema mecánico y estructural</div>
 <div class="p4">CanSat de ala delta de membrana · contenedor Ø90 × 242 mm · 500 g</div>
 <div class="p5">{P.EQUIPO}<br>Revisión {P.REV} · {P.FECHA}</div>
</div>''', "portadaslide"))

slide("Contenido", tabla(["Sección", "Qué responde", "Láminas"], [
    ["1. Requisitos y alcance", "Qué exige el Apéndice A al subsistema mecánico y qué requisitos derivamos", "4 – 6"],
    ["2. Configuración del sistema", "Por qué contenedor + planeador; dimensiones; concepto de operaciones", "7 – 14"],
    ["3. Materiales", "Comparación y selección por pieza", "15 – 16"],
    ["4. Estructura y mecanismos", "Bastidor, contenedor, anclaje del paracaídas, liberación, ala y su despliegue", "17 – 27"],
    ["5. Análisis estructural", "Modelo FEA, modos, respuesta en frecuencia a 15 G, choque de 30 G, márgenes", "28 – 43"],
    ["6. Masa, ensayos y riesgos", "Presupuesto de masa, plan de ensayos, riesgos, cumplimiento", "44 – 50"],
    ["Anexo: planos", "Siete hojas A3 (CS-MEC-01 a 07)", "51 – 57"],
], [150, 400, 70], fs=11.5) + nota(
    "Todo lo que se muestra sale de un único modelo paramétrico (<b>src/params.py</b>): CAD, planos, malla, análisis y "
    "este documento se regeneran con <b>make</b>. Las masas no estructurales son asignaciones a confirmar por cada subsistema."))

slide("Acrónimos y convenciones", cols(
    tabla(["Sigla", "Significado"], [
        ["A / I / T / D", "Verificación por Análisis / Inspección / Ensayo / Demostración"],
        ["BA, BF", "Borde de ataque, borde de fuga"],
        ["CFRP", "Polímero reforzado con fibra de carbono (tubo pultruido)"],
        ["CG", "Centro de gravedad"],
        ["FAD", "Factor de amplificación dinámica"],
        ["FEA", "Análisis por elementos finitos"],
        ["FS, MS", "Factor de seguridad; margen de seguridad = σ<sub>adm</sub>/(FS·σ) − 1"],
        ["G10 / FR-4", "Laminado de fibra de vidrio y epoxi"],
        ["LW-PLA", "PLA espumado de baja densidad (impresión 3D)"],
        ["PA12-CF", "Poliamida 12 con fibra corta de carbono (impresión 3D)"],
        ["SRS", "Espectro de respuesta al choque"],
        ["ζ, Q", "Amortiguamiento modal; Q = 1/(2ζ)"],
    ], [78, 250], fs=9.3),
    caja("Sistema de coordenadas del vehículo",
         "<b>x</b>: eje del cuerpo, de la nariz (x = 0) hacia la cola.<br><b>y</b>: envergadura, positivo a la derecha.<br>"
         "<b>z</b>: hacia arriba en vuelo.<br><br>En el cohete y bajo el paracaídas el eje x queda vertical, con la nariz "
         "hacia abajo: «axial» es siempre x.<br><br>Las cuadernas se numeran de nariz a cola: C1 a C4. A, J, T y B son "
         "los cuatro pernos del ala (ápice, articulación, punta y tirante).")
    + img("des_iso.png", w=250), w=[340, None]))

# ---------------------------------------------------------------- requisitos
separador("1. Requisitos y alcance", "Apéndice A – Requisitos de misión (CONAE)")
X = "✕"
req1 = [
    ["C1", "El contenedor va montado dentro del fuselaje del cohete, en la parte superior.", "Contenedor cilíndrico Ø90 liso, sin salientes.", "", X, "", ""],
    ["C2", "Carga útil y contenedor se despliegan con la carga de expulsión del motor.", "Salen juntos; el planeador va trabado adentro.", "", "", X, X],
    ["C3", "Descenso a 15 ± 3 m/s con paracaídas de apertura automática.", "Paracaídas alojado sobre la tapa; brida de 3 puntos.", X, "", X, ""],
    ["C4", "Al 80 % de la altitud máxima se libera otro sistema de descenso: 5 ± 3 m/s en promedio.", "Planeador de ala delta; estimado " + n(MAS["w_estimado"], 1) + " m/s.", X, "", X, X],
    ["C6 / C7", "Video de todo el descenso apuntando a cenit y a nadir.", "Soportes de cámara arriba y abajo del planeador.", "", X, "", X],
    ["S1", "Masa combinada de CanSat y contenedor: 500 ± 10 g.", "Presupuesto: 500 g con " + n(MAS["lastre"], 0) + " g de lastre/margen.", X, X, "", ""],
    ["S2", "Diámetro del CanSat: 90 mm.", "Contenedor Ø90,0.", "", X, "", ""],
    ["S3", "Longitud total, con los sistemas de descenso: 200 a 250 mm.", f"Contenedor de {P.CT_LEN:g} mm con el paracaídas adentro.", "", X, "", ""],
    ["S4", "La estructura debe soportar vibraciones de 15 G.", "FEA: casi-estático y barrido senoidal de 15 G en 3 ejes.", X, "", X, ""],
    ["S5", "El CanSat debe soportar un choque de 30 G.", "FEA: semiseno de 30 G en 3 ejes + tirón del paracaídas.", X, "", X, ""],
]
cab_req = ["N.º", "Requisito", "Cómo lo cumple el diseño", "A", "I", "T", "D"]
slide("Requisitos del subsistema mecánico (1/2)", tabla(cab_req, req1, [40, 268, 268, 18, 18, 18, 18], fs=9.4,
                                                        alin=[None, None, None, "c", "c", "c", "c"]))
req2 = [
    ["S6", "Pared exterior de al menos 2 mm si se imprime en 3D; no debe flexionarse ni deformarse.", "Tubo impreso con pared de 2,0 mm; flecha calculada por FEA.", X, X, "", ""],
    ["S7", "El cilindro puede sujetar piezas desplegables, pero debe deslizar libre fuera del cohete.", "La pared retiene las alas plegadas; exterior liso.", "", X, "", X],
    ["S8", "Componentes montados de forma fija: separadores, tornillos o adhesivos de alto rendimiento.", "Separadores M2,5, tornillos M2 con inserto, epoxi estructural.", "", X, "", ""],
    ["S9", "Materiales del contenedor no contaminantes.", "LW-PLA (base biológica) y PA12-CF; sin metales pesados.", "", X, "", ""],
    ["M1", "Sin actuadores pirotécnicos ni químicos.", "Solo servos y resortes.", "", X, "", ""],
    ["M2", "Mecanismos con calor no expuestos al exterior.", "No se usan mecanismos térmicos.", "", X, "", ""],
    ["M3", "Los mecanismos mantienen su configuración bajo todas las fuerzas.", "Llave de bayoneta: la carga no pasa por el servo. Manguito con traba.", X, "", X, ""],
    ["M4", "Sin contactos de resorte para las baterías.", "Celda 18650 con lengüetas soldadas, en sillas con cincha.", "", X, "", ""],
    ["E3", "Uno o más paneles solares que reciban radiación.", "Celdas sobre la tapa superior de G10 del planeador.", "", X, "", ""],
    ["E4 – E6", "Interruptor accesible a través del contenedor; orificios de hasta 10 mm; indicador de encendido.", "Orificios Ø8 (interruptor) y Ø5 (LED) en la pared.", "", X, "", ""],
]
slide("Requisitos del subsistema mecánico (2/2)", tabla(cab_req, req2, [40, 268, 268, 18, 18, 18, 18], fs=9.4,
                                                        alin=[None, None, None, "c", "c", "c", "c"]))
slide("Requisitos derivados", tabla(["N.º", "Requisito derivado", "Origen", "Valor de diseño"], [
    ["RD-1", "El planeador estibado cabe en un cilindro Ø84, con 1 mm de huelgo radial a la pared interior.", "S2, S6, S7", f"Ø{2 * P.RB:g} (varillas hasta R 41,9)"],
    ["RD-2", "El ala respeta la geometría de la nota de membrana: cuerda de raíz 198,6 mm, flecha 45°, S = 394 cm².", "C4", f"A–B = {n(P.D_AB)} mm · S = {P.S_TRI:.0f} cm²"],
    ["RD-3", "El largo del planeador deja lugar a los pernos de pivote sin recortar el ala.", "S3, RD-2", f"{P.L_G:g} mm (pernos a 4,2 mm de cada extremo)"],
    ["RD-4", "Factores de seguridad: 1,25 a fluencia en metales, 1,5 en laminados, 2,0 en piezas impresas. MS ≥ 0.", "S4, S5", "Aplicados en todos los márgenes"],
    ["RD-5", "La retención del planeador soporta 30 G × FAD 1,8 sin que la carga pase por el servo.", "S5, M3", f"{F_ret:.0f} N por la llave de bayoneta"],
    ["RD-6", "Las frecuencias propias en lanzamiento quedan por encima de 100 Hz.", "S4", f"f₁ = {f[0]:.0f} Hz"],
    ["RD-7", "Masa de vuelo (CanSat completo) compatible con 5 ± 3 m/s con S = 394 cm².", "C4, S1", f"500 g → {n(MAS['w_estimado'], 1)} m/s"],
], [44, 330, 70, 210], fs=10) + nota(
    "S4 y S5 no dicen cómo se aplica la carga. Los interpretamos así: <b>15 G</b> como aceleración casi-estática y como amplitud "
    "de un barrido senoidal de 5 a 1000 Hz en la base; <b>30 G</b> como pulso semiseno en la base (11 ms nominal, se barre la "
    "duración) y como tirón del paracaídas. Es la lectura más exigente que encontramos; conviene confirmarla con la organización."))

# ---------------------------------------------------------------- configuracion
separador("2. Configuración del sistema", "Arquitectura, dimensiones y concepto de operaciones")
slide("Resumen del subsistema mecánico", cols(
    anot("lan_corte.png", "lan", 190, izq=[("paracaidas", "Paracaídas\n15 m/s"), ("llave", "Llave de\nbayoneta"), ("bateria", "Batería 18650"),
                                           ("lastre", "Lastre de\ncentrado"), ("boca", "Boca abierta\n(salida)")],
         der=[("tapa", "Tapa nervada\nPA12-CF"), ("tubo", "Contenedor\nLW-PLA 2 mm"), ("pcb", "PCB principal"),
              ("ala", "Ala plegada"), ("c1", "Cuaderna C1")], lw=92, fs=7.8),
    tabla(["Conjunto", "Piezas", "Material", "Masa [g]"], [
        ["Contenedor", "Tubo Ø90 × 242, pared 2", "LW-PLA impreso", n(next(x["masa"] for x in MAS["filas"] if "Tubo" in x["item"]))],
        ["", "Tapa nervada", "PA12-CF impreso", n(next(x["masa"] for x in MAS["filas"] if "Tapa nervada" in x["item"]))],
        ["Bastidor", "4 cuadernas C1–C4", "PA12-CF impreso", n(sum(x["masa"] for x in MAS["filas"] if "Cuaderna" in x["item"]))],
        ["", "4 largueros Ø5/3,5", "CFRP pultruido", n(next(x["masa"] for x in MAS["filas"] if "Largueros" in x["item"]))],
        ["", "Paneles, tapa y bandeja", "G10 0,5 / 0,8", n(sum(x["masa"] for x in MAS["filas"] if "G10" in x["item"]))],
        ["Ala", "Varillas, tirantes, herrajes", "CFRP / Al 7075", n(MAS["sub"]["Ala de membrana"]["masa"])],
        ["", "Membrana", "Ripstop 40 g/m²", "incl."],
        ["Liberación", "Llave de bayoneta + servo", "Inox A2-70", "14"],
    ], [62, 128, 92, 46], fs=9.2)
    + ul([f"Masa total: <b>500 g</b> (contenedor {m_cont:.0f} g + planeador {m_plan:.0f} g).",
          f"Estructura primaria del planeador: {MAS['sub']['Estructura del planeador']['masa']:.0f} g.",
          "Un solo actuador para liberar; el ala se abre sola al salir del cilindro."], "s"),
    w=[376, None]))

slide("Configuración del sistema: comparación", cols(
    caja("A · Cuerpo integral con ranuras",
         img("opcion_a.png", h=150) + ul([
             "El cilindro Ø90 es el fuselaje; las alas salen por dos ranuras laterales de 16 × 200 mm.",
             "Vuela con los 500 g completos.",
             "<b>Contra:</b> las ranuras son aberturas mucho mayores que los 10 mm de E5 y debilitan la pared que S6 pide rígida.",
             "<b>Contra:</b> las alas quedan expuestas a la eyección y pueden trabarse en el fuselaje (S7).",
             "<b>Contra:</b> hacen falta trabas y un actuador para soltar las alas."], "s")),
    caja("B · Contenedor + planeador &nbsp;<span class='sel'>Seleccionada</span>",
         cols(img("cont_cerrado.png", h=150), img("des_iso.png", h=150), gap=4) + ul([
             "Contenedor cerrado Ø90 con pared de 2 mm; el planeador sale por la boca inferior.",
             "La pared retiene las alas plegadas: el despliegue es pasivo (S7).",
             "Exterior liso; solo dos orificios de 8 y 5 mm (E5).",
             f"El planeador vuela con {m_plan:.0f} g: menor carga alar, más margen para los 5 m/s.",
             f"<b>Contra:</b> el contenedor ({m_cont:.0f} g con paracaídas) no vuela con el planeador."], "s")),
))
slide("Configuración del sistema: selección", tabla(
    ["Criterio", "Peso", "A · Cuerpo integral con ranuras", "B · Contenedor + planeador"], [
        ["Pared exterior ≥ 2 mm y rígida (S6)", "Alto", "Parcial: pared cortada en dos tejas", "Cumple: tubo cerrado"],
        ["Deslizamiento libre fuera del cohete (S7)", "Alto", "Riesgo: varillas contra el fuselaje", "Cumple: exterior liso"],
        ["Orificios de hasta 10 mm (E5)", "Medio", "No cumple (ranuras de 16 × 200)", "Cumple (Ø8 y Ø5)"],
        ["Despliegue del ala", "Alto", "Activo: trabas + servo", "Pasivo: resortes"],
        ["Protección del ala en la eyección (S5)", "Medio", "Expuesta", "Protegida por el tubo"],
        ["Masa que vuela con el ala", "Medio", "500 g", f"{m_plan:.0f} g si se separa; 500 g si no"],
        ["Velocidad de descenso estimada (C4)", "Alto", f"{n(MAS['w_estimado'], 1)} m/s con 500 g", f"{n(MAS['w_planeador_solo'], 1)} m/s con {m_plan:.0f} g; {n(MAS['w_estimado'], 1)} con 500 g"],
        ["Mecanismos críticos", "Medio", "Trabas de ala + suelta del drogue", "Una llave de bayoneta"],
        ["Objetos que descienden", "Bajo", "Uno", "Dos (contenedor con paracaídas)"],
    ], [200, 46, 205, 205], fs=10) + cols(
    caja("Seleccionada: B", "Es la única que cumple S6, S7 y E5 al pie de la letra, simplifica el despliegue y baja la carga alar. "
         "El costo es que el contenedor desciende aparte con su paracaídas."),
    caja("Si el equipo prefiere A", "El bastidor, el ala y el análisis del planeador valen igual: el tubo se parte en dos tejas "
         "atornilladas a C1 y C4. Habría que rehacer el análisis del tubo ranurado."), gap=12) + nota("<b>Conflicto con la masa de vuelo.</b> Los 500 g del CanSat completo tienen que bajar con el ala, y en esta revisión el contenedor "
         f"({m_cont:.0f} g) se separa: el planeador vuela con {m_plan:.0f} g. Con 500 g la opción B no sirve como está dibujada; hay que volver al cuerpo integral (A) "
         "o hacer que el contenedor baje con el ala. Pendiente de decisión y de rehacer la estructura."))

slide("Layout físico (1/3): configuración de lanzamiento", img("lay_lanzamiento.png", w=676) + cols(
    ul([f"Diámetro exterior <b>90,0 mm</b> (S2) y largo total <b>{P.CT_LEN:g} mm</b>, con el paracaídas adentro (S3: 200 a 250).",
        "Pared exterior de <b>2,0 mm</b> (S6). Diámetro interior 86 mm.",
        f"El planeador mide {P.L_G:g} mm y Ø{2 * P.RB:g}: queda 1 mm de huelgo radial, que toman 8 patines de PTFE."], "s"),
    ul([f"La nariz queda {abs(P.CT_X[0]):g} mm adentro de la boca: en el lanzamiento no apoya contra el cohete.",
        f"Tapa nervada de {P.CT_CAP_H:g} mm a {P.CT_TOP[0] - P.CT_X[0]:g} mm de la boca; arriba quedan "
        f"{P.CT_X[1] - P.CT_TOP[0] - P.CT_CAP_H:g} mm para el paracaídas plegado.",
        "Todas las cotas en milímetros. Plano CS-MEC-01."], "s")))
slide("Layout físico (2/3): planeador estibado", cols(img("lay_estibado.png", w=470),
      ul([f"Caja central de {n(2 * P.Y_OUT)} × {n(2 * P.Z_BOX + P.T_COVER)} mm entre cuadernas de Ø{2 * P.RB:g}.",
          "Las alas se pliegan en los dos gajos laterales, fuera de la caja de aviónica.",
          f"Pivotes A y B a {n(P.X_A)} mm de cada extremo: <b>{n(P.D_AB)} mm</b> entre pernos, la cuerda de raíz de la nota de membrana.",
          "El botalón de cola va estibado sobre la tapa superior, guiado en C2, C3 y C4.",
          "Tres compartimentos: nariz (lastre, servo de cola), central (batería, PCB principal) y cola (radio/GNSS, servo del cerrojo).",
          "Plano CS-MEC-02."], "s"), w=[474, None]))
slide("Layout físico (3/3): planeador desplegado", cols(img("lay_desplegado.png", h=408),
      tabla(["Parámetro", "Valor"], [
          ["Envergadura", f"{n(P.SPAN)} mm"], ["Cuerda de raíz (A–B)", f"{n(P.D_AB)} mm"],
          ["Borde de ataque (A–T)", f"{n(P.L_LE)} mm"], ["Tramos del borde de ataque", f"2 × {n(P.L_SEG)} mm"],
          ["Flecha", "45°"], ["Área (dos triángulos)", f"{P.S_TRI:.0f} cm²"],
          ["Área de tela con franja de raíz", f"{P.S_WING:.0f} cm²"], ["Alargamiento", "4,0"],
          ["Masa de vuelo (CanSat completo)", "500 g"], ["Carga alar", f"{n(MAS['carga_alar'], 0)} N/m²"],
      ], [150, 100], fs=9.6) + nota(
          "La cola en V y el botalón son geometría de referencia de la nota de cola. La franja de tela entre la varilla de "
          "raíz y la línea de pivotes agrega 18 cm² que la nota no contaba."), w=[410, None]))

slide("Ubicación de componentes", anot("equipos.png", "equipos", 430,
      izq=[("c1", "Cuaderna C1\n(pivotes A)"), ("lastre", "Lastre de centrado\n(asignación)"), ("servo_cola", "Servo de cola"),
           ("bandeja", "Bandeja de aviónica\nG10 0,8"), ("pcb", "PCB principal\n(bajo la bandeja)")],
      der=[("larguero", "Larguero CFRP\nØ5/3,5"), ("bateria", "Batería 18650\nsobre sillas"), ("pcb_radio", "PCB radio / GNSS"),
           ("c4", "Cuaderna C4\n(pivotes B)"), ("servo_cerrojo", "Servo del cerrojo"), ("llave", "Llave de bayoneta")], lw=120)
      + nota("Se ocultaron el panel lateral izquierdo, la tapa superior y las alas. Las masas y envolventes de la electrónica son "
             "asignaciones; el montaje se ajusta cuando el subsistema eléctrico congele las placas."))

slide("Concepto de operaciones mecánico", img("conops.png", w=676) + tabla(
    ["Fase", "Carga que dimensiona", "Qué trabaja"], [
        ["1 · Lanzamiento", "15 G axial y vibración", "Llave de bayoneta, tapa, tubo en compresión"],
        ["2 · Eyección y 3 · apertura del paracaídas", "Choque de 30 G", "Brida, tapa nervada, llave, cuaderna C4"],
        ["5 · Despliegue del ala", "Presión de apertura 3 × la de vuelo (367 Pa)", "Varillas, manguito, pivotes A y B"],
        ["6 · Planeo", "122 Pa sobre la membrana", "Varillas y tirante (pandeo)"],
    ], [200, 220, 236], fs=9.4))

_n = PL["nominal"]["cuerpo romo (disco de nariz plano)"]
_o = PL["nominal"]["con ojiva en la nariz"]
slide("Velocidad de descenso del planeador (C4)", img("planeo.png", w=676) + tabla(
    ["Configuración", "C_L", "C_D", "L/D", "w nominal [m/s]", "w 5–95 % [m/s]", "Alcance desde 400 m"], [
        ["Delta, α = 20°, f = 0,5", n(_n["delta"]["CL"], 2), n(_n["delta"]["CD"], 2), n(_n["delta"]["LD"], 1), n(_n["delta"]["w"], 1),
         f"{n(PL['mc']['delta']['p'][0], 1)} a {n(PL['mc']['delta']['p'][2], 1)}", f"{400 * _n['delta']['LD']:.0f} m"],
        ["Avión recto (referencia), C_L = 0,8", n(_n["recta"]["CL"], 2), n(_n["recta"]["CD"], 2), n(_n["recta"]["LD"], 1), n(_n["recta"]["w"], 1),
         f"{n(PL['mc']['recta']['p'][0], 1)} a {n(PL['mc']['recta']['p'][2], 1)}", f"{400 * _n['recta']['LD']:.0f} m"],
    ], [180, 40, 40, 40, 100, 100, 110], fs=9.2, alin=[None, "c", "c", "c", "c", "c", "c"]) + nota(
    f"CanSat completo de {PL['masa_g']:.0f} g con S = 394 cm² y 20° de alabeo. Cuerpo romo del diseño incluido. "
    f"Con ojiva en la nariz: delta {n(_o['delta']['w'], 1)} m/s, avión {n(_o['recta']['w'], 1)} m/s. Polhamus está fuera de su rango "
    "de validez (alargamiento 4, ensayado hasta 2): los rangos son juicio del autor. El avión recto no está diseñado."))
slide("Compatibilidad con el cohete", cols(
    tabla(["Verificación", "Valor", "Requisito"], [
        ["Diámetro exterior", "90,0 mm", "S2: 90 mm"],
        ["Largo total", f"{P.CT_LEN:g} mm", "S3: 200 a 250 mm"],
        ["Salientes fuera del cilindro", "Ninguna", "S7"],
        ["Orificios en la pared", "Ø8 y Ø5", "E5: ≤ 10 mm"],
        ["Pared exterior impresa", "2,0 mm", "S6: ≥ 2 mm"],
        ["Masa total", "500 g", "S1: 500 ± 10 g"],
        ["Rugosidad exterior", "Lijado, sin costura", "S7 (deslizamiento)"],
    ], [150, 90, 110], fs=10)
    + ul(["El contenedor es un cilindro liso: no hay nada que pueda engancharse en el fuselaje.",
          "El paracaídas va plegado dentro del borde superior, por debajo del canto del tubo.",
          "Ensayo previsto: pasar el CanSat armado por un calibre Ø90,5 y dejarlo salir por su propio peso."], "s"),
    img("cont_cerrado.png", h=330), w=[380, None]))

# ---------------------------------------------------------------- materiales
separador("3. Materiales", "Comparación y selección por pieza")
MT = P.MAT
slide("Materiales: comparación", tabla(
    ["Material", "Densidad [g/cm³]", "E [GPa]", "Resistencia [MPa]", "Entre capas [MPa]", "A favor", "En contra"], [
        ["PLA+ impreso", n(MT["PLA"]["rho"], 2), n(MT["PLA"]["E"] / 1e3, 1), f'{MT["PLA"]["Sut"]:.0f}', f'{MT["PLA"]["Sut_z"]:.0f}', "Fácil de imprimir, rígido", "Frágil; ablanda a 55 °C"],
        ["PETG impreso", n(MT["PETG"]["rho"], 2), n(MT["PETG"]["E"] / 1e3, 1), f'{MT["PETG"]["Sut"]:.0f}', f'{MT["PETG"]["Sut_z"]:.0f}', "Tenaz, buena unión entre capas", "Pesado y poco rígido"],
        ["<b>PA12-CF impreso</b>", n(MT["PA12CF"]["rho"], 2), n(MT["PA12CF"]["E"] / 1e3, 1), f'{MT["PA12CF"]["Sut"]:.0f}', f'{MT["PA12CF"]["Sut_z"]:.0f}', "Mejor rigidez y resistencia por gramo; aguanta 150 °C", "Hay que secarlo; boquilla endurecida"],
        ["<b>LW-PLA espumado</b>", n(MT["LWPLA"]["rho"], 2), n(MT["LWPLA"]["E"] / 1e3, 1), f'{MT["LWPLA"]["Sut"]:.0f}', f'{MT["LWPLA"]["Sut_z"]:.0f}', "La mitad de densidad; base biológica (S9)", "Poca resistencia; ablanda a 55 °C"],
        ["ASA-LW espumado", n(MT["ASALW"]["rho"], 2), n(MT["ASALW"]["E"] / 1e3, 2), f'{MT["ASALW"]["Sut"]:.0f}', f'{MT["ASALW"]["Sut_z"]:.0f}', "Liviano; aguanta sol y 95 °C", "El más débil; no es de base biológica"],
        ["<b>G10 / FR-4 en placa</b>", n(MT["G10"]["rho"], 2), n(MT["G10"]["E"] / 1e3, 0), f'{MT["G10"]["Sut"]:.0f}', "—", "Muy rígido en lámina fina; transparente a RF", "Denso; polvo al cortar"],
        ["<b>CFRP pultruido (tubo)</b>", n(MT["CFRP"]["rho"], 2), n(MT["CFRP"]["E"] / 1e3, 0), f'{MT["CFRP"]["Suc"]:.0f} (compr.)', "50 (corte)", "Máxima rigidez específica", "Conductor: lejos de las antenas"],
        ["<b>Aluminio 7075-T6</b>", n(MT["AL7075"]["rho"], 2), n(MT["AL7075"]["E"] / 1e3, 0), f'{MT["AL7075"]["Sy"]:.0f} (fluencia)', "—", "Herrajes chicos de precisión", "Mecanizado"],
    ], [112, 58, 42, 70, 58, 170, 150], fs=8.9) + nota(
    "Valores típicos de hojas de datos de fabricantes. <b>Los de piezas impresas dependen de la máquina y del lote: hay que "
    "confirmarlos con probetas propias antes del CDR</b> (tracción en el plano y entre capas). Los márgenes de este PDR usan "
    "la resistencia entre capas cuando la carga cruza las capas. En negrita, los materiales seleccionados."))
slide("Materiales: selección por pieza", tabla(["Pieza", "Material", "Por qué"], [
    ["Tubo del contenedor", "LW-PLA, pared 2,0 mm", "S6 fija el espesor: con 2 mm manda la densidad. 87 g contra 173 g en PETG. Base biológica (S9)."],
    ["Tapa del contenedor", "PA12-CF, nervada", "Recibe la brida del paracaídas y la llave: es el punto de mayor carga concentrada."],
    ["Cuadernas C1–C4, cunas", "PA12-CF, 100 % de relleno", "Llevan los pivotes del ala y los bujes de los largueros; necesitan resistencia local."],
    ["Largueros", "Tubo CFRP Ø5/3,5", "El mismo tubo que el borde de ataque: una sola compra. Dan la rigidez axial y de flexión."],
    ["Paneles laterales y tapa", "G10 0,5 mm", "Almas de corte de la caja. Transparentes a RF: no tapan el GNSS ni la radio."],
    ["Bandeja de aviónica", "G10 0,8 mm", "Plano de montaje de toda la electrónica y alma horizontal."],
    ["Varillas del ala", "Tubo CFRP Ø5/3,5 y Ø3/2", "Dimensionadas por rigidez en la nota de membrana."],
    ["Manguito y herrajes del ala", "Aluminio 7075-T6", "Piezas chicas con ajuste deslizante y cargas de contacto."],
    ["Llave de bayoneta, pernos", "Inoxidable A2-70", "Corte y aplastamiento con sección mínima."],
    ["Patines de guía", "PTFE 1 mm", "Deslizamiento del planeador dentro del tubo."],
    ["Membrana", "Nailon ripstop 40 g/m²", "Rompe a ~4000 N/m contra 152 N/m de trabajo (nota de membrana)."],
    ["Uniones", "Epoxi estructural + M2 / M2,5 con inserto", "S8: adhesivo de alto rendimiento y tornillos."],
], [140, 150, 386], fs=9.3))

# ---------------------------------------------------------------- estructura y mecanismos
separador("4. Estructura y mecanismos", "Bastidor, contenedor, liberación y ala")
slide("Estructura del planeador: comparación", tabla(
    ["", "A · Monocasco impreso", "B · Varillas roscadas + discos", "C · Bastidor CFRP + G10 <span class='sel'>Seleccionada</span>"], [
        ["Descripción", "Tubo Ø84 de PETG de 2 mm con cuadernas pegadas", "4 varillas M3 de acero y 5 discos impresos", "4 largueros de carbono, 4 cuadernas PA12-CF, paneles de G10"],
        ["Masa estimada", "≈ 135 g", "≈ 140 g", f"{MAS['sub']['Estructura del planeador']['masa']:.0f} g (CAD)"],
        ["Salida de las alas", "Hay que ranurar el tubo: pierde rigidez", "Libre", "Libre: gajos laterales abiertos"],
        ["Rigidez", "Buena cerrado, pobre ranurado", "Baja a flexión y torsión", "Alta: caja cerrada por paneles"],
        ["Acceso a la electrónica", "Malo", "Bueno", "Bueno: tapa y paneles atornillados"],
        ["Transparencia a RF", "Buena", "Buena", "Buena (G10); el carbono queda en las aristas"],
        ["Fabricación", "Una impresión larga", "Muy simple", "Corte de placa + impresión + pegado"],
    ], [100, 180, 180, 216], fs=9.6) + nota(
    "Se elige C porque el ala necesita los gajos laterales abiertos, y una caja de paneles finos con largueros en las aristas es la "
    "forma más rígida de cerrar el resto. La masa es parecida a las otras dos; lo que mejora es la rigidez y el acceso."))
slide("Estructura primaria del planeador", cols(
    anot("bastidor_explotado.png", "bastidor", 330,
         izq=[("tapa", "Tapa superior\nG10 0,5"), ("c1", "C1 (nariz)"), ("p_lat", "Panel lateral\nG10 0,5"), ("bandeja", "Bandeja G10 0,8")],
         der=[("guia", "Guía de botalón"), ("c4", "C4 (cola)"), ("larguero", "Larguero CFRP"), ("c3", "C3"), ("cuna", "Cuna de ala")], lw=84, fs=7.6),
    ul(["<b>Largueros:</b> 4 tubos de carbono Ø5/3,5 × 201 mm. Pegados 5 mm en los bujes de C1 y C4 y pasantes en C2 y C3.",
        "<b>Cuadernas extremas C1 y C4:</b> 8 mm, alma de 1,6, aro y nervios. Llevan los pernos de pivote del ala dentro de su espesor.",
        "<b>Cuadernas C2 y C3:</b> marcos de 4 mm con aberturas de paso. Sostienen los paneles y las cunas del ala plegada.",
        "<b>Paneles:</b> dos laterales y la tapa cierran una caja en U; la bandeja la cierra por abajo a media altura.",
        "<b>Camino de carga axial:</b> llave → C4 → largueros y paneles → resto.",
        "<b>Camino lateral:</b> patines de C1 y C4 contra la pared del contenedor."], "s"), w=[505, None]))
slide("Cuadernas", cols(
    cols(img("c1.png", h=150, cap="C1 · nariz"), img("c4.png", h=150, cap="C4 · cola"), img("c2.png", h=150, cap="C2 / C3"), gap=2),
    "", w=[676, 0]) + cols(
    tabla(["", "C1", "C2 / C3", "C4"], [
        ["Espesor", "8 mm", "4 mm", "8 mm"], ["Forma", f"Disco Ø{2 * P.RB:g}", "Marco 54,5 × 62", f"Disco Ø{2 * P.RB:g}"],
        ["Masa", n(next(x["masa"] for x in MAS["filas"] if "nariz C1" in x["item"])) + " g",
         n(next(x["masa"] for x in MAS["filas"] if "C2 y C3" in x["item"]) / 2) + " g c/u",
         n(next(x["masa"] for x in MAS["filas"] if "cola C4" in x["item"])) + " g"],
        ["Función", "Pivotes A, cierre de nariz", "Apoyo de paneles y cunas", "Pivotes B, llave, botalón"],
    ], [60, 110, 110, 110], fs=9.4),
    ul(["Se imprimen acostadas, con las capas en el plano y–z: los nervios y el aro trabajan en el plano de capa.",
        "La carga axial cruza las capas; por eso los márgenes de las cuadernas se calculan con la resistencia entre capas (35 MPa).",
        "Ranura de 8 mm para el herraje del ala: en C1 a z = 0 y en C4 a z = −7 (el tirante pasa por debajo).",
        "Plano CS-MEC-05."], "s"), w=[400, None]))
tubo_m = next(x["masa"] for x in MAS["filas"] if "Tubo" in x["item"])
vol_tubo = tubo_m / MT["LWPLA"]["rho"]
slide("Contenedor: comparación y selección", cols(tabla(
    ["Opción", "Pared", "Masa del tubo", "S6", "S9", "Observación"], [
        ["PETG impreso", "2,0 mm", f"{vol_tubo * MT['PETG']['rho']:.0f} g", "Cumple", "Regular", "Un tercio de la masa total"],
        ["<b>LW-PLA impreso</b>", "2,0 mm", f"<b>{tubo_m:.0f} g</b>", "Cumple", "Bueno", "Seleccionada"],
        ["ASA-LW impreso", "2,0 mm", f"{vol_tubo * MT['ASALW']['rho']:.0f} g", "Cumple", "Regular", "Mejor al sol; más débil"],
        ["Tubo de fibra de vidrio", "0,6 mm", "≈ 75 g", "No aplica", "Regular", "Difícil de conseguir en Ø90"],
        ["Tubo de cartón kraft", "1,5 mm", "≈ 70 g", "No aplica", "Muy bueno", "Sensible a la humedad"],
    ], [118, 44, 70, 52, 50, 130], fs=9.4) + ul([
        "S6 fija 2 mm si la pared es impresa: lo único que se puede bajar es la densidad.",
        "El tubo es una sola pieza impresa de pie. Lleva solo dos orificios: Ø8 para el interruptor y Ø5 para el LED.",
        "La <b>tapa</b> es una pieza aparte de PA12-CF, con 6 nervios, pegada y con 3 tornillos radiales M2,5. "
        "La primera versión, de LW-PLA de 3 mm, daba margen negativo bajo la carga de la llave: el FEA motivó el cambio.",
        "El LW-PLA ablanda a unos 55 °C: contenedor blanco y a la sombra hasta el lanzamiento."], "s"),
    img("cont_iso.png", h=350), w=[476, None]))
leg = F_par / (3 * math.cos(math.radians(35)))
sb_brida = leg / (3.0 * P.CT_CAP_RIB)
tau_tapa = F_par / (math.pi * 2 * P.CT_RI * P.CT_CAP_H)
slide("Anclaje del paracaídas", cols(
    anot("cerrojo.png", "cerrojo", 300, izq=[("brida", "Anclaje de brida\n(Ø3 en el nervio)"), ("tapa", "Tapa nervada"), ("c4", "Cuaderna C4")],
         der=[("pasador", "Pasador Ø3\nde la llave"), ("llave", "Llave Ø5"), ("servo", "Servo del\ncerrojo")], lw=86, fs=7.6),
    ul(["<b>Brida de 3 puntos</b> de cordón de Kevlar de 1,5 mm, anudada a tres de los seis nervios de la tapa (a 120°), "
        "con eslabón giratorio hacia el paracaídas.",
        "La carga entra por la tapa y baja directo a la llave: el tubo de LW-PLA no participa del tirón.",
        f"Tirón de diseño: 500 g × 30 G × FAD 1,8 = <b>{F_par:.0f} N</b>.",
        f"Por ramal (a 35° del eje): {leg:.0f} N. Aplastamiento en el orificio del nervio: {n(sb_brida)} MPa contra "
        f"{MT['PA12CF']['Sut'] / 2:.1f} MPa admisibles → MS = {ms(MT['PA12CF']['Sut'] / 2 / sb_brida - 1)}.",
        f"Pegado tapa–tubo (faldón de {P.CT_CAP_H:g} mm): corte medio de {n(tau_tapa, 2)} MPa si todo el tirón pasara por ahí.",
        "Los tres puntos mantienen el eje del contenedor vertical, con la boca hacia abajo, para la salida del planeador."], "s"),
    w=[474, None]))
tau_pas = F_ret / (2 * math.pi * 1.5 ** 2)
sig_llave = F_ret / (math.pi * 2.5 ** 2)
sb_llave = F_ret / (2 * 3.0 * (P.CT_CAP_BOSS - 2.8))
T_fric = m_plan / 1000 * G0 * 0.3 * 5.0
slide("Liberación del planeador: comparación", tabla(
    ["", "A · Llave de bayoneta con servo <span class='sel'>Seleccionada</span>", "B · Hilo de nailon y nicrom", "C · Pasador con servo lineal"], [
        ["Principio", "Una llave en T gira 90° y pasa por el ojo de cerradura de la tapa", "Un hilo sostiene el planeador; una resistencia lo corta", "Un pasador radial se retira de un alojamiento"],
        ["Camino de carga", "Tracción en la llave; el servo solo ve fricción", "El hilo lleva todo", "Corte en el pasador; fricción contra el servo"],
        ["M2 (calor)", "No aplica", "Cumple si va cerrado; riesgo si queda expuesto", "No aplica"],
        ["M3 (mantener estado)", "Cumple: traba geométrica", "Cumple hasta que corta", "Depende del par del servo bajo carga"],
        ["Rearmable en campo", "Sí, en segundos", "No: hay que reenhebrar", "Sí"],
        ["Masa", "≈ 14 g con servo", "≈ 6 g", "≈ 16 g"],
    ], [100, 200, 188, 188], fs=9.4) + ul([
        f"Carga de retención: {m_plan:.0f} g × 30 G × 1,8 = <b>{F_ret:.0f} N</b>. Tracción en la llave Ø5: {n(sig_llave)} MPa. "
        f"Corte doble en el pasador Ø3: {n(tau_pas)} MPa (admisible 216 MPa). "
        f"Aplastamiento sobre el buje de la tapa: {n(sb_llave)} MPa → MS = {ms(MT['PA12CF']['Sut'] / 2 / sb_llave - 1)}.",
        f"Par para girar la llave colgando a 1 G: {n(T_fric)} N·mm (0,06 kg·cm) contra 1,8 kg·cm de un microservo: sobra más de 20 veces.",
        "Un fiador de bolilla marca la posición cerrada; un anillo de espuma entre C4 y la tapa quita el juego axial."], "s"))
slide("Estiba del ala: comparación", cols(tabla(
    ["", "A · Varilla entera", "B · Unión a 190 mm", "C · Articulación al medio <span class='sel'>Sel.</span>"], [
        ["Tramos", "1 × 280,9", "190 + 90,9", f"2 × {n(P.L_SEG)}"],
        ["Entra en 207 mm", "No", "Sí", "Sí"],
        ["Pliegue con el tirante fijo en B y T", "—", "No cierra: T queda a 99 mm de A", "Cierra plano: T cae sobre A"],
        ["Momento en la unión (choque)", "—", "≈ 365 N·mm", "424 N·mm"],
        ["Grados de libertad", "—", "Tirante suelto: 2", "1 (cuadrilátero A–J–T–B)"],
    ], [128, 78, 110, 130], fs=9.2) + ul([
        "Con <b>AJ = JT</b> y <b>BT = AB</b> el cuadrilátero pliega plano: todas las barras quedan alineadas sobre el costado "
        "del cuerpo y entran en el gajo de 14 mm.",
        "La nota de membrana proponía llevar la unión a 190 mm para bajar el momento. Eso rompe el pliegue: el tirante dejaría "
        "de estar unido a la punta. Preferimos dejar la articulación al medio y dimensionar el manguito para 424 N·mm.",
        "Desplegada, A–J–T queda alineada: es un punto muerto y sin traba la tela la cerraría. El manguito la traba."], "s"),
    img("est_iso.png", w=215, cap="Ala plegada en el gajo lateral"), w=[452, None]))
slide("Despliegue del ala", img("ala_mecanismo.png", w=676) + cols(
    ul(["<b>Pasivo:</b> mientras el planeador está en el contenedor, la pared sostiene las varillas. Al salir, un resorte de "
        "torsión en B abre el tirante y arrastra las dos mitades de la varilla.",
        "Un cordón elástico por dentro de los dos tramos los alinea, como en una vara de carpa.",
        "Al alinearse, el <b>manguito</b> de aluminio corre empujado por su resorte, cubre la articulación y la traba (M3)."], "s"),
    ul(["El pliegue real no es exactamente plano: los tramos quedan uno al lado del otro a 5,4 mm. La holgura de las "
        "articulaciones lo absorbe (0,07 mm en el largo del tirante).",
        "El par del resorte de torsión se define con el ensayo de apertura; valor de partida: 40 N·mm.",
        "Plano CS-MEC-06."], "s")))
pt, nt, vu = ALA["portico"], ALA["nota"], ALA["vuelo"]
slide("Ala: dimensionamiento de las varillas", img("ala_esfuerzos.png", w=676) + tabla(
    ["Caso (presión de apertura 367 Pa, panza 6 %)", "M ápice [N·mm]", "σ varilla [MPa]", "Flecha punta [mm]", "M en J [N·mm]", "N tirante [N]", "σ tirante [MPa]"], [
        ["Nota de membrana (valores publicados)", "680", "73", "4,9", "422", "9,79", "—"],
        ["Este modelo con las hipótesis de la nota", f"{nt['M_apice']:.0f}", f"{nt['sigma_LE']:.0f}", n(nt["flecha_z_punta"]), f"{nt['M_J']:.0f}", n(-nt["N_tirante"], 2), "—"],
        ["Este diseño: el tirante sostiene la punta", f"{pt['M_apice']:.0f}", f"{pt['sigma_LE']:.0f}", n(pt["flecha_z_punta"]), f"{pt['M_J']:.0f}", n(-pt["N_tirante"], 2), f"{pt['sigma_TE']:.0f}"],
    ], [232, 76, 76, 80, 70, 68, 74], fs=9.2) + nota(
    f"El modelo de pórtico reproduce la nota dentro del 1 %. Con el tirante unido a la punta por horquilla, el momento en el ápice "
    f"baja un {100 * (1 - pt['M_apice'] / nt['M_apice']):.0f} %, pero el tirante pasa a trabajar a flexión ({pt['sigma_TE']:.0f} MPa). "
    f"Varilla: MS = {ms(400 / pt['sigma_LE'] - 1)} con 400 MPa admisibles. Pandeo del tirante: P<sub>cr</sub>/N = {n(ALA['tirante']['coef'])}."))
M_ap = nt["M_apice"]
F_perno = M_ap / 8.0
sig_slv = nt["M_J"] * (P.SLV_DO / 2) / (math.pi * (P.SLV_DO ** 4 - P.SLV_DI ** 4) / 64)
p_slv = 6 * nt["M_J"] / (P.LE_DO * 15.0 ** 2)
slide("Ala: articulación y pivotes", cols(
    img("CS-MEC-06.png", w=330, src_dir=PLANOS, maxpx=2200, style="overflow:hidden", cap="Detalles del plano CS-MEC-06"),
    tabla(["Verificación", "Carga", "Tensión", "Admisible", "MS"], [
        ["Manguito Ø8/5,1 a flexión", f"{nt['M_J']:.0f} N·mm", f"{n(sig_slv)} MPa", "402 MPa", ms(402 / sig_slv - 1)],
        ["Contacto manguito–tubo (15 mm)", f"{nt['M_J']:.0f} N·mm", f"{n(p_slv)} MPa", "50 MPa", ms(50 / p_slv - 1)],
        ["Perno de pivote A Ø2,5 (corte)", f"{F_perno:.0f} N", f"{n(F_perno / 4.91)} MPa", "216 MPa", ms(216 / (F_perno / 4.91) - 1)],
        ["Oreja de C1 (aplastamiento)", f"{F_perno:.0f} N", f"{n(F_perno / 20.0)} MPa", "32,5 MPa", ms(32.5 / (F_perno / 20.0) - 1)],
        ["Tirante Ø3/2 (pandeo)", f"{n(ALA['tirante']['N'], 1)} N", f"P<sub>cr</sub> = {ALA['tirante']['Pcr']:.0f} N", "coef. ≥ 10", n(ALA['tirante']['coef'])],
    ], [140, 60, 62, 54, 38], fs=8.8) + ul([
        f"El pivote A recibe el momento de raíz de la varilla ({M_ap:.0f} N·mm) como un par sobre las dos orejas de la cuaderna, "
        "separadas 8 mm.",
        "Manguito de 32 mm: 15 mm de apoyo sobre cada tramo, más el juego de la articulación.",
        "Los herrajes de aluminio van pegados dentro del tubo con 4 mm de solape y un perno de Ø1,5.",
        "El manguito y la horquilla son las piezas con menos antecedentes: primer prototipo a fabricar."], "s"), w=[336, None]))
slide("Cámaras, celda solar y accesos", cols(
    anot("est_iso.png", "est", 300, izq=[("tapa", "Tapa superior:\nceldas solares (E3)\ny cámara a cenit"), ("membrana", "Membrana plegada"),
                                         ("patin", "Patín de PTFE")],
         der=[("botalon", "Botalón de cola"), ("manguito", "Manguito"), ("cuna", "Cuna de ala"), ("llave", "Llave")], lw=96, fs=7.6),
    ul(["<b>Cámara a cenit (C6):</b> sobre la tapa superior de G10, junto al botalón. En planeo mira hacia arriba.",
        "<b>Cámara a nadir (C7):</b> bajo la bandeja, mirando por una ventana de la cubierta inferior.",
        "<b>Celdas solares (E3):</b> pegadas sobre la tapa superior, que queda al sol durante el planeo.",
        "<b>Interruptor (E4, E5):</b> orificio Ø8 en la pared del contenedor, alineado con el interruptor montado en el panel lateral.",
        "<b>Indicador (E6):</b> LED visible por un orificio Ø5.",
        "<b>Pendiente con el subsistema de cámaras:</b> dentro del contenedor ninguna cámara ve hacia afuera. Para registrar la apertura "
        "del paracaídas hace falta definir una ventana o reubicar una cámara. Queda como acción abierta."], "s"), w=[494, None]))
slide("Integridad estructural de la electrónica", cols(
    img("equipos_lateral.png", w=676), "", w=[676, 0]) + tabla(
    ["Componente", "Montaje", "Masa", "Carga a 30 G × 1,8", "Sujeción"], [
        ["PCB principal", "4 separadores M2,5 de 8 mm bajo la bandeja", "25 g", f"{0.025 * 30 * G0 * 1.8:.0f} N", "4 tornillos M2,5 con arandela dentada"],
        ["PCB radio / GNSS", "4 separadores M2,5 de 8 mm sobre la bandeja", "20 g", f"{0.020 * 30 * G0 * 1.8:.0f} N", "4 tornillos M2,5"],
        ["Batería 18650", "Dos sillas impresas + cincha; lengüetas soldadas (M4)", "46 g", f"{0.046 * 30 * G0 * 1.8:.0f} N", "Cincha de 20 mm y topes en x"],
        ["Servos", "Atornillados a la bandeja por sus orejas", "9 g c/u", f"{0.009 * 30 * G0 * 1.8:.0f} N", "2 tornillos M2 c/u"],
        ["Conectores", "JST con traba; cables atados a la bandeja cada 40 mm", "—", "—", "Precintos y adhesivo en los enchufes"],
    ], [92, 232, 44, 84, 224], fs=9.2) + nota(
    "Toda la electrónica cuelga de una sola pieza, la bandeja de G10, que entra y sale del bastidor con la tapa superior quitada. "
    "Las placas del modelo FEA llevan su masa repartida y dan sus propios modos de flexión."))

def peor_rig(clave, crit="sigma_x entre capas", eje="x"):
    for k, v in RIG_["armonico"][eje]["margenes"].items():
        g, c = [t.strip() for t in k.split("|")]
        if g.startswith(clave) and c == crit:
            return f"{v['sigma']:.0f}"
    return "?"


RIG_ = json.load(open(os.path.join(FEA, "iteracion_rigida.json")))

# ---------------------------------------------------------------- analisis estructural
separador("5. Análisis estructural", "Vibración de 15 G (S4) y choque de 30 G (S5)")
RIG = json.load(open(os.path.join(FEA, "iteracion_rigida.json")))
zm = R["zeta_modal"]
fe_ = R["f_elast"]
ix, fx, mx = modo_dom(0)
iy, fy, my = modo_dom(1)
iz, fz, mz = modo_dom(2)
slide("Ambiente de cargas y criterios", cols(tabla(
    ["Caso", "Qué representa", "Cómo se aplica", "Ejes"], [
        ["CE-15", "Aceleración de lanzamiento (S4)", "15 G casi-estáticos", "x, y, z"],
        ["RF-15", "Vibración (S4)", "Barrido senoidal de 15 G de amplitud en la base, 5 a 1000 Hz; se evalúa la respuesta en cada resonancia", "x, y, z"],
        ["CH-30", "Choque (S5)", "Semiseno de 30 G en la base; 11 ms nominal y barrido de 1 a 20 ms", "x, y, z"],
        ["PA-30", "Tirón del paracaídas (S5)", "30 G × FAD 1,8, colgado de los 3 anclajes de la brida", "x"],
        ["AL-3p", "Apertura del ala", "Presión de 367 Pa (3 × la de vuelo), modelo de tiras de la nota de membrana", "—"],
    ], [50, 130, 250, 44], fs=9.3) + tabla(
    ["Material", "Admisible", "FS", "Criterio"], [
        ["PA12-CF impreso", "65 MPa en el plano · 35 MPa entre capas", "2,0", "von Mises y σx"],
        ["LW-PLA impreso", "14 MPa en el plano · 8 MPa entre capas", "2,0", "von Mises y σx"],
        ["G10 / FR-4", "280 MPa", "1,5", "von Mises"],
        ["CFRP pultruido", "900 MPa (compresión de fibra) · 50 MPa (corte)", "1,5", "σx y τ"],
        ["Inox A2-70", "450 MPa (fluencia)", "1,25", "von Mises"],
    ], [110, 230, 34, 100], fs=9.3),
    caja("Condiciones de borde",
         "<b>Lanzamiento y ensayo:</b> borde inferior del contenedor apoyado (x, y, z fijos) y borde superior guiado "
         "lateralmente por el fuselaje (y, z fijos).<br><br><b>Paracaídas:</b> fijo en los tres anclajes de la brida.")
    + caja("Amortiguamiento",
           f"Estructura: ζ = {zeta * 100:.0f} % (Q = {Q:.0f}).<br>Elastómero de los aisladores: factor de pérdida η = "
           f"{R['eta_elast']:.2f}.<br>El ζ de cada modo sale de la fracción de energía de deformación que queda en el elastómero."),
    w=[486, None]))
slide("Evolución del diseño guiada por el análisis", tabla(
    ["Iteración", "Qué se probó", "Qué mostró el análisis", "Cambio"], [
        ["1", "Tapa del contenedor de LW-PLA de 3 mm, de una pieza con el tubo; contenedor en voladizo.",
         "f₁ = 140 Hz (flexión del tubo). Tapa y base del tubo sin margen a 30 G lateral.",
         "Tapa aparte, nervada, de PA12-CF. El fuselaje guía el borde superior."],
        ["2", "Tapa nervada; llave unida rígidamente a la tapa y a C4.",
         f"Modo axial a {RIG['freq'][0]:.0f} Hz con el {RIG['m_eff'][0][0] / 5:.0f} % de la masa. En resonancia amplifica "
         f"{RIG['armonico']['x']['trans_max']['Bateria']:.0f} veces: σx de {peor_rig('Contenedor: tapa')} MPa en la tapa. Margen negativo en tapa, C4 y tubo.",
         "La llave pasa a ser un perno pasante con arandelas: las piezas impresas trabajan a compresión."],
        ["3 (actual)", "Anillo elastomérico bajo el plato de apoyo de la llave; patines de elastómero con cara de PTFE.",
         f"Modo axial a {fx:.0f} Hz con ζ = {zm[ix] * 100:.0f} %. Amplificación en resonancia: "
         f"{R['armonico']['x']['trans_max']['Bateria']:.1f} veces.",
         "Diseño de este PDR."],
    ], [58, 190, 220, 208], fs=9.4) + nota(
    "Con unión rígida, un barrido senoidal de 15 G excita el modo axial con Q = 25: son casi 400 G sobre el planeador. "
    "Ninguna pieza impresa liviana aguanta eso con margen. La solución no es reforzar sino <b>aislar</b>: un anillo de elastómero "
    "en el único punto por donde pasa la carga axial baja la frecuencia y, sobre todo, disipa."), )

slide("Modelo de elementos finitos", cols(
    img("fea_malla.png", w=350, cap="Malla cortada por el plano y = 0, coloreada por material"),
    tabla(["", ""], [
        ["Geometría", "La del CAD, sin simplificar la estructura"],
        ["Elementos", f"{R['elementos']:,} tetraedros cuadráticos (C3D10)".replace(",", ".")],
        ["Nodos / grados de libertad", f"{R['nodos']:,} / {3 * R['nodos']:,}".replace(",", ".")],
        ["Mallador / solver", "Gmsh 4.15 / CalculiX 2.21"],
        ["Uniones", "Pegadas: malla conforme entre piezas"],
        ["Materiales", "Isótropos; CFRP y elastómeros ortótropos"],
        ["Masa del modelo", f"{R['masa_g']:.0f} g (el lastre lleva el total a 500 g)"],
        ["Modos extraídos", f"{len(f)} (hasta {f[-1]:.0f} Hz)"],
        ["Respuesta dinámica", "Superposición modal con corrección estática"],
    ], [118, 196], fs=9.2, cls="sinhead") + ul([
        "Baterías, servos y lastre: sólidos con su masa y envolvente. Placas: FR-4 con la masa de componentes repartida.",
        "Ala estibada: su masa va en los cuatro apoyos reales (pivotes A y B, cunas de C2 y C3).",
        "Aislador y patines: elastómero con módulo de compresión aparente E(1 + 2S²).",
        f"Se descartaron {R['n_filtrados']} elementos de {R['n_ever']:,} por nodos medios fuera de equilibrio en el autovector (artefacto numérico).".replace(",", "."),
    ], "s"), w=[356, None]))
e1 = lambda a, b: f"{100 * (a / b - 1):+.1f} %".replace(".", ",")
slide("Verificación del método de cálculo", cols(
    tabla(["Magnitud (viga en voladizo de aluminio 12 × 8 × 200 mm)", "Este método", "Analítico", "Diferencia"], [
        ["1.ª frecuencia de flexión [Hz]", n(VER["f_fem"][0]), n(VER["f_analitico"][0]), e1(VER["f_fem"][0], VER["f_analitico"][0])],
        ["2.ª frecuencia de flexión [Hz]", n(VER["f_fem"][1]), n(VER["f_analitico"][1]), e1(VER["f_fem"][1], VER["f_analitico"][1])],
        ["Flecha de punta a 1 G [µm]", n(VER["flecha_1g_fem"] * 1e3, 2), n(VER["flecha_1g_analitico"] * 1e3, 2), e1(VER["flecha_1g_fem"], VER["flecha_1g_analitico"])],
        ["Flecha a 1 G por suma modal [µm]", n(VER["flecha_1g_suma_modal"] * 1e3, 2), n(VER["flecha_1g_analitico"] * 1e3, 2), e1(VER["flecha_1g_suma_modal"], VER["flecha_1g_analitico"])],
        ["Tensión en la raíz a 1 G [MPa]", n(VER["sigma_raiz_fem"], 3), n(VER["sigma_raiz_analitico"], 3), e1(VER["sigma_raiz_fem"], VER["sigma_raiz_analitico"])],
        ["Punta en resonancia, 15 G, ζ = 2 % [mm]", n(VER["arm_punta_fem"], 2), n(VER["arm_punta_analitico"], 2), e1(VER["arm_punta_fem"], VER["arm_punta_analitico"])],
        ["Punta bajo semiseno de 30 G, 11 ms [mm]", n(VER["choque_punta_fem"], 3), n(VER["choque_punta_1gdl"], 3), e1(VER["choque_punta_fem"], VER["choque_punta_1gdl"])],
    ], [240, 70, 70, 66], fs=9.4),
    caja("Qué verifica",
         "La misma cadena que se usa para el CanSat (CAD → Gmsh → CalculiX → superposición modal propia) reproduce las soluciones "
         "de viga de Euler-Bernoulli y de un grado de libertad dentro del 3 %.<br><br>La suma modal recupera el resultado estático: "
         "signos y unidades de los factores de participación son correctos.<br><br>El ala desplegada se verificó aparte contra la "
         "nota de membrana (lámina 26)."), w=[452, None]) + tabla(
    ["Control en el modelo del CanSat", "x", "y", "z"], [
        ["Desplazamiento estático de la batería por unidad de aceleración: CalculiX [µs²]"] +
        [n(R["control_estatico"][e]["estatico"] * 1e6, 4) for e in EJES],
        [f"Ídem por suma de {len(f)} modos"] + [n(R["control_estatico"][e]["suma_modal"] * 1e6, 4) for e in EJES],
        ["Masa efectiva acumulada"] + [f"{100 * v:.0f} %" for v in R["m_eff_frac"][-1]],
    ], [430, 70, 70, 70], fs=9.2))
nm_t = min(12, len(f))
slide("Análisis modal: frecuencias y masas efectivas", cols(
    tabla(["Modo", "f [Hz]", "Masa efectiva x / y / z [%]", "ζ [%]", "Energía en elastómero", "Tipo"], [
        [i + 1, n(f[i]), " / ".join(f"{mef[i][d] / R['masa_g'] * 100:.0f}" for d in range(3)), n(zm[i] * 100, 1),
         f"{fe_[i] * 100:.0f} %", desc_modo(i)] for i in range(nm_t)
    ], [34, 46, 122, 36, 80, 78], fs=8.8, alin=["c", "c", "c", "c", "c", None]),
    img("fea_masa_efectiva.png", w=270) + ul([
        f"Primer modo: <b>{f[0]:.0f} Hz</b> (RD-6: más de 100 Hz).",
        f"Modo axial principal: {fx:.0f} Hz, {mx:.0f} % de la masa, ζ = {zm[ix] * 100:.0f} %.",
        f"Modos laterales principales: {fy:.0f} Hz (y) y {fz:.0f} Hz (z)." ,
        (f"Sin la guía del fuselaje (contenedor en voladizo) el primer modo baja a {R['freq_libre'][0]:.0f} Hz."
         if R.get("freq_libre") else ""),
    ], "s"), w=[404, None]))
slide("Formas modales", img("fea_modos.png", h=410))
tm = lambda e, k: R["armonico"][e]["trans_max"][k]
slide("Respuesta en frecuencia a 15 G: aceleraciones", cols(img("fea_respuesta_g.png", h=410), tabla(
    ["Punto", "Pico en X [G]", "a [Hz]", "Pico en Y [G]", "a [Hz]", "Pico en Z [G]", "a [Hz]"], [
        [k] + sum([[f"{15 * tm(e, k):.0f}", f"{R['armonico'][e]['f_trans_max'][k]:.0f}"] for e in EJES], [])
        for k in R["armonico"]["x"]["trans_max"]
    ], [78, 30, 30, 30, 30, 30, 30], fs=7.4, alin=[None, "c", "c", "c", "c", "c", "c"]) + nota(
    "Aceleración absoluta de respuesta para una entrada senoidal de 15 G en la base. La línea de trazos es la entrada. "
    "Dato para el subsistema eléctrico: es el nivel que ven las placas y la batería."), w=[390, None]))
slide("Respuesta en frecuencia a 15 G: tensiones", cols(img("fea_util_frecuencia.png", h=410), ul([
    "Índice de utilización = FS·σ/σ<sub>adm</sub> de cada grupo de piezas, contra la frecuencia de excitación. Por debajo de 1 hay margen.",
    "Cada pico es una resonancia. La curva se calcula con el campo completo de tensiones en los puntos de integración de CalculiX.",
    f"Los picos del eje X quedan achatados por el aislador (ζ = {zm[ix] * 100:.0f} % en el modo axial). En Y y Z mandan los modos del planeador sobre los patines.",
], "s"), w=[390, None]))
slide("Respuesta en frecuencia a 15 G: mapas", img("fea_arm_mapas.png", h=412))
slide("Choque de 30 G: pulso y respuesta", img("fea_choque_pulso.png", w=676) + cols(
    ul(["Pulso <b>semiseno de 30 G</b> aplicado en la base, en cada eje. Duración nominal de 11 ms.",
        "La duración real del golpe de eyección no se conoce: se barre de 1 a 20 ms y se toma la peor.",
        f"El espectro de respuesta dice cuánto amplifica cada modo: hasta 1,7 veces para un modo poco amortiguado, "
        f"menos para el axial (ζ = {zm[ix] * 100:.0f} %)."], "s"),
    tabla(["Punto", "X [G]", "Y [G]", "Z [G]"], [
        [k] + [n(R["choque"][e]["acc_max_g"][k]) for e in EJES] for k in list(R["choque"]["x"]["acc_max_g"])[:6]
    ], [130, 46, 46, 46], fs=8.8, alin=[None, "c", "c", "c"]), w=[380, None]))
slide("Choque de 30 G: mapas", img("fea_choque_mapas.png", h=412))
slide("Choque de 30 G: sensibilidad a la duración", img("fea_choque_duracion.png", w=640) + tabla(
    ["Grupo", "Criterio", "σ a 11 ms [MPa]", "σ peor duración [MPa]", "Duración crítica", "MS"], [
        [GNOM[g], CNOM[peor("choque", g)[3]], n(peor("choque", g)[4]["sigma_11ms"]), n(peor("choque", g)[1]),
         f"{peor('choque', g)[4]['tau_crit'] * 1e3:.0f} ms ({peor('choque', g)[2]})", ms(peor("choque", g)[0])] for g in GRUPOS
    ], [190, 100, 90, 110, 100, 50], fs=8.6, alin=[None, None, "c", "c", "c", "c"]))
slide("Tirón del paracaídas", img("fea_parac_mapas.png", w=600) + tabla(["Grupo", "Criterio", "σ [MPa]", "MS"], [
    [GNOM[g], CNOM[peor("paracaidas", g)[3]], n(peor("paracaidas", g)[1]), ms(peor("paracaidas", g)[0])] for g in GRUPOS
], [300, 140, 80, 80], fs=8.4, alin=[None, None, "c", "c"]))
ch = ALA["choque"]
slide("Ala desplegada: modos y choque", img("ala_modos.png", w=640) + cols(
    tabla(["Modo", "1", "2", "3", "4", "5"], [["f [Hz]"] + [n(x, 0) for x in ALA["modal"]["freq"][:5]]], [60, 50, 50, 50, 50, 50], fs=9.2,
          alin=[None, "c", "c", "c", "c", "c"]) + ul([
        "Pórtico de vigas: varilla de borde de ataque con manguito y tirante, con la masa de tela repartida. No incluye la rigidez "
        "que aporta la tensión de la tela ni la masa de aire arrastrada.",
        f"Primer modo a {ALA['modal']['freq'][0]:.0f} Hz: flexión fuera del plano. Queda muy por encima del período del planeo."], "s"),
    tabla(["Choque de 30 G con el ala abierta", "σ varilla [MPa]", "M ápice [N·mm]", "Duración crítica", "MS"], [
        [f"Eje {e.upper()}", n(ch[e]["sigma"]), n(ch[e]["M_apice"], 0), f"{ch[e]['tau'] * 1e3:.0f} ms", ms(400 / max(ch[e]["sigma"], 1e-9) - 1)]
        for e in EJES
    ], [150, 62, 66, 66, 40], fs=8.8, alin=[None, "c", "c", "c", "c"]) + nota(
        "S5 se verifica en la configuración de lanzamiento. Este caso cubre un golpe con el ala ya abierta (aterrizaje). "
        "La carga que dimensiona el ala sigue siendo la presión de apertura de 367 Pa."), w=[330, None]))

# ---------- resumen de margenes
def celda(caso, g):
    p = peor(caso, g)
    return ms(p[0]) + f'<span class="mini"> {CNOM[p[3]].replace("σx ", "σx ")}{"" if caso == "paracaidas" else ", " + p[2]}</span>'


ms_all = [(peor(c, g)[0], g, c) for g in GRUPOS for c in ("cuasi15", "armonico", "choque", "paracaidas")]
ms_min = min(ms_all)
neg = [x for x in ms_all if x[0] < 0]
CASO_NOM = {"cuasi15": "casi-estático de 15 G", "armonico": "respuesta en frecuencia", "choque": "choque de 30 G",
            "paracaidas": "tirón del paracaídas"}
slide("Resumen de márgenes de seguridad", tabla(
    ["Grupo de piezas", "CE-15 · casi-estático 15 G", "RF-15 · resonancia a 15 G", "CH-30 · choque 30 G", "PA-30 · paracaídas"], [
        [GNOM[g], celda("cuasi15", g), celda("armonico", g), celda("choque", g), celda("paracaidas", g)] for g in GRUPOS
    ] + [
        ["Ala: varilla de borde de ataque", "—", "—", ms(400 / max(max(ch[e]["sigma"] for e in EJES), 1e-9) - 1) + '<span class="mini"> ala abierta</span>',
         ms(400 / pt["sigma_LE"] - 1) + '<span class="mini"> apertura 367 Pa</span>'],
        ["Ala: tirante (pandeo)", "—", "—", "—", f'{n(ALA["tirante"]["coef"])}<span class="mini"> = P<sub>cr</sub>/N (≥ 10)</span>'],
    ], [170, 126, 126, 126, 126], fs=9.2) + nota(
    f"MS = σ<sub>adm</sub>/(FS·σ) − 1, mínimo sobre los tres ejes; entre paréntesis, criterio y eje que mandan. "
    f"<b>Margen mínimo: {ms(ms_min[0])}</b> en «{GNOM[ms_min[1]]}», caso {CASO_NOM[ms_min[2]]}. "
    + ("Todos los márgenes son positivos." if not neg else
       f"Hay {len(neg)} combinaciones con margen negativo: ver riesgos y acciones.")
    + " Los valores de resonancia dependen del amortiguamiento supuesto: es lo primero que hay que medir."))

# ---------- uniones
A_bond_lon = math.pi * P.LON_DO * 5.0
tau_lon = (F_ret / 4) / A_bond_lon
A_iso = math.pi * (P.WASH_D ** 2 - P.KEY_HOLE ** 2) / 4
sig_iso15 = m_plan / 1000 * 15 * G0 / A_iso
sig_isoch = F_ret / A_iso
import fe_model as _F
Ec_iso = _F.elastico("ELAST_X")[1]["E1"]
k_iso = Ec_iso * A_iso / P.ISO_T
sb_cubo = F_ret / A_iso
slide("Verificación de uniones (cálculo manual)", tabla(
    ["Unión", "Carga de diseño", "Tensión", "Admisible", "MS", "Observación"], [
        ["Llave Ø5 (tracción)", f"{F_ret:.0f} N", f"{n(sig_llave)} MPa", "360 MPa", ms(360 / sig_llave - 1), "30 G × 1,8 sobre el planeador"],
        ["Pasador Ø3 de la llave (corte doble)", f"{F_ret:.0f} N", f"{n(tau_pas)} MPa", "216 MPa", ms(216 / tau_pas - 1), "0,6·Sy/1,25"],
        ["Asiento del aislador en la tapa (compresión)", f"{F_ret:.0f} N", f"{n(sb_cubo, 2)} MPa", "17,5 MPa", ms(17.5 / sb_cubo - 1), "PA12-CF entre capas"],
        ["Aislador: deformación a 15 G / en choque", f"{m_plan / 1000 * 15 * G0:.0f} / {F_ret:.0f} N",
         f"{100 * sig_iso15 / Ec_iso:.0f} % / {100 * sig_isoch / Ec_iso:.0f} %", "20 % / 30 %", "cumple", f"k = {k_iso:.0f} N/mm"],
        ["Anclaje de brida en el nervio", f"{leg:.0f} N", f"{n(sb_brida)} MPa", "32,5 MPa", ms(32.5 / sb_brida - 1), "3 ramales a 35°"],
        ["Pegado tapa–tubo", f"{F_par:.0f} N", f"{n(tau_tapa, 2)} MPa", "2,0 MPa", ms(2.0 / tau_tapa - 1), "+ 3 tornillos M2,5 de respaldo"],
        ["Pegado de cada larguero en su buje", f"{F_ret / 4:.0f} N", f"{n(tau_lon, 2)} MPa", "9,0 MPa", ms(9.0 / tau_lon - 1), "Cota superior: sin contar los paneles"],
        ["Cincha de batería", f"{0.046 * 30 * G0 * 1.8:.0f} N", "—", "> 100 N", "cumple", "Cinta de 20 mm con hebilla"],
        ["Tornillos M2,5 de la PCB principal", f"{0.025 * 30 * G0 * 1.8 / 4:.1f} N c/u".replace(".", ","), "—", "> 300 N", "cumple", "4 tornillos"],
        ["Varilla plegada entre apoyos (134 mm)", "30 G × 1,8", "2 MPa", "400 MPa", "> 10", "1.er modo local ≈ 1,2 kHz"],
    ], [196, 74, 70, 62, 44, 190], fs=8.9) + nota(
    "Las uniones no están en la malla (el modelo es pegado y conforme): se verifican aquí con las fuerzas de interfaz. "
    "El par para girar la llave es 0,06 kg·cm: el servo no forma parte del camino de carga (M3)."))

# ---------------------------------------------------------------- masa, ensayos, riesgos
separador("6. Masa, ensayos y riesgos", "Presupuesto de masa, plan de verificación y acciones abiertas")


def filas_masa(subs):
    out = []
    for s_ in subs:
        fs_ = [x for x in MAS["filas"] if x["sub"] == s_]
        out.append(dict(cls="grupo", f=[f"<b>{s_}</b>", "", "", "", "", ""]))
        for x in fs_:
            out.append([x["item"], x["cant"], n(x["unit"]), n(x["masa"]), "±" + n(x["inc"]), x["fuente"]])
        out.append(dict(cls="sub", f=[f"Subtotal {s_.lower()}", "", "", n(MAS["sub"][s_]["masa"]), "±" + n(MAS["sub"][s_]["inc"]), ""]))
    return out


cab_m = ["Componente", "Cant.", "g c/u", "Masa [g]", "Incert. [g]", "Fuente"]
slide("Presupuesto de masa (1/3): planeador, estructura y ala", tabla(cab_m, filas_masa(
    ["Estructura del planeador", "Ala de membrana"]), [270, 40, 56, 62, 66, 130], fs=8.4, alin=[None, "c", "c", "c", "c", None]))
slide("Presupuesto de masa (2/3): cola, aviónica y contenedor", tabla(cab_m, filas_masa(
    ["Cola (nota de cola)", "Avionica y equipos", "Contenedor"]), [270, 40, 56, 62, 66, 130], fs=8.4,
    alin=[None, "c", "c", "c", "c", None]).replace("Avionica", "Aviónica").replace("avionica", "aviónica"))
slide("Presupuesto de masa (3/3): total y centro de gravedad", cols(
    tabla(["Subsistema", "Masa [g]", "Incert. [g]"], [
        [k.replace("Avionica", "Aviónica"), n(v["masa"]), "±" + n(v["inc"])] for k, v in MAS["sub"].items()
    ] + [dict(cls="sub", f=["<b>Total</b>", f"<b>{n(MAS['total'])}</b>", "±" + n(MAS["inc_rss"]) + " (cuadrática)"])],
        [170, 66, 100], fs=9.6, alin=[None, "c", "c"]) + ul([
        f"S1 pide 500 ± 10 g. El presupuesto cierra en 500 g con <b>{n(MAS['lastre'], 0)} g de lastre</b>, que es a la vez el margen.",
        f"La incertidumbre (±{n(MAS['inc_rss'], 0)} g) es mayor que la tolerancia: la masa se ajusta en la pesada final.",
        "Si sobra masa: aligerar las cuadernas C1 y C4 (hoy 22 g cada una) o bajar el relleno de la tapa.",
        "Si falta: lastre de plomo-estaño en el compartimento de nariz, que además adelanta el CG.",
        "Fuente «CAD»: volumen del modelo por densidad nominal. «Asignación»: valor pedido al subsistema, a confirmar."], "s"),
    tabla(["Centro de gravedad (desde la nariz)", "x [mm]"], [
        ["Conjunto de lanzamiento", n(MAS["x_cg_lanzamiento"], 0)],
        ["Planeador estibado", n(MAS["x_cg_planeador_estibado"], 0)],
        ["En vuelo, CanSat completo (ala y cola abiertas)", n(MAS["x_cg_vuelo_total"], 0)],
        ["Centroide del ala (2/3 de la cuerda)", n(MAS["x_centroide_ala"], 0)],
    ], [200, 60], fs=9.6, alin=[None, "c"]) + caja("Para aerodinámica",
        f"Masa de vuelo: <b>500 g</b> (como en la nota de membrana). Carga alar: {n(MAS['carga_alar'], 0)} N/m². "
        f"Calculada como planeador, con la resistencia del cuerpo: <b>{n(MAS['w_estimado'], 1)} m/s</b> "
        f"(C4: 5 ± 3 m/s).<br><br>El CG en vuelo queda {MAS['x_centroide_ala'] - MAS['x_cg_vuelo_total']:.0f} mm por delante "
        "del centroide del ala. El margen estático hay que recalcularlo con la cola."), w=[350, None]))
slide("Plan de ensayos", tabla(["Ensayo", "Requisito", "Método", "Criterio de aceptación"], [
    ["Calibre y deslizamiento", "S2, S3, S7", "Tubo calibre Ø90,5 × 260. El CanSat armado sale por su peso.", "Sale sin trabarse en 10 de 10 intentos"],
    ["Masa y CG", "S1", "Balanza de 0,1 g; CG sobre filo.", "500 ± 10 g; CG dentro de ±3 mm del previsto"],
    ["Probetas de impresión", "RD-4", "Tracción en el plano y entre capas: PA12-CF y LW-PLA, 5 probetas c/u.", "Resistencia ≥ valor usado en este PDR"],
    ["Amortiguamiento", "S4", "Golpe con martillo y acelerómetro en el planeador; ancho de banda a −3 dB.", "ζ axial ≥ 10 %; ζ lateral ≥ el calculado"],
    ["Vibración", "S4", "CanSat dentro de un tramo de fuselaje sobre mesa vibrante o lijadora orbital; 3 ejes, 1 min por eje.", "Sin daño ni piezas sueltas; el ala no se abre; telemetría continua"],
    ["Choque / caída", "S5", "Caída colgado de la brida con cuerda no elástica de 61 cm (≈ 30 G).", "Sin daño; el planeador sigue trabado"],
    ["Tracción de la llave", "RD-5, M3", f"Carga estática de {1.5 * F_ret:.0f} N (1,5 × diseño) entre planeador y tapa.", "Sin fluencia ni fisuras"],
    ["Liberación y despliegue", "C4, S7", "Contenedor colgado; comando de liberación; video a 240 cps.", "20 de 20: sale, abre y traba el manguito"],
    ["Carga del ala", "C4", "Bolsas de arena sobre la membrana hasta 3 × la carga de vuelo.", "Flecha de punta ≤ 5 mm; sin daño"],
    ["Temperatura", "S6", "Contenedor 30 min a 50 °C con el planeador adentro.", "Sin deformación; sigue deslizando"],
], [112, 62, 290, 212], fs=8.8))
slide("Riesgos y acciones abiertas", tabla(["Riesgo", "Causa", "Prob.", "Impacto", "Mitigación / acción"], [
    ["El amortiguamiento real es menor que el calculado", "Propiedades del elastómero supuestas (E = 3 MPa, η = 0,30)", "Media", "Alto",
     "Ensayo de martillo en el primer prototipo. Elegir el compuesto por hoja de datos y repetir el análisis."],
    ["Las piezas impresas rinden menos que la hoja de datos", "Humedad del PA12; espumado irregular del LW-PLA", "Media", "Alto",
     "Probetas del mismo lote. Los márgenes ya usan la resistencia entre capas y FS = 2."],
    ["El ala no traba al abrir", "Fricción del manguito; tela enganchada", "Media", "Alto",
     "20 aperturas filmadas. Cordón elástico interno. El manguito es la primera pieza a prototipar."],
    ["El planeador no sale del contenedor", "Patines con demasiada interferencia; tela pellizcada", "Baja", "Alto",
     "Cara de PTFE; huelgo de 1 mm; ensayo de deslizamiento en frío y en caliente."],
    ["La interpretación de S4 y S5 no es la de la organización", "El Apéndice A no define espectro ni duración", "Media", "Medio",
     "Consultar el procedimiento de ensayo. El análisis cubre barrido senoidal y semiseno con duración variable."],
    ["Las cámaras no ven la apertura del paracaídas", "Dentro del contenedor no hay visual (C6, C7)", "Alta", "Medio",
     "Definir con el subsistema de cámaras: ventana en la tapa o cámara en el contenedor."],
    ["El contenedor se ablanda al sol", "LW-PLA: transición vítrea a 55 °C", "Baja", "Medio",
     "Color blanco, sombra hasta el lanzamiento. Alternativa: ASA-LW."],
    ["Masa fuera de tolerancia", f"Incertidumbre ±{n(MAS['inc_rss'], 0)} g contra ±10 g", "Media", "Medio",
     f"Lastre ajustable de {n(MAS['lastre'], 0)} g; pesadas parciales por subsistema."],
], [150, 150, 40, 44, 292], fs=8.6) + nota(
    "Pendientes para el CDR: nota de cola (botalón y mecanismo), resorte de torsión del ala, detalle de bujes e insertos de las "
    "cuadernas, modelo de membrana 3D, y un segundo nivel de malla para confirmar la convergencia de las tensiones de pico."))
cump = [
    ["S1", "Masa 500 ± 10 g", f"500 g con {n(MAS['lastre'], 0)} g de lastre", "Cumple (análisis)"],
    ["S2", "Diámetro 90 mm", "Ø90,0", "Cumple"],
    ["S3", "Largo 200 a 250 mm", f"{P.CT_LEN:g} mm", "Cumple"],
    ["S4", "Vibraciones de 15 G", f"MS mínimo: casi-estático {ms(min(peor('cuasi15', g)[0] for g in GRUPOS))}, resonancia {ms(min(peor('armonico', g)[0] for g in GRUPOS))}",
     "Cumple" if min(peor('armonico', g)[0] for g in GRUPOS) >= 0 else "Parcial: ver riesgos"],
    ["S5", "Choque de 30 G", f"MS mínimo: choque {ms(min(peor('choque', g)[0] for g in GRUPOS))}, paracaídas {ms(min(peor('paracaidas', g)[0] for g in GRUPOS))}",
     "Cumple" if min(min(peor('choque', g)[0], peor('paracaidas', g)[0]) for g in GRUPOS) >= 0 else "Parcial: ver riesgos"],
    ["S6", "Pared impresa ≥ 2 mm, rígida", "2,0 mm; tubo cerrado", "Cumple"],
    ["S7", "Desliza libre; puede retener desplegables", "Exterior liso; la pared retiene el ala", "Cumple (a demostrar)"],
    ["S8", "Montaje fijo", "Separadores, tornillos con inserto, epoxi", "Cumple"],
    ["S9", "Materiales no contaminantes", "LW-PLA y PA12-CF", "Cumple"],
    ["M1 / M2", "Sin pirotecnia ni calor expuesto", "Servo y resortes", "Cumple"],
    ["M3", "Mecanismos mantienen su estado", "Llave con traba geométrica; manguito", "Cumple (a ensayar)"],
    ["M4", "Sin contactos de resorte en baterías", "Lengüetas soldadas", "Cumple"],
    ["C4", "5 ± 3 m/s", f"{n(MAS['w_estimado'], 1)} m/s estimado", "Cumple (análisis)"],
    ["E3 – E6", "Solar, interruptor, orificios ≤ 10 mm, indicador", "Tapa superior; Ø8 y Ø5", "Cumple"],
    ["C6 / C7", "Video a cenit y nadir", "Soportes definidos; visual dentro del contenedor pendiente", "Abierto"],
]
slide("Cumplimiento de requisitos", tabla(["N.º", "Requisito", "Resultado", "Estado"], [
    dict(cls="" if "Cumple" in c[3] and "Parcial" not in c[3] else "warn", f=c) for c in cump
], [56, 200, 290, 130], fs=9.2))

# ---------------------------------------------------------------- planos
separador("Anexo: planos", "Siete hojas A3 generadas desde el modelo CAD · archivo Planos_CanSat_AlaDelta.pdf")
for k, t in enumerate(["Conjunto de lanzamiento", "Planeador: configuración estibada", "Planeador: configuración desplegada",
                       "Estructura primaria (bastidor)", "Cuadernas C1, C2/C3 y C4", "Ala: mecanismo y articulación",
                       "Contenedor: tubo y tapa nervada"], 1):
    slide(f"Plano CS-MEC-0{k}: {t}", img(f"CS-MEC-0{k}.png", h=418, src_dir=PLANOS, maxpx=2600, style="text-align:center"))

# ======================================================================= salida
CSS = """
@page { size: 720pt 540pt; margin: 0 }
* { box-sizing: border-box }
html, body { margin: 0; padding: 0 }
body { font-family: 'Inter', 'Liberation Sans', Arial, sans-serif; color: #111; -webkit-print-color-adjust: exact; print-color-adjust: exact }
.slide { width: 720pt; height: 540pt; position: relative; overflow: hidden; page-break-after: always; background: #fff }
.hdr { position: absolute; top: 9pt; left: 20pt; right: 20pt; height: 58pt; display: flex; align-items: center }
.hdr .logo { flex: 0 0 60pt }
.hdr h1 { flex: 1; margin: 0 8pt; text-align: center; color: #2f3192; font-size: 21pt; line-height: 1.1; font-weight: 800; letter-spacing: -0.2pt }
.comp { flex: 0 0 76pt; text-align: center; line-height: 1 }
.comp .c1 { font-weight: 900; font-size: 15pt; color: #1d2046; letter-spacing: 0.5pt }
.comp .c2 { font-weight: 800; font-size: 9.6pt; color: #3aa0d8; letter-spacing: 1.4pt; margin-top: 1pt }
.comp .c3 { font-size: 5.2pt; color: #444; letter-spacing: 0.8pt; margin-top: 2pt; font-weight: 600 }
.r1 { position: absolute; top: 70pt; left: 18pt; right: 18pt; height: 2.4pt; background: #2f3192 }
.r2 { position: absolute; bottom: 28pt; left: 18pt; right: 18pt; height: 2.4pt; background: #2f3192 }
.ftr { position: absolute; bottom: 9pt; left: 24pt; right: 24pt; font-size: 8.6pt; display: flex; justify-content: space-between; color: #111 }
.body { position: absolute; top: 79pt; bottom: 35pt; left: 22pt; right: 22pt; font-size: 10.4pt; line-height: 1.32 }
.cols { display: flex }
table.t { border-collapse: collapse; font-size: 9.6pt; line-height: 1.22; width: 100%; table-layout: fixed; margin-bottom: 6pt }
table.t th { background: #2f3192; color: #fff; font-weight: 700; padding: 3pt 4pt; border: 0.8pt solid #2f3192; text-align: center }
table.t td { border: 0.8pt solid #2f3192; padding: 2.2pt 4pt; vertical-align: middle; overflow-wrap: break-word }
table.t tr:nth-child(odd) td { background: #e3e3f3 }
table.t td.c { text-align: center }
table.t tr.grupo td { background: #c9cae8 !important; border-bottom-width: 1.2pt }
table.t tr.sub td { background: #ffd966 !important; font-weight: 700 }
table.t tr.warn td:last-child { background: #ffe2b8 !important; font-weight: 700 }
table.sinhead tr:first-child { display: none }
ul { margin: 4pt 0 4pt 0; padding-left: 13pt }
ul li { margin-bottom: 3.2pt }
ul.s { font-size: 9.6pt; line-height: 1.3 }
.fig { text-align: center }
.fig img { max-width: 100%; display: inline-block }
.cap { font-size: 8.2pt; color: #333; margin-top: 1pt; font-weight: 600 }
.caja { border: 1.4pt solid #2f3192; border-radius: 6pt; margin-bottom: 7pt; overflow: hidden }
.caja .ct { background: #2f3192; color: #fff; font-weight: 700; font-size: 10pt; padding: 2.5pt 7pt }
.caja .cc { padding: 5pt 7pt; font-size: 9.4pt; line-height: 1.3 }
.caja .cc ul { margin-top: 2pt }
.sel { background: #19a34a; color: #fff; border-radius: 3pt; padding: 0 4pt; font-size: 8.2pt; font-weight: 800; white-space: nowrap }
.nota { font-size: 9pt; line-height: 1.3; background: #f3f3f8; border-left: 3pt solid #2f3192; padding: 4pt 7pt; margin-top: 4pt }
.ok { color: #0a6b2d; font-weight: 700 }
.bad { color: #b3261e; font-weight: 800 }
.mini { font-size: 7pt; color: #444 }
svg.anot { display: block; margin: 0 auto; font-family: 'Inter', Arial, sans-serif }
.grid2x2 { display: grid; grid-template-columns: 1fr 1fr; gap: 4pt 8pt }
.sep { position: absolute; left: 0; right: 0; top: 150pt; text-align: center }
.sep .st { color: #2f3192; font-size: 30pt; font-weight: 800 }
.sep .ss { font-size: 15pt; font-weight: 600; margin-top: 60pt; color: #111 }
.portada { position: absolute; inset: 0; text-align: center; background: #fff }
.portada .p0 { margin-top: 44pt }
.portada .p1 { font-size: 20pt; font-weight: 700; color: #1d2046; margin-top: 16pt }
.portada .p2 { font-size: 34pt; font-weight: 800; color: #2f3192; margin-top: 10pt; letter-spacing: -0.4pt }
.portada .p3 { font-size: 22pt; font-weight: 700; margin-top: 18pt }
.portada .p4 { font-size: 13pt; margin-top: 12pt; color: #333 }
.portada .p5 { font-size: 12pt; margin-top: 46pt; line-height: 1.5; font-weight: 600 }
"""


def render():
    out = ['<!doctype html><html lang="es"><head><meta charset="utf-8"><title>PDR - Subsistema mecánico</title>',
           f"<style>{CSS}</style></head><body>"]
    for k, (titulo, cuerpo, cls) in enumerate(slides, 1):
        out.append(f'<section class="slide {cls}">')
        if cls == "portadaslide":
            out.append(cuerpo)
        else:
            t = titulo or ""
            out.append(f'<div class="hdr"><div class="logo">{LOGO}</div><h1>{t}</h1>{COMP}</div><div class="r1"></div>')
            out.append(f'<div class="body">{cuerpo}</div>' if titulo else cuerpo)
            out.append(f'<div class="r2"></div><div class="ftr"><span>Presentador: {P.PRESENTADOR}</span>'
                       f'<span>CanSat {P.TEMPORADA} PDR: {P.EQUIPO}</span><span>{k}</span></div>')
        out.append("</section>")
    out.append("</body></html>")
    hp = os.path.join(BUILD, "pdr.html")
    open(hp, "w", encoding="utf-8").write("\n".join(out))
    js = os.path.join(BUILD, "print.js")
    open(js, "w").write("""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + process.argv[2]);
  await p.evaluate(() => document.fonts.ready);
  // ajuste automatico: si el contenido de una lamina excede su area util, se escala para que entre
  const over = await p.evaluate(() => [...document.querySelectorAll('.slide')].map((s, i) => {
    const body = s.querySelector('.body'); if (!body) return null;
    const bb = body.getBoundingClientRect(); let mx = 0, mw = 0;
    body.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect(); if (r.height > 0 && r.width > 0) { mx = Math.max(mx, r.bottom); mw = Math.max(mw, r.right); } });
    const sc = Math.min(1, bb.height / (mx - bb.top + 1), bb.width / (mw - bb.left + 1));
    if (sc < 0.995) { body.style.transformOrigin = 'top left'; body.style.transform = 'scale(' + sc + ')'; return [i + 1, Math.round(sc * 100)]; }
    return null;
  }).filter(x => x));
  console.log('ESCALADAS ' + JSON.stringify(over));
  await p.pdf({ path: process.argv[3], width: '10in', height: '7.5in', printBackground: true, preferCSSPageSize: true });
  await b.close();
})();
""")
    r = subprocess.run(["node", js, hp, PDF], capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip()[-600:])
    print(f"{len(slides)} láminas -> {PDF}")


if __name__ == "__main__":
    render()
