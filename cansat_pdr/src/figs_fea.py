"""Figuras del analisis estructural para el PDR.
Uso: python3 figs_fea.py <carpeta_fea> <tag> <res.json> <res.npz> <ala.npz> <carpeta_figs>
"""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyvista as pv
import params as P

pv.OFF_SCREEN = True
plt.rcParams.update({"font.family": "Inter", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "0.88", "grid.linewidth": 0.6, "axes.linewidth": 0.8,
                     "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 220, "lines.linewidth": 1.5})
AZUL, ROJO, VERDE, NAR, VIOL, GRIS = "#2f3192", "#c0392b", "#1a8a55", "#e67e22", "#7d3c98", "#555555"
COL = [AZUL, ROJO, VERDE, NAR, VIOL, "#008b8b", "#8d6e63", "#333333"]
EJES = "xyz"
NOM_EJE = {"x": "X (axial)", "y": "Y (lateral)", "z": "Z (lateral)"}
ADM_MAT = {"LWPLA": 14.0 / 2, "PA12CF": 65.0 / 2, "G10": 280.0 / 1.5, "CFRP": 900.0 / 1.5, "EQ_PCB": 280.0 / 1.5,
           "A2-70": 450.0 / 1.25}
COL_MAT = {"LWPLA": (0.93, 0.93, 0.88), "PA12CF": (0.25, 0.27, 0.30), "G10": (0.55, 0.68, 0.42), "CFRP": (0.08, 0.08, 0.09),
           "EQ_PCB": (0.05, 0.45, 0.25), "A2-70": (0.75, 0.75, 0.78), "EQ_BLK": (0.85, 0.5, 0.15), "EQ_BAT": (0.15, 0.35, 0.75),
           "EQ_SOFT": (0.9, 0.25, 0.25), "EQ_BOOM": (0.1, 0.1, 0.1), "PAD_A": (0.95, 0.9, 0.4), "PAD_B": (0.95, 0.9, 0.4)}
CAM = ((-1.0, -1.35, 0.8), (0, 0, 1))


def malla_pv(xyz, els):
    n = len(els)
    cells = np.hstack([np.full((n, 1), 4), els[:, :4]]).ravel()
    return pv.UnstructuredGrid(cells, np.full(n, pv.CellType.TETRA), xyz.astype(float))


def foto(grid, scalars, path, clim=None, cmap="turbo", titulo="", corte=True, size=(1700, 1150), zoom=1.45, edges=False,
         rgb=False, warp=None, fantasma=None, nan_color=(0.82, 0.82, 0.82), cam=CAM, nlab=6, fmt="%.2f"):
    g = grid.copy()
    if warp is not None:
        g.points = g.points + warp
    if scalars is not None:
        g.cell_data["s"] = scalars
    if corte:
        g = g.clip(normal=(0, -1, 0), origin=(0, 0.01, 0), invert=True)
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    if fantasma is not None:
        f = fantasma.clip(normal=(0, -1, 0), origin=(0, 0.01, 0), invert=True) if corte else fantasma
        pl.add_mesh(f.extract_surface().extract_feature_edges(feature_angle=40), color=(0.55, 0.55, 0.55), line_width=1)
    kw = dict(show_edges=edges, edge_color=(0.25, 0.25, 0.25), line_width=0.4, lighting=True, ambient=0.35, diffuse=0.75,
              specular=0.05)
    if rgb:
        pl.add_mesh(g, scalars="s", rgb=True, **kw)
    elif scalars is None:
        pl.add_mesh(g, color=(0.8, 0.8, 0.8), **kw)
    else:
        pl.add_mesh(g, scalars="s", cmap=cmap, clim=clim, nan_color=nan_color, n_colors=14,
                    scalar_bar_args=dict(title=titulo, vertical=True, position_x=0.88, position_y=0.18, width=0.07,
                                         height=0.64, title_font_size=26, label_font_size=24, color="black", fmt=fmt,
                                         n_labels=nlab, font_family="arial"), **kw)
    pl.view_vector(cam[0], viewup=cam[1])
    pl.enable_parallel_projection()
    pl.camera.zoom(zoom)
    pl.screenshot(path)
    pl.close()


def main(wd, tag, fjson, fnpz, fala, out):
    os.makedirs(out, exist_ok=True)
    R = json.load(open(fjson))
    Z = np.load(fnpz)
    z = np.load(os.path.join(wd, f"malla_{tag}.npz"))
    xyz, els, epart = z["xyz"], z["els"], z["epart"]
    partes = json.load(open(os.path.join(wd, f"partes_{tag}.json")))
    ever = Z["ever"]
    grid = malla_pv(xyz, els)
    mat = np.array([p["mat"] for p in partes])[epart]
    # ------------------------------------------------ malla por material
    rgb = np.array([COL_MAT.get(m, (0.7, 0.7, 0.7)) for m in mat])
    foto(grid, (rgb * 255).astype(np.uint8), f"{out}/fea_malla.png", rgb=True, edges=True)
    foto(grid, (rgb * 255).astype(np.uint8), f"{out}/fea_malla_ext.png", rgb=True, edges=True, corte=False)
    # indice de utilizacion por elemento = FS * vM / admisible (von Mises; CFRP: referencia de fibra)
    adm = np.array([ADM_MAT.get(m, np.nan) for m in mat])

    def util(vm_ever):
        u = np.full(len(els), np.nan)
        u[ever] = vm_ever / adm[ever]
        return u
    # ------------------------------------------------ modos
    f = np.array(R["freq"])
    for i in range(min(6, len(f))):
        U = Z[f"modo_{i}"].astype(float)
        amp = np.linalg.norm(U, axis=1)
        sc = 14.0 / amp.max()
        cell_amp = amp[els[:, :4]].mean(axis=1) / amp.max()
        foto(grid, cell_amp, f"{out}/fea_modo{i + 1}.png", clim=(0, 1), cmap="viridis", titulo="|u| norm.", warp=U * sc,
             fantasma=grid, size=(1500, 1050))
    # ------------------------------------------------ mapas de utilizacion
    for e in EJES:
        for caso, nom in (("arm", "arm"), ("choque", "choque")):
            u = util(Z[f"{caso}_vm_{e}"])
            cm = float(np.nanpercentile(u, 99.95))
            foto(grid, u, f"{out}/fea_{nom}_util_{e}.png", clim=(0, max(cm, 0.05)), titulo="Utilizacion")
    u = util(Z["parac_vm"])
    foto(grid, u, f"{out}/fea_parac_util.png", clim=(0, max(float(np.nanpercentile(u, 99.95)), 0.05)), titulo="Utilizacion",
         warp=Z["parac_U"].astype(float) * (4.0 / max(np.linalg.norm(Z["parac_U"], axis=1).max(), 1e-9)), fantasma=grid)
    for e in EJES:
        U = Z[f"arm_U_{e}"].astype(float)
        amp = np.linalg.norm(U, axis=1)
        foto(grid, amp[els[:, :4]].mean(axis=1), f"{out}/fea_arm_def_{e}.png", cmap="viridis", titulo="|u| rel. [mm]",
             warp=U * (10.0 / amp.max()), fantasma=grid, size=(1500, 1050), fmt="%.3f")
    # ------------------------------------------------ transmisibilidad
    fg = Z["fgrid"]
    mons = [k.split("_", 2)[2] for k in Z.files if k.startswith("trans_x_")]
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.9), sharey=True)
    for a, e in zip(axs, EJES):
        for c, mn in zip(COL, mons):
            a.loglog(fg, Z[f"trans_{e}_{mn}"], color=c, label=mn)
        for fn in f[f < 1000]:
            a.axvline(fn, color="0.85", lw=0.5, zorder=0)
        a.set_title(f"Excitación en {NOM_EJE[e]}", fontsize=10, weight="bold")
        a.set_xlabel("Frecuencia [Hz]")
        a.set_xlim(5, 1000)
        a.set_ylim(0.3, 60)
    axs[0].set_ylabel("Transmisibilidad  |a$_{resp}$| / |a$_{base}$|")
    axs[2].legend(fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{out}/fea_transmisibilidad.png")
    plt.close(fig)
    # aceleracion de respuesta en g (15 g de entrada)
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.9), sharey=True)
    for a, e in zip(axs, EJES):
        for c, mn in zip(COL, mons):
            a.loglog(fg, P.N_VIB * Z[f"trans_{e}_{mn}"], color=c, label=mn)
        a.axhline(P.N_VIB, color="k", ls="--", lw=0.9)
        a.text(5.5, P.N_VIB * 1.1, "entrada: 15 g", fontsize=8)
        a.set_title(f"Excitación en {NOM_EJE[e]}", fontsize=10, weight="bold")
        a.set_xlabel("Frecuencia [Hz]")
        a.set_xlim(5, 1000)
        a.set_ylim(5, 900)
    axs[0].set_ylabel("Aceleración de respuesta [g]")
    axs[2].legend(fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{out}/fea_respuesta_g.png")
    plt.close(fig)
    # ------------------------------------------------ utilizacion contra frecuencia
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 4.1), sharey=True)
    for a, e in zip(axs, EJES):
        M = R["armonico"][e]["margenes"]
        for c, (k, v) in zip(COL * 2, [(k, v) for k, v in M.items()]):
            gn, cn = [s.strip() for s in k.split("|")]
            cual = {"von Mises": "vm", "sigma_x entre capas": "sx", "sigma_x fibra": "sx", "corte interlaminar": "tau"}[cn]
            if cual != "vm" and "fibra" not in cn:
                continue
            cur = Z[f"arm_{e}_{gn}|{cual}"] * v["FS"] / v["adm"]
            a.loglog(fg, cur, color=c, label=gn)
        a.axhline(1.0, color="k", ls="--", lw=1)
        a.text(5.5, 1.12, "límite (MS = 0)", fontsize=8)
        a.set_title(f"Excitación en {NOM_EJE[e]}", fontsize=10, weight="bold")
        a.set_xlabel("Frecuencia [Hz]")
        a.set_xlim(5, 1000)
        a.set_ylim(1e-3, 5)
    axs[0].set_ylabel("Índice de utilización  FS·σ / σ$_{adm}$")
    axs[2].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{out}/fea_util_frecuencia.png")
    plt.close(fig)
    # ------------------------------------------------ choque
    t = np.linspace(-2, 25, 600) * 1e-3
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.7))
    a = axs[0]
    a.plot(t * 1e3, np.where((t >= 0) & (t <= P.TAU_SHOCK), P.N_SHOCK * np.sin(np.pi * t / P.TAU_SHOCK), 0), color=AZUL, lw=2)
    for tau, ls in ((0.003, ":"), (0.006, "--")):
        a.plot(t * 1e3, np.where((t >= 0) & (t <= tau), P.N_SHOCK * np.sin(np.pi * t / tau), 0), color=GRIS, lw=1, ls=ls)
    a.set_xlabel("Tiempo [ms]")
    a.set_ylabel("Aceleración de base [g]")
    a.set_title("Pulso semiseno de 30 g", fontsize=10, weight="bold")
    a.text(11.5, 24, "11 ms (nominal)\n3 y 6 ms (barrido)", fontsize=8)
    a = axs[1]
    a.loglog(Z["srs_f"], Z["srs_a"], color=ROJO, lw=2)
    for fn in f[:12]:
        a.axvline(fn, color="0.8", lw=0.6, zorder=0)
    a.axhline(P.N_SHOCK, color="k", ls="--", lw=0.8)
    a.set_xlabel("Frecuencia natural [Hz]")
    a.set_ylabel("Respuesta máxima [g]")
    a.set_title(f"Espectro de respuesta (SRS), ζ = {R['zeta'] * 100:.0f} %", fontsize=10, weight="bold")
    a.set_ylim(3, 80)
    a = axs[2]
    tt = Z["choque_tacc_x"] * 1e3
    for c, mn in zip(COL, mons):
        a.plot(tt, Z[f"choque_acc_x_{mn}"], color=c, lw=1.1, label=mn)
    a.set_xlim(0, 40)
    a.set_xlabel("Tiempo [ms]")
    a.set_ylabel("Aceleración absoluta [g]")
    a.set_title("Respuesta al choque axial (X), 11 ms", fontsize=10, weight="bold")
    a.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(f"{out}/fea_choque_pulso.png")
    plt.close(fig)
    # sensibilidad a la duracion del pulso
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.7), sharey=True)
    for a, e in zip(axs, EJES):
        C = R["choque"][e]
        M = C["margenes"]
        for c, (k, cur) in zip(COL * 2, [(k, v) for k, v in C["duraciones"].items()]):
            if not ("von Mises" in k or "fibra" in k):
                continue
            v = M[k]
            a.semilogy(np.array(C["taus"]) * 1e3, np.array(cur) * v["FS"] / v["adm"], "o-", color=c, ms=3,
                       label=k.split("|")[0].strip())
        a.axhline(1.0, color="k", ls="--", lw=1)
        a.axvline(11, color="0.7", lw=0.8)
        a.set_title(f"Choque en {NOM_EJE[e]}", fontsize=10, weight="bold")
        a.set_xlabel("Duración del semiseno [ms]")
        a.set_ylim(1e-3, 5)
    axs[0].set_ylabel("Índice de utilización  FS·σ / σ$_{adm}$")
    axs[2].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{out}/fea_choque_duracion.png")
    plt.close(fig)
    # ------------------------------------------------ masas efectivas
    me = np.array(R["m_eff"])
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    w = 0.27
    n = min(12, len(f))
    for k, (e, c) in enumerate(zip(EJES, (AZUL, ROJO, VERDE))):
        ax.bar(np.arange(n) + (k - 1) * w, me[:n, k] / R["masa_g"] * 100, w, color=c, label=NOM_EJE[e])
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels([f"{i + 1}\n{f[i]:.0f} Hz" for i in range(n)], fontsize=7.5)
    ax.set_ylabel("Masa efectiva [% de 500 g]")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{out}/fea_masa_efectiva.png")
    plt.close(fig)
    # ------------------------------------------------ ala desplegada
    A = np.load(fala)
    s = A["s_le"]
    sm = 0.5 * (s[:-1] + s[1:])
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.7))
    a = axs[0]
    a.plot(sm, A["Mf_nota"], color=AZUL, ls="--", label="fuera del plano (nota: voladizo)")
    a.plot(sm, A["Mf"], color=AZUL, label="fuera del plano (pórtico con tirante)")
    a.plot(sm, A["Mp"], color=ROJO, label="en el plano (tensión de tela)")
    a.plot(sm, A["M"], color="k", lw=1, label="resultante (pórtico)")
    a.axvline(P.L_SEG, color="0.6", ls=":")
    a.text(P.L_SEG + 3, 600, "J (manguito)", fontsize=8)
    a.set_xlabel("Distancia al ápice [mm]")
    a.set_ylabel("Momento flector [N·mm]")
    a.set_title("Varilla de borde de ataque, p = 367 Pa", fontsize=10, weight="bold")
    a.legend(fontsize=7.2)
    a = axs[1]
    a.plot(s, A["uz_nota"], color=AZUL, ls="--", label="nota (voladizo)")
    a.plot(s, A["uz"], color=AZUL, label="pórtico con tirante")
    a.set_xlabel("Distancia al ápice [mm]")
    a.set_ylabel("Flecha fuera del plano [mm]")
    a.set_title("Deformada de la varilla", fontsize=10, weight="bold")
    a.legend(fontsize=8)
    a = axs[2]
    a.plot(A["t_z"] * 1e3, A["utip_z"], color=ROJO)
    a2 = a.twinx()
    a2.plot(A["t_z"] * 1e3, A["ab_z"] / 9806.65, color="0.6", lw=1)
    a2.set_ylabel("Base [g]", color="0.5")
    a2.grid(False)
    a.set_xlim(0, 60)
    a.set_xlabel("Tiempo [ms]")
    a.set_ylabel("Flecha relativa de la punta [mm]")
    a.set_title("Choque de 30 g en Z, ala desplegada", fontsize=10, weight="bold")
    fig.tight_layout()
    fig.savefig(f"{out}/ala_esfuerzos.png")
    plt.close(fig)
    # modos del ala (planta + elevacion)
    xy = A["xyz"]
    nle = int(A["nle"])
    dof = A["dof"]
    fig, axs = plt.subplots(1, 4, figsize=(12.6, 3.4), subplot_kw=dict(projection="3d"))
    for k, a in enumerate(axs):
        ph = A["phi"][k]
        U = np.stack([ph[dof[:, 0]], ph[dof[:, 1]], ph[dof[:, 2]]], axis=1)
        U = U / np.abs(U).max() * 35
        for sl in (slice(0, nle), slice(nle, None)):
            a.plot(xy[sl, 0], xy[sl, 1], 0 * xy[sl, 0], color="0.7", lw=1)
            a.plot(xy[sl, 0] + U[sl, 0], xy[sl, 1] + U[sl, 1], U[sl, 2], color=AZUL if sl.start == 0 else VERDE, lw=2)
        a.plot([0, P.D_AB], [0, 0], [0, 0], color="k", lw=3)
        a.set_title(f"Modo {k + 1}: {A['freq'][k]:.0f} Hz", fontsize=10, weight="bold")
        a.set_box_aspect((1, 1, 0.5))
        a.set_axis_off()
        a.view_init(28, -60)
    fig.tight_layout()
    fig.savefig(f"{out}/ala_modos.png")
    plt.close(fig)
    print("figuras FEA ok")


if __name__ == "__main__":
    main(*sys.argv[1:7])
