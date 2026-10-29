# Estándares y accesibilidad — avance 0.30

Este avance incorpora validación independiente, una copia PDF/A-2b comprobada y preparación básica de accesibilidad. Los asistentes están separados por área; no se genera otro portable.

## Validar estándares PDF

En **Proteger → Validar estándares PDF**, selecciona PDF/A-1b, PDF/A-2b, PDF/A-3b o PDF/UA-1 y pulsa **Validar perfil seleccionado**. Se valida la copia con las ediciones actuales, sin alterar el PDF abierto ni su historial.

El resultado incluye perfil, conformidad según veraPDF, reglas y comprobaciones fallidas. Puedes filtrar por texto o cláusula y desplegar la expresión de cada regla. Las descripciones normativas se conservan en el idioma del validador. Cambiar de perfil retira el resultado anterior: se debe validar el nuevo perfil.

**Descargar informe de estándares JSON** conserva SHA-256 del PDF revisado, tamaño, fecha, versión de veraPDF, perfil y reglas. No incluye texto de las páginas, valores de formulario, rutas temporales ni los contextos detallados del PDF que genera el validador. El informe afirma conformidad únicamente cuando termina un trabajo completo, sin errores, con perfil y contadores consistentes. Un fallo, timeout o informe incompleto no se presenta como conformidad.

Se usa veraPDF CLI 1.30.3 con recursos de validación verificados por SHA-256. Requiere Java. No es la inspección estructural orientativa de «Revisar documento»: aquí se ejecuta un validador externo con perfiles normativos. Aun así, cumplir reglas automáticas PDF/UA no demuestra por sí solo orden de lectura correcto, utilidad de las alternativas o uso adecuado con lectores de pantalla. PDF/X, PDF/A-4, PDF/UA-2 y corrección automática de todas las reglas no se ofrecen en este alcance.

## Crear copia PDF/A-2b

En **Convertir y OCR → Crear copia PDF/A-2b**, revisa las limitaciones y activa la confirmación de revisión visual. **Preparar y validar copia PDF/A** reconstruye una copia mediante Ghostscript y la pasa por veraPDF. Solo un resultado conforme habilita la descarga.

La copia incorpora las ediciones aplicadas, incrusta un perfil sRGB y solicita incrustación de fuentes sin reducir deliberadamente la resolución de imágenes. No se rasteriza sistemáticamente el documento: se mantienen texto buscable y contenido PDF compatible. El proceso puede sustituir fuentes, transformar colores o reorganizar recursos.

Antes de entregarla se exige:

- Resultado completo y conforme PDF/A-2b en veraPDF.
- Mismo número de páginas y tamaños visibles con tolerancia de 0,5 pt.
- Mismo texto extraído por página tras normalización Unicode NFKC y de espacios. Si difiere, este flujo conservador rechaza la copia; no intenta decidir automáticamente que una diferencia es inocua.
- Límites de tiempo y tamaño respetados.

La revisión muestra original y resultado de la primera página, con **Ampliar comparación**. No sustituye revisar el resto de páginas ni verificar apariencia en un lector independiente. PDF/A no garantiza una reproducción visual exacta ni implica PDF/UA.

La descarga vuelve a generar y validar el PDF. Su informe final contiene la huella de los bytes realmente descargados; puede diferir del candidato revisado por fechas/identificadores de generación. **Descargar informe de copia PDF/A** corresponde al archivo final, no a una huella de prueba. La sesión original permanece editable.

Este primer flujo protege documentos con firmas, campos, comentarios, enlaces, adjuntos, capas o árbol de etiquetas: no los retira silenciosamente para convertirlos. Requiere permisos de edición/copia y una copia de trabajo sin cifrado. Si necesitas aplanar un formulario o retirar funciones, hazlo en una copia y revisa el resultado antes. Se necesita Ghostscript además de Java/veraPDF; no se afirma que estén incluidos en el antiguo portable o validados en Windows.

## Accesibilidad y preparación

En **Leer → Accesibilidad y preparación**, se revisan:

- Título, idioma principal y preferencia del visor de mostrar el título.
- Presencia del árbol de etiquetas, figuras etiquetadas, alternativas Alt/ActualText detectadas, tablas y roles personalizados.
- Nodos repetidos/ciclos y límites de profundidad del árbol.
- Imágenes sin texto detectado, como posibles páginas que requieren OCR.
- Campos sin descripción emergente y recursos Type0 sin entrada ToUnicode detectada.

No se comprueba la calidad semántica de las etiquetas, alternativas o mapeos Unicode, ni se infiere el orden de lectura a partir de coordenadas. Los recursos pueden no ser visibles y una imagen sin texto puede ser una ilustración. El resultado es un diagnóstico orientativo, no una declaración de accesibilidad.

