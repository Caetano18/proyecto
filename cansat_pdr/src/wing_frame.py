"""Ala desplegada: modelo de portico 3D (vigas de Euler-Bernoulli, 6 GDL por nodo).

Barras: varilla de borde de ataque A-J-T (tubo d5/3,5 con manguito en J) y tirante de borde
de fuga B-T (tubo d3/2).  A y B son horquillas con perno vertical: giro libre alrededor de z,
el resto restringido.  En T un perno vertical une las dos barras (giro z relativo libre).
Cargas de la tela: modelo de tiras de la nota de membrana del equipo.
"""
import json, math, sys
import numpy as np
from scipy.linalg import eigh
import params as P
import fe_post as post

E_CF, G_CF, RHO_CF = P.MAT["CFRP"]["E"], P.MAT["CFRP"]["G12"], P.MAT["CFRP"]["rho"] * 1e-9
E_AL, RHO_AL = P.MAT["AL7075"]["E"], P.MAT["AL7075"]["rho"] * 1e-9


def tubo(do, di, E=E_CF, G=G_CF, rho=RHO_CF):
    A = math.pi * (do ** 2 - di ** 2) / 4
    I = math.pi * (do ** 4 - di ** 4) / 64
    return dict(A=A, I=I, J=2 * I, E=E, G=G, rho=rho, c=do / 2)


SEC_LE = tubo(P.LE_DO, P.LE_DI)
SEC_TE = tubo(P.TE_DO, P.TE_DI)
SEC_SLV = tubo(P.SLV_DO, P.SLV_DI, E=E_AL, G=E_AL / 2.66, rho=RHO_AL)


def k_m_elem(x0, x1, sec, m_extra=0.0):
    """Rigidez y masa consistente (12x12, ejes globales) de una barra de seccion circular."""
    d = x1 - x0
    L = np.linalg.norm(d)
    ex = d / L
    ref = np.array([0, 0, 1.0]) if abs(ex[2]) < 0.9 else np.array([1.0, 0, 0])
    ey = np.cross(ref, ex)
    ey /= np.linalg.norm(ey)
    ez = np.cross(ex, ey)
    R = np.vstack([ex, ey, ez])
    T = np.zeros((12, 12))
    for k in range(4):
        T[3 * k:3 * k + 3, 3 * k:3 * k + 3] = R
    E, G, A, I, J = sec["E"], sec["G"], sec["A"], sec["I"], sec["J"]
    k = np.zeros((12, 12))
    a = E * A / L
    k[0, 0] = k[6, 6] = a
    k[0, 6] = k[6, 0] = -a
    t = G * J / L
    k[3, 3] = k[9, 9] = t
    k[3, 9] = k[9, 3] = -t
    b = E * I / L ** 3
    for (u1, r1, u2, r2, s) in ((1, 5, 7, 11, 1.0), (2, 4, 8, 10, -1.0)):
        kb = b * np.array([[12, 6 * L * s, -12, 6 * L * s],
                           [6 * L * s, 4 * L * L, -6 * L * s, 2 * L * L],
                           [-12, -6 * L * s, 12, -6 * L * s],
                           [6 * L * s, 2 * L * L, -6 * L * s, 4 * L * L]])
        ix = [u1, r1, u2, r2]
        k[np.ix_(ix, ix)] += kb
    ml = sec["rho"] * A * L + m_extra
    m = np.zeros((12, 12))
    m[0, 0] = m[6, 6] = ml / 3
    m[0, 6] = m[6, 0] = ml / 6
    ip = ml * J / A
    m[3, 3] = m[9, 9] = ip / 3
    m[3, 9] = m[9, 3] = ip / 6
    for (u1, r1, u2, r2, s) in ((1, 5, 7, 11, 1.0), (2, 4, 8, 10, -1.0)):
        mb = ml / 420 * np.array([[156, 22 * L * s, 54, -13 * L * s],
                                  [22 * L * s, 4 * L * L, 13 * L * s, -3 * L * L],
                                  [54, 13 * L * s, 156, -22 * L * s],
                                  [-13 * L * s, -3 * L * L, -22 * L * s, 4 * L * L]])
        ix = [u1, r1, u2, r2]
        m[np.ix_(ix, ix)] += mb
    return T.T @ k @ T, T.T @ m @ T, T, k


