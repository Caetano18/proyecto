"""Modelo CAD parametrico del CanSat ala delta (CadQuery / OpenCascade).

Arquitectura: contenedor cilindrico d90 (pared 2 mm) + planeador de ala delta
que sale por la boca inferior.  build(config) devuelve la lista de piezas:
  "estibado"    : planeador con alas plegadas (sin contenedor)
  "lanzamiento" : planeador estibado dentro del contenedor
  "desplegado"  : planeador en vuelo, alas a 45 grados y cola extendida
  "fe"          : estructura + equipos idealizados para el modelo FEA
Cada pieza es un dict(nombre, shape, mat, color, grupo, masa[g]).
"""
import math
import cadquery as cq
from cadquery import Vector as V
import params as P

GRIS = (0.34, 0.36, 0.40)
CF = (0.13, 0.13, 0.15)
ALU = (0.75, 0.77, 0.80)
G10C = (0.55, 0.68, 0.42)
TELA = (0.95, 0.45, 0.10)
BLANCO = (0.93, 0.93, 0.90)

# ------------------------------------------------------------ primitivas


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rod(p0, p1, do, di=0.0):
    p0, p1 = V(*p0), V(*p1)
    d = p1 - p0
    s = cq.Solid.makeCylinder(do / 2, d.Length, p0, d)
    if di > 0:
        s = s.cut(cq.Solid.makeCylinder(di / 2, d.Length, p0, d))
    return s


def disc(x0, x1, r=P.RB, y=0.0, z=0.0):
    return cq.Solid.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def fuse(*shapes):
    s = shapes[0]
    for o in shapes[1:]:
        s = s.fuse(o)
    return s.clean()


def sector(x0, x1, r0, r1, ang, width):
    """Sector anular centrado en el angulo `ang` (grados, desde +y hacia +z)."""
    ring = disc(x0, x1, r1).cut(disc(x0, x1, r0))
    half = math.tan(math.radians(width / 2)) * r1
    b = box(x0, x1, 0.0, r1 + 5, -half, half)
    b = b.rotate(V(0, 0, 0), V(1, 0, 0), ang)
    return ring.intersect(b)


# -------------------------------------------------------- cuadernas


def cuaderna_extrema(tail=False, fe=False):
    """C1 (nariz) o C4 (cola): alma + aro + nervios + bujes de larguero + orejas de pivote."""
    x0, x1 = P.X_C4 if tail else P.X_C1
    full = disc(x0, x1)
    web = disc(x1 - P.WEB_T, x1) if tail else disc(x0, x0 + P.WEB_T)
    rim = full.cut(disc(x0, x1, P.RB - P.RIM_T))
    yo = P.Y_OUT
    ztop = P.Z_BOX + P.T_COVER
    parts = [web, rim]
    for s in (1, -1):
        y_in, y_out = sorted((s * (yo - P.RIB_T), s * yo))
        parts.append(box(x0, x1, y_in, y_out, -P.Z_BOX, ztop))                # nervio lateral
        y_in, y_out = sorted((s * yo, s * (P.RB + 1)))
        parts.append(box(x0, x1, y_in, y_out, -12, 12))                       # oreja de pivote
    parts.append(box(x0, x1, -yo, yo, ztop - P.RIB_T, ztop))                  # nervio superior
    parts.append(box(x0, x1, -yo, yo, -P.Z_BOX, -P.Z_BOX + P.RIB_T))          # nervio inferior
    parts.append(box(x0, x1, -yo, yo, P.Z_TRAY[0] - 1.2, P.Z_TRAY[1] + 1.2))  # asiento de bandeja
    for sy in (1, -1):
        for sz in (1, -1):
            parts.append(disc(x0, x1, P.BOSS_D / 2, sy * P.LON_Y, sz * P.LON_Z))
    if tail:
        parts.append(disc(x0, x1, 9.0))                       # buje del cerrojo de bayoneta
        parts.append(disc(x0, x1, 5.0, 0, P.Z_BOOM))          # buje del botalon de cola
    body = fuse(*parts).intersect(full)
    for sy in (1, -1):
        for sz in (1, -1):
            xa, xb = (x0, P.LON_X[1]) if tail else (P.LON_X[0], x1)
            body = body.cut(disc(xa, xb, P.LON_DO / 2, sy * P.LON_Y, sz * P.LON_Z))
        zc = P.Z_TE if tail else 0.0
        ya, yb2 = sorted((sy * 31.0, sy * 50.0))
        body = body.cut(box(x0 - 1, x1 + 1, ya, yb2, zc - 4.0, zc + 4.0))     # ranura del herraje
        if not fe:
            xp = P.X_B if tail else P.X_A
            body = body.cut(rod((xp, sy * P.Y_PIV, -12.5), (xp, sy * P.Y_PIV, 12.5), 2.5))
    if tail:
        body = body.cut(disc(x0 - 1, x1 + 1, 3.0, 0, P.Z_BOOM))                # paso del botalon
        body = body.cut(disc(x0 - 1, x1 + 1, P.KEY_HOLE / 2))                   # pasaje del eje de la llave
    return body.clean()


