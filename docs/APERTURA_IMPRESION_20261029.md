# Apertura e impresión desde el escritorio

El menú Archivo de la ventana Qt incorpora Abrir PDF e Imprimir, con Ctrl+O y Ctrl+P. Abrir utiliza un diálogo de archivos del escritorio y conserva el flujo de validación de Reapdf, incluidos contraseña, permisos y confirmación de cambios. Si hay una operación o un diálogo de edición activo, la apertura se bloquea con un mensaje. No se transmite una ruta local arbitraria desde la página al host; el archivo lo selecciona el usuario en el diálogo.

Imprimir solicita al backend el PDF preparado con las operaciones de la sesión y lo entrega mediante QWebChannel al host. La ventana muestra el diálogo de impresión de Qt. No se imprime el HTML del editor ni se requiere abrir una pestaña. Se comprueba el formato, tamaño, rango de páginas y permisos. El modo web habitual conserva su recorrido de impresión existente.

Alcance de impresión actual: ajuste proporcional al área imprimible, páginas seleccionadas y orden inverso cuando lo indica la impresora. Representación raster de hasta 300 ppp, o 150 cuando falta permiso de alta calidad, con un máximo de 16 millones de píxeles por página. El PDF guardado conserva su representación original: este rasterizado corresponde a la impresión. Impresión vectorial, grandes formatos, fidelidad en equipos físicos y opciones avanzadas requieren trabajo y aceptación adicionales.

El editor de bloques carga el texto automáticamente al cambiar de modo. Ctrl+Enter prepara la vista previa; repetirlo aplica la configuración revisada. Se mantiene la confirmación de descarte del borrador al cambiar de modo.

Comprobaciones dirigidas: Qt WebEngine real en Linux offscreen abre un archivo por el menú nativo, comprueba la imagen de página, imprime la segunda página en una impresora PDF controlada y verifica su contenido gráfico y número de páginas. Comprueba también cancelar impresión, rechazo de contenido inválido/páginas sobredimensionadas y las protecciones anteriores de descarga y cierre. La prueba controla los diálogos de archivo/impresora; no equivale a probar una impresora física o Windows. Chromium comprueba carga automática entre modos, cancelación del descarte, Ctrl+Enter, edición TrueType, deshacer/rehacer y exportación.

No se genera instalable ni portable en este avance. Las fuentes y evidencias se respaldan en recovery/editing-20261029.

Resultado de regresión: 2078 pruebas Python, 105 JavaScript, compilación, recorrido Chromium de edición y recorrido Qt de apertura/impresión/cancelación/descarga/cierre aprobados. Registros y huellas en validation/native-print-20261029/. Se mantienen los dos avisos Python conocidos. No se ejecutó toda la suite gráfica histórica.

Pendiente: abrir desde el sistema/segunda instancia, guardar sin el paso de descarga, impresión vectorial/gran formato, icono/inicio y aceptación Windows. Continuar con 6.1 Sol, razonamiento medio. La estimación global de la base recuperada sigue sin auditar; no se incrementa por acumular pruebas ni se reutiliza automáticamente el 61,3 % histórico.
