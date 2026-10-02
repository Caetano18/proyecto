#!/usr/bin/env python3
"""Barrido de polares con XFOIL 6.99 en modo por lotes, con manejo de faltas de convergencia.

Estrategia (versión reducida, pensada para correr en ~15 min con 4 núcleos):
  * Cada caso (perfil, Re, Ncrit) se resuelve con TRES densidades de panelado
    (160, 200 y 240 nodos). Para cada una se recorren dos ramas con ASEQ y paso de
    0,25 grados, desde el ángulo de arranque (2 grados en perfiles con curvatura, 0 en
    los simétricos) hasta +16 y hasta -6. XFOIL guarda (PACC) solo los puntos
    convergidos.
  * Si una corrida se cuelga (tiempo de espera), se reanuda dos pasos más allá del
    último punto guardado (máx. 4 reanudaciones por rama).
  * Fusión: en cada ángulo se toma la mediana de los valores convergidos con los
    distintos panelados. Si solo hay dos y difieren en más de 0,08 en Cl, el punto se
    descarta por no robusto. La dispersión entre panelados se guarda como
    incertidumbre numérica.
  * Capa límite: para la placa 7 % y el NACA 6412 se vuelcan DUMP y CPWR en ángulos
    seleccionados (análisis de la burbuja de separación laminar).

El XFOIL empaquetado activa trampas de punto flotante (gfortran -ffpe-trap) y aborta
con SIGFPE en operaciones que el código original tolera; se neutralizan con una
biblioteca LD_PRELOAD mínima que se compila al vuelo.

Salidas (analysis/data):
  polares_<perfil>_Re<k>.dat        Ncrit 9  (alpha cl cd cm xtrs xtri npan dcl dcd)
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
ITER = 200
TIMEOUT = 90.0
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


def cabecera(geom, npan, re_, ncrit):
    return (f"PLOP\nG F\n\nLOAD {geom}\nPPAR\nN {npan}\n\n\nOPER\nVISC {re_:.0f}\n"
            f"VPAR\nN {ncrit}\n\nITER {ITER}\n")


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


def rama(caso, npan, a0, a1, etiqueta):
    """ASEQ de a0 a a1; reanuda tras un cuelgue. Devuelve (puntos, reanudaciones)."""
    paso = DA if a1 > a0 else -DA
    inicio, todos, reanud = a0, [], 0
    for intento in range(5):
        pol = f"{etiqueta}_{intento}.pol"
        ruta = os.path.join(caso["dir"], pol)
        if os.path.exists(ruta):
            os.remove(ruta)
        cmds = cabecera(caso["geom"], npan, caso["re"], caso["ncrit"])
        cmds += f"PACC\n{pol}\n\nASEQ {inicio:.3f} {a1:.3f} {paso:.3f}\nPACC\n\nQUIT\n"
        _, colgado = correr(cmds, caso["dir"])
        P = leer_polar(ruta)
        if len(P):
            todos.append(P)
        if not colgado:
            break
        reanud += 1
        ultimo = P[-1, 0] if len(P) else inicio
        inicio = ultimo + 2 * paso
        if (paso > 0 and inicio > a1) or (paso < 0 and inicio < a1):
            break
    return (np.vstack(todos) if todos else np.zeros((0, 9))), reanud


def fusionar(por_panel):
    """Mediana entre panelados en una grilla de 0,25 grados."""
    grilla = np.round(np.arange(AMIN, AMAX + 1e-9, DA), 3)
    filas, descartados, unicos = [], [], 0
    for a in grilla:
        vals = []
        for P in por_panel.values():
            if len(P) == 0:
                continue
            j = np.where(np.abs(P[:, 0] - a) < 1e-3)[0]
            if len(j):
                vals.append(P[j[0]])
        if not vals:
            continue
        V = np.array(vals)
        if len(V) == 2 and abs(V[0, 1] - V[1, 1]) > TOL_CL:
            descartados.append(float(a))
            continue
        if len(V) == 1:
            unicos += 1
        med = np.median(V, axis=0)
        dcl = V[:, 1].max() - V[:, 1].min()
        dcd = V[:, 2].max() - V[:, 2].min()
        # alpha cl cd cm xtr_sup xtr_inf npan dcl dcd
        filas.append([a, med[1], med[2], med[4], med[5], med[6], len(V), dcl, dcd])
    return np.array(filas), descartados, unicos, grilla


def caso_polar(caso):
    os.makedirs(caso["dir"], exist_ok=True)
    t0 = time.time()
    a_s = 2.0 if caso["perfil"] in CURVOS else 0.0
    por_panel, reanud = {}, 0
    for npan in PANELES:
        up, r1 = rama(caso, npan, a_s, AMAX, f"p{npan}_sube")
        dn, r2 = rama(caso, npan, a_s, AMIN, f"p{npan}_baja")
        reanud += r1 + r2
        P = np.vstack([x for x in (up, dn) if len(x)]) if (len(up) or len(dn)) else np.zeros((0, 9))
        por_panel[npan] = P
    F, desc, unicos, grilla = fusionar(por_panel)
    faltan = [float(a) for a in grilla if not len(F) or not np.any(np.abs(F[:, 0] - a) < 1e-3)]
    log = dict(tag=caso["tag"], n_grilla=len(grilla), n_ok=len(F), unicos=unicos,
               descartados=desc, faltan=faltan, reanudaciones=reanud,
               por_panel={k: int(len(v)) for k, v in por_panel.items()},
               seg=round(time.time() - t0, 1))
    np.savetxt(os.path.join(caso["dir"], "fusion.txt"), F)
    with open(os.path.join(caso["dir"], "log.json"), "w") as f:
        json.dump(log, f)
    suf = "" if caso["ncrit"] == 9 else f"_N{caso['ncrit']}"
    with open(os.path.join(DATA, f"polares_{caso['perfil']}_Re{caso['re']//1000}{suf}.dat"), "w") as f:
        f.write("alpha cl cd cm xtrs xtri npan dcl dcd\n")
        for r in F:
            f.write(f"{r[0]:.2f} {r[1]:.4f} {r[2]:.5f} {r[3]:.4f} {r[4]:.4f} {r[5]:.4f} "
                    f"{int(r[6])} {r[7]:.4f} {r[8]:.5f}\n")
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
                      f"unicos={log['unicos']:2d} desc={len(log['descartados']):2d} "
                      f"faltan={len(log['faltan']):2d} reanud={log['reanudaciones']} "
                      f"{log['por_panel']} [{time.time()-t0:5.0f} s]", flush=True)
        if not solo:
            with open(os.path.join(RAW, "logs.json"), "w") as f:
                json.dump(logs, f)
    if "capa" in etapa:
        with Pool(NPROC) as pool:
            for r in pool.imap_unordered(caso_capa, casos_capa()):
                print("capa", r, flush=True)


if __name__ == "__main__":
    main()
