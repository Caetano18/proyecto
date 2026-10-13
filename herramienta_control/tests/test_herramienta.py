"""Pruebas automáticas: reproducen los resultados verificados del apunte y de los dos parciales.

Ejecutar desde la carpeta herramienta_control:   python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
import warnings

import numpy as np
import control as ct

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
warnings.filterwarnings("ignore")

from controlfreq.sistema import (Sistema, tf_desde_expresion, tf_desde_factores_bode, tf_desde_asintotas,  # noqa: E402
                                 tf_desde_polos_ceros)
from controlfreq.frecuencia import margenes, nyquist_conteo, cerrado_frecuencia, zeta_desde_Mr, Mp_desde_zeta  # noqa: E402
from controlfreq.estabilidad import rangos_estables, kappa_para_MF, kappa_para_MG, kappa_para_Mr, casos_de_K  # noqa: E402
from controlfreq.compensacion import disenar, ParamsDiseno  # noqa: E402
from controlfreq.metricas import calcular_metricas  # noqa: E402
from controlfreq.temporal import respuesta_escalon  # noqa: E402

s = ct.tf("s")


def sis(expr, **kw):
    return Sistema(tf_desde_expresion(expr, **kw))


class TestSistema(unittest.TestCase):
    def test_tipo_y_constantes(self):
        c = sis("K/(s**3+10*s**2+5*s)", K=100).constantes_error()
        self.assertEqual(c["tipo"], 1)
        self.assertAlmostEqual(c["Kv"], 20.0, 6)
        self.assertEqual(c["Kp"], float("inf"))
        c0 = sis("10/((s+1)*(s+2))").constantes_error()
        self.assertEqual(c0["tipo"], 0)
        self.assertAlmostEqual(c0["Kp"], 5.0, 6)
        c2 = sis("(1+2*s)/(s**2*(1+0.5*s))").constantes_error()
        self.assertEqual(c2["tipo"], 2)
        self.assertAlmostEqual(c2["Ka"], 1.0, 6)

    def test_factores_bode_parcial2(self):
        S = Sistema(tf_desde_factores_bode(K_dB=[34, -2.41, -40], integradores=1, polos=[1.3, 100]))
        fb = S.forma_bode()
        self.assertAlmostEqual(fb.K_B, 10 ** (-8.41 / 20), 6)
        self.assertEqual(fb.N, 1)
        self.assertAlmostEqual(S.constantes_error()["Kv"], 0.37975, 4)
        m = margenes(S)
        self.assertAlmostEqual(m.MF, 74.08, 1)
        self.assertAlmostEqual(m.MG_dB, 48.52, 1)

    def test_asintotas_igual_a_factores(self):
        a = Sistema(tf_desde_asintotas(0.1, 20, -20, [(1.3, -20), (100, -20)]))
        b = Sistema(tf_desde_factores_bode(K=1, integradores=1, polos=[1.3, 100]))
        w = np.logspace(-2, 3, 50)
        np.testing.assert_allclose(a.respuesta(w), b.respuesta(w), rtol=1e-9)

    def test_polos_ceros_bode(self):
        G = tf_desde_polos_ceros([0, -1, -2], [], K=2, forma="bode")
        self.assertAlmostEqual(Sistema(G).constantes_error()["Kv"], 2.0, 9)


class TestMargenesYNyquist(unittest.TestCase):
    def test_parcial1_sin_compensar(self):
        m = margenes(sis("K/(s**3+10*s**2+5*s)", K=100))
        self.assertAlmostEqual(m.MF, -8.83, 1)
        self.assertAlmostEqual(m.wc, 3.1435, 3)
        self.assertAlmostEqual(m.MG_dB, -6.02, 2)
        self.assertAlmostEqual(m.w180, np.sqrt(5), 4)

    def test_conteo_nyquist_K(self):
        for K, Z in [(10, 0), (100, 2)]:
            c = nyquist_conteo(sis("K/(s**3+10*s**2+5*s)", K=K))
            self.assertEqual((c.P, c.Z), (0, Z))
            self.assertTrue(c.coincide)
        self.assertTrue(nyquist_conteo(sis("K/(s**3+10*s**2+5*s)", K=50)).marginal)

    def test_lazo_abierto_inestable(self):
        c2 = nyquist_conteo(sis("2*(s+3)/(s*(s-1))"))
        self.assertEqual((c2.P, c2.N, c2.Z), (1, -1, 0))
        c05 = nyquist_conteo(sis("0.5*(s+3)/(s*(s-1))"))
        self.assertEqual((c05.P, c05.N, c05.Z), (1, 1, 2))
        self.assertTrue(c05.coincide)

    def test_retardo(self):
        S = Sistema(tf_desde_expresion("2/(s*(s+1))"), retardo=0.2)
        m = margenes(S)
        self.assertAlmostEqual(m.MF, 24.35, 1)
        self.assertAlmostEqual(m.margen_retardo, 0.34, 2)

    def test_mr_nichols_compensado_parcial1(self):
        S = sis("K/(s**3+10*s**2+5*s)", K=100).con_compensador(ct.tf([50, 1], [4700, 1]))
        m, cf = margenes(S), cerrado_frecuencia(S)
        self.assertAlmostEqual(m.MF, 62.4, 1)
        self.assertAlmostEqual(m.MG_dB, 33.09, 1)
        self.assertAlmostEqual(cf.Mr_dB, 0.74, 2)
        self.assertAlmostEqual(cf.wr, 0.063, 2)
        z = zeta_desde_Mr(cf.Mr)
        self.assertAlmostEqual(z, 0.55, 2)
        self.assertAlmostEqual(Mp_desde_zeta(z), 12.7, 0)
        e = respuesta_escalon(S)
        self.assertAlmostEqual(e.Mp, 11.06, 0)


class TestEstabilidad(unittest.TestCase):
    def test_rango_K_parcial1(self):
        r = rangos_estables(sis("K/(s**3+10*s**2+5*s)", K=100))
        (lo, hi), = r["positivo"]
        self.assertAlmostEqual(lo, 0.0)
        self.assertAlmostEqual(100 * hi, 50.0, 3)

    def test_rangos_condicional(self):
        r = rangos_estables(sis("(1+s)**2/(s*(1+10*s)**2*(1+0.1*s)**2)"))["positivo"]
        self.assertEqual(len(r), 2)
        self.assertAlmostEqual(r[0][1], 0.318, 3)
        self.assertAlmostEqual(r[1][0], 51.0, 0)
        self.assertAlmostEqual(r[1][1], 1285, -1)

    def test_casos_de_K(self):
        casos = casos_de_K(sis("K/(s**3+10*s**2+5*s)", K=100), 100.0, [-20, 10, 30, 50, 100])
        cats = [c["categoria"] for c in casos]
        self.assertEqual(cats, ["inestable", "oscilatorio", "oscilatorio", "marginal", "inestable"])

    def test_K_para_especificaciones(self):
        S = sis("1/(s*(s+1)*(s+5))")
        (w, k), = kappa_para_MF(S, 45)
        self.assertAlmostEqual(k, 4.667, 3)
        self.assertAlmostEqual(w, 0.7417, 3)
        (_, k2), = kappa_para_MG(S, 10 ** (10 / 20))
        self.assertAlmostEqual(k2, 9.487, 3)
        k3, = kappa_para_Mr(S, 20 * np.log10(1.3))
        self.assertAlmostEqual(k3, 4.619, 2)


class TestCompensacion(unittest.TestCase):
    def test_adelanto_del_apunte(self):
        S = sis("1/(s*(s+1)*(0.05*s+1))")
        hechos, reco, _ = disenar(S, dict(Kv=10, MF=45, MG_dB=10), ("adelanto",), ParamsDiseno(redondear=False))
        d = hechos[0]
        self.assertTrue(d.exito and d.cumple)
        self.assertAlmostEqual(d.parametros["delta"], 12.0)
        self.assertAlmostEqual(d.parametros["alfa"], 0.150, 2)
        self.assertAlmostEqual(d.parametros["cero"], 1.92, 2)
        self.assertAlmostEqual(d.parametros["polo"], 12.8, 1)
        self.assertAlmostEqual(d.metricas.margenes.MF, 45.14, 1)

    def test_atraso_adelanto_del_apunte(self):
        S = sis("1/(s*(s+1)*(s+4))")
        hechos, _, _ = disenar(S, dict(Kv=10, MF=50, MG_dB=10), ("atraso_adelanto",), ParamsDiseno(redondear=False))
        d = hechos[0]
        self.assertTrue(d.cumple)
        self.assertAlmostEqual(d.parametros["alfa"], 0.0935, 3)
        self.assertAlmostEqual(d.parametros["cero_adelanto"], 0.611, 2)
        self.assertAlmostEqual(d.parametros["polo_adelanto"], 6.54, 1)
        self.assertAlmostEqual(d.metricas.margenes.MF, 51.0, 0)

    def test_parcial2_atraso_en_05(self):
        S = Sistema(tf_desde_factores_bode(K_dB=[34, -2.41, -40], integradores=1, polos=[1.3, 100]))
        hechos, _, _ = disenar(S, dict(Kv=20, MF=50, MG=40), ("atraso",), ParamsDiseno(wc_nuevo=0.5, redondear=True))
        d = hechos[0]
        self.assertTrue(d.cumple)
        self.assertAlmostEqual(d.kappa, 52.67, 1)
        self.assertAlmostEqual(d.parametros["beta"], 38.0, delta=2.0)
        self.assertGreater(d.metricas.margenes.MF, 50)

    def test_error_tipo_incompatible(self):
        from controlfreq.compensacion import ErrorDiseno
        S = sis("10/((s+1)*(s+2))")                      # tipo 0: Kv sería 0
        with self.assertRaises(ErrorDiseno) as cm:
            disenar(S, dict(Kv=5, MF=45), ("adelanto",))
        self.assertIn("integrador", str(cm.exception))


class TestPipeline(unittest.TestCase):
    def test_pipeline_parcial1(self):
        from controlfreq.pipeline import cargar_entradas, ejecutar
        ent = cargar_entradas(os.path.join(RAIZ, "ejemplos", "parcial1_nyquist_atraso.py"))
        with tempfile.TemporaryDirectory() as d:
            res = ejecutar(ent, mostrar=False, salida=d, imprimir=False, guardar_graficos=False)
            self.assertIn("COINCIDE", res.informe)
            self.assertIn("estable para  0 < K < 50", res.informe)
            self.assertIsNotNone(res.recomendado)
            self.assertTrue(res.recomendado.cumple)
            self.assertTrue(os.path.exists(os.path.join(d, "informe.txt")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
