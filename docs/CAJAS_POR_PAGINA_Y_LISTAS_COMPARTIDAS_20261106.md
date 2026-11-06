# Continuación con cajas por página y listas compartidas · 6 de noviembre de 2026

## Implementación

**Geometría de párrafos continuados.** Un párrafo completo compatible con BBox/Width/Height Layout ya puede continuar en áreas de otras páginas o crear páginas automáticamente. Se prueba primero la cobertura completa de los MCID y la caja original. Las declaraciones espaciales que dejan de describir una sola página pasan a las hojas Span de cada página; el contenedor lógico, su rol, orden y atributos no espaciales permanecen. No se calcula una caja con coordenadas de páginas distintas. Las clases y atributos compartidos se aíslan sin modificar sus otros usuarios.

Las cajas de salida se calculan desde cada fragmento y la transformación de su propia página, conservando dimensiones numéricas, Auto o ausencia. Se comprueba la asociación única con ParentTree antes y después de guardar. Los fragmentos guardados pueden editarse nuevamente en su página sin alterar el otro. Se incluyen fuentes/tamaños, rotaciones y recortes. Si un grupo de estilo queda completamente vacío al editar el texto, se retira su geometría obsoleta sin borrar el resto del párrafo. Dimensiones Auto/numéricas superpuestas incompatibles se rechazan; no se decide silenciosamente cuál ignorar.

Esto amplía el perfil de cajas que antes solo admitía redistribución dentro de la página. No habilita cualquier caja multipágina de un PDF ajeno: la declaración de origen debe poder asociarse completamente a la página seleccionada. CSS, semántica general/mixta, ActualText/Stm generales y otras composiciones siguen pendientes. No certifica PDF/UA.

**Listas compartidas.** Una lista o desplegable de selección simple que pertenece al mismo campo lógico en varias páginas ya se rellena desde cualquiera de sus posiciones. Valor, selección y apariencias se actualizan juntos. El PDF conserva /V e /I en el propietario del campo; los Widgets no reciben valores locales que oculten al propietario. Borrar y volver a seleccionar, guardar/reabrir, datos JSON y aplanado explícito recorren el grupo completo.

Las opciones, etiquetas y tipo de control deben coincidir y el índice opcional debe concordar con el valor. Una contradicción, una posición de solo lectura, acciones no compatibles o una estructura inválida bloquean todo el grupo. No se habilitan XFA, selección múltiple o escritura libre en una lista ni se ejecuta JavaScript.

## Uso

- **Continuar texto:** Editar → Editar texto → pulsa el texto sobre la página → Editar párrafo. Ajusta texto y formato. Usa Continuar en otra página y selecciona áreas vacías, o paginación automática. Comprueba la distribución y aplícala completa. Guarda desde Reapdf. Las cajas de accesibilidad se actualizan automáticamente; no hay un paso adicional para hacerlo.
- **Lista compartida:** Formularios y firmas → Rellenar formulario. Selecciona la lista en la página o panel, elige una opción, espera la vista previa y aplica. Todas sus posiciones compatibles se sincronizan. Para borrarla, elige Sin selección. Guarda y vuelve a abrir; seleccionar la otra posición muestra el mismo valor.

La guía general conserva acceso, pasos, resultado y límites de las 75 herramientas y 15 operaciones de escritorio. Las revisiones personales continúan al final; no se publica otro portable en esta pasada.

## Verificación

Fuente `c41be59da7ddd6c597795fd5dd9788416676b599`, respaldada en `recovery/editing-20261029`. **4.957 pruebas Python aprobadas, 79 netas nuevas, tres advertencias**, más 203 dirigidas, 151 JavaScript, compilación y auditoría de guía 75+15. La regresión completa corresponde al mismo contenido final, sin cambios de implementación posteriores.

**46 recorridos Qt desde fuente limpia en Linux y Windows Server 2025.** Recibo Windows **42280874609-1**, contrastado con objetos Git, evidencias y hashes. **19 ejecuciones independientes de Reapdf.exe aprobadas**, incluidas tres básicas. El recorrido geométrico ahora continúa desde una muestra que sí tiene cajas declaradas y comprueba que se materializan cajas por página; el nuevo recorrido de formulario rellena la lista compartida y comprueba valores, índices, apariencias y página ajena. Archivo interno SHA256 `9bd890d990226d9739ccd64ab0bea77881df47fcb463bf8bf4fe4358fcc05446`; no se publicó otro portable.

