# Composición, celdas, estilos XFDF y notas Word · 30 de octubre de 2026

Base: `024a024f7cba4af0b6f6f8f8a5e927ded67baaa0`. Mejoras sobre 0.43 recuperada; 0.55 no está recuperada. No se crea instalador/portable ni se incluyen PDFs personales en Git. Los archivos de prueba se generan sintéticamente fuera del repositorio.

## Cambios utilizables

### 1. Edición original con modos de mezcla

**Editar → Editar texto**, con selección sobre la página y cursor:

- Se admiten los modos de mezcla estándar declarados por nombre: Multiply, Screen, Overlay, Darken, Lighten, ColorDodge, ColorBurn, HardLight, SoftLight, Difference, Exclusion, Hue, Saturation, Color y Luminosity, además de Normal/Compatible.
- Se mantienen operadores gráficos, colores, opacidad, recursos y fuentes originales. El cambio de una aparición Form compartida conserva las demás apariciones/páginas.
- También se admiten grupos RGB/Gray no aislados con indicadores compatibles y sin knockout. No se recrea ni rasteriza su apariencia.
- La interfaz mantiene bloqueados el cambio de fuente y la sustitución del párrafo cuando podrían eliminar la composición. El control del servidor no depende de que el visor consiga identificar una caja de texto nativa.

La restricción es conservadora por ámbito de contenido (página/Form), no un análisis aislado del estado activo de cada glifo. No se admiten máscaras suaves, arrays de modos de mezcla, knockout, espacios de grupo complejos/CMYK ni estados adicionales desconocidos. Se mantienen límites previos de objetos, geometría, fuentes y colisiones.

### 2. Varios fragmentos en una celda semántica

**Documentos → Etiquetas y orden de lectura → Preparar etiquetas iniciales**:

1. Asignar TH/TD, tabla, fila y columna a los objetos revisados.
2. Para varios objetos de la misma celda, marcar **Este fragmento comparte celda con otros objetos** en cada uno.
3. Mantener iguales rol, ámbito y combinaciones; revisar la página y crear etiquetas.

Se crea un único TH/TD con varios MCID y ParentTree coherente. Los objetos se mantienen separados en el contenido PDF; no se unen sus textos ni se alteran píxeles. Deshacer/proyecto/división conservan la estructura compatible. Las coincidencias de coordenadas sin confirmación explícita siguen rechazándose para no convertir un error de edición en una agrupación silenciosa. La sugerencia geométrica anterior sigue limitada a un objeto por celda; este avance amplía la revisión manual.

Pendientes: celdas vacías sin objeto original, contenido mixto/figuras/enlaces dentro de una celda, asociaciones de encabezados complejas, tablas generales y validación integral PDF/UA con lector de pantalla.

### 3. Texto libre XFDF con negrita y cursiva reales

**Documentos → Intercambiar XFDF**, revisión e importación como antes:

- Las doce variantes Helvetica/Times/Courier incluyen regular, negrita, cursiva y combinación de ambas. Las variantes añadidas usan métricas reales de la fuente, con tamaño, alineación y giro; no se declaran como negritas conservando un programa regular.
- Se crea una apariencia PDF nativa con sus recursos y DA coherentes. Se conservan relleno, borde discontinuo compatible, opacidad, recorte de página y giros probados.
- Se corrige el crecimiento acumulativo de la caja causado por la expansión del borde al regenerar FreeText. La caja externa intercambiada permanece estable.
- Se rechazan desbordamiento, caracteres fuera de WinAnsi en las nuevas variantes y diccionarios de fuentes que pretendan ser una fuente base distinta. Las fuentes reales se inspeccionan en recursos directos e indirectos; las apariencias estilizadas deben coincidir con la fuente declarada.

No se interpretan RC/DS enriquecidos, fuentes incrustadas arbitrarias, fuentes desconocidas ni llamadas especiales. La edición general posterior de FreeText no se añade a la herramienta de anotaciones existentes en esta pasada. El borde de las variantes nuevas se reconstruye con el borde sencillo admitido por el intercambio; esto no acredita equivalencia con cualquier apariencia externa personalizada. La aceptación Acrobat/Nitro sigue pendiente.

### 4. Marcas personalizadas en notas Word

**Archivo → Crear PDF desde Word → convertir, revisar páginas y abrir**:

- Se admiten referencias con `customMarkFollows` y una marca literal de uno a cuatro caracteres en el mismo fragmento, inmediatamente después de la referencia.
- La referencia y la nota usan la misma marca y mantienen enlaces de ida/retorno. Las marcas personalizadas no consumen la numeración de las notas automáticas y no reciben un punto añadido.
- Una marca inicial separada repetida en la definición se incorpora una sola vez. No se elimina un prefijo de una palabra del contenido.
- Se comprueba que la marca sea imprimible, sin espacios/controles y con glifos en la fuente incluida. Marcas ambiguas, largas, ausentes o no cubiertas se rechazan antes de publicar.
- El resumen de importación muestra cuántas marcas personalizadas se conservaron.

No se añaden notas partidas entre páginas, reinicio de numeración por página ni marcas distribuidas entre fragmentos. La conversión continúa siendo una nueva maquetación revisable, sin ejecutar Office, macros ni recursos remotos.

## Comprobaciones y evidencias

**Aprobadas:** 3427 pruebas Python generales (346,55 s), 571 dirigidas finales, 128 JavaScript, compilación y recorridos Chromium/Qt Linux.

Consultar `validation/composition-cells-styles-notes-20261030/results.json`, los registros y sus huellas. La regresión general y las pruebas dirigidas se superponen; no se suman como cobertura independiente. Las pruebas dirigidas finales verifican los controles de marcas no imprimibles/glifos e incluyen la última protección ante una apariencia estilizada ausente, incorporada después de iniciar la regresión general.

Los recorridos Chromium verifican selección/cursor, bloqueo de sustitución, edición original/exportación, agrupación de celdas, revisión/importación de XFDF estilizado y notas Word personalizadas con revisión de todas las páginas. Qt Linux comprueba la ventana propia, guardado atómico y reapertura del texto con mezcla y de las celdas agrupadas. No se afirma ejecución Windows ni interoperabilidad comercial.

## Pendientes y siguiente trabajo

Los bloques 1–4 siguen ampliados, sin cierre general: fuentes/matrices/recursos restantes, máscaras y knockout; estructura mixta y reparación general/PDF/UA; XFA/JavaScript/fuentes y apariencias restantes; Office general, notas largas/partidas/reinicio por página y escaneos/diseños complejos. Los modos de mezcla estándar compatibles, los grupos no aislados RGB/Gray sencillos, las celdas con fragmentos explícitamente agrupados, las doce variantes XFDF descritas y las marcas Word acotadas ya no se presentan como pendientes.

Los bloques 5–8 mantienen sus pendientes de firmas/seguridad/estándares, planos/vinculación/portfolios/capas, Windows/estabilidad y servicios/IA. No se considera que solo falten estos cuatro bloques.

Siguiente avance recomendado: máscaras suaves revisadas con conservación de recursos, reinicio de notas Word por página y grupos de revisión XFDF. Modelo recomendado: **6.1 Sol, razonamiento medio**. Los puntos de aceptación con Windows, lector de pantalla, corpus personal y Acrobat/Nitro se mantienen separados del desarrollo en nube.
