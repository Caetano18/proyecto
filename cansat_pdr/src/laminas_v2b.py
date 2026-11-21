"""Laminas en la plantilla del PDR (mismo modelo y formato que las del principio): estructura v2, opcion B con estaciones
roscadas para ajustar el CG, y FEM del impulso de 30 G (prueba de caida).  En ingles, como el resto de la presentacion.

Uso: python3 laminas_v2b.py <presentacion_equipo.pptx> <salida.pptx>
Lee ../fea/cg_v2BR.json y ../fea/caida_v2_ABBR.json, y las figuras *_en.png de ../figs.
"""
import os
import sys
import json
from pptx import Presentation
from pptx.oxml.ns import qn
import laminas_pdr as LP
from laminas_pdr import I, X0, X1, Y0, Y1, GAP, tarjeta, tabla, panel, limpiar, subtitulo, seccion, badge, poner_texto_run
import cg_v2 as CG

FEA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fea")
CGR = json.load(open(os.path.join(FEA, "cg_v2BR.json")))
RES = {r["var"]: r for r in json.load(open(os.path.join(FEA, "caida_v2_ABBR.json")))}
CAS = CGR["casos"]


def n1(x, d=1):
    return f"{x:.{d}f}"


def minimo(r):
    return min(r["piezas"].items(), key=lambda kv: kv[1]["G_rot_p999"])


def pieza_en(n):
    if n.startswith("Adhesivo"):
        return n.split()[-1] + " bond to the wall"
    if n.startswith("CT1"):
        return "PETG wall"
    if n.startswith("Cuna"):
        return "battery cradle"
    if n.startswith("Varilla"):
        return "rods"
    if n.startswith("Cancamo"):
        return "eyebolts"
    return "bulkhead " + n[:2]


NA, PA = minimo(RES["A"])
NB, PB = minimo(RES["B"])
NR, PR = minimo(RES["BR"])


def L_trade(sl):
    wi = I(5.7)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("v2A_interior_anot_en.png", 1), ("v2B_interior_anot_en.png", 1)],
          "Option A (left) and option B (right) of the team's v2 design, cut away")
    x = X0 + wi + GAP
    tabla(sl, x, Y0, X1 - x, [1.45, 1.55, 1.55], ["Criterion", "A: glued monocoque", "B: M3 rod skeleton"], [
        ["Load path in the drop test", "Everything hangs from the M4 bond", "The rods carry the load to the bridle"],
        ["Failure in the drop test (FEM)", f"{PA['G_rot_p999']:.0f} G ({pieza_en(NA)})", f"{PB['G_rot_p999']:.0f} G ({pieza_en(NB)})"],
        ["Access to electronics", "Closed once glued", "Skeleton slides out (6 screws)"],
        ["CG adjustment", "No (glued bulkheads)", "Yes: threaded stations"],
        ["Main uncertainty", "Bond strength on PETG (2–6 MPa)", "Nuts loosening (nyloc + paint mark)"],
    ], sz=10, sz_cab=10.5, alto=I(0.46), alto_cab=I(0.36), col_sel=2, ml=70000)
    y = Y0 + I(0.36) + 5 * I(0.46) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Selection: option B", [
        "Both options are in the v2 trade study; v2 chose B qualitatively. The drop-test FEM confirms it: B fails at "
        f"**{PB['G_rot_p999']:.0f} G**, A at **{PA['G_rot_p999']:.0f} G**.",
        "B also allows the CG to be trimmed by moving the heavy modules along the rods (next slide).",
    ], sz=11, spc=300)


def L_estaciones(sl):
    wi = I(4.3)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("v2BR_interior_anot_en.png", 1)], "Adjustable option B, nominal stations")
    x = X0 + wi + GAP
    hd = I(2.15)
    panel(sl, x, Y0, X1 - x, hd, [("v2BR_detalle_anot_en.png", 1)])
    y = Y0 + hd + I(0.15)
    w2 = (X1 - x - GAP) // 2
    tarjeta(sl, x, y, w2, Y1 - y, "Threaded stations", [
        "The four M3 rods are threaded along their full length; each bulkhead is clamped between two nyloc nuts.",
        "**1 turn of the nuts = 0.5 mm** of station travel.",
        "A bulkhead with threaded holes cannot turn on four parallel rods at once: the nuts turn, the bulkhead slides.",
        f"32 nuts (steel at the ends, Al 7075 nyloc at the stations): about +5 g over v2.",
    ], sz=10, spc=200)
    tabla(sl, x + w2 + GAP, y, X1 - x - w2 - GAP, [1.25, 0.8, 1.0, 1.0],
          ["Module", "Mass", "Nominal", "Travel"], [
              ["Battery (M2 + U cradle + pack)", f"{CGR['m_bateria']:.0f} g", f"x = {CG.NOM2:.0f}", f"{CG.RANGO2[0]:.0f}–{CG.RANGO2[1]:.0f} mm"],
              ["Avionics (M3 + rails + boards)", f"{CGR['m_avionica']:.0f} g", f"x = {CG.NOM3:.0f}", f"{CG.RANGO3[0]:.0f}–{CG.RANGO3[1]:.0f} mm"],
              ["M1, M4 (pivots, cup, bridle)", "—", "fixed", "—"],
          ], sz=10, sz_cab=10.5, alto=I(0.52), alto_cab=I(0.34), alin=["l", "r", "c", "c"], ml=60000)


