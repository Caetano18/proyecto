"""CAD del diseno combinado (rev. E): cuerpo integral del documento v2 del equipo con la carcasa laminada de la rev. D.

Coordenadas: x = eje del CanSat, 0 en el fondo de nadir y 240 en la tapa de cenit (estaciones del documento v2);
z = lomo (quilla de la vela), y = flancos.
build(config): "estibado" (lanzamiento), "desplegado" (planeo, fase 2) o "fase1" (bajo el paracaidas).
Cada pieza es un dict(nombre, shape | mesh, color, grupo).
"""
import math
import numpy as np
import pyvista as pv
import cadquery as cq
from cadquery import Vector as V
from cad import box, rod, disc, fuse, sector

L = 240.0
RO = 45.0
XH = 130.0                         # union carbono (abajo) / vidrio (arriba)
TC, TV = 0.8, 0.6
RAN_X = (14.0, 206.0)              # ranuras de los largueros (192 mm)
RAN_ANG = 35.0
RAN_W = 6.0
R_LAR = 41.0                       # eje del larguero estibado
L_LAR, L_PUNTA = 185.0, 40.0
FLECHA = 52.0
QUILLA = (14.0, 204.0)             # 190 mm sobre el lomo
CANAL_W = 28.0                     # canal dorsal donde va la vela plegada
CANAL_P = 6.0                      # profundidad del canal
R_VAR = 33.0
VAR_ANG = (45.0, 135.0, 225.0, 315.0)
MAMP = {"M1": (0.0, 4.0), "M2": (83.0, 87.0), "M3": (173.0, 177.0), "M4": (216.0, 220.0), "M5": (236.0, 240.0)}
PANEL_X = (135.0, 185.0)
Y_FLAT = 41.2

C_CARB = (0.17, 0.17, 0.19)
C_VID = (0.83, 0.86, 0.76)
C_PETG = (0.42, 0.46, 0.55)
C_CF = (0.10, 0.10, 0.12)
C_AL = (0.76, 0.78, 0.81)
C_ACERO = (0.62, 0.64, 0.68)
C_TELA = (0.95, 0.45, 0.10)
C_PCB = (0.10, 0.45, 0.22)
C_NEGRO = (0.08, 0.08, 0.09)
C_BAT = (0.15, 0.36, 0.78)
C_SOLAR = (0.10, 0.16, 0.42)
C_PARA = (0.78, 0.13, 0.13)
C_BLANCO = (0.96, 0.96, 0.94)
C_DYN = (0.98, 0.80, 0.10)
C_CUB = (0.90, 0.90, 0.86)

YL, ZL = R_LAR * math.cos(math.radians(RAN_ANG)), R_LAR * math.sin(math.radians(RAN_ANG))


def punta(s_sign):
    """Largo de la puntera plegable.  En BR el larguero izquierdo (-y, mirando hacia adelante = nadir) va sin puntera:
    ese lobulo tiene menos superficie y la diferencia de sustentacion hace virar al CanSat."""
    return 0.0 if (VAR == "BR" and s_sign < 0) else L_PUNTA

# variante: "E" = rev. E (laminado + esqueleto con lastre); "A" = v2 diseno A (monocasco PETG 2 mm, mamparos pegados);
# "B" = v2 diseno B (esqueleto de 4 varillas M3 + mamparos + carena PETG 2 mm)
VAR = "E"
T_PETG = 2.0
C_PETGC = (0.80, 0.84, 0.90)
C_ADH = (0.86, 0.62, 0.18)
D_PARA = 233.0


X_M2, X_M3 = 83.0, 173.0          # estaciones de M2 (modulo de bateria) y M3 (modulo de avionica)


def variante(v, x_m2=83.0, x_m3=173.0):
    """v = "E", "A", "B" o "BR" (B regulable: estaciones roscadas; x_m2 y x_m3 son las caras inferiores de M2 y M3)."""
    global VAR, D_PARA, X_M2, X_M3
    VAR = v
    D_PARA = 233.0 if v == "E" else 226.0
    X_M2, X_M3 = (x_m2, x_m3) if v == "BR" else (83.0, 173.0)
    MAMP["M2"] = (X_M2, X_M2 + 4.0)
    MAMP["M3"] = (X_M3, X_M3 + 4.0)


def tuerca(x0, y, z, ancho=5.5, alto=2.4):
    """Tuerca hexagonal M3 (eje x) con la cara inferior en x0."""
    return cq.Workplane("YZ").polygon(6, ancho / math.cos(math.radians(30))).extrude(alto).val().translate(V(x0, y, z))


