> Documento histórico: esta matriz contiene estados antiguos que ya no describen todas las capacidades actuales. Para uso del programa consulta [el manual de funciones](MANUAL_DE_FUNCIONES.md), contrastado con las 73 herramientas del catálogo actual. Para pendientes técnicos consulta [el plan vigente](PLAN_ACTUAL.md). Ninguna guía declara por sí sola un cierre al 100 %.

# Matriz funcional inicial

Referencia aspiracional: Acrobat de escritorio y sus servicios asociados. No constituye una lista exhaustiva ni una comparación actual de planes comerciales. La consulta anterior a páginas oficiales fue bloqueada por la red; queda pendiente verificar versiones, plataformas y disponibilidad por plan.

Estados: **inicial** = implementado con límites y pruebas sintéticas; **pendiente** = no implementado.

| ID | Capacidad | Aceptación prevista | Estado |
|---|---|---|---|
| V01 | Abrir, navegar y zoom | Páginas y orientación visibles, errores comprensibles | Inicial; PDF editado preparado para impresión desde Archivo/Ctrl+P, sin validación física |
| V02 | Búsqueda y selección | Coincidencias y selección alineadas con el texto | Inicial: búsqueda en texto editado y selección/copia nativa; OCR español/inglés disponible; tipografías complejas pendientes |
| V03 | Miniaturas, marcadores y pestañas | Navegación correcta y conservación al guardar | Inicial: miniaturas y edición de marcadores internos compatibles con jerarquía y estilos; destinos especiales en lectura y pestañas de documentos pendientes |
| V04 | Impresión | Escala, márgenes y orientación comprobados en Windows | Inicial: PDF editado en el lector con menú/Ctrl+P; impresora física, Windows y baja resolución pendientes |
| P01 | Unir, dividir, extraer e insertar | Orden y aspecto iguales a fuentes | Inicial: extracción, unión de dos PDF por operación e inserción de rangos; división por bloques o grupos en ZIP |
| P02 | Reordenar, reemplazar, eliminar, rotar y recortar | Sin modificaciones inesperadas en otras páginas | Inicial: duplicar, insertar hojas en blanco, reordenar, eliminar, rotar, reemplazar bloques y recortar/restaurar márgenes; corpus avanzado pendiente |
| A01 | Lápiz, color y grosor | Anotación persistente y coordenadas correctas con zoom/rotación | Inicial |
| A02 | Seleccionar, mover, borrar anotaciones | Solo cambia la anotación elegida | Inicial: seleccionar, mover, redimensionar y borrar marcas de la sesión; anotaciones preexistentes compatibles: selección, color, contenido de notas y borrado; movimiento numérico de notas/rectángulos/elipses importados y cambio de tamaño de rectángulos/elipses estándar; movimiento de trazos/líneas importados compatibles añadido; movimiento de resaltados y otras geometrías importadas sigue pendiente |
| A03 | Resaltar, subrayar, tachar | Geometría alineada con texto, incluso multilínea | Inicial: palabras completas o fragmentos por caracteres, selección visible al arrastrar, texto sobre ejes de página y páginas giradas; texto oblicuo y reflujo de marcas pendientes |
| A04 | Figuras, flechas, notas y sellos | Persisten al reabrir en otro lector | Inicial: líneas, flechas y rectángulos y notas editables en la sesión; cuatro sellos estándar nuevos en hojas a 0°; sellos personalizados y lector externo pendientes |
| A05 | Comentarios, respuestas y exportación | Autor, contenido y vínculo conservados | Inicial: conversaciones nativas, respuestas, estados de revisión e informes JSON/CSV; relaciones especiales protegidas; XFDF/FDF y lector comercial pendientes |
| E01 | Reemplazar texto existente | Texto anterior ausente y resto del contenido conservado | Inicial: líneas simples, tres familias base y sus 12 variantes |
| E02 | Fuente, tamaño, color, alineación y párrafos | Fuentes controladas y desbordamiento visible | Inicial: cajas nuevas con varias líneas y alineación; edición existente con 12 variantes base, tamaño/color y validación de ancho y cruces; bloques digitales seleccionables por detección o región, también en páginas giradas con conservación de giro/recorte, con 12 variantes DejaVu Sans/Serif/Mono incrustadas, color, alineación, interlineado, unión explícita de líneas y ajuste de tamaño con mínimo e informe; conservación de estilos/fuentes compatibles por fragmentos añadida, incluidos subconjuntos TrueType verificables; CFF/Type3, estructuras complejas y reflujo entre páginas pendientes |
| E03 | Imágenes y objetos | Posición, escala y calidad controlables | Inicial: insertar PNG/JPEG, mover/redimensionar/eliminar imágenes nuevas, historial y píxeles originales; mover/reemplazar/eliminar imágenes existentes directas no compartidas añadido; estructuras complejas y objetos generales pendientes |
| E04 | Enlaces, encabezados, pies y marcas de agua | Destinos correctos y alcance de páginas explícito | Inicial: enlaces nuevos HTTP/HTTPS o página con interacción en Lectura; encabezados/pies y numeración decimal/romana por rangos con vista previa; marca de agua vectorial por rangos añadida; modificación de destino/área y eliminación de enlaces existentes HTTP/HTTPS e internos compatibles añadidas |
| H01 | Deshacer/rehacer | Se revierte y restaura el conjunto de operaciones | Inicial: sesión actual, incluidas organización, unión/inserción y ediciones previas |
| H02 | Recuperación y guardado automático | Recuperar trabajo tras interrupción sin dañar fuentes | Inicial: proyectos editables y un checkpoint local del estado aplicado; borradores e historial completo pendientes |
| C01 | Crear desde imágenes y Office | Orden, diseño y áreas de impresión verificados | Inicial: crear desde PNG/JPEG, orden/papel/márgenes y píxeles originales; Office pendiente |
| C02 | Exportar Word, Excel, imágenes y texto | Fidelidad medida por corpus; pérdidas informadas | Inicial: PNG/JPEG de páginas editadas con resolución elegida y ZIP; TXT UTF-8 por rangos; tablas CSV con revisión; DOCX de texto digital con formato básico, imágenes compatibles y tablas rectangulares editables; sin maquetación exacta; Word/Excel completos pendientes |
| O01 | OCR y limpieza de escaneados | Texto buscable alineado y caracteres críticos revisados | Inicial: español/inglés local, texto invisible sin sustituir imagen; omite páginas digitales; corrección manual de giro añadida; orientación automática, limpieza y corpus real pendientes |
| F01 | Rellenar/crear formularios y cálculos | Valores y apariencias consistentes tras reapertura | Inicial: rellenar campos simples existentes de texto, casillas y listas de selección única; valores/apariencias/proyectos; creación/eliminación de campos simples añadida; jerarquías compatibles, texto/casillas compartidos y radios exclusivos añadidos, con diseño/eliminación de grupos; importación/duplicación/reemplazo de árboles compatibles añadidos con validación; XFA, cálculos y estructuras no verificadas pendientes |
| F02 | Importar/exportar datos y aplanar | Campos correctos, cambio de editabilidad explícito | Inicial: JSON vinculado por huella/identidad y aplanado de campos compatibles con historial; XFDF/FDF pendientes |
| S01 | Firma visual | Apariencia y ubicación persistentes | Inicial: dibujo vectorial, posición, vista previa, versión reversible y exportación; sin certificado |
| S02 | Firmas digitales y sellado de tiempo | Validación externa, cadena y estado explicados | Inicial: aprobación SHA-256 P12/PFX, firmas sucesivas, verificación local de integridad/revisiones y confianza explícita con JSON; Poppler verifica la firma generada; revocación, TSA, LT/LTA, tokens y lectores comerciales pendientes |
| S03 | Solicitar firmas | Flujo remoto, identidad y trazabilidad verificados | Pendiente; requiere servicios |
| Q01 | Contraseñas y permisos | Acceso y restricciones comprobados | Inicial: copia AES-256, apertura autorizada y conservación de restricciones en versiones; Windows y firma/cifrado combinados pendientes |
| Q02 | Censura y saneamiento | Texto/imágenes sensibles no recuperables en salida | Inicial acotada: regiones directas y copia saneada comprobadas; bloquea estructuras complejas, formularios, capas e imágenes compartidas; sin certificación forense universal |
| Q03 | Compresión y optimización | Tamaño y calidad comparados | Inicial: compactación sin reducir píxeles; compresión RGB/gris/CMYK y recursos en Form XObjects anidados con DPI/calidad JPEG, perfiles preservados, comparación e informe; transparencia/máscaras, corpus y preflight pendientes |
| R01 | Comparar documentos | Cambios textuales y visuales localizados | Inicial: comparación por posición hasta 20 páginas, texto/apariencia y JSON con muestras; alineación avanzada y semántica pendientes |
| X01 | Bates y procesamiento por lotes | Orden, unicidad y fallos por archivo trazables | Inicial: Bates continuo entre hasta 10 PDF/100 páginas, ZIP y manifiesto; recetas generales de ocho tareas, biblioteca JSON, nombres, revisión y CLI; OCR/Office en recetas y planificación pendientes |
| X02 | Adjuntos, portfolios y capas | Estructura y visibilidad conservadas | Inicial: listar/añadir/retirar/descargar adjuntos con límites; portfolios/capas pendientes |
| X03 | PDF/A, PDF/UA, PDF/X y preflight | Validación con herramientas independientes | Inicial: perfiles PDF/A-1b/2b/3b y PDF/UA-1 con veraPDF, informe de reglas; copia PDF/A-2b validada; PDF/X y preflight universal pendientes |
| X04 | Accesibilidad | Etiquetas, orden de lectura y navegación asistida | Inicial: diagnóstico orientativo, título/idioma/XMP y preferencia del visor editables; etiquetado, orden de lectura, alternativas y revisión asistida completos pendientes |
| X05 | Medición de planos | Escala/unidades calibradas; no inferir geometría ausente | Pendiente |
| N01 | Compartir, sincronizar y colaboración | Permisos, conflictos y privacidad comprobados | Pendiente |
| N02 | Asistencia IA | Referencias verificables, consentimiento y costos definidos | Pendiente |

