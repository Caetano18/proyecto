"""Construcción del sistema y propiedades básicas.

El lazo es siempre  L(s) = C(s) · G(s) · H(s) · e^{-τ s}  con realimentación negativa:

    r --->(+)--> C(s) --> G(s) --e^{-τs}--> y
           ^-                               |
           +---------- H(s) <---------------+

 * G: planta        * C: compensador (1 por defecto)
 * H: sensor (1 = realimentación unitaria)    * τ: retardo puro (exacto en frecuencia,
   Padé en el dominio del tiempo).

Este módulo tiene:
  - los *constructores* de G(s) (coeficientes, texto, polos/ceros, factores y asíntotas del Bode);
  - la clase `Sistema` (evaluación de L(jω), polos, ceros, tipo, constantes de error, lazo cerrado);
  - la descomposición en *forma de Bode* (K_B, N, quiebres) y utilidades de formato.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
import control as ct

TOL_ORIGEN = 1e-7        # |raíz| menor que esto (relativo) se considera raíz en el origen
TOL_CANCELA = 1e-6       # tolerancia para cancelar polos y ceros iguales
s = ct.tf("s")


# ----------------------------------------------------------------------------
#  utilidades de polinomios / funciones de transferencia
# ----------------------------------------------------------------------------
def coeficientes(tf: ct.TransferFunction) -> tuple[np.ndarray, np.ndarray]:
    """(num, den) como arreglos reales, sin ceros a la izquierda."""
    num = np.array(tf.num[0][0], dtype=float).ravel()
    den = np.array(tf.den[0][0], dtype=float).ravel()
    num = np.trim_zeros(num, "f")
    den = np.trim_zeros(den, "f")
    if num.size == 0:
        num = np.array([0.0])
    if den.size == 0:
        raise ValueError("El denominador de la función de transferencia es cero.")
    return num, den


def a_tf(obj) -> ct.TransferFunction:
    """Convierte un número, (num, den) o TransferFunction en TransferFunction."""
    if isinstance(obj, ct.TransferFunction):
        return obj
    if isinstance(obj, (int, float, np.floating, np.integer)):
        return ct.tf([float(obj)], [1.0])
    if isinstance(obj, (tuple, list)) and len(obj) == 2:
        return ct.tf(np.atleast_1d(obj[0]).astype(float), np.atleast_1d(obj[1]).astype(float))
    raise TypeError(f"No se puede interpretar como función de transferencia: {obj!r}")


def _cancelar(z: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Elimina pares polo-cero (prácticamente) iguales."""
    z = list(z)
    p = list(p)
    for zi in list(z):
        for pj in list(p):
            if abs(zi - pj) <= TOL_CANCELA * max(1.0, abs(zi)):
                z.remove(zi)
                p.remove(pj)
                break
    return np.array(z, dtype=complex), np.array(p, dtype=complex)


def _es_origen(r: complex, escala: float) -> bool:
    return abs(r) <= TOL_ORIGEN * max(1.0, escala)


# ----------------------------------------------------------------------------
#  constructores de G(s)
# ----------------------------------------------------------------------------
def tf_desde_expresion(expresion: str, **variables) -> ct.TransferFunction:
    """Evalúa un texto como  "K/(s*(s+1)*(s+2))"  usando 's' y las variables dadas (K, a, ...).

    También se pueden usar: np, pi, sqrt, exp, log10. El retardo NO va acá: usar `retardo`.
    """
    ns = {"s": s, "np": np, "pi": np.pi, "sqrt": np.sqrt, "exp": np.exp, "log10": np.log10}
    ns.update(variables)
    try:
        res = eval(expresion.replace("^", "**"), {"__builtins__": {}}, ns)  # noqa: S307 (entrada del usuario, uso local)
    except Exception as exc:  # pragma: no cover - mensaje claro para el usuario
        raise ValueError(f"No pude evaluar EXPRESION = {expresion!r}: {exc}") from exc
    return a_tf(res)


