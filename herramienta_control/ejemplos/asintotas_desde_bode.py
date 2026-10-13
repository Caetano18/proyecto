# TITULO: Reconstruir G(s) desde asíntotas — 20 dB en 0,1 rad/s con pendiente -20 y quiebres en 1,3 y 100
NOMBRE = "G desde asíntotas"
ASINTOTAS_BODE = dict(w_ref=0.1, mag_dB=20, pendiente_inicial=-20, quiebres=[(1.3, -20), (100, -20)])
DISENO = None
MOSTRAR = False