def servo_flecha(desplegada=False):
    """BR: servo de flecha en la bahia 1, entre los pivotes.  Los resortes de torsion empujan los largueros hacia afuera y el
    servo, con dos varillas de empuje, los frena en el angulo que se le ordena (es un tope regulable)."""
    out = []
    cuerpo = box(8.0, 30.8, -6.1, 6.1, 8.0, 34.5)
    orejas = box(4.0, 34.8, -6.1, 6.1, 26.0, 28.5)
    out.append(_pz("Servo de flecha", fuse(cuerpo, orejas), (0.10, 0.20, 0.55), "equipo"))
    out.append(_pz("Soporte del servo", box(4.0, 8.0, -9.0, 9.0, 6.0, 30.0), C_PETG, "esqueleto"))
    eje = (19.4, 0.0, 34.5)
    out.append(_pz("Brazo del servo", fuse(rod((19.4, 0, 34.5), (19.4, 0, 36.0), 6.0), box(16.0, 22.8, -14.0, 14.0, 35.0, 36.0)),
                   C_BLANCO, "equipo"))
    var = None
    for s_ in (1, -1):
        if desplegada:
            d = np.array([math.cos(math.radians(FLECHA)), s_ * math.sin(math.radians(FLECHA)), 0.0])
            q = tuple(np.array([14.0, s_ * YL, ZL]) + 9.0 * d)
        else:
            q = (24.0, s_ * (YL - 1.5), ZL + 1.0)
        r_ = rod((19.4, s_ * 13.0, 35.5), q, 1.4)
        var = r_ if var is None else var.fuse(r_)
    out.append(_pz("Varillas de empuje", var, C_ACERO, "equipo"))
    return out


def tuercas_estaciones():
    """BR: cada mamparo queda apretado entre dos tuercas nyloc M3; girandolas se corre la estacion (0,5 mm por vuelta)."""
    out = []
    xs = [MAMP["M1"][1], MAMP["M2"][0] - 2.4, MAMP["M2"][1], MAMP["M3"][0] - 2.4, MAMP["M3"][1], MAMP["M4"][0] - 2.4]
    for a in VAR_ANG:
        y, z = R_VAR * math.cos(math.radians(a)), R_VAR * math.sin(math.radians(a))
        sh = None
        for x0 in xs:
            t_ = tuerca(x0, y, z)
            sh = t_ if sh is None else sh.fuse(t_)
        out.append(_pz("Tuercas nyloc de las estaciones", sh, C_ACERO, "esqueleto"))
    return out


def t_en(x):
    """Espesor de la pared en la estacion x."""
    if VAR == "E":
        return TC if x < XH else TV
    return T_PETG


def _ang(w, r=RO):
    return math.degrees(2 * math.asin(w / 2 / r))


def _pz(nombre, shape, color, grupo, **kw):
    d = dict(nombre=nombre, shape=shape, color=color, grupo=grupo)
    d.update(kw)
    return d


# ------------------------------------------------------------------ carcasa laminada
def carcasa(ventana_cenit=True):
    wr = math.degrees(RAN_W / RO)
    ran = fuse(*[sector(RAN_X[0], RAN_X[1], R_LAR - 3.5, RO + 1, a, wr) for a in (RAN_ANG, 180 - RAN_ANG)])
    out = []
    if VAR == "E":
        tramos = (("CT1a carcasa carbono-epoxi 0,8", 0.0, XH, TC, C_CARB), ("CT1b carcasa vidrio-epoxi 0,6", XH, L - 4.0, TV, C_VID))
    else:
        tramos = (("CT1 " + ("monocasco PETG 2 mm" if VAR == "A" else "carena PETG 2 mm"), 0.0, L - 4.0, T_PETG, C_PETGC),)
    for nombre, x0, x1, t, col in tramos:
        ext = disc(x0, x1, RO).cut(sector(QUILLA[0], RAN_X[1], RO - CANAL_P, RO + 1, 90, _ang(CANAL_W)))
        cw = _ang(CANAL_W + 2 * t, RO - CANAL_P)
        inn = disc(x0 - 1, x1 + 1, RO - t).cut(sector(QUILLA[0] - t, RAN_X[1] + t, RO - CANAL_P - t, RO + 1, 90, cw))
        for s in (1, -1):                                   # planos embutidos de los paneles solares (flancos)
            ext = ext.cut(box(PANEL_X[0], PANEL_X[1], Y_FLAT, 60, -15, 15).mirror("XZ") if s < 0 else
                          box(PANEL_X[0], PANEL_X[1], Y_FLAT, 60, -15, 15))
            b = box(PANEL_X[0] - t, PANEL_X[1] + t, Y_FLAT - t, 60, -15 - t, 15 + t)
            inn = inn.cut(b.mirror("XZ") if s < 0 else b)
        sh = ext.cut(inn).cut(ran)
        sh = sh.intersect(box(x0, x1, -60, 60, -60, 60))
        xb = 12.0 if VAR == "BR" else 22.0
        if x0 < xb < x1:
            sh = sh.cut(rod((xb, 30, 0), (xb, 50, 0), 8.0))                    # orificio de la baliza
        if ventana_cenit and x0 < 212 < x1:
            sh = sh.cut(rod((212, 30, 0), (212, 50, 0), 10.0))                 # ventana de la camara de cenit
        out.append(_pz(nombre, sh.clean(), col, "carcasa"))
    return out


