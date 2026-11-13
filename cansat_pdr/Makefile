# Regenera todo el PDR mecanico a partir de src/params.py
# Requiere: python3 (numpy, scipy, matplotlib, cadquery, gmsh, pyvista, pillow), CalculiX (ccx), pdflatex y node+playwright (laminas)
FEA_TMP ?= /tmp/cansat_fea
PY = cd src && python3

all: cad planos fea informe

cad:
	$(PY) figs_cad.py ../figs && $(PY) figs_layout.py ../figs
	$(PY) -c "import cad; [cad.export_step(cad.build(c), '../cad/cansat_%s.step' % c) for c in ('lanzamiento', 'desplegado')]"

planos: cad
	$(PY) planos.py ../planos ../figs

fea:
	$(PY) fe_bench.py $(FEA_TMP)/bench ../fea/verificacion_viga.json
	$(PY) fe_model.py $(FEA_TMP) 1.6 e
	$(PY) fe_analisis.py $(FEA_TMP) e ../fea/resultados_fea.json $(FEA_TMP)/res.npz
	$(PY) wing_frame.py ../fea/ala_desplegada.json ../fea/ala_desplegada.npz
	$(PY) masas.py ../fea/masas.json
	$(PY) polhamus.py ../fea/polhamus.json ../figs/polhamus.png
	$(PY) figs_fea.py $(FEA_TMP) e ../fea/resultados_fea.json $(FEA_TMP)/res.npz ../fea/ala_desplegada.npz ../figs

informe:
	$(PY) build_informe.py

aero:
	$(PY) polhamus.py ../fea/polhamus.json ../figs/polhamus.png
	$(PY) planeo.py ../fea/planeo.json ../figs/planeo.png
	$(PY) planeo.py ../fea/planeo_500g.json ../figs/planeo_500g.png 500
	$(PY) aero_dist.py
	$(PY) aero_planeador.py

laminas:
	$(PY) build_pdr.py

.PHONY: all cad planos fea informe laminas aero
