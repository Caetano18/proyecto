"""Informe de texto (consola / archivo) con todo lo calculado, en secciones numeradas."""
from __future__ import annotations

import numpy as np

from .sistema import Sistema, tf_a_texto
from .frecuencia import ConteoNyquist

LINEA = "─" * 78


def _n(x, fmt="{:.4g}", inf="∞", nada="—"):
    if x is None:
        return nada
    if isinstance(x, (float, np.floating)) and np.isinf(x):
        return inf
    return fmt.format(x)


def _t(titulo: str, nivel: int = 1) -> str:
    if nivel == 1:
        return f"\n{'═' * 78}\n {titulo}\n{'═' * 78}"
    return f"\n── {titulo} " + "─" * max(2, 74 - len(titulo))


def _tabla(filas: list[list], cabecera: list[str] | None = None, sep: str = "  ", sangria: int = 4) -> str:
    todas = ([cabecera] if cabecera else []) + [[str(c) for c in f] for f in filas]
    anchos = [max(len(str(f[i])) for f in todas) for i in range(len(todas[0]))]
    pre = " " * sangria
    out = []
    for k, f in enumerate(todas):
        out.append(pre + sep.join(str(c).ljust(a) for c, a in zip(f, anchos)).rstrip())
        if cabecera and k == 0:
            out.append(pre + sep.join("─" * a for a in anchos))
    return "\n".join(out)


def _poles(p: np.ndarray, dec: int = 4) -> str:
    items = []
    p = np.array([complex(0.0 if abs(r.real) < 1e-9 * max(1, abs(r)) else r.real,
                          0.0 if abs(r.imag) < 1e-9 * max(1, abs(r)) else r.imag) for r in p])
    for r in sorted(p, key=lambda x: (abs(x.imag) > 1e-9, x.real)):
        if abs(r.imag) < 1e-9 * max(1, abs(r)):
            items.append(f"{r.real:.{dec}g}")
        elif r.imag > 0:
            items.append(f"{r.real:.{dec}g} ± j{abs(r.imag):.{dec}g}")
    return ";  ".join(items) if items else "—"


# ----------------------------------------------------------------------------
def seccion_sistema(sis: Sistema, nombre: str = "Lazo abierto L(s)") -> str:
    fb = sis.forma_bode()
    ce = sis.constantes_error()
    k, z, p = sis.raices()
    out = [_t("1. SISTEMA")]
    out.append(f"  {nombre} = C(s)·G(s)·H(s)" + (f"·e^(-{sis.retardo:g}·s)" if sis.retardo else ""))
    out.append(f"  Polinomios:      {tf_a_texto(sis.L, 'polinomios', 5)}")
    out.append(f"  Polos y ceros:   {tf_a_texto(sis.L, 'polos_ceros', 5)}")
    out.append(f"  Forma de Bode:   {fb.texto()}")
    out.append(f"  Polos de L:      {_poles(p)}")
    out.append(f"  Ceros de L:      {_poles(z) if z.size else '(ninguno)'}")
    out.append(f"  Tipo del sistema: {ce['tipo']}      Ganancia de Bode K_B = {fb.K_B:.5g}  ({20 * np.log10(abs(fb.K_B)):.2f} dB)")
    out.append(f"  Constantes de error:  Kp = {_n(ce['Kp'])}    Kv = {_n(ce['Kv'])} s⁻¹    Ka = {_n(ce['Ka'])} s⁻²")
    errs = []
    Kp, Kv, Ka = ce["Kp"], ce["Kv"], ce["Ka"]
    errs.append(f"escalón: {_n(0.0 if np.isinf(Kp) else 1.0 / (1 + Kp), '{:.4g}')}")
    errs.append(f"rampa: {'∞' if Kv == 0 else _n(0.0 if np.isinf(Kv) else 1.0 / Kv)}")
    errs.append(f"parábola: {'∞' if Ka == 0 else _n(0.0 if np.isinf(Ka) else 1.0 / Ka)}")
    out.append("  Error en régimen (realim. unitaria):  " + "   ".join(errs))
    q = fb.quiebres()
    if q:
        out.append("  Quiebres (para trazar el Bode asintótico):")
        out.append(_tabla([[f"{w:.4g}", f"{d:+.0f} dB/dec", desc] for w, d, desc in q], ["ω [rad/s]", "cambio de pendiente", "origen"], "   "))
        pend = -20 * fb.N
        filas = [[f"ω < {q[0][0]:.4g}", f"{pend:+.0f} dB/dec"]]
        for i, (w, d, _) in enumerate(q):
            pend += d
            lim = f"{w:.4g} < ω < {q[i + 1][0]:.4g}" if i + 1 < len(q) else f"ω > {w:.4g}"
            filas.append([lim, f"{pend:+.0f} dB/dec"])
        out.append("  Pendiente de la asíntota por tramos:")
        out.append(_tabla(filas, None, "   "))
    return "\n".join(out)


