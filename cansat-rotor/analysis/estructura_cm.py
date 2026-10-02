#!/usr/bin/env python3
"""Coeficiente de momento de la placa curvada al 7 % con XFOIL (corrida indicativa).

Usa la geometría de analysis/data/polares_geom_placa7.dat. Re = 36 000 (media pala),
Ncrit = 9, alfa de 0 a 6 grados; y el caso no viscoso como cota de teoría de perfil
delgado (Cm_c/4 = -pi f/c). Escribe analysis/data/estructura_cm.dat.
Requiere /usr/bin/xfoil; si existe la biblioteca LD_PRELOAD que neutraliza las
trampas de punto flotante (ver polares_xfoil.py), la usa.
"""
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GEOM = os.path.join(HERE, "data", "polares_geom_placa7.dat")
OUT = os.path.join(HERE, "data", "estructura_cm.dat")
SHIM = "/tmp/polares_xfoil/libnofpe.so"
ALFAS = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]


def run(re_num):
    with tempfile.TemporaryDirectory() as d:
        with open(GEOM) as f:
            lines = f.read().splitlines()[1:]
        open(os.path.join(d, "p.dat"), "w").write("\n".join(lines) + "\n")
        cmd = "PLOP\nG F\n\nLOAD p.dat\nplaca7\nPPAR\nN 240\n\n\nOPER\n"
        if re_num:
            cmd += f"VISC {re_num}\nITER 300\n"
        cmd += "PACC\npol.txt\n\n" + "".join(f"ALFA {a}\n" for a in ALFAS) + "PACC\n\nQUIT\n"
        env = dict(os.environ)
        if os.path.exists(SHIM):
            env["LD_PRELOAD"] = SHIM
        try:
            subprocess.run(["xfoil"], input=cmd.encode(), cwd=d, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=200)
        except subprocess.TimeoutExpired:
            pass
        res = {}
        p = os.path.join(d, "pol.txt")
        if os.path.exists(p):
            for ln in open(p).read().splitlines()[12:]:
                v = ln.split()
                # descarta puntos no físicos (convergencia falsa, Cl casi nulo)
                if len(v) >= 5 and float(v[1]) > 0.2:
                    res[float(v[0])] = (float(v[1]), float(v[4]))
        return res


if __name__ == "__main__":
    visc = run(36000)
    inv = run(0)
    with open(OUT, "w") as f:
        f.write("alfa Cl_visc Cm_visc Cl_inv Cm_inv\n")
        for a in ALFAS:
            cv, mv = visc.get(float(a), (float("nan"),) * 2)
            ci, mi = inv.get(float(a), (float("nan"),) * 2)
            f.write(f"{a:.1f} {cv:.4f} {mv:.4f} {ci:.4f} {mi:.4f}\n")
    print(open(OUT).read())
