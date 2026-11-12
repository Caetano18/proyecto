"""Posproceso del modelo FEA: lectura de CalculiX, recuperacion de tensiones y
respuesta dinamica por superposicion modal con correccion estatica.

Ecuacion en coordenadas relativas a la base (aceleracion de base a_b(t) en la direccion d):
    q_i'' + 2 zeta w_i q_i' + w_i^2 q_i = -Gamma_i,d a_b(t)
    u(t) = u_est,d a_b(t) + sum_i phi_i [ q_i(t) - q_i,est(t) ],   q_i,est = -Gamma_i,d a_b / w_i^2
(metodo de aceleracion modal: los modos truncados entran con su respuesta estatica).
Unidades: mm, N, s, tonelada.  Tensiones en MPa.
"""
import os, re, json
import numpy as np
import params as P

G_MM = P.G0 * 1000.0

# ---------------------------------------------------------------- lectura


def leer_frd_U(path, nn):
    """Devuelve la lista de campos de desplazamiento [nn,3] del archivo .frd (ASCII)."""
    data = open(path, "rb").read()
    out = []
    pos = 0
    while True:
        k = data.find(b" -4  DISP", pos)
        if k < 0:
            break
        a = data.find(b"\n -1", k) + 1
        b = data.find(b"\n -3", a)
        blk = data[a:b + 1]
        ll = blk.find(b"\n") + 1
        n = len(blk) // ll
        arr = np.frombuffer(blk[:n * ll], dtype=np.uint8).reshape(n, ll)
        ids = arr[:, 3:13].copy().view("S10").astype(np.int64).ravel() - 1
        vals = np.ascontiguousarray(arr[:, 13:49]).view("S12").astype(np.float64).reshape(n, 3)
        U = np.zeros((nn, 3))
        U[ids] = vals
        out.append(U)
        pos = b
    return out


def leer_dat_S(path):
    """Tensiones en puntos de integracion impresas por CalculiX (*EL PRINT, S).
    Devuelve (elementos [n], S [nbloques, n, 4, 6]) con Voigt (xx, yy, zz, xy, yz, zx), en MPa."""
    data = open(path, "rb").read()
    bloques, elems = [], None
    pos = 0
    while True:
        k = data.find(b"stresses (elem", pos)
        if k < 0:
            break
        a = data.find(b"\n", k) + 1
        while data[a:a + 1] in (b"\n", b"\r"):
            a += 1
        ll = data.find(b"\n", a) - a + 1
        b = data.find(b"\n\n", a)
        if b < 0:
            b = len(data) - 1
        blk = data[a:b + 1]
        n = len(blk) // ll
        arr = np.frombuffer(blk[:n * ll], dtype=np.uint8).reshape(n, ll)
        el = np.ascontiguousarray(arr[:, 0:10]).view("S10").astype(np.int64).ravel() - 1
        ip = np.ascontiguousarray(arr[:, 10:14]).view("S4").astype(np.int64).ravel() - 1
        v = np.ascontiguousarray(arr[:, 14:98]).view("S14").astype(np.float64).reshape(n, 6)
        if elems is None:
            elems = np.unique(el)
            fila = -np.ones(int(elems.max()) + 1, dtype=np.int64)
            fila[elems] = np.arange(len(elems))
        S = np.zeros((len(elems), 4, 6), dtype=np.float32)
        S[fila[el], ip] = v[:, [0, 1, 2, 3, 5, 4]]          # CalculiX: xx,yy,zz,xy,xz,yz
        bloques.append(S)
        pos = b
    return elems, np.array(bloques)


