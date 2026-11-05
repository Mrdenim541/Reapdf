# Edición accesible, Form etiquetados y acceso rápido · 5 de noviembre de 2026

Este trabajo añade soporte que antes estaba protegido: ActualText de un grupo nativo, Form con asociación semántica en la página y streams Form con referencias MCR/Stm propias. También incorpora el acceso rápido pedido mediante capturas: clic derecho → Editar → cuadro pequeño con el texto cargado. La edición directa con ratón/cursor sobre la página se conserva. No se presenta como repetición del perfil anterior de párrafos etiquetados directos ni como cierre del programa completo.

## Cómo funciona la edición rápida

1. Activa **Editar texto** y haz clic derecho sobre el texto de la página. Con teclado, enfoca el texto y pulsa **Shift+F10**.
2. **Editar** abre un cuadro compacto con el valor actual seleccionado. Escribe y pulsa **Aplicar** o **Ctrl+Enter**. **Cancelar** deja el documento intacto.
3. Si el contenido no cabe o su fuente no admite los caracteres, el cuadro conserva el borrador y explica el fallo; no publica un PDF parcial.
4. **Eliminar** retira el fragmento compatible y su ActualText asociado, cuando existe. **Deshacer** recupera la edición. Eliminar no es la herramienta de censura de seguridad.

El menú también se cierra con Escape o fuera de él. La selección se resalta sobre la página; el cuadro no exige localizar texto en un panel lateral. El borrador participa en las protecciones de navegación, exportación y cierre de la ventana. Se mantienen firmas y permisos del documento; el acceso rápido no los omite.

## Texto visible y lectura accesible

El editor muestra los glifos reales para seleccionar y editar, aunque ActualText sea diferente o esté vacío. La copia/extracción y búsqueda normales siguen usando la representación de lectura del PDF; el modo de edición no elimina alternativas para obtener los glifos.

Cuando ActualText y el texto visible coinciden, se actualizan juntos. Si difieren, el editor permite conservar o cambiar la lectura accesible y envía esa elección explícita. El API no acepta cambiar silenciosamente el texto visible dejando una alternativa distinta sin revisar. El cuadro rápido reúne las opciones de lectura en una sección compacta, abierta cuando los valores difieren. También se puede modificar solo la lectura; una prueba compara los píxeles antes y después y exige que permanezcan idénticos. Una alternativa vacía se conserva por elección explícita y puede ocultar la extracción; la interfaz lo explica.

Se admiten cadenas inline en BDC y ActualText de nodos estructurales cuya asociación cubra exactamente un grupo visible verificable. Alternativas coincidentes sobre ese mismo grupo se coordinan; alternativas contradictorias o repartidas entre varios grupos no se modifican parcialmente. Se validan Unicode, longitud y controles. El plan declara todas las actualizaciones de un lote antes de escribir; una región inválida impide publicar todo el lote.

## Dos tipos distintos de Form

| Estructura original | Comportamiento incorporado |
| --- | --- |
| Form sin marcadores propios, bajo una etiqueta de página | Aísla la aparición seleccionada mediante copia del camino de invocación y conserva las otras apariciones, incluidas las de otras páginas. El árbol y los marcadores de página mantienen su asociación. |
| Párrafo completo dentro de Form de solo texto con etiquetas de página | Permite edición, reflujo, continuación a áreas vacías y paginación compatibles, coordinando las etiquetas como en el perfil anterior. Exige objetos completos y no reúne párrafos por semejanza visual. |
| Form con StructParents propio y referencias MCR/Stm | Permite editar una línea y su ActualText compatible cuando el stream tiene una sola aparición en todo el documento y coinciden MCID, ParentTree, página y propietario. Conserva la identidad del stream y sus referencias; la compactación puede renumerar xrefs sin cambiar esa identidad lógica. |
| Stream Form etiquetado reutilizado en varias apariciones | Permanece protegido: no se modifica en sitio ni se clona dejando referencias Stm apuntando al contenido anterior. |

El editor conserva fuente, tamaño, color, posición, transformación, recortes y apariencia compatibles. Las matrices, el estado gráfico y los demás operandos no se reescriben para simular la edición con una caja blanca o una imagen.

## Comprobación semántica

El modo nuevo compara el grafo estructural y los marcadores de página/Form con el resultado planificado, además de comprobar los glifos, geometría, estilo, opacidad y textos vecinos del PDF guardado. Los Form se identifican por aparición y los streams etiquetados por su índice semántico único, sin adivinar asociaciones por proximidad. El modo estricto anterior continúa protegido por defecto; aceptar alternativas y Stm requiere el recorrido nativo coordinado.