class Ala:
    def __init__(self, c=P.D_AB, n_le=56, n_te=28, con_tirante=True, punta_libre=False):
        """c: cuerda de raiz (A-B).  punta_libre: sin tirante fuera del plano (hipotesis de la nota)."""
        self.c = c
        L = c * math.sqrt(2)
        self.L = L
        A, B, T = np.array([0, 0, 0.0]), np.array([c, 0, 0.0]), np.array([c, c, 0.0])
        self.s_le = np.linspace(0, L, n_le + 1)
        self.x_le = A + np.outer(self.s_le / L, T - A)
        self.s_te = np.linspace(0, c, n_te + 1)
        self.x_te = B + np.outer(self.s_te / c, T - B)
        self.xyz = np.vstack([self.x_le, self.x_te])
        nle, nte = n_le + 1, n_te + 1
        self.nle, self.nte = nle, nte
        nn = nle + nte
        # numeracion de GDL: el extremo del tirante comparte ux,uy,uz,rx,ry con la punta de la varilla
        dof = np.arange(nn * 6).reshape(nn, 6)
        tip_le, tip_te = nle - 1, nn - 1
        self.tip = tip_le
        if punta_libre:
            # el tirante solo apoya la punta en el plano (ux, uy); fuera del plano no colabora
            dof[tip_te, 0:2] = dof[tip_le, 0:2]
        else:
            dof[tip_te, 0:5] = dof[tip_le, 0:5]
        self.dof = dof
        nd = nn * 6
        K = np.zeros((nd, nd))
        M = np.zeros((nd, nd))
        self.elems = []
        sJ = L / 2
        for i in range(n_le):
            sm = 0.5 * (self.s_le[i] + self.s_le[i + 1])
            sec = SEC_SLV if abs(sm - sJ) < P.SLV_L / 2 else SEC_LE
            ds = self.s_le[i + 1] - self.s_le[i]
            # tela tributaria a la varilla: 0,5 g repartidos en forma triangular
            m_tela = 0.5e-6 * 2 * sm / L * ds / L
            self.elems.append((i, i + 1, sec, m_tela, "LE"))
        for i in range(n_te):
            ds = self.s_te[1] - self.s_te[0]
            self.elems.append((nle + i, nle + i + 1, SEC_TE, 0.25e-6 * ds / c, "TE"))
        self.kloc = []
        for (a, b, sec, me, tag) in self.elems:
            kg, mg, Tm, kl = k_m_elem(self.xyz[a], self.xyz[b], sec, me)
            ix = np.concatenate([dof[a], dof[b]])
            K[np.ix_(ix, ix)] += kg
            M[np.ix_(ix, ix)] += mg
            self.kloc.append((ix, Tm, kl, sec, tag))
        # masas concentradas: articulacion + manguito en J (3,85 g menos el tubo ya modelado), herraje de punta
        jn = int(np.argmin(np.abs(self.s_le - sJ)))
        self.jn = jn
        for node, m in ((jn, 1.2e-6), (tip_le, 1.2e-6)):
            for d in range(3):
                M[dof[node, d], dof[node, d]] += m
        # condiciones de borde: A y B = horquillas con perno vertical
        fixed = list(dof[0, [0, 1, 2, 3, 4]]) + list(dof[nle, [0, 1, 2, 3, 4]])
        if punta_libre:
            fixed += list(dof[tip_te, [2, 3, 4]])
        if not con_tirante:
            fixed = list(dof[0, [0, 1, 2, 3, 4]]) + list(dof[nle:].ravel())
        used = np.unique(dof)
        self.free = np.array([d for d in used if d not in set(fixed)])
        self.K, self.M = K, M
        self.con_tirante = con_tirante

    # ------------------------------------------------------------ cargas
    def carga_tela(self, p, m=P.NOTA["m_panza"]):
        """Cargas nodales de la tela (modelo de tiras): presion p [Pa] sobre el ala."""
        phi = math.radians(P.SWEEP)
        F = np.zeros(self.K.shape[0])
        pm = p * 1e-6                                     # N/mm2
        th = math.atan(4 * m)
        n_plano = np.array([math.sin(phi), -math.cos(phi), 0.0])   # perpendicular a la varilla, hacia el cuerpo
        for i in range(self.nle - 1):
            s0, s1 = self.s_le[i], self.s_le[i + 1]
            for s, w in ((s0, 0.5), (s1, 0.5)):
                ell = s * math.sin(phi)                   # largo de la tira
                qz = pm * ell / 2 * math.cos(phi)
                Tt = pm * ell / (8 * m)
                qy = Tt * math.cos(th) * math.cos(phi) ** 2
                node = i if s == s0 else i + 1
                F[self.dof[node, 2]] += qz * (s1 - s0) * w
                F[self.dof[node, 0:3]] += qy * (s1 - s0) * w * n_plano
        return F

    def carga_inercial(self, d, a):
        r = np.zeros(self.K.shape[0])
        r[self.dof[:, d].ravel()] = 1.0
        return -self.M @ r * a

    # ---------------------------------------------------------- solucion
    def estatico(self, F):
        f = self.free
        u = np.zeros(self.K.shape[0])
        u[f] = np.linalg.solve(self.K[np.ix_(f, f)], F[f])
        return u

    def modal(self, n=8):
        f = self.free
        w2, v = eigh(self.K[np.ix_(f, f)], self.M[np.ix_(f, f)], subset_by_index=[0, n - 1])
        phi = np.zeros((n, self.K.shape[0]))
        phi[:, f] = v.T
        gam = np.zeros((n, 3))
        for d in range(3):
            r = np.zeros(self.K.shape[0])
            r[self.dof[:, d].ravel()] = 1.0
            gam[:, d] = phi @ (self.M @ r)
        return np.sqrt(np.abs(w2)) / (2 * np.pi), phi, gam

    def esfuerzos(self, u):
        """Por elemento: axial N, momento flector resultante M (max de los dos extremos), tension."""
        out = []
        for (ix, Tm, kl, sec, tag), (a, b, *_r) in zip(self.kloc, self.elems):
            f = kl @ (Tm @ u[ix])
            N = -f[0]
            M1 = math.hypot(f[4], f[5])
            M2 = math.hypot(f[10], f[11])
            Mz1, My1 = f[5], f[4]
            Mmax = max(M1, M2)
            sig = abs(N) / sec["A"] + Mmax * sec["c"] / sec["I"]
            out.append(dict(tag=tag, a=a, b=b, N=N, M=Mmax, M1=M1, M2=M2, Mplano=abs(f[5]), Mfuera=abs(f[4]),
                            sigma=sig, sec=sec))
        return out

    def reacciones(self, u, F):
        return self.K @ u - F


