# Plan de desarrollo: primero el editor general

La prioridad aceptada por el usuario es construir las funciones de un editor comercial tomando Acrobat como referencia. Las automatizaciones personales se desarrollarán como flujos generales configurables; la entrega de prueba del ejecutable precede al nuevo bloque según la solicitud vigente. No se promete paridad completa en esta primera versión.

## Distribuir funciones por áreas — incremento 0.22

Solicitud del usuario del 20 de octubre de 2026: la interfaz muestra demasiadas funciones en una sola pantalla. La búsqueda y los filtros de 0.21 no cierran este requisito. Estado: implementado en 0.22; áreas, búsqueda global, paneles y protección de borradores. Evidencia en [AREAS_DE_TRABAJO.md](AREAS_DE_TRABAJO.md); no aumenta el porcentaje de avance.

- Separar el trabajo en áreas: **Leer**, **Editar**, **Comentar**, **Organizar páginas**, **Formularios y firmas**, **Convertir y OCR** y **Proteger**. Distribución inicial que se ajustará con recorridos de uso.
- Mostrar por defecto únicamente las herramientas del área activa. Conservar una búsqueda global para acceder a cualquier función y cambiar al área correspondiente.
- Mostrar propiedades contextuales cuando se selecciona una herramienta u objeto. Permitir plegar navegación y propiedades para priorizar la página.
- Separar los asistentes de varias etapas (OCR, comparación, censura y lotes) del espacio de lectura mediante vistas o diálogos dedicados, con retorno claro al documento.
- Mantener acciones comunes accesibles: abrir, guardar proyecto, exportar, deshacer/rehacer y navegación. Evitar duplicar botones entre paneles.
- Conservar borradores al cambiar de área: pedir aplicar/cancelar o bloquear el cambio de manera explicada. El cambio de área no debe modificar el PDF ni añadir historial.

Criterios de cierre: apertura inicial con un conjunto reducido de controles; acceso claro a cada función desde su área o búsqueda; área activa visible; navegación por teclado y foco coherentes; propiedades pertinentes; pruebas en distintos tamaños de ventana y regresión de edición, proyectos, recuperación y exportación. Mantener las prioridades funcionales de fuentes/reflujo y formularios después de esta reorganización.

## Entregas: preferencia vigente del usuario (20 de octubre de 2026)

No generar nuevos portables al cerrar cada incremento. Cuando el programa esté listo para la prueba personal, entregar un ejecutable propio con logo de inicio y ventana de escritorio; mantener esta entrega pospuesta durante el desarrollo. Mantener los avances en código, pruebas y documentación. Reservar la entrega para pruebas personales hasta tener el alcance previsto casi completo; entonces preparar un programa ejecutable para Windows, con arranque directo y dependencias incluidas, y verificarlo en Windows. Los paquetes antiguos permanecen como antecedentes; no representan automáticamente la última versión del código. Esta indicación prevalece sobre los órdenes de empaquetado de los incrementos históricos siguientes.


| Hito | Entrega | Criterio para cerrarlo | Estado |
|---|---|---|---|
| 0 | Matriz funcional y casos de referencia | Cada capacidad tiene alcance, prueba y evidencia oficial de referencia | Matriz inicial creada; contraste oficial pendiente |
| 1 | Prueba del motor y estructura reproducible | Abrir, editar contenido real, anotar, exportar y comprobar resultados | Prototipo funcional; decisión de motor definitiva pendiente |
| 2 | Visor completo y organización de páginas | Búsqueda, selección, miniaturas, marcadores, unión, división y organización sin pérdida | Navegación, zoom, búsqueda, selección/copia de texto, miniaturas y edición de marcadores internos compatibles implementadas; duplicación, páginas en blanco, reordenación, rotación, eliminación y extracción implementadas; unión e inserción de rangos implementadas; división por bloques/grupos, reemplazo de bloques y recorte/restauración implementados |
| 3 | Anotaciones completas | Lápiz, figuras, resaltados, notas, sellos, selección, movimiento, borrado y persistencia | Lápiz, líneas, flechas, rectángulos, color, grosor, selección/borrado de marcas de la sesión y deshacer/rehacer implementados; resaltado, subrayado, tachado y notas de sesión añadidos; movimiento y redimensionado de sesión implementados; selección, color, contenido de notas y eliminación de anotaciones preexistentes compatibles añadidos |
| 4 | Texto e imágenes | Edición fiable de fuentes y regiones admitidas, ajuste de cajas y modificación de imágenes | Líneas simples de fuentes base; selección de fuente, tamaño y color implementados; inserción y transformación de imágenes nuevas implementadas; cajas nuevas multilínea, enlaces nuevos y encabezados/pies con numeración por rangos implementados; imágenes existentes directas y bloques de varias líneas con fuente libre incrustada añadidos; fragmentos con fuentes/estilos originales base y TrueType compatibles añadidos; reflujo general y estructuras complejas pendientes |
| 5 | OCR y conversiones | Escaneados buscables, conversión con fidelidad documentada y casos límite | Crear PDF desde PNG/JPEG y exportar páginas a imágenes implementados; OCR español/inglés y TXT; Word con texto/imágenes/tablas compatibles y copia PDF/A-2b verificada; importación Office y fidelidad completa pendientes |
| 6 | Formularios, firmas y seguridad | Pruebas específicas de persistencia, validez y eliminación de contenido | Relleno/creación/eliminación de campos simples, datos JSON, aplanado, cifrado y apertura autorizada implementados; jerarquías compatibles, grupos compartidos/radios, firma visual y censura acotada añadidos; importación/duplicación/reemplazo de árboles compatibles añadidos; firma de aprobación P12/PFX y verificación local añadidas; revocación, TSA, LT/LTA y seguridad avanzada pendientes |
| 7 | Herramientas profesionales | Comparación, optimización, Bates, estándares, accesibilidad y lotes | Comparación, propiedades, compactación, Bates, adjuntos, tablas CSV, lotes y revisión estructural; validación normativa externa y diagnóstico/preparación de accesibilidad añadidos; recetas generales con ocho tareas, biblioteca y CLI añadidas; OCR/Office en recetas, planificación, PDF/X, etiquetado y accesibilidad completos pendientes |
| 8 | Distribución Windows | Instalación limpia, actualización, impresión y recuperación verificadas | Portable x64 ensamblado y verificado estáticamente; proyectos, checkpoint y PDF preparado para impresión probados en Linux; modo ventana experimental implementado; ventana gráfica y ejecución Windows pendientes |
| 9 | Automatizaciones personales | Recetas de registros/planos/RN sobre un motor probado | Pospuesto |

