# Reapdf

Estado vigente: [división con nombres personalizados, marcadores y listas](docs/DIVISION_CON_NOMBRES_Y_LISTAS_20261029.md), **80,98 % del programa completo (≈81 %)**, estimación de madurez con Windows pendiente. [Plan actual](docs/PLAN_ACTUAL.md) y [matriz con pesos estables](docs/avance-global.json).

Continuar en una PC Windows con Codex local: [guía de traslado y configuración](docs/CONTINUAR_EN_PC.md). Uso opcional de [REA](docs/REA_PARA_REAPDF.md) para investigaciones concretas.

Ventana propia Qt, edición de fuentes compatibles, vinculación configurable, medición, capas, XFDF y OCR regional comprobados en Linux. No se genera instalador/portable en este avance. La base procede de 0.43 recuperado y mejoras nuevas; 0.55 no se ha recuperado. Generación de informes/registros/ensayos excluida.

Primera versión experimental de un editor PDF personal, con Adobe Acrobat como referencia funcional. Primero se construye el editor general; la vinculación entre documentos usa archivos y funciones elegidos por el usuario.

## Funciona en este prototipo

- Abrir PDF, navegar y ampliar con resolución adaptada al zoom y a la pantalla; ajustar al ancho o ver la página completa.
- Miniaturas que reflejan las ediciones y marcadores editables con jerarquía, destinos y estilos.
- Añadir encabezados, pies y numeración decimal/romana por rangos, con vista previa y corrección de sesión.
- Buscar texto en el documento editado, resaltar coincidencias y navegar entre resultados.
- Seleccionar texto digital en modo Lectura y copiarlo con Ctrl+C.
- Insertar PNG/JPEG, mover, redimensionar y eliminar las imágenes nuevas con historial; exportar sin reducir su resolución original.
- Dibujar trazos, líneas, flechas y rectángulos con color y grosor, exportados como anotaciones PDF.
- Resaltar, subrayar y tachar palabras o fragmentos por caracteres, con selección visible durante el arrastre, incluso en varias líneas y páginas giradas.
- Crear notas, corregir su contenido y conservar caracteres Unicode.
- Seleccionar marcas existentes compatibles, cambiar color, editar el contenido de notas y eliminarlas con historial.
- Seleccionar, mover, redimensionar y eliminar marcas creadas en la sesión, con deshacer/rehacer. Las notas conservan el tamaño de su icono.
- Deshacer y rehacer cambios de la sesión.
- Añadir cajas de texto nuevas con varias líneas, fuente base, tamaño, color y alineación.
- Colocar cuatro sellos estándar y crear enlaces web o a páginas del documento.
- Reemplazar texto real en líneas simples compatibles, con 12 variantes base de Helvetica/Times/Courier, tamaño y color, validación de espacio y vista previa del PDF resultante.
- Organizar páginas: cambiar orden, girar por selección y eliminar conservando al menos una página.
- Deshacer/rehacer la organización sin perder las ediciones anteriores.
- Extraer una selección en un PDF aparte sin modificar el documento abierto.
- Recortar márgenes en páginas seleccionadas y restaurar la página completa.
- Reemplazar un bloque de páginas por páginas elegidas de otro PDF.
- Dividir por bloques o grupos personalizados y descargar las partes en un ZIP.
- Unir otro PDF completo al final, o insertar una selección como `1-3, 5` en una posición elegida.
- Deshacer/rehacer la inserción conservando las ediciones anteriores.
- Duplicar páginas con sus ediciones e insertar hojas en blanco A4, Carta o personalizadas.
- Guardar/abrir proyectos `.reapdf` y recuperar automáticamente el último estado aplicado.
- Preparar la impresión del PDF editado en el lector del navegador con Ctrl+P.
- Rellenar campos simples de formularios PDF existentes: texto, casillas y listas; conservar valores y apariencias editables.
- Crear PDF desde imágenes PNG/JPEG ordenadas, con papel y márgenes elegidos.
- Exportar páginas editadas a PNG/JPEG en ZIP, con resolución y calidad elegidas.
- Importar/exportar datos de formularios JSON vinculados al PDF, aplanar y crear/eliminar campos simples.
- Reconocer escaneados en español/inglés con OCR local y exportar texto UTF-8.
- Mover, reemplazar o eliminar imágenes existentes compatibles sin reducir sus píxeles originales.
- Reemplazar bloques digitales de varias líneas con DejaVu Sans incrustada y control de desbordamiento.
- Añadir marcas de agua, editar propiedades y optimizar sin reducir resolución.
- Descargar copias AES-256 y abrir PDF con contraseña autorizada.
- Comparar texto y apariencia de dos PDF por páginas y descargar un informe.
- Editar etiquetas de página y navegar por sus nombres, conservando página física y etiquetas Unicode.
- Añadir, descargar y retirar adjuntos del PDF con límites de tamaño y descompresión.
- Numerar lotes de varios PDF con Bates continuo y manifiesto de rangos/SHA-256.
- Detectar/revisar tablas y descargar CSV con protección de fórmulas.
- Dibujar una firma visual vectorial, sin certificado ni validación de identidad.
- Firmar copias con P12/PFX y SHA-256, añadir firmas sucesivas compatibles y verificar integridad/revisiones/confianza explícita con informe JSON.
- Validar perfiles PDF/A y PDF/UA con veraPDF y preparar copias PDF/A-2b que superen validación independiente.
- Revisar indicadores de accesibilidad y corregir título/idioma sin simular etiquetado completo.
- Descargar una copia censurada y saneada de regiones compatibles, sin sustituir la sesión original.
- Mover notas y rectángulos importados por coordenadas; corregir el giro de reconocimiento OCR sin modificar la imagen.
- Rellenar jerarquías compatibles y sincronizar texto/casillas compartidos; elegir radios exclusivos, crear/eliminar grupos y conservar datos/apariencias.
- Importar, duplicar o reemplazar páginas con formularios jerárquicos compatibles, conservando grupos e independencia entre original y copia.
- Corregir fragmentos con fuentes/estilos originales compatibles, incluso TrueType parcial, con ampliación de ancho opcional y bloqueo de glifos ausentes.
- Trabajar por áreas con herramientas específicas y paneles contextuales plegables; buscar funciones globalmente y guardar favoritos locales; usar una paleta de comandos y atajos.
- Saltar a una página física, ampliar el área de lectura y proteger borradores frente a navegación o cambios de herramienta.
- Revisar estructura por páginas y descargar un informe JSON sin textos ni valores de campos.
- Exportar una copia sin modificar el archivo de entrada.

