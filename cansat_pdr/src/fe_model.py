"""Modelo de elementos finitos de la configuracion de lanzamiento.

CadQuery -> Gmsh (tetraedros cuadraticos C3D10, malla conforme) -> CalculiX.
Corridas:
  modal   : *FREQUENCY con la base (borde inferior del contenedor) empotrada
  estat   : *STATIC, 1 g en -x, -y, -z (correccion estatica / casi-estatico)
  parac   : *STATIC, 1 g en -x colgado de los 3 anclajes de la brida
Salida: malla.npz (nodos, elementos, materiales) + .frd / .dat de CalculiX.
"""
import os, sys, json, subprocess, time, math
import numpy as np
import gmsh
import params as P
import cad

G_MM = P.G0 * 1000.0          # mm/s2

# tamano de elemento por pieza [mm]
def h_de(p, escala=1.0):
    n, m = p["nombre"], p["mat"]
    if m == "CFRP":
        h = 1.7
    elif m == "G10":
        h = 1.8          # rev. B: laminas de 0,5 mm con relacion de aspecto <= 4 (antes 2,6: aspecto ~7)
    elif n.startswith("Patin") or n.startswith("Aislador"):
        h = 1.4
    elif n.startswith("Manguito"):
        h = 1.1
    elif n.startswith("CT"):
        h = 4.2
    elif m == "EQ_PCB":
        h = 3.0
    elif m in ("EQ_BLK", "EQ_BAT", "EQ_SOFT"):
        h = 6.0
    elif m == "A2-70":
        h = 1.8
    else:
        h = 2.4
    return h * escala


def elastico(mat):
    """Devuelve (tipo, constantes) para CalculiX y la matriz D 6x6 global (Voigt xx,yy,zz,xy,yz,zx)."""
    M = P.MAT
    if mat == "CFRP":
        c = M["CFRP"]
        return "ortho", dict(E1=c["E"], E2=c["E2"], E3=c["E2"], nu12=c["nu"], nu13=c["nu"], nu23=c["nu23"],
                             G12=c["G12"], G13=c["G12"], G23=c["G23"], ori=None)
    if mat in ("PAD_A", "PAD_B", "ELAST_X", "ELAST_C"):
        # elastomero pegado entre caras rigidas: modulo de compresion aparente Ec = E (1 + 2 S^2), S = factor de forma
        el = M["ELAST"]
        if mat == "ELAST_X":
            S = (P.WASH_D - P.KEY_HOLE) / (4 * P.ISO_T)
        elif mat == "ELAST_C":
            # manguito bajo carga radial: zona comprimida de +-45 grados (ancho w) por el largo de enganche L
            w = 0.5 * math.pi * (P.CEN_RO + P.CEN_ELT / 2)
            L = P.CEN_EX[1] - P.CEN_EX[0]
            S = w * L / (2 * (w + L) * P.CEN_ELT)
        else:
            w = 2 * math.tan(math.radians(P.PAD_ANG / 2)) * P.CT_RI
            L = P.T_END
            S = w * L / (2 * (w + L) * (P.CT_RI - P.R_C1))
        Ec = el["E"] * (1 + 2 * S ** 2)
        if mat == "ELAST_X":
            return "ortho", dict(E1=Ec, E2=el["E"], E3=el["E"], nu12=0.0, nu13=0.0, nu23=0.0, G12=el["G"], G13=el["G"],
                                 G23=el["G"], ori=None, S=S)
        # patines y manguito: la cara de PTFE desliza; solo transmiten compresion radial (eje local 1)
        g = P.G_DESL
        return "ortho", dict(E1=Ec, E2=el["E"], E3=el["E"], nu12=0.0, nu13=0.0, nu23=0.0, G12=g, G13=g, G23=g, ori=None, S=S)
    iso = {"EQ_BAT": (5.0e3, 0.30), "EQ_PCB": (M["FR4"]["E"], M["FR4"]["nu"]), "EQ_BLK": (2.0e3, 0.35),
           "EQ_BOOM": (100e3, 0.30), "EQ_SOFT": (50.0, 0.30)}
    if mat in iso:
        return "iso", dict(E=iso[mat][0], nu=iso[mat][1])
    return "iso", dict(E=M[mat]["E"], nu=M[mat]["nu"])


