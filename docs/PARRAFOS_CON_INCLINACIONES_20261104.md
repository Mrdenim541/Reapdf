**Comprobación en curso: pendientes regresión Python completa y Windows de la fuente exacta.**

# Párrafos con inclinaciones distintas · 4 de noviembre de 2026

Nuevo perfil de edición nativa: fragmentos de un párrafo que comparten dirección de lectura y orientación vertical, pero usan inclinaciones verticales o escalas distintas. Antes se exigía una matriz lineal idéntica y se rechazaba este caso aunque cada fragmento fuese editable por separado. No cierra el reflujo general ni ninguno de los ocho bloques globales.

## Resultado funcional

- Conserva la fuente original, tamaño, color y matriz de cada estilo; no aplana los fragmentos a la transformación del primero ni los convierte en imagen.
- Calcula el espacio ocupado por la inclinación y reserva separación entre fragmentos para que sus celdas métricas no se superpongan. El espaciado y kerning internos se conservan; la separación entre estilos puede aumentar al redistribuirlos.
- Reconoce el caso aunque el primer fragmento sea recto y solo otro esté inclinado. La caja única de edición sobre la página permanece; el usuario puede escribir y aplicar con Ctrl+Enter. Una nota explica la conservación de inclinaciones.
- Conserva la transformación individual también al continuar en otra página y al añadir automáticamente páginas nuevas.
- La selección explícita permite combinar objetos completos de rutas Form diferentes, aislando las apariciones compartidas. Se mantienen las comprobaciones de recorte, obstáculos, fuentes/glifos, composición, firmas y permisos.
- El resultado compatible guardado puede reabrirse para otra edición. Se reconoce la separación añadida por el propio formato. Cuando el extractor divide el resultado en bloques distintos sin una asociación verificable, puede requerirse selección explícita; no se inventa una agrupación de párrafo.

## Comprobaciones

Las pruebas comparan las transformaciones lineales, fuentes, tamaños y colores con el documento original, comprueban que no hay superposición de las celdas y que las apariciones Form no elegidas y otras páginas conservan sus píxeles. Incluyen rotaciones de página, reflexión compatible del marco común, escala horizontal, inclinaciones positivas/negativas, tracking/espacio de palabra y pares TJ retenidos, continuación manual y paginación automática. También se comprueban reapertura/reedición, API de inspección/vista previa/aplicación, desbordamiento atómico y rechazo de glifos/direcciones incompatibles.

El recorrido Qt selecciona con el ratón, escribe con el cursor en la caja única, guarda con el diálogo nativo, reabre para otra edición, añade páginas por desbordamiento, deshace/rehace y vuelve a guardar/reabrir. Las comprobaciones del ejecutable se registran por separado; el diálogo nativo de guardado no se atribuye a una exportación por API.

## Límites conservados

Se requiere dirección de lectura común y orientación vertical compatible, objetos completos y contenido visible verificable. No habilita direcciones incompatibles dentro del mismo párrafo, escritura RTL o vertical, composición especial, fuentes o glifos no compatibles ni párrafos etiquetados mixtos/ActualText/Stm generales. No incorpora cambio general de fuente o edición universal de CFF2/Type3.

Continuación conserva sus áreas vacías verificadas; la paginación mantiene el límite de 16 páginas nuevas. Si no cabe, se conserva el borrador y no se publica texto parcial. Los casos nuevos utilizan documentos sintéticos, sin PDFs o capturas personales en Git. No se afirma que el PDF de 42 páginas de las capturas haya sido probado para este perfil.

No se publicó otro portable. El preview anterior no incorpora estas mejoras. Windows Server y las pruebas automatizadas no sustituyen Windows cliente limpio, DPI, impresión física, carga sostenida ni aceptación personal final.

## Incidencia de comprobación del paquete (pendiente)

La fuente 917ecec aprobó 4.540 pruebas Python y 33 recorridos de fuente en Linux/Windows. El candidato se generó, pero el verificador agotó 25 s esperando el cierre del recorrido de paginación, antes de ejecutar el perfil nuevo. El primer log no registra los diálogos y no permite confirmar la causa. Se conserva el intento fallido.

Se amplió únicamente el verificador para detectar la confirmación nativa conocida «Cambios pendientes» del proceso de prueba y elegir Descartar; registra otras ventanas propias si persiste un bloqueo. El quinto recorrido exige pasar por esa confirmación. No se cambia closeEvent del producto ni se declara resuelta toda intermitencia histórica. La nueva ejecución está pendiente.
