# Impresión — versión 0.13

Con un PDF abierto, elige **Archivo → Imprimir…** o pulsa **Ctrl+P** (Cmd+P en equipos Apple). Reapdf prepara el PDF con los cambios aplicados y lo abre en otra ventana o pestaña. Allí utiliza el botón Imprimir del lector PDF del navegador o su Ctrl+P para elegir impresora, páginas, escala y copias. Reapdf conserva el documento abierto y no marca el trabajo como exportado.

Si el navegador bloquea la ventana, permite las ventanas de esta aplicación o exporta una copia PDF e imprímela desde tu lector. Se necesita un lector PDF integrado o externo disponible. No se imprime el HTML de la interfaz cuando el atajo se usa con un documento abierto.

Antes de preparar la impresión deben aplicarse o cancelarse los borradores. Se respetan los permisos de impresión y alta calidad del PDF; la impresión restringida a baja resolución aún no está implementada. Un PDF firmado puede prepararse sin ediciones cuando sus permisos lo permiten; no se modifican sus bytes. El endpoint devuelve `application/pdf`, disposición inline y sin caché.

Se verificaron los bytes del PDF abierto en la ventana, su texto editado, imágenes originales, copia de páginas y hojas vacías, además de los permisos y la preservación de la fuente. **No se probó una impresora física ni el diálogo de impresión de Windows.** La configuración final y las apariencias de anotaciones dependen del lector y del controlador de impresión; esta entrega no certifica salida física ni gestión de color.