La continuación geométrica manual, formato, deshacer/rehacer, guardado y reapertura se ejercitan en la ventana Qt; la paginación automática con geometría también tiene pruebas del motor guardado/reabierto. El recorrido de lista compartida selecciona ambas posiciones al reabrir y comprueba la ruta nativa de guardado con selector de archivo sustituido por el test. Los recorridos compilados exportan por el servidor incluido y verifican con el intérprete incluido; no acreditan el diálogo nativo de guardar del exe. Las sondas de los drivers compartidos desde Qt fuente se registran como fuente, aunque su mensaje use la palabra «compiled».

## Fallos encontrados y límites de la evidencia

La interfaz reveló un rechazo real cuando un estilo del párrafo quedaba sin texto. Se corrigió la retirada de su caja obsoleta y se añadieron cuatro regresiones, borrando cualquiera de los estilos con y sin continuación. No se permite conservar una caja que describe glifos que ya no existen.

Un verificador nuevo intentaba inspeccionar fuentes en una página vacía; se corrigió el fixture para inspeccionar páginas con texto. Las dos antiguas expectativas de rechazo de continuación se sustituyeron por una comprobación de vista previa y salida, además de las nuevas pruebas independientes de contenido, geometría, estilos y páginas ajenas. Las protecciones de cajas inválidas/contenido no seleccionado permanecen. Una sonda diagnóstica llamó por error a la propiedad booleana Response.ok como función; se corrigió solo esa sonda.

Dos recorridos Qt lanzados en paralelo no respondieron en el plazo del verificador; se aislaron cachés y se ejecutaron secuencialmente. Una primera tanda de 46 pasó antes de recompilar el texto nuevo de la ayuda. Tras recompilar, otra tanda se detuvo en el recorrido de portfolio por falta de respuesta de Qt al guardar el diseño, sin error HTTP demostrado. La tanda final aislada, después de terminar Python, aprobó los 46. **Se preserva esa intermitencia y no se afirma que su causa esté probada o corregida por aprobar después.** No se ampliaron plazos, quitaron comprobaciones ni incorporaron reintentos que ignoren fallos. No acredita cliente Windows limpio, DPI, impresora física, carga sostenida ni resolución de las intermitencias históricas.

[Evidencias y hashes](validation/pageboxes-shared-choices-20261106/results.json). Todas las muestras son sintéticas; documentos personales fuera de Git.

## Estado y siguiente trabajo

**Avance global estimado: 87,83 % provisional (≈88 %)**; antes 87,73 %. Mismos diecisiete pesos y alcance. Texto/imágenes 99,75→99,9 aporta 0,024 puntos; accesibilidad 99→99,5 aporta 0,015; formularios 94→95 aporta 0,06. Cálculo exacto **87,730→87,829**, incremento **0,099**. No se añaden puntos por documentación, preparación, pruebas ni diagnósticos. Es juicio de ingeniería, no una medición objetiva de paridad con Acrobat ni de horas restantes. [Referencia anterior](progress/20261106-before-pageboxes-shared-choices.json).

Los ocho bloques generales continúan abiertos; **la entrega técnica completa solicitada no está cumplida**. No solo faltan las pruebas personales. El [plan vigente](PLAN_ACTUAL.md) conserva implementaciones pendientes de CSS/semántica y geometría inicial ambigua, formularios XFA/acciones generales, Office/OCR, firmas/estándares, planos/portfolios/capas, cierre de distribución/estabilidad y servicios/IA locales. Estos trabajos no se trasladan al usuario como verificaciones.

Siguiente prioridad: atributos CSS tipográficos y acciones/validadores de formularios fuera del perfil actual. La continuación con cajas por fragmento y las listas compartidas compatibles ya están incorporadas; no se presentan de nuevo como funciones ausentes. Modelo recomendado: **6.1 Sol, razonamiento medio**.
