# Bloque del plan: cálculos nativos de PDF y notas de Word

Se completa el bloque previsto después de formularios estándar y tablas OCR: cálculos originales de PDF, orden/dependencias/ciclos, notas al pie/finales de Word y recorridos de edición, persistencia y guardado. No se presentan como nuevos los cálculos declarativos del proyecto ni el OCR tabular ya incorporados.

## Trabajos incorporados

1. **Cálculos estándar del PDF.** Se interpreta `AFSimple_Calculate` con SUM, PRD, AVG, MIN y MAX y fuentes literales mediante `new Array(...)` o `[...]`. No se ejecuta JavaScript. Un cambio de entrada recalcula los resultados dependientes, incluidos los de otras páginas, conservando acciones C/F/K/V admitidas, valores nativos, formatos y propiedad lógica de campos compartidos.
2. **Dependencias, ciclos y orden CO.** Se comprueban nombres únicos, fuentes existentes, tipos numéricos compatibles, fuentes inmutables seguras y correspondencia entre acciones y `/CO`. Los ciclos, acciones desconocidas y órdenes incompletos bloquean la edición del formulario, sin resultados parciales. Un CO válido pero desordenado tiene reparación explícita desde la interfaz: cambia el orden y permite deshacer; no cambia silenciosamente valores al abrir el archivo.
3. **Recálculo y protección.** El botón Actualizar cálculos del PDF permite refrescar resultados sin cambiar una entrada. Los resultados son de solo lectura para el usuario. Se protegen las fuentes necesarias frente a eliminación o extracción de páginas que rompa sus dependencias. La copia aplanada calcula sus resultados antes de convertir los campos y retira AcroForm. Exportar sin operaciones conserva los bytes originales.
4. **Persistencia.** Entradas y recálculo explícito sobreviven a proyectos Reapdf; los datos JSON exportan las entradas editables y recalculan salidas al importarse. La organización conserva dependencias cuando sobreviven sus fuentes. Se comprobó un resultado compartido en dos Widgets/páginas con un único propietario y acción original.
5. **Notas al pie Word.** Se importan definiciones locales, referencias, numeración estándar continua o reiniciada por sección, imágenes y enlaces compatibles de cada parte. Una paginación acotada reserva espacio al pie de la página de la referencia; se verifican las posiciones finales y la ausencia de solapamiento con el cuerpo y el pie. Se conserva texto seleccionable, no una captura de las notas.
6. **Notas finales y navegación.** Las notas finales se colocan al final del documento o sección, según la configuración compatible, y pueden ocupar varias páginas. Referencias y notas tienen enlaces de ida y retorno, también entre páginas/secciones. La revisión de importación muestra el número de notas conservadas.
7. **Integridad de la conversión.** Se comprueba el texto teniendo en cuenta las marcas generadas y las palabras divididas entre estilos. Se rechazan definiciones ausentes, referencias repetidas o anidadas, XML dañado, revisiones pendientes y referencias en estructuras que el importador no procesa; no se omiten esas notas para entregar un resultado parcial.
8. **Uso de la aplicación.** Chromium comprobó recálculo, resultados protegidos, reparación de CO, historial, PDF y proyectos; después importación/revisión de notas, edición de una nota sobre la página con su fuente original y persistencia. Qt Linux comprobó los cálculos y la importación/revisión de notas con guardado atómico nativo y originales intactos.

## Validaciones reales

- **3019 pruebas Python generales aprobadas**, 3 avisos existentes, 297,24 s.
- **564 pruebas dirigidas finales aprobadas**, 2 avisos existentes, tras añadir el resultado compartido y la protección adicional contra referencias de notas no procesadas. Los subconjuntos se solapan y no se suman. La suite general anterior precede a ese último refuerzo conservador; el bloque completo de formularios/Word/proyectos se verificó después con las dirigidas.
- **120 pruebas JavaScript y compilación aprobadas.**
- Recorrido **Chromium** aprobado, incluida edición directa de la nota convertida y restauración del proyecto.
- Recorrido **Qt Linux** aprobado: guardar cálculos originales y el Word convertido con notas mediante la ventana propia y sus diálogos nativos.

