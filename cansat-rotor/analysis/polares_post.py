#!/usr/bin/env python3
"""Posproceso de las polares XFOIL: métricas, tendencias con Re, burbuja laminar y
polares extendidas a +-180 grados para la BEMT.

Entradas: analysis/data/polares_<perfil>_Re<k>[_N5].dat (de polares_xfoil.py) y los
volcados de capa límite en <raw>/capa.
Salidas (analysis/data):
  polares_resumen.dat          métricas por perfil, Re y Ncrit
  polares_alt_<perfil>_Re<k>.dat  puntos biestables (rama de Cl alto)
  polares_repala.dat           Re local a lo largo de la pala
  polares_tend.dat             (Cl/Cd)max y Cl,max frente a Re (formato ancho)
  polares_burbuja.dat          separación, transición y reinserción (placa 7 %, NACA 6412)
  polares_cp_<caso>.dat        Cp(x) en casos seleccionados
  polares_ext_<perfil>_Re<k>.dat   polar extendida (alpha cl cd cm fuente)
  polares_ext_placa7_Re50_2D.dat   variante con C_D,max bidimensional (1,98)

Modelo de la polar extendida (ver capítulo 11):
  * XFOIL en el bloque convergido [a_lo, a_hi] (interpolación lineal en 0,5 grados).
  * a > a_hi: Viterna-Corrigan con C_D,max = 1,11 + 0,018 AR (AR = 3,47), empalmado
    en (a_hi, Cl, Cd), con a_hi = min(fin del bloque convergido, alfa(Cl,max) + 1).
  * a < a_lo: placa plana (Cn = C_D,max sen a) más el desvío en a_lo, que decae con un
    coseno en 12 grados.
  * |a| > 90: flujo invertido, Cl = -0,7 Cl(reflejado) y Cd = Cd(reflejado).
  * Cm: centro de presión que migra de su valor en el empalme a 0,5c (90 grados) y a
    0,75c (180 grados).

Uso: python3 analysis/polares_post.py [directorio_raw]
"""
import os
import sys
import glob
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "analysis", "data")
RAW = sys.argv[1] if len(sys.argv) > 1 else "/tmp/polares_xfoil"
PERFILES = ["placa7", "placa4", "plana3", "clarky", "naca6412", "naca0012"]
RES = [20, 35, 50, 75, 100]
AR = 0.156 / 0.045
CDMAX = 1.11 + 0.018 * AR
CDMAX_2D = 1.98
CL_DISENO = 0.9


def cargar(perfil, re_k, suf=""):
    p = os.path.join(DATA, f"polares_{perfil}_Re{re_k}{suf}.dat")
    if not os.path.exists(p):
        return None
    D = np.loadtxt(p, skiprows=1, ndmin=2)
    return D if len(D) else None


def bloques(a, salto=1.6):
    """Índices de bloques contiguos (huecos de más de `salto` grados los separan; los
    huecos menores, de hasta cinco ángulos sin solución, se interpolan)."""
    cortes = np.where(np.diff(a) > salto + 1e-6)[0]
    ini = np.r_[0, cortes + 1]
    fin = np.r_[cortes, len(a) - 1]
    return list(zip(ini, fin))


