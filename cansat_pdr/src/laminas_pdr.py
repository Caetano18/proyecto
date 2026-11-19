"""Laminas del PDR en la plantilla de la competencia (presentacion del equipo Hermes, en ingles).

Completa las laminas que le tocan al subsistema mecanico (configuracion del sistema, layout fisico,
control de descenso, diseno mecanico y presupuesto de masa) con el estilo de las laminas que el equipo ya
lleno (tarjetas F1F4F9, titulos 138A8A, tablas con encabezado 242C4F, Montserrat). Agrega dos laminas de
verificacion estructural despues de "Selection (with criteria)" del subsistema mecanico y renumera.

Uso: python3 laminas_pdr.py <presentacion_equipo.pptx> <salida.pptx>
Lee los resultados de ../fea (masas, paracaidas, planeo, aero, resultados_fea) y las figuras *_en.png de ../figs.
"""
import sys
import os
import re
import copy
import json
import math
from xml.sax.saxutils import escape
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.util import Emu
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
import params as P

AQUI = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(AQUI, "..", "figs")
FEA = os.path.join(AQUI, "..", "fea")
TMP = os.environ.get("LAMINAS_TMP", os.path.join(AQUI, "..", "build", "laminas_img"))
os.makedirs(TMP, exist_ok=True)

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
EMU_IN = 914400
NAVY, TEAL, CARD, BORDE, GRIS, ROJO, BLANCO = "242C4F", "138A8A", "F1F4F9", "D5DAE5", "5B6478", "B23A2E", "FFFFFF"
SEL = "FBE9E9"            # fondo de la opcion seleccionada (rojo muy claro, como en los PDR de referencia)
FONT = "Montserrat"
X0, X1, Y0, Y1 = 368560, 11823440, 2150000, 6450000
W_UTIL = X1 - X0
GAP = 256000


def I(x):
    return int(round(x * EMU_IN))


def j(name):
    return json.load(open(os.path.join(FEA, name), encoding="utf-8"))


MAS = j("masas.json")
PAR = j("paracaidas.json")
PL = j("planeo.json")
AE = j("aero.json")
R = j("resultados_fea.json")                     # CanSat parado y fijo en la base (ensayo de la lijadora)
RV = j("resultados_fea_vuelo.json") if os.path.exists(os.path.join(FEA, "resultados_fea_vuelo.json")) else None  # vuelo


def n(x, d=1):
    return f"{x:.{d}f}"


def ms(x):
    return ("+" if x >= 0 else "−") + f"{abs(x):.2f}"


# ============================================================ texto
def _run(text, sz, bold, color, italic=False):
    return (f'<a:r><a:rPr lang="en-US" sz="{int(round(sz * 100))}" b="{1 if bold else 0}" i="{1 if italic else 0}" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:latin typeface="{FONT}"/><a:ea typeface="{FONT}"/><a:cs typeface="{FONT}"/></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r>')


def _runs(text, sz, color, bold=False, italic=False):
    """**negrita** y [[color:texto]] (color en hex) dentro de un renglon."""
    out = []
    for parte in re.split(r"(\*\*.+?\*\*|\[\[[0-9A-F]{6}:.+?\]\])", text):
        if not parte:
            continue
        if parte.startswith("**"):
            out.append(_run(parte[2:-2], sz, True, color, italic))
        elif parte.startswith("[["):
            c, t = parte[2:-2].split(":", 1)
            out.append(_run(t, sz, True, c, italic))
        else:
            out.append(_run(parte, sz, bold, color, italic))
    return "".join(out)


def parrafo(text, sz=14, color=NAVY, bullet=False, bold=False, italic=False, algn="l", spc=500, lvl=0):
    if bullet:
        mar = 228600 + 200000 * lvl
        car = "•" if lvl == 0 else "–"
        ppr = (f'<a:pPr marL="{mar}" indent="-228600" algn="{algn}"><a:spcBef><a:spcPts val="{spc}"/></a:spcBef>'
               f'<a:buFont typeface="Arial"/><a:buChar char="{car}"/></a:pPr>')
    else:
        ppr = f'<a:pPr algn="{algn}"><a:spcBef><a:spcPts val="{spc}"/></a:spcBef><a:buNone/></a:pPr>'
    xml = (f'<a:p xmlns:a="{A_NS}">{ppr}{_runs(text, sz, color, bold, italic)}'
           f'<a:endParaRPr lang="en-US" sz="{int(round(sz * 100))}" dirty="0"/></a:p>')
    return etree.fromstring(xml)


def _llenar(txBody, items, sz, color=NAVY, titulo=None, sz_tit=None, spc=500):
    for p in txBody.findall(qn("a:p")):
        txBody.remove(p)
    if titulo:
        txBody.append(parrafo(titulo, sz_tit or sz + 1, TEAL, bold=True, spc=0))
    for k, it in enumerate(items):
        if isinstance(it, tuple):           # (texto, nivel) o ("", "nota")
            t, lvl = it
            if lvl == "plain":
                txBody.append(parrafo(t, sz, color, spc=spc))
            elif lvl == "note":
                txBody.append(parrafo(t, sz - 1.5, GRIS, italic=True, spc=spc))
            else:
                txBody.append(parrafo(t, sz - 1, color, bullet=True, lvl=lvl, spc=max(spc - 200, 0)))
        else:
            txBody.append(parrafo(it, sz, color, bullet=True, spc=(spc if (titulo or k) else 0)))


def _body(sh, l=180000, t=120000, r=180000, b=80000, anchor="t"):
    bp = sh._element.txBody.find(qn("a:bodyPr"))
    for k, v in dict(wrap="square", lIns=l, tIns=t, rIns=r, bIns=b, rtlCol="0", anchor=anchor).items():
        bp.set(k, str(v))
    for ch in list(bp):
        bp.remove(ch)
    etree.SubElement(bp, qn("a:noAutofit"))


def tarjeta(sl, x, y, w, h, titulo=None, items=(), sz=13, nombre="Card", fill=CARD, sz_tit=None, spc=500, anchor="t"):
    sh = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    sh.name = nombre
    sh.adjustments[0] = min(129000 / min(w, h), 0.2)        # mismo radio de esquina que las tarjetas del equipo
    sh.fill.solid()
    sh.fill.fore_color.rgb = RGBColor.from_string(fill)
    sh.line.fill.background()
    st = sh._element.find(qn("p:style"))
    if st is not None:
        sh._element.remove(st)
    etree.SubElement(sh._element.spPr, qn("a:effectLst"))
    _body(sh, anchor=anchor)
    _llenar(sh._element.txBody, list(items), sz, titulo=titulo, sz_tit=sz_tit, spc=spc)
    return sh


def texto(sl, x, y, w, h, items, sz=11, color=NAVY, nombre="Text", algn="l", anchor="t", italic=False):
    tb = sl.shapes.add_textbox(x, y, w, h)
    tb.name = nombre
    _body(tb, 0, 0, 0, 0, anchor)
    txb = tb._element.txBody
    for p in txb.findall(qn("a:p")):
        txb.remove(p)
    for k, it in enumerate(items):
        txb.append(parrafo(it, sz, color, algn=algn, italic=italic, spc=0 if k == 0 else 300))
    return tb


def nota(sl, x, y, w, h, t, sz=10.5):
    return texto(sl, x, y, w, h, [t], sz, GRIS, "Note", italic=True)


def etiqueta(sl, x, y, w, h, t, fill=TEAL, sz=10):
    sh = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    sh.name = "Tag"
    sh.adjustments[0] = 0.3
    sh.fill.solid()
    sh.fill.fore_color.rgb = RGBColor.from_string(fill)
    sh.line.fill.background()
    st = sh._element.find(qn("p:style"))
    if st is not None:
        sh._element.remove(st)
    _body(sh, 40000, 0, 40000, 0, "ctr")
    txb = sh._element.txBody
    for p in txb.findall(qn("a:p")):
        txb.remove(p)
    txb.append(parrafo(t, sz, BLANCO, bold=True, algn="ctr", spc=0))
    return sh


# ============================================================ tablas
def _tcpr(fill, anchor="ctr", ml=100000, mt=45000):
    lados = "".join(f'<a:{l} w="9525"><a:solidFill><a:srgbClr val="{BORDE}"/></a:solidFill></a:{l}>'
                    for l in ("lnL", "lnR", "lnT", "lnB"))
    return etree.fromstring(f'<a:tcPr xmlns:a="{A_NS}" marL="{ml}" marR="{ml}" marT="{mt}" marB="{mt}" anchor="{anchor}">'
                            f'{lados}<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr>')


def tabla(sl, x, y, w, anchos, cab, filas, sz=11, sz_cab=12, alto=None, alto_cab=None, alin=None, resaltar=(),
          col_sel=None, negrita_col0=True, nombre="Table", ml=100000, mt=45000, sub=()):
    """anchos relativos; filas de textos (\\n = otro parrafo). resaltar: indices de fila con fondo SEL;
    col_sel: columna seleccionada (fondo SEL); sub: filas de subtotal (fondo CARD, negrita)."""
    nf, nc = len(filas) + (1 if cab else 0), len(anchos)
    alto = alto or I(0.30)
    alto_cab = alto_cab or alto
    h = (alto_cab if cab else 0) + alto * len(filas)
    gf = sl.shapes.add_table(nf, nc, x, y, w, h)
    gf.name = nombre
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    for k in list(tblPr.attrib):
        del tblPr.attrib[k]
    tblPr.set("firstRow", "1")
    tblPr.set("bandRow", "0")
    for ch in list(tblPr):
        tblPr.remove(ch)
    sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = "{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"
    tot = float(sum(anchos))
    acum = 0
    for c, a in enumerate(anchos):
        cw = int(round(w * a / tot)) if c < nc - 1 else w - acum
        tbl.columns[c].width = cw
        acum += cw
    alin = alin or ["l"] * nc
    filas_tot = ([cab] if cab else []) + list(filas)
    for r, fila in enumerate(filas_tot):
        es_cab = bool(cab) and r == 0
        rf = r - (1 if cab else 0)
        tbl.rows[r].height = alto_cab if es_cab else alto
        for c in range(nc):
            txt = fila[c] if c < len(fila) else ""
            tc = tbl.cell(r, c)._tc
            txb = tc.txBody
            for p in txb.findall(qn("a:p")):
                txb.remove(p)
            if es_cab:
                fill, color, bold, s = ("C00000" if c == col_sel else NAVY), BLANCO, True, sz_cab
            else:
                sel = (rf in resaltar) or (col_sel is not None and c == col_sel)
                es_sub = rf in sub
                fill = SEL if sel else (CARD if (c == 0 or es_sub) else BLANCO)
                color, bold, s = NAVY, (c == 0 and negrita_col0) or es_sub, sz
            for k, linea in enumerate(str(txt).split("\n")):
                txb.append(parrafo(linea, s, color, bold=bold, algn=alin[c] if not es_cab else ("l" if alin[c] == "l" else alin[c]),
                                   spc=0 if k == 0 else 200))
            old = tc.find(qn("a:tcPr"))
            if old is not None:
                tc.remove(old)
            tc.append(_tcpr(fill, ml=ml, mt=mt))
    return gf