## Próximo incremento

1. Ampliar fuentes/codificaciones y reflujo controlado de texto, con corpus real y comparación independiente de los PDF resultantes.
2. Ampliar tipos/fuentes/selección múltiple de formularios y corpus real; la copia de árboles compatibles queda incorporada en 0.23.
3. Ampliar censura de estructuras complejas/OCR y movimiento/tamaño de anotaciones importadas; conservar límites explícitos y rechazos atómicos.
4. Preparar conversión Office, automatización general, firmas digitales y estándares con criterios de fidelidad verificables.
5. Reservar el ejecutable para pruebas personales hasta un alcance casi completo; validar entonces su arranque y los documentos exportados en Windows y un lector independiente.

Cada incremento debe tener una capacidad demostrable, pruebas positivas y negativas, limitaciones explícitas y un documento exportado verificable. No se considerará terminada una función por tener un botón.

## Evidencia inicial

Pasaron 762 pruebas Python y 63 JavaScript (rangos, geometría, cabeceras de imagen y jerarquía de marcadores), la compilación de interfaz y un recorrido real con Chromium que comprueba el contenido exportado, miniaturas, marcadores, búsqueda actualizada, copia al portapapeles, edición y eliminación de anotaciones preexistentes, organización reversible, recorte/restauración, reemplazo reversible, división en ZIP, extracción, edición posterior al cambio de orden, inserción de rangos y unión completa. Los registros detallados de comandos se encuentran en la conversación de desarrollo. Las pruebas de GitHub Actions y Windows están configuradas o documentadas, pero no ejecutadas desde esta sesión.


## Preferencia de validación del usuario

El usuario no puede instalar software en su PC actual. Continuar el desarrollo y las pruebas en el entorno disponible. La prueba personal y la validación de instalación en Windows se realizarán cuando exista un avance mayor y tenga un equipo apropiado; no dependen del siguiente incremento.

## Seguimiento del avance

Al cerrar cada incremento se actualizará y comunicará el porcentaje global estimado usando los pesos estables de [AVANCE.md](AVANCE.md). La versión 0.6 no significa 60 % de producto terminado.

## Próximos trabajos recomendados tras 0.9

1. Ampliar edición de texto: seleccionar fuentes compatibles, tamaño y color con validación de espacio y fuentes incrustadas.
2. Añadir inserción, posición y tamaño de imágenes, con exportación y conservación de calidad.
3. Guardar y recuperar sesiones pendientes tras interrupción o cierre, sin depender del historial en memoria.

Seguir completando movimiento/tamaño de marcas importadas y corpus de anotaciones. Cada cierre de avance debe comunicar lo implementado, validaciones, porcentaje global y los siguientes trabajos recomendados.

## Próximos trabajos tras 0.10

1. Validar el portable en Windows; el flujo preparado permite comprobar el intérprete incluido y el recorrido HTTP de abrir/editar/exportar. En este entorno no se ejecutó Windows.
2. Insertar, mover, redimensionar y eliminar imágenes con historial y exportación.
3. Guardar y recuperar sesiones pendientes tras interrupción o cierre.
4. Ampliar texto a fuentes incrustadas y párrafos, usando un corpus real; las 12 variantes base no equivalen a edición universal.

## Incremento 0.11: claridad y precisión

Renderizado según zoom y densidad, ajuste al ancho/página, vista estable durante la actualización, herramientas agrupadas, guía contextual y control de borradores antes de exportar. Marcado de palabras por clic o arrastre horizontal. Validación de interfaz en densidad 2 y escalas rápidas, además de los recorridos anteriores. Detalles y límites en USABILIDAD.md.

Próximo orden: validar el portable actualizado con documentos reales, editar imágenes con calidad conservada y recuperar sesiones. El renderizado por regiones para planos grandes queda pendiente.

## Incremento 0.12: imágenes nuevas

Inserción PNG/JPEG con píxeles originales, posición y tamaño por ratón/teclado/valores, eliminación e historial. Pruebas con páginas giradas y recortadas, transparencia y JPEG conservado; recorrido Chromium comprueba el PDF exportado. Alcance en IMAGENES.md.

Siguiente bloque: guardar y recuperar sesiones. Después, validar Windows y desarrollar una ventana propia según ESCRITORIO.md; edición de imágenes existentes y texto complejo continúan pendientes.

## Incremento amplio 0.13

Cinco capacidades en cuatro bloques: guardar/abrir proyectos editables y recuperar checkpoint persistente, duplicar páginas con ediciones, insertar hojas en blanco y preparar el PDF para impresión con Ctrl+P. Ctrl+S guarda proyecto. Evidencia y limitaciones en SESIONES.md, PAGINAS_NUEVAS.md e IMPRESION.md.

Los checkpoints se escriben atómicamente y usan revisión/bloqueo del sistema para rechazar escritores antiguos. Chromium prueba recuperación tras reinicio del servidor y fallo de almacenamiento con proyecto alternativo. Los proyectos no incluyen borradores ni todo el historial.

