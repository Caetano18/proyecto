"""Métricas completas de un sistema y verificación contra especificaciones."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .sistema import Sistema
from .frecuencia import (Margenes, CerradoFrecuencia, margenes, cerrado_frecuencia, rejilla,
                         zeta_desde_Mr, Mp_desde_zeta, zeta_desde_MF)
from .temporal import RespuestaTemporal, RespuestaRampa, respuesta_escalon, respuesta_rampa


@dataclass
class Metricas:
    estable: bool
    polos_cl: np.ndarray
    constantes: dict
    margenes: Margenes
    cerrado: CerradoFrecuencia
    escalon: RespuestaTemporal | None = None
    rampa: RespuestaRampa | None = None
    zeta_Mr: float | None = None
    Mp_Mr: float | None = None
    zeta_MF: float | None = None
    Mp_MF: float | None = None
    zeta_regla: float | None = None
    Mp_regla: float | None = None

    def fila(self) -> dict:
        """Diccionario plano con los valores más usados (None si no existen)."""
        m, c, e = self.margenes, self.cerrado, self.escalon
        return dict(
            estable=self.estable, Kp=self.constantes["Kp"], Kv=self.constantes["Kv"], Ka=self.constantes["Ka"],
            MF=m.MF, wc=m.wc, MG_veces=m.MG_veces, MG_dB=m.MG_dB, w180=m.w180, margen_retardo=m.margen_retardo,
            Mr_dB=c.Mr_dB, wr=c.wr, BW=c.BW, Ms_dB=c.Ms_dB,
            Mp=None if e is None else e.Mp, tp=None if e is None else e.tp,
            tr=None if e is None else e.tr, ts=None if e is None else e.ts,
        )


def calcular_metricas(sis: Sistema, orden_pade: int = 8, t_final: float | None = None, temporal: bool = True,
                      w: np.ndarray | None = None) -> Metricas:
    if w is None:
        w = rejilla(sis, n=6000)
    pc = sis.polos_lazo_cerrado(orden_pade)
    estable = bool(np.all(pc.real < -1e-9))
    m = margenes(sis, w)
    cf = cerrado_frecuencia(sis, w)
    out = Metricas(estable=estable, polos_cl=pc, constantes=sis.constantes_error(), margenes=m, cerrado=cf)
    if temporal and estable:
        out.escalon = respuesta_escalon(sis, t_final=t_final, orden_pade=orden_pade)
        out.rampa = respuesta_rampa(sis, t_final=t_final, orden_pade=orden_pade)
    elif temporal:
        out.escalon = respuesta_escalon(sis, t_final=t_final, orden_pade=orden_pade)
    if estable:
        out.zeta_Mr = zeta_desde_Mr(cf.Mr)
        out.Mp_Mr = None if out.zeta_Mr is None else Mp_desde_zeta(out.zeta_Mr)
        if m.MF is not None and m.MF > 0:
            out.zeta_MF = zeta_desde_MF(m.MF)
            out.Mp_MF = None if out.zeta_MF is None else Mp_desde_zeta(out.zeta_MF)
            out.zeta_regla = m.MF / 100.0
            out.Mp_regla = Mp_desde_zeta(min(out.zeta_regla, 0.999))
    return out


# ----------------------------------------------------------------------------
#  especificaciones
# ----------------------------------------------------------------------------
CLAVES_ESPECS = ("Kp", "Kv", "Ka", "MF", "MG", "MG_dB", "Mp", "ts", "wc_min", "BW_min", "Mr_dB")


def _num(x, fmt="{:.4g}") -> str:
    if x is None:
        return "—"
    if isinstance(x, (float, np.floating)) and np.isinf(x):
        return "∞"
    return fmt.format(x)


def evaluar_especificaciones(met: Metricas, especs: dict) -> list[dict]:
    """Compara las métricas con las especificaciones.

    especs (cualquiera puede ser None):
      Kp, Kv, Ka (>=, con 1 % de tolerancia), MF [°] (>=), MG [veces] (>=), MG_dB (>=), Mp [%] (<=),
      ts [s] (<=, 2 %), wc_min [rad/s] (>=), BW_min [rad/s] (>=), Mr_dB (<=).
    Devuelve filas con: nombre, requisito, obtenido, cumple (True/False/None si no se pudo medir).
    """
    f = met.fila()
    filas = [dict(nombre="Estable en lazo cerrado", requisito="sí", obtenido="sí" if met.estable else "NO", cumple=met.estable)]

    def fila(nombre, req, obt, ok):
        filas.append(dict(nombre=nombre, requisito=req, obtenido=obt, cumple=ok))

    def mayor(nombre, clave, req, unidad="", tol=0.0, fmt="{:.4g}"):
        v = f.get(clave)
        ok = None if v is None else bool(v >= req * (1 - tol) - 1e-12)
        fila(nombre, f"≥ {_num(req)}{unidad}", _num(v, fmt) + (unidad if v is not None else ""), ok)

    def menor(nombre, clave, req, unidad="", fmt="{:.4g}"):
        v = f.get(clave)
        ok = None if v is None else bool(v <= req + 1e-12)
        fila(nombre, f"≤ {_num(req)}{unidad}", _num(v, fmt) + (unidad if v is not None else ""), ok)

    for k in ("Kp", "Kv", "Ka"):
        if especs.get(k) is not None:
            mayor(k, k, especs[k], " s⁻¹" if k == "Kv" else ("" if k == "Kp" else " s⁻²"), tol=0.01)
    if especs.get("MF") is not None:
        v = f["MF"]
        fila("Margen de fase", f"≥ {_num(especs['MF'])}°", "—" if v is None else f"{v:.4g}°", True if v is None and met.estable else (None if v is None else bool(v >= especs["MF"] - 1e-9)))
    if especs.get("MG") is not None:
        v = f["MG_veces"]
        fila("Margen de ganancia", f"≥ {_num(especs['MG'])} (veces)", "∞" if v is None else f"{v:.4g} ({f['MG_dB']:.3g} dB)", True if v is None else bool(v >= especs["MG"] - 1e-9))
    if especs.get("MG_dB") is not None:
        v = f["MG_dB"]
        fila("Margen de ganancia", f"≥ {_num(especs['MG_dB'])} dB", "∞" if v is None else f"{v:.4g} dB", True if v is None else bool(v >= especs["MG_dB"] - 1e-9))
    if especs.get("Mp") is not None:
        menor("Sobreimpulso Mp", "Mp", especs["Mp"], " %")
    if especs.get("ts") is not None:
        menor("Tiempo de establecimiento (2 %)", "ts", especs["ts"], " s")
    if especs.get("wc_min") is not None:
        mayor("Frecuencia de cruce ωc", "wc", especs["wc_min"], " rad/s")
    if especs.get("BW_min") is not None:
        mayor("Ancho de banda", "BW", especs["BW_min"], " rad/s")
    if especs.get("Mr_dB") is not None:
        menor("Pico de resonancia Mr", "Mr_dB", especs["Mr_dB"], " dB")
    return filas


def cumple_todo(filas: list[dict]) -> bool:
    return all(r["cumple"] is not False for r in filas)