# ============================================================ imagenes
def recortar(nombre, pad=12, umbral=246, src=FIGS):
    """Recorta el blanco alrededor de la figura (para aprovechar el lugar en la lamina)."""
    src_p = os.path.join(src, nombre)
    out = os.path.join(TMP, "r_" + nombre)
    im = Image.open(src_p).convert("RGB")
    g = im.convert("L").point(lambda v: 255 if v < umbral else 0)
    bb = g.getbbox()
    if bb:
        x0, y0, x1, y1 = bb
        im = im.crop((max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, im.width), min(y1 + pad, im.height)))
    im.save(out)
    return out, im.width, im.height


def imagen(sl, nombre, x, y, w, h, alin="c", valin="c", src=FIGS, nombre_sh=None):
    p, iw, ih = recortar(nombre, src=src)
    esc = min(w / iw, h / ih)
    ww, hh = int(iw * esc), int(ih * esc)
    xx = x + {"l": 0, "c": (w - ww) // 2, "r": w - ww}[alin]
    yy = y + {"t": 0, "c": (h - hh) // 2, "b": h - hh}[valin]
    pic = sl.shapes.add_picture(p, xx, yy, ww, hh)
    pic.name = nombre_sh or ("Figure " + nombre)
    return pic


def panel(sl, x, y, w, h, figs, pie=None, sz_pie=10.5, pad=I(0.12)):
    """Tarjeta con una o varias figuras lado a lado (lista de (nombre, peso_ancho)) y un pie opcional."""
    tarjeta(sl, x, y, w, h, nombre="Figure panel")
    hp = I(0.42) if pie else 0
    tot = sum(p for _, p in figs)
    xx = x + pad
    wu = w - 2 * pad - pad * (len(figs) - 1)
    for nom, peso in figs:
        ww = int(wu * peso / tot)
        imagen(sl, nom, xx, y + pad, ww, h - 2 * pad - hp)
        xx += ww + pad
    if pie:
        texto(sl, x + pad, y + h - hp - I(0.04), w - 2 * pad, hp, [pie], sz_pie, GRIS, "Caption", algn="c", anchor="ctr", italic=True)


# ============================================================ estructura de la presentacion
def limpiar(sl):
    """Quita el bloque 'Expectations' de la plantilla (todo lo que esta debajo del encabezado)."""
    for sh in list(sl.shapes):
        if sh.top is not None and sh.top >= 2000000:
            sh._element.getparent().remove(sh._element)


def badge(sl):
    for sh in sl.shapes:
        if sh.shape_type == 1 and sh.left == 368560 and sh.top == 1500000 and sh.has_text_frame:
            return sh
    return None


def poner_texto_run(sh, txt):
    rs = sh.text_frame.paragraphs[0].runs
    rs[0].text = txt
    for r in rs[1:]:
        r.text = ""


def subtitulo(sl):
    for sh in sl.shapes:
        if sh.has_text_frame and sh.left == 1050000 and sh.top == 1500000:
            return sh
    return None


def seccion(sl):
    for sh in sl.shapes:
        if sh.has_text_frame and sh.left == 1560000 and sh.top == 150000:
            return sh
    return None


def duplicar(prs, idx_src, pos):
    """Copia la lamina idx_src (0-based) con su encabezado y la ubica en la posicion pos (0-based)."""
    src = prs.slides[idx_src]
    new = prs.slides.add_slide(src.slide_layout)
    for sh in list(new.shapes):
        sh._element.getparent().remove(sh._element)
    mapa = {}
    for rid, rel in src.part.rels.items():
        if rel.reltype.endswith("/image"):
            mapa[rid] = new.part.relate_to(rel._target, rel.reltype)
    bg = src._element.find(qn("p:cSld")).find(qn("p:bg"))
    if bg is not None:                      # el fondo (barras y logo) vive fuera de las formas
        bg2 = copy.deepcopy(bg)
        for bl in bg2.iter(qn("a:blip")):
            if bl.get(qn("r:embed")) in mapa:
                bl.set(qn("r:embed"), mapa[bl.get(qn("r:embed"))])
        new._element.find(qn("p:cSld")).insert(0, bg2)
    for el in src.shapes._spTree.iterchildren():
        if el.tag in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            continue
        e2 = copy.deepcopy(el)
        for b in e2.iter(qn("a:blip")):
            rid = b.get(qn("r:embed"))
            if rid in mapa:
                b.set(qn("r:embed"), mapa[rid])
        new.shapes._spTree.append(e2)
    lst = prs.slides._sldIdLst
    ids = list(lst)
    el = ids[-1]
    lst.remove(el)
    lst.insert(pos, el)
    return prs.slides[pos]


# ============================================================ datos
FILAS = MAS["filas"]
G0 = P.G0


def fila(clave):
    return next(f for f in FILAS if clave in f["item"])


m_plan, m_cont = MAS["m_planeador"], MAS["m_contenedor"]
TUBO_EN = {"GFRP": "glass-epoxy", "ASALW": "LW-ASA", "LWPLA": "LW-PLA"}.get(P.CT_MAT, P.CT_MAT)
HIBRIDO = P.CT_MAT == "GFRP" and P.CT_LAM_INF != P.CT_LAM
if HIBRIDO:
    TUBO_EN = "carbon / glass-epoxy"
TUBO_DESC = (f"carbon-epoxy {P.CT_T_INF:g} mm (lower {P.CT_X_H - P.CT_X[0]:.0f} mm) + glass-epoxy {P.CT_T:g} mm "
             "(upper, RF window over radio and GNSS)") if HIBRIDO else f"{TUBO_EN}, {P.CT_T:g} mm wall"
lastre = MAS["lastre"]
mtot = MAS["total"]

EN = {  # nombres en ingles de los renglones del presupuesto de masa
    "Cuaderna de nariz C1": ("Nose bulkhead C1 (PA12-CF)", "S"),
    "Cuadernas C2 y C3": ("Bulkheads C2 and C3 (PA12-CF)", "S"),
    "Cuaderna de cola C4": ("Tail bulkhead C4 (PA12-CF)", "S"),
    "Largueros angulares": ("Corner angles CFRP 6×6×1 × 201", "S"),
    "Paneles laterales": ("Side panels G10 0.5 mm", "S"),
    "Tapa superior": ("Top cover G10 0.5 mm", "S"),
    "Bandeja de avionica": ("Avionics tray G10 0.8 mm", "S"),
    "Rieles longitudinales": ("Tray rails (PA12-CF)", "S"),
    "Cunas de ala": ("Wing cradles (PA12-CF)", "S"),
    "Guias de botalon": ("Boom guides (PA12-CF)", "S"),
    "Cubierta inferior": ("Bottom cover PC 0.25 mm", "S"),
    "Tornillos M2": ("Screws M2/M2.5, inserts, adhesive", "S"),
    "Varillas de borde de ataque": ("Leading-edge rods CFRP Ø5/3.5 (4 segments)", "S"),
    "Tirantes de borde de fuga": ("Trailing-edge struts CFRP Ø3/2", "S"),
    "Varillas de raiz": ("Root rods CFRP", "S"),
    "Manguitos de traba": ("Locking sleeves (Al 7075)", "S"),
    "Herrajes A, B y T": ("Fittings A, B and T (Al 7075)", "S"),
    "Membrana ripstop": ("Ripstop membrane with seams", "S"),
    "Articulaciones, resortes": ("Hinges, springs, bungee cord", "S"),
    "Botalon + cola en V": ("Tail boom + V-tail + fittings", "S"),
    "Servo de cola": ("Tail servo (9 g class)", "C"),
    "Bateria Li-ion 18650": ("Li-ion 18650 cell (1S)", "C"),
    "Sillas + cincha": ("Battery cradles + strap", "C"),
    "PCB principal": ("Main PCB (MCU, IMU, baro, SD)", "C"),
    "PCB radio": ("Radio + GNSS PCB + antenna", "C"),
    "Camaras cenit y nadir": ("Zenith and nadir cameras", "C"),
    "Baliza sonora": ("Audio beacon + coin cell", "C"),
    "Celdas solares": ("Solar cells", "C"),
    "Servo del cerrojo": ("Release servo (9 g class)", "C"),
    "Separadores, cableado": ("Spacers, wiring, connectors", "C"),
    "Llave de bayoneta": ("Bayonet key + bearing plate (A2-70)", "C"),
    "Arandela de la llave": ("Key washer on C4 (Al 7075, Ø22)", "C"),
    "Aislador elastomerico": ("Key elastomer isolator", "C"),
    "Patines de C1": ("C1 guide pads (elastomer + PTFE)", "C"),
    "Zapatas de patin": ("Pad shoes on C2 and C3 (PA12-CF)", "S"),
    "Manguito elastomerico del centrador": ("Tail centring sleeve (elastomer)", "C"),
    "Tubo d90": ((f"Container tube Ø90 × {P.CT_LEN:g}: carbon {P.CT_T_INF:g} + glass {P.CT_T:g} mm") if HIBRIDO
                 else f"Container tube Ø90 × {P.CT_LEN:g}, {P.CT_T:g} mm wall ({TUBO_EN})", "S"),
    "Tapa nervada": ("Ribbed container cap (PA12-CF)", "S"),
    "Paracaidas de 15": ("Container parachute (15 m/s)", "C"),
    "Brida de 3 puntos": ("3-point bridle + swivel", "C"),
    "Lastre de centrado": ("Trim ballast / mass margin", "C"),
}
FUENTE = {"CAD": "CAD", "Estimado": "Estimate", "Nota de membrana": "Wing note", "Asignacion": "Allocation",
          "Hoja de datos": "Datasheet", "Ajuste": "Balance"}


def en(f):
    for k, v in EN.items():
        if k in f["item"]:
            return v
    raise KeyError(f["item"])


def mfila(f):
    nom, _ = en(f)
    return [nom, str(f["cant"]), n(f["masa"]), "±" + n(f["inc"]), FUENTE.get(f["fuente"], f["fuente"])]


def suma(fs):
    return sum(f["masa"] for f in fs), math.sqrt(sum(f["inc"] ** 2 for f in fs))


# ============================================================ laminas
def L17_configA(sl):
    wi = I(5.0)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("opcion_a.png", 1)],
          "Configuration A deployed: the Ø90 body is the fuselage; the wings exit through two side slots.")
    tarjeta(sl, X0 + wi + GAP, Y0, W_UTIL - wi - GAP, Y1 - Y0, "A · Integral body with wing slots", [
        "**Structure:** the printed Ø90 × 242 mm cylinder is both container and fuselage. The folded delta wing lies "
        "along the avionics box and opens through two 16 × 200 mm slots in the wall.",
        "**First stage (C3):** the whole CanSat descends at 15 m/s under a parachute fixed to the top cap.",
        "**Second stage (C4):** at 80 % of apogee the parachute is released, the wing latches open and the full "
        f"500 g glides (≈ {n(MAS['w_estimado'])} m/s estimated).",
        "**Container:** not a separate part; only the parachute is left behind.",
        "**Against:** the slotted wall becomes two shells and loses the stiffness S6 requires; the openings are far "
        "beyond the small access holes of E5; the wing is exposed during ejection; wing latches, an actuator and a "
        "parachute release are needed (M2).",
    ], sz=13)


