"""Tema visual del equipo Hermes para la presentacion del PDR.

Cambia la paleta de la plantilla (violeta y turquesa de la competencia) por la del logo de Hermes:
azul noche, dorado y azul tierra.  Regenera los cuatro fondos (portada, titulo, laminas y cierre)
conservando los logos oficiales (CanSat Argentina y CONAE), recolorea textos, tarjetas y tablas de
todas las laminas segun su contexto (texto, relleno o linea) y actualiza los colores del tema.
"""
import io
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pptx.oxml.ns import qn

# ---------------------------------------------------------------- paleta (logo de Hermes)
NOCHE = (10, 26, 56)        # #0A1A38  fondo espacial
AZUL = (14, 33, 72)         # #0E2148  azul noche: texto y encabezados
TIERRA = (31, 95, 168)      # #1F5FA8  azul tierra: acento secundario
ORO = (224, 165, 38)        # #E0A526  dorado: barras y acentos
ORO_T = "A8730C"            # dorado oscuro para texto sobre blanco (contraste 3,6:1, texto grande)
MARFIL = "F6F2E9"           # tarjetas
BORDE = "E2D9C6"            # bordes de tabla
SEL = "E7EEF8"              # fondo de la opcion seleccionada


def hx(c):
    return "%02X%02X%02X" % c


TEXTO = {"242C4F": hx(AZUL), "138A8A": ORO_T, "5B6478": "5A6070", "6B7280": "5A6070", "5A6280": "5A6070"}
RELLENO = {"242C4F": hx(AZUL), "138A8A": hx(TIERRA), "F1F4F9": MARFIL, "E2F1F1": SEL, "BFE6E6": "F3E3BC",
           "D5DAE5": BORDE}
LINEA = {"D5DAE5": BORDE, "138A8A": hx(ORO), "242C4F": hx(AZUL)}
TEMA = {"dk2": hx(AZUL), "lt2": MARFIL, "accent1": hx(AZUL), "accent2": hx(ORO), "accent3": hx(TIERRA),
        "accent4": ORO_T, "accent5": "6E86B8", "accent6": "5A6070", "hlink": hx(TIERRA), "folHlink": "6E4E9E"}

W, H = 1920, 1080


# ---------------------------------------------------------------- fondos
def _degrade(c0, c1, ang=0.0, w=W, h=H):
    y, x = np.mgrid[0:h, 0:w].astype(float)
    t = (x / w) * np.cos(ang) + (y / h) * np.sin(ang)
    t = (t - t.min()) / (t.max() - t.min())
    a = np.array(c0, float)[None, None, :] * (1 - t[..., None]) + np.array(c1, float)[None, None, :] * t[..., None]
    return Image.fromarray(a.astype(np.uint8), "RGB")


def _resplandor(im, cx, cy, r, color, alfa=0.55):
    """Halo circular suave (la Tierra del logo)."""
    y, x = np.mgrid[0:H, 0:W].astype(float)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2 * alfa
    base = np.asarray(im, float)
    out = base * (1 - a[..., None]) + np.array(color, float)[None, None, :] * a[..., None]
    return Image.fromarray(out.astype(np.uint8), "RGB")


def _estrellas(im, n=170, semilla=7, zona=None):
    rnd = random.Random(semilla)
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x0, y0, x1, y1 = zona or (0, 0, W, H)
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        r = rnd.choice([0.8, 1.0, 1.2, 1.6, 2.2])
        a = int(rnd.uniform(60, 200))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    return Image.alpha_composite(im.convert("RGBA"), capa).convert("RGB")


def _pegar(im, logo, cx, cy, lado):
    lg = logo.copy()
    lg.thumbnail((lado, lado), Image.LANCZOS)
    base = im.convert("RGBA")
    base.alpha_composite(lg, (int(cx - lg.width / 2), int(cy - lg.height / 2)))
    return base.convert("RGB")


def _logo_blanco(png, fondo):
    """Logo blanco sobre fondo liso -> RGBA (alfa por luminancia)."""
    a = np.asarray(png.convert("RGB"), float)
    f = np.array(fondo, float)
    l = (a - f).clip(0).mean(axis=2) / (255 - f.mean())
    rgba = np.zeros(a.shape[:2] + (4,), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = (l.clip(0, 1) * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def fondo_laminas(orig):
    """Laminas de contenido: blanco, barra azul noche con filete dorado arriba y abajo, logo de la competencia."""
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 11], fill=AZUL)
    d.rectangle([0, 12, W, 15], fill=ORO)
    d.rectangle([0, H - 26, W, H - 23], fill=ORO)
    d.rectangle([0, H - 22, W, H], fill=AZUL)
    # filete del encabezado: misma posicion que la plantilla, en dorado claro
    o = np.asarray(orig.convert("RGB"), int)
    fila = int(np.argmin(o[100:200, 200:1500].sum(axis=(1, 2)))) + 100
    d.rectangle([72, fila - 1, 1672, fila], fill=(214, 196, 150))
    # logo de CanSat Argentina (arriba a la derecha, sobre blanco): se recorta tal cual
    caja = o[20:260, 1690:1920]
    no_bl = np.where((caja < 235).any(axis=2))
    y0, y1, x0, x1 = no_bl[0].min() + 20, no_bl[0].max() + 21, no_bl[1].min() + 1690, no_bl[1].max() + 1691
    im.paste(orig.convert("RGB").crop((x0, y0, x1, y1)), (x0, y0))
    return im


