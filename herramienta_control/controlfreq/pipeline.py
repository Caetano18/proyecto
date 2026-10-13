"""Orquestador: lee las ENTRADAS, construye el sistema y ejecuta cada segmento (análisis, diseño, gráficos, informe)."""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field

import numpy as np
import control as ct

from . import sistema as S
from .sistema import Sistema, a_tf, tf_a_texto
from .frecuencia import nyquist_conteo, rejilla
from .metricas import calcular_metricas, evaluar_especificaciones, CLAVES_ESPECS
from .estabilidad import rangos_estables, casos_de_K, ganancias_criticas
from .compensacion import ParamsDiseno, Diseno, disenar, ErrorDiseno
from . import informe as inf
from . import graficos as gr
from . import exportar as ex


# ----------------------------------------------------------------------------
#  entradas
# ----------------------------------------------------------------------------
@dataclass
class Entradas:
    NOMBRE: str = "Planta"
    NUM: list | None = None
    DEN: list | None = None
    EXPRESION: str | None = None
    POLOS_CEROS: dict | None = None
    FACTORES_BODE: dict | None = None
    ASINTOTAS_BODE: dict | None = None
    K: float = 1.0
    RETARDO: float = 0.0
    SENSOR: object = None
    COMPENSADOR: object = None
    ESPECS: dict = field(default_factory=dict)
    DISENO: object = None
    PARAMS_DISENO: dict = field(default_factory=dict)
    SECCIONES: dict = field(default_factory=dict)
    GRAFICOS: dict = field(default_factory=dict)
    CASOS_K: list | None = None
    W_MIN: float | None = None
    W_MAX: float | None = None
    N_PUNTOS: int = 4000
    T_FINAL: float | None = None
    ORDEN_PADE: int = 8
    CARPETA_SALIDA: str = "salidas"
    FORMATOS: tuple = ("png",)
    DPI: int = 140
    MOSTRAR: bool = True
    EXPORTAR_DAT: bool = False


SECCIONES_DEFECTO = dict(sistema=True, estabilidad=True, frecuencia=True, temporal=True, compensacion=True)
GRAFICOS_DEFECTO = dict(descomposicion=True, bode=True, nyquist=True, nichols=True, temporal=True, polos=True,
                        estabilidad_K=True, sensibilidad=True, compensacion=True, comparacion=True)


