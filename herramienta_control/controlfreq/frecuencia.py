"""Respuesta en frecuencia: Bode, márgenes (todos los cruces), Nyquist (conteo numérico),
Nichols (contornos M) y lazo cerrado en frecuencia (Mr, BW, sensibilidad).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from .sistema import Sistema, TOL_ORIGEN


# ----------------------------------------------------------------------------
#  rejilla de frecuencias y Bode
# ----------------------------------------------------------------------------
def rejilla(sis: Sistema, wmin: float | None = None, wmax: float | None = None, n: int = 4000,
            extra: tuple = ()) -> np.ndarray:
    """Frecuencias (rad/s) espaciadas en log que cubren todos los polos y ceros (± 2 décadas)."""
    _, z, p = sis.raices()
    cand = [abs(r) for r in np.r_[z, p] if abs(r) > 1e-9]
    cand += [float(e) for e in extra if e and e > 0]
    if sis.retardo > 0:
        cand.append(1.0 / sis.retardo)
    if not cand:
        cand = [1.0]
    lo = min(cand) / 100.0 if wmin is None else wmin
    hi = max(cand) * 100.0 if wmax is None else wmax
    if hi / lo < 1e3:
        c = np.sqrt(lo * hi)
        lo, hi = c / 40.0, c * 40.0
    return np.logspace(np.log10(lo), np.log10(hi), n)


def bode_datos(sis: Sistema, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(magnitud en dB, fase continua en grados). La fase parte de -90°·N (referencia de baja frecuencia)."""
    Lw = sis.respuesta(w)
    mag = 20.0 * np.log10(np.abs(Lw))
    fase = np.degrees(np.unwrap(np.angle(Lw)))
    ref = sis.forma_bode().fase_baja_frecuencia
    k = np.round((ref - fase[0]) / 360.0) * 360.0
    return mag, fase + k


# ----------------------------------------------------------------------------
#  márgenes
# ----------------------------------------------------------------------------
def _envolver_180(deg: float) -> float:
    """Lleva un ángulo a [-180, 180)."""
    return float((deg + 180.0) % 360.0 - 180.0)


@dataclass
class Margenes:
    cruces_ganancia: list = field(default_factory=list)   # [(w, MF_deg)]
    cruces_fase: list = field(default_factory=list)       # [(w, MG_veces, MG_dB)]
    wc: float | None = None
    MF: float | None = None
    w180: float | None = None
    MG_veces: float | None = None
    MG_dB: float | None = None
    margen_retardo: float | None = None                   # segundos

    @property
    def tiene_mg(self) -> bool:
        return self.MG_veces is not None


def _raiz(f, a: float, b: float) -> float | None:
    try:
        return brentq(f, a, b, xtol=1e-14, rtol=1e-12, maxiter=200)
    except (ValueError, RuntimeError):
        return None


