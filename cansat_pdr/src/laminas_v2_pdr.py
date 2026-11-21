"""Presentacion PDR del equipo (106 laminas) con las laminas de estructura y de control de descenso rellenas.
Diseno: cuerpo integral, esqueleto de 4 varillas M3 roscadas con estaciones regulables (bateria y avionica), carena
de PETG, paracaidas plano de ripstop, vela Rogallo con un lobulo mas chico para virar (flecha fija), despliegue con
tres micro servos (tapa, paracaidas y ala), sin resortes.  Formato de los PDR de referencia en variante neutra.  En ingles, como el resto.

Laminas: 20-26 (configuracion y layout fisico), 48-52 (control de descenso), 53-57 (subsistema mecanico),
58-62 (presupuesto de masa).
Uso: python3 laminas_v2_pdr.py <presentacion_equipo.pptx> <salida.pptx>   (estilo del equipo)
"""
import os
import sys
import json
import math
from pptx import Presentation
from laminas_pdr import I, X0, X1, Y0, Y1, GAP, tarjeta, tabla, panel, limpiar, subtitulo
import cg_v2 as CG

FEA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fea")
CGR = json.load(open(os.path.join(FEA, "cg_v2BR.json")))
DES = json.load(open(os.path.join(FEA, "descenso_v2.json")))
CAS = CGR["casos"]
WU = X1 - X0
APOGEO = 673.0                    # simulacion del vector (documento de la competencia)
V1 = 15.5                         # fase 1 con la densidad del sitio

# ------------------------------------------------------------ presupuesto de masa
# item -> (grupo, incertidumbre [g], fuente, nombre en ingles)
FUENTE = {
    "Carena PETG 2 mm (240 mm, ranuras y canal)": ("S", 8.0, "CAD volume × PETG density", "PETG fairing, 2 mm wall, 240 mm"),
    "M1 fondo de nadir (25 % de relleno)": ("S", 1.0, "Slicer, 25 % infill", "Bulkhead M1 (nadir end)"),
    "M4 mamparo de cenit (25 % de relleno)": ("S", 1.0, "Slicer, 25 % infill", "Bulkhead M4 (bridle anchor)"),
    "M5 tapa de la copa (2 mm con nervios)": ("S", 0.7, "Slicer", "Cup lid M5 (2 mm, ribbed)"),
    "M2 (25 % de relleno)": ("S", 1.0, "Slicer, 25 % infill", "Bulkhead M2 (battery station)"),
    "M3 (25 % de relleno)": ("S", 1.0, "Slicer, 25 % infill", "Bulkhead M3 (avionics station)"),
    "Varillas roscadas M3 Al 6061 (4)": ("S", 0.3, "Catalogue", "Threaded rods M3, Al 6061 (4)"),
    "Tuercas de los extremos (8, Al 7075)": ("S", 0.1, "Catalogue", "End nuts (8, Al 7075)"),
    "Tuercas de M1 y M4 (8, Al 7075)": ("S", 0.1, "Catalogue", "Nuts at M1 and M4 (8, Al 7075)"),
    "Tuercas de M2 (8, Al 7075)": ("S", 0.1, "Catalogue", "Nuts at M2 (8, Al 7075)"),
    "Tuercas de M3 (8, Al 7075)": ("S", 0.1, "Catalogue", "Nuts at M3 (8, Al 7075)"),
    "Cuna en U (PETG, paredes de 2 mm)": ("S", 0.7, "CAD volume", "Battery U cradle (PETG)"),
    "Rieles de las placas": ("S", 0.8, "CAD volume", "Board rails (PETG)"),
    "Paracaídas Ø226 ripstop + líneas": ("D", 0.5, "Ripstop nylon 35 g/m² + Kevlar lines", "Parachute Ø226, ripstop nylon + lines"),
    "Horquilla, pasador con PTFE y 2 anillos": ("D", 0.4, "Estimate", "Two-ring release, PTFE-sleeved pin, clevis"),
    "Servo de la tapa SG90 + traba": ("D", 0.5, "Datasheet (SG90, 9 g)", "Lid servo SG90 + latch"),
    "Vela Rogallo plegada": ("D", 1.5, "Cut area + seams + keel strip", "Rogallo sail, ripstop nylon"),
    "Largueros CF Ø4/3 + punteras plegables + bisagras": ("D", 1.0, "CF tube length × catalogue + fittings", "CF spars Ø4/3 + folding tips, hinges, latches"),
    "Pivotes: ejes M4 de Al 7075, manivelas y bloques": ("D", 0.5, "Catalogue + CAD", "Spar pivots: Al 7075 M4 shafts, cranks, blocks"),
    "Servo de liberación del paracaídas SG90 + varilla": ("D", 0.5, "Datasheet (SG90, 9 g)", "Parachute release servo SG90 + rod"),
    "Servo del ala SG90 + bocina y 2 bielas": ("D", 0.5, "Datasheet (SG90, 9 g) + CAD", "Wing servo SG90 + horn and two links"),
    "Panel solar (1)": ("E", 0.4, "Datasheet", "Solar panel (1)"),
    "Baliza piezo + pila propia": ("E", 1.0, "Estimate", "Beacon: piezo + CR2032 cell"),
    "Cámara de nadir": ("E", 1.0, "Estimate (module + microSD + mount)", "Nadir camera ESP32-CAM"),
    "Cámara de cenit": ("E", 1.0, "Estimate (module + microSD + mount)", "Zenith camera ESP32-CAM"),
    "Cableado y conectores (arnés corto)": ("E", 3.0, "Estimate", "Wiring and connectors"),
    "Pack 2 × 18650 (2200 mAh)": ("E", 1.0, "Battery selection (44.5 g max per cell)", "Battery 2 × 18650, 2S1P 2200 mAh"),
    "PCB principal": ("E", 1.0, "Estimate, populated FR4", "Main PCB (ESP32, sensors, RTC)"),
    "Radio LoRa RFM95W 920 MHz + antena": ("E", 1.0, "Estimate (breakout + λ/4 wire monopole)", "LoRa radio RFM95W 920 MHz + antenna"),
    "GNSS u-blox NEO-7M + antena": ("E", 0.5, "Datasheet", "GNSS u-blox NEO-7M + patch antenna"),
}
REDUCCION_EN = [  # mismo orden que CG.REDUCCION
    "Bulkheads M1–M4 printed at 25 % infill (instead of 40 %)",
    "Cup lid M5 of 2 mm with ribs (instead of 4 mm solid)",
    "One solar panel (E3 asks for at least one)",
    "Smaller beacon with its own CR2032 cell",
    "Shorter wiring harness",
    "Battery cradle with 2 mm walls",
    "End nuts in Al 7075 (instead of steel)",
    "Pivot shafts in Al 7075 (instead of steel)",
]
assert len(REDUCCION_EN) == len(CG.REDUCCION)
ITEMS = [(n, m, x) + FUENTE[n] for n, m, x in CG.items()]
GR_NOM = {"S": "Structure", "D": "Descent and mechanisms", "E": "Electronics and payload"}
GR_FUENTE = {"S": "CAD volume × PETG density, slicer (printed parts); catalogue (rods, nuts)",
             "D": "Fabric area × ripstop density (sail, parachute); catalogue and datasheets (spars, servos); "
                  "estimate (links, pin)",
             "E": "Battery selection; datasheets (GNSS, panel); estimate (cameras, radio, main PCB, wiring, beacon)"}


