"""Gráficos (matplotlib): Bode, Nyquist, Nichols, temporal, polos, estabilidad vs K, sensibilidad, compensación.

Todas las funciones `fig_*` devuelven la figura (no la muestran). Cada una recibe una lista de
sistemas [(etiqueta, Sistema), ...] para poder superponer "sin compensar" y "compensado".
"""
from __future__ import annotations

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from .sistema import Sistema
from .frecuencia import (bode_datos, margenes, nyquist_conteo, contornos_M, rejilla, cerrado_frecuencia)
from .temporal import respuesta_escalon, respuesta_rampa

AZUL, ROJO, VERDE, NARANJA, GRIS, VIOLETA = "#1f4e79", "#b91e28", "#007346", "#d76e00", "#5f5f5f", "#6e3296"
COLORES = [GRIS, AZUL, ROJO, VERDE, NARANJA, VIOLETA]
ESTILOS = ["--", "-", "-", "-", "-", "-"]


def configurar(mostrar: bool = True) -> None:
    """Usar backend sin ventana cuando no se muestra (por ejemplo en servidores)."""
    if not mostrar:
        plt.switch_backend("Agg")
    plt.rcParams.update({
        "figure.dpi": 100, "axes.grid": True, "grid.alpha": 0.35, "axes.titlesize": 11, "axes.labelsize": 10,
        "legend.fontsize": 8.5, "legend.framealpha": 0.9, "lines.linewidth": 1.8, "font.size": 10,
    })


def guardar(fig, nombre: str, carpeta: str = "salidas", dpi: int = 140, formatos=("png",)) -> list[str]:
    os.makedirs(carpeta, exist_ok=True)
    rutas = []
    for ext in formatos:
        ruta = os.path.join(carpeta, f"{nombre}.{ext}")
        fig.savefig(ruta, dpi=dpi, bbox_inches="tight")
        rutas.append(ruta)
    return rutas


def _estilo(i: int, n: int) -> dict:
    """Primer sistema (el 'sin compensar') punteado en gris si hay varios; el resto en colores."""
    if n == 1:
        return dict(color=AZUL, ls="-")
    paleta = [GRIS, ROJO, AZUL, VERDE, NARANJA, VIOLETA]
    return dict(color=paleta[i % len(paleta)], ls="--" if i == 0 else "-")