def margenes(sis: Sistema, w: np.ndarray | None = None) -> Margenes:
    """Cruces de ganancia (|L|=1) y de fase (L sobre el eje real negativo), con sus márgenes.

    MF = 180° + ∠L(jωc) llevado a (-180°, 180°]  |  MG = 1/|L(jω180)|.
    Se informan TODOS los cruces; los valores principales son los de menor |margen|.
    """
    if w is None:
        w = rejilla(sis, n=6000)
    L = sis.respuesta(w)
    ok = np.isfinite(L) & (np.abs(L) < 1e14) & (np.abs(L) > 1e-14)
    m = Margenes()

    # --- cruces de ganancia
    lg = np.log10(np.where(ok, np.abs(L), np.nan))
    f_g = lambda x: np.log10(abs(sis.respuesta(x)))
    for i in np.where(ok[:-1] & ok[1:] & (lg[:-1] * lg[1:] < 0))[0]:
        wc = _raiz(f_g, w[i], w[i + 1])
        if wc is None:
            continue
        ang = np.degrees(np.angle(sis.respuesta(wc)))
        m.cruces_ganancia.append((wc, _envolver_180(180.0 + ang)))

    # --- cruces de fase (eje real negativo)
    im, re = L.imag, L.real
    f_p = lambda x: sis.respuesta(x).imag
    for i in np.where(ok[:-1] & ok[1:] & (im[:-1] * im[1:] < 0) & (re[:-1] + re[1:] < 0))[0]:
        w180 = _raiz(f_p, w[i], w[i + 1])
        if w180 is None:
            continue
        Lc = sis.respuesta(w180)
        if Lc.real >= 0 or abs(Lc.imag) > 1e-6 * abs(Lc):   # falso cruce (polo sobre el eje, etc.)
            continue
        mg = 1.0 / abs(Lc)
        m.cruces_fase.append((w180, mg, 20.0 * np.log10(mg)))

    # --- principales
    if m.cruces_ganancia:
        wc, mf = min(m.cruces_ganancia, key=lambda t: abs(t[1]))
        m.wc, m.MF = wc, mf
        pos = [np.radians(mf_) / w_ for w_, mf_ in m.cruces_ganancia if mf_ > 0]
        m.margen_retardo = min(pos) if pos else None
    if m.cruces_fase:
        w180, mg, mgdb = min(m.cruces_fase, key=lambda t: abs(t[2]))
        m.w180, m.MG_veces, m.MG_dB = w180, mg, mgdb
    return m


# ----------------------------------------------------------------------------
#  Nyquist: conteo numérico de rodeos  (Z = N + P)
# ----------------------------------------------------------------------------
@dataclass
class ConteoNyquist:
    P: int                       # polos de L en el semiplano derecho
    N: int                       # rodeos (horario +) de L(jω) al punto -1
    Z: int                       # polos de lazo cerrado en el SPD según Nyquist (= N + P)
    Z_real: int | None           # idem, contando raíces del polinomio característico
    marginal: bool               # hay raíces de lazo cerrado sobre el eje imaginario
    polos_eje: list              # polos de L sobre el eje imaginario (rad/s, 0 = origen)
    residuo: float               # |N_bruto - N|: cerca de 0 si el conteo es confiable
    s_contorno: np.ndarray | None = None
    L_contorno: np.ndarray | None = None

    @property
    def coincide(self) -> bool | None:
        return None if self.Z_real is None else self.Z == self.Z_real


def _tol_eje(escala: float) -> float:
    return 1e-7 * max(1.0, escala)


