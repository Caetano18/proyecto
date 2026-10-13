# TITULO: Parcial 1 — K/(s³+10s²+5s): Nyquist vs K y compensación para Kv=20, MG>5, MF>50°
NOMBRE = "Parcial 1: K/(s³+10s²+5s)"
EXPRESION = "K/(s**3 + 10*s**2 + 5*s)"
K = 100
ESPECS = dict(Kv=20, MF=50, MG=5)
DISENO = "auto"
PARAMS_DISENO = dict(wc_nuevo=None)      # probá wc_nuevo=0.2 para reproducir el diseño del PDF (atraso en 0,2 rad/s)
CASOS_K = [-20, 10, 30, 50, 100]
MOSTRAR = False
