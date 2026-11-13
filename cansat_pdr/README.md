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
    make fea            # malla + CalculiX + respuesta dinámica (20 min, 8 GB de RAM)
    make aero           # aerodinámica del planeador (Polhamus, polar, descenso, estabilidad)
    make informe        # PDF en LaTeX
    make laminas        # PDF de láminas

Cambiar una medida o un material es editar `src/params.py` y volver a correr.

## Supuestos que hay que confirmar

- Las masas de electrónica, cola y paracaídas son asignaciones.
- Las propiedades de las piezas impresas y del elastómero son de hoja de datos: faltan probetas y un ensayo de amortiguamiento.
- S4 y S5 se interpretaron como barrido senoidal de 15 G y semiseno de 30 G en la base; hay que confirmarlo con la organización.
- Quedan márgenes negativos locales en resonancia y en choque lateral (pared del tubo junto a la tapa, sillas de la batería); la corrección está descrita en el informe y todavía no se volvió a calcular.