def _tramo(lo: float, hi: float, n: int) -> np.ndarray:
    """Puntos en [lo, hi], densos en ambos extremos y con cobertura logarítmica."""
    d = hi - lo
    if d <= 0:
        return np.array([])
    dist = np.logspace(np.log10(max(d * 1e-7, 1e-14)), np.log10(d), max(n // 2, 8))
    pts = np.r_[lo + dist, hi - dist[::-1]]
    if lo > 0:
        pts = np.r_[pts, np.geomspace(lo, hi, max(n // 2, 8))]
    return np.unique(np.clip(pts, lo, hi))


def nyquist_conteo(sis: Sistema, orden_pade: int = 8, n_pts: int = 4000, guardar_contorno: bool = True) -> ConteoNyquist:
    """Aplica el criterio de Nyquist de forma numérica sobre el contorno completo
    (eje imaginario, con indentaciones hacia la derecha alrededor de los polos que están sobre el eje).

    N = rodeos horarios de L al punto -1 (= giros de 1+L alrededor de 0), P = polos de L en el SPD,
    Z = N + P = polos de lazo cerrado en el SPD.
    """
    k, z, p = sis.raices()
    esc = max([1.0] + [abs(r) for r in np.r_[z, p]])
    tol = _tol_eje(esc)
    P = int(sum(r.real > tol for r in p))
    eje_pos = sorted(r.imag for r in p if abs(r.real) <= tol and r.imag > tol)
    origen = any(abs(r) <= tol for r in p)
    polos_eje = ([0.0] if origen else []) + eje_pos

    cand = [abs(r) for r in np.r_[z, p] if abs(r) > tol] or [1.0]
    eps = 1e-4 * min(cand)                       # radio de las indentaciones
    wlo = min(cand) / 1e3 if not origen else eps
    whi = max(cand) * 1e3
    if sis.retardo:
        whi = max(whi, 1e3 / sis.retardo)

    # --- mitad positiva del contorno: tramos sobre el eje y arcos alrededor de los polos en el eje
    estaciones = [0.0] + eje_pos
    partes = []
    for idx, a in enumerate(estaciones):
        b = estaciones[idx + 1] if idx + 1 < len(estaciones) else np.inf
        lo = (eps if origen else wlo) if a == 0.0 else a + eps
        hi = whi if np.isinf(b) else b - eps
        partes.append(1j * _tramo(lo, hi, n_pts))
        if not np.isinf(b):
            th = np.linspace(-np.pi / 2, np.pi / 2, 400)
            partes.append(1j * b + eps * np.exp(1j * th))
    s_pos = np.concatenate(partes)
    s_neg = np.conj(s_pos[::-1])
    if origen:
        th = np.linspace(-np.pi / 2, np.pi / 2, 400)
        s_total = np.concatenate([s_neg, eps * np.exp(1j * th), s_pos])
    else:
        s_total = np.concatenate([s_neg, s_pos])

    L_tot = sis.evaluar_s(s_total)
    F = 1.0 + L_tot
    buenos = np.isfinite(F) & (np.abs(F) > 0)
    s_total, L_tot, F = s_total[buenos], L_tot[buenos], F[buenos]
    bruto = -np.angle(F[1:] / F[:-1]).sum() / (2 * np.pi)
    N = int(round(bruto))

    pc = sis.polos_lazo_cerrado(orden_pade)
    z_real = int(sum(r.real > max(tol, 1e-9 * max(1.0, abs(r))) for r in pc))
    marginal = any(abs(r.real) <= 1e-7 * max(1.0, abs(r)) for r in pc)
    return ConteoNyquist(P=P, N=N, Z=N + P, Z_real=z_real, marginal=marginal, polos_eje=polos_eje,
                         residuo=abs(bruto - N),
                         s_contorno=s_total if guardar_contorno else None,
                         L_contorno=L_tot if guardar_contorno else None)


# ----------------------------------------------------------------------------
#  Nichols
# ----------------------------------------------------------------------------
def nichols_datos(sis: Sistema, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(fase en grados, magnitud en dB) de L(jω), con fase continua."""
    mag, fase = bode_datos(sis, w)
    return fase, mag


def contornos_M(niveles_dB=(-12, -6, -3, -1, 0, 1, 3, 6, 12), n: int = 1200) -> dict[float, list[tuple[np.ndarray, np.ndarray]]]:
    """Contornos de |T| = M constante en el plano (fase, magnitud en dB) de la carta de Nichols.

    En el plano de L el lugar |T|=M es una circunferencia de centro -M²/(M²-1) y radio M/|M²-1|
    (M=1: la recta Re L = -1/2). Devuelve {nivel_dB: [(fase_deg, mag_dB), ...]} (varios tramos si hace falta).
    """
    out: dict[float, list] = {}
    for nd in niveles_dB:
        M = 10 ** (nd / 20.0)
        if abs(M - 1.0) < 1e-9:
            y = np.linspace(-200, 200, 6000)
            Lc = -0.5 + 1j * y
        else:
            c = -M**2 / (M**2 - 1.0)
            r = M / abs(M**2 - 1.0)
            th = np.linspace(0, 2 * np.pi, n, endpoint=False)
            Lc = c + r * np.exp(1j * th)
            Lc = np.r_[Lc, Lc[:1]]
        mag = 20.0 * np.log10(np.abs(Lc))
        fase = np.degrees(np.angle(Lc))
        fase = np.where(fase > 0, fase - 360.0, fase)          # (-360, 0]
        # cortar en los saltos de fase
        tramos, ini = [], 0
        for i in range(1, len(fase)):
            if abs(fase[i] - fase[i - 1]) > 180.0:
                tramos.append((fase[ini:i], mag[ini:i]))
                ini = i
        tramos.append((fase[ini:], mag[ini:]))
        out[float(nd)] = [(f, g) for f, g in tramos if len(f) > 1]
    return out


# ----------------------------------------------------------------------------
#  lazo cerrado en frecuencia
# ----------------------------------------------------------------------------
@dataclass
class CerradoFrecuencia:
    w: np.ndarray
    T: np.ndarray          # T(jω)
    S: np.ndarray          # S(jω) = 1/(1+L)
    Mr: float              # pico de |T| (veces)
    Mr_dB: float
    wr: float
    BW: float | None       # ancho de banda a -3 dB respecto de |T(0)|
    T0: float              # |T| en la frecuencia más baja de la rejilla (≈ |T(0)|)
    Ms: float
    Ms_dB: float
    wMs: float


def cerrado_frecuencia(sis: Sistema, w: np.ndarray | None = None) -> CerradoFrecuencia:
    if w is None:
        w = rejilla(sis, n=8000)
    L = sis.respuesta(w)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        T = (L / sis.respuesta_H(w)) / (1.0 + L)       # T = C·G/(1 + L)
        S = 1.0 / (1.0 + L)
    aT = np.abs(T)
    ok = np.isfinite(aT)
    i = int(np.nanargmax(np.where(ok, aT, -np.inf)))
    T0 = float(aT[0])
    bw = None
    umbral = T0 / np.sqrt(2.0)
    idx = np.where(ok[:-1] & ok[1:] & (aT[:-1] > umbral) & (aT[1:] <= umbral))[0]
    if idx.size:
        j = idx[0]
        # interpolación lineal en log(w)
        x0, x1 = np.log10(w[j]), np.log10(w[j + 1])
        y0, y1 = aT[j], aT[j + 1]
        bw = float(10 ** (x0 + (umbral - y0) * (x1 - x0) / (y1 - y0)))
    aS = np.abs(S)
    jS = int(np.nanargmax(np.where(np.isfinite(aS), aS, -np.inf)))
    return CerradoFrecuencia(w=w, T=T, S=S, Mr=float(aT[i]), Mr_dB=float(20 * np.log10(aT[i])), wr=float(w[i]),
                             BW=bw, T0=T0, Ms=float(aS[jS]), Ms_dB=float(20 * np.log10(aS[jS])), wMs=float(w[jS]))


# ----------------------------------------------------------------------------
#  relaciones con la respuesta temporal (segundo orden)
# ----------------------------------------------------------------------------
def zeta_desde_Mr(Mr: float) -> float | None:
    """ζ tal que Mr = 1/(2ζ√(1-ζ²)), con ζ < 0,707. None si Mr <= 1 (sin pico)."""
    if Mr <= 1.0 + 1e-9:
        return None
    x = (1.0 - np.sqrt(max(1.0 - 1.0 / Mr**2, 0.0))) / 2.0
    return float(np.sqrt(x))


def Mp_desde_zeta(z: float) -> float:
    """Sobreimpulso (%) de un segundo orden estándar."""
    if z >= 1.0:
        return 0.0
    return float(100.0 * np.exp(-np.pi * z / np.sqrt(1.0 - z**2)))


def MF_desde_zeta(z: float) -> float:
    """MF exacto (°) del lazo L = wn²/(s(s+2ζwn))."""
    return float(np.degrees(np.arctan(2.0 * z / np.sqrt(np.sqrt(1.0 + 4.0 * z**4) - 2.0 * z**2))))


def zeta_desde_MF(mf: float) -> float | None:
    """Inversa exacta de MF_desde_zeta (MF en grados)."""
    if mf <= 0 or mf >= MF_desde_zeta(1.0):
        return None if mf <= 0 else 1.0
    return float(brentq(lambda z: MF_desde_zeta(z) - mf, 1e-6, 1.0))