def tf_desde_polos_ceros(polos: Sequence[complex] = (), ceros: Sequence[complex] = (), K: float = 1.0,
                         forma: str = "monica") -> ct.TransferFunction:
    """G(s) a partir de polos y ceros (raíces, en rad/s; negativos = semiplano izquierdo).

    forma="monica":  G = K · Π(s - z) / Π(s - p)
    forma="bode":    G = K · Π(1 - s/z) / Π(1 - s/p), con las raíces en 0 como s^N (K = ganancia de Bode K_B)
    """
    polos = np.array(polos, dtype=complex)
    ceros = np.array(ceros, dtype=complex)
    if forma == "monica":
        num = K * np.poly(ceros) if ceros.size else np.array([K])
        den = np.poly(polos) if polos.size else np.array([1.0])
    elif forma == "bode":
        z0 = ceros[np.abs(ceros) > TOL_ORIGEN]
        p0 = polos[np.abs(polos) > TOL_ORIGEN]
        n_orig_p = int(np.sum(np.abs(polos) <= TOL_ORIGEN))
        n_orig_z = int(np.sum(np.abs(ceros) <= TOL_ORIGEN))
        num = np.array([K], dtype=complex)
        for zi in z0:
            num = np.polymul(num, [-1.0 / zi, 1.0])
        den = np.array([1.0], dtype=complex)
        for pi_ in p0:
            den = np.polymul(den, [-1.0 / pi_, 1.0])
        num = np.polymul(num, np.r_[1.0, np.zeros(n_orig_z)])
        den = np.polymul(den, np.r_[1.0, np.zeros(n_orig_p)])
    else:
        raise ValueError("forma debe ser 'monica' o 'bode'")
    return ct.tf(np.real_if_close(num).real, np.real_if_close(den).real)


def tf_desde_factores_bode(K: float | None = None, K_dB: float | Sequence[float] | None = None,
                           integradores: int = 0, derivadores: int = 0,
                           polos: Iterable[float] = (), ceros: Iterable[float] = (),
                           polos_spd: Iterable[float] = (), ceros_spd: Iterable[float] = (),
                           pares_polos: Iterable[tuple[float, float]] = (),
                           pares_ceros: Iterable[tuple[float, float]] = ()) -> ct.TransferFunction:
    """G(s) a partir de los factores que se leen del diagrama de Bode (forma de constantes de tiempo).

        G = K_B · Π(1 + s/z) · Π(s²/wn² + 2ζ s/wn + 1) / ( s^N · Π(1 + s/p) · Π(...) )

    * `K` es la ganancia de Bode; `K_dB` también se acepta, y puede ser una LISTA de ganancias
      en dB que se SUMAN (por ejemplo, [34, -2.41, -40] como las curvas G1, G3 y G4 del enunciado).
    * `polos` / `ceros`: frecuencias de quiebre (rad/s) de factores reales en el semiplano izquierdo.
    * `polos_spd` / `ceros_spd`: ídem, pero con la raíz en el semiplano DERECHO (fase no mínima).
    * `pares_*`: lista de (wn, zeta); zeta negativo => raíces en el semiplano derecho.
    """
    if K is None and K_dB is None:
        K = 1.0
    if K is None:
        K = 10 ** (float(np.sum(K_dB)) / 20.0)
    num = np.array([float(K)])
    den = np.array([1.0])
    for z in ceros:
        num = np.polymul(num, [1.0 / z, 1.0])
    for z in ceros_spd:
        num = np.polymul(num, [-1.0 / z, 1.0])
    for p in polos:
        den = np.polymul(den, [1.0 / p, 1.0])
    for p in polos_spd:
        den = np.polymul(den, [-1.0 / p, 1.0])
    for wn, ze in pares_ceros:
        num = np.polymul(num, [1.0 / wn**2, 2.0 * ze / wn, 1.0])
    for wn, ze in pares_polos:
        den = np.polymul(den, [1.0 / wn**2, 2.0 * ze / wn, 1.0])
    den = np.polymul(den, np.r_[1.0, np.zeros(int(integradores))])
    num = np.polymul(num, np.r_[1.0, np.zeros(int(derivadores))])
    return ct.tf(num, den)


