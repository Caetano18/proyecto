"""Formato clasico de PDR CanSat (como los PDR de referencia de los equipos 1043 y 1093) para toda la presentacion.

Fondo blanco, logo del equipo a la izquierda y de la competencia a la derecha, un solo titulo azul en negrita
sobre un filete azul, pie con presentador / equipo / numero de pagina, letra Arial, tablas con encabezado azul
y la opcion seleccionada en rojo.  Se aplica sobre las 108 laminas (las del equipo y las del subsistema mecanico).
"""
import io
import numpy as np
from lxml import etree
from PIL import Image, ImageDraw
from pptx.oxml.ns import qn
from pptx.util import Pt
from pptx.dml.color import RGBColor

AZUL = "1F4E79"        # encabezados de tabla, titulos
AZUL_T = "1F3864"      # texto
CELESTE = "DCE6F2"     # primera columna de tablas
ROJO_SEL = "C00000"    # opcion seleccionada
ROSA_SEL = "FBE9E9"
BORDE = "8EA9DB"
EQUIPO = "CanSat Argentina 2026 PDR: Team Hermes (UTN FRH)"
EMU_IN = 914400
DY = int(0.55 * EMU_IN)          # el contenido sube: el subtitulo pasa al encabezado
W, H = 1920, 1080

TEXTO = {"242C4F": AZUL_T, "138A8A": AZUL, "5B6478": "595959", "6B7280": "595959", "5A6280": "595959"}
RELLENO = {"242C4F": AZUL, "138A8A": "2E75B6", "F1F4F9": CELESTE, "E2F1F1": ROSA_SEL, "BFE6E6": CELESTE,
           "D5DAE5": BORDE}
LINEA = {"D5DAE5": BORDE, "138A8A": AZUL, "242C4F": AZUL}
CTX_TEXTO = {qn("a:rPr"), qn("a:endParaRPr"), qn("a:defRPr")}
CTX_LINEA = {qn("a:ln"), qn("a:lnL"), qn("a:lnR"), qn("a:lnT"), qn("a:lnB")}


NEUTRO = False


