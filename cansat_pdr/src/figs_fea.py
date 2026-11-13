"""Figuras del analisis estructural.
Uso: python3 figs_fea.py <carpeta_fea> <tag> <res.json> <res.npz> <ala.npz> <carpeta_figs>

Mapas: indice de utilizacion FS*sigma/sigma_adm (cada elemento contra el admisible de su material), suavizado a
nodos, en escala logaritmica de 0,01 a 1; magenta = sin margen.  Modelo cortado por el plano y = 0.
"""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
import pyvista as pv
import params as P
from viz import recortar

pv.OFF_SCREEN = True
plt.rcParams.update({"font.family": "Inter", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "0.88", "grid.linewidth": 0.6, "axes.linewidth": 0.9,
                     "legend.frameon": False, "savefig.dpi": 230, "lines.linewidth": 1.9, "axes.titlesize": 12,
                     "axes.titleweight": "bold", "axes.labelsize": 11})
AZUL, ROJO, VERDE, NAR, VIOL, GRIS = "#2f3192", "#c0392b", "#1a8a55", "#e67e22", "#7d3c98", "#555555"
COL = [AZUL, ROJO, VERDE, NAR, VIOL, "#008b8b", "#8d6e63", "#222222"]
EJES = "xyz"
NOM_EJE = {"x": "X (axial)", "y": "Y (lateral)", "z": "Z (lateral)"}
ADM_MAT = {"LWPLA": 14.0 / 2, "PA12CF": 65.0 / 2, "G10": 280.0 / 1.5, "CFRP": 900.0 / 1.5, "EQ_PCB": 280.0 / 1.5,
           "A2-70": 450.0 / 1.25}
MATS = [("LWPLA", "LW-PLA (tubo)", (0.93, 0.93, 0.86)), ("PA12CF", "PA12-CF (cuadernas, tapa)", (0.36, 0.38, 0.42)),
        ("G10", "G10 (paneles, bandeja)", (0.55, 0.70, 0.42)), ("CFRP", "CFRP (largueros)", (0.12, 0.12, 0.14)),
        ("EQ_PCB", "FR-4 (placas)", (0.05, 0.47, 0.27)), ("A2-70", "Inox (llave)", (0.78, 0.78, 0.82)),
        ("EQ_BAT", "Batería", (0.16, 0.38, 0.78)), ("EQ_BLK", "Masas de equipo", (0.90, 0.55, 0.18)),
        ("EQ_BOOM", "Botalón", (0.25, 0.20, 0.20)), ("ELAST", "Elastómero", (0.95, 0.85, 0.25))]
COL_MAT = {k: c for k, _, c in MATS}
COL_MAT.update({"PAD_A": COL_MAT["ELAST"], "PAD_B": COL_MAT["ELAST"], "ELAST_X": COL_MAT["ELAST"]})
CAM = ((-1.0, -1.35, 0.8), (0, 0, 1))
NB = 12
CM_U = ListedColormap(plt.get_cmap("turbo")(np.linspace(0.03, 0.93, NB)))
SIN_MARGEN = (0.80, 0.0, 0.75)
CM_U.set_over(SIN_MARGEN)
CLIM = (0.01, 1.0)


def malla_pv(xyz, els, idx=None):
    e = els if idx is None else els[idx]
    cells = np.hstack([np.full((len(e), 1), 4), e[:, :4]]).ravel()
    return pv.UnstructuredGrid(cells, np.full(len(e), pv.CellType.TETRA), xyz.astype(float))


def cortar(g):
    return g.clip(normal=(0, -1, 0), origin=(0, 0.01, 0), invert=True)


