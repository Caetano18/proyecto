"""Analisis dinamico de la configuracion de lanzamiento (resultados de CalculiX).
  - respuesta en frecuencia: barrido senoidal de 15 g (5-1000 Hz) en x, y, z
  - choque: semiseno de 30 g (11 ms nominal + barrido de duraciones) en x, y, z
  - casi-estatico 15 g / 30 g y tiron del paracaidas (30 g x FAD, colgado de la brida)
Uso: python3 fe_analisis.py <carpeta_fea> <tag> <salida.json> <salida.npz>
"""
import os, sys, json, time
import numpy as np
import params as P
import fe_post as post
import fe_model as F
from fe_post import von_mises, G_MM

EJES = "xyz"
F_BARRIDO = (5.0, 1000.0)
FAD_PARAC = 1.8          # factor de amplificacion dinamica del tiron (maximo del SRS de un semiseno)


def grupos_de(mod):
    """Grupos de verificacion: nombre -> (filas de elementos, criterios)."""
    M = P.MAT
    # se excluyen los elementos pegados a nodos con desplazamiento impuesto (singularidad numerica del apoyo)
    fijos = set(F.nodos_base(mod.xyz)) | set(F.nodos_guia(mod.xyz))
    toca = np.array([any(n in fijos for n in e) for e in mod.els[mod.ever][:, :4]])
    g = {}

    def sel(pred, excl=False):
        f = mod.filas(pred)
        f = f[mod.valido[f]]
        return f[~toca[f]] if excl else f
    g["Contenedor: tubo (LW-PLA)"] = dict(
        idx=sel(lambda p: p["nombre"].startswith("CT1"), True),
        crit=[("von Mises", "vm", M["LWPLA"]["Sut"], M["LWPLA"]["FS"]),
              ("sigma_x entre capas", "sx", M["LWPLA"]["Sut_z"], M["LWPLA"]["FS"])])
    g["Contenedor: tapa (PA12-CF)"] = dict(
        idx=sel(lambda p: p["nombre"].startswith("CT2")),
        crit=[("von Mises", "vm", M["PA12CF"]["Sut"], M["PA12CF"]["FS"]),
              ("sigma_x entre capas", "sx", M["PA12CF"]["Sut_z"], M["PA12CF"]["FS"])])
    g["Cuadernas (PA12-CF)"] = dict(
        idx=sel(lambda p: p["mat"] == "PA12CF" and p["grupo"] == "estructura" and "riel" not in p["nombre"]),
        crit=[("von Mises", "vm", M["PA12CF"]["Sut"], M["PA12CF"]["FS"]),
              ("sigma_x entre capas", "sx", M["PA12CF"]["Sut_z"], M["PA12CF"]["FS"])])
    # rieles impresos acostados (capas paralelas a x): sigma_x queda en el plano de las capas
    g["Rieles de bandeja (PA12-CF)"] = dict(
        idx=sel(lambda p: "riel" in p["nombre"]),
        crit=[("von Mises", "vm", M["PA12CF"]["Sut"], M["PA12CF"]["FS"])])
    g["Paneles y bandeja (G10)"] = dict(
        idx=sel(lambda p: p["mat"] == "G10"),
        crit=[("von Mises", "vm", M["G10"]["Sut"], M["G10"]["FS"])])
    g["Largueros (CFRP)"] = dict(
        idx=sel(lambda p: p["mat"] == "CFRP"),
        crit=[("sigma_x fibra", "sx", M["CFRP"]["Suc"], M["CFRP"]["FS"]),
              ("corte interlaminar", "tau", 50.0, M["CFRP"]["FS"])])
    g["Arandela de C4 (Al 7075)"] = dict(
        idx=sel(lambda p: p["nombre"].startswith("Arandela de C4")),
        crit=[("von Mises", "vm", M["AL7075"]["Sy"], M["AL7075"]["FS"])])
    g["Llave de bayoneta (A2-70)"] = dict(
        idx=sel(lambda p: p["mat"] == "A2-70"),
        crit=[("von Mises", "vm", M["A2-70"]["Sy"], M["A2-70"]["FS"])])
    return g