Guía del avance 0.18 y restricciones: [AVANCE_LARGO_018.md](docs/AVANCE_LARGO_018.md). Formularios del avance 0.19: [FORMULARIOS_AVANZADOS.md](docs/FORMULARIOS_AVANZADOS.md). Edición del avance 0.20: [TEXTO_CON_ESTILOS.md](docs/TEXTO_CON_ESTILOS.md). Importación de formularios del avance 0.23: [IMPORTAR_FORMULARIOS.md](docs/IMPORTAR_FORMULARIOS.md). Distribución por áreas del avance 0.22: [AREAS_DE_TRABAJO.md](docs/AREAS_DE_TRABAJO.md). Interfaz y revisión del avance 0.21: [ESPACIO_DE_TRABAJO.md](docs/ESPACIO_DE_TRABAJO.md). Estimación global: **86 % ±5 puntos** del plan propio, sin equivalencia con el catálogo completo de Acrobat.

No es todavía una alternativa completa a Acrobat. Hay un portable experimental para Windows x64, con intérprete y dependencias incluidos, y una entrega de código para desarrollo. La interfaz se sirve localmente y el portable intenta abrirla en una ventana de Edge/Chrome; hay un modo de navegador normal como alternativa. No utiliza servicios externos para procesar documentos.

Por indicación del usuario, no se generan portables en cada avance. La solicitud más reciente pide una entrega de prueba ahora: 0.43 incorpora `Reapdf.exe` y el motor Windows incluido. Su ventana usa Edge/Chrome instalado; la ejecución gráfica Windows aún necesita verificarse. El paquete 0.20 queda como antecedente. Código actual: 0.43.

Para consultar el portable anterior sin instalar Python ni Node.js, véase [PORTABLE.md](docs/PORTABLE.md). Su ensamblado se comprobó en Linux; todavía no se ejecutó en Windows.

Para probar la entrega de código en Windows con comandos de doble clic y un documento de ejemplo, sigue [la guía de prueba](docs/PROBAR.md). El ZIP generado con `scripts/package_trial.py` incluye código y ejemplo; todavía requiere Python y Node.js.

