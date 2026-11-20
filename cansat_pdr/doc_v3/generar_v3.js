// Memoria PDR v3: combinacion del documento v2 del equipo (concepto integral, vela Rogallo) con la verificacion de la rev. D.
// Uso: node generar_v3.js datos_v3.json salida.docx
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  HeadingLevel, BorderStyle, LevelFormat, Footer, PageNumber, TableLayoutType, VerticalAlign,
} = require("docx");

const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const AZUL = "1F4E79", CELESTE = "DCE6F2", GRIS = "595959", ROJO = "C00000", BORDE = "8EA9DB";
const ANCHO = 9638;   // A4 con margenes de 2 cm
const f1 = (x, d = 1) => x.toFixed(d).replace(".", ",");
const ms = (x) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(2).replace(".", ",");

// ---- texto con **negrita** y [[rojo]]
function runs(t, o0 = {}) {
  const o = Object.fromEntries(Object.entries(o0).filter(([, v]) => v !== undefined));   // sin claves vacias que pisen negrita/color
  const out = [];
  for (const parte of t.split(/(\*\*.+?\*\*|\[\[.+?\]\])/)) {
    if (!parte) continue;
    if (parte.startsWith("**")) out.push(new TextRun({ ...o, text: parte.slice(2, -2), bold: true }));
    else if (parte.startsWith("[[")) out.push(new TextRun({ ...o, text: parte.slice(2, -2), bold: true, color: ROJO }));
    else out.push(new TextRun({ text: parte, ...o }));
  }
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t, o.run || {}), spacing: { after: 100 }, alignment: o.align, ...o.par });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const B = (t, nivel = 0) => new Paragraph({ numbering: { reference: "vinetas", level: nivel }, children: runs(t), spacing: { after: 60 } });
const Nota = (t) => new Paragraph({ children: runs(t, { italics: true, color: GRIS, size: 18 }), spacing: { after: 140 } });

const borde = { style: BorderStyle.SINGLE, size: 4, color: BORDE };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };

function celda(t, w, o = {}) {
  const lineas = String(t).split("\n");
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders: bordes, verticalAlign: VerticalAlign.CENTER,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: lineas.map((l) => new Paragraph({ alignment: o.align, children: runs(l, { bold: o.bold, color: o.color, size: o.size || 18 }) })),
  });
}

// tabla: cab = encabezados; filas = arrays; anchos relativos; sel = indice de columna seleccionada (encabezado rojo)
function tabla(cab, filas, anchos, o = {}) {
  const tot = anchos.reduce((a, b) => a + b, 0);
  const w = anchos.map((a) => Math.round((ANCHO * a) / tot));
  w[w.length - 1] = ANCHO - w.slice(0, -1).reduce((a, b) => a + b, 0);
  const rows = [];
  if (cab) rows.push(new TableRow({ tableHeader: true, children: cab.map((c, j) => celda(c, w[j], {
    fill: j === o.sel ? ROJO : AZUL, bold: true, color: "FFFFFF", align: (o.alin || [])[j] })) }));
  filas.forEach((f, i) => rows.push(new TableRow({ children: f.map((c, j) => celda(c, w[j], {
    fill: (o.sub || []).includes(i) ? CELESTE : (j === 0 && o.col0 !== false ? CELESTE : (j === o.sel ? "FBE9E9" : undefined)),
    bold: (j === 0 && o.col0 !== false) || (o.sub || []).includes(i), align: (o.alin || [])[j] })) })));
  return [new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: w, layout: TableLayoutType.FIXED, rows }),
          new Paragraph({ spacing: { after: 120 }, children: [] })];
}

// ecuacion en recuadro con numero
function ec(lineas, num) {
  const w1 = Math.round(ANCHO * 0.86), w2 = ANCHO - w1;
  const c1 = new TableCell({ width: { size: w1, type: WidthType.DXA }, borders: bordes,
    shading: { fill: "F3F6FA", type: ShadingType.CLEAR, color: "auto" }, margins: { top: 60, bottom: 60, left: 120, right: 120 },
    children: lineas.map((l) => new Paragraph({ children: runs(l, { font: "Cambria Math", size: 20 }) })) });
  const c2 = new TableCell({ width: { size: w2, type: WidthType.DXA }, borders: bordes, verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: num, size: 18, color: GRIS })] })] });
  return [new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: [w1, w2], layout: TableLayoutType.FIXED,
    rows: [new TableRow({ children: [c1, c2] })] }), new Paragraph({ spacing: { after: 120 }, children: [] })];
}

