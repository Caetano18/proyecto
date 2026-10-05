#!/usr/bin/env python3
"""Barrido de polares con XFOIL 6.99 en modo por lotes, con manejo de faltas de convergencia.

Estrategia:
  * Cada caso (perfil, Re, Ncrit) se resuelve con TRES densidades de panelado
    (160, 200 y 240 nodos) y CUATRO barridos por panelado, con paso de 0,25 grados:
    -6 -> 16, 2 -> 16 (ascendentes) y 8 -> -6, 2 -> -6 (descendentes). Cada barrido es
    una lista de comandos ALFA en una sola sesión: un punto que no converge no detiene
    el barrido y XFOIL guarda (PACC) solo los convergidos. Tiempo de espera: 60 s.
  * Fusión en cada ángulo (hasta 12 valores): mediana si los Cl caben en 0,08; si no,
    se separan dos grupos por el mayor salto. Un grupo de un punto es un atípico y se
    descarta; dos grupos de 2 o más puntos marcan un ángulo biestable (histéresis de la
    burbuja laminar): la polar principal toma la rama de Cl bajo (conservadora) y la
    otra se guarda como alternativa (columnas clalt, cdalt).
  * Rescate: si faltan más de 3 ángulos se repiten los cuatro barridos con VACC = 0,005
    (160, 200, 240 nodos) y con 140 nodos, y se vuelve a fusionar todo.
  * Capa límite: para la placa 7 % y el NACA 6412 se vuelcan DUMP y CPWR en ángulos
    seleccionados (análisis de la burbuja de separación laminar).

El XFOIL empaquetado activa trampas de punto flotante (gfortran -ffpe-trap) y aborta
con SIGFPE en operaciones que el código original tolera; se neutralizan con una
biblioteca LD_PRELOAD mínima que se compila al vuelo.

Salidas (analysis/data):
  polares_<perfil>_Re<k>.dat        Ncrit 9  (alpha cl cd cm xtrs xtri npts dcl dcd biest clalt cdalt)
  polares_<perfil>_Re<k>_N5.dat     Ncrit 5
  polares_conv.dat                  resumen de convergencia por caso
Crudos (RAW): polares, volcados de capa límite (.bl) y de Cp (.cp).

Uso: python3 analysis/polares_xfoil.py [directorio_raw] [nproc]
"""
import os
import re
import sys
import json
import time
import subprocess
from multiprocessing import Pool

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "analysis", "data")
RAW = sys.argv[1] if len(sys.argv) > 1 else "/tmp/polares_xfoil"
NPROC = int(sys.argv[2]) if len(sys.argv) > 2 else 4

PANELES = (160, 200, 240)
DA = 0.25
AMIN, AMAX = -6.0, 16.0
ITER = 120
TIMEOUT = 60.0
TOL_CL = 0.08
RES = [20000, 35000, 50000, 75000, 100000]
CURVOS = {"placa7", "placa4", "clarky", "naca6412", "placa7_t11", "placa7_t20"}


def shim():
    os.makedirs(RAW, exist_ok=True)
    so = os.path.join(RAW, "libnofpe.so")
    if not os.path.exists(so):
        src = os.path.join(RAW, "nofpe.c")
        with open(src, "w") as f:
            f.write("void _gfortran_set_fpe(int v){(void)v;}\n")
        subprocess.check_call(["gcc", "-shared", "-fPIC", "-O2", "-o", so, src])
    return so


def correr(cmds, cwd, timeout=TIMEOUT):
    env = dict(os.environ, LD_PRELOAD=shim())
    try:
        o = subprocess.run(["xfoil"], input=cmds.encode(), cwd=cwd, capture_output=True,
                           timeout=timeout, env=env)
        return o.stdout.decode("latin-1"), False
    except subprocess.TimeoutExpired:
        return "", True


def cabecera(geom, npan, re_, ncrit, vacc=None):
    v = "" if vacc is None else f"VACC {vacc}\n"
    return (f"PLOP\nG F\n\nLOAD {geom}\nPPAR\nN {npan}\n\n\nOPER\nVISC {re_:.0f}\n"
            f"VPAR\nN {ncrit}\n{v}\nITER {ITER}\n")


def leer_polar(path):
    if not os.path.exists(path):
        return np.zeros((0, 9))
    with open(path) as f:
        lineas = f.readlines()
    i = next((k for k, l in enumerate(lineas) if l.strip().startswith("------")), None)
    if i is None:
        return np.zeros((0, 9))
    filas = [[float(v) for v in l.split()[:9]] for l in lineas[i + 1:] if len(l.split()) >= 9]
    return np.array(filas) if filas else np.zeros((0, 9))


SWEEPS = (("sube_m6", AMIN, AMAX), ("sube_p2", 2.0, AMAX),
          ("baja_p8", 8.0, AMIN), ("baja_p2", 2.0, AMIN))


