# Edición de texto — versión 0.10

**Actualización 0.20:** hay un modo de edición por fragmentos con fuentes y estilos originales compatibles. Véase [TEXTO_CON_ESTILOS.md](TEXTO_CON_ESTILOS.md). Este documento describe el editor inicial de líneas con fuentes base.

La selección usa líneas originales horizontales de un único fragmento en páginas sin rotación. Se reconocen Helvetica, Times y Courier y sus cuatro variantes normal/negrita/cursiva/negrita cursiva, junto con alias conocidos de Arial y equivalentes. No se incorporan fuentes del sistema ni se descargan fuentes al editar.

El panel permite reemplazar el texto, elegir una de las 12 variantes PDF base, tamaño de 6 a 144 puntos y color RGB. Los cambios sin estilo explícito conservan la variante base equivalente, tamaño y color. Reabrir una línea durante la sesión muestra su texto y estilo actuales.

Se conserva el origen y la línea base. El ancho del texto nuevo debe caber en el ancho original; puede reducirse el tamaño para insertar más caracteres. Se permite aumentar la altura si no sale de la página ni invade otras líneas. También se rechazan cruces entre dos textos editados. Los cambios rechazados no se incorporan al historial ni sustituyen la última vista válida.

Se admiten caracteres latinos compatibles en una línea, con un máximo de 2000. Saltos de línea, emoji, escritura compleja, texto vertical o inclinado, párrafos, ampliación libre de cajas y fuentes incrustadas arbitrarias siguen pendientes. Los escaneados requieren OCR. Al cambiar a una variante base no se promete reproducir exactamente una fuente Arial incrustada de origen.

El texto original se elimina de su región conservando imágenes y gráficos de fondo; se inserta el nuevo contenido con el estilo elegido. No se considera una herramienta de censura general: metadatos, adjuntos y otros contenidos requieren un flujo específico de saneamiento.

Pruebas: 38 casos específicos de variantes, conservación de estilo, tamaño/color, línea base, ancho, cruces, límites de página, dos líneas que crecen simultáneamente y API. Chromium cambia a Times-Bold de 22 puntos y color elegido, comprueba selección posterior, rechazo de desbordamiento, historial y contenido del PDF descargado. El portable incluye una autoprueba de edición real, pendiente ejecutar con su intérprete Windows en este entorno.

Desde 0.14 hay una herramienta separada **Añadir texto** para crear cajas nuevas con varias líneas, fuentes base y alineación. No cambia los límites anteriores de modificación del texto preexistente. Véase CONTENIDO_NUEVO.md.
