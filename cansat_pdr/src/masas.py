"""Presupuesto de masa y centro de gravedad a partir del CAD y de las asignaciones.
Uso: python3 masas.py <salida.json>
"""
import sys, json
import numpy as np
import params as P
import cad
import planeo as _pl

M = P.M_EQ


def centro(p):
    c = p["shape"].Center()
    return np.array([c.x, c.y, c.z])


def main(out):
    lan = cad.build("lanzamiento")
    des = cad.build("desplegado")
    filas = []          # (subsistema, item, cant, masa unit, masa total, incert, fuente, x_cg)

    def add(sub, item, cant, m_tot, inc, fuente, x):
        filas.append(dict(sub=sub, item=item, cant=cant, unit=m_tot / cant, masa=m_tot, inc=inc, fuente=fuente, x=x))

    def grupo(sub, clave, nombre, parts, frac=0.05, fuente="CAD"):
        ps = [p for p in parts if clave in p["nombre"]]
        m = sum(p["masa"] for p in ps)
        x = sum(p["masa"] * centro(p)[0] for p in ps) / m
        add(sub, nombre, len(ps), m, m * frac, fuente, x)
        return m
    # ---------------- estructura del planeador (CAD x densidad)
    E = "Estructura del planeador"
    grupo(E, "C1 cuaderna", "Cuaderna de nariz C1 (PA12-CF)", lan, 0.10)
    grupo(E, "cuaderna intermedia", "Cuadernas C2 y C3 (PA12-CF)", lan, 0.10)
    grupo(E, "C4 cuaderna", "Cuaderna de cola C4 (PA12-CF)", lan, 0.10)
    grupo(E, "larguero", "Largueros CFRP d5/3,5 x 201", lan, 0.05)
    grupo(E, "panel lateral", "Paneles laterales G10 0,5", lan, 0.05)
    grupo(E, "tapa superior", "Tapa superior G10 0,5", lan, 0.05)
    grupo(E, "bandeja", "Bandeja de avionica G10 0,8", lan, 0.05)
    grupo(E, "Cuna de ala", "Cunas de ala (PA12-CF)", lan, 0.10)
    grupo(E, "Guia de botalon", "Guias de botalon (PA12-CF)", lan, 0.10)
    add(E, "Cubierta inferior PC 0,25", 1, M["cubierta_inf"], 0.6, "Estimado", 103.0)
    add(E, "Tornillos M2/M2,5, insertos y adhesivo", 1, 8.0, 1.6, "Estimado", 103.0)
    # ---------------- ala
    A = "Ala de membrana"
    grupo(A, "Varilla BA", "Varillas de borde de ataque (4 tramos)", lan)
    grupo(A, "Tirante", "Tirantes de borde de fuga", lan)
    grupo(A, "Varilla de raiz", "Varillas de raiz", lan)
    grupo(A, "Manguito", "Manguitos de traba Al 7075", lan)
    grupo(A, "Herraje", "Herrajes A, B y T (Al 7075)", lan, 0.10)
    add(A, "Membrana ripstop con costuras", 2, 2.1, 0.4, "Nota de membrana", 136.0)
    add(A, "Articulaciones, resortes, cordon elastico", 2, 4.0, 0.8, "Estimado", 140.0)
    # ---------------- cola
    C = "Cola (nota de cola)"
    add(C, "Botalon + cola en V + herrajes", 1, M["cola"], 4.2, "Asignacion", 110.0)
    add(C, "Servo de cola", 1, M["servo_cola"], 0.5, "Hoja de datos", 23.5)
    # ---------------- avionica y equipos
    V = "Avionica y equipos"
    add(V, "Bateria Li-ion 18650", 1, M["bateria"], 1.0, "Hoja de datos", 100.5)
    add(V, "Sillas + cincha de bateria", 1, M["porta_bateria"], 1.0, "Estimado", 100.5)
    add(V, "PCB principal (MCU, IMU, baro, SD)", 1, M["pcb_principal"], 5.0, "Asignacion", 101.0)
    add(V, "PCB radio + GNSS + antena", 1, M["pcb_radio"], 4.0, "Asignacion", 170.0)
    add(V, "Camaras cenit y nadir", 2, M["camaras"], 3.2, "Asignacion", 100.0)
    add(V, "Baliza sonora + pila boton", 1, M["baliza"], 1.6, "Asignacion", 170.0)
    add(V, "Celdas solares", 1, M["solar"], 1.2, "Asignacion", 103.0)
    add(V, "Servo del cerrojo", 1, M["servo_lib"], 0.5, "Hoja de datos", 176.5)
    add(V, "Separadores, cableado y conectores", 1, M["cableado_tornillos"] - 8.0 + 3.0, 2.6, "Estimado", 103.0)
    add(V, "Llave de bayoneta + plato de apoyo (inox)", 1,
        sum(p["masa"] for p in lan if "Llave" in p["nombre"] or "Plato" in p["nombre"]), 0.4, "CAD", 210.0)
    add(V, "Aislador elastomerico de la llave", 1, [p["masa"] for p in lan if "Aislador" in p["nombre"]][0], 0.1, "CAD", 217.0)
    add(V, "Patines de elastomero con cara de PTFE", 8, 8 * 0.11, 0.2, "CAD", 103.0)
    m_plan_sin = sum(f["masa"] for f in filas)
    # ---------------- contenedor
    K = "Contenedor"
    grupo(K, "CT1", "Tubo d90 x 242, pared 2 (LW-PLA)", lan, 0.10)
    grupo(K, "CT2", "Tapa nervada (PA12-CF)", lan, 0.10)
    add(K, "Paracaidas de 15 m/s", 1, M["paracaidas"], 3.0, "Asignacion", 230.0)
    add(K, "Brida de 3 puntos + eslabon giratorio", 1, M["brida_herrajes"], 1.0, "Estimado", 232.0)
    m_cont = sum(f["masa"] for f in filas if f["sub"] == K)
    lastre = P.M_TOT - sum(f["masa"] for f in filas)
    add(V, "Lastre de centrado / margen", 1, lastre, 0.0, "Ajuste", 33.0)
    tot = sum(f["masa"] for f in filas)
    inc = float(np.sqrt(sum(f["inc"] ** 2 for f in filas)))
    inc_lin = sum(f["inc"] for f in filas)
    sub = {}
    for f in filas:
        s = sub.setdefault(f["sub"], dict(masa=0.0, inc2=0.0, mx=0.0))
        s["masa"] += f["masa"]
        s["inc2"] += f["inc"] ** 2
        s["mx"] += f["masa"] * f["x"]
    for s in sub.values():
        s["inc"] = float(np.sqrt(s.pop("inc2")))
        s["x"] = s.pop("mx") / s["masa"]
    m_plan = tot - m_cont
    x_plan = sum(f["masa"] * f["x"] for f in filas if f["sub"] != K) / m_plan
    x_tot = sum(f["masa"] * f["x"] for f in filas) / tot
    # CG en vuelo: las alas y la cola se mueven
    ala_est = sum(f["masa"] * f["x"] for f in filas if f["sub"] == A)
    m_ala = sub[A]["masa"]
    x_ala_des = P.X_A + 0.60 * P.D_AB           # varillas a 45 grados + tela: centroide aprox. al 60 % de la cuerda
    x_cola_des = 250.0
    x_vuelo = (x_plan * m_plan - ala_est + m_ala * x_ala_des - M["cola"] * 110.0 + M["cola"] * x_cola_des) / m_plan
    res = dict(filas=filas, sub=sub, total=tot, inc_rss=inc, inc_lin=inc_lin, lastre=lastre, m_planeador=m_plan,
               m_contenedor=m_cont, x_cg_planeador_estibado=x_plan, x_cg_lanzamiento=x_tot,
               x_cg_planeador_vuelo=x_vuelo, x_centroide_ala=P.X_A + 2 * P.D_AB / 3,
               carga_alar=m_plan / 1000 * P.G0 / (P.S_TRI * 1e-4),
               w_estimado=float(_pl.sink(*_pl.delta(20.0), m=m_plan / 1000)[0]),
               w_estimado_sin_cuerpo_nota=P.NOTA["w"] * float(np.sqrt(m_plan / 500.0 * P.NOTA["S"] / P.S_TRI)))
    json.dump(res, open(out, "w"), indent=1)
    for k, s in sub.items():
        print(f"{k:<28s} {s['masa']:7.1f} +/- {s['inc']:.1f} g   x = {s['x']:.0f}")
    print(f"TOTAL {tot:.1f} +/- {inc:.1f} (RSS) g; lastre/margen {lastre:.1f} g; planeador {m_plan:.1f} g; contenedor {m_cont:.1f} g")
    print(f"x_cg lanzamiento {x_tot:.1f}; planeador estibado {x_plan:.1f}; en vuelo {x_vuelo:.1f}; centroide ala {res['x_centroide_ala']:.1f}")
    print(f"carga alar {res['carga_alar']:.1f} N/m2; w estimado {res['w_estimado']:.2f} m/s")


if __name__ == "__main__":
    main(sys.argv[1])