def L18_configB(sl):
    wi = I(5.6)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("lan_corte.png", 0.8), ("des_iso.png", 1.25)],
          "Left: launch configuration (cutaway). Right: payload after release, wing deployed.")
    tarjeta(sl, X0 + wi + GAP, Y0, W_UTIL - wi - GAP, Y1 - Y0, "B · Container + delta-wing glider (payload)", [
        f"**Container:** closed laminated tube Ø90 × {P.CT_LEN:g} mm ({TUBO_DESC}) and a ribbed PA12-CF cap; "
        "the 15 m/s parachute is packed above the cap.",
        f"**Payload:** {P.L_G:g} mm glider. CFRP corner angles, G10 panels and four PA12-CF bulkheads; the membrane "
        "delta wing is folded flat in the two side bays.",
        "**First stage (C3):** the CanSat descends at ≈ 15 m/s under the container parachute.",
        "**Second stage (C4):** at 80 % of apogee one servo turns the bayonet key; the glider drops out of the open "
        f"bottom end, the wing opens passively and the payload glides at ≈ {n(MAS['w_planeador_solo'])} m/s "
        f"({m_plan:.0f} g). The container goes on under its parachute ({n(PAR['disenos'][1]['v_contenedor'])} m/s).",
        "**Against:** two objects descend; the container needs its own parachute.",
    ], sz=13)


def L19_seleccion(sl):
    filas = [
        ["Rigid exterior wall that does not flex (S6)", "High", "Partial: wall split by the slots", "Meets: closed tube"],
        ["Slides freely out of the rocket (S7)", "High", "Risk: rods against the airframe", "Meets: smooth outer wall"],
        ["Small access holes only (E5)", "Medium", "Two 200 mm slots", "Switch and LED holes ≤ 8 mm"],
        ["Wing deployment", "High", "Active: latches + actuator", "Passive: springs; the wall holds the wing"],
        ["Wing protection at ejection (S5)", "Medium", "Exposed", "Protected by the tube"],
        ["Mass that glides / wing loading", "Medium", f"500 g / {MAS['carga_alar']:.0f} N/m²",
         f"{m_plan:.0f} g / {MAS['carga_alar_planeador']:.0f} N/m²"],
        ["Second-stage descent rate (C4: 5 ± 3 m/s)", "High", f"{n(MAS['w_estimado'])} m/s", f"{n(MAS['w_planeador_solo'])} m/s"],
        ["Critical mechanisms", "Medium", "Wing latches + parachute release", "One bayonet key (one servo)"],
        ["Objects that descend", "Low", "One", "Two (container under its parachute)"],
    ]
    tabla(sl, X0, Y0, W_UTIL, [3.3, 0.9, 3.0, 3.3], ["Criterion", "Weight", "A · Integral body", "B · Container + glider (selected)"],
          filas, sz=11, alto=I(0.305), alto_cab=I(0.34), col_sel=3)
    y = Y0 + I(0.34) + 9 * I(0.305) + I(0.17)
    tarjeta(sl, X0, y, W_UTIL, Y1 - y, "Selection: B · Container + glider", [
        "Only B meets S6 and S7 as written, it makes the wing deployment passive and it lowers the wing loading by 25 %.",
        "The cost is a second object descending: the container comes down under its own parachute.",
        "If A were required, the frame, wing and glider analyses stay valid; only the slotted tube would be redesigned and re-analysed.",
    ], sz=12, spc=300)


def L20_dimensiones(sl):
    wa = I(8.35)
    hf = I(3.35)
    panel(sl, X0, Y0, wa, hf, [("lam_dimensiones.png", 1)])
    y = Y0 + hf + I(0.17)
    tabla(sl, X0, y, wa, [1, 1, 1, 1, 1, 1],
          ["Tube wall", "Tube bore", "Pivots A–B", "Avionics box", "Payload mass", "CanSat mass (S1)"],
          [[ (f"{P.CT_T_INF:g} / {P.CT_T:g} mm" if HIBRIDO else f"{P.CT_T:g} mm"),
             (f"Ø{2 * P.CT_RI_INF:g} / {2 * P.CT_RI:g}" if HIBRIDO else f"Ø{2 * P.CT_RI:g} mm"), f"{n(P.D_AB)} mm", f"{n(2 * P.Y_OUT)} × {n(2 * P.Z_BOX + P.T_COVER)}", f"{m_plan:.0f} g", f"{mtot:.0f} g"]],
          sz=11.5, sz_cab=11, alto=I(0.4), alto_cab=I(0.4), alin=["c"] * 6, negrita_col0=False)
    x = X0 + wa + GAP
    panel(sl, x, Y0, X1 - x, Y1 - Y0, [("lam_planta.png", 1)],
          f"Span {n(P.SPAN)} mm · area {P.S_TRI:.0f} cm² · AR 4.0. All dimensions in mm.")


def L21_componentes(sl):
    wi = I(6.9)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("equipos_anot_en.png", 1)],
          "Left side panel, top cover and wing hidden. Electronics envelopes are allocations.")
    tarjeta(sl, X0 + wi + GAP, Y0, W_UTIL - wi - GAP, Y1 - Y0, "Three bays on one G10 tray", [
        "**Nose bay (C1–C2):** trim ballast and tail servo.",
        "**Centre bay:** 18650 cell on two cradles above the tray; main PCB (MCU, IMU, barometer, SD) under the tray.",
        "**Tail bay (C3–C4):** radio + GNSS PCB above the tray; release servo and bayonet key at C4.",
        "**GNSS and radio antennas:** under the G10 top cover and side panels, which are RF-transparent; carbon only on the four edges.",
        "**Top cover:** solar cells (E3) and zenith camera (C6). **Under the tray:** nadir camera (C7).",
        "**Switches and LED (E4, E6, E9):** reached through ≤ 8 mm holes in the container wall.",
    ], sz=12, spc=400)


def L22_lanzamiento(sl):
    wa, wb = I(2.55), I(5.15)
    panel(sl, X0, Y0, wa, Y1 - Y0, [("lan_corte.png", 1)])
    panel(sl, X0 + wa + GAP, Y0, wb, Y1 - Y0, [("lam_lanzamiento.png", 1)], "Section through the CanSat, as it sits in the rocket")
    x = X0 + wa + wb + 2 * GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Stowed for launch", [
        "**Support:** the CanSat stands on the rocket support at its open end, with nothing above it (launch vehicle document).",
        "**Wing:** folded flat in the side bays, held by the tube wall.",
        "**Tail boom:** stowed on the top cover, guided in C2–C4.",
        f"**Parachute:** packed above the cap ({P.CT_X[1] - P.CT_TOP[0] - P.CT_CAP_H:g} mm space).",
        "**Retention:** bayonet key through the cap; geometric lock (M2).",
        f"**Guidance:** C1 on four {P.PAD_T:g} mm PTFE-faced pads ({P.ELAST_SH} Shore A); C4 collar centred in the cap.",
        "**S7:** smooth outer wall; nothing protrudes from the cylinder.",
    ], sz=11.5, spc=350)