def suma(g=None):
    it = [t for t in ITEMS if g is None or t[3] == g]
    return sum(t[1] for t in it), math.sqrt(sum(t[4] ** 2 for t in it))


MTOT, UTOT = suma()


def n1(x, d=1):
    return f"{x:.{d}f}"


def rango_cg():
    return f"{n1(CAS['todo abajo']['x_cg'])}–{n1(CAS['todo arriba']['x_cg'])} mm"


def me_rango():
    lo = min(v["ME"][0] for v in CAS.values())
    hi = max(v["ME"][1] for v in CAS.values())
    return f"{100 * lo:.0f}–{100 * hi:.0f} %"


VZ = DES["vz"]
T2 = 0.8 * APOGEO / VZ["nom"]
T1 = 0.2 * APOGEO / V1


# ============================================================ SYSTEMS OVERVIEW
def L20_configA(sl):
    panel(sl, X0, Y0, I(6.0), Y1 - Y0, [("v2A_exterior_anot_en.png", 1), ("v2A_interior_anot_en.png", 1)],
          "Configuration A: printed monocoque, exterior and cut-away", misma_escala=True)
    x = X0 + I(6.0) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Configuration A: printed monocoque", [
        "**Integral CanSat, Ø90 × 240 mm (S2, S3):** a single body that is also its own container and slides freely "
        "out of the rocket bay (S7).",
        "**Structure:** 3D-printed PETG tube with a 2 mm wall (S6); the bulkheads are bonded to the wall and the bridle "
        "is tied to four M3 eyebolts in the top bulkhead.",
        "**Phase 1 (C3):** when the breakwire detects the separation (X3), a servo releases the lid of the top cup; the lid, "
        "tied to the flat ripstop-nylon parachute, pulls it out.",
        "**Phase 2 (C4):** at 80 % of apogee a servo releases the parachute and the wing servo opens a "
        "Rogallo sail on two carbon spars.",
    ], sz=11, spc=300)


def L21_configB(sl):
    panel(sl, X0, Y0, I(6.0), Y1 - Y0, [("v2B_exterior_anot_en.png", 1), ("v2BR_interior_anot_en.png", 1)],
          "Configuration B: rod skeleton with threaded stations, exterior and cut-away", misma_escala=True)
    x = X0 + I(6.0) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Configuration B: rod skeleton and fairing", [
        "**Same envelope and descent sequence** as configuration A.",
        "**Structure:** four threaded aluminium rods (M3 thread) carry the loads from every bulkhead to the bridle; a 2 mm PETG "
        "fairing closes the body and is held by six screws.",
        "**Threaded stations:** each bulkhead is clamped between two nyloc nuts. The battery module (M2) and the "
        "avionics module (M3) slide along the rods to set the centre of gravity: one turn of the nuts moves them 0.5 mm.",
        "**Integration:** with the six screws out, the whole skeleton slides out of the fairing.",
    ], sz=11, spc=300)


