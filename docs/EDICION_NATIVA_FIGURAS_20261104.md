# Edición nativa de figuras etiquetadas · 4 de noviembre de 2026

Se incorporó un recorrido completo de edición de figuras compatibles conservando su estructura de accesibilidad. Antes el editor rechazaba globalmente las imágenes de cualquier PDF etiquetado; la salida disponible era crear una copia sin etiquetas. Esa alternativa sigue existiendo para asociaciones no compatibles, pero ya no es necesaria para las figuras del perfil descrito aquí. No se declaran cerrados los ocho bloques generales ni la edición avanzada completa.

## Comportamiento incorporado

- **Mover y redimensionar:** se vincula una aparición concreta de imagen con su Figure y MCID mediante el árbol de padres, sin inferir asociaciones por parecido de cajas. Se conservan descripción y orden de lectura y se actualizan BBox/Width/Height locales. Los atributos compartidos se copian antes de modificar la figura elegida.
- **Reemplazar:** conserva el marco, transformación, recorte y geometría semántica existentes. Permite revisar la descripción accesible y exige una descripción válida antes de preparar/aplicar la sustitución. No cambia la descripción de otras figuras que reutilicen el mismo objeto de imagen.
- **Eliminar:** retira la aparición, su elemento Figure y sus delimitadores de contenido marcado, y deja null en su posición del ParentTree. No renumera MCID ajenos ni retira las otras etiquetas. No equivale a censura/saneamiento de datos.
- **Acciones por figura:** un recorte parcial, curvo o una máscara externa puede impedir mover, pero permite reemplazar o eliminar conservando el marco. La interfaz ofrece las acciones compatibles; no presenta el editor entero como inservible. IDTree/ID/Ref pueden impedir eliminar sin impedir otras acciones compatibles.
- **Uso más directo:** la muestra permite seleccionar y arrastrar; la vista previa se actualiza automáticamente, sin exigir pulsar Vista previa antes de cada aplicación. Se cancelan respuestas obsoletas, se mantiene la edición de controles mientras se prepara la muestra y Aplicar solo se habilita para la configuración revisada. El botón manual queda como actualización/reintento. Se liberan imágenes de muestras anteriores para evitar acumular sus píxeles en memoria.

## Comprobación antes de publicar la versión

El grafo semántico previsto se calcula tras el cambio intencional y se contrasta después de guardar y reabrir el resultado. Se comprueban los marcadores semánticos, el texto extraído y las otras apariciones de imágenes, incluyendo geometría/digest/transformación. Un cambio no previsto aborta el resultado. Las pruebas independientes comprueban además posiciones/estilos del texto, ParentTree con pyHanko y apariencia de otras páginas.

El grafo permite conservar ActualText ajenos sin modificarlos; no habilita su edición textual. El perfil de control de imágenes admite hasta 100.000 elementos, 64 niveles y 1.000.000 pasos de comprobación, con límites adicionales de cadenas, arrays, operadores y apariciones. La protección original de la edición de texto permanece activa. Se prueba una figura en un documento sintético de 42 páginas con más de 2.000 etiquetas y alternativas ajenas.

## Límites que permanecen

Se requiere una Figure independiente, un único MCID de página y una única imagen directa; K puede ser entero, array unitario o MCR sin Stm. Se protegen contenido marcado mixto, Forms con asociaciones de stream, alternativas del elemento o sus antecesores, clases/namespaces/archivos asociados y otros atributos fuera del perfil.

Mover requiere un marco completo dentro de recortes rectangulares verificados y sin máscara externa. No desplaza ni recompone recortes/máscaras de página. La sustitución conserva el recorte existente; no ofrece un editor universal de recortes. Las imágenes con OCR, firmas o permisos incompatibles siguen protegidas. No certifica PDF/UA ni interoperabilidad con todos los lectores.