def piezas_fe():
    """Piezas del modelo, con las masas no modeladas repartidas y el lastre ajustado a M_TOT."""
    parts = cad.build("fe")
    M = P.M_EQ
    by = {p["nombre"]: p for p in parts}
    # masa del ala en las cunas
    for k, frac in ((2, 0.20), (3, 0.28)):
        for tag in ("der.", "izq."):
            by[f"Cuna de ala C{k} {tag}"]["masa"] += M["ala_por_lado"] * frac
    # cableado sobre la bandeja; camaras y baliza montadas sobre los marcos C2 y C3; celdas sobre la tapa;
    # paracaidas y brida sobre la tapa del contenedor
    by["B1 bandeja de avionica"]["masa"] += M["cableado_tornillos"] + M["cubierta_inf"]
    by["C2 cuaderna intermedia"]["masa"] += M["camaras"] / 2 + M["baliza"] / 2
    by["C3 cuaderna intermedia"]["masa"] += M["camaras"] / 2 + M["baliza"] / 2
    by["P3 tapa superior"]["masa"] += M["solar"]
    by["CT2 tapa nervada"]["masa"] += M["paracaidas"] + M["brida_herrajes"]
    tot = sum(p["masa"] for p in parts if p["masa"] is not None)
    lastre = by["Lastre de centrado (asignacion)"]
    lastre["masa"] = P.M_TOT - tot
    assert lastre["masa"] > 0, "la masa supera M_TOT"
    for p in parts:
        p["rho"] = p["masa"] / p["vol"] * 1e-9 * 1e3       # g/mm3 -> t/mm3
    orden = {"CFRP": 0, "G10": 1}
    parts.sort(key=lambda p: orden.get(p["mat"], 2))
    return parts


