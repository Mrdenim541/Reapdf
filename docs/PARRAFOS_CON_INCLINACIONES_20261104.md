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

## Incidencias del procedimiento de comprobación

La primera fuente, 917ecec, aprobó 4.540 pruebas Python y 33 recorridos fuente Linux/Windows. El paquete se construyó, pero el verificador agotó 25 s esperando el cierre del recorrido de paginación, anterior al perfil nuevo. Se conserva el informe y el log; no recogía diálogos y no permite demostrar qué causó ese bloqueo.

Se cambió solo el verificador: identifica por PID el diálogo propio conocido «Cambios pendientes», elige Descartar para el documento sintético ya exportado y diagnostica otras ventanas si no cierra. El quinto recorrido fuerza ese estado para exigir una comprobación real de la confirmación y salida normal. Cinco pruebas unitarias comprueban que no interactúa con otros procesos o diálogos desconocidos ni repite indiscriminadamente la acción. El código de aplicación backend/portable/web y el manual son idénticos a 917ecec; no se modificó closeEvent ni se declara corregida la causa de toda intermitencia histórica.

La primera repetición Linux de la revisión del verificador no recibió un callback de Qt durante el scroll al texto, antes de editar; se conserva el fallo y se repite sin alterar el producto. La repetición final se registra abajo por separado. Ningún intento fallido se cuenta como aprobado.

## Verificación final

Fuente `2bf53913f27eaebf0d8d4b395a9e0ede33f5b501`, respaldada en recovery/editing-20261029.

- **4.545 pruebas Python aprobadas (62 funcionales nuevas + 5 del verificador)**, 3 advertencias conocidas; 151 pruebas JavaScript, build y manual 75 herramientas + 15 operaciones generales aprobados.
- **33 recorridos Qt Linux y 33 Windows Server 2025**, fuente limpia antes/después; comprobante `41946587633-1` contrastado con objetos Git y hashes de los logs.
- **Cinco aperturas independientes de Reapdf.exe**. La quinta selecciona estilos con inclinaciones distintas, edita en la caja única, continúa en una página vacía y deshace/rehace. Exporta mediante el servidor real del paquete; su intérprete compara las fuentes, tamaños, colores y matrices con el original y verifica todo el texto y la página ajena. Identidad de ventana Qt y cierre normal comprobados, sin navegador externo.
- Guardado nativo, reapertura y otra edición, además de paginación automática, comprobados en el recorrido fuente Qt. No se atribuye ese diálogo nativo a la exportación del recorrido compilado.

**Estimación global de referencia: 87,14 % provisional, sin recalcular en esta pasada.** Se registran las capacidades nuevas y sus límites sin cambiar pesos, alcance o madurez de las áreas ni presentar el perfil como un bloque general terminado. La cifra anterior no es una medición de paridad con Acrobat ni de horas restantes. Los ocho bloques generales siguen abiertos.

[Evidencia](validation/sheared-paragraphs-20261104/results.json) · [Manual](funciones-uso.json) · [Pendientes generales](PLAN_ACTUAL.md).
