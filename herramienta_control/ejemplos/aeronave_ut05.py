# TITULO: UT05 — aeronave en cabeceo con fuselaje flexible (K=2): solo análisis (pico elástico, varios cruces)
NOMBRE = "Aeronave UT05 (K=2)"
EXPRESION = "K * 50/(s+50) * 18*(s+1)/(s*(s**2+4.2*s+9)) * 400/(s**2+s+400)"
K = 2
ESPECS = dict(Kv=4, MF=45)
DISENO = ["solo_ganancia", "adelanto", "atraso"]
MOSTRAR = False