def L23_desplegado(sl):
    wi = I(6.6)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("des_iso_anot_en.png", 1)], "Payload after release with the wing and tail deployed")
    x = X0 + wi + GAP
    tabla(sl, x, Y0, X1 - x, [2.0, 1.6], ["Deployed glider", "Value"], [
        ["Span / root chord", f"{P.SPAN:.0f} / {P.D_AB:.0f} mm"],
        ["Area / aspect ratio", f"{P.S_TRI:.0f} cm² / 4.0"],
        ["Flight mass", f"{m_plan:.0f} g"],
        ["Wing loading", f"{MAS['carga_alar_planeador']:.0f} N/m²"],
        ["Trim angle of attack", "≈ 20°"],
        ["Descent rate (estimate)", f"{n(MAS['w_planeador_solo'])} m/s"],
    ], sz=11, alto=I(0.31), alto_cab=I(0.34))
    y = Y0 + I(0.34) + 6 * I(0.31) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Deployment sequence (passive)", [
        "The tube wall holds the rods while the glider is inside.",
        "Out of the tube, a torsion spring at B opens the strut; an inner bungee aligns the two rod segments.",
        "A spring-loaded Al sleeve slides over hinge J and locks it (M2).",
    ], sz=11.5, spc=300)


def pasos(sl, x, y, w, h, items, d=I(0.42)):
    """Secuencia de pasos con circulos numerados (formas nativas, editables)."""
    tarjeta(sl, x, y, w, h, nombre="Sequence panel")
    n_ = len(items)
    cw = (w - I(0.2)) // n_
    yc = y + I(0.18) + d // 2
    ln = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x + I(0.1) + cw // 2, yc, x + I(0.1) + cw * (n_ - 1) + cw // 2, yc)
    ln.line.color.rgb = RGBColor.from_string(TEAL)
    ln.line.width = Emu(19050)
    for k, (tit, txt) in enumerate(items):
        cx = x + I(0.1) + cw * k + cw // 2
        c = sl.shapes.add_shape(MSO_SHAPE.OVAL, cx - d // 2, yc - d // 2, d, d)
        c.fill.solid()
        c.fill.fore_color.rgb = RGBColor.from_string(NAVY)
        c.line.fill.background()
        st = c._element.find(qn("p:style"))
        if st is not None:
            c._element.remove(st)
        _body(c, 0, 0, 0, 0, "ctr")
        txb = c._element.txBody
        for p in txb.findall(qn("a:p")):
            txb.remove(p)
        txb.append(parrafo(str(k + 1), 13, BLANCO, bold=True, algn="ctr", spc=0))
        tb = sl.shapes.add_textbox(cx - cw // 2 + I(0.06), yc + d // 2 + I(0.08), cw - I(0.12), h - d - I(0.35))
        _body(tb, 0, 0, 0, 0, "t")
        txb = tb._element.txBody
        for p in txb.findall(qn("a:p")):
            txb.remove(p)
        txb.append(parrafo(tit, 12, TEAL, bold=True, algn="ctr", spc=0))
        txb.append(parrafo(txt, 10.5, NAVY, algn="ctr", spc=300))


APOGEO = 673.0       # m, simulacion OpenRocket del equipo (lamina 25)


def L45_descenso(sl):
    hf = I(2.1)
    cr = next(d for d in PAR["disenos"] if d["clave"] == "cruz")
    h80 = 0.8 * APOGEO
    nd = PL["nominal"]["cuerpo romo (disco de nariz plano)"]
    R_esp = nd["delta"]["V"] ** 2 / (G0 * math.tan(math.radians(20)))
    pasos(sl, X0, Y0, W_UTIL, hf, [
        ("Ejection", f"At apogee (≈ {APOGEO:.0f} m). The charge pushes the CanSat out: 30 G shock."),
        ("Parachute, 15 m/s", "The cross canopy opens; the CanSat hangs from the 3-point bridle, glider inside."),
        ("Release at 80 %", f"≈ {h80:.0f} m: the servo turns the bayonet key 90° and the glider drops out."),
        ("Wing opens", "Torsion springs open the wing, the sleeves lock the hinges, the tail deploys."),
        ("Spiral glide, 5 m/s", f"20° bank, ≈ {R_esp:.0f} m radius; cameras film zenith and nadir."),
        ("Landing", f"Glider ≈ {h80 / MAS['w_planeador_solo']:.0f} s after release; container at {n(cr['v_contenedor'])} m/s; beacon on."),
    ])
    y = Y0 + hf + I(0.15)
    w2 = (W_UTIL - GAP) // 2
    tarjeta(sl, X0, y, w2, Y1 - y, "Stage 1 · Container parachute (C3)", [
        f"**Cross parachute**, S0 = {cr['S0_cm2']:.0f} cm² (arms {cr['geo']['brazo_mm']:.0f} mm, span {cr['geo']['envergadura_mm']:.0f} mm), ripstop nylon.",
        f"**Descent:** {n(cr['v_rango'][0])} to {n(cr['v_rango'][1])} m/s with 500 g (Cd0 ± 10 %).",
        "**Attachment:** 3-point Kevlar bridle on the cap ribs + swivel; the container hangs open end down.",
    ], sz=12, spc=300)
    tarjeta(sl, X0 + w2 + GAP, y, w2, Y1 - y, "Stage 2 · Delta-wing glider (C4)", [
        "**Release at 80 % of apogee:** the servo turns the bayonet key 90° and the glider drops out.",
        f"**Glide:** membrane delta wing, {P.S_TRI:.0f} cm², ≈ {n(MAS['w_planeador_solo'])} m/s with {m_plan:.0f} g; "
        "spiral at 20° bank.",
        f"**Container** continues alone at {n(cr['v_contenedor'])} m/s.",
    ], sz=12, spc=300)


def L46_paracaidas(sl):
    wi = I(6.0)
    panel(sl, X0, Y0, wi, Y1 - Y0 - I(0.95), [("paracaidas_en.png", 1)])
    nota_y = Y1 - I(0.85)
    tarjeta(sl, X0, nota_y, wi, I(0.85), None, [(
        "Sizing: m g = ½ ρ V² Cd0 S0, with m = 500 g, V = 15 m/s, ρ = 1.15 kg/m³ (≈ 700 m). "
        "Cd0 from Knacke, Parachute Recovery Systems Design Manual, table 5-1.", "plain")], sz=10.5)
    x = X0 + wi + GAP
    d = {k["clave"]: k for k in PAR["disenos"]}
    tabla(sl, x, Y0, X1 - x, [1.45, 1.55, 1.55, 1.55], ["", "Flat circular", "Cross", "Hemispherical"], [
        ["Cd0 (S0 ref.)", "0.75", "0.70", "0.70"],
        ["S0 for 15 m/s", f"{d['plano']['S0_cm2']:.0f} cm²", f"{d['cruz']['S0_cm2']:.0f} cm²", f"{d['hemi']['S0_cm2']:.0f} cm²"],
        ["Size", f"D0 = {d['plano']['geo']['D0_mm']:.0f} mm", f"arms {d['cruz']['geo']['brazo_mm']:.0f} mm,\nspan {d['cruz']['geo']['envergadura_mm']:.0f} mm",
         f"projected D = {d['hemi']['geo']['D_proyectado_mm']:.0f} mm"],
        ["Oscillation", "±10 to 40°", "0 to ±3°", "±10 to 15°"],
        ["Fabrication", "6 gores + spill hole", "Flat cloth, no gores", "8 to 12 shaped gores"],
        ["Fabric mass", f"{d['plano']['m_tela_g']:.1f} g", f"{d['cruz']['m_tela_g']:.1f} g", f"{d['hemi']['m_tela_g']:.1f} g"],
        ["V for Cd0 ± 10 %", f"{n(d['plano']['v_rango'][0])}–{n(d['plano']['v_rango'][1])} m/s",
         f"{n(d['cruz']['v_rango'][0])}–{n(d['cruz']['v_rango'][1])} m/s", f"{n(d['hemi']['v_rango'][0])}–{n(d['hemi']['v_rango'][1])} m/s"],
    ], sz=10.5, sz_cab=11.5, alto=I(0.38), alto_cab=I(0.34), alin=["l", "c", "c", "c"], ml=70000)
    y = Y0 + I(0.34) + 7 * I(0.38) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Draft 45 cm canopy is too large", [
        f"A 45 cm flat canopy ({PAR['plano_45cm']['S0_cm2']:.0f} cm²) brings 500 g down at "
        f"[[{ROJO}:{n(PAR['plano_45cm']['v'])} m/s]]: below the 12 m/s limit of C3. The canopy has to be about one third of that area.",
    ], sz=11.5, spc=300)


def L47_sel_paracaidas(sl):
    d = {k["clave"]: k for k in PAR["disenos"]}
    tabla(sl, X0, Y0, W_UTIL, [3.0, 0.9, 2.5, 2.5, 2.5],
          ["Criterion", "Weight", "Flat circular", "Cross (selected)", "Hemispherical"], [
              ["Descent rate inside 15 ± 3 m/s with Cd0 ± 10 %", "High", "Yes", "Yes", "Yes"],
              ["Oscillation (stable zenith/nadir video, C6/C7)", "High", "±10 to 40°: poor", "0 to ±3°: best", "±10 to 15°"],
              ["Fabrication by the team", "Medium", "6 gores + spill hole", "Two strips of flat cloth", "Shaped gores: hardest"],
              ["Packing volume above the cap", "Medium", f"{d['plano']['S0_cm2']:.0f} cm²", f"{d['cruz']['S0_cm2']:.0f} cm²", f"{d['hemi']['S0_cm2']:.0f} cm²"],
              ["Known drawback", "Low", "Coning, swinging", "Tends to spin: swivel needed", "Higher cost of making"],
          ], sz=11, alto=I(0.42), alto_cab=I(0.36), col_sel=3)
    y = Y0 + I(0.36) + 5 * I(0.42) + I(0.2)
    w2 = (W_UTIL - GAP) // 2
    tarjeta(sl, X0, y, w2, Y1 - y, "Selected: cross parachute", [
        "Lowest oscillation of the three: the container hangs steady and the cameras record a usable video of both stages.",
        "Simplest to make: two strips of ripstop sewn in a cross, no shaped gores.",
        "Spinning is handled by the swivel in the bridle.",
    ], sz=12, spc=300)
    tarjeta(sl, X0 + w2 + GAP, y, w2, Y1 - y, "Parachute data", [
        f"S0 = {d['cruz']['S0_cm2']:.0f} cm²: arms {d['cruz']['geo']['brazo_mm']:.0f} mm wide, {d['cruz']['geo']['envergadura_mm']:.0f} mm across.",
        f"Mass allocation 15 g (fabric ≈ {d['cruz']['m_tela_g']:.0f} g + lines); bridle and swivel 5 g.",
        "Cd0 to be measured in a drop test before CDR; area trimmed to hit 15 m/s.",
    ], sz=12, spc=300)