def medida(s, cual):
    if cual == "vm":
        return von_mises(s)
    if cual == "sx":
        return np.abs(s[..., 0])
    if cual == "tau":
        return np.sqrt(s[..., 3] ** 2 + s[..., 5] ** 2)
    raise ValueError(cual)


def pico_ciclo(Sc, cual, nfase=8):
    """Maximo sobre un ciclo y sobre los puntos de Gauss de un campo complejo [E, 4, 6] -> [E]."""
    out = None
    for th in np.linspace(0, np.pi, nfase, endpoint=False):
        v = medida((Sc * np.exp(1j * th)).real, cual).max(axis=-1)
        out = v if out is None else np.maximum(out, v)
    return out


def monitores(mod):
    pts = {"Nariz (C1)": (1, 0, 0), "Bandeja nariz": (33, 0, -4.6), "Bandeja centro": (100, 0, -4.6),
           "Bandeja cola": (170, 0, -4.6), "C4 (cola)": (203, 20, 20), "Tapa del contenedor": (212, 20, 3),
           "Tubo (media altura)": (120, 0, 44)}
    return {k: int(np.argmin(np.linalg.norm(mod.xyz - np.array(v), axis=1))) for k, v in pts.items()}


# pares de puntos para desplazamientos relativos: (punto A, pieza A, punto B, pieza B, referencia [mm], que se verifica)
_xf = P.CT_TOP[0] + P.CT_CAP_FLOOR
PARES = {
    "Manguito del centrador (y)": ((209.0, 20.0, 0.0), "C4", (209.0, 21.0, 0.0), "CT2", P.CEN_ELT, "deformacion"),
    "Manguito del centrador (z)": ((209.0, 0.0, 20.0), "C4", (209.0, 0.0, 21.0), "CT2", P.CEN_ELT, "deformacion"),
    "Patin C1 a 45 grados": ((4.0, P.R_C1 * 0.70711, P.R_C1 * 0.70711), "C1", (4.0, P.CT_RI * 0.70711, P.CT_RI * 0.70711), "CT1",
                             P.CT_RI - P.R_C1, "deformacion"),
    "Aislador de la llave": ((_xf, 0.0, 5.5), "CT2", (_xf + P.ISO_T, 0.0, 5.5), "Llave", P.ISO_T, "deformacion"),
    "Huelgo aro C4 - tubo (y)": ((203.0, P.RB, 0.0), "C4", (203.0, P.CT_RI, 0.0), "CT1", P.CT_RI - P.RB, "huelgo"),
    "Huelgo aro C4 - tubo (z)": ((203.0, 0.0, P.RB), "C4", (203.0, 0.0, P.CT_RI), "CT1", P.CT_RI - P.RB, "huelgo"),
}


def rel_estatico(du, eje, A):
    n_ = eje / np.linalg.norm(eje)
    r_ = abs(float(np.dot(du, n_))) * A
    m_ = float(np.linalg.norm(du)) * A
    return dict(max=m_, rad=r_, cort=float(np.sqrt(max(m_ ** 2 - r_ ** 2, 0.0))))


def nodos_pares(mod):
    """Nodo de la pieza A mas cercano al punto A y de la pieza B mas cercano al punto B.  La direccion de referencia
    (compresion o cierre) es la de A hacia B en coordenadas nominales."""
    out = {}
    for k, (a, pa, b, pb, ref, tipo) in PARES.items():
        sel = []
        for pt, pref in ((a, pa), (b, pb)):
            ids = [i for i, p in enumerate(mod.partes) if p["nombre"].startswith(pref)]
            nod = np.unique(mod.els[np.isin(mod.epart, ids)])
            sel.append(int(nod[np.argmin(np.linalg.norm(mod.xyz[nod] - np.array(pt), axis=1))]))
        out[k] = (sel[0], sel[1], ref, tipo, np.array(b, float) - np.array(a, float))
    return out


