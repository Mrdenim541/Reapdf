# Revisión de texto y notas — versión 0.7

Resaltar, Subrayar y Tachar crean anotaciones nativas HighLight, Underline y StrikeOut. Un clic marca la palabra bajo el puntero. Al arrastrar sobre el texto se incluyen palabras que intersectan el área, con una tolerancia de 3 puntos para facilitar el gesto horizontal. Cada palabra conserva sus cuatro vértices, también tras girar la página. No se elimina ni se rasteriza el texto. La selección admite varias líneas y hasta 500 palabras por anotación.

Se admite texto digital horizontal en su sistema original y giros globales de página de 0, 90, 180 y 270 grados. En el alcance inicial quedaban pendientes texto oblicuo, selección parcial de caracteres y OCR; las ampliaciones actuales se detallan al final. El orden de lectura de columnas no se interpreta: se seleccionan las palabras contenidas en el área indicada.

Nota coloca un icono PDF y permite guardar hasta 4000 caracteres, incluidos saltos de línea y Unicode. El motor rechaza notas vacías y posiciones que no dejan espacio para el icono. En Seleccionar marca se puede elegir la nota por clic o por la lista de marcas de la página y corregir su contenido. La lista también permite seleccionar marcas superpuestas. Crear, corregir y eliminar se incluyen en deshacer/rehacer.

Las regiones de las marcas quedan ancladas a coordenadas de página. Una edición posterior del texto no reajusta automáticamente esos límites. Organizar o unir consolida las anotaciones en una nueva versión: se conservan, pero pasan a ser preexistentes; hay que deshacer esa operación para volver a editarlas con las herramientas de sesión.

Las anotaciones preexistentes compatibles se gestionan desde la versión 0.9; véase ANOTACIONES_EXISTENTES.md. Respuestas, estados de revisión y exportación de comentarios siguen pendientes. Las notas no constituyen firma ni certificación. El tachado es una marca visual y **no elimina información confidencial**; para retirar contenido se debe usar Censurar y sanear copia, dentro de sus límites documentados.

## Verificación

Pruebas del motor: tipos PDF, vértices y texto conservado para cuatro rotaciones; notas Unicode; páginas recortadas; permisos y firmas; rechazo de coordenadas y regiones inválidas; combinación con edición de texto; conservación al organizar y unir.

API: palabras seleccionables, vista previa, exportación, rechazo de nota vacía y original intacto. Chromium: las tres marcas, nota nueva y corregida, deshacer/rehacer, selección y eliminación, y comprobación del PDF descargado. Se mantiene el recorrido anterior del editor y organización.

Pendiente: lector independiente, Windows y corpus amplio de documentos reales.

## Movimiento y tamaño — versión 0.7

Seleccionar marca muestra un marco, un tirador circular para mover y otro en la esquina inferior derecha para redimensionar. Arrastrar el borde del marco también mueve la marca. Escape o cancelación del puntero descartan el gesto. La silueta azul permite anticipar el cambio; la imagen del PDF se actualiza tras validar y aplicar la operación.

Las flechas con el foco en un tirador ajustan 1 punto; Mayús+flecha ajusta 10. También se puede introducir posición y tamaño en el panel de propiedades. X/Y indican la esquina superior izquierda de los límites geométricos visibles, sin el margen adicional de apariencia de la anotación. La nota usa un área de referencia fija de 20 puntos para asegurar espacio para su icono.

Trazos, figuras y las regiones de resaltado/subrayado/tachado se escalan dentro de su nueva caja; se conserva el grosor, color, contenido y orden de vértices. Las notas solo se trasladan. Una línea vertical u horizontal conserva su dimensión cero y permite cambiar su longitud. Las dimensiones que se redimensionan deben medir al menos 1 punto. Los trazos originalmente más estrechos se pueden trasladar sin ensancharlos.

Cada cambio aceptado crea una entrada de historial, validada con el motor que produce la exportación. Los datos originales no se mutan. El arrastre se limita a la página; los valores numéricos inválidos se rechazan. Se puede deshacer y rehacer sin alterar las demás marcas. La selección continúa después de aplicar el cambio.

El redimensionado de una marca de texto es geométrico: no vuelve a seleccionar palabras ni cambia el contenido de la página. El tamaño del icono de nota no es editable. La rotación de la propia anotación y tiradores en las otras esquinas quedan pendientes, al igual que el movimiento y tamaño de las anotaciones preexistentes.

Verificación añadida: 23 pruebas de geometría y recorrido Chromium a zoom 90 % para traslación, escala, cancelación, rechazo de una posición inválida, historial y comprobación de vértices del PDF descargado. El recorrido también transforma una figura en una página girada 90° y prueba ajustes por teclado. Las pruebas del motor cubren la exportación de figuras y marcas de texto en los cuatro giros globales.

Desde 0.27 hay conversaciones nativas con respuestas, estados de revisión e informes completos CSV/JSON. Alcance, permisos y restricciones: [AVANCE_AMPLIO_027.md](AVANCE_AMPLIO_027.md).

Desde 0.29 Revisar documento enlaza a la verificación criptográfica cuando hay indicadores de firma. La inspección estructural no afirma por sí sola que una firma sea válida; el asistente dedicado separa integridad, revisiones y confianza. Guía: [FIRMAS_DIGITALES.md](FIRMAS_DIGITALES.md).

Desde 0.30 existe Validar estándares PDF con veraPDF como asistente independiente de la revisión estructural. El diagnóstico de accesibilidad también está separado de una declaración PDF/UA. Guía: [ESTANDARES_Y_ACCESIBILIDAD.md](ESTANDARES_Y_ACCESIBILIDAD.md).

Desde 0.31 se puede elegir selección por caracteres o palabras y ver los fragmentos durante el arrastre. La censura, separada de las anotaciones visuales, incorpora búsqueda y revisión multipágina. Guía: [SELECCION_Y_CENSURA.md](SELECCION_Y_CENSURA.md).