def leer_dat_modal(path):
    """Frecuencias [Hz], factores de participacion [nm,6] y masas efectivas [nm,6] (t)."""
    txt = open(path).read()

    def tabla(titulo, ncol):
        k = txt.find(titulo)
        rows = []
        for line in txt[k:].split("\n")[1:]:
            s = line.split()
            if len(s) == ncol and s[0].isdigit():
                rows.append([float(x) for x in s[1:]])
            elif rows and not line.strip():
                break
            elif rows and len(s) != ncol:
                break
        return np.array(rows)
    ev = tabla("E I G E N V A L U E   O U T P U T", 5 if "IMAGINARY" not in txt[:4000] else 5)
    if ev.size == 0:
        ev = tabla("E I G E N V A L U E   O U T P U T", 4)
    pf = tabla("P A R T I C I P A T I O N   F A C T O R S", 7)
    em = tabla("E F F E C T I V E   M O D A L   M A S S", 7)
    m = re.search(r"T O T A L   E F F E C T I V E   M A S S.*?\n(.*?)\n\s*\n", txt, re.S)
    freq = ev[:, 2]          # columna: frecuencia en ciclos/tiempo
    return freq, pf, em


# ---------------------------------------------------- elemento tetraedro 10

_a, _b = 0.5854101966249685, 0.1381966011250105
GP = np.array([[_a, _b, _b, _b], [_b, _a, _b, _b], [_b, _b, _a, _b], [_b, _b, _b, _a]])
CENTRO = np.array([[0.25, 0.25, 0.25, 0.25]])


def _dN_dL(L):
    """Derivadas de las 10 funciones de forma respecto de L1..L4 (orden de nodos Abaqus)."""
    L1, L2, L3, L4 = L
    d = np.zeros((10, 4))
    d[0, 0] = 4 * L1 - 1
    d[1, 1] = 4 * L2 - 1
    d[2, 2] = 4 * L3 - 1
    d[3, 3] = 4 * L4 - 1
    d[4] = [4 * L2, 4 * L1, 0, 0]
    d[5] = [0, 4 * L3, 4 * L2, 0]
    d[6] = [4 * L3, 0, 4 * L1, 0]
    d[7] = [4 * L4, 0, 0, 4 * L1]
    d[8] = [0, 4 * L4, 0, 4 * L2]
    d[9] = [0, 0, 4 * L4, 4 * L3]
    return d


def gradientes(xyz, els, pts=GP):
    """dN/dx [E, npt, 10, 3] y volumen de cada elemento."""
    X = xyz[els]                                   # [E,10,3]
    out = np.zeros((len(els), len(pts), 10, 3))
    vol = np.zeros(len(els))
    for g, L in enumerate(pts):
        dL = _dN_dL(L)
        dxi = dL[:, :3] - dL[:, 3:4]               # [10,3]
        J = np.einsum("eia,ik->eak", X, dxi)       # dx_a / dxi_k
        Ji = np.linalg.inv(J)
        out[:, g] = np.einsum("ik,eka->eia", dxi, Ji)
        vol += np.abs(np.linalg.det(J)) / 6.0 / len(pts)
    return out, vol


def matriz_D(tipo, c):
    """Matriz elastica 6x6 (Voigt xx,yy,zz,xy,yz,zx; distorsiones ingenieriles) en ejes globales."""
    if tipo == "iso":
        E, nu = c["E"], c["nu"]
        lam = E * nu / ((1 + nu) * (1 - 2 * nu))
        mu = E / (2 * (1 + nu))
        D = np.zeros((6, 6))
        D[:3, :3] = lam
        D[np.arange(3), np.arange(3)] += 2 * mu
        D[3, 3] = D[4, 4] = D[5, 5] = mu
        return D
    S = np.zeros((6, 6))
    E1, E2, E3 = c["E1"], c["E2"], c["E3"]
    S[0, 0], S[1, 1], S[2, 2] = 1 / E1, 1 / E2, 1 / E3
    S[0, 1] = S[1, 0] = -c["nu12"] / E1
    S[0, 2] = S[2, 0] = -c["nu13"] / E1
    S[1, 2] = S[2, 1] = -c["nu23"] / E2
    S[3, 3], S[4, 4], S[5, 5] = 1 / c["G12"], 1 / c["G23"], 1 / c["G13"]
    return np.linalg.inv(S)


