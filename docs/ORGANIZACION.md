# Organización de páginas: versión inicial

Cada solicitud usa el documento actual y las ediciones de la sesión para generar un PDF nuevo. La entrada y las versiones anteriores permanecen intactas. El historial del editor conserva el identificador del documento y sus operaciones; deshacer/rehacer puede restaurar el estado anterior a una organización.

La lista de organización contiene páginas únicas y su rotación absoluta (0, 90, 180 o 270). Su orden define el resultado; las páginas ausentes se eliminan. Debe quedar al menos una. La extracción utiliza la misma transformación para descargar una selección, sin sustituir el documento abierto ni marcar sus cambios como guardados.

PyMuPDF `Document.select` conserva los objetos de página y remapea enlaces/marcadores locales. Los destinos locales eliminados desaparecen. Las rotaciones se aplican después de las ediciones, para que los trazos y los reemplazos mantengan sus coordenadas originales. Las etiquetas de página visibles se conservan como prefijos explícitos por página; el esquema de numeración automático original no se conserva como tal.

Pruebas actuales: orden, rotaciones, igualdad visual en páginas conservadas, anotaciones, notas, un campo de formulario de texto, etiquetas, marcadores, enlaces locales directos, enlaces URI, extracción, permisos, indicadores de firma y rechazo por cuota sin daño a la entrada. Chromium verifica la reversión y ediciones posteriores sobre el nuevo orden.

La selección de páginas ahora restaura y poda el árbol AcroForm: mantiene registrados los campos de las páginas conservadas y retira los widgets eliminados. Las pruebas incluyen campos jerárquicos y modificación tras guardar/reabrir.

Recorte/restauración, reemplazo de bloques y división están disponibles como herramientas separadas; véase PAGINAS_AVANZADAS.md. Límite: no duplicación directa desde el organizador todavía. La unión/inserción está disponible por separado; véase UNION.md. Las marcas anteriores a la organización pasan a ser anotaciones preexistentes en el nuevo documento; pueden recuperarse como operaciones editables al deshacer la organización. El límite global de archivos y versiones temporales es 300 MB. El historial se pierde al cerrar/recargar; no se presenta como recuperación automática.

Los corpus actuales son sintéticos. Formularios complejos, destinos nombrados, acciones especiales, documentos etiquetados, estructuras avanzadas y lectores externos requieren validación adicional antes de prometer conservación universal. La eliminación de páginas no es una herramienta de censura o saneamiento de adjuntos/metadatos.
