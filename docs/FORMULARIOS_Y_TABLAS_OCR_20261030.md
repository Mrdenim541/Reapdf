# Bloque amplio: formularios estándar y tablas digitales/escaneadas

Este bloque añade funciones de formularios y conversión que no estaban presentes. Los cálculos declarativos del proyecto ya existentes no se cuentan como nuevos.

## Trabajos terminados

1. **Números y monedas compatibles.** Lectura declarativa de `AFNumber_Format` con 0–6 decimales, cuatro estilos de separadores, signo negativo o paréntesis y prefijo/sufijo monetario latino de hasta 12 caracteres. La apariencia muestra el número formateado y `/V` conserva su valor numérico sin formato. No se pierde el texto visible aunque supere MaxLen por separadores/moneda.
2. **Porcentajes.** `AFPercent_Format` con entrada de fracción, separador local y presentación porcentual. Se conservan el valor numérico, las acciones originales y la apariencia del campo.
3. **Fechas y rangos.** `AFDate_FormatEx` en dd/mm/yyyy, mm/dd/yyyy, yyyy-mm-dd y dd.mm.yyyy, con comprobación de fechas reales. `AFRange_Validate` comprueba límites inclusivos. Se aceptan filtros K estándar que coinciden con su formato; la validación se realiza sobre valores completos, sin simular cada pulsación de Acrobat.
4. **Conservación de formularios.** Las llamadas se interpretan mediante una gramática cerrada; no se ejecuta JavaScript. Antes de actualizar apariencias se retiran temporalmente las acciones de los nodos involucrados y luego se restauran. Los campos compartidos mantienen valor lógico y apariencias sincronizadas. Las acciones desconocidas, encadenadas o de otros tipos permanecen protegidas. Un valor inicial inválido puede corregirse.
5. **Relleno más directo.** Selección de campos con el ratón sobre la página, vista previa automática al escribir, explicación del formato y del valor que se mostrará. Revisión de campos obligatorios por nombre y página, agrupando sus apariciones. Se permite guardar borradores parciales; no se obliga a completar todo para conservar el trabajo.
6. **Extraer tabla por región.** Nueva herramienta en Convertir y OCR → Exportar. Selección del área con ratón, modo digital/OCR/automático, idiomas español/inglés verificados y 150/200/300 ppp. Detecta líneas de cuadrículas sencillas y conserva coordenadas de palabras tras giros y CropBox. Puede reconocer imágenes de tablas aunque la página tenga texto en otras zonas.
7. **Cuadrícula y revisión.** Separadores movibles con ratón, redistribución por número de filas/columnas y corrección de cada celda. Reutiliza las palabras reconocidas al ajustar separadores. Advierte sobre texto que cruza límites y exige revisión del resultado. La supresión de líneas se realiza solo sobre una imagen auxiliar para OCR, conservando el PDF original.
8. **CSV y Word revisados.** Exportación de las celdas corregidas a CSV UTF-8 y a una tabla Word editable, con encabezado opcional. El CSV protege prefijos de fórmulas. El Word no contiene macros ni relaciones externas; se comprobó la reimportación en Reapdf con todo el texto de las celdas.
9. **Uso en escritorio propio.** Comprobación real desde Qt Linux: rellenar y guardar PDF mediante escritura atómica, abrir una tabla escaneada, ejecutar OCR, corregir una celda y descargar CSV/DOCX mediante los diálogos nativos de guardado. No se utilizó un navegador externo en ese recorrido.

## Comprobaciones reales

