# Párrafos etiquetados, columnas Word y enlaces internos · 5 de noviembre de 2026

La solicitud de terminar todos los pendientes del programa **no está cumplida**. Este trabajo incorpora tres capacidades funcionales y sus recorridos de guardado/reapertura; no declara completado ninguno de los ocho bloques generales. Las verificaciones personales siguen reservadas para después de la entrega técnica final.

## Edición de párrafos con estructura de accesibilidad

Antes, Editar párrafo permitía redistribuir un fragmento etiquetado en su página, pero bloqueaba el reflujo de estilos mixtos y su continuación. Ahora reconoce el párrafo mediante MCID, ParentTree y orden K. No agrupa etiquetas por parecido visual ni mezcla celdas o párrafos diferentes. Admite contenedores P, encabezados y celdas compatibles, con descendientes Span, contenido directo y objetos completos de la página.

El usuario pulsa el texto con el ratón, elige **Editar párrafo**, escribe en una caja y aplica con Ctrl+Enter. Puede elegir **Seleccionar varios bloques** para una selección explícita; se comprueba que cubra el párrafo completo en su orden semántico. Una selección parcial, mezclada o ambigua se rechaza sin publicar cambios. Se conservan fuente, tamaño, color, espaciado y transformaciones compatibles de cada estilo. Las superposiciones métricas preexistentes no impiden un cambio contenido en la huella original de su fragmento; no habilitan ampliar el párrafo sobre textos vecinos.

En la misma página conserva el árbol y todos los marcadores. **Continuar en otra página** admite hasta siete áreas vacías, y la paginación automática añade hasta dieciséis páginas nuevas. Al continuar crea hojas Span con página y MCID propios bajo los contenedores originales, coordina ParentTree y conserva el orden de lectura. Antes de retirar una restricción Pg de un contenedor que ahora abarca varias páginas, materializa las asociaciones de sus hijos; los hermanos no editados mantienen sus páginas. No elimina etiquetas ni convierte el documento en imágenes.

La comprobación posterior al guardado compara el grafo y los marcadores esperados, los glifos/estilos/geometría resultantes, las asociaciones del párrafo guardado y los demás textos. La prueba de lectura interpretada por MuPDF reconoce las continuaciones. El presupuesto de comprobación estructural se amplía de 30.000 a un millón de pasos, conservando límites de profundidad, tamaño y alternativas protegidas. Una muestra sintética de 42 páginas y más de 4.200 nodos verifica edición y conservación del grafo; no sustituye el documento privado de 42 páginas de las capturas.

Siguen protegidos ActualText/Alt, Stm, etiquetas de Forms, figuras mezcladas con el párrafo, atributos geométricos/clases/espacios de nombres no coordinados, fuentes o composición no verificables y direcciones incompatibles. La selección editable sigue limitada a cien fragmentos y cuatro mil caracteres. No es reparación general ni certificación PDF/UA; el texto añadido por otras herramientas no se etiqueta automáticamente.

## Importación Word con columnas

**Archivo → Crear PDF desde Word** reconoce de una a cuatro columnas por sección, iguales o con anchos individuales, sus espacios y separadores opcionales. El contenido fluye primero hacia abajo y luego a la siguiente columna. Los encabezados/pies y la numeración cuentan páginas físicas, no columnas. Las notas al pie siguen a su referencia y reservan una región bajo todas las columnas; los enlaces de retorno se conservan. El informe y la interfaz muestran las columnas de cada sección.

Se comprueban las palabras del PDF generado; una pérdida de texto en columnas aborta la conversión. Cada columna necesita al menos 72 pt; anchos desiguales y espacios deben corresponder al área disponible. Las secciones continuas, los saltos manuales dentro de varias columnas y el equilibrado de la última página permanecen pendientes. El PDF conserva texto seleccionable y trazos nativos para los separadores. La importación sigue sustituyendo fuentes por DejaVu Sans y no promete fidelidad universal de Office.

## Enlaces internos de Word

Los enlaces w:anchor a marcadores compatibles del cuerpo se convierten en enlaces internos PDF nativos. Se resuelven hacia delante y hacia atrás después de paginar, incluso entre columnas/páginas. Los marcadores pueden abarcar párrafos y varios enlaces pueden compartir un destino. Los nombres/identidades ambiguos y los destinos declarados sin cierre se rechazan. Los destinos inexistentes conservan el texto visible con advertencia, sin inventar un salto. Los marcadores sin cierre que no sean destinos no eliminan texto y se informan como omitidos. Las partes de encabezados no duplican por coincidencia los destinos del cuerpo.

