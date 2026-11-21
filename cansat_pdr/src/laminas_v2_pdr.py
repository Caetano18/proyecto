"""Presentacion PDR completa del equipo (plantilla de 106 laminas) con las laminas de estructura y de control de descenso
rellenas con el diseno v2 opcion B regulable (estaciones roscadas). Sin FEM.  En ingles, como el resto.

Laminas: 20-26 (configuracion y layout fisico), 48-52 (control de descenso), 53-57 (subsistema mecanico),
58-62 (presupuesto de masa).
Uso: python3 laminas_v2_pdr.py <presentacion_equipo.pptx> <salida.pptx>
"""
import os
import sys
import json
import math
from pptx import Presentation
import laminas_pdr as LP
from laminas_pdr import I, X0, X1, Y0, Y1, GAP, ROJO, tarjeta, tabla, panel, limpiar, subtitulo
import cg_v2 as CG

FEA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fea")
CGR = json.load(open(os.path.join(FEA, "cg_v2BR.json")))
DES = json.load(open(os.path.join(FEA, "descenso_v2.json")))
CAS = CGR["casos"]
WU = X1 - X0

# ------------------------------------------------------------ presupuesto de masa (con fuente e incertidumbre)
# item -> (grupo, incertidumbre en g, fuente)
FUENTE = {
    "Carena PETG 2 mm (240 mm, ranuras y canal)": ("S", 8.0, "CAD volume × PETG density"),
    "M1 fondo de nadir": ("S", 1.3, "Slicer, 40 % infill"), "M4 mamparo de cenit": ("S", 1.3, "Slicer, 40 % infill"),
    "M5 tapa de la copa": ("S", 1.3, "Slicer, 40 % infill"), "M2": ("S", 1.3, "Slicer, 40 % infill"),
    "M3": ("S", 1.3, "Slicer, 40 % infill"),
    "Varillas roscadas M3 Al 6061 (4)": ("S", 0.3, "Catalogue"), "Tuercas de los extremos (8, acero)": ("S", 0.2, "Catalogue"),
    "Tuercas de M1 y M4 (8, Al 7075)": ("S", 0.1, "Catalogue"), "Tuercas de M2 (8, Al 7075)": ("S", 0.1, "Catalogue"),
    "Tuercas de M3 (8, Al 7075)": ("S", 0.1, "Catalogue"), "Cuna en U (PETG)": ("S", 1.0, "CAD volume"),
    "Rieles de las placas": ("S", 0.8, "CAD volume"),
    "Paracaídas Ø226 + líneas": ("D", 0.5, "Fabric 35 g/m² + Kevlar"), "Resorte expulsor + horquilla y pasador": ("D", 1.0, "Estimate"),
    "Vela Rogallo plegada": ("D", 0.5, "Cut area + seams"), "Largueros CF + bisagras": ("D", 0.4, "CF tube + printed hinge"),
    "Pivotes: pernos M4, resortes, bloques": ("D", 0.8, "Catalogue + CAD"), "Cápsula de nicrom (PTFE)": ("D", 0.5, "Estimate"),
    "Paneles solares (2)": ("E", 0.4, "Datasheet"), "Baliza + batería propia": ("E", 1.5, "Estimate"),
    "Cámara de nadir": ("E", 0.5, "Datasheet"), "Cámara de cenit": ("E", 0.5, "Datasheet"),
    "Cableado y conectores": ("E", 4.0, "Estimate"), "Pack 2 × 18650": ("E", 1.0, "Datasheet (46 g per cell)"),
    "PCB principal": ("E", 1.0, "Estimate, populated FR4"), "Radio 915 MHz + antena": ("E", 0.5, "Datasheet"),
    "GNSS + antena": ("E", 0.5, "Datasheet"),
}
EN = {
    "Carena PETG 2 mm (240 mm, ranuras y canal)": "PETG fairing 2 mm (240 mm, slots, channel)",
    "M1 fondo de nadir": "Bulkhead M1 (nadir end)", "M4 mamparo de cenit": "Bulkhead M4 (zenith)",
    "M5 tapa de la copa": "M5 cup lid", "M2": "Bulkhead M2 (battery station)", "M3": "Bulkhead M3 (avionics station)",
    "Varillas roscadas M3 Al 6061 (4)": "Threaded rods M3 Al 6061 (4)", "Tuercas de los extremos (8, acero)": "End nuts (8, steel)",
    "Tuercas de M1 y M4 (8, Al 7075)": "Nuts at M1 and M4 (8, Al 7075)", "Tuercas de M2 (8, Al 7075)": "Nuts at M2 (8, Al 7075)",
    "Tuercas de M3 (8, Al 7075)": "Nuts at M3 (8, Al 7075)", "Cuna en U (PETG)": "Battery U cradle (PETG)",
    "Rieles de las placas": "Board rails (PETG)",
    "Paracaídas Ø226 + líneas": "Parachute Ø226 + lines", "Resorte expulsor + horquilla y pasador": "Lid spring, clevis and pin",
    "Vela Rogallo plegada": "Rogallo sail (ripstop)", "Largueros CF + bisagras": "CF spars + tip hinges",
    "Pivotes: pernos M4, resortes, bloques": "Spar pivots: M4 bolts, springs, blocks", "Cápsula de nicrom (PTFE)": "Nichrome capsule (PTFE)",
    "Paneles solares (2)": "Solar panels (2)", "Baliza + batería propia": "Beacon + own battery",
    "Cámara de nadir": "Nadir camera", "Cámara de cenit": "Zenith camera", "Cableado y conectores": "Wiring and connectors",
    "Pack 2 × 18650": "2 × 18650 pack", "PCB principal": "Main PCB", "Radio 915 MHz + antena": "Radio 915 MHz + antenna",
    "GNSS + antena": "GNSS + antenna",
}
ITEMS = [(n, m, x) + FUENTE[n] for n, m, x in CG.items()]
GR_NOM = {"S": "Structure", "D": "Descent and mechanisms", "E": "Electronics and payload"}