En 0.18 también se añaden edición de etiquetas Unicode/navegación y movimiento numérico de notas/rectángulos importados. Redimensionado importado y estructuras avanzadas siguen pendientes. Alcance completo: AVANCE_LARGO_018.md.

En 0.19 se amplían F01/F02 con grupos estándar y jerarquías compatibles, conservando restricciones. La copia/importación de árboles avanzados se bloquea explícitamente hasta verificarla. Guía: FORMULARIOS_AVANZADOS.md.

En 0.20 E02 incorpora fuentes originales compatibles por fragmentos, ancho opcional y varios estilos; no implica reflujo general ni fidelidad universal. Guía: TEXTO_CON_ESTILOS.md.

En 0.21 se añade una revisión estructural orientativa por páginas y JSON, búsqueda por tareas, favoritos y comandos. No se acredita X03: esta inspección no valida estándares ni equivale a preflight. Guía: ESPACIO_DE_TRABAJO.md.

En 0.23 F01/F02 y la composición de páginas admiten árboles de formularios compatibles conservando grupos e independencia entre copias. Se validan valores, propiedades, flujos de apariencia, estructura final y fuentes inalteradas; no habilita firmas digitales, XFA ni scripts. Guía: IMPORTAR_FORMULARIOS.md.

En 0.24 E02 amplía el formato y la selección de párrafos con vista previa obligatoria; guía: PARRAFOS_Y_FORMATO.md. La estimación global sigue siendo secundaria frente a las capacidades verificadas.