def metricas(D):
    a, cl, cd, cm = D[:, 0], D[:, 1], D[:, 2], D[:, 3]
    ld = cl / cd
    i = int(np.argmax(ld))
    blq = [b for b in bloques(a) if b[0] <= i <= b[1]][0]
    # Cl,max dentro del bloque principal (fuera de él XFOIL da ramas de pérdida poco fiables)
    j = blq[0] + int(np.argmax(cl[blq[0]:blq[1] + 1]))
    # Cl,max "cerrado" si después del máximo hay puntos convergidos con Cl menor
    despues = (a > a[j] + 0.4) & (cl < cl[j] - 0.02)
    cerrado = bool(np.any(despues))
    # empalme superior de la polar extendida: 1 grado después de Cl,max, sin salir del bloque
    ahi_ext = min(a[blq[1]], a[j] + 1.0)
    nbi = int(D[:, 9].sum()) if D.shape[1] > 9 else 0
    # punto de diseño Cl = 0,9: primer cruce en el bloque principal
    s = slice(blq[0], blq[1] + 1)
    aa, cc, dd = a[s], cl[s], cd[s]
    k = np.where((cc[:-1] < CL_DISENO) & (cc[1:] >= CL_DISENO))[0]
    if len(k):
        k = k[0]
        f = (CL_DISENO - cc[k]) / (cc[k + 1] - cc[k])
        a09 = aa[k] + f * (aa[k + 1] - aa[k])
        cd09 = dd[k] + f * (dd[k + 1] - dd[k])
        ld09 = CL_DISENO / cd09
    else:
        a09 = ld09 = np.nan
    return dict(n=len(a), amin=a.min(), amax=a.max(), clmax=cl[j], aclmax=a[j],
                cerrado=int(cerrado), ldmax=ld[i], ald=a[i], clld=cl[i], cdld=cd[i],
                cmld=cm[i], cdmin=cd.min(), a09=a09, ld09=ld09,
                alo=a[blq[0]], ahi=a[blq[1]], ahi_ext=ahi_ext, nbi=nbi)


def resumen():
    filas = []
    for p in PERFILES + ["placa7_t11", "placa7_t20"]:
        for r in RES:
            for suf, n in (("", 9), ("_N5", 5)):
                D = cargar(p, r, suf)
                if D is None:
                    continue
                m = metricas(D)
                filas.append((p, r, n, m))
    with open(os.path.join(DATA, "polares_resumen.dat"), "w") as f:
        f.write("perfil Re ncrit n amin amax clmax aclmax cerrado ldmax ald clld cdld cmld "
                "cdmin a09 ld09 alo ahi ahiext nbi\n")
        for p, r, n, m in filas:
            f.write(f"{p} {r*1000} {n} {m['n']} {m['amin']:.2f} {m['amax']:.2f} "
                    f"{m['clmax']:.3f} {m['aclmax']:.2f} {m['cerrado']} {m['ldmax']:.1f} "
                    f"{m['ald']:.2f} {m['clld']:.3f} {m['cdld']:.4f} {m['cmld']:.3f} "
                    f"{m['cdmin']:.4f} {m['a09']:.2f} {m['ld09']:.1f} {m['alo']:.2f} "
                    f"{m['ahi']:.2f} {m['ahi_ext']:.2f} {m['nbi']}\n")
    # formato ancho para las figuras de tendencia
    with open(os.path.join(DATA, "polares_tend.dat"), "w") as f:
        cols = [f"ld_{p}" for p in PERFILES] + [f"cl_{p}" for p in PERFILES] + \
               ["ld_placa7_N5", "ld_naca6412_N5", "cl_placa7_N5", "cl_naca6412_N5"]
        f.write("Re " + " ".join(cols) + "\n")
        idx = {(p, r, n): m for p, r, n, m in filas}
        for r in RES:
            v = []
            for key in ("ldmax", "clmax"):
                for p in PERFILES:
                    m = idx.get((p, r, 9))
                    v.append(m[key] if m else np.nan)
            for key in ("ldmax", "clmax"):
                for p in ("placa7", "naca6412"):
                    m = idx.get((p, r, 5))
                    v.append(m[key] if m else np.nan)
            f.write(f"{r*1000} " + " ".join("nan" if np.isnan(x) else f"{x:.3f}" for x in v) + "\n")
    return filas


# ------------------------------------------------------------------ capa límite
def leer_bl(path):
    filas = []
    with open(path) as f:
        for l in f:
            if l.startswith("#"):
                continue
            p = l.split()
            if len(p) >= 8:
                filas.append([float(x) for x in p[:8]])
    B = np.array(filas)
    ue = B[:, 3]
    k = int(np.argmax(ue <= 0))           # primera estación del intradós
    sup = B[:k][::-1]                     # extradós ordenado desde el borde de ataque
    return sup  # s x y ue dstar theta cf H