def cuaderna_media(x0, x1):
    """C2 / C3: marco rectangular de la caja, con aberturas de paso."""
    body = box(x0, x1, -P.Y_BOX, P.Y_BOX, -P.Z_BOX, P.Z_BOX)
    body = body.cut(box(x0 - 1, x1 + 1, -16.5, 16.5, -2.0, 24.0))
    body = body.cut(box(x0 - 1, x1 + 1, -16.5, 16.5, -24.0, -7.2))
    for sy in (1, -1):
        for sz in (1, -1):
            body = body.cut(disc(x0 - 1, x1 + 1, P.LON_DO / 2, sy * P.LON_Y, sz * P.LON_Z))
    return body.clean()


def cuna_ala(x0, x1, side):
    """Cuna que sostiene las varillas plegadas (sobre la cara exterior del panel)."""
    ya, yb = sorted((side * P.Y_OUT, side * 44.0))
    return box(x0, x1, ya, yb, -10.0, 6.0).intersect(disc(x0, x1))


def guia_botalon(x0, x1):
    zt = P.Z_BOX + P.T_COVER
    g = box(x0, x1, -6.5, 6.5, zt, 45.0).intersect(disc(x0, x1))
    return g.cut(disc(x0 - 1, x1 + 1, 3.0, 0, P.Z_BOOM))


# ------------------------------------------------------------ piezas


def piezas_estructura(fe=False):
    out = []

    def add(nombre, shape, mat, color, grupo="estructura", masa=None):
        out.append(dict(nombre=nombre, shape=shape, mat=mat, color=color, grupo=grupo, masa=masa))

    add("C1 cuaderna de nariz", cuaderna_extrema(False, fe), "PA12CF", GRIS)
    add("C2 cuaderna intermedia", cuaderna_media(*P.X_C2), "PA12CF", GRIS)
    add("C3 cuaderna intermedia", cuaderna_media(*P.X_C3), "PA12CF", GRIS)
    add("C4 cuaderna de cola", cuaderna_extrema(True, fe), "PA12CF", GRIS)
    k = 1
    for sy in (1, -1):
        for sz in (1, -1):
            add(f"L{k} larguero", rod((P.LON_X[0], sy * P.LON_Y, sz * P.LON_Z),
                                      (P.LON_X[1], sy * P.LON_Y, sz * P.LON_Z), P.LON_DO, P.LON_DI), "CFRP", CF)
            k += 1
    xa, xb = P.X_C1[1], P.X_C4[0]
    add("P1 panel lateral der.", box(xa, xb, P.Y_BOX, P.Y_OUT, -P.Z_BOX, P.Z_BOX), "G10", G10C)
    add("P2 panel lateral izq.", box(xa, xb, -P.Y_OUT, -P.Y_BOX, -P.Z_BOX, P.Z_BOX), "G10", G10C)
    add("P3 tapa superior", box(xa, xb, -P.Y_OUT, P.Y_OUT, P.Z_BOX, P.Z_BOX + P.T_COVER), "G10", G10C)
    add("B1 bandeja de avionica", box(xa, xb, -P.Y_BOX, P.Y_BOX, *P.Z_TRAY), "G10", (0.62, 0.74, 0.48))
    for k, x in ((2, P.X_C2), (3, P.X_C3)):
        add(f"Guia de botalon C{k}", guia_botalon(*x), "PA12CF", GRIS)
        for s, tag in ((1, "der."), (-1, "izq.")):
            add(f"Cuna de ala C{k} {tag}", cuna_ala(x[0], x[1], s), "PA12CF", GRIS)
    return out