def tornillos_carena():
    """Diseno B: la carena se atornilla a M1 y M4 (al sacar los tornillos, el esqueleto sale entero)."""
    out = []
    for xc in (2.0, 218.0):
        for a in (0.0, 180.0, 270.0):
            c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
            out.append(_pz("Tornillo de la carena", rod((xc, (RO - 0.9) * c, (RO - 0.9) * s_), (xc, (RO + 0.05) * c,
                                                                                          (RO + 0.05) * s_), 4.6),
                           C_ACERO, "tornillos"))
    return out


def cubierta():
    a = _ang(CANAL_W)
    cub = sector(QUILLA[0] + 0.3, RAN_X[1] - 0.3, RO - 0.8, RO, 90, a - 0.4)
    vela = sector(QUILLA[0] + 4, RAN_X[1] - 4, RO - CANAL_P + 0.2, RO - 1.0, 90, a - 2.0)
    return [_pz("Cubierta dorsal", cub, C_CUB, "cubierta"), _pz("Vela plegada en acordeon", vela, C_TELA, "vela")]


# ------------------------------------------------------------------ esqueleto
def varillas():
    out = []
    if VAR == "A":                       # sin varillas: la brida va a 4 cancamos M3 roscados en M4 (pegado a la carcasa)
        for k, a in enumerate(VAR_ANG):
            y, z = R_VAR * math.cos(math.radians(a)), R_VAR * math.sin(math.radians(a))
            sh = fuse(disc(214.0, 226.0, 1.25, y, z), disc(220.0, 222.4, 2.75, y, z), disc(212.6, 216.0, 2.75, y, z))
            out.append(_pz(f"Cancamo M3 {k + 1}", sh, C_ACERO, "esqueleto"))
            out.append(_pz(f"Ojal de brida {k + 1}", cq.Solid.makeTorus(2.2, 0.7, V(226.5, y, z), V(0, -z, y)), C_ACERO,
                           "esqueleto"))
        return out
    for k, a in enumerate(VAR_ANG):
        y, z = R_VAR * math.cos(math.radians(a)), R_VAR * math.sin(math.radians(a))
        v = disc(0.4, 226.0, 1.25, y, z)
        tu = fuse(disc(0.4, 2.8, 2.75, y, z), disc(220.0, 222.4, 2.75, y, z))
        ojo = cq.Solid.makeTorus(2.2, 0.7, V(226.5, y, z), V(0, -z, y))
        out.append(_pz(f"Varilla M3 {k + 1}", v, C_AL, "esqueleto"))
        out.append(_pz(f"Tuercas varilla {k + 1}", tu, C_ACERO, "esqueleto"))
        out.append(_pz(f"Ojal de brida {k + 1}", ojo, C_ACERO, "esqueleto"))
        if VAR == "E":                  # v2 no lleva lastre: ya pasa los 500 g
            out.append(_pz(f"Lastre arandelas {k + 1}", disc(68.0, 83.0, 5.5, y, z).cut(disc(67, 84, 1.6, y, z)),
                           C_ACERO, "esqueleto"))
    return out


def _agujeros_varillas(sh, x0, x1):
    for a in VAR_ANG:
        sh = sh.cut(disc(x0 - 1, x1 + 1, 1.6, R_VAR * math.cos(math.radians(a)), R_VAR * math.sin(math.radians(a))))
    return sh