def suma(g=None):
    it = [t for t in ITEMS if g is None or t[3] == g]
    return sum(t[1] for t in it), math.sqrt(sum(t[4] ** 2 for t in it))


MTOT, UTOT = suma()
XN = CAS["nominal"]["x_cg"]


def n1(x, d=1):
    return f"{x:.{d}f}"


# ============================================================ SYSTEMS OVERVIEW
def L20_configA(sl):
    panel(sl, X0, Y0, I(6.0), Y1 - Y0, [("v2A_exterior_anot_en.png", 1), ("v2A_interior_anot_en.png", 1)],
          "Configuration A: printed monocoque, exterior and cut-away")
    x = X0 + I(6.0) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Configuration A: glued monocoque", [
        "**Integral CanSat:** one Ø90 × 240 body descends as a whole; it is its own container (smooth cylinder, no "
        "protrusions).",
        "**Structure:** 3D-printed PETG tube, 2 mm wall; bulkheads M1–M5 glued to the wall; the bridle is tied to four "
        "M3 eyebolts screwed into M4.",
        "**Descent, phase 1:** Ø226 flat parachute with Ø40 vent in the top cup, released by the lid spring at ejection.",
        "**Descent, phase 2 (80 % of apogee):** the nichrome cuts the Dyneema loop, the parachute is released and the "
        "Rogallo sail opens on two CF spars (torsion springs).",
        "**Weak points:** the glued joints carry all the loads; the electronics cannot be reached once glued.",
    ], sz=11, spc=280)


def L21_configB(sl):
    panel(sl, X0, Y0, I(6.0), Y1 - Y0, [("v2B_exterior_anot_en.png", 1), ("v2BR_interior_anot_en.png", 1)],
          "Configuration B: rod skeleton with threaded stations, exterior and cut-away")
    x = X0 + I(6.0) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Configuration B: rod skeleton + fairing", [
        "**Integral CanSat:** same envelope, descent sequence and release as A.",
        "**Structure:** four threaded M3 Al 6061 rods carry the loads from the bulkheads to the bridle; a 2 mm PETG "
        "fairing slides over the skeleton and is held by 6 screws.",
        "**Threaded stations:** each bulkhead is clamped between two nyloc nuts; M2 (battery module) and M3 (avionics "
        "module) move along the rods to trim the CG (0.5 mm per turn).",
        "**Access:** removing 6 screws, the whole skeleton slides out of the fairing.",
        "**Descent:** Ø226 flat parachute (phase 1) and passive Rogallo glider (phase 2).",
    ], sz=11, spc=280)


