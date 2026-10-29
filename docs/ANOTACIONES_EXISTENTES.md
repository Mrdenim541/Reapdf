# Anotaciones existentes — versión 0.9

Seleccionar marca incluye ahora el panel **Marcas del PDF**. Permite seleccionar mediante la página o una lista, cambiar el color de trazo de marcas compatibles, corregir el contenido de notas y eliminar anotaciones. Cada cambio validado entra en deshacer/rehacer y se refleja en vista previa, miniaturas y exportación. El archivo de entrada permanece intacto.

## Tipos y alcance

Admitidos: notas Text, trazos Ink, líneas/flechas Line, rectángulos Square, elipses Circle (desde 0.26), resaltados Highlight, subrayados Underline y tachados StrikeOut. El contenido editable se limita a notas Text, con hasta 4000 caracteres y saltos de línea. No se interpreta texto libre FreeText como una nota ni se modifican campos de formulario.

Los demás tipos se muestran en solo lectura. También quedan en solo lectura los documentos con indicadores de firma o sin permiso de anotación, marcas con flags ReadOnly, Locked o LockedContents, anotaciones vinculadas a capas, grupos y hilos de respuestas. Se protegen tanto el padre como las respuestas, incluso con referencias entre páginas. Las marcas ocultas se pueden leer en la lista sin crear un objetivo sobre la página; cambiar propiedades no elimina su flag de ocultación.

La eliminación de una nota compatible también retira su popup. No se permite modificar popups ni widgets como si fueran marcas de revisión. Las censuras pendientes son de solo lectura: no se aplican, borran ni reinterpretan con esta herramienta.

Desde 0.18 las notas Text y rectángulos Square compatibles se mueven con los controles X/Y, conservando tamaño, también con giros y recortes. Desde 0.26 también se mueven elipses Circle estándar y se redimensionan rectángulos/elipses compatibles, con ancho/alto de al menos 10 pt y conservación de sus propiedades. Las demás geometrías y la rotación importada siguen pendientes. Los tiradores existentes siguen disponibles para marcas nuevas de sesión. Los tipos y apariencias personalizadas no verificados no reciben garantía de fidelidad universal.

## Conservación e historial

Las operaciones apuntan a la referencia de la anotación en la página de la versión fuente, que se mantiene inmutable. Se validan pertenencia a la página, tipo, permisos y restricciones antes de modificar. Solo se admite una operación consolidada por anotación en cada exportación: varios cambios sucesivos fusionan propiedades sin perder el historial de acciones.

El motor modifica la anotación existente. Las pruebas comprueban conservación de identificador PDF, autor, asunto, fecha de creación, geometría, vértices, opacidad, bordes, relleno y extremos de flecha, y que otras marcas no cambian. Las propiedades no solicitadas no se vuelven a escribir desde el formulario. El selector de color aproxima gris/CMYK para mostrar RGB; editar únicamente el contenido no cambia el espacio de color original.

La serialización final puede renumerar referencias internas. Al reabrir una exportación, organizar, recortar o unir páginas se enumeran de nuevo las anotaciones de esa versión. Sus operaciones anteriores no se reutilizan sobre referencias de otra versión. El historial permite volver a la versión anterior y recuperar sus operaciones de sesión.

Una página muestra hasta 2000 anotaciones en la lista, indicando si se truncó. Hilos de comentarios, estados, respuestas y exportación de comentarios quedan pendientes. Desde 0.13 se puede guardar un proyecto y recuperar el último estado aplicado mediante checkpoint; véase SESIONES.md. Exportar PDF sigue siendo la opción para otros lectores.

## Verificación

58 pruebas específicas del motor/API: siete tipos en cuatro giros; modificación aislada de color; notas Unicode y popup; autor e identidad; opacidad, borde, relleno y extremos de flecha; eliminación selectiva; bloqueo, permisos, firmas, capas, grupos/respuestas, marcas ocultas, truncamiento y rechazo de referencias o propiedades inválidas. Incluye mezcla con edición de texto, marcas nuevas y organización seguida de una nueva edición de anotaciones.

Chromium: documento anotado con giro 90°, edición de contenido y color en pasos sucesivos, deshacer/rehacer, selección real del resaltado, eliminación reversible, marca bloqueada, inspección del PDF descargado y reapertura para continuar editando. Las pruebas son sintéticas en Linux; falta un corpus amplio de documentos reales y validación en Windows y lectores independientes.

Guía de la ampliación 0.26 y verificaciones: [AVANCE_AMPLIO_026.md](AVANCE_AMPLIO_026.md).

Desde 0.32 también se trasladan trazos Ink y líneas/flechas Line compatibles, conservando vértices y apariencias en movimientos puros. Tamaño y casos especiales siguen protegidos; las restricciones y la evidencia se detallan en [INTERFAZ_PROFESIONAL.md](INTERFAZ_PROFESIONAL.md).

En 0.33 se añaden tiradores y cambio de tamaño sobre los vértices de Ink/Line compatibles, con guía, cancelación, teclado y comprobación previa de apariencia. Alcance y limitaciones: [TIRADORES_IMPORTADOS.md](TIRADORES_IMPORTADOS.md).

En 0.34 se editan extremos de líneas/flechas y se seleccionan varias marcas existentes compatibles de una página, con alineación/distribución, movimiento/color y borrado conjuntos. La fidelidad al recolorear trazos también se comprueba. Guía: [AVANCE_AMPLIO_034.md](AVANCE_AMPLIO_034.md).