def piezas_fe_estructural():
    """Modelo exclusivamente estructural: sin baterias, placas, servos, lastre, soportes de equipos, botalon ni ala estibada.
    La masa de esos componentes se reparte como masa no estructural (densidad adicional) sobre la pieza que la lleva:
      bandeja (3 tramos: nariz, centro, cola)  : servo de cola, bateria, placas, servo del cerrojo, cableado y lastre
      marcos C2 y C3                           : camaras y baliza
      cunas de ala, C1 y C4                    : ala estibada;  guias de botalon y C4: botalon de cola
      tapa superior                            : celdas solares;  tapa nervada: paracaidas y brida
    El lastre de centrado cierra la masa total en M_TOT y va en el tramo de nariz de la bandeja."""
    global LASTRE_G
    parts = [p for p in cad.build("fe") if p["grupo"] in ("estructura", "contenedor", "mecanismo")]
    M = P.M_EQ
    # bandeja cortada en tres tramos para repartir la masa segun su posicion
    b1 = next(p for p in parts if p["nombre"].startswith("B1"))
    parts.remove(b1)
    tramos = (("B1a bandeja tramo de nariz", P.X_C1[1], 60.0), ("B1b bandeja tramo central", 60.0, 142.0),
              ("B1c bandeja tramo de cola", 142.0, P.X_C4[0]))
    for nombre, x0, x1 in tramos:
        sh = b1["shape"].intersect(cad.box(x0, x1, -60, 60, -60, 60))
        parts.append(dict(nombre=nombre, shape=sh, mat="G10", color=b1["color"], grupo="estructura", vol=sh.Volume(),
                          masa=sh.Volume() * P.MAT["G10"]["rho"] / 1000.0))
    by = {p["nombre"]: p for p in parts}
    largo = {n_: x1 - x0 for n_, x0, x1 in tramos}
    L_tot = sum(largo.values())
    nse = {"B1a bandeja tramo de nariz": M["servo_cola"] + 0.8, "B1b bandeja tramo central": M["bateria"] + M["porta_bateria"] + M["pcb_principal"] + 1.2,
           "B1c bandeja tramo de cola": M["pcb_radio"] + 1.0 + M["servo_lib"]}
    for n_, v in nse.items():
        by[n_]["masa"] += v + (M["cableado_tornillos"] + M["cubierta_inf"]) * largo[n_] / L_tot
    for k, frac in ((2, 0.20), (3, 0.28)):
        for tag in ("der.", "izq."):
            by[f"Cuna de ala C{k} {tag}"]["masa"] += M["ala_por_lado"] * frac
    by["C1 cuaderna de nariz"]["masa"] += 2 * M["ala_por_lado"] * 0.30
    by["C4 cuaderna de cola"]["masa"] += 2 * M["ala_por_lado"] * 0.22 + M["cola"] / 3
    by["Guia de botalon C2"]["masa"] += M["cola"] / 3
    by["Guia de botalon C3"]["masa"] += M["cola"] / 3
    by["C2 cuaderna intermedia"]["masa"] += M["camaras"] / 2 + M["baliza"] / 2
    by["C3 cuaderna intermedia"]["masa"] += M["camaras"] / 2 + M["baliza"] / 2
    by["P3 tapa superior"]["masa"] += M["solar"]
    by["CT2 tapa nervada"]["masa"] += M["paracaidas"] + M["brida_herrajes"]
    tot = sum(p["masa"] for p in parts)
    LASTRE_G = P.M_TOT - tot
    assert LASTRE_G > 0, "la masa supera M_TOT"
    by["B1a bandeja tramo de nariz"]["masa"] += LASTRE_G
    for p in parts:
        p["rho"] = p["masa"] / p["vol"] * 1e-9 * 1e3
    orden = {"CFRP": 0, "G10": 1}
    parts.sort(key=lambda p: orden.get(p["mat"], 2))
    return parts


LASTRE_G = 0.0


def quitar_solapes(parts):
    """Corta cada pieza con las anteriores (las de mas prioridad quedan enteras)."""
    bbs = [p["shape"].BoundingBox() for p in parts]
    for i, p in enumerate(parts):
        for j in range(i):
            a, b = bbs[i], bbs[j]
            if (a.xmin > b.xmax - 1e-6 or b.xmin > a.xmax - 1e-6 or a.ymin > b.ymax - 1e-6 or b.ymin > a.ymax - 1e-6
                    or a.zmin > b.zmax - 1e-6 or b.zmin > a.zmax - 1e-6):
                continue
            com = p["shape"].intersect(parts[j]["shape"])
            if com.isValid() and com.Volume() > 1e-3:
                p["shape"] = p["shape"].cut(parts[j]["shape"]).clean()
        p["vol"] = p["shape"].Volume()
    return parts