def piezas_equipo(fe=False):
    """Equipos montados sobre la bandeja.  Masas = asignaciones de params.M_EQ."""
    out = []
    M = P.M_EQ
    zt0, zt1 = P.Z_TRAY

    def add(nombre, shape, mat, color, masa, grupo="equipo"):
        out.append(dict(nombre=nombre, shape=shape, mat=mat, color=color, grupo=grupo, masa=masa))

    bat = rod((68, 0, 6.5), (133, 0, 6.5), 18.5)
    sillas = fuse(box(72, 80, -8, 8, zt1, 2.0), box(121, 129, -8, 8, zt1, 2.0)).cut(bat)
    add("Bateria 18650", bat, "EQ_BAT", (0.15, 0.35, 0.75), M["bateria"])
    add("Sillas de bateria", sillas, "PA12CF", (0.85, 0.85, 0.85), M["porta_bateria"])
    add("PCB principal", box(69, 133, -25, 25, -14.6, -13.0), "EQ_PCB", (0.05, 0.40, 0.20), M["pcb_principal"])
    sep = fuse(*[rod((x, y, -13.0), (x, y, zt0), 5.0) for x in (73, 129) for y in (-21, 21)])
    add("Separadores PCB principal", sep, "PA12CF", (0.80, 0.70, 0.30), 1.2)
    add("PCB radio/GNSS", box(147, 193, -20, 20, 4.0, 5.6), "EQ_PCB", (0.05, 0.40, 0.20), M["pcb_radio"])
    sep2 = fuse(*[rod((x, y, zt1), (x, y, 4.0), 5.0) for x in (151, 189) for y in (-16, 16)])
    add("Separadores PCB radio", sep2, "PA12CF", (0.80, 0.70, 0.30), 1.0)
    add("Servo de cola", box(12, 35, -6, 6, -27, zt0), "EQ_BLK", (0.10, 0.10, 0.10), M["servo_cola"])
    add("Servo del cerrojo", box(165, 188, -6, 6, -27, zt0), "EQ_BLK", (0.10, 0.10, 0.10), M["servo_lib"])
    add("Lastre de centrado (asignacion)", box(12, 54, -22, 22, 0.0, 14.0), "EQ_BLK", (0.85, 0.45, 0.10), None)
    sep3 = fuse(*[rod((x, y, zt1), (x, y, 0.0), 6.0) for x in (15.5, 50.5) for y in (-18.5, 18.5)])
    add("Separadores del lastre", sep3, "PA12CF", (0.80, 0.70, 0.30), 0.8)
    if fe:
        # ala estibada: su masa se reparte en los cuatro apoyos reales (pivotes A y B, cunas C2 y C3)
        for s_, tag in ((1, "der."), (-1, "izq.")):
            ya, yb = sorted((s_ * P.Y_OUT, s_ * 41.0))
            m = M["ala_por_lado"]
            add(f"Ala estibada: apoyo A {tag}", box(8, 14, ya, yb, -5, 5), "EQ_BLK", (0.9, 0.2, 0.2), m * 0.30)
            add(f"Ala estibada: apoyo B {tag}", box(P.X_C4[0] - 6, P.X_C4[0], ya, yb, -12, -2), "EQ_BLK",
                (0.9, 0.2, 0.2), m * 0.22)
        add("Botalon de cola (estibado)", rod((P.X_C2[0], 0, P.Z_BOOM), (P.X_C4[1], 0, P.Z_BOOM), 6.0),
            "EQ_BOOM", CF, M["cola"])
    return out