def L22_seleccion(sl):
    w1 = I(7.0)
    tabla(sl, X0, Y0, w1, [1.6, 1.6, 1.8], ["Criterion", "A: printed monocoque", "B: rod skeleton"], [
        ["Load path", "Bonded bulkhead-to-wall joints", "Rods, from each bulkhead to the bridle"],
        ["Printed layers", "The wall is loaded across its layers", "The fairing carries no structural load"],
        ["Integration and repair", "Closed once bonded", "Skeleton slides out (six screws)"],
        ["Centre of gravity", "Set by the design", "Adjustable after integration"],
        ["Mass", "Lighter: no rods", "Rods and nuts add about 20 g"],
        ["Manufacturing", "One long print and bonding", "Small prints and standard hardware"],
    ], sz=11, sz_cab=11.5, alto=I(0.52), alto_cab=I(0.38), col_sel=2, ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Selected: configuration B", [
        "The rods take the drop-test and launch loads, so no printed part is loaded across its layers.",
        "The electronics stay accessible for integration, environmental tests and repairs.",
        f"The battery and avionics modules can be moved after weighing the real parts; the CG can be set anywhere "
        f"between {rango_cg()} from the nadir end.",
        f"The rods fit in the mass budget: {MTOT:.0f} g in total (S1).",
    ], sz=12, spc=380)


def L23_dimensiones(sl):
    panel(sl, X0, Y0, I(8.6), Y1 - Y0, [("v2_dimensiones_en.png", 1)], "Dimensions in mm")
    x = X0 + I(8.6) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Main dimensions", [
        "**Envelope:** Ø90 × 240 mm (S2, S3); nothing protrudes from the cylinder when stowed; fits the Ø100 mm "
        "launch vehicle within its ±1 mm tolerance.",
        "**Stations:** M1 at x = 0; M2 adjustable 66–90 mm; M3 adjustable 156–177 mm; M4 at 216; lid at 236.",
        "**Wing stowage:** two 6 × 192 mm slots and a 28 × 6 mm dorsal channel.",
        f"**Glider:** keel 190 mm; spars at 60° from the keel with 5° dihedral, right 350 mm and left 310 mm (185 mm + folding tip); sail "
        f"{DES['S']:.3f} m².",
    ], sz=11, spc=300)


def L24_componentes(sl):
    panel(sl, X0, Y0, I(4.6), Y1 - Y0, [("v2BR_interior_anot_en.png", 1)], "Cut-away, nominal stations")
    x = X0 + I(4.6) + GAP
    tabla(sl, x, Y0, X1 - x, [1.5, 1.0, 2.6], ["Component", "Station x [mm]", "Location and mounting"], [
        ["Battery 2 × 18650", "41–79", "Bay 2, U cradle printed with M2; moves with M2"],
        ["Main PCB (ESP32, IMU, barometer)", "98–166", "Bay 3, rails hanging from M3"],
        ["GNSS u-blox NEO-7M", "146–168", "Upper board, patch facing the dorsal side (sky in glide)"],
        ["LoRa radio RFM95W, 920 MHz", "120–146", "Upper board, λ/4 monopole"],
        ["Nadir camera ESP32-CAM", "6–14", "Bay 1, Ø14 window in M1"],
        ["Zenith camera ESP32-CAM", "192–213", "Bay 4, under M4, window in the flank"],
        ["Beacon with its own CR2032 cell", "6–20", "Bay 1, switch through a hole ≤ 10 mm"],
        ["Lid and parachute servos (SG90)", "183–215", "Bay 4, on a bracket under M4"],
        ["Wing servo (SG90)", "5–17", "Bay 1, between the spar pivots"],
        ["Solar panel 45 × 25 mm", "138–183", "Recessed in the −y flank; vent for the external SHT31 on +y"],
    ], sz=10, sz_cab=10.5, alto=I(0.41), alto_cab=I(0.34), alin=["l", "c", "l"], ml=60000)


def L25_lanzamiento(sl):
    panel(sl, X0, Y0, I(6.4), Y1 - Y0, [("v2B_exterior_anot_en.png", 1), ("v2BR_interior_anot_en.png", 1)],
          "Launch configuration: exterior and cut-away", misma_escala=True)
    x = X0 + I(6.4) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Stowed configuration", [
        "**In the rocket:** the CanSat sits on its support between the rocket parachutes and the nose cone, with no "
        "vertical restraint, and slides out at ejection (C1, C2, S7). The fairing is the container.",
        "**Separation (X3):** a breakwire loop leaves through M1 and is tied to the support; it breaks when the CanSat "
        "slides out.",
        "**Wing:** spars and folded tips in the two slots; the sail is folded in the dorsal channel under a flush cover "
        "that the spars hold.",
        "**Retention (M3, S5):** the wing links sit over centre, so launch and 30 G loads go into the pins and not into "
        "the servo gears; the parachute pin sits in a clevis; the lid servo latch holds the lid.",
    ], sz=11, spc=300)