def mallar(parts, wd, escala=1.0, nthreads=4):
    os.makedirs(wd, exist_ok=True)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", nthreads)
    gmsh.model.add("cansat")
    tags = []
    for i, p in enumerate(parts):
        f = os.path.join(wd, f"p{i}.brep")
        p["shape"].exportBrep(f)
        dt = gmsh.model.occ.importShapes(f)
        tags.append([t for t in dt if t[0] == 3])
    allv = [t for tt in tags for t in tt]
    if len(allv) > 1:
        out, omap = gmsh.model.occ.fragment(allv, [])
    else:
        omap = [allv]
    gmsh.model.occ.synchronize()
    vol2part = {}
    k = 0
    for i, tt in enumerate(tags):
        for _ in tt:
            for d, v in omap[k]:
                vol2part.setdefault(v, i)
            k += 1
    # tamanos: primero los gruesos, despues los finos (mandan en puntos compartidos)
    hs = [h_de(p, escala) for p in parts]
    for i in np.argsort(hs)[::-1]:
        vols = [(3, v) for v, pi in vol2part.items() if pi == i]
        pts = gmsh.model.getBoundary(vols, combined=False, oriented=False, recursive=True)
        gmsh.model.mesh.setSize(pts, hs[i])
    gmsh.option.setNumber("Mesh.MeshSizeMax", 6.5 * escala)
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.6)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 9)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)
    gmsh.option.setNumber("Mesh.Optimize", 1)
    gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)
    gmsh.option.setNumber("Mesh.OptimizeThreshold", 0.35)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)
    gmsh.model.mesh.generate(3)
    ntags, coords, _ = gmsh.model.mesh.getNodes()
    xyz_all = np.asarray(coords).reshape(-1, 3)
    idmap = np.zeros(int(ntags.max()) + 1, dtype=np.int64)
    idmap[np.asarray(ntags, dtype=np.int64)] = np.arange(len(ntags))
    els, epart = [], []
    for v, pi in vol2part.items():
        et, _, en = gmsh.model.mesh.getElements(3, v)
        for t, n in zip(et, en):
            if t != 11:
                continue
            c = idmap[np.asarray(n, dtype=np.int64)].reshape(-1, 10)
            els.append(c)
            epart.append(np.full(len(c), pi))
    gmsh.finalize()
    els = np.vstack(els)
    epart = np.concatenate(epart)
    used = np.unique(els)
    remap = -np.ones(len(xyz_all), dtype=np.int64)
    remap[used] = np.arange(len(used))
    xyz = xyz_all[used]
    els = remap[els]
    els = els[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]       # orden de nodos gmsh -> Abaqus/CalculiX
    return xyz, els, epart


def es_verificable(p):
    """Piezas cuyas tensiones se imprimen (se excluyen masas idealizadas y patines)."""
    return not (p["mat"].startswith("EQ_BLK") or p["mat"] in ("EQ_BAT", "EQ_SOFT", "EQ_BOOM"))