const fmtMS = (par) => (par[0] < 0 ? `[[${ms(par[0])}]]` : ms(par[0]));
const C = [];

// ================================================================ portada
C.push(...tabla(null, [[
  "MEMORIA DE CÁLCULO Y DISEÑO PRELIMINAR (PDR) — EDICIÓN COMBINADA v3\nControl de descenso (fases 1 y 2), estructura primaria, mecanismos de liberación y presupuesto de masa — CanSat Argentina Universitario 2026",
]], [1], { col0: true }));
C.push(...tabla(null, [
  ["Código de documento", "PDR-STR-REC-2026-v3", "Base", "v2 del equipo + revisión D (verificación estructural)"],
  ["Masa nominal (S1)", "500,0 ± 10 g (W = 4,905 N)", "Envolvente (S2, S3)", "Ø 90,0 mm × 240,0 mm"],
  ["Descenso fase 1 (C3)", "14,3–15,9 m/s — paracaídas plano Ø233 mm", "Descenso fase 2 (C4)", "5,1–6,5 m/s — vela Rogallo en espiral"],
  ["Carcasa", "Laminado carbono 0,8 mm + vidrio 0,6 mm", "Fecha", "20/11/2026"],
], [2.2, 3.2, 2.0, 3.6], { col0: false }));

// ================================================================ 0
C.push(H1("0. Qué combina esta edición"));
C.push(P("Esta memoria une los dos trabajos del subsistema mecánico. De la **memoria v2** del equipo se toma el concepto: cuerpo integral (todo el CanSat baja junto), vela Rogallo con espiral pasiva, liberación por nicrom encapsulado, cámaras que ven hacia afuera y la electrónica de 2 celdas. De la **revisión D** se toma la verificación: modelo de elementos finitos, ensayo de la lijadora con el CanSat parado, carga del ensayo de caída sobre el anclaje del paracaídas y presupuesto de masa por fuente."));
C.push(P("Al verificar el diseño v2 con el modelo de elementos finitos apareció un problema: con la carcasa de PETG de 2 mm el primer modo lateral queda en 161–172 Hz y **no pasa el ensayo de la lijadora** (MS = −0,55 en la carcasa). Además, la carcasa pesa 163 g y no 139 g, y el CanSat suma 503 g sin lastre. La revisión E conserva todo el concepto v2 y cambia la carcasa por la carcasa laminada de la revisión D: el modo lateral sube a 349–370 Hz, todos los márgenes son positivos y quedan 51 g de margen de masa."));
C.push(...tabla(["Tema", "Origen", "Decisión de la revisión E", "Motivo"], [
  ["Concepto de vuelo", "v2", "Cuerpo integral: el paracaídas se suelta al 80 % del apogeo y el mismo cuerpo planea", "Una sola pieza a recuperar; cámaras al exterior; el Apéndice A no exige separar payload y contenedor"],
  ["2.º sistema de descenso", "v2", "Vela Rogallo de 670 cm², flecha 52°, espiral pasiva de 25°", "Sin cola ni servos: unos 30 g menos y ningún mecanismo activo en vuelo"],
  ["Liberación", "v2", "Lazo de Dyneema cortado por nicrom dentro de una cápsula de PTFE (M1)", "Un solo actuador; si falla, el CanSat sigue bajando con el paracaídas"],
  ["Paracaídas", "v2 + rev. D", "Plano con ventana, Ø233 mm (densidad del sitio 1,15 kg/m³)", "Con la densidad a nivel del mar, el Ø226 de v2 da 15,4 m/s en el sitio"],
  ["Carcasa", "rev. D", "Laminado: carbono-epoxi 0,8 mm (x < 130 mm) + vidrio-epoxi 0,6 mm (arriba)", "PETG 2 mm: 161 Hz, lijadora −0,55. Laminado: 349 Hz, +15; 87 g más liviana"],
  ["Esqueleto interno", "v2", "5 mamparos de PETG + 4 varillas roscadas M3 de aluminio", "Pasa todos los casos con amplio margen; la bandeja sale entera"],
  ["Anclaje del paracaídas", "rev. D", "Brida de 3 ramales a los extremos superiores de las varillas", "Ensayo de caída: 265 N; el lazo de Dyneema queda fuera del camino de carga"],
  ["Verificación", "rev. D", "FEM modal y estático + factores dinámicos de la lijadora y del choque", "v2 no verificaba la vibración (S4)"],
  ["Presupuesto de masa", "v2 + rev. D", "Ítems que faltaban; incertidumbre por fuente", "La carcasa estaba subestimada y faltaban unos 29 g"],
  ["Energía", "v2 (equipo)", "2 celdas 18650 (2S1P)", "Coincide con el subsistema eléctrico y entra con margen"],
], [1.6, 0.9, 3.3, 3.6]));
C.push(Nota("De la revisión D quedan como alternativa —si los organizadores exigieran que el payload se separe del contenedor— el contenedor separado, el bastidor de carbono y G10, la cola en V con servo y la llave de bayoneta. Toda esa verificación está en el repositorio."));

