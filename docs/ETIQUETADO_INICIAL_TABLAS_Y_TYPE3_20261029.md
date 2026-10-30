# Etiquetado inicial, combinaciones automáticas y Type3 con color

Fecha local del usuario: 29 de octubre de 2026. Este bloque amplía los tres trabajos previstos; no repite como nuevos el OCR geométrico manual, las combinaciones manuales ni la edición de etiquetas existentes.

## Trabajos completados

1. **Cuadrículas con separadores parciales.** La opción «Sugerir combinaciones por bordes» localiza segmentos largos, incluidos divisores presentes solo en algunas filas/columnas. Conserva la detección anterior cuando la opción está desactivada. Funciona con texto digital y OCR, así como con páginas giradas.
2. **Sugerencias de combinaciones verificables.** Se mide presencia/ausencia del borde de cada celda y se excluyen las cajas del texto reconocido para que una palabra que cruce un divisor ausente no se confunda con una línea. Solo se sugieren grupos rectangulares con evidencia coherente y borde exterior completo. Bordes ambiguos, grupos en L, contradicciones y regiones abiertas conservan celdas separadas y muestran observaciones. No hay puntuación de confianza OCR inventada.
3. **Revisión y exportación.** Se reúne el texto por posición real dentro de cada combinación, sin ocultar palabras en celdas cubiertas. Las sugerencias aparecen en la cuadrícula, se corrigen o separan con los controles existentes y se exportan con gridSpan/vMerge a Word. La cuenta de palabras que cruzan bordes considera la celda combinada. No se modifica el PDF fuente.
4. **Preparación de etiquetas iniciales.** Para PDFs compatibles sin estructura se identifican objetos de texto directo BT/ET, se construye una estructura temporal y se extraen texto/caja de cada objeto mediante el intérprete de contenido marcado. El usuario revisa cada página, cambia roles a encabezados, selecciona objetos en la vista y ajusta su orden dentro de la página.
5. **Estructura real en el PDF.** Tras revisión explícita se crean StructTreeRoot, Document/Sect/P/H1–H6, MCID por página, ParentTree, StructParents, idioma y MarkInfo. El resto del contenido vectorial queda marcado decorativo, según la revisión exigida. Los bytes internos de los objetos de texto se conservan. Se relee el PDF y se compara texto y representación antes de publicar el resultado.
6. **Persistencia y protección.** Guardado PDF/proyecto y deshacer/rehacer conservan la estructura. Se rechazan fuentes firmadas, permisos insuficientes, estructura existente/parcial, marcas anteriores, imágenes/Forms, enlaces, anotaciones, campos, objetos incompletos, revisiones obsoletas, duplicados y roles fuera del conjunto. No se publican etiquetas parciales para eludir esos límites.
7. **Type3 con relleno de color interno.** Se amplía el programa verificado a d0 con colores literales g/rg/k, valores 0–1 y q/Q balanceados. Conserva CharProcs, mapas, anchuras, recursos y colores internos. La edición en página funciona con giros, matrices afines compatibles y apariciones compartidas de Forms; otras apariciones quedan intactas. Se verifican cambios de texto, conservación del programa y píxeles vecinos. No sustituye la fuente.
8. **Recorridos de aplicación.** Chromium revisó dos páginas, encabezados/orden, creación real de etiquetas, PDF/proyecto e historial; reconoció una tabla escaneada con combinaciones horizontales/verticales, corrigió una celda y exportó Word; editó Type3 de color directamente sobre la página. Qt Linux revisó/creó etiquetas, guardó PDF atómicamente conservando el original y exportó la tabla reconocida mediante diálogo nativo.

## Validaciones

**3150 pruebas Python generales y 123 JavaScript aprobadas; compilación, Chromium y Qt Linux aprobados.** Resultados, registros y hashes en `validation/initial-tags-auto-merges-20261029/`. Se usaron únicamente muestras sintéticas públicas. Las suites dirigidas se solapan con la general y no se suman. Compilación, JavaScript, Chromium y ventana propia Qt Linux comprobados. Windows, interoperabilidad en Acrobat/Nitro/Word, lector de pantalla y aceptación personal no se ejecutaron. No se generó instalador ni portable.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_basic_tagging.py tests/test_auto_table_merges.py tests/test_colored_type3.py tests/test_type3_fonts.py tests/test_table_regions.py tests/test_reading_preview.py -q
node --test tests/*.mjs
npm run build
node scripts/smoke_initial_tags_auto_merges.mjs
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu' .venv/bin/python -m scripts.smoke_initial_tags_auto_merges_qt
```

## Límites conservados

**Tablas:** sugerencias geométricas, no interpretación semántica universal. Se necesitan bordes rectos legibles, segmentos de aproximadamente 18 pt o mayores y separaciones de al menos 3 pt. Hasta 100 filas/30 columnas/3000 celdas, 10000 palabras, 100000 caracteres, 4000 por celda y 16 MP. Texto OCR incorrecto puede afectar tanto contenido como clasificación de bordes: revisión obligatoria. No incorpora tablas sin líneas, grupos no rectangulares, perspectiva de tablas ni una sesión de cuadrícula persistente en proyectos. CSV no representa combinaciones; conserva contenido en la celda principal.

**Etiquetado:** hasta 20 páginas, 200 objetos por página/500 totales, 16 MB de contenido directo, 4000 caracteres por objeto/100000 totales. Se etiqueta por objeto de texto, no por párrafo semántico inferido; algunos PDFs dividen una línea en varios objetos y requieren tratamiento especializado. No admite imágenes, Forms, enlaces, anotaciones, widgets, contenido ya marcado ni árboles parciales/existentes. Los gráficos vectoriales se declaran decorativos solo con revisión de todas las páginas; diagramas significativos requieren otro tratamiento. Puede ordenar dentro de cada página, conservando la secuencia de páginas. No crea listas/tablas semánticas ni certifica PDF/UA. La comprobación de representación se limita a un máximo de 4 MP por página; las muestras también comparan representación original a escala completa.

**Type3:** solamente matriz estándar .001, FontBBox/Widths/ToUnicode verificables, recursos internos vacíos y rellenos vectoriales simples. El d0 exige color literal antes de pintar. No admite imágenes, otros recursos, trazos, patrones, transparencia, estados externos, clipping, cm ni matrices de fuente no estándar. d1 mantiene su restricción sin color. Cambiar texto no edita el color dibujado dentro del glifo. Fuentes variables y CFF2 con VarStore siguen pendientes.

## Avance global

**80,17 % estimado del programa completo**, antes 79,61 %. Alcance y diecisiete pesos sin cambios: texto/imágenes 97→97,5 (+0,08 global), OCR/conversión 88→90 (+0,18), accesibilidad 60→70 (+0,30). No suma puntos por pruebas, documentación o herramientas. Es una estimación de madurez, no paridad certificada con Acrobat ni aceptación final.

Siguiente bloque recomendado: etiquetado de imágenes/enlaces y fuentes todavía incompatibles, junto con detección automática de inclinación OCR. Auditar variantes y agrupar implementación, conservación y recorridos; no repetir creación básica de etiquetas de texto, sugerencias rectangulares por bordes ni Type3 d0 de color literal como pendientes. Windows y aceptación personal siguen siendo puertas de entrega antes de un candidato cercano al 90 %.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