def tensiones(U, els, dNdx, Dall, epart):
    """Tensiones [E, npt, 6] (MPa) de un campo de desplazamientos [nn,3]."""
    ue = U[els]                                            # [E,10,3]
    H = np.einsum("eib,egia->egba", ue, dNdx)              # du_b/dx_a
    eps = np.empty(H.shape[:2] + (6,))
    eps[..., 0] = H[..., 0, 0]
    eps[..., 1] = H[..., 1, 1]
    eps[..., 2] = H[..., 2, 2]
    eps[..., 3] = H[..., 0, 1] + H[..., 1, 0]
    eps[..., 4] = H[..., 1, 2] + H[..., 2, 1]
    eps[..., 5] = H[..., 2, 0] + H[..., 0, 2]
    return np.einsum("eij,egj->egi", Dall[epart], eps)


def von_mises(s):
    sx, sy, sz, txy, tyz, tzx = (s[..., k] for k in range(6))
    return np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy ** 2 + tyz ** 2 + tzx ** 2))


# ------------------------------------------------------- respuesta modal


def q_armonico(freq_n, gam, f, A, zeta):
    """Coordenadas modales complejas y su parte casi-estatica para aceleracion de base A (mm/s2)."""
    wn = 2 * np.pi * freq_n
    w = 2 * np.pi * f
    q = -gam * A / (wn ** 2 - w ** 2 + 2j * zeta * wn * w)
    qst = -gam * A / wn ** 2
    return q, qst


def semiseno(t, A, tau):
    return np.where((t >= 0) & (t <= tau), A * np.sin(np.pi * t / tau), 0.0)


def q_transitorio(freq_n, gam, t, ab, zeta):
    """Integra cada modo con el metodo exacto para excitacion lineal a tramos (Nigam-Jennings)."""
    wn = 2 * np.pi * freq_n
    wd = wn * np.sqrt(1 - zeta ** 2)
    dt = t[1] - t[0]
    e = np.exp(-zeta * wn * dt)
    s, c = np.sin(wd * dt), np.cos(wd * dt)
    k = wn ** 2
    A11 = e * (c + zeta * wn / wd * s)
    A12 = e * s / wd
    A21 = -e * wn ** 2 / wd * s
    A22 = e * (c - zeta * wn / wd * s)
    t1 = (2 * zeta ** 2 - 1) / (wn ** 2 * dt)
    t2 = 2 * zeta / (wn ** 3 * dt)
    B11 = e * ((t1 + zeta / wn) * s / wd + (t2 + 1 / wn ** 2) * c) - t2
    B12 = -e * (t1 * s / wd + t2 * c) - 1 / wn ** 2 + t2
    B21 = e * ((t1 + zeta / wn) * (c - zeta * wn / wd * s) - (t2 + 1 / wn ** 2) * (wd * s + zeta * wn * c)) + 1 / (wn ** 2 * dt)
    B22 = -e * (t1 * (c - zeta * wn / wd * s) - t2 * (wd * s + zeta * wn * c)) - 1 / (wn ** 2 * dt)
    nm = len(wn)
    q = np.zeros((len(t), nm))
    v = np.zeros(nm)
    x = np.zeros(nm)
    p = -np.outer(ab, gam)                    # fuerza modal por unidad de masa generalizada
    for i in range(len(t) - 1):
        xn = A11 * x + A12 * v + B11 * p[i] + B12 * p[i + 1]
        v = A21 * x + A22 * v + B21 * p[i] + B22 * p[i + 1]
        x = xn
        q[i + 1] = x
    qst = p / wn ** 2
    return q, qst


