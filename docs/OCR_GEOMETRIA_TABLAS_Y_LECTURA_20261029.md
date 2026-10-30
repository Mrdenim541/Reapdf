# OCR geométrico, combinaciones de tablas y revisión de lectura

Bloque previsto en el plan, completado con ampliaciones concretas sobre el OCR regional, las cuadrículas y la edición de etiquetas existentes. Fecha local del usuario: 29 de octubre de 2026. No se entrega instalador ni portable intermedio.

## Funciones nuevas

1. **Inclinación manual de escaneos.** OCR por región con ángulo de −15 a 15 grados y contorno girado visible antes de aplicar. Se reconoce la imagen rectificada y se devuelve el texto a las coordenadas originales; no se endereza ni sustituye la imagen del PDF.
2. **Perspectiva de cuatro esquinas.** Puntos arrastrables sobre la página, validación de convexidad, posición, aristas y presupuesto. La rectificación usa una homografía y el mismo mapa coloca las palabras reconocidas. Se comprobó la coincidencia entre imagen y coordenadas con puntos de referencia bajo perspectiva marcada. Se usa Pillow 13.0.0 fijado en requisitos; la dependencia Windows x64 CPython 3.13 tiene wheel descargado y SHA-256 registrado, sin ejecutar Windows ni ensamblar un paquete.
3. **Conservación del original.** Texto invisible, búsqueda/copia, rechazo de texto previo y campos, operaciones reversibles y proyectos. Las pruebas comparan los píxeles antes/después, incluidas inclinación, giro y CropBox. Los errores no publican una región parcialmente reconocida.
4. **Combinaciones rectangulares revisadas.** Selección por fila/columna inicial y final, reunión de todo el contenido en la celda principal, edición posterior y separación explícita. Se impiden solapamientos, texto oculto y celdas fuera de límites. Redistribuir la cuadrícula retira las combinaciones y requiere confirmar si hay correcciones.
5. **Exportación Word con estructura de tabla.** `gridSpan` y `vMerge` conservan combinaciones horizontales/verticales, con anchos coherentes. Un encabezado repetido no puede atravesar filas del cuerpo. CSV conserva texto en la celda principal y las cubiertas vacías, ya que no representa combinaciones; mantiene protección contra fórmulas. No se detectan automáticamente las combinaciones de la tabla original.
6. **Vista de lectura.** Texto extraído con rutas de estructura de MuPDF, ordenado por índices de etiquetas hermanas, lista seleccionable y área remarcada sobre la página. Se verificó que invertir el orden de etiquetas cambia la vista aunque el orden de pintado permanezca igual. El contenido sin etiqueta conserva su posición de flujo y queda señalado; no se le asigna un xref por semejanza visual.
7. **Semántica de etiquetas existentes.** Cambiar entre P/H/H1–H6 estándar y definir idioma BCP 47 básico por etiqueta con padre verificable. Se conservan MCID, contenido y apariencia. Roles personalizados y espacios de nombres PDF 2 no se convierten silenciosamente. No crea etiquetas en documentos sin estructura.
8. **Interfaz distribuida y uso propio.** Vista de lectura y edición de etiquetas en secciones separadas; corrección de una superposición del pie del diálogo de tablas que impedía pulsar un botón. Recorridos Chromium y ventana Qt propia incluyen OCR, guardar PDF/proyecto, revisión/corrección de combinaciones y Word, y cambio de encabezado con guardado nativo.

## Verificación

**3080 pruebas Python generales aprobadas; 163 dirigidas finales y 25 de preparación/distribución de fuentes aprobadas. 123 pruebas JavaScript y compilación aprobadas; Chromium y Qt Linux aprobados.** Resultados definitivos y hashes en `validation/geometry-tables-reading-20261029/results.json` y sus registros. La regresión Python general precede al ajuste final del muestreo proyectivo y su nueva prueba de puntos; la suite dirigida final verifica esa versión, junto con proyectos, tablas, estructura y escritorio. Sus resultados se solapan y no se suman. JavaScript, compilación, Chromium y Qt Linux se ejecutaron; Windows y aceptación personal siguen pendientes. Solo se usaron muestras sintéticas públicas.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_scan_geometry.py tests/test_table_regions.py tests/test_structure_preflight_regions.py tests/test_reading_preview.py tests/test_table_spans.py tests/test_projects.py tests/test_desktop.py -q
.venv/bin/python -m pytest tests/test_portable.py tests/test_local_workspace.py -q
node --test tests/*.mjs
npm run build
node scripts/smoke_geometry_tables_reading.mjs
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu' .venv/bin/python -m scripts.smoke_geometry_tables_reading_qt
```

## Límites prácticos

**OCR:** corrección manual y una región por operación geométrica, hasta 16 MP y 8192 px por dimensión; idiomas inglés/español verificados, 150/200/300 ppp y orientaciones ortogonales. No existe detección automática de ángulo/esquinas ni garantía de reconocimiento. Una homografía rectifica la imagen; cada palabra invisible se aproxima mediante una matriz afín local, por lo que bajo perspectiva muy marcada su contorno no coincide exactamente en las cuatro esquinas. El informe conserva las esquinas mapeadas. Copiar texto inclinado puede introducir saltos entre palabras. No hace editable la tipografía impresa de un escaneo ni declara confianza OCR. No se modifica la imagen original para mejorar su apariencia.

**Tablas:** combinaciones manuales rectangulares sobre cuadrícula revisada; 100 filas, 30 columnas, 3000 celdas, 4000 caracteres por celda y 100000 totales. Separar mantiene el texto reunido en la celda principal; no reconstruye las celdas anteriores. No se incorporan detección automática de combinaciones, tablas irregulares, sin líneas ni perspectiva OCR de tablas. Las combinaciones no alteran el PDF fuente; se usan en la revisión y exportación, sin sesión de tabla persistente en proyectos.

**Lectura:** hasta 500 bloques/100000 caracteres por página y 32 niveles. Los índices proceden del intérprete de MuPDF; mezclas de contenido etiquetado/sin etiquetar, referencias especiales, figuras sin texto y árboles inconsistentes necesitan revisión. No valida calidad semántica, lector de pantalla ni PDF/UA, y no crea/repara ParentTree/MCID generales. Cambios de rol/idioma y orden son versiones reversibles del PDF y sobreviven a guardado; no sustituyen validación externa.

No se comprobó interoperabilidad en Acrobat/Nitro/Word ni Windows, DPI o impresora física. Ninguna descarga de dependencia equivale a un ejecutable Windows probado. Las obligaciones de licencias y aceptación final siguen en la matriz general.

## Avance y continuación

**79,61 % estimado del programa completo (≈80 %), antes 78,97 %.** Se mantienen el alcance y los diecisiete pesos: interfaz 95→96 (+0,07), OCR/conversión 85→88 (+0,27), accesibilidad 50→60 (+0,30). No se añaden puntos por preparar herramientas, requisitos, pruebas o documentación. Estimación de madurez, no paridad certificada con Acrobat.

Siguiente bloque recomendado: detección automática de combinaciones en tablas, creación controlada de etiquetas/MCID en documentos sin estructura y fuentes originales restantes. No volver a anunciar como pendientes el OCR geométrico manual, las combinaciones revisadas ni los roles/idiomas existentes. Windows y aceptación personal siguen aplazados y deben resolverse antes de una entrega candidata.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
