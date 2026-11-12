"""Planos de conjunto y de detalle (A3) generados desde el modelo CAD.
Uso: python3 planos.py <carpeta_salida> [carpeta_renders]
"""
import os, sys, math
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Polygon, Circle, Arc
import params as P
import cad
from hlr import Hoja

V = cq.Vector


def f1(x):
    return f"{x:.1f}".replace(".", ",")


def medio(shapes, eje="y", lado=1):
    """Corta las piezas con un semiespacio para las vistas en corte."""
    big = 400
    if eje == "y":
        b = cad.box(-big, big, 0 if lado > 0 else -big, big if lado > 0 else 0, -big, big)
    else:
        b = cad.box(-big, big, -big, big, 0 if lado > 0 else -big, big if lado > 0 else 0)
    out = []
    for s in shapes:
        try:
            c = s.intersect(b)
            if c.isValid() and c.Volume() > 1e-6:
                out.append(c)
        except Exception:
            pass
    return out


def img(h, path, x, y, w):
    if path and os.path.exists(path):
        im = plt.imread(path)
        hh = w * im.shape[0] / im.shape[1]
        h.ax.imshow(im, extent=(x, x + w, y, y + hh), zorder=1, interpolation="lanczos")


def S(parts, grupos=None, excl=(), nombres=None):
    out = []
    for p in parts:
        if grupos and p["grupo"] not in grupos:
            continue
        if any(e in p["nombre"] for e in excl):
            continue
        if nombres and not any(n in p["nombre"] for n in nombres):
            continue
        out.append(p["shape"])
    return out


# ============================================================ hojas


def hoja1(pdf, out, R):
    lan = cad.build("lanzamiento")
    h = Hoja("CS-MEC-01", "Conjunto de lanzamiento", "1:1", "Ver lista",
             notas=("Contenedor Ø90 × 242 (S2, S3): pared exterior de 2,0 mm impresa (S6), boca inferior abierta.",
                    "El planeador sale por la boca al girar 90° la llave de bayoneta (ítem 4).",
                    "La pared retiene las alas plegadas (S7); 1 mm de huelgo radial tomado por 8 patines de elastómero con cara de PTFE.",
                    "Orificios en la pared: interruptor Ø8 e indicador Ø5 (E5: ≤ 10 mm).  La brida ancla en tres nervios de la tapa."))
    todo = [p["shape"] for p in lan if p["grupo"] != "carenado"]
    x0 = P.CT_X[0]
    # corte longitudinal
    T = h.vista(medio(todo, "y", 1), "lateral", (40, 222), 1.0, titulo="CORTE A-A  (plano y = 0, visto desde -y)", ref=(x0, 0, 0), titulo_dy=21)
    yb = T((0, 0, -45))[1]
    h.cota_h(T((x0, 0, -45)), T((P.CT_X[1], 0, -45)), yb - 13, valor=P.CT_LEN)
    h.cota_h(T((0, 0, -45)), T((P.L_G, 0, -45)), yb - 6.5, txt=f"{P.L_G:g} (planeador)")
    yt = T((0, 0, 45))[1]
    xc = P.CT_TOP[0] + P.CT_CAP_H
    h.cota_h(T((P.CT_TOP[0], 0, 45)), T((xc, 0, 45)), yt + 5, txt=f"{P.CT_CAP_H:g}")
    h.cota_h(T((xc, 0, 45)), T((P.CT_X[1], 0, 45)), yt + 5, txt=f"{P.CT_X[1] - xc:g}")
    h.cota_h(T((x0, 0, 45)), T((P.CT_TOP[0], 0, 45)), yt + 5, txt=f"{P.CT_TOP[0] - x0:g}")
    xl = T((x0, 0, 0))[0]
    h.cota_v(T((x0, 0, -45)), T((x0, 0, 45)), xl - 8, txt="Ø90")
    h.cota_v(T((x0, 0, -43)), T((x0, 0, 43)), xl - 15, txt="Ø86")
    h.eje(T((x0 - 6, 0, 0)), T((P.CT_X[1] + 6, 0, 0)))
    for n, p3, q in ((1, (120, 0, 44), (150, 280)), (2, (P.CT_TOP[0] + 1.5, 0, 30), (262, 280)),
                     (3, (P.CT_TOP[0] + P.CT_CAP_H + 9, 0, 20), (285, 262)), (4, (P.L_G + 2, 0, 0), (290, 222)), (11, (P.CT_TOP[0] + 5.5, 0, 6), (290, 240)),
                     (5, (P.L_G - 4, 0, -20), (290, 200)), (6, (4, 0, 20), (30, 262)), (7, (100, 0, 6.5), (120, 250)),
                     (8, (100, 0, -14), (120, 192)), (9, (30, 0, 8), (64, 250)), (10, (175, 0, -44), (215, 168))):
        h.globo(T(p3), q, n)
    # vista exterior
    ext = [p["shape"] for p in lan if p["grupo"] == "contenedor"]
    T2 = h.vista(ext, "lateral", (40, 112), 1.0, titulo="VISTA EXTERIOR", ref=(x0, 0, 0), titulo_dy=16)
    h.cota_h(T2((x0, 0, -45)), T2((175, 0, -45)), T2((0, 0, -45))[1] - 6, txt=f"{175 - x0:g}")
    h.llamada(T2((175, 0, -45)), (T2((175, 0, 0))[0] - 30, T2((0, 0, -45))[1] - 12), "Ø8 interruptor", ha="right")
    h.llamada(T2((185, 0, -45)), (T2((185, 0, 0))[0] + 8, T2((0, 0, -45))[1] - 12), "Ø5 LED")
    # vista desde la boca
    T3 = h.vista(todo, "frontal", (352, 222), 1.0, titulo="VISTA DESDE LA BOCA (nariz)")
    h.cota_h(T3((0, -45, 0)), T3((0, 45, 0)), T3((0, 0, 45))[1] + 6, txt="Ø90")
    lista = [(1, "Tubo del contenedor", "LW-PLA 2,0 mm", "1"), (2, "Tapa nervada", "PA12-CF", "1"),
             (3, "Paracaídas + brida 3 puntos", "Ripstop / Kevlar", "1"), (4, "Llave de bayoneta Ø5", "Inox A2-70", "1"),
             (5, "Cuaderna de cola C4", "PA12-CF", "1"), (6, "Cuaderna de nariz C1", "PA12-CF", "1"),
             (7, "Batería 18650 + sillas", "-", "1"), (8, "PCB principal", "FR-4", "1"),
             (9, "Lastre de centrado", "Asignación", "1"), (10, "Patín de guia", "Elastómero + PTFE", "8"),
             (11, "Aislador + plato de apoyo", "Elastómero / inox", "1")]
    h.tabla(300, 160, ["N.", "Denominación", "Material", "Cant."], lista, [8, 46, 36, 12], titulo="LISTA DE PARTES")
    h.guardar(pdf, os.path.join(out, "CS-MEC-01.png"))