def tf_desde_asintotas(w_ref: float, mag_dB: float, pendiente_inicial: float,
                       quiebres: Iterable[tuple] = ()) -> ct.TransferFunction:
    """Reconstruye G(s) (fase mínima) desde las asíntotas del Bode de magnitud.

    * `w_ref`, `mag_dB`: un punto SOBRE la asíntota de baja frecuencia (por ejemplo, en 0,1 rad/s vale 20 dB).
    * `pendiente_inicial`: pendiente de baja frecuencia en dB/dec (0, -20, -40, ...).
    * `quiebres`: lista de (wb, cambio_de_pendiente) o (wb, cambio, zeta) con cambio en {-20, +20, -40, +40}.
      Con ±40 y `zeta` es un par complejo (si no se da zeta, se toma un par real doble, zeta = 1).
    """
    N = int(round(-pendiente_inicial / 20.0))
    corr = 0.0
    lista = []
    for q in quiebres:
        wb, d = float(q[0]), float(q[1])
        ze = q[2] if len(q) > 2 else None
        lista.append((wb, d, ze))
        if w_ref > wb:                 # un quiebre a la izquierda del punto de referencia ya cambió la pendiente
            corr += d * np.log10(w_ref / wb)
    # mag(w_ref) = 20 log K_B - 20 N log w_ref + corr
    K_B_dB = mag_dB + 20.0 * N * np.log10(w_ref) - corr
    polos, ceros, pp, pc = [], [], [], []
    for wb, d, ze in lista:
        if abs(d) == 20:
            (ceros if d > 0 else polos).append(wb)
        elif abs(d) == 40:
            z_ = 1.0 if ze is None else ze
            (pc if d > 0 else pp).append((wb, z_))
        else:
            raise ValueError(f"Cambio de pendiente no soportado: {d} dB/dec (usar ±20 o ±40).")
    return tf_desde_factores_bode(K_dB=K_B_dB, integradores=max(N, 0), derivadores=max(-N, 0),
                                  polos=polos, ceros=ceros, pares_polos=pp, pares_ceros=pc)