// ================================================================ 1
C.push(H1("1. Marco normativo y condiciones de contorno"));
C.push(...tabla(["Req.", "Requisito", "Especificación", "Impacto en el diseño (rev. E)"], [
  ["C1 / C2", "Integración y eyección", "Dentro del cohete; sale con la carga de eyección", "Cilindro liso Ø90 mm, sin salientes; ranuras de los largueros enrasadas"],
  ["C3", "Fase 1 (paracaídas)", "Despliegue automático, 15 ± 3 m/s", "Paracaídas plano Ø233 mm con ventana Ø40 mm en la copa superior"],
  ["C4", "Fase 2 (80 % del apogeo)", "Otro sistema de descenso, 5 ± 3 m/s", "Se suelta el paracaídas y se abre la vela Rogallo; espiral pasiva"],
  ["C6 / C7", "Video cenit y nadir", "Toda la secuencia de descenso", "Ventana de nadir Ø14 en M1; cámara de cenit inclinada 35° en M4"],
  ["C8 / E8 / E9", "Baliza", "Audible, batería e interruptor propios", "Bahía 1, acceso por orificio ≤ 10 mm"],
  ["S1", "Masa", "500 ± 10 g", "448,6 g secos + 51,4 g de lastre y margen"],
  ["S2 / S3", "Dimensiones", "Ø 90 mm; largo 200–250 mm", "Ø 90 × 240 mm (cuerpo de 220 mm + copa de 20 mm)"],
  ["S4 / S5", "Vibración y choque", "15 G; 30 G", "Verificado por FEM: lijadora con el CanSat parado, 15 G cuasi-estático y choque de 30 G"],
  ["S6", "Pared exterior", "≥ 2 mm si es impresa; no debe flexionar", "La carcasa es laminada, no impresa: la regla de 2 mm no aplica. La rigidez se verifica por FEM"],
  ["S7", "Deslizamiento", "Debe salir libremente del cohete", "Superficie lisa; largueros dentro de la envolvente"],
  ["M1 / M2", "Mecanismos", "Sin calor expuesto; mantener la configuración", "Nicrom dentro de una cápsula cerrada; trinquete de bloqueo de los largueros"],
], [1.0, 1.7, 2.6, 4.1]));
C.push(Nota("Corrección respecto de v2: el Apéndice A solo tiene M1 y M2 (v2 cita M1–M3)."));

