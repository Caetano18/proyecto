"""Prueba de caida (Prueba 1 de la competencia): el CanSat cuelga de la brida y la cuerda de 61 cm lo frena de golpe
(unos 30 G).  Diseno v2 del equipo, sus dos opciones de estructura:
  A: monocasco de PETG 2 mm impreso, mamparos pegados a la carcasa; la brida va a 4 cancamos M3 roscados en M4.
  B: esqueleto de 4 varillas M3 de Al 6061 + mamparos + carena de PETG 2 mm; la brida va a los extremos de las varillas.
Modelo: los anclajes de la brida fijos y la inercia de 1 G hacia nadir (-x).  Se calcula el modal con ese apoyo (modo
axial, para el factor dinamico del pulso) y el estatico de 1 G.  El post-proceso (caida_post.py) escala a la rotura.
Uso: python3 caida.py <carpeta> <A|B> [escala de malla]
"""
import os
import sys
import json
import time
import math
import numpy as np
import params as P
import cad
import fe_model as F
import integral as I

X0 = I.X0                    # -2 (fondo de nadir)
X_ANC = 226.0                # extremo de las varillas / cancamos (anclaje de la brida)
T = 2.0                      # pared de PETG
G_ADH = 1.0                  # espesor del cordon de adhesivo en el modelo
MAMP = [m for m in I.MAMPAROS if not m[0].startswith("M5")]      # en la caida la tapa ya salio con el paracaidas


def materiales():
    I.materiales()
    M = P.MAT
    # adhesivo estructural sobre PETG (epoxi o cianoacrilato): la pega sobre PETG es la que limita, no el adhesivo
    M.setdefault("ADH", dict(nombre="Adhesivo (epoxi) sobre PETG", rho=1.2, E=2000.0, nu=0.38, Sut=30.0, tau=4.0, FS=2.0))


def piezas(var):
    materiales()
    parts = []
    for nombre, sh, mat, ri in I.carcasa("PETG"):
        nombre = "CT1 " + ("monocasco PETG 2 mm" if var == "A" else "carena PETG 2 mm")
        parts.append(dict(nombre=nombre, shape=sh, mat="PETG", grupo="contenedor", h=1.5))
    ejes = [(I.R_VAR * math.cos(math.radians(a)), I.R_VAR * math.sin(math.radians(a))) for a in I.VAR_ANG]
    for nombre, x0, x1 in MAMP:
        r = I.RO - T - (G_ADH if var == "A" else 0.0)
        sh = cad.disc(x0, x1, r)
        if nombre.startswith("M1"):
            sh = sh.cut(cad.disc(x0 - 1, x1 + 1, 7.0, 0.0, -20.0))
        if var == "B" or nombre.startswith("M4"):
            for y, z in ejes:
                sh = sh.cut(cad.disc(x0 - 1, x1 + 1, 1.265 if var == "B" else 1.5, y, z))
        parts.append(dict(nombre=nombre, shape=sh.clean(), mat="PETG40", grupo="estructura", h=1.25))
        if var == "A":
            ra = I.RO - T
            cord = cad.disc(x0, x1, ra).cut(cad.disc(x0 - 1, x1 + 1, r))
            parts.append(dict(nombre=f"Adhesivo {nombre[:2]}", shape=cord, mat="ADH", grupo="estructura", h=G_ADH))
    for k, (y, z) in enumerate(ejes):
        if var == "B":
            v = cad.disc(X0, X_ANC, 2.53 / 2, y, z)
            parts.append(dict(nombre=f"Varilla {k + 1} (M3 Al)", shape=v, mat="AL6061", grupo="estructura", h=0.55))
        else:
            v = cad.disc(I.MAMPAROS[3][1] - 3.4, X_ANC, 1.5, y, z).fuse(
                cad.disc(I.MAMPAROS[3][1] - 3.4, I.MAMPAROS[3][1], 2.75, y, z)).clean()
            parts.append(dict(nombre=f"Cancamo {k + 1} (M3 A2-70)", shape=v, mat="A2-70", grupo="estructura", h=0.55))
    for p in parts:
        p["vol"] = p["shape"].Volume()
        p["masa"] = p["vol"] * P.MAT[p["mat"]]["rho"] / 1000.0
    nsm = {k: dict(v) for k, v in I.NSM.items() if k != "M5"}
    nsm["M4"]["cableado de la copa"] = 4.0                        # el paracaidas (8 g) ya no esta en el cuerpo
    for c, d in nsm.items():
        ps = [p for p in parts if p["nombre"].startswith(c) or (c == "carcasa" and p["nombre"].startswith("CT1"))]
        vt = sum(p["vol"] for p in ps)
        for p in ps:
            p["masa"] += sum(d.values()) * p["vol"] / vt
    tot = sum(p["masa"] for p in parts)
    for p in parts:
        p["rho"] = p["masa"] / p["vol"] * 1e-6
    return parts, tot


def nodos_anclaje(xyz):
    sel = np.zeros(len(xyz), bool)
    for a in I.VAR_ANG:
        y, z = I.R_VAR * math.cos(math.radians(a)), I.R_VAR * math.sin(math.radians(a))
        sel |= (np.abs(xyz[:, 0] - X_ANC) < 1e-3) & (np.hypot(xyz[:, 1] - y, xyz[:, 2] - z) < 1.6)
    return np.where(sel)[0]


def main(wd, var, escala=1.6):
    os.makedirs(wd, exist_ok=True)
    t0 = time.time()
    tag = var
    parts, tot = piezas(var)
    parts = F.quitar_solapes(parts)
    h0 = F.h_de
    F.h_de = lambda p, e=1.0: (p["h"] * e) if "h" in p else h0(p, e)
    xyz, els, ep = F.mallar(parts, wd, escala)
    F.h_de = h0
    anc = nodos_anclaje(xyz)
    print(f"[{tag}] {len(xyz)} nodos, {len(els)} tetraedros, masa {tot:.1f} g, {len(anc)} nodos de anclaje "
          f"({time.time() - t0:.0f} s)", flush=True)
    np.savez_compressed(os.path.join(wd, f"malla_{tag}.npz"), xyz=xyz, els=els, epart=ep)
    json.dump([dict(nombre=p["nombre"], mat=p["mat"], masa=p["masa"], vol=p["vol"]) for p in parts],
              open(os.path.join(wd, f"partes_{tag}.json"), "w"), indent=1)
    F.escribir_inp(os.path.join(wd, f"modal_{tag}.inp"), xyz, els, ep, parts, "modal", [(anc, 1, 3)], 8)
    F.correr_ccx(f"modal_{tag}", wd)
    filas = I.resumen_modal(os.path.join(wd, f"modal_{tag}.dat"))
    mt = tot / 1e6
    print(f"[{tag}] modos: " + "  ".join(f"{f:.0f} Hz ({'xyz'[int(np.argmax(c))]} {100 * max(c) / mt:.0f} %)"
                                          for f, c in filas), flush=True)
    F.escribir_inp(os.path.join(wd, f"estat_{tag}.inp"), xyz, els, ep, parts, "estat1", [(anc, 1, 3)])
    F.correr_ccx(f"estat_{tag}", wd)
    json.dump(dict(var=var, masa=tot, modos=[dict(f=f, meff=c) for f, c in filas], n_anc=int(len(anc))),
              open(os.path.join(wd, f"resumen_{tag}.json"), "w"), indent=1)
    print(f"[{tag}] total {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *(float(x) for x in sys.argv[3:4]))
