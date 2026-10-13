"""Diseño de compensadores en frecuencia (recetas del apunte).

Todos los diseños siguen el mismo esquema:
  1. Se fija la ganancia κ que cumple el error en régimen (Kp, Kv o Ka)  ->  L0 = κ·L.
  2. Se diseña una red (adelanto / atraso / atraso-adelanto / PI / PID) sobre L0, con ganancia
     unitaria en continua, de modo que el error no cambie.
  3. Se VERIFICA el lazo compensado (márgenes, estabilidad) y, si no cumple, se itera
     (reserva δ del adelanto, nuevo cruce del atraso, ...).
El compensador devuelto, `Gc`, ya incluye κ:  Gc(s) = κ · (red).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import control as ct
from scipy.optimize import brentq

from .sistema import Sistema, tf_a_texto
from .frecuencia import margenes, bode_datos, rejilla, Margenes
from .metricas import Metricas, calcular_metricas, evaluar_especificaciones, cumple_todo


class ErrorDiseno(Exception):
    """El diseño no se pudo hacer (con un mensaje explicativo para el usuario)."""


@dataclass
class ParamsDiseno:
    delta_adelanto: float = 5.0        # reserva inicial de fase del adelanto [°]
    delta_max: float = 30.0            # máxima reserva que se prueba [°]
    paso_delta: float = 1.0
    delta_atraso: float = 6.0          # reserva de fase del atraso [°]
    razon_cero_atraso: float = 10.0    # el cero del atraso se ubica en ωc'/razón
    wc_nuevo: float | None = None      # fuerza el nuevo cruce del atraso / atraso-adelanto
    etapas_adelanto: int | str = "auto"   # 1, 2 o "auto" (2 si hace falta más de 60°)
    phi_max_etapa: float = 60.0        # máxima fase aportada por una etapa de adelanto [°]
    redondear: bool = True
    cifras: int = 2
    N_derivativo: float = 10.0         # filtro de la acción derivativa del PID


@dataclass
class Diseno:
    tipo: str
    exito: bool
    Gc: ct.TransferFunction | None = None
    sistema: Sistema | None = None
    kappa: float = 1.0
    parametros: dict = field(default_factory=dict)
    iteraciones: list = field(default_factory=list)
    notas: list = field(default_factory=list)
    metricas: Metricas | None = None
    cumplimiento: list | None = None

    @property
    def cumple(self) -> bool:
        return bool(self.exito and self.cumplimiento is not None and cumple_todo(self.cumplimiento))

    def texto(self) -> str:
        if self.Gc is None:
            return "(sin compensador)"
        return tf_a_texto(self.Gc, "polos_ceros", 5)


# ----------------------------------------------------------------------------
#  utilidades
# ----------------------------------------------------------------------------
def _sig(x: float, cifras: int) -> float:
    if x == 0 or not np.isfinite(x):
        return x
    return float(f"{x:.{cifras}g}")


def _const(k: float) -> ct.TransferFunction:
    return ct.tf([float(k)], [1.0])


def _red_atraso_adelanto(T: float, a: float) -> ct.TransferFunction:
    """(T s + 1)/(a T s + 1)."""
    return ct.tf([T, 1.0], [a * T, 1.0])


def _estable(sis: Sistema, orden_pade: int = 8) -> bool:
    return bool(np.all(sis.polos_lazo_cerrado(orden_pade).real < -1e-9))


def kappa_por_error(sis: Sistema, Kp: float | None = None, Kv: float | None = None, Ka: float | None = None) -> float:
    """Factor κ que lleva las constantes de error de la planta a las pedidas (la mayor κ si hay varias)."""
    c = sis.constantes_error()
    kap = []
    req = {"Kp": (Kp, 0), "Kv": (Kv, 1), "Ka": (Ka, 2)}
    for nombre, (valor, tipo_req) in req.items():
        if valor is None:
            continue
        N = c["tipo"]
        if N == tipo_req:
            kap.append(valor / c[nombre])
        elif N > tipo_req:
            kap.append(1.0)           # ya es de mayor tipo: el error es nulo
        else:
            raise ErrorDiseno(
                f"Pediste {nombre} = {valor}, pero la planta es de tipo {N}: {nombre} sería 0. "
                f"Hace falta agregar {tipo_req - N} integrador(es) (por ejemplo, un PI). Usá DISENO = 'PI'.")
    return max(kap) if kap else 1.0


def _frecuencias_con_modulo(sis: Sistema, mod_dB: float, w: np.ndarray) -> list[float]:
    """Frecuencias donde |L(jω)| = mod_dB (todas las raíces)."""
    mag, _ = bode_datos(sis, w)
    sol = []
    d = mag - mod_dB
    for i in np.where(np.isfinite(d[:-1]) & np.isfinite(d[1:]) & (d[:-1] * d[1:] < 0))[0]:
        try:
            sol.append(brentq(lambda x: 20 * np.log10(abs(sis.respuesta(x))) - mod_dB, w[i], w[i + 1], xtol=1e-13))
        except ValueError:
            pass
    return sol


def _frecuencias_con_fase(sis: Sistema, fase_deg: float, w: np.ndarray) -> list[float]:
    """Frecuencias donde la fase continua de L vale fase_deg (módulo 360°)."""
    _, ph = bode_datos(sis, w)
    sol = []
    for m in range(-8, 9):
        t = fase_deg + 360.0 * m
        if not (np.nanmin(ph) <= t <= np.nanmax(ph)):
            continue
        d = ph - t
        for i in np.where(d[:-1] * d[1:] < 0)[0]:
            try:
                sol.append(brentq(lambda x: ((np.degrees(np.angle(sis.respuesta(x))) - t + 180) % 360) - 180, w[i], w[i + 1], xtol=1e-13))
            except ValueError:
                pass
    return sorted(set(sol))


def _cumple_margenes(sis: Sistema, MF_req: float | None, MG_req: float | None, orden_pade: int = 8) -> tuple[bool, Margenes]:
    m = margenes(sis)
    ok = _estable(sis, orden_pade)
    if MF_req is not None and m.MF is not None:
        ok = ok and m.MF >= MF_req - 1e-9
    if MG_req is not None and m.MG_veces is not None:
        ok = ok and m.MG_veces >= MG_req - 1e-9
    return ok, m


def _finalizar(d: Diseno, sis0: Sistema, especs: dict, orden_pade: int, t_final=None) -> Diseno:
    """Calcula métricas completas del sistema compensado y las compara con las especificaciones."""
    if d.sistema is None:
        return d
    d.metricas = calcular_metricas(d.sistema, orden_pade=orden_pade, t_final=t_final)
    d.cumplimiento = evaluar_especificaciones(d.metricas, especs or {})
    return d


def _MG_req(especs: dict) -> float | None:
    if especs.get("MG") is not None:
        return float(especs["MG"])
    if especs.get("MG_dB") is not None:
        return 10 ** (especs["MG_dB"] / 20.0)
    return None


# ----------------------------------------------------------------------------
#  1) solo ganancia
# ----------------------------------------------------------------------------
def diseno_solo_ganancia(sis0: Sistema, kappa: float, especs: dict, orden_pade: int = 8) -> Diseno:
    Gc = _const(kappa)
    d = Diseno("solo_ganancia", True, Gc=Gc, sistema=sis0.con_compensador(Gc), kappa=kappa,
               parametros=dict(kappa=kappa))
    d.notas.append("Solo se ajusta la ganancia para cumplir el error en régimen (sin red de compensación).")
    return _finalizar(d, sis0, especs, orden_pade)


# ----------------------------------------------------------------------------
#  2) adelanto
# ----------------------------------------------------------------------------
def diseno_adelanto(sis0: Sistema, kappa: float, especs: dict, p: ParamsDiseno | None = None,
                    orden_pade: int = 8) -> Diseno:
    """Adelanto (T s+1)/(αT s+1), α<1, con iteración sobre la reserva δ (receta del apunte).

    φm = MF_req - MF0 + δ ; α = (1-sin φm)/(1+sin φm) ; el nuevo cruce es ωm, donde |L0| = 10 log α [dB]
    (1/T = ωm√α, 1/(αT) = ωm/√α)."""
    p = p or ParamsDiseno()
    MF_req = especs.get("MF")
    if MF_req is None:
        raise ErrorDiseno("El adelanto necesita la especificación de margen de fase (MF).")
    MG_req = _MG_req(especs)
    L0 = sis0.con_compensador(_const(kappa))
    w = rejilla(L0, n=6000)
    m0 = margenes(L0, w)
    d = Diseno("adelanto", False, kappa=kappa)
    if m0.MF is None:
        raise ErrorDiseno("L0 nunca cruza 0 dB: no hace falta adelanto (ya hay margen de fase infinito).")
    MF0, wc0 = m0.MF, m0.wc
    d.parametros.update(MF0=MF0, wc0=wc0)
    delta = p.delta_adelanto
    while delta <= p.delta_max + 1e-9:
        phim = MF_req - MF0 + delta
        it = dict(delta=delta, phim=phim)
        d.iteraciones.append(it)
        if phim <= 0:
            it["nota"] = "no hace falta fase adicional"
            delta += p.paso_delta
            continue
        n_et = p.etapas_adelanto if isinstance(p.etapas_adelanto, int) else (2 if phim > p.phi_max_etapa else 1)
        phi_et = phim / n_et
        if phi_et >= 89.0:
            it["nota"] = "φm demasiado grande (≥ 89° por etapa)"
            break
        a = (1 - np.sin(np.radians(phi_et))) / (1 + np.sin(np.radians(phi_et)))
        objetivo_dB = n_et * 10 * np.log10(a)                    # |L0(jωm)| = α^(n/2) en dB
        cands = _frecuencias_con_modulo(L0, objetivo_dB, w)
        if not cands:
            it["nota"] = "no existe una frecuencia con la ganancia requerida"
            delta += p.paso_delta
            continue
        wm = min(cands, key=lambda x: abs(np.log(x / wc0)))
        T = 1.0 / (wm * np.sqrt(a))
        red = _red_atraso_adelanto(T, a)
        for _ in range(n_et - 1):
            red = red * _red_atraso_adelanto(T, a)
        Gc = _const(kappa) * red
        sis_c = sis0.con_compensador(Gc)
        ok, mc = _cumple_margenes(sis_c, MF_req, MG_req, orden_pade)
        it.update(alfa=a, wm=wm, T=T, cero=1 / T, polo=1 / (a * T), etapas=n_et, MF=mc.MF, MG_dB=mc.MG_dB, cumple=ok)
        if ok:
            d.exito, d.Gc, d.sistema = True, Gc, sis_c
            d.parametros.update(delta=delta, phim=phim, alfa=a, T=T, wm=wm, cero=1 / T, polo=1 / (a * T), etapas=n_et)
            break
        delta += p.paso_delta
    if not d.exito:
        con_mf = [it for it in d.iteraciones if it.get("MF") is not None and it["MF"] >= MF_req - 1e-9]
        if con_mf and MG_req is not None:
            d.notas.append(f"El adelanto alcanza el margen de fase pedido, pero con margen de ganancia insuficiente "
                           f"(≤ {max(it['MG_dB'] for it in con_mf):.1f} dB frente a los {20 * np.log10(MG_req):.1f} dB pedidos): "
                           "al subir el cruce, el adelanto acerca el cruce de fase. Probar atraso o atraso-adelanto.")
        else:
            mejor = max((it["MF"] for it in d.iteraciones if it.get("MF") is not None), default=None)
            d.notas.append("No se logró el margen de fase pedido con adelanto"
                           + (f" (el mejor fue {mejor:.1f}° con δ hasta {p.delta_max:g}°)" if mejor is not None else "")
                           + ". Probar atraso o atraso-adelanto.")
        return d
    if p.redondear:
        Tr, ar = _sig(d.parametros["T"], p.cifras + 1), _sig(d.parametros["alfa"], p.cifras + 1)
        red = _red_atraso_adelanto(Tr, ar)
        for _ in range(d.parametros["etapas"] - 1):
            red = red * _red_atraso_adelanto(Tr, ar)
        Gc_r = _const(kappa) * red
        sis_r = sis0.con_compensador(Gc_r)
        ok, _ = _cumple_margenes(sis_r, MF_req, MG_req, orden_pade)
        if ok:
            d.Gc, d.sistema = Gc_r, sis_r
            d.parametros.update(T=Tr, alfa=ar, cero=1 / Tr, polo=1 / (ar * Tr))
            d.notas.append(f"Parámetros redondeados a {p.cifras + 1} cifras significativas (se verificó que siguen cumpliendo).")
    d.notas.append("El adelanto sube el cruce y el ancho de banda (respuesta más rápida) pero amplifica el ruido de alta frecuencia en 1/α.")
    return _finalizar(d, sis0, especs, orden_pade)


# ----------------------------------------------------------------------------
#  3) atraso
# ----------------------------------------------------------------------------
def _beta_exacto(A: float, w: float, T: float) -> float:
    """β tal que |(jωT+1)/(β jωT+1)|·A = 1 (A > 1 es el módulo de L0 en ω)."""
    f = lambda b: abs((1j * w * T + 1) / (b * 1j * w * T + 1)) * A - 1.0
    return float(brentq(f, 1.0 + 1e-9, 1e7))


def diseno_atraso(sis0: Sistema, kappa: float, especs: dict, p: ParamsDiseno | None = None,
                  orden_pade: int = 8) -> Diseno:
    """Atraso (T s+1)/(βT s+1), β>1. El nuevo cruce ωc' es donde ∠L0 = -180° + MF + δ; β baja |L0| a 0 dB ahí;
    el cero se ubica en ωc'/razón (1/T = ωc'/10). No cambia Kv (ganancia 1 en continua)."""
    p = p or ParamsDiseno()
    MF_req = especs.get("MF")
    if MF_req is None:
        raise ErrorDiseno("El atraso necesita la especificación de margen de fase (MF).")
    MG_req = _MG_req(especs)
    L0 = sis0.con_compensador(_const(kappa))
    w = rejilla(L0, n=6000)
    d = Diseno("atraso", False, kappa=kappa)
    mag, _ = bode_datos(L0, w)
    if p.wc_nuevo is not None:
        cands = [p.wc_nuevo]
    else:
        objetivo = -180.0 + MF_req + p.delta_atraso
        cands = [x for x in _frecuencias_con_fase(L0, objetivo, w) if abs(L0.respuesta(x)) > 1.0]
        cands = sorted(cands, reverse=True)
    if not cands:
        d.notas.append("No existe una frecuencia (con |L0|>1) donde la fase de L0 permita el margen de fase pedido: "
                       "un atraso solo no alcanza (probar atraso-adelanto).")
        return d
    wcn = cands[0]
    for intento in range(14):
        A = abs(L0.respuesta(wcn))
        T = p.razon_cero_atraso / wcn
        it = dict(wc_nuevo=wcn, A_dB=20 * np.log10(A), T=T)
        d.iteraciones.append(it)
        if A <= 1.0:
            it["nota"] = "|L0| ≤ 1 en ωc': no hace falta atenuar"
            break
        beta = _beta_exacto(A, wcn, T)
        red = _red_atraso_adelanto(T, beta)
        Gc = _const(kappa) * red
        sis_c = sis0.con_compensador(Gc)
        ok, mc = _cumple_margenes(sis_c, MF_req, MG_req, orden_pade)
        it.update(beta=beta, cero=1 / T, polo=1 / (beta * T), MF=mc.MF, MG_dB=mc.MG_dB, cumple=ok)
        if ok:
            d.exito, d.Gc, d.sistema = True, Gc, sis_c
            d.parametros.update(wc_nuevo=wcn, beta=beta, T=T, cero=1 / T, polo=1 / (beta * T), A_dB=20 * np.log10(A))
            break
        wcn *= 0.85          # bajar el cruce un poco más
    if not d.exito:
        d.notas.append("No se logró cumplir MF/MG con un atraso (probar atraso-adelanto).")
        return d
    if p.redondear:
        beta_r, T_r = _sig(d.parametros["beta"], p.cifras), _sig(d.parametros["T"], p.cifras)
        Gc_r = _const(kappa) * _red_atraso_adelanto(T_r, beta_r)
        sis_r = sis0.con_compensador(Gc_r)
        ok, _ = _cumple_margenes(sis_r, MF_req, MG_req, orden_pade)
        if ok:
            d.Gc, d.sistema = Gc_r, sis_r
            d.parametros.update(beta=beta_r, T=T_r, cero=1 / T_r, polo=1 / (beta_r * T_r))
            d.notas.append(f"β y T redondeados a {p.cifras} cifras significativas (se verificó que siguen cumpliendo).")
    d.notas.append("El atraso NO usa su fase: usa su atenuación. Baja el cruce a una zona de mejor fase; la respuesta es más lenta "
                   "y el dipolo (cero y polo cerca del origen) deja una cola lenta.")
    return _finalizar(d, sis0, especs, orden_pade)


# ----------------------------------------------------------------------------
#  4) atraso-adelanto
# ----------------------------------------------------------------------------
def diseno_atraso_adelanto(sis0: Sistema, kappa: float, especs: dict, p: ParamsDiseno | None = None,
                           orden_pade: int = 8) -> Diseno:
    """Atraso-adelanto: la parte de adelanto (centrada en ωc') aporta la fase; la de atraso, la atenuación.

    ωc' por defecto es ω180 de L0 (o p.wc_nuevo). φm = MF_req - (180° + ∠L0(jωc')) + δ ;
    β = |L0(jωc')|·|adelanto(jωc')| ; cero del atraso en ωc'/razón."""
    p = p or ParamsDiseno()
    MF_req = especs.get("MF")
    if MF_req is None:
        raise ErrorDiseno("El atraso-adelanto necesita la especificación de margen de fase (MF).")
    MG_req = _MG_req(especs)
    L0 = sis0.con_compensador(_const(kappa))
    w = rejilla(L0, n=6000)
    m0 = margenes(L0, w)
    d = Diseno("atraso_adelanto", False, kappa=kappa)
    wcn = p.wc_nuevo or m0.w180 or m0.wc
    if wcn is None:
        raise ErrorDiseno("No se pudo elegir ωc' (L0 no tiene cruces); indicá `wc_nuevo` en PARAMS_DISENO.")
    _, ph = bode_datos(L0, np.array([wcn]))
    MF_disp = 180.0 + float(ph[0])
    A0 = abs(L0.respuesta(wcn))
    d.parametros.update(wc_nuevo=wcn, MF_disponible=MF_disp)
    delta = p.delta_atraso
    while delta <= p.delta_atraso + 30:
        phim = max(MF_req - MF_disp + delta, 0.0)
        it = dict(delta=delta, phim=phim)
        d.iteraciones.append(it)
        if phim >= 89:
            it["nota"] = "φm ≥ 89°"
            break
        a = (1 - np.sin(np.radians(phim))) / (1 + np.sin(np.radians(phim))) if phim > 0 else 1.0
        T1 = 1.0 / (wcn * np.sqrt(a))
        adelanto = _red_atraso_adelanto(T1, a) if a < 1 else _const(1.0)
        A = A0 / np.sqrt(a)                    # |L0(jωc')|·|adelanto(jωc')| = A0/√α
        if A > 1.0:
            T2 = p.razon_cero_atraso / wcn
            beta = _beta_exacto(A, wcn, T2)
            atraso = _red_atraso_adelanto(T2, beta)
        else:
            T2, beta, atraso = None, 1.0, _const(1.0)
        Gc = _const(kappa) * adelanto * atraso
        sis_c = sis0.con_compensador(Gc)
        ok, mc = _cumple_margenes(sis_c, MF_req, MG_req, orden_pade)
        it.update(alfa=a, beta=beta, T1=T1, T2=T2, MF=mc.MF, MG_dB=mc.MG_dB, cumple=ok)
        if ok:
            d.exito, d.Gc, d.sistema = True, Gc, sis_c
            d.parametros.update(delta=delta, phim=phim, alfa=a, beta=beta, T1=T1, T2=T2,
                                cero_adelanto=1 / T1, polo_adelanto=1 / (a * T1),
                                cero_atraso=None if T2 is None else 1 / T2,
                                polo_atraso=None if T2 is None else 1 / (beta * T2))
            break
        delta += 2.0
    if not d.exito:
        d.notas.append("No se logró cumplir las especificaciones con atraso-adelanto en ese ωc' (probar otro `wc_nuevo`).")
        return d
    d.notas.append("Atraso-adelanto: el adelanto da la fase y la velocidad; el atraso da la atenuación sin tocar el error.")
    return _finalizar(d, sis0, especs, orden_pade)