// ================================================================ 2
C.push(H1("2. Fase 1: paracaídas primario (C3)"));
C.push(P("Se mantienen las ecuaciones de v2 (caída libre axial del cilindro, C_d = 0,86 según Hoerner para L/D = 2,44; v_libre = 38,3 m/s; Re entre 9 × 10⁴ y 2,3 × 10⁵). Lo que cambia es la **densidad de diseño**: v2 usa la atmósfera estándar a nivel del mar (1,225 kg/m³). En el sitio, sumando la altura de apertura (unos 700 m), es 1,15 kg/m³, y con menos densidad se baja más rápido."));
C.push(...ec([
  "(C_d·A)_tot = 2·W / (ρ·v²) = 2·4,905 / (1,15·15,0²) = 0,03791 m²",
  "(C_d·A)_para = 0,03791 − (C_d·A)_cil = 0,03791 − 0,00547 = 0,03244 m²   →   S₀ = 0,03244 / 0,78 = 0,0416 m²",
  "D_ext = √(4·(S₀ + A_ventana)/π) = 234 mm  →  se adopta D_ext = 233 mm con ventana Ø40 mm",
], "(Ec. 2.1)"));
C.push(...tabla(["Caso", "C_d0", "Masa", "Velocidad [m/s]"], [
  ["Nominal en el sitio (ρ = 1,15)", "0,78", "500 g", "15,0"],
  ["Banda de diseño", "0,70–0,86 (± 10 %)", "490–510 g", "14,3–15,9"],
  ["A nivel del mar (ρ = 1,225)", "0,78", "500 g", "14,6"],
  ["Paracaídas de v2 (Ø226) en el sitio", "0,78", "500 g", "15,4"],
], [3.4, 2.0, 1.5, 2.0], { alin: [null, "center", "center", "center"] }));
C.push(P("Se mantiene la elección de v2: **paracaídas plano con ventana central**. La ventana reduce el balanceo a menos de ±8°, y el cruciforme tiene más riesgo de enredo en una eyección rápida. Masa de 8,5 g (tela de 1,5 g, líneas y giratorio)."));
C.push(H2("2.1 Cargas sobre el anclaje"));
C.push(P("v2 calcula la carga de apertura en 12,2 N (20 m/s, factor de choque 1,4), lo cual está bien para el vuelo. Pero el **ensayo de caída** de la competencia (cuerda atada al punto de anclaje del paracaídas, caída de 61 cm) carga ese anclaje con unos 30 G. La carga de diseño es:"));
C.push(...ec([
  "F_caída = m · 30 · g · FAD = 0,500 · 30 · 9,81 · 1,8 = 265 N",
  "Por varilla (brida de 3 ramales a los extremos de las 4 varillas): 66 N  →  σ_M3 = 66 / 5,03 = 13,2 MPa  (MS = +13)",
  "Pasador de liberación Ø3 de acero, corte doble: τ = 265 / (2·π·1,5²) = 18,7 MPa  (MS = +10)",
], "(Ec. 2.2)"));
C.push(P("[[Condición de diseño:]] el lazo de Dyneema (180 N de rotura) **no puede estar en el camino de carga**. Con 265 N se cortaría en el ensayo de caída. El lazo solo retiene el pasador, que trabaja a corte; la brida va a las varillas, no a la tapa M5."));

