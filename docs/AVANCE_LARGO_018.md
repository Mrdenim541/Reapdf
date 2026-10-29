# Avance largo 0.18 — herramientas profesionales y seguridad

20 de octubre de 2026. Continúa el bloque 0.17 y sitúa la **estimación global en 70 % ±5 puntos**, con los mismos pesos y alcance de AVANCE.md. No significa equivalencia con el 70 % de todas las funciones o casos de Acrobat; es una valoración de la cobertura y madurez del producto previsto. Persisten funciones importantes y validación real pendientes.

## Cómo probar las novedades

Todas están en el grupo **Documento**; las coordenadas se expresan en puntos PDF (72 por pulgada).

| Herramienta | Recorrido de prueba | Resultado |
|---|---|---|
| Etiquetas de página | Define reglas ordenadas, prefijo y formato; aplica y usa el selector junto al número físico | Etiquetas nativas PDF; no imprime números sobre el contenido |
| Archivos adjuntos | Añade un archivo, vuelve a abrir el listado, descárgalo y prueba retirarlo/deshacer | Archivos dentro del PDF, sin ejecutarlos |
| Numeración Bates por lotes | Añade PDF, ordénalos, define prefijo/inicio/cifras y genera vista previa | ZIP con secuencia continua entre archivos y manifiesto de huellas/rangos |
| Exportar tablas a CSV | Elige páginas y detección por líneas o texto; revisa y descarga | CSV UTF-8 por tabla, con protección de fórmulas y manifiesto |
| Firma visual manuscrita | Dibuja, ajusta posición/tamaño, revisa vista previa y aplica | Anotación vectorial; sin certificado ni verificación de identidad |
| Censurar y sanear copia | Arrastra o escribe una región, añádela, revisa y descarga | PDF separado con contenido retirado y zonas negras |
| Reconocer texto (OCR) | Elige la corrección de giro que pone el escaneo derecho para reconocerlo | Texto invisible alineado; la imagen original conserva sus píxeles y orientación |
| Seleccionar marca | Selecciona una nota o rectángulo existente, corrige X/Y y aplica | Desplazamiento real, tamaño conservado e historial |

Las vistas previas de Bates, firma y censura se pueden ampliar. Los cambios de etiquetas, adjuntos y firmas crean versiones reversibles, consolidando las operaciones anteriores. Las descargas de Bates, tablas y censura no sustituyen el documento abierto. Guarda un proyecto para continuar trabajando; exporta PDF para abrirlo en otros lectores.

## Alcance y límites

**Etiquetas.** Hasta 100 reglas nuevas; inicio en la primera página y reglas crecientes. Formatos decimal, romano, alfabético PDF y solo prefijo; prefijos Unicode, paréntesis, barras y caracteres escapados preservados mediante cadenas PDF válidas. El alfabético sigue la convención PDF: tras Z vienen AA, BB…; no es la numeración de columnas Excel. El selector identifica además la página física, aunque haya etiquetas repetidas. Reordenar, duplicar e insertar conservan etiquetas visibles como reglas explícitas; no renumeran el contenido impreso.

**Adjuntos.** Añadir hasta 8 MB por archivo, 100 archivos y 32 MB de tamaños declarados por documento. Descargas con límite independiente de descompresión de 8 MB; no se confía solo en el tamaño declarado por el PDF. Solo se admiten flujos simples sin compresión o FlateDecode, sin parámetros avanzados. Los nombres Unicode se preservan y los de descarga se limpian. Retirar del listado no es borrado seguro: otras referencias y versiones pueden retener datos. No incluye portfolios ni gestión de capas.

**Bates.** Hasta 10 PDF y 100 páginas en total, secuencia máxima 999999 y hasta 8 cifras de relleno. Numeración vectorial en pie derecho; prefijo/sufijo latinos de hasta 40 caracteres, fuente Helvetica de 9 puntos. Valida todos los archivos antes de ofrecer ZIP; un fallo no entrega un lote parcial. La vista previa muestra la primera página del primer documento: revisa los demás archivos al descargar. El manifiesto registra nombre de salida, páginas, primer/último identificador y SHA-256 del origen y salida. No elimina numeraciones anteriores ni evita superponerse a pies existentes. No permite PDF firmados o sin modificación; fuentes adicionales con contraseña requieren abrir previamente una copia autorizada.

**Tablas.** Hasta 20 páginas, 100 tablas y 50000 celdas por extracción; límites adicionales de tamaño y complejidad por página. La revisión muestra hasta 20 filas/columnas por tabla; el CSV contiene el resultado completo. Bordes o alineación pueden producir detecciones incompletas y celdas combinadas necesitan revisión. Los valores que comienzan, tras espacios, por `=`, `+`, `-` o `@` reciben un apóstrofo; esto también afecta negativos y se declara en el manifiesto. No exporta un libro Excel ni reconstruye su formato.