def L48_estrategias(sl):
    wi, hf = I(8.0), I(3.2)
    panel(sl, X0, Y0, wi, hf, [("planeo_en.png", 1)])
    nd = PL["nominal"]["cuerpo romo (disco de nariz plano)"]
    R_esp = nd["delta"]["V"] ** 2 / (G0 * math.tan(math.radians(20)))
    y = Y0 + hf + I(0.15)
    tarjeta(sl, X0, y, wi, Y1 - y, "Steering strategy (both designs)", [
        "One tail servo deflects both V-tail surfaces as a rudder; the FSW holds a 20° bank, so the glider "
        f"spirals with a radius of ≈ {R_esp:.0f} m and stays over the field. Servo centred: straight glide.",
        "Left plot: speed polar at 500 g. Right: descent rate of 20 000 Monte Carlo cases (model and trim uncertainties).",
    ], sz=11.5, spc=250)
    x = X0 + wi + GAP
    tabla(sl, x, Y0, X1 - x, [1.25, 1.5, 1.5], ["", "A · Delta membrane wing", "B · Straight-wing glider"], [
        ["Wing", "45° sweep, AR 4, folds flat", "Rigid panels, AR 5.5, hinged"],
        ["Trim point", "α ≈ 20°, CL 1.20", "CL 0.80"],
        ["L/D", n(nd["delta"]["LD"]), n(nd["recta"]["LD"])],
        ["w at 500 g", f"{n(nd['delta']['w'])} m/s", f"{n(nd['recta']['w'])} m/s"],
        ["w, 5–95 %", f"{n(PL['mc']['delta']['p'][0])}–{n(PL['mc']['delta']['p'][2])} m/s",
         f"{n(PL['mc']['recta']['p'][0])}–{n(PL['mc']['recta']['p'][2])} m/s"],
        ["w at 373 g", f"{n(MAS['w_planeador_solo'])} m/s", "—"],
        ["Steering", "V-tail, 1 servo", "V-tail, 1 servo"],
    ], sz=10.5, sz_cab=10.5, alto=I(0.52), alto_cab=I(0.55), alin=["l", "c", "c"], ml=60000)


def L49_sel_estrategia(sl):
    sd, sr = PL["sens"]["delta"], PL["sens"]["recta"]
    tabla(sl, X0, Y0, W_UTIL, [3.2, 0.9, 3.4, 3.4], ["Criterion", "Weight", "A · Delta membrane wing (selected)", "B · Straight-wing glider"], [
        ["Inside 5 ± 3 m/s (Monte Carlo)", "High", f"{100 * PL['mc']['delta']['dentro']:.1f} % of cases",
         f"{100 * PL['mc']['recta']['dentro']:.1f} % of cases"],
        ["Sensitivity of w to trim", "High", f"Low: rank correlation with α {sd['ángulo de ataque']:.2f}".replace("-", "−"),
         f"High: rank correlation with trim CL {sr['CL de trim']:.2f}".replace("-", "−")],
        ["Stowage in the Ø86 bore", "High", "Folds flat in 14 mm side bays", "Rigid panels need hinges and more volume"],
        ["Deployment", "High", "Passive (springs, wall)", "Panels must unfold and lock"],
        ["Wing mass", "Medium", f"{MAS['sub']['Ala de membrana']['masa']:.0f} g (CAD)", "Not designed (heavier rigid panels)"],
        ["Prediction maturity", "Medium", "Polhamus used beyond AR 2 (tested range)", "Classical, well known"],
    ], sz=11, alto=I(0.36), alto_cab=I(0.36), col_sel=2)
    y = Y0 + I(0.36) + 6 * I(0.36) + I(0.2)
    w2 = (W_UTIL - GAP) // 2
    tarjeta(sl, X0, y, w2, Y1 - y, "Selected: A · delta membrane wing", [
        "Every Monte Carlo case falls inside 5 ± 3 m/s; the descent rate hardly depends on the trim angle.",
        "It is the only wing that folds flat around the box and opens without an actuator.",
    ], sz=12, spc=300)
    sm = AE["est"]["SM"]
    tarjeta(sl, X0 + w2 + GAP, y, w2, Y1 - y, "Open item: pitch stability", [
        f"Neutral point {AE['est']['np'][0]:.0f}–{AE['est']['np'][1]:.0f} mm from the nose; CG {MAS['x_cg_planeador_vuelo']:.0f} mm "
        f"(glider alone) to {AE['est']['x_cg']:.0f} mm (complete CanSat). With the 80 cm² V-tail at 217 mm the static margin is "
        f"[[{ROJO}:≤ 0 (down to −{abs(100 * sm[0]):.0f} %)]].",
        f"Fix before CDR: a larger tail (≈ 120–200 cm² at 300 mm) or the CG forward to ≈ {AE['est']['cg_req']:.0f} mm "
        "(nose ballast, battery forward).",
    ], sz=12, spc=300)


def L50_mecanico(sl):
    wi = I(4.3)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("lam_lanzamiento.png", 1)])
    x = X0 + wi + GAP
    sb = lambda *k: sum(f["masa"] for f in FILAS if any(s in f["item"] for s in k))
    tabla(sl, x, Y0, X1 - x, [1.25, 2.6, 1.9, 0.85], ["Assembly", "Parts", "Material", "Mass [g]"], [
        ["Container", (f"Tube Ø90 × {P.CT_LEN:g}, {P.CT_T_INF:g} / {P.CT_T:g} mm wall" if HIBRIDO else
                       f"Tube Ø90 × {P.CT_LEN:g}, {P.CT_T:g} mm wall"),
         "Carbon (lower) / glass-epoxy" if HIBRIDO else ("Glass-epoxy laminate" if P.CT_MAT == "GFRP" else "LW-ASA, printed"),
         n(fila("Tubo")["masa"])],
        ["", "Ribbed cap (bridle + key seat)", "PA12-CF, printed", n(fila("Tapa nervada")["masa"])],
        ["", "Cross parachute + 3-point bridle", "Ripstop, Kevlar", n(sb("Paracaidas", "Brida"))],
        ["Payload frame", "Bulkheads C1–C4", "PA12-CF, printed", n(sb("Cuaderna"))],
        ["", "4 corner angles 6 × 6 × 1", "CFRP, pultruded", n(fila("Largueros")["masa"])],
        ["", "Side panels, top cover, tray", "G10 0.5 / 0.8 mm", n(sb("G10"))],
        ["Wing", "Rods, struts, fittings, membrane", "CFRP, Al 7075, ripstop", n(MAS["sub"]["Ala de membrana"]["masa"])],
        ["Tail", "Boom, V-tail, servo", "Per tail design note", n(MAS["sub"]["Cola (nota de cola)"]["masa"])],
        ["Release", "Bayonet key + release servo", "Stainless A2-70", n(sb("Llave de bayoneta", "Servo del cerrojo"))],
    ], sz=10.5, sz_cab=11, alto=I(0.305), alto_cab=I(0.34), alin=["l", "l", "l", "r"], ml=80000)
    y = Y0 + I(0.34) + 9 * I(0.305) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, None, [
        f"**Total 500 g:** container {m_cont:.0f} g + payload {m_plan:.0f} g (including {lastre:.0f} g of trim ballast).",
        "**Load path:** cap → bayonet key → C4 → corner angles and panels; laterally, the C1 pads and the C4 collar "
        "centre the glider; the laminated tube carries the CanSat to the rocket support.",
        "**One actuator** releases the glider; the wing opens by itself.",
    ], sz=11.5, spc=300)


def L51_estructura(sl):
    wi = I(4.6)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("bastidor_explotado.png", 1)],
          "Frame C exploded: PA12-CF bulkheads C1–C4 (grey), CFRP corner angles (black), G10 panels, cover and tray (green).")
    x = X0 + wi + GAP
    tabla(sl, x, Y0, X1 - x, [1.15, 1.9, 1.9, 2.1], ["", "A · Printed monocoque", "B · Threaded rods + discs", "C · CFRP frame + G10 (selected)"], [
        ["Concept", "Ø84 PETG tube, 2 mm, bonded bulkheads", "4 steel M3 rods, 5 printed discs", "4 CFRP corner angles, 4 PA12-CF bulkheads, G10 panels"],
        ["Mass", "≈ 135 g", "≈ 140 g", f"{MAS['sub']['Estructura del planeador']['masa']:.0f} g (CAD)"],
        ["Wing exit", "Tube must be slotted", "Free", "Free: side bays open"],
        ["Stiffness", "Good closed, poor slotted", "Low in bending and torsion", "High: closed panel box"],
        ["Access", "Poor", "Good", "Good: screwed cover"],
        ["RF", "Transparent", "Transparent", "G10 transparent; carbon on edges"],
        ["Making", "One long print", "Very simple", "Cut plates + prints + bonding"],
    ], sz=10, sz_cab=10.5, alto=I(0.42), alto_cab=I(0.46), col_sel=3, alin=["l", "l", "l", "l"], ml=70000)
    y = Y0 + I(0.46) + 7 * I(0.42) + I(0.15)
    nota(sl, x, y, X1 - x, Y1 - y,
         "C is chosen because the wing needs the side bays open, and a box of thin panels with spars on the edges is the stiffest "
         "way to close the rest. The mass is similar to A and B; stiffness and access are better.", sz=11)