// ================================================================ 3
C.push(H1("3. Fase 2: planeador de vela Rogallo (C4)"));
C.push(P("Se mantienen la geometría y las ecuaciones de planeo helicoidal de v2: quilla de 190 mm sobre el lomo del cilindro, largueros de 225 mm con flecha de 52°, envergadura de 425 mm, S = 0,0670 m², alargamiento 2,69, holgura de la tela (billow) del 8,2 % y altura de inflado de 31 mm. Las cuentas de v2 son correctas: V = 8,71 m/s, V_z = 5,03 m/s y R = 11,0 m."));
C.push(P("La revisión E agrega la **incertidumbre**. v2 usa toda la sustentación de vórtice de Polhamus (K_v = π) con α = 28°, en una vela flexible de 52° de flecha, cerca del ángulo en que el vórtice se rompe. Por eso se repite el cálculo con una fracción f de la sustentación de vórtice y con las dos densidades:"));
C.push(...tabla(["Fracción de vórtice f", "C_L", "C_D", "γ", "V_z ρ = 1,225", "V_z ρ = 1,15", "Radio de la espiral"], [
  ["1,0 (v2)", "1,42", "0,91", "35,5°", "5,05 m/s", "5,22 m/s", "11,0–11,7 m"],
  ["0,5 (rev. D)", "1,11", "0,75", "36,8°", "5,84 m/s", "6,02 m/s", "13,3–14,2 m"],
  ["0,3 (pesimista)", "0,99", "0,69", "37,5°", "6,26 m/s", "6,46 m/s", "14,6–15,5 m"],
], [2.0, 0.8, 0.8, 0.8, 1.4, 1.4, 1.6], { alin: [null, "center", "center", "center", "center", "center", "center"] }));
C.push(P("En todos los casos el descenso queda dentro de 5 ± 3 m/s: **entre 5,1 y 6,5 m/s**. El margen hacia el límite de 8 m/s es de 1,5 m/s en el peor caso."));
C.push(H2("3.1 Estabilidad en cabeceo (no estaba calculada en v2)"));
C.push(P("v2 afirma una estabilidad pendular pasiva, pero el centro de gravedad queda apenas unos 45 mm debajo de la quilla: casi no hay efecto péndulo, y sin cola la estabilidad depende de dónde quede el centro de gravedad respecto del punto neutro. En un ala delta esbelta, el punto neutro está entre el 55 % y el 67 % de la quilla desde el ápice. Con el ápice en x = 14 mm, el punto neutro queda en **x = 119–141 mm** desde la cara de nadir. El centro de gravedad de diseño de v2 (95–105 mm) da un **margen estático del 10 al 21 % de la quilla**: estable."));
C.push(P("[[Pendiente:]] sin cola, el ángulo de equilibrio (α ≈ 28°) depende de la posición del centro de gravedad y de la holgura de la tela. Se fija con ensayos de lanzamiento de la vela, moviendo el lastre. Los 51 g de margen de masa alcanzan para correr el centro de gravedad unos 10 mm."));
C.push(P("Guiado: se mantiene el de v2, totalmente pasivo. La espiral de 25° se induce con 4 mm de holgura extra en el lóbulo izquierdo o con topes asimétricos de 53° y 51°."));

