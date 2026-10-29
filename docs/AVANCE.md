# Avance estimado del producto

Estado vigente de la base recuperada: [edición/revisiones/escritorio](EDICION_REVISIONES_Y_PRUEBA_20261029.md), ≈72 % (71,9 ponderado). Las cifras de versiones anteriores que siguen son históricas y no reemplazan la matriz reconstruida actual.

## Corte: versión 0.43

**Entrega 0.43:** ejecutable portable de prueba solicitado por el usuario, con lanzador Windows GUI, señal de preparación, cierre del proceso propio y registros. La ejecución gráfica Windows sigue pendiente. Guía: [ENTREGA_EJECUTABLE_043.md](ENTREGA_EJECUTABLE_043.md). Plan general configurable: [PLAN_CIERRE_Y_FLUJOS.md](PLAN_CIERRE_Y_FLUJOS.md).

**Seguimiento vigente: capacidades y criterios verificables.** En 0.42 se incorporan ocho entregables: secciones Word independientes, herencia de encabezados/pies, numeración continua/reiniciada, etiquetas, totales globales, SECTIONPAGES, saltos manuales y revisión/informes. Guía: [WORD_SECCIONES_042.md](WORD_SECCIONES_042.md). Matriz: [ESTADO_FUNCIONAL.md](ESTADO_FUNCIONAL.md).

**No se recalcula un porcentaje global en este corte.** El ≈90 % anterior era una estimación por áreas demasiado amplias, sin auditoría exhaustiva del catálogo ni un inventario de esfuerzo restante. Se conserva abajo como referencia histórica hasta 0.39; no se incrementa por acumular pruebas ni se presenta como una medición precisa del programa.

### Referencia histórica de ponderaciones hasta 0.39

| Área estable | Peso sobre el producto | Cobertura estimada en el área | Aporte global |
|---|---:|---:|---:|
| Lectura, búsqueda y navegación | 10 % | 95 % | 9,5 puntos |
| Organización y composición de páginas | 10 % | 95 % | 9,5 puntos |
| Anotaciones y revisión | 10 % | 95 % | 9,5 puntos |
| Edición de texto, imágenes y objetos | 20 % | 90 % | 18 puntos |
| Creación, conversión y OCR | 15 % | 95 % | 14,25 puntos |
| Formularios, firmas y seguridad | 15 % | 95 % | 14,25 puntos |
| Herramientas profesionales y automatización general | 10 % | 90 % | 9 puntos |
| Distribución, recuperación y calidad operativa | 10 % | 55 % | 5,5 puntos |
| **Total** | **100 %** | | **89,5 puntos / 100 (≈90 %)** |

Fórmula: suma de peso × cobertura de cada área. Conservar estos pesos entre avances; cualquier cambio de alcance debe documentarse y recalcular la referencia. Las automatizaciones personales de registros y planos están pospuestas y no forman parte de este denominador.

La cobertura se estima por capacidades utilizables y evidencia de validación, con crédito parcial para prototipos limitados. Tener un botón, conservar campos existentes o disponer de comandos de instalación no equivale a completar formularios, firmas o distribución Windows. Las pruebas sintéticas no justifican dar por cerradas funciones complejas. No se asignará 100 % a un área sin completar sus criterios y validar documentos representativos y la plataforma objetivo.

Desde 0.18 hay etiquetas nativas editables y navegación por etiqueta, movimiento de notas/rectángulos importados, tablas CSV con revisión y OCR con giro manual, firma visual, censura/saneamiento acotado, Bates entre varios archivos y adjuntos. Reciben crédito parcial por sus límites. Desde 0.19 hay radios exclusivos, texto/casillas compartidos y jerarquías compatibles, con datos, diseño y eliminación de grupos. En aquel corte estaban pendientes la importación de sus árboles, estructuras más complejas, firmas digitales/remotas, conversión Office, reflujo tipográfico, estándares, accesibilidad y automatización general. La distribución estaba en 50 %, sin prueba de ejecución Windows; los incrementos posteriores se detallan abajo. Guía detallada y restricciones: [AVANCE_LARGO_018.md](AVANCE_LARGO_018.md).

El aumento desde 61 puntos se distribuye en lectura +0,5 por navegación por etiquetas; páginas +0,5 por su edición/preservación; anotaciones +0,5 por movimiento conservador; conversión/OCR +1,5 por tablas y orientación manual; formularios/firmas/seguridad +3 por firma visual y censura/saneamiento inicial con verificaciones; herramientas profesionales +3 por Bates entre documentos, manifiestos y adjuntos. Edición y distribución no suben en este corte. Estas valoraciones no convierten prototipos en capacidades completas ni miden dificultad restante.