## Instalación y ejecución

Requisitos: Python 3.12, Node.js 24 y npm. Ejecutar desde la raíz del repositorio.

Linux/macOS (Linux comprobado):

```bash
bash scripts/install.sh
bash scripts/start.sh
```

Windows PowerShell (instrucciones preparadas, todavía no ejecutadas en Windows):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm ci
npm run build
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

El servidor escucha únicamente en loopback, puerto 8000. No exponer esta versión a Internet. Para desarrollo de interfaz, mantener el backend iniciado y ejecutar `npm run dev` en otra terminal; Vite usa el puerto 5173 y redirige `/api` al backend.

## Pruebas

```bash
npm test
npm run test:ranges
npm run test:geometry
npm run test:images
npm run test:bookmarks
npm run build
npx playwright install chromium
npm run test:ui
```

La prueba de navegador inicia y detiene su propio servidor en el puerto 8765; genera un documento sintético, edita texto, dibuja trazos y figuras con zoom, selecciona y elimina una marca, deshace/rehace, navega por miniaturas y marcadores, busca en el texto editado, comprueba el portapapeles y verifica el PDF descargado. Después organiza páginas, deshace/rehace, extrae una selección, elimina una página y edita sobre el nuevo orden. También inserta un rango no contiguo, comprueba rangos inválidos, deshace/rehace y une un PDF completo al final. Los archivos exportados se vuelven a abrir para comprobar contenido, rotaciones y marcadores. Usa Chromium del sistema si existe en `/usr/bin/chromium`, o el navegador instalado por Playwright. Se puede indicar su ruta con `CHROMIUM_PATH`.

No son necesarios archivos privados. `scripts/create_sample.py` genera un PDF de dos páginas; recibe como argumento la ruta de salida. Las pruebas usan temporales y nunca deben apuntarse a un archivo personal existente.

El workflow `.github/workflows/ci.yml` prepara pruebas del motor en Linux y Windows y del navegador en Linux. Su existencia no demuestra que GitHub Actions haya ejecutado o aprobado esos trabajos.

Avance largo 0.17 y límites de cada herramienta: [guía](docs/AVANCE_LARGO_017.md).

Formularios: [alcance y uso](docs/FORMULARIOS.md). Creación/exportación de imágenes: [CONVERSIONES.md](docs/CONVERSIONES.md).

Marcadores, encabezados y numeración: [guía de uso](docs/MARCADORES_Y_ENCABEZADOS.md).

Texto nuevo, sellos y enlaces: [CONTENIDO_NUEVO.md](docs/CONTENIDO_NUEVO.md).

Imágenes nuevas y límites: [IMAGENES.md](docs/IMAGENES.md). Interfaz actual y futura ventana propia: [ESCRITORIO.md](docs/ESCRITORIO.md).

Proyectos y recuperación: [SESIONES.md](docs/SESIONES.md). Duplicación y hojas vacías: [PAGINAS_NUEVAS.md](docs/PAGINAS_NUEVAS.md). Preparación de impresión: [IMPRESION.md](docs/IMPRESION.md).

Guía de zoom, herramientas y cambios pendientes: [USABILIDAD.md](docs/USABILIDAD.md).

## Límites actuales

- Formularios: campos AcroForm simples compatibles, hasta 500; creación/eliminación de campos simples, datos JSON y aplanado disponibles; campos compartidos/jerárquicos y radios estándar disponibles con restricciones; fuentes complejas, listas compartidas, XFA y cálculos pendientes. La importación, duplicación y sustitución de páginas con árboles compatibles conserva sus grupos e independencia; se rechazan ciclos, nombres ambiguos, cálculos/scripts y estructuras no verificadas. No se confunden plantillas impresas con campos.
- Conversión: creación desde PNG/JPEG y exportación a imágenes; Word con texto, imágenes compatibles y tablas editables con revisión; importación Office y fidelidad completa pendientes; OCR español/inglés disponible con revisión. Límites y conservación en CONVERSIONES.md.