def L_cg(sl):
    wi = I(7.0)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("v2BR_posiciones_en.png", 1)], "Extreme and nominal positions, CG marked")
    x = X0 + wi + GAP
    filas = []
    for k, t in (("todo abajo", "All toward nadir"), ("bateria abajo", "Battery toward nadir"), ("nominal", "Nominal"),
                 ("bateria arriba", "Battery toward zenith"), ("todo arriba", "All toward zenith")):
        v = CAS[k]
        filas.append([t, f"{v['x_m2']:.0f}", f"{v['x_m3']:.0f}", n1(v["x_cg"]), f"{100 * v['ME'][0]:.0f}–{100 * v['ME'][1]:.0f} %"])
    tabla(sl, x, Y0, X1 - x, [1.75, 0.6, 0.6, 0.75, 0.95], ["Position", "M2 x", "M3 x", "CG x", "Static margin"], filas,
          sz=10, sz_cab=10, alto=I(0.36), alto_cab=I(0.34), alin=["l", "c", "c", "c", "c"], resaltar=(2,), ml=60000)
    y = Y0 + I(0.34) + 5 * I(0.36) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Reading", [
        f"Mass {CGR['masa']:.0f} g; nominal CG at **{n1(CAS['nominal']['x_cg'])} mm** from the nadir end. Moving both "
        f"modules sweeps the CG over {n1(CAS['todo abajo']['x_cg'])}–{n1(CAS['todo arriba']['x_cg'])} mm.",
        f"Trim rule: Δx module = (m total / m module) · Δx CG = **{CGR['masa'] / CGR['m_bateria']:.1f} mm of battery travel per mm of CG**.",
        "Static margin stays positive (neutral point at 55–67 % of the 190 mm keel); moving the modules toward nadir "
        "always increases it. The v2 target (95–105 mm) is only reached with both modules down.",
    ], sz=10, spc=250)


def L_fem_modelo(sl):
    wi = I(7.6)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("v2BR_fem_modelo_en.png", 1)], "FE model of the adjustable option B for the drop test")
    x = X0 + wi + GAP
    r = RES["BR"]
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "30 G impulse: drop test", [
        "**Test:** non-elastic 61 cm cord tied to the parachute; the CanSat is released and the cord stops it: about 30 G "
        "along the axis.",
        "**Support:** the CanSat hangs from the bridle; the rod ends (anchors) are fixed in x, y, z.",
        f"**Load:** inertia toward nadir, {r['masa_real']:.0f} g (CanSat without the parachute); the 92 g pack sits in the "
        "M2 cradle, the avionics on M3.",
        f"**Pulse:** half-sine of 30 G, {r['T_pulso_ms']:.0f} ms (cord as a spring, with rebound). First axial mode "
        f"{'above ' if r.get('f_axial_cota') else ''}{r['f_axial']:.0f} Hz, so the dynamic factor is {r['DAF']:.2f} "
        f"(worst duration {r['DAF_peor']:.2f}).",
        "**Failure criterion:** no safety factor; printed PETG checked in plane and across layers "
        "(PETG 45/25 MPa, 40 % infill 20/11 MPa, Al 6061 310 MPa).",
    ], sz=10.5, spc=280)


def L_fem_resultados(sl):
    wi = I(6.6)
    panel(sl, X0, Y0, wi, Y1 - Y0, [("v2_caida_rotura_3_en.png", 1)], "Pulse peak that breaks each part (99.9th percentile)")
    x = X0 + wi + GAP
    filas = []
    for v, nom in (("A", "A: glued monocoque"), ("B", "B: rod skeleton"), ("BR", "Adjustable B")):
        n_, p_ = minimo(RES[v])
        filas.append([nom, pieza_en(n_), f"{p_['G_rot_p999']:.0f} G", f"× {p_['G_rot_p999'] / 30:.1f}"])
    tabla(sl, x, Y0, X1 - x, [1.4, 1.5, 0.8, 0.7], ["Option", "First part to fail", "Failure", "vs 30 G"], filas,
          sz=10.5, sz_cab=10.5, alto=I(0.42), alto_cab=I(0.36), alin=["l", "l", "r", "r"], resaltar=(2,), ml=60000)
    y = Y0 + I(0.36) + 3 * I(0.42) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Result", [
        "**All three options survive the 30 G drop test.**",
        f"A: everything hangs from the M4 bond; it fails at {PA['G_rot_p999']:.0f} G and depends on the bond strength on PETG.",
        f"B: the rods carry the load; the weakest part is a bulkhead at {PB['G_rot_p999']:.0f} G.",
        f"Adjustable B: the pack hangs from M2; minimum {PR['G_rot_p999']:.0f} G ({pieza_en(NR)}), "
        f"{PR['G_rot_p999'] / 30:.0f} times the test load.",
    ], sz=10.5, spc=280)