En 0.19 solo aumenta formularios/firmas/seguridad, de 65 a 75 % de cobertura: +1,5 puntos globales. El total ponderado es 71,5, comunicado como aproximadamente 72 %. No suben firmas digitales, distribución ni las demás áreas por este trabajo. Guía y restricciones: [FORMULARIOS_AVANZADOS.md](FORMULARIOS_AVANZADOS.md).

En 0.20 solo aumenta edición, de 70 a 75 % de cobertura: +1 punto global por la corrección de fragmentos con fuentes originales compatibles, incluidos subconjuntos TrueType y varios estilos, con ancho opcional y verificaciones. El total ponderado es 72,5, comunicado como aproximadamente 73 %. No se cuentan reflujo general, CFF/Type3, páginas etiquetadas complejas ni ejecución Windows. Guía: [TEXTO_CON_ESTILOS.md](TEXTO_CON_ESTILOS.md).

En 0.21 aumenta herramientas profesionales de 55 a 60 % por revisión estructural paginada, filtros, navegación e informe; calidad operativa de 50 a 55 % por búsqueda de funciones, comandos, atajos, controles de foco y protección de borradores comprobados. Suma +1 punto global; total 73,5 ≈74 %. Los pesos se mantienen; no hay crédito por ejecución Windows, nuevos formatos de conversión ni edición universal. Guía: [ESPACIO_DE_TRABAJO.md](ESPACIO_DE_TRABAJO.md).

En 0.22 se completa la distribución de funciones por áreas y el plegado contextual de paneles, con regresión de teclado, borradores y exportaciones. Se conserva la estimación 73,5 ≈74 %: es una mejora de usabilidad de funciones existentes, sin ampliar su cobertura de motor. Guía: [AREAS_DE_TRABAJO.md](AREAS_DE_TRABAJO.md).

En 0.23 formularios/firmas/seguridad pasa de 75 a 80 % por incorporar árboles compatibles al unir, duplicar y reemplazar páginas, con independencia de valores/grupos y verificación de la salida. Aporta +0,75 puntos globales: 74,25 ≈74 %. Se conserva el margen ±5, sin crédito por firmas digitales, XFA, cálculos o ejecución Windows. Guía: [IMPORTAR_FORMULARIOS.md](IMPORTAR_FORMULARIOS.md).

## Registro de incrementos