En 0.25 E01/E02 amplían la edición por bloques a páginas giradas, formato sugerido y comparación original/resultado. No se extiende la edición rápida de líneas del panel lateral a páginas giradas; se usa el editor de bloques. Guía: EDICION_PAGINAS_GIRADAS.md.

En 0.26 se amplían A02/E04 y el diseño de campos con formato y valores iniciales. Se añade automatización general inicial por lotes: optimización, extracción TXT y copias AES-256, con validación previa y manifiesto de resultados. Ver AVANCE_AMPLIO_026.md.

En 0.27 F01 amplía propiedades y geometría de campos existentes con grupos y vista previa; A05 incorpora conversaciones nativas, estados e informes; C02 incorpora DOCX textual editable, con pérdidas explícitas. Guía: AVANCE_AMPLIO_027.md.

En 0.28 C02 incorpora imágenes compatibles, tablas Word editables con revisión y motivos de omisión; F01 incorpora renombrado jerárquico y edición/reordenación de opciones de listas conservando valores actual y de restablecimiento. Guía: AVANCE_AMPLIO_028.md.

En 0.29 se incorpora firma digital de aprobación SHA-256 con P12/PFX, marca visible opcional, firmas sucesivas y verificación local de integridad, revisiones y confianza explícita. La confianza/revocación no se infiere de la apariencia o de incluir un certificado en el PDF. Revocación, TSA, LT/LTA y tokens siguen pendientes. Guía: FIRMAS_DIGITALES.md.