def L52_electrica(sl):
    hf = I(1.75)
    panel(sl, X0, Y0, I(6.2), hf, [("equipos_lateral.png", 1)], None)
    tarjeta(sl, X0 + I(6.2) + GAP, Y0, W_UTIL - I(6.2) - GAP, hf, "One removable tray", [
        "All electronics hang from the G10 tray, which slides out of the frame with the top cover removed (S8).",
    ], sz=12, spc=300)
    y = Y0 + hf + I(0.17)
    F = lambda m: f"{m / 1000 * 30 * G0 * 1.8:.0f} N"
    tabla(sl, X0, y, W_UTIL, [1.7, 4.0, 0.8, 1.3, 3.1], ["Component", "Location and mounting", "Mass", "30 G × 1.8", "Fastening (S8)"], [
        ["Main PCB", "Centre bay, under the tray; four 8 mm M2.5 spacers", "25 g", F(25), "4 × M2.5 with toothed washers"],
        ["Radio / GNSS PCB", "Tail bay, above the tray; antenna under the G10 cover", "20 g", F(20), "4 × M2.5"],
        ["18650 cell", "Centre bay, two printed cradles + strap; tabs soldered", "46 g", F(46), "20 mm strap, end stops in x"],
        ["Servos (tail, release)", "Nose bay and C4, screwed by their lugs", "9 g each", F(9), "2 × M2 each"],
        ["Cameras", "Zenith on the top cover; nadir under the tray (window)", "8 g each", F(8), "2 × M2 + adhesive"],
        ["Connectors", "Locking JST; harness tied to the tray every 40 mm", "—", "—", "Cable ties, adhesive on plugs"],
    ], sz=10.5, sz_cab=11, alto=I(0.33), alto_cab=I(0.34), alin=["l", "l", "c", "c", "l"], ml=80000)


def L53_mecanismos(sl):
    wi = I(4.55)
    hf = I(2.75)
    panel(sl, X0, Y0, wi, hf, [("cerrojo_anot_en.png", 1)])
    x = X0 + wi + GAP
    panel(sl, x, Y0, X1 - x, hf, [("lam_ala.png", 1)])
    y = Y0 + hf + I(0.15)
    F_ret = m_plan / 1000 * P.N_SHOCK * G0 * 1.8
    T_fric = m_plan / 1000 * G0 * 0.3 * 5.0
    tarjeta(sl, X0, y, wi, Y1 - y, "Payload release (at C4 and the cap)", [
        "Ø5 T-key with a Ø3 pin passes the keyhole of the cap; the servo turns it 90°.",
        f"Holds {F_ret:.0f} N (30 G × 1.8); the servo only sees friction ({n(T_fric)} vs 180 N·mm).",
        "Geometric lock (M2), no heat (M1), re-armed in seconds.",
    ], sz=11, spc=200)
    w2 = (X1 - x - GAP) // 2
    tarjeta(sl, x, y, w2, Y1 - y, "Wing deployment", [
        "Four-bar A–J–T–B with AJ = JT and BT = AB: folds flat into the 14 mm side bay.",
        "Torsion spring at B opens it; the Al sleeve slides over J and locks it.",
    ], sz=11, spc=200)
    tarjeta(sl, x + w2 + GAP, y, X1 - x - w2 - GAP, Y1 - y, "Parachute attachment", [
        "3-point Kevlar bridle on the cap ribs + swivel.",
        "Snatch load goes cap → key, not through the tube.",
    ], sz=11, spc=200)


def L54_seleccion_mec(sl):
    tabla(sl, X0, Y0, W_UTIL, [2.0, 3.6, 2.6, 4.3], ["Item", "Options compared", "Selected", "Main reasons"], [
        ["Payload structure", "Printed monocoque; threaded rods + discs; CFRP frame + G10", "CFRP frame + G10 panels",
         "Side bays open for the wing; stiff closed box; access; RF-transparent"],
        ["Payload release", "Bayonet key + servo; nylon line + nichrome; pin + linear servo", "Bayonet key + servo",
         "Geometric lock (M2), no heat (M1), servo sees friction only, re-armable"],
        ["Wing stowage", "One-piece rod; joint at 190 mm; hinge at mid-length", "Hinge at mid-length",
         "Folds flat in a 14 mm bay; single degree of freedom"],
        ["Container tube", "Printed LW-ASA 2 mm; glass-epoxy 0.6 mm; carbon (lower) + glass (upper)",
         f"Carbon {P.CT_T_INF:g} mm + glass {P.CT_T:g} mm" if HIBRIDO else f"Glass-epoxy, {P.CT_T:g} mm",
         "Lateral mode standing on the sander: 117 / 228 / 310 Hz; only the hybrid clears 233 Hz"],
        ["Bulkheads, cap", "PLA+; PETG; PA12-CF", "PA12-CF, 100 % infill", "Best stiffness and strength per gram; 150 °C"],
        ["Joints", "Screws; epoxy; both", "Epoxy + M2/M2.5 with inserts", "S8; screwed parts can be removed"],
    ], sz=10.5, sz_cab=11, alto=I(0.5), alto_cab=I(0.36), alin=["l"] * 4, ml=80000)
    y = Y0 + I(0.36) + 6 * I(0.5) + I(0.17)
    tarjeta(sl, X0, y, W_UTIL, Y1 - y, None, [
        "**Why a hybrid laminated tube:** standing on the sander, the printed 2 mm tube had a 117 Hz lateral mode (MS −0.66). "
        "All-glass 0.6 mm reached 228 Hz, inside the 200–233 Hz sander band. Carbon in the lower 132 mm, where the bending moment "
        "is largest, takes it to 310 Hz; the upper part stays glass so the radio and GNSS see out. S6's 2 mm applies to "
        "printed walls; the epoxy is post-cured above 60 °C.",
    ], sz=11.5, spc=200)


# ---------------------------------------------------------------- verificacion estructural
GRUPOS = [("Contenedor: tubo", f"Container tube ({TUBO_EN})"), ("Contenedor: tapa", "Container cap (PA12-CF)"),
          ("Cuadernas", "Bulkheads, cradles, guides (PA12-CF)"), ("Rieles de bandeja", "Tray rails (PA12-CF)"),
          ("Paneles y bandeja", "Panels and tray (G10)"), ("Largueros", "Corner angles (CFRP)"),
          ("Arandela de C4", "Key washer on C4 (Al 7075)"), ("Llave de bayoneta", "Bayonet key (A2-70)")]
EJES = ("x", "y", "z")


def peor(caso, g, RR=None):
    best = None
    blk = (R if RR is None else RR).get(caso)
    if blk is None:
        return None
    ejes = [None] if "margenes" in blk else list(EJES)
    for e in ejes:
        d = blk["margenes"] if e is None else blk[e]["margenes"]
        for k, v in d.items():
            gg = k.split("|")[0].strip()
            if gg.startswith(g) and (best is None or v["MS"] < best[0]):
                best = (v["MS"], v["sigma"], e or "x", k.split("|")[1].strip())
    return best


def celda(caso, g, RR=None):
    p = peor(caso, g, RR)
    if p is None:
        return "—"
    s = ms(p[0])
    return f"[[{ROJO}:{s}]]" if p[0] < 0 else s


def modos(RR):
    """(f_lateral, f_axial) por masa efectiva: primer modo con mas del 30 % de la masa en y o z, y en x."""
    f, mf = RR["freq"], RR["m_eff_frac"]
    inc = [[mf[k][e] - (mf[k - 1][e] if k else 0.0) for e in range(3)] for k in range(len(f))]
    lat = next((f[k] for k in range(len(f)) if max(inc[k][1], inc[k][2]) > 0.3), None)
    ax = next((f[k] for k in range(len(f)) if inc[k][0] > 0.3), None)
    return lat, ax


def L_fem1(sl):
    f, mf, zm = R["freq"], R["m_eff_frac"], R["zeta_modal"]
    wi = I(6.3)
    fig = "fea_modos_en.png" if os.path.exists(os.path.join(FIGS, "fea_modos_en.png")) else "fea_modos.png"
    panel(sl, X0, Y0, wi, Y1 - Y0, [(fig, 1)], "First four mode shapes of the complete CanSat (cantilever from the rocket support)")
    x = X0 + wi + GAP
    tabla(sl, x, Y0, X1 - x, [1.25, 3.05, 1.2], ["Case", "Load and support", "Requirement"], [
        ["CE-15", "Quasi-static 15 G, x, y, z", "S4"],
        ["Sander test", "Standing, fixed at the base: orbital sander up to 233 Hz, 29 G, start/stop", "Vibration test"],
        ["Flight 15 G", "Sine sweep 15 G, 5–1000 Hz; resting in the bay, wall guides the top", "S4"],
        ["CH-30", "Half-sine 30 G, 1–20 ms, x, y, z", "S5, drop test"],
        ["PA-30", "Parachute snatch 30 G × 1.8", "S5, C3"],
    ], sz=10.5, sz_cab=11, alto=I(0.44), alto_cab=I(0.34), alin=["l", "l", "l"], ml=80000)
    y = Y0 + I(0.34) + 5 * I(0.44) + I(0.17)
    fv = RV["freq"] if RV else None
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Finite element model (CalculiX)", [
        f"{R['elementos'] / 1000:.0f} k quadratic tetrahedra, {R['nodos'] / 1000:.0f} k nodes, {R['masa_g']:.0f} g.",
        f"Standing on the sander (fixed base): lateral mode {modos(R)[0]:.0f} Hz, above the 233 Hz of the sander; "
        f"axial mode (glider on the key isolator) {modos(R)[1]:.0f} Hz.",
        (f"Resting in the bay (top guided by the wall): lateral mode {modos(RV)[0]:.0f} Hz." if RV else ""),
        "Checked: modal vs. static stress field (< 1 %), mesh, hand calculations of joints.",
    ], sz=10.5, spc=200)


