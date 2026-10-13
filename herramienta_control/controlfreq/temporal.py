"""Respuesta temporal del lazo cerrado: escalón, rampa y métricas (Mp, tp, tr, ts, error)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import control as ct

from .sistema import Sistema


@dataclass
class RespuestaTemporal:
    t: np.ndarray
    y: np.ndarray
    estable: bool
    valor_final: float | None = None
    Mp: float | None = None              # sobreimpulso en %
    tp: float | None = None              # instante del pico
    tr: float | None = None              # tiempo de subida 10-90 %
    ts: float | None = None              # tiempo de establecimiento 2 %
    ts5: float | None = None             # 5 %
    nota: str = ""


def tiempo_automatico(polos_cl: np.ndarray, t_final: float | None = None, n: int = 20000,
                      t_max: float = 5000.0) -> np.ndarray:
    """Vector de tiempos (uniforme) ajustado a la dinámica del lazo cerrado."""
    if t_final is None:
        re = np.abs(polos_cl.real[np.abs(polos_cl.real) > 1e-9])
        if polos_cl.size == 0 or re.size == 0:
            t_final = 50.0
        else:
            inest = polos_cl.real > 1e-9
            if inest.any():
                t_final = min(8.0 / polos_cl.real[inest].max(), t_max)
                im = np.abs(polos_cl.imag).max()
                t_final = max(t_final, 12.0 * 2 * np.pi / im) if im > 0 else t_final
            else:
                t_final = min(8.0 / re.min(), t_max)
                im = np.abs(polos_cl.imag).max()
                if im > 0:
                    t_final = max(t_final, 6.0 * 2 * np.pi / im)
        t_final = max(t_final, 1e-3)
    return np.linspace(0.0, t_final, n)


def respuesta_escalon(sis: Sistema, t: np.ndarray | None = None, t_final: float | None = None,
                      orden_pade: int = 8) -> RespuestaTemporal:
    """Escalón unitario en la referencia + métricas (si el lazo es estable)."""
    pc = sis.polos_lazo_cerrado(orden_pade)
    estable = bool(np.all(pc.real < -1e-9))
    if t is None:
        t = tiempo_automatico(pc, t_final)
    T = sis.T(orden_pade)
    _, y = ct.step_response(T, t)
    y = np.asarray(y, float).ravel()
    r = RespuestaTemporal(t=t, y=y, estable=estable)
    if not np.all(np.isfinite(y)):
        r.nota = "la respuesta diverge (valores no finitos)"
        return r
    if not estable:
        r.nota = "lazo cerrado inestable: no se calculan métricas"
        return r
    yss = float(ct.dcgain(T)) if np.isfinite(ct.dcgain(T)) else float(y[-1])
    r.valor_final = yss
    if abs(yss) < 1e-12:
        r.nota = "valor final nulo: no se calculan métricas"
        return r
    yn = y / yss
    i_pico = int(np.argmax(yn))
    r.Mp = float(max(yn[i_pico] - 1.0, 0.0) * 100.0)
    r.tp = float(t[i_pico])

    def primer_cruce(nivel: float) -> float | None:
        idx = np.where(yn >= nivel)[0]
        if idx.size == 0:
            return None
        j = idx[0]
        if j == 0:
            return float(t[0])
        return float(t[j - 1] + (nivel - yn[j - 1]) * (t[j] - t[j - 1]) / (yn[j] - yn[j - 1]))

    t10, t90 = primer_cruce(0.1), primer_cruce(0.9)
    r.tr = None if (t10 is None or t90 is None) else t90 - t10

    def ts_tol(tol: float) -> float | None:
        fuera = np.where(np.abs(yn - 1.0) > tol)[0]
        if fuera.size == 0:
            return 0.0
        if fuera[-1] >= len(t) - 1:
            return None                      # no se estableció dentro de la ventana simulada
        return float(t[fuera[-1] + 1])

    r.ts, r.ts5 = ts_tol(0.02), ts_tol(0.05)
    if r.ts is None:
        r.nota = "no se estabiliza dentro de la ventana simulada (aumentar T_FINAL)"
    return r


@dataclass
class RespuestaRampa:
    t: np.ndarray
    y: np.ndarray
    error: np.ndarray
    e_ss_numerico: float | None
    e_ss_teorico: float | None
    estable: bool


def respuesta_rampa(sis: Sistema, t: np.ndarray | None = None, t_final: float | None = None,
                    orden_pade: int = 8) -> RespuestaRampa:
    """Rampa unitaria r(t)=t, error e(t)=r-y y error en régimen (numérico y 1/Kv)."""
    pc = sis.polos_lazo_cerrado(orden_pade)
    estable = bool(np.all(pc.real < -1e-9))
    if t is None:
        t = tiempo_automatico(pc, t_final)
    T = sis.T(orden_pade)
    res = ct.forced_response(T, t, U=t)
    y = np.asarray(res.outputs, float).ravel()
    e = t - y
    e_ss = float(np.mean(e[-max(len(e) // 50, 5):])) if estable and np.all(np.isfinite(e)) else None
    Kv = sis.constantes_error()["Kv"]
    e_teo = None if Kv == 0 else (0.0 if np.isinf(Kv) else 1.0 / Kv)
    return RespuestaRampa(t=t, y=y, error=e, e_ss_numerico=e_ss, e_ss_teorico=e_teo, estable=estable)