def _ala(side, desplegada):
    """Piezas de un ala (side = +1 derecha, -1 izquierda)."""
    out = []
    s = side

    def add(nombre, shape, mat, color):
        out.append(dict(nombre=nombre, shape=shape, mat=mat, color=color, grupo="ala", masa=None))

    A = (P.X_A, s * P.Y_PIV, 0.0)
    B = (P.X_B, s * P.Y_PIV, P.Z_TE)
    if desplegada:
        T = (P.X_B, s * (P.Y_PIV + P.D_AB), 0.0)
        J = ((A[0] + T[0]) / 2, (A[1] + T[1]) / 2, 0.0)
        add("Varilla BA tramo interior", rod(A, J, P.LE_DO, P.LE_DI), "CFRP", CF)
        add("Varilla BA tramo exterior", rod(J, T, P.LE_DO, P.LE_DI), "CFRP", CF)
        u = (V(*T) - V(*A)).normalized()
        j0 = V(*J) - u * (P.SLV_L / 2)
        add("Manguito de traba", rod(j0.toTuple(), (j0 + u * P.SLV_L).toTuple(), P.SLV_DO, P.SLV_DI), "AL7075", ALU)
        add("Tirante de borde de fuga", rod(B, (T[0], T[1], P.Z_TE), P.TE_DO, P.TE_DI), "CFRP", CF)
        add("Herraje de punta T", rod((T[0], T[1], P.Z_TE - 2.5), (T[0], T[1], 3.5), 5.6), "AL7075", ALU)
        pts = [(P.X_A, s * P.Y_ROOT), (P.X_A, s * P.Y_PIV), (P.X_B, s * (P.Y_PIV + P.D_AB)), (P.X_B, s * P.Y_ROOT)]
        memb = cq.Workplane("XY").workplane(offset=2.6).polyline(pts).close().extrude(0.25).val()
        add("Membrana (ripstop)", memb, "RIPSTOP", TELA)
    else:
        Jx = P.X_A + P.L_SEG
        yo = s * (P.Y_PIV + P.FOLD_OFF)
        add("Varilla BA tramo interior", rod(A, (Jx, A[1], 0), P.LE_DO, P.LE_DI), "CFRP", CF)
        add("Varilla BA tramo exterior", rod((Jx, yo, 0), (P.X_A, yo, 0), P.LE_DO, P.LE_DI), "CFRP", CF)
        add("Manguito de traba", rod((Jx - 6 - P.SLV_L, A[1], 0), (Jx - 6, A[1], 0), P.SLV_DO, P.SLV_DI), "AL7075", ALU)
        add("Tirante de borde de fuga", rod(B, (P.X_A, yo, P.Z_TE), P.TE_DO, P.TE_DI), "CFRP", CF)
        add("Herraje de punta T", rod((P.X_A, yo, P.Z_TE - 2.5), (P.X_A, yo, 3.5), 5.6), "AL7075", ALU)
        ya, yb = sorted((s * 28.0, s * 31.2))
        add("Membrana plegada", box(14, 190, ya, yb, 2.2, 9.0), "RIPSTOP", TELA)
    add("Herraje de apice A", rod((A[0], A[1], -3.2), (A[0], A[1], 3.2), 6.0), "AL7075", ALU)
    add("Herraje de cola B", rod((B[0], B[1], B[2] - 3.2), (B[0], B[1], B[2] + 3.2), 6.0), "AL7075", ALU)
    add("Varilla de raiz", rod((10, s * P.Y_ROOT, 0), (P.L_G - 10, s * P.Y_ROOT, 0), P.RR_DO, P.RR_DI), "CFRP", CF)
    return out


def piezas_cola(desplegada):
    out = []
    if desplegada:
        out.append(dict(nombre="Botalon de cola", shape=rod((140, 0, P.Z_BOOM), (336, 0, P.Z_BOOM), 6.0, 4.0),
                        mat="CFRP", color=CF, grupo="cola", masa=None))
        for s in (1, -1):
            pts = [(288, 0), (336, 0), (336, 85), (306, 85)]
            pl = cq.Workplane("XY").polyline(pts).close().extrude(0.8).val()
            pl = pl.rotate(V(0, 0, 0), V(1, 0, 0), 35.0)
            if s < 0:
                pl = pl.mirror("XZ")
            pl = pl.translate(V(0, 0, P.Z_BOOM))
            out.append(dict(nombre="Cola en V (ref.)", shape=pl, mat="RIPSTOP", color=TELA, grupo="cola", masa=None))
    else:
        out.append(dict(nombre="Botalon de cola", shape=rod((10, 0, P.Z_BOOM), (P.L_G - 1, 0, P.Z_BOOM), 6.0, 4.0),
                        mat="CFRP", color=CF, grupo="cola", masa=None))
    return out


