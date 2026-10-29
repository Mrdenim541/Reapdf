# Avance largo 0.17 — alcance y prueba personal

Este bloque amplía varios ámbitos del editor general. Todas procesan los documentos localmente. La interfaz sigue siendo React/HTML servida por el motor local y puede abrirse en la ventana experimental del portable.

## Formularios y datos

**Datos de formulario** descarga JSON con valores aplicados de campos compatibles. El archivo incluye la huella SHA256 del PDF base y la identidad, tipo y nombre de cada campo. **Importar y aplicar datos** verifica el conjunto completo antes de cambiar la sesión; se puede deshacer. Conserva los campos no incluidos y los demás cambios. Se exige el mismo PDF base: un PDF exportado, reorganizado o con propiedades cambiadas puede tener otra huella. Conserva el proyecto de origen. No es XFDF/FDF ni un sistema de correspondencia automática entre formularios parecidos. La exportación requiere permiso de copia.

**Aplanar formulario** convierte todos los campos compatibles en contenido fijo, conservando sus apariencias y las anotaciones independientes. Requiere confirmar que se quiere perder su editabilidad en esa versión. Deshacer recupera los campos mientras se conserve el historial; el proyecto anterior también permite recuperarlos. Se rechazan formularios con estructuras no compatibles o campos sin apariencia; no se aplanan parcialmente.

**Crear o eliminar campos** añade texto, varias líneas, casilla o lista desplegable. En Crear, arrastra una caja en la muestra o introduce X/Y/ancho/alto, elige nombre único y tipo; las listas admiten de 1 a 100 opciones distintas. Requiere página a 0°, caja interior de al menos 15 × 15 pt, hasta 500 campos por documento. Usa Helvetica a 12 pt y nombres de hasta 100 caracteres. Después puedes rellenarlo con la herramienta habitual. Eliminar retira un campo compatible y su apariencia. Ambas operaciones crean versiones reversibles. Radio, firmas, cálculos, grupos compartidos y jerarquías avanzadas siguen pendientes.

## OCR y exportación de texto

Abre `ejemplos/reapdf-escaneado.pdf` y pulsa **Reconocer texto (OCR)**. Elige páginas, español, inglés o ambos, y 150/200/300 ppp. Reconoce hasta 10 páginas, 16 millones de píxeles por página, 8192 px por lado y 64 millones de píxeles por lote. Solo se admite un OCR a la vez. El motor trabaja fuera del bucle principal del servidor, pero la herramienta espera a que termine; no hay cancelación de página ni porcentaje de progreso.

El programa omite las páginas que ya contienen texto para evitar duplicarlo. Reconoce en coordenadas sin giro y restaura el giro de la hoja. Añade solo una capa de texto invisible: mantiene el escaneado, sus píxeles y su flujo de imagen, los marcadores y las demás páginas. La nueva versión permite buscar, seleccionar/copiar texto y exportarlo. Deshacer vuelve al escaneado anterior; proyectos y recuperación conservan la versión reconocida. OCR no convierte la fotografía del texto en un párrafo editable: el bloque gráfico sigue siendo una imagen.

Revisa siempre nombres, cifras, acentos y orden de lectura. No hay corrección automática de orientación interna, perspectiva, inclinación, ruido ni reconocimiento fiable de escritura manual, fórmulas o tablas. Las páginas mixtas con algo de texto digital se omiten completas, incluso si también contienen zonas escaneadas. Se rechazan páginas con campos sin texto y documentos firmados o sin permisos de modificación/copia.

**Exportar texto** descarga UTF-8 por rangos y conserva el orden escrito. Incluye texto aplicado, valores visibles de formulario y OCR, con separadores de página. No conserva diseño Word/Excel ni garantiza el orden de tablas/columnas. Una página escaneada sin OCR no produce texto de su imagen.

Los idiomas `eng` y `spa` de tessdata_fast 4.1.0 están incluidos con URLs fijadas, SHA256 y licencia Apache-2.0 en `resources/tessdata`. Se verifican antes del OCR. No se necesita instalar Tesseract ni descargar idiomas en el PC de prueba: PyMuPDF incorpora el motor usado por esta función. La ejecución real del binario Windows todavía debe comprobarse.

## Imágenes existentes

**Editar imágenes del PDF** permite mover/redimensionar una imagen directa, reemplazarla por PNG/JPEG o eliminarla. Selecciona la imagen, usa medidas o arrastra el marco/tirador y revisa la vista previa antes de aplicar. Mover conserva el objeto de imagen, píxeles, flujo JPEG y máscara alfa; no decodifica para volver a muestrear. Los flujos sin compresión pueden comprimirse sin pérdida al guardar. Reemplazar conserva la caja y puede cambiar la proporción del archivo nuevo; hasta 2 MB y 24 millones de píxeles. Eliminar no equivale a saneamiento o censura forense.

