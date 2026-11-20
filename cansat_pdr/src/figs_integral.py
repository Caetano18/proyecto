"""Figuras FEM del diseno combinado (cuerpo integral): malla, modos y mapas de utilizacion, carcasa PETG (v2) vs laminada (rev. E).

Uso: python3 figs_integral.py <carpeta PETG> <tag PETG> <carpeta laminado> <tag laminado> <carpeta de figuras>
Usa las salidas de integral.py (malla, partes, modal y estatico de 1 G) y de integral_post.py (aceleracion equivalente).
"""
import os
import sys
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import params as P
import fe_post as FP
import integral as I
from figs_fea import malla_pv, cortar, vtk, panel, barra_util, CM_U, CLIM, SIN_MARGEN

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5})
COL = {"PETG": (0.93, 0.90, 0.80), "GFRP": (0.80, 0.90, 0.80), "GFRP_INF": (0.22, 0.22, 0.24), "PETG40": (0.45, 0.50, 0.60),
       "AL6061": (0.75, 0.75, 0.78)}
NOM = {"PETG": "Carcasa PETG 2 mm", "GFRP": "Carcasa vidrio-epoxi 0,6 mm", "GFRP_INF": "Carcasa carbono-epoxi 0,8 mm",
       "PETG40": "Mamparos PETG (40 % de relleno)", "AL6061": "Varillas M3 Al 6061"}


def cargar(wd, tag):
    I.materiales()
    z = np.load(os.path.join(wd, f"malla_{tag}.npz"))
    xyz, els, ep = z["xyz"], z["els"], z["epart"]
    partes = json.load(open(os.path.join(wd, f"partes_{tag}.json")))
    phi = np.array(FP.leer_frd_U(os.path.join(wd, f"modal_{tag}.frd"), len(xyz)), dtype=float)
    modos = I.resumen_modal(os.path.join(wd, f"modal_{tag}.dat"))
    ever, S = FP.leer_dat_S(os.path.join(wd, f"estat_{tag}.dat"))
    mg = json.load(open(os.path.join(wd, f"margenes_{tag}.json")))
    mat = np.array([p["mat"] for p in partes])[ep]
    return dict(xyz=xyz, els=els, ep=ep, mat=mat, phi=phi, modos=modos, ever=ever, S=S, mg=mg,
                masa=sum(p["masa"] for p in partes))


def utilizacion(M, d, fac):
    """FS*sigma/sigma_adm por elemento (criterio mas desfavorable), caso de 1 G en la direccion d escalado por fac."""
    Mt = P.MAT
    s = M["S"][d].mean(axis=1) * fac
    xx, yy, zz, xy, yz, zx = [s[:, k] for k in range(6)]
    vm = np.sqrt(0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3 * (xy ** 2 + yz ** 2 + zx ** 2))
    mat = M["mat"][M["ever"]]
    u = np.zeros(len(vm))
    for m in np.unique(mat):
        k = mat == m
        c = Mt[m]
        adm = c.get("Sy", c.get("Sut")) / c["FS"]
        u[k] = vm[k] / adm
        if m in ("PETG", "PETG40"):
            u[k] = np.maximum(u[k], np.abs(xx[k]) / (c["Sut_z"] / c["FS"]))
        if m in ("GFRP", "GFRP_INF"):
            u[k] = np.maximum(u[k], np.abs(xx[k]) / (c["Sut"] / c["FS"]))
    base = set(np.where(np.abs(M["xyz"][:, 0] - P.CT_X[0]) < 1e-4)[0].tolist())
    toca = np.array([any(n in base for n in e) for e in M["els"][M["ever"]][:, :4]])
    u[toca] = np.nan                               # apoyo: singularidad del empotramiento
    return u


def capa_u(M, u):
    g = malla_pv(M["xyz"], M["els"], M["ever"])
    g.cell_data["u"] = np.clip(np.nan_to_num(u, nan=CLIM[0]), CLIM[0] * 1.001, None)
    g = g.cell_data_to_point_data()
    return [dict(grid=cortar(g), scalars="u", cmap=CM_U, clim=CLIM, log=True, above=SIN_MARGEN)]


