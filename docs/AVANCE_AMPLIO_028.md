# Avance amplio 0.28

Este bloque amplía conversión a Word y diseño de formularios existentes. Las herramientas siguen dentro de sus áreas, con los ajustes avanzados plegados. No se genera un nuevo portable.

## Word con imágenes y tablas editables

En **Convertir y OCR → Exportar texto a Word**, activa las opciones que necesites:

- **Incluir imágenes compatibles**: inserta objetos de imagen entre párrafos, ajustados al área útil del papel. Un JPEG RGB compatible conserva sus bytes; otros formatos y máscaras compatibles se convierten a PNG RGB/RGBA. Se mantienen sus píxeles originales y la proporción de su área en el PDF, con tamaño ajustado para Word.
- **Detectar tablas editables con líneas**: detecta cuadrículas rectangulares y crea tablas Word con celdas editables. El texto de las celdas no se repite en los párrafos. En la revisión se puede desplegar cada tabla, ver sus primeras 20 filas y comprobar cantidades; se exportan todas las filas aceptadas.

Ambas opciones están desactivadas inicialmente para permitir una extracción de texto sencilla. **Revisar exportación Word** informa páginas, caracteres, imágenes, tablas, celdas y motivos de omisión. Cambiar páginas u opciones invalida la revisión y bloquea la descarga hasta revisarla de nuevo. La exportación incorpora las ediciones actuales, conserva su orden de páginas y no modifica la sesión ni el historial.

Las imágenes giradas/reflejadas/inclinadas internamente, recortadas por la página, mínimas, en línea, dentro de formularios gráficos o asociadas a capas/recortes/transparencia especial se omiten con motivo. Se admiten máscaras alfa estándar de imágenes independientes. Una imagen de escaneado sigue siendo una imagen: el texto editable requiere OCR previo. Los gráficos vectoriales, las superposiciones y las posiciones exactas del PDF no se reconstruyen.

Las tablas con celdas combinadas, solapamientos o texto que cruza el límite detectado se conservan como texto y se informa del rechazo. La detección puede omitir tablas sin cuadrícula; no constituye una detección universal. No se conservan anchos de columna, formato original ni estilo de texto dentro de celdas. El orden entre bloques es aproximado, de arriba abajo; no hay reconstrucción completa de columnas o maquetación.

Límites: 50 páginas sin detección de tablas; 20 con detección; 100 posiciones de imagen, 20 millones de píxeles por imagen y 20 MB de recursos; 50 tablas y 5000 celdas; 100 000 caracteres, 20 000 fragmentos y 20 MB de DOCX final. Las imágenes de más de 20 millones de píxeles se omiten con aviso. Si se supera un presupuesto acumulado se rechaza la exportación completa, sin descargar un documento parcial. Cuando no queda texto ni imagen compatible se pide OCR o revisar el contenido.

El paquete se verifica por XML y con python-docx: imágenes, relaciones, tablas, contenido de celdas y secciones. Esto acredita lectura estructural; la apariencia real en Microsoft Word/LibreOffice sigue pendiente. No se implementa importación Office.

## Renombrar campos conservando grupos

En **Formularios y firmas → Propiedades de campos existentes**, cambia el **Nombre parcial del campo**. Solo cambia el nombre del campo lógico terminal: el contenedor y todas las posiciones compartidas permanecen. Por ejemplo, `Datos.Nombre` puede pasar a `Datos.Solicitante` editando únicamente `Nombre`.

Se admiten 1–100 caracteres Unicode, sin puntos, controles ni espacios en los extremos. Se rechazan nombres que colisionan con campos o contenedores hermanos. Valores actuales, valores de restablecimiento, geometría, jerarquía y apariencias se conservan. Se comprueba texto, texto multilínea, casillas, radios y selección única compatibles.

No se renombran campos en formularios con acciones o cálculos detectados. Las integraciones externas o ficheros de datos que dependan del nombre anterior necesitan revisarse; no se reescriben referencias externas. El renombrado utiliza la vista previa obligatoria y crea una versión que admite deshacer/rehacer, proyecto y recuperación.

## Opciones de listas existentes

Despliega **Opciones de la lista existente** para añadir, retirar, subir, bajar y corregir opciones. Cada fila tiene **valor de datos** y **etiqueta visible**, que pueden diferir. Las flechas cambian el orden y el índice seleccionado se vuelve a calcular.

Se conserva el valor actual. No se puede retirar o cambiar su código hasta rellenar otra opción; tampoco se puede eliminar una opción necesaria para restablecer el campo a su valor predeterminado, incluso si no es el actual. Corregir la etiqueta de una opción seleccionada regenera su apariencia con esa etiqueta y conserva el código exportable.

Se admiten desplegables y listas de selección única con un Widget: de 1 a 500 opciones, valores distintos no vacíos de hasta 2000 caracteres y etiquetas latinas de 1–300 caracteres. No se cambia el tipo de campo ni se habilitan selección múltiple, XFA, scripts o listas compartidas no verificadas. Los campos de solo lectura compatibles se pueden diseñar conservando el bloqueo; se vuelven a comprobar las restricciones antes de permitir desbloquearlos.

## Avance y próximos trabajos

**83 % ±5 puntos** del plan propio: 83,25 puntos ponderados. Conversión pasa de 65 a 75 % de cobertura estimada (+1,5 puntos globales) por imágenes y tablas con revisión y límites verificados. Formularios permanece al 90 %: estas ampliaciones mejoran cobertura dentro de esa referencia, pero no completan firmas, XFA, cálculos o seguridad avanzada. Los pesos y las demás áreas no cambian.

Siguientes trabajos recomendados:

1. Corpus de documentos reales y revisión en Word/lectores externos; ampliar tablas combinadas y geometrías de imagen según los fallos observados.
2. Definir e implementar firma con certificados, verificación criptográfica y presentación clara del estado de validación.
3. Estándares PDF/A/accesibilidad y estructuras complejas de edición/censura, con validadores independientes.
4. Preparar y validar en Windows el ejecutable propio con logo, ventana y recuperación cuando corresponda su entrega.

Validación del cierre 0.28: **1357 pruebas Python y 83 JavaScript aprobadas (1440 en total)**, compilación de producción y recorrido completo de Chromium aprobados en Linux. Tras los últimos ajustes de presentación se repitió el recorrido específico: imágenes/tablas, revisión de omisiones, nombres/opciones/reordenación, historial, proyecto y recuperación. Se comprueba lectura independiente con python-docx, máscaras alfa reales, JPEG sin recodificar, cuatro giros y recorte, tablas combinadas protegidas y conservación de valores actuales/de restablecimiento. La apariencia en Microsoft Word/LibreOffice, lectores comerciales y ejecución Windows nativa sigue pendiente. No se generó otro portable.

## Capturas

- [Nombre y opciones de listas](images/Reapdf-Listas-0.28.png).
- [Word con imágenes y tablas revisadas](images/Reapdf-Word-tablas-0.28.png).