def piezas_cerrojo(fe=False):
    """Llave de bayoneta: eje pasante con arandela interior en C4, aislador elastomerico y plato de apoyo en la tapa."""
    out = []
    acero = (0.8, 0.8, 0.82)
    xa = P.X_C4[0] - P.WASH_T                       # arandela interior (cara interna de C4)
    xf = P.CT_TOP[0] + P.CT_CAP_FLOOR               # fondo del cubo de la tapa
    xi = xf + P.ISO_T                               # cara superior del aislador
    xpl = xi + P.WASH_T                             # cara superior del plato de apoyo
    eje = rod((xa, 0, 0), (xpl + (0.0 if fe else 3.2), 0, 0), P.KEY_D)
    arandela = disc(xa, P.X_C4[0], P.WASH_D / 2)
    plato = disc(xi, xpl, P.WASH_D / 2)
    aislador = disc(xf, xi, P.WASH_D / 2).cut(disc(xf - 1, xi + 1, P.KEY_HOLE / 2))
    if fe:
        llave = fuse(eje, arandela, plato)
    else:
        plato = plato.cut(disc(xi - 1, xpl + 1, 2.8)).cut(box(xi - 1, xpl + 1, -1.8, 1.8, -7.4, 7.4))
        aislador = aislador.cut(box(xf - 1, xi + 1, -1.8, 1.8, -7.6, 7.6))
        llave = fuse(eje, arandela, rod((xpl + 1.6, 0, -7), (xpl + 1.6, 0, 7), 3.0))
        out.append(dict(nombre="Plato de apoyo", shape=plato, mat="A2-70", color=acero, grupo="mecanismo", masa=None))
    out.append(dict(nombre="Llave de bayoneta", shape=llave, mat="A2-70", color=acero, grupo="mecanismo", masa=None))
    out.append(dict(nombre="Aislador elastomerico", shape=aislador, mat="ELAST_X" if fe else "ELAST",
                    color=(0.15, 0.15, 0.6), grupo="mecanismo", masa=aislador.Volume() * 1.2e-3))
    return out


def tapa_contenedor(fe=False):
    """Tapa estructural: placa + faldon + 6 nervios radiales + cubo central con asiento del aislador (PA12-CF)."""
    x0, xp = P.CT_TOP
    x1 = x0 + P.CT_CAP_H
    placa = disc(x0, xp, P.CT_RI)
    faldon = disc(x0, x1, P.CT_RI).cut(disc(x0 - 1, x1 + 1, P.CT_RI - P.CT_CAP_SKIRT))
    cubo = disc(x0, x1, P.CT_CAP_BOSS).cut(disc(x0 + P.CT_CAP_FLOOR, x1 + 1, P.WASH_D / 2 + 0.6))
    partes = [placa, faldon, cubo]
    for ang in P.CT_RIB_ANG:
        n = box(xp - 0.5, x1, P.CT_CAP_BOSS - 1, P.CT_RI - 1, -P.CT_CAP_RIB / 2, P.CT_CAP_RIB / 2)
        partes.append(n.rotate(V(0, 0, 0), V(1, 0, 0), ang))
    tapa = fuse(*partes).intersect(disc(x0, x1, P.CT_RI))
    tapa = tapa.cut(disc(x0 - 1, x1 + 1, P.KEY_HOLE / 2))                              # pasaje del eje
    if not fe:
        tapa = tapa.cut(box(x0 - 1, x1 + 1, -1.8, 1.8, -7.6, 7.6))                    # ojo de cerradura
        for ang in P.CT_BRIDA_ANG:                                                     # anclajes de la brida
            a = math.radians(ang)
            t = V(0, -math.sin(a), math.cos(a))
            c0 = V(x1 - 3.5, P.R_BRIDA * math.cos(a), P.R_BRIDA * math.sin(a))
            tapa = tapa.cut(rod((c0 - t * 4).toTuple(), (c0 + t * 4).toTuple(), 3.0))
    return tapa.clean()


