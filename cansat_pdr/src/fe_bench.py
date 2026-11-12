"""Verificacion de la cadena de calculo (Gmsh -> CalculiX -> superposicion modal propia)
contra soluciones analiticas: viga en voladizo de aluminio 12 x 8 x 200 mm."""
import os, sys, json
import numpy as np
import cadquery as cq
import params as P
import fe_model as F
import fe_post as post

L, b, h = 200.0, 12.0, 8.0


def main(wd, out_json):
    os.makedirs(wd, exist_ok=True)
    mat = P.MAT["AL6061"]
    E, rho = mat["E"], mat["rho"] * 1e-9
    shape = cq.Solid.makeBox(L, b, h, cq.Vector(0, -b / 2, -h / 2))
    part = dict(nombre="viga", shape=shape, mat="AL6061", grupo="estructura", masa=shape.Volume() * mat["rho"] / 1000,
                vol=shape.Volume(), rho=rho, color=(0.7, 0.7, 0.7))
    F.h_de_orig = F.h_de
    F.h_de = lambda p, escala=1.0: 2.0
    xyz, els, epart = F.mallar([part], wd)
    F.h_de = F.h_de_orig
    fijos = np.where(np.abs(xyz[:, 0]) < 1e-6)[0]
    F.escribir_inp(os.path.join(wd, "modal_b.inp"), xyz, els, epart, [part], "modal", [(fijos, 1, 3)], 12)
    F.escribir_inp(os.path.join(wd, "estat_b.inp"), xyz, els, epart, [part], "estat3", [(fijos, 1, 3)])
    F.correr_ccx("modal_b", wd)
    F.correr_ccx("estat_b", wd)
    nn = len(xyz)
    freq, pf, em = post.leer_dat_modal(os.path.join(wd, "modal_b.dat"))
    phi = np.array(post.leer_frd_U(os.path.join(wd, "modal_b.frd"), nn))
    ust = np.array(post.leer_frd_U(os.path.join(wd, "estat_b.frd"), nn)) / post.G_MM
    I, A = b * h ** 3 / 12, b * h
    c = np.sqrt(E * I / (rho * A))
    lam = np.array([1.8751041, 4.6940911, 7.8547574])
    f_an = lam ** 2 / (2 * np.pi * L ** 2) * c
    # modos de flexion en z: los que tienen participacion dominante en z
    iz = [i for i in range(len(freq)) if abs(pf[i, 2]) > 10 * max(abs(pf[i, 0]), abs(pf[i, 1]), 1e-12)][:3]
    tip = np.argmin(np.linalg.norm(xyz - np.array([L, 0, 0]), axis=1))
    res = dict(nodos=int(nn), elementos=int(len(els)))
    res["f_fem"] = [float(freq[i]) for i in iz]
    res["f_analitico"] = [float(x) for x in f_an]
    # estatico: flecha de punta por 1 g
    d_an = rho * A * post.G_MM * L ** 4 / (8 * E * I)
    d_fem = abs(ust[2][tip, 2]) * post.G_MM
    res["flecha_1g_fem"], res["flecha_1g_analitico"] = float(d_fem), float(d_an)
    # la suma modal reproduce el estatico (signo y unidades de los factores de participacion)
    wn = 2 * np.pi * freq
    u_modal = np.sum([-pf[i, 2] / wn[i] ** 2 * phi[i][tip, 2] for i in range(len(freq))]) * post.G_MM
    res["flecha_1g_suma_modal"] = float(abs(u_modal))
    res["signo_ok"] = bool(np.sign(u_modal) == np.sign(ust[2][tip, 2]))
    # tension en la raiz por 1 g
    dN, vol = post.gradientes(xyz, els, post.GP)
    D = np.array([post.matriz_D("iso", dict(E=E, nu=mat["nu"]))])
    s = post.tensiones(ust[2] * post.G_MM, els, dN, D, epart)
    cen = xyz[els[:, :4]].mean(axis=1)
    sel = (cen[:, 0] > 8) & (cen[:, 0] < 12) & (np.abs(cen[:, 2]) > 2.8)
    xg = cen[sel, 0].mean()
    zg = np.abs(cen[sel, 2]).mean()
    s_an = rho * A * post.G_MM * (L - xg) ** 2 / 2 * zg / I
    res["sigma_raiz_fem"] = float(np.abs(s[sel][:, :, 0]).mean())
    res["sigma_raiz_analitico"] = float(s_an)
    # armonico en resonancia del primer modo: amplitud de punta
    zeta, Aacc = P.ZETA, P.N_VIB * post.G_MM
    i1 = iz[0]
    q, qst = post.q_armonico(freq, pf[:, 2], freq[i1], Aacc, zeta)
    u_tip = Aacc * ust[2][tip, 2] + np.sum((q - qst) * phi[:, tip, 2])
    res["arm_punta_fem"] = float(abs(u_tip))
    res["arm_punta_analitico"] = float(1.5660 * Aacc / (2 * zeta * (2 * np.pi * f_an[0]) ** 2))
    # choque semiseno 30 g, 11 ms: pico de desplazamiento de punta contra 1 GDL analitico x 1,566
    t = np.linspace(0, 0.05, 5001)
    ab = post.semiseno(t, P.N_SHOCK * post.G_MM, P.TAU_SHOCK)
    qt, qs = post.q_transitorio(freq, pf[:, 2], t, ab, zeta)
    ut = ab * ust[2][tip, 2] + (qt - qs) @ phi[:, tip, 2]
    q1, _ = post.q_transitorio(np.array([f_an[0]]), np.array([1.0]), t, ab, zeta)
    res["choque_punta_fem"] = float(np.max(np.abs(ut)))
    res["choque_punta_1gdl"] = float(1.5660 * np.max(np.abs(q1)))
    json.dump(res, open(out_json, "w"), indent=1)
    for k, v in res.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
