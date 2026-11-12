"""Renders CAD para el PDR y los planos.  Uso: python3 figs_cad.py <carpeta>"""
import os, sys, json
import cadquery as cq
import cad, viz
import params as P

V = cq.Vector


def explotar(parts):
    out = []
    for p in parts:
        n, g = p["nombre"], p["grupo"]
        d = (0, 0, 0)
        if n.startswith("C1"):
            d = (-45, 0, 0)
        elif n.startswith("C4"):
            d = (45, 0, 0)
        elif "panel lateral der" in n:
            d = (0, 55, 0)
        elif "panel lateral izq" in n:
            d = (0, -55, 0)
        elif "tapa superior" in n:
            d = (0, 0, 60)
        elif "bandeja" in n:
            d = (0, 0, -55)
        elif "Cuna" in n:
            d = (0, 75 if "der" in n else -75, 0)
        elif "Guia" in n:
            d = (0, 0, 85)
        q = dict(p)
        q["shape"] = p["shape"].translate(V(*d))
        out.append(q)
    return out


def main(out):
    os.makedirs(out, exist_ok=True)
    est, lan, des = cad.build("estibado"), cad.build("lanzamiento"), cad.build("desplegado")
    r = viz.render
    big = (2000, 1500)
    r(est, f"{out}/est_iso.png", "iso", big, 1.35, hide=("carenado",))
    r(est, f"{out}/est_iso_cola.png", "iso_cola", big, 1.35, hide=("carenado",))
    r(des, f"{out}/des_iso.png", ((-1.0, -1.1, 0.85), (0, 0, 1)), big, 1.3, hide=("carenado",))
    r(des, f"{out}/des_planta.png", "planta", big, 1.3, hide=("carenado",))
    r(des, f"{out}/des_frente.png", "frente", (2000, 800), 1.6, hide=("carenado",))
    r(lan, f"{out}/lan_iso.png", "vertical", (1500, 2000), 1.25, opac={"CT1": 0.28, "CT2": 0.5, "Paracaidas": 0.6})
    r(lan, f"{out}/lan_corte.png", "vertical", (1500, 2000), 1.25, clip=((0, -1, 0), (0, 0, 0)), hide=("carenado",))
    r(lan, f"{out}/lan_corte_h.png", "iso", big, 1.3, clip=((0, -1, 0), (0, 0, 0)), hide=("carenado",))
    cont = [p for p in lan if p["grupo"] == "contenedor" and p["nombre"].startswith("CT")]
    r(cont, f"{out}/cont_iso.png", ((1.0, -1.1, 0.7), (-1, 0, 0)), (1500, 1800), 1.25)
    r(cont, f"{out}/cont_cerrado.png", "vertical", (1500, 2000), 1.25)
    st = [p for p in est if p["grupo"] == "estructura"]
    r(st, f"{out}/bastidor_iso.png", "iso", big, 1.35)
    r(st, f"{out}/bastidor_sin_paneles.png", "iso", big, 1.35, hide=("panel lateral izq", "tapa superior"))
    r(explotar(st), f"{out}/bastidor_explotado.png", "iso", big, 1.3)
    eq = [p for p in est if p["grupo"] in ("estructura", "equipo", "mecanismo")]
    r(eq, f"{out}/equipos_abajo.png", "iso_abajo", big, 1.35, hide=("panel lateral izq", "tapa superior", "Cuna", "Guia", "Patin"))
    r(eq, f"{out}/equipos_lateral.png", "lateral", (2000, 900), 1.5,
      hide=("panel lateral", "tapa superior", "Cuna", "Guia", "Patin"))
    ala = [p for p in des if p["grupo"] in ("ala",) or p["nombre"].startswith(("C1", "C4", "P1", "P2", "L"))]
    r(des, f"{out}/ala_J.png", ((-0.3, -1.0, 0.8), (0, 0, 1)), (1600, 1200), 5.0, hide=("carenado",))
    c1 = [p for p in est if p["nombre"].startswith("C1")]
    c4 = [p for p in est if p["nombre"].startswith("C4")]
    c2 = [p for p in est if p["nombre"].startswith("C2")]
    r(c1, f"{out}/c1.png", ((1.0, -0.8, 0.6), (0, 0, 1)), (1400, 1200), 1.3)
    r(c4, f"{out}/c4.png", ((-1.0, -0.8, 0.6), (0, 0, 1)), (1400, 1200), 1.3)
    r(c2, f"{out}/c2.png", ((1.0, -0.8, 0.6), (0, 0, 1)), (1400, 1200), 1.3)
    cola = [p for p in lan if p["nombre"].startswith(("C4", "Llave", "CT2", "Servo del cerrojo"))]
    M = {}
    M["cerrojo"] = r(cola, f"{out}/cerrojo.png", ((-0.35, -1.0, 0.3), (1, 0, 0)), (1700, 1300), 1.3,
                     clip=((0, -1, 0), (0, 0, 0)),
                     marcas={"llave": (216, 0, 0), "pasador": (222.6, 0, 5), "tapa": (216, 0, 28), "c4": (203, 0, -30),
                             "servo": (176, 0, -16), "nervio": (218, 0, -25), "brida": (217.5, 0, 33)})
    hide_eq = ("panel lateral izq", "tapa superior", "Cuna", "Guia", "Patin")
    M["equipos"] = r(eq, f"{out}/equipos.png", "iso", big, 1.35, hide=hide_eq,
                     marcas={"lastre": (33, -10, 14), "bateria": (100, 0, 15.5), "pcb_radio": (170, 0, 5.6),
                             "servo_cola": (23, -6, -16), "pcb": (110, -25, -14), "servo_cerrojo": (176, -6, -16),
                             "llave": (212, 0, 0), "c1": (4, 30, 30), "c4": (203, 0, 38), "bandeja": (50, -27, -4.5),
                             "larguero": (150, 20.5, 26), "panel": (120, 27.5, 20)})
    M["est"] = r(est, f"{out}/est_iso.png", "iso", big, 1.35, hide=("carenado",),
                 marcas={"c1": (0, 0, 25), "tapa": (100, 0, 31.5), "botalon": (60, 0, 39.5), "panel": (150, 27.75, -20),
                         "membrana": (90, 29.6, 9), "varilla_int": (60, 34, 2.5), "varilla_ext": (40, 39.4, 2.5),
                         "manguito": (122, 34, 4), "tirante": (150, 37, -7), "patin": (4, 29.7, 29.7), "cuna": (62, 40, 6),
                         "llave": (214, 0, 0), "c4": (203, 30, 28)})
    M["des"] = r(des, f"{out}/des_iso.png", ((-1.0, -1.1, 0.85), (0, 0, 1)), big, 1.3, hide=("carenado",),
                 marcas={"A": (P.X_A, P.Y_PIV, 0), "J": P.P_J, "T": P.P_T, "B": (P.X_B, P.Y_PIV, P.Z_TE),
                         "membrana": (150, 120, 2.8), "tirante": (P.X_B, 130, P.Z_TE), "raiz": (100, P.Y_ROOT, 0),
                         "botalon": (260, 0, P.Z_BOOM), "cola": (320, 30, P.Z_BOOM + 20), "solar": (100, 0, 31.5),
                         "ba": (60, 90, 0)})
    M["lan"] = r(lan, f"{out}/lan_corte.png", "vertical", (1500, 2000), 1.25, clip=((0, -1, 0), (0, 0, 0)),
                 hide=("carenado",),
                 marcas={"tubo": (120, 0, 44), "tapa": (216, 0, 30), "paracaidas": (230, 0, 20), "llave": (212, 0, 0),
                         "c4": (203, 0, -25), "c1": (4, 0, 25), "bateria": (100, 0, 6.5), "pcb": (101, 0, -14),
                         "boca": (-2, 0, 44), "lastre": (33, 0, 7), "ala": (100, 0, -38)})
    M["bastidor"] = r(explotar(st), f"{out}/bastidor_explotado.png", "iso", big, 1.3,
                      marcas={"c1": (-45, 0, 30), "c2": (62, 0, 28), "c3": (140, 0, 28), "c4": (252, 0, 30),
                              "larguero": (100, -20.5, 26), "p_lat": (100, -82.5, 0), "tapa": (100, 0, 91),
                              "bandeja": (100, 0, -59.5), "cuna": (62, -108, 0), "guia": (140, 0, 122)})
    json.dump(M, open(f"{out}/marcas.json", "w"), indent=1)
    print("renders ok")


if __name__ == "__main__":
    main(sys.argv[1])