def neutro():
    """Variante neutra: blanco y grises, sin colores; tarjetas redondeadas sin borde (menos 'cuadrado')."""
    global AZUL, AZUL_T, CELESTE, ROJO_SEL, ROSA_SEL, BORDE, TEXTO, RELLENO, LINEA, NEUTRO
    NEUTRO = True
    AZUL, AZUL_T, CELESTE, ROJO_SEL, ROSA_SEL, BORDE = "262626", "262626", "F4F4F4", "262626", "EBEBEB", "D0D0D0"
    TEXTO = {"242C4F": "262626", "138A8A": "262626", "5B6478": "595959", "6B7280": "595959", "5A6280": "595959",
             "B23A2E": "262626", "1F4E79": "262626", "C00000": "262626"}
    RELLENO = {"242C4F": "404040", "138A8A": "595959", "F1F4F9": "F4F4F4", "E2F1F1": "EBEBEB", "BFE6E6": "F4F4F4",
               "D5DAE5": "D0D0D0", "C00000": "1F1F1F", "FBE9E9": "EBEBEB", "2E75B6": "595959", "1F4E79": "404040"}
    LINEA = {"D5DAE5": "D0D0D0", "138A8A": "8C8C8C", "242C4F": "8C8C8C", "1F4E79": "8C8C8C"}


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- fondos
def _png(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def _logo_ca_chico(orig):
    o = np.asarray(orig.convert("RGB"), int)
    caja = o[20:260, 1690:1920]
    nb = np.where((caja < 235).any(axis=2))
    y0, y1, x0, x1 = nb[0].min() + 20, nb[0].max() + 21, nb[1].min() + 1690, nb[1].max() + 1691
    return orig.convert("RGB").crop((x0, y0, x1, y1)), (x0, y0)


def fondo_laminas(orig):
    im = Image.new("RGB", (W, H), (255, 255, 255))
    logo, pos = _logo_ca_chico(orig)
    im.paste(logo, pos)
    d = ImageDraw.Draw(im)
    y = int(1.62 / 7.5 * H)
    d.rectangle([36, y, W - 36, y + 3], fill=_rgb(AZUL))
    return im


def _pegar(im, logo, cx, cy, lado):
    lg = logo.copy()
    lg.thumbnail((lado, lado), Image.LANCZOS)
    base = im.convert("RGBA")
    base.alpha_composite(lg, (int(cx - lg.width / 2), int(cy - lg.height / 2)))
    return base.convert("RGB")


def _blanco_a_color(png, fondo, color):
    a = np.asarray(png.convert("RGB"), float)
    l = (a - np.array(fondo, float)).clip(0).mean(axis=2) / (255 - np.mean(fondo))
    rgba = np.zeros(a.shape[:2] + (4,), np.uint8)
    rgba[..., :3] = color
    rgba[..., 3] = (l.clip(0, 1) * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def fondo_titulo(orig, logo_ca):
    im = Image.new("RGB", (W, H), (255, 255, 255))
    im = _pegar(im, logo_ca, W / 2, 190, 300)
    o = orig.convert("RGB")
    viejo = tuple(int(v) for v in np.median(np.asarray(o.crop((40, 1000, 300, 1070))).reshape(-1, 3), axis=0))
    pie = _blanco_a_color(o.crop((0, 940, W, 1080)), viejo, _rgb(AZUL))
    base = im.convert("RGBA")
    base.alpha_composite(pie, (0, 940))
    d = ImageDraw.Draw(base)
    d.rectangle([36, 370, W - 36, 373], fill=_rgb(AZUL) + (255,))
    return base.convert("RGB")


def fondo_blanco(logo_ca=None, pos=None, lado=0):
    im = Image.new("RGB", (W, H), (255, 255, 255))
    if logo_ca is not None:
        im = _pegar(im, logo_ca, pos[0], pos[1], lado)
    return im


# ---------------------------------------------------------------- texto y formas
def _texto_run(sh):
    return [r for p in sh.text_frame.paragraphs for r in p.runs]


def _set_font(el):
    for tag in ("a:latin", "a:ea", "a:cs"):
        for f in el.iter(qn(tag)):
            if f.get("typeface") in ("Montserrat", "Montserrat SemiBold", "Montserrat Medium"):
                f.set("typeface", "Arial")


def recolorear(el, blanco_a_azul=False):
    for c in el.iter(qn("a:srgbClr")):
        v = c.get("val", "").upper()
        tabla = RELLENO
        p = c.getparent()
        while p is not None:
            if p.tag in CTX_TEXTO:
                tabla = TEXTO
                break
            if p.tag in CTX_LINEA:
                tabla = LINEA
                break
            if p.tag in (qn("p:sp"), qn("a:tc"), qn("p:cxnSp")):
                break
            p = p.getparent()
        if blanco_a_azul and tabla is TEXTO and v == "FFFFFF":
            c.set("val", AZUL)
        elif v in tabla:
            c.set("val", tabla[v])
    if blanco_a_azul:
        for rpr in el.iter(qn("a:rPr")):
            for sc in rpr.iter(qn("a:schemeClr")):
                if sc.get("val") in ("bg1", "lt1"):
                    sf = sc.getparent()
                    sf.remove(sc)
                    etree.SubElement(sf, qn("a:srgbClr")).set("val", AZUL)


def tarjetas_a_recuadros(el):
    """Tarjetas redondeadas grises -> recuadros blancos con filete azul (como los PDR de referencia).
    En la variante neutra quedan redondeadas, en gris muy claro y sin borde."""
    if NEUTRO:
        for sp in el.iter(qn("p:sp")):
            sppr = sp.find(qn("p:spPr"))
            if sppr is None:
                continue
            geo, sf = sppr.find(qn("a:prstGeom")), sppr.find(qn("a:solidFill"))
            if geo is None or geo.get("prst") != "roundRect" or sf is None:
                continue
            c = sf.find(qn("a:srgbClr"))
            if c is None or c.get("val", "").upper() not in ("F1F4F9", "F4F4F4"):
                continue
            c.set("val", "F4F4F4")
            ln = sppr.find(qn("a:ln"))
            if ln is not None:
                sppr.remove(ln)
            etree.SubElement(sppr, qn("a:ln")).append(etree.Element(qn("a:noFill")))
        return
    for sp in el.iter(qn("p:sp")):
        sppr = sp.find(qn("p:spPr"))
        if sppr is None:
            continue
        geo = sppr.find(qn("a:prstGeom"))
        sf = sppr.find(qn("a:solidFill"))
        if geo is None or geo.get("prst") != "roundRect" or sf is None:
            continue
        c = sf.find(qn("a:srgbClr"))
        if c is None or c.get("val", "").upper() not in ("F1F4F9", CELESTE):
            continue
        geo.set("prst", "rect")
        av = geo.find(qn("a:avLst"))
        if av is not None:
            for ch in list(av):
                av.remove(ch)
        c.set("val", "FFFFFF")
        ln = sppr.find(qn("a:ln"))
        if ln is not None:
            sppr.remove(ln)
        ln = etree.Element(qn("a:ln"), w="12700")
        etree.SubElement(etree.SubElement(ln, qn("a:solidFill")), qn("a:srgbClr")).set("val", AZUL)
        idx = list(sppr).index(sf) + 1
        sppr.insert(idx, ln)


def _caja(slide, x, y, w, h, textos, sz, color, algn, bold=False):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    bp = tf._txBody.find(qn("a:bodyPr"))
    for k in ("lIns", "tIns", "rIns", "bIns"):
        bp.set(k, "0")
    bp.set("anchor", "ctr")
    p = tf.paragraphs[0]
    p.alignment = {"l": 1, "c": 2, "r": 3}[algn]
    r = p.add_run()
    r.text = textos
    r.font.size = Pt(sz)
    r.font.bold = bold
    r.font.name = "Arial"
    r.font.color.rgb = RGBColor.from_string(color)
    return tb


def encabezado(slide, k):
    """Seccion (chica, arriba) + titulo de la lamina (grande, azul, negrita); sin circulo numerado."""
    sec = sub = badge = None
    for sh in slide.shapes:
        if sh.has_text_frame and sh.left == 1560000 and sh.top == 150000:
            sec = sh
        elif sh.has_text_frame and sh.left == 1050000 and sh.top == 1500000:
            sub = sh
        elif sh.shape_type == 1 and sh.left == 368560 and sh.top == 1500000:
            badge = sh
    if badge is not None:
        badge._element.getparent().remove(badge._element)
    if sec is not None:
        sec.left, sec.top, sec.width, sec.height = int(1.55 * EMU_IN), int(0.18 * EMU_IN), int(9.9 * EMU_IN), int(0.34 * EMU_IN)
        for r in _texto_run(sec):
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor.from_string("595959")
    if sub is not None:
        sub.left, sub.top, sub.width, sub.height = int(1.55 * EMU_IN), int(0.52 * EMU_IN), int(9.9 * EMU_IN), int(1.0 * EMU_IN)
        bp = sub.text_frame._txBody.find(qn("a:bodyPr"))
        bp.set("anchor", "ctr")
        for r in _texto_run(sub):
            r.font.size = Pt(24)
            r.font.bold = True
            r.font.color.rgb = RGBColor.from_string(AZUL)
    elif sec is not None:      # laminas sin subtitulo: la seccion es el titulo
        sec.top, sec.height = int(0.45 * EMU_IN), int(0.9 * EMU_IN)
        for r in _texto_run(sec):
            r.font.size = Pt(24)
            r.font.bold = True
            r.font.color.rgb = RGBColor.from_string(AZUL)
    for sh in list(slide.shapes):
        if sh is sec or sh is sub or sh.top is None:
            continue
        if sh.top >= 2000000:
            sh.top = sh.top - DY
    # logo del equipo un poco mas chico, alineado con el titulo
    for sh in slide.shapes:
        if sh.shape_type == 13 and sh.left == 368560 and sh.top == 320000:
            sh.left, sh.top, sh.width, sh.height = int(0.3 * EMU_IN), int(0.28 * EMU_IN), int(1.1 * EMU_IN), int(1.1 * EMU_IN)


def pie(slide, k):
    y = int(7.08 * EMU_IN)
    h = int(0.3 * EMU_IN)
    _caja(slide, int(0.35 * EMU_IN), y, int(3.6 * EMU_IN), h, "Presenter: ", 10, "000000", "l")
    _caja(slide, int(3.9 * EMU_IN), y, int(5.53 * EMU_IN), h, EQUIPO, 10, "000000", "c")
    _caja(slide, int(11.9 * EMU_IN), y, int(1.08 * EMU_IN), h, str(k), 10, "000000", "r")


def _fondo_de(slide):
    bg = slide._element.find(qn("p:cSld")).find(qn("p:bg"))
    if bg is None:
        return None
    blip = bg.find(".//" + qn("a:blip"))
    return None if blip is None else slide.part.related_part(blip.get(qn("r:embed")))


def aplicar(prs):
    slides = list(prs.slides)
    n_lam = len(slides)
    logo_ca = None
    for sh in slides[0].shapes:
        if sh.shape_type == 13 and sh.image.size[0] > 800:
            logo_ca = Image.open(io.BytesIO(sh.image.blob)).convert("RGBA")
    # fondos
    hechos = set()
    for i, s in enumerate(slides):
        p = _fondo_de(s)
        if p is None or p.partname in hechos:
            continue
        hechos.add(p.partname)
        orig = Image.open(io.BytesIO(p.blob))
        if i == 0:
            nuevo = fondo_blanco()
        elif i == 1:
            nuevo = fondo_titulo(orig, logo_ca)
        elif i == n_lam - 1:
            nuevo = fondo_blanco(logo_ca, (1536, 540), 470)
        else:
            nuevo = fondo_laminas(orig)
        p._blob = _png(nuevo.resize(orig.size, Image.LANCZOS))
    # logo de CONAE del cierre: de blanco a azul
    for sh in slides[-1].shapes:
        if sh.shape_type == 13 and sh.image.size[0] < 400:
            im = Image.open(io.BytesIO(sh.image.blob)).convert("RGBA")
            a = np.asarray(im).copy()
            a[..., :3] = _rgb(AZUL)
            parte = sh.part.related_part(sh._element.blipFill.blip.rEmbed)
            parte._blob = _png(Image.fromarray(a, "RGBA"))
    for i, s in enumerate(slides):
        k = i + 1
        portada = i in (0, 1, n_lam - 1)
        recolorear(s._element, blanco_a_azul=portada)
        tarjetas_a_recuadros(s._element)
        _set_font(s._element)
        if not portada:
            encabezado(s, k)
            pie(s, k)
    # indice: numeros de pagina reales (antes, el numero del circulo = pagina - 3)
    for sh in slides[3].shapes:
        if sh.has_table:
            for r in list(sh.table.rows)[1:]:
                runs = r.cells[0].text_frame.paragraphs[0].runs
                t = "".join(x.text for x in runs).strip()
                if t.isdigit():
                    runs[0].text = str(int(t) + 3)
                    for x in runs[1:]:
                        x.text = ""
    # tema: Arial y colores (lo que el equipo agregue sale igual)
    tema = prs.slide_master.part.part_related_by(
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme")
    raiz = etree.fromstring(tema.blob)
    esq = raiz.find(".//" + qn("a:clrScheme"))
    for kk, v in {"dk2": AZUL_T, "accent1": AZUL, "accent2": ROJO_SEL, "accent5": "2E75B6", "hlink": "2E75B6"}.items():
        e = esq.find(qn("a:" + kk))
        if e is not None:
            for ch in list(e):
                e.remove(ch)
            etree.SubElement(e, qn("a:srgbClr")).set("val", v)
    for f in raiz.iter(qn("a:latin")):
        if f.getparent().tag in (qn("a:majorFont"), qn("a:minorFont")):
            f.set("typeface", "Arial")
    tema._blob = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", standalone=True)