def srs_semiseno(fn, A, tau, zeta, n=4000):
    """Espectro de respuesta al choque (aceleracion absoluta maxima) de un semiseno."""
    out = np.zeros(len(fn))
    for k, f in enumerate(fn):
        T = max(tau * 4, 3.0 / f + tau)
        t = np.linspace(0, T, n)
        ab = semiseno(t, A, tau)
        q, _ = q_transitorio(np.array([f]), np.array([1.0]), t, ab, zeta)
        wn = 2 * np.pi * f
        v = np.gradient(q[:, 0], t)
        aabs = -(2 * zeta * wn * v + wn ** 2 * q[:, 0])
        out[k] = np.max(np.abs(aabs))
    return out


# ------------------------------------------------------------- modelo


def nodos_anomalos(phi, els, umbral=0.02):
    """Nodos medios cuyo desplazamiento modal no acompana al de los vertices de su arista (artefacto numerico
    del autovector: nodo medio fuera de equilibrio).  Devuelve los indices de nodo."""
    pares = [(0, 1, 4), (1, 2, 5), (2, 0, 6), (0, 3, 7), (1, 3, 8), (2, 3, 9)]
    malos = set()
    for u in phi:
        amp = np.linalg.norm(u, axis=1).max()
        for a, b, m in pares:
            dev = np.linalg.norm(u[els[:, m]] - 0.5 * (u[els[:, a]] + u[els[:, b]]), axis=1)
            dif = np.linalg.norm(u[els[:, a]] - u[els[:, b]], axis=1)
            bad = (dev > umbral * amp) & (dev > 0.45 * dif)
            if bad.any():
                malos |= set(els[bad][:, m].tolist())
    return np.array(sorted(malos), dtype=np.int64)


def energia_elastomero(S, vol, c, ejes=None):
    """Energia de deformacion [N.mm] de elementos de elastomero ortotropo (nu = 0).  S: [E, 4, 6] global."""
    T = np.zeros(S.shape[:2] + (3, 3))
    T[..., 0, 0], T[..., 1, 1], T[..., 2, 2] = S[..., 0], S[..., 1], S[..., 2]
    T[..., 0, 1] = T[..., 1, 0] = S[..., 3]
    T[..., 1, 2] = T[..., 2, 1] = S[..., 4]
    T[..., 0, 2] = T[..., 2, 0] = S[..., 5]
    if ejes is not None:
        Rm = np.array(ejes).T                       # columnas = ejes locales en coordenadas globales
        T = np.einsum("ia,egij,jb->egab", Rm, T, Rm)
    u = 0.5 * (T[..., 0, 0] ** 2 / c["E1"] + T[..., 1, 1] ** 2 / c["E2"] + T[..., 2, 2] ** 2 / c["E3"]
               + T[..., 0, 1] ** 2 / c["G12"] + T[..., 1, 2] ** 2 / c["G23"] + T[..., 0, 2] ** 2 / c["G13"])
    return float(np.sum(u * vol[:, None] / 4.0))