Evidencias y hashes: `validation/native-calcs-notes-20261030/`. Se utilizaron únicamente documentos sintéticos públicos. No se generó portable/instalador ni se utilizó REA. Windows, impresora física, aceptación personal e interoperabilidad externa en Acrobat/Nitro/Microsoft Word no se ejecutaron.

Comandos principales, con backend actualizado en 127.0.0.1:8000 para los recorridos gráficos:

```bash
.venv/bin/python -m pytest tests/test_native_calculations.py tests/test_form*.py tests/test_advanced_forms.py tests/test_projects.py tests/test_docx*.py -q
node --test tests/*.mjs
npm run build
node scripts/smoke_native_calcs_notes.mjs
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu' .venv/bin/python -m scripts.smoke_native_calcs_notes_qt
```

## Límites que permanecen

**Cálculos:** hasta 50 reglas y 30 fuentes literales por regla, dentro del límite de 500 Widgets. Solo campos de texto numérico de una línea y sus formatos compatibles. Decimal con precisión 34, vacíos como cero, valores/resultados e intermedios de producto hasta 10¹². No se pretende reproducir cada detalle del redondeo binario de Acrobat. No se admiten expresiones arbitrarias, JavaScript general, XFA, acciones en streams, nombres ambiguos, variables, listas/botones como fuentes ni otras variantes de ayudantes. Las reglas del proyecto no usan salidas nativas como fuentes; no se admite un grafo mixto arbitrario. La reparación CO no repara ciclos, código desconocido ni campos ausentes.

**Notas:** hasta 200 referencias y 200 definiciones por parte (además de separadores), 100000 caracteres, 3000 párrafos y 50 páginas para la conversión completa. Reserva de notas de una página limitada a 216 pt y al 40 % del cuerpo, con hasta 12 pasadas. Las notas que no caben completas se rechazan; no se implementan notas partidas entre páginas, marcas personalizadas ni reinicio de numeración por página. Referencias en encabezados/pies o estructuras no admitidas se rechazan. Las definiciones sin referencia se omiten con aviso. Se mantienen las sustituciones de fuentes y límites de tablas/imágenes del importador; la paginación puede cambiar y conservar espacios de reserva. No se promete el diseño exacto ni la reconstrucción semántica original de notas si el PDF se vuelve a exportar a DOCX. Comentarios Word y otras partes aún omitidas siguen pendientes.

La comprobación del PDF usa una nueva lectura/representación de MuPDF y pruebas de geometría y contenido; no acredita compatibilidad universal ni PDF/UA. Los trabajos de firmas, estándares, accesibilidad, servicios, fuentes restantes y distribución Windows mantienen sus propios pendientes en la matriz.

## Avance global y siguiente bloque

**78,97 % estimado del programa completo (≈79 %)**, antes 78,00 %. Mismos alcance y 17 pesos: formularios 80→87,5 (+0,45 global), Office/OCR 80→85 (+0,45) e interfaz 94→95 (+0,07). No se suman puntos por generar pruebas, preparar herramientas ni configurar distribución. Es una estimación de madurez, no paridad objetiva con Acrobat ni aceptación final.

El siguiente bloque recomendado amplía OCR con inclinación/perspectiva y el tratamiento de tablas más complejas, junto con accesibilidad/orden de lectura tras revisar su cobertura existente. Debe agrupar implementación, geometría, conservación del documento y recorridos, sin volver a anunciar cálculos CO o notas compatibles como trabajos pendientes. Windows y la aceptación personal permanecen como verificaciones reales antes de una entrega candidata.

**Modelo recomendado: 6.1 Sol, razonamiento medio.**