- Hasta 30 MB, 500 páginas y 3000 puntos por dimensión de página. Estos límites no son una certificación de rendimiento para todos los archivos de esos tamaños.
- Texto: líneas horizontales de un único fragmento en páginas sin rotar, con fuentes base reconocidas. Se puede elegir entre 12 variantes de Helvetica/Times/Courier, tamaño de 6 a 144 puntos y color. Se conservan el origen y la línea base y se valida ancho, altura y separación. No hay reflujo de párrafos; se rechaza texto que no cabe, caracteres fuera del conjunto admitido y regiones que se cruzan con otros textos.
- OCR local añade texto buscable a escaneados, sin convertir la imagen en texto editable. Reemplazar bloque de texto admite varias líneas y fuentes de origen mezcladas, sustituidas por DejaVu Sans; su modo de párrafo sustituye los estilos y no hace reflujo entre páginas. El modo nuevo por fragmentos conserva fuentes/estilos compatibles con las restricciones descritas en TEXTO_CON_ESTILOS.md. Edición de imágenes existentes limitada a estructuras directas compatibles.
- La selección abarca texto sobre los ejes de página, incluyendo documentos con rotación global y cajas de texto nuevas. Usa una fuente de interfaz ajustada al ancho; la selección de caracteres puede ser aproximada en tipografías especiales. Texto inclinado dentro de la página y orden de lectura complejo están pendientes.
- Búsqueda: texto digital, sin expresiones regulares, máximo 200 caracteres por consulta y 500 regiones de resultado. Las frases partidas entre líneas pueden producir varios resultados. La búsqueda sin distinguir mayúsculas depende del motor y no cubre todos los alfabetos. Los escaneados necesitan OCR.
- Los marcadores internos compatibles se crean/editan con hasta 2000 entradas y 10 niveles; índices con destinos especiales quedan en lectura. Encabezados y pies usan seis posiciones, una línea latina por posición y 12 fuentes base; no desplazan el contenido existente. Bates entre documentos se ofrece en una herramienta separada.
- La organización crea una versión nueva y conserva las versiones anteriores para deshacer/rehacer. En esa nueva versión las marcas previas pasan a tratarse como anotaciones preexistentes: para editarlas con las herramientas de sesión hay que deshacer la organización. Las etiquetas visibles de página se conservan como prefijos explícitos. Los enlaces locales a páginas eliminadas se retiran.
- La unión/inserción admite un archivo de origen por operación; se puede repetir para combinar más. Los rangos respetan el orden escrito, rechazan duplicados y el resultado no puede superar 500 páginas. Los marcadores importados se agrupan por nombre de archivo y los campos homónimos se mantienen independientes.
- La importación inicial rechaza PDF con indicadores de firma, XFA, capas, cálculos/scripts de formulario y ciertos enlaces o marcadores con acciones especiales. Solo copia páginas y sus anotaciones, no adjuntos ni la estructura completa de accesibilidad del origen. Véase [el alcance de la unión](docs/UNION.md).
- Las marcas creadas en la sesión se pueden seleccionar y eliminar, además de deshacer/rehacer. La lista de marcas permite elegir entre anotaciones superpuestas. Se admiten movimiento y cambio de tamaño por tiradores o valores numéricos; las marcas preexistentes compatibles admiten color, contenido de nota y eliminación. Notas y rectángulos importados admiten movimiento numérico; el tamaño y otras geometrías importadas están pendientes.
- Los PDF con contraseña se abren con autorización; las restricciones pueden exigir contraseña de propietario. La copia de trabajo, proyecto y recuperación quedan descifrados. Los detectados con indicadores de firma se abren para lectura y verificación criptográfica local con confianza explícita. Se puede añadir una firma compatible en copia; no hay consulta de revocación ni TSA.
- La modificación respeta los permisos declarados del documento. Las páginas con censuras pendientes no permiten editar texto, para evitar aplicar otras censuras accidentalmente.
- El almacenamiento temporal de documentos y versiones está limitado a 300 MB. Al agotarse, la operación se rechaza sin reemplazar el documento abierto; exporta el trabajo y abre de nuevo un archivo para liberar el historial. La recuperación persistente se guarda aparte como un único proyecto local.
- Los documentos originales se guardan temporalmente en el equipo del backend. Se eliminan al reemplazarlos en la interfaz o al cerrar normalmente el servidor. Hay un punto de recuperación persistente del último estado aplicado; espera a «Recuperación local actualizada» o guarda un proyecto antes de cerrar. No incluye borradores ni historial completo.
- Las pruebas visuales actuales usan documentos sintéticos y el mismo motor; Poppler contrasta la extracción de texto en las pruebas de censura. Falta validar con documentos reales y lectores independientes como Acrobat, además de Windows, impresoras físicas y lápiz físico.