| Versión | Avance cerrado | Estimación global |
|---|---|---:|
| 0.43 | Ejecutable propio de prueba y plan de flujos configurables | Compilación/estructura verificables; ejecución gráfica Windows pendiente |
| 0.42 | Secciones Word independientes, SECTIONPAGES, saltos reales y revisión por sección | 100 % del bloque acotado verificado; sin nueva cifra global |
| 0.41 | Campos Word complejos, numeración y etiquetas PDF, tablas combinadas e informe integrado | Sin cifra global nueva; 5 entregables compatibles cerrados |
| 0.40 | Reflujo mixto por fragmentos, ajuste proporcional, verificación y revisión multipágina | Sin cifra global nueva; 5/5 criterios del bloque |
| 0.39 | Reglas entre operaciones de páginas/campos; encabezados/pies Word y revisión ajustada/ampliada | ≈90 % |
| 0.38 | Estilos/listas y formato de párrafo Word; reglas preservadas al organizar con protección de dependencias | ≈90 % |
| 0.37 | Importar DOCX compatible a PDF, reglas dependientes en proyectos y Word como salida de recetas | ≈90 % |
| 0.36 | Flujo explícito entre regiones/páginas, cálculos decimales de campos y enlaces web en Word | ≈89 % |
| 0.35 | Recetas ordenables, biblioteca JSON, revisión e informes por paso, ejecución CLI; compresión CMYK y en objetos anidados | ≈88 % |
| 0.34 | Extremos independientes, selección múltiple con alineación/distribución y acciones colectivas; carga modular y auditoría local de cierre | ≈87 % |
| 0.33 | Redimensionado nativo y tiradores de trazos/flechas importados, guía y cancelación, teclado e historial con selección conservada | ≈86 % |
| 0.32 | Interfaz minimalista, grupos plegables y ayuda persistente; movimiento nativo de trazos/líneas importados con apariencia conservada | ≈86 % |
| 0.31 | Selección precisa por caracteres, censura manual multipágina y búsqueda selectiva de términos/correos con revisión de todas las páginas | ≈86 % |
| 0.30 | Validación independiente PDF/A y PDF/UA, copia PDF/A-2b comprobada, título/idioma sincronizados y diagnóstico de accesibilidad | ≈86 % |
| 0.29 | Firma digital P12/PFX, firmas sucesivas, verificación de integridad/revisiones/confianza explícita e informes; lectura independiente con Poppler | ≈84 % |
| 0.28 | Word con imágenes y tablas editables, revisión de omisiones; renombrado jerárquico y opciones de listas existentes conservando valores | ≈83 % |
| 0.27 | Propiedades de campos existentes; conversaciones y estados nativos; informes CSV/JSON; texto editable a Word con revisión | ≈82 % |
| 0.26 | Enlaces existentes; formato y valores iniciales de campos; movimiento/tamaño de elipses y rectángulos importados; lotes de optimización, TXT y protección | ≈79 % |
| 0.25 | Edición de párrafos y fragmentos en páginas giradas con recorte, conservación del giro y fuentes, formato sugerido y comparación original/resultado | ≈75 % |
| 0.24 | Selección de bloques, 12 variantes tipográficas, color, interlineado, ajuste acotado de tamaño y vista previa con informe | ≈74 % |
| 0.23 | Importación, duplicación y reemplazo de formularios compatibles, grupos independientes y verificación de valores/apariencias y árbol final | ≈74 % |
| 0.22 | Siete áreas, búsqueda global que activa el área correspondiente, paneles contextuales plegables y protección de borradores | ≈74 % |
| 0.21 | Catálogo por tareas, favoritos, comandos, atajos y navegación; protección de borradores y revisión estructural con JSON | ≈74 % |
| 0.20 | Fuentes y estilos originales por fragmentos, TrueType parcial verificable, ancho opcional, vista previa y conservación de recursos compartidos | ≈73 % |
| 0.19 | Jerarquías compatibles, texto/casillas compartidos, radios exclusivos, diseño/eliminación de grupos y datos/aplanado con verificaciones | ≈72 % |
| 0.18 | Etiquetas/navegación, Bates entre archivos, adjuntos, tablas CSV, movimiento importado, firma visual, censura/saneamiento y giro OCR | 70 % |
| 0.17 | OCR local, datos/aplanado/diseño de formularios, imágenes existentes, bloques digitales, marcas de agua, metadatos, optimización, cifrado/apertura y comparación | 61 % |
| 0.16 | Relleno de formularios simples; creación de PDF desde PNG/JPEG; exportación de páginas editadas a imágenes por rangos y resolución | 42 % |
| 0.15 | Marcadores internos editables con jerarquía y estilos; encabezados/pies y numeración por rangos con vista previa, proyectos e historial | 39 % |
| 0.14 | Texto nuevo, sellos estándar y enlaces editables con proyectos; modo ventana experimental sobre Edge/Chrome | 37 % |
| 0.13 | Proyectos editables, recuperación local tras reinicio, duplicación, hojas en blanco y PDF preparado para impresión | 34 % |
| 0.12 | Imágenes PNG/JPEG nuevas: inserción, posición/tamaño, eliminación, historial y exportación con píxeles originales | 30 % |
| 0.11 | Zoom adaptado a pantalla y ampliación, controles de ajuste, herramientas agrupadas, guías y borradores explícitos | 28 % |
| 0.10 | Texto: fuente/tamaño/color en líneas base; portable Windows x64 offline ensamblado, pendiente ejecutar en Windows | 27 % |
| 0.9 | Selección, color, contenido de notas y eliminación de anotaciones preexistentes compatibles, con historial y restricciones | 24 % |
| 0.8 | Recorte/restauración, reemplazo reversible de bloques y división por bloques o grupos en ZIP | 23 % |
| 0.7 | Movimiento y cambio de tamaño de marcas de sesión, tiradores, ajustes numéricos y cancelación | 21 % |
| 0.6 | Resaltado, subrayado, tachado, notas editables de sesión y selección de marcas superpuestas | 20 % |

La versión 0.6 estableció la primera referencia porcentual. Al terminar cada avance se actualizarán esta tabla, la evidencia y el porcentaje comunicado al usuario. No se inventa una serie retrospectiva para versiones anteriores.

No se generan nuevos paquetes en este corte por indicación del usuario. La próxima entrega para pruebas personales se reserva para un ejecutable de Windows cuando el alcance esté casi completo.

## Evidencia de este corte

