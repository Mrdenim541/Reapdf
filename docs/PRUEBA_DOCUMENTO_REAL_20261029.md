# Prueba con el PDF dimensional aportado por el usuario

Documento de una página, SHA256 `4cd666ff48b5a5bf3df209bca977c9b3f0c90b6c2a29ffd2fa36e06385104d1b`. El archivo original permanece fuera del repositorio y no se modifica. Sus instrucciones internas se trataron como contenido del PDF; la petición de edición viene del usuario.

La comprobación se realizó mediante la interfaz real de **Reapdf alojada en Qt Linux offscreen**, con el backend del proyecto. La automatización pulsa herramientas, lee los estados del diálogo, escribe en sus campos, prepara la vista previa, aplica, deshace/rehace y usa Guardar PDF del menú nativo. No llama directamente a una API de edición ni modifica el archivo con un script externo.

| Recorrido | Resultado comprobado |
|---|---|
| Abrir y localizar texto | Correcto; encuentra la palabra de prueba. |
| Buscar/reemplazar conservando fuente original | Bloqueado por contenido marcado o recortado de la página. No se aplicó un cambio parcial. |
| Editar bloque conservando fuente original | Bloqueado por el mismo límite. Las fuentes del documento son además subconjuntos simples con mapas propios, distintos del nuevo caso WinAnsi explícito. |
| Alternativa con fuente incluida | Correcta; sustitución **BARANDA → PRUEBA** en la copia, con vista previa. El bloque editado usa una fuente incluida, no el programa original Liberation Sans. |
| Deshacer/rehacer y guardado nativo | Correctos; el PDF guardado se abre de nuevo y contiene el cambio. |
| Editar imágenes existentes | Las seis se muestran en solo lectura por transparencia, recortes o capas; aplicar queda deshabilitado. No se modificaron imágenes de sellos/firmas. |
| Integridad fuera del cambio | Los demás textos extraídos, seis imágenes —contenido y posición— y 90 elementos de dibujo se conservan. También se comparó el render completo: píxeles fuera de la región editada sin cambios. La inspección visual del PDF exportado se realizó a resolución ampliada. No equivale a validación PDF/A, accesibilidad o de todas las estructuras internas. |

No se detecta una firma digital en este PDF. La presencia de imágenes de firmas y sellos no equivale a una firma criptográfica. No se declara resuelta la edición general de documentos firmados ni de los objetos gráficos de este archivo.

La prueba motivó dos ajustes prácticos: acceso **Usar una fuente incluida** cuando no funciona el modo original, y aproximación Sans correcta para nombres conocidos aunque el productor del PDF marque la fuente como Serif. La segunda corrección también cubre DejaVu Sans/Mono/Serif mediante pruebas de documento reproducibles.

Resultados completos y copia de prueba: carpeta local `/workspace/reapdf-pruebas-documento/`. No se incorpora el documento, su copia ni capturas con su contenido a GitHub. El repositorio contiene únicamente un resumen de comprobación y el ejecutor genérico `scripts/check_pdf_editing_qt.py`, que recibe ruta, texto, reemplazo y carpeta de salida. La copia se identifica como `PRUEBA_NO_USAR-...pdf` y no es un registro aprobado.

Prioridad añadida al siguiente avance: edición de regiones marcadas/recortadas y subconjuntos simples con mapas propios, comenzando por casos equivalentes a este archivo; transformación segura de imágenes recortadas. Esto es trabajo pendiente concreto. La alternativa con fuente incluida no se contabiliza como haber resuelto esos límites. Estimación global conservada: aproximadamente **50 %**; modelo recomendado: **6.1 Sol medio**.