def L22_seleccion(sl):
    w1 = I(7.0)
    tabla(sl, X0, Y0, w1, [1.6, 1.6, 1.8], ["Criterion", "A: glued monocoque", "B: rod skeleton (selected)"], [
        ["Load path", "Bulkhead-to-wall bonds", "Rods, from each bulkhead to the bridle"],
        ["Delamination of the print", "Critical: the wall carries the loads across layers", "The fairing carries no load"],
        ["Integration and repair", "Closed once glued", "Skeleton slides out (6 screws)"],
        ["CG adjustment", "Not possible (glued)", "M2 and M3 move along the threads"],
        ["Mass", "Lighter (no rods)", "+18 g of rods, +5 g of nuts"],
        ["Manufacturing", "One long print, bonding on PETG", "Small parts, standard hardware"],
    ], sz=11, sz_cab=11.5, alto=I(0.52), alto_cab=I(0.38), col_sel=2, ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Selected: configuration B", [
        "**The rods carry the loads**, so the printed parts are never loaded across their layers.",
        "**The electronics can be reached** for integration, testing and repairs.",
        f"**The CG can be trimmed** after integration by moving the battery and avionics modules "
        f"({n1(CAS['todo abajo']['x_cg'])}–{n1(CAS['todo arriba']['x_cg'])} mm from the nadir end).",
        "The extra mass of the rods is the price; it is covered in the mass margin plan (page 59).",
    ], sz=12, spc=380)


def L23_dimensiones(sl):
    panel(sl, X0, Y0, I(8.6), Y1 - Y0, [("v2_dimensiones_en.png", 1)], "Dimensions in mm")
    x = X0 + I(8.6) + GAP
    S, b = DES["S_real"], 425
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Main dimensions", [
        "**Envelope (S2, S3):** Ø90 × 240 mm; 2 mm PETG wall; no part outside the cylinder when stowed.",
        "**Stations:** M1 x = 0, M2 x = 66–90 (nominal 83), M3 x = 156–177 (nominal 173), M4 x = 216, lid x = 236.",
        "**Slots:** 6 × 192 mm at ±35° from the top; dorsal channel 28 × 6 mm for the folded sail.",
        f"**Glider:** keel 190 mm, spars 225 mm at 52°, span {b} mm, planform area {S:.3f} m².",
        "There is no separate container: the body is the container.",
    ], sz=11, spc=300)


def L24_componentes(sl):
    panel(sl, X0, Y0, I(4.6), Y1 - Y0, [("v2BR_interior_anot_en.png", 1)], "Cut-away, nominal stations")
    x = X0 + I(4.6) + GAP
    tabla(sl, x, Y0, X1 - x, [1.5, 1.0, 2.6], ["Component", "Station x [mm]", "Location / mounting"], [
        ["Battery 2 × 18650", "37–79", "Bay 2, U cradle printed with M2 (moves with M2)"],
        ["Main PCB (MCU, IMU, baro)", "98–166", "Bay 3, rails hanging from M3"],
        ["GPS antenna (ceramic patch)", "148–166", "Upper board, facing the top; PETG is radio-transparent"],
        ["Radio 915 MHz + antenna", "120–143", "Upper board; helical antenna 21 mm"],
        ["Nadir camera", "6–14", "Bay 1, Ø14 window in M1"],
        ["Zenith camera", "196–212", "Bay 4, under M4, 35° above the flank, Ø10 window"],
        ["Beacon + battery", "6–20", "Bay 1, access hole ≤ 10 mm"],
        ["Actuator: nichrome capsule", "186–202", "Bay 4; cuts the Dyneema loop"],
        ["Solar panels (2)", "135–185", "Recessed in the flanks"],
    ], sz=10, sz_cab=10.5, alto=I(0.44), alto_cab=I(0.34), alin=["l", "c", "l"], ml=60000)


def L25_lanzamiento(sl):
    panel(sl, X0, Y0, I(6.4), Y1 - Y0, [("v2B_exterior_anot_en.png", 1), ("v2BR_interior_anot_en.png", 1)],
          "Launch configuration: exterior and cut-away")
    x = X0 + I(6.4) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Stowed parts", [
        "**Wing spars:** folded parallel to the axis inside the two 6 mm slots; the 40 mm tips fold inwards at the hinge.",
        "**Sail:** accordion-folded in the dorsal channel under a flush cover.",
        "**Retention:** one Dyneema loop holds both spar tips and the parachute release pin; it runs through the nichrome "
        "capsule (bay 4).",
        "**Parachute:** packed in the top cup under the lid; the ejection spring is compressed and the rocket wall holds "
        "the lid until ejection.",
        "**Envelope:** smooth Ø90 cylinder, no protrusions (S7).",
    ], sz=11, spc=280)