def escribir_inp(path, xyz, els, epart, parts, pasos, bcs, nmodes=30):
    """pasos: 'modal' | 'estat3' | 'estat1'.  bcs: lista de (nodos, gdl_ini, gdl_fin)."""
    with open(path, "w") as f:
        f.write("*NODE, NSET=NALL\n")
        for i, (x, y, z) in enumerate(xyz):
            f.write(f"{i + 1},{x:.6f},{y:.6f},{z:.6f}\n")
        for pi, p in enumerate(parts):
            idx = np.where(epart == pi)[0]
            if len(idx) == 0:
                continue
            f.write(f"*ELEMENT, TYPE=C3D10, ELSET=E{pi}\n")
            for e in idx:
                f.write(f"{e + 1}," + ",".join(str(n + 1) for n in els[e]) + "\n")
        for k, (nodos, d0, d1) in enumerate(bcs):
            f.write(f"*NSET, NSET=NFIX{k}\n")
            for j in range(0, len(nodos), 12):
                f.write(",".join(str(n + 1) for n in nodos[j:j + 12]) + "\n")
        act = [pi for pi in range(len(parts)) if np.any(epart == pi)]
        f.write("*ELSET, ELSET=EALL\n")
        for k in range(0, len(act), 10):
            f.write(",".join(f"E{pi}" for pi in act[k:k + 10]) + "\n")
        ver = [pi for pi in act if es_verificable(parts[pi])]
        f.write("*ELSET, ELSET=EVER\n")
        for k in range(0, len(ver), 10):
            f.write(",".join(f"E{pi}" for pi in ver[k:k + 10]) + "\n")
        f.write("*ORIENTATION, NAME=ORA, SYSTEM=RECTANGULAR\n0.,0.70710678,0.70710678,0.,-0.70710678,0.70710678\n")
        f.write("*ORIENTATION, NAME=ORB, SYSTEM=RECTANGULAR\n0.,-0.70710678,0.70710678,0.,-0.70710678,-0.70710678\n")
        f.write("*ORIENTATION, NAME=ORC, SYSTEM=CYLINDRICAL\n0.,0.,0.,1.,0.,0.\n")     # 1 radial, 2 tangencial, 3 = x
        for pi in act:
            p = parts[pi]
            tipo, c = elastico(p["mat"])
            f.write(f"*MATERIAL, NAME=M{pi}\n")
            if tipo == "iso":
                f.write(f"*ELASTIC\n{c['E']:.4f},{c['nu']:.4f}\n")
            else:
                f.write("*ELASTIC, TYPE=ENGINEERING CONSTANTS\n")
                f.write(f"{c['E1']},{c['E2']},{c['E3']},{c['nu12']},{c['nu13']},{c['nu23']},{c['G12']},{c['G13']},\n")
                f.write(f"{c['G23']},293.\n")
            f.write(f"*DENSITY\n{p['rho']:.6e}\n")
            ori = ""
            if p["mat"] == "PAD_A":
                ori = ", ORIENTATION=ORA"
            elif p["mat"] == "PAD_B":
                ori = ", ORIENTATION=ORB"
            elif p["mat"] == "ELAST_C":
                ori = ", ORIENTATION=ORC"
            f.write(f"*SOLID SECTION, ELSET=E{pi}, MATERIAL=M{pi}{ori}\n")
        f.write("*BOUNDARY\n")
        for k, (nodos, d0, d1) in enumerate(bcs):
            f.write(f"NFIX{k},{d0},{d1}\n")
        salida = "*NODE FILE\nU\n*EL PRINT, ELSET=EVER, GLOBAL=YES\nS\n*END STEP\n"
        if pasos == "modal":
            f.write(f"*STEP\n*FREQUENCY\n{nmodes}\n" + salida)
        else:
            dirs = ((-1, 0, 0), (0, -1, 0), (0, 0, -1)) if pasos == "estat3" else ((-1, 0, 0),)
            for d in dirs:
                f.write("*STEP\n*STATIC\n*DLOAD, OP=NEW\n")      # OP=NEW: sin esto CalculiX acumula la gravedad de los pasos previos
                f.write(f"EALL,GRAV,{G_MM:.3f},{d[0]}.,{d[1]}.,{d[2]}.\n" + salida)


def correr_ccx(job, wd, nthreads=None):
    # CCX_HILOS: hilos de CalculiX.  SPOOLES multihilo puede dejar ruido local en los autovectores (ver informe)
    nthreads = int(os.environ.get("CCX_HILOS", "4")) if nthreads is None else nthreads
    nsolver = os.environ.get("CCX_SPOOLES", str(nthreads))          # hilos del resolvedor SPOOLES
    env = dict(os.environ, OMP_NUM_THREADS=str(nthreads), CCX_NPROC_EQUATION_SOLVER=nsolver)
    t0 = time.time()
    r = subprocess.run(["ccx", job], cwd=wd, env=env, capture_output=True, text=True)
    open(os.path.join(wd, job + ".log"), "w").write(r.stdout + r.stderr)
    ok = os.path.exists(os.path.join(wd, job + ".frd")) and "Job finished" in r.stdout
    print(f"  ccx {job}: {'ok' if ok else 'ERROR'} en {time.time() - t0:.0f} s")
    if not ok:
        print(r.stdout[-1500:], r.stderr[-800:])
    return ok


def nodos_base(xyz):
    """Borde inferior del contenedor (apoyo sobre el plato del cohete / utillaje de ensayo)."""
    return np.where(np.abs(xyz[:, 0] - P.CT_X[0]) < 1e-4)[0]


def nodos_guia(xyz):
    """Borde superior del contenedor: guiado lateralmente por el fuselaje del cohete."""
    return np.where(np.abs(xyz[:, 0] - P.CT_X[1]) < 1e-4)[0]