def L_fem_mapas(sl):
    panel(sl, X0, Y0, X1 - X0, I(3.55), [("v2_caida_mapas_3_en.png", 1)],
          "Fraction of failure at 30 G (σ / σ_ult, no safety factor), cut along the mid plane")
    y = Y0 + I(3.55) + I(0.15)
    tarjeta(sl, X0, y, X1 - X0, Y1 - y, None, [
        "Highest values: in A, the bond and the bulkhead around the eyebolts in M4; in B, the holes where the rods load the "
        "bulkheads. Elements within 4 mm of the anchors are excluded (load introduction).",
    ], sz=10.5, spc=200)


def L_pendientes(sl):
    tabla(sl, X0, Y0, X1 - X0, [1.6, 3.4, 3.0], ["Open item", "Why", "How it closes"], [
        ["Mass (S1)", f"{CGR['masa']:.0f} g recalculated, above the 510 g limit", "Lower bulkhead infill, shorter fairing, review electronics masses"],
        ["Sander test", "With the 2 mm PETG fairing the first lateral mode falls inside 0–233 Hz (MS −0.55)", "Laminated shell (memo v3) or a stiffer fairing"],
        ["Sail area", "With the 190 mm keel and 225 mm spars at 52° the area is 0.045 m², not 0.067 m²", "Resize the sail or check the v2 area definition"],
        ["CG within the v2 range", f"Nominal {n1(CAS['nominal']['x_cg'])} mm; with both modules down {n1(CAS['todo abajo']['x_cg'])} mm", "Measure the real CG, trim, glide tests"],
        ["Nuts loosening", "Sander and flight vibration", "Nyloc nuts + paint mark; inspect after each test"],
        ["Thermal test (60 °C)", "PETG loses stiffness close to 60 °C", "2 h test with the integrated structure"],
        ["Lateral shock", "Only the axial drop was checked", "30 G lateral case (landing) with the same model"],
    ], sz=10.5, sz_cab=11, alto=I(0.5), alto_cab=I(0.36), ml=70000)


LAMINAS = [(L_trade, "Structure Trade: Option A vs. Option B"),
           (L_estaciones, "Option B with Adjustable (Threaded) Stations"),
           (L_cg, "CG Adjustment with the Battery and Avionics Modules"),
           (L_fem_modelo, "FEM: 30 G Impulse (Drop Test) – Model"),
           (L_fem_resultados, "FEM: 30 G Impulse – Failure Load of Each Part"),
           (L_fem_mapas, "FEM: 30 G Impulse – Stress Maps"),
           (L_pendientes, "Open Items")]


def main(entrada, salida):
    prs = Presentation(entrada)
    n0 = len(prs.slides)
    st = subtitulo(prs.slides[56])
    assert st is not None and "selection" in st.text_frame.text.lower(), st.text_frame.text if st else None
    for k, (fn, tit) in enumerate(LAMINAS):
        s = LP.duplicar(prs, 56 + k, 2 + k)          # la 57 (contenido mecanico) se corre k lugares al insertar
        limpiar(s)
        poner_texto_run(subtitulo(s), tit)
        rs = seccion(s).text_frame.paragraphs[0].runs
        rs[-1].text = " - Structure (option B)"
        fn(s)
    nl = len(LAMINAS)
    conservar = {0, 1, n0 + nl - 1} | set(range(2, 2 + nl))
    lst = prs.slides._sldIdLst
    for i, sld in enumerate(list(lst)):
        if i not in conservar:
            prs.part.drop_rel(sld.get(qn("r:id")))
            lst.remove(sld)
    for i, s in enumerate(prs.slides, 1):
        b = badge(s)
        if b is not None and b.text_frame.text.strip().isdigit():
            poner_texto_run(b, str(i - 2))
    import formato_cansat
    formato_cansat.aplicar(prs)
    prs.save(salida)
    print("ok:", salida, len(prs.slides), "laminas")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
