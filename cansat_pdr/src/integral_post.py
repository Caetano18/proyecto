"""Margenes del diseno combinado (cuerpo integral) a partir de modal + estatico de 1 G (integral.py).

Metodo (PDR, conservador):
  - tensiones de 1 G en x, y, z del caso estatico (CalculiX), por pieza; se excluyen los elementos que tocan el apoyo
  - lijadora (CanSat parado, base fija): excitacion lateral (y, z) del plato orbital, a(f) = 29 G (f/233)^2.  Si el modo lateral
    queda debajo de 233 Hz, el arranque/frenado lo cruza: respuesta transitoria de un oscilador (lsim) con el modo y zeta;
    si queda encima, marcha sostenida a 233 Hz.  Aceleracion equivalente estatica a_eq = max |respuesta| (en G).
  - axial de la lijadora (plato que no es perfectamente plano): 29 G cuasi-estatico, por si acaso
  - CE-15: 15 G cuasi-estatico; CH-30: semiseno de 30 G, factor de espectro de choque 1,7 (maximax para f*tau >= 1)
  MS = sigma_adm / (FS * sigma) - 1 con von Mises (y sigma_x entre capas en piezas impresas).
Uso: python3 integral_post.py <carpeta> <tag> [salida.json]
"""
import sys
import os
import json
import numpy as np
from scipy.signal import lsim, lti
import params as P
import fe_post as FP
import integral as I

G0 = 9.80665
ZETA = P.ZETA


def lijadora_aeq(fn, z=ZETA, t_sub=1.0, t_baj=2.0, hold=5.0):
    wn = 2 * np.pi * fn
    A = lambda f: 29.0 * (f / 233.0) ** 2
    if fn > 240:
        r = 233.0 / fn
        return A(233.0) / abs(1 - r * r), 233.0
    sys_ = lti([2 * z * wn, wn ** 2], [1.0, 2 * z * wn, wn ** 2])      # aceleracion absoluta / aceleracion de base
    dt = 1 / 40000
    t = np.arange(0, t_sub + hold + t_baj + 0.3, dt)
    t1, t2 = t_sub, t_sub + hold
    f = np.where(t < t1, 233 * t / t1, np.where(t < t2, 233.0, np.clip(233 * (1 - (t - t2) / t_baj), 0, None)))
    ph = 2 * np.pi * np.cumsum(f) * dt
    a = A(f) * np.sin(ph)
    _, y, _ = lsim(sys_, a, t)
    i = int(np.argmax(np.abs(y)))
    return float(np.abs(y).max()), float(f[i])


def vm(s):
    xx, yy, zz, xy, yz, zx = [s[..., k] for k in range(6)]
    return np.sqrt(0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3 * (xy ** 2 + yz ** 2 + zx ** 2))


def main(wd, tag, out=None):
    I.materiales()
    R = json.load(open(os.path.join(wd, f"resumen_{tag}.json")))
    z = np.load(os.path.join(wd, f"malla_{tag}.npz"))
    xyz, els, ep = z["xyz"], z["els"], z["epart"]
    partes = json.load(open(os.path.join(wd, f"partes_{tag}.json")))
    ever, S = FP.leer_dat_S(os.path.join(wd, f"estat_{tag}.dat"))
    base = set(np.where(np.abs(xyz[:, 0] - P.CT_X[0]) < 1e-4)[0].tolist())
    toca = np.array([any(n in base for n in e) for e in els[ever][:, :4]])
    # modos laterales: primero con mas de 20 % de masa en y y en z
    mt = (R["masa_sin_lastre"] + max(R["lastre"], 0.0)) / 1e6
    modos = [dict(f=f, meff_frac=[c / mt for c in m]) for f, m in I.resumen_modal(os.path.join(wd, f"modal_{tag}.dat"))]
    flat = {}
    for e, k in (("y", 1), ("z", 2)):
        m = next((m for m in modos if m["meff_frac"][k] > 0.2), None)
        flat[e] = m["f"] if m else None
    aeq = {}
    for e in ("y", "z"):
        aeq[e] = lijadora_aeq(flat[e]) if flat[e] else (29.0, 233.0)
    casos = {"CE-15": {"x": 15.0, "y": 15.0, "z": 15.0},
             "Lijadora (parado)": {"x": 29.0, "y": aeq["y"][0], "z": aeq["z"][0]},
             "CH-30": {"x": 51.0, "y": 51.0, "z": 51.0}}
    M = P.MAT
    res = dict(tag=tag, carcasa=R["carcasa"], largueros=R["largueros"], masa_sin_lastre=R["masa_sin_lastre"],
               lastre=R["lastre"], f_lateral=flat, aeq_lijadora={e: aeq[e][0] for e in aeq},
               modos=[dict(f=m["f"], meff=m["meff_frac"]) for m in modos], margenes={})
    for pi, p in enumerate(partes):
        filas = np.where((ep[ever] == pi) & ~toca)[0]
        if len(filas) == 0:
            continue
        mat = p["mat"]
        if mat == "AL6061":
            crit = [("von Mises", "vm", M[mat]["Sy"], M[mat]["FS"])]
        elif mat in ("GFRP", "GFRP_INF"):
            crit = [("sigma_x fibra", "sx", M[mat]["Sut"], M[mat]["FS"]), ("von Mises", "vm", M[mat]["Sut"], M[mat]["FS"])]
        elif mat == "CFRP":
            crit = [("sigma_x fibra", "sx", M[mat]["Suc"], M[mat]["FS"])]
        else:     # impresos: carcasa impresa de pie (capas normales a x), mamparos acostados (capas normales a x)
            crit = [("von Mises", "vm", M[mat]["Sut"], M[mat]["FS"]), ("sigma_x entre capas", "sx", M[mat]["Sut_z"], M[mat]["FS"])]
        for caso, fac in casos.items():
            peor = None
            for d, e in enumerate("xyz"):
                s = S[d][filas].mean(axis=1)                 # promedio de los 4 puntos de Gauss
                for cn, cual, adm, fs in crit:
                    v = vm(s) if cual == "vm" else np.abs(s[:, 0])
                    sig = float(np.percentile(v, 99.9)) * fac[e]     # p99,9: sin el pico de un solo elemento
                    sigmax = float(v.max()) * fac[e]
                    ms_ = adm / (fs * sig) - 1
                    if peor is None or ms_ < peor["MS"]:
                        peor = dict(MS=ms_, MS_max=adm / (fs * sigmax) - 1, sigma=sig, eje=e, criterio=cn)
            res["margenes"].setdefault(p["nombre"], {})[caso] = peor
    print(f"[{tag}] carcasa {R['carcasa']} largueros {R['largueros']}: masa sin lastre {R['masa_sin_lastre']:.1f} g, "
          f"lastre {R['lastre']:.1f} g")
    print(f"   modo lateral y {flat['y']:.0f} Hz, z {flat['z']:.0f} Hz; lijadora a_eq y {aeq['y'][0]:.0f} G (a {aeq['y'][1]:.0f} Hz), "
          f"z {aeq['z'][0]:.0f} G")
    for n, d in res["margenes"].items():
        print(f"   {n[:34]:34s} " + "  ".join(f"{c}: {v['MS']:+.2f} ({v['eje']}, {v['criterio'][:8]}; max {v['MS_max']:+.2f})"
                                               for c, v in d.items()))
    if out:
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