def L26_desplegado(sl):
    panel(sl, X0, Y0, I(8.0), Y1 - Y0, [("v2BR_fase1_anot_en.png", 0.7), ("v2BR_desplegado_anot_en.png", 1.6)],
          "Phase 1 under the parachute (left) and phase 2 gliding (right)")
    x = X0 + I(8.0) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Deployed configuration", [
        "**Phase 1:** after ejection the lid spring deploys the Ø226 parachute; the CanSat hangs from a 4-leg bridle "
        "tied to the rods and descends at about 15.5 m/s.",
        "**Phase 2 (80 % of apogee):** the nichrome melts the Dyneema loop: the release pin drops the parachute and the "
        "torsion springs open the spars to 52°, where a ratchet locks them.",
        "The sail inflates between the keel (dorsal channel) and the spars; the body hangs under the wing.",
    ], sz=11, spc=300)


# ============================================================ DESCENT CONTROL
def L48_descenso(sl):
    panel(sl, X0, Y0, I(7.0), Y1 - Y0, [("v2BR_secuencia_en.png", 1)], "Stowed, phase 1 and phase 2")
    x = X0 + I(7.0) + GAP
    tabla(sl, x, Y0, X1 - x, [1.0, 1.7, 1.3], ["Phase", "Device", "Descent rate"], [
        ["1 (C3)", "Flat parachute Ø226, Ø40 vent", "15.5 m/s at the site"],
        ["2 (C4)", "Rogallo sail, passive spiral", "5 ± 3 m/s target"],
    ], sz=10.5, sz_cab=11, alto=I(0.5), alto_cab=I(0.36), alin=["l", "l", "l"], ml=60000)
    y = Y0 + I(0.36) + 2 * I(0.5) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "Selected configuration", [
        "**Phase 1:** the lid spring deploys the parachute at ejection; no actuator.",
        "**Transition at 80 % of apogee:** one nichrome cut releases the parachute and frees the wing.",
        "**Phase 2:** the whole CanSat glides under the Rogallo sail in a fixed spiral (radius about 11 m); no servos.",
        "If the nichrome fails, the CanSat keeps descending under the parachute.",
    ], sz=11, spc=280)


def L49_paracaidas(sl):
    panel(sl, X0, Y0, I(7.6), Y1 - Y0, [("v2_paracaidas_en.png", 1)], "Two parachute designs and their descent rate")
    x = X0 + I(7.6) + GAP
    tabla(sl, x, Y0, X1 - x, [1.4, 1.2, 1.2], ["Parameter", "1A flat + vent", "1B cruciform"], [
        ["Cd0", "0.78", "0.68"],
        ["Fabric area S0", "386 cm²", "443 cm²"],
        ["Size", "Ø226, vent Ø40", "5 squares of 94 mm"],
        ["Lines", "8 Kevlar, 282 mm", "8 Kevlar, 282 mm"],
        ["Mass / volume", "8.0 g / 25 cm³", "9.5 g / 30 cm³"],
        ["Oscillation", "< ±8°", "±5°"],
        ["Rate at the site", "15.5 m/s", "15.5 m/s"],
    ], sz=10, sz_cab=10.5, alto=I(0.4), alto_cab=I(0.36), alin=["l", "c", "c"], ml=60000)
    y = Y0 + I(0.36) + 7 * I(0.4) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, None, [
        "Both sized for 15 m/s at sea level; with the site density (1.15 kg/m³) both give 15.5 m/s, inside C3.",
    ], sz=10.5, spc=200)


def L50_sel_paracaidas(sl):
    w1 = I(6.6)
    tabla(sl, X0, Y0, w1, [1.6, 1.4, 1.4, 0.8], ["Criterion", "1A flat + vent", "1B cruciform", "Weight"], [
        ["Meets C3 (15 ± 3 m/s)", "Yes, 15.5", "Yes, 15.5", "Must"],
        ["Mass", "8.0 g", "9.5 g", "High"],
        ["Packed volume in the 20 mm cup", "25 cm³", "30 cm³", "High"],
        ["Risk of tangling at ejection", "Low", "Higher (4 arms)", "High"],
        ["Pendulum oscillation", "< ±8° (vent)", "±5°", "Medium"],
        ["Manufacturing", "One cut, 8 gores", "5 squares, more seams", "Low"],
    ], sz=11, sz_cab=11.5, alto=I(0.5), alto_cab=I(0.38), col_sel=1, alin=["l", "c", "c", "c"], ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Selected: 1A, flat circular with central vent", [
        "**Lighter and smaller** packed, which matters in the 20 mm cup.",
        "**Lower risk of tangling** during the fast ejection from the rocket.",
        "The Ø40 vent spills the central vortex and keeps the swing under ±8°.",
        "With the site density it descends at 15.5 m/s; a Ø233 canopy would centre it at 15.0 m/s if the tests show "
        "it is needed.",
    ], sz=12, spc=380)