def L26_desplegado(sl):
    panel(sl, X0, Y0, I(8.0), Y1 - Y0, [("v2BR_fase1_anot_en.png", 0.7), ("v2BR_desplegado_anot_en.png", 1.6)],
          "Phase 1 under the parachute (left) and phase 2 gliding (right)")
    x = X0 + I(8.0) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Deployed configuration", [
        f"**Phase 1:** at the separation the lid servo releases the lid, which pulls the parachute out; the CanSat "
        f"hangs from a short bridle to the rod ends and descends at about {V1:.1f} m/s.",
        "**Phase 2, step 1:** at 80 % of apogee the wing opens while still under the parachute: the flow runs along the "
        "keel, so the servo works at low load. The links lock over centre at 60°; the airflow unfolds the tips and a "
        "snap latch holds them.",
        "**Step 2:** the parachute servo pulls the pin of the two-ring release. The left lobe is smaller, so the CanSat "
        f"flies a left spiral of about {DES['R']:.0f} m radius.",
        "If the wing is not confirmed open, the parachute is kept and the CanSat lands under it.",
    ], sz=11, spc=300)


# ============================================================ DESCENT CONTROL
def L48_descenso(sl):
    panel(sl, X0, Y0, I(7.0), Y1 - Y0, [("v2BR_secuencia_en.png", 1)], "Stowed, phase 1 and phase 2")
    x = X0 + I(7.0) + GAP
    tabla(sl, x, Y0, X1 - x, [0.8, 1.7, 1.3], ["Phase", "Device", "Descent rate"], [
        ["1 (C3)", "Flat ripstop parachute, Ø226 with Ø40 vent", f"{V1:.1f} m/s"],
        ["2 (C4)", f"Rogallo sail, left spiral of {DES['R']:.0f} m", f"about {VZ['nom']:.1f} m/s"],
    ], sz=10.5, sz_cab=11, alto=I(0.55), alto_cab=I(0.36), alin=["l", "l", "l"], ml=60000)
    y = Y0 + I(0.36) + 2 * I(0.55) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, "How it works", [
        f"**Separation:** the breakwire detects it (X3) and the lid servo releases the lid, which pulls the "
        f"parachute out; phase 1 lasts about {T1:.0f} s with the "
        f"{APOGEO:.0f} m apogee of the launch vehicle.",
        f"**80 % of apogee ({0.8 * APOGEO:.0f} m):** the wing servo opens the wing under the parachute; once it is "
        "locked, the parachute servo opens the two-ring release.",
        f"**Phase 2:** about {T2:.0f} s of gliding in a spiral of {DES['R']:.0f} m (about "
        f"{T2 / DES['vueltas_s']:.1f} turns), with no actuators after the release. Landing at about "
        f"{DES['V']:.0f} m/s along the path: {0.5 * MTOT / 1000 * DES['V'] ** 2:.0f} J, against "
        f"{0.5 * MTOT / 1000 * V1 ** 2:.0f} J under the parachute.",
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
        ["Rate at the site", f"{V1:.1f} m/s", f"{V1:.1f} m/s"],
    ], sz=10, sz_cab=10.5, alto=I(0.4), alto_cab=I(0.36), alin=["l", "c", "c"], ml=60000)
    y = Y0 + I(0.36) + 7 * I(0.4) + I(0.17)
    tarjeta(sl, x, y, X1 - x, Y1 - y, None, [
        "Both in calendered ripstop nylon (35 g/m²), already available to the team. Both meet C3 (15 ± 3 m/s).",
        "**Theory:** drag equation at terminal velocity; canopy Cd0 (Knacke) and body Cd (Hoerner).",
    ], sz=10.5, spc=200)


def L50_sel_paracaidas(sl):
    w1 = I(6.6)
    tabla(sl, X0, Y0, w1, [1.6, 1.4, 1.4, 0.8], ["Criterion", "1A flat + vent", "1B cruciform", "Weight"], [
        ["Meets C3 (15 ± 3 m/s)", f"Yes, {V1:.1f} m/s", f"Yes, {V1:.1f} m/s", "Must"],
        ["Mass", "8.0 g", "9.5 g", "High"],
        ["Packed volume (20 mm cup)", "25 cm³", "30 cm³", "High"],
        ["Risk of tangling at ejection", "Low", "Higher (four arms)", "High"],
        ["Pendulum oscillation", "< ±8° (vent)", "±5°", "Medium"],
        ["Manufacturing", "One cut, 8 gores", "5 squares, more seams", "Low"],
    ], sz=11, sz_cab=11.5, alto=I(0.5), alto_cab=I(0.38), col_sel=1, alin=["l", "c", "c", "c"], ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Selected: 1A, flat circular with central vent", [
        "Lighter and smaller when packed, which matters in the 20 mm cup.",
        "Lower risk of tangling during the fast ejection from the rocket.",
        "The vent spills the central vortex and keeps the swing small, which helps the zenith and nadir videos (C6, C7).",
        "Diameter and vent are confirmed with drop tests from a drone before CDR.",
    ], sz=12, spc=380)


def L51_estrategias(sl):
    panel(sl, X0, Y0, I(7.0), Y1 - Y0, [("v2BR_desplegado_anot_en.png", 1)], "Rogallo glider, phase 2")
    x = X0 + I(7.0) + GAP
    tabla(sl, x, Y0, X1 - x, [1.3, 1.6, 1.6], ["", "A: asymmetric sail", "B: servo steering"], [
        ["How it turns", "Left lobe 10 % smaller (left folding tip 40 mm shorter)",
         "A servo pulls a line on one spar on command"],
        ["Path", f"Steady left spiral, about {DES['R']:.0f} m radius", "Can be steered toward a point"],
        ["Hardware", "None", "Servo, line and driver"],
        ["Software", "None after the release", "Guidance with GNSS and IMU"],
        ["Main risk", "Spiral radius set by the real sail", "Line and servo must survive 30 G"],
    ], sz=10, sz_cab=10.5, alto=I(0.62), alto_cab=I(0.36), alin=["l", "l", "l"], ml=60000)