Se protegen imágenes compartidas entre varias apariciones, imágenes dentro de formularios gráficos, imágenes recortadas/inclinadas/reflejadas, capas, páginas con estados gráficos o recortes especiales y páginas con capa OCR identificada como GlyphLessFont. Tampoco se transforman imágenes diminutas transparentes de soporte. La operación crea una versión con los cambios anteriores incorporados; Deshacer restaura la anterior. Se verificaron cuatro giros, recorte de página, JPEG y máscara alfa.

## Bloques de texto y marcas de agua

**Reemplazar bloque de texto** funciona sobre una región digital de página sin giro. Arrastra o ajusta sus bordes, pulsa **Leer bloque seleccionado**, corrige el párrafo, tamaño y alineación, revisa la vista previa y aplica. Hasta 4000 caracteres y 6–72 pt, con alineación izquierda, centro, derecha o justificada. Reemplaza realmente el texto anterior, conservando lo que queda fuera de la región y los gráficos de fondo.

La región debe contener fragmentos completos, sin cortar sus cajas, sin imágenes/escaneados, campos, anotaciones, censuras pendientes o texto inclinado/transparente. Se incrusta **DejaVu Sans**, incluida con su licencia y huella en `resources/fonts`. Admite sus glifos latinos, griegos y cirílicos; otros caracteres pueden rechazarse. Las tipografías y estilos mezclados del bloque se sustituyen por una fuente y tamaño, no se conservan automáticamente. Si el texto no cabe, se rechaza sin modificación parcial. No hay reflujo entre regiones/páginas ni edición de una fotografía del texto. Crea una versión reversible; no convierte la operación en una herramienta de censura general.

**Marca de agua** coloca texto vectorial centrado, con rango, tamaño 12–144 pt, opacidad 5–75 % y ángulo -45/0/45°. Admite una línea latina de hasta 120 caracteres y comprueba que quepa en todas las páginas. La muestra debe actualizarse antes de aplicar. Puedes corregir o retirar la configuración de sesión y deshacer. No borra marcas ya incorporadas al original. Las marcas diagonales son buscables en el PDF; la capa de selección HTML aún se limita a texto sobre los ejes.

## Propiedades, optimización y contraseñas

**Propiedades del PDF** modifica título, autor, asunto, palabras clave y aplicación creadora. Puedes vaciarlas y retirar también XMP. No elimina adjuntos, comentarios, datos ocultos o contenido sensible del documento. La nueva versión es reversible.

**Optimizar PDF** compacta recursos y estructuras, sin reducir resolución de imágenes. Informa bytes antes/después y conserva la versión editada si no hay ahorro. No es conversión o certificación PDF/A, PDF/UA o PDF/X. Mantiene contenido, formularios y marcadores en los casos probados. Se conserva el cifrado/permisos del origen en las versiones que ya lo tenían y no se descifraron expresamente.

**Proteger copia** descarga un PDF AES-256 con contraseña de apertura y otra distinta de propietario, de 8–100 caracteres y hasta 127 bytes UTF-8. Permite indicar copia e impresión; los demás permisos de edición/relleno se permiten. Las restricciones dependen de que el lector las respete. Las contraseñas solo se usan para esa descarga y no se guardan en el proyecto/checkpoint. La sesión actual y su proyecto/recuperación no quedan protegidos con esas contraseñas. No se realiza un guardado incremental cifrado sobre el original.

Al abrir un PDF protegido, aparece un campo de contraseña. Se admite contraseña de usuario cuando permite todas las acciones usadas por esta versión, o la de propietario. Si hay restricciones, exige propietario antes de crear una copia descifrada. No se intenta adivinar ni retirar contraseñas sin autorización. Los PDF cifrados con indicadores de firma se rechazan para no generar una copia con validez aparente. El original se conserva; la sesión y proyecto de la copia descifrada quedan sin el cifrado de origen. Las restricciones de archivos con usuario vacío se conservan al editar, organizar, recortar u optimizar.

## Comparación

**Comparar documentos** carga un PDF de referencia y compara páginas por posición frente a la versión actual editada. Hasta 20 páginas por documento, 3 millones de píxeles por página y 40 millones en conjunto a 72 ppp. Muestra páginas con diferencias de texto/apariencia, miniaturas de ambos lados, páginas ausentes y diferencias textuales. Puedes descargar el informe JSON, que incluye las muestras. Se necesita permiso de copia en ambos documentos.

No alinea páginas movidas, no hace comparación semántica ni valida firmas. Los cambios de renderizado pueden contar como diferencias visuales y el texto de columnas/escaneados necesita revisión/OCR. Los listados largos de diferencias se limitan a 2000 líneas por página. Los documentos de referencia protegidos requieren abrirse y exportarse primero con autorización. No modifica ninguno de los documentos.

## Evidencia y pendientes

Las pruebas usan documentos sintéticos públicos y archivos descargados desde Chromium. No sustituyen la validación de documentos reales, lectores independientes, impresoras ni Windows. La matriz y el avance global se mantienen en AVANCE.md; añadir capacidades no demuestra automáticamente llegar al 70 %.