Validación del cierre 0.41: **2046 pruebas Python y 105 JavaScript aprobadas (2151 en total)**, compilación y recorrido completo de Chromium en Linux. Son 53 pruebas nuevas: campos repartidos/anidados/incompletos, formatos/inicios/etiquetas, MERGEFORMAT/CHARFORMAT, límites, combinaciones de tablas y alternativas sin pérdida, posiciones y edición posterior; integración en asistente, informe/hash, navegación romana, proyecto/recuperación y 600 px. Se mantiene la regresión previa. Evidencias: [validation/0.41/receipt.json](validation/0.41/receipt.json) y [CIERRE_041.json](CIERRE_041.json). Windows sigue sin validación; no se generó otro portable. Guía: [WORD_CAMPOS_TABLAS_041.md](WORD_CAMPOS_TABLAS_041.md).

En 0.8 la cobertura estimada del área de páginas pasa de 60 a 80 %, por completar tres familias previstas en P01/P02. Los demás pesos y estimaciones se mantienen. Las restricciones y el corpus sintético impiden considerar completa esta área.

En 0.9 la cobertura estimada de anotaciones pasa de 60 a 70 %, por gestionar identidades y propiedades de siete tipos existentes con historial y restricciones. No se declara completa la edición de anotaciones importadas. Los demás pesos y estimaciones no cambian.

## Siguientes trabajos recomendados

1. Hito siguiente concreto: secciones Word con papel/orientación/márgenes y encabezados propios. PAGE/NUMPAGES complejos, tablas combinadas compatibles y reflujo mixto ya están implementados en sus alcances declarados.
2. Fórmulas nativas interoperables, estructuras y tipos de formularios complejos y corpus real; ampliar la conservación de reglas a otras transformaciones compatibles.
3. Censura de estructuras complejas/OCR y corpus real; ampliar las geometrías y los grupos de anotaciones compatibles.
4. Secciones y campos complejos Word con corpus y contraste visual; OCR y rangos por paso en recetas; transparencia y máscaras en compresión.
5. Revocación, TSA y validación avanzada de firmas; accesibilidad/estándares y validación real del ejecutable Windows cuando corresponda su entrega.

El 90 % aproximado de los cortes anteriores se conserva como antecedente del modelo por áreas. Desde 0.40 no se comunica como una medición vigente auditada; se reportan criterios y capacidades con límites y evidencia.

En 0.10 la edición sube de 5 a 15 % de cobertura por fuentes base, tamaño y color con control de espacio; distribución sube de 20 a 30 % por el portable ensamblado, manifiesto de integridad, runtime/DLL incluidos y lanzador comprobado en Linux. La ausencia de ejecución Windows impide dar por terminada la distribución. Se conservan todos los pesos. El resto de áreas no cambia.

Recomendación registrada en 0.10: imágenes y recuperación de sesiones. Primero se debe registrar el resultado de la prueba del portable en Windows cuando sea posible. Fuentes incrustadas, párrafos y gestión avanzada de anotaciones siguen pendientes.

En 0.11 lectura pasa de 60 a 70 % por el renderizado adaptado al zoom y densidad, ajuste al ancho/página y estabilidad de la vista. Chromium valida DPR 2, zoom 200 %, cambios rápidos y marcado por clic/arrastre. Se agrupan herramientas, se añade guía contextual y se exige aplicar o cancelar borradores antes de exportar. Los otros pesos y coberturas no cambian. Los límites de resolución y los escaneados se describen en USABILIDAD.md.

Siguiente orden recomendado tras 0.11: recoger la prueba del portable actualizado con documentos reales; añadir edición de imágenes con conservación de calidad; guardar y recuperar sesiones. Continúan pendientes impresión, renderizado por regiones para planos grandes, fuentes incrustadas y párrafos.

En 0.12 edición pasa de 15 a 25 % por insertar y transformar imágenes nuevas con historial y exportación que conserva las dimensiones originales en píxeles. Hay 428 pruebas automáticas, compilación y recorrido Chromium aprobados. Las imágenes preexistentes, objetos generales, recorte interno, fotografías con orientación/perfiles especiales y lectores externos siguen pendientes. No cambian los pesos ni las demás coberturas.

Próximo orden tras 0.12: guardar/recuperar sesiones; validar Windows y preparar ventana propia; ampliar edición de imágenes existentes y texto complejo. La interfaz HTML/React es reutilizable en escritorio y el motor ya es local; véase ESCRITORIO.md.