def cargar_entradas(ruta: str | None = None) -> Entradas:
    """Importa un archivo de entradas (por defecto `entradas.py` junto a main.py) y arma el objeto Entradas."""
    if ruta is None:
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "entradas.py")
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f"No encuentro el archivo de entradas: {ruta}")
    spec = importlib.util.spec_from_file_location("entradas_usuario", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ent = Entradas()
    for nombre in ent.__dataclass_fields__:
        if hasattr(mod, nombre):
            setattr(ent, nombre, getattr(mod, nombre))
    desconocidas = [n for n in dir(mod) if n.isupper() and n not in ent.__dataclass_fields__]
    ent._desconocidas = desconocidas
    ent.SECCIONES = {**SECCIONES_DEFECTO, **(ent.SECCIONES or {})}
    ent.GRAFICOS = {**GRAFICOS_DEFECTO, **(ent.GRAFICOS or {})}
    ent._ruta = ruta
    return ent


def construir_planta(ent: Entradas) -> tuple[ct.TransferFunction, float, str]:
    """(G, K_ref, descripción). K_ref es el valor de 'K' que se usa para expresar los rangos de ganancia."""
    if ent.EXPRESION:
        return S.tf_desde_expresion(ent.EXPRESION, K=ent.K), float(ent.K), f"expresión «{ent.EXPRESION}» con K = {ent.K:g}"
    if ent.FACTORES_BODE:
        G = S.tf_desde_factores_bode(**ent.FACTORES_BODE) * ent.K
        return G, Sistema(G).forma_bode().K_B, "factores leídos del Bode"
    if ent.ASINTOTAS_BODE:
        G = S.tf_desde_asintotas(**ent.ASINTOTAS_BODE) * ent.K
        return G, Sistema(G).forma_bode().K_B, "asíntotas leídas del Bode"
    if ent.POLOS_CEROS:
        G = S.tf_desde_polos_ceros(**ent.POLOS_CEROS) * ent.K
        return G, Sistema(G).forma_bode().K_B, "polos y ceros"
    if ent.NUM is not None and ent.DEN is not None:
        return ct.tf(np.array(ent.NUM, float), np.array(ent.DEN, float)) * ent.K, float(ent.K), f"NUM/DEN con K = {ent.K:g}"
    raise ValueError("Falta definir la planta: completá EXPRESION, o NUM y DEN, o POLOS_CEROS, FACTORES_BODE o ASINTOTAS_BODE en entradas.py.")


def _a_tf_usuario(obj, ent: Entradas):
    if obj is None:
        return None
    if isinstance(obj, str):
        return S.tf_desde_expresion(obj, K=ent.K)
    if isinstance(obj, dict):
        return S.tf_desde_polos_ceros(**obj) if ("polos" in obj or "ceros" in obj) else ct.tf(obj["num"], obj["den"])
    return a_tf(obj)


# ----------------------------------------------------------------------------
@dataclass
class Resultados:
    entradas: Entradas
    sis0: Sistema
    K_ref: float
    descripcion: str
    metricas0: object = None
    nyquist0: object = None
    rangos: dict | None = None
    casos: list | None = None
    candidatos: list = field(default_factory=list)
    recomendado: Diseno | None = None
    elegido: Diseno | None = None
    metricas_elegido: object = None
    informe: str = ""
    archivos: list = field(default_factory=list)


def ejecutar(ent: Entradas, mostrar: bool | None = None, salida: str | None = None, imprimir: bool = True,
             guardar_graficos: bool = True) -> Resultados:
    """Ejecuta todo según las entradas. Devuelve un objeto Resultados (útil para usar la librería desde Python)."""
    mostrar = ent.MOSTRAR if mostrar is None else mostrar
    carpeta = salida or ent.CARPETA_SALIDA
    G, K_ref, desc = construir_planta(ent)
    sens = _a_tf_usuario(ent.SENSOR, ent)
    comp_usuario = _a_tf_usuario(ent.COMPENSADOR, ent)
    sis0 = Sistema(G=G, H=sens, retardo=float(ent.RETARDO), nombre=ent.NOMBRE)
    res = Resultados(entradas=ent, sis0=sis0, K_ref=K_ref, descripcion=desc)
    sec = ent.SECCIONES
    pade = ent.ORDEN_PADE
    w0 = rejilla(sis0, ent.W_MIN, ent.W_MAX, ent.N_PUNTOS)
    partes: list[str] = []
    if getattr(ent, "_desconocidas", None):
        partes.append("  ⚠ Variables desconocidas en el archivo de entradas (¿error de tipeo?): " + ", ".join(ent._desconocidas))

    cab = f"ANÁLISIS DE «{ent.NOMBRE}»   ({desc})"
    partes.append("\n" + "█" * 78 + f"\n  {cab}\n" + "█" * 78)

    # -------------------------------------------------------------- análisis de la planta
    sis_an = sis0.con_compensador(comp_usuario) if comp_usuario is not None else sis0
    res.metricas0 = calcular_metricas(sis0, orden_pade=pade, t_final=ent.T_FINAL, w=w0)
    if sec.get("sistema", True):
        partes.append(inf.seccion_sistema(sis0, "Lazo abierto sin compensar L(s)"))
    if sec.get("estabilidad", True):
        res.nyquist0 = nyquist_conteo(sis0, pade)
        res.rangos = rangos_estables(sis0, pade)
        res.casos = casos_de_K(sis0, K_ref, ent.CASOS_K, pade)
        partes.append(inf.seccion_estabilidad(res.nyquist0, res.metricas0.polos_cl, res.rangos, K_ref, res.casos, ganancias_criticas(sis0)))
    if sec.get("frecuencia", True):
        partes.append(inf.seccion_frecuencia(res.metricas0, "sin compensar"))
    if sec.get("temporal", True):
        partes.append(inf.seccion_temporal(res.metricas0, "sin compensar"))

    # -------------------------------------------------------------- compensación
    especs = {k: v for k, v in (ent.ESPECS or {}).items() if v is not None}
    validas = {c.lower(): c for c in CLAVES_ESPECS}
    for k in list(especs):
        if k not in CLAVES_ESPECS:
            if k.lower() in validas:
                especs[validas[k.lower()]] = especs.pop(k)
            else:
                raise ValueError(f"ESPECS tiene la clave desconocida «{k}». Claves válidas: {', '.join(CLAVES_ESPECS)}.")
    candidatos: list[Diseno] = []
    msgs: list[str] = []
    if comp_usuario is not None:
        d = Diseno("usuario", True, Gc=comp_usuario, sistema=sis_an, parametros={})
        d.metricas = calcular_metricas(sis_an, orden_pade=pade, t_final=ent.T_FINAL)
        d.cumplimiento = evaluar_especificaciones(d.metricas, especs)
        d.notas.append("Compensador ingresado por el usuario (COMPENSADOR en entradas.py).")
        candidatos.append(d)
    if ent.DISENO and sec.get("compensacion", True):
        if not especs:
            msgs.append("DISENO está activo pero ESPECS está vacío: completá las especificaciones (Kv, MF, ...).")
        else:
            tipos = (ent.DISENO,) if isinstance(ent.DISENO, str) else tuple(ent.DISENO)
            params = ParamsDiseno(**(ent.PARAMS_DISENO or {}))
            try:
                hechos, reco, m = disenar(sis0, especs, tipos, params, pade)
                candidatos += hechos
                msgs += m
                res.recomendado = reco
            except ErrorDiseno as e:
                msgs.append(f"No se pudo diseñar: {e}")
    res.candidatos = candidatos
    if candidatos and sec.get("compensacion", True):
        partes.append(inf.seccion_compensacion(especs, msgs, candidatos, res.recomendado, res.metricas0))
    elif msgs:
        partes.append(_t_msgs(msgs))
    elegido = res.recomendado or next((d for d in candidatos if d.exito and d.sistema is not None), None)
    res.elegido = elegido
    if elegido is not None:
        res.metricas_elegido = elegido.metricas or calcular_metricas(elegido.sistema, orden_pade=pade, t_final=ent.T_FINAL)
        partes.append(inf._t(f"6. SISTEMA COMPENSADO ELEGIDO: {elegido.tipo}"))
        partes.append("  Gc(s) = " + tf_a_texto(elegido.Gc, "polos_ceros", 5))
        partes.append("  L(s)·Gc(s) en forma de Bode:  " + elegido.sistema.forma_bode().texto())
        if sec.get("estabilidad", True):
            c1 = nyquist_conteo(elegido.sistema, pade)
            partes.append(inf.seccion_estabilidad(c1, res.metricas_elegido.polos_cl, rangos_estables(elegido.sistema, pade), 1.0, None,
                                                  ganancias_criticas(elegido.sistema), unidad_K="κ", num="6.1", nombre="compensado"))
        if sec.get("frecuencia", True):
            partes.append(inf.seccion_frecuencia(res.metricas_elegido, "compensado", num="6.2"))
        if sec.get("temporal", True):
            partes.append(inf.seccion_temporal(res.metricas_elegido, "compensado", num="6.3"))
        partes.append(_comparacion(res))
    res.informe = inf.generar_informe(partes)
    if imprimir:
        print(res.informe)

    # -------------------------------------------------------------- gráficos
    figs: list[tuple[str, object]] = []
    G_ = ent.GRAFICOS
    gr.configurar(mostrar)
    sistemas = [("Sin compensar", sis0)]
    if elegido is not None:
        sistemas.append((f"Compensada ({elegido.tipo})", elegido.sistema))
    try:
        if G_.get("descomposicion"):
            figs.append(("01_descomposicion_bode", gr.fig_descomposicion_bode(sis0)))
        if G_.get("bode"):
            figs.append(("02_bode", gr.fig_bode(sistemas, w=None, titulo=f"Diagrama de Bode — {ent.NOMBRE}")))
        if G_.get("nyquist"):
            figs.append(("03_nyquist", gr.fig_nyquist(sistemas, titulo=f"Nyquist — {ent.NOMBRE}")))
        if G_.get("nichols"):
            figs.append(("04_nichols", gr.fig_nichols(sistemas, titulo=f"Carta de Nichols — {ent.NOMBRE}")))
        if G_.get("temporal"):
            figs.append(("05_temporal", gr.fig_temporal(sistemas, t_final=ent.T_FINAL, orden_pade=pade)))
        if G_.get("polos"):
            figs.append(("06_polos_ceros", gr.fig_polos_ceros(elegido.sistema if elegido else sis0, orden_pade=pade)))
        if G_.get("estabilidad_K") and sec.get("estabilidad", True) and res.casos is not None:
            figs.append(("07_estabilidad_K", gr.fig_estabilidad_K(sis0, K_ref, res.casos, res.rangos, orden_pade=pade)))
        if G_.get("sensibilidad"):
            figs.append(("08_sensibilidad", gr.fig_sensibilidad(sistemas)))
        if G_.get("compensacion") and elegido is not None:
            figs.append((f"09_compensacion_{elegido.tipo}", gr.fig_compensacion(sistemas, Sistema(G=elegido.Gc), titulo=f"Compensación: {elegido.tipo}",
                                                                                orden_pade=pade, t_final=ent.T_FINAL)))
        if G_.get("comparacion") and len([d for d in candidatos if d.exito]) > 1:
            figs.append(("10_comparacion_candidatos", gr.fig_comparacion_candidatos(sis0, candidatos, t_final=ent.T_FINAL, orden_pade=pade)))
    except Exception as exc:                           # un gráfico fallido no debe tirar abajo el análisis
        print(f"\n⚠ Error al generar un gráfico: {type(exc).__name__}: {exc}", file=sys.stderr)
    if guardar_graficos:
        for nombre, fig in figs:
            res.archivos += gr.guardar(fig, nombre, carpeta, ent.DPI, ent.FORMATOS)
    if ent.EXPORTAR_DAT:
        res.archivos += ex.exportar_dat(sistemas, os.path.join(carpeta, "datos"), "sis", pade)
        filas = [(n, calcular_metricas(s, orden_pade=pade, temporal=False).fila()) for n, s in sistemas]
        res.archivos.append(ex.exportar_csv_resumen(filas, os.path.join(carpeta, "resumen.csv")))
    os.makedirs(carpeta, exist_ok=True)
    ruta_inf = os.path.join(carpeta, "informe.txt")
    with open(ruta_inf, "w", encoding="utf-8") as f:
        f.write(res.informe)
    res.archivos.append(ruta_inf)
    if imprimir and res.archivos:
        print("\nArchivos generados en", os.path.abspath(carpeta) + ":")
        for a in res.archivos:
            print("   ", os.path.relpath(a, carpeta))
    if mostrar:
        import matplotlib.pyplot as plt
        plt.show()
    else:
        import matplotlib.pyplot as plt
        plt.close("all")
    return res


def _t_msgs(msgs: list[str]) -> str:
    return inf._t("5. COMPENSACIÓN") + "\n" + "\n".join("  " + m for m in msgs)


def _comparacion(res: Resultados) -> str:
    m0, m1 = res.metricas0, res.metricas_elegido
    f0, f1 = m0.fila(), m1.fila()

    def mp_nichols(m):
        return "—" if (m.Mp_Mr is None and m.cerrado.Mr <= 1.0 + 1e-9 and m.estable is False) else (
            "≈0 %" if m.Mp_Mr is None else f"{m.Mp_Mr:.1f} %")

    def v(x, fmt="{:.4g}", suf=""):
        if x is None:
            return "—"
        if isinstance(x, float) and np.isinf(x):
            return "∞"
        return fmt.format(x) + suf

    filas = []
    for nombre, f, m in (("Sin compensar", f0, m0), ("Compensado", f1, m1)):
        filas.append([nombre, "estable" if f["estable"] else "INESTABLE", v(f["Kv"]), v(f["MF"], "{:.1f}", "°"), v(f["MG_dB"], "{:.1f}", " dB"),
                      v(f["wc"], "{:.3g}"), v(f["Mr_dB"], "{:.2f}", " dB") if f["estable"] else "—",
                      mp_nichols(m) if f["estable"] else "—", v(f["Mp"], "{:.1f}", " %"), v(f["ts"], "{:.3g}", " s")])
    return (inf._t("7. COMPARACIÓN: SIN COMPENSAR vs COMPENSADO") + "\n" +
            inf._tabla(filas, ["", "lazo cerrado", "Kv", "MF", "MG", "ωc", "Mr (Nichols)", "Mp por Mr", "Mp simulado", "ts(2%)"], "  ") +
            "\n  (Mp por Mr = sobreimpulso estimado con la carta de Nichols y el modelo de 2.º orden; Mp simulado = respuesta al escalón.)")