def resumen_caso(ala, u, nombre):
    es = ala.esfuerzos(u)
    le = [e for e in es if e["tag"] == "LE" and e["sec"] is SEC_LE]
    te = [e for e in es if e["tag"] == "TE"]
    ej = [e for e in es if e["tag"] == "LE" and (e["a"] == ala.jn or e["b"] == ala.jn)]
    d = dict(caso=nombre,
             flecha_z_punta=float(u[ala.dof[ala.tip, 2]]),
             flecha_z_max=float(np.max(np.abs(u[ala.dof[:ala.nle, 2]]))),
             flecha_plano_max=float(np.max(np.hypot(u[ala.dof[:ala.nle, 0]], u[ala.dof[:ala.nle, 1]]))),
             M_apice=float(le[0]["M1"]), sigma_LE=float(max(e["sigma"] for e in le)),
             M_J=float(max(e["M"] for e in ej)), M_J_fuera=float(max(e["Mfuera"] for e in ej)),
             M_J_plano=float(max(e["Mplano"] for e in ej)),
             N_tirante=float(min(e["N"] for e in te)) if te else 0.0,
             sigma_TE=float(max(e["sigma"] for e in te)) if te else 0.0,
             N_LE=float(min(e["N"] for e in le)))
    return d


def main(out_json, out_npz):
    res = {}
    p_d = P.NOTA["p_choque"]
    # (1) hipotesis de la nota: voladizo fuera del plano, biapoyada en el plano
    nota = Ala(c=P.NOTA["c"], punta_libre=True)
    u = nota.estatico(nota.carga_tela(p_d))
    res["nota"] = resumen_caso(nota, u, "nota de membrana (voladizo + biapoyada), p = 367 Pa")
    # (2) portico real: el tirante con horquilla tambien sostiene la punta fuera del plano
    ala = Ala()
    F = ala.carga_tela(p_d)
    u2 = ala.estatico(F)
    res["portico"] = resumen_caso(ala, u2, "portico con tirante (este diseno), p = 367 Pa")
    R = ala.reacciones(u2, F)
    res["portico"]["R_A"] = [float(x) for x in R[ala.dof[0]]]
    res["portico"]["R_B"] = [float(x) for x in R[ala.dof[ala.nle]]]
    u3 = ala.estatico(ala.carga_tela(P.NOTA["p_vuelo"]))
    res["vuelo"] = resumen_caso(ala, u3, "portico, vuelo estabilizado p = 122 Pa")
    # (3) modal
    freq, phi, gam = ala.modal(8)
    res["modal"] = dict(freq=[float(f) for f in freq])
    # (4) choque de 30 g (semiseno) con el ala desplegada, en los tres ejes: peor caso sobre duraciones
    zeta = P.ZETA
    res["choque"] = {}
    hist = {}
    for d, eje in enumerate("xyz"):
        peor = None
        for tau in (0.003, 0.006, 0.011, 0.020):
            t = np.linspace(0, tau + 4 / freq[0], 4000)
            ab = post.semiseno(t, P.N_SHOCK * post.G_MM, tau)
            q, qs = post.q_transitorio(freq, gam[:, d], t, ab, zeta)
            ust = ala.estatico(ala.carga_inercial(d, 1.0))
            sig_t = np.zeros(len(t))
            # tension maxima en el tiempo (muestreo de 200 instantes alrededor del pico)
            utip = ab * ust[ala.dof[ala.tip, 2]] + (q - qs) @ phi[:, ala.dof[ala.tip, 2]]
            best = dict(sigma=0)
            for k in np.linspace(0, len(t) - 1, 400).astype(int):
                uk = ab[k] * ust + (q[k] - qs[k]) @ phi
                r = resumen_caso(ala, uk, "")
                if r["sigma_LE"] > best["sigma"]:
                    best = dict(sigma=r["sigma_LE"], M_apice=r["M_apice"], M_J=r["M_J"], sigma_TE=r["sigma_TE"],
                                N_tirante=r["N_tirante"], t=float(t[k]))
            best["tau"] = tau
            best["flecha_punta_max"] = float(np.max(np.abs(utip)))
            if peor is None or best["sigma"] > peor["sigma"]:
                peor = best
                hist[eje] = (t, utip, ab)
        res["choque"][eje] = peor
    # (5) pandeo del tirante
    Pcr = math.pi ** 2 * SEC_TE["E"] * SEC_TE["I"] / P.L_TE ** 2
    res["tirante"] = dict(Pcr=Pcr, N=abs(res["portico"]["N_tirante"]), coef=Pcr / abs(res["portico"]["N_tirante"]))
    json.dump(res, open(out_json, "w"), indent=1, default=float)
    np.savez(out_npz, s_le=ala.s_le, xyz=ala.xyz, nle=ala.nle,
             uz_nota=u[nota.dof[:nota.nle, 2]], uz=u2[ala.dof[:ala.nle, 2]],
             M_nota=[e["M"] for e in nota.esfuerzos(u) if e["tag"] == "LE"],
             Mf_nota=[e["Mfuera"] for e in nota.esfuerzos(u) if e["tag"] == "LE"],
             Mp_nota=[e["Mplano"] for e in nota.esfuerzos(u) if e["tag"] == "LE"],
             M=[e["M"] for e in ala.esfuerzos(u2) if e["tag"] == "LE"],
             Mf=[e["Mfuera"] for e in ala.esfuerzos(u2) if e["tag"] == "LE"],
             Mp=[e["Mplano"] for e in ala.esfuerzos(u2) if e["tag"] == "LE"],
             freq=freq, phi=phi, dof=ala.dof,
             t_z=hist["z"][0], utip_z=hist["z"][1], ab_z=hist["z"][2])
    for k, v in res.items():
        print(k, json.dumps(v, default=float)[:600])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