## Verificación y límites de entrega

Fuente verificada **001183628c71da181b8a1ef74ae3144a0abc5417**, respaldada en recovery/editing-20261029.

- **4.608 pruebas Python aprobadas**, tres advertencias conocidas; 63 casos funcionales nuevos. JavaScript: **151 aprobadas**. Compilación y manual de 75 herramientas y 15 operaciones generales aprobados.
- **35 recorridos Qt Linux y 35 Windows** desde fuente limpia antes/después. Windows: comprobante **42046215356-1**, contrastado con los objetos Git y las sumas de sus evidencias.
- **Siete aperturas independientes de Reapdf.exe aprobadas**, incluidas selección explícita/continuación de párrafo etiquetado e importación Word con columnas/marcadores. El intérprete incluido reabre las salidas y verifica texto, estilos/matrices, lectura etiquetada, separadores y destino del enlace. No se usa un navegador externo.

El primer intento f2ffeed falló en Linux y Windows porque un recorrido antiguo exigía deshabilitar siempre selección/paginación etiquetada. Se actualiza esa expectativa y se habilita la selección explícita con comprobación semántica. La revisión también detectó y corrigió el rechazo de una edición dentro de su huella en páginas densas; se añade prueba que exige rechazar expansión hacia el vecino. La batería Python inicial se interrumpió para incorporar esa corrección y se ejecutó de nuevo completa en la fuente final.

El primer recorrido Word independiente contó también el subrayado del enlace como si fuera un separador y falló su aserción; se identifica ahora el separador por su geometría vertical y se comprueba de nuevo la salida guardada. La primera batería Linux en 0011836 se detuvo en una respuesta Qt ausente durante apertura de portfolio; se conserva el fallo. La repetición completa, ejecutada después de Python, aprobó sin modificar la fuente. Esto **no demuestra la causa ni la resolución de intermitencias históricas**. Los recorridos Qt comprueban guardado nativo y reapertura; los recorridos compilados exportan mediante el servidor real del paquete y no acreditan por ello un diálogo nativo de guardado.

No se publica otro portable ni se solicitan pruebas personales. La preview de prueba anterior no contiene estas mejoras. Las pruebas nuevas emplean muestras sintéticas, sin datos privados en Git. Windows Server en CI no acredita Windows cliente limpio, DPI, impresión física, pérdidas de energía ni carga sostenida. Las intermitencias históricas no se declaran resueltas por repetir una batería.

## Alcance que sigue abierto

1. **Edición avanzada:** fuentes/composición/direcciones generales, ActualText/Stm y Forms etiquetados, máscaras y colores/grupos complejos. El nuevo perfil de párrafos etiquetados compatibles ya está incorporado y no debe volver a listarse como ausente.
2. **Accesibilidad:** reparación semántica general, contenido nuevo, relaciones complejas y PDF/UA; pruebas externas de lectura e interoperabilidad.
3. **Formularios/intercambio:** XFA, acciones/validadores JavaScript generales y variantes de apariencias/XFDF.
4. **OCR/Office:** secciones continuas, equilibrio y saltos manuales en columnas; campos/fidelidad Office generales, notas partidas y variantes OCR/tablas aún protegidas. Las columnas compatibles y enlaces a marcadores ya están incorporados.
5. **Seguridad/estándares:** PAdES-LT/LTA, renovación/revocación histórica por red, censura nativa compleja y PDF/X/preflight.
6. **Planos/portfolios/capas:** geometría fuera del perfil verificado, carpetas/esquemas complejos, reglas OCG generales y edición de contenido de capas.
7. **Windows/estabilidad:** paquete final del alcance completo, cliente limpio/DPI/asociaciones/impresión y carga/recuperación sostenidas.
8. **Servicios/IA:** colaboración/sincronización y modelo local real con licencia, recursos y evaluación. Se mantiene la prioridad de funcionamiento local sin servicios de pago.

La matriz global conserva diecisiete áreas y sus pesos. La entrega técnica completa y la aceptación personal se registran por separado; ninguna es verdadera. Modelo recomendado: **6.1 Sol, razonamiento medio**.

Estimación global actualizada: **87,29 % provisional** (antes 87,14 %). Con los mismos pesos/alcance: accesibilidad 95→97 por asociación semántica de estilos y continuación; OCR/conversión 97→98 por columnas y navegación interna de Word. No se asignan puntos por documentación, preparar herramientas o repetir pruebas. No es una medición de paridad con Acrobat ni de tiempo restante.