// ================================================================ 4
C.push(H1("4. Estructura primaria y verificación"));
C.push(H2("4.1 Estudio de compromiso"));
C.push(...tabla(["Criterio", "A · Monocasco impreso", "B · Esqueleto M3 + carcasa PETG 2 mm (v2)", "C · Esqueleto M3 + carcasa laminada (rev. E)"], [
  ["Modo lateral, CanSat parado", "≈ 120 Hz (rev. B, impreso)", `${D.f_petg.z.toFixed(0)} / ${D.f_petg.y.toFixed(0)} Hz`, `${D.f_lam.z.toFixed(0)} / ${D.f_lam.y.toFixed(0)} Hz`],
  ["Ensayo de la lijadora (200–233 Hz)", "Falla", "[[Falla: MS −0,55]]", "Pasa: MS +15"],
  ["Masa de la carcasa", "≈ 160 g", "163 g (v2 decía 139 g)", "75 g"],
  ["Masa sin lastre del CanSat", "—", `${f1(D.masa_v2_petg_sin_lastre)} g (no cierra en 500 g)`, `${f1(D.seco)} g (51 g de margen)`],
  ["Requisito S6", "Cumple", "Cumple", "No es impresa: la regla de 2 mm no aplica; la rigidez se verifica por FEM"],
  ["Radio y GNSS", "Transparente", "Transparente", "Vidrio arriba (x > 130 mm) transparente; el carbono de abajo es conductor"],
  ["Fabricación", "Una impresión larga", "Impresión + ranuras", "Laminado manual sobre mandril de Ø88 + post-curado > 60 °C; ranuras cortadas y reforzadas"],
], [2.0, 2.0, 2.6, 2.8], { sel: 3 }));
C.push(H2("4.2 Zonificación interna (v2, con una regla nueva)"));
C.push(...tabla(["Estación x", "Bahía / mamparo", "Contenido"], [
  ["0–35 mm", "Bahía 1 (nadir) + M1 (fondo)", "Cámara de nadir con ventana Ø14 + lente; baliza con batería e interruptor propios"],
  ["35–105 mm", "Bahía 2 + M2 puente (x = 85)", "Pack 2 × 18650 con lengüetas soldadas; encastre de los largueros y topes"],
  ["105–175 mm", "Bahía 3 (aviónica) + M3", "PCB principal, GNSS, radio de 915 MHz, interruptor general"],
  ["175–220 mm", "Bahía 4 (cenit) + M4", "Cámara de cenit inclinada 35°; cápsula de nicrom; paneles solares en el lomo"],
  ["220–240 mm", "Bahía 5 (copa) + M5 (tapa)", "Paracaídas Ø233 mm; resorte expulsor de la tapa; brida a las varillas"],
], [1.3, 2.6, 5.5]));
C.push(P("[[Regla nueva:]] las antenas de radio y GNSS van por **encima de x = 135 mm**, bajo el tramo de vidrio. El tramo de carbono (x < 130 mm) es conductor y las taparía."));
C.push(H2("4.3 Modelo de elementos finitos"));
C.push(P("Se usa el mismo procedimiento que en la revisión D, con CalculiX y tetraedros cuadráticos. El modelo incluye:"));
C.push(B("Carcasa Ø90 × 240 mm con las dos ranuras pasantes de 6 × 192 mm para los largueros."));
C.push(B("Mamparos M1–M5 de PETG con 40 % de relleno (rigidez y densidad efectivas)."));
C.push(B("4 varillas M3 de aluminio 6061 pasantes."));
C.push(B("Los equipos como masa repartida en el mamparo o la carcasa que los sostiene. Total: 500 g."));
C.push(B("Laminados ortótropos en ejes cilíndricos: carbono-epoxi [0/90, ±45, 0/90] y vidrio-epoxi 0/90."));
C.push(P("Apoyo: base fija, como en el ensayo de la lijadora, con el CanSat parado y sujeto por la base. Malla gruesa (unos 260 000 nodos) para comparar variantes; antes del CDR se repite con malla fina."));
C.push(...tabla(["Variante", "Modo 1", "Modo 2", "Modo 3", "Primer modo axial"], [
  ["B · carcasa PETG 2 mm (v2)", "161 Hz (lateral z, 61 %)", "172 Hz (lateral y, 58 %)", "400 Hz (torsión)", "> 550 Hz"],
  ["C · carcasa laminada (rev. E)", "349 Hz (lateral z, 54 %)", "370 Hz (lateral y, 52 %)", "489 Hz (axial, 15 %)", "489 Hz"],
], [2.6, 2.0, 2.0, 1.8, 1.4], { alin: [null, "center", "center", "center", "center"] }));
C.push(H2("4.4 Casos de carga y método"));
C.push(...tabla(["Caso", "Carga", "Requisito"], [
  ["CE-15", "15 G cuasi-estático en x, y, z", "S4"],
  ["Lijadora (parado)", "Plato orbital a(f) = 29 G·(f/233)². Si el modo lateral queda debajo de 233 Hz, el arranque y el frenado lo cruzan (respuesta transitoria, ζ = 2 %); si queda encima, marcha sostenida a 233 Hz. Axial: 29 G", "S4 (ensayo de la competencia)"],
  ["CH-30", "Semiseno de 30 G, factor de espectro de choque 1,7 (51 G) en x, y, z", "S5"],
  ["Caída 61 cm", "265 N sobre el anclaje del paracaídas (sección 2.1)", "S5 (ensayo de la competencia)"],
], [1.6, 6.0, 1.8]));
C.push(P(`Método: tensiones de 1 G del modelo en cada eje × aceleración equivalente del caso. MS = σ_adm / (FS · σ) − 1. FS = 2,0 en impresos (entre capas cuando la carga las cruza), 1,5 en laminados y 1,25 en metales. Se informa el percentil 99,9 de cada pieza y, entre paréntesis, el pico de un solo elemento. Aceleración equivalente de la lijadora: con PETG, ${D.aeq_petg.y.toFixed(0)} G (pasa por la resonancia); con el laminado, ${D.aeq_lam.y.toFixed(0)} G (por encima de la resonancia).`));
C.push(H2("4.5 Márgenes de seguridad"));
const filaMS = (f) => [f[0], `${fmtMS(f[1])} (${ms(f[1][1])})`, `${fmtMS(f[2])} (${ms(f[2][1])})`, `${fmtMS(f[3])} (${ms(f[3][1])})`];
C.push(P("**C · Revisión E (carcasa laminada):** todos los márgenes son positivos."));
C.push(...tabla(["Pieza", "CE-15", "Lijadora (parado)", "CH-30"], D.lam.map(filaMS), [3.2, 2.0, 2.2, 2.0], { alin: [null, "center", "center", "center"] }));
C.push(P("**B · v2 (carcasa PETG de 2 mm):** no pasa el ensayo de la lijadora."));
C.push(...tabla(["Pieza", "CE-15", "Lijadora (parado)", "CH-30"], D.petg.map(filaMS), [3.2, 2.0, 2.2, 2.0], { alin: [null, "center", "center", "center"] }));
C.push(H2("4.6 Cálculos manuales de v2, revisados"));
C.push(B("**Varillas M3 a 30 G** (v2: 7,3 MPa, FS 32,8): correcto. El FEM también da márgenes amplios (+28 en CH-30)."));
C.push(B("**Mamparo M2 a 30 G** (v2: 17,4 MPa, FS 2,59): v2 usa 45 MPa, la resistencia del PETG macizo, pero el mamparo tiene 40 % de relleno (unos 20 MPa efectivos). Con la viga simplemente apoyada de v2, el FS bajaría a 1,15. El FEM, que lo apoya en las varillas y en la carcasa como es en realidad, da MS = +4,3 en CH-30: la viga de v2 era muy conservadora en el apoyo pero optimista en el material."));
C.push(B("**Viga puente y largueros de carbono del ala** (v2: FS 5,8 y 7,1): correctos; no cambian."));
C.push(B("**Carcasa a compresión** (v2: 0,27 MPa): irrelevante; lo que dimensiona la carcasa es la flexión en la resonancia lateral, que v2 no calculaba."));