Siguiente bloque amplio recomendado: prototipo de ventana propia y validación Windows, creación de texto nuevo y mejoras de revisión (sellos/enlaces). Las funciones de motor complejas, imágenes existentes, párrafos y OCR mantienen hitos y corpus específicos. Mantener avances con varias capacidades relacionadas, comprobando sus interacciones, y comunicar porcentaje y próximos trabajos al cierre.

## Incremento amplio 0.14

Cajas de texto nuevo con varias líneas y 12 fuentes base, tamaño/color/alineación y controles de área; cuatro sellos estándar nativos en hojas a 0°; enlaces HTTP/HTTPS o a páginas con interacción en Lectura. Historial, proyectos, recuperación y exportación integrados. Selección y marcado de texto sobre los ejes, incluido contenido nuevo en hojas giradas. Véase CONTENIDO_NUEVO.md.

El portable intenta abrir una ventana de Edge/Chrome con perfil exclusivo y cierra su motor al terminar ese proceso; dispone de alternativa de navegador normal. El modo es experimental y las pruebas de detección/procesos/cierre son controladas desde Linux; Windows gráfico sigue pendiente. Véase ESCRITORIO.md.

Próximo bloque amplio recomendado: edición de marcadores, encabezados/pies y numeración de páginas. Mantener el trabajo de validación Windows del modo ventana y lectores externos; ampliar imágenes preexistentes, párrafos y OCR en bloques propios.


## Incremento amplio 0.15

Índice editable con creación/borrado, destinos, estilos, jerarquía y movimientos de ramas completas. Encabezados y pies en seis posiciones con fuente/tamaño/color, márgenes y rangos; numeración decimal con ceros o romana; variables de posición, total y secuencia. Vista previa validada obligatoria, ampliación de muestra y edición/remoción de configuración sin duplicación. Historial, proyectos, recuperación, impresión y exportación integrados. Detalles y límites en MARCADORES_Y_ENCABEZADOS.md.

Se corrigieron los destinos de índice en hojas giradas/recortadas, el redondeo en alineación derecha y la altura necesaria para las 12 fuentes base. Los índices con acciones o destinos especiales permanecen protegidos para lectura. No hay reflujo de cuerpo, Bates ni actualización automática después de consolidar con operaciones de páginas.

Siguiente bloque recomendado: rellenar formularios existentes compatibles, crear PDF desde imágenes y exportar páginas a imágenes. Persistencia y apariencias de campos requieren pruebas específicas; no equivalen a creación de formularios, XFA, firmas digitales o cálculos. Continuar después imágenes existentes, párrafos/fuentes incrustadas y OCR, con validación Windows y lectores externos cuando sea posible.


## Incremento amplio 0.16

Relleno de texto, casillas y listas compatibles, con vista previa, control de espacio y caracteres, permisos, historial, proyectos y recuperación. Valores y apariencias persisten como campos editables. Vaciado real sin conservar el valor anterior; rótulos de listas visibles con códigos de exportación separados. Se protegen campos de solo lectura, scripts/cálculos, XFA, radio y estructuras compartidas o jerárquicas. Guía: FORMULARIOS.md.

Creación desde PNG/JPEG ordenados, papel/márgenes y tamaño según resolución, sin reducir los píxeles originales. Exportación de páginas editadas a PNG/JPEG en ZIP con rangos, orden, resolución y calidad. Se comprueban permisos y límites antes de rasterizar; no se reduce resolución de forma oculta. Guía: CONVERSIONES.md. Portable actualizado con formulario sintético y autoprueba de las tres capacidades.

Siguiente bloque recomendado: importar/exportar datos de formulario y aplanar expresamente, con verificación de apariencias; OCR inicial con idiomas elegidos, texto buscable y revisión de resultados, incluyendo dependencias y empaquetado. Formularios avanzados, imágenes existentes, párrafos/fuentes incrustadas y conversión Office siguen requiriendo bloques propios. Validación Windows y lectores externos pendiente.


## Incremento largo 0.17 y objetivo 70 %

Se amplió el bloque previsto con OCR real local e idiomas incluidos, TXT, datos JSON y aplanado, creación/eliminación de campos, cifrado/apertura, marcas de agua, propiedades, optimización, comparación de dos PDF, imágenes existentes y reemplazo de bloques digitales con fuente libre incrustada. Las operaciones de documento usan versiones reversibles; las descargas no alteran el original. Se conserva el cifrado/permisos de archivos restringidos que no se descifraron expresamente. Guía y límites: AVANCE_LARGO_017.md.

El seguimiento global pasa de 42 a 61 % con los pesos estables. No se declara alcanzado el 70 %. Para cerrar el tramo siguiente se priorizan jerarquías/radios de formularios, censura/saneamiento verificable, Bates/lotes y adjuntos/etiquetas, movimiento de anotaciones importadas, conservación de tipografías y validación Windows/corpus real. No deben asignarse puntos por botones sin flujo exportable o por funciones que todavía carecen de validación.

La disponibilidad de código y pruebas Linux no equivale a ejecución Windows. El portable incluye idiomas OCR y fuente con licencias; autoprueba preparada para el equipo objetivo. No hay evidencia nueva de instalación o ejecución gráfica Windows desde este entorno.


## Incremento largo 0.18 — cierre del tramo estimado al 70 %

Bates entre varios PDF con secuencia continua, manifiesto y validación atómica; etiquetas nativas Unicode y navegación; adjuntos con descargas y descompresión limitada; tablas CSV revisables; movimiento numérico de notas/rectángulos importados; firma manuscrita vectorial; censura de regiones en copia con saneamiento y comprobaciones de recursos; giro manual OCR que conserva píxeles. Guía: AVANCE_LARGO_018.md.

