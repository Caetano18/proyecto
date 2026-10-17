# Rotor libre para el CanSat 2026–27

Documento de investigación y anteproyecto del sistema de descenso de dos etapas
(drogue + rotor libre), con teoría, dimensionamiento, planos en TikZ, electrónica,
riesgos, ensayos y bibliografía. La versión 2 adapta el modelo al anexo A modificado
(CanSat de Ø90, drogue soltado antes de abrir el rotor, R = 0,25 m) y a la electrónica
real del equipo; agrega los capítulos de arquitectura (23), sensibilidad (24) y
selección de sensores (25).

- `main.pdf`: documento compilado.
- `main.tex` y `capitulos/`: fuente LaTeX.
- `calculos.py`: script con los cálculos base (`python3 calculos.py`);
  `calculos_salida.txt` es su salida, que se incluye en el apéndice B.
- `analysis/`: modelos y estudios (BEMT, arranque, estabilidad, estructura, sensibilidad,
  sensores, confiabilidad). La configuración se elige con `CANSAT_CFG` (`v2` por defecto en
  la BEMT y el arranque; `v1` reproduce la versión anterior). Los datos van a `analysis/data/`.

Compilar: `latexmk -pdf main.tex` (o `pdflatex main.tex` dos veces). Requiere
TeX Live con `pgfplots`, `pgfgantt`, `siunitx`, `tcolorbox` y `babel-spanish`.
