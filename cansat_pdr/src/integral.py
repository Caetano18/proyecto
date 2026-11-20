"""Diseno combinado (rev. E): cuerpo integral del documento v2 del equipo + verificacion de la rev. D.

Modelo de elementos finitos del CanSat integral (todo baja junto; vela Rogallo plegada contra la carcasa):
  carcasa O90 x 240 con dos ranuras pasantes para los largueros del ala, 5 mamparos (PETG, 40 % de relleno),
  4 varillas roscadas M3 (o tubos de carbono) pasantes, masas de equipos repartidas en los mamparos y la carcasa.
Uso:  python3 integral.py <carpeta> <tag> [carcasa=PETG|HIB] [largueros=M3|CF6] [nmodos] [escala] [pasos=modal|modal,estat]
Las coordenadas siguen el resto del proyecto: x = eje (x = -2 apoyo inferior, nadir), CT_X[0] = -2.
"""
import os
import sys
import re
import json
import time
import numpy as np
import params as P
import cad
import fe_model as F

X0, X1 = P.CT_X[0], P.CT_X[0] + 240.0          # carcasa de 240 mm (S3), apoyo en x = -2
RO = 45.0
RANURA_X = (14.0, 206.0)                         # canales de los largueros del ala (192 mm, documento v2)
RANURA_ANG = (35.0, 145.0)                       # pivotes de la quilla a y = +-35 mm sobre el lomo
RANURA_ANCHO = 6.0
MAMPAROS = (("M1 fondo nadir (ventana O14)", X0, X0 + 4.0), ("M2 mamparo puente", 83.0, 87.0),
            ("M3 mamparo de avionica", 173.0, 177.0), ("M4 mamparo cenit", 216.0, 220.0),
            ("M5 tapa de la copa del paracaidas", X1 - 4.0, X1))
R_VAR = 33.0
VAR_ANG = (45.0, 135.0, 225.0, 315.0)

# masas no estructurales [g] (documento v2) y donde se apoyan
NSM = {
    "M1": {"baliza": 15.0, "camara nadir": 11.5, "medio pack 18650": 46.0, "cableado": 4.0},
    "M2": {"medio pack 18650": 46.0, "media avionica": 27.25, "pivotes y resortes del ala": 13.0, "cableado": 4.0},
    "M3": {"media avionica": 27.25, "cableado": 4.0},
    "M4": {"camara cenit": 11.5, "capsula de nicrom": 0.0, "cableado": 4.0},
    "M5": {"paracaidas y lineas": 8.0, "cableado": 4.0},
    "carcasa": {"vela Rogallo plegada": 11.5, "largueros de carbono del ala": 11.0, "paneles solares": 9.0},
}
LASTRE_EN = ("M1", "M2")        # arandelas de ajuste sobre las varillas (documento v2)


def materiales():
    M = P.MAT
    M.setdefault("PETG40", dict(nombre="PETG impreso, 40 % de relleno", rho=0.57, E=0.9e3, nu=0.38, Sut=20.0, Sut_z=11.0,
                                FS=2.0))
    M.setdefault("AL6061", dict(nombre="Aluminio 6061-T6", rho=2.70, E=68.9e3, nu=0.33, Sy=240.0, Sut=310.0, FS=1.25))


def carcasa(tipo):
    """Lista de (nombre, forma, material)."""
    out = []
    corte = None
    for a in RANURA_ANG:
        w = np.degrees(RANURA_ANCHO / RO)
        s = cad.sector(RANURA_X[0], RANURA_X[1], RO - 8.0, RO + 1.0, a, w)
        corte = s if corte is None else corte.fuse(s)
    if tipo == "PETG":
        t = 2.0
        sh = cad.disc(X0, X1, RO).cut(cad.disc(X0 - 1, X1 + 1, RO - t)).cut(corte)
        out.append(("CT1 carcasa PETG 2 mm", sh, "PETG", RO - t))
    else:      # hibrida (rev. D): carbono abajo, vidrio arriba
        ti, ts, xh = P.CT_T_INF, P.CT_T, P.CT_X_H
        inf = cad.disc(X0, xh, RO).cut(cad.disc(X0 - 1, xh + 1, RO - ti)).cut(corte)
        sup = cad.disc(xh, X1, RO).cut(cad.disc(xh - 1, X1 + 1, RO - ts)).cut(corte)
        out.append(("CT1a carcasa carbono", inf, "GFRP_INF", RO - ti))
        out.append(("CT1b carcasa vidrio", sup, "GFRP", RO - ts))
    return out