En 0.13 lectura pasa de 70 a 80 % por preparar el PDF editado para imprimir desde menú/atajo; organización pasa de 80 a 90 % por duplicación y hojas en blanco con historial; distribución/recuperación pasa de 30 a 50 % por proyectos editables, checkpoint persistente, reemplazo atómico y revisiones con bloqueo entre procesos. Se mantienen todos los pesos. Los límites de formatos, permisos, corpus y plataforma impiden dar por completas estas áreas.

Evidencia 0.13: 480 pruebas automáticas (429 Python y 51 JavaScript), compilación y Chromium. El recorrido guarda/reabre proyectos con imágenes editables, rechaza uno dañado, recupera tras recargar y tras reiniciar realmente el motor, aplica y deshace/rehace hojas en blanco y duplicación, comprueba el PDF de impresión y simula un fallo de almacenamiento con descarga alternativa y reintento. El lanzador se comprueba con Python Linux en una carpeta con espacios, ahora incluyendo proyecto/checkpoint/restauración/impresión HTTP. Windows nativo e impresora física siguen pendientes.

Próximo bloque amplio: ventana de escritorio y prueba Windows, junto con creación de texto nuevo y revisión con sellos/enlaces según dependencias. Completar el editor de imágenes existentes y ampliar texto a párrafos/fuentes incrustadas requieren trabajo específico de motor y corpus.

En 0.14 edición pasa de 25 a 35 % por cajas de texto nuevas multilínea con fuente/tamaño/color/alineación y enlaces nuevos internos/web; revisión pasa de 70 a 80 % por sellos estándar con controles de sesión. La distribución permanece al 50 %: el modo ventana con Edge/Chrome instalado está implementado y tiene pruebas de ciclo de vida controladas en Linux, pero no una ventana Windows real. Se conservan los pesos y el resto de coberturas.

Evidencia 0.14: 558 pruebas automáticas (504 Python y 54 JavaScript), compilación y Chromium. Hay pruebas de cuatro giros/recorte para texto y enlaces, destino a la propia hoja girada, conservación de contenido vectorial, desbordamiento, permisos y proyectos. El recorrido de navegador crea/corrige/mueve texto, añade sello y dos enlaces, navega por el interno, verifica el PDF descargado y vuelve a editar tras abrir proyecto y recuperar. El lanzador comprueba texto nuevo/sello/enlace en su autoprueba y mantiene las comprobaciones HTTP anteriores.

Siguiente bloque amplio recomendado: marcadores editables, encabezados/pies y numeración de páginas, junto con validación del portable en Windows cuando sea posible. Imágenes preexistentes, párrafos existentes, fuentes incrustadas, OCR y sellos personalizados conservan sus trabajos específicos.


En 0.15 lectura pasa de 80 a 90 % por crear/editar marcadores compatibles con jerarquía, estilos y destinos; edición pasa de 35 a 40 % por encabezados/pies y numeración decimal/romana por rangos con seis posiciones y vista previa. El resto de estimaciones y todos los pesos permanecen iguales: 9 + 9 + 8 + 8 + 0 + 0 + 0 + 5 = 39 %. Destinos especiales, Bates y etiquetas internas siguen pendientes.

Evidencia 0.15: 662 pruebas automáticas (599 Python y 63 JavaScript), compilación y recorrido Chromium en Linux. Se verifican destinos/puntos/estilos/ramas con cuatro giros y recorte, lectura protegida de destinos especiales, seis posiciones y 12 fuentes base, límites de espacio/numeración, rangos fuera de orden, proyectos/checkpoint/impresión y consolidación tras organizar páginas. Chromium crea y mueve ramas, navega y deshace, exige vista previa vigente, aplica/quita/recupera numeración, inspecciona el PDF descargado, reabre proyecto y restaura sesión. El portable actualiza su autoprueba con índice y pie numerado; ejecución Windows real continúa pendiente.

Próximo bloque amplio recomendado: rellenar formularios existentes compatibles y persistir sus valores; añadir creación de PDF desde imágenes y exportación de páginas a imágenes. Validar el portable en Windows cuando sea posible. Imágenes preexistentes, párrafos, fuentes incrustadas y OCR mantienen hitos propios.


En 0.16 creación/conversión/OCR pasa de 0 a 10 % por crear PDF desde PNG/JPEG con orden/papel/márgenes y exportar páginas editadas a PNG/JPEG con resolución/ZIP; no se asigna avance a OCR u Office. Formularios/firmas/seguridad pasa de 0 a 10 % por rellenar campos simples existentes con valores y apariencias persistentes, historial/proyectos/recuperación; creación de campos, estructuras avanzadas, firmas y seguridad permanecen pendientes. Resto de áreas y todos los pesos iguales: 9 + 9 + 8 + 8 + 1,5 + 1,5 + 0 + 5 = 42 %.