**Firma visual.** Hasta 50 trazos y 10000 puntos; se ajusta proporcionalmente al recuadro con margen. Se guarda como una anotación Ink con varios trazos, nombre descriptivo opcional y aviso de ausencia de certificado. Es editable, reversible y compatible con proyecto/recuperación de la versión aplicada. No valida identidad ni integridad, no es firma digital y no equivale a solicitar firmas remotas. Los trazos sin aplicar no se guardan.

**Movimiento de marcas.** Notas Text y rectángulos Square compatibles, por coordenadas, conservando tamaño. Se mantiene la geometría con páginas recortadas y giros de 0/90/180/270°. El resto de vértices, redimensionado importado, grupos y conversaciones siguen pendientes. Bloqueos y permisos anteriores se conservan.

**OCR con giro.** Corrección manual de 0/90/180/270° para reconocer escaneos físicamente ladeados. Se aplica al mapa de reconocimiento y se invierte al colocar la capa, sin girar ni recomprimir la imagen original. Los límites e idiomas de 0.17 se conservan. No hay detección automática, corrección de perspectiva ni garantía de exactitud de caracteres.

## Censura y saneamiento: alcance preciso

La salida se genera con redacciones nativas aplicadas, retirada de texto intersectado, sustitución de píxeles de imagen afectados y eliminación de trazos que toquen la región. Puede retirar un trazo completo aunque solo una parte se cruce. La aplicación no entrega un rectángulo que simplemente tape el original.

La copia retira comentarios/anotaciones, enlaces, adjuntos, marcadores, scripts, miniaturas y metadatos del documento, además de referencias estructurales/alternativas que podrían retener información. Vacía los recursos EmbeddedFile antes de compactar y reescribe sin guardado incremental, con limpieza de recursos y eliminación de objetos no usados. Conserva el texto fuera de las regiones: no debe interpretarse como una eliminación de toda información sensible del documento.

Se admiten hasta 100 regiones y 20 páginas por solicitud; la interfaz prepara regiones de la página actual. Bloquea PDF firmados, capas, campos sin aplanar, censuras previas sin aplicar, páginas con Form XObjects, contenido marcado, imágenes en línea, patrones/sombreados, imágenes compartidas y estructuras o recursos superiores a los límites. Son restricciones conservadoras, no soporte pendiente simulado. El OCR generado en 0.17 usa Form XObjects: esas páginas todavía se bloquean para esta censura inicial. No se certifica eliminación forense universal ni se admiten todas las estructuras PDF.

**El original, el proyecto, el historial y la recuperación conservan el contenido sin censurar.** La herramienta exige reconocer este alcance y revisar la copia antes de descargar; no reemplaza el estado de trabajo por una versión aparentemente saneada. Comparte solo el PDF censurado tras comprobar todas sus páginas. Si hay otra aparición del dato fuera de las regiones, permanece y debe censurarse por separado.

## Evidencia

- 868 pruebas Python y 63 JavaScript: **931 pruebas automáticas aprobadas** en Linux, compilación de producción y recorrido Chromium de los flujos anteriores y los nuevos.
- 106 pruebas nuevas de motor/API: permisos, conservación de cifrado/restricciones, Unicode y caracteres escapados, límites, descompresión acotada, lotes y manifiestos, tablas/CSV, posiciones, firma, OCR y censura.
- Censura verificada en texto y escaneados, con los cuatro giros y recortes: se inspeccionan texto, objetos/streams, adjuntos, metadatos y recursos de imagen; los píxeles retirados ya no están en la imagen extraíble. Poppler `pdftotext` contrasta la ausencia del texto censurado en salidas digitales; no es una auditoría independiente completa de seguridad.
- OCR: se comprueba posición del texto reconocido y píxeles originales con cuatro orientaciones físicas y giros PDF adicionales.
- Chromium inspecciona descargas reales de ZIP/CSV/adjuntos/PDF y prueba etiquetas, deshacer, vistas previas, firma manuscrita, movimiento, censura y OCR ladeado.
- La autoprueba del portable incorpora etiquetas Unicode, adjunto, Bates, firma y censura, además de OCR y cifrado. Se ejecuta con Python Linux en una carpeta preparada; la entrega Windows se verifica estáticamente. **No se ha ejecutado en Windows.**

## Próximo bloque recomendado

1. Formularios con radios, campos compartidos y jerarquías: validar árbol, valores heredados y apariencias con lectores externos antes de permitir escritura. Se posponen expresamente; no se cuentan como implementados en 0.18.
2. Censura sobre estructuras complejas/OCR y corpus real, validación externa de imágenes y objetos; más edición de anotaciones importadas.
3. Conservar fuentes/estilos originales y ampliar reflujo de párrafos; imágenes anidadas, recorte interno y edición gráfica.
4. Conversión Word/Excel/Office, compresión con pérdida controlada y procesamiento general por lotes.
5. Firmas digitales, accesibilidad/estándares y prueba real del portable Windows. La firma visual y el saneamiento inicial no sustituyen estos trabajos.