# ----------------------------------------------------------------------------
#  forma de Bode
# ----------------------------------------------------------------------------
@dataclass
class FormaBode:
    """L(s) = K_B Π(1 + s/z..) ... / ( s^N Π(1 + s/p..) ... ) · e^{-τ s}"""
    K_B: float
    N: int                                   # integradores netos (polos en 0 menos ceros en 0)
    reales: list = field(default_factory=list)   # dicts: tipo ('polo'|'cero'), wb, spd (bool)
    pares: list = field(default_factory=list)    # dicts: tipo, wn, zeta (negativo si SPD)
    retardo: float = 0.0

    @property
    def fase_baja_frecuencia(self) -> float:
        """Fase para ω→0 en grados: -90·N (y -180° si K_B < 0)."""
        return -90.0 * self.N + (-180.0 if self.K_B < 0 else 0.0)

    def quiebres(self) -> list[tuple[float, float, str]]:
        """[(frecuencia, cambio de pendiente dB/dec, descripción)] ordenada."""
        out = []
        for r in self.reales:
            d = 20.0 if r["tipo"] == "cero" else -20.0
            out.append((r["wb"], d, f"{r['tipo']} real {'SPD ' if r['spd'] else ''}en {r['wb']:.4g}"))
        for q in self.pares:
            d = 40.0 if q["tipo"] == "cero" else -40.0
            out.append((q["wn"], d, f"par de {q['tipo']}s ωn={q['wn']:.4g}, ζ={q['zeta']:.3g}"))
        return sorted(out)

    def magnitud_asintotica_dB(self, w: np.ndarray) -> np.ndarray:
        w = np.asarray(w, float)
        m = 20.0 * np.log10(abs(self.K_B)) - 20.0 * self.N * np.log10(w)
        for wb, d, _ in self.quiebres():
            m = m + d * np.log10(np.maximum(w / wb, 1.0))
        return m

    def fase_asintotica_deg(self, w: np.ndarray) -> np.ndarray:
        """Fase aproximada por rectas (reales: ωb/10 a 10ωb; pares: ωn·10^∓ζ)."""
        w = np.asarray(w, float)
        lw = np.log10(w)
        ph = np.full_like(w, self.fase_baja_frecuencia)

        def rampa(centro: float, semiancho_dec: float, total: float) -> np.ndarray:
            a, b = np.log10(centro) - semiancho_dec, np.log10(centro) + semiancho_dec
            return total * np.clip((lw - a) / (b - a), 0.0, 1.0)

        for r in self.reales:
            signo = {("cero", False): +1, ("polo", False): -1, ("cero", True): -1, ("polo", True): +1}[(r["tipo"], r["spd"])]
            ph = ph + rampa(r["wb"], 1.0, signo * 90.0)
        for q in self.pares:
            spd = q["zeta"] < 0
            signo = {("cero", False): +1, ("polo", False): -1, ("cero", True): -1, ("polo", True): +1}[(q["tipo"], spd)]
            ph = ph + rampa(q["wn"], max(min(abs(q["zeta"]), 1.0), 0.05), signo * 180.0)
        return ph - np.degrees(self.retardo * w) if self.retardo else ph

    def texto(self) -> str:
        num, den = [], []
        for r in self.reales:
            f = f"(1 {'-' if r['spd'] else '+'} s/{r['wb']:.4g})"
            (num if r["tipo"] == "cero" else den).append(f)
        for q in self.pares:
            f = f"(s²/{q['wn']:.4g}² + {2 * q['zeta'] / q['wn']:.4g}·s + 1)"
            (num if q["tipo"] == "cero" else den).append(f)
        if self.N > 0:
            den.insert(0, "s" if self.N == 1 else f"s^{self.N}")
        elif self.N < 0:
            num.insert(0, "s" if self.N == -1 else f"s^{-self.N}")
        n_txt = f"{self.K_B:.5g}" + ("·" + "·".join(num) if num else "")
        d_txt = "·".join(den) if den else ""
        ret = f" · e^(-{self.retardo:.4g}·s)" if self.retardo else ""
        return f"{n_txt}" + (f" / [{d_txt}]" if d_txt else "") + ret


