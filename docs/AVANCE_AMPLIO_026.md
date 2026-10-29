# Avance amplio 0.26

Cuatro bloques funcionales, manteniendo la sesión editable y las entregas Windows pospuestas por indicación del usuario.

## Enlaces existentes

En **Editar → Editar enlaces del PDF**, selecciona un enlace de la lista o su contorno sobre la página. Puedes modificar HTTP/HTTPS, cambiar a otra página del documento, mover/redimensionar su área o eliminarlo. Se exige una vista previa válida para aplicar; cualquier ajuste posterior la invalida. La vista previa no abre enlaces ni ejecuta acciones.

Mover solo el área conserva el destino y zoom originales. Cambiar un destino interno crea una referencia nativa a la página completa (`/Fit`). Se conservan los demás enlaces y propiedades ajenas a la modificación. Se verifican los cuatro giros y los recortes desplazados. Las identidades xref pueden cambiar al compactar el PDF; el contenido y las propiedades se conservan, no su número de objeto.

Quedan protegidos enlaces con acciones adicionales/encadenadas, capas, relaciones, bloqueos, archivos externos, destinos no resueltos o áreas fuera de la página. Máximo 2000 enlaces por página para editar. Los cambios crean versiones compatibles con deshacer/rehacer, proyectos y recuperación.

## Campos nuevos con formato

En **Formularios y firmas → Crear o eliminar campos**, el diseño incorpora:

- Descripción emergente, indicador PDF de campo obligatorio y límite de 1–2000 caracteres para texto.
- Tres familias verificadas: Helvetica, Times y Courier. Tamaño fijo de 6–72 pt o automático con 0; color de texto.
- Borde continuo, discontinuo o subrayado, grosor 0–5 pt y color; fondo opcional.
- Valor inicial de texto, texto multilínea, desplegable, casilla y grupo de radio. Se valida el valor, sus caracteres y que quepa antes de crear la copia.
- **Vista previa del campo** con apariencia nativa y el valor inicial; aviso si se cambian los ajustes después.

Las opciones de formato se muestran en un panel desplegable para mantener claro el asistente. La descripción es un tooltip, no una etiqueta impresa. El indicador obligatorio sirve a aplicaciones que validan formularios: Reapdf permite guardar campos vacíos. El valor inicial es el valor actual `/V`, no un valor de restablecimiento `/DV`.

Se admiten caracteres latinos en los valores. El motor normaliza silenciosamente otras variantes de fuente a Helvetica durante la actualización de Widgets; se restringe la selección a las tres familias comprobadas y se protegen los campos importados con variantes fuera de ese contrato. Esto no limita las doce variantes del editor de párrafos. Los radios mantienen el aspecto y etiquetas impresas del creador anterior; aquí se configura su descripción, obligatoriedad y selección inicial. Crear campos sigue requiriendo páginas sin giro.

## Rectángulos y elipses importados

En **Comentar → Seleccionar marca**, las propiedades de rectángulos y elipses estándar muestran X, Y, ancho y alto. Permiten mover y cambiar tamaño en puntos de la página visible, también con giro/recorte. Se preservan color, borde, opacidad, autor y contenido. Las notas solo se trasladan; conservan su tamaño.

Las figuras redimensionadas deben quedar dentro de la página y medir al menos 10 × 10 pt. Los efectos de borde especiales, intenciones de medida, indicadores NoRotate/NoZoom, bloqueos y relaciones incompatibles no habilitan redimensionado. Se mantienen la protección de borradores, cancelación y cambios consolidados del historial. No se amplía todavía el tamaño de trazos, líneas o resaltados importados.

## Procesamiento por lotes

En **Convertir y OCR → Procesar varios PDF**, selecciona una tarea, añade PDF y pulsa **Revisar lote**. Solo una revisión vigente habilita **Descargar lote ZIP**. Cambiar tarea, documentos o contraseñas exige repetir la revisión.

Las tres tareas son optimización estructural sin reducir resolución de imágenes, extracción del texto digital a TXT UTF-8 y copias protegidas AES-256 con permisos de copia/impresión. Las contraseñas de apertura/propietario deben ser distintas, se usan para todo el lote y no se guardan en el manifiesto ni en el proyecto. El lote mantiene la sesión abierta sin crear historial ni sustituir el documento.

Cada ZIP incluye nombres seguros y únicos, más `manifest.json` con orden, tarea, páginas, tamaños, huellas SHA-256 de entradas/salidas y aviso de operaciones de sesión incorporadas. La revisión realiza una ejecución sin descargar: en protección, las huellas de salida cambian al regenerar el cifrado; el manifiesto descargado describe los bytes finales. Todos los archivos deben validar: no se entrega un ZIP parcial si uno falla.

Límites: 10 PDF, 100 páginas, 60 MB de entrada y 100 MB de salida. La extracción no hace OCR ni conserva maquetación, valores de Widgets o comentarios; la optimización puede no reducir tamaño. Las operaciones respetan permisos y firmas. Los documentos adicionales se retiran del almacén de sesión al cerrar el diálogo. Los PDF con contraseña deben abrirse primero como copias autorizadas.

## Estimación y pendientes

**79 % ±5 puntos**, con 78,5 puntos en la matriz de pesos estable. No representa paridad con Acrobat ni porcentaje de horas restantes. El 90 % no se declara: faltan, entre otros, conversiones Office, firmas con certificados, estándares/accesibilidad, más estructuras complejas de edición/censura y la validación real de la aplicación Windows con ventana propia. Se continúa sin generar portables por avance.

Validación del cierre 0.26: **1231 pruebas Python y 80 JavaScript aprobadas (1311 en total)**, compilación de producción y recorrido completo en Chromium aprobados. Los recorridos descargan y comprueban PDF, proyectos y ZIP de las tres tareas, además de historial y recuperación. Hay contraste independiente de texto y apariencia con Poppler. Windows nativo y lector comercial siguen pendientes.
