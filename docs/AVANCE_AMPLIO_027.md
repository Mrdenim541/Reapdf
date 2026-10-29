# Avance amplio 0.27

Este corte incorpora tres asistentes separados en sus áreas de trabajo y amplía el catálogo a 51 herramientas. Los cambios del PDF conservan historial, proyectos y recuperación; las exportaciones son copias independientes.

## Propiedades de campos existentes

En **Formularios y firmas → Propiedades de campos existentes**, elige un campo y ajusta descripción emergente, obligatoriedad, solo lectura y límite de caracteres de texto. Los campos compatibles admiten Helvetica, Times o Courier, tamaño automático o 6–72 pt, colores, borde y fondo. El apartado de formato se despliega cuando se necesita.

La geometría X/Y/ancho/alto afecta únicamente a la posición elegida; las propiedades del campo lógico afectan a sus posiciones compartidas. Se admiten los cuatro giros de página y recortes desplazados. El área debe permanecer dentro de la página y medir al menos 15 × 15 pt. Solo una vista previa vigente permite aplicar los cambios. Se conservan nombres, valores actuales, valores de restablecimiento y otros campos.

Un campo marcado como solo lectura para rellenado puede desbloquearse desde este asistente si la estructura y los permisos permiten editarlo. No se desbloquean contenedores heredados ni anotaciones protegidas. Acciones, XFA, giro interno del Widget, fuentes o estilos no verificados quedan protegidos. No se renombran campos, cambian tipos u opciones de listas. Casillas y radios conservan símbolos y apariencias compatibles; cambiar tamaño puede escalar su apariencia, y las etiquetas impresas no se trasladan con el campo. Los radios no admiten cambios de formato aquí. El indicador obligatorio no impide guardar vacío.

## Comentarios, respuestas y estados

En **Comentar → Comentarios y revisión**, busca por contenido o autor, filtra por estado y selecciona una conversación y su mensaje. Puedes corregir contenido/autor compatibles, responder, establecer un estado de revisión o retirar una nota de texto sin descendientes. Cada aplicación crea una versión reversible. Las conversaciones se consultan de nuevo al reabrir el asistente.

Las respuestas usan relaciones PDF nativas `/IRT`; los estados usan `/StateModel (Review)` y `/State`, con Pendiente, Aceptado, Rechazado, Cancelado y Completado. Los registros de estado se ocultan en la página para evitar iconos adicionales, pero permanecen en la conversación. El estado mostrado es el último registro en el orden de anotaciones del PDF, sin inferir una cronología por fechas. Los registros de estado no se editan ni eliminan en este asistente.

El informe **JSON o CSV** contiene todos los comentarios del documento, independientemente de los filtros visibles: página, autor, contenido, relaciones, fechas y estado. JSON añade restricciones y huella SHA-256 del PDF revisado. El CSV usa UTF-8 con BOM y protege celdas que podrían interpretarse como fórmulas. Exportar requiere permiso de copia; modificar requiere permiso de anotación. El informe no modifica el historial.

Límites: 2000 anotaciones, 16 niveles de conversación, 4000 caracteres por contenido y 100 por autor. Contenido importado mayor se presenta truncado y protegido. Ciclos, referencias ausentes, conversaciones entre páginas, relaciones de agrupación, acciones, capas, bloqueos y tipos especiales quedan de solo lectura. No se incluye colaboración remota, importación XFDF/FDF ni validación en la interfaz de Adobe/Nitro.

## Texto editable a Word

En **Convertir y OCR → Exportar texto a Word**, elige páginas y si deseas conservar saltos de línea. Pulsa **Revisar exportación Word** y comprueba las páginas con texto, páginas sin texto y tamaños ajustados antes de **Descargar Word editable**. Cambiar opciones exige revisar de nuevo. El PDF abierto permanece intacto.

Se genera un DOCX OOXML con texto digital editable, párrafos, formato básico de tamaño/color/negrita/cursiva y secciones por página. Las fuentes base se asignan a Arial, Times New Roman o Courier New según corresponda. Cada sección aproxima el tamaño visible de la página; las dimensiones superiores al límite de Word se reducen y se informan. Los valores visibles de campos que el extractor entregue pueden aparecer como texto plano.

Esta exportación no reconstruye imágenes, tablas, campos interactivos, enlaces, fuentes incrustadas ni maquetación exacta. Tampoco aplica OCR: un documento sin texto digital debe pasar primero por OCR y revisión. Unir líneas no corrige guiones automáticamente. Límites: 50 páginas, 100 000 caracteres, 20 000 fragmentos y 20 MB de salida. Se respetan los permisos de copia.

El paquete se verifica por XML y con el lector independiente python-docx disponible en este entorno. La apariencia en Microsoft Word o LibreOffice sigue pendiente de prueba. No equivale a conversión Office completa ni permite importar documentos Word.

## Estimación y siguientes trabajos

**82 % ±5 puntos** del plan propio: 81,75 puntos ponderados manteniendo los pesos anteriores. Revisión sube de 90 a 95 % (+0,5 global); conversión de 55 a 65 % (+1,5) con crédito parcial por DOCX textual; formularios de 85 a 90 % (+0,75); herramientas profesionales de 70 a 75 % (+0,5) por informes de revisión. Las demás coberturas permanecen iguales.

No se declara 95 %: faltan conversiones Office con fidelidad comprobada, certificados y firmas digitales, estándares y accesibilidad, estructuras complejas de edición/censura y validación real del ejecutable propio en Windows. El porcentaje estima cobertura, no horas restantes ni paridad con Acrobat. No se genera un nuevo portable.

Siguiente orden recomendado:

1. Ampliar la conversión a Word con imágenes y tablas, informe de pérdidas y comparación sobre documentos representativos; evaluar después importación Office con motor y licencia adecuados.
2. Ampliar formularios existentes con renombrado y opciones de listas, cuidando grupos y referencias; contrastar conversaciones y campos en lectores externos.
3. Incorporar firmas con certificados y validación independiente, estándares y accesibilidad con criterios propios.
4. Preparar y validar el ejecutable Windows con logo, ventana propia, apertura de archivos y recuperación cuando corresponda la entrega.

## Capturas del avance

- [Propiedades de campos](images/Reapdf-Propiedades-campos-0.27.png).
- [Comentarios y revisión](images/Reapdf-Comentarios-0.27.png).
- [Exportación a Word](images/Reapdf-Word-0.27.png).


Validación del cierre 0.27: **1302 pruebas Python y 83 JavaScript aprobadas (1385 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Se comprueban campos con giros/recorte y grupos, valores y apariencias, respuestas/estados nativos e informes, DOCX y lectura independiente con python-docx, historial/proyectos/recuperación y las funciones anteriores. Poppler contrasta texto y apariencia; un estado de revisión oculto no cambia los píxeles de la página. La apariencia en Word/LibreOffice, lectores comerciales y ejecución Windows nativa sigue pendiente. No se generaron nuevos portables.