def hoja2(pdf, out, R):
    est = cad.build("estibado")
    h = Hoja("CS-MEC-02", "Planeador: configuración estibada", "1:1", "Ver CS-MEC-04",
             notas=("Todo el planeador queda dentro de un cilindro Ø84; las varillas plegadas llegan a R 41,9.",
                    "Las alas pliegan planas: el tramo exterior de la varilla queda junto al interior y el tirante debajo (z = -7).",
                    "Estaciones medidas desde la cara frontal de C1 (x = 0, nariz)."))
    shapes = [p["shape"] for p in est if p["grupo"] != "carenado"]
    T = h.vista(shapes, "lateral", (38, 226), 1.0, titulo="VISTA LATERAL", titulo_dy=19)
    yb = T((0, 0, -P.RB))[1]
    xs = [0, P.X_C1[1], P.X_C2[0], P.X_C2[1], P.X_C3[0], P.X_C3[1], P.X_C4[0], P.L_G]
    for a, b in zip(xs[:-1], xs[1:]):
        h.cota_h(T((a, 0, -P.RB)), T((b, 0, -P.RB)), yb - 5, txt=f"{b - a:g}", fs=5)
    h.cota_h(T((0, 0, -P.RB)), T((P.L_G, 0, -P.RB)), yb - 11.5, valor=P.L_G)
    xl = T((0, 0, 0))[0]
    h.cota_v(T((0, 0, -P.RB)), T((0, 0, P.RB)), xl - 7, txt="Ø84")
    h.cota_v(T((P.L_G, 0, -P.Z_BOX)), T((P.L_G, 0, P.Z_BOX + P.T_COVER)), T((P.L_G, 0, 0))[0] + 16, txt=f1(2 * P.Z_BOX + P.T_COVER), dx=1.2)
    for nm, x in (("C1", 4), ("C2", 62), ("C3", 140), ("C4", 203)):
        h.texto(T((x, 0, 0))[0], T((0, 0, P.RB))[1] + 3, nm, fs=6, ha="center", weight="bold")
    T2 = h.vista(shapes, "superior", (38, 112), 1.0, titulo="VISTA SUPERIOR")
    h.cota_v(T2((0, -P.Y_OUT, 0)), T2((0, P.Y_OUT, 0)), T2((0, 0, 0))[0] - 7, txt=f1(2 * P.Y_OUT))
    h.cota_h(T2((0, P.RB, 0)), T2((P.X_A, P.RB, 0)), T2((0, P.RB, 0))[1] + 5, txt=f1(P.X_A), fs=5)
    h.cota_h(T2((P.X_B, P.RB, 0)), T2((P.L_G, P.RB, 0)), T2((0, P.RB, 0))[1] + 5, txt=f1(P.L_G - P.X_B), fs=5)
    h.cota_h(T2((P.X_A, P.RB, 0)), T2((P.X_B, P.RB, 0)), T2((0, P.RB, 0))[1] + 5, txt=f"{f1(P.D_AB)}  (A - B)")
    h.llamada(T2((P.X_A + P.L_SEG - 22, P.Y_PIV, 0)), (T2((225, 0, 0))[0], T2((0, 20, 0))[1]), "Manguito de traba\n(articulación J)")
    T3 = h.vista(shapes, "frontal", (340, 226), 1.0, titulo="VISTA FRONTAL (desde la nariz)")
    h.cota_h(T3((0, -P.Y_PIV, 0)), T3((0, P.Y_PIV, 0)), T3((0, 0, P.RB))[1] + 5, txt=f"{2 * P.Y_PIV:g}  (pivotes)")
    img(h, R and os.path.join(R, "est_iso.png"), 268, 60, 135)
    h.texto(335, 58, "Isométrica (sin escala)", fs=6, ha="center", weight="bold")
    h.guardar(pdf, os.path.join(out, "CS-MEC-02.png"))