def seccion_estabilidad(c: ConteoNyquist, polos_cl: np.ndarray, rangos: dict, K_ref: float, casos: list[dict] | None,
                        ganancias_criticas: list, unidad_K: str = "K", num: str = "2.", nombre: str = "") -> str:
    out = [_t(f"{num} ESTABILIDAD" + (f" — {nombre}" if nombre else ""))]
    out.append("  Criterio de Nyquist (conteo numérico sobre el contorno completo, con indentaciones en los polos del eje):")
    out.append(f"    P = {c.P} polos de L en el semiplano derecho")
    out.append(f"    N = {c.N} rodeos horarios al punto −1")
    out.append(f"    Z = N + P = {c.Z}  polos de lazo cerrado en el semiplano derecho")
    if c.polos_eje:
        out.append("    Polos de L sobre el eje imaginario (indentados): " + ", ".join("0" if w == 0 else f"±j{w:.4g}" for w in c.polos_eje))
    if c.Z_real is not None:
        out.append(f"    Verificación con las raíces del polinomio característico: Z = {c.Z_real}  ->  "
                   + ("COINCIDE" if c.coincide else "NO coincide (revisar: ¿retardo? ¿caso marginal?)"))
    if c.marginal:
        out.append("    ¡Ojo!: hay polos de lazo cerrado sobre el eje imaginario (sistema MARGINAL).")
    if c.residuo > 0.05:
        out.append(f"    Advertencia numérica: el conteo bruto no es entero (residuo {c.residuo:.2f}); mirar el diagrama.")
    out.append(f"  Polos de lazo cerrado: {_poles(polos_cl)}")
    est = bool(np.all(polos_cl.real < -1e-9))
    out.append("  => Lazo cerrado " + ("ESTABLE" if est else "NO ESTABLE"))
    pos = rangos.get("positivo", [])
    out.append("\n  Rango de ganancia para estabilidad (el factor κ multiplica a L; " + unidad_K + " = " + f"{K_ref:.5g}·κ" + "):")
    if pos:
        for lo, hi in pos:
            out.append(f"    estable para  {K_ref * lo:.5g} < {unidad_K} < {'∞' if np.isinf(hi) else format(K_ref * hi, '.5g')}")
    else:
        out.append("    no hay ningún K > 0 que estabilice el lazo")
    neg = rangos.get("negativo", [])
    if neg:
        for lo, hi in neg:
            out.append(f"    (con signo negativo) estable para  -{K_ref * hi if not np.isinf(hi) else '∞'} < {unidad_K} < -{K_ref * lo:.5g}")
    if ganancias_criticas:
        out.append("  Ganancias críticas (cruces de fase de L, L sobre el eje real negativo):")
        out.append(_tabla([[f"{w:.5g}", f"{K_ref * g:.5g}", f"{20 * np.log10(g):.2f} dB"] for w, g in ganancias_criticas],
                          ["ω180 [rad/s]", f"{unidad_K} crítico", "margen respecto del K actual"], "   "))
    if casos:
        out.append("\n  Casos de K con distinta naturaleza de respuesta:")
        filas = []
        for cs in casos:
            e = cs.get("escalon")
            mp = "—" if (e is None or e.Mp is None) else f"{e.Mp:.1f} %"
            ts = "—" if (e is None or e.ts is None) else f"{e.ts:.4g} s"
            filas.append([f"{cs['K']:.5g}", _poles(cs["polos"], 3), cs["descripcion"], mp, ts])
        out.append(_tabla(filas, [unidad_K, "polos de lazo cerrado", "comportamiento", "Mp", "ts(2%)"], "  "))
    return "\n".join(out)


