#!/usr/bin/env python3
"""Barrido de polares con XFOIL 6.99 y manejo de faltas de convergencia.

Para cada caso (perfil, Re, Ncrit) se abre una sesión interactiva de XFOIL y se
recorren dos ramas: de 0 grados hacia +16 y de 0 hacia -6, con paso de 0,25 grados.
XFOIL guarda (PACC) solo los puntos convergidos. Si un punto no converge:
  1) INIT (reinicia la capa límite), se reconverge el último punto bueno y se
     avanza en 4 subpasos;
  2) si sigue sin converger, ITER 400 + INIT y un intento directo;
  3) si la sesión se cuelga (tiempo de espera), se mata, se reabre y se reanuda
     desde el último punto bueno (cuenta como "reinicio").
Los ángulos que siguen sin converger quedan registrados en el informe de
convergencia. En ángulos enteros se vuelcan la capa límite (DUMP) y el Cp (CPWR)
para el análisis de la burbuja de separación laminar.

El XFOIL empaquetado activa trampas de punto flotante (gfortran -ffpe-trap) y
aborta con SIGFPE en operaciones que el código original tolera; se neutralizan con
una biblioteca LD_PRELOAD mínima que se compila al vuelo.

Uso: python3 analysis/polares_xfoil.py [directorio_raw] [nproc]
"""
import os
import re
import sys
import time
import json
import select
import signal
import subprocess
import itertools
from multiprocessing import Pool

import numpy as np

RAW = sys.argv[1] if len(sys.argv) > 1 else "/tmp/polares_xfoil"
NPROC = int(sys.argv[2]) if len(sys.argv) > 2 else 4

NPAN = 240            # nodos de panel (ver estudio de independencia)
ITER = 150
DA = 0.25             # paso de ángulo
AMAX, AMIN = 16.0, -6.0
TIMEOUT = 45.0        # s por comando
PROMPT = re.compile(rb"\s[a-zA-Z]>\s*$")

SHIM_C = b"void _gfortran_set_fpe(int v){(void)v;}\n"


def shim():
    os.makedirs(RAW, exist_ok=True)
    so = os.path.join(RAW, "libnofpe.so")
    if not os.path.exists(so):
        src = os.path.join(RAW, "nofpe.c")
        with open(src, "wb") as f:
            f.write(SHIM_C)
        subprocess.check_call(["gcc", "-shared", "-fPIC", "-O2", "-o", so, src])
    return so


class Timeout(Exception):
    pass