def hoja3(pdf, out, R):
    des = cad.build("desplegado")
    h = Hoja("CS-MEC-03", "Planeador: configuración desplegada", "1:2", "Ver CS-MEC-06",
             notas=("Geometría del ala según la nota de membrana: cuerda de raíz 198,6, flecha 45°, S = 394 cm² (dos triangulos).",
                    "La franja de tela entre la varilla de raíz y la línea de pivotes suma 18 cm²: S de tela = 412 cm².",
                    "Cola en V y botalón: geometría de referencia (nota de cola); no se dimensionan en este plano."))
    shapes = [p["shape"] for p in des if p["grupo"] != "carenado"]
    e = 0.5
    vista = ((0, 0, 1), (0, 1, 0))                     # planta con la nariz hacia arriba
    T = h.vista(shapes, vista, (136, 266), e, titulo="VISTA EN PLANTA  (1:2)", titulo_dy=6)
    A, B = (P.X_A, P.Y_PIV, 0), (P.X_B, P.Y_PIV, 0)
    Tp = (P.X_B, P.Y_PIV + P.D_AB, 0)
    yb = T(B)[1]
    h.cota_h(T((P.X_B, -P.SEMI_SPAN, 0)), T((P.X_B, P.SEMI_SPAN, 0)), yb - 14, txt=f"{f1(P.SPAN)}  (envergadura)", dy=-1.4)
    h.cota_h(T(B), T(Tp), yb - 7, txt=f"{f1(P.L_TE)}  (tirante B - T)", dy=-1.4)
    h.cota_al(T(A), T(Tp), 9, f"{f1(P.L_LE)}  (borde de ataque A - T)")
    h.cota_al(T(A), T(P.P_J), -6, f1(P.L_SEG))
    xr = T((0, P.SEMI_SPAN, 0))[0] + 12
    h.cota_v(T((P.X_A, P.SEMI_SPAN, 0)), T((P.X_B, P.SEMI_SPAN, 0)), xr, txt=f1(P.D_AB), dx=1.2)
    h.cota_v(T((0, -P.SEMI_SPAN, 0)), T((336, -P.SEMI_SPAN, 0)), T((0, -P.SEMI_SPAN, 0))[0] - 10, txt="336")
    aa = T(A)
    h.ax.add_patch(Arc(aa, 44, 44, theta1=-90, theta2=-45, lw=0.3))
    h.texto(aa[0] + 10, aa[1] - 27, "45", fs=5.6)
    h.llamada(T(P.P_J), (T(P.P_J)[0] + 22, T(P.P_J)[1] + 14), "J: articulación + manguito Ø8")
    h.llamada(T(A), (aa[0] - 30, aa[1] + 10), "A: pivote de ápice", ha="right")
    h.llamada(T(B), (T(B)[0] + 22, T(B)[1] - 22), "B: pivote del tirante")
    h.llamada(T(Tp), (T(Tp)[0] - 2, T(Tp)[1] + 14), "T: herraje de punta", ha="right")
    h.llamada(T((100, -80, 0)), (T((100, -80, 0))[0] - 30, T((0, 0, 0))[1] + 6), "Membrana ripstop 40 g/m2", ha="right")
    T2 = h.vista(shapes, "frontal", (338, 178), 1 / 3.0, titulo="VISTA FRONTAL  (1:3)", titulo_dy=5)
    datos = [("Envergadura b", f"{f1(P.SPAN)} mm"), ("Cuerda de raíz (A - B)", f"{f1(P.D_AB)} mm"),
             ("Borde de ataque A - T", f"{f1(P.L_LE)} mm (2 × {f1(P.L_SEG)})"), ("Flecha del borde de ataque", "45°"),
             ("Área de membrana (2 triangulos)", f"{P.S_TRI:.0f} cm²"), ("Área de tela (con franja de raíz)", f"{P.S_WING:.0f} cm²"),
             ("Alargamiento (b = 2c)", "4,0"), ("Varilla de borde de ataque", "tubo CFRP Ø5 / 3,5"),
             ("Tirante y varilla de raíz", "tubo CFRP Ø3 / 2"), ("Largo total en vuelo", "336 mm"),
             ("Masa en vuelo (sin contenedor)", "ver presupuesto de masa")]
    h.tabla(292, 268, ["Parámetro", "Valor"], datos, [58, 56], titulo="DATOS GEOMETRICOS")
    img(h, R and os.path.join(R, "des_iso.png"), 280, 50, 124)
    h.guardar(pdf, os.path.join(out, "CS-MEC-03.png"))


