# Correcciones de OCR, nombres y bloqueos por etiquetas · 4 de noviembre de 2026

Se incorporan las observaciones del usuario al trabajo pendiente. **No es un cierre del programa al 100 %**. Las herramientas que aparecen en el menú conservan límites y no se consideran universalmente funcionales por estar visibles. El ZIP de prueba publicado anteriormente no contiene estos cambios; esta pasada no publica otro portable.

Fuente de implementación: `909959d0baa04448afc3cb74ca3da038156f376f`, respaldada en `recovery/editing-20261029`.

## Cambios que se pueden usar

| Observación | Corrección | Lo que no queda resuelto |
| --- | --- | --- |
| El OCR podría desplazar cuadros o imágenes | Continúa añadiendo solo texto invisible. Ahora compara el aspecto y los límites de cada página procesada después de guardar el resultado, a la resolución elegida. Si hay una diferencia, aborta sin publicar otra versión. La orientación de reconocimiento no cambia la orientación de la imagen. | Puede reconocer caracteres mal o desalinear la capa invisible. La comparación no certifica otros lectores/resoluciones. No convierte letras de una imagen en texto visible nativo editable. |
| Nombres como 1.46 PINTURA 001 | Dividir PDF admite prefijo, espacio/guion/guion bajo/sin separador, inicio y de 1 a 8 cifras mínimas. La serie se muestra y actualiza automáticamente; los nombres personalizados se conservan hasta regenerarlos. Un nombre inválido permanece editable. | Se mantienen límites de nombres, permisos, tamaño y lotes. |
| Dividir se bloquea por las etiquetas | Se conservan por defecto. El usuario puede desmarcar Conservar etiquetas en las partes y obtener copias nativas sin árbol de accesibilidad ni declaraciones PDF/UA/PDF/A. No modifica el documento abierto ni rasteriza las partes. | No repara la estructura general ni salta protecciones de firmas, capas, XFA o scripts. Retirar etiquetas requiere permisos de copia/modificación. |
| Buscar y reemplazar ofrece compatibles que luego fallan por estructura | La búsqueda comprueba esa restricción antes de permitir elegir los resultados. Indica encontrados y compatibles por separado. Cuando el bloqueo es estructural, ofrece Crear copia sin etiquetas para editar; conserva el texto de búsqueda/reemplazo y vuelve a buscar automáticamente en la copia. | Ajuste, caracteres disponibles, fuentes/objetos ambiguos y ActualText incrustado en el contenido pueden impedir reemplazos. No es sustitución universal de fuentes. |
| Editar imágenes queda en solo lectura por etiquetas | La misma copia explícita permite continuar con imágenes compatibles. Retira solo las asociaciones estructurales; verifica que todos los streams binarios originales y la geometría de páginas se conserven. La copia tiene identidad nueva de guardado y puede deshacerse. | No edita las etiquetas coordinadamente. Siguen protegidas imágenes con OCR, capas/propiedades no verificadas, inline y recortes incompatibles; no todos esos bloqueos se resuelven con la copia. |
| Una edición podía alterar etiquetas de otra página | Se corrigió la edición de páginas sin marcas dentro de documentos parcialmente etiquetados: usa la ruta nativa y compactación que conserva identidades de nodos. Se comprueba el grafo completo después de guardar. | No amplía la semántica soportada de ActualText, referencias a streams o estructuras fuera del presupuesto; esos casos requieren la alternativa explícita o permanecen protegidos. |
| Cuadros de búsqueda difíciles de recorrer | El título y pie del diálogo permanecen visibles; se elimina la lista con otro scroll dentro del panel. La vista previa se invalida al cambiar de documento. | No acredita todos los tamaños de pantalla, DPI ni aceptación general de interfaz. |

La copia sin etiquetas es voluntaria, **no se aplica automáticamente**. Conserva texto, imágenes y formularios compatibles, sin aplanarlos. No ejecuta scripts ni elimina restricciones o firmas. No es una herramienta de censura/saneamiento: pueden permanecer objetos antiguos no referenciados. El original y el historial se conservan; Guardar en una copia utiliza una identidad nueva para no escribir automáticamente sobre el archivo original.

El [manual actualizado](MANUAL_DE_FUNCIONES.md) explica los pasos de las cuatro herramientas. Las alternativas con pérdida de estructura se identifican expresamente; no se presentan como edición semántica nativa.

## Comprobaciones

- **4419 pruebas Python aprobadas**, 22 nuevas netas, con 3 advertencias registradas. Las nuevas pruebas verifican copias, conservación de formularios/recursos, prevalidación, bloqueo de pérdidas de apariencia y liberación del motor OCR tras errores.
- **151 pruebas JavaScript**, build y manual 75+15 aprobados.
- **29 recorridos Qt Linux y 29 Windows Server 2025**, con fuente limpia antes/después. El recorrido nuevo completa búsqueda/reemplazo, imágenes, división y OCR usando el programa, diálogos nativos y archivos reabiertos. Comprueba el diálogo en una ventana Qt de 1280 × 760 y que Guardar en las copias no sobrescriba el original.
- **Tres aperturas independientes de Reapdf.exe** y tarea programada empaquetada aprobadas; comprobante `41891361800-1`, objetos Git y hashes contrastados. No acredita Windows cliente limpio, DPI ni impresión física.

[Resultados](validation/observations-20261104/results.json), [regresión](validation/observations-20261104/full.log), [Linux](validation/observations-20261104/linux/desktop-report.json), [Windows](validation/observations-20261104/windows/assessment.json).

Se probó además un PDF previamente proporcionado por el usuario en la ventana Qt real: copia explícita, redimensionado de una imagen existente, vista previa, aplicación, Guardar normal con identidad nueva y reapertura. Se conservaron el texto y sus posiciones, las demás imágenes y ambos archivos originales. El archivo, sus textos, capturas, resultados y logs privados no se añaden a Git. Se archiva únicamente un resumen booleano sin identificación del documento. **No se ha probado el PDF exacto de 42 páginas de las capturas**, que no está adjunto a estas observaciones.

## Estado y continuidad

Estimación global registrada **86,87 % provisional, sin incremento por esta corrección**. No se cuenta como ampliación comercial el mero retiro de una restricción mediante una copia con pérdidas semánticas. Los ocho bloques del [plan](PLAN_ACTUAL.md) siguen abiertos; la edición nativa de etiquetas/ActualText y fuentes generales continúa pendiente junto con los demás desarrollos. No se trasladan esas implementaciones al usuario como pruebas personales.

La descarga publicada de prueba `preview-windows-20261104-ddd9bdd` conserva su fuente y checksum anteriores y **todavía no contiene estas correcciones**. La compilación de comprobación de esta fuente permanece interna; no se publica otra entrega sin petición.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