La estimación llega al 70 % con los pesos previos y crédito parcial por estructuras limitadas. No hay firmas digitales ni equivalencia completa con Acrobat. Las jerarquías, campos compartidos y radios de formulario se posponen hasta verificar valores/apariencias en lectores externos. Siguiente secuencia: formularios avanzados; ampliar censura/corpus; fuentes/estilos y objetos complejos; Office/automatización; firmas digitales y estándares. Mantener la validación real Windows como pendiente explícito.


## Incremento 0.19 — formularios avanzados compatibles

Valida el árbol y su propiedad lógica; sincroniza texto/casillas compartidos y radios exclusivos; conserva valores y apariencias al exportar, importar datos, guardar proyecto y aplanar. Añade diseño y eliminación de grupos, ejemplo de dos páginas, selección de la página correspondiente y limpieza de valores cuando una opción desaparece por extracción. La importación/duplicación de un origen jerárquico se bloquea: el motor de copia no conserva todavía su árbol correctamente. Un PDF plano se puede insertar en el documento original conservando sus grupos.

Estimación global: 71,5 puntos ponderados, comunicados como aproximadamente 72 % ±5 puntos, con los mismos pesos. Solo sube el área de formularios/firmas/seguridad; no se da crédito por firmas digitales ni por distribución Windows. Guía: FORMULARIOS_AVANZADOS.md. Siguiente bloque: fuentes/estilos originales y árboles importados, con corpus real y validación Windows.


## Incremento 0.20 — fuentes originales por fragmentos

Modo adicional en Reemplazar bloque de texto para conservar fuente, tamaño, color RGB y línea base, con varias familias/estilos. Reutiliza recursos base y TrueType Identity-H, valida contornos de subconjuntos y bloquea caracteres ausentes; controla ancho y colisiones, permite expansión explícita dentro del área y exige vista previa. Se separan recursos compartidos antes de retirar texto; proyectos, recuperación y versiones reversibles integrados. Guía: TEXTO_CON_ESTILOS.md.

988 pruebas Python y 63 JavaScript, recorrido completo de Chromium y contraste de texto/apariencia con Poppler. Nuevo ejemplo público y autoprueba portable. Total ponderado: 72,5 ≈73 % ±5 puntos con los pesos anteriores; solo sube edición, de 70 a 75 % de cobertura. No se da crédito por reflujo general, todas las fuentes o ejecución Windows. Siguiente trabajo: tipografías/estructuras complejas, reflujo y copia de árboles de formularios.

## Incremento 0.21 — espacio de trabajo y control estructural

Catálogo único con búsqueda por tareas, categorías y favoritos; paleta de comandos con navegación de teclado y motivos de indisponibilidad; guía, atajos, salto por página física y vista de lectura ampliada. Protección de borradores frente a navegación, cambio de herramienta e historial; atajos respetan campos de texto y diálogos. Revisión de la copia por lotes de 20 páginas, filtros, enlaces a páginas e informe JSON sin contenido extraído. Ejemplo público reapdf-recorrido.pdf.

1004 pruebas Python y 76 JavaScript. Se mantiene el recorrido completo de Chromium y se añaden pruebas de teclado, preferencias, informe, recuperación y ventanas de varios tamaños. Total ponderado: 73,5 ≈74 % ±5, con pesos estables y sin atribuir ejecución Windows. Próximos: fuentes/reflujo, importación de árboles de formulario y corpus real de documentos.

## Incremento 0.22 — distribución de funciones por áreas

Apertura en Leer con cinco herramientas; siete áreas con catálogo específico y descripciones; propiedades contextuales, paneles plegables y dimensiones visibles en el visor. Búsqueda/comandos y favoritos siguen siendo globales y abren el área correspondiente. Cambiar de área vuelve el lienzo a lectura sin modificar PDF ni historial; los borradores y gestos bloquean esa transición. Flechas/Inicio/Fin y asociación accesible de pestañas/panel. Los asistentes de varias etapas mantienen diálogos dedicados.

Verificación 0.22: 1004 pruebas Python, 78 JavaScript, compilación y recorrido completo de Chromium aprobados en Linux. Estimación sin cambio: 73,5 ≈74 % ±5 puntos; no se añaden nuevas capacidades de motor. No generar portables. Siguientes prioridades: fuentes/codificaciones y reflujo, importación de árboles de formulario, corpus real y posteriormente ejecutable Windows.

## Incremento 0.23 — copiar formularios con grupos independientes

Reconstrucción por identidad del árbol AcroForm importado, incluidos padres clonados varias veces, jerarquías mixtas y nombres Unicode. Unir/insertar, duplicar y reemplazar conservan valores, propiedades y flujos de apariencia compatibles; se verifica el árbol y los atributos después de reabrir. Los nombres raíz en conflicto reciben sufijos. Se protege el árbol antes de seleccionar páginas y se corrigen escrituras sobre diccionarios AcroForm indirectos. Se mantienen rechazos de firma, capas, XFA, cálculos/scripts y límites.

Validación: 1058 pruebas Python y 78 JavaScript, compilación y recorrido completo de Chromium aprobados; contraste independiente con Poppler. La cobertura del área de formularios pasa de 75 a 80 %; total ponderado 74,25 ≈74 % ±5 puntos. No se generan portables ni ejecutables durante este avance. Siguiente trabajo: fuentes/codificaciones y reflujo, después formularios más amplios y censura de estructuras complejas.

## Incremento 0.24 — párrafos, formato y selección visual

Selección de hasta 100 bloques digitales detectados por página, tanto con lista como sobre la imagen o con teclado. Doce variantes DejaVu (Sans/Serif/Mono × regular/negrita/cursiva/negrita cursiva), color e interlineado. Unión explícita de líneas con conservación de líneas en blanco; ajuste de tamaño opcional, mínimo elegido e informe del tamaño real. Vista previa obligatoria y renovación al cambiar cualquier ajuste. Editor con controles y página en columnas en pantallas amplias. Recursos de fuente separados antes de editar para conservar otras páginas que los compartan.