class Modelo:
    """Resultados de CalculiX: modos (U y tensiones en puntos de Gauss) y casos estaticos."""

    def __init__(self, wd, tag):
        z = np.load(os.path.join(wd, f"malla_{tag}.npz"))
        self.xyz, self.els, self.epart = z["xyz"], z["els"], z["epart"]
        self.partes = json.load(open(os.path.join(wd, f"partes_{tag}.json")))
        nn = len(self.xyz)
        self.freq, self.pf, self.em = leer_dat_modal(os.path.join(wd, f"modal_{tag}.dat"))
        self.phi = np.array(leer_frd_U(os.path.join(wd, f"modal_{tag}.frd"), nn), dtype=np.float32)
        self.ever, self.s_phi = leer_dat_S(os.path.join(wd, f"modal_{tag}.dat"))
        nm = min(len(self.freq), len(self.phi), len(self.s_phi))
        self.freq, self.pf, self.em = self.freq[:nm], self.pf[:nm], self.em[:nm]
        self.phi, self.s_phi = self.phi[:nm], self.s_phi[:nm]
        self.ust = np.array(leer_frd_U(os.path.join(wd, f"estat_{tag}.frd"), nn)) / G_MM      # por unidad de a_b
        ev2, sst = leer_dat_S(os.path.join(wd, f"estat_{tag}.dat"))
        assert np.array_equal(ev2, self.ever)
        self.s_st = sst / G_MM
        self.upar = leer_frd_U(os.path.join(wd, f"parac_{tag}.frd"), nn)[0] / G_MM
        ev3, spar = leer_dat_S(os.path.join(wd, f"parac_{tag}.dat"))
        assert np.array_equal(ev3, self.ever)
        self.s_par = spar[0] / G_MM
        self.fila = -np.ones(len(self.els), dtype=np.int64)
        self.fila[self.ever] = np.arange(len(self.ever))
        self.masa = sum(p["masa"] for p in self.partes)
        libre = os.path.join(wd, f"libre_{tag}.dat")
        self.freq_libre = leer_dat_modal(libre)[0] if os.path.exists(libre) and os.path.getsize(libre) > 0 else None
        # --- filtro de nodos medios no equilibrados (se excluyen sus elementos de la verificacion)
        es_elast = np.array([p["mat"] in ("PAD_A", "PAD_B", "ELAST_X") for p in self.partes])
        rig = ~es_elast[self.epart]
        self.anom = nodos_anomalos(self.phi, self.els[rig])
        marca = np.zeros(nn, bool)
        marca[self.anom] = True
        self.valido = ~marca[self.els[self.ever]].any(axis=1)
        self.s_phi[:, ~self.valido] = 0.0
        # --- amortiguamiento modal por energia de deformacion en los elastomeros
        import fe_model as F
        import params as P
        self.vol_ever = gradientes(self.xyz, self.els[self.ever], CENTRO)[1]
        wn2 = (2 * np.pi * self.freq) ** 2
        U_el = np.zeros(nm)
        for i, p in enumerate(self.partes):
            if not es_elast[i]:
                continue
            filas = self.fila[np.where(self.epart == i)[0]]
            filas = filas[filas >= 0]
            _, c = F.elastico(p["mat"])
            ejes = None
            if p["mat"] == "PAD_A":
                ejes = [(0.0, 0.70710678, 0.70710678), (0.0, -0.70710678, 0.70710678), (1.0, 0.0, 0.0)]
            elif p["mat"] == "PAD_B":
                ejes = [(0.0, -0.70710678, 0.70710678), (0.0, -0.70710678, -0.70710678), (1.0, 0.0, 0.0)]
            for k in range(nm):
                U_el[k] += energia_elastomero(self.s_phi[k][filas].astype(np.float64), self.vol_ever[filas], c, ejes)
        self.f_elast = np.clip(U_el / (0.5 * wn2), 0.0, 1.0)
        eta = P.MAT["ELAST"]["eta"]
        self.zeta = P.ZETA * (1 - self.f_elast) + 0.5 * eta * self.f_elast

    def filas(self, pred):
        """Filas (en los arreglos de tension) de los elementos de las piezas que cumplen pred."""
        ok = np.array([pred(p) for p in self.partes])
        f = self.fila[np.where(ok[self.epart])[0]]
        return f[f >= 0]

    def S(self, comb_modal, comb_est):
        """Tensiones [Ev, 4, 6] para u = sum comb_est[d] u_est[d] + sum comb_modal[i] phi[i]."""
        return (np.tensordot(np.asarray(comb_est, np.float32), self.s_st, axes=1)
                + np.tensordot(np.asarray(comb_modal, np.float32), self.s_phi, axes=1))

    def U(self, comb_modal, comb_est):
        return np.tensordot(comb_est, self.ust, axes=1) + np.tensordot(comb_modal, self.phi, axes=1)