def main(wd, tag, out_json, out_npz, zeta=None):
    t0 = time.time()
    mod = post.Modelo(wd, tag)
    nm = len(mod.freq)
    wn = 2 * np.pi * mod.freq
    A_v = P.N_VIB * G_MM
    A_s = P.N_SHOCK * G_MM
    zeta = mod.zeta if zeta is None else np.full(nm, float(zeta))
    G = grupos_de(mod)
    mon = monitores(mod)
    pares = nodos_pares(mod)
    cen = mod.xyz[mod.els[mod.ever][:, :4]].mean(axis=1)
    res = dict(nodos=int(len(mod.xyz)), elementos=int(len(mod.els)), masa_g=mod.masa, zeta=P.ZETA,
               zeta_modal=[float(x) for x in zeta], f_elast=[float(x) for x in mod.f_elast],
               eta_elast=P.MAT["ELAST"]["eta"], n_filtrados=int((~mod.valido).sum()), n_nodos_anomalos=int(len(mod.anom)),
               n_ever=int(len(mod.ever)),
               freq=[float(f) for f in mod.freq], m_eff=(mod.em[:, :3] * 1e6).tolist(),
               m_eff_frac=(np.cumsum(mod.em[:, :3], axis=0) * 1e6 / mod.masa).tolist(),
               pf=mod.pf[:, :3].tolist(),
               freq_libre=None if mod.freq_libre is None else [float(f) for f in mod.freq_libre],
               piezas=[dict(nombre=p["nombre"], mat=p["mat"], masa=p["masa"], n_el=int(np.sum(mod.epart == i)))
                       for i, p in enumerate(mod.partes)])
    print(f"modelo cargado ({time.time() - t0:.0f} s): {nm} modos, f1 = {mod.freq[0]:.1f} Hz, "
          f"{len(mod.ever)} elementos con tensiones")
    chk = {}
    for d in range(3):
        n = mon["Bandeja centro"]
        um = float(np.sum(-mod.pf[:, d] / wn ** 2 * mod.phi[:, n, d]))
        # control completo: norma del vector desplazamiento en todos los nodos, no solo la componente del eje
        uf = -np.tensordot(mod.pf[:, d] / wn ** 2, mod.phi, axes=1)
        err = float(np.linalg.norm(uf - mod.ust[d]) / np.linalg.norm(mod.ust[d]))
        chk[EJES[d]] = dict(estatico=float(mod.ust[d][n, d]), suma_modal=um, error_relativo_campo=err)
    res["control_estatico"] = chk
    res["estat_acumulado_corregido"] = bool(mod.estat_acumulado)
    print("control estatico (bateria):", {k: (f"{v['estatico']:.3e}", f"{v['suma_modal']:.3e}") for k, v in chk.items()})
    arr = dict(ever=mod.ever)

    def margenes(S):
        out = {}
        for nombre, gd in G.items():
            idx = gd["idx"]
            for (cn, cual, adm, fs) in gd["crit"]:
                v = medida(S[idx], cual).max(axis=-1)
                vmax, p999 = float(v.max()), float(np.percentile(v, 99.9))
                e = idx[np.argmax(v)]
                out[f"{nombre} | {cn}"] = dict(sigma=vmax, p999=p999, adm=adm, FS=fs, MS=adm / (fs * vmax) - 1,
                                               MS_p999=adm / (fs * p999) - 1, pos=[float(c) for c in cen[e]])
        return out

    # ============================================================ casi-estatico
    res["cuasi15"], res["cuasi30"] = {}, {}
    for d in range(3):
        comb = np.zeros(3)
        comb[d] = A_s
        S = mod.S(np.zeros(nm), comb)
        res["cuasi30"][EJES[d]] = dict(margenes=margenes(S), umax=float(np.linalg.norm(mod.ust[d], axis=1).max() * A_s),
                                       rel={k: rel_estatico(mod.ust[d][na] - mod.ust[d][nb], eje_, A_s)
                                            for k, (na, nb, ref, tipo, eje_) in pares.items()})
        res["cuasi15"][EJES[d]] = dict(margenes=margenes(S * (A_v / A_s)),
                                       umax=float(np.linalg.norm(mod.ust[d], axis=1).max() * A_v))
        arr[f"cuasi_vm_{EJES[d]}"] = von_mises(S).max(axis=1)
    Sp = mod.s_par * (A_s * FAD_PARAC)
    nb = set(F.nodos_brida(mod.xyz))
    toca = np.array([any(n in nb for n in e) for e in mod.els[mod.ever]])
    Sp[toca] = 0.0
    res["paracaidas"] = dict(margenes=margenes(Sp), umax=float(np.linalg.norm(mod.upar, axis=1).max() * A_s * FAD_PARAC),
                             rel={k: rel_estatico(mod.upar[na] - mod.upar[nb], eje_, A_s * FAD_PARAC)
                                  for k, (na, nb, ref, tipo, eje_) in pares.items()},
                             FAD=FAD_PARAC)
    arr["parac_vm"] = von_mises(Sp).max(axis=1)
    arr["parac_U"] = (mod.upar * A_s * FAD_PARAC).astype(np.float32)
    print(f"casi-estatico listo ({time.time() - t0:.0f} s)")

    # ============================================================ respuesta en frecuencia
    res["armonico"] = {}
    fgrid = np.unique(np.concatenate([np.geomspace(*F_BARRIDO, 380)] +
                                     [f * (1 + z_ * np.linspace(-4, 4, 17)) for f, z_ in zip(mod.freq, zeta)
                                      if f < F_BARRIDO[1]]))
    fgrid = fgrid[(fgrid >= F_BARRIDO[0]) & (fgrid <= F_BARRIDO[1])]
    arr["fgrid"] = fgrid
    medidas = sorted({(n, c[1]) for n, g_ in G.items() for c in g_["crit"]})
    for d in range(3):
        eje = EJES[d]
        gam = mod.pf[:, d]
        fres = [f for f in mod.freq if F_BARRIDO[0] <= f <= F_BARRIDO[1]]
        top = {k: set() for k in medidas}
        for f in fres:                       # campo completo en cada resonancia
            q, qst = post.q_armonico(mod.freq, gam, f, A_v, zeta)
            Sc = A_v * mod.s_st[d].astype(np.complex64) + np.tensordot((q - qst).astype(np.complex64), mod.s_phi, axes=1)
            for (gn, cual) in medidas:
                idx = G[gn]["idx"]
                v = pico_ciclo(Sc[idx], cual, 6)
                top[(gn, cual)].update(idx[np.argsort(v)[-120:]].tolist())
        curvas = {}
        for (gn, cual) in medidas:           # barrido fino sobre los elementos mas cargados
            sub = np.array(sorted(top[(gn, cual)]))
            sst = A_v * mod.s_st[d][sub].astype(np.complex64)
            sph = mod.s_phi[:, sub]
            cur = np.zeros(len(fgrid))
            for k, f in enumerate(fgrid):
                q, qst = post.q_armonico(mod.freq, gam, f, A_v, zeta)
                cur[k] = pico_ciclo(sst + np.tensordot((q - qst).astype(np.complex64), sph, axes=1), cual, 6).max()
            curvas[(gn, cual)] = cur
            arr[f"arm_{eje}_{gn}|{cual}"] = cur
        for mn, node in mon.items():         # transmisibilidad
            Tm = np.zeros(len(fgrid))
            for k, f in enumerate(fgrid):
                q, qst = post.q_armonico(mod.freq, gam, f, A_v, zeta)
                u = A_v * mod.ust[d][node, d] + np.sum((q - qst) * mod.phi[:, node, d])
                Tm[k] = abs(A_v - (2 * np.pi * f) ** 2 * u) / A_v
            arr[f"trans_{eje}_{mn}"] = Tm
        rel = {}
        for k, (na, nb, ref, tipo, eje_) in pares.items():
            nrm = eje_ / np.linalg.norm(eje_)
            cur, cur_r = np.zeros(len(fgrid)), np.zeros(len(fgrid))
            for kk, f in enumerate(fgrid):
                q, qst = post.q_armonico(mod.freq, gam, f, A_v, zeta)
                du = A_v * (mod.ust[d][na] - mod.ust[d][nb]) + np.tensordot(q - qst, mod.phi[:, na] - mod.phi[:, nb], axes=1)
                cur[kk] = float(np.sqrt(np.sum(np.abs(du) ** 2)))
                cur_r[kk] = float(abs(np.dot(du, nrm)))
            cur_t = np.sqrt(np.maximum(cur ** 2 - cur_r ** 2, 0.0))
            rel[k] = dict(max=float(cur.max()), rad=float(cur_r.max()), cort=float(cur_t.max()), f=float(fgrid[np.argmax(cur_r)]))
            arr[f"rel_{eje}_{k}"] = cur_r
        marg = {}
        env = np.zeros(len(mod.ever), np.float32)        # envolvente de von Mises en las frecuencias criticas
        for nombre, gd in G.items():
            for (cn, cual, adm, fs) in gd["crit"]:
                cur = curvas[(nombre, cual)]
                fc = float(fgrid[np.argmax(cur)])
                q, qst = post.q_armonico(mod.freq, gam, fc, A_v, zeta)
                Sc = A_v * mod.s_st[d].astype(np.complex64) + np.tensordot((q - qst).astype(np.complex64), mod.s_phi, axes=1)
                idx = gd["idx"]
                v = pico_ciclo(Sc[idx], cual, 12)
                env = np.maximum(env, pico_ciclo(Sc, "vm", 6))
                e = idx[np.argmax(v)]
                marg[f"{nombre} | {cn}"] = dict(sigma=float(v.max()), p999=float(np.percentile(v, 99.9)), adm=adm, FS=fs,
                                                MS=adm / (fs * float(v.max())) - 1,
                                                MS_p999=adm / (fs * float(np.percentile(v, 99.9))) - 1, f_crit=fc,
                                                pos=[float(c) for c in cen[e]])
        arr[f"arm_vm_{eje}"] = env
        # deformada en la resonancia de mayor masa efectiva del eje
        i0 = int(np.argmax(mod.em[:, d]))
        q, qst = post.q_armonico(mod.freq, gam, mod.freq[i0], A_v, zeta)
        dq = (q - qst) * np.exp(-1j * np.angle((q - qst)[i0]))
        arr[f"arm_U_{eje}"] = mod.U(dq.real.astype(np.float32), np.eye(3)[d] * 0.0).astype(np.float32)
        res["armonico"][eje] = dict(margenes=marg, f_modo_principal=float(mod.freq[i0]), rel=rel,
                                    trans_max={mn: float(arr[f"trans_{eje}_{mn}"].max()) for mn in mon},
                                    f_trans_max={mn: float(fgrid[np.argmax(arr[f"trans_{eje}_{mn}"])]) for mn in mon})
        print(f"armonico {eje} listo ({time.time() - t0:.0f} s)")

    # ============================================================ choque
    res["choque"] = {}
    taus = [0.001, 0.002, 0.003, 0.004, 0.006, 0.008, 0.011, 0.015, 0.020]
    for d in range(3):
        eje = EJES[d]
        gam = mod.pf[:, d]

        def historia(tau, n=1200):
            T = tau + 4.0 / mod.freq[0]
            t = np.linspace(0, T, n)
            ab = post.semiseno(t, A_s, tau)
            q, qst = post.q_transitorio(mod.freq, gam, t, ab, zeta)
            return t, ab, (q - qst).astype(np.float32)
        top = {k: set() for k in medidas}
        for tau in (0.003, P.TAU_SHOCK):
            t, ab, dq = historia(tau)
            for k in np.linspace(0, len(t) - 1, 70).astype(int):
                S = ab[k] * mod.s_st[d] + np.tensordot(dq[k], mod.s_phi, axes=1)
                for (gn, cual) in medidas:
                    idx = G[gn]["idx"]
                    v = medida(S[idx], cual).max(axis=-1)
                    top[(gn, cual)].update(idx[np.argsort(v)[-120:]].tolist())
        marg, dur = {}, {}
        env = np.zeros(len(mod.ever), np.float32)
        for nombre, gd in G.items():
            for (cn, cual, adm, fs) in gd["crit"]:
                sub = np.array(sorted(top[(nombre, cual)]))
                sst, sph = mod.s_st[d][sub], mod.s_phi[:, sub]
                best = (0.0, 0, 0.0)
                curva_tau = []
                for tau in taus:
                    tt, aa, dd = historia(tau)
                    S = aa.astype(np.float32)[:, None, None, None] * sst[None] + np.tensordot(dd, sph, axes=1)
                    v = medida(S, cual).max(axis=(1, 2))
                    curva_tau.append(float(v.max()))
                    if tau == P.TAU_SHOCK:
                        knom, vnom = int(np.argmax(v)), float(v.max())
                        arr[f"choque_hist_{eje}_{nombre}|{cual}"] = v
                        arr[f"choque_t_{eje}"] = tt
                        arr[f"choque_ab_{eje}"] = aa
                    if v.max() > best[0]:
                        best = (float(v.max()), int(np.argmax(v)), tau)
                dur[f"{nombre} | {cn}"] = curva_tau
                tt, aa, dd = historia(best[2])
                comb = np.zeros(3)
                comb[d] = aa[best[1]]
                S = mod.S(dd[best[1]], comb)
                idx = gd["idx"]
                v = medida(S[idx], cual).max(axis=-1)
                env = np.maximum(env, von_mises(S).max(axis=1))
                e = idx[np.argmax(v)]
                marg[f"{nombre} | {cn}"] = dict(sigma=float(v.max()), p999=float(np.percentile(v, 99.9)), adm=adm, FS=fs,
                                                MS=adm / (fs * float(v.max())) - 1,
                                                MS_p999=adm / (fs * float(np.percentile(v, 99.9))) - 1,
                                                tau_crit=best[2], sigma_11ms=vnom, MS_11ms=adm / (fs * vnom) - 1,
                                                pos=[float(c) for c in cen[e]])
        arr[f"choque_vm_{eje}"] = env
        rel = {}
        for k, (na, nb, ref, tipo, eje_) in pares.items():
            nrm = eje_ / np.linalg.norm(eje_)
            mx, mr, mt = 0.0, 0.0, 0.0
            for tau in taus:
                tt, aa, dd = historia(tau)
                du = aa[:, None] * (mod.ust[d][na] - mod.ust[d][nb])[None, :] + dd @ (mod.phi[:, na] - mod.phi[:, nb])
                r_ = np.abs(du @ nrm)
                t_ = np.sqrt(np.maximum(np.sum(du ** 2, axis=1) - r_ ** 2, 0.0))
                mx = max(mx, float(np.linalg.norm(du, axis=1).max()))
                mr, mt = max(mr, float(r_.max())), max(mt, float(t_.max()))
            rel[k] = dict(max=mx, rad=mr, cort=mt)
        t, ab, dq = historia(P.TAU_SHOCK, 2400)
        acc = {}
        for mn, node in mon.items():
            u = ab * mod.ust[d][node, d] + dq @ mod.phi[:, node, d]
            a_abs = ab + np.gradient(np.gradient(u, t), t)
            acc[mn] = float(np.max(np.abs(a_abs)) / G_MM)
            arr[f"choque_acc_{eje}_{mn}"] = (a_abs / G_MM).astype(np.float32)
        arr[f"choque_tacc_{eje}"] = t
        res["choque"][eje] = dict(margenes=marg, duraciones=dur, taus=taus, acc_max_g=acc, rel=rel)
        print(f"choque {eje} listo ({time.time() - t0:.0f} s)")
    fn = np.geomspace(10, 2000, 110)
    arr["srs_f"] = fn
    arr["srs_a"] = post.srs_semiseno(fn, P.N_SHOCK, P.TAU_SHOCK, P.ZETA)
    arr["srs_a15"] = post.srs_semiseno(fn, P.N_SHOCK, P.TAU_SHOCK, 0.15)
    for i in range(min(nm, 8)):
        arr[f"modo_{i}"] = mod.phi[i]
        arr[f"modo_vm_{i}"] = von_mises(mod.s_phi[i]).max(axis=1)
    res["pares"] = {k: dict(ref=v[2], tipo=v[3], a=PARES[k][0], b=PARES[k][2]) for k, v in pares.items()}
    json.dump(res, open(out_json, "w"), indent=1)
    np.savez_compressed(out_npz, **arr)
    print(f"total {time.time() - t0:.0f} s")
    return res


if __name__ == "__main__":
    main(*sys.argv[1:5], zeta=float(sys.argv[5]) if len(sys.argv) > 5 else None)