def mamparos(con_tapa=True):
    out = []
    for n, (x0, x1) in MAMP.items():
        if n == "M5" and not con_tapa:
            continue
        t = t_en(x0)
        r = RO - t - (0.8 if VAR == "A" else 0.05)
        if n == "M5":
            sh = disc(x0, x1, RO - 0.2).fuse(disc(x0 - 4, x0 + 0.5, RO - t - 0.2).cut(disc(x0 - 5, x0 + 1, RO - t - 3.0)))
            out.append(_pz("M5 tapa de la copa", sh.clean(), C_PETG, "tapa"))
            continue
        sh = disc(x0, x1, r)
        if n in ("M2", "M3"):
            sh = sh.cut(sector(x0 - 1, x1 + 1, RO - CANAL_P - t - 0.2, RO + 1, 90, _ang(CANAL_W + 2 * t + 0.8, RO - CANAL_P)))
            sh = sh.cut(disc(x0 - 1, x1 + 1, 5.0, 0, -28.0))                    # paso de cables
            for a in (RAN_ANG, 180 - RAN_ANG):                                   # paso de los largueros
                sh = sh.cut(sector(x0 - 1, x1 + 1, 33.8, RO + 1, a, 11.0))
            if PANEL_X[0] < x1 and x0 < PANEL_X[1]:                              # planos de los paneles
                for yy in (1, -1):
                    b = box(x0 - 1, x1 + 1, Y_FLAT - t - 0.1, 60, -15 - t - 0.8, 15 + t + 0.8)
                    sh = sh.cut(b if yy > 0 else b.mirror("XZ"))
        if n == "M1":
            sh = sh.cut(disc(x0 - 1, x1 + 1, 7.0, 0.0, -20.0))                  # ventana de nadir
            for a in (VAR_ANG if VAR != "A" else ()):
                y, z = R_VAR * math.cos(math.radians(a)), R_VAR * math.sin(math.radians(a))
                sh = sh.cut(disc(x0 - 1, 2.8, 3.0, y, z))                       # tuercas embutidas
        if n == "M4":
            sh = sh.cut(disc(x0 - 1, x1 + 1, 3.0))                              # paso del lazo
        if VAR != "A":
            sh = _agujeros_varillas(sh, x0, x1)
        out.append(_pz(f"{n}", sh.clean(), C_PETG, "esqueleto"))
        if VAR == "A":                   # cordon de adhesivo entre el mamparo y la carcasa (las dos caras)
            ra = RO - t
            cord = disc(x0, x1, ra).cut(disc(x0 - 1, x1 + 1, r))
            if x0 > 0.5:                                   # M1: el filete de abajo quedaria fuera del cuerpo
                cord = cord.fuse(disc(x0 - 1.2, x0, ra).cut(disc(x0 - 2, x0 + 1, ra - 1.2)))
            cord = cord.fuse(disc(x1, x1 + 1.2, ra).cut(disc(x1 - 1, x1 + 2, ra - 1.2)))
            if QUILLA[0] < x1 and x0 < RAN_X[1]:          # el cordon no entra en el canal ni en las ranuras
                cord = cord.cut(sector(x0 - 2, x1 + 2, RO - CANAL_P - t - 0.3, RO + 1, 90, _ang(CANAL_W + 2 * t + 2, RO - CANAL_P)))
                for a_ in (RAN_ANG, 180 - RAN_ANG):
                    cord = cord.cut(sector(x0 - 2, x1 + 2, 33.8, RO + 1, a_, 12.0))
            if PANEL_X[0] < x1 + 1.2 and x0 - 1.2 < PANEL_X[1]:
                for yy in (1, -1):
                    bx = box(x0 - 2, x1 + 2, Y_FLAT - t - 0.1, 60, -15 - t - 0.8, 15 + t + 0.8)
                    cord = cord.cut(bx if yy > 0 else bx.mirror("XZ"))
            out.append(_pz(f"Adhesivo {n}", cord.clean(), C_ADH, "adhesivo"))
    return out


# ------------------------------------------------------------------ ala: pivotes, largueros y vela
def pivotes(desplegada):
    out = []
    for s in (1, -1):
        blk = sector(4.0, 26.0, 34.6, RO - t_en(10.0) - 0.05, RAN_ANG, 24.0)
        blk = blk.cut(rod((3, YL, ZL), (27, YL, ZL), 4.4)).cut(rod((14, YL, ZL - 9), (14, YL, ZL + 9), 4.0))
        perno = rod((14, YL, ZL - 8.0), (14, YL, ZL + 5.0), 4.0)
        res = fuse(cq.Solid.makeTorus(3.6, 0.8, V(14, YL, ZL - 3.4), V(0, 0, 1)),
                   cq.Solid.makeTorus(3.6, 0.8, V(14, YL, ZL - 6.4), V(0, 0, 1)))
        if s < 0:
            blk, perno, res = blk.mirror("XZ"), perno.mirror("XZ"), res.mirror("XZ")
        out += [_pz("Bloque de pivote", blk, C_PETG, "esqueleto"), _pz("Perno M4 del pivote", perno, C_ACERO, "ala"),
                _pz("Resortes de torsion", res, C_ACERO, "ala")]
    return out