# Configuraciones de rescate (solo si faltan más de 3 ángulos con las de base): factor
# de relajación viscosa VACC = 0,005 (por defecto 0,01) con los tres panelados, y un
# panelado más grueso de 140 nodos. En la placa curvada a Re 1e5 evitan los cuelgues
# de XFOIL por encima de 5 grados.
RESCATE = ((160, 0.005), (200, 0.005), (240, 0.005), (140, None))
REUSAR = os.environ.get("POLARES_REUSAR") == "1"


def barrido(caso, npan, a0, a1, etiqueta, vacc=None):
    """Lista de ALFA de a0 a a1 (paso DA) en una sola sesión. XFOIL guarda solo los
    puntos convergidos; un punto que no converge no detiene el barrido (a diferencia
    de ASEQ, que con la placa fina a veces queda en un bucle). Devuelve (puntos, colgado)."""
    paso = DA if a1 > a0 else -DA
    pol = f"{etiqueta}.pol"
    ruta = os.path.join(caso["dir"], pol)
    if os.path.exists(ruta):
        if REUSAR:
            return leer_polar(ruta), False
        os.remove(ruta)
    cmds = cabecera(caso["geom"], npan, caso["re"], caso["ncrit"], vacc) + f"PACC\n{pol}\n\n"
    for a in np.arange(a0, a1 + 0.5 * paso, paso):
        cmds += f"ALFA {a:.3f}\n"
    cmds += "PACC\n\nQUIT\n"
    _, colgado = correr(cmds, caso["dir"])
    return leer_polar(ruta), colgado


def fusionar(valores):
    """valores: {alpha: [(fila XFOIL, sentido), ...]} -> polar fusionada.

    Si los Cl de un ángulo caben en TOL_CL se toma la mediana. Si no, se separan en dos
    grupos por el mayor salto; un grupo de un solo punto se descarta (atípico numérico).
    Si quedan dos grupos de al menos dos puntos, el ángulo es biestable: la polar
    principal toma el grupo de Cl bajo (conservador para la autorrotación) y se guarda
    el otro como rama alternativa."""
    grilla = np.round(np.arange(AMIN, AMAX + 1e-9, DA), 3)
    filas, atipicos, biest = [], 0, []
    for a in grilla:
        vals = valores.get(float(a), [])
        if not vals:
            continue
        V = np.array([v[0] for v in vals])
        V = V[np.argsort(V[:, 1])]
        alt = None
        if V[-1, 1] - V[0, 1] > TOL_CL:
            k = int(np.argmax(np.diff(V[:, 1])))
            lo, hi = V[:k + 1], V[k + 1:]
            if len(lo) >= 2 and len(hi) >= 2:
                biest.append(float(a))
                V, alt = lo, np.median(hi, axis=0)
            elif len(lo) >= 2:
                atipicos += len(hi); V = lo
            elif len(hi) >= 2:
                atipicos += len(lo); V = hi
            else:
                atipicos += len(V)
                continue
        med = np.median(V, axis=0)
        dcl = V[:, 1].max() - V[:, 1].min()
        dcd = V[:, 2].max() - V[:, 2].min()
        b = 0 if alt is None else 1
        cla = med[1] if alt is None else alt[1]
        cda = med[2] if alt is None else alt[2]
        filas.append([a, med[1], med[2], med[4], med[5], med[6], len(V), dcl, dcd, b, cla, cda])
    return np.array(filas), atipicos, biest, grilla


def caso_polar(caso):
    os.makedirs(caso["dir"], exist_ok=True)
    t0 = time.time()
    valores, colgados, por_barrido = {}, 0, {}

    def correr_conf(npan, vacc):
        nonlocal colgados
        for nom, a0, a1 in SWEEPS:
            et = f"p{npan}_{nom}" + ("" if vacc is None else "_v")
            P, colg = barrido(caso, npan, a0, a1, et, vacc)
            colgados += int(colg)
            por_barrido[et] = int(len(P))
            for r in P:
                a = round(round(r[0] / DA) * DA, 3)
                if abs(a - r[0]) < 1e-3:
                    valores.setdefault(float(a), []).append((r, nom))

    for npan in PANELES:
        correr_conf(npan, None)
    F, atip, biest, grilla = fusionar(valores)
    faltan = [float(a) for a in grilla if not len(F) or not np.any(np.abs(F[:, 0] - a) < 1e-3)]
    rescate = len(faltan) > 3
    if rescate:
        for npan, vacc in RESCATE:
            correr_conf(npan, vacc)
        F, atip, biest, grilla = fusionar(valores)
        faltan = [float(a) for a in grilla if not len(F) or not np.any(np.abs(F[:, 0] - a) < 1e-3)]
    log = dict(tag=caso["tag"], n_grilla=len(grilla), n_ok=len(F), atipicos=atip, rescate=rescate,
               biestables=biest, faltan=faltan, colgados=colgados,
               por_barrido=por_barrido, seg=round(time.time() - t0, 1))
    np.savetxt(os.path.join(caso["dir"], "fusion.txt"), F)
    with open(os.path.join(caso["dir"], "log.json"), "w") as f:
        json.dump(log, f)
    suf = "" if caso["ncrit"] == 9 else f"_N{caso['ncrit']}"
    with open(os.path.join(DATA, f"polares_{caso['perfil']}_Re{caso['re']//1000}{suf}.dat"), "w") as f:
        f.write("alpha cl cd cm xtrs xtri npts dcl dcd biest clalt cdalt\n")
        for r in F:
            f.write(f"{r[0]:.2f} {r[1]:.4f} {r[2]:.5f} {r[3]:.4f} {r[4]:.4f} {r[5]:.4f} "
                    f"{int(r[6])} {r[7]:.4f} {r[8]:.5f} {int(r[9])} {r[10]:.4f} {r[11]:.5f}\n")
    return log