def L52_sel_estrategia(sl):
    panel(sl, X0, Y0, I(6.2), Y1 - Y0, [("v2_planeo_en.png", 1)], "Phase 2 descent rate (estimate)")
    x = X0 + I(6.2) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Selected: A, asymmetric sail", [
        f"**How it works:** the left lobe has {100 * (1 - DES['lob_izq'] / DES['lob_der']):.0f} % less area than the "
        f"right one. The lift difference banks the glider about {DES['phi_deg']:.0f}° and it flies a steady left "
        f"spiral of about {DES['R']:.0f} m radius ({DES['vueltas_s']:.0f} s per turn).",
        f"**Descent rate:** about {VZ['nom']:.1f} m/s ({VZ['min']:.1f}–{VZ['max']:.1f}) with the lift-drag ratio "
        f"measured on parawings with rigid leading edges and keel ({DES['LD_nom']:.1f} for tubes of {DES['d_rel']:.1f} % "
        f"of the keel), corrected to our Reynolds number; {DES['vz_placa']:.1f} m/s for a flat plate. Inside C4 in both cases.",
        f"**Limits:** our wing is less swept ({DES['flecha']:.0f}° against 40–75° tested) and flies at "
        f"Re ≈ {DES['re_vuelo'] / 1e5:.0f} × 10⁵ (tests: 1.5 × 10⁶). The trend with sweep is favourable, but it is an "
        "extrapolation: glide drops at flight mass confirm rate and radius.",
        "**Theory:** NASA wind-tunnel data for parawings with rigid leading edges and keel (TN D-1957); flat-plate "
        "normal force (Hoerner); ripstop skin friction; body Cd (Hoerner); coordinated turn.",
    ], sz=10, spc=220)


# ============================================================ MECHANICAL
def L53_mecanico(sl):
    w1 = I(6.6)
    tabla(sl, X0, Y0, w1, [1.5, 1.8, 1.7], ["Element", "Material", "Function"], [
        ["Fairing", "PETG, 2 mm wall, printed", "Envelope, slots, dorsal channel"],
        ["Bulkheads M1–M5", "PETG, 25 % infill", "Carry the bays; stations"],
        ["Rods (4)", "Threaded M3, Al 6061", "Primary structure, bridle anchor"],
        ["Station nuts", "Nyloc M3, Al 7075", "Clamp the bulkheads; set the CG"],
        ["Wing spars", "Carbon tube Ø4/3, folding tips", "Leading edges of the sail"],
        ["Sail and parachute", "Ripstop nylon, Kevlar lines", "Phase 2 and phase 1"],
        ["Servos", "Three SG90 servos and links", "Lid, parachute release, wing opening"],
    ], sz=10.5, sz_cab=11, alto=I(0.5), alto_cab=I(0.38), ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Mechanical configuration", [
        "**One integral body:** skeleton of four threaded rods and five bulkheads inside a PETG fairing; five bays.",
        "**Mechanisms:** three SG90 servos and no springs: the lid servo opens the cup, the parachute servo pulls the "
        "pin of a two-ring release and the wing servo opens both spars through two links that lock over centre at both "
        "ends (stowed and 60°), so the gears carry no load at rest.",
        "**Requirements:** 2 mm printed wall (S6); smooth cylinder (S7); everything screwed, clamped or on standoffs "
        "(S8); PETG and nylon (S9); no pyrotechnics or heat (M1, M2); latches and links hold without power (M3); soldered battery "
        "tabs (M4).",
        "**Environmental tests:** rods for the 30 G shock (S5) and nyloc nuts for the 15 G vibration (S4); PETG keeps "
        "its shape at 60 °C; no sealed volumes for the vacuum test; servos operated after each test; GNSS and LoRa "
        "checked with the rods and spars installed.",
    ], sz=11, spc=280)


def L54_estructura(sl):
    panel(sl, X0, Y0, I(7.4), Y1 - Y0, [("v2A_interior_anot_en.png", 1), ("v2BR_interior_anot_en.png", 1)],
          "Structure A, printed monocoque (left), and B, rod skeleton with threaded stations (right)", misma_escala=True)
    x = X0 + I(7.4) + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Two structures", [
        "**A:** the printed tube is the structure; the bulkheads are bonded to the wall and the bridle is tied to "
        "eyebolts in M4.",
        "**B (selected):** four threaded rods are the structure; the bulkheads are clamped by nuts and the bridle is tied to "
        "the rod ends. The fairing only closes the body.",
        "Both keep the same bays, stations and envelope, so the electronics layout does not change.",
    ], sz=11.5, spc=330)