def largueros(desplegada):
    out = []
    for s in (1, -1):
        p0 = np.array([14.0, s * YL, ZL])
        if desplegada:
            d = np.array([math.cos(math.radians(FLECHA)), s * math.sin(math.radians(FLECHA)), 0.0])
            pb = p0 + L_LAR * d
            tubo = rod(tuple(p0 - 6 * d), tuple(pb), 4.0, 2.0)
            out.append(_pz("Larguero CF", tubo, C_CF, "ala"))
            if punta(s) > 0:
                out += [_pz("Puntera del larguero", rod(tuple(pb), tuple(pb + punta(s) * d), 4.0, 2.0), C_CF, "ala"),
                        _pz("Bisagra de la puntera", rod(tuple(pb - 3 * d), tuple(pb + 3 * d), 6.0, 4.0), C_AL, "ala")]
        else:
            x1 = 14.0 + L_LAR
            tubo = rod((8.0, s * YL, ZL), (x1, s * YL, ZL), 4.0, 2.0)
            bis = rod((x1 - 3, s * YL, ZL), (x1 + 3, s * YL, ZL), 6.0, 4.0)
            rp = R_LAR - 4.8
            yp, zp = s * rp * math.cos(math.radians(RAN_ANG)), rp * math.sin(math.radians(RAN_ANG))
            out.append(_pz("Larguero CF", tubo, C_CF, "ala"))
            if punta(s) > 0:
                out += [_pz("Puntera plegada", rod((x1 - L_PUNTA, yp, zp), (x1, yp, zp), 4.0, 2.0), C_CF, "ala"),
                        _pz("Bisagra de la puntera", bis, C_AL, "ala")]
    return out


def vela_mesh(s_sign, ns=140, nt=70, h=31.0):
    """Lobulo de la vela Rogallo: superficie reglada entre la quilla y el larguero, con el inflado (billow) de v2."""
    d = np.array([math.cos(math.radians(FLECHA)), s_sign * math.sin(math.radians(FLECHA)), 0.0])
    P0 = np.array([14.0, s_sign * YL, ZL])
    zq = RO - CANAL_P + 0.6
    S, T = np.meshgrid(np.linspace(0, 1, ns), np.linspace(0, 1, nt), indexing="ij")
    K = np.stack([QUILLA[0] + (QUILLA[1] - QUILLA[0]) * S, 0 * S, zq + 0 * S], axis=-1)
    Lp = P0[None, None, :] + (L_LAR + punta(s_sign)) * S[..., None] * d[None, None, :]
    X = (1 - T)[..., None] * K + T[..., None] * Lp
    X[..., 2] += h * S * 4 * T * (1 - T)
    y = np.abs(X[..., 1])
    yc = CANAL_W / 2
    zs = np.sqrt(np.clip((RO + 0.6) ** 2 - y ** 2, 0, None))
    zmin = np.where(y < yc, zq + (math.sqrt((RO + 0.6) ** 2 - yc ** 2) - zq) * (y / yc) ** 2, zs)
    zmin = np.where(y < RO + 0.6, zmin, -1e9)
    dentro = (X[..., 0] > QUILLA[0] - 1) & (X[..., 0] < 240)
    zmin = np.where(dentro, zmin, -1e9)
    X[..., 2] = np.maximum(X[..., 2], zmin)
    g = pv.StructuredGrid(X[..., 0], X[..., 1], X[..., 2])
    return g.extract_surface().triangulate()


def vela_desplegada():
    out = []
    for s in (1, -1):
        out.append(dict(nombre="Vela Rogallo", mesh=vela_mesh(s), color=C_TELA, grupo="vela"))
    out.append(_pz("Quilla (fondo del canal)", box(QUILLA[0], QUILLA[1], -1.5, 1.5, RO - CANAL_P, RO - CANAL_P + 1.2),
                   C_CF, "ala"))
    return out


