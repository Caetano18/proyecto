"""Estabilidad en función de la ganancia K y ganancias de diseño (para un MF, un MG o un Mr dados)."""
from __future__ import annotations

import numpy as np
import control as ct
from scipy.optimize import brentq

from .sistema import Sistema
from .frecuencia import (bode_datos, cerrado_frecuencia, margenes, rejilla, _envolver_180)
from .temporal import respuesta_escalon


# ----------------------------------------------------------------------------
#  rangos de K para los que el lazo cerrado es estable
# ----------------------------------------------------------------------------
def _poli_base(sis: Sistema, orden_pade: int = 8) -> tuple[np.ndarray, np.ndarray]:
    n, d = sis.num_den()
    if sis.retardo > 0:
        pn, pd = ct.pade(sis.retardo, orden_pade)
        n, d = np.polymul(n, pn), np.polymul(d, pd)
    return n, d


def _polos_kappa(n: np.ndarray, d: np.ndarray, kappa: float) -> np.ndarray:
    return np.roots(np.polyadd(d, kappa * n))


def _estable(n, d, kappa) -> bool:
    r = _polos_kappa(n, d, kappa)
    return bool(r.size == 0 or np.all(r.real < -1e-9 * np.maximum(1.0, np.abs(r))))


def rangos_estables(sis: Sistema, orden_pade: int = 8, k_min: float = 1e-6, k_max: float = 1e6,
                    n_grilla: int = 2400) -> dict:
    """Intervalos del factor de ganancia κ (que multiplica a L) con lazo cerrado estable.

    Devuelve {"positivo": [(lo, hi), ...], "negativo": [(lo, hi), ...]} con κ>0 y κ<0 (módulo) respectivamente.
    lo = 0 significa estable desde ganancia nula; hi = inf, estable para toda ganancia.
    """
    n, d = _poli_base(sis, orden_pade)
    grilla = np.logspace(np.log10(k_min), np.log10(k_max), n_grilla)
    out = {}
    for nombre, signo in (("positivo", 1.0), ("negativo", -1.0)):
        est = np.array([_estable(n, d, signo * g) for g in grilla])
        tramos = []
        i = 0
        while i < len(est):
            if est[i]:
                j = i
                while j + 1 < len(est) and est[j + 1]:
                    j += 1
                lo = 0.0 if i == 0 else _bisecar(n, d, signo, grilla[i - 1], grilla[i], True)
                hi = np.inf if j == len(est) - 1 else _bisecar(n, d, signo, grilla[j], grilla[j + 1], False)
                tramos.append((float(lo), float(hi)))
                i = j + 1
            else:
                i += 1
        out[nombre] = tramos
    return out


def _bisecar(n, d, signo, a, b, sube: bool) -> float:
    """Frontera entre a (no estable si sube / estable si no) y b, por bisección geométrica."""
    for _ in range(80):
        m = np.sqrt(a * b)
        e = _estable(n, d, signo * m)
        if e == sube:
            b = m
        else:
            a = m
    return float(np.sqrt(a * b))


def ganancias_criticas(sis: Sistema) -> list[tuple[float, float]]:
    """[(ω, κ_crítico)] de los cruces de fase (L sobre el eje real negativo): κ = 1/|L(jω)|."""
    m = margenes(sis)
    return [(w, mg) for w, mg, _ in m.cruces_fase]


# ----------------------------------------------------------------------------
#  clasificación de la dinámica de lazo cerrado y casos de K
# ----------------------------------------------------------------------------
def clasificar_polos(polos: np.ndarray) -> tuple[str, str]:
    """(categoría, descripción) de la respuesta según los polos de lazo cerrado."""
    if polos.size == 0:
        return "estatico", "sin dinámica"
    tol = 1e-9 * np.maximum(1.0, np.abs(polos))
    spd = polos[polos.real > tol]
    eje = polos[np.abs(polos.real) <= tol]
    if spd.size:
        dom = spd[np.argmax(spd.real)]
        if abs(dom.imag) > 1e-9:
            return "inestable", f"inestable: {spd.size} polo(s) en el SPD, oscilación creciente (ω≈{abs(dom.imag):.3g} rad/s)"
        return "inestable", f"inestable: {spd.size} polo(s) en el SPD, divergencia monótona"
    if eje.size:
        w = max(abs(e.imag) for e in eje)
        if w > 1e-9:
            return "marginal", f"marginal: oscilación sostenida a ω≈{w:.4g} rad/s"
        return "marginal", "marginal: polo en el origen (no se estabiliza)"
    # estable: polo dominante = el de parte real más cercana al eje
    dom = polos[np.argmax(polos.real)]
    if abs(dom.imag) > 1e-9:
        z = -dom.real / abs(dom)
        calif = "casi sin amortiguamiento" if z < 0.1 else ("poco amortiguada" if z < 0.4 else "bien amortiguada")
        return "oscilatorio", f"estable, oscilación {calif} (ζ≈{z:.2f}, ωn≈{abs(dom):.3g} rad/s)"
    return "sobreamortiguado", f"estable, sin oscilación (polo dominante en {dom.real:.3g})"


