# Crear y exportar imágenes — versión 0.16

## Crear un PDF

**Crear PDF desde imágenes** está disponible desde la bienvenida y con un documento abierto. Añade PNG/JPEG y ordena las imágenes con las flechas; cada entrada genera una página. Puedes quitar una entrada antes de crear.

Elige A4, Carta o **Tamaño según imagen y resolución**. A4/Carta centran la imagen dentro del margen, conservando la proporción. Tamaño según imagen usa `píxeles × 72 / ppp`, más dos márgenes, para calcular las dimensiones físicas en puntos PDF. Elige 72, 150, 300 o 600 ppp y un margen entre 0 y 144 pt. Esta resolución determina el tamaño físico, sin añadir detalle ni volver a muestrear la imagen.

**Crear y abrir PDF** abre un documento nuevo; guarda el proyecto o exporta antes de reemplazar una sesión abierta. El nuevo documento se puede organizar, anotar, guardar como proyecto y exportar mediante las herramientas habituales. El archivo no se guarda en tu carpeta hasta que descargues una copia o proyecto.

Límites: 1–30 imágenes, 2 MB y 24 millones de píxeles por imagen, 20 MB de archivos por lote y páginas entre 10 y 3000 pt por dimensión. Solo PNG y JPEG válidos. El motor comprueba las dimensiones antes de decodificar. Conserva los píxeles originales, el flujo JPEG original y la transparencia PNG. El papel visible es blanco.

La creación desde imágenes no corrige EXIF ni trata perfiles de color especiales; no importa TIFF/HEIC u Office. El OCR español/inglés y la exportación Word de los avances posteriores se usan en sus asistentes separados. Revisa especialmente fotografías con orientación o perfiles especiales.

## Exportar páginas como imágenes

En **Páginas → Exportar páginas como imágenes**, elige rango, formato y resolución. El rango conserva su orden: `3, 1` descarga primero la tercera página y después la primera. El valor inicial es la página actual.

- PNG: compresión sin pérdida, fondo blanco.
- JPEG: fondo blanco, calidad entre 50 y 100; valores altos aumentan el tamaño.
- Resolución: 72, 150, 300 o 600 ppp. A4 a 150 ppp produce aproximadamente 1240 × 1754 píxeles; se incluyen los metadatos de resolución.

**Descargar imágenes en ZIP** incluye los cambios ya aplicados: texto, imágenes, marcas, encabezados y valores de formulario. Los nombres llevan orden de salida y página de origen, por ejemplo `001-pagina-003.png`. No modifica el PDF abierto ni marca su sesión como guardada.

Hasta 50 páginas por lote, 24 millones de píxeles y 8192 px por lado en cada imagen, 120 millones de píxeles totales y 100 MB de ZIP. Si se supera un límite, el programa informa del error; reduce el rango o la resolución. No disminuye automáticamente la resolución solicitada. El límite de píxeles se comprueba antes de rasterizar; el tamaño comprimido se controla al escribir cada imagen.

Se requiere permiso de copia/extracción del PDF. La salida es una imagen de la página visible, con su giro y recorte; no incluye contenido fuera del CropBox. No conserva texto seleccionable, marcadores, capas, campos editables ni firmas digitales. Aumentar resolución no recupera detalle ausente de un escaneado.

Las pruebas verifican conservación de imágenes insertadas, transparencia, JPEG original, dimensiones, resolución, orden, giros/recorte, permisos, límites y contenido editado. Chromium comprueba el PDF y el ZIP descargados, incluidos píxeles exactos del formulario relleno en PNG. Windows nativo y lectores externos siguen pendientes.

Desde 0.27 se exporta texto digital a DOCX editable con formato básico y secciones por página, revisión obligatoria e informe de pérdidas. No reconstruye imágenes, tablas o maquetación, ni realiza OCR implícito. Guía: [AVANCE_AMPLIO_027.md](AVANCE_AMPLIO_027.md).

Desde 0.28 Word admite opcionalmente imágenes compatibles y tablas rectangulares editables, con revisión de celdas y motivos de omisión. No reconstruye maquetación exacta ni importa Office. Guía: [AVANCE_AMPLIO_028.md](AVANCE_AMPLIO_028.md).

Desde 0.30 hay una copia PDF/A-2b con Ghostscript y validación veraPDF antes de descargar, límites conservadores y revisión visual de la primera página. No equivale a PDF/UA ni conserva interactividad/etiquetas no admitidas. Guía: [ESTANDARES_Y_ACCESIBILIDAD.md](ESTANDARES_Y_ACCESIBILIDAD.md).