Los índices de contenido se leen como enteros de 64 bits y se contrastan con sus límites, evitando truncar un valor excesivo a otro MCID. El caso malformado se añadió como prueba de rechazo. Las propiedades de lectura nombradas, incluso si Resources se hereda de un antecesor de página, permanecen protegidas también al intentar cambiar de fuente; no se descartan alternativas para forzar la edición. Se mantienen presupuestos de objetos, bytes, profundidad y caracteres; no se pretende reparación general de PDFs dañados.

## Límites que siguen abiertos

- ActualText que agrupa varios fragmentos/figuras, alternativas contradictorias, propiedades de marcado nombradas y redistribución general de alternativas.
- Reflujo de streams Stm con estructura propia, streams etiquetados compartidos y asociaciones múltiples o no verificables.
- Fuentes no compatibles, sustitución general de fuente/tamaño dentro de estos contenedores, composición y direcciones de lectura fuera del perfil verificado.
- PDF/UA general, validación externa con lectores de pantalla, interoperabilidad universal y el resto de los ocho bloques del plan.

No se deben volver a anunciar como completamente ausentes los tres perfiles incorporados de ActualText/Form. Tampoco se deben declarar resueltas las variantes anteriores por haber ampliado los casos compatibles.

## Evidencia

Fuente exacta `7d37c20eb2b77de518e8253f8d3b4aba52ed5183`, respaldada en `recovery/editing-20261029`. **4.662 pruebas Python (54 nuevas), 151 JavaScript, build y manual 75+15 aprobados**. **37 recorridos Qt en Linux y 37 en Windows Server 2025**, fuente limpia antes/después; comprobante Windows `42062314499-1` contrastado con sus objetos Git y hashes. **Diez aperturas independientes de Reapdf.exe** aprobadas, incluidas las tres nuevas de Stm/ActualText, continuación desde Form de página y cuadro rápido/eliminación/deshacer. Evidencias y SHA256 en [results.json](validation/semantic-text-20261105/results.json).

Una ejecución anterior completa pasó 4.660 pruebas antes de añadir dos protecciones; otra se interrumpió para incorporar la última protección y no se cuenta como aprobada. El primer recorrido rápido dirigido falló por un selector de prueba que confundía el área Editar con la acción contextual; se acotó el selector. Dos CI Windows anteriores aprobaron los 37 recorridos desde fuente, pero fallaron al cerrar paginación o esperar la primera ventana compilada; se conservan los comprobantes y logs y no se declara resuelta su causa por la aprobación posterior. El verificador compilado también se ajustó para esperar un texto visible invariable, pues la capa de lectura usa ActualText. No se confunde lectura alternativa con glifos visibles. Las pruebas nuevas emplean documentos sintéticos, con códigos genéricos y sin copiar certificados, PDF privados ni capturas del usuario al repositorio.

El recorrido Qt comprueba ratón/cursor, lectura accesible, edición solo semántica sin diferencias de píxeles, guardado nativo y reapertura/reedición; también el acceso rápido, teclado, cancelación, borrador tras error, eliminación/deshacer y continuación desde un Form compartido. Los recorridos compilados exportan mediante el servidor real incluido en Reapdf.exe y reabren las salidas con su intérprete; esa exportación no se presenta como automatización del diálogo nativo de guardar.

No se publica otro portable ni se solicitan pruebas personales intermedias. La preview anterior no contiene estas mejoras. Las comprobaciones de Windows Server no acreditan Windows cliente limpio, DPI, impresión física ni recuperación bajo pérdida de energía; no se declaran resueltas las intermitencias históricas por repetir pruebas.

La entrega técnica completa y la aceptación personal siguen pendientes. Siguiente trabajo funcional recomendado: permitir sustituir fuente/tamaño de texto original conservando sus asociaciones, especialmente cuando la fuente original carece del carácter necesario. Es una capacidad distinta de la conservación semántica incorporada aquí. Modelo recomendado: **6.1 Sol, razonamiento medio**.

## Estimación global

**87,38 % provisional** (antes 87,29 %), con los mismos diecisiete pesos y alcance. Interfaz 97,25→98 aporta 0,0525 puntos y accesibilidad 97→98 aporta 0,03; suma sin redondear 87,375 %. No se añaden puntos por documentación, entorno ni repetición de pruebas. Baseline: [20261105-before-semantic-text.json](progress/20261105-before-semantic-text.json). Los ocho bloques siguen abiertos; `technical_complete` y `accepted_complete` permanecen falsos. Esta estimación de ingeniería no mide de forma objetiva la paridad con Acrobat ni el tiempo que falta.