En 0.30 X03 incorpora validación normativa externa y copia PDF/A-2b verificada; X04 incorpora diagnóstico acotado y preparación de metadatos, sin crear etiquetas ni declarar accesibilidad completa. Guía: ESTANDARES_Y_ACCESIBILIDAD.md.

En 0.31 A03 añade selección precisa por caracteres y vista durante el arrastre. La censura incorpora regiones manuales multipágina y búsqueda literal/correos con selección individual, inspecciones vinculadas al documento y revisión de todas las páginas afectadas; mantiene el motor conservador y no certifica detección ni eliminación universal. Guía: SELECCION_Y_CENSURA.md.

En 0.32 A02 incorpora traslado nativo de trazos/líneas compatibles, conservando apariencia y propiedades; la interfaz distribuye las 56 herramientas por secciones de tareas y unifica su estilo. Guía: INTERFAZ_PROFESIONAL.md.

En 0.33 A02 incorpora cambio de tamaño y tiradores de movimiento/redimensionado para trazos/flechas importados compatibles. La edición de extremos individuales y selección múltiple siguen pendientes. Guía: TIRADORES_IMPORTADOS.md.

En 0.34 A02 añade extremos independientes de Line y selección múltiple de marcas existentes compatibles: seis alineaciones, dos distribuciones y acciones colectivas con historial. No incluye grupos PDF persistentes ni mezcla con marcas nuevas de sesión. Guía: AVANCE_AMPLIO_034.md; pendientes de cierre: release-criteria.json.

En 0.34 Q03 incorpora reducción controlada de imágenes directas RGB/gris con conservación del perfil, respeto de la colocación mayor de recursos compartidos, revisión y recibo con hash de la copia descargada; casos complejos pendientes.

En 0.35 X01 añade recetas declarativas de ocho tareas ordenables, biblioteca de 20 recetas, intercambio JSON sin contraseñas, nombres seguros, revisión por documento y manifiestos por paso. Q03 amplía a CMYK y recursos en Form XObjects anidados; contraste de perfiles y color con motores independientes. Guía: [AVANCE_AMPLIO_035.md](AVANCE_AMPLIO_035.md).

En 0.36 la edición añade reflujo explícito entre regiones de varias páginas con formato común y revisión completa; formularios añade cálculos decimales puntuales (suma/producto/promedio/mínimo/máximo) guardados como valores; Word conserva enlaces HTTP/HTTPS completos con informe de omisiones. No equivale a reflujo automático, fórmulas PDF ni importación Office. Guía: [AVANCE_AMPLIO_036.md](AVANCE_AMPLIO_036.md).