Filtra observaciones del documento o de páginas; **Ir a la página** cierra el asistente y navega a la página señalada. El informe JSON incluye datos estructurales, metadatos y huella del PDF, sin valores de campos ni texto de las páginas.

En el apartado plegado **Preparar título e idioma** puedes corregir título, idioma y preferencia de mostrar título. El idioma usa formato BCP 47 básico, por ejemplo `es-PE`: se valida la forma, no todo el registro IANA. Elige el idioma real del documento.

Aplicar sincroniza título/idioma compatibles con XMP y propiedades PDF, conserva las propiedades ajenas y traducciones de título ya existentes, y crea una versión reversible con proyecto/recuperación. No crea etiquetas, no cambia el contenido de páginas ni agrega una afirmación PDF/UA. Si el XMP es incompatible o contiene DTD/entidades, la actualización se bloquea sin destruirlo. Los documentos firmados o sin permiso de modificación permanecen de solo lectura. Después de editar metadatos de un documento que declara un estándar, vuelve a validarlo.

## Requisitos y límites

Validación/conversión: hasta 50 páginas, 30 MB y 50 000 objetos. Cada proceso externo tiene 90 segundos y se permite una operación de estándares a la vez; la conversión y su validación pueden requerir dos procesos sucesivos. Java se limita a 384 MB de heap; el informe externo tiene límite de 8 MB. Los procesos usan archivos temporales y estos se retiran al terminar. No se configuran servicios de red para procesar los PDF.

Diagnóstico de accesibilidad: hasta 100 páginas, 50 000 objetos, 2000 nodos de estructura, 32 niveles y 5000 anotaciones/campos; 2000 recursos por tipo/página. XMP editable hasta 2 MB. Los límites protegen este alcance inicial; no se declara soporte universal.

Recursos y licencias están en `resources/standards`: veraPDF 1.30.3 se obtuvo de Maven Central y se verificó contra el SHA-256 publicado; el perfil sRGB proviene de icc-profiles-free y conserva su aviso Zlib. Java y Ghostscript son herramientas externas. Se han probado aquí Java 21 y Ghostscript 10.05.1 en Linux. La ejecución real Windows y la distribución completa de estas herramientas siguen pendientes. La interfaz deja las funciones externas deshabilitadas si faltan herramientas o los recursos no superan la comprobación.

## Avance estimado y siguientes trabajos

**86 % ±5 puntos** del plan propio: 85,75 puntos ponderados. Creación/conversión pasa de 75 a 80 % (+0,75 global) por la copia PDF/A verificada; herramientas profesionales pasa de 75 a 85 % (+1 global) por perfiles normativos independientes y diagnóstico/preparación de accesibilidad. Los pesos y las demás áreas permanecen iguales. No se da crédito por etiquetado completo, conformidad universal, PDF/X, validación de Windows o instalación de Java/Ghostscript en el futuro ejecutable.

Siguiente orden recomendado:

1. Ampliar la gestión de etiquetas y orden de lectura con revisión manual, documentos representativos y tecnologías de asistencia.
2. Corpus y lectores externos para conversión, edición y censura; ampliar los casos admitidos a partir de sus resultados.
3. Revocación, TSA y validación avanzada de firmas con proveedores y confianza explícitos.
4. Completar los criterios de distribución del ejecutable Windows con logo, ventana propia y dependencias verificadas antes de la entrega personal.

## Capturas

- [Accesibilidad y preparación](images/Reapdf-Accesibilidad-0.30.png).
- [Validación de estándares](images/Reapdf-Validacion-estandares-0.30.png).
- [Copia PDF/A y comparación](images/Reapdf-Copia-PDFA-0.30.png).

Validación del cierre 0.30: **1451 pruebas Python y 85 JavaScript aprobadas (1536 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Las 55 pruebas nuevas del motor cubren veraPDF real, PDF/A conforme y PDF/UA no conforme, perfiles/informes consistentes, límites/timeouts, bloqueo de estructuras protegidas, giros/recortes, Unicode/transparencia, XMP y etiquetas. Chromium verifica navegación por observaciones, título/idioma con historial, filtros de reglas, ampliación/comparación, PDF/A e informe con huella de los bytes descargados, proyecto/recuperación y los flujos anteriores. Java 21/Ghostscript 10.05.1/veraPDF 1.30.3 se probaron aquí; ejecución Windows, lectores comerciales y revisión manual con tecnologías de asistencia siguen pendientes. No se generó otro portable.
