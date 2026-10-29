# Precisión de medición e intercambio XFDF

29 de octubre de 2026. **Avance global estimado: 75,50 % (≈76 %), antes 74,60 %.** Mismos diecisiete pesos y alcance. Se incrementan medición, anotaciones e interoperabilidad por las funciones descritas; no se suman puntos por el número de pruebas. [Matriz](avance-global.json), [plan](PLAN_ACTUAL.md).

## Medición sobre el plano

- Ajuste del cursor a extremos de líneas/curvas vectoriales y esquinas de rectángulos, cuadriláteros e imágenes. Radio de ocho píxeles adaptado al zoom; Alt lo desactiva temporalmente. Una ambigüedad entre extremos diferentes no fuerza una elección. No usa controles Bézier como si fueran puntos del contorno. Hasta 10000 objetivos; informa si limita la geometría. Con capas se desactiva esta ruta hasta verificar visibilidad.
- Edición de vértices de mediciones propias: arrastrar, flechas (0,1 pt; Mayús 1 pt) o coordenadas numéricas. Permite añadir/quitar puntos según el tipo. Cambiar una medición vuelve a comprobar geometría, unidad y escala; reemplaza trazado y etiqueta juntos conservando su identificador. No publica polígonos cruzados ni cambios incompletos. La edición puede deshacerse como una versión del documento.
- Hasta veinte escalas regionales por página, con nombre, referencia y límites persistidos en el PDF. Se pueden crear, actualizar y retirar. Al iniciar una medición se selecciona la región que contiene el primer punto; las fronteras ambiguas requieren elección explícita. Las regiones no pueden solaparse y una medición regional no cruza sus límites. Cambiar una escala no recalcula silenciosamente mediciones anteriores: cada una conserva su calibración histórica.
- El diálogo mantiene controles y plano en paneles separados; se corrigió la superposición del pie sobre controles. La ampliación solicita una imagen con más resolución, hasta el límite del renderizador. Los estilos del diálogo no cambian la distribución de otras herramientas.

## Coordenadas y conservación

Las nuevas mediciones usan registro de versión 2 con puntos y referencias anclados al espacio PDF. Se derivan transformaciones desde la página enderezada para evitar omisiones de desplazamiento de recorte y UserUnit en las matrices rotadas del motor. Se prueban las cuatro rotaciones, recortes y UserUnit 1 y 2. La etiqueta ajusta su tamaño a esa unidad interna. Se mantienen los diccionarios PDF `/Measure` y su conversión, comprobados también con pyHanko.

La geometría nativa se contrasta con el registro antes de editar. Si alguien desplaza el trazado mediante otra herramienta sin actualizar sus datos, se avisa de la medición incompatible y no se ofrece un valor recalculado como fiable. La escala y las mediciones persisten al guardar/reabrir proyecto; la compilación de documentos relacionados copia también la clave de escalas regionales.

Los registros antiguos de versión 1 se leen y muestran mediante su geometría nativa, pero no se editan como si tuvieran el nuevo anclaje. Sus referencias de vista no se reutilizan automáticamente: requieren nueva calibración/medición. Las mediciones parcialmente recortadas tampoco se ofrecen para editar vértices. No se afirma una migración general editable de medidas de otros programas.

Límites restantes: intersecciones y puntos intermedios de curvas, mediciones angulares, corpus técnico real y aceptación externa. Un polígono mide sus segmentos rectos, no el área de curvas a las que solo se ajustaron extremos. Las comprobaciones no certifican exactitud de la calibración introducida por el usuario.

## XFDF ampliado

- Texto libre sencillo con Helvetica, Times-Roman o Courier regulares, tamaño/alineación/color y giros de 0/90/180/270 grados. Se conserva la fuente del subconjunto admitido; se rechazan otros estilos en vez de convertirlos silenciosamente a regular. El motor utilizado no conserva esos estilos a través de su API de texto libre.
- Subrayado ondulado, rellenos compatibles, bordes discontinuos incluidos valores fraccionarios, indicadores nativos, iconos/apertura de notas, asunto/fechas y extremos de polilínea.
- Se corrigió la expansión de figuras al reimportarlas teniendo en cuenta sus márgenes compatibles. Se comprueba geometría y apariencia tras giro y recorte. Los colores del intercambio usan RGB de ocho bits; no se afirma conservación exacta de espacios de color profesionales.
- Conflictos de nombres detectados también dentro del mismo lote y frente a anotaciones nativas de tipos no exportables. La importación conserva su carácter atómico y la reimportación idéntica se omite.
- Las etiquetas de medición no se exportan aisladas de las medidas que las justifican. Las mediciones siguen fuera de este subconjunto XFDF.

Siguen fuera texto enriquecido, llamadas de texto libre, fuentes/estilos adicionales, márgenes avanzados, hilos y estados XFDF, medidas, capas y otros subtipos. Las respuestas/estados internos ya existentes no se anuncian como funciones nuevas. Sin ejecución de scripts ni carga de recursos externos. Escribir y releer PDF/XFDF no acredita aún su aceptación en Acrobat o Nitro.

## Verificación real

**2589 pruebas Python** en la regresión completa, **116 JavaScript** y compilación aprobadas. Después se añadieron seis casos de esquinas de imágenes/escala nativa; la comprobación final de medición aprobó **51 pruebas**, incluidas esas seis. No se repitió la regresión general para esos casos adicionales sin cambios de motor.

Tres recorridos Chromium aprobados: nuevo ajuste/escala regional/selección automática/edición de vértice/exportación/deshacer/rehacer/XFDF ampliado; documentos vinculados/medición anterior/capas; formularios XFDF/copia identificada de firmado/accesibilidad/OCR/zoom A0. Datos, fuentes, coordenadas, etiquetas y conversión nativa se comprueban en archivos exportados, con lectura independiente mediante pyHanko. [Registros y huellas](validation/precision-xfdf-20261029).

Sin nueva prueba Qt específica de estas herramientas, Windows, impresión física ni aceptación personal. Esas comprobaciones no se sustituyen por Chromium. Sin portable/instalador, inspección de programas comerciales ni instalación de REA. No se modificaron ni publicaron PDFs privados.

## Continuación

1. Compatibilidad de texto original en Forms con inclinación, reflexión y giro interno, con detección de recortes y preservación de otras apariciones.
2. Después, fuentes CFF2/variables/Type3 según compatibilidad demostrable; no sustituir sus programas silenciosamente.
3. Migrar el recorrido gráfico histórico pendiente y ejecutar la verificación Windows del candidato cuando corresponda. La prueba personal sigue aplazada.
4. Conservar separados los demás pendientes comerciales: formularios, conversión/OCR avanzada, accesibilidad, firmas/estándares, servicios, licencias e interoperabilidad externa.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