def burbuja(sup):
    """Separación laminar (primer Cf<0 desde el BA), reinserción, separación de fuga."""
    x, cf = sup[:, 1], sup[:, 6]
    neg = cf < 0
    xs = xr = xte = np.nan
    i0 = np.argmax(x > 0.002)
    idx = np.where(neg[i0:])[0]
    if len(idx):
        i = i0 + idx[0]
        xs = x[i]
        j = np.where(~neg[i:])[0]
        if len(j):
            xr = x[i + j[0]]
            # separación turbulenta que llega al borde de fuga
            k = np.where(neg[i + j[0]:])[0]
            if len(k) and np.all(neg[i + j[0] + k[0]:]):
                xte = x[i + j[0] + k[0]]
        else:
            xr = np.nan  # no se reinserta
    return xs, xr, xte


def capa():
    d = os.path.join(RAW, "capa")
    filas = []
    for path in sorted(glob.glob(os.path.join(d, "*.bl"))):
        tag = os.path.basename(path)[:-3]
        if len(tag.split("_")) != 4:
            continue  # volcado residual sin etiqueta
        perfil, rek, nc, al = tag.split("_")
        sup = leer_bl(path)
        xs, xr, xte = burbuja(sup)
        # transición: de la polar fusionada en ese ángulo (si existe)
        suf = "" if nc == "N9" else "_N5"
        D = cargar(perfil, int(rek[2:]), suf)
        a = float(al[1:])
        # transición del extradós: de la misma corrida que generó el volcado
        xt = np.nan
        pt = os.path.join(d, tag + ".pt")
        if os.path.exists(pt):
            xt = float(np.loadtxt(pt, ndmin=2)[0, 5])
        with open(os.path.join(DATA, f"polares_cf_{tag}.dat"), "w") as f:
            f.write("x cf H\n")
            for r in sup:
                if r[1] > 0.0005:
                    f.write(f"{r[1]:.5f} {r[6]:.6f} {r[7]:.4f}\n")
        filas.append((perfil, int(rek[2:]), int(nc[1:]), a, xs, xt, xr, xte))
        cp = os.path.join(d, tag + ".cp")
        if os.path.exists(cp) and (abs(a - 4) < 1e-6 or perfil == "placa7"):
            C = np.loadtxt(cp, comments="#")
            with open(os.path.join(DATA, f"polares_cp_{tag}.dat"), "w") as f:
                f.write("x cp\n")
                for x, c in C[:, :2]:
                    f.write(f"{x:.5f} {c:.4f}\n")
    with open(os.path.join(DATA, "polares_burbuja.dat"), "w") as f:
        f.write("perfil Re ncrit alpha xs xt xr xte\n")
        for r in sorted(filas):
            f.write(f"{r[0]} {r[1]*1000} {r[2]} {r[3]:.1f} " +
                    " ".join("nan" if np.isnan(v) else f"{v:.4f}" for v in r[4:]) + "\n")
    return filas


# ------------------------------------------------------------------ polar extendida
def viterna(a_deg, a_s, cl_s, cd_s, cdmax):
    a, s = np.radians(a_deg), np.radians(a_s)
    B2 = (cd_s - cdmax * np.sin(s) ** 2) / np.cos(s)
    A2 = (cl_s - cdmax * np.sin(s) * np.cos(s)) * np.sin(s) / np.cos(s) ** 2
    cl = cdmax / 2 * np.sin(2 * a) + A2 * np.cos(a) ** 2 / np.sin(a)
    cd = cdmax * np.sin(a) ** 2 + B2 * np.cos(a)
    return cl, cd


