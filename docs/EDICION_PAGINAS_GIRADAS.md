# Edición en páginas giradas — 0.25

**Editar → Reemplazar bloque de texto** admite páginas cuyo giro PDF es 0°, 90°, 180° o 270°. Dentro del diálogo se muestra una vista enderezada para facilitar la lectura, selección y escritura. El aviso indica el giro que conservará la salida. Aplicar mantiene el giro, MediaBox y CropBox del documento; no convierte el contenido a imagen.

Ambos modos están incluidos:

- **Redistribuir párrafo y cambiar formato:** fuentes incluidas, tamaño, color, estilos, interlineado y ajuste de tamaño con mínimo.
- **Conservar fuente y estilo por fragmentos:** mantiene fuente, tamaño, color, línea base y posición nativa, con los controles de caracteres y anchura anteriores. Los subconjuntos TrueType siguen limitados a sus glifos comprobados.

La detección de bloques, selección sobre la página, campos numéricos y vista previa usan la misma vista enderezada. Las coordenadas se expresan en puntos desde la esquina superior izquierda del CropBox sin giro, también cuando el recorte tiene un desplazamiento respecto al MediaBox. La página principal vuelve a mostrar la orientación original después de aplicar.

## Formato inicial y comparación

Leer un párrafo propone tamaño, color y estilo a partir del primer fragmento con texto, y aproxima la familia original con Sans, Serif o Mono de las fuentes incluidas. **Esto no conserva la fuente exacta**: para ese propósito se utiliza el modo de fragmentos. Si el bloque mezcla formatos, un aviso explica que redistribuir aplicará un formato único al bloque.

Tras generar una vista previa válida, **Ver original / Ver resultado** permite comparar la página antes de aplicar. Cambiar el texto, región o formato invalida la vista previa como antes. Aplicar continúa creando una versión reversible compatible con PDF, proyecto y recuperación local.

## Alcance y límites

El soporte corresponde al giro de la página definido en el PDF. No habilita fragmentos intrínsecamente inclinados, verticales, contorneados o transparentes, ni escrituras con composición tipográfica avanzada. Continúan las protecciones frente a regiones parciales, imágenes/campos/anotaciones superpuestos y, en el modo de estilos originales, estructuras complejas no verificadas. No hay reflujo entre páginas.

La edición rápida de líneas del panel lateral mantiene su límite anterior; en páginas giradas se indica usar el editor de bloques.

## Contrato de API

`POST paragraph-preview` recibe `page`, `operations` y `scale`; devuelve PNG enderezado y `X-Page-Rotation` con el giro original. Los dos endpoints de reemplazo devuelven su vista previa en las mismas coordenadas cuando `preview: true`; el documento aplicado conserva el giro. Inspección, detección y reemplazo reciben regiones en coordenadas nativas del CropBox. Las vistas previas operan sobre copias y no modifican el documento almacenado.

## Validación

Pruebas de los cuatro giros con/sin recorte, párrafo y fuentes originales base/TrueType parciales; contraste de geometría y píxeles frente a una edición independiente a 0° girada después; preservación de otra página y programas de fuente. Comprobación de API, formatos mezclados, restricciones y lectura/rasterización con Poppler. Chromium recorre los tres giros y ambos modos, comparación, exportación, historial, proyecto y recuperación.

Estimación orientativa: **75 % ±5 puntos** del plan propio; 75,25 puntos en la matriz ponderada. No equivale a paridad completa con Acrobat ni a ejecución Windows validada.

Validación del cierre 0.25: **1133 pruebas Python y 78 JavaScript aprobadas (1211 en total)**, compilación de producción y recorrido completo en Chromium aprobados. Incluye los tres giros y ambos modos, conservación de fuentes y recortes, comparación, historial/proyecto/recuperación y contraste independiente con Poppler. No se genera un nuevo portable ni se declara validada la ejecución Windows.
