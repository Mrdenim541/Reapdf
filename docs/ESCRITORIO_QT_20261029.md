# Ventana propia y protección de borradores

La base recuperada ahora dispone de un alojamiento Qt con QWebEngineView. El proceso de Reapdf crea su propia ventana y utiliza un motor web integrado; no necesita abrir Chrome/Edge instalado. La interfaz React y el motor PDF actuales se reutilizan.

Inicio de desarrollo: instalar `requirements-desktop.txt`, compilar con `npm run build` y ejecutar `PYTHONPATH=. .venv/bin/python portable/launcher.py --native-desktop`. El lanzador reserva el puerto local, inicia el backend y termina el servidor cuando sale su ventana. Si falta Qt o el proceso falla, el modo nativo exige la dependencia y comunica el fallo. El modo antiguo `--desktop` permanece para compatibilidad con el paquete histórico; no representa la entrega futura acordada.

Implementado: ventana propia, perfil de sesión no persistente, navegación principal restringida al origen local, diálogo de guardado para descargas, confirmaciones JavaScript integradas y comprobación de cambios/borradores al cerrar. Las operaciones activas bloquean el cierre normal. Cancelar conserva la ventana; Descartar confirma su cierre. Los cambios entre los modos de edición de párrafo piden confirmación antes de descartar contenido modificado.

Validación: scripts/smoke_native_window.py utiliza Qt WebEngine real en Linux offscreen con GPU desactivada solo en el entorno de prueba. Abre un PDF a través de la interfaz, comprueba la carga de la imagen de página, descarga mediante el diálogo de archivo controlado por la prueba, verifica texto exportado y comprueba las decisiones de cierre. La prueba detectó y permitió corregir la serialización del estado entre JavaScript y Qt. scripts/smoke-recovered-editing.mjs comprueba edición TrueType y cancelación de cambio de modo conservando el borrador.

La cancelación o interrupción de una descarga PDF/proyecto mantiene protección al cerrar hasta guardar una copia o confirmar el descarte. Esto cubre el caso en que la interfaz haya preparado la descarga pero el usuario cancele el diálogo de destino.

Resultado: 2078 pruebas Python y 105 JavaScript aprobadas, compilación, recorrido Chromium de edición y recorrido Qt de carga/render/descarga/cierre aprobados. Dos avisos Python conocidos; Qt emitió avisos de GPU/Vulkan/OOM del contenedor durante la ejecución offscreen. No se desactivó el sandbox de Chromium para superar las pruebas.

Pendientes: ejecución Windows real, integración completa de abrir archivos/segunda instancia/impresión, icono y arranque de marca, distribución de las dependencias Qt y aceptación de usabilidad. No se afirma que todo el escritorio esté terminado. No se genera instalable ni portable en este avance. No se restaura el código 0.55 que sigue sin localizarse.

Pruebas y huellas de esta entrega se conservan en validation/native-20261029/. El porcentaje global sigue pendiente de auditar para la base recuperada; el 61,3 % histórico no es una medición de estos cambios.

Siguiente bloque recomendado: abrir y guardar desde controles de escritorio, integración de impresión y simplificación del editor de texto. Modelo recomendado: 6.1 Sol, razonamiento medio.
