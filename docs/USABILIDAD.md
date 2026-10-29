# Zoom y herramientas — versión 0.11

La vista vuelve a renderizar el PDF al cambiar el zoom o la densidad de pantalla. Antes se ampliaba una imagen fija, lo que degradaba la nitidez. Ahora se mantiene la vista anterior mientras se prepara y decodifica la nueva; un aviso indica la actualización. La exportación conserva el contenido PDF y no depende de la resolución de pantalla.

## Lectura y zoom

- Usa el porcentaje o los botones − y + entre 5 y 400 %.
- **Ajustar ancho** calcula el tamaño para el espacio disponible; **Página completa** permite ver la hoja entera.
- El cambio de zoom mantiene como referencia el centro visible. La página dispone de sus propias barras de desplazamiento.
- Se considera la densidad del monitor y se solicita un margen de resolución de 1,25. El motor limita cada imagen a 24 millones de píxeles, 8192 píxeles por lado y escala 8. Si alcanza el límite, la interfaz lo indica. Los planos grandes y ampliaciones extremas requieren renderizado por regiones en una fase posterior.
- Ampliar un escaneado o una imagen pequeña no recupera detalles que no existen en el original. OCR sigue pendiente.

## Herramientas y cambios

La barra izquierda agrupa lectura/edición, anotación de texto, dibujo y páginas. Sus herramientas se desplazan dentro del panel, con Deshacer/Rehacer al pie. Páginas, Índice y Buscar tienen accesos visibles en el panel de navegación. Las propiedades muestran instrucciones relacionadas con la herramienta activa; la guía superior explica el siguiente gesto.

Para resaltar, subrayar o tachar, haz clic en una palabra o arrastra sobre el texto. Para varias líneas, cubre el área que quieras marcar. Se seleccionan palabras completas; el clic en espacios vacíos no crea marcas. El gesto admite páginas giradas y requiere texto digital.

Editar texto requiere seleccionar una línea compatible y pulsar **Aplicar cambio**. Las notas, las propiedades de marcas importadas y los ajustes numéricos de posición/tamaño también requieren aplicar. Mientras existe un borrador, la guía indica qué falta y Exportar copia queda deshabilitado: aplica o cancela desde su panel. Después exporta para conservar los cambios; puedes guardar un proyecto o esperar al checkpoint del estado aplicado; véase SESIONES.md.

## Evidencia y pendientes

Pruebas de motor/API comprueban escalas, límites de memoria y que el original no cambia. Chromium prueba pantalla con densidad 2, zoom 200 %, cambios rápidos de escala, ajuste de página, ausencia de solicitudes de texto al ampliar, cancelación de borradores y PDF descargado con resaltado por clic y subrayado por arrastre. También conserva los recorridos anteriores. Falta validar Windows, monitores y documentos reales del usuario, lápiz físico y lectores independientes.