def vtk(path, capas, cam=CAM, zoom=1.5, size=(2000, 1300), foco=None, marcas=None, lineas=True):
    """capas: lista de dict(grid, scalars|color|rgb, cmap, clim, log, edges).  foco = (punto, semialto en mm)."""
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    for c in capas:
        g = c["grid"]
        if g.n_cells == 0:
            continue
        kw = dict(lighting=True, ambient=0.38, diffuse=0.72, specular=0.08, show_edges=c.get("edges", False),
                  edge_color=(0.2, 0.2, 0.2), line_width=0.35, show_scalar_bar=False)
        if "scalars" in c:
            pl.add_mesh(g, scalars=c["scalars"], cmap=c["cmap"], clim=c["clim"], log_scale=c.get("log", False),
                        n_colors=c.get("n", NB), above_color=c.get("above"), nan_color=(0.85, 0.85, 0.85), **kw)
        elif c.get("rgb"):
            pl.add_mesh(g, scalars="rgb", rgb=True, **kw)
        else:
            pl.add_mesh(g, color=c.get("color", (0.86, 0.86, 0.86)), opacity=c.get("opacity", 1.0), **kw)
        if lineas and c.get("lineas", True):
            fe = g.extract_surface(algorithm="dataset_surface").extract_feature_edges(feature_angle=38)
            if fe.n_points:
                pl.add_mesh(fe, color=c.get("col_linea", (0.12, 0.12, 0.14)), line_width=c.get("ancho_linea", 1.0))
    pl.view_vector(cam[0], viewup=cam[1])
    pl.enable_parallel_projection()
    if foco is not None:
        d = np.array(cam[0], float)
        d /= np.linalg.norm(d)
        pl.camera.focal_point = tuple(foco[0])
        pl.camera.position = tuple(np.array(foco[0]) + d * 600)
        pl.camera.parallel_scale = foco[1]
    else:
        pl.camera.zoom(zoom)
    pl.enable_anti_aliasing("ssaa")
    pl.screenshot(path)
    out = {}
    for k, p in (marcas or {}).items():
        pl.renderer.SetWorldPoint(p[0], p[1], p[2], 1.0)
        pl.renderer.WorldToView()
        v = pl.renderer.GetViewPoint()
        out[k] = (0.5 * (v[0] + 1), 1 - 0.5 * (v[1] + 1))
    pl.close()
    return recortar(path, out, 10) if foco is None else out


def barra_util(fig, rect, horizontal=True):
    ax = fig.add_axes(rect)
    lv = np.geomspace(*CLIM, NB + 1)
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=BoundaryNorm(lv, NB), cmap=CM_U), cax=ax, extend="max",
                      orientation="horizontal" if horizontal else "vertical", spacing="uniform")
    cb.cmap.set_over(SIN_MARGEN)
    tk = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
    pos = [np.interp(np.log(t), np.log(lv), lv) for t in tk]
    cb.set_ticks(tk)
    cb.set_ticklabels([f"{t:g}".replace(".", ",") for t in tk])
    cb.ax.tick_params(labelsize=10)
    cb.set_label("Índice de utilización  FS·σ / σ$_{adm}$   (escala logarítmica; magenta: sin margen)", fontsize=10.5)
    return cb


def panel(ax, path, titulo=None, marca=None, texto=None, lado=1):
    im = plt.imread(path)
    ax.imshow(im, interpolation="lanczos")
    ax.axis("off")
    if titulo:
        ax.set_title(titulo, fontsize=12, weight="bold", pad=4)
    if marca is not None:
        h, w = im.shape[:2]
        px, py = marca[0] * w, marca[1] * h
        ax.plot([px], [py], "o", mfc="none", mec="k", mew=1.8, ms=13, zorder=5)
        ax.annotate(texto, xy=(px, py), xytext=(px + lado * 0.16 * w, py - 0.20 * h), fontsize=10, ha="center", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="k", lw=0.9),
                    arrowprops=dict(arrowstyle="-", color="k", lw=1.0))


