# Reflujo mixto en el marco original

No es la entrega final solicitada. No se entregó otro portable/instalador ni se pidieron pruebas personales. El alcance general de PLAN_ACTUAL.md sigue abierto. No se recalculó el porcentaje por este subconjunto.

## Qué cambió respecto al trabajo anterior

El trabajo anterior permitía editar párrafos mixtos horizontales en una caja única. El reflujo afín existente exigía una sola fuente, tamaño y color. Ahora el editor acepta estilos paralelos distintos dentro de un mismo objeto de texto inclinado, girado, reflejado o con escala no uniforme. Conserva fuentes, tamaños, colores y transformación. La misma caja única y Ctrl+Enter envían los fragmentos originales al recorrido afín; no se añade un asistente ni un panel lateral obligatorio.

También se habilita una aparición opaca y compatible de un Form compartido con estilos mixtos, incluidas las horizontales que antes se bloqueaban por contener Forms. Las otras apariciones y páginas se conservan. El caso horizontal uniforme conserva su protección anterior; no se amplía por accidente la edición con composición especial.

## Integridad del cambio

Se reemplazan operandos de texto mediante el escritor nativo y se aíslan las invocaciones compartidas. No se censura ni rasteriza la página y no se sustituyen los programas de fuente. Cada estilo se escribe dentro de su contexto original. Las matrices se calculan en el marco local; el borde superior del párrafo se conserva también cuando el primer estilo es más pequeño que otro.

La verificación admite que el lector fusione fragmentos iguales al borrar un estilo intermedio; se verifican caracteres y cajas sin exigir la segmentación original. Antes de publicar el resultado se comprueban glifos, geometría, recortes, límites de página y obstáculos. Se revisa el texto vecino después de escribir. La selección debe incluir el objeto completo y los identificadores/estilos deben coincidir con el texto completo. Una selección cortada, obsoleta o desordenada se rechaza. Un error de ajuste conserva el borrador en la interfaz.

Límites: hasta 100 grupos y 4000 caracteres, dimensiones locales de 10 a 2000 pt; fuentes y avances ya verificables. Estilos paralelos del mismo objeto/ruta, sin composición especial ni espaciado Tc/Tw. El contenido etiquetado, la mezcla entre objetos, la distribución general entre páginas, recursos no verificables y composiciones especiales siguen pendientes. Los bordes se tratan de forma conservadora: no se acredita reflujo general dentro de cualquier celda dibujada.

## Comprobación

3900 pruebas Python de regresión; 45 dirigidas nuevas de reflujo mixto afín. 140 JavaScript y build aprobados. Los casos nuevos cubren giros de página, inclinación, reflexión, escala no uniforme, varias líneas, tamaño inicial menor, Form compartido, API/revisión/aplicación e integridad ante identificadores obsoletos, recortes, colisiones, salida de página, glifos ausentes y contenido protegido.

Qt comprobó ratón sobre el texto, edición con cursor, deshacer/rehacer, Ctrl+Enter, guardado nativo atómico y reapertura sobre un Form compartido en página girada; fuentes/estilos, otras páginas y archivo original conservados. Chromium comprobó selección, caja única, desbordamiento con borrador conservado y posterior aplicación/exportación correcta.

Dieciséis recorridos de fuente Linux aprobaron con fuente limpia antes/después. Windows Server 2025 también aprobó 16 recorridos y el paquete interno Reapdf.exe pasó ventana propia, edición, deshacer/rehacer, exportación y cierre. Comprobante 41756542882-1, fuente/objetos/logs/huella contrastados. No acredita cada herramienta especializada empaquetada ni Windows cliente/DPI/impresión física.

Una comprobación inmediata del teclado falló una vez en Linux. Se sincronizaron dos pruebas para esperar el estado exacto tras eventos asíncronos y espaciar teclas 20 ms; dos repeticiones y la batería final Linux aprobaron. No se modificó el programa. Windows corresponde a 3730f140548a565bd682f02dab8b3c26e46ef0a2 y Linux al ajuste de pruebas 585fe0b91475beae2aab334d6644473a6d037470: todos los objetos Git de aplicación coinciden; solo difieren esos dos scripts de prueba. Los logs anteriores y posteriores se conservan. Fuente: 3730f140548a565bd682f02dab8b3c26e46ef0a2. [Resultados y logs](validation/affine-mixed-20261104/results.json).