# ------------------------------------------------------------------ equipos
def equipos(con_paracaidas=True, lazo=True, pasador=True, x_pas=225.0):
    E = []
    # bahia 1: camara de nadir y baliza
    E.append(_pz("Camara de nadir", box(6.0, 14.0, -11, 11, -31, -9), C_NEGRO, "equipo"))
    E.append(_pz("Lente de nadir", disc(1.2, 6.0, 4.0, 0, -20), (0.35, 0.37, 0.42), "equipo"))
    E.append(_pz("Ventana de policarbonato", disc(0.2, 1.2, 6.8, 0, -20), (0.70, 0.82, 0.92), "equipo"))
    xb = 12.0 if VAR == "BR" else 22.0                  # BR: baliza mas abajo para dar recorrido al modulo de bateria
    E.append(_pz("Baliza (zumbador)", rod((xb, 36.0, 0), (xb, 43.2, 0), 12.0), C_NEGRO, "equipo"))
    E.append(_pz("Bateria de la baliza", box(6.0, 20.0, 18, 30, -7, 5) if VAR == "BR" else box(9.0, 33.0, 18, 30, -7, 5),
                 (0.85, 0.62, 0.15), "equipo"))
    # bahia 2: pack 2 x 18650 transversal
    d2 = X_M2 - 83.0
    for xc in (50.0 + d2, 70.0 + d2):
        E.append(_pz("Celda 18650", rod((xc, -32.5, -4), (xc, 32.5, -4), 18.6), C_BAT, "equipo"))
    E.append(_pz("Lenguetas soldadas", fuse(box(45 + d2, 75 + d2, 32.5, 33.3, -9, 1), box(45 + d2, 75 + d2, -33.3, -32.5, -9, 1)),
                 C_AL, "equipo"))
    if VAR == "BR":       # cuna en U impresa con M2: el pack cuelga de M2 y se mueve con el
        cuna = box(X_M2 - 46.0, X_M2, -30, 30, -16.6, -13.6)
        for sg in (1, -1):
            w = fuse(box(X_M2 - 46.0, X_M2, 33.5, 36.0, -16.6, 2.0), box(X_M2 - 46.0, X_M2, 29.9, 33.6, -16.6, -13.6))
            cuna = cuna.fuse(w if sg > 0 else w.mirror("XZ"))
    else:
        cuna = box(4.0, 83.0, -30, 30, -16.6, -13.6)
    for xc in (50.0 + d2, 70.0 + d2):
        cuna = cuna.fuse(box(xc - 7, xc + 7, -30, 30, -14.5, -10.0).cut(rod((xc, -31, -4), (xc, 31, -4), 18.8)))
    E.append(_pz("Cuna de las celdas", cuna.clean(), C_PETG, "esqueleto"))
    # bahia 3: avionica (en BR los rieles cuelgan solo de M3 y el modulo se mueve con M3)
    n0 = len(E)
    xr0 = 95.0 if VAR == "BR" else 87.0
    for y0 in (17.0, -21.0):
        E.append(_pz("Riel de PCB", box(xr0, 173.0, y0, y0 + 4, -17.0, -13.6), C_PETG, "esqueleto"))
        E.append(_pz("Riel de PCB", box(xr0, 173.0, y0, y0 + 4, 4.0, 8.4), C_PETG, "esqueleto"))
    E.append(_pz("PCB principal", box(98.0, 166.0, -22, 22, -13.6, -12.0), C_PCB, "equipo"))
    for b in ((116, 130, -7, 7), (140, 147, -13, -6), (150, 156, 8, 14), (104, 110, 10, 17), (158, 163, -16, -9)):
        E.append(_pz("Componente", box(b[0], b[1], b[2], b[3], -12.0, -10.6), C_NEGRO, "equipo"))
    E.append(_pz("PCB de radio y GNSS", box(116.0, 170.0, -21, 21, 8.4, 10.0), C_PCB, "equipo"))
    E.append(_pz("Modulo de radio 915 MHz", box(120.0, 136.0, 3, 19, 10.0, 12.2), C_NEGRO, "equipo"))
    E.append(_pz("Antena helicoidal 915 MHz", rod((143, 11, 10.0), (143, 11, 31.0), 6.0), (0.80, 0.62, 0.30), "equipo"))
    E.append(_pz("Modulo GNSS", box(146.0, 168.0, -20, 2, 10.0, 12.0), C_NEGRO, "equipo"))
    E.append(_pz("Antena ceramica GNSS", box(148.0, 166.0, -18, 0, 12.0, 16.0), (0.86, 0.80, 0.66), "equipo"))
    d3 = X_M3 - 173.0
    if abs(d3) > 1e-9:
        for p in E[n0:]:
            p["shape"] = p["shape"].translate(V(d3, 0, 0))
    # bahia 4: nicrom, camara de cenit
    if VAR in ("A", "B", "BR"):   # despliegue con dos micro servos de un solo uso (paracaidas y ala)
        for k_, y0 in enumerate((-12.5, 0.5)):
            E.append(_pz("Servo de liberacion " + ("del paracaidas" if k_ == 0 else "del ala"),
                         fuse(box(186.0, 202.0, y0, y0 + 11.5, 13.0, 24.5), box(183.0, 205.0, y0, y0 + 11.5, 21.0, 22.5)),
                         (0.10, 0.20, 0.55), "equipo"))
            E.append(_pz("Brazo de traba", box(190.0, 198.0, y0 + 2.0, y0 + 9.5, 24.5, 26.0), C_BLANCO, "equipo"))
    else:
        E.append(_pz("Capsula de nicrom (PTFE)", box(186.0, 202.0, -8, 8, 15, 25), C_BLANCO, "equipo"))
    cam = box(-4, 4, -10, 10, -10, 10)                    # cuerpo de la camara: eje optico +x local
    lente = disc(4, 10, 4.0)
    ang = 90.0 - 35.0                                     # eje 35 grados sobre el flanco, hacia el cenit
    for nom, sh, col in (("Camara de cenit", cam, C_NEGRO), ("Lente de cenit", lente, (0.35, 0.37, 0.42))):
        sh = sh.rotate(V(0, 0, 0), V(0, 0, 1), ang).translate(V(202.0, 28.0, 0.0))
        E.append(_pz(nom, sh, col, "equipo"))
    E.append(_pz("Soporte de la camara de cenit", box(196.0, 216.0, 16, 40, -12, -9).cut(disc(190, 220, 60).cut(
        disc(190, 220, RO - t_en(200.0) - 0.2))).fuse(box(210, 216, 20, 36, -12, 12)).clean(), C_PETG, "esqueleto"))
    # copa: paracaidas, horquilla y pasador, resorte expulsor
    if pasador:
        E.append(_pz("Horquilla del pasador", box(220.0, 228.0, -4, 4, -5, 5).cut(box(221.5, 229, -1.6, 1.6, -6, 6)),
                     C_PETG, "esqueleto"))
        E.append(_pz("Pasador de liberacion", rod((225.0, -6, 0), (225.0, 6, 0), 3.0), C_ACERO, "equipo"))
    if con_paracaidas:
        E.append(_pz("Paracaidas plegado", disc(222.5, 235.5, 27.0).cut(disc(222, 236, 7.0)), C_PARA, "paracaidas"))
        res = None
        for k in range(7):
            t = cq.Solid.makeTorus(38.5, 0.7, V(221.2 + 2.25 * k, 0, 0), V(1, 0, 0))
            res = t if res is None else res.fuse(t)
        E.append(_pz("Resorte expulsor", res, C_ACERO, "paracaidas"))
    if lazo:
        lz = [((194.0, 0, 25), (199.0, YL - 2.5, ZL - 1.5)), ((194.0, 0, 25), (199.0, -YL + 2.5, ZL - 1.5)),
              ((194.0, 0, 25), (214.0, 0, 2.0)), ((214.0, 0, 2.0), (x_pas, 0, 2.0))]
        sh = None
        for a, b in lz:
            r_ = rod(a, b, 0.9)
            sh = r_ if sh is None else sh.fuse(r_)
        E.append(_pz("Lazo de Dyneema", sh, C_DYN, "lazo"))
    # paneles solares en los flancos
    for s in (1, -1):
        p = box(PANEL_X[0] + 1, PANEL_X[1] - 1, Y_FLAT, Y_FLAT + 1.0, -14, 14)
        E.append(_pz("Panel solar", p.mirror("XZ") if s < 0 else p, C_SOLAR, "solar"))
    return E