# ----------------------------------------------------------------------------
#  el sistema (lazo abierto) y sus propiedades
# ----------------------------------------------------------------------------
@dataclass
class Sistema:
    """L(s) = C(s)·G(s)·H(s)·e^{-τ s} con realimentación negativa."""
    G: ct.TransferFunction
    C: ct.TransferFunction | None = None
    H: ct.TransferFunction | None = None
    retardo: float = 0.0
    nombre: str = "G"

    def __post_init__(self):
        self.G = a_tf(self.G)
        self.C = a_tf(1.0 if self.C is None else self.C)
        self.H = a_tf(1.0 if self.H is None else self.H)
        if self.retardo < 0:
            raise ValueError("El retardo no puede ser negativo.")
        self._cache = None

    # ---- polinomios ---------------------------------------------------------
    def num_den(self) -> tuple[np.ndarray, np.ndarray]:
        if self._cache is None:
            nC, dC = coeficientes(self.C)
            nG, dG = coeficientes(self.G)
            nH, dH = coeficientes(self.H)
            num = np.polymul(np.polymul(nC, nG), nH)
            den = np.polymul(np.polymul(dC, dG), dH)
            self._cache = (np.trim_zeros(num, "f") if np.any(num) else np.array([0.0]), np.trim_zeros(den, "f"))
        return self._cache

    @property
    def L(self) -> ct.TransferFunction:
        """Lazo abierto racional (sin retardo)."""
        n, d = self.num_den()
        return ct.tf(n, d)

    def evaluar_s(self, sv) -> np.ndarray:
        """L(s) (con retardo) en puntos complejos s."""
        n, d = self.num_den()
        sv = np.asarray(sv, dtype=complex)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            val = np.polyval(n, sv) / np.polyval(d, sv)
            if self.retardo:
                val = val * np.exp(-sv * self.retardo)
        return val

    def respuesta(self, w) -> np.ndarray:
        """L(jω)."""
        return self.evaluar_s(1j * np.asarray(w, dtype=float))

    def respuesta_H(self, w) -> np.ndarray:
        """H(jω) del sensor."""
        n, d = coeficientes(self.H)
        jw = 1j * np.asarray(w, dtype=float)
        return np.polyval(n, jw) / np.polyval(d, jw)

    # ---- raíces, tipo, constantes de error ---------------------------------
    def raices(self) -> tuple[float, np.ndarray, np.ndarray]:
        """(k, ceros, polos) de L(s), con los pares polo-cero iguales cancelados. k = coef. principal."""
        n, d = self.num_den()
        z = np.roots(n) if n.size > 1 else np.array([], dtype=complex)
        p = np.roots(d) if d.size > 1 else np.array([], dtype=complex)
        z, p = _cancelar(z, p)
        return float(n[0] / d[0]), z, p

    def tipo(self) -> int:
        _, z, p = self.raices()
        esc = max([1.0] + [abs(r) for r in np.r_[z, p]])
        return int(sum(_es_origen(r, esc) for r in p) - sum(_es_origen(r, esc) for r in z))

    def forma_bode(self) -> FormaBode:
        k, z, p = self.raices()
        esc = max([1.0] + [abs(r) for r in np.r_[z, p]])
        nz = int(sum(_es_origen(r, esc) for r in z))
        npo = int(sum(_es_origen(r, esc) for r in p))
        z = np.array([r for r in z if not _es_origen(r, esc)], dtype=complex)
        p = np.array([r for r in p if not _es_origen(r, esc)], dtype=complex)
        K_B = k * np.prod(-z).real / np.prod(-p).real
        fb = FormaBode(K_B=float(K_B), N=npo - nz, retardo=self.retardo)

        def clasificar(raices: np.ndarray, tipo: str):
            usados = np.zeros(raices.size, bool)
            for i, r in enumerate(raices):
                if usados[i]:
                    continue
                if abs(r.imag) <= 1e-7 * max(1.0, abs(r)):
                    fb.reales.append(dict(tipo=tipo, wb=abs(r.real), spd=r.real > 0))
                    usados[i] = True
                else:
                    # buscar el conjugado
                    j = next((j for j in range(raices.size) if not usados[j] and j != i and abs(raices[j] - np.conj(r)) < 1e-6 * max(1, abs(r))), None)
                    usados[i] = True
                    if j is not None:
                        usados[j] = True
                    wn = abs(r)
                    ze = -r.real / wn
                    fb.pares.append(dict(tipo=tipo, wn=float(wn), zeta=float(ze)))
        clasificar(z, "cero")
        clasificar(p, "polo")
        return fb

    def constantes_error(self) -> dict:
        """Kp, Kv, Ka (para realimentación unitaria; con sensor H ≠ 1 son las de L(s))."""
        fb = self.forma_bode()
        N, K = fb.N, fb.K_B
        inf = float("inf")
        return {
            "tipo": N,
            "Kp": K if N == 0 else (inf if N > 0 else 0.0),
            "Kv": 0.0 if N < 1 else (K if N == 1 else inf),
            "Ka": 0.0 if N < 2 else (K if N == 2 else inf),
        }

    # ---- lazo cerrado --------------------------------------------------------
    def _forward_y_pade(self, orden_pade: int = 8) -> tuple[ct.TransferFunction, ct.TransferFunction]:
        adelante = self.C * self.G
        if self.retardo > 0:
            n, d = ct.pade(self.retardo, orden_pade)
            adelante = adelante * ct.tf(n, d)
        return adelante, self.H

    def T(self, orden_pade: int = 8) -> ct.TransferFunction:
        """Lazo cerrado  C·G/(1 + C·G·H)  (retardo aproximado por Padé)."""
        adelante, H = self._forward_y_pade(orden_pade)
        return ct.feedback(adelante, H)

    def polinomio_caracteristico(self, orden_pade: int = 8) -> np.ndarray:
        """den(L) + num(L) (con Padé si hay retardo)."""
        n, d = self.num_den()
        if self.retardo > 0:
            pn, pd = ct.pade(self.retardo, orden_pade)
            n = np.polymul(n, pn)
            d = np.polymul(d, pd)
        return np.polyadd(d, n)

    def polos_lazo_cerrado(self, orden_pade: int = 8) -> np.ndarray:
        return np.roots(self.polinomio_caracteristico(orden_pade))

    # ---- derivados -----------------------------------------------------------
    def con_ganancia(self, kappa: float) -> "Sistema":
        """Mismo sistema con la planta multiplicada por `kappa`."""
        return Sistema(G=self.G * kappa, C=self.C, H=self.H, retardo=self.retardo, nombre=self.nombre)

    def con_compensador(self, Gc, nombre: str | None = None) -> "Sistema":
        """Sistema con el compensador adicional Gc en serie (se multiplica por el C existente)."""
        return Sistema(G=self.G, C=self.C * a_tf(Gc), H=self.H, retardo=self.retardo, nombre=nombre or self.nombre)