def extendida(perfil, re_k, cdmax=CDMAX, suf_out=""):
    D = cargar(perfil, re_k)
    if D is None:
        return None
    m = metricas(D)
    a_lo, a_hi = m["alo"], m["ahi_ext"]
    sel = (D[:, 0] >= a_lo - 1e-6) & (D[:, 0] <= a_hi + 1e-6)
    a_x, cl_x, cd_x, cm_x = D[sel, 0], D[sel, 1], D[sel, 2], D[sel, 3]
    cd_min = cd_x.min()

    def base(al):
        """Polar en (-90, 90]: XFOIL + Viterna-Corrigan + placa plana. Devuelve cl cd cm fuente."""
        if a_lo <= al <= a_hi:
            cl = np.interp(al, a_x, cl_x)
            cd = np.interp(al, a_x, cd_x)
            cm = np.interp(al, a_x, cm_x)
            return cl, cd, cm, 0
        if al > a_hi:
            cl, cd = viterna(al, a_hi, cl_x[-1], cd_x[-1], cdmax)
            cd = max(cd, cd_min)
            cn_s = cl_x[-1] * np.cos(np.radians(a_hi)) + cd_x[-1] * np.sin(np.radians(a_hi))
            xcp_s = 0.25 - cm_x[-1] / cn_s
            xcp = xcp_s + (0.5 - xcp_s) * (al - a_hi) / (90 - a_hi)
            fuente = 1
        else:
            ar = np.radians(al)
            cl_fp, cd_fp = cdmax * np.sin(ar) * np.cos(ar), cdmax * np.sin(ar) ** 2
            arl = np.radians(a_lo)
            dcl = cl_x[0] - cdmax * np.sin(arl) * np.cos(arl)
            dcd = cd_x[0] - cdmax * np.sin(arl) ** 2
            w = 0.5 * (1 + np.cos(np.pi * min((a_lo - al) / 12.0, 1.0)))
            cl, cd = cl_fp + w * dcl, max(cd_fp + w * dcd, cd_min)
            cn_s = cl_x[0] * np.cos(arl) + cd_x[0] * np.sin(arl)
            xcp_s = 0.25 - cm_x[0] / cn_s if abs(cn_s) > 0.05 else 0.25
            xcp = xcp_s + (0.5 - xcp_s) * (a_lo - al) / (90 + a_lo)
            fuente = 2
        ar = np.radians(al)
        cn = cl * np.cos(ar) + cd * np.sin(ar)
        return cl, cd, -cn * (xcp - 0.25), fuente

    filas = []
    for al in np.round(np.arange(-180, 180.001, 0.5), 3):
        if -90 < al <= 90:
            cl, cd, cm, src = base(al)
        else:
            ref = 180 - al if al > 90 else -180 - al     # ángulo reflejado en (-90, 90]
            clr, cdr, _, _ = base(ref)
            cl, cd, src = -0.7 * clr, cdr, 3
            xcp = 0.5 + 0.25 * (abs(al) - 90) / 90
            ar = np.radians(al)
            cn = cl * np.cos(ar) + cd * np.sin(ar)
            cm = -cn * (xcp - 0.25)
        filas.append((al, cl, cd, cm, src))
    nombre = f"polares_ext_{perfil}_Re{re_k}{suf_out}.dat"
    with open(os.path.join(DATA, nombre), "w") as f:
        f.write("alpha cl cd cm fuente\n")
        for r in filas:
            f.write(f"{r[0]:.1f} {r[1]:.4f} {r[2]:.4f} {r[3]:.4f} {r[4]}\n")
    return a_lo, a_hi, cdmax


def alternativas():
    """Puntos biestables (rama de Cl alto) para dibujarlos aparte."""
    for p in PERFILES + ["placa7_t11", "placa7_t20"]:
        for r in RES:
            for suf in ("", "_N5"):
                D = cargar(p, r, suf)
                if D is None or D.shape[1] < 12:
                    continue
                B = D[D[:, 9] > 0]
                with open(os.path.join(DATA, f"polares_alt_{p}_Re{r}{suf}.dat"), "w") as f:
                    f.write("alpha cl cd clalt cdalt\n")
                    if len(B) == 0:
                        f.write("nan nan nan nan nan\n")
                    for b in B:
                        f.write(f"{b[0]:.2f} {b[1]:.4f} {b[2]:.5f} {b[10]:.4f} {b[11]:.5f}\n")