## Arquitectura y licencia del motor

React/Vite para la interfaz; FastAPI para la API local; PyMuPDF para lectura, renderizado, anotaciones y la prueba de edición real. La interfaz consume operaciones declarativas y no accede directamente a PyMuPDF.

PyMuPDF es un candidato con licencia AGPL/comercial. No se ha comprado una licencia comercial ni se ha tomado la decisión de distribuir Reapdf como producto propietario con este motor. Antes de distribuirlo o servirlo a terceros hay que resolver las obligaciones de licencia o seleccionar otra implementación. La evaluación de alternativas figura en [la decisión técnica](docs/MOTOR.md).

Consulta [el plan de desarrollo](docs/PLAN.md) y [la matriz de funciones](docs/FUNCIONES.md). `PRODUCTO.md` conserva la investigación inicial; su prioridad de automatizaciones quedó reemplazada por este plan.

El avance global estimado y sus criterios se registran en [docs/AVANCE.md](docs/AVANCE.md). Alcance de las anotaciones de texto y notas: [docs/REVISION.md](docs/REVISION.md).

Recorte, reemplazo y división: [alcance y límites](docs/PAGINAS_AVANZADAS.md).

Anotaciones preexistentes, tipos compatibles y restricciones: [docs/ANOTACIONES_EXISTENTES.md](docs/ANOTACIONES_EXISTENTES.md).

Fuentes, tamaño, color y límites del texto: [docs/TEXTO.md](docs/TEXTO.md).

Edición de párrafos 0.24: selección de bloques detectados, doce variantes de fuentes incluidas, color, interlineado y ajuste de tamaño con vista previa obligatoria. Guía: [PARRAFOS_Y_FORMATO.md](docs/PARRAFOS_Y_FORMATO.md).

Edición 0.25: párrafos y fragmentos compatibles en páginas giradas, conservando giro y recorte; formato sugerido desde el bloque y comparación original/resultado. Guía: [EDICION_PAGINAS_GIRADAS.md](docs/EDICION_PAGINAS_GIRADAS.md).

Avance amplio 0.26: edición de enlaces existentes, diseño de formularios con formato y valores iniciales, redimensionado de rectángulos/elipses importados y procesamiento por lotes. Guía: [AVANCE_AMPLIO_026.md](docs/AVANCE_AMPLIO_026.md).

Avance amplio 0.27: propiedades y geometría de campos existentes, conversaciones con respuestas/estados nativos e informes CSV/JSON, y exportación de texto digital a Word editable con revisión de límites. Guía: [AVANCE_AMPLIO_027.md](docs/AVANCE_AMPLIO_027.md).

Avance amplio 0.28: Word con imágenes, tablas editables e informe de omisiones; renombrado de campos conservando jerarquías/grupos y edición de opciones de listas con valores y etiquetas separados. Guía: [AVANCE_AMPLIO_028.md](docs/AVANCE_AMPLIO_028.md).

Avance amplio 0.29: firma de copias con certificado P12/PFX, firmas sucesivas, marca visible opcional, verificación criptográfica con confianza explícita e informes JSON. Funciona sin consultas de red ni revocación. La firma manuscrita sigue siendo una herramienta distinta. Guía y límites: [FIRMAS_DIGITALES.md](docs/FIRMAS_DIGITALES.md).

Avance amplio 0.30: validación PDF/A y PDF/UA con veraPDF, copia PDF/A-2b validada con comparación visual y comprobación de texto/tamaños, y diagnóstico/preparación de título e idioma. La validación requiere Java; la conversión también Ghostscript. No se declara accesibilidad completa ni ejecución Windows. Guía: [ESTANDARES_Y_ACCESIBILIDAD.md](docs/ESTANDARES_Y_ACCESIBILIDAD.md).

Avance 0.31: selección precisa por caracteres con vista durante el arrastre; censura manual en varias páginas, búsqueda de términos/correos con elección de coincidencias y revisión de todas las páginas antes de descargar. Se conservan los límites del motor y el documento original. Guía: [SELECCION_Y_CENSURA.md](docs/SELECCION_Y_CENSURA.md).