def L51_estrategias(sl):
    panel(sl, X0, Y0, I(6.0), Y1 - Y0, [("v2BR_desplegado_anot_en.png", 1)], "Rogallo glider, phase 2")
    x = X0 + I(6.0) + GAP
    tabla(sl, x, Y0, X1 - x, [1.3, 1.6, 1.6], ["", "A: passive spiral", "B: active steering"], [
        ["How it turns", "Asymmetric sail: +4 mm of billow on the left lobe, or stops at 53° / 51°",
         "Servo pulls a line on one spar (or shifts the keel) on command"],
        ["Path", "Fixed spiral, bank 25°, radius about 11 m", "Can steer toward a target"],
        ["Hardware", "None", "Servo, line, driver: about +22 g"],
        ["Software", "None", "Guidance law with GNSS and IMU"],
        ["Risk", "Spiral radius depends on the real sail", "Servo and line must survive 30 G"],
    ], sz=10, sz_cab=10.5, alto=I(0.62), alto_cab=I(0.36), alin=["l", "l", "l"], ml=60000)


def L52_sel_estrategia(sl):
    panel(sl, X0, Y0, I(6.2), Y1 - Y0, [("v2_planeo_en.png", 1)], "Glide descent rate vs. vortex lift and sail area")
    x = X0 + I(6.2) + GAP
    V = DES["vz"]
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Selected: A, passive spiral", [
        "**No servos and no moving parts in flight:** 22 g lighter and nothing to fail at 30 G.",
        "The spiral keeps the CanSat inside a circle of about 22 m.",
        f"**Descent rate:** v2 used S = 0.067 m²; the planform of the drawn sail is **{DES['S_real']:.3f} m²**. "
        f"With it the rate is {V['real']['1.0']:.1f} m/s with full vortex lift and {V['real']['0.5']:.1f} m/s with half; "
        f"[[{ROJO}:{V['real']['0.3']:.1f} m/s with 30 %, at the C4 limit]].",
        f"**Action for CDR:** enlarge the sail to about 0.068 m² (spars of about {DES['L_req']:.0f} mm, three segments) "
        f"to get {V['068']['0.5']:.1f} m/s with half vortex lift; confirm with drop tests of the sail.",
    ], sz=11, spc=300)


# ============================================================ MECHANICAL
def L53_mecanico(sl):
    w1 = I(7.0)
    tabla(sl, X0, Y0, w1, [1.6, 1.8, 1.7], ["Element", "Material", "Function"], [
        ["Fairing", "PETG, 2 mm wall (printed)", "Envelope, slots, dorsal channel"],
        ["Bulkheads M1–M5", "PETG, 40 % infill, 4 mm", "Carry the bays; stations"],
        ["Rods (4)", "Threaded M3 Al 6061", "Primary structure, bridle anchor"],
        ["Station nuts", "Nyloc M3 (Al 7075, steel at ends)", "Clamp each bulkhead; trim the CG"],
        ["Wing spars", "CF tube Ø4/2", "Leading edges of the sail"],
        ["Sail / parachute", "Ripstop nylon; Kevlar lines", "Phase 2 / phase 1"],
        ["Release", "Nichrome in PTFE capsule, Dyneema loop", "Phase 1 → 2 transition"],
    ], sz=10.5, sz_cab=11, alto=I(0.5), alto_cab=I(0.38), ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Mechanical configuration", [
        "**One integral body** (no separate container): skeleton of four threaded rods and five bulkheads inside a "
        "PETG fairing.",
        "**Five bays:** nadir camera and beacon; battery; avionics; zenith camera and release; parachute cup.",
        "**Adjustable stations:** M2 and M3 slide along the threads to trim the CG.",
        "**Mechanisms:** spar pivots with torsion springs and ratchet, nichrome release, lid ejection spring, parachute "
        "release pin.",
    ], sz=11.5, spc=330)


