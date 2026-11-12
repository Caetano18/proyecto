"""Proyeccion ortogonal con eliminacion de lineas ocultas (OpenCascade HLR) y
utilidades de dibujo tecnico sobre matplotlib (hojas A3, cotas, rotulo)."""
import math
import numpy as np
import cadquery as cq
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepLib import BRepLib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Polygon
import params as P

# vistas normalizadas: (direccion desde la que se mira, eje horizontal del papel)
VISTAS = {
    "superior": ((0, 0, 1), (1, 0, 0)),      # planta: x a la derecha, y hacia arriba
    "lateral": ((0, -1, 0), (1, 0, 0)),      # x a la derecha, z hacia arriba
    "frontal": ((-1, 0, 0), (0, 1, 0)),      # desde la nariz: y a la derecha, z arriba (visto desde -x: y invertida)
    "posterior": ((1, 0, 0), (0, -1, 0)),
    "inferior": ((0, 0, -1), (1, 0, 0)),
}


def _edges(compound, defl=0.05):
    out = []
    if compound is None or compound.IsNull():
        return out
    BRepLib.BuildCurves3d_s(compound)
    ex = TopExp_Explorer(compound, TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge_s(ex.Current())
        try:
            c = BRepAdaptor_Curve(e)
            d = GCPnts_QuasiUniformDeflection(c, defl)
            if d.IsDone() and d.NbPoints() >= 2:
                pts = np.array([[d.Value(i).X(), d.Value(i).Y()] for i in range(1, d.NbPoints() + 1)])
                out.append(pts)
        except Exception:
            pass
        ex.Next()
    return out


def proyectar(shapes, vista, ocultas=False):
    """Devuelve (visibles, ocultas): listas de polilineas 2D en coordenadas de la vista."""
    d, xd = VISTAS[vista] if isinstance(vista, str) else vista
    comp = cq.Compound.makeCompound(shapes) if isinstance(shapes, (list, tuple)) else shapes
    hlr = HLRBRep_Algo()
    hlr.Add(comp.wrapped)
    hlr.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*d), gp_Dir(*xd))))
    hlr.Update()
    hlr.Hide()
    hs = HLRBRep_HLRToShape(hlr)
    vis = []
    for c in (hs.VCompound(), hs.OutLineVCompound(), hs.Rg1LineVCompound()):
        vis += _edges(c)
    hid = []
    if ocultas:
        for c in (hs.HCompound(), hs.OutLineHCompound()):
            hid += _edges(c)
    return vis, hid


def ejes_vista(vista):
    d, xd = VISTAS[vista] if isinstance(vista, str) else vista
    d, xd = np.array(d, float), np.array(xd, float)
    yd = np.cross(d, xd)
    return xd, yd