- **2956 pruebas Python generales aprobadas**, 3 avisos existentes, 350,91 s.
- Después de corregir el límite de cuadrícula máxima y añadir casos de CropBox/longitudes: **349 pruebas dirigidas finales aprobadas**, 2 avisos existentes. Los subconjuntos se solapan y no se suman.
- **120 pruebas JavaScript y compilación aprobadas.** El catálogo y sus secciones comprueban que la nueva herramienta aparece en la interfaz.
- **Chromium:** números, fechas, porcentajes, obligatorios, selección directa, vista previa automática, fecha inválida, historial y exportación. Tabla de un escaneado real, cuadrícula, arrastre de separador, corrección y CSV/Word; valores nativos, acciones y otra página conservados.
- **Qt Linux:** el recorrido descrito arriba pasó con archivos originales intactos. El primer automatismo se corrigió para esperar a que el botón de herramienta estuviera habilitado tras cargar la página.
- OCR real probado con tabla sintética rasterizada, giro de página de 0/90/180/270°, corrección de orientación de 180° y CropBox desplazado; modo digital con geometrías equivalentes. Campo compartido con formato y MaxLen verificados.

Evidencias y hashes: `validation/forms-ocr-tables-20261030/`. Solo documentos sintéticos públicos; no se usaron PDFs privados ni se generó instalador/portable. Chromium y Qt Linux no sustituyen Windows, aceptación personal ni interoperabilidad externa en Acrobat/Nitro/Word.

Comandos principales:

```bash
.venv/bin/python -m pytest tests/test_form*.py tests/test_advanced_forms.py tests/test_table_regions.py tests/test_projects.py -q
node --test tests/*.mjs
npm run build
node scripts/smoke_commercial_forms_tables.mjs
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu' .venv/bin/python -m scripts.smoke_commercial_native
```

Los dos recorridos gráficos requieren el backend actualizado en 127.0.0.1:8000.

## Límites que permanecen

**Formularios:** XFA, CO/cálculos nativos PDF, `AFSimple_Calculate`, JavaScript general y otros eventos/validadores. No se ejecutan scripts ni se reinterpretan expresiones. Se mantienen los límites de fuentes/texto de formularios anteriores; monedas no latinas, estilos negativos con cambio de color, otros formatos de fecha y acciones JS en streams quedan fuera. Los valores numéricos se limitan a 10¹². Los cálculos declarativos del proyecto requieren separadores coherentes con los campos formateados.

**Tablas/OCR:** hasta 100 filas × 30 columnas y 100000 caracteres, 10000 palabras, 16 MP y lado máximo aproximado de 8192 píxeles; no equivale a un motor general de estructura documental. Se admiten cuadrículas rectangulares sin celdas combinadas. Perspectiva, deskew general, columnas sin líneas ambiguas y corpus multilingüe siguen pendientes. OCR puede equivocarse; no se inventa una puntuación de confianza. Regiones que cruzan campos de formulario se rechazan para no omitir sus valores; se pueden exportar sus datos o usar una copia aplanada. No se modifica el PDF ni se convierten sus píxeles en texto original editable.

**Office:** el nuevo Word contiene la tabla revisada, no una reconstrucción de todo el diseño del documento original. La fidelidad Office general, notas al pie/finales y otras partes omitidas aún requieren trabajo. No se probó Microsoft Word ni Excel externos.

## Avance total y siguiente bloque

**78,00 % estimado del programa completo**, antes 76,40 %. Se conservan alcance y 17 pesos. Formularios pasa de 70 a 80; OCR/conversión de 70 a 80; interfaz de 92,5 a 94. El cálculo sin redondear pasa de 76,395 a 78,000. La valoración es provisional de ingeniería; no es paridad objetiva con Acrobat ni aceptación final.

Próximo bloque amplio recomendado, con entregables agrupados:

1. Cálculos estándar nativos de PDF y su orden CO, dependencias y ciclos, sin ejecutar JavaScript general; conservar compatibilidad con formatos y valores compartidos.
2. Ampliar fidelidad de importación Word en las partes que el motor actual todavía omite, comenzando por notas al pie/finales, con informes de contenido conservado.
3. Completar recorridos de uso y persistencia de esas ampliaciones, conservando los límites de OCR complejo y la verificación Windows como pendientes explícitos.

No repetir como futuros la revisión de obligatorios, selección visual de campos, formatos estándar ya admitidos, OCR tabular rectangular revisable ni su CSV/Word.

**Modelo recomendado: 6.1 Sol, razonamiento medio.**