def seccion_frecuencia(met, nombre: str = "", num: str = "3.") -> str:
    m, c = met.margenes, met.cerrado
    out = [_t(f"{num} RESPUESTA EN FRECUENCIA" + (f" — {nombre}" if nombre else ""))]
    out.append("  Márgenes de estabilidad relativa (lazo abierto):")
    if m.cruces_ganancia:
        out.append(_tabla([[f"{w:.5g}", f"{mf:.2f}°"] for w, mf in m.cruces_ganancia], ["ωc [rad/s] (|L|=1)", "margen de fase"], "   "))
    else:
        out.append("    |L| nunca cruza 0 dB: margen de fase infinito (no hay ωc).")
    if m.cruces_fase:
        out.append(_tabla([[f"{w:.5g}", f"{mg:.4g}  (×)", f"{db:.2f} dB"] for w, mg, db in m.cruces_fase],
                          ["ω180 [rad/s] (∠L=−180°)", "margen de ganancia", "en dB"], "   "))
    else:
        out.append("    La fase nunca llega a −180°: margen de ganancia infinito (no hay ω180).")
    if len(m.cruces_ganancia) > 1 or len(m.cruces_fase) > 1:
        out.append("    (Hay varios cruces: los valores principales son los de menor |margen|; con varios cruces verificar con Nyquist.)")
    if m.margen_retardo is not None:
        out.append(f"  Margen de retardo adicional: {m.margen_retardo:.4g} s")
    out.append(f"\n  Lazo cerrado T = L/(1+L):   Mr = {c.Mr:.4g} ({c.Mr_dB:.2f} dB) en ωr = {c.wr:.4g} rad/s"
               f"   |   ancho de banda (−3 dB) = {_n(c.BW)} rad/s")
    out.append(f"  Sensibilidad S = 1/(1+L):   Ms = {c.Ms:.4g} ({c.Ms_dB:.2f} dB) en {c.wMs:.4g} rad/s"
               f"   ->  MG ≥ {c.Ms / (c.Ms - 1):.3g} (×) y MF ≥ {np.degrees(2 * np.arcsin(1 / (2 * c.Ms))):.1f}°" if c.Ms > 1 else "")
    if met.estable:
        out.append("\n  Estimación del sobreimpulso desde la respuesta en frecuencia (modelo de 2.º orden):")
        filas = []
        if met.zeta_Mr is not None:
            filas.append(["carta de Nichols: Mr", f"Mr = {c.Mr_dB:.2f} dB", f"ζ ≈ {met.zeta_Mr:.3f}", f"Mp ≈ {met.Mp_Mr:.1f} %"])
        else:
            filas.append(["carta de Nichols: Mr", f"Mr = {c.Mr_dB:.2f} dB", "sin pico (ζ ≥ 0,707)", "Mp ≈ 0 %"])
        if met.zeta_MF is not None:
            filas.append(["margen de fase exacto (2.º orden)", f"MF = {m.MF:.1f}°", f"ζ ≈ {met.zeta_MF:.3f}", f"Mp ≈ {met.Mp_MF:.1f} %"])
            filas.append(["regla práctica ζ ≈ MF/100", f"MF = {m.MF:.1f}°", f"ζ ≈ {met.zeta_regla:.3f}", f"Mp ≈ {met.Mp_regla:.1f} %"])
        if met.escalon is not None and met.escalon.Mp is not None:
            filas.append(["SIMULACIÓN (escalón)", "—", "—", f"Mp = {met.escalon.Mp:.1f} %"])
        out.append(_tabla(filas, ["método", "dato", "amortiguamiento", "sobreimpulso"], "   "))
    return "\n".join(out)


def seccion_temporal(met, nombre: str = "", num: str = "4.") -> str:
    out = [_t(f"{num} RESPUESTA TEMPORAL" + (f" — {nombre}" if nombre else ""))]
    e = met.escalon
    if e is None:
        return "\n".join(out + ["  (no calculada)"])
    if not met.estable:
        out.append("  Lazo cerrado inestable: la respuesta diverge; no se calculan Mp, tr ni ts.")
        return "\n".join(out)
    out.append("  Escalón unitario:")
    out.append(_tabla([["valor final", _n(e.valor_final)], ["sobreimpulso Mp", f"{_n(e.Mp)} %"], ["instante del pico tp", f"{_n(e.tp)} s"],
                       ["tiempo de subida tr (10–90 %)", f"{_n(e.tr)} s"], ["tiempo de establecimiento ts (2 %)", f"{_n(e.ts)} s"],
                       ["tiempo de establecimiento ts (5 %)", f"{_n(e.ts5)} s"]], None, "   "))
    if e.nota:
        out.append(f"  Nota: {e.nota}")
    r = met.rampa
    if r is not None:
        out.append(f"  Rampa unitaria: error en régimen numérico = {_n(r.e_ss_numerico, '{:.4g}')} ; teórico 1/Kv = {_n(r.e_ss_teorico, '{:.4g}')}")
    return "\n".join(out)


