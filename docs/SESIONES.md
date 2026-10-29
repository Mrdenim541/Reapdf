# Proyectos y recuperación — versión 0.13

## Guardar para continuar editando

**Guardar proyecto**, en la barra de recuperación o en Archivo, descarga un archivo `.reapdf`. También funciona Ctrl+S (Cmd+S en equipos Apple). **Archivo → Abrir proyecto…** permite retomarlo en otro inicio o equipo con una versión compatible de Reapdf.

El proyecto incluye el PDF base de la versión actual, sus cambios aplicados, nombre, página y zoom. Las marcas, imágenes, cajas de texto, sellos y enlaces nuevos de esa versión conservan sus controles de edición. Desde 0.15 también se conservan el índice editable y la configuración de encabezados/pies y numeración; desde 0.16, los valores aplicados de los campos de formulario. Crear desde imágenes inicia otro documento; exportar imágenes no sustituye el proyecto o PDF editable. No guarda texto/notas/medidas pendientes de Aplicar, ni el historial completo anterior. Al restaurar empieza un historial nuevo: se pueden deshacer los cambios que se hagan desde ese momento. Las ediciones incorporadas al PDF por operaciones de páginas siguen siendo contenido existente.

**Exportar copia** genera el PDF para otros lectores. Guardar un proyecto permite conservar el trabajo editable, pero no equivale a exportar ese PDF. La descarga se prepara en el navegador: verifica que el archivo quede guardado en la carpeta elegida.

## Recuperación automática local

Después de abrir un documento o aplicar cambios, se programa un guardado aproximadamente un segundo después del último cambio. La barra indica si está pendiente, guardando o actualizada. El tiempo real depende del tamaño del PDF, del motor y del disco. Cerrar antes de que indique **Recuperación local actualizada** puede perder los últimos cambios. Los borradores sin aplicar no entran en este guardado.

Al volver a abrir Reapdf, **Recuperar sesión** restaura el último punto válido. Sirve tras recargar el navegador, cerrar normalmente el servidor o interrumpirlo una vez completado el guardado. Es un punto de recuperación, no un historial de versiones ni una garantía frente a daños del disco. La página y el zoom corresponden al momento del checkpoint; para guardar expresamente la vista actual usa Guardar proyecto.

Hay un solo punto local por usuario y directorio de datos. Abrir otro documento desde la bienvenida avisa antes de reemplazar una sesión recuperable. Varias ventanas no deben editar simultáneamente el mismo punto: el bloqueo del sistema y la revisión del archivo impiden que una escritura basada en una revisión antigua lo sobrescriba. Si hay conflicto, guarda un proyecto aparte y vuelve a abrir la aplicación.

**Descartar recuperación**, en la bienvenida, elimina ese punto después de confirmar. No elimina los PDF ni proyectos descargados. Si falla el almacenamiento, la aplicación conserva el documento en memoria, informa del problema y mantiene la recuperación anterior. Guarda un proyecto o exporta un PDF; **Reintentar recuperación** vuelve a consultar el estado y permite guardar cuando el problema se resuelva.

## Ubicación y privacidad

La recuperación conserva contenido documental en el equipo, incluso después de cerrar el programa:

- Windows: `%LOCALAPPDATA%\Reapdf\recovery.reapdf`.
- Linux: `$XDG_STATE_HOME/reapdf/recovery.reapdf` o `~/.local/state/reapdf/recovery.reapdf`.
- Para configurar otra carpeta, define `REAPDF_DATA_DIR` antes de iniciar el motor.

El portable guarda su recuperación en el equipo de ejecución; para llevar el trabajo en una memoria USB, guarda un proyecto en esa memoria. No se instala un servicio ni se envían documentos a servicios externos. El checkpoint no está cifrado por Reapdf; aplica el mismo cuidado que a los archivos PDF originales. No se guardan en el ZIP de distribución los archivos personales de recuperación.

## Formato y límites

El formato 1 es un ZIP con exactamente `manifest.json`, `base.pdf` y `operations.json`. Los SHA256 detectan daños o cambios en el PDF/operaciones; no son una firma de identidad. Se comprueban formato, tamaños declarados, integridad, dimensiones/estado, permisos y las operaciones reales al abrir. No se extraen rutas del ZIP al sistema de archivos.

Hasta 60 MB de PDF base, 5 MB de operaciones y 70 MB por proyecto; se mantienen los límites de 500 páginas, 1000 operaciones y las restricciones de imágenes. Las solicitudes JSON completas siguen limitadas a 5 MB. La importación debe caber en los 300 MB temporales de documentos y versiones. Los fallos no reemplazan el documento abierto. Una versión futura incompatible se rechaza y requiere migración explícita.

El checkpoint se escribe en un temporal del mismo directorio, se sincroniza y se reemplaza atómicamente. Una escritura fallida mantiene el punto anterior. El bloqueo entre procesos se libera al terminar el proceso. La validación de Windows real sigue pendiente; las pruebas actuales se ejecutaron en Linux.