def hoja4(pdf, out, R):
    est = cad.build("estibado")
    h = Hoja("CS-MEC-04", "Estructura primaria (bastidor)", "1:1", "Ver lista",
             notas=("Largueros pegados con epoxi estructural en los bujes de C1 y C4 (5 mm) y pasantes en C2 y C3.",
                    "Paneles de G10 atornillados (M2 × 6 + inserto térmico) y pegados sobre los nervios de las cuadernas.",
                    "Cuadernas impresas en PA12-CF, 100 % de relleno, capas en el plano y-z (carga axial perpendicular a las capas: ver margenes).",
                    "Masas calculadas con el volumen CAD y la densidad nominal."))
    st = [p for p in est if p["grupo"] == "estructura"]
    shapes = [p["shape"] for p in st]
    T = h.vista(shapes, "lateral", (38, 226), 1.0, ocultas=True, titulo="VISTA LATERAL (líneas ocultas)", titulo_dy=19)
    yb = T((0, 0, -P.RB))[1]
    h.cota_h(T((P.LON_X[0], 0, -P.RB)), T((P.LON_X[1], 0, -P.RB)), yb - 5, txt=f"{P.LON_X[1] - P.LON_X[0]:g}  (largueros)")
    h.cota_h(T((P.X_C1[1], 0, -P.RB)), T((P.X_C4[0], 0, -P.RB)), yb - 11, txt=f"{P.X_C4[0] - P.X_C1[1]:g}  (paneles)")
    xr = T((P.L_G, 0, 0))[0]
    h.cota_v(T((P.L_G, 0, -P.LON_Z)), T((P.L_G, 0, P.LON_Z)), xr + 7, txt=f"{2 * P.LON_Z:g}", dx=1.2)
    h.cota_v(T((P.L_G, 0, P.Z_TRAY[0])), T((P.L_G, 0, P.Z_BOX)), xr + 15, txt=f"{P.Z_BOX - P.Z_TRAY[0]:g}", dx=1.2)
    sup = [p["shape"] for p in st if "tapa" not in p["nombre"]]
    T2 = h.vista(sup, "superior", (38, 112), 1.0, ocultas=False, titulo="VISTA SUPERIOR (sin tapa P3)")
    xl = T2((0, 0, 0))[0]
    h.cota_v(T2((0, -P.LON_Y, 0)), T2((0, P.LON_Y, 0)), xl - 6, txt=f"{2 * P.LON_Y:g}")
    for n, p3, q in ((1, (4, 0, 38), (30, 280)), (2, (62, 0, 20), (88, 280)), (3, (140, 0, 20), (166, 280)),
                     (4, (203, 0, 38), (230, 280)), (5, (100, 0, P.LON_Z), (122, 280)), (6, (110, 0, -15), (150, 172)),
                     (7, (90, 0, P.Z_BOX), (62, 280)), (8, (80, 0, -4.6), (100, 172))):
        h.globo(T(p3), q, n)
    filas = []
    orden = [("C1 cuaderna de nariz", 1, "PA12-CF"), ("C2 cuaderna intermedia", 2, "PA12-CF"),
             ("C3 cuaderna intermedia", 3, "PA12-CF"), ("C4 cuaderna de cola", 4, "PA12-CF"),
             ("larguero", 5, "CFRP Ø5/3,5 × 201"), ("panel lateral", 6, "G10 0,5 mm"), ("tapa superior", 7, "G10 0,5 mm"),
             ("bandeja", 8, "G10 0,8 mm"), ("Cuna de ala", 9, "PA12-CF"), ("Guia de botalon", 10, "PA12-CF")]
    tot = 0.0
    for key, n, mat in orden:
        ps = [p for p in st if key in p["nombre"]]
        m = sum(p["masa"] for p in ps)
        tot += m
        nombre = {"larguero": "Larguero L1-L4", "panel lateral": "Panel lateral P1/P2", "tapa superior": "Tapa superior P3",
                  "bandeja": "Bandeja de aviónica B1", "Guia de botalon": "Guía de botalón"}.get(key, key)
        filas.append((n, nombre, mat, len(ps), f1(m / len(ps)), f1(m)))
    filas.append(("", "TOTAL estructura primaria", "", "", "", f1(tot)))
    h.tabla(262, 275, ["N.", "Denominación", "Material", "Cant.", "g c/u", "g"], filas, [7, 45, 38, 11, 13, 13],
            titulo="LISTA DE MATERIALES")
    img(h, R and os.path.join(R, "bastidor_explotado.png"), 262, 52, 142)
    h.guardar(pdf, os.path.join(out, "CS-MEC-04.png"))