def casos_de_K(sis: Sistema, K_ref: float = 1.0, Ks: list[float] | None = None, orden_pade: int = 8,
               con_temporal: bool = True) -> list[dict]:
    """Analiza distintos valores de K (K = K_ref·κ). Si `Ks` es None se eligen automáticamente
    representantes de cada comportamiento: estable poco/muy oscilatorio, marginal, inestable y K<0."""
    rangos = rangos_estables(sis, orden_pade)
    if Ks is None:
        cand = []
        pos = rangos["positivo"]
        for lo, hi in pos:
            if np.isfinite(hi):
                cand += [hi / 5.0, 0.6 * hi, hi, 2.0 * hi]
            else:
                cand += [max(lo, 1.0) * 2.0]
        if not pos:
            cand += [1.0]
        if not rangos["negativo"] or rangos["negativo"][0][0] > 0:
            cand += [-0.2]
        cand += [1.0]
        kappas = sorted(set(float(f"{c:.4g}") for c in cand))
        Ks = [K_ref * k for k in kappas]
    out = []
    for K in Ks:
        kappa = K / K_ref if K_ref else K
        n, d = _poli_base(sis, orden_pade)
        polos = _polos_kappa(n, d, kappa)
        cat, desc = clasificar_polos(polos)
        caso = dict(K=K, kappa=kappa, polos=polos, categoria=cat, descripcion=desc, escalon=None)
        if con_temporal:
            try:
                caso["escalon"] = respuesta_escalon(sis.con_ganancia(kappa), orden_pade=orden_pade)
            except Exception as exc:     # pragma: no cover
                caso["escalon"] = None
                caso["error"] = str(exc)
        out.append(caso)
    return out


# ----------------------------------------------------------------------------
#  ganancia K para una especificación (receta "K para un MF / MG / Mr")
# ----------------------------------------------------------------------------
def kappa_para_MF(sis: Sistema, MF_obj: float, w: np.ndarray | None = None) -> list[tuple[float, float]]:
    """[(ω_c, κ)] tales que el lazo κ·L tiene margen de fase MF_obj (°) en ω_c.

    Se resuelve la condición de fase  ∠L(jω) = -180° + MF  (no depende de κ) y luego κ = 1/|L(jω)|.
    """
    if w is None:
        w = rejilla(sis, n=8000)
    _, fase = bode_datos(sis, w)
    objetivo = -180.0 + MF_obj
    sol = []
    for m in range(-6, 7):
        t = objetivo + 360.0 * m
        if not (fase.min() <= t <= fase.max()):
            continue
        dif = fase - t
        for i in np.where(dif[:-1] * dif[1:] < 0)[0]:
            f = lambda x: _envolver_180(np.degrees(np.angle(sis.respuesta(x))) - t)
            try:
                wc = brentq(f, w[i], w[i + 1], xtol=1e-13)
            except ValueError:
                continue
            mod = abs(sis.respuesta(wc))
            if np.isfinite(mod) and mod > 0:
                sol.append((float(wc), float(1.0 / mod)))
    return sorted(set(sol))


def kappa_para_MG(sis: Sistema, MG_veces: float) -> list[tuple[float, float]]:
    """[(ω180, κ)] tales que el lazo κ·L tiene margen de ganancia MG_veces."""
    return [(w, mg / MG_veces) for w, mg in ganancias_criticas(sis)]


def kappa_para_Mr(sis: Sistema, Mr_dB_obj: float, k_rango: tuple[float, float] = (1e-4, 1e4), n: int = 160,
                  orden_pade: int = 8) -> list[float]:
    """κ (puede haber varios) tales que el lazo cerrado de κ·L tiene un pico de resonancia Mr = Mr_dB_obj."""
    w = rejilla(sis, n=5000)
    ks = np.logspace(np.log10(k_rango[0]), np.log10(k_rango[1]), n)

    def mr(k):
        s2 = sis.con_ganancia(k)
        if not np.all(s2.polos_lazo_cerrado(orden_pade).real < -1e-9):
            return np.nan
        return cerrado_frecuencia(s2, w).Mr_dB

    vals = np.array([mr(k) for k in ks])
    sol = []
    for i in range(len(ks) - 1):
        a, b = vals[i], vals[i + 1]
        if np.isnan(a) or np.isnan(b):
            continue
        if (a - Mr_dB_obj) * (b - Mr_dB_obj) < 0:
            try:
                sol.append(float(brentq(lambda k: mr(k) - Mr_dB_obj, ks[i], ks[i + 1], xtol=1e-10)))
            except ValueError:
                pass
    return sol