En 0.37 la creación/conversión incorpora DOCX→PDF compatible, con formato directo, imágenes, tablas, revisión multipágina e informe. Formularios añade reglas declarativas con dependencias en proyectos (PDF exportado con valores; sin recálculo externo). Automatización admite salida Word con sus opciones y manifiestos. Persistencia de reglas tras cambios estructurales y fidelidad Office compleja pendientes. Guía: [AVANCE_AMPLIO_037.md](AVANCE_AMPLIO_037.md).

## Incorporado en 0.38

- Word a PDF: estilos heredados compatibles, valores predeterminados, formato directo prioritario, espaciado y sangrías.
- Listas decimales, alfabéticas, romanas y viñetas; niveles, contadores, valores iniciales y reinicios básicos, con avisos para formatos no admitidos.
- Informe/asistente con estilos y elementos de lista incorporados; revisión de cada página conservada.
- Reglas de proyecto conservadas al ordenar/girar/eliminar páginas; campos compartidos supervivientes y bloqueo atómico de dependencias eliminadas.
- Historial, proyecto y recuperación con las nuevas referencias. Otras transformaciones aún materializan valores.

Alcance, evidencia y restricciones: [AVANCE_AMPLIO_038.md](AVANCE_AMPLIO_038.md).

## Incorporado en 0.39

- Reglas activas entre inserción, reemplazo, duplicación, hojas nuevas, recorte y cambios compatibles de campos, incluidos nombres jerárquicos/compartidos.
- Prevención de pérdida o reasignación accidental de dependencias; copias con valores independientes.
- Encabezados/pies Word con variantes general/portada/pares, relaciones locales, texto/imágenes/tablas/enlaces compatibles y reserva de espacio.
- PAGE/NUMPAGES simples con valores reales del PDF y formato compatible; otros campos conservan resultados guardados con aviso.
- Vista Word ajustada o ampliada con imagen de mayor resolución; revisión por página y recuperación del proyecto comprobadas.

Alcance, evidencia y restricciones: [AVANCE_AMPLIO_039.md](AVANCE_AMPLIO_039.md).

## Incorporado en 0.40

- Reflujo por fragmentos con negrita/cursiva, tamaño y color, usando familias incluidas.
- Lectura del formato compatible, separación de selección y edición/creación/eliminación de fragmentos.
- Distribución entre regiones/páginas con ajuste proporcional opcional y rechazo de desbordamientos.
- Verificación del texto PDF generado y límites de fragmentos; comparación multipágina, historial/proyecto/recuperación.

Alcance y cinco criterios cerrados: [REFLUJO_MIXTO.md](REFLUJO_MIXTO.md). Estado general sin porcentaje nuevo arbitrario: [ESTADO_FUNCIONAL.md](ESTADO_FUNCIONAL.md).

## Incorporado en 0.41

- PAGE/NUMPAGES complejos de encabezados/pies; delimitación e instrucciones repartidas entre fragmentos, formatos compatibles y rechazo de estructuras incompletas.
- Inicio y formatos decimales/romanos/alfabéticos; MERGEFORMAT/CHARFORMAT compatibles y etiquetas nativas PDF.
- Tablas con combinaciones horizontales/verticales rectangulares; alternativas declaradas por filas cuando no se puede reconstruir sin pérdida.
- Informe con campos/tablas/numeración, revisión multipágina, navegación, exportación, proyecto y recuperación verificados.

Cinco entregables y sus límites: [WORD_CAMPOS_TABLAS_041.md](WORD_CAMPOS_TABLAS_041.md).

## Incremento 0.42

Secciones Word con salto a página siguiente: papel/orientación/márgenes propios, encabezados/pies vinculados por variante, continuidad/reinicio y etiquetas PDF, totales globales y SECTIONPAGES. Saltos manuales de página reales y resumen plegable por sección, con exportación/proyecto/recuperación. Guía: [WORD_SECCIONES_042.md](WORD_SECCIONES_042.md).

Siguiente bloque recomendado: grupos persistentes de anotaciones. Después, cálculos nativos interoperables y validación del ejecutable propio en Windows. Las secciones compatibles ya no se presentan como trabajo sin empezar.