def main(wd, tag, fjson, fnpz, fala, out):
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    R = json.load(open(fjson))
    Z = np.load(fnpz)
    z = np.load(os.path.join(wd, f"malla_{tag}.npz"))
    xyz, els, epart = z["xyz"], z["els"], z["epart"]
    partes = json.load(open(os.path.join(wd, f"partes_{tag}.json")))
    ever = Z["ever"]
    mat = np.array([p["mat"] for p in partes])[epart]
    adm = np.array([ADM_MAT.get(m, np.nan) for m in mat])
    cen_all = xyz[els[:, :4]].mean(axis=1)
    ver_ok = ~np.isnan(adm[ever])
    idx_v = ever[ver_ok]                         # elementos con admisible (se colorean)
    resto = np.setdiff1d(np.arange(len(els)), idx_v)
    g_resto = cortar(malla_pv(xyz, els, resto))
    f = np.array(R["freq"])
    zm = np.array(R["zeta_modal"])
    mef = np.array(R["m_eff"])

    def capas_util(vm_ever, warp=None):
        g = malla_pv(xyz, els, idx_v)
        u = np.clip(vm_ever[ver_ok] / adm[idx_v], CLIM[0] * 1.001, None)
        g.cell_data["u"] = u
        g = g.cell_data_to_point_data()
        gr = g_resto
        if warp is not None:
            g.points = g.points + warp[g["vtkOriginalPointIds"]] if "vtkOriginalPointIds" in g.array_names else g.points + warp
        return [dict(grid=cortar(g), scalars="u", cmap=CM_U, clim=CLIM, log=True, above=SIN_MARGEN),
                dict(grid=gr, color=(0.88, 0.88, 0.88), col_linea=(0.45, 0.45, 0.45), ancho_linea=0.7)], u

    def critico(u):
        """Elemento mas cargado: posicion, utilizacion, material e indice de pieza."""
        k = int(np.argmax(u))
        return cen_all[idx_v[k]].copy(), float(u[k]), mat[idx_v[k]], int(epart[idx_v[k]])

    NOMB = {"LWPLA": "tubo de LW-PLA", "PA12CF": "PA12-CF", "G10": "G10", "CFRP": "larguero", "EQ_PCB": "placa", "A2-70": "llave"}

    def nc(x, d=2):
        return f"{x:.{d}f}".replace(".", ",")

    def figura_caso(clave, titulo_eje, nombre, zoom_txt):
        """Tres vistas (una por eje) + la pieza mas cargada aislada, con el punto critico marcado."""
        info = {}
        for e in EJES:
            capas, u = capas_util(Z[f"{clave}_vm_{e}"])
            vtk(f"{tmp}/{clave}_{e}.png", capas)
            info[e] = critico(u) + (u,)
        em = max(EJES, key=lambda e: info[e][1])
        p, umax, m, ip, u = info[em]
        # pieza critica aislada: se corta por un plano que deja el punto del lado visible
        sel = np.where(epart[idx_v] == ip)[0]
        g = malla_pv(xyz, els, idx_v[sel])
        g.cell_data["u"] = u[sel]
        g = g.cell_data_to_point_data()
        if p[1] < 0:
            g = g.clip(normal=(0, 1, 0), origin=(0, min(p[1] + 12, -0.01), 0), invert=False) if False else g
        gz = g.clip(normal=(0, -1, 0), origin=(0, min(p[1] - 6.0, 0.0), 0), invert=True)
        mz = vtk(f"{tmp}/{clave}_zoom.png", [dict(grid=gz, scalars="u", cmap=CM_U, clim=CLIM, log=True, above=SIN_MARGEN)],
                 foco=(p, 30.0), size=(1500, 1300), marcas={"c": p})
        fig = plt.figure(figsize=(11.0, 8.9))
        for k, e in enumerate(EJES):
            ax = fig.add_axes([0.005 + 0.333 * k, 0.615, 0.325, 0.345])
            panel(ax, f"{tmp}/{clave}_{e}.png", f"{titulo_eje} {NOM_EJE[e]}\nmáx. {nc(info[e][1])} · {NOMB.get(info[e][2], '')}")
        ax = fig.add_axes([0.02, 0.125, 0.44, 0.44])
        panel(ax, f"{tmp}/{clave}_zoom.png", f"Pieza más cargada, aislada ({partes[ip]['nombre'].split(' ', 1)[1]}, eje {em.upper()})",
              mz["c"], f"von Mises:\nFS·σ/σ$_{{adm}}$ = {nc(umax)}")
        ax = fig.add_axes([0.48, 0.12, 0.51, 0.45])
        ax.axis("off")
        ax.text(0, 1, zoom_txt(em), va="top", fontsize=9.6, linespacing=1.5, family="DejaVu Sans Mono")
        barra_util(fig, [0.14, 0.062, 0.72, 0.016])
        fig.savefig(f"{out}/{nombre}.png")
        plt.close(fig)
        return em

    def tabla_txt(ms, col3, cab):
        lin = [f"{'Grupo':<30s}{'σ [MPa]':>9s}{cab:>10s}{'MS':>8s}", "-" * 57]
        for k, v in ms.items():
            g_, c_ = [t.strip() for t in k.split("|")]
            crit = {"von Mises": "vM", "sigma_x entre capas": "σx capas", "sigma_x fibra": "σx fibra", "corte interlaminar": "τ"}[c_]
            lin.append(f"{g_.split('(')[0].strip()[:20]:<20s} {crit:<9s}{nc(v['sigma'], 1):>9s}{col3(v):>10s}{nc(v['MS']):>8s}")
        return "\n".join(lin)

    def txt_arm(e):
        return (f"Entrada: seno de 15 G en la base, de 5 a 1000 Hz.\nCada mapa es la envolvente sobre todas las resonancias.\n"
                f"El color es von Mises contra el admisible de cada material;\nen piezas impresas manda además σx entre capas (tabla).\n\n"
                f"Peor resonancia de cada grupo, excitación en {e.upper()}:\n"
                + tabla_txt(R["armonico"][e]["margenes"], lambda v: f"{v['f_crit']:.0f} Hz", "f crít."))

    def txt_ch(e):
        return (f"Entrada: semiseno de 30 G en la base.\nCada mapa es la envolvente en el tiempo, con la duración\n"
                f"más desfavorable entre 1 y 20 ms.\n"
                f"El color es von Mises contra el admisible de cada material;\nen piezas impresas manda además σx entre capas (tabla).\n\n"
                f"Peor caso de cada grupo, choque en {e.upper()}:\n"
                + tabla_txt(R["choque"][e]["margenes"], lambda v: f"{v['tau_crit'] * 1e3:.0f} ms", "duración"))
    plt.rcParams["font.family"] = "Inter"
    figura_caso("arm", "Excitación en", "fea_arm_mapas", txt_arm)
    figura_caso("choque", "Choque en", "fea_choque_mapas", txt_ch)

    # ------------------------------------------------ tiron del paracaidas
    Up = Z["parac_U"].astype(float)
    esc = 5.0 / max(np.linalg.norm(Up, axis=1).max(), 1e-9)
    g = malla_pv(xyz, els, idx_v)
    u = np.clip(Z["parac_vm"][ver_ok] / adm[idx_v], CLIM[0] * 1.001, None)
    g.cell_data["u"] = u
    g = g.cell_data_to_point_data()
    used = np.unique(els[idx_v][:, :4])
    p, umax, m, ip = critico(u)
    capas = [dict(grid=cortar(g), scalars="u", cmap=CM_U, clim=CLIM, log=True, above=SIN_MARGEN),
             dict(grid=g_resto, color=(0.88, 0.88, 0.88), col_linea=(0.45, 0.45, 0.45), ancho_linea=0.7)]
    vtk(f"{tmp}/parac.png", capas)
    cola = (np.array([212.0, 0.0, 0.0]), 34.0)
    vtk(f"{tmp}/parac_zoom.png", capas, foco=cola, size=(1500, 1300))
    fig = plt.figure(figsize=(11.0, 4.9))
    panel(fig.add_axes([0.0, 0.16, 0.56, 0.76]), f"{tmp}/parac.png",
          f"Tirón del paracaídas: 30 G × 1,8, colgado de la brida\nmáx. {nc(umax)} · {NOMB.get(m, '')}")
    panel(fig.add_axes([0.58, 0.16, 0.41, 0.76]), f"{tmp}/parac_zoom.png", "Tapa, llave, aislador y C4")
    barra_util(fig, [0.14, 0.105, 0.72, 0.028])
    fig.savefig(f"{out}/fea_parac_mapas.png")
    plt.close(fig)

    # ------------------------------------------------ malla por material + acercamiento
    g = malla_pv(xyz, els)
    g.cell_data["rgb"] = (np.array([COL_MAT.get(m_, (0.7, 0.7, 0.7)) for m_ in mat]) * 255).astype(np.uint8)
    gc = cortar(g)
    capa = [dict(grid=gc, rgb=True, edges=True, lineas=False)]
    vtk(f"{tmp}/malla.png", capa, size=(2200, 1400))
    vtk(f"{tmp}/malla_zoom.png", capa, foco=cola, size=(1500, 1300))
    fig = plt.figure(figsize=(11.0, 4.7))
    panel(fig.add_axes([0.0, 0.17, 0.60, 0.77]), f"{tmp}/malla.png", f"{len(els):,} tetraedros cuadráticos · {len(xyz):,} nodos".replace(",", "."))
    panel(fig.add_axes([0.61, 0.17, 0.38, 0.77]), f"{tmp}/malla_zoom.png", "Detalle: tapa, llave y aislador")
    fig.subplots_adjust(bottom=0.2)
    pres = [m_ for m_ in MATS if (mat == m_[0]).any() or (m_[0] == "ELAST" and np.isin(mat, ["PAD_A", "PAD_B", "ELAST_X"]).any())]
    fig.legend(handles=[Patch(fc=c, ec="0.3", label=nm) for _, nm, c in pres], loc="lower center", ncol=5, fontsize=9.5,
               handlelength=1.2, columnspacing=1.4)
    fig.savefig(f"{out}/fea_malla.png")
    plt.close(fig)

    # ------------------------------------------------ formas modales (2 x 2)
    def tipo(i):
        fr = mef[i] / R["masa_g"] * 100
        return "local" if fr.max() < 2 else ["axial X", "lateral Y", "lateral Z"][int(np.argmax(fr))]
    g0 = cortar(malla_pv(xyz, els))
    fig = plt.figure(figsize=(11.0, 7.6))
    for k in range(4):
        U = Z[f"modo_{k}"].astype(float)
        amp = np.linalg.norm(U, axis=1)
        gm = malla_pv(xyz, els)
        gm.point_data["a"] = amp / amp.max()
        gm.points = gm.points + U * (13.0 / amp.max())
        vtk(f"{tmp}/modo{k}.png", [dict(grid=cortar(gm), scalars="a", cmap="viridis", clim=(0, 1), n=10),
                                   dict(grid=g0, color=(1, 1, 1), opacity=0.0, col_linea=(0.55, 0.55, 0.55), ancho_linea=0.8)],
            size=(1700, 1150))
        ax = fig.add_axes([0.01 + 0.5 * (k % 2), 0.555 - 0.445 * (k // 2), 0.48, 0.40])
        panel(ax, f"{tmp}/modo{k}.png", f"Modo {k + 1}:  {f[k]:.0f} Hz  ·  {tipo(k)}  ·  ζ = {zm[k] * 100:.1f} %".replace(".", ","))
    cax = fig.add_axes([0.30, 0.085, 0.40, 0.016])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 1), cmap=plt.get_cmap("viridis", 10)), cax=cax, orientation="horizontal")
    cb.set_label("Desplazamiento modal normalizado (deformada amplificada; en gris, la forma sin deformar)", fontsize=10)
    fig.savefig(f"{out}/fea_modos.png")
    plt.close(fig)

    # ------------------------------------------------ respuesta en aceleracion y utilizacion contra frecuencia
    fg = Z["fgrid"]
    mons = [k.split("_", 2)[2] for k in Z.files if k.startswith("trans_x_")]
    fig, axs = plt.subplots(3, 1, figsize=(8.6, 9.2), sharex=True)
    for a, e in zip(axs, EJES):
        for c, mn in zip(COL, mons):
            a.loglog(fg, P.N_VIB * Z[f"trans_{e}_{mn}"], color=c, label=mn)
        a.axhline(P.N_VIB, color="k", ls="--", lw=1)
        a.text(5.4, P.N_VIB * 1.12, "entrada: 15 G", fontsize=9.5)
        a.set_ylabel("Respuesta [G]")
        a.set_title(f"Excitación en {NOM_EJE[e]}", loc="left")
        a.set_xlim(5, 1000)
        a.set_ylim(8, 600)
        i = int(np.argmax(mef[:, EJES.index(e)]))
        a.axvline(f[i], color="0.75", lw=0.9, zorder=0)
        a.text(f[i] * 0.97, 430, f"{f[i]:.0f} Hz", fontsize=9.5, ha="right", color="0.3")
    axs[2].set_xlabel("Frecuencia de excitación [Hz]")
    axs[0].legend(fontsize=9, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{out}/fea_respuesta_g.png")
    plt.close(fig)

    fig, axs = plt.subplots(3, 1, figsize=(8.6, 9.2), sharex=True)
    for a, e in zip(axs, EJES):
        M = R["armonico"][e]["margenes"]
        j = 0
        for k, v in M.items():
            gn, cn = [s.strip() for s in k.split("|")]
            if not ("von Mises" in cn or "fibra" in cn):
                continue
            cual = "vm" if "von Mises" in cn else "sx"
            a.loglog(fg, Z[f"arm_{e}_{gn}|{cual}"] * v["FS"] / v["adm"], color=COL[j % len(COL)], label=gn)
            j += 1
        a.axhline(1.0, color="k", ls="--", lw=1.1)
        a.axhspan(1.0, 10, color=ROJO, alpha=0.07, lw=0)
        a.text(5.4, 1.25, "sin margen", fontsize=9.5, color=ROJO)
        a.set_ylabel("FS·σ / σ$_{adm}$")
        a.set_title(f"Excitación en {NOM_EJE[e]}", loc="left")
        a.set_xlim(5, 1000)
        a.set_ylim(2e-3, 4)
    axs[2].set_xlabel("Frecuencia de excitación [Hz]")
    axs[0].legend(fontsize=8.6, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{out}/fea_util_frecuencia.png")
    plt.close(fig)

    # ------------------------------------------------ choque: pulso, SRS, historias
    t = np.linspace(-2, 25, 600) * 1e-3
    fig, axs = plt.subplots(1, 3, figsize=(11.0, 3.6))
    a = axs[0]
    a.plot(t * 1e3, np.where((t >= 0) & (t <= P.TAU_SHOCK), P.N_SHOCK * np.sin(np.pi * t / P.TAU_SHOCK), 0), color=AZUL, lw=2.4, label="11 ms")
    for tau, ls in ((0.003, ":"), (0.006, "--")):
        a.plot(t * 1e3, np.where((t >= 0) & (t <= tau), P.N_SHOCK * np.sin(np.pi * t / tau), 0), color=GRIS, lw=1.3, ls=ls,
               label=f"{tau * 1e3:.0f} ms")
    a.set_xlabel("Tiempo [ms]")
    a.set_ylabel("Aceleración de base [G]")
    a.set_title("Pulso semiseno de 30 G")
    a.legend(fontsize=9)
    a = axs[1]
    a.loglog(Z["srs_f"], Z["srs_a"], color=ROJO, lw=2.2, label="ζ = 2 %")
    if "srs_a15" in Z.files:
        a.loglog(Z["srs_f"], Z["srs_a15"], color=AZUL, lw=1.8, ls="--", label="ζ = 15 %")
    a.axhline(P.N_SHOCK, color="k", ls=":", lw=0.9)
    a.axvline(f[0], color="0.75", lw=0.9, zorder=0)
    a.text(f[0] * 1.06, 6, f"modo 1\n{f[0]:.0f} Hz", fontsize=9, color="0.3")
    a.set_xlabel("Frecuencia natural [Hz]")
    a.set_ylabel("Respuesta máxima [G]")
    a.set_title("Espectro de respuesta (11 ms)")
    a.set_ylim(4, 80)
    a.legend(fontsize=9, loc="lower right")
    a = axs[2]
    tt = Z["choque_tacc_x"] * 1e3
    for c, mn in zip(COL, mons):
        a.plot(tt, Z[f"choque_acc_x_{mn}"], color=c, lw=1.3, label=mn)
    a.set_xlim(0, 30)
    a.set_xlabel("Tiempo [ms]")
    a.set_ylabel("Aceleración absoluta [G]")
    a.set_title("Respuesta al choque axial")
    a.legend(fontsize=7.4, ncol=2)
    fig.tight_layout()
    fig.savefig(f"{out}/fea_choque_pulso.png")
    plt.close(fig)

    fig, axs = plt.subplots(1, 3, figsize=(11.0, 4.3), sharey=True)
    for a, e in zip(axs, EJES):
        C = R["choque"][e]
        j = 0
        for k, cur in C["duraciones"].items():
            if not ("von Mises" in k or "fibra" in k):
                continue
            v = C["margenes"][k]
            a.semilogy(np.array(C["taus"]) * 1e3, np.array(cur) * v["FS"] / v["adm"], "o-", color=COL[j % len(COL)], ms=4,
                       label=k.split("|")[0].strip())
            j += 1
        a.axhline(1.0, color="k", ls="--", lw=1.1)
        a.axhspan(1.0, 10, color=ROJO, alpha=0.07, lw=0)
        a.axvline(11, color="0.7", lw=0.9)
        a.set_title(f"Choque en {NOM_EJE[e]}")
        a.set_xlabel("Duración del semiseno [ms]")
        a.set_ylim(2e-3, 4)
    axs[0].set_ylabel("FS·σ / σ$_{adm}$")
    fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4, fontsize=9)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(f"{out}/fea_choque_duracion.png")
    plt.close(fig)

    # ------------------------------------------------ masas efectivas
    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    w, nmo = 0.27, min(12, len(f))
    for k, (e, c) in enumerate(zip(EJES, (AZUL, ROJO, VERDE))):
        ax.bar(np.arange(nmo) + (k - 1) * w, mef[:nmo, k] / R["masa_g"] * 100, w, color=c, label=NOM_EJE[e])
    ax.set_xticks(np.arange(nmo))
    ax.set_xticklabels([f"{i + 1}\n{f[i]:.0f} Hz" for i in range(nmo)], fontsize=9)
    ax.set_ylabel("Masa efectiva [% de 500 g]")
    ax.legend(fontsize=9.5)
    fig.tight_layout()
    fig.savefig(f"{out}/fea_masa_efectiva.png")
    plt.close(fig)

    # ------------------------------------------------ ala desplegada
    A = np.load(fala)
    s = A["s_le"]
    sm = 0.5 * (s[:-1] + s[1:])
    fig, axs = plt.subplots(1, 3, figsize=(11.0, 3.9))
    a = axs[0]
    a.plot(sm, A["Mf_nota"], color=AZUL, ls="--", label="fuera del plano (nota)")
    a.plot(sm, A["Mf"], color=AZUL, label="fuera del plano (pórtico)")
    a.plot(sm, A["Mp"], color=ROJO, label="en el plano (tela)")
    a.plot(sm, A["M"], color="k", lw=1.2, label="resultante")
    a.axvline(P.L_SEG, color="0.6", ls=":")
    a.text(P.L_SEG + 4, 610, "J", fontsize=10)
    a.set_xlabel("Distancia al ápice [mm]")
    a.set_ylabel("Momento flector [N·mm]")
    a.set_title("Varilla, p = 367 Pa")
    a.legend(fontsize=8.4)
    a = axs[1]
    a.plot(s, A["uz_nota"], color=AZUL, ls="--", label="nota (voladizo)")
    a.plot(s, A["uz"], color=AZUL, label="pórtico con tirante")
    a.set_xlabel("Distancia al ápice [mm]")
    a.set_ylabel("Flecha fuera del plano [mm]")
    a.set_title("Deformada")
    a.legend(fontsize=9)
    a = axs[2]
    a.plot(A["t_z"] * 1e3, A["utip_z"], color=ROJO)
    a.set_xlim(0, 60)
    a.set_xlabel("Tiempo [ms]")
    a.set_ylabel("Flecha relativa de la punta [mm]")
    a.set_title("Choque de 30 G en Z, ala abierta")
    fig.tight_layout()
    fig.savefig(f"{out}/ala_esfuerzos.png")
    plt.close(fig)
    xy, nle, dof = A["xyz"], int(A["nle"]), A["dof"]
    fig, axs = plt.subplots(1, 4, figsize=(11.0, 3.2), subplot_kw=dict(projection="3d"))
    for k, a in enumerate(axs):
        ph = A["phi"][k]
        U = np.stack([ph[dof[:, 0]], ph[dof[:, 1]], ph[dof[:, 2]]], axis=1)
        U = U / np.abs(U).max() * 35
        for sl in (slice(0, nle), slice(nle, None)):
            a.plot(xy[sl, 0], xy[sl, 1], 0 * xy[sl, 0], color="0.7", lw=1.2)
            a.plot(xy[sl, 0] + U[sl, 0], xy[sl, 1] + U[sl, 1], U[sl, 2], color=AZUL if sl.start == 0 else VERDE, lw=2.4)
        a.plot([0, P.D_AB], [0, 0], [0, 0], color="k", lw=3.5)
        a.set_title(f"Modo {k + 1}: {A['freq'][k]:.0f} Hz")
        a.set_box_aspect((1, 1, 0.5))
        a.set_axis_off()
        a.view_init(28, -60)
    fig.tight_layout()
    fig.savefig(f"{out}/ala_modos.png")
    plt.close(fig)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print("figuras FEA ok")


if __name__ == "__main__":
    main(*sys.argv[1:7])
