# Edición directa: párrafos mixtos y fuentes Type3

Este trabajo no es la entrega técnica final solicitada. No se entregó otro instalador/portable ni se pidió al usuario hacer pruebas. Permanecen implementaciones en los ocho bloques del plan. No se recalculó el porcentaje global por esta tanda: la referencia anterior sigue siendo una estimación provisional, sin acreditación de cierre.

## Edición más práctica sobre la página

Editar párrafo ofrece una caja única incluso cuando el original contiene varias fuentes, tamaños y colores. El texto sin cambios conserva sus estilos; una inserción toma el estilo del carácter anterior (al inicio, el primero). Los ajustes por fragmentos permanecen en un apartado avanzado plegado. Reemplazar una selección completa asigna a lo nuevo el estilo de la posición de inserción; no infiere estilos semánticos de lo pegado.

Aplicar o Ctrl+Enter ejecuta la validación de ajuste y composición en el backend. Ya no exige un clic previo en Comprobar ajuste; esa revisión sigue disponible. Un fallo de espacio o compatibilidad conserva el borrador. Deshacer/rehacer del navegador restaura texto y estilos mediante hasta 128 instantáneas acotadas; no mezcla estilos después de borrar y recuperar un rango. El historial del documento aplicado se mantiene independiente.

## Type3 con recursos originales

Se habilitan FontMatrix diagonales positivas con escala entre 1e-6 y 1 y traslación absoluta hasta 10, sujetas además a la verificación de geometría real del texto. El avance se calcula con la escala horizontal efectiva, sin suponer siempre 0.001. Rotación, cizalla y otras matrices permanecen protegidas.

Los glifos d0 admiten imágenes bitmap de color de dispositivo; d1 admite máscaras bitmap. Se comprueban dimensiones, profundidad, longitud real, descompresión Flate acotada, recursos indirectos y caja pintada. Solo se admite Flate simple o datos sin compresión; no máscaras externas, recursos arbitrarios ni otros filtros. Hasta 16 imágenes, 8 MB comprimidos y 16 MB decodificados por recurso de fuente. Los programas y recursos originales se reutilizan; la página no se rasteriza.

Se verificaron caracteres con bitmaps distintos, máscaras distintas, matrices y traslaciones, páginas giradas, Forms compartidos y combinaciones. La comparación independiente a doble resolución cambia solo el operando literal del PDF de referencia; no usa la misma implementación de edición como resultado esperado. Se conservan los programas, bitmaps y páginas/apariciones no seleccionadas.

## Evidencia y límites

3855 pruebas Python de regresión, 209 dirigidas Type3 y 140 JavaScript aprobadas; build y recorridos Chromium/Qt. El backend no cambió después de su regresión general. La interfaz posterior se comprobó con pruebas JS, navegador y escritorio. El caso de desbordamiento conserva el borrador y luego permite corregir/aplicar sin perder los estilos supervivientes. La prueba Qt usa ratón para Type3 y teclado/cursor/deshacer/rehacer para el párrafo, con guardado nativo y reapertura.

Quince recorridos de fuente Linux y Windows Server 2025 aprobados sobre fuente limpia. Windows incluyó ratón Type3 y teclado/cursor/deshacer/rehacer de párrafo mixto, guardado nativo y reapertura. El paquete interno Reapdf.exe pasó ventana propia, edición, deshacer/rehacer, exportación y cierre; no acredita cada herramienta especializada empaquetada. Comprobante 41750022125-1, fuente/objetos Git/logs/huella contrastados. Una primera comprobación de una revisión intermedia falló por falta de respuesta del callback Qt en el plazo de 5 s; no se registró como aprobada. La batería final se ejecutó con servidor aislado y sin otros recorridos gráficos simultáneos.

Fuente final: 300072732915c456641f3831c30158111d8ec07b. [Resultados y logs](validation/mixed-type3-20261104/results.json). Windows cliente limpio, DPI, impresión física y cierre general del producto siguen pendientes.

Siguen pendientes reflujo mixto afín/entre páginas y cambio de fuente generales, variantes de fuentes y composición protegidas, LT/LTA y el resto de PLAN_ACTUAL.md. Ninguno se traslada al usuario como una simple prueba pendiente.
