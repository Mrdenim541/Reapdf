# Párrafos repartidos entre objetos de texto

No es la entrega final del programa. No se entregó otro paquete ni se pidió al usuario hacer pruebas; siguen las implementaciones del plan.

Antes, el reflujo mixto afín estaba limitado a un objeto de texto. Ahora puede reunir objetos completos de un bloque visual continuo con transformación paralela y la misma ruta. Mantiene fuente/tamaño/color de cada fragmento y parchea cada objeto dentro de su contexto original; no rasteriza ni censura la página. La selección automática se valida geométricamente. Si hay huecos, columnas o estados incompatibles, conserva el recorrido previo en lugar de mezclar etiquetas ajenas.

Se conserva la exigencia de seleccionar completos todos los objetos afectados, así como clips, obstáculos y revisión de texto vecino. También funciona dentro de una aparición compatible de Form compartido; las otras apariciones y páginas quedan intactas. El PDF resultante se pudo inspeccionar y editar otra vez, con identificadores nuevos y estilos conservados.

No cubre rutas de Form diferentes, bloques discontinuos, texto etiquetado/composición especial, espaciado especial ni distribución general entre páginas. No se declara terminado todo el bloque de edición ni se recalcula el porcentaje global por este subconjunto.

3935 Python, 362 dirigidas (incluidas 35 nuevas), 140 JavaScript y build aprobados. Casos nuevos: giro/inclinación/reflexión/escala no uniforme, objetos independientes, Form compartido y conservación de otros contenidos, huecos y selección parcial. Qt comprobó ratón/cursor/undo/redo/Ctrl+Enter, guardado nativo y reapertura. Chromium comprobó desbordamiento con borrador conservado y exportación con los estilos originales. Diecisiete recorridos Linux sobre fuente limpia aprobaron; Windows Server 2025 también aprobó 17 recorridos sobre la misma fuente, y Reapdf.exe interno pasó ventana propia, edición, deshacer/rehacer, exportación y cierre. Comprobante 41760358411-1, objetos/logs/huella contrastados; no acredita todas las herramientas empaquetadas ni Windows cliente/DPI/impresión física.

Fuente f63fe3c23b31e1864c6766b4518656fe296bddcf. [Resultados y logs](validation/multi-object-20261104/results.json). Siguen los otros pendientes de PLAN_ACTUAL.md y la solicitud de entrega completa aún no está cumplida.