def hoja5(pdf, out, R):
    h = Hoja("CS-MEC-05", "Cuadernas C1, C2/C3 y C4", "2:1 / 1:1", "PA12-CF impreso",
             notas=("C1 y C4: alma de 1,6, aro de 2,2, nervios de 2,8 y bujes Ø9,5 para los largueros (alojamiento Ø5 × 5).",
                    "Ranura de herraje: C1 en z = 0 (varilla de borde de ataque), C4 en z = -7 (tirante).  Perno de pivote Ø2,5.",
                    "C4 lleva el buje central Ø18 con pasaje Ø6 para el eje de la llave de bayoneta y el paso Ø6 del botalón de cola.",
                    "Radios de acuerdo de 1 mm en todos los encuentros de nervios (no dibujados)."))
    c1 = cad.cuaderna_extrema(False)
    c4 = cad.cuaderna_extrema(True)
    c2 = cad.cuaderna_media(*P.X_C2)
    e = 2.0
    cy = 188
    T = h.vista([c1], "posterior", (100, cy), e, ref=(0, 0, 0))
    h.texto(100, cy - 2 * P.RB - 14, "C1 - VISTA DESDE ADENTRO (2:1)", fs=6.5, weight="bold", ha="center")
    yt = T((0, 0, P.RB))[1]
    yb = T((0, 0, -P.RB))[1]
    h.cota_h(T((0, P.RB, 0)), T((0, -P.RB, 0)), yb - 5, txt=f"Ø{2 * P.RB:g}", dy=-1.4)
    h.cota_h(T((0, P.Y_OUT, P.Z_BOX)), T((0, -P.Y_OUT, P.Z_BOX)), yt + 5, txt=f1(2 * P.Y_OUT))
    h.cota_h(T((0, P.LON_Y, -P.LON_Z)), T((0, -P.LON_Y, -P.LON_Z)), T((0, 0, -P.LON_Z))[1] + 16, txt=f"{2 * P.LON_Y:g}")
    h.cota_v(T((0, -P.LON_Y, -P.LON_Z)), T((0, -P.LON_Y, P.LON_Z)), T((0, -P.LON_Y, 0))[0] - 16, txt=f"{2 * P.LON_Z:g}")
    xr = T((0, -P.RB, 0))[0]
    h.cota_v(T((0, -P.RB, -4)), T((0, -P.RB, 4)), xr + 5, txt="8", dx=1.2)
    h.llamada(T((0, P.LON_Y, P.LON_Z)), (40, cy + 2 * P.RB + 9), "4 × buje Ø9,5 con alojamiento Ø5 × 5", ha="left")
    h.llamada(T((0, P.Y_PIV, 0)), (16, 62), "Perno de pivote A Ø2,5 (eje vertical, y = ±34)", ha="left")
    h.llamada(T((0, 6, P.Z_TRAY[0])), (16, 70), "Asiento de la bandeja (z = -5)", ha="left")
    h.llamada(T((0, 0, 12)), (16, 78), "Alma de 1,6 (cara de nariz cerrada)", ha="left")
    T4 = h.vista([c4], "frontal", (306, cy), e)
    h.texto(306, cy - 2 * P.RB - 14, "C4 - VISTA DESDE ADENTRO (2:1)", fs=6.5, weight="bold", ha="center")
    h.llamada(T4((0, 0, 0)), (330, 70), "Buje Ø18, pasaje Ø6: eje de la llave Ø5")
    h.llamada(T4((0, 0, P.Z_BOOM)), (330, 78), "Paso del botalón de cola Ø6")
    h.llamada(T4((0, P.Y_PIV, P.Z_TE)), (330, 62), "Perno de pivote B Ø2,5 (ranura en z = -7)")
    h.cota_v(T4((0, P.RB, P.Z_TE - 4)), T4((0, P.RB, P.Z_TE + 4)), T4((0, P.RB, 0))[0] + 5, txt="8", dx=1.2)
    T5 = h.vista(medio([c1], "y", 1), "lateral", (195, cy), e)
    h.texto(203, cy - 2 * P.RB - 14, "C1 - CORTE (2:1)", fs=6.5, weight="bold", ha="center")
    h.cota_h(T5((0, 0, P.RB)), T5((P.T_END, 0, P.RB)), T5((0, 0, P.RB))[1] + 4, txt=f"{P.T_END:g}", fs=5)
    h.cota_h(T5((0, 0, -P.RB)), T5((P.WEB_T, 0, -P.RB)), T5((0, 0, -P.RB))[1] - 4, txt=f1(P.WEB_T), fs=5, dy=-1.2)
    T6 = h.vista([c2], "frontal", (212, 70), 0.75)
    h.texto(212, 70 - 0.75 * P.Z_BOX - 5, "C2 / C3 (3:4, espesor 4)", fs=6, weight="bold", ha="center")
    h.cota_h(T6((0, -P.Y_BOX, P.Z_BOX)), T6((0, P.Y_BOX, P.Z_BOX)), T6((0, 0, P.Z_BOX))[1] + 3.5, txt=f1(2 * P.Y_BOX), fs=5)
    h.cota_v(T6((0, -P.Y_BOX, -P.Z_BOX)), T6((0, -P.Y_BOX, P.Z_BOX)), T6((0, -P.Y_BOX, 0))[0] - 4, txt=f"{2 * P.Z_BOX:g}", fs=5)
    h.guardar(pdf, os.path.join(out, "CS-MEC-05.png"))