# ----------------------------------------------------------------------------
#  formato de funciones de transferencia
# ----------------------------------------------------------------------------
def _fmt(x: float, cifras: int = 5) -> str:
    return f"{x:.{cifras}g}"


def tf_a_texto(tf: ct.TransferFunction, forma: str = "polos_ceros", cifras: int = 4) -> str:
    """Texto legible. forma: 'polos_ceros' (K·Π(s-z)/Π(s-p)), 'bode' (constantes de tiempo) o 'polinomios'."""
    num, den = coeficientes(tf)
    if forma == "polinomios":
        def poli(c):
            gr = len(c) - 1
            tt = []
            for i, a in enumerate(c):
                if a == 0:
                    continue
                pot = gr - i
                t = _fmt(a, cifras) + (("·s" if pot == 1 else f"·s^{pot}") if pot else "")
                tt.append(t)
            return " + ".join(tt) if tt else "0"
        return f"({poli(num)}) / ({poli(den)})"
    s_ = Sistema(G=tf)
    k, z, p = s_.raices()
    if forma == "bode":
        return s_.forma_bode().texto()

    def factores(raices):
        out = []
        for r in sorted(raices, key=lambda x: (abs(x), x.imag)):
            if abs(r.imag) < 1e-9 * max(1, abs(r)):
                out.append("s" if abs(r.real) < 1e-12 else f"(s {'+' if -r.real >= 0 else '-'} {_fmt(abs(r.real), cifras)})")
            elif r.imag > 0:
                out.append(f"(s² {'+' if -2 * r.real >= 0 else '-'} {_fmt(abs(2 * r.real), cifras)}·s + {_fmt(abs(r) ** 2, cifras)})")
        return out
    nf, df = factores(z), factores(p)
    cab = _fmt(k, cifras)
    nt = cab + ("·" + "·".join(nf) if nf else "")
    return nt + (" / [" + "·".join(df) + "]" if df else "")