def mapas_png():
    """Fila superior de los mapas de resonancia y de choque + barra de color, en una sola figura."""
    out = os.path.join(TMP, "fea_mapas_lamina.png")
    a = Image.open(os.path.join(FIGS, "fea_arm_mapas_en.png")).convert("RGB")
    b = Image.open(os.path.join(FIGS, "fea_choque_mapas_en.png")).convert("RGB")
    w, h = a.size
    fa, fb = a.crop((0, 0, w, int(0.37 * h))), b.crop((0, 0, w, int(0.37 * h)))
    cb = a.crop((int(0.08 * w), int(0.885 * h), int(0.95 * w), h))
    lienzo = Image.new("RGB", (w, fa.height + fb.height + cb.height + 20), "white")
    lienzo.paste(fa, (0, 0)); lienzo.paste(fb, (0, fa.height + 10))
    lienzo.paste(cb, ((w - cb.width) // 2, fa.height + fb.height + 20))
    lienzo.save(out)
    return out


def L_fem_mapas(sl):
    wi = I(8.3)
    p = mapas_png()
    tarjeta(sl, X0, Y0, wi, Y1 - Y0, nombre="Figure panel")
    pic_w = wi - I(0.24)
    im = Image.open(p)
    esc = min(pic_w / im.width, (Y1 - Y0 - I(0.24)) / im.height)
    sl.shapes.add_picture(p, X0 + I(0.12) + (pic_w - int(im.width * esc)) // 2, Y0 + I(0.12), int(im.width * esc), int(im.height * esc))
    x = X0 + wi + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "How to read the maps", [
        "**Top row:** 15 G sine sweep, envelope over all resonances, one map per excitation axis.",
        "**Bottom row:** 30 G half-sine shock, envelope in time for the worst pulse duration.",
        "**Colour:** utilisation FS·σ / σ_allow of each material (log scale). Magenta = no margin.",
        f"Lateral sweep: the tube turns magenta (utilisation up to ≈ 5) at the {R['freq'][0]:.0f} Hz sway mode: the open item "
        "of the next slide.",
        "Axial sweep and shock: every part stays below 1 (positive margins).",
    ], sz=11, spc=300)


def casos_fem():
    c = [("cuasi15", "CE-15", R)]
    if "lijadora" in R:
        c.append(("lijadora", "Sander test", R))
    if RV is not None:
        c.append(("armonico", "Flight 15 G", RV))
    c += [("choque", "CH-30", R), ("paracaidas", "PA-30", R)]
    return c


def L_fem2(sl):
    casos = casos_fem()
    filas = [[nom] + [celda(c, g, RR) for c, _, RR in casos] for g, nom in GRUPOS]
    nc = len(casos)
    tabla(sl, X0, Y0, W_UTIL, [3.4] + [1.25] * nc, ["Part group (material)"] + [c for _, c, _ in casos], filas,
          sz=11, sz_cab=11.5, alto=I(0.33), alto_cab=I(0.36), alin=["l"] + ["c"] * nc)
    y = Y0 + I(0.36) + len(GRUPOS) * I(0.33) + I(0.17)
    todos = [(peor(c, g, RR)[0], g, nom) for g, _ in GRUPOS for c, nom, RR in casos if peor(c, g, RR)]
    neg = [t for t in todos if t[0] < 0]
    mn = min(todos)
    w2 = (W_UTIL - GAP) // 2
    tarjeta(sl, X0, y, w2, Y1 - y, "Criterion", [
        "MS = σallow / (FS · σ) − 1, worst of the three axes.",
        "FS 2.0 printed parts (interlayer strength when the load crosses the layers), 1.5 composites, 1.25 metals.",
        "Resonant cases depend on the damping assumed: to be measured in a sine test.",
    ], sz=11, spc=250)
    nombres = dict(GRUPOS)
    if not neg:
        res = [f"**All margins are positive.** Minimum {ms(mn[0])}: {nombres[mn[1]]}, {mn[2]}.",
               f"Rev. D: printed 2 mm tube (lateral mode 117 Hz) → hybrid laminate (carbon lower, glass upper) and "
               f"stiffer C1 pads; lateral mode standing on the sander now {modos(R)[0]:.0f} Hz."]
    else:
        res = [f"{len(neg)} negative: " + "; ".join(f"{nombres[g]} in {c} ({ms(m)})" for m, g, c in sorted(neg)[:3]) + "."]
    tarjeta(sl, X0 + w2 + GAP, y, w2, Y1 - y, "Result", res, sz=11, spc=250)


# ---------------------------------------------------------------- masa
def tabla_masa(sl, x, y, w, grupos, sz=10, alto=I(0.255)):
    filas, sub = [], []
    for titulo, fs in grupos:
        if len(fs) == 1:                     # renglon unico: va como subtotal, sin repetirlo
            f = fs[0]
            sub.append(len(filas))
            filas.append([titulo, str(f["cant"]), n(f["masa"]), "±" + n(f["inc"]), FUENTE.get(f["fuente"], f["fuente"])])
            continue
        for f in fs:
            filas.append(mfila(f))
        m, u = suma(fs)
        sub.append(len(filas))
        filas.append([titulo, "", n(m), "±" + n(u), ""])
    return tabla(sl, x, y, w, [3.9, 0.55, 0.9, 0.85, 1.2], ["Item", "Qty", "Mass [g]", "Unc. [g]", "Source"], filas,
                 sz=sz, sz_cab=10.5, alto=alto, alto_cab=I(0.3), alin=["l", "c", "r", "r", "l"], sub=sub, negrita_col0=False,
                 ml=70000, mt=20000), len(filas)


def comp(sub=None, keys=None):
    out = []
    for f in FILAS:
        if en(f)[1] != "C":
            continue
        if sub and f["sub"] not in sub:
            continue
        if keys and not any(k in f["item"] for k in keys):
            continue
        out.append(f)
    return out


def estr(sub):
    return [f for f in FILAS if en(f)[1] == "S" and f["sub"] in sub]


AVI = ["Bateria", "Sillas", "PCB principal", "PCB radio", "Camaras", "Baliza", "Celdas", "Separadores"]
MECA = ["Servo de cola", "Servo del cerrojo", "Llave de bayoneta", "Arandela de la llave", "Aislador", "Patines", "Manguito elastomerico"]
RECU = ["Paracaidas", "Brida"]


def L55_componentes(sl):
    w2 = (W_UTIL - GAP) // 2
    tabla_masa(sl, X0, Y0, w2, [("Avionics and power subtotal", comp(keys=AVI))], alto=I(0.3))
    tabla_masa(sl, X0 + w2 + GAP, Y0, w2, [("Actuators and mechanisms subtotal", comp(keys=MECA)),
                                           ("Recovery subtotal", comp(keys=RECU)),
                                           ("Trim ballast / mass margin", comp(keys=["Lastre"]))], alto=I(0.255))
    m, _ = suma(comp())
    nota(sl, X0, Y1 - I(0.62), w2, I(0.6),
         f"Components total: {m:.1f} g. Electronics masses are allocations pending the EPS and C&DH boards "
         "(see the margin slide for the current estimates).", sz=10.5)


def L56_estructura(sl):
    w2 = (W_UTIL - GAP) // 2
    tabla_masa(sl, X0, Y0, w2, [("Payload frame subtotal", estr(["Estructura del planeador"]))], alto=I(0.29))
    tabla_masa(sl, X0 + w2 + GAP, Y0, w2, [("Wing subtotal", estr(["Ala de membrana"])),
                                           ("Tail boom + V-tail + fittings", estr(["Cola (nota de cola)"])),
                                           ("Container subtotal", estr(["Contenedor"]))], alto=I(0.255))
    m, _ = suma(estr(["Estructura del planeador", "Ala de membrana", "Cola (nota de cola)", "Contenedor"]))
    nota(sl, X0, Y1 - I(0.4), w2, I(0.38), f"Structural elements total: {m:.1f} g. CAD masses: volume × density of the material.", sz=10.5)


CORTO = {"Tubo": "container tube", "PCB principal": "main PCB", "Botalon": "tail boom and V-tail",
         "PCB radio": "radio/GNSS PCB", "Camaras": "cameras", "Cuaderna de cola": "C4"}


def L57_incertidumbre(sl):
    orden = ["CAD", "Datasheet", "Wing note", "Estimate", "Allocation"]
    base = {"CAD": "Volume × density from the CAD model", "Datasheet": "Manufacturer datasheet",
            "Wing note": "Wing design note (membrane + seams)", "Estimate": "Engineering estimate (fasteners, wiring, hinges)",
            "Allocation": "Budget given to a part not yet designed"}
    unc = {"CAD": "±5 % (CFRP, G10, metal) to ±10 % (printed)", "Datasheet": "±0.5 to ±1 g", "Wing note": "±20 %",
           "Estimate": "±20 %", "Allocation": "±20 %"}
    filas = []
    for o in orden:
        fs = [f for f in FILAS if FUENTE.get(f["fuente"]) == o]
        m, u = suma(fs)
        filas.append([o, str(len(fs)), n(m), "±" + n(u), unc[o], base[o]])
    tabla(sl, X0, Y0, W_UTIL, [1.3, 0.7, 1.0, 0.95, 2.8, 4.0], ["Source", "Items", "Mass [g]", "RSS [g]", "Uncertainty assumed", "Basis"],
          filas, sz=10.5, sz_cab=11, alto=I(0.36), alto_cab=I(0.34), alin=["l", "c", "r", "r", "l", "l"], ml=80000)
    y = Y0 + I(0.34) + len(filas) * I(0.36) + I(0.2)
    w2 = (W_UTIL - GAP) // 2
    big = sorted(FILAS, key=lambda f: -f["inc"])[:4]
    tarjeta(sl, X0, y, w2, Y1 - y, "Combined uncertainty", [
        f"**Root sum square: ±{n(MAS['inc_rss'])} g.** Worst case (all errors the same sign): ±{n(MAS['inc_lin'])} g.",
        "Largest single contributors: " + ", ".join(f"{CORTO.get(next((k for k in CORTO if k in f['item']), ''), en(f)[0])} "
                                                    f"±{n(f['inc'])} g" for f in big) + ".",
    ], sz=11.5, spc=300)
    tarjeta(sl, X0 + w2 + GAP, y, w2, Y1 - y, "How it will shrink", [
        "Weigh printed coupons to fix the density of each printer and filament.",
        "Weigh every part as it is made; replace allocations with the EPS and C&DH board masses.",
        "Final trim with the nose ballast, which also sets the glider CG.",
    ], sz=11.5, spc=300)


def L58_total(sl):
    S = MAS["sub"]
    est = estr(["Estructura del planeador", "Ala de membrana", "Cola (nota de cola)", "Contenedor"])
    me, ue = suma(est)
    mc, uc = suma([f for f in comp() if "Lastre" not in f["item"]])
    w1 = I(7.2)
    tabla(sl, X0, Y0, w1, [3.2, 1.2, 1.1, 1.3], ["Subsystem", "Mass [g]", "RSS [g]", "CG x [mm]"], [
        ["Payload frame", n(S["Estructura del planeador"]["masa"]), "±" + n(S["Estructura del planeador"]["inc"]), f"{S['Estructura del planeador']['x']:.0f}"],
        ["Wing", n(S["Ala de membrana"]["masa"]), "±" + n(S["Ala de membrana"]["inc"]), f"{S['Ala de membrana']['x']:.0f}"],
        ["Tail (boom, V-tail, servo)", n(S["Cola (nota de cola)"]["masa"]), "±" + n(S["Cola (nota de cola)"]["inc"]), f"{S['Cola (nota de cola)']['x']:.0f}"],
        ["Avionics, mechanisms, ballast", n(S["Avionica y equipos"]["masa"]), "±" + n(S["Avionica y equipos"]["inc"]), f"{S['Avionica y equipos']['x']:.0f}"],
        ["Payload (glider)", n(m_plan), "", f"{MAS['x_cg_planeador_estibado']:.0f}"],
        ["Container (tube, cap, parachute)", n(S["Contenedor"]["masa"]), "±" + n(S["Contenedor"]["inc"]), f"{S['Contenedor']['x']:.0f}"],
        ["CanSat total", n(mtot), "±" + n(MAS["inc_rss"]), f"{MAS['x_cg_lanzamiento']:.0f}"],
    ], sz=11, sz_cab=11.5, alto=I(0.4), alto_cab=I(0.36), alin=["l", "r", "r", "r"], sub=(4, 6))
    x = X0 + w1 + GAP
    tabla(sl, x, Y0, X1 - x, [2.3, 1.2], ["By type", "Mass [g]"], [
        ["Structural elements", n(me)],
        ["Components", n(mc)],
        ["Trim ballast / margin", n(lastre)],
        ["Total", n(mtot)],
    ], sz=11.5, sz_cab=11.5, alto=I(0.4), alto_cab=I(0.36), alin=["l", "r"], sub=(3,))
    y = Y0 + I(0.36) + 4 * I(0.4) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, None, [
        f"**S1: 500 ± 10 g.** The design closes at {mtot:.0f} g with ±{n(MAS['inc_rss'])} g (RSS).",
        f"CG x (stowed) from the glider nose (face of C1), {abs(P.CT_X[0]):g} mm above the open end of the container.",
        f"Payload CG in flight (wing and tail deployed): {MAS['x_cg_planeador_vuelo']:.0f} mm; it has to move forward "
        "for pitch stability (page 52).",
        f"Container alone: {m_cont:.0f} g, descends at {n(next(d for d in PAR['disenos'] if d['clave'] == 'cruz')['v_contenedor'])} m/s.",
    ], sz=11.5, spc=300)


def L59_margen(sl):
    w1 = I(4.6)
    marg = 510 - (mtot - lastre)
    tarjeta(sl, X0, Y0, w1, Y1 - Y0, "Margin", [
        f"Requirement S1: 500 ± 10 g.",
        f"Designed mass without ballast: **{mtot - lastre:.1f} g**.",
        f"**Margin to 500 g: {lastre:.1f} g**, carried as nose ballast.",
        f"Room to the 510 g limit: {marg:.1f} g, against ±{n(MAS['inc_rss'])} g (RSS) of uncertainty.",
        ("**If the mass grows:** lighten the ballast first; then thinner cap ribs and lighter brackets.", 1),
        ("**If it falls short:** add nose ballast; it also moves the CG forward, which the glider needs.", 1),
    ], sz=12, spc=350)
    x = X0 + w1 + GAP
    resto = sum(f["masa"] for f in comp(keys=["PCB principal", "PCB radio", "Camaras", "Baliza", "Celdas", "Separadores"]))
    INT = [("Battery", "1 × 18650: 46 g", "2S1P pack: 94 g", 94 - 46, "1S cell + boost converter on the EPS board"),
           ("Servos", "2 × 9 g: 18 g", "3 × SG90: 36 g", 36 - 18, "Two servos (release, tail): the wing opens passively"),
           ("Parachute", "15 g", "45 cm flat: 85 g", 85 - 15, f"Cross canopy sized for 15 m/s (45 cm gives {n(PAR['plano_45cm']['v'])} m/s)"),
           ("Rest of the electronics", f"{resto:.0f} g", f"≈ {177.7 - 94:.0f} g", 177.7 - 94 - resto, "Keep the allocations")]
    filas = [[a, b, c, (f"[[{ROJO}:+{d:.0f}]]" if d > 0.5 else f"{d:+.0f}".replace("-", "−")), e] for a, b, c, d, e in INT]
    delta = sum(t[3] for t in INT)
    tabla(sl, x, Y0, X1 - x, [1.3, 1.7, 1.7, 0.6, 2.6], ["Item", "Mechanical budget", "Team EPS/C&DH docs", "Δ [g]", "Correction"],
          filas, sz=10, sz_cab=10.5, alto=I(0.5), alto_cab=I(0.48), alin=["l", "l", "l", "r", "l"], ml=70000)
    y = Y0 + I(0.48) + 4 * I(0.5) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Integration risk", [
        f"With the current EPS/C&DH estimates the CanSat would weigh ≈ {mtot - lastre + delta:.0f} g: "
        f"[[{ROJO}:about {mtot - lastre + delta - 510:.0f} g over the 510 g limit]].",
        "The three corrections in the table bring it back to the budget; they must be agreed with EPS before CDR.",
    ], sz=11.5, spc=300)


