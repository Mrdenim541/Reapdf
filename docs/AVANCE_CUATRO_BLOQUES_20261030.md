# Avance conjunto de los bloques 1–4 · 30 de octubre de 2026

Trabajo sobre `8e4dc3b`, sin instalador ni portable nuevo. La referencia corresponde a 0.43 recuperada y sus mejoras posteriores, no a la fuente histórica 0.55. Fuentes y pruebas usan documentos sintéticos; no se han añadido PDFs personales a Git.

## Resultado y criterio de cierre

Se implementaron herramientas en los cuatro bloques solicitados. **Los cuatro bloques amplios no están cerrados al 100 %.** La agrupación anterior incluía, entre otras cosas, XFA, JavaScript general, conversión Office general y accesibilidad integral: estas capacidades no quedan implementadas por añadir los subconjuntos de este avance ni por superar miles de pruebas sintéticas. No se trasladan sus pendientes a los bloques 5–8 para aparentar cierre.

La matriz mantiene diecisiete áreas, pesos y alcance. Las nuevas capacidades justifican una mejora de madurez; las pruebas Windows, Acrobat/Nitro, lector de pantalla y aceptación personal continúan pendientes.

## Bloque 1 · Fuentes y edición

- **Editar → Preparar fuentes variables** inspecciona los ejes incrustados y sus valores predeterminados. Tras revisión explícita, genera una instancia estática compatible sin elegir silenciosamente otro peso/ancho.
- Se conserva el orden de glifos y métricas horizontales. El resultado solo se publica si coinciden palabras/posiciones y renderizado de todas las páginas en dos escalas acotadas. Hay pruebas con TrueType/gvar y CFF2/VarStore/blend reales; después se edita texto con el motor original.
- El cambio crea una versión reversible y puede guardarse desde Qt. Si hay diferencias, se rechaza completo: una fuente variable con hinting que cambie el renderizado no se fuerza a estática.
- Type3 añade patrones de trazo discontinuo numéricos acotados y clipping de caminos W/W*, con pen/cajas comprobados. Los programas de glifo originales permanecen intactos.

Límites: hasta 50 páginas, 32 programas variables, ocho ejes por programa y 16 MB por fuente/64 MB total. Solo instancia predeterminada explícita; otros ejes/instancias, CFF2 crudo, imágenes/recursos Type3 y FontMatrix no estándar siguen pendientes. También reflujo afín/cambio de fuente y composición con máscaras, mezclas especiales o grupos complejos. Las dos escalas son una comprobación de fidelidad, no una certificación universal de renderizado.

## Bloque 2 · Estructura y accesibilidad

En **Documentos → Etiquetas y orden de lectura → Preparar etiquetas iniciales**:

- **Sugerir tabla por posición** prepara con un clic roles/filas/columnas para páginas con una tabla rectangular alineada y un objeto por celda, sin giro. Se cambia solo el borrador y se exige revisión; diseños mixtos o ambiguos conservan los controles manuales.
- Los roles TH/TD permiten revisar número de tabla, fila, columna, combinaciones rectangulares y ámbito Row/Column/Both del encabezado. Se crea Table/TR/TH/TD con MCID, ParentTree y asociaciones reales. Se rechazan huecos, solapamientos, orden incorrecto y tablas interrumpidas. Un objeto de texto por celda; no se inventan celdas vacías sin contenido.
- Las filas completamente cubiertas por un rowspan conservan su TR vacío. Sus títulos de fila distinguen nodos semánticos para impedir que la deduplicación de objetos PDF los fusione.
- Listas revisadas de hasta seis niveles: L/LI/LBody/P, con niveles consecutivos y orden real. Las viñetas permanecen en el cuerpo; no se crean Lbl separados.
- Los **Forms de solo texto** se revisan como una unidad semántica por aparición, incluidos Forms anidados/compartidos. Se marca su invocación en la página; no se reescriben sus streams ni recursos, ni se afirma reparar MCID internos arbitrarios. Forms mixtos, marcados, cíclicos o con estados no compatibles se rechazan.
- Dividir conserva los atributos Table compatibles, listas anidadas y apariciones Form admitidas; sigue podando ramas de páginas excluidas y reconstruyendo claves. Las estructuras complejas ajenas al subconjunto no se simplifican silenciosamente.

Se conservan píxeles y texto, orden de lectura y proyectos. Límites anteriores de 20 páginas/500 objetos por documento, seis niveles de lista, 100 filas/columnas y auditoría Form de 200 llamadas/ocho niveles/32 MB. Pendientes: estructura general y mixta dentro de Forms, imágenes inline/recortes complejos, enlaces ambiguos, otras anotaciones, tablas con contenido múltiple por celda, etiquetas de viñeta y reparación general/PDF 2. No acredita PDF/UA ni aceptación con lector de pantalla.

## Bloque 3 · Formularios y XFDF