def piezas_contenedor(fe=False):
    out = []
    x0, x1 = P.CT_X
    tubo = disc(x0, x1, P.CT_RO).cut(disc(x0 - 1, x1 + 1, P.CT_RI))
    if not fe:
        tubo = tubo.cut(rod((175, 0, -40), (175, 0, -48), 8.0))     # interruptor (E4, E5)
        tubo = tubo.cut(rod((185, 0, -40), (185, 0, -48), 5.0))     # indicador LED (E6)
    out.append(dict(nombre="CT1 tubo del contenedor", shape=tubo, mat="LWPLA", color=BLANCO, grupo="contenedor",
                    masa=None))
    out.append(dict(nombre="CT2 tapa nervada", shape=tapa_contenedor(fe), mat="PA12CF", color=GRIS,
                    grupo="contenedor", masa=None))
    xc = P.CT_TOP[0] + P.CT_CAP_H
    if not fe:      # en el modelo FEA la masa del paracaidas se suma a la densidad de la tapa
        out.append(dict(nombre="Paracaidas plegado", shape=disc(xc + 2.5, P.CT_X[1] - 1.5, 36.0), mat="EQ_SOFT",
                        color=(0.9, 0.2, 0.2), grupo="contenedor",
                        masa=P.M_EQ["paracaidas"] + P.M_EQ["brida_herrajes"]))
    return out


def piezas_patines(fe=False):
    out = []
    for xr, tag in ((P.X_C1, "C1"), (P.X_C4, "C4")):
        for ang in P.PAD_POS:
            sh = sector(xr[0], xr[1], P.RB, P.CT_RI, ang, P.PAD_ANG)
            mat = "PAD_A" if ang in (45.0, 225.0) else "PAD_B"
            out.append(dict(nombre=f"Patin {tag} {int(ang)}", shape=sh, mat=mat if fe else "ELAST",
                            color=(0.95, 0.95, 0.6), grupo="mecanismo", masa=0.11))
    return out


def cubierta_inferior():
    sh = box(P.X_C1[1], P.X_C4[0], -P.Y_OUT, P.Y_OUT, -P.Z_BOX - 0.25, -P.Z_BOX)
    return [dict(nombre="Cubierta inferior (PC 0,25)", shape=sh, mat="PC", color=(0.75, 0.85, 0.95),
                 grupo="carenado", masa=P.M_EQ["cubierta_inf"])]


def build(config="estibado"):
    fe = config == "fe"
    parts = piezas_estructura(fe) + piezas_equipo(fe) + piezas_patines(fe)
    if fe:
        parts += piezas_cerrojo(True) + piezas_contenedor(True)
    else:
        desp = config == "desplegado"
        parts += _ala(1, desp) + _ala(-1, desp) + piezas_cola(desp) + cubierta_inferior() + piezas_cerrojo(False)
        if config == "lanzamiento":
            parts += piezas_contenedor(False)
    for p in parts:
        p["vol"] = p["shape"].Volume()
        if p["masa"] is None and p["mat"] in P.MAT and "rho" in P.MAT[p["mat"]]:
            p["masa"] = p["vol"] * P.MAT[p["mat"]]["rho"] / 1000.0
    return parts


def masa_grupo(parts, grupo):
    return sum(p["masa"] or 0.0 for p in parts if p["grupo"] == grupo)


def export_step(parts, path):
    asm = cq.Assembly(name="cansat")
    names = {}
    for p in parts:
        n = p["nombre"].replace(" ", "_").replace("/", "-").replace(".", "").replace(",", "_")
        names[n] = names.get(n, 0) + 1
        if names[n] > 1:
            n = f"{n}_{names[n]}"
        asm.add(p["shape"], name=n, color=cq.Color(*p["color"]))
    asm.save(path)


if __name__ == "__main__":
    for cfg in ("lanzamiento", "desplegado", "fe"):
        ps = build(cfg)
        print(f"--- {cfg}: {len(ps)} piezas")
        if cfg == "lanzamiento":
            for p in ps:
                m = p["masa"]
                print(f"  {p['nombre']:<34s} {p['mat']:<8s} {p['grupo']:<11s} V={p['vol']:9.0f}  m={m if m is None else round(m, 2)}")
            for g in ("estructura", "contenedor", "equipo", "ala", "cola", "mecanismo"):
                print(f"  masa {g}: {masa_grupo(ps, g):.1f} g")
