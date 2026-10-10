# Apunte: respuesta en frecuencia y compensación

- `apunte.pdf`: apunte compilado (36 páginas).
- `apunte.tex`: fuente LaTeX. Las figuras se dibujan con pgfplots a partir de `datos/*.dat`.
- `generar_datos.py`: regenera `datos/` (`pip install numpy scipy matplotlib control`).
- `compensacion.m`: script de MATLAB que reproduce los ejemplos y el problema integrador.

Para compilar: `latexmk -pdf apunte.tex` (o `pdflatex` dos veces).
En Overleaf hay que subir la carpeta completa, incluida `datos/`.