# ----------------------------------------------------------------------------
#  5) PI y Ziegler-Nichols
# ----------------------------------------------------------------------------
def diseno_PI(sis0: Sistema, kappa: float, especs: dict, p: ParamsDiseno | None = None, orden_pade: int = 8) -> Diseno:
    """PI = κ (Ti s + 1)/(Ti s): agrega un integrador (anula el error al escalón si la planta es tipo 0).
    Ti = razón/ωc ('razón' = 10 por defecto, cuesta unos 5,7° de MF); se aumenta la razón hasta cumplir."""
    p = p or ParamsDiseno()
    MF_req, MG_req = especs.get("MF"), _MG_req(especs)
    L0 = sis0.con_compensador(_const(kappa))
    m0 = margenes(L0)
    d = Diseno("PI", False, kappa=kappa)
    wc = m0.wc
    if wc is None:
        raise ErrorDiseno("L0 no cruza 0 dB: no se puede ubicar el cero del PI (fijar `wc_nuevo`).")
    wc = p.wc_nuevo or wc
    for razon in (p.razon_cero_atraso, 15, 20, 30, 50, 100):
        Ti = razon / wc
        Gc = _const(kappa) * ct.tf([Ti, 1.0], [Ti, 0.0])
        sis_c = sis0.con_compensador(Gc)
        ok, mc = _cumple_margenes(sis_c, MF_req, MG_req, orden_pade)
        d.iteraciones.append(dict(razon=razon, Ti=Ti, MF=mc.MF, MG_dB=mc.MG_dB, cumple=ok))
        if ok:
            d.exito, d.Gc, d.sistema = True, Gc, sis_c
            d.parametros.update(Kp=kappa, Ti=Ti, razon=razon, cero=1 / Ti)
            break
    if not d.exito:
        d.notas.append("El PI no alcanza los márgenes pedidos (la planta ya tiene poco margen en ωc).")
        return d
    d.notas.append("El PI sube el tipo del sistema (error nulo ante el escalón si la planta era tipo 0).")
    return _finalizar(d, sis0, especs, orden_pade)