# ============================================================ main
def main(entrada, salida):
    prs = Presentation(entrada)
    sl = prs.slides
    # comprobacion: numeracion y titulos esperados
    esperado = {20: "Configuration A", 21: "Configuration B", 22: "Selection and rationale", 23: "Dimensions",
                24: "Placement of Major", 25: "Launch Configuration", 26: "Deployed Configuration",
                48: "Descent Control Subsystem Overview", 49: "parachute design", 50: "Selection", 51: "Para-glider steering",
                52: "Selection", 53: "Mechanical Subsystem Overview", 54: "Structure of payload", 55: "electrical components",
                56: "mechanisms", 57: "Selection", 58: "Mass of all components", 59: "structural elements",
                60: "Sources or uncertainties", 61: "Total Mass", 62: "Margin"}
    for k, t in esperado.items():
        st = subtitulo(sl[k - 1])
        assert st is not None and t.lower() in st.text_frame.text.lower(), (k, st.text_frame.text if st else None)
    for i, s in enumerate(sl, 1):
        b = badge(s)
        if b is not None and b.text_frame.text.strip().isdigit():
            assert int(b.text_frame.text) == i - 3, (i, b.text_frame.text)
    trabajo = {20: L17_configA, 21: L18_configB, 22: L19_seleccion, 23: L20_dimensiones, 24: L21_componentes,
               25: L22_lanzamiento, 26: L23_desplegado, 48: L45_descenso, 49: L46_paracaidas, 50: L47_sel_paracaidas,
               51: L48_estrategias, 52: L49_sel_estrategia, 53: L50_mecanico, 54: L51_estructura, 55: L52_electrica,
               56: L53_mecanismos, 57: L54_seleccion_mec, 58: L55_componentes, 59: L56_estructura, 60: L57_incertidumbre,
               61: L58_total, 62: L59_margen}
    slides = {k: sl[k - 1] for k in trabajo}
    for k, fn in trabajo.items():
        limpiar(slides[k])
        fn(slides[k])
    # dos laminas de verificacion estructural despues de la 57
    nuevas = []
    for pos, (fn, sub) in enumerate([(L_fem1, "Structural Verification (1/3): FE Model, Modes and Load Cases"),
                                     (L_fem_mapas, "Structural Verification (2/3): Stress Maps"),
                                     (L_fem2, "Structural Verification (3/3): Margins of Safety")]):
        s = duplicar(prs, 56, 57 + pos)
        limpiar(s)
        poner_texto_run(subtitulo(s), sub)
        sec = seccion(s)
        rs = sec.text_frame.paragraphs[0].runs
        rs[-1].text = " - Structural Verification"
        fn(s)
        nuevas.append(s)
    # renumeracion de los circulos y del indice
    for i, s in enumerate(prs.slides, 1):
        b = badge(s)
        if b is not None and b.text_frame.text.strip().isdigit():
            poner_texto_run(b, str(i - 3))
    ind = prs.slides[3]
    for sh in ind.shapes:
        if sh.has_table:
            for r in list(sh.table.rows)[1:]:
                c = r.cells[0]
                t = c.text_frame.text.strip()
                if t.isdigit() and int(t) > 54:
                    c.text_frame.paragraphs[0].runs[0].text = str(int(t) + len(nuevas))
    import formato_cansat
    formato_cansat.aplicar(prs)
    prs.save(salida)
    print("ok:", salida, len(prs.slides), "laminas (formato CanSat clasico)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
