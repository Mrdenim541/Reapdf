# Edición de texto con giros, inclinaciones y reflejos

29 de octubre de 2026. **Avance total estimado: 76,08 % (≈76 %), antes 75,50 %.** Diecisiete áreas y pesos sin cambios; aumentan edición e interfaz. La cifra es una valoración de madurez del alcance completo, no un porcentaje medido de paridad comercial. [Matriz](avance-global.json), [plan](PLAN_ACTUAL.md).

## Implementado

La edición con fuente original admite transformaciones afines verificables: giro interno, inclinación, reflexión horizontal/vertical y combinaciones con escala. Abarca texto directo con matrices gráficas `cm`, matrices de texto `Tm` y apariciones aisladas de Forms compartidos. Se mantienen los operadores y matrices originales: se cambian únicamente los operandos de texto seleccionados y se copia la ruta de la aparición cuando es compartida. Las demás apariciones/páginas y los programas de fuente se conservan.

El motor comprueba fuente/códigos/glifos, origen y tamaño transformados, dirección de escritura y cada origen de carácter. Las cajas se derivan de la matriz y de las métricas de la fuente. Los recortes de Forms se conservan como polígonos, en lugar de ampliar su área a una caja rectangular. Se rechazan matrices singulares o excesivamente deformadas y cajas de recorte vacías/invertidas. Siguen aplicándose los presupuestos de grupos, profundidad, fuentes y contenido copiado.

Los choques se comprueban con la celda transformada. Un fragmento en una esquina vacía de la caja exterior no bloquea por sí solo la edición. El texto nuevo no invade otros fragmentos, imágenes, campos o anotaciones ni sale de su región, página o recorte. La ampliación explícita de una región admite crecimiento sobre la línea de base reflejada, si todas las restricciones se cumplen. No es reflujo automático de párrafo.

Tras guardar, un lector nuevo comprueba el texto resultante, su origen, caja y color antes de publicarlo. La eliminación comprueba que no quede texto residual en ese origen. Un fallo de verificación no crea una versión aceptada ni sobrescribe el archivo fuente.

## Uso sobre la página

La selección utiliza cuadriláteros transformados, con un contorno activo al editar. El cuadro de escritura permanece legible y derecho, aunque el texto del PDF esté reflejado o girado; al aplicar conserva la geometría original. El campo dispone de un ancho mínimo útil en fragmentos verticales. Se comprueban selección con ratón, deshacer/rehacer y exportación.

En fragmentos transformados se bloquean las opciones de cambiar a una fuente incluida o reescribir el párrafo cuando descartarían su matriz. También se refuerza la comprobación del motor: contenido no analizable, como el caso probado de imagen inline con texto reflejado, no habilita una sustitución horizontal silenciosa.

Las regiones con fragmentos vecinos cortados pueden mostrar esos vecinos como no editables sin impedir modificar el fragmento completo que sí se seleccionó. La coincidencia de texto/origen y los identificadores se vuelven a validar en el servidor; los contornos visuales por sí solos no autorizan una edición.

## Alcance y límites

Fuentes probadas: base, TrueType, OpenType CFF y CID CFF con su programa original. Casos directos, matrices de texto y Forms; giros de página 0/90/180/270 y recortes. No se afirma soporte de cualquier matriz ni cualquier fuente.

CFF2, fuentes variables y Type3, escritura vertical/RTL compleja, grupos de transparencia, estructura semántica de Forms, alternativas ActualText y estados intermedios incompatibles siguen pendientes o protegidos. La edición de una línea no crea glifos ausentes, cambia de fuente ni redistribuye texto automáticamente. El reflujo y la sustitución de fuente de texto afín siguen fuera.

Las celdas usan métricas de fuente para una comprobación conservadora: pueden rechazar una proximidad que visualmente parezca libre entre contornos de tinta. Otras anotaciones se protegen por su caja. Los objetivos visuales se calculan sin volver a analizar programas de fuente; cada modificación sí realiza la comprobación completa. Contenido desconocido queda sin editar cuando no se puede demostrar compatibilidad.

No se amplía la edición directa de documentos firmados ni se conserva la validez de una firma después de alterar contenido. Permanece el flujo de copia de trabajo identificada.

## Validación real

- **2735 pruebas Python** en la regresión completa. Posteriormente se añadió el caso de imagen inline/reflexión y se reforzó la protección de sustitución: **447 pruebas dirigidas** aprobadas sobre los módulos afectados. No se presenta como una sola ejecución sobre código inmutable.
- **116 pruebas JavaScript**, compilación y tres recorridos Chromium aprobados: nuevo texto afín, regresión CFF/Form/párrafos y regresión de flujo/portfolios.
- **Qt Linux real:** abrir un PDF sintético con Form TrueType inclinado, editar sobre la página y guardar con el menú nativo; fuente, recorte, segunda aparición y otra página conservados. El archivo fuente permanece intacto. No es una verificación Windows.
- Inspección de solo lectura del PDF privado de referencia: continúa siendo compatible con edición original. No se modificó ni publicó ese archivo.

Las pruebas cubren 141 casos nuevos de texto afín, incluidos reflejos, inclinaciones, giros internos, ampliación, obstáculos, recortes, singularidad y lotes atómicos. [Registros y huellas](validation/affine-text-20261029). La prueba Qt y los recorridos positivos preceden al última comprobación conservadora de sustitución; la comprobación dirigida final cubre ese guardado.

Sin instalador/portable nuevo, aceptación personal, impresión física, prueba en Acrobat/Nitro ni validación Windows. No se instaló REA ni se inspeccionaron programas comerciales.

## Próximos trabajos

1. Fuentes restantes: CFF2, variables y Type3, con mapas y programas comprobables. Evaluar subconjuntos seguros antes de habilitar edición; no sustituir fuentes silenciosamente.
2. Estados gráficos y estructura de Forms todavía protegidos: estudiar transparencia y semántica sin repetir como pendientes los giros/inclinaciones/reflejos ya admitidos.
3. Cerrar la validación Windows y migrar el recorrido histórico pendiente cuando corresponda. La prueba personal sigue aplazada.
4. Ampliar las áreas comerciales que mantienen su valoración: formularios complejos, conversión/OCR, accesibilidad, firmas/estándares, servicios, licencias y corpus externo.

Continuar con **6.1 Sol, razonamiento medio**.