# ------------------------------------------------------------------ fase 1: paracaidas
def paracaidas_abierto(x_conf=275.0, solo_info=False):
    """Paracaidas plano O233 con ventana O40 inflado, 8 lineas de 282 mm, destorcedor, brida de 4 ramales."""
    out = []
    D0, dv, Ls = 233.0, 40.0, 282.0
    Rs = 80.0
    phi_max = (D0 / 2) / Rs
    rp = Rs * math.sin(phi_max)
    x_sw = x_conf + 8.0
    x_skirt = x_sw + math.sqrt(Ls ** 2 - rp ** 2)
    if solo_info:
        return [], dict(x_skirt=x_skirt, x_apex=x_skirt + Rs * (1 - math.cos(phi_max)), rp=rp, x_sw=x_sw, x_conf=x_conf)
    for g in range(8):
        th = np.linspace(g * 45, (g + 1) * 45, 24)
        ph = np.linspace((dv / 2) / Rs, phi_max, 30)
        TH, PH = np.meshgrid(np.radians(th), ph, indexing="ij")
        lob = 1 + 0.06 * np.sin(np.pi * (TH - np.radians(g * 45)) / np.radians(45)) * (PH / phi_max)
        r = Rs * np.sin(PH) * lob
        X = x_skirt + Rs * (np.cos(PH) - np.cos(phi_max))
        g_ = pv.StructuredGrid(X, r * np.cos(TH), r * np.sin(TH)).extract_surface().triangulate()
        out.append(dict(nombre="Paracaidas (gajo)", mesh=g_, color=C_PARA if g % 2 == 0 else C_BLANCO, grupo="paracaidas"))
    lineas = None
    for k in range(8):
        a = math.radians(k * 45)
        r_ = rod((x_sw, 0, 0), (x_skirt, rp * math.cos(a), rp * math.sin(a)), 1.0)
        lineas = r_ if lineas is None else lineas.fuse(r_)
    out.append(_pz("Lineas de Kevlar", lineas, (0.85, 0.75, 0.35), "paracaidas"))
    out.append(_pz("Destorcedor", fuse(disc(x_conf + 2, x_sw, 2.5), cq.Solid.makeTorus(3.0, 0.8, V(x_conf, 0, 0), V(0, 1, 0))),
                   C_ACERO, "paracaidas"))
    brida = None
    for a in VAR_ANG:
        y, z = R_VAR * math.cos(math.radians(a)), R_VAR * math.sin(math.radians(a))
        r_ = rod((226.5, y, z), (x_conf - 3, 0, 0), 1.2)
        brida = r_ if brida is None else brida.fuse(r_)
    out.append(_pz("Brida de 4 ramales", brida, (0.85, 0.75, 0.35), "paracaidas"))
    out.append(_pz("Pasador de liberacion", rod((x_conf - 3, -5, 0), (x_conf - 3, 5, 0), 3.0), C_ACERO, "paracaidas"))
    return out, dict(x_skirt=x_skirt, x_apex=x_skirt + Rs * (1 - math.cos(phi_max)), rp=rp, x_sw=x_sw, x_conf=x_conf)