def L54_estructura(sl):
    panel(sl, X0, Y0, I(7.4), Y1 - Y0, [("v2A_interior_anot_en.png", 1), ("v2BR_interior_anot_en.png", 1)],
          "Structure A, glued monocoque (left), and B, rod skeleton with threaded stations (right)")
    x = X0 + I(7.4) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Two structures", [
        "**A:** the printed tube is the structure; bulkheads glued to the wall; bridle on M4 eyebolts. All loads cross "
        "the bonds and the print layers.",
        "**B (selected):** four M3 rods are the structure; bulkheads clamped by nuts; bridle on the rod ends. The "
        "fairing only closes the body.",
        "Both keep the same bays, stations and envelope, so the electronics layout is the same.",
    ], sz=11.5, spc=330)


def L55_electrica(sl):
    panel(sl, X0, Y0, I(4.6), Y1 - Y0, [("v2BR_interior_anot_en.png", 1)], "Electrical components inside the body")
    x = X0 + I(4.6) + GAP
    tabla(sl, x, Y0, X1 - x, [1.6, 0.8, 2.6], ["Component", "Bay", "Mounting"], [
        ["2 × 18650 pack (2S1P)", "2", "U cradle printed with M2; walls retain the cells sideways"],
        ["Main PCB: MCU, IMU, barometer, temperature, INA219", "3", "Lower rails hanging from M3"],
        ["GNSS module + ceramic antenna", "3", "Upper board, antenna facing the top"],
        ["Radio 915 MHz + helical antenna", "3", "Upper board"],
        ["Nadir camera", "1", "On M1, Ø14 window with polycarbonate lens"],
        ["Zenith camera", "4", "Bracket under M4, flank window"],
        ["Beacon, own battery and switch", "1", "Bay 1, access hole ≤ 10 mm"],
        ["Nichrome capsule + MOSFET", "4", "PTFE block; driven from the main PCB"],
        ["Solar panels (2)", "Flanks", "Recessed in the fairing"],
    ], sz=10, sz_cab=10.5, alto=I(0.44), alto_cab=I(0.34), alin=["l", "c", "l"], ml=60000)


def L56_mecanismos(sl):
    panel(sl, X0, Y0, I(6.4), Y1 - Y0, [("v2B_exterior_anot_en.png", 1), ("v2BR_detalle_anot_en.png", 1.5)],
          "Slots, pivots and hinges (left); threaded station of M2 (right)")
    x = X0 + I(6.4) + GAP
    tabla(sl, x, Y0, X1 - x, [1.5, 0.8, 2.2], ["Mechanism", "x [mm]", "What it does"], [
        ["Spar pivots (2)", "14", "M4 bolt, two AISI 302 torsion springs, stop and ratchet at 52°"],
        ["Spar tip hinges (2)", "199", "40 mm tips fold to fit the 192 mm slots"],
        ["Dyneema loop + nichrome", "186–202", "Holds the spar tips and the release pin until 80 % of apogee"],
        ["Lid ejection spring", "220–236", "Opens the cup and deploys the parachute at ejection"],
        ["Parachute release pin", "225", "Ø3 steel pin in double shear; the loop only holds it in place"],
        ["Threaded stations", "M2, M3", "Move the battery and avionics modules (0.5 mm per turn)"],
    ], sz=10, sz_cab=10.5, alto=I(0.56), alto_cab=I(0.34), alin=["l", "c", "l"], ml=60000)


def L57_seleccion_mec(sl):
    tabla(sl, X0, Y0, WU, [1.7, 2.2, 2.2, 2.4], ["Decision", "Selected", "Alternative", "Reason"], [
        ["Structure", "B: rod skeleton + fairing", "A: glued monocoque", "Rods carry the loads; access; CG trim"],
        ["Release actuator", "Nichrome in a closed PTFE capsule", "Micro servo", "12 g lighter, no gears to fail at 30 G, no pyro (M1)"],
        ["Wing opening", "Two torsion springs per spar + ratchet", "Elastic bands", "Known torque (405 N·mm open), locks at 52°"],
        ["Station fixing", "Nyloc nuts on both sides", "Glued or fixed bulkheads", "Moves the CG after integration"],
        ["Bulkheads with nuts", "Nuts turn, bulkhead slides", "Threaded bulkheads", "A bulkhead cannot turn on four rods at once"],
        ["Parachute anchor", "4-leg bridle to the rod ends", "Bridle to the lid", "The load goes straight into the rods"],
    ], sz=11, sz_cab=11.5, alto=I(0.55), alto_cab=I(0.38), col_sel=1, ml=70000)
    y = Y0 + I(0.38) + 6 * I(0.55) + I(0.17)
    tarjeta(sl, X0, y, WU, Y1 - y, None, [
        "All mechanisms are passive except the single nichrome cut; if it fails, the CanSat lands under the parachute.",
    ], sz=11, spc=200)


