# Párrafos y formato — 0.24

En **Editar → Reemplazar bloque de texto** se puede redistribuir un párrafo digital con fuentes incluidas o corregir fragmentos conservando las fuentes originales compatibles. La selección manual sigue disponible.

1. Pulsa **Detectar bloques de texto**. Elige uno en la lista o pulsa su contorno en la página. También puedes enfocar los contornos con Tab y seleccionarlos con Enter o Espacio.
2. Ajusta el área si necesitas más espacio y pulsa **Leer bloque seleccionado**. El área debe contener fragmentos completos.
3. En el modo de redistribución, edita el texto y elige familia, estilo, tamaño, alineación, color e interlineado. **Unir líneas del párrafo** elimina saltos simples y conserva las líneas vacías; revisa las palabras partidas con guiones antes de aplicar.
4. Opcionalmente activa **Reducir tamaño si no cabe** y fija el mínimo. El ajuste reduce desde el tamaño solicitado en pasos de 0,25 pt y prueba también el mínimo exacto. Nunca agranda la fuente ni baja del mínimo. Si no cabe, la operación falla sin aplicar cambios.
5. Genera la **Vista previa del bloque**. El informe muestra tamaño solicitado, tamaño utilizado e interlineado. Revisa la página y aplica. Cambiar cualquier ajuste obliga a repetir la vista previa.

Las fuentes son DejaVu Sans, Serif y Sans Mono, cada una en regular, negrita, cursiva y negrita cursiva. Se incluyen los doce archivos con licencia y hashes en `resources/fonts/manifest.json`; funcionan sin descargar fuentes. El color se elige con el selector nativo. La vista previa queda junto a los controles en pantallas amplias y debajo en pantallas pequeñas.

La selección de otra región vuelve a mostrar la página original de esta edición. Aplicar crea una versión compatible con deshacer/rehacer, exportación PDF, proyecto y recuperación local. Los recursos compartidos se separan antes de eliminar el texto original para evitar afectar las fuentes de otras páginas.

## Límites

- Hasta 4000 caracteres por edición, tamaño 6–72 pt e interlineado 1–2,5. El ajuste puede necesitar varias pruebas internas; no implica reflujo entre páginas.
- Desde 0.25 también se admiten páginas con giro de 90°/180°/270° mediante una vista de edición enderezada, conservando su giro final. Se requieren regiones con texto digital completo, sin imágenes, campos ni anotaciones superpuestos. Hasta 100 bloques detectados por página; se omiten regiones incompatibles. La detección propone áreas: hay que revisarlas, especialmente en tablas y columnas.
- Redistribuir sustituye las fuentes y el formato interno del bloque por el formato elegido. Conservar fuente sigue siendo un modo independiente, con sus restricciones anteriores.
- No hay composición tipográfica avanzada de árabe/índico, separación silábica automática, texto vertical ni ajuste del resto del documento. La disponibilidad de un glifo no acredita la composición correcta de una escritura compleja.
- No se trata de la herramienta de censura ni acredita eliminación forense de datos.
- No se produce un nuevo archivo portable ni se declara validada la ejecución Windows.

## Verificación

Pruebas de los doce estilos con Unicode, color, posiciones, ajuste mínimo y errores, preservación de recursos compartidos y píxeles de otra página, API sin modificar el original durante la vista previa y comprobación independiente con Poppler. El recorrido Chromium cubre detección, teclado, unión de líneas, formato, desbordamiento, ajuste, invalidación de vista previa, exportación y deshacer/rehacer.

Validación del cierre 0.24: **1094 pruebas Python y 78 JavaScript aprobadas (1172 en total)**, compilación de producción y recorrido completo de Chromium aprobados. Comprobación adicional aprobada del editor a 390 px de ancho, proyecto guardado y recuperación de sesión; verificación de texto/píxeles con Poppler. Estas comprobaciones no acreditan ejecución Windows ni equivalencia completa con Acrobat.

Desde 0.25 se propone tamaño, color, familia aproximada y estilo del primer fragmento leído. Si hay formatos mezclados, se avisa antes de unificarlos. La comparación **Ver original / Ver resultado** conserva la validación de la vista previa. Detalles: [EDICION_PAGINAS_GIRADAS.md](EDICION_PAGINAS_GIRADAS.md).