def hoja6(pdf, out, R):
    h = Hoja("CS-MEC-06", "Ala: mecanismo y articulación", "1:2 / 4:1", "CFRP / Al 7075-T6",
             notas=("Cuadrilátero articulado A-J-T-B de un grado de libertad.  Con AJ = JT y BT = AB pliega plano dentro del cuerpo.",
                    "Abierta, A-J-T queda alíneada (punto muerto): el manguito, empujado por su resorte, cubre la articulación y la traba.",
                    "El resorte de torsión en B abre el ala; un cordón elástico interior mantiene unidos los tramos (tipo vara de carpa).",
                    "Manguito dimensionado para el momento biaxial de 424 N·mm de la nota de membrana (choque de apertura)."))
    a = h.ax
    e = 0.5
    c = P.D_AB
    seg = P.L_SEG

    def barras(ox, oy, th_deg, titulo, tela=False):
        """Posicion del mecanismo con el tirante a th_deg (180 = estibado, 90 = desplegado)."""
        th = math.radians(th_deg)
        A = np.array([0.0, 0.0])
        B = np.array([c, 0.0])
        Tt = B + c * np.array([math.cos(th), math.sin(th)])
        d = np.linalg.norm(Tt - A)
        if d < 1e-6:
            J = np.array([seg, 0.0])
        else:
            hh = math.sqrt(max(seg ** 2 - (d / 2) ** 2, 0.0))
            m = (A + Tt) / 2
            n = np.array([(Tt - A)[1], -(Tt - A)[0]]) / d
            J = m + n * hh
        o = np.array([ox, oy])
        pA, pB, pT, pJ = (o + e * np.array([p[0], p[1]]) for p in (A, B, Tt, J))
        a.add_patch(Rectangle((ox - 2, oy - 0.5 * 68 * e - 2), 207 * e, 68 * e * 0.5, fc="0.92", ec="0.5", lw=0.3))
        if tela:
            a.add_patch(Polygon([pA, pT, pB], closed=True, fc=(1, 0.85, 0.7), ec="none"))
        a.plot(*zip(pA, pJ, pT), color="#1f4e9c", lw=1.6, solid_capstyle="round")
        a.plot(*zip(pB, pT), color="#1a8a55", lw=1.2, solid_capstyle="round")
        for p, nm, dx, dy in ((pA, "A", -4, 2), (pB, "B", 3, 2), (pT, "T", 2, 3), (pJ, "J", -2, 4)):
            a.add_patch(Circle(p, 1.1, fc="white", ec="k", lw=0.5, zorder=5))
            a.text(p[0] + dx, p[1] + dy, nm, fontsize=7, weight="bold", ha="center")
        a.text(ox + 50, oy - 24, titulo, fontsize=6.5, weight="bold", ha="center")
        return pA, pB, pT, pJ
    barras(28, 222, 179.0, "1. ESTIBADA (dentro del contenedor)")
    barras(150, 222, 140.0, "2. EN APERTURA")
    pA, pB, pT, pJ = barras(282, 178, 90.0, "3. DESPLEGADA Y TRABADA", tela=True)
    h.cota_al(pA, pJ, 5, f"AJ = {f1(seg)}")
    h.cota_al(pJ, pT, 5, f"JT = {f1(seg)}")
    h.cota_v(pB, pT, pB[0] + 9, txt=f"BT = {f1(c)}", dx=1.2)
    h.cota_h(pA, pB, pA[1] - 9, txt=f"AB = {f1(c)}")
    h.texto(28, 186, "Mecanismo en planta, escala 1:2.  Azul: varilla de borde de ataque (dos tramos Ø5/3,5).\n"
            "Verde: tirante de borde de fuga (Ø3/2).  Gris: cuerpo del planeador.", fs=5.6, va="top")
    # ---------------- detalle de la articulación J (4:1), corte longitudinal
    s = 4.0
    ox, oy = 100, 108

    def rect(x0, x1, y0, y1, **kw):
        a.add_patch(Rectangle((ox + s * x0, oy + s * y0), s * (x1 - x0), s * (y1 - y0), **kw))
    Lh = P.SLV_L / 2
    for sg in (1, -1):
        for (y0, y1) in ((P.LE_DI / 2, P.LE_DO / 2), (-P.LE_DO / 2, -P.LE_DI / 2)):
            x0, x1 = (0.8, Lh + 14) if sg > 0 else (-Lh - 14, -0.8)
            rect(x0, x1, y0, y1, fc="0.25", ec="k", lw=0.4)
    for (y0, y1) in ((P.SLV_DI / 2, P.SLV_DO / 2), (-P.SLV_DO / 2, -P.SLV_DI / 2)):
        rect(-Lh, Lh, y0, y1, fc="#b9c4d0", ec="k", lw=0.5, hatch="////")
    for sg in (1, -1):
        rect(sg * 0.8 if sg > 0 else -4.8, 4.8 if sg > 0 else -0.8, -P.LE_DI / 2, P.LE_DI / 2, fc="#e8d9a0", ec="k", lw=0.4)
    a.add_patch(Circle((ox, oy), s * 0.75, fc="white", ec="k", lw=0.5, zorder=5))
    a.plot([ox - s * (Lh + 17), ox + s * (Lh + 17)], [oy, oy], color="0.2", lw=0.2, ls=(0, (9, 2, 1.5, 2)))
    # resorte del manguito
    xs = np.linspace(-Lh - 12, -Lh, 40)
    a.plot(ox + s * xs, oy + s * (3.3 * np.sign(np.sin(np.linspace(0, 12 * np.pi, 40)))), color="0.3", lw=0.5)
    rect(-Lh - 14, -Lh - 12, -3.6, 3.6, fc="#b9c4d0", ec="k", lw=0.4)
    yb = oy - s * P.SLV_DO / 2
    h.cota_h((ox - s * Lh, yb), (ox + s * Lh, yb), yb - 6, txt=f"{P.SLV_L:g}")
    h.cota_v((ox + s * Lh, oy - s * P.SLV_DO / 2), (ox + s * Lh, oy + s * P.SLV_DO / 2), ox + s * Lh + 18, txt=f"Ø{P.SLV_DO:g}", dx=1.2)
    h.cota_v((ox + s * (Lh + 14), oy - s * P.LE_DO / 2), (ox + s * (Lh + 14), oy + s * P.LE_DO / 2), ox + s * (Lh + 14) + 5,
             txt=f"Ø{P.LE_DO:g}", dx=1.2)
    h.llamada((ox + s * 6, oy + s * 3.3), (ox + 30, oy + 30), f"Manguito Al 7075-T6 Ø{P.SLV_DO:g} / {f1(P.SLV_DI)}")
    h.llamada((ox, oy), (ox - 10, oy + 30), "Perno de articulación Ø1,5", ha="right")
    h.llamada((ox + s * 3, oy), (ox + 20, oy - 30), "Horquilla de articulación (Al),\npegada 4 mm en cada tramo")
    h.llamada((ox - s * (Lh + 6), oy - s * 3.3), (ox - 30, oy - 30), "Resorte de compresion + tope", ha="right")
    h.llamada((ox + s * (Lh + 8), oy + s * 2.1), (ox + 96, oy + 24), "Tubo CFRP Ø5 / 3,5")
    h.texto(ox + 10, oy - 46, "DETALLE J - ARTICULACIÓN CON MANGUITO, TRABADA (4:1)", fs=6.5, weight="bold", ha="center")
    # ---------------- detalle del pivote A (4:1): horquilla en la cuaderna, corte por el eje del perno
    ox, oy = 318, 104
    rect(-8, 8, 4, 10, fc="0.55", ec="k", lw=0.4, hatch="....")
    rect(-8, 8, -10, -4, fc="0.55", ec="k", lw=0.4, hatch="....")
    rect(-3, 3, -3.2, 3.2, fc="#b9c4d0", ec="k", lw=0.5)
    rect(3, 16, -2.5, 2.5, fc="0.25", ec="k", lw=0.4)
    rect(-1.25, 1.25, -11.5, 11.5, fc="white", ec="k", lw=0.5)
    h.cota_v((ox + s * 16, oy - s * 4), (ox + s * 16, oy + s * 4), ox + s * 16 + 6, txt="8 (ranura)", dx=1.2)
    h.llamada((ox, oy + s * 9), (ox - 40, oy + 44), "Perno Ø2,5 inox (eje z)", ha="right")
    h.llamada((ox - s * 6, oy + s * 7), (ox - 40, oy + 30), "Oreja de C1 (PA12-CF)", ha="right")
    h.llamada((ox - s * 2.5, oy), (ox - 40, oy - 4), "Herraje de ápice\n(Al 7075)", ha="right")
    h.llamada((ox + s * 10, oy + s * 2.5), (ox + 42, oy + 30), "Varilla de borde\nde ataque")
    h.texto(ox + 10, oy - 54, "DETALLE A - PIVOTE DE ÁPICE (4:1)", fs=6.5, weight="bold", ha="center")
    h.guardar(pdf, os.path.join(out, "CS-MEC-06.png"))