// ================================================================ 5
C.push(H1("5. Mecanismos de estiba, retención y despliegue (M1, M2)"));
C.push(P("Se mantiene el diseño de v2 con un solo cambio en el camino de carga del paracaídas:"));
C.push(B("**Estiba:** largueros de carbono plegados en las ranuras laterales, dentro de Ø90 mm (S7). La vela va plegada en acordeón bajo una cubierta dorsal retenida por el mismo lazo."));
C.push(B("**Liberación:** lazo de Dyneema Ø0,40 mm (180 N de rotura) que retiene las puntas de los largueros y el pasador de liberación del paracaídas. Lo funde un nicrom AWG 30 de 3 espiras dentro de una cápsula cerrada de PTFE (pulso de 3,7 V, 2,2 A durante 0,7 s, comandado por MOSFET al detectar el 80 % del apogeo)."));
C.push(B("**Resortes de torsión:** dos por larguero, AISI 302 de 1,8 mm, diámetro medio de 10 mm, 16,4 espiras. Tensión de 762 MPa (FS 1,44 contra fluencia; contra la resistencia del alambre de resorte el margen es mayor). Par de 405 N·mm abierto contra 268 N·mm de cierre aerodinámico."));
C.push(B("**Tope y trinquete:** hombro en M2 a 14 mm del eje, aplastamiento de 2,0 MPa; trinquete elástico que impide el cierre (M2)."));
C.push(B("**Cambio de la revisión E:** la brida del paracaídas va a los extremos de las varillas, y el lazo de Dyneema solo retiene el pasador (sección 2.1)."));