class XFoil:
    def __init__(self, cwd, so):
        env = dict(os.environ, GFORTRAN_UNBUFFERED_PRECONNECTED="y", LD_PRELOAD=so)
        self.p = subprocess.Popen(["xfoil"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, cwd=cwd, env=env,
                                  start_new_session=True)
        self.fd = self.p.stdout.fileno()
        os.set_blocking(self.fd, False)
        self.read_until_prompt()

    def read_until_prompt(self, timeout=TIMEOUT):
        buf = b""
        t0 = time.time()
        while True:
            r, _, _ = select.select([self.fd], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(self.fd, 65536)
                except BlockingIOError:
                    chunk = b""
                if not chunk and self.p.poll() is not None:
                    raise Timeout("xfoil terminó")
                buf += chunk
                if PROMPT.search(buf[-200:]):
                    return buf.decode("latin-1")
            if time.time() - t0 > timeout:
                raise Timeout("sin respuesta")

    def cmd(self, s, timeout=TIMEOUT):
        self.p.stdin.write((s + "\n").encode())
        self.p.stdin.flush()
        return self.read_until_prompt(timeout)

    def close(self):
        try:
            os.killpg(self.p.pid, signal.SIGKILL)
        except Exception:
            pass
        self.p.wait()


def abrir(caso, so, polar):
    """Abre XFOIL, carga y panela el perfil y entra en OPER viscoso con PACC."""
    x = XFoil(caso["dir"], so)
    x.cmd("PLOP")
    x.cmd("G F")
    x.cmd("")
    x.cmd(f"LOAD {caso['geom']}")
    x.cmd("PPAR")
    x.cmd(f"N {caso.get('npan', NPAN)}")
    x.cmd("")
    x.cmd("")
    x.cmd("OPER")
    x.cmd(f"VISC {caso['re']:.0f}")
    x.cmd("VPAR")
    x.cmd(f"N {caso['ncrit']}")
    x.cmd("")
    x.cmd(f"ITER {ITER}")
    x.cmd("PACC")
    x.cmd(polar)
    x.cmd("")
    return x


RES = re.compile(r"a =\s*([-\d.]+)\s+CL =\s*([-\d.]+)\s*\n\s*Cm =\s*([-\d.]+)\s+CD =\s*([-\d.]+)")


def alfa(x, a):
    out = x.cmd(f"ALFA {a:.3f}")
    ok = "Convergence failed" not in out
    m = RES.findall(out)
    cl = float(m[-1][1]) if m else np.nan
    return ok and bool(m), cl


def barrido(caso):
    so = shim()
    os.makedirs(caso["dir"], exist_ok=True)
    tag = caso["tag"]
    log = {"tag": tag, "fallas": [], "rescates": [], "reinicios": 0, "puntos": 0}
    dumps = set(caso.get("dumps", []))
    for rama, objetivos in (("sube", np.arange(0.0, AMAX + 1e-9, DA)),
                            ("baja", np.arange(-DA, AMIN - 1e-9, -DA))):
        polar = f"{tag}_{rama}.pol"
        pp = os.path.join(caso["dir"], polar)
        if os.path.exists(pp):
            os.remove(pp)
        x = abrir(caso, so, polar)
        ultimo = None
        if rama == "baja":
            # arrancar la rama negativa desde una solución convergida en 0 grados
            try:
                ok, _ = alfa(x, 0.0)
                ultimo = 0.0 if ok else None
            except Timeout:
                pass
        for a in objetivos:
            a = round(float(a), 3)
            try:
                ok, cl = alfa(x, a)
                if not ok:
                    # 1) INIT + subpasos desde el último punto bueno
                    x.cmd("INIT")
                    if ultimo is not None:
                        alfa(x, ultimo)
                        for sub in np.linspace(ultimo, a, 5)[1:]:
                            ok, cl = alfa(x, round(float(sub), 4))
                            if not ok:
                                break
                    # 2) más iteraciones e intento directo
                    if not ok:
                        x.cmd("ITER 400")
                        x.cmd("INIT")
                        ok, cl = alfa(x, a)
                        x.cmd(f"ITER {ITER}")
                    if ok:
                        log["rescates"].append(a)
            except Timeout:
                # 3) sesión colgada: reabrir y reanudar desde el último punto bueno
                log["reinicios"] += 1
                x.close()
                x = abrir(caso, so, polar)
                ok = False
                try:
                    if ultimo is not None:
                        alfa(x, ultimo)
                    ok, cl = alfa(x, a)
                except Timeout:
                    x.close()
                    x = abrir(caso, so, polar)
            if ok:
                ultimo = a
                log["puntos"] += 1
                if abs(a - round(a)) < 1e-6 and (not dumps or round(a) in dumps):
                    try:
                        x.cmd(f"DUMP {tag}_a{int(round(a)):+03d}.bl")
                        x.cmd(f"CPWR {tag}_a{int(round(a)):+03d}.cp")
                    except Timeout:
                        pass
            else:
                log["fallas"].append(a)
                try:
                    x.cmd("INIT")
                except Timeout:
                    log["reinicios"] += 1
                    x.close()
                    x = abrir(caso, so, polar)
        try:
            x.cmd("PACC")
            x.cmd("")
            x.cmd("QUIT")
        except Exception:
            pass
        x.close()
    with open(os.path.join(caso["dir"], tag + "_log.json"), "w") as f:
        json.dump(log, f)
    return log


def leer_polar(path):
    filas = []
    if not os.path.exists(path):
        return np.zeros((0, 9))
    with open(path) as f:
        lineas = f.readlines()
    i = next((k for k, l in enumerate(lineas) if l.strip().startswith("------")), None)
    if i is None:
        return np.zeros((0, 9))
    for l in lineas[i + 1:]:
        p = l.split()
        if len(p) >= 9:
            filas.append([float(v) for v in p[:9]])
    return np.array(filas) if filas else np.zeros((0, 9))


def casos_base():
    perfiles = ["placa7", "placa4", "plana3", "clarky", "naca6412", "naca0012"]
    res = [20000, 35000, 50000, 75000, 100000]
    ncs = [9, 5]
    casos = []
    for p, re_, n in itertools.product(perfiles, res, ncs):
        tag = f"{p}_Re{re_//1000}_N{n}"
        casos.append(dict(tag=tag, geom=os.path.join(RAW, p + ".dat"), re=re_, ncrit=n,
                          dir=os.path.join(RAW, "runs", tag)))
    # sensibilidad de la geometría de la placa 7 % (espesor y nariz), Ncrit 9
    for p in ["placa7_t11", "placa7_t20", "placa7_le2"]:
        for re_ in [20000, 50000, 100000]:
            tag = f"{p}_Re{re_//1000}_N9"
            casos.append(dict(tag=tag, geom=os.path.join(RAW, p + ".dat"), re=re_, ncrit=9,
                              dir=os.path.join(RAW, "runs", tag), dumps=[0, 4, 8]))
    # verificación del generador NACA: polar con la geometría interna de XFOIL
    return casos


def main():
    shim()
    casos = casos_base()
    solo = os.environ.get("POLARES_SOLO")
    if solo:
        casos = [c for c in casos if re.fullmatch(solo, c["tag"])]
    t0 = time.time()
    with Pool(NPROC) as pool:
        for log in pool.imap_unordered(barrido, casos):
            print(f"{log['tag']:24s} puntos={log['puntos']:3d} fallas={len(log['fallas']):2d} "
                  f"rescates={len(log['rescates']):2d} reinicios={log['reinicios']}  "
                  f"[{time.time()-t0:6.0f} s]", flush=True)


if __name__ == "__main__":
    main()