def L55_electrica(sl):
    panel(sl, X0, Y0, I(4.6), Y1 - Y0, [("v2BR_interior_anot_en.png", 1)], "Electrical components inside the body")
    x = X0 + I(4.6) + GAP
    tabla(sl, x, Y0, X1 - x, [1.7, 0.7, 2.6], ["Component", "Bay", "Mounting"], [
        ["Battery 2 × 18650, soldered tabs (E2, M4)", "2", "U cradle printed with M2; walls hold the cells"],
        ["Main PCB: ESP32, BMI160, BMP390, INA219, RTC", "3", "Lower rails hanging from M3"],
        ["GNSS u-blox NEO-7M + patch antenna", "3", "Upper board, patch facing the dorsal side"],
        ["LoRa radio RFM95W, 920 MHz", "3", "Upper board, λ/4 monopole"],
        ["2× ESP32-CAM, nadir and zenith (C6, C7)", "1, 4", "On M1 (Ø14 window) and under M4 (flank window)"],
        ["Beacon with CR2032 cell and switch (C8, E8, E9)", "1", "Switch through a hole ≤ 10 mm"],
        ["Main switch and power LED (E4–E6)", "3", "Through a hole ≤ 10 mm in the fairing"],
        ["Lid and parachute servos (SG90)", "4", "On a bracket under M4"],
        ["Wing servo (SG90)", "1", "On M1, between the spar pivots"],
        ["Solar panel 45 × 25 mm (E3)", "Flank", "Recessed in the −y flank of the fairing"],
        ["External SHT31 (secondary mission)", "3", "Behind a Ø6 vent in the +y flank"],
    ], sz=10, sz_cab=10.5, alto=I(0.38), alto_cab=I(0.34), alin=["l", "c", "l"], ml=60000)


def L56_mecanismos(sl):
    panel(sl, X0, Y0, I(6.4), Y1 - Y0, [("v2BR_detalle_anot_en.png", 1)],
          "Threaded station of M2: the battery module moves along the rods")
    x = X0 + I(6.4) + GAP
    tabla(sl, x, Y0, X1 - x, [1.5, 0.8, 2.2], ["Mechanism", "x [mm]", "What it does"], [
        ["Spar pivots (2)", "14", "Al 7075 M4 shaft tilted 5° (dihedral) with a crank; fixed stop at 60°"],
        ["Spar tip hinges (2)", "199", "Tips of 165 / 125 mm fold under the spar; the airflow unfolds them, a snap latch holds them"],
        ["Wing servo and links", "5–17", "Over centre at both ends: no load on the gears stowed or open"],
        ["Parachute servo", "183–223", "PTFE-sleeved pin of a two-ring release: about 3 N of pull at the 30 G drop load (servo: 18 N)"],
        ["Lid servo and latch", "183–234", "Releases the lid at the separation; the lid pulls the parachute out"],
        ["Dorsal cover", "14–206", "Held by the stowed spars; freed when the wing opens; tethered"],
        ["Threaded stations", "M2, M3", "Move the battery and avionics modules (0.5 mm per turn)"],
    ], sz=10, sz_cab=10.5, alto=I(0.52), alto_cab=I(0.34), alin=["l", "c", "l"], ml=60000)


def L57_seleccion_mec(sl):
    tabla(sl, X0, Y0, WU, [1.7, 2.2, 2.2, 2.4], ["Decision", "Selected", "Alternative", "Reason"], [
        ["Structure", "B: rod skeleton + fairing", "A: printed monocoque", "Rods carry the loads; access; CG adjustment"],
        ["Lid opening", "Micro servo + latch", "Compression spring", "Opens after the separation; no stored energy"],
        ["Parachute release", "Servo pulls a pin on a two-ring release", "Nichrome wire; pin under full load", "No heat (M2); the pin carries about 1/25 of the riser load"],
        ["Wing opening", "One servo, links over centre, under the parachute", "Torsion springs + ratchet", "No springs; low load; gears unloaded at rest"],
        ["Turn", "Smaller left lobe", "Servo steering", "No actuators in phase 2"],
        ["Station fixing", "Nyloc nuts on both sides", "Bonded bulkheads", "CG set after weighing the real parts"],
        ["Parachute anchor", "Short bridle to the rod ends", "Bridle to the lid", "The load goes straight into the rods"],
    ], sz=11, sz_cab=11.5, alto=I(0.49), alto_cab=I(0.38), col_sel=1, ml=70000)
    y = Y0 + I(0.38) + 7 * I(0.49) + I(0.17)
    tarjeta(sl, X0, y, WU, Y1 - y, None, [
        "The servos only open and release; they do not steer the flight. The parachute is released only after the wing "
        "is confirmed open; otherwise the CanSat lands under the parachute.",
    ], sz=11, spc=200)


# ============================================================ MASS BUDGET
def filas_items(grupos):
    return [[t[6], n1(t[1]), f"±{n1(t[4])}"] for g in grupos for t in ITEMS if t[3] == g]


def L58_componentes(sl):
    w = (WU - GAP) // 2
    tabla(sl, X0, Y0, w, [3.0, 0.8, 0.8], ["Structure", "Mass [g]", "±"], filas_items(["S"]), sz=9, sz_cab=10,
          alto=I(0.265), alto_cab=I(0.3), alin=["l", "r", "r"], ml=50000, mt=20000)
    tabla(sl, X0 + w + GAP, Y0, w, [3.0, 0.8, 0.8], ["Descent, mechanisms and electronics", "Mass [g]", "±"],
          filas_items(["D", "E"]), sz=9, sz_cab=10, alto=I(0.265), alto_cab=I(0.3), alin=["l", "r", "r"], ml=50000,
          mt=20000)


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
        "The fairing is the largest item: 240 mm of 2 mm printed PETG, the minimum wall of S6.",
        "Bulkheads printed at 25 % infill; nuts in aluminium 7075.",
    ], sz=11.5, spc=350)