def piezas(tipo_carcasa="PETG", largueros="M3"):
    materiales()
    parts = []
    for nombre, sh, mat, ri in carcasa(tipo_carcasa):
        parts.append(dict(nombre=nombre, shape=sh, mat=mat, color=(0.9, 0.9, 0.9), grupo="contenedor"))
    varillas = []
    for a in VAR_ANG:
        y, z = R_VAR * np.cos(np.radians(a)), R_VAR * np.sin(np.radians(a))
        if largueros == "M3":
            v = cad.disc(X0, X1, 2.53 / 2, y, z)
            mat = "AL6061"
        else:     # tubo de carbono pultruido O6/4
            v = cad.disc(X0, X1, 3.0, y, z).cut(cad.disc(X0 - 1, X1 + 1, 2.0, y, z))
            mat = "CFRP"
        varillas.append((v, mat))
    for nombre, x0, x1 in MAMPAROS:
        if tipo_carcasa == "PETG":
            ri = RO - 2.0
        else:                                            # el mamparo toca la pared del tramo en que esta
            ri = RO - (P.CT_T_INF if x1 <= P.CT_X_H else P.CT_T)
        sh = cad.disc(x0, x1, ri)
        if nombre.startswith("M1"):
            sh = sh.cut(cad.disc(x0 - 1, x1 + 1, 7.0, 0.0, -20.0))          # ventana de nadir O14
        for v, _ in varillas:
            sh = sh.cut(v)
        parts.append(dict(nombre=nombre, shape=sh.clean(), mat="PETG40", color=(0.4, 0.4, 0.45), grupo="estructura"))
    for k, (v, mat) in enumerate(varillas):
        parts.append(dict(nombre=f"Varilla {k + 1} ({'M3 Al' if mat == 'AL6061' else 'CF O6/4'})", shape=v, mat=mat,
                          color=(0.2, 0.2, 0.2), grupo="estructura", h=1.3 if mat == "AL6061" else 1.5))
    # masas
    for p in parts:
        p["vol"] = p["shape"].Volume()
        p["masa"] = p["vol"] * P.MAT[p["mat"]]["rho"] / 1000.0
        if "Varilla" in p["nombre"] and p["mat"] == "AL6061":
            p["masa"] += 1.2                                   # tuercas nyloc y arandelas
    def por_clave(c):
        return [p for p in parts if p["nombre"].startswith(c) or (c == "carcasa" and p["nombre"].startswith("CT1"))]
    for c, d in NSM.items():
        ps = por_clave(c)
        vt = sum(p["vol"] for p in ps)
        for p in ps:
            p["masa"] += sum(d.values()) * p["vol"] / vt
    tot = sum(p["masa"] for p in parts)
    lastre = P.M_TOT - tot
    if lastre > 0:
        for c in LASTRE_EN:
            for p in por_clave(c):
                p["masa"] += lastre / len(LASTRE_EN)
    for p in parts:
        p["rho"] = p["masa"] / p["vol"] * 1e-6
    return parts, lastre, tot


def resumen_modal(dat):
    """[(f [Hz], masa efectiva [t] en x, y, z)] de la salida de CalculiX."""
    import re as _re
    txt = open(dat).read()
    blk = _re.search(r"E I G E N V A L U E   O U T P U T(.*?)P A R T I C I P A T I O N", txt, _re.S).group(1)
    fr = [float(m.group(1)) for m in _re.finditer(r"^\s+\d+\s+\S+\s+\S+\s+(\S+)\s+\S+\s*$", blk, _re.M)]
    em = _re.search(r"E F F E C T I V E   M O D A L   M A S S.*?MODE NO\..*?\n(.*?)\nTOTAL", txt, _re.S).group(1)
    rows = [[float(x) for x in l.split()[1:4]] for l in em.splitlines() if l.strip()]
    return list(zip(fr, rows))


def main(wd, tag, carc="PETG", larg="M3", nmodos=8, escala=2.4, pasos="modal"):
    os.makedirs(wd, exist_ok=True)
    t0 = time.time()
    parts, lastre, tot = piezas(carc, larg)
    parts = F.quitar_solapes(parts)
    h0 = F.h_de
    F.h_de = lambda p, e=1.0: (p["h"] * e) if "h" in p else h0(p, e)
    xyz, els, ep = F.mallar(parts, wd, escala)
    F.h_de = h0
    masa_modelo = sum(p["masa"] for p in parts)
    print(f"[{tag}] carcasa {carc}, largueros {larg}: {len(xyz)} nodos, masa sin lastre {tot:.1f} g, lastre {lastre:.1f} g, "
          f"modelo {masa_modelo:.1f} g ({time.time() - t0:.0f} s)")
    np.savez_compressed(os.path.join(wd, f"malla_{tag}.npz"), xyz=xyz, els=els, epart=ep)
    json.dump([dict(nombre=p["nombre"], mat=p["mat"], masa=p["masa"], vol=p["vol"]) for p in parts],
              open(os.path.join(wd, f"partes_{tag}.json"), "w"), indent=1)
    base = F.nodos_base(xyz)
    out = dict(tag=tag, carcasa=carc, largueros=larg, masa_sin_lastre=tot, lastre=lastre,
               masas={p["nombre"]: p["masa"] for p in parts})
    if "modal" in pasos:
        F.escribir_inp(os.path.join(wd, f"modal_{tag}.inp"), xyz, els, ep, parts, "modal", [(base, 1, 3)], nmodos)
        F.correr_ccx(f"modal_{tag}", wd)
        filas = resumen_modal(os.path.join(wd, f"modal_{tag}.dat"))
        mt = masa_modelo / 1e6
        out["modos"] = [dict(f=f, meff_frac=[c_ / mt for c_ in c]) for f, c in filas]
        txt = "  ".join(f"{f:.0f} Hz({'xyz'[int(np.argmax(c))]} {100 * max(c) / mt:.0f}%)" for f, c in filas)
        print(f"[{tag}] RESULTADO {txt}")
    if "estat" in pasos:
        F.escribir_inp(os.path.join(wd, f"estat_{tag}.inp"), xyz, els, ep, parts, "estat3", [(base, 1, 3)])
        F.correr_ccx(f"estat_{tag}", wd)
    json.dump(out, open(os.path.join(wd, f"resumen_{tag}.json"), "w"), indent=1)
    print(f"[{tag}] total {time.time() - t0:.0f} s")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], *(a[3:5]), *(int(x) for x in a[5:6]), *(float(x) for x in a[6:7]), *(a[7:8]))
