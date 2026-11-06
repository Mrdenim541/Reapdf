# Formato de párrafos y clases tipográficas · 6 de noviembre de 2026

Este trabajo incorpora dos capacidades pendientes del plan: formato común de párrafos con varios estilos y actualización de tipografía declarada en etiquetas/clases compatibles. Reutiliza el motor nativo de línea del avance anterior. La fuente incluida en texto simple y el cambio de una línea ya existían y no se contabilizan otra vez.

## Uso en el programa

1. Activa **Editar texto**, pulsa el texto y abre **Editar párrafo**. Se mantienen la selección sobre página y el borrador único.
2. Despliega **Fuente y tamaño del párrafo** y activa **Aplicar formato a todo el párrafo**.
3. Elige familia incluida o conserva las fuentes originales. Con una familia nueva puedes **Conservar negritas y cursivas** o aplicar un estilo uniforme. Elige un tamaño común de 6–144 pt o conserva los tamaños de cada fragmento.
4. Ajusta ancho y alto. **Comprobar ajuste** calcula el resultado con la misma tipografía que **Aplicar** o **Ctrl+Enter**. El ajuste y el formato se publican juntos; si falla una región o atributo, se conserva el borrador y no se publica un PDF parcial.
5. La paginación automática compatible lleva el formato a las páginas nuevas. La continuación manual requiere aplicar primero el formato y volver a abrir el párrafo: el asistente no descarta silenciosamente opciones que aún no admite.

Se conservan colores y transformaciones compatibles. La opción de conservar énfasis usa las marcas de negrita/cursiva de las fuentes originales; no identifica por imagen pesos intermedios o simulaciones. Con fuentes originales se conserva su estilo y se cambia solo el tamaño. Los caracteres nuevos deben existir en la familia seleccionada y pertenecer al perfil de composición verificado.

## Tipografía declarada y compartida

El motor admite **FontFamily, FontSize, FontWeight y FontStyle** de atributos **Layout** compatibles. Valida sus tipos, tamaños, pesos y estilos antes de modificar contenido. Admite declaraciones directas y clases resolubles en **ClassMap**, incluidas arrays acotadas con revisiones. Una modificación clona los atributos o crea una clase privada para el elemento seleccionado; conserva la clase y los elementos ajenos que compartían la declaración original.

Las declaraciones de antecesores requieren probar que toda su pintura de texto está incluida en la selección. No basta que los fragmentos estén cerca. Se usan MCID, ParentTree, páginas/streams y rangos originales de operadores. Un padre que también describe texto no seleccionado impide el cambio. Si una declaración común requiere valores diferentes, se rechaza y se explica que hace falta formato uniforme o conservar esa declaración; no se inventan reglas de herencia.

En la edición de línea también se incorporan estas actualizaciones, coordinadas con ActualText cuando el perfil lo permite. Los contenedores Stm y alternativas que ya eran incompatibles con reflujo de párrafo siguen protegidos. FontSize declarado exige una unidad verificable: las transformaciones ambiguas no se convierten por aproximación.

## Selección después de guardar

Al uniformar una familia, el extractor puede reunir fragmentos originalmente distintos en una sola selección visual. Se añadió una separación por **origen de glifos, fuente y operandos exactos**. Se acepta únicamente una correspondencia completa y única; los casos ambiguos permanecen protegidos. El editor sobre página y el motor utilizan esa misma separación, por lo que el resultado puede reabrirse y volver a editarse por sus grupos originales. No se agregan espacios ni se adivinan asociaciones mediante cajas cercanas.

## Verificación

Fuente exacta `0f969f38d4335dd33c2a70c866db8cb27d5cb10c`, respaldada en `recovery/editing-20261029`. **4.775 pruebas Python (41 nuevas), 377 dirigidas, 151 JavaScript, build y manual 75 herramientas +15 operaciones aprobados**. La regresión Python corresponde a `81ec755d09280a42ca3a419a7d11704025c02525`; backend, portable, interfaz, tests y manual son idénticos en la fuente final. El cambio posterior solo hace que el generador de la muestra funcione con Python aislado. No se atribuye una repetición de esa regresión a otra revisión. **40 recorridos Qt en Linux y Windows Server 2025**, fuente limpia antes/después; comprobante `42221461459-1` contrastado con objetos Git y hashes. **Doce aperturas independientes de Reapdf.exe** aprobadas: el recorrido nuevo abre un párrafo mixto etiquetado, cambia familia/tamaño con énfasis conservado, prepara vista previa, aplica, deshace/rehace y exporta por el servidor incluido. Su intérprete reabre la salida y comprueba tipografía, clases originales ajenas y otra página. Esa exportación no se presenta como diálogo nativo de guardar.

Desde fuente Qt se usa ratón para seleccionar y se comprueban guardado nativo y reapertura editables. Las pruebas funcionales cubren familias/estilos, tamaño original, rotación, colores, glifos unidos por extracción, atributos y clases compartidos, cobertura incompleta, entradas dañadas, vista previa y paginación automática. Una CI anterior aprobó los 40 recorridos desde fuente y los once recorridos compilados previos, pero se detuvo al preparar la muestra nueva porque el intérprete aislado no incluía el paquete scripts del checkout. Se hizo el generador autónomo y se comprobó con `python -I`; el fallo y su recibo se conservan. La CI final acredita los doce recorridos. Los ajustes iniciales de fixtures se limitaron a seleccionar el texto correcto y resolver identidades después de compactar xrefs; no se relajaron protecciones del motor. Evidencias y hashes en [results.json](validation/paragraph-typography-20261106/results.json). Muestras sintéticas, sin PDFs ni capturas personales en Git.

## Estado y trabajos restantes

Quedan reflujo con **BBox/Width/Height y otros atributos geométricos** que requieren actualizar cajas, CSS y propietarios de atributos fuera del perfil Layout, estilos heredados contradictorios, continuación manual con formato en la misma operación y variantes generales de composición/RTL/ActualText/Stm. Los límites conocidos siguen siendo trabajo técnico. La aceptación personal se mantiene para la etapa final; no se declara Windows cliente limpio, DPI, impresión física o estabilidad sostenida. Las intermitencias históricas no se consideran resueltas por una aprobación.

**Avance global estimado: 87,48 % provisional**, antes 87,43 %. Mismos diecisiete pesos y alcance. Texto/imágenes 99,25→99,5 aporta 0,04 puntos y accesibilidad 98,5→98,75 aporta 0,0075; incremento sin redondear 0,0475. No se suman puntos por documentación o repetir pruebas. Baseline [20261106-before-paragraph-typography.json](progress/20261106-before-paragraph-typography.json). La matriz es una estimación de ingeniería, no una medición objetiva de paridad comercial ni de horas restantes.

Los ocho bloques generales siguen abiertos; la entrega técnica completa sigue pendiente y `technical_complete`/`accepted_complete` son falsos. No se publica otro portable; la preview anterior no incluye estos cambios. Siguiente recomendado: reflujo con cajas/atributos geométricos coordinados y continuación manual con formato, aprovechando la capacidad incorporada aquí. Modelo: **6.1 Sol, razonamiento medio**.