Evidencia 0.16: 753 pruebas automáticas (690 Python y 63 JavaScript), compilación y recorrido completo Chromium en Linux. Incluye valores/apariencias y vaciado, rótulos/códigos de listas, permisos de relleno/copia, campos bloqueados, estructura de proyecto y organización, giros/recorte, píxeles/JPEG originales, transparencia, dimensiones y resolución de salida y límites de recursos. Chromium crea/corrige/recupera campos y compara píxeles exactos del PNG exportado con el PDF relleno; ordena dos imágenes, crea PDF, verifica JPEG original y exporta un rango inverso a JPEG a 150 ppp. El portable incluye formulario sintético y autoprueba de relleno/conversión. Ejecución Windows y corpus de documentos reales siguen pendientes.

Siguiente bloque amplio recomendado: datos de formularios (importar/exportar y aplanado explícito) y OCR inicial en escaneados con idioma elegido y control de calidad. El OCR necesita motor, idiomas, distribución portable y pruebas propios; no queda resuelto por exportar una página como imagen.


En 0.17 edición pasa de 40 a 70 % por imágenes existentes directas (mover/reemplazar/eliminar), reemplazo de bloques de varias líneas/múltiples fragmentos con DejaVu Sans incrustada y marcas de agua. Creación/conversión/OCR pasa de 10 a 45 % por OCR local español/inglés con conservación de imágenes y exportación TXT; Office y conversión Word/Excel siguen sin implementar. Formularios/firmas/seguridad pasa de 10 a 45 % por crear/eliminar campos simples, datos JSON vinculados por identidad, aplanado, AES-256, apertura autorizada y conservación de permisos en versiones. No se atribuye avance a firmas digitales o censura. Herramientas profesionales pasa de 0 a 25 % por comparación por páginas, propiedades/metadatos y compactación sin reducir píxeles. Se conservan pesos y demás áreas: 9 + 9 + 8 + 14 + 6,75 + 6,75 + 2,5 + 5 = 61 %.

Evidencia 0.17: 825 pruebas automáticas (762 Python y 63 JavaScript), compilación y Chromium en Linux. Hay OCR real con alineación, cuatro giros/recorte, búsqueda, conservación de píxeles/flujo de escaneado y omisión de páginas digitales; JSON con validación de identidad y rechazo atómico, aplanado conservando píxeles y anotaciones, creación/relleno/eliminación de campos, comparación de texto/apariencia, cifrado/autenticación/permisos, imágenes existentes con JPEG y máscara alfa, bloques Unicode con fuente incrustada y desbordamiento. Se comprueban restricciones de usuario vacío después de editar/organizar/recortar/optimizar. El recorrido inspecciona PDF/JSON/TXT descargados, recuperación y deshacer. La autoprueba portable incorpora idiomas verificados, OCR real y cifrado/apertura en el lanzador probado con Python Linux. Windows nativo, lectores independientes y corpus amplio continúan pendientes; distribución permanece al 50 %.

Alcance completo y límites de este bloque: AVANCE_LARGO_017.md. El porcentaje es una estimación de cobertura y madurez, no una equivalencia con Acrobat ni una promesa de que las funciones complejas estén completas.

En 0.24 se amplía la edición de párrafos y su usabilidad. Se conserva la estimación global como referencia secundaria hasta revisar cobertura con un corpus representativo; el trabajo se registra por funciones terminadas y verificadas. No se genera un nuevo portable. Guía: [PARRAFOS_Y_FORMATO.md](PARRAFOS_Y_FORMATO.md).

En 0.25 edición pasa de 75 a 80 % al valorar conjuntamente las capacidades verificadas de 0.24 y 0.25: doce variantes tipográficas, formato de párrafo y ajuste con límites, detección y comparación, más edición a 90°/180°/270° conservando recorte, fuentes compatibles y giro del PDF. Aporta +1 punto global; total ponderado 75,25 ≈75 % ±5 puntos. Los pesos se conservan. No se cuentan texto intrínsecamente inclinado/vertical, reflujo entre páginas, CFF/Type3, estructuras complejas ni ejecución Windows. Guía: [EDICION_PAGINAS_GIRADAS.md](EDICION_PAGINAS_GIRADAS.md).