- Se conservan e interpretan como datos AFTime_Format/Keystroke y sus variantes Ex para cuatro formatos acotados de hora. La interfaz explica el patrón y rechaza horas inválidas.
- AFSpecial_Format/Keystroke incorpora código postal, extensión postal, teléfono de diez dígitos e identificador de nueve dígitos, conservando ceros iniciales. Son los formatos estándar de esos ayudantes, no validaciones universales de identificadores personales o teléfonos internacionales.
- Se añaden fórmulas de la forma `event.value = this.getField("A").value * (this.getField("B").value + 2);`, con campos literales, decimales, paréntesis y +/−/×/÷. No se ejecuta JavaScript. Se conservan AA y CO, y se comprueban dependencias, orden, ciclos, fuentes numéricas, división entre cero y resultados intermedios hasta 10¹². Aritmética decimal de 34 dígitos; no equivale al entorno ECMAScript binario completo de Acrobat.
- XFDF importa/exporta respuestas de notas con IRT/RT y estados Review/Marked. Ordena padres antes que hijos, admite entrada desordenada y rechaza ciclos, padres ausentes/de otra página y nombres ambiguos. Reimportar registros idénticos no duplica anotaciones. Si al exportar un padre no es compatible, se omiten sus descendientes y se cuenta la omisión.

Pruebas de valores/apariencias, acciones originales, recálculo dependiente, reapertura, duplicados y fallos atómicos. Límites XFDF de 2 MB/500 anotaciones; respuestas simples en la misma página y RT=R. Pendientes: XFA, JavaScript general, fórmulas/acciones fuera del subconjunto, grafos mixtos con reglas de proyecto, apariencias/fuentes enriquecidas, adjuntos y tipos XFDF restantes. La interoperabilidad comercial sigue sin aceptación externa.

## Bloque 4 · OCR y tablas

En **Convertir y OCR → OCR de región**:

- **Comparar orientaciones OCR** ejecuta cuatro reconocimientos locales a 0/90/180/270°. Muestra texto de cada resultado para que el usuario elija. Solo destaca una sugerencia con margen suficiente; sus recuentos son heurísticos, no puntuaciones de confianza de Tesseract.
- **Sugerir esquinas del escaneo** detecta papel claro contra fondo oscuro, devuelve cuatro puntos ajustables y se abstiene con fondo blanco, bordes tocando la región, bajo contraste o formas irregulares. No cambia la imagen; la corrección geométrica se utiliza después para reconocer.
- **Extraer tabla por región** sugiere cuadrícula sin líneas cuando encuentra espacios consistentes entre columnas en todas las filas. Mantiene revisión/corrección y exportación CSV/Word. Casos de una columna, separación ambigua o filas irregulares se dejan para cuadrícula manual.

Cada análisis mantiene permisos de copia, regiones acotadas, protección de widgets y bloqueo OCR compartido. Orientación: hasta cuatro muestras de 4 MP; esquinas: hasta 640000 píxeles. No añade otro ejecutable OCR ni servicios remotos. Pendientes: detección general de esquinas, perspectiva de tablas, filas multilínea/irregulares, otros idiomas y fidelidad Office general, notas Word partidas y otras variantes documentadas. No convierte las letras escaneadas en texto tipográfico original editable.

## Verificación

**Aprobadas:** 3339 pruebas Python generales (406,76 s), 452 dirigidas incluidas en esa regresión, 128 JavaScript, compilación y recorridos Chromium/Qt Linux. Las dos expectativas incompatibles detectadas en la primera regresión quedaron corregidas antes de repetirla completa.

Ver `validation/four-blocks-20261030/results.json` para resultados finales, comandos, límites y huellas. Los recuentos dirigidos se superponen con la regresión general: no se suman para inflar cobertura. Los recorridos gráficos verifican controles reales y archivos exportados/reabiertos. Qt Linux no sustituye Windows.

## Bloques pendientes

| Bloque | Estado después de esta pasada | Falta para cierre |
|---|---|---|
| 1. Edición avanzada | Ampliado; cierre general pendiente | Instancias/ejes no predeterminados y fuentes/estados complejos descritos arriba; corpus externo. |
| 2. Accesibilidad y estructura | Ampliado; cierre general pendiente | Semántica y reparación general, contenido mixto, lector de pantalla y PDF/UA. |
| 3. Formularios, anotaciones e intercambio | Ampliado; cierre general pendiente | XFA/JS general, variantes restantes y aceptación Acrobat/Nitro. |
| 4. OCR y Office | Ampliado; cierre general pendiente | Diseños/escaneos generales, idiomas y conversión Office de fidelidad amplia. |
| 5. Firmas, seguridad y estándares | Pendiente de ampliación/cierre | TSA/revocación/LT/LTA/tokens, censura compleja, PDF/X y preflight. |
| 6. Planos, vinculación, portfolios y capas | Pendiente de ampliación/cierre | Ángulos/curvas/intersecciones, revisiones complejas, carpetas/esquemas y capas avanzadas. |
| 7. Windows y estabilidad | Pendiente de verificación y correcciones | Ejecutable Windows limpio, DPI/asociaciones/impresión, estrés, recuperación y prueba personal. |
| 8. Servicios e IA | Sin implementación | Proveedores, costes, licencias, sincronización/revisión/firmas remotas y asistencia. |

Siguiente prioridad técnica: resolver composición/fuentes complejas y casos representativos de los cuatro primeros bloques; reservar Windows/interoperabilidad y aceptación para sus pruebas reales. No repetir como pendientes las instancias predeterminadas compatibles, Type3 dash/clipping, tablas semánticas revisadas, listas anidadas, Forms de texto por aparición, horas/formatos especiales, expresiones aritméticas acotadas, hilos XFDF y sugerencias OCR implementadas aquí. Modelo recomendado: **6.1 Sol, razonamiento medio**; auditoría arquitectónica puntual de XFA/JS y composición puede beneficiarse de Astra antes de ampliar esos motores.