Siguientes trabajos recomendados: ampliar la edición conservando fuentes originales y sus codificaciones; edición de texto en páginas giradas; después ampliar formularios y validar documentos reales complejos. El reflujo entre páginas, la composición tipográfica de escrituras complejas y las conversiones Office siguen pendientes. La entrega Windows con ventana propia, logo e inicio queda para la etapa de distribución.

Validación del cierre 0.24: **1094 pruebas Python y 78 JavaScript aprobadas (1172 en total)**, compilación de producción y recorrido completo de Chromium aprobados. Comprobación adicional aprobada del editor a 390 px de ancho, proyecto guardado y recuperación de sesión; verificación de texto/píxeles con Poppler. Estas comprobaciones no acreditan ejecución Windows ni equivalencia completa con Acrobat.

## Incremento 0.25 — editar páginas giradas sin cambiar su orientación final

El editor de bloques muestra una vista enderezada de las páginas con giro de 90°, 180° y 270°. Detección, coordenadas, arrastre y vista previa usan el mismo CropBox nativo; aplicar conserva el giro original, sin rasterizar el contenido. Los dos modos, redistribución de párrafos y conservación de fuentes, comparten este contrato. Se añaden formato inicial sugerido del primer fragmento, aviso de formatos mezclados y comparación con el original.

La cobertura de edición pasa a 80 % considerando conjuntamente 0.24 y 0.25; total ponderado 75,25 ≈75 % ±5 puntos. Siguientes trabajos: ampliar codificaciones de fuentes originales, mejorar la selección de texto complejo y ampliar formularios con validación en documentos representativos. Reflujo entre páginas, Office y firmas con certificados siguen pendientes. La entrega con ventana propia, logo y ejecutable Windows permanece en la etapa de distribución; no se generan portables en este avance.

Validación del cierre 0.25: **1133 pruebas Python y 78 JavaScript aprobadas (1211 en total)**, compilación de producción y recorrido completo en Chromium aprobados. Incluye los tres giros y ambos modos, conservación de fuentes y recortes, comparación, historial/proyecto/recuperación y contraste independiente con Poppler. No se genera un nuevo portable ni se declara validada la ejecución Windows.

## Incremento amplio 0.26 — enlaces, formularios, marcas y lotes

Cuatro frentes cerrados en código: editar/eliminar enlaces web e internos existentes con vista previa obligatoria; configurar campos nuevos (fuente, tamaño, colores, borde/fondo, descripción, obligatoriedad, límite y valor inicial); mover/redimensionar rectángulos y elipses estándar importados; procesar lotes de optimización, extracción TXT o copias AES-256 con revisión y manifiesto. No se genera un nuevo portable. Guía: AVANCE_AMPLIO_026.md.

Estimación: 78,5 puntos ponderados, aproximadamente 79 % ±5. Los siguientes trabajos recomendados son ampliar fuentes y geometrías de campos existentes, anotaciones con otras geometrías y comentarios, edición/censura de estructuras complejas y conversiones Office. Antes de declarar 90 %, validar también los pendientes mayores de firmas/estándares y la aplicación ejecutable Windows con logo y ventana propia. No se reasignan pesos para adelantar el porcentaje.

Validación del cierre 0.26: **1231 pruebas Python y 80 JavaScript aprobadas (1311 en total)**, compilación de producción y recorrido completo en Chromium aprobados. Los recorridos descargan y comprueban PDF, proyectos y ZIP de las tres tareas, además de historial y recuperación. Hay contraste independiente de texto y apariencia con Poppler. Windows nativo y lector comercial siguen pendientes.

## Incremento amplio 0.27 — campos existentes, conversaciones y Word

Completados los asistentes de propiedades de campos existentes (geometría individual y propiedades compartidas, vista previa y valores conservados), comentarios con respuestas/estados nativos e informes CSV/JSON, y exportación DOCX de texto digital con revisión de pérdidas. Guía: [AVANCE_AMPLIO_027.md](AVANCE_AMPLIO_027.md).

Estimación: 81,75 ≈82 % ±5 con los mismos pesos. Próximo bloque recomendado: Word con imágenes/tablas y corpus, ampliación conservadora de formularios y contraste con lectores externos. Firmas con certificados, estándares/accesibilidad y ejecutable Windows mantienen criterios propios antes de declarar un 95 %. No se genera portable en este corte.

