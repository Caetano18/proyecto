# CanSat de ala delta: PDR del subsistema mecánico

Diseño estructural, materiales, mecanismos, planos y análisis (respuesta en frecuencia a 15 G y choque de 30 G)
para el CanSat Argentina Universitario (Apéndice A: Ø90 mm, 200 a 250 mm, 500 ± 10 g).

| Archivo | Qué es |
|---|---|
| `PDR_Mecanica_CanSat_AlaDelta.pdf` | Informe (LaTeX), con los planos como anexo |
| `Aerodinamica_Planeador.pdf` | Sección de aerodinámica del planeador, suelta (también es la sección 8 del informe) |
| `PDR_Mecanica_Laminas.pdf` | El mismo contenido en láminas 4:3, formato PDR |
| `planos/Planos_CanSat_AlaDelta.pdf` | Siete planos A3 (CS-MEC-01 a 07) |
| `cad/*.step` | Modelo 3D en lanzamiento y desplegado |
| `fea/*.json` | Resultados: márgenes, modos, masas, ala, verificación |
| `src/` | Código que genera todo desde `src/params.py` |

## Regenerar

    make cad planos     # CAD, renders y planos (1 min)
    make fea            # malla + CalculiX + respuesta dinámica (25 min, 8 GB de RAM)
    make aero           # aerodinámica del planeador (Polhamus, polar, descenso, distribución de carga con VLM, estabilidad)
    make informe        # PDF en LaTeX
    make laminas        # PDF de láminas

Cambiar una medida o un material es editar `src/params.py` y volver a correr.

## Supuestos que hay que confirmar

- Las masas de electrónica, cola y paracaídas son asignaciones.
- Las propiedades de las piezas impresas y del elastómero son de hoja de datos: faltan probetas y un ensayo de amortiguamiento.
- S4 y S5 se interpretaron como barrido senoidal de 15 G y semiseno de 30 G en la base; hay que confirmarlo con la organización.
- El modelo de elementos finitos es exclusivamente estructural: equipos, ala estibada y botalón entran como masa no estructural.
- Patines de C1 y manguito del centrador se modelan como apoyos que deslizan (cara de PTFE): solo transmiten compresión radial.
- El borde inferior del contenedor se modela empotrado (cota conservadora para la pared junto a la boca).

## Revisión B (18/11/2026)

- Centrador de cola en la tapa (collar de C4 + manguito de elastómero + anillo-alojamiento); se sacaron los patines de C4,
  que cargaban la pared del tubo junto al empotramiento de la tapa (único margen negativo real de la revisión A).
- Largueros: angulares CFRP 6 × 6 × 1 en las aristas interiores de la caja (antes, tubos Ø5 interiores y unión panel–tapa por canto).
- Patines de C1 de 24° × 1,5 mm (C1 Ø83) y rieles bajo la bandeja.
- CalculiX con SPOOLES en un hilo (`CCX_SPOOLES=1`, fijado en el `Makefile`): en varios hilos dejaba ruido local en los autovectores
  que aparecía como picos falsos de cientos a miles de MPa.