Avance 0.32: interfaz minimalista con grupos de tareas plegables, iconos, ayuda opcional persistente, controles y asistentes con estilo común y títulos fijos. Movimiento nativo de trazos/líneas importados compatibles con conservación de apariencia, giros, recortes e historial. Guía: [INTERFAZ_PROFESIONAL.md](docs/INTERFAZ_PROFESIONAL.md).

Avance 0.33: tiradores para mover/redimensionar trazos y flechas importados compatibles, guía durante el gesto, cancelación, teclado, historial y medidas sobre los vértices. Se comprueba fidelidad de apariencia antes de redimensionar. Guía: [TIRADORES_IMPORTADOS.md](docs/TIRADORES_IMPORTADOS.md).

Avance amplio 0.34: edición de extremos individuales de líneas/flechas, selección múltiple de marcas existentes con alineación/distribución, desplazamiento/color y borrado conjuntos; comprobación de fidelidad al recolorear trazos; carga separada de asistentes y evidencia local de cierre con hashes/registros y pendientes explícitos. Guía: [AVANCE_AMPLIO_034.md](docs/AVANCE_AMPLIO_034.md).

Avance amplio 0.35: recetas de trabajo en cuatro etapas con ocho tareas ordenables, biblioteca e intercambio JSON, nombres de salida, revisión y manifiestos; ejecución local sin navegador; compresión CMYK y de imágenes en Form XObjects anidados. Guía, límites y capturas: [AVANCE_AMPLIO_035.md](docs/AVANCE_AMPLIO_035.md).

Avance amplio 0.36: flujo de texto entre regiones de varias páginas con comparación y aplicación completa; cálculos decimales puntuales sobre campos compatibles, sin fórmulas automáticas; enlaces web completos en la exportación Word, con informe de omisiones. Guía y capturas: [AVANCE_AMPLIO_036.md](docs/AVANCE_AMPLIO_036.md).

Avance amplio 0.37: importar DOCX compatible a PDF con revisión de todas las páginas e informe; cálculos dependientes en proyectos y recuperación Reapdf; Word como salida de recetas con manifiestos. Guía, límites y capturas: [AVANCE_AMPLIO_037.md](docs/AVANCE_AMPLIO_037.md).

Avance amplio 0.38: estilos heredados, espaciado/sangrías y listas multinivel en la importación Word; reglas de cálculo activas tras ordenar/girar/eliminar páginas, con protección de sus dependencias. Guía y evidencia: [AVANCE_AMPLIO_038.md](docs/AVANCE_AMPLIO_038.md).

Avance amplio 0.39: cálculos de proyecto conservados al insertar/reemplazar/duplicar/añadir hojas/recortar y editar campos compatibles; encabezados/pies Word con variantes y PAGE/NUMPAGES simples; revisión de página completa y ampliada. Guía y evidencia: [AVANCE_AMPLIO_039.md](docs/AVANCE_AMPLIO_039.md).

Avance 0.40: reflujo con formato mixto entre regiones, edición/separación de fragmentos, ajuste proporcional y comprobación del PDF resultante. Alcance cerrado: [REFLUJO_MIXTO.md](docs/REFLUJO_MIXTO.md). El seguimiento vigente usa capacidades y criterios, sin atribuir precisión al porcentaje anterior: [ESTADO_FUNCIONAL.md](docs/ESTADO_FUNCIONAL.md).

Avance 0.41: PAGE/NUMPAGES complejos en encabezados/pies, inicio y formatos de numeración, etiquetas PDF y tablas con celdas combinadas horizontales/verticales; informe y revisión integrados. Cinco entregables cerrados con límites y evidencia: [WORD_CAMPOS_TABLAS_041.md](docs/WORD_CAMPOS_TABLAS_041.md).

Avance 0.42: secciones Word con dimensiones y márgenes independientes, herencia de encabezados, reinicios y etiquetas PDF; SECTIONPAGES, saltos manuales reales e informe por sección. Alcance y evidencia: [WORD_SECCIONES_042.md](docs/WORD_SECCIONES_042.md).

Entrega de prueba 0.43 solicitada por el usuario: `Reapdf.exe` portable Windows x64 con logo de inicio y motor incluido. Arranque gráfico Windows aún sin verificar; la ventana utiliza Edge/Chrome instalado. Guía: [portable/LEEME.md](portable/LEEME.md). Plan actualizado: [PLAN_CIERRE_Y_FLUJOS.md](docs/PLAN_CIERRE_Y_FLUJOS.md).