// ================================================================ 6
C.push(H1("6. Presupuesto de masa (S1)"));
const filasM = [];
const subs = [];
for (const [cat, items] of D.masa) {
  let m = 0, u2 = 0;
  for (const [it, n, mm, u, src] of items) { filasM.push([it, String(n), f1(mm), "±" + f1(u), src]); m += mm; u2 += u * u; }
  subs.push(filasM.length);
  filasM.push([`${cat} — subtotal`, "", f1(m), "±" + f1(Math.sqrt(u2)), ""]);
}
filasM.push(["Masa seca", "", f1(D.seco), "±" + f1(D.rss) + " (RSS)", ""]);
filasM.push(["Lastre y margen de ajuste (arandelas sobre las varillas en M1/M2)", "", f1(D.lastre), "", "Cierre a 500 g"]);
filasM.push(["TOTAL (S1: 500 ± 10 g)", "", "500,0", "", "Cumple"]);
C.push(...tabla(["Componente", "Cant.", "Masa [g]", "Incert. [g]", "Fuente"], filasM, [4.6, 0.7, 1.0, 1.4, 2.6],
  { alin: [null, "center", "right", "right", null], sub: [...subs, filasM.length - 3, filasM.length - 1] }));
C.push(P(`Correcciones respecto de v2: la carcasa de PETG de 240 mm pesa 163 g (v2: 139 g); faltaban la tapa con su resorte, la cubierta de la vela, los tornillos y el adhesivo, las sillas de las celdas y la lente de nadir (unos 29 g en total); y las incertidumbres de ±3 % eran optimistas para piezas impresas y laminadas. Con la carcasa laminada, la masa seca es ${f1(D.seco)} g ± ${f1(D.rss)} g (RSS; ±${f1(D.lineal)} g en el peor caso lineal).`));
C.push(P("**Métodos de corrección:**"));
C.push(B("Si la masa medida es menor de 495 g: agregar arandelas de acero sobre las varillas en M1 y M2. Corren el centro de gravedad hacia la nariz, lo que también ayuda a la estabilidad (sección 3.1)."));
C.push(B("Si es mayor de 505 g: reducir el lastre. Si no alcanza, bajar el relleno de los mamparos del 40 % al 25 % (−14 g) y acortar los arneses (−5 g)."));
C.push(B("No se toca la carcasa: su espesor sale del ensayo de la lijadora, no de la masa."));

// ================================================================ 7
C.push(H1("7. Pendientes y ensayos antes del CDR"));
C.push(...tabla(["Pendiente", "Por qué", "Cómo se cierra"], [
  ["Propiedades del laminado", "El modo de 349 Hz depende del módulo real de carbono y vidrio con laminado manual", "Probetas y un tubo de prueba: medir espesor, módulo y masa; post-curado > 60 °C (ensayo térmico)"],
  ["Bordes de las ranuras", "Concentración de tensiones en los extremos de las ranuras de 192 mm", "Cinta de vidrio en los bordes; FEM con malla fina"],
  ["Modo y amortiguamiento reales", "El ensayo se analizó con ζ = 2 %", "Ensayo con la lijadora sobre el prototipo con acelerómetro: verificar que no haya resonancia por debajo de 233 Hz"],
  ["Anclaje del paracaídas", "265 N en el ensayo de caída", "Ensayo de caída de 61 cm; confirmar que el lazo de Dyneema no carga"],
  ["Equilibrio y estabilidad de la vela", "Sin cola, el ángulo de equilibrio depende del centro de gravedad y de la holgura de la tela", "Lanzamientos de la vela con lastre móvil; medir la velocidad de descenso"],
  ["Cámaras en las dos fases", "En planeo el eje del cuerpo queda casi horizontal", "Verificar los campos de visión a cenit y nadir con la actitud de planeo (γ ≈ 36°)"],
  ["Masa de la electrónica", "Asignaciones de EPS y C&DH", "Pesar las placas reales; actualizar el lastre"],
], [2.2, 3.4, 3.8]));

// ================================================================ documento
const doc = new Document({
  creator: "Equipo Hermes", title: "PDR v3 — Descenso, estructura, mecanismos y masa",
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 26, bold: true, color: AZUL }, paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Arial", size: 22, bold: true, color: AZUL }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "vinetas", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 260 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 800, hanging: 260 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [
      new TextRun({ text: "PDR-STR-REC-2026-v3 · Equipo Hermes · página ", size: 16, color: GRIS }),
      new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GRIS })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(process.argv[3], b); console.log("ok", process.argv[3]); });