def L60_incertidumbre(sl):
    w1 = I(7.4)
    filas = []
    for g in ("S", "D", "E"):
        m, u = suma(g)
        filas.append([GR_NOM[g], n1(m), f"±{n1(u)}", GR_FUENTE[g]])
    filas.append(["Total (RSS)", n1(MTOT), f"±{n1(UTOT)}", ""])
    tabla(sl, X0, Y0, w1, [1.5, 0.7, 0.6, 3.4], ["Group", "Mass [g]", "± [g]", "Sources"], filas, sz=10, sz_cab=10.5,
          alto=I(0.62), alto_cab=I(0.36), alin=["l", "r", "r", "l"], sub=(3,), ml=60000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Uncertainty", [
        "**Datasheet and catalogue:** ±2–5 % (cells, servos, GNSS, rods, nuts).",
        "**CAD volume and slicer:** ±5–10 % (printed parts; ±8 g on the fairing).",
        "**Estimates:** ±10–25 % (wiring, beacon, main PCB, cameras, radio).",
        "The total uses the root sum of squares. Every part is weighed during integration.",
    ], sz=11, spc=320)


def L61_total(sl):
    w1 = I(6.0)
    filas = [[GR_NOM[g], n1(suma(g)[0]), f"±{n1(suma(g)[1])}"] for g in ("S", "D", "E")]
    filas.append(["CanSat total", n1(MTOT), f"±{n1(UTOT)}"])
    tabla(sl, X0, Y0, w1, [2.4, 1.0, 0.9], ["Group", "Mass [g]", "± (RSS)"], filas, sz=12, sz_cab=12, alto=I(0.5),
          alto_cab=I(0.4), alin=["l", "r", "r"], sub=(3,), ml=70000)
    x = X0 + w1 + GAP
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Total mass and centre of gravity", [
        f"**Total: {n1(MTOT)} ± {n1(UTOT)} g** (S1: 500 ± 10 g).",
        f"**CG:** {n1(CAS['nominal']['x_cg'])} mm from the nadir end with the nominal stations; moving M2 and M3 "
        f"sets it anywhere between {rango_cg()}.",
        "**Longitudinal stability:** the pitching moments measured in NASA TN D-1957 (fig. 13), moved to our CG, "
        "show a stable trim only inside a narrow CG window, because our CG sits close to the wing.",
        "**How it is controlled:** a 5° dihedral (spar pivot shafts tilted 5°) raises the wing 9.5 mm over the CG "
        "and widens the window to x ≈ 107–111 mm (static margin 3–6 %); the threaded stations put the CG inside it "
        "(M2 at about 79 mm → CG ≈ 109.4 mm) and glide drops fine-tune it (0.5 mm per nut turn).",
        "**Fallback:** if the drops show it too sensitive, the wing is raised 25 mm on folding struts (margin 7 %).",
    ], sz=11.5, spc=330)