def disenos_ziegler_nichols(sis0: Sistema, especs: dict, p: ParamsDiseno | None = None, orden_pade: int = 8) -> list[Diseno]:
    """P, PI y PID de Ziegler-Nichols por ganancia última (K_u = ganancia crítica, P_u = 2π/ω180).

    Se aplican a la planta con su ganancia actual (sin κ). Son sintonías de partida: no buscan cumplir
    las especificaciones (se informa cuáles cumplen)."""
    p = p or ParamsDiseno()
    m0 = margenes(sis0)
    if m0.w180 is None or m0.MG_veces is None:
        raise ErrorDiseno("Ziegler-Nichols necesita un cruce de fase (ω180): el lazo nunca llega a -180°.")
    Ku, wu = m0.MG_veces, m0.w180
    Pu = 2 * np.pi / wu
    out = []
    for tipo, Kp, Ti, Td in (("PID_ZN_P", 0.5 * Ku, None, None), ("PID_ZN_PI", 0.45 * Ku, Pu / 1.2, None),
                             ("PID_ZN", 0.6 * Ku, Pu / 2, Pu / 8)):
        if Ti is None:
            Gc = _const(Kp)
        elif Td is None:
            Gc = _const(Kp) * ct.tf([Ti, 1.0], [Ti, 0.0])
        else:
            # Kp (1 + 1/(Ti s) + Td s/(1 + Td s/N))
            der = ct.tf([Td, 0.0], [Td / p.N_derivativo, 1.0])
            Gc = _const(Kp) * (ct.tf([1.0], [1.0]) + ct.tf([1.0], [Ti, 0.0]) + der)
        sis_c = sis0.con_compensador(Gc)
        d = Diseno(tipo, True, Gc=Gc, sistema=sis_c, kappa=1.0,
                   parametros=dict(Ku=Ku, wu=wu, Pu=Pu, Kp=Kp, Ti=Ti, Td=Td, N=p.N_derivativo if Td else None))
        d.notas.append("Sintonía de Ziegler-Nichols (punto de partida): suele dar poco margen de fase (≈25°-30°).")
        out.append(_finalizar(d, sis0, especs, orden_pade))
    return out


