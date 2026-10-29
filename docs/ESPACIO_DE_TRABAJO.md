# Espacio de trabajo y revisión — 0.21

**Actualización 0.22:** el catálogo inicial completo se sustituye por siete áreas con herramientas contextuales y paneles plegables. La búsqueda sigue siendo global. Consulta [AREAS_DE_TRABAJO.md](AREAS_DE_TRABAJO.md); los apartados de filtros/categorías siguientes describen 0.21.

Este avance mejora el acceso a las funciones existentes y añade una inspección estructural del PDF. No declara equivalencia con Acrobat ni valida todos los PDF existentes.

## Encontrar y usar una herramienta

- **Buscar herramienta** acepta nombres y tareas: `fuentes cursiva`, `escaneo`, `numeracion bates`, `excel` o `diagnostico`. Ignora acentos y mayúsculas; todas las palabras deben aparecer en el nombre, descripción, categoría o palabras asociadas.
- **Categoría de herramientas** filtra lectura/revisión, contenido, anotaciones, páginas, formularios/firma y documento/conversión.
- La **estrella** guarda favoritos en este navegador. No guarda documentos ni se incluye en el proyecto. Si el almacenamiento del navegador está deshabilitado, la selección sirve durante la sesión.
- **Ctrl+K / ⌘+K** abre la paleta de comandos. Escribe, recorre con flechas y pulsa Intro. Las funciones no disponibles explican si falta un documento, permiso, preparación de página o aplicación de un borrador. Esc cierra; el diálogo conserva el foco dentro de él.
- El número físico de página se introduce en **Número de página** y se confirma con Intro o **Ir**. Acepta exclusivamente enteros entre 1 y el total; no confunde etiquetas romanas o prefijos con números físicos. Ctrl+G lleva al campo. Esc restaura el valor actual.
- **Vista de lectura ampliada** oculta herramientas, miniaturas y propiedades para dar más espacio a la página. El mismo botón o Esc recupera los paneles.
- **Guía y atajos**, en la cabecera, explica la diferencia entre guardar proyecto, exportar copia y recuperación automática.

## Atajos y borradores

Ctrl/⌘+F abre y enfoca la búsqueda de texto del PDF; Ctrl/⌘+O abre un PDF; Ctrl/⌘+S guarda un proyecto; Ctrl/⌘+Mayús+S exporta una copia PDF; Ctrl/⌘+P prepara impresión; Ctrl/⌘+Z deshace y Ctrl/⌘+Mayús+Z (o Ctrl+Y) rehace. Deshacer/rehacer respeta la edición nativa dentro de campos de texto. Los diálogos toman el teclado: un Ctrl+S dentro de un formulario no dispara una descarga del documento de fondo.

Los cambios sin aplicar de texto, notas, contenido o propiedades bloquean el cambio de herramienta, la navegación y el historial. Aplica o cancela el borrador desde su panel. Se evita descartarlo accidentalmente al pulsar otra función o página. Abrir otro archivo conserva la confirmación de descarte ya existente.

## Revisar documento

Abre `ejemplos/reapdf-recorrido.pdf` y busca **Revisar documento**. Encontrarás una nota/enlace en la primera página, un posible escaneado en la segunda, un campo en la tercera y una cuarta página sin texto girada.

La revisión trabaja sobre una copia con las operaciones aplicadas. Recorre lotes de hasta 20 páginas, muestra el progreso, permite cerrar/cancelar y ofrece reintentar si falla un lote. Un informe incompleto no se puede descargar como completo.

Por página informa: dimensiones visibles en puntos, giro, recursos de imagen/fuente, anotaciones, apariciones de campos, enlaces y presencia de texto digital. Permite filtrar y saltar a la página elegida. Incluye conteos de capas y adjuntos, indicadores de firma y permisos declarados. No modifica el PDF ni añade versiones al historial.

**Descargar informe JSON** exporta todas las páginas revisadas, independientemente del filtro activo, con nombre de documento, fecha, alcance y estado de completitud. El endpoint no devuelve texto extraído, valores de campos, nombres de campos, comentarios, URL ni contenido de adjuntos. El informe puede contener el nombre del documento y sus etiquetas de página: revísalo antes de compartirlo.

### Límites de la inspección

- «Posible escaneado» significa imagen definida y ausencia de texto detectado; no demuestra que la página necesite OCR. Puede ser una ilustración o un recurso no visible.
- Los recursos de imagen no equivalen a imágenes visibles y un recurso puede usarse más de una vez. Los campos compartidos cuentan por aparición, no por grupo lógico.
- Las fuentes contadas no garantizan que estén incrustadas, que permitan todos los caracteres ni que sean editables. La herramienta de edición hace sus propias validaciones.
- Un documento puede declarar permisos permisivos y contener estructuras que una herramienta no admite.
- No comprueba conformidad PDF/A, PDF/UA/PDF/X, accesibilidad, cadenas de certificados, malware, censura forense ni editabilidad universal.
- Límite de 100 000 objetos PDF y 2000 recursos de cada clase o anotaciones por página; el editor mantiene sus límites generales de 30 MB/500 páginas. No decodifica imágenes ni renderiza páginas para esta inspección; la detección de texto usa el motor PDF local.

## Evidencia y próximos pasos

Pruebas unitarias: búsqueda y permisos del catálogo, páginas inválidas, paginación de 43 páginas, revisión con operaciones aplicadas, conservación de fuente, no exposición de contenido, lectura con restricciones/firma, límites y API. Prueba de Chromium: favoritos persistentes, búsqueda por tareas, teclado, foco, revisión/JSON, salto a campos, historial dentro/fuera de entradas de texto, protección de borradores, un solo guardado por atajo, recuperación y ventanas de 1440, 1100 y 600 píxeles. El recorrido anterior de edición/exportación se mantiene como regresión.

Próxima prioridad funcional: ampliar el motor de fuentes y reflujo, y reconstruir/validar los árboles de formularios al copiar/importar páginas. La prueba real del portable en Windows sigue pendiente. El control estructural no sustituye esas verificaciones.

Por indicación del usuario, este avance no genera un portable nuevo. El ejemplo está disponible mediante scripts/create_review_sample.py; su inclusión en una futura entrega ya está preparada. La siguiente entrega para pruebas personales se reserva para un ejecutable cuando el programa esté casi completo.
