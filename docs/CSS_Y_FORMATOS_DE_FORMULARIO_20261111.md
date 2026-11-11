# Tipografía CSS y formatos de formulario · 11 de noviembre de 2026

## Cambios funcionales

**Edición con tipografía CSS.** Cambiar fuente, estilo o tamaño ya actualiza las declaraciones explícitas de CSS-1.00 junto con los glifos. Incluye una línea nativa, párrafos, continuación y los perfiles de geometría incorporados. Se mantienen el propietario CSS, nombres de propiedades, unidades pt/px y representación textual de peso/estilo. Los atributos directos y clases compartidas se aíslan: la clase original de otros elementos no se sobrescribe. La selección debe cubrir completamente los marcadores afectados. Al conservar la fuente original solo cambia el tamaño declarado.

El perfil admite familia única, tamaño absoluto positivo en pt/px, peso normal/bold o 100–900 y estilo normal/italic/oblique. No es un evaluador de CSS. Reglas relativas, listas de fuentes/cascada, herencia textual, transformaciones, otras propiedades/propietarios y composición general siguen protegidos. Las unidades declaradas requieren la transformación verificable que ya exige el formato nativo. Los documentos guardados mantienen su edición nativa y la asociación semántica; no se rasterizan ni se certifica PDF/UA.

**Importes negativos en rojo.** Se incorporan los estilos estándar 1 y 3 de AFNumber_Format: importe absoluto rojo, o importe rojo entre paréntesis. El valor PDF conserva el signo para edición/cálculos. Al introducir un positivo o cero real vuelve a negro; borrar genera un campo vacío. Un negativo que redondea a 0,00 conserva su apariencia negativa. Se comprueban la apariencia nativa, guardado/reapertura, campos compartidos y aplanado; no basta cambiar el valor que muestra la interfaz. Los estilos sin color mantienen su tratamiento anterior. No se ejecuta JavaScript del PDF.

**Rangos con límites textuales.** AFRange_Validate admite límites activos escritos como números o cadenas decimales literales con punto, finitos y acotados a 10^12. Los límites desactivados se ignoran. Un dato fuera del rango se rechaza y su borrador permanece disponible para corregirlo. Expresiones, límites activos inválidos o acciones adicionales siguen protegidos. No habilita validadores JavaScript generales ni XFA.

El comportamiento de los estilos estándar se contrastó con la [implementación pública de PDF.js](https://github.com/mozilla/pdf.js/blob/master/src/scripting_api/aform.js), como referencia de interoperabilidad; no se importó su motor de scripts ni se ejecutan acciones del documento.

## Uso

- **Texto:** Editar → Editar texto → selecciona el texto sobre la página. Cambia fuente/tamaño en la edición nativa o usa Editar párrafo y continúa si hace falta. Comprueba y aplica; los metadatos CSS compatibles se actualizan automáticamente. No hay un paso extra para buscarlos en un panel.
- **Importes y rangos:** Formularios y firmas → Rellenar formulario. Elige el campo e introduce el número respetando su separador. La vista previa muestra el formato y los límites. Aplica y guarda. Si el campo tiene un formato rojo, un negativo conserva su signo al editar aunque su apariencia use color o paréntesis. Un positivo vuelve a negro sin tener que cambiar el color manualmente.

La ayuda integrada y el manual por función incluyen estas capacidades y sus límites. No se publica otro portable ni se solicitan pruebas personales intermedias.

## Verificación de esta revisión

Fuente exacta `c1463f59f1f6d71c49ab01df8c1f3d43ab8f131f`, respaldada en `recovery/editing-20261029`. **5.003 pruebas Python aprobadas, 46 netas nuevas, tres advertencias**. También 151 JavaScript, compilación final y auditoría de guía 75 herramientas +15 operaciones. Hubo 268 pruebas dirigidas durante la implementación y 22 actuales de color/rangos; se solapan y no se suman como casos diferentes. La regresión completa incluye las tres regresiones de campos compartidos/redondeo añadidas después de aquella tanda dirigida.

**47 recorridos Qt desde fuente limpia en Linux y Windows Server 2025** y **20 ejecuciones independientes de Reapdf.exe aprobadas**, con tres básicas. Recibo **43029524260-1**, contrastado con objetos Git, logs y hashes. Archivo interno SHA256 `b7d9fa5084a99eaa2242102a5c9ae8d03a9147f4577befccfe37b814d18de1b2`; no se publica como otra entrega de usuario.

El recorrido geométrico existente ahora usa una muestra con CSS y cajas, cambia familia/tamaño y continúa conservando metadatos compatibles. El nuevo recorrido de formulario observa y aplica negativos/positivos y verifica los PDFs producidos con el servidor e intérprete incluidos. La comprobación compilada verifica familia CSS, glifos/cajas y valor/apariencia/color de campo de las salidas negativa y positiva. No acredita el diálogo nativo de guardar del exe. Desde fuente Qt se comprueban guardado y reapertura por la ruta nativa, con selector sustituido por el test; el rechazo de borrador fuera de rango se prueba allí y en el motor.

Las sondas de los drivers compartidos sobre Qt fuente no se cuentan como ejecuciones del exe aunque sus mensajes usen «compiled». Sus verificadores independientes también se probaron sobre las salidas reales de esas sondas antes de ejecutar Windows CI. Se corrigió el escape de un verificador multilínea antes de usarlo; no se atribuye una aprobación a esa versión inicial. Una expectativa antigua de solo lectura del estilo rojo 1 se sustituyó por pruebas independientes de valor con signo, color real del texto, cambio a positivo/cero, campos compartidos y aplanado. Los ayudantes desconocidos, instrucciones adicionales y expresiones continúan protegidos.

La tanda Qt Linux final se ejecutó después de terminar Python, con caché aislada y ayuda recompilada. Se preservan los límites de estabilidad e intermitencias históricas ya documentados: aprobar esta revisión no demuestra su causa ni las declara corregidas. No acredita Windows cliente limpio, DPI, impresora física, carga sostenida, interoperabilidad general ni aceptación personal. No se relajaron los plazos ni se ignoraron fallos para aprobar.

[Evidencia y hashes](validation/css-formats-20261111/results.json). Solo muestras sintéticas; documentos personales fuera de Git.

## Estado global

**Avance global estimado: 87,90 % provisional (≈88 %)**; antes 87,83 %. Mismos diecisiete pesos y alcance. Texto/imágenes 99,9→99,95 aporta 0,008 puntos; accesibilidad 99,5→99,75 aporta 0,0075; formularios 95→96 aporta 0,06. Cálculo exacto **87,829→87,9045**, incremento **0,0755**. No se suman puntos por documentación, preparación o repetir pruebas. Es juicio de ingeniería, no una medición objetiva de paridad con Acrobat ni de horas restantes. [Referencia anterior](progress/20261111-before-css-formats.json).

**Los ocho bloques generales siguen abiertos y la entrega técnica completa solicitada no está cumplida.** No solo faltan tus pruebas. El [plan vigente](PLAN_ACTUAL.md) mantiene las implementaciones de CSS relativo/composición, semántica general, XFA/acciones generales, Office/OCR, firmas/estándares, planos/portfolios/capas, cierre de escritorio y servicios/IA locales. No se trasladan al usuario como verificaciones.

La siguiente prioridad es el bloque 5: perfiles de preflight para estándares PDF/X, partiendo del diagnóstico de color/fuentes/cajas existente, sin repetirlo como una función nueva ni certificar conformidad sin comprobar sus requisitos. Modelo recomendado: **6.1 Sol, razonamiento medio**.