def hoja7(pdf, out, R):
    lan = cad.build("lanzamiento")
    ct = [p["shape"] for p in lan if p["nombre"].startswith("CT")]
    tapa = [p["shape"] for p in lan if p["nombre"].startswith("CT2")]
    h = Hoja("CS-MEC-07", "Contenedor: tubo y tapa nervada", "1:1", "LW-PLA / PA12-CF",
             notas=("Tubo: pieza única de LW-PLA impresa de pie (eje x vertical), 3 perímetros; pared exterior 2,0 mm (S6).",
                    "Tapa: PA12-CF, placa de 2,5 + faldón + 6 nervios de 2,5; pegada al tubo y con 3 tornillos radiales M2,5.",
                    "Cubo central: asiento del aislador (fondo de 4) con ojo de cerradura Ø6 + ranura de 3,6 × 15,2.",
                    "Superficie interior lisa para los patines; exterior sin salientes (S7).  Sin metales pesados (S9)."))
    x0 = P.CT_X[0]
    xc = P.CT_TOP[0] + P.CT_CAP_H
    T = h.vista(medio(ct, "y", 1), "lateral", (40, 215), 1.0, titulo="CORTE A-A (plano y = 0)", ref=(x0, 0, 0), titulo_dy=19)
    yb = T((0, 0, -45))[1]
    h.cota_h(T((x0, 0, -45)), T((P.CT_X[1], 0, -45)), yb - 12, valor=P.CT_LEN)
    h.cota_h(T((x0, 0, -45)), T((P.CT_TOP[0], 0, -45)), yb - 5.5, txt=f"{P.CT_TOP[0] - x0:g}")
    h.cota_h(T((P.CT_TOP[0], 0, -45)), T((xc, 0, -45)), yb - 5.5, txt=f"{P.CT_CAP_H:g}", fs=5)
    h.cota_h(T((xc, 0, -45)), T((P.CT_X[1], 0, -45)), yb - 5.5, txt=f"{P.CT_X[1] - xc:g}")
    xl = T((x0, 0, 0))[0]
    h.cota_v(T((x0, 0, -45)), T((x0, 0, 45)), xl - 7, txt="Ø90")
    h.cota_v(T((x0, 0, -43)), T((x0, 0, 43)), xl - 14, txt="Ø86")
    yt = T((0, 0, 45))[1]
    h.cota_h(T((x0, 0, 45)), T((175, 0, 45)), yt + 5, txt=f"{175 - x0:g}")
    h.cota_h(T((175, 0, 45)), T((185, 0, 45)), yt + 5, txt="10", fs=5)
    h.llamada(T((120, 0, 44)), (T((120, 0, 0))[0], yt + 14), "Pared 2,0 mm")
    h.llamada(T((P.CT_TOP[0] + 1.2, 0, 25)), (T((180, 0, 0))[0], T((0, 0, 20))[1]), "Placa de 2,5", ha="right")
    h.llamada(T((P.CT_TOP[0] + 2, 0, 4)), (T((180, 0, 0))[0], T((0, 0, 6))[1]), "Fondo del cubo: 4", ha="right")
    h.llamada(T((xc - 3.5, 0, P.R_BRIDA)), (T((180, 0, 0))[0], T((0, 0, 34))[1]), "Anclaje de brida Ø3", ha="right")
    h.llamada(T((175, 0, -44)), (T((150, 0, 0))[0], T((0, 0, -30))[1]), "Ø8: interruptor (E4)", ha="right")
    h.llamada(T((185, 0, -44)), (T((150, 0, 0))[0], T((0, 0, -22))[1]), "Ø5: indicador LED (E6)", ha="right")
    T2 = h.vista(tapa, "posterior", (348, 222), 1.0, titulo="TAPA - VISTA DESDE ARRIBA (lado del paracaídas)")
    h.llamada(T2((0, 0, 0)), (T2((0, 0, 0))[0] - 50, T2((0, 0, 0))[1] + 56), "Ojo de cerradura\nd6 + 3,6 × 15,2", ha="right")
    h.llamada(T2((0, 25, 0.5)), (T2((0, 0, 0))[0] - 54, T2((0, 0, 0))[1] - 52), "6 nervios de 2,5\ncada 60°", ha="right")
    h.cota_h(T2((0, P.CT_RI, 0)), T2((0, -P.CT_RI, 0)), T2((0, 0, P.CT_RI))[1] + 5, txt="Ø86")
    T3 = h.vista(ct, "inferior", (40, 105), 1.0, titulo="VISTA INFERIOR (orificios de acceso)", ref=(x0, 0, 0))
    img(h, R and os.path.join(R, "cerrojo.png"), 298, 50, 104)
    h.guardar(pdf, os.path.join(out, "CS-MEC-07.png"))


def main(out, R=None):
    os.makedirs(out, exist_ok=True)
    with PdfPages(os.path.join(out, "Planos_CanSat_AlaDelta.pdf")) as pdf:
        for f in (hoja1, hoja2, hoja3, hoja4, hoja5, hoja6, hoja7):
            f(pdf, out, R)
            print("ok", f.__name__)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
