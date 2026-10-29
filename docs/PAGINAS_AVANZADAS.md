# Recortar, reemplazar y dividir — versión 0.8

Estas herramientas usan las ediciones actuales de la sesión. La fuente y versiones previas permanecen intactas. Recortar/restaurar y reemplazar generan una nueva versión con deshacer/rehacer. Dividir descarga un ZIP y conserva el documento abierto, el historial y el indicador de cambios sin exportar.

## Recorte y restauración

Se eligen páginas o rangos y cuatro márgenes en puntos PDF: superior, derecho, inferior e izquierdo. Se miden sobre la orientación visible de cada página, incluidos giros de 90°, 180° y 270°. La primera página seleccionada muestra el límite de recorte; los márgenes se aplican a todas las elegidas. Cada página debe conservar al menos 10 × 10 puntos. Requiere permiso de modificación y no admite indicadores de firma.

El recorte modifica CropBox, conservando MediaBox, objetos, anotaciones y formularios. Un recorte posterior parte del encuadre actual. «Restaurar página completa» vuelve a MediaBox, también en documentos cuyo origen de coordenadas no es cero; puede mostrar contenido que ya estaba oculto al importar el PDF. Deshacer restaura el encuadre anterior exacto.

No se elimina contenido de los márgenes. Esta función **no es censura ni saneamiento**. Al consolidar la versión, las marcas previas pasan a ser anotaciones preexistentes; para recuperar sus herramientas de sesión hay que deshacer la operación. El tamaño del papel de MediaBox no cambia: queda pendiente redimensionar el soporte físico.

## Reemplazo de páginas

Se selecciona otro PDF, las páginas de origen en el orden deseado, la primera página del bloque de destino y cuántas páginas originales retirar. El número de páginas importadas puede ser distinto del retirado. El total final debe estar entre 1 y 500 páginas.

Se sustituyen páginas completas, incluidos sus campos y anotaciones. Se conservan el contenido de las páginas restantes, sus cambios actuales y las páginas importadas con sus marcas, campos simples, enlaces compatibles y etiquetas. Los campos con nombres repetidos permanecen independientes.

Los enlaces y marcadores que apuntaban a páginas retiradas desaparecen; no se redirigen a la nueva página por posición. Los marcadores de origen se agrupan por archivo. Las etiquetas de origen sustituyen a las del bloque retirado. Las validaciones de importación de UNION.md siguen vigentes. El documento base también se valida para evitar retirar campos asociados a cálculos/scripts o acciones que aún no se remapean de forma verificada.

Se admite reemplazar todo el documento y reemplazar páginas dentro de un PDF de 500 páginas: el límite se aplica al resultado final, no a la copia intermedia en memoria. Las estructuras documentales avanzadas, accesibilidad y adjuntos de los archivos de origen no tienen garantía de conservación completa.

## División

Dos modos:

- Bloques de tamaño fijo: una cantidad de páginas por parte; la última puede tener menos.
- Grupos personalizados: una línea por parte, con páginas y rangos como `4,1` o `2-3`. Se respeta el orden escrito y cada página del documento debe aparecer exactamente una vez.

El ZIP contiene nombres seguros y correlativos `parte-001.pdf`, `parte-002.pdf`, etc. Se admite hasta 100 MB de PDF de salida sumados antes de comprimir. No se crean versiones de sesión para estas partes.

Las páginas conservan giros, etiquetas, anotaciones, campos simples y marcadores compatibles. Los enlaces a páginas que quedan en otra parte se retiran para evitar destinos erróneos. Las ediciones de sesión se aplican antes de dividir. Se exige permiso de copia y se rechazan documentos con indicadores de firma. En esta versión se rechazan capas, XFA, cálculos/scripts y acciones de enlace/marcador no verificadas, como en la importación.

## Evidencia y límites

Pruebas del motor/API: cuatro giros, comparación visual del recorte y restauración, encuadres consecutivos, MediaBox desplazado, campos simples, notas, etiquetas, marcadores, enlaces retirados, edición antes de cada operación, reemplazo total y al límite de 500 páginas, grupos no contiguos y orden invertido, ZIP, cuotas, permisos, firmas y estructuras no admitidas. Las solicitudes inválidas no crean una versión nueva ni modifican la entrada.

Chromium recorre recorte/restauración y su historial, reemplazo de dos páginas por un rango de origen, deshacer/rehacer y división en ambos modos. Inspecciona los PDF descargados dentro de los ZIP y confirma que dividir no borra el estado de cambios pendientes.

La validación actual sigue basada en documentos sintéticos y Linux/Chromium. Windows, lectores independientes y un corpus amplio de documentos reales están pendientes. No se considera probada la conservación universal de PDF complejos.