Validación del cierre 0.27: **1302 pruebas Python y 83 JavaScript aprobadas (1385 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Se comprueban campos con giros/recorte y grupos, valores y apariencias, respuestas/estados nativos e informes, DOCX y lectura independiente con python-docx, historial/proyectos/recuperación y las funciones anteriores. Poppler contrasta texto y apariencia; un estado de revisión oculto no cambia los píxeles de la página. La apariencia en Word/LibreOffice, lectores comerciales y ejecución Windows nativa sigue pendiente. No se generaron nuevos portables.

## Incremento amplio 0.28 — Word ilustrado y formularios existentes

Completadas imágenes compatibles y tablas rectangulares editables en DOCX, revisión de celdas/omisiones y presupuestos; renombrado de campos lógicos conservando jerarquías/grupos; opciones de listas con valores y etiquetas, reordenación e índices, conservación del valor actual y de restablecimiento. Guía: [AVANCE_AMPLIO_028.md](AVANCE_AMPLIO_028.md).

Estimación: 83,25 ≈83 % ±5, con los mismos pesos y crédito parcial para conversión. Próximos trabajos: corpus real y lectores externos, firmas con certificados, estándares/accesibilidad y validación del ejecutable Windows. No se generan nuevos portables.

Validación del cierre 0.28: **1357 pruebas Python y 83 JavaScript aprobadas (1440 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Tras los últimos ajustes de presentación se repitió el recorrido específico: imágenes/tablas, revisión de omisiones, nombres/opciones/reordenación, historial, proyecto y recuperación. Se comprueba lectura independiente con python-docx, máscaras alfa reales, JPEG sin recodificar, cuatro giros y recorte, tablas combinadas protegidas y conservación de valores actuales/de restablecimiento. La apariencia en Microsoft Word/LibreOffice, lectores comerciales y ejecución Windows nativa sigue pendiente. No se generó otro portable.

## Incremento amplio 0.29 — certificados y firmas digitales

Implementados inspección de P12/PFX y restricciones de uso/vigencia/clave, firma SHA-256 en copia con marca opcional, firma sucesiva incremental, verificación separada de integridad/cobertura/confianza explícita e informes JSON. Se conservan bytes firmados en proyecto/recuperación. La revisión de documento enlaza al verificador. Guía: [FIRMAS_DIGITALES.md](FIRMAS_DIGITALES.md).

Estimación 84 % ±5 con los mismos pesos: +0,75 puntos en formularios/firmas/seguridad. Revocación, TSA, LT/LTA, tokens y validación Windows no se dan por implementados. Próximos trabajos: corpus/lectores externos, revocación y tiempo con proveedores configurables, estándares/accesibilidad y ejecutable Windows con validación real. No se genera portable.

Validación del cierre 0.29: **1396 pruebas Python y 84 JavaScript aprobadas (1480 en total)**, compilación de producción y recorrido completo en Chromium aprobados en Linux. El recorrido incluye firma visible, limpieza de credenciales del asistente, verificación sin confianza y con confianza explícita, informes, segunda firma, proyecto/recuperación con bytes intactos y detección de alteración, además de todos los flujos anteriores. Poppler pdfsig verifica independientemente la firma generada. Las 40 dependencias Windows se descargaron y validaron con hashes; no se ejecutó Windows ni se generó un nuevo portable. Revocación, TSA y LT/LTA siguen pendientes.

## Incremento amplio 0.30 — estándares y accesibilidad

Implementados perfiles PDF/A-1b/2b/3b y PDF/UA-1 con veraPDF, filtros e informes de reglas; copia PDF/A-2b con validación independiente, texto/tamaños conservados y comparación de la primera página; diagnóstico orientativo de accesibilidad y título/idioma/XMP/preferencia de visor editables con historial. Guía: [ESTANDARES_Y_ACCESIBILIDAD.md](ESTANDARES_Y_ACCESIBILIDAD.md).

Estimación 85,75 ≈86 % ±5 con pesos estables. No se cuentan etiquetado completo, PDF/X, orden semántico, revisión manual asistida o ejecución Windows. Siguientes trabajos: etiquetas/orden de lectura con corpus, lectores externos y tecnologías de asistencia; ampliar edición/censura/conversión; validación avanzada de firmas; ejecutable Windows cuando cumpla criterios. No se genera otro portable.

Validación del cierre 0.30: **1451 pruebas Python y 85 JavaScript aprobadas (1536 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Las 55 pruebas nuevas del motor cubren veraPDF real, PDF/A conforme y PDF/UA no conforme, perfiles/informes consistentes, límites/timeouts, bloqueo de estructuras protegidas, giros/recortes, Unicode/transparencia, XMP y etiquetas. Chromium verifica navegación por observaciones, título/idioma con historial, filtros de reglas, ampliación/comparación, PDF/A e informe con huella de los bytes descargados, proyecto/recuperación y los flujos anteriores. Java 21/Ghostscript 10.05.1/veraPDF 1.30.3 se probaron aquí; ejecución Windows, lectores comerciales y revisión manual con tecnologías de asistencia siguen pendientes. No se generó otro portable.

## Incremento 0.31 — selección y censura revisable

Selección de fragmentos por caracteres con vista durante el arrastre, compactación de vértices y exportación nativa; censura manual multipágina con eliminación individual de regiones; búsqueda literal y sugerencias de correos con selección explícita; inspecciones vinculadas al documento y revisión de todas las páginas antes de descargar. Guía y límites: [SELECCION_Y_CENSURA.md](SELECCION_Y_CENSURA.md).

La estimación se mantiene en 85,75 ≈86 % ±5: este incremento profundiza las capacidades de anotación y censura ya incluidas en la cobertura. No se contabiliza dos veces como una familia nueva, ni se aumenta distribución sin ejecutar Windows. Siguientes trabajos: ampliar movimiento/tamaño de geometrías importadas, corpus de edición y censura compleja/OCR, accesibilidad semántica y validación independiente; reservar el ejecutable para la entrega prevista.

Validación del cierre 0.31: **1502 pruebas Python y 90 JavaScript aprobadas (1592 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Se añaden 51 pruebas Python y 5 JavaScript para selección parcial, vértices de tres tipos de marca en cuatro giros, búsqueda/censura selectiva con giros y recortes, Unicode, conservación de contenido no seleccionado, permisos, límites y rechazo de inspecciones/identificadores inválidos. Chromium verifica el arrastre visible, anotaciones nativas descargadas, historial, búsquedas sin selección automática, revisión de todas las páginas, invalidación de revisiones, censura manual multipágina y regiones eliminables. Poppler comprueba de forma independiente la extracción del PDF censurado. Se revisaron capturas de la interfaz. Windows, lectores comerciales y censura universal siguen pendientes. El portable 0.20 conserva su huella y no se generó otro paquete.

## Incremento 0.32 — interfaz profesional y geometrías importadas

Siete áreas con secciones plegables por tarea, filas compactas e iconos, descripciones opcionales persistentes, barra de visualización simplificada y estilo común de superficies/texto/controles. Títulos de asistentes fijos y adaptación a cuatro anchos. Se mantienen búsqueda, favoritos, teclado y protección de borradores. Movimiento de trazos y líneas/flechas importados compatibles con vértices y apariencias nativas conservados, incluidas páginas giradas/recortadas.

Estimación conservada: 85,75 ≈86 % ±5. Siguientes trabajos: ampliar geometrías importadas con redimensionado/tiradores y corpus de fabricantes; revisar los asistentes complejos por pasos y comparación; ampliar edición de texto compleja y accesibilidad semántica; validar el ejecutable en Windows cuando corresponda la entrega. Guía: [INTERFAZ_PROFESIONAL.md](INTERFAZ_PROFESIONAL.md).

Validación del cierre 0.32: **1548 pruebas Python y 91 JavaScript aprobadas (1639 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Las 46 pruebas nuevas del motor cubren traslado de Ink/Line con cuatro giros y recortes, vértices/apariencias nativas/píxeles y propiedades conservados, cambios combinados de color y geometría, permisos, firmas, propiedades especiales y tamaños/posiciones inválidos. La prueba adicional del catálogo exige que las 56 herramientas estén distribuidas exactamente una vez en sus secciones. Chromium comprueba secciones plegables por teclado/ratón, ayuda persistente, contraste representativo de al menos 4,5:1, borradores, búsqueda/favoritos, títulos fijos, movimiento de lápiz/flecha con historial/exportación/recuperación y anchos de 600/900/1100/1440 px, además de los recorridos anteriores. Se inspeccionaron capturas de la interfaz. Windows y lectores comerciales siguen pendientes. No se generó otro portable; el paquete 0.20 conserva su huella anterior.

## Incremento 0.33 — cierre de tiradores y tamaño importado

Añadidos: tamaño de Ink/Line nativos, tiradores de movimiento/tamaño sobre la página, guía, cancelación, teclado y selección conservada en deshacer/rehacer; coordenadas basadas en vértices y compatibilidad de proyectos anteriores. La apariencia se contrasta antes de regenerar y el borde/puntas deben quedar dentro de página. Esto cierra el subtrabajo anunciado tras 0.32 y no vuelve a presentar el movimiento numérico o el estilo visual como nuevas funciones.

Estimación conservada: 85,75 ≈86 % ±5. Próximos trabajos distintos: edición por extremos individuales de líneas/flechas para cambiar dirección, selección múltiple/alineación de marcas y validación de corpus externo; el ejecutable Windows continúa reservado a la entrega prevista. Guía: [TIRADORES_IMPORTADOS.md](TIRADORES_IMPORTADOS.md).

Validación del cierre 0.33: **1596 pruebas Python y 94 JavaScript aprobadas (1690 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Se añaden 48 pruebas Python y 3 JavaScript: escala de vértices con cuatro giros/recortes, estilos y puntas conservados, dimensiones cero y líneas casi horizontales, movimiento con apariencia intacta, combinación con color, límites, apariencia personalizada rechazada, API, proyectos y compatibilidad de geometría anterior. Poppler comprueba de forma independiente la representación de una flecha redimensionada y el texto conservado. Chromium verifica los tiradores al 75 % de zoom, guía, Escape, teclado, borradores, historial con selección conservada, exportación, proyectos/recuperación y líneas horizontales, junto a los flujos anteriores. Después del ajuste final para evitar un marco de selección duplicado, se repitió y aprobó el recorrido específico de los tiradores en los cuatro giros. Se inspeccionó su captura. Windows, lectores comerciales, extremos individuales y selección múltiple siguen pendientes. No se generó otro portable; el paquete 0.20 conserva su huella anterior.

## Incremento amplio 0.34 — extremos y operaciones sobre varias marcas

Cerrados: extremos individuales de Line, selección múltiple de anotaciones existentes compatibles, seis alineaciones con dos referencias, dos distribuciones, movimiento/color/borrado conjuntos con historial, protección de borradores y fidelidad al recolorear. Compresión RGB/gris con DPI/calidad y comparación, texto/geometría contrastados e informe de la copia; carga modular de firmas/estándares/accesibilidad y registro local de validación con hashes y criterios pendientes.

Creación/conversión/OCR pasa de 80 a 85 % (+0,75 global); pesos y otras áreas se conservan: 86,5 ≈87 % ±5. Para avanzar hacia el cierre hay que abordar familias que aún faltan: compresión de imágenes complejas y corpus, texto/Office complejo, formularios avanzados y accesibilidad semántica; después, corpus e interoperabilidad y prueba Windows. La auditoría no permite declarar 1.0 por completar solo las pruebas Linux. Guía: [AVANCE_AMPLIO_034.md](AVANCE_AMPLIO_034.md).

## Incremento amplio 0.35 — recetas y compresión ampliada

Se implementan recetas generales en cuatro etapas con ocho tareas ordenables, biblioteca local, intercambio JSON sin contraseñas, nombres de salida, revisión y manifiestos por paso. La misma receta se ejecuta por consola sin servidor. La compresión añade CMYK con perfil conservado y recursos de imagen en Form XObjects anidados; pruebas de color, recursos compartidos, giros y recortes.

Creación/conversión/OCR pasa de 85 a 90 % (+0,75 global); herramientas profesionales/automatización pasa de 85 a 90 % (+0,5 global). Pesos y demás áreas se conservan: 87,75 ≈88 % ±5. No hay crédito por ejecución Windows, importación Office, OCR automático de recetas ni paridad universal. La próxima secuencia aborda texto/reflujo y Office complejos, formularios/accesibilidad y corpus/Windows. Guía: [AVANCE_AMPLIO_035.md](AVANCE_AMPLIO_035.md).

## Incremento amplio 0.36 — flujo de texto, cálculos y Word

Se añaden flujo explícito entre hasta ocho regiones de páginas existentes, formato común, ajuste uniforme, comparación de todas las páginas y aplicación reversible completa. Los campos compatibles admiten cinco cálculos decimales puntuales con revisión y valores persistentes. Word incorpora enlaces HTTP/HTTPS completos y avisa de enlaces parciales o no compatibles.

Edición pasa de 85 a 90 % (+1 punto global); demás áreas y pesos permanecen iguales: 88,75 ≈89 % ±5. No se cuenta reflujo general automático, fórmulas nativas, importación Office ni Windows. Próxima secuencia: importación DOCX con validación, reflujo de formato mixto/estructuras, formularios automáticos y accesibilidad; corpus y prueba Windows. Guía: [AVANCE_AMPLIO_036.md](AVANCE_AMPLIO_036.md).

## Incremento amplio 0.37 — Word entrante, reglas y Word por recetas

Se implementa DOCX compatible a PDF editable con revisión de todas las páginas, informe y límites explícitos. Se añaden reglas declarativas con dependencias y ciclos comprobados, recalculadas dentro de proyectos Reapdf; las exportaciones PDF contienen valores y los cambios estructurales consolidan esas reglas. Word se añade como salida terminal de recetas, con informe de contenido y omisiones.

Creación/conversión/OCR pasa de 90 a 95 % (+0,75 global); demás áreas y pesos se mantienen: 89,5 ≈90 % ±5. No se contabiliza Office universal, fórmulas nativas entre lectores ni ejecución Windows. Próximos bloques: estilos/listas/encabezados de DOCX y corpus; remapeo de reglas entre versiones; reflujo de formato mixto, accesibilidad y Windows. Guía: [AVANCE_AMPLIO_037.md](AVANCE_AMPLIO_037.md).

## Incremento 0.38: estilos/listas Word y reglas al organizar

Implementado: herencia acotada de estilos de párrafo/carácter, formato directo prioritario, espaciado/sangrías y numeración multinivel compatible; conteos y avisos en revisión. Organizar páginas conserva reglas de proyecto con remapeo validado; eliminar un campo necesario rechaza el cambio completo. Pruebas de renderizado, grupos compartidos, edición posterior, proyectos y recuperación. Guía: [AVANCE_AMPLIO_038.md](AVANCE_AMPLIO_038.md).

Pendientes siguientes: remapeo en inserción/reemplazo y cambios de campos; encabezados/pies y corpus Office real; formato mixto y conservación semántica; ejecución Windows antes del entregable personal.

## Incremento 0.39: continuidad entre herramientas y encabezados Word

Implementado: remapeo validado de reglas al insertar/reemplazar/duplicar/añadir hojas/recortar y renombrar/cambiar propiedades/crear/eliminar campos compatibles, con copias independientes y bloqueo de dependencias eliminadas. Word incorpora encabezados/pies internos, variantes de portada/pares, campos simples PAGE/NUMPAGES, reserva de espacio y revisión completa/ampliada. Guía: [AVANCE_AMPLIO_039.md](AVANCE_AMPLIO_039.md).

Siguientes bloques: formato mixto entre regiones; secciones/campos complejos Word y corpus; interoperabilidad de fórmulas y firmas avanzadas; validación del ejecutable propio en Windows antes de su entrega.

## Incremento 0.40: cerrar reflujo mixto compatible

Implementado y verificado: lectura de estilos y texto en fragmentos, edición/separación de selección, distribución multipágina con negrita/cursiva/tamaño/color y fuentes incluidas, ajuste proporcional y comprobación de contenido/límites, comparación y persistencia del resultado. Cinco criterios cerrados, con límites explícitos: [REFLUJO_MIXTO.md](REFLUJO_MIXTO.md).

El porcentaje previo queda como referencia histórica, no como medición auditada. Seguimiento vigente: [ESTADO_FUNCIONAL.md](ESTADO_FUNCIONAL.md). Siguiente hito concreto: campos Word PAGE/NUMPAGES complejos; fuentes originales exactas y semántica son ampliaciones distintas del bloque cerrado.

## Incremento 0.41: varios entregables de Word

Cerrados en alcance compatible: campos PAGE/NUMPAGES complejos, numeración de sección con formatos/inicio, etiquetas PDF, combinaciones rectangulares de tablas e informe/revisión integrados. Incluye resultados guardados para campos no admitidos, rechazo de campos incompletos y conservación del documento abierto. Evidencia y límites: [WORD_CAMPOS_TABLAS_041.md](WORD_CAMPOS_TABLAS_041.md).

Siguiente hito distinto: secciones Word con papel/orientación/márgenes y encabezados propios; los campos complejos de página y combinaciones compatibles ya no son pendientes genéricos. Seguimiento: [ESTADO_FUNCIONAL.md](ESTADO_FUNCIONAL.md).

## Incremento 0.42

Secciones Word con salto a página siguiente: papel/orientación/márgenes propios, encabezados/pies vinculados por variante, continuidad/reinicio y etiquetas PDF, totales globales y SECTIONPAGES. Saltos manuales de página reales y resumen plegable por sección, con exportación/proyecto/recuperación. Guía: [WORD_SECCIONES_042.md](WORD_SECCIONES_042.md).

Siguiente bloque recomendado: grupos persistentes de anotaciones. Después, cálculos nativos interoperables y validación del ejecutable propio en Windows. Las secciones compatibles ya no se presentan como trabajo sin empezar.

## Solicitud vigente: ejecutable de prueba y flujos generales

El usuario solicita ahora el avance actual como ejecutable para probarlo antes de los nuevos módulos. Esto sustituye la espera anterior hasta un alcance casi completo; no implica generar un portable en cada incremento. Plan detallado, nombres generales, etapas y criterios: [PLAN_CIERRE_Y_FLUJOS.md](PLAN_CIERRE_Y_FLUJOS.md). Registro/plano, MT/UT y RN son perfiles de uso, no categorías obligatorias del motor ni nuevas funciones ya implementadas.