Los ocho bloques de PLAN_ACTUAL.md siguen abiertos. La edición textual general con ActualText/Stm, las fuentes/composición pendientes y las imágenes/Forms fuera de este perfil no se delegan al usuario como verificaciones.

## PDF privado

Se probó el PDF adjunto disponible mediante la ventana Qt: arrastre y ajuste de marco dentro del recorte, muestra automática, aplicación, guardado nativo y reapertura manteniendo etiquetas. Se compararon todo el texto y sus posiciones, las otras cinco imágenes, roles/alternativas del árbol y marcadores. También se compararon los píxeles fuera de la unión de la caja original y la nueva. El original se conserva.

Las seis imágenes admiten acciones nativas; tres permiten movimiento dentro del recorte verificado y tres ofrecen reemplazo/eliminación conservando su marco. Esto no significa que todas admitan traslación libre. El documento de 42 páginas de las capturas no está disponible: la prueba de 42 páginas utiliza datos sintéticos. PDF, capturas y logs privados quedan fuera de Git; solo se archiva un resumen booleano/conteos.

## Incidencias de comprobación

La primera regresión Linux se detuvo en el callback de JavaScript de la apertura inicial, antes de las funciones nuevas. Un segundo recorrido de esa fuente aprobó las 32 comprobaciones. Se conserva el fallo y no se atribuye una corrección definitiva de la intermitencia a esta implementación.

Un intento privado coincidió con la recompilación de Vite y recibió 503 porque dist estaba siendo sustituido; se repitió después de completar el build y aprobó. Es un problema de orden en el procedimiento de prueba, no una prueba aprobada ni una corrección del motor. Sus logs crudos privados no se publican. El prechequeo CDP de fuente Linux también detectó una exportación sin desplazamiento tras la simulación del ratón; no se usa como evidencia aprobada del ejecutable. En Windows, el recorrido del ejecutable requiere comprobar independientemente que la imagen realmente se desplazó.

No se publicó otro portable. La descarga preview anterior no incorpora este trabajo. La ejecución de CI sobre Windows Server no sustituye Windows cliente limpio, DPI, impresión física, carga sostenida ni aceptación personal final.

## Verificaciones de la revisión final

Fuente `cd35dabb458f23a20eae44c4876a22e7e5403d46`, respaldada en recovery/editing-20261029.

- 4.478 pruebas Python aprobadas (+51), 3 advertencias conocidas; 151 pruebas JavaScript, build y manual 75 herramientas + 15 operaciones generales aprobados.
- 32 recorridos Qt Linux y 32 Windows Server 2025, fuente limpia antes/después. Comprobante `41932705666-1`, contrastado con objetos Git y hashes de logs.
- Cuatro aperturas independientes de Reapdf.exe. La cuarta arrastra una figura etiquetada, espera la muestra automática, aplica, deshace/rehace, reemplaza con descripción y elimina; exporta tres PDFs mediante su servidor incluido. El intérprete del paquete comprueba desplazamiento real, tags, Alt, ParentTree, texto, otra imagen y otra página. Identidad de ventana Qt y cierre normal verificados, sin navegador externo. El guardado mediante diálogo nativo de las tres acciones se comprueba en los recorridos de fuente Qt; no se atribuye ese diálogo al recorrido compilado.
- Prueba privada final y caso sintético de 42 páginas descritos arriba.

Estimación total provisional: **87,14 % (≈87 %)**, antes 87,08 %. Mismos diecisiete pesos y alcance; solo accesibilidad pasa de 93 a 95 por la coordinación semántica implementada. No se da crédito nuevo a toda la edición de texto/imágenes ni se declara un bloque general al 100 %. La cifra es un juicio de ingeniería, no paridad medida con Acrobat ni horas restantes. Baseline y justificación en avance-global.json.

[Evidencia consolidada](validation/tagged-images-20261104/results.json) · [Manual](funciones-uso.json) · [Pendientes generales](PLAN_ACTUAL.md).
