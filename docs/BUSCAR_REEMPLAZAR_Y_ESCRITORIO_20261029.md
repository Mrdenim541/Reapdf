# Buscar y reemplazar, instancia única y preparación Windows

## Buscar y reemplazar

Nueva herramienta del área Editar, accesible también con Ctrl+H. Admite texto literal, mayúsculas/minúsculas, palabras completas y ámbito de página, rango o documento. Permite elegir una coincidencia, un conjunto o todas las compatibles. Las coincidencias aparecen resaltadas dentro de su contexto; la vista previa ocupa un panel separado.

Se revisa el resultado antes de aplicar. Cambiar consulta, reemplazo o selección invalida la vista previa. El backend vincula los resultados al PDF y operaciones de entrada y comprueba el plan antes de publicar una nueva versión. Si un fragmento falla, no se publica un lote parcial. Deshacer/rehacer revierte/restaura todo el lote. Las fuentes, tamaño, color, posición y contenido no seleccionado se conservan dentro de la compatibilidad del motor original.

Límites actuales: 500 resultados, dos millones de caracteres analizados, hasta 100 coincidencias en 20 fragmentos distintos por aplicación y 1000 caracteres de reemplazo. El texto nuevo debe caber en el ancho original. Coincidencias dentro de un mismo fragmento digital; no cruza fragmentos, estilos o líneas ni reconoce escaneados. Las búsquedas con espacios inferidos por el lector pueden diferir de la búsqueda visual del visor. Fuentes ausentes, capas, marcado, transparencias, formas complejas y firmas se mantienen protegidos por el motor. Un resultado visible no implica que pueda reemplazarse: la interfaz informa del motivo.

La vista previa calcula todos los cambios elegidos y muestra imágenes de las primeras tres páginas afectadas. No es censura de información confidencial ni reemplazo forense: para eliminar datos sensibles se utiliza la herramienta de censura.

## Ventana existente y recuperación del arranque

La instancia de escritorio se identifica por usuario e instalación. QLockFile y QLocalServer controlan el reenvío local y evitan abrir otra ventana. Una invocación sin archivo activa la existente; una ruta PDF se valida y encola. La aceptación de la solicitud confirma su recepción, no que el usuario haya aceptado descartar cambios.

Una edición pendiente sigue protegida: rechazar el descarte conserva el borrador y el documento; confirmar permite abrir el siguiente PDF. Las operaciones o diálogos activos retienen la apertura en la cola. Se limita el número de conexiones, tamaño/tiempo de mensaje y cola de archivos. Si el proceso propietario murió, el bloqueo obsoleto se recupera antes de volver a escuchar. Un proceso activo sin respuesta produce error y no se sustituye por una copia adicional.

La segunda invocación termina su propio arranque tras reenviar la solicitud. La arquitectura actual puede iniciar brevemente su backend antes del reenvío; no se afirma que solo exista un proceso del sistema. Qt WebEngine utiliza además sus procesos de representación habituales.

## Preparación de Windows

El arranque C ahora recibe una ruta PDF con espacios/Unicode y la entrega al modo Qt. Se corrigió el final de una segunda invocación exitosa para no mostrar un error de arranque. El código compiló a Windows x64 GUI con Zig 0.13.0; no se ejecutó en Windows.

`portable/windows_association.py` genera, sin aplicar, archivos .reg de registro y retirada. Añade Reapdf a Abrir con mediante HKCU y no modifica el lector predeterminado ni UserChoice. La retirada elimina solo las entradas de Reapdf. El texto usa UTF-16 y CRLF sin traducción adicional en Windows. Ejemplo para preparar una revisión:

`python portable/windows_association.py --executable "C:\Program Files\Reapdf\Reapdf.exe" --output Reapdf-abrir-con.reg`

No importar ese archivo hasta que el paquete final exista en esa ruta y se haya validado en Windows. Los helpers de escritorio y las dependencias Qt Windows quedaron incorporados al procedimiento de empaquetado, con versiones y hashes oficiales fijados. No se descargaron ni ensamblaron esos wheels Windows en este avance. No se generó un instalador ni un portable nuevo; solo se compiló el pequeño arranque en una carpeta temporal para comprobar el código.

## Evidencia y continuación

Regresión local: 2116 pruebas Python y 105 JavaScript aprobadas; compilación de interfaz y del arranque Windows. Cinco recorridos dirigidos: Buscar/reemplazar y edición en Chromium; reenvío con otro proceso, guardado e impresión/cierre con Qt Linux offscreen. La prueba de fuente TrueType comprueba el programa original y usa Poppler cuando está disponible. También se comprueban planes obsoletos, glifos ausentes, fallos tardíos, páginas giradas, límites, bloqueo obsoleto y rechazo del descarte. No suite gráfica histórica completa ni aceptación Windows. Evidencias: validation/find-replace-desktop-20261029/.

Estimación global: 48,8 % ponderado, aproximadamente **49 %**, intervalo subjetivo 40–60 %. Edición 50→55 (+0,8 puntos globales); escritorio 40→45 (+0,3). Las otras quince áreas y todos los pesos se conservan. Referencia anterior: progress/20261029-before-find-replace.json.

Siguiente pasada recomendada: ampliar compatibilidad de edición y reemplazos entre fragmentos/lotes, y preparar pruebas Windows del escritorio. Modelo recomendado: 6.1 Sol, razonamiento medio. Generación de documentos de ensayos, registros e informes personales excluida; vinculación configurable de documentos continúa pendiente.
