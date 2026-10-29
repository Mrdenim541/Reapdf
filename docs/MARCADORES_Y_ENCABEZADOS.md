# Marcadores, encabezados y numeración — versión 0.15

## Editar el índice

En **Páginas → Editar marcadores**, selecciona un marcador y cambia título, página de destino, negrita, cursiva o color. **Añadir submarcador** crea un hijo; **Añadir marcador** crea una entrada principal después de la rama principal seleccionada. Subir/bajar mueve la rama completa entre sus hermanos. Aumentar nivel la coloca bajo el hermano anterior; disminuir nivel la coloca después de los demás hijos de su padre. Eliminar rama incluye sus descendientes.

**Aplicar marcadores** actualiza el índice lateral y el PDF exportado. Deshacer/Rehacer revierte el índice completo. **Restablecer índice** recupera el estado con que se abrió el diálogo; Cancelar descarta sus cambios. Eliminar todas las entradas y aplicar retira el índice. Los títulos admiten Unicode, hasta 300 caracteres sin controles, 2000 entradas y 10 niveles.

Renombrar conserva el punto de destino, zoom, estilo y estado de apertura de las ramas compatibles. Cambiar la página lleva su destino al inicio de la nueva hoja. La navegación lateral actual lleva a la página, sin reproducir el zoom o punto preciso del destino; estos sí se conservan en la salida PDF. Los puntos se verificaron con páginas giradas y recortadas.

Se editan índices con destinos internos XYZ de coordenadas y zoom numéricos. Índices con enlaces externos, destinos por nombre, ajuste Fit, coordenadas nulas, acciones encadenadas u otras estructuras no compatibles se conservan para lectura y su editor queda bloqueado. No se convierten silenciosamente a otro tipo de destino.

## Encabezados y pies

En **Páginas → Encabezados y pies** hay seis posiciones: izquierda, centro y derecha, arriba y abajo. Cada posición dispone de un tercio del ancho entre los márgenes laterales. Comparte fuente, tamaño y color con las demás. Admite una línea de hasta 200 caracteres latinos, 12 variantes base de Helvetica/Times/Courier y tamaños de 6 a 36 puntos. Los márgenes se expresan en puntos PDF: 72 puntos equivalen a una pulgada.

Elige páginas con rangos como `1-3, 5`. Se respeta el orden escrito, sin repetir páginas. Pulsa **Actualizar vista previa**: el motor valida toda la configuración y muestra la página de muestra elegida. **Ampliar vista previa** abre esa imagen en otra ventana para revisarla con más detalle. Si cambias cualquier parámetro o la página de muestra, debes actualizarla antes de aplicar. Texto demasiado ancho, márgenes sin espacio o numeración inválida producen un error, sin aplicar parcialmente el trabajo.

**Aplicar encabezados y pies** añade texto PDF vectorial, seleccionable y buscable. Funciona sobre los cuatro giros y páginas recortadas. Reabrir el diálogo permite corregir la configuración de sesión; la sustituye sin acumular otra copia. **Quitar configuración de sesión** la retira; Deshacer la recupera. No identifica ni elimina encabezados ya incorporados al archivo original.

El contenido se superpone en los márgenes: no desplaza el texto existente ni detecta todos los cruces con imágenes, fondos o texto. Revisa el resultado; cambia los márgenes si hay contenido en esa zona. No reduce el cuerpo de la página para hacer espacio. Las cajas necesitan ancho y altura suficientes, aun en hojas pequeñas.

## Numerar páginas

**Páginas → Numerar páginas** abre el mismo editor con una plantilla de pie central. Variables:

| Variable | Resultado |
|---|---|
| `{pagina}` | Posición real de la hoja en el PDF, empezando por 1 |
| `{total}` | Total de hojas del PDF, no del rango seleccionado |
| `{numero}` | Secuencia desde el inicio indicado, según el orden escrito del rango |

Ejemplo: PDF de 10 hojas, rango `3, 1`, inicio 7 y dígitos mínimos 3. `{numero} / {pagina} / {total}` escribe `007 / 3 / 10` en la tercera hoja y `008 / 1 / 10` en la primera. El formato romano mayúsculo/minúsculo modifica solo `{numero}` y admite 1–3999. El decimal admite hasta 999999 y relleno de 0–8 dígitos; no trunca números más largos.

Esto no cambia las etiquetas internas de página ni implementa Bates o numeración entre archivos.

## Sesión y operaciones de páginas

Marcadores y configuración de encabezados se guardan en proyectos `.reapdf` y en el checkpoint aplicado, y se incluyen al exportar o preparar impresión. Los diálogos abiertos no se guardan como borradores; cierra o aplica antes de usar Ctrl+S/Ctrl+P.

Ordena e inserta las páginas antes de numerar. Al organizar, duplicar, insertar o recortar después, las operaciones previas quedan incorporadas al PDF de esa versión: la numeración queda fija y deja de recalcularse. Los destinos compatibles se ajustan según las reglas de la operación de páginas. Deshacer esa operación restaura la configuración anterior y sus controles.

PDF firmados o sin permiso de modificación no admiten estos cambios. Las pruebas actuales incluyen documentos sintéticos, exportación, proyectos, recuperación y Chromium en Linux. La ejecución Windows y la revisión en lectores independientes siguen pendientes.
