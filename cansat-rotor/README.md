# Rotor libre para el CanSat 2026–27

Documento de investigación y anteproyecto del sistema de descenso de dos etapas
(drogue + rotor libre), con teoría, dimensionamiento, planos en TikZ, electrónica,
riesgos, ensayos y bibliografía.

- `main.pdf`: documento compilado.
- `main.tex` y `capitulos/`: fuente LaTeX.
- `calculos.py`: script con todos los cálculos (`python3 calculos.py`);
  `calculos_salida.txt` es su salida, que se incluye en el apéndice B.

Compilar: `latexmk -pdf main.tex` (o `pdflatex main.tex` dos veces). Requiere
TeX Live con `pgfplots`, `pgfgantt`, `siunitx`, `tcolorbox` y `babel-spanish`.
