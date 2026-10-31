# Manual de funciones de Reapdf

Este manual describe las herramientas del código actual. No declara que el programa esté al 100 % ni que todas las variantes de PDF sean compatibles. Se actualizará y acompañará al ejecutable final. Tus revisiones personales se realizarán después de la entrega técnica; las comprobaciones automáticas son responsabilidad del desarrollo.

Las confirmaciones de OCR, censura, firma, tablas o cambios destructivos forman parte del uso normal. Posponer la prueba personal no elimina esas protecciones.

## Operaciones generales de escritorio

| Función | Uso y resultado esperado |
| --- | --- |
| Abrir PDF | Archivo → Abrir o Ctrl+O. Se abre en la ventana propia de Reapdf; solicita contraseña si está cifrado. |
| Guardar PDF | Ctrl+S confirma la escritura del contenido aplicado. Cancelar o fallar conserva el estado pendiente. |
| Guardar como | Ctrl+Shift+S elige otro destino y permite conservar el original. |
| Exportar copia | Prepara un PDF con los cambios aplicados y avisa de borradores pendientes. |
| Proyecto editable | Guardar proyecto conserva PDF y estado editable. Abrir verifica su integridad antes de adoptarlo. |
| Recuperación | Al iniciar, ofrece restaurar trabajo aplicado recuperable sin sobrescribir silenciosamente el original. |
| Deshacer/rehacer | Revierte o restaura operaciones y versiones durante la sesión. |
| Imprimir | Archivo → Imprimir o Ctrl+P prepara el PDF editado. La impresión física y Windows aún requieren comprobación técnica. |
| Navegar y ampliar | Usa página, miniaturas, marcadores, zoom y ajustes de ancho/página. |
| Seleccionar y copiar | En Leer, selecciona texto y pulsa Ctrl+C. Un escaneado requiere OCR. |
| Buscar | Introduce texto y recorre coincidencias en el documento editado. |
| Crear desde imágenes | Archivo → Crear PDF desde imágenes: carga, ordena y configura papel/márgenes. |
| Crear desde Word | Archivo → Crear PDF desde Word: carga DOCX y revisa la conversión. No hay garantía de fidelidad universal. |
| Herramientas y favoritos | Cambia de área o busca por nombre. Aplica o cancela los borradores antes de cambiar de tarea. |
| Instancia y cierre | La aplicación propia recibe nuevos archivos y protege borradores u operaciones pendientes al cerrar. |

## Índice de herramientas