# ----------------------------------------------------------------------------
#  selector automático
# ----------------------------------------------------------------------------
NOMBRES_CANDIDATOS = ("solo_ganancia", "adelanto", "atraso", "atraso_adelanto", "PI", "PID_ZN")


def disenar(sis0: Sistema, especs: dict, tipos=("auto",), p: ParamsDiseno | None = None,
            orden_pade: int = 8) -> tuple[list[Diseno], Diseno | None, list[str]]:
    """Diseña los compensadores pedidos y elige el recomendado.

    tipos: "auto"/"todos" (solo ganancia, adelanto, atraso, atraso-adelanto), o nombres sueltos
    ("adelanto", "atraso", "atraso_adelanto", "PI", "PID_ZN", "solo_ganancia").
    Recomendado = el que cumple todas las especificaciones con menor tiempo de establecimiento
    (o, si no hay ts, el de menor orden). Devuelve (candidatos, recomendado, mensajes).
    """
    p = p or ParamsDiseno()
    msgs: list[str] = []
    kappa = kappa_por_error(sis0, especs.get("Kp"), especs.get("Kv"), especs.get("Ka"))
    msgs.append(f"Ganancia por error en régimen: κ = {kappa:.5g}" + (" (la planta ya cumple el error)" if abs(kappa - 1) < 1e-9 else ""))
    nombres = list(tipos)
    if nombres == ["auto"] or nombres == ["todos"]:
        nombres = ["solo_ganancia", "adelanto", "atraso", "atraso_adelanto"]
    hechos: list[Diseno] = []
    for nm in nombres:
        try:
            if nm == "solo_ganancia":
                hechos.append(diseno_solo_ganancia(sis0, kappa, especs, orden_pade))
            elif nm == "adelanto":
                hechos.append(diseno_adelanto(sis0, kappa, especs, p, orden_pade))
            elif nm == "atraso":
                hechos.append(diseno_atraso(sis0, kappa, especs, p, orden_pade))
            elif nm == "atraso_adelanto":
                hechos.append(diseno_atraso_adelanto(sis0, kappa, especs, p, orden_pade))
            elif nm == "PI":
                hechos.append(diseno_PI(sis0, kappa, especs, p, orden_pade))
            elif nm in ("PID_ZN", "PID"):
                hechos.extend(disenos_ziegler_nichols(sis0, especs, p, orden_pade))
            else:
                msgs.append(f"Tipo de diseño desconocido: {nm!r} (opciones: {', '.join(NOMBRES_CANDIDATOS)}).")
        except ErrorDiseno as e:
            hechos.append(Diseno(nm, False, notas=[str(e)]))
    validos = [d for d in hechos if d.cumple]
    reco = None
    if validos:
        def clave(d: Diseno):
            ts = d.metricas.escalon.ts if (d.metricas and d.metricas.escalon and d.metricas.escalon.ts is not None) else np.inf
            orden = 0 if d.tipo == "solo_ganancia" else (1 if d.tipo in ("adelanto", "atraso", "PI") else 2)
            return (ts, orden)
        reco = min(validos, key=clave)
    return hechos, reco, msgs
