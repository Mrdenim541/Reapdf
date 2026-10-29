# Edición escalada, grupos de texto y vínculos por áreas

Estimación total **≈73 % (72,75 ponderado)**, frente a 71,9. Alcance, diecisiete áreas y pesos se mantienen en [avance-global.json](avance-global.json); el corte anterior está en [progress/20261029-before-scale-manual.json](progress/20261029-before-scale-manual.json). Son estimaciones de madurez, no equivalencia con Acrobat ni aceptación final. Cambian edición y vinculación; las otras quince áreas no suman puntos.

Se continúa el desarrollo en nube. La verificación personal en PC queda aplazada por indicación del usuario. No se instala REA ni se prepara/entrega otro ejecutable en este bloque. Las comprobaciones internas del motor y de los flujos afectados acompañan al código; no requieren participación del usuario ni acreditan Windows.

## Funciones nuevas

### Texto comprimido o estirado

El editor sobre la página conserva el factor horizontal PDF Tz en el intervalo positivo 10–400 %. Calcula el ancho y las posiciones incluyendo escala, ajustes TJ y espaciados Tc/Tw. Distingue el tamaño nominal de la fuente del tamaño aparente que devuelve el extractor: no convierte accidentalmente un texto nominal de 18 pt y escala 80 % en uno de 16,1 pt.

Conserva programa de fuente, color, posición y operadores externos a la edición. Mantiene los ajustes entre parejas de caracteres que siguen juntas. Se verificaron fuentes base y TrueType simple/Identity-H, cuatro escalas y cuatro giros. Transformaciones inclinadas/reflejadas, mapas de fuente incompatibles, glifos ausentes y espacios inferidos siguen protegidos.

El reflujo original de bloques escalados queda bloqueado expresamente; editar una línea conservando escala es distinto de redistribuir un párrafo. No se normaliza su escala silenciosamente al entrar al reflujo.

### Líneas divididas en varias instrucciones internas

Un PDF puede representar una sola línea mediante varias instrucciones consecutivas Tj/TJ dentro del mismo objeto de texto. El motor ahora identifica el grupo completo y permite corregirlo desde el mismo campo sobre la página. Sustituye el grupo por una instrucción compatible; preserva los bytes anteriores/posteriores y las fuentes.

No absorbe cambios de fuente, color, posición, marcado o estado entre instrucciones. Tampoco agrupa líneas distintas o estructuras ambiguas. La detección de la ruta de edición se guarda en la caché por página para no repetir el análisis de agrupación en cada región de un lote.

### Vincular áreas sin depender de códigos detectados

En **Documentos → Vincular documentos**, elegir origen/destino y abrir **Vincular áreas manualmente**. Escribir una referencia general, elegir página y arrastrar un área en cada documento; después crear el vínculo. Funciona con páginas escaneadas sin OCR y sin interpretar su contenido como instrucciones.

Las regiones se validan dentro de la página y se vinculan a la huella del PDF, página, coordenadas y referencia. Se guardan/reabren, aparecen en la navegación y pueden compilarse en un PDF con enlaces y marcadores. Se conservan las condiciones existentes para firmas, formularios, capas y permisos de esa compilación; el conjunto mantiene los originales.

Los conjuntos con referencias manuales usan formato **2**. El lector actual admite formatos 1 y 2; los conjuntos sin referencias manuales continúan exportándose como formato 1. Las versiones antiguas que solo admiten el formato 1 no abrirán un conjunto con áreas manuales. No se permite declararlo falsamente como formato 1.

Al cargar una revisión de un archivo, una región manual **no se copia ni se sigue automáticamente**, aunque se encuentre un código impreso igual. El usuario debe volver a marcar la región/página en el archivo nuevo o retirar ese vínculo expresamente; después confirma la revisión. Se mantiene deshacer la última revisión del conjunto.

## Evidencia y límites

**Resultados internos:** 2382 pruebas Python de regresión aprobadas; 89 pruebas dirigidas posteriores, incluidos cuatro casos nuevos de extremos de escala; 109 JavaScript y compilación aprobados. Tres recorridos Chromium aprobados. Lectura de compatibilidad del PDF original del usuario correcta, sin modificarlo.

Resultados finales en [validation/scaled-manual-20261029/results.json](validation/scaled-manual-20261029/results.json), con registros y huellas. Se comprobaron cambios de texto, conservación de posiciones/fuentes, límites de tamaño y estados intermedios rechazados; conjuntos antiguos, áreas alteradas, remapeo de IDs, revisión manual y enlaces compilados en cuatro rotaciones.

El recorrido Chromium pulsa el texto escalado, lo edita y exporta; marca áreas en dos escaneados, crea el vínculo, carga una revisión de dos páginas, vuelve a marcar la segunda y guarda/reabre el conjunto. No modifica documentos personales. Se repiten también los recorridos vigentes de edición/párrafos y vínculos/medición/capas.

No se acreditan en este bloque aceptación Windows, impresión física, CFF/Type3, texto dentro de Form, reflujo original mixto ni la migración completa de la antigua suite gráfica. Su verificación no se inventa para elevar el porcentaje. La generación de informes/registros/ensayos personales sigue excluida.

## Próximos trabajos

1. Compatibilidad de fuentes CFF y texto dentro de Form, con casos concretos rechazados actualmente.
2. Reflujo original con estilos mixtos y selección de bloques más flexible; mantener una alternativa clara cuando una estructura no es compatible.
3. Migrar el recorrido gráfico histórico a la interfaz actual. La aceptación personal y Windows se retomarán después, según lo indicado por el usuario.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