def L62_margen(sl):
    w1 = I(6.8)
    filas = [[en, n1(b), n1(c)] for en, (_, b, c) in zip(REDUCCION_EN, CG.REDUCCION)]
    tabla(sl, X0, Y0, w1, [3.4, 0.9, 0.9], ["Mass-saving measure (included)", "Standard [g]", "Selected [g]"], filas, sz=10.5,
          sz_cab=11, alto=I(0.46), alto_cab=I(0.38), alin=["l", "r", "r"], ml=70000)
    x = X0 + w1 + GAP
    ahorro = sum(b - c for _, b, c in CG.REDUCCION)
    tarjeta(sl, x, Y0, X1 - x, Y1 - Y0, "Margin", [
        f"**Margin = 500 − {n1(MTOT)} = +{n1(500 - MTOT)} g** (the measures in the table save {ahorro:.0f} g).",
        "**If the real mass is lower:** steel washers on the rods at M1 bring it to 500 g and move the CG toward the apex.",
        "**If it is higher:** shorter fairing (S3 allows 200–250 mm; about 10 g less per 15 mm) and lighter brackets.",
        "Final trim after weighing all parts, together with the station positions.",
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


def aligerar(salida, entrada, laminas, lado_max=1800):
    """Deja el archivo robusto para cualquier visor (el de iOS mezclaba imagenes entre laminas por el rId):
    - las figuras agregadas llevan identificadores de relacion unicos en todo el archivo (rIdFig<lamina>_<n>),
      distintos de los rId1..rId5 que usan las laminas del equipo;
    - las figuras se reducen a lo que realmente se ve (lado mayor <= lado_max px).
    Las imagenes y laminas del equipo no se tocan."""
    import io
    import re
    import zipfile
    from PIL import Image
    equipo = {n for n in zipfile.ZipFile(entrada).namelist() if n.startswith("ppt/media/")}
    zin = zipfile.ZipFile(salida)
    datos = {i.filename: zin.read(i.filename) for i in zin.infolist()}
    orden = [i.filename for i in zin.infolist()]
    zin.close()
    pres = datos["ppt/_rels/presentation.xml.rels"].decode()
    destino = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(slides/slide\d+\.xml)"', pres))
    ids = re.findall(r'<p:sldId [^>]*r:id="(rId\d+)"', datos["ppt/presentation.xml"].decode())
    for k in laminas:
        xml_n = "ppt/" + destino[ids[k - 1]]
        rel_n = xml_n.replace("slides/", "slides/_rels/") + ".rels"
        rels, xml = datos[rel_n].decode(), datos[xml_n].decode()
        cambio = {}
        for rid, tgt in re.findall(r'Id="(rId\d+)" Type="[^"]*/image" Target="\.\./(media/[^"]+)"', rels):
            if "ppt/" + tgt not in equipo:
                cambio[rid] = f"rIdFig{k}_{len(cambio) + 1}"
        for a, b in cambio.items():
            rels = rels.replace(f'Id="{a}"', f'Id="{b}"')
            xml = xml.replace(f'r:embed="{a}"', f'r:embed="{b}"')
        datos[rel_n], datos[xml_n] = rels.encode(), xml.encode()
    for n in orden:
        if n.startswith("ppt/media/") and n not in equipo and n.endswith(".png"):
            im = Image.open(io.BytesIO(datos[n]))
            if max(im.size) > lado_max:
                f = lado_max / max(im.size)
                im = im.resize((round(im.size[0] * f), round(im.size[1] * f)), Image.LANCZOS)
            b = io.BytesIO()
            im.save(b, "PNG", optimize=True)
            datos[n] = b.getvalue()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in orden:
            zout.writestr(n, datos[n])


# ============================================================ ajustes minimos en laminas del equipo (coherencia)
def _texto(par, t):
    """Reemplaza el texto de un parrafo conservando el formato del primer run."""
    runs = par.runs
    runs[0].text = t
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def _celda(tabla_sh, i, j, viejo, nuevo):
    c = tabla_sh.table.cell(i, j)
    assert c.text == viejo, (i, j, c.text)
    _texto(c.text_frame.paragraphs[0], nuevo)


def ajustes_equipo(prs):
    """Lamina 30: largo real del CanSat (240 mm con el paracaidas adentro).  Las laminas de electronica (sensores,
    C&DH, EPS, FSW, GCS) no se tocan.  Si el texto original cambio, no se toca nada."""
    sl = prs.slides[29]
    sh = {x.shape_id: x for x in sl.shapes}
    if sh[357].text_frame.text != "CanSat" or sh[362].text_frame.text != "200 mm":
        print("AVISO: la lamina 30 cambio; no se ajusta")
    else:
        mm = 3375000 / 270.0                       # la bahia de 270 mm mide 3375000 EMU en el dibujo
        tope, base = 2610000, 5985000
        top_c = base - int(240 * mm)
        sh[356].top, sh[356].height = tope, top_c - tope
        par = sh[356].text_frame.paragraphs
        _texto(par[0], "Clearance")
        for q in par[1:]:
            q._p.getparent().remove(q._p)
        sh[357].top, sh[357].height = top_c, base - top_c
        p2 = sh[357].text_frame.add_paragraph()
        p2.alignment = sh[357].text_frame.paragraphs[0].alignment
        r = p2.add_run()
        r.text = "parachute inside\n(top cup)"
        r.font.size = sh[358].text_frame.paragraphs[0].runs[0].font.size
        r.font.bold = False
        f0 = sh[357].text_frame.paragraphs[0].runs[0].font
        r.font.name = f0.name
        if f0.color and f0.color.type is not None:
            r.font.color.rgb = f0.color.rgb
        sh[359].begin_y, sh[359].end_y = tope, top_c
        sh[360].top, sh[360].height = tope, top_c - tope
        _texto(sh[360].text_frame.paragraphs[0], "30 mm")
        sh[361].begin_y, sh[361].end_y = top_c, base
        sh[362].top = (top_c + base) // 2 - sh[362].height // 2
        _texto(sh[362].text_frame.paragraphs[0], "240 mm")
        _celda(sh[367], 2, 1, "CanSat: 200 mm, plus 50 mm of parachute space",
               "CanSat: 240 mm with the parachute inside (top cup); 30 mm clearance to the nose cone")


def main(entrada, salida, neutro=False):
    prs = Presentation(entrada)
    sl = prs.slides
    for k, t in ESPERADO.items():
        st = subtitulo(sl[k - 1])
        assert st is not None and t.lower() in st.text_frame.text.lower(), (k, st.text_frame.text if st else None)
    for k, fn in TRABAJO.items():
        limpiar(sl[k - 1])
        fn(sl[k - 1])
    if len(sl) == 106 and subtitulo(sl[29]) is not None and "Launch Vehicle Compatibility (2/2)" in subtitulo(sl[29]).text_frame.text:
        ajustes_equipo(prs)
    if neutro:                  # variante neutra (reformatea TODA la presentacion; no es la que usa el equipo)
        import formato_cansat
        formato_cansat.neutro()
        formato_cansat.aplicar(prs)
    prs.save(salida)
    aligerar(salida, entrada, sorted(TRABAJO))
    print("ok:", salida, len(prs.slides), "laminas;", len(TRABAJO), "rellenas")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], neutro="--neutro" in sys.argv)