def seccion_compensacion(especs: dict, kappa_msg: list[str], candidatos: list, reco, sis0_metricas) -> str:
    out = [_t("5. COMPENSACIÓN")]
    out.append("  Especificaciones: " + ", ".join(f"{k} = {v}" for k, v in especs.items() if v is not None))
    for m in kappa_msg:
        out.append("  " + m)
    if sis0_metricas is not None:
        f = sis0_metricas.fila()
        out.append(f"  Planta sin compensar: Kv = {_n(f['Kv'])}, MF = {_n(f['MF'], '{:.1f}')}°, MG = {_n(f['MG_dB'], '{:.2f}')} dB, "
                   + ("estable" if f["estable"] else "INESTABLE"))
    out.append("\n  Comparación de candidatos:")
    filas = []
    for d in candidatos:
        f = d.metricas.fila() if d.metricas else {}
        est = "—" if not d.exito else ("CUMPLE" if d.cumple else "no cumple")
        filas.append([d.tipo, est, _n(f.get("Kv")), _n(f.get("MF"), "{:.1f}") + "°" if f.get("MF") is not None else "—",
                      _n(f.get("MG_dB"), "{:.1f}") + " dB" if f.get("MG_dB") is not None else "—",
                      _n(f.get("Mp"), "{:.1f}") + " %" if f.get("Mp") is not None else "—",
                      _n(f.get("ts"), "{:.3g}") + " s" if f.get("ts") is not None else "—",
                      _n(f.get("wc"), "{:.3g}") if f.get("wc") is not None else "—"])
    out.append(_tabla(filas, ["diseño", "estado", "Kv", "MF", "MG", "Mp", "ts(2%)", "ωc"], "  "))
    for d in candidatos:
        out.append(_t(f"Diseño: {d.tipo}", 2))
        if not d.exito:
            for n in d.notas:
                out.append("  " + n)
            if d.iteraciones:
                out.append("  Iteraciones intentadas:")
                out.append(_iteraciones(d))
            continue
        out.append(f"  Compensador Gc(s) = {tf_a_texto(d.Gc, 'polos_ceros', 5)}")
        out.append(f"  (en polinomios)     {tf_a_texto(d.Gc, 'polinomios', 5)}")
        out.append("  Parámetros: " + _params(d))
        if d.iteraciones:
            out.append("  Iteraciones:")
            out.append(_iteraciones(d))
        if d.cumplimiento:
            out.append("  Verificación de especificaciones:")
            out.append(_tabla([[r["nombre"], r["requisito"], r["obtenido"], "?" if r["cumple"] is None else ("SÍ" if r["cumple"] else "NO")]
                               for r in d.cumplimiento], ["especificación", "pedido", "obtenido", "cumple"], "   "))
        for n in d.notas:
            out.append("  • " + n)
    out.append("\n" + LINEA)
    if reco is not None:
        out.append(f"  RECOMENDADO: {reco.tipo}   (cumple todas las especificaciones" +
                   (f"; ts = {reco.metricas.escalon.ts:.3g} s" if reco.metricas and reco.metricas.escalon and reco.metricas.escalon.ts else "") + ")")
        out.append(f"  Gc(s) = {tf_a_texto(reco.Gc, 'polos_ceros', 5)}")
    else:
        out.append("  Ningún candidato cumple todas las especificaciones. Probar: otro tipo de red, relajar una especificación,"
                   " o ajustar PARAMS_DISENO (delta, wc_nuevo, etapas).")
    return "\n".join(out)


def _fmt_val(v):
    if isinstance(v, (float, np.floating)):
        return f"{v:.5g}"
    return str(v)


def _params(d) -> str:
    claves = {"adelanto": ["kappa", "delta", "phim", "alfa", "T", "wm", "cero", "polo", "etapas"],
              "atraso": ["wc_nuevo", "beta", "T", "cero", "polo"],
              "atraso_adelanto": ["wc_nuevo", "phim", "alfa", "beta", "cero_adelanto", "polo_adelanto", "cero_atraso", "polo_atraso", "delta"],
              "PI": ["Kp", "Ti", "razon", "cero"]}.get(d.tipo, list(d.parametros))
    ps = dict(d.parametros)
    ps["kappa"] = d.kappa
    return ",  ".join(f"{k} = {_fmt_val(ps[k])}" for k in claves if k in ps and ps[k] is not None)


def _iteraciones(d, maximo: int = 10) -> str:
    claves = []
    for it in d.iteraciones:
        for k in it:
            if k not in claves and k not in ("nota",):
                claves.append(k)
    filas = [[_fmt_val(it.get(k, "")) if it.get(k) is not None else "" for k in claves] + [it.get("nota", "")] for it in d.iteraciones]
    if len(filas) > maximo:
        omitidas = len(filas) - maximo
        filas = filas[: maximo // 2] + [["…"] + [""] * (len(claves)) ] + filas[-(maximo - maximo // 2):]
        return _tabla(filas, claves + ["nota"], "  ") + f"\n    (se omitieron {omitidas} iteraciones intermedias)"
    return _tabla(filas, claves + ["nota"], "  ")


def generar_informe(secciones: list[str]) -> str:
    return "\n".join(secciones) + "\n"