def nodos_brida(xyz):
    """Nodos de los 3 nervios de la tapa donde ancla la brida del paracaidas."""
    sel = np.zeros(len(xyz), bool)
    xt = P.CT_TOP[0] + P.CT_CAP_H
    for ang in P.CT_BRIDA_ANG:
        a = math.radians(ang)
        c = np.array([xt - 3.5, P.R_BRIDA * math.cos(a), P.R_BRIDA * math.sin(a)])
        sel |= (np.linalg.norm(xyz - c, axis=1) < 3.4) & (xyz[:, 0] < xt + 1e-6)
    return np.where(sel)[0]


def solo_correr(wd, tag):
    """Corre los cuatro trabajos de CalculiX sobre mazos ya escritos."""
    t0 = time.time()
    for job in (f"estat_{tag}", f"parac_{tag}", f"modal_{tag}", f"libre_{tag}"):
        correr_ccx(job, wd)
    print(f"total {time.time() - t0:.0f} s")


def main(wd, escala=1.0, nmodes=30, tag="base", solo=None):
    os.makedirs(wd, exist_ok=True)
    t0 = time.time()
    parts = quitar_solapes(piezas_fe_estructural())
    print(f"piezas FE (solo estructura): {len(parts)}  masa total modelo = {sum(p['masa'] for p in parts):.1f} g  "
          f"(lastre en la nariz = {LASTRE_G:.1f} g)")
    xyz, els, epart = mallar(parts, wd, escala)
    print(f"malla: {len(xyz)} nodos, {len(els)} C3D10  ({time.time() - t0:.0f} s)")
    meta = [dict(nombre=p["nombre"], mat=p["mat"], grupo=p["grupo"], masa=p["masa"], vol=p["vol"], rho=p["rho"],
                 color=p["color"], ver=es_verificable(p)) for p in parts]
    np.savez_compressed(os.path.join(wd, f"malla_{tag}.npz"), xyz=xyz, els=els, epart=epart)
    json.dump(meta, open(os.path.join(wd, f"partes_{tag}.json"), "w"), indent=1)
    base, guia, brida = nodos_base(xyz), nodos_guia(xyz), nodos_brida(xyz)
    print(f"nodos: base {len(base)}, guia superior {len(guia)}, brida {len(brida)}")
    bc_guia = [(base, 1, 3), (guia, 2, 3)]
    bc_lanz = [(base, 1, 3)] if P.APOYO == "base" else bc_guia
    escribir_inp(os.path.join(wd, f"modal_{tag}.inp"), xyz, els, epart, parts, "modal", bc_lanz, nmodes)
    escribir_inp(os.path.join(wd, f"estat_{tag}.inp"), xyz, els, epart, parts, "estat3", bc_lanz)
    escribir_inp(os.path.join(wd, f"parac_{tag}.inp"), xyz, els, epart, parts, "estat1", [(brida, 1, 3)])
    # corrida de comparacion: la otra condicion de apoyo (si el caso base es voladizo, aqui el borde superior va guiado)
    escribir_inp(os.path.join(wd, f"libre_{tag}.inp"), xyz, els, epart, parts, "modal",
                 bc_guia if P.APOYO == "base" else [(base, 1, 3)], 6)
    solo = solo or [x for x in os.environ.get("FE_SOLO", "").split(",") if x]      # FE_SOLO=malla: solo malla y mazos
    for job in (f"estat_{tag}", f"parac_{tag}", f"modal_{tag}", f"libre_{tag}"):
        if solo and not any(job.startswith(x) for x in solo):
            continue
        correr_ccx(job, wd)
    print(f"total {time.time() - t0:.0f} s")


if __name__ == "__main__":
    if sys.argv[1] == "--correr":
        solo_correr(sys.argv[2], sys.argv[3])
        sys.exit(0)
    wd = sys.argv[1]
    escala = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    tag = sys.argv[3] if len(sys.argv) > 3 else "base"
    main(wd, escala, tag=tag)
