# Rellenar formularios — versión 0.16

> Este documento describe el alcance inicial. Para grupos/jerarquías, importación y diseño actuales, ver [FORMULARIOS_AVANZADOS.md](FORMULARIOS_AVANZADOS.md), [IMPORTAR_FORMULARIOS.md](IMPORTAR_FORMULARIOS.md) y [AVANCE_AMPLIO_026.md](AVANCE_AMPLIO_026.md). En 0.26 ya se crean campos con propiedades y valores iniciales.

**Actualización 0.19:** hay radios exclusivos, campos compartidos y jerarquías compatibles. Alcance nuevo y límites en [FORMULARIOS_AVANZADOS.md](FORMULARIOS_AVANZADOS.md). El texto siguiente documenta el editor inicial.

En **Rellenar formulario**, elige un campo por nombre y página. Completa texto, activa/desactiva una casilla o selecciona un valor de lista. **Vista previa del formulario** valida todos los cambios del diálogo y muestra la página del campo seleccionado. **Ampliar formulario** permite revisar esa muestra con más detalle. Si cambias un valor o cambias a un campo de otra página, actualiza la vista previa antes de aplicar.

**Aplicar formulario** conserva los campos como AcroForm editables en el PDF exportado, sin sustituirlos por imágenes. Deshacer/Rehacer revierte/restaura los valores. Puedes corregirlos al volver a abrir el diálogo, guardar/abrir proyecto `.reapdf` y recuperar el checkpoint aplicado. Cancelar descarta los cambios del diálogo. Los borradores no se guardan; Ctrl+S/Ctrl+P esperan a que cierres o apliques el diálogo.

Para probar sin archivos personales, abre `ejemplos/reapdf-formulario.pdf` del portable. Incluye texto, casilla, lista desplegable, texto de varias líneas y un campo de solo lectura. También se genera con `python scripts/create_form_sample.py ruta.pdf`.

## Alcance admitido

- Campos simples de texto con fuentes base compatibles, una o varias líneas. Hasta 2000 caracteres latinos por campo o el límite menor definido en él. El editor no permite saltos de línea en campos de una sola línea.
- Campos con tamaño automático: se calcula un tamaño legible entre 6 y 12 pt. Se conserva el tamaño fijo compatible del campo. Se rechaza texto que no cabe; no se descarta silenciosamente el resto del valor.
- Casillas independientes con estado de activación conocido. Se puede marcar y desmarcar.
- Listas desplegables y listas de selección única con opciones explícitas y rótulos latinos. Se conserva el código de exportación y se genera la apariencia del rótulo; por ejemplo, valor `BOG` y texto visible `Bogotá`. **Sin selección** vacía el valor.
- Hasta 500 campos por documento. Campos en hojas giradas o recortadas, siempre que queden dentro de la página visible.
- Permiso de rellenar formularios: no requiere permiso de edición del cuerpo. Los PDF con contraseña de apertura y los firmados siguen fuera del alcance actual.

El selector identifica los campos bloqueados y explica el motivo: solo lectura, radio/botones/firmas, campos compartidos o jerárquicos, fuentes no admitidas, selección múltiple, contraseña, texto enriquecido, listas no compatibles, scripts, XFA o cálculos. No se ejecuta JavaScript ni se sustituyen cálculos por valores inventados. Los índices de cálculo/XFA o JavaScript a nivel de documento bloquean el relleno del formulario completo.

No se crean campos, no se implementan cálculos, radios agrupados, validación de reglas de negocio ni indicación completa de campos obligatorios. Que un campo quede visualmente relleno no demuestra que un formulario esté completo para su trámite. Un texto impreso o una tabla escaneada no es un formulario AcroForm; puede anotarse con Añadir texto, pero seguirá siendo una superposición.

## Exportación y operaciones de páginas

Exportar PDF y preparar impresión incluyen los valores y apariencias. Exportar imágenes los incluye como píxeles y pierde la editabilidad de los campos en esas imágenes. Al organizar páginas, los valores se incorporan al nuevo PDF base y el árbol AcroForm se conserva para las estructuras admitidas. El editor vuelve a leer los identificadores de esa nueva versión. Deshacer la organización restaura la configuración de sesión previa.

Las pruebas comprueban cuatro giros y recorte, valores/apariencias, selección mediante código/rótulo, vaciado de campos y casillas, permisos, campos bloqueados, proyectos, organización, impresión y recuperación en Chromium. Falta validar formularios reales de distintos productores y lectores externos; las estructuras no compatibles quedan expresamente fuera del editor.

Desde 0.27 se pueden modificar propiedades y geometría de campos existentes compatibles, conservando valores y grupos, con vista previa obligatoria. Alcance y restricciones: [AVANCE_AMPLIO_027.md](AVANCE_AMPLIO_027.md).

Desde 0.28 se pueden renombrar campos terminales conservando contenedores/grupos y editar/reordenar opciones de listas de selección única, con valores exportables y etiquetas independientes. Se conservan valores actual y de restablecimiento. Guía: [AVANCE_AMPLIO_028.md](AVANCE_AMPLIO_028.md).

Desde 0.29 hay firma con certificado P12/PFX y verificación criptográfica como herramientas separadas de la firma visual. Los documentos firmados permiten lectura/verificación y una firma sucesiva compatible en copia; las ediciones ordinarias permanecen protegidas. Guía: [FIRMAS_DIGITALES.md](FIRMAS_DIGITALES.md).
