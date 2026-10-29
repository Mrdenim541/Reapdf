# Guardado directo y archivo inicial

El escritorio ahora guarda PDF y proyectos directamente mediante el puente Qt. Guardar PDF (Ctrl+S) pide destino la primera vez y lo reutiliza durante la misma sesión de documento, incluidas versiones avanzadas y deshacer/rehacer. Guardar PDF como (Ctrl+Shift+S) pide otro destino. El botón Exportar copia mantiene la elección explícita de destino. Guardar proyecto utiliza un destino separado.

El estado de guardado solo cambia después de una escritura confirmada. Cancelar o fallar conserva los cambios pendientes. QSaveFile escribe de forma atómica, sin habilitar escritura directa como alternativa: un fallo conserva el archivo anterior. El original abierto se mantiene hasta que el usuario seleccione explícitamente reemplazarlo. Si el destino cambia externamente, se pide elegir y revisar el destino; cancelar conserva el contenido externo.

Se puede pasar una ruta de PDF al iniciar el modo nativo:

`PYTHONPATH=. .venv/bin/python portable/launcher.py --native-desktop /ruta/documento.pdf`

La ventana espera a que la interfaz esté preparada y abre el archivo mediante las validaciones existentes. Es la ruta de arranque necesaria para una futura asociación con Windows; no se afirma que exista ya una asociación instalada ni control de segunda instancia. Se mantienen límites de tamaño y protección de la edición pendiente.

Comprobación real en Qt Linux offscreen: archivo inicial, edición del texto visible, cancelación con estado pendiente conservado, guardado correcto, conservación del original, reutilización del destino y rechazo de sobrescritura tras modificación externa. Pruebas unitarias de escritura atómica, datos inválidos y destino inaccesible. Se repiten los recorridos de impresión/descarga/cierre y edición de bloques. Evidencias en validation/native-save-20261029/.

No se entrega otro portable. Pendientes: Windows, segunda instancia, asociaciones definitivas, persistencia de destinos entre sesiones y aceptación personal. Próximo modelo recomendado: 6.1 Sol, razonamiento medio.

Resultado local: 2082 pruebas Python y 105 JavaScript aprobadas, compilación y tres recorridos dirigidos (edición Chromium, apertura/impresión/cierre Qt y archivo inicial/guardado Qt). No suite gráfica completa ni ejecución Windows. Nueva referencia global reconstruida: aproximadamente 48 %, explicada en AUDITORIA_GLOBAL_20261029.md.