**Leer**: [Lectura](#funcion-view), [Accesibilidad y preparación](#funcion-accessibility), [Revisar documento](#funcion-review), [Comparar documentos](#funcion-compare), [Archivos adjuntos](#funcion-attachments), [Propiedades del PDF](#funcion-metadata).

**Editar**: [Preparar fuentes variables](#funcion-variable_fonts), [Buscar y reemplazar](#funcion-find_replace), [Editar texto](#funcion-text), [Reemplazar bloque de texto](#funcion-paragraph), [Añadir texto](#funcion-textbox), [Enlaces](#funcion-link), [Editar enlaces del PDF](#funcion-existing_links), [Imágenes](#funcion-images), [Editar imágenes del PDF](#funcion-existing_images), [Encabezados y pies](#funcion-headers), [Continuar texto entre regiones](#funcion-flow), [Marca de agua](#funcion-watermark).

**Comentar**: [Seleccionar marca](#funcion-select), [Resaltar](#funcion-highlight), [Subrayar](#funcion-underline), [Tachar](#funcion-strikeout), [Nota](#funcion-note), [Lápiz](#funcion-ink), [Línea](#funcion-line), [Flecha](#funcion-arrow), [Rectángulo](#funcion-rectangle), [Sellos](#funcion-stamp), [Comentarios y revisión](#funcion-comments).

**Organizar páginas**: [Organizar páginas](#funcion-organizer), [Unir o insertar PDF](#funcion-insert), [Reemplazar páginas](#funcion-replace), [Duplicar páginas](#funcion-duplicate), [Página en blanco](#funcion-blank), [Recortar páginas](#funcion-crop), [Dividir PDF](#funcion-split), [Etiquetas de página](#funcion-labels), [Editar marcadores](#funcion-bookmarks), [Numerar páginas](#funcion-numbering), [Numeración Bates por lotes](#funcion-bates).

**Formularios y firmas**: [Rellenar formulario](#funcion-forms), [Propiedades de campos existentes](#funcion-field_properties), [Crear o eliminar campos](#funcion-field), [Datos de formulario](#funcion-data), [Aplanar formulario](#funcion-flatten), [Firmar con certificado](#funcion-digital_sign), [Verificar firmas digitales](#funcion-verify_signatures), [Firma visual manuscrita](#funcion-signature), [Cálculos automáticos del proyecto](#funcion-form_rules), [Calcular valores de campos](#funcion-calculate).

**Convertir y OCR**: [Extraer tabla por región](#funcion-table_region), [OCR de región](#funcion-region_ocr), [Crear copia PDF/A-2b](#funcion-archive), [Reconocer texto (OCR)](#funcion-ocr), [Exportar páginas como imágenes](#funcion-export_images), [Exportar tablas a CSV](#funcion-tables), [Exportar texto a Word](#funcion-docx), [Exportar texto](#funcion-export_text), [Recetas de trabajo](#funcion-automation), [Procesar varios PDF](#funcion-batch), [Reducir imágenes del PDF](#funcion-compress), [Optimizar PDF](#funcion-optimize).

**Documentos**: [Etiquetas y orden de lectura](#funcion-structure), [Intercambiar XFDF](#funcion-xfdf), [Vincular documentos](#funcion-document_links), [Medir planos](#funcion-measurement), [Capas del PDF](#funcion-layers), [Portfolio PDF](#funcion-portfolio).

**Proteger**: [Inspección de impresión](#funcion-preflight), [Copia de trabajo sin firmas](#funcion-working_copy), [Validar estándares PDF](#funcion-standards), [Proteger copia](#funcion-protect), [Censurar y sanear copia](#funcion-redact).

## Leer

<a id="funcion-view"></a>

### Lectura

**Acceso:** Leer → Lectura.

1. Abre el PDF.
2. elige Leer.
3. navega por páginas y ajusta el zoom.

**Resultado esperado:** La página se muestra con el giro correcto y la resolución se adapta al zoom.

**Límites actuales:** Un escaneado requiere OCR para seleccionar su texto; las capas ocultas siguen ocultas.

<a id="funcion-accessibility"></a>

### Accesibilidad y preparación

**Acceso:** Leer → Accesibilidad y preparación.

1. Abre Accesibilidad y preparación.
2. revisa el diagnóstico.
3. configura título e idioma y aplica.

**Resultado esperado:** Los metadatos de accesibilidad se actualizan sin inventar etiquetas.

**Límites actuales:** El diagnóstico no certifica PDF/UA; el etiquetado se gestiona en su herramienta propia.

<a id="funcion-review"></a>

### Revisar documento

**Acceso:** Leer → Revisar documento.

1. Abre Revisar documento.
2. ejecuta la inspección.
3. consulta páginas y hallazgos.

**Resultado esperado:** Se muestran problemas estructurales orientativos con su ubicación.

**Límites actuales:** No equivale a certificación normativa ni a inspección forense.

<a id="funcion-compare"></a>

### Comparar documentos

**Acceso:** Leer → Comparar documentos.

1. Elige Comparar documentos.
2. carga la segunda versión.
3. recorre diferencias y vistas paralelas.

**Resultado esperado:** Se localizan diferencias de texto y apariencia sin modificar los originales.

**Límites actuales:** Comparación acotada; cambios de maquetación pueden producir múltiples diferencias.

<a id="funcion-attachments"></a>

### Archivos adjuntos

**Acceso:** Leer → Archivos adjuntos.

1. Abre Archivos adjuntos.
2. selecciona un archivo.
3. añade, descarga o retira según corresponda.

**Resultado esperado:** Los bytes del adjunto se conservan y se actualiza el listado del PDF.

**Límites actuales:** Descargar no ejecuta el archivo; retirar del listado no acredita saneamiento forense.

<a id="funcion-metadata"></a>

### Propiedades del PDF

**Acceso:** Leer → Propiedades del PDF.

1. Abre Propiedades del PDF.
2. modifica los campos editables.
3. aplica y guarda.

**Resultado esperado:** Título, autor y demás propiedades seleccionadas persisten al reabrir.

**Límites actuales:** Los campos protegidos o no interpretables no se reescriben automáticamente.

## Editar

<a id="funcion-variable_fonts"></a>

### Preparar fuentes variables

**Acceso:** Editar → Preparar fuentes variables.

1. Elige Preparar fuentes variables.
2. revisa los ejes detectados.
3. confirma la instancia compatible.

**Resultado esperado:** Se crea una fuente estática predeterminada solo si texto y apariencia superan la comprobación.

**Límites actuales:** No permite cualquier eje o instancia que altere el renderizado sin verificar.

<a id="funcion-find_replace"></a>

### Buscar y reemplazar

**Acceso:** Editar → Buscar y reemplazar.

1. Abre Buscar y reemplazar.
2. escribe búsqueda y sustitución y el alcance.
3. revisa coincidencias y aplica el lote.

**Resultado esperado:** Se sustituyen las coincidencias seleccionadas de forma atómica y reversible.

**Límites actuales:** Búsqueda literal; fuentes, geometrías o coincidencias incompatibles se explican y protegen.

<a id="funcion-text"></a>

### Editar texto

**Acceso:** Editar → Editar texto.

1. Elige Editar texto.
2. pulsa el texto directamente en la página.
3. escribe y aplica o usa Ctrl+Enter.

**Resultado esperado:** El contenido nuevo se guarda con la fuente y geometría originales compatibles.

**Límites actuales:** No se exige localizar el texto en una lista lateral. Un escaneado necesita OCR; fuentes y composiciones no verificables permanecen protegidas.

<a id="funcion-paragraph"></a>

### Reemplazar bloque de texto

**Acceso:** Editar → Reemplazar bloque de texto.

1. Elige Reemplazar bloque de texto.
2. selecciona el bloque o dibuja su región.
3. ajusta texto, formato y ajuste antes de aplicar.

**Resultado esperado:** El bloque compatible se sustituye conservando contenido vecino y mostrando el ajuste.

**Límites actuales:** Sustituir con una fuente incluida puede cambiar métricas; no se descartan transformaciones o composición complejas.

<a id="funcion-textbox"></a>

### Añadir texto

**Acceso:** Editar → Añadir texto.

1. Elige Añadir texto.
2. pulsa una posición y escribe.
3. ajusta ancho, tamaño y color y aplica.

**Resultado esperado:** Se añade texto con altura automática dentro de la página.

**Límites actuales:** La fuente incluida debe cubrir los caracteres y el texto debe caber sin colisión.

<a id="funcion-link"></a>

### Enlaces

**Acceso:** Editar → Enlaces.

1. Elige Enlaces.
2. marca el área.
3. define página o dirección web y aplica.

**Resultado esperado:** La región abre el destino al usar el modo de lectura.

**Límites actuales:** Se admiten destinos compatibles; las direcciones no se ejecutan durante la edición.

<a id="funcion-existing_links"></a>

### Editar enlaces del PDF

**Acceso:** Editar → Editar enlaces del PDF.

1. Abre Editar enlaces del PDF.
2. selecciona el enlace.
3. cambia destino o región, o retíralo.

**Resultado esperado:** Se actualiza únicamente el enlace compatible seleccionado.

**Límites actuales:** Acciones especiales o ambiguas permanecen protegidas.

<a id="funcion-images"></a>

### Imágenes

**Acceso:** Editar → Imágenes.

1. Elige Imágenes.
2. carga PNG o JPEG.
3. coloca, redimensiona y aplica.

**Resultado esperado:** La imagen nueva conserva sus píxeles originales al guardar.

**Límites actuales:** Ampliarla no inventa detalle; compresión y cambio de resolución son operaciones distintas.

<a id="funcion-existing_images"></a>

### Editar imágenes del PDF

**Acceso:** Editar → Editar imágenes del PDF.

1. Abre Editar imágenes del PDF.
2. selecciona una imagen existente.
3. revisa y aplica el cambio compatible.

**Resultado esperado:** Se mueve, reemplaza o retira la aparición compatible y se conserva el resto del documento.

**Límites actuales:** Imágenes compartidas, recortadas o en estructuras complejas pueden requerir otro tratamiento.

<a id="funcion-headers"></a>

### Encabezados y pies

**Acceso:** Editar → Encabezados y pies.

1. Abre Encabezados y pies.
2. introduce contenido y alcance.
3. revisa posición y aplica.

**Resultado esperado:** Se incorporan encabezados y pies en las páginas elegidas.

**Límites actuales:** Debe revisarse el espacio disponible para no cubrir contenido.

<a id="funcion-flow"></a>

### Continuar texto entre regiones

**Acceso:** Editar → Continuar texto entre regiones.

1. Elige Continuar texto entre regiones.
2. marca y ordena las regiones.
3. revisa estilo, distribución y aplica.

**Resultado esperado:** El texto se distribuye por el recorrido seleccionado sin publicar una distribución parcial.

**Límites actuales:** Las regiones deben ser compatibles; no es reflujo general de cualquier PDF.

<a id="funcion-watermark"></a>

### Marca de agua

**Acceso:** Editar → Marca de agua.

1. Elige Marca de agua.
2. define texto, apariencia y páginas.
3. revisa y aplica.

**Resultado esperado:** La marca aparece en las páginas seleccionadas y persiste al guardar.

**Límites actuales:** No es una firma digital ni protección contra copia.

## Comentar

<a id="funcion-select"></a>

### Seleccionar marca

**Acceso:** Comentar → Seleccionar marca.

1. Elige Seleccionar marca.
2. pulsa la anotación.
3. mueve, ajusta propiedades o elimina.

**Resultado esperado:** Se modifica únicamente la anotación seleccionada y el cambio puede deshacerse.

**Límites actuales:** Solo se habilitan propiedades verificables del tipo de anotación.

<a id="funcion-highlight"></a>

### Resaltar

**Acceso:** Comentar → Resaltar.

1. Elige Resaltar.
2. selecciona palabras o fragmentos.
3. guarda el PDF.

**Resultado esperado:** La anotación queda alineada con el texto seleccionado y persiste.

**Límites actuales:** La selección precisa depende de texto digital compatible; no se reconoce texto por apariencia.

<a id="funcion-underline"></a>

### Subrayar

**Acceso:** Comentar → Subrayar.

1. Elige Subrayar.
2. selecciona el texto.
3. guarda.

**Resultado esperado:** Se crea un subrayado nativo sobre el texto elegido.

**Límites actuales:** La geometría de texto oblicuo o complejo puede permanecer protegida.

<a id="funcion-strikeout"></a>

### Tachar

**Acceso:** Comentar → Tachar.

1. Elige Tachar.
2. selecciona el texto.
3. guarda.

**Resultado esperado:** Se crea una anotación de tachado sin eliminar el texto original.

**Límites actuales:** Tachar no es censurar: el texto continúa en el PDF.

<a id="funcion-note"></a>

### Nota

**Acceso:** Comentar → Nota.

1. Elige Nota.
2. pulsa la ubicación.
3. escribe el comentario y aplica.

**Resultado esperado:** La nota mantiene posición y contenido al reabrir.

**Límites actuales:** No altera el texto de la página.

<a id="funcion-ink"></a>

### Lápiz

**Acceso:** Comentar → Lápiz.

1. Elige Lápiz.
2. ajusta color y grosor.
3. dibuja sobre la página y guarda.

**Resultado esperado:** Los trazos se conservan como anotaciones PDF.

**Límites actuales:** Para mover un trazo, cambia a selección; dibujar encima no elimina contenido.

<a id="funcion-line"></a>

### Línea

**Acceso:** Comentar → Línea.

1. Elige Línea.
2. define origen y extremo.
3. ajusta apariencia y guarda.

**Resultado esperado:** Se conserva una línea editable con coordenadas correctas.

**Límites actuales:** No representa una medición calibrada.

<a id="funcion-arrow"></a>

### Flecha

**Acceso:** Comentar → Flecha.

1. Elige Flecha.
2. arrastra entre sus extremos.
3. guarda.

**Resultado esperado:** Se conserva una anotación con punta de flecha.

**Límites actuales:** Para precisión técnica utiliza Medir planos.

<a id="funcion-rectangle"></a>

### Rectángulo

**Acceso:** Comentar → Rectángulo.

1. Elige Rectángulo.
2. arrastra el área.
3. ajusta color y grosor y guarda.

**Resultado esperado:** El marco se conserva como anotación.

**Límites actuales:** Un rectángulo opaco no acredita eliminación del contenido inferior.

<a id="funcion-stamp"></a>

### Sellos

**Acceso:** Comentar → Sellos.

1. Elige Sellos.
2. selecciona un sello compatible.
3. ubícalo y aplica.

**Resultado esperado:** La marca visual persiste en la página.

**Límites actuales:** Un sello visual no acredita firma criptográfica ni aprobación legal.

<a id="funcion-comments"></a>

### Comentarios y revisión

**Acceso:** Comentar → Comentarios y revisión.

1. Abre Comentarios y revisión.
2. selecciona una conversación.
3. responde, cambia un estado compatible o exporta.

**Resultado esperado:** Se conservan autor, contenido y relaciones compatibles.

**Límites actuales:** Los grafos o tipos no interpretables se protegen; la aceptación externa depende del lector.

## Organizar páginas

<a id="funcion-organizer"></a>

### Organizar páginas

**Acceso:** Organizar páginas → Organizar páginas.

1. Abre Organizar páginas.
2. selecciona páginas.
3. cambia orden, giro o retira y aplica.

**Resultado esperado:** Se conserva el orden solicitado y se actualiza la navegación compatible.

**Límites actuales:** Documentos con estructuras no verificables pueden necesitar una copia preparada.

<a id="funcion-insert"></a>

### Unir o insertar PDF

**Acceso:** Organizar páginas → Unir o insertar PDF.

1. Elige Unir o insertar PDF.
2. carga el segundo archivo y selecciona páginas.
3. define posición y aplica.

**Resultado esperado:** Se incorporan las páginas elegidas sin sobrescribir las fuentes.

**Límites actuales:** Formularios, etiquetas y estructuras especiales se incorporan solo cuando son compatibles.

<a id="funcion-replace"></a>

### Reemplazar páginas

**Acceso:** Organizar páginas → Reemplazar páginas.

1. Elige Reemplazar páginas.
2. selecciona el bloque de origen y el archivo nuevo.
3. revisa y aplica.

**Resultado esperado:** Se reemplaza el bloque solicitado y se conserva el resto.

**Límites actuales:** La estructura y los vínculos especiales requieren compatibilidad verificable.

<a id="funcion-duplicate"></a>

### Duplicar páginas

**Acceso:** Organizar páginas → Duplicar páginas.

1. Elige Duplicar páginas.
2. indica las páginas y posición.
3. aplica.

**Resultado esperado:** Se crean copias independientes de las páginas compatibles.

**Límites actuales:** No se duplica ciegamente una estructura que pueda producir referencias ambiguas.

<a id="funcion-blank"></a>

### Página en blanco

**Acceso:** Organizar páginas → Página en blanco.

1. Elige Página en blanco.
2. define tamaño y posición.
3. aplica.

**Resultado esperado:** Se inserta una página vacía en el lugar elegido.

**Límites actuales:** No contiene por sí sola texto, formulario ni escala técnica.

<a id="funcion-crop"></a>

### Recortar páginas

**Acceso:** Organizar páginas → Recortar páginas.

1. Abre Recortar páginas.
2. marca o introduce los márgenes y el alcance.
3. revisa y aplica.

**Resultado esperado:** Cambia el área visible conservando el contenido del PDF y la posibilidad compatible de restaurarlo.

**Límites actuales:** Recortar no elimina datos sensibles ni sustituye la censura.

<a id="funcion-split"></a>

### Dividir PDF

**Acceso:** Organizar páginas → Dividir PDF.

1. Elige Dividir PDF.
2. define rangos, bloques o marcadores y nombres.
3. revisa los archivos y exporta.

**Resultado esperado:** Se obtiene un ZIP de PDF independientes con nombres personalizados.

**Límites actuales:** Las estructuras no divisibles de forma verificada se protegen; no se atribuye validez de firmas a archivos nuevos.

<a id="funcion-labels"></a>

### Etiquetas de página

**Acceso:** Organizar páginas → Etiquetas de página.

1. Abre Etiquetas de página.
2. define rangos y formato.
3. aplica.

**Resultado esperado:** La navegación utiliza etiquetas personalizadas, decimales o romanas.

**Límites actuales:** La etiqueta de navegación no añade un número visible en el papel.

<a id="funcion-bookmarks"></a>

### Editar marcadores

**Acceso:** Organizar páginas → Editar marcadores.

1. Elige Editar marcadores.
2. ajusta título, jerarquía y destino.
3. guarda.

**Resultado esperado:** El índice compatible mantiene su estructura y destinos al reabrir.

**Límites actuales:** Los destinos o acciones especiales pueden mantenerse en lectura.

<a id="funcion-numbering"></a>

### Numerar páginas

**Acceso:** Organizar páginas → Numerar páginas.

1. Elige Numerar páginas.
2. define rango, inicio, formato y posición.
3. revisa y aplica.

**Resultado esperado:** Se añade numeración visible según las reglas indicadas.

**Límites actuales:** Es distinta de las etiquetas internas de navegación.

<a id="funcion-bates"></a>

### Numeración Bates por lotes

**Acceso:** Organizar páginas → Numeración Bates por lotes.

1. Abre Numeración Bates por lotes.
2. carga y ordena los PDF.
3. define prefijo, inicio y alcance y revisa el lote.

**Resultado esperado:** Se produce numeración continua y una salida trazable por archivo.

**Límites actuales:** Se aplican los límites de archivos/páginas del lote; originales conservados.

## Formularios y firmas

<a id="funcion-forms"></a>

### Rellenar formulario

**Acceso:** Formularios y firmas → Rellenar formulario.

1. Abre Rellenar formulario.
2. selecciona un campo en la página.
3. introduce y revisa sus valores antes de aplicar.

**Resultado esperado:** Valores y apariencias compatibles persisten al guardar.

**Límites actuales:** XFA y acciones no soportadas no se presentan como formularios completamente editables.

<a id="funcion-field_properties"></a>

### Propiedades de campos existentes

**Acceso:** Formularios y firmas → Propiedades de campos existentes.

1. Elige Propiedades de campos existentes.
2. selecciona un campo.
3. ajusta nombre, opciones o apariencia y aplica.

**Resultado esperado:** Se conservan las relaciones compatibles de campos y grupos.

**Límites actuales:** Restricciones, firmas y propiedades no verificables permanecen protegidas.

<a id="funcion-field"></a>

### Crear o eliminar campos

**Acceso:** Formularios y firmas → Crear o eliminar campos.

1. Elige Crear o eliminar campos.
2. define tipo y región, o selecciona el campo a retirar.
3. revisa y aplica.

**Resultado esperado:** Se crean o eliminan campos y grupos compatibles sin referencias rotas.

**Límites actuales:** No es un diseñador general de formularios XFA.

<a id="funcion-data"></a>

### Datos de formulario

**Acceso:** Formularios y firmas → Datos de formulario.

1. Abre Datos de formulario.
2. elige importar o exportar.
3. revisa la correspondencia de campos.

**Resultado esperado:** Se intercambian valores vinculados a identidades y estructura compatibles.

**Límites actuales:** No se aplican datos a un PDF distinto por simple coincidencia visual.

<a id="funcion-flatten"></a>

### Aplanar formulario

**Acceso:** Formularios y firmas → Aplanar formulario.

1. Elige Aplanar formulario.
2. revisa el alcance.
3. confirma la copia aplanada.

**Resultado esperado:** Los valores compatibles pasan a apariencia permanente y los campos dejan de ser interactivos.

**Límites actuales:** Aplanar cambia la editabilidad; no reemplaza una firma ni una censura.

<a id="funcion-digital_sign"></a>

### Firmar con certificado

**Acceso:** Formularios y firmas → Firmar con certificado.

1. Abre Firmar con certificado.
2. selecciona P12/PFX e introduce su contraseña.
3. revisa la copia y firma.

**Resultado esperado:** Se entrega una copia firmada y comprobada criptográficamente.

**Límites actuales:** Certificado y contraseña no se guardan en el proyecto. TSA remota y firma de larga duración siguen pendientes.

<a id="funcion-verify_signatures"></a>

### Verificar firmas digitales

**Acceso:** Formularios y firmas → Verificar firmas digitales.

1. Abre Verificar firmas digitales.
2. selecciona confianza y evidencias locales si corresponde.
3. ejecuta la comprobación.

**Resultado esperado:** Se separan integridad, revisiones, confianza, sello de tiempo y revocación local.

**Límites actuales:** No acredita revocación de TSA, validación histórica, LT/LTA ni validez jurídica universal.

<a id="funcion-signature"></a>

### Firma visual manuscrita

**Acceso:** Formularios y firmas → Firma visual manuscrita.

1. Elige Firma visual manuscrita.
2. dibuja la firma y define posición.
3. revisa y aplica.

**Resultado esperado:** Se incorpora una firma dibujada persistente.

**Límites actuales:** No contiene certificado ni acredita identidad criptográfica.

<a id="funcion-form_rules"></a>

### Cálculos automáticos del proyecto

**Acceso:** Formularios y firmas → Cálculos automáticos del proyecto.

1. Abre Cálculos automáticos del proyecto.
2. relaciona campos de origen y resultado.
3. revisa y aplica.

**Resultado esperado:** El proyecto calcula resultados según las reglas configuradas.

**Límites actuales:** Las reglas del proyecto no equivalen a ejecutar JavaScript arbitrario del PDF.

<a id="funcion-calculate"></a>

### Calcular valores de campos

**Acceso:** Formularios y firmas → Calcular valores de campos.

1. Elige Calcular valores de campos.
2. revisa reglas y dependencias.
3. confirma los resultados.

**Resultado esperado:** Se guardan valores calculados compatibles y se detectan ciclos o dependencias inválidas.

**Límites actuales:** No interpreta cualquier script; los resultados incompatibles se protegen.

## Convertir y OCR

<a id="funcion-table_region"></a>

### Extraer tabla por región

**Acceso:** Convertir y OCR → Extraer tabla por región.

1. Elige Extraer tabla por región.
2. selecciona área y, si procede, las cuatro esquinas.
3. extrae, corrige celdas y exporta.

**Resultado esperado:** Se obtiene CSV o Word con la tabla revisada y el PDF original intacto.

**Límites actuales:** OCR, combinaciones y separadores requieren revisión; no resuelve cualquier tabla irregular.

<a id="funcion-region_ocr"></a>

### OCR de región

**Acceso:** Convertir y OCR → OCR de región.

1. Abre OCR de región.
2. marca el área y corrige orientación o esquinas si procede.
3. reconoce y revisa.

**Resultado esperado:** El texto reconocido se sitúa sobre la región conservando la imagen.

**Límites actuales:** Las correcciones geométricas son acotadas; no garantizan lectura exacta de todos los caracteres.

<a id="funcion-archive"></a>

### Crear copia PDF/A-2b

**Acceso:** Convertir y OCR → Crear copia PDF/A-2b.

1. Elige Crear copia PDF/A-2b.
2. revisa las condiciones.
3. genera y consulta la validación.

**Resultado esperado:** Se entrega una copia únicamente si supera la validación disponible.

**Límites actuales:** Depende de herramientas normativas instaladas; no equivale a conservar todas las funciones interactivas.

<a id="funcion-ocr"></a>

### Reconocer texto (OCR)

**Acceso:** Convertir y OCR → Reconocer texto (OCR).

1. Elige Reconocer texto (OCR).
2. define páginas, idioma y resolución.
3. ejecuta y revisa.

**Resultado esperado:** Se añade una capa buscable sin sustituir la imagen del escaneado.

**Límites actuales:** La exactitud depende de la imagen y el idioma; se omiten o protegen páginas incompatibles.

<a id="funcion-export_images"></a>

### Exportar páginas como imágenes

**Acceso:** Convertir y OCR → Exportar páginas como imágenes.

1. Elige Exportar páginas como imágenes.
2. define páginas, formato y resolución.
3. exporta.

**Resultado esperado:** Se obtienen imágenes de las páginas editadas con el alcance indicado.

**Límites actuales:** La resolución aumenta el muestreo, no el detalle de imágenes de origen.

<a id="funcion-tables"></a>

### Exportar tablas a CSV

**Acceso:** Convertir y OCR → Exportar tablas a CSV.

1. Elige Exportar tablas a CSV.
2. selecciona las tablas detectadas.
3. revisa y exporta.

**Resultado esperado:** Se obtienen datos tabulares editables.

**Límites actuales:** Para escaneados o regiones ambiguas utiliza la extracción regional con revisión.

<a id="funcion-docx"></a>

### Exportar texto a Word

**Acceso:** Convertir y OCR → Exportar texto a Word.

1. Elige Exportar texto a Word.
2. configura el alcance.
3. revisa el resultado y exporta.

**Resultado esperado:** Se obtiene DOCX editable con contenido y estructuras compatibles.

**Límites actuales:** No se garantiza maquetación idéntica a la de cualquier PDF.

<a id="funcion-export_text"></a>

### Exportar texto

**Acceso:** Convertir y OCR → Exportar texto.

1. Elige Exportar texto.
2. define páginas.
3. descarga el archivo.

**Resultado esperado:** Se obtiene texto UTF-8 del contenido extraíble.

**Límites actuales:** No extrae texto de una imagen sin OCR ni garantiza el orden de todos los diseños complejos.

<a id="funcion-automation"></a>

### Recetas de trabajo

**Acceso:** Convertir y OCR → Recetas de trabajo.

1. Abre Recetas de trabajo.
2. elige o crea la secuencia.
3. revisa entradas, nombres y resultados antes de ejecutar.

**Resultado esperado:** Se procesan tareas compatibles en el orden de la receta con salida por archivo.

**Límites actuales:** Solo se admiten las tareas declaradas; no ejecuta instrucciones arbitrarias de documentos.

<a id="funcion-batch"></a>

### Procesar varios PDF

**Acceso:** Convertir y OCR → Procesar varios PDF.

1. Elige Procesar varios PDF.
2. carga y ordena los archivos.
3. configura la tarea y revisa la salida.

**Resultado esperado:** Cada archivo tiene resultado o fallo informado sin sobrescribir su original.

**Límites actuales:** Se aplican presupuestos de tamaño y número de archivos; no se ocultan fallos parciales.

<a id="funcion-compress"></a>

### Reducir imágenes del PDF

**Acceso:** Convertir y OCR → Reducir imágenes del PDF.

1. Abre Reducir imágenes del PDF.
2. selecciona resolución y calidad.
3. compara y aplica.

**Resultado esperado:** Se reduce el tamaño de imágenes compatibles con un informe del resultado.

**Límites actuales:** Puede perder detalle; imágenes o composiciones no compatibles se conservan o bloquean.

<a id="funcion-optimize"></a>

### Optimizar PDF

**Acceso:** Convertir y OCR → Optimizar PDF.

1. Elige Optimizar PDF.
2. ejecuta la operación.
3. consulta el tamaño y guarda la copia.

**Resultado esperado:** Se compacta la estructura compatible sin bajar deliberadamente la resolución de imágenes.

**Límites actuales:** No garantiza reducción en todos los archivos ni elimina información sensible.

## Documentos

<a id="funcion-structure"></a>

### Etiquetas y orden de lectura

**Acceso:** Documentos → Etiquetas y orden de lectura.

1. Abre Etiquetas y orden de lectura.
2. revisa estructura existente o prepara etiquetas.
3. asigna roles, orden, idioma y alternativas y aplica.

**Resultado esperado:** El árbol compatible conserva referencias reales y apariencia; admite listas y tablas revisadas.

**Límites actuales:** No certifica PDF/UA ni repara cualquier árbol o contenido mixto automáticamente.

<a id="funcion-xfdf"></a>

### Intercambiar XFDF

**Acceso:** Documentos → Intercambiar XFDF.

1. Abre Intercambiar XFDF.
2. importa o exporta anotaciones y datos.
3. confirma correspondencia y revisa conflictos.

**Resultado esperado:** Se conservan relaciones, estilos y valores de los tipos compatibles.

**Límites actuales:** No todas las variantes externas son compatibles; originales y tipos no interpretables se protegen.

<a id="funcion-document_links"></a>

### Vincular documentos

**Acceso:** Documentos → Vincular documentos.

1. Abre Vincular documentos.
2. añade archivos y asigna funciones generales.
3. relaciona identificadores o regiones y revisa destinos.

**Resultado esperado:** Se guarda un conjunto vinculado portable y se navega entre referencias verificadas.

**Límites actuales:** No supone qué archivo es registro o plano por su nombre. Las revisiones con referencias obsoletas necesitan correspondencia explícita.

<a id="funcion-measurement"></a>

### Medir planos

**Acceso:** Documentos → Medir planos.

1. Elige Medir planos.
2. calibra longitudes o selecciona Ángulo.
3. marca puntos, calcula y guarda.

**Resultado esperado:** Se conserva medición, etiqueta, unidad e identificador; los vértices compatibles pueden editarse.

**Límites actuales:** Los ángulos no requieren escala. No se infieren curvas o geometrías ausentes; los resultados técnicos requieren una referencia válida.

<a id="funcion-layers"></a>

### Capas del PDF

**Acceso:** Documentos → Capas del PDF.

1. Abre Capas del PDF.
2. elige configuración y visibilidad.
3. revisa la vista previa y guarda.

**Resultado esperado:** Se conserva el contenido y cambia el estado inicial compatible.

**Límites actuales:** Se respetan bloqueos y grupos exclusivos; reglas automáticas complejas quedan protegidas. Ocultar no es censurar.

<a id="funcion-portfolio"></a>

### Portfolio PDF

**Acceso:** Documentos → Portfolio PDF.

1. Abre Portfolio PDF.
2. organiza la presentación o las columnas.
3. revisa los cambios y guarda.

**Resultado esperado:** Los adjuntos mantienen sus bytes y las propiedades compatibles persisten.

**Límites actuales:** Columnas complejas, carpetas y reglas externas no verificables tienen límites explícitos.

## Proteger

<a id="funcion-preflight"></a>

### Inspección de impresión

**Acceso:** Proteger → Inspección de impresión.

1. Abre Inspección de impresión.
2. define la resolución mínima.
3. consulta los hallazgos por página.

**Resultado esperado:** Se informa de fuentes, imágenes, colores y cajas que requieren atención.

**Límites actuales:** Inspección orientativa; no certifica todas las condiciones de imprenta ni PDF/X.

<a id="funcion-working_copy"></a>

### Copia de trabajo sin firmas

**Acceso:** Proteger → Copia de trabajo sin firmas.

1. Elige Copia de trabajo sin firmas.
2. revisa el aviso y alcance.
3. genera una copia identificada.

**Resultado esperado:** Se obtiene una copia editable compatible sin trasladar la validez de la firma original.

**Límites actuales:** Modificar una copia no conserva una firma criptográfica válida del original.

<a id="funcion-standards"></a>

### Validar estándares PDF

**Acceso:** Proteger → Validar estándares PDF.

1. Abre Validar estándares PDF.
2. elige perfil e inicia la validación.
3. consulta reglas y resultado.

**Resultado esperado:** Se informa del cumplimiento mediante el validador externo disponible.

**Límites actuales:** Requiere la herramienta normativa instalada; una inspección orientativa no sustituye la validación PDF/A o PDF/UA.

<a id="funcion-protect"></a>

### Proteger copia

**Acceso:** Proteger → Proteger copia.

1. Elige Proteger copia.
2. define contraseña y permisos.
3. genera y abre la copia para comprobar acceso.

**Resultado esperado:** Se crea una copia cifrada compatible manteniendo la sesión original.

**Límites actuales:** Los permisos PDF no son una garantía absoluta contra lectores que los ignoren.

<a id="funcion-redact"></a>

### Censurar y sanear copia

**Acceso:** Proteger → Censurar y sanear copia.

1. Abre Censurar y sanear copia.
2. marca regiones o coincidencias.
3. revisa todas las páginas afectadas y confirma.

**Resultado esperado:** Se entrega una copia saneada solo si supera las comprobaciones previstas.

**Límites actuales:** Un rectángulo, tachado o recorte no sustituye esta operación; composiciones complejas no verificables quedan protegidas.

## Funciones complementarias

Desde el texto de la página, **Distribuir en líneas** conserva fuente y transformación originales compatibles. **Editar párrafo** permite revisar el ajuste; un párrafo transformado debe cumplir paralelismo, estilo y composición. La edición no exige localizar el texto en una lista lateral.

En **Medir planos**, «Actualizar referencia» migra mediciones antiguas interpretables con referencia nueva e identificador conservado. Los ángulos usan tres puntos y grados/radianes; los cruces de segmentos sirven como ajuste del cursor.

En **Portfolio PDF → Columnas del portfolio existente → Diseñar columnas**, crea, renombra, ordena o retira columnas compatibles. La retirada de columnas elimina sus valores y exige confirmación; no elimina los adjuntos. Tipos existentes y columnas protegidas se conservan.

En el etiquetado inicial, un objeto **Lbl** precede a su cuerpo **LI**. Las celdas vacías se añaden por tabla/fila/columna y no introducen texto ficticio.

## Capacidades todavía pendientes

La relación de pendientes técnicos está en [el plan](PLAN_ACTUAL.md): edición/composición avanzadas, reparación/accesibilidad general, XFA y scripts generales, fidelidad OCR/Office general, TSA/LT/LTA y estándares avanzados, curvas/carpetas/OCG complejos, distribución Windows y servicios remotos/IA. Una entrada de este manual no acredita todas las variantes comerciales de la función.

La entrega final incluirá ejecutable instalable o portable de Windows, esta guía actualizada, notas de compatibilidad y resultados de comprobaciones técnicas. **La revisión personal queda al final y no detiene implementaciones independientes.**