En 0.26 edición pasa de 80 a 85 % (+1 punto global) por modificar/eliminar enlaces existentes conservando sus otras propiedades; anotaciones de 85 a 90 % (+0,5) por incorporar elipses estándar y redimensionado verificado de rectángulos/elipses; formularios de 80 a 85 % (+0,75) por formato, descripción, obligatoriedad, límites y valores iniciales con vista previa; herramientas profesionales de 60 a 70 % (+1) por lotes de optimización, extracción TXT y protección con revisión y manifiesto. Total 78,5 ≈79 % ±5 puntos, sin cambiar los pesos ni dar crédito por capacidad Windows, Office, certificados o estructuras complejas aún pendientes.

La petición de intentar llegar al 90 % no modifica los criterios de cierre: quedan conversiones Office con fidelidad comprobada, firmas con certificados, estándares/accesibilidad, más estructuras de edición/censura y validación del ejecutable propio en Windows. Tener estas funciones en un plan no suma cobertura. Guía: [AVANCE_AMPLIO_026.md](AVANCE_AMPLIO_026.md).

En 0.27 revisión pasa de 90 a 95 %, conversión de 55 a 65 %, formularios de 85 a 90 % y herramientas profesionales de 70 a 75 %. Aportan respectivamente +0,5, +1,5, +0,75 y +0,5 puntos globales: total 81,75 ≈82 % ±5. DOCX recibe crédito parcial por texto y formato básico; no por imágenes, tablas, importación o fidelidad de maquetación. Los pesos y las demás áreas permanecen iguales. No se declara 95 % ni se genera otro portable. Guía y pendientes: [AVANCE_AMPLIO_027.md](AVANCE_AMPLIO_027.md).

En 0.28 conversión pasa de 65 a 75 % (+1,5 puntos globales) por imágenes compatibles y tablas rectangulares editables, revisión de celdas y omisiones, con límites y lectura independiente del paquete. Formularios permanece al 90 % pese al renombrado y opciones de listas: no se completa todavía firmas/cálculos/XFA. Pesos y demás áreas iguales; total 83,25 ≈83 % ±5. No se cuentan importación Office, maquetación exacta ni validación Windows. Guía: [AVANCE_AMPLIO_028.md](AVANCE_AMPLIO_028.md).

En 0.29 formularios/firmas/seguridad pasa de 90 a 95 % (+0,75 puntos globales) por firma de aprobación SHA-256, certificados P12/PFX, revisiones incrementales y verificación con confianza explícita. Solo recibe crédito el alcance local verificado; no revocación, TSA, LT/LTA, tokens, XFA ni firma remota. No se añade crédito duplicado por el informe ni por preparar dependencias Windows. Pesos y demás áreas iguales: 84 ≈84 % ±5. Guía: [FIRMAS_DIGITALES.md](FIRMAS_DIGITALES.md).

En 0.30 creación/conversión pasa de 75 a 80 % (+0,75 global) y herramientas profesionales de 75 a 85 % (+1 global). Se valora la copia PDF/A-2b con validación independiente, comprobación de texto/tamaño y revisión visual; perfiles PDF/A/PDF/UA con veraPDF; diagnóstico y preparación de metadatos de accesibilidad. No se cuentan etiquetado completo, orden de lectura semántico, PDF/X ni ejecución Windows. Pesos y demás áreas iguales: 85,75 ≈86 % ±5. Guía: [ESTANDARES_Y_ACCESIBILIDAD.md](ESTANDARES_Y_ACCESIBILIDAD.md).

En 0.31 se mantiene 85,75 ≈86 % ±5. Se profundizan anotaciones y censura ya incluidas en la cobertura: selección parcial y vista de arrastre, preparación manual multipágina, búsqueda literal/correos con elección de coincidencias e inspecciones vinculadas al original/ediciones/consulta, revisión obligatoria por página y conservación de los límites del motor. No se contabilizan detección universal de datos sensibles, censura de estructuras complejas, nuevas familias comerciales ni ejecución Windows. Guía: [SELECCION_Y_CENSURA.md](SELECCION_Y_CENSURA.md).

En 0.32 se mantiene 85,75 ≈86 % ±5: se profundiza el trabajo de interfaz y anotaciones dentro de las áreas ya contabilizadas. Hay grupos de tareas, ayuda persistente, estilo común y controles más claros; traslado nativo de lápiz/líneas con apariencias conservadas. No se aumenta distribución sin ejecutar Windows ni se cuentan accesibilidad completa o manipulación universal de anotaciones. Guía: [INTERFAZ_PROFESIONAL.md](INTERFAZ_PROFESIONAL.md).

