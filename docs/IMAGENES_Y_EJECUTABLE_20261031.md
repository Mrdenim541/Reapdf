# Edición de imágenes por aparición y comprobación del ejecutable

La orden de entrega completa queda registrada en `AGENTS.md`. Las pruebas personales se realizan al final; no sirven para sustituir implementaciones pendientes. Este documento describe trabajo técnico y evidencia, no una entrega completa del producto.

## Cambios funcionales

El editor de imágenes permite seleccionar con el ratón la aparición que se desea modificar, incluso si varias posiciones o páginas comparten el mismo objeto de imagen o Forms anidados. La selección se transmite al servidor mediante un identificador de aparición. Una solicitud antigua que solo indique un xref compartido se rechaza por ambigüedad.

Mover/redimensionar modifica únicamente la invocación seleccionada, conservando su orientación, filtro y máscara alfa. Reemplazar importa el archivo nuevo en los recursos independientes de la aparición. Eliminar retira esa invocación; no es una operación de censura. Los Forms y diccionarios de recursos se separan mediante copia al escribir, conservando los recursos heredados. Se mantiene la vista previa, aplicación, deshacer y rehacer. Antes de devolver el resultado se reabre el PDF serializado y se comprueba la aparición editada, las demás imágenes y el texto.

Los PDF etiquetados, capas incompatibles, imágenes inline, páginas OCR y cajas que saldrían del recorte de un Form siguen protegidos. Una protección es una limitación de compatibilidad, no una función completada. No se afirma edición universal de objetos PDF.

Corregida también la configuración de portfolios cuyos adjuntos comparten FileSpec o diccionario CI: título, descripción y orden se editan por entrada independiente, preservando otros metadatos, adjuntos y portada.

Los editores especializados se cargan al abrirlos. El JavaScript inicial baja de 619,38 a 344,78 KB (aproximadamente 44 %); comprimido, de 172,40 a 106,20 KB. No se eliminan herramientas del catálogo. El pie de la ventana identifica el escritorio y elimina la versión antigua 0.41 que no correspondía al código actual.

La guía integrada y `MANUAL_DE_FUNCIONES.md` se actualizan con los pasos de selección y los límites reales de imágenes. El manual actual cubre 73 herramientas y 15 operaciones generales; esa cobertura documental no acredita paridad comercial.

## Comprobación del paquete

El verificador anterior ejecutaba el Python incluido y probaba HTTP, proyectos, recuperación e impresión preparada. Ese resultado ya no marca por sí solo `windows_execution_verified`.

La comprobación ampliada extrae el paquete en una ruta con espacios y arranca el `Reapdf.exe` compilado con un PDF de ejemplo. Identifica una ventana Qt perteneciente al intérprete incluido, exige el puente nativo, edita texto sobre la página, deshace/rehace, exporta y verifica el contenido con el intérprete del paquete. Comprueba además el cierre normal del ejecutable y que el original permanezca intacto. La exportación de este recorrido usa el servidor de la ventana; no se presenta como una prueba adicional de diálogo nativo de guardado. El guardado atómico y los diálogos se prueban en los recorridos Qt separados.

La conexión de automatización se habilita únicamente en el entorno del proceso de verificación, vinculada a loopback. El programa normal no habilita ese puerto. No se lanza un navegador externo para esta comprobación.

El comprobante registra revisión Git, objetos de fuente, estado limpio y SHA256 del archivo probado. Un informe ausente, incompleto, de otra fuente o que solo pruebe el motor mantiene el paquete sin aprobar. El paquete es interno de CI: no se publica ni se entrega como producto terminado.

La primera ejecución Windows construyó el paquete, superó las once comprobaciones desde fuente y llegó a la ventana del ejecutable, pero falló la conexión del controlador de pruebas porque Qt no admite `Browser.setDownloadBehavior`. Se corrigió el controlador para conservar la configuración de Qt mediante `noDefaults`; el recorrido de conexión se comprobó en Qt Linux antes de repetir Windows. No se presenta el primer intento como un paquete aprobado.

## Estado de cierre

La revisión **c24f30573347e5c19c2ca1366787eb3c958a1d58** pasó las once comprobaciones Qt tanto en Windows Server 2025 como en Linux, con fuente limpia antes/después. El paquete interno, con Python 3.13.16, pasó la comprobación real de Reapdf.exe descrita arriba y el cierre normal. Comprobante de CI `41224374646-1`, recuperado por Git y verificado contra la fuente exacta. SHA256 del archivo probado: `2da3547abe2f7475dea6b67437351e0a232f594eb7ba0be1cec952c7f1115f71`.

La regresión final aprobó **3667 Python**, con tres avisos conocidos; **189 dirigidas**, solapadas con la general; **128 JavaScript**; compilación y recorridos Chromium de imágenes compartidas y uso cotidiano. La evidencia se conserva en [validation/images-executable-20261031/results.json](validation/images-executable-20261031/results.json), con informes y huellas de logs. La aclaración de la guía portable y esta documentación se escribieron después de validar; el código ejecutable no cambió.

La estimación ponderada pasa de 84,88 % a **85,18 % (≈85 %)** al elevar escritorio de 80 a 85 por la prueba real del ejecutable incluido. Se conservan los diecisiete pesos y el alcance; no se suma por documentación o repetición de comprobaciones. El programa **no está técnicamente completo**: permanecen los pendientes funcionales de los ocho bloques, Windows cliente limpio/DPI/asociaciones/impresión física/estabilidad y el cierre de distribución. No se entrega el paquete interno ni se solicita revisión personal intermedia. La guía por función está preparada, pero no sustituye esas implementaciones.