def re_pala(omega=120.0, R=0.200, e=0.044, c=0.045, nu=1.5e-5, V=0.0, vi=0.0):
    """Re local a lo largo de la pala (velocidad relativa con la componente axial)."""
    with open(os.path.join(DATA, "polares_repala.dat"), "w") as f:
        f.write("r re re_lo re_hi\n")
        for r in np.linspace(e, R, 33):
            w = np.hypot(omega * r, V)
            f.write(f"{r:.4f} {w*c/nu:.0f} {np.hypot(0.8*omega*r, V)*c/nu:.0f} "
                    f"{np.hypot(1.2*omega*r, V)*c/nu:.0f}\n")


def para_graficar():
    """Copias para pgfplots con fila nan en cada hueco (> 0,3 grados), columna ld = Cl/Cd y
    phi = atan(Cd/Cl) en grados (ángulo de entrada neutro, ec. de autorrotación)."""
    for p in PERFILES + ["placa7_t11", "placa7_t20"]:
        for r in RES:
            for suf in ("", "_N5"):
                D = cargar(p, r, suf)
                if D is None:
                    continue
                with open(os.path.join(DATA, f"polares_g_{p}_Re{r}{suf}.dat"), "w") as f:
                    f.write("alpha cl cd cm ld phi\n")
                    for k, d in enumerate(D):
                        if k and d[0] - D[k - 1, 0] > 0.3:
                            f.write("nan nan nan nan nan nan\n")
                        ld = d[1] / d[2]
                        phi = np.degrees(np.arctan2(d[2], d[1])) if d[1] > 0.05 else np.nan
                        f.write(f"{d[0]:.2f} {d[1]:.4f} {d[2]:.5f} {d[3]:.4f} {ld:.2f} "
                                + ("nan" if np.isnan(phi) else f"{phi:.3f}") + "\n")


def convergencia():
    """Resumen de convergencia de cada caso (de los log.json de polares_xfoil.py)."""
    import json
    filas = []
    for path in sorted(glob.glob(os.path.join(RAW, "runs", "*", "log.json"))):
        L = json.load(open(path))
        p, rek, nc = L["tag"].rsplit("_", 2)
        fal = L.get("faltan", [])
        filas.append((p, int(rek[2:]), int(nc[1:]), L["n_ok"], L["n_grilla"], len(fal),
                      len(L.get("biestables", [])), L.get("atipicos", 0), int(L.get("rescate", 0)),
                      L.get("colgados", 0), " ".join(f"{a:g}" for a in fal) or "-"))
    with open(os.path.join(DATA, "polares_conv.dat"), "w") as f:
        f.write("perfil Re ncrit ok grilla faltan biest atip rescate colgados angulos\n")
        for r in filas:
            f.write(" ".join(str(v) for v in r[:10]) + " " + r[10].replace(" ", ",") + "\n")
    return filas


def main():
    convergencia()
    para_graficar()
    alternativas()
    re_pala()
    filas = resumen()
    print(f"{'perfil':11s} {'Re':>6s} N  n  [amin,amax]  Clmax@a (c)  L/Dmax@a  Cl  Cm  a09 LD09")
    for p, r, n, m in filas:
        print(f"{p:11s} {r*1000:6d} {n} {m['n']:2d} [{m['amin']:5.2f},{m['amax']:5.2f}] "
              f"{m['clmax']:.3f}@{m['aclmax']:5.2f} ({m['cerrado']}) {m['ldmax']:5.1f}@{m['ald']:5.2f} "
              f"{m['clld']:.3f} {m['cmld']:.3f} {m['a09']:5.2f} {m['ld09']:5.1f}  blq[{m['alo']},{m['ahi']}] ext<={m['ahi_ext']} bi={m['nbi']}")
    if os.path.isdir(os.path.join(RAW, "capa")):
        for r in capa():
            print("capa", r)
    print(f"C_D,max (Viterna-Corrigan, AR = {AR:.2f}) = {CDMAX:.3f}")
    for p in ("placa7", "plana3", "placa4", "naca6412"):
        for r in RES:
            e = extendida(p, r)
            if e:
                print(f"ext {p} Re{r}: XFOIL en [{e[0]}, {e[1]}]")
    extendida("placa7", 50, cdmax=CDMAX_2D, suf_out="_2D")


if __name__ == "__main__":
    main()