En 0.33 se mantiene la estimación conservadora de 85,75 ≈86 % ±5. Se completa el subtrabajo concreto de tiradores y redimensionado de trazos/flechas dentro del área de anotaciones ya contabilizada; no se cuenta otra vez el movimiento numérico de 0.32 ni se aumenta distribución sin ejecutar Windows. Siguen pendientes extremos individuales, selección múltiple, otras geometrías y corpus de fabricantes. Guía: [TIRADORES_IMPORTADOS.md](TIRADORES_IMPORTADOS.md).

En 0.34 creación/conversión/OCR pasa de 80 a 85 % (+0,75 global) por reducción controlada de imágenes RGB/gris de alta resolución, calidad JPEG, perfiles conservados, comparación, verificación de texto/geometría y recibo del PDF descargado. Las demás áreas y pesos se conservan: 86,5 ≈87 % ±5. También se cierran extremos independientes y operaciones múltiples en anotaciones existentes compatibles, sin contar dos veces sus capacidades anteriores; hay carga modular y evidencia local ligada a código/build/registros. No se cuentan compresión universal, Office fiel, accesibilidad semántica, seguridad avanzada ni ejecución Windows. Detalles: [AVANCE_AMPLIO_034.md](AVANCE_AMPLIO_034.md).

En 0.35 la estimación pasa de 86,5 a 87,75 ≈88 % ±5: creación/conversión/OCR 85→90 % por CMYK y recursos en Form XObjects anidados; herramientas profesionales/automatización 85→90 % por recetas, biblioteca, manifiestos y CLI. El resto de áreas y los pesos permanecen iguales. Las herramientas ya existentes no se vuelven a sumar por encadenarse en recetas. Transparencia/máscaras, OCR/Office en recetas y Windows siguen pendientes. Guía: [AVANCE_AMPLIO_035.md](AVANCE_AMPLIO_035.md).

En 0.36 edición pasa de 85 a 90 % por flujo explícito entre regiones y páginas (+1 punto global); áreas y pesos restantes sin cambio: 88,75 ≈89 % ±5. Cálculos puntuales y enlaces web profundizan formularios/Word ya incluidos; no se cuentan fórmulas automáticas, importación Office, etiquetado semántico ni Windows. Guía: [AVANCE_AMPLIO_036.md](AVANCE_AMPLIO_036.md).

En 0.37 creación/conversión/OCR pasa de 90 a 95 % por DOCX compatible a PDF (+0,75 global), con fuentes sustituidas y pérdidas declaradas. Pesos y otras áreas sin cambio: 89,5 ≈90 % ±5. Reglas en proyectos y Word en recetas amplían áreas ya incluidas; no suman otra vez familias completas. Office complejo, remapeo de reglas y Windows siguen pendientes. Guía: [AVANCE_AMPLIO_037.md](AVANCE_AMPLIO_037.md).

En 0.38 se mantiene 89,5 ≈90 % ±5. Estilos/listas Word y conservación de reglas al organizar profundizan familias ya contabilizadas. Se cierra ese remapeo concreto; quedan inserción/reemplazo, cambios de campos, Office complejo, semántica y ejecución Windows. No se asignan puntos duplicados ni se declara 1.0. Guía: [AVANCE_AMPLIO_038.md](AVANCE_AMPLIO_038.md).

En 0.39 se mantiene 89,5 ≈90 % ±5. Se amplía continuidad de reglas a las operaciones compatibles de páginas/campos y Word incorpora encabezados/pies y campos simples de página, con revisión ajustada/ampliada. Son subcapacidades de familias ya contabilizadas, sin puntos duplicados ni validación Windows atribuida. Guía: [AVANCE_AMPLIO_039.md](AVANCE_AMPLIO_039.md).

En 0.40 se retira la atribución de precisión al porcentaje global anterior y se separan capacidades implementadas/parciales/pendientes. Se cierran cinco criterios de reflujo mixto compatible, sin declarar reflujo universal ni inflar la cobertura comercial. Guía: [REFLUJO_MIXTO.md](REFLUJO_MIXTO.md). Matriz vigente: [ESTADO_FUNCIONAL.md](ESTADO_FUNCIONAL.md).

En 0.41 se cierran cinco entregables compatibles de Word sin convertirlos en puntos globales arbitrarios. Se actualizan los pendientes para separar los campos de página y tablas ya implementados de secciones, otros campos y estructuras todavía abiertas. Guía: [WORD_CAMPOS_TABLAS_041.md](WORD_CAMPOS_TABLAS_041.md).