class Hoja:
    """Hoja A3 apaisada (420 x 297 mm) dibujada a escala real en milimetros de papel."""
    W, H = 420.0, 297.0

    def __init__(self, numero, titulo, escala_txt, material="-", notas=()):
        self.fig = plt.figure(figsize=(self.W / 25.4, self.H / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, self.W)
        self.ax.set_ylim(0, self.H)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self.numero, self.titulo = numero, titulo
        self._marco()
        self._rotulo(escala_txt, material)
        self._notas(notas)

    # ---------------------------------------------------------- formato
    def _marco(self):
        a = self.ax
        a.add_patch(Rectangle((10, 10), self.W - 20, self.H - 20, fill=False, lw=0.9, ec="k"))
        for i in range(1, 8):
            x = 10 + i * (self.W - 20) / 8
            a.plot([x, x], [10, 13], "k", lw=0.4)
            a.plot([x, x], [self.H - 13, self.H - 10], "k", lw=0.4)
            a.text(x - (self.W - 20) / 16, self.H - 11.5, str(i), ha="center", va="center", fontsize=5)
        for i, c in enumerate("ABCDEF"):
            y = self.H - 10 - (i + 0.5) * (self.H - 20) / 6
            a.text(11.5, y, c, ha="center", va="center", fontsize=5)

    def _rotulo(self, escala_txt, material):
        a = self.ax
        x0, y0, w, h = self.W - 10 - 180, 10, 180, 36
        a.add_patch(Rectangle((x0, y0), w, h, fill=True, fc="white", lw=0.9, ec="k", zorder=5))
        for y in (y0 + 12, y0 + 24):
            a.plot([x0, x0 + w], [y, y], "k", lw=0.4, zorder=6)
        for x, ya, yb in ((x0 + 62, y0, y0 + 24), (x0 + 110, y0, y0 + 24), (x0 + 145, y0, y0 + 24)):
            a.plot([x, x], [ya, yb], "k", lw=0.4, zorder=6)

        def cel(x, y, lab, val, fs=7.5, bold=False):
            a.text(x + 1.5, y + 9.6, lab, fontsize=4.2, color="0.35", va="center", zorder=7)
            a.text(x + 1.5, y + 4.2, val, fontsize=fs, va="center", zorder=7, weight="bold" if bold else "normal")
        a.text(x0 + 1.5, y0 + 33, "PROYECTO", fontsize=4.2, color="0.35", va="center", zorder=7)
        a.text(x0 + 1.5, y0 + 28, f"CanSat ala delta - {P.EQUIPO} {P.TEMPORADA}", fontsize=8.5, va="center",
               zorder=7, weight="bold")
        a.text(x0 + w - 2, y0 + 30, "PDR · Subsistema mecánico", fontsize=6, ha="right", va="center", zorder=7)
        cel(x0, y0 + 12, "TÍTULO", self.titulo, 7.5, True)
        cel(x0 + 62, y0 + 12, "MATERIAL", material, 6)
        cel(x0 + 110, y0 + 12, "ESCALA", escala_txt, 7.5)
        cel(x0 + 145, y0 + 12, "PLANO N.º", self.numero, 9, True)
        cel(x0, y0, "UNIDADES / TOLERANCIA GENERAL", "mm  ·  ±0,2 (impresas ±0,3)", 6)
        cel(x0 + 62, y0, "FECHA", P.FECHA, 6.5)
        cel(x0 + 110, y0, "REV.", P.REV, 7.5)
        cel(x0 + 145, y0, "HOJA", f"{self.numero.split('-')[-1]} de 07", 6.5)

    def _notas(self, notas):
        y = 43
        if notas:
            self.ax.text(14, y - 26 + 4.2 * len(notas), "NOTAS", fontsize=6, weight="bold", va="bottom")
        for i, n in enumerate(notas):
            self.ax.text(14, y - 26 + 4.2 * (len(notas) - 1 - i), f"{i + 1}. {n}", fontsize=5.3, va="bottom")

    # ------------------------------------------------------------ vistas
    def vista(self, shapes, vista, origen, escala=1.0, ocultas=False, titulo=None, lw=0.45, color="k", ref=(0, 0, 0),
              titulo_dy=None):
        """Dibuja la proyeccion.  `origen` = posicion en la hoja del punto 3D `ref`.  Devuelve T(p3d)->hoja."""
        vis, hid = proyectar(shapes, vista, ocultas)
        xd, yd = ejes_vista(vista)
        r = np.array(ref, float)
        off = np.array(origen, float) - escala * np.array([r @ xd, r @ yd])
        for pl in hid:
            q = pl * escala + off
            self.ax.plot(q[:, 0], q[:, 1], color="0.45", lw=0.22, ls=(0, (4, 2.5)), solid_capstyle="round")
        allq = []
        for pl in vis:
            q = pl * escala + off
            allq.append(q)
            self.ax.plot(q[:, 0], q[:, 1], color=color, lw=lw, solid_capstyle="round")

        def T(p):
            p = np.array(p, float)
            return off + escala * np.array([p @ xd, p @ yd])
        if titulo and allq:
            allq = np.vstack(allq)
            yb = allq[:, 1].min() - (7 if titulo_dy is None else titulo_dy)
            self.ax.text(0.5 * (allq[:, 0].min() + allq[:, 0].max()), yb, titulo, ha="center", va="top", fontsize=6.5,
                         weight="bold")
        return T

    # ------------------------------------------------------------- cotas
    def _flecha(self, p, q):
        self.ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>", mutation_scale=4.2, lw=0.28, color="k",
                                          shrinkA=0, shrinkB=0))

    def cota_h(self, p1, p2, y, txt=None, fs=5.6, ext=1.5, valor=None, dy=1.4):
        """Cota horizontal entre dos puntos de hoja; la linea de cota va a la altura y."""
        x1, x2 = p1[0], p2[0]
        for p, x in ((p1, x1), (p2, x2)):
            s = 1 if y > p[1] else -1
            self.ax.plot([x, x], [p[1] + s * 0.8, y + s * ext], "k", lw=0.2)
        self._flecha((x1, y), (x2, y))
        t = txt if txt is not None else f"{valor:g}".replace(".", ",")
        self.ax.text(0.5 * (x1 + x2), y + dy, t, ha="center", va="bottom" if dy > 0 else "top", fontsize=fs)

    def cota_v(self, p1, p2, x, txt=None, fs=5.6, ext=1.5, valor=None, dx=-1.2):
        y1, y2 = p1[1], p2[1]
        for p, y in ((p1, y1), (p2, y2)):
            s = 1 if x > p[0] else -1
            self.ax.plot([p[0] + s * 0.8, x + s * ext], [y, y], "k", lw=0.2)
        self._flecha((x, y1), (x, y2))
        t = txt if txt is not None else f"{valor:g}".replace(".", ",")
        self.ax.text(x + dx, 0.5 * (y1 + y2), t, ha="right" if dx < 0 else "left", va="center", fontsize=fs,
                     rotation=90)

    def cota_al(self, p1, p2, off, txt, fs=5.6):
        """Cota alineada (paralela al segmento p1-p2, desplazada `off`)."""
        p1, p2 = np.array(p1, float), np.array(p2, float)
        d = (p2 - p1) / np.linalg.norm(p2 - p1)
        n = np.array([-d[1], d[0]])
        a, b = p1 + n * off, p2 + n * off
        for p, q in ((p1, a), (p2, b)):
            self.ax.plot([p[0], q[0] + n[0] * 1.2 * np.sign(off)], [p[1], q[1] + n[1] * 1.2 * np.sign(off)], "k", lw=0.2)
        self._flecha(tuple(a), tuple(b))
        ang = math.degrees(math.atan2(d[1], d[0]))
        if ang > 90 or ang < -90:
            ang += 180
        m = 0.5 * (a + b) + n * 1.6 * np.sign(off)
        self.ax.text(m[0], m[1], txt, ha="center", va="center", fontsize=fs, rotation=ang, rotation_mode="anchor")

    def llamada(self, p, q, txt, fs=5.6, ha="left"):
        """Linea de referencia desde el punto p hasta el texto en q."""
        self.ax.annotate(txt, xy=p, xytext=q, fontsize=fs, ha=ha, va="center",
                         arrowprops=dict(arrowstyle="-|>", lw=0.28, color="k", mutation_scale=4, shrinkA=1, shrinkB=0))

    def globo(self, p, q, n, r=2.6):
        self.ax.plot([p[0], q[0]], [p[1], q[1]], "k", lw=0.25)
        self.ax.plot([p[0]], [p[1]], "ko", ms=1.2)
        self.ax.add_patch(plt.Circle(q, r, fill=True, fc="white", ec="k", lw=0.35, zorder=4))
        self.ax.text(q[0], q[1], str(n), ha="center", va="center", fontsize=5.5, zorder=5)

    def eje(self, p, q):
        self.ax.plot([p[0], q[0]], [p[1], q[1]], color="0.2", lw=0.2, ls=(0, (9, 2, 1.5, 2)))

    def texto(self, x, y, t, fs=6, **kw):
        self.ax.text(x, y, t, fontsize=fs, **kw)

    def tabla(self, x, y, cols, filas, anchos, fs=5.2, alto=4.4, titulo=None):
        """Tabla con encabezado; (x, y) = esquina superior izquierda."""
        a = self.ax
        W = sum(anchos)
        if titulo:
            a.text(x, y + 1.5, titulo, fontsize=6.2, weight="bold", va="bottom")
        a.add_patch(Rectangle((x, y - alto), W, alto, fc="0.85", ec="k", lw=0.35))
        xx = x
        for c, w in zip(cols, anchos):
            a.text(xx + 1, y - alto / 2, c, fontsize=fs, va="center", weight="bold")
            xx += w
        for i, f in enumerate(filas):
            yy = y - alto * (i + 2)
            a.add_patch(Rectangle((x, yy), W, alto, fill=False, ec="k", lw=0.25))
            xx = x
            for c, w in zip(f, anchos):
                a.text(xx + 1, yy + alto / 2, str(c), fontsize=fs, va="center")
                xx += w
        xx = x
        for w in anchos[:-1]:
            xx += w
            a.plot([xx, xx], [y, y - alto * (len(filas) + 1)], "k", lw=0.25)

    def guardar(self, pdf=None, png=None, dpi=200):
        if pdf is not None:
            pdf.savefig(self.fig)
        if png:
            self.fig.savefig(png, dpi=dpi)
        plt.close(self.fig)


class Lienzo(Hoja):
    """Figura libre (sin marco ni rotulo) para las laminas del PDR.  Unidades: mm de papel."""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.fig = plt.figure(figsize=(W / 25.4, H / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(0, H)
        self.ax.set_aspect("equal")
        self.ax.axis("off")

    def guardar(self, png, dpi=260):
        self.fig.savefig(png, dpi=dpi)
        plt.close(self.fig)