def caso_capa(c):
    """Converge hasta alfa y vuelca capa límite y Cp; prueba los tres panelados."""
    os.makedirs(c["dir"], exist_ok=True)
    a_s = 2.0 if c["perfil"] in CURVOS else 0.0
    for npan in PANELES:
        pol = f"cl_{c['alfa']:+05.1f}_{npan}.pol"
        ruta = os.path.join(c["dir"], pol)
        if os.path.exists(ruta):
            os.remove(ruta)
        bl = f"{c['tag']}.bl"
        cp = f"{c['tag']}.cp"
        cmds = cabecera(c["geom"], npan, c["re"], c["ncrit"])
        paso = DA if c["alfa"] >= a_s else -DA
        cmds += (f"PACC\n{pol}\n\nASEQ {a_s:.2f} {c['alfa']:.2f} {paso:.2f}\nPACC\n"
                 f"DUMP {bl}\nCPWR {cp}\n\nQUIT\n")
        _, colgado = correr(cmds, c["dir"])
        P = leer_polar(ruta)
        if not colgado and len(P) and abs(P[-1, 0] - c["alfa"]) < 1e-3:
            return dict(tag=c["tag"], npan=npan, ok=True)
    return dict(tag=c["tag"], npan=None, ok=False)


def casos():
    L = []

    def add(p, re_, n):
        tag = f"{p}_Re{re_//1000}_N{n}"
        L.append(dict(tag=tag, perfil=p, re=re_, ncrit=n, geom=os.path.join(RAW, p + ".dat"),
                      dir=os.path.join(RAW, "runs", tag)))
    for p in ["placa7", "naca6412", "placa4", "plana3", "clarky", "naca0012"]:
        for re_ in RES:
            add(p, re_, 9)
    for p in ["placa7", "naca6412"]:
        for re_ in RES:
            add(p, re_, 5)
    for p in ["placa7_t11", "placa7_t20"]:
        add(p, 50000, 9)
    return L


def casos_capa():
    L = []

    def add(p, re_, n, a):
        tag = f"{p}_Re{re_//1000}_N{n}_a{a:+03d}"
        L.append(dict(tag=tag, perfil=p, re=re_, ncrit=n, alfa=float(a),
                      geom=os.path.join(RAW, p + ".dat"), dir=os.path.join(RAW, "capa")))
    for p in ["placa7", "naca6412"]:
        for a in [0, 2, 4, 6, 8, 10]:
            add(p, 50000, 9, a)
    for re_ in [20000, 100000]:
        add("placa7", re_, 9, 4)
    add("placa7", 50000, 5, 4)
    return L


def main():
    shim()
    os.makedirs(DATA, exist_ok=True)
    solo = os.environ.get("POLARES_SOLO")
    etapa = os.environ.get("POLARES_ETAPA", "polares,capa")
    t0 = time.time()
    if "polares" in etapa:
        C = casos()
        if solo:
            C = [c for c in C if re.fullmatch(solo, c["tag"])]
        logs = []
        with Pool(NPROC) as pool:
            for log in pool.imap_unordered(caso_polar, C):
                logs.append(log)
                print(f"{log['tag']:22s} ok={log['n_ok']:2d}/{log['n_grilla']} "
                      f"atip={log['atipicos']:2d} biest={len(log['biestables']):2d} "
                      f"faltan={len(log['faltan']):2d} colg={log['colgados']} resc={int(log['rescate'])} "
                      f"[{time.time()-t0:5.0f} s]", flush=True)
        if not solo:
            with open(os.path.join(RAW, "logs.json"), "w") as f:
                json.dump(logs, f)
    if "capa" in etapa:
        with Pool(NPROC) as pool:
            for r in pool.imap_unordered(caso_capa, casos_capa()):
                print("capa", r, flush=True)


if __name__ == "__main__":
    main()
