# Duplicación y hojas en blanco — versión 0.13

**Duplicar páginas** permite indicar un rango como `1-3, 5` y una ubicación: al inicio o después de una página. Copia la versión con sus cambios aplicados, sin rasterizar las hojas. Conserva anotaciones compatibles, imágenes, texto y formularios; los campos copiados son independientes. El rango no admite repetidos; se puede repetir la operación para crear más copias. Las páginas con capas, XFA, cálculos/scripts y acciones de enlaces/marcadores no admitidas se rechazan siguiendo las restricciones de unión.

Los enlaces internos entre páginas copiadas se remapean al bloque nuevo; los destinos fuera de la selección se retiran. Los marcadores copiados quedan bajo «Páginas duplicadas». Las etiquetas existentes se mantienen como prefijos explícitos.

**Página en blanco** inserta una o varias hojas con tamaño igual a la página actual, A4/Carta vertical u horizontal, o dimensiones personalizadas en puntos PDF (72 puntos = 1 pulgada). Cada dimensión admite 10 a 3000 puntos. El total del documento no puede superar 500 páginas. Las hojas nuevas no contienen texto, imágenes ni marcas y admiten las herramientas de anotación e inserción de imágenes existentes; desde 0.14 también admiten cajas de texto nuevo; véase CONTENIDO_NUEVO.md.

Ambas operaciones permiten Deshacer/Rehacer y conservan el documento original. Crean una versión nueva del PDF: las marcas/imágenes anteriores pasan a ser contenido existente. Para recuperar sus controles de sesión, deshaz la operación de páginas. Los PDF firmados o sin permisos adecuados se rechazan. La duplicación exige permiso de copia y de organización.

Las pruebas comprueban inicio/medio/final, páginas giradas, formularios independientes, anotaciones editadas, enlaces, marcadores, etiquetas, tamaños, planes inválidos y restricciones. Chromium valida hojas en blanco y duplicación tras recuperar un proyecto, historial y el PDF de cinco páginas preparado para impresión. Falta un corpus amplio y lectores externos.