# ============================================================ MASS BUDGET
def filas_items(grupos):
    f = []
    for g in grupos:
        for n, m, x, gr, u, src in ITEMS:
            if gr == g:
                f.append([EN[n], n1(m), f"±{n1(u)}"])
    return f


def L58_componentes(sl):
    w = (WU - GAP) // 2
    izq = filas_items(["S"])
    der = filas_items(["D", "E"])
    tabla(sl, X0, Y0, w, [3.0, 0.8, 0.8], ["Structure", "Mass [g]", "±"], izq, sz=9, sz_cab=10, alto=I(0.265),
          alto_cab=I(0.3), alin=["l", "r", "r"], ml=50000, mt=20000)
    tabla(sl, X0 + w + GAP, Y0, w, [3.0, 0.8, 0.8], ["Descent, mechanisms and electronics", "Mass [g]", "±"], der, sz=9,
          sz_cab=10, alto=I(0.265), alto_cab=I(0.3), alin=["l", "r", "r"], ml=50000, mt=20000)


def L59_estructura(sl):
    w1 = I(6.6)
    f = filas_items(["S"])
    m, u = suma("S")
    f.append(["Structure total", n1(m), f"±{n1(u)}"])
    tabla(sl, X0, Y0, w1, [3.0, 0.8, 0.8], ["Structural element", "Mass [g]", "±"], f, sz=10, sz_cab=10.5, alto=I(0.3),
          alto_cab=I(0.32), alin=["l", "r", "r"], sub=(len(f) - 1,), ml=60000, mt=25000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Structure", [
        f"**{n1(m)} g**, {100 * m / MTOT:.0f} % of the CanSat.",
        "The fairing is the largest item (163 g): 240 mm of 2 mm PETG, the minimum printed wall of S6.",
        "Rods and nuts add 21 g; they are what allows the bulkheads to move.",
        "Bulkheads printed at 40 % infill (13.2 g each).",
    ], sz=11.5, spc=350)


def L60_incertidumbre(sl):
    w1 = I(7.4)
    filas = []
    for g in ("S", "D", "E"):
        m, u = suma(g)
        srcs = sorted({t[5] for t in ITEMS if t[3] == g})
        filas.append([GR_NOM[g], n1(m), f"±{n1(u)}", "; ".join(srcs)])
    filas.append(["Total (RSS)", n1(MTOT), f"±{n1(UTOT)}", ""])
    tabla(sl, X0, Y0, w1, [1.5, 0.7, 0.6, 3.4], ["Group", "Mass [g]", "± [g]", "Sources"], filas, sz=10, sz_cab=10.5,
          alto=I(0.62), alto_cab=I(0.36), alin=["l", "r", "r", "l"], sub=(3,), ml=60000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "How the uncertainty is set", [
        "**Datasheet / catalogue:** ±2–5 % (cells, cameras, rods, nuts).",
        "**CAD volume × density, slicer:** ±5–10 % (printed parts, the fairing at ±8 g).",
        "**Estimates:** ±10–20 % (wiring, beacon, PCB, capsule).",
        "The total uses the root sum of squares; the largest terms are the fairing and the wiring.",
        "All parts will be weighed on a 0.01 g scale before CDR.",
    ], sz=11, spc=320)


