# Imágenes/enlaces etiquetados, inclinación automática y trazos Type3

Bloque previsto en el plan, fecha local del usuario 29 de octubre de 2026. Se amplían objetos y comportamientos nuevos sobre las funciones anteriores; no se entrega paquete intermedio.

## Cambios incorporados

1. **Imágenes por aparición.** El etiquetado inicial acepta imágenes XObject directas y compara la secuencia de llamadas con la representación. Cada aparición tiene selección y alternativa independiente aunque reutilice el mismo recurso. El usuario elige Figure con alternativa o Artifact decorativo. No convierte el bitmap en texto ni altera sus bytes.
2. **Enlaces simples asociados al contenido.** Se admite un enlace HTTP/HTTPS o a página interna cuando cubre exactamente un objeto completo de texto y no comparte su contenido con otro enlace. Se revisa su nombre y se crea Link con MCID y OBJR a la anotación original; StructParent y ParentTree enlazan ambos sentidos, y Tabs/S adopta el orden estructural. Se conserva destino y geometría; Contents recibe el nombre revisado.
3. **Revisión y persistencia.** Alternativas y nombres se muestran junto al objeto resaltado en la página. Las imágenes decorativas no crean un Figure ficticio ni consumen MCID. Se exige revisar todas las páginas. PDF, proyecto y deshacer/rehacer conservan etiquetas, alternativas y enlaces. Imágenes recortadas fuera de página, Forms y asociaciones ambiguas se rechazan; no se publican resultados parciales. Los contadores distinguen objetos etiquetados e imágenes decorativas.
4. **Sugerencia de inclinación OCR.** Detectar inclinación analiza una región con un perfil horizontal acotado, búsqueda gruesa de −15 a 15° y refinamiento de 0,1°. La orientación de 0/90/180/270° sigue siendo explícita y se considera en el análisis. Zonas vacías, oscuras o ambiguas no obtienen ángulo. El análisis es de solo lectura: propone el contorno para revisión y el OCR se ejecuta después, conservando la imagen original. No presenta la concentración de líneas como confianza de reconocimiento.
5. **Trazos Type3.** Los programas verificados admiten S/s/B/B*/b/b*, cm internos no singulares y parámetros explícitos de pluma. Se verifica todo el contorno con expansión conservadora por anchura, transformaciones, uniones/miter y extremos cuadrados. Los estados no se infieren del documento externo. d0 exige colores literales correspondientes antes de pintar; d1 continúa sin operadores propios de color. CharProcs, mapas, anchuras y recursos originales permanecen intactos.
6. **Asociación y comprobación del texto Type3.** Algunos glifos de trazos aparecen fragmentados y como texto ignorado en las trazas de MuPDF, aunque sus vectores sean visibles. Solo se reúnen cuando un programa Type3 validado, la codificación, el origen y un objeto original coinciden. Cada carácter requiere una traza única con glifo/posición/visibilidad coherentes. Tr3 externo y sobreimpresiones ambiguas permanecen protegidos. La selección en página, la detección de colisiones y la verificación del PDF guardado usan esa misma asociación.
7. **Pruebas de aplicación.** Chromium revisó alternativas/imagen decorativa/nombre de enlace, PDF/proyecto/historial, detección del ángulo y OCR, y edición directa de texto Type3 de trazos con transformación interna. Qt Linux revisó medios/enlace y guardó PDF atómicamente; detectó/revisó el ángulo, reconoció y guardó desde la ventana propia. Se comparan texto, píxeles, programas y destinos originales.

## Validación

**3215 pruebas Python generales aprobadas; 373 dirigidas finales tras el refuerzo de extremo cuadrado anisotrópico. 123 JavaScript, compilación, Chromium y Qt Linux aprobados.** Resultados y hashes definitivos en `validation/media-tags-skew-strokes-20261029/`. La suite general precede al último refuerzo conservador del extremo cuadrado bajo transformación anisotrópica; la dirigida final verifica ese refuerzo junto con fuentes, geometría, composición, imágenes/enlaces e inclinación. Los subconjuntos se solapan y no se suman. Los enlaces estructurales también se comprobaron mediante pyHanko, independientemente del intérprete MuPDF. Solo se utilizaron muestras sintéticas públicas.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_type3_strokes.py tests/test_type3_fonts.py tests/test_colored_type3.py tests/test_affine_text_editing.py tests/test_text_states_compositing.py tests/test_media_tagging.py tests/test_deskew.py -q
node --test tests/*.mjs
npm run build
node scripts/smoke_media_tags_skew.mjs
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu' .venv/bin/python -m scripts.smoke_media_tags_skew_qt
```

Windows, impresora física, interoperabilidad en Acrobat/Nitro, lector de pantalla y aceptación personal no se ejecutaron. No se declara PDF/UA ni se genera instalador/portable.

## Límites actuales

**Etiquetado:** solo documentos inicialmente sin estructura, hasta 20 páginas/200 objetos por página/500 totales/16 MB de contenido. Imágenes directas, hasta 16 MP por aparición y 64 MP total; no imágenes inline, Forms, apariciones cuyo contorno queda fuera de página ni recursos sin asociación verificable. Enlaces HTTP/HTTPS o internos, hasta 100 por página, de un único objeto de texto completo. No enlaza imágenes, varios objetos, destinos remotos/nombrados, acciones adicionales, anotaciones bloqueadas o estructura previa. No repara árboles existentes ni crea listas/tablas semánticas. Las alternativas describen el objeto y deben ser revisadas por la persona; no se generan automáticamente. La modificación del nombre del enlace en este bloque corresponde al etiquetado inicial.

**Inclinación:** sugerencia basada en geometría, no reconocimiento de texto. Muestra de hasta 800 × 800 px, área mínima 40 × 40 pt, rango ±15°. No decide la orientación ortogonal ni corrige perspectiva automáticamente. Fotografías, trazos de planos, columnas, pocas letras y líneas verticales pueden resultar ambiguos o sugerir un ángulo inadecuado: se revisa el contorno y se puede ajustar manualmente. El OCR conserva sus límites de idiomas, resolución, región sin texto previo y geometría afín aproximada por palabra.

**Type3:** FontMatrix estándar .001, recursos internos vacíos, mapas/anchuras y cajas verificables, hasta 2000 operadores por glifo y 16 niveles q/Q. Anchura de pluma positiva ≤1000 unidades, miter explícito cuando se usa y transformaciones acotadas. No dash, clipping, imágenes, texto interno, patrones, estados externos ni FontMatrix general. La expansión conservadora puede rechazar trazos que un intérprete dibujaría; no amplía cajas para forzarlos. No modifica el dibujo o el color de los glifos. Fuentes variables y CFF2 con VarStore siguen pendientes.

## Avance y siguiente bloque

**80,54 % estimado del programa completo (≈81 %)**, antes 80,17 %. Se conservan alcance y diecisiete pesos: texto/imágenes 97,5→97,75 (+0,04 global), OCR/conversión 90→92 (+0,18) y accesibilidad 70→75 (+0,15). No suma puntos por pruebas, documentación o herramientas. Es una estimación de madurez, no paridad certificada con Acrobat.

Siguiente bloque recomendado: listas/tablas semánticas, contenido dentro de Forms y fuentes variables, tras auditar las variantes y delimitar la compatibilidad. No repetir imágenes directas/enlaces simples, inclinación automática revisable ni trazos/cm Type3 verificados como pendientes. Windows y aceptación personal siguen siendo puertas antes de una entrega candidata cercana al 90 %.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