def fondo_portada(logo_ca):
    im = _degrade(NOCHE, (19, 46, 92), ang=0.35)
    im = _resplandor(im, 1500, 1350, 900, TIERRA, 0.45)
    im = _estrellas(im, 220, 3)
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 14, W, H], fill=ORO)
    return im


def fondo_titulo(logo_ca, orig):
    im = Image.new("RGB", (W, H), NOCHE)
    im = _estrellas(im, 120, 11, (0, 230, W, 900))
    banda = _degrade((16, 40, 86), TIERRA, ang=0.0, h=200)
    im.paste(banda, (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 200, W, 209], fill=ORO)
    im = _pegar(im, logo_ca, W / 2, 205, 330)
    # pie: lineas y logo de CONAE tomados de la plantilla (blanco sobre azul liso)
    o = orig.convert("RGB")
    fondo_viejo = tuple(int(v) for v in np.median(np.asarray(o.crop((40, 1000, 300, 1070))).reshape(-1, 3), axis=0))
    pie = _logo_blanco(o.crop((0, 940, W, 1080)), fondo_viejo)
    base = im.convert("RGBA")
    base.alpha_composite(pie, (0, 940))
    return base.convert("RGB")


def fondo_cierre(logo_ca):
    im = _degrade(NOCHE, (20, 44, 90), ang=0.6)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.polygon([(0, 1080), (0, 700), (720, 1080)], fill=(31, 95, 168, 70))
    d.polygon([(1100, 0), (1920, 0), (1920, 520)], fill=(31, 95, 168, 55))
    d.polygon([(0, 1080), (0, 1010), (1920, 380), (1920, 450)], fill=(224, 165, 38, 235))
    im = Image.alpha_composite(im.convert("RGBA"), capa.filter(ImageFilter.GaussianBlur(0.6))).convert("RGB")
    im = _estrellas(im, 140, 5)
    im = _pegar(im, logo_ca, 1536, 540, 470)
    return im


def _png(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


# ---------------------------------------------------------------- recoloreo
CTX_TEXTO = {qn("a:rPr"), qn("a:endParaRPr"), qn("a:defRPr")}
CTX_LINEA = {qn("a:ln"), qn("a:lnL"), qn("a:lnR"), qn("a:lnT"), qn("a:lnB")}


def recolorear(el):
    n = 0
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
        if v in tabla:
            c.set("val", tabla[v])
            n += 1
    return n


def fondo_de(slide):
    bg = slide._element.find(qn("p:cSld")).find(qn("p:bg"))
    if bg is None:
        return None
    blip = bg.find(".//" + qn("a:blip"))
    return None if blip is None else slide.part.related_part(blip.get(qn("r:embed")))


def aplicar(prs):
    # fondos: se reemplaza cada imagen una vez (las comparten todas las laminas que la usan)
    partes = {}
    for i, s in enumerate(prs.slides):
        p = fondo_de(s)
        if p is not None:
            partes.setdefault(p.partname, (p, i))
    logo_ca = None
    for s in [prs.slides[0]]:
        for sh in s.shapes:
            if sh.shape_type == 13 and sh.image.size[0] > 800:
                logo_ca = Image.open(io.BytesIO(sh.image.blob)).convert("RGBA")
    n_lam = len(prs.slides)
    for nombre, (p, i) in partes.items():
        orig = Image.open(io.BytesIO(p.blob))
        if i == 0:
            nuevo = fondo_portada(logo_ca)
        elif i == 1:
            nuevo = fondo_titulo(logo_ca, orig)
        elif i == n_lam - 1:
            nuevo = fondo_cierre(logo_ca)
        else:
            nuevo = fondo_laminas(orig)
        p._blob = _png(nuevo.resize(orig.size, Image.LANCZOS))
    # colores de textos, rellenos y lineas
    n = sum(recolorear(s._element) for s in prs.slides)
    # colores del tema (lo que el equipo agregue despues sale con la paleta)
    tema = prs.slide_master.part.part_related_by(
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme")
    from lxml import etree
    raiz = etree.fromstring(tema.blob)
    esq = raiz.find(".//" + qn("a:clrScheme"))
    for k, v in TEMA.items():
        e = esq.find(qn("a:" + k))
        if e is not None:
            for ch in list(e):
                e.remove(ch)
            etree.SubElement(e, qn("a:srgbClr")).set("val", v)
    tema._blob = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", standalone=True)
    return n