def main(wa, ta, wb, tb, out):
    tmp = os.path.join(out, "_tmp_int")
    os.makedirs(tmp, exist_ok=True)
    A, B = cargar(wa, ta), cargar(wb, tb)

    # -------------------------------------------- malla por material (laminado) + PETG
    fig = plt.figure(figsize=(11.0, 4.6))
    for k, (M, tit) in enumerate(((A, "v2: carcasa PETG de 2 mm"), (B, "Rev. E: carcasa laminada"))):
        g = malla_pv(M["xyz"], M["els"])
        g.cell_data["rgb"] = (np.array([COL.get(m, (0.7, 0.7, 0.7)) for m in M["mat"]]) * 255).astype(np.uint8)
        vtk(f"{tmp}/malla_{k}.png", [dict(grid=cortar(g), rgb=True, edges=True, lineas=False)], size=(1800, 1250))
        panel(fig.add_axes([0.005 + 0.5 * k, 0.17, 0.49, 0.75]), f"{tmp}/malla_{k}.png",
              f"{tit}: {len(M['els']):,} tetraedros".replace(",", "."))
    pres = [m for m in ("PETG", "GFRP_INF", "GFRP", "PETG40", "AL6061")]
    fig.legend(handles=[Patch(fc=COL[m], ec="0.3", label=NOM[m]) for m in pres], loc="lower center", ncol=3, fontsize=9.5,
               frameon=False)
    fig.savefig(f"{out}/v3_malla.png", dpi=200)
    plt.close(fig)

    # -------------------------------------------- modos laterales (2 x 2)
    fig = plt.figure(figsize=(11.0, 7.8))
    for r, (M, nom) in enumerate(((A, "v2 · PETG 2 mm"), (B, "Rev. E · laminado"))):
        g0 = cortar(malla_pv(M["xyz"], M["els"]))
        mt = M["masa"] / 1e6
        for c in range(2):
            U = M["phi"][c]
            amp = np.linalg.norm(U, axis=1)
            gm = malla_pv(M["xyz"], M["els"])
            gm.point_data["a"] = amp / amp.max()
            gm.points = gm.points + U * (14.0 / amp.max())
            vtk(f"{tmp}/modo_{r}{c}.png", [dict(grid=cortar(gm), scalars="a", cmap="viridis", clim=(0, 1), n=10),
                                           dict(grid=g0, color=(1, 1, 1), opacity=0.0, col_linea=(0.55, 0.55, 0.55),
                                                ancho_linea=0.8)], size=(1700, 1150))
            f, me = M["modos"][c]
            eje = "xyz"[int(np.argmax(me))]
            ax = fig.add_axes([0.01 + 0.5 * c, 0.55 - 0.44 * r, 0.48, 0.39])
            panel(ax, f"{tmp}/modo_{r}{c}.png",
                  f"{nom}\nmodo {c + 1}: {f:.0f} Hz · lateral {eje} · {100 * max(me) / mt:.0f} % de la masa")
    cax = fig.add_axes([0.30, 0.075, 0.40, 0.016])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 1), cmap=plt.get_cmap("viridis", 10)), cax=cax,
                      orientation="horizontal")
    cb.set_label("Desplazamiento modal normalizado (deformada amplificada; en gris, sin deformar)", fontsize=10)
    fig.savefig(f"{out}/v3_modos.png", dpi=200)
    plt.close(fig)

    # -------------------------------------------- mapas de utilizacion: lijadora (y) y choque (z)
    fig = plt.figure(figsize=(11.0, 7.6))
    casos = (("lijadora, CanSat parado (lateral y)", 1, lambda M: M["mg"]["aeq_lijadora"]["y"]),
             ("choque de 30 G (lateral z, 51 G)", 2, lambda M: 51.0))
    for r, (tit, d, fac) in enumerate(casos):
        for c, (M, nom) in enumerate(((A, "v2 · PETG 2 mm"), (B, "Rev. E · laminado"))):
            u = utilizacion(M, d, fac(M))
            vtk(f"{tmp}/u_{r}{c}.png", capa_u(M, u), size=(1700, 1150))
            p999 = np.nanpercentile(u, 99.9)
            ax = fig.add_axes([0.01 + 0.5 * c, 0.56 - 0.43 * r, 0.48, 0.38])
            panel(ax, f"{tmp}/u_{r}{c}.png", f"{nom}: {tit}"
                  + (f", {fac(M):.0f} G" if d == 1 else "") + f"\nmáx. (p99,9) = {p99_txt(p999)}")
    barra_util(fig, [0.22, 0.075, 0.56, 0.018])
    fig.savefig(f"{out}/v3_mapas.png", dpi=200)
    plt.close(fig)
    print("figuras FEM del diseno combinado ok")


def p99_txt(x):
    return f"{x:.2f}".replace(".", ",") + (" (sin margen)" if x > 1 else "")


if __name__ == "__main__":
    main(*sys.argv[1:6])