def paracaidas_punto(fr, th_deg, x_conf=275.0):
    _, i = paracaidas_abierto(x_conf, solo_info=True)
    Rs = 80.0
    phi_max = (233.0 / 2) / Rs
    ph = (20.0 / Rs) + fr * (phi_max - 20.0 / Rs)
    th = math.radians(th_deg)
    return (i["x_skirt"] + Rs * (math.cos(ph) - math.cos(phi_max)), Rs * math.sin(ph) * math.cos(th),
            Rs * math.sin(ph) * math.sin(th))


def vela_punto(s_sign, s, t, h=31.0):
    """Punto de la vela desplegada (para las llamadas de las figuras)."""
    d = np.array([math.cos(math.radians(FLECHA)), s_sign * math.sin(math.radians(FLECHA)), 0.0])
    P0 = np.array([14.0, s_sign * YL, ZL])
    K = np.array([QUILLA[0] + (QUILLA[1] - QUILLA[0]) * s, 0.0, RO - CANAL_P + 0.6])
    X = (1 - t) * K + t * (P0 + (L_LAR + punta(s_sign)) * s * d)
    X[2] += h * s * 4 * t * (1 - t)
    return tuple(float(v) for v in X)


def larguero_punto(s_sign, l):
    d = np.array([math.cos(math.radians(FLECHA)), s_sign * math.sin(math.radians(FLECHA)), 0.0])
    return tuple(float(v) for v in np.array([14.0, s_sign * YL, ZL]) + l * d)


# ------------------------------------------------------------------
def build(config="estibado"):
    if config == "estibado":
        return (carcasa() + cubierta() + varillas() + mamparos() + pivotes(False) + largueros(False) + equipos()
                + (tornillos_carena() if VAR in ("B", "BR") else []) + (tuercas_estaciones() if VAR == "BR" else []))
    if config == "desplegado":
        return (carcasa() + varillas() + mamparos(con_tapa=False) + pivotes(True) + largueros(True) + vela_desplegada()
                + equipos(con_paracaidas=False, lazo=False))
    if config == "fase1":
        par, par_info = paracaidas_abierto()
        return (carcasa() + cubierta() + varillas() + mamparos(con_tapa=False) + pivotes(False) + largueros(False)
                + equipos(con_paracaidas=False, pasador=False, x_pas=par_info["x_conf"] - 3) + par)
    raise ValueError(config)


if __name__ == "__main__":
    import time
    for c in ("estibado", "desplegado", "fase1"):
        t = time.time()
        ps = build(c)
        print(c, len(ps), "piezas", f"{time.time() - t:.1f} s")
