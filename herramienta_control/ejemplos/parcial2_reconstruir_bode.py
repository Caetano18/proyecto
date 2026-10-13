# TITULO: Parcial 2 — reconstruir G(s) desde el Bode (G1=34 dB, G2=1/s, G3=-2,41 dB@1,3, G4=-40 dB@100) y compensar
NOMBRE = "Parcial 2: G reconstruida desde el Bode"
FACTORES_BODE = dict(K_dB=[34, -2.41, -40], integradores=1, polos=[1.3, 100])
ESPECS = dict(Kv=20, MF=50, MG=40)       # MG en veces (40 ≈ 32 dB)
DISENO = "auto"
PARAMS_DISENO = dict(wc_nuevo=0.5, delta_atraso=6, razon_cero_atraso=10)   # como en la resolución del PDF
MOSTRAR = False