# ----------------------------------------------------------------------------
#  Bode
# ----------------------------------------------------------------------------
def _dibujar_bode(ax_m, ax_f, sistemas, w=None, asintotas=False, marcas=True, extra=None):
    if w is None:
        ws = [rejilla(s, n=1500) for _, s in sistemas]
        w = np.logspace(np.log10(min(x[0] for x in ws)), np.log10(max(x[-1] for x in ws)), 2500)
    n = len(sistemas)
    for i, (lab, sis) in enumerate(sistemas):
        mag, fase = bode_datos(sis, w)
        st = _estilo(i, n)
        ax_m.semilogx(w, mag, label=lab, **st)
        ax_f.semilogx(w, fase, **st)
        if asintotas and i == 0:
            fb = sis.forma_bode()
            ax_m.semilogx(w, fb.magnitud_asintotica_dB(w), color=VIOLETA, ls=":", lw=1.4, label=f"asíntotas de «{lab}»")
            ax_f.semilogx(w, fb.fase_asintotica_deg(w), color=VIOLETA, ls=":", lw=1.4)
        if marcas:
            m = margenes(sis, w)
            c = st["color"]
            if m.wc is not None:
                ax_m.axvline(m.wc, color=c, ls=":", lw=1)
                ax_f.axvline(m.wc, color=c, ls=":", lw=1)
                ph = float(np.interp(np.log10(m.wc), np.log10(w), fase))
                ref = -180.0 + 360.0 * round((ph + 180.0) / 360.0)
                ax_f.annotate("", xy=(m.wc, ref), xytext=(m.wc, ph), arrowprops=dict(arrowstyle="<->", color=c, lw=1.3))
                ax_f.annotate(f"MF={m.MF:.1f}°", xy=(m.wc, (ph + ref) / 2), xytext=(8, (i - (n - 1) / 2) * 14),
                              textcoords="offset points", color=c, fontsize=8.5, va="center",
                              bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
            if m.w180 is not None:
                ax_m.axvline(m.w180, color=c, ls="-.", lw=1)
                ax_f.axvline(m.w180, color=c, ls="-.", lw=1)
                mg = float(np.interp(np.log10(m.w180), np.log10(w), mag))
                ax_m.annotate("", xy=(m.w180, 0.0), xytext=(m.w180, mg), arrowprops=dict(arrowstyle="<->", color=c, lw=1.3))
                ax_m.annotate(f"MG={m.MG_dB:.1f} dB", xy=(m.w180, mg / 2), xytext=(8, (i - (n - 1) / 2) * 14),
                              textcoords="offset points", color=c, fontsize=8.5, va="center",
                              bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    if extra:
        for lab, sis in extra:
            mag, fase = bode_datos(sis, w)
            ax_m.semilogx(w, mag, color=NARANJA, ls="-.", label=lab)
            ax_f.semilogx(w, fase, color=NARANJA, ls="-.")
    ax_m.axhline(0, color="k", lw=0.8)
    ax_f.axhline(-180, color="k", lw=0.8)
    ax_m.set_ylabel("Magnitud [dB]")
    ax_f.set_ylabel("Fase [°]")
    ax_f.set_xlabel("ω [rad/s]")
    ax_m.legend(loc="best")
    lo, hi = ax_f.get_ylim()
    paso = 45 if hi - lo < 600 else 90
    ax_f.set_yticks(np.arange(np.floor(lo / paso) * paso, np.ceil(hi / paso) * paso + 1, paso))
    ax_m.grid(True, which="both", alpha=0.25)
    ax_f.grid(True, which="both", alpha=0.25)


def fig_bode(sistemas, titulo="Diagrama de Bode", w=None, asintotas=True, marcas=True, extra=None):
    fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(9, 7), gridspec_kw=dict(height_ratios=[1.1, 1]))
    _dibujar_bode(a1, a2, sistemas, w=w, asintotas=asintotas, marcas=marcas, extra=extra)
    a1.set_title(titulo)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  Nyquist
# ----------------------------------------------------------------------------
def _cruces_eje_real(sis: Sistema, w) -> list[float]:
    m = margenes(sis, w)
    return [-1.0 / mg for _, mg, _ in m.cruces_fase]


def _dibujar_nyquist(ax, sistemas, ventana, w=None, flechas=True, anotar_conteo=True):
    n = len(sistemas)
    for i, (lab, sis) in enumerate(sistemas):
        ww = rejilla(sis, n=6000) if w is None else w
        L = sis.respuesta(ww)
        ok = np.isfinite(L) & (np.abs(L) < 1e6)
        st = _estilo(i, n)
        txt = lab
        if anotar_conteo:
            try:
                c = nyquist_conteo(sis, guardar_contorno=False)
                txt = f"{lab}  (N={c.N}, P={c.P} → Z={c.Z}{', marginal' if c.marginal else ''})"
            except Exception:
                pass
        ax.plot(L.real[ok], L.imag[ok], label=txt, **st)
        ax.plot(L.real[ok], -L.imag[ok], color=st["color"], ls=":", lw=1.2)
        if flechas:
            x0, x1, y0, y1 = ventana
            dentro = np.where(ok & (L.real > x0) & (L.real < x1) & (L.imag > y0) & (L.imag < y1))[0]
            if dentro.size > 20:
                k = dentro[len(dentro) // 3]
                k2 = min(k + max(len(dentro) // 100, 2), len(L) - 1)
                ax.annotate("", xy=(L.real[k2], L.imag[k2]), xytext=(L.real[k], L.imag[k]),
                            arrowprops=dict(arrowstyle="->", color=st["color"], lw=1.4))
        for xc in _cruces_eje_real(sis, ww):
            if ventana[0] < xc < ventana[1]:
                ax.plot([xc], [0], "o", ms=4, color=st["color"])
    th = np.linspace(0, 2 * np.pi, 400)
    ax.plot(np.cos(th), np.sin(th), color="gray", lw=0.8, ls="--")
    ax.plot([-1], [0], "x", color="k", ms=9, mew=2, label="−1")
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlim(ventana[0], ventana[1])
    ax.set_ylim(ventana[2], ventana[3])
    ax.set_xlabel("Re L(jω)")
    ax.set_ylabel("Im L(jω)")
    ax.set_aspect("equal", adjustable="box")


def _ventana_nyquist(sistemas) -> tuple:
    R = 1.6
    for _, sis in sistemas:
        for xc in _cruces_eje_real(sis, None):
            R = max(R, 1.5 * abs(xc))
    R = min(R, 40.0)
    return (-R, 0.6 * R, -R * 0.8, R * 0.8)


def fig_nyquist(sistemas, titulo="Diagrama de Nyquist", ventana=None):
    """Vista general + zoom alrededor de −1. Línea llena ω>0, punteada ω<0. Los puntos son cruces con el eje real."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5.6))
    v = ventana or _ventana_nyquist(sistemas)
    _dibujar_nyquist(a1, sistemas, v)
    a1.set_title(titulo + " (vista general)")
    a1.legend(loc="best", fontsize=8)
    _dibujar_nyquist(a2, sistemas, (-2.2, 0.8, -1.5, 1.5), anotar_conteo=False)
    a2.set_title("Zoom alrededor de −1")
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  Nichols
# ----------------------------------------------------------------------------
def _dibujar_nichols(ax, sistemas, niveles=(-12, -6, -3, -1, 0, 1, 3, 6, 12), w=None, resaltar_Mr=True, ylim=None):
    cont = contornos_M(niveles)
    for nd, tramos in cont.items():
        for f, g in tramos:
            ax.plot(f, g, color="#9a9a9a", lw=0.8)
        if abs(nd) == 1:                      # evita amontonar etiquetas junto al contorno de 0 dB
            continue
        f, g = max(tramos, key=lambda t: len(t[0]))
        idx = int(np.argmax(g)) if nd >= 0 else int(np.argmin(g))
        ax.text(f[idx], g[idx], f"{nd:g} dB", fontsize=7, color="#6a6a6a", ha="center", va="bottom" if nd >= 0 else "top")
    n = len(sistemas)
    xs, ys = [], []
    for i, (lab, sis) in enumerate(sistemas):
        ww = rejilla(sis, n=6000) if w is None else w
        mag, fase = bode_datos(sis, ww)
        st = _estilo(i, n)
        ax.plot(fase, mag, label=lab, **st)
        xs += [fase.min(), fase.max()]
        ys += [np.nanmin(mag), np.nanmax(mag)]
        if resaltar_Mr and np.all(sis.polos_lazo_cerrado().real < -1e-9):     # solo si el lazo cerrado es estable
            try:
                cf = cerrado_frecuencia(sis)
                if cf.Mr_dB > 0.05 and np.isfinite(cf.Mr_dB):
                    for f, g in contornos_M([cf.Mr_dB])[float(cf.Mr_dB)]:
                        ax.plot(f, g, color=st["color"], lw=1.1, ls=":")
                    ax.plot([], [], color=st["color"], ls=":", label=f"  contorno Mr = {cf.Mr_dB:.2f} dB")
            except Exception:
                pass
    ax.plot([-180], [0], "x", color="k", ms=10, mew=2, label="−1  (−180°, 0 dB)")
    ax.set_xlabel("Fase de L [°]")
    ax.set_ylabel("Magnitud de L [dB]")
    ax.set_xlim(max(min(xs) - 15, -400), min(max(xs) + 15, 20))
    ax.set_ylim(*(ylim or (max(min(ys) - 5, -80), min(max(ys) + 5, 80))))
    ax.set_xticks(np.arange(-360, 1, 45))
    ax.legend(loc="best", fontsize=8)


def fig_nichols(sistemas, titulo="Carta de Nichols", niveles=(-12, -6, -3, -1, 0, 1, 3, 6, 12), ylim=None):
    """Curvas L(jω) sobre los contornos M (|T| constante). El Mr es el contorno tangente más alto."""
    fig, ax = plt.subplots(figsize=(9, 7))
    _dibujar_nichols(ax, sistemas, niveles, ylim=ylim)
    ax.set_title(titulo)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  temporal
# ----------------------------------------------------------------------------
def _dibujar_escalon(ax, sistemas, t_final=None, orden_pade=8, anotar=True):
    n = len(sistemas)
    ymax = 1.5
    for i, (lab, sis) in enumerate(sistemas):
        r = respuesta_escalon(sis, t_final=t_final, orden_pade=orden_pade)
        st = _estilo(i, n)
        y = r.y if r.estable else np.clip(r.y, -4.0, 4.0)
        ax.plot(r.t, y, label=lab + ("" if r.estable else "  (INESTABLE, recortado a ±4)"), **st)
        if r.estable and r.Mp is not None:
            yss = r.valor_final
            ax.plot([r.tp], [yss * (1 + r.Mp / 100)], "o", ms=4, color=st["color"])
            if anotar:
                ax.annotate(f"Mp={r.Mp:.1f}%", (r.tp, yss * (1 + r.Mp / 100)), textcoords="offset points", xytext=(6, 6),
                            fontsize=8, color=st["color"])
            if r.ts:
                ax.axvline(r.ts, color=st["color"], ls=":", lw=0.9)
            ymax = max(ymax, 1.25 * yss * (1 + r.Mp / 100))
        elif not r.estable:
            ymax = max(ymax, 4.2)
    ax.axhline(1.0, color="k", lw=0.7)
    ax.axhspan(0.98, 1.02, color="gray", alpha=0.12)
    ax.set_ylim(-0.2 if ymax < 4.2 else -4.2, ymax)
    ax.set_xlim(0, None)
    ax.set_xlabel("t [s]")
    ax.set_ylabel("y(t)")
    ax.legend(loc="best")


def fig_temporal(sistemas, titulo="Respuesta temporal de lazo cerrado", t_final=None, orden_pade=8):
    """Escalón (con Mp y ts marcados, banda del 2 %) + rampa y error de seguimiento."""
    fig = plt.figure(figsize=(12, 6.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.35, 1])
    a1 = fig.add_subplot(gs[:, 0])
    a2 = fig.add_subplot(gs[0, 1])
    a3 = fig.add_subplot(gs[1, 1])
    _dibujar_escalon(a1, sistemas, t_final, orden_pade)
    a1.set_title(titulo + " — escalón unitario")
    n = len(sistemas)
    for i, (lab, sis) in enumerate(sistemas):
        r = respuesta_rampa(sis, t_final=t_final, orden_pade=orden_pade)
        st = _estilo(i, n)
        if i == 0:
            a2.plot(r.t, r.t, color="k", lw=0.8, label="referencia")
        if r.estable and np.all(np.isfinite(r.y)):
            a2.plot(r.t, r.y, **st)
            a3.plot(r.t, r.error, **st, label=lab + ("" if r.e_ss_numerico is None else f" (ess≈{r.e_ss_numerico:.3g})"))
    a2.set_title("Rampa unitaria")
    a2.set_ylabel("y(t)")
    a3.set_title("Error e(t) = r − y")
    a3.set_xlabel("t [s]")
    a3.legend(fontsize=7.5)
    a2.legend(fontsize=7.5)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  polos y ceros
# ----------------------------------------------------------------------------
def fig_polos_ceros(sis: Sistema, titulo="Polos y ceros", orden_pade=8):
    """Plano s: polos y ceros de lazo abierto y polos de lazo cerrado. Izquierda: vista completa; derecha: zoom
    cerca del origen (donde suelen estar los polos dominantes)."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.8))
    k, z, p = sis.raices()
    pc = sis.polos_lazo_cerrado(orden_pade)
    todo = np.r_[p, z, pc]
    mags = np.abs(todo[np.abs(todo) > 1e-9])
    # zoom: radio que contiene los polos dominantes de lazo cerrado (los de parte real más cercana al eje)
    dom = pc[np.argsort(-pc.real)][: max(3, len(pc) // 2)]
    r_zoom = 2.2 * max(np.abs(dom).max(), 0.05) if dom.size else 1.0
    for ax, R, nombre in ((a1, None, "vista completa"), (a2, r_zoom, "zoom cerca del origen")):
        ax.plot(p.real, p.imag, "x", color=AZUL, ms=9, mew=2, label="polos de lazo abierto")
        if z.size:
            ax.plot(z.real, z.imag, "o", mfc="none", color=AZUL, ms=8, mew=1.6, label="ceros de lazo abierto")
        ax.plot(pc.real, pc.imag, "s", color=ROJO, ms=6, label="polos de lazo cerrado")
        ax.axvline(0, color="k", lw=0.9)
        ax.axhline(0, color="k", lw=0.5)
        xmax = (todo.real.max() if R is None else R)
        ax.axvspan(0, max(xmax, 1e-3) * 10, color="red", alpha=0.06)
        if R is None:
            ancho = max(mags.max() if mags.size else 1.0, 1.0) * 1.15
            ax.set_xlim(-ancho, max(todo.real.max() * 1.3, ancho * 0.15))
            ax.set_ylim(-ancho * 0.6, ancho * 0.6)
        else:
            ax.set_xlim(-R, 0.4 * R)
            ax.set_ylim(-R * 0.7, R * 0.7)
        ax.set_xlabel("Re s")
        ax.set_ylabel("Im s")
        ax.set_title(f"{titulo} — {nombre}")
    a1.legend(loc="best", fontsize=8)
    a1.text(0.98, 0.02, "zona roja: semiplano derecho", transform=a1.transAxes, ha="right", fontsize=8, color=ROJO)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  estabilidad en función de K
# ----------------------------------------------------------------------------
def fig_estabilidad_K(sis: Sistema, K_ref: float, casos: list[dict], rangos: dict, orden_pade=8,
                      titulo="Estabilidad en función de K"):
    from .estabilidad import _poli_base, _polos_kappa
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.8))
    n, d = _poli_base(sis, orden_pade)
    his = [hi for lo, hi in rangos.get("positivo", []) if np.isfinite(hi)]
    k_lo, k_hi = (min(his) / 40.0, max(his) * 6.0) if his else (1e-2, 1e2)
    kap = np.logspace(np.log10(k_lo), np.log10(k_hi), 600)            # solo κ > 0, alrededor de la frontera
    R = np.array([_polos_kappa(n, d, k) for k in kap])      # (n_k, n_polos)
    sc = None
    for j in range(R.shape[1]):
        sc = a1.scatter(R[:, j].real, R[:, j].imag, c=np.log10(kap * K_ref), s=4, cmap="viridis")
    k0, z0, p0 = sis.raices()
    a1.plot(p0.real, p0.imag, "kx", ms=8, mew=1.6, label="polos de lazo abierto (K→0)")
    if sc is not None:
        cb = fig.colorbar(sc, ax=a1)
        cb.set_label("log10 K")
    a1.axvline(0, color="r", lw=1.2)
    paleta = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf"]
    for ic, c in enumerate(casos):
        c["_color"] = paleta[ic % len(paleta)]
        a1.plot(c["polos"].real, c["polos"].imag, "o", mfc="none", ms=9, mew=1.6, color=c["_color"])
    a1.set_xlabel("Re s")
    a1.set_ylabel("Im s")
    a1.set_title("Polos de lazo cerrado al variar K (círculos: casos analizados)")
    pts = np.concatenate([c["polos"] for c in casos] + [p0]) if casos else p0
    esc = 1.5 * max(np.abs(pts.real).max(), np.abs(pts.imag).max(), 1e-3)
    a1.set_xlim(-esc, esc * 0.6)
    a1.set_ylim(-esc * 0.8, esc * 0.8)
    a1.legend(loc="lower left", fontsize=8)
    # respuestas al escalón de cada caso
    for c in casos:
        e = c.get("escalon")
        if e is None or not np.all(np.isfinite(e.y)):
            continue
        y = np.clip(e.y, -6, 6)
        a2.plot(e.t, y, color=c["_color"], label=f"K={c['K']:.4g}: {c['categoria']}")
    a2.axhline(1, color="k", lw=0.6)
    a2.set_ylim(-3, 5)
    a2.set_xlabel("t [s]")
    a2.set_ylabel("y(t)")
    a2.set_title("Escalón unitario para cada K (recortado a ±6)")
    a2.legend(fontsize=8, loc="upper right")
    pos = rangos.get("positivo", [])
    txt = "Estable para: " + (" ∪ ".join(f"{K_ref * lo:.4g} < K < {'∞' if np.isinf(hi) else format(K_ref * hi, '.4g')}" for lo, hi in pos) if pos else "ningún K > 0")
    fig.suptitle(f"{titulo}   —   {txt}", fontsize=11)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  sensibilidad
# ----------------------------------------------------------------------------
def fig_sensibilidad(sistemas, titulo="Lazo cerrado en frecuencia: |T| y |S|"):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)
    n = len(sistemas)
    for i, (lab, sis) in enumerate(sistemas):
        cf = cerrado_frecuencia(sis)
        st = _estilo(i, n)
        estable = bool(np.all(sis.polos_lazo_cerrado().real < -1e-9))
        if estable:
            l1 = f"{lab}  (Mr={cf.Mr_dB:.2f} dB en {cf.wr:.3g}" + (f", BW={cf.BW:.3g})" if cf.BW else ")")
            l2 = f"{lab}  (Ms={cf.Ms_dB:.2f} dB)"
        else:
            l1 = l2 = f"{lab}  (lazo cerrado INESTABLE)"
        a1.semilogx(cf.w, 20 * np.log10(np.abs(cf.T)), label=l1, **st)
        a2.semilogx(cf.w, 20 * np.log10(np.abs(cf.S)), label=l2, **st)
        if estable:
            a1.plot([cf.wr], [cf.Mr_dB], "o", ms=4, color=st["color"])
            a2.plot([cf.wMs], [cf.Ms_dB], "o", ms=4, color=st["color"])
            if cf.BW:
                a1.axvline(cf.BW, color=st["color"], ls=":", lw=0.9)
    a1.axhline(-3, color="k", lw=0.6, ls="--")
    a1.axhline(0, color="k", lw=0.6)
    a2.axhline(0, color="k", lw=0.6)
    a1.set_title("T(jω) = L/(1+L)")
    a2.set_title("S(jω) = 1/(1+L)")
    for a in (a1, a2):
        a.set_xlabel("ω [rad/s]")
        a.set_ylabel("[dB]")
        a.legend(loc="best")
        a.grid(True, which="both", alpha=0.25)
        a.set_ylim(-60, None)
    fig.suptitle(titulo)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  descomposición del Bode en factores (para "reconstruir G(s) desde el Bode")
# ----------------------------------------------------------------------------
def fig_descomposicion_bode(sis: Sistema, titulo="Descomposición del Bode en factores"):
    """Cada factor de la forma de Bode (K_B, integradores, polos, ceros) y su suma (= curva total)."""
    fb = sis.forma_bode()
    w = rejilla(sis, n=3000)
    fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(9.5, 8), gridspec_kw=dict(height_ratios=[1.2, 1]))
    s = 1j * w
    curvas = [(f"K_B = {fb.K_B:.4g} ({20 * np.log10(abs(fb.K_B)):.2f} dB)", np.full_like(w, 20 * np.log10(abs(fb.K_B))),
               np.full_like(w, 0.0 if fb.K_B > 0 else -180.0))]
    if fb.N != 0:
        mag = -20 * fb.N * np.log10(w)
        curvas.append((f"{'integrador' if fb.N > 0 else 'derivador'} s^{-fb.N}" if abs(fb.N) > 1 else ("integrador 1/s" if fb.N > 0 else "derivador s"),
                       mag, np.full_like(w, -90.0 * fb.N)))
    for r in fb.reales:
        f = (1 + (s / r["wb"]) * (-1 if r["spd"] else 1))
        val = f if r["tipo"] == "cero" else 1 / f
        curvas.append((f"{r['tipo']} real{' SPD' if r['spd'] else ''} en {r['wb']:.4g}", 20 * np.log10(abs(val)), np.degrees(np.unwrap(np.angle(val)))))
    for q in fb.pares:
        f = (s**2 / q["wn"] ** 2 + 2 * q["zeta"] * s / q["wn"] + 1)
        val = f if q["tipo"] == "cero" else 1 / f
        curvas.append((f"par de {q['tipo']}s ωn={q['wn']:.4g}, ζ={q['zeta']:.3g}", 20 * np.log10(abs(val)), np.degrees(np.unwrap(np.angle(val)))))
    for i, (lab, m, f) in enumerate(curvas):
        c = COLORES[(i + 1) % len(COLORES)]
        a1.semilogx(w, m, color=c, lw=1.3, label=lab)
        a2.semilogx(w, f, color=c, lw=1.3)
    mag, fase = bode_datos(sis, w)
    a1.semilogx(w, mag, color="k", lw=2.4, label="TOTAL L(jω)")
    a1.semilogx(w, fb.magnitud_asintotica_dB(w), color=ROJO, ls="--", lw=1.3, label="asíntota total")
    a2.semilogx(w, fase, color="k", lw=2.4)
    for wb, d, desc in fb.quiebres():
        for a in (a1, a2):
            a.axvline(wb, color="gray", ls=":", lw=0.8)
    a1.axhline(0, color="k", lw=0.6)
    a2.axhline(-180, color="k", lw=0.6)
    a1.set_ylabel("Magnitud [dB]")
    a2.set_ylabel("Fase [°]")
    a2.set_xlabel("ω [rad/s]")
    a1.set_title(titulo + "  —  L(s) = " + fb.texto())
    a1.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  compensación (panel completo)
# ----------------------------------------------------------------------------
def fig_compensacion(sistemas, Gc_sistema: Sistema | None = None, titulo="Compensación", orden_pade=8, t_final=None):
    """Panel 2×2: Bode (magnitud y fase), Nichols y escalón, para comparar sin compensar / compensado."""
    fig = plt.figure(figsize=(14, 8.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1])
    a_m = fig.add_subplot(gs[0, 0])
    a_f = fig.add_subplot(gs[1, 0], sharex=a_m)
    a_n = fig.add_subplot(gs[0, 1])
    a_t = fig.add_subplot(gs[1, 1])
    extra = [("Gc(jω) (solo el compensador)", Gc_sistema)] if Gc_sistema is not None else None
    _dibujar_bode(a_m, a_f, sistemas, asintotas=False, marcas=True, extra=extra)
    _dibujar_nichols(a_n, sistemas)
    _dibujar_escalon(a_t, sistemas, t_final, orden_pade)
    a_m.set_title(titulo + " — Bode")
    a_n.set_title("Carta de Nichols")
    a_t.set_title("Escalón de lazo cerrado")
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
#  comparación de varios diseños candidatos
# ----------------------------------------------------------------------------
def fig_comparacion_candidatos(sis0: Sistema, candidatos, titulo="Comparación de diseños", t_final=None, orden_pade=8):
    """Superpone la planta y todos los diseños que salieron bien: Bode (magnitud y fase) y escalón."""
    sist = [("Planta sin compensar", sis0)]
    for d in candidatos:
        if d.exito and d.sistema is not None:
            sist.append((f"{d.tipo}" + ("" if d.cumple else " (no cumple)"), d.sistema))
    fig = plt.figure(figsize=(14, 7.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.2, 1])
    a_m = fig.add_subplot(gs[0, 0])
    a_f = fig.add_subplot(gs[1, 0], sharex=a_m)
    a_t = fig.add_subplot(gs[:, 1])
    _dibujar_bode(a_m, a_f, sist, marcas=False)
    _dibujar_escalon(a_t, sist, t_final, orden_pade, anotar=False)
    a_m.set_title(titulo + " — Bode")
    a_t.set_title("Escalón de lazo cerrado")
    fig.tight_layout()
    return fig