def L61_total(sl):
    w1 = I(6.0)
    filas = []
    for g in ("S", "D", "E"):
        m, u = suma(g)
        filas.append([GR_NOM[g], n1(m), f"±{n1(u)}"])
    filas.append(["CanSat total", n1(MTOT), f"±{n1(UTOT)}"])
    tabla(sl, X0, Y0, w1, [2.4, 1.0, 0.9], ["Group", "Mass [g]", "± (RSS)"], filas, sz=12, sz_cab=12, alto=I(0.5),
          alto_cab=I(0.4), alin=["l", "r", "r"], sub=(3,), ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Total mass and CG", [
        f"**Total: {n1(MTOT)} ± {n1(UTOT)} g** (S1: 500 ± 10 g).",
        f"**CG:** {n1(XN)} mm from the nadir end with nominal stations; moving M2 and M3 gives "
        f"{n1(CAS['todo abajo']['x_cg'])}–{n1(CAS['todo arriba']['x_cg'])} mm.",
        "The static margin of the sail stays positive over the whole range (3–19 %).",
        f"[[{ROJO}:The design is {MTOT - 510:.0f} g above the 510 g limit]]: correction plan on the next page.",
    ], sz=12, spc=380)


def L62_margen(sl):
    w1 = I(6.8)
    acc = [("Bulkhead infill 40 % → 25 %", -14.0, "v2 estimate"), ("Shorter wiring harness", -5.0, "v2 estimate"),
           ("Fairing 240 → 225 mm (S3 allows 200–250)", -10.2, "163 g × 15/240"),
           ("Beacon with a smaller cell", -5.0, "Estimate"), ("Lighter lid and spring", -3.0, "Estimate")]
    tot = sum(a[1] for a in acc)
    filas = [[a, f"{b:+.1f}".replace("-", "−"), c] for a, b, c in acc]
    filas.append(["Total of the corrections", f"{tot:+.1f}".replace("-", "−"), f"→ {MTOT + tot:.1f} g"])
    tabla(sl, X0, Y0, w1, [3.0, 0.8, 1.6], ["Correction", "Δ mass [g]", "Basis"], filas, sz=11, sz_cab=11.5, alto=I(0.5),
          alto_cab=I(0.38), alin=["l", "r", "l"], sub=(len(filas) - 1,), ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Margin", [
        f"Margin = 500 − {n1(MTOT)} = [[{ROJO}:{500 - MTOT:+.1f} g]]; to the 510 g limit: "
        f"[[{ROJO}:{510 - MTOT:+.1f} g]].",
        f"With the corrections: {MTOT + tot:.0f} g, inside 500 ± 10 g.",
        "**Final trim:** with the stations (CG) and steel washers on the rods (mass), after weighing the real parts.",
        "The rods stay in aluminium: carbon rods (v2 option, −10 g) cannot be threaded for the stations.",
    ], sz=11.5, spc=330)


TRABAJO = {20: L20_configA, 21: L21_configB, 22: L22_seleccion, 23: L23_dimensiones, 24: L24_componentes,
           25: L25_lanzamiento, 26: L26_desplegado, 48: L48_descenso, 49: L49_paracaidas, 50: L50_sel_paracaidas,
           51: L51_estrategias, 52: L52_sel_estrategia, 53: L53_mecanico, 54: L54_estructura, 55: L55_electrica,
           56: L56_mecanismos, 57: L57_seleccion_mec, 58: L58_componentes, 59: L59_estructura, 60: L60_incertidumbre,
           61: L61_total, 62: L62_margen}
ESPERADO = {20: "Configuration A", 21: "Configuration B", 22: "Selection and rationale", 23: "Dimensions",
            24: "Placement of Major", 25: "Launch Configuration", 26: "Deployed Configuration",
            48: "Descent Control Subsystem Overview", 49: "parachute design", 50: "Selection", 51: "Para-glider steering",
            52: "Selection", 53: "Mechanical Subsystem Overview", 54: "Structure of payload", 55: "electrical components",
            56: "mechanisms", 57: "Selection", 58: "Mass of all components", 59: "structural elements",
            60: "Sources or uncertainties", 61: "Total Mass", 62: "Margin"}


def main(entrada, salida, formato=True):
    prs = Presentation(entrada)
    sl = prs.slides
    for k, t in ESPERADO.items():
        st = subtitulo(sl[k - 1])
        assert st is not None and t.lower() in st.text_frame.text.lower(), (k, st.text_frame.text if st else None)
    for k, fn in TRABAJO.items():
        limpiar(sl[k - 1])
        fn(sl[k - 1])
    if formato:                 # formato clasico de la competencia; sin el, queda el estilo propio del equipo
        import formato_cansat
        formato_cansat.aplicar(prs)
    prs.save(salida)
    print("ok:", salida, len(prs.slides), "laminas;", len(TRABAJO), "rellenas")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], formato="--estilo-equipo" not in sys.argv)
