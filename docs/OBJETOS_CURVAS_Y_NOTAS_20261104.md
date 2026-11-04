# Edición entre objetos, cruces de curvas y notas Word

La entrega final solicitada todavía no está cumplida. No se entregó un instalador/portable intermedio ni se trasladaron implementaciones pendientes a las pruebas personales. La referencia global permanece en 85,68 % provisional, sin reevaluación por esta tanda.

## Cambios utilizables

- **Editar varios textos de objetos internos distintos.** Abre Editar texto, pulsa el texto de la página, Seleccionar varios bloques, elige los textos y Redistribuir selección. Ahora admite rutas Form distintas, también página/Form, padre/hijo y apariciones compartidas. Conserva el orden elegido, las fuentes/colores/tamaños y cada recorte original; cambiar selección y cancelar siguen disponibles. La interfaz indica que combina objetos internos. Ctrl+Enter aplica, el desbordamiento conserva el borrador y deshacer/rehacer mantiene los estilos. La identidad del objeto incluye la ruta de aparición: no confunde índices locales iguales ni añade otros fragmentos implícitamente.
- **Medir entre cruces de dos curvas.** En Medir planos, Ajustar a geometría del PDF acerca el punto a cruces entre dos Bézier además de los anteriores. Usa los controles cúbicos originales, no cruces de la polilínea dibujada. Incluye tangencias, varios cruces y extremos compartidos. La transformación de coordenadas conserva precisión doble; tolerancia numérica 0,000002 pt, fusión de candidatos próximos 0,00001 pt. Pares coincidentes/no aislables o que agotan el presupuesto se omiten y se informa ajuste parcial. Presupuestos: 500 curvas, 12 000 nodos por par y 100 000 compartidos por página.
- **Importar marcas de notas Word en el siguiente fragmento.** Crear PDF desde Word acepta una marca personalizada en el fragmento de texto adyacente a la referencia, aunque tenga otro estilo. Consume únicamente ese fragmento de 1–4 caracteres; conserva el texto anterior/posterior y los enlaces de ida/vuelta. No busca marcas a través de campos, límites de enlaces, marcadores estructurales o párrafos, ni consume fragmentos con tabulaciones/dibujos u otro contenido. También se corrigió la comprobación de palabras a ambos lados de una referencia intermedia.

## Pruebas y evidencia

Fuente **cc0c283b3b588e611184f339ebdf79115d651431**; Linux y Windows comprueban los mismos objetos Git, con fuente limpia antes/después. **4018 Python** (72 casos nuevos), **140 JavaScript**, build y auditor del manual **74 herramientas + 15 operaciones generales** aprobados. Las 219 dirigidas anteriores al refinamiento de coordenadas se conservan identificadas como tales; el refinamiento pasó 74 de precisión/medición y la regresión completa final. Los fallos iniciales de construcción de fixtures, tangencias duplicadas y separación de palabras se corrigieron antes de la revisión acreditada.

**21 recorridos Qt** Linux y **21 Windows Server 2025** aprobados; comprobante **41815513183-1**, hashes y objetos contrastados. Ventana real: selección con ratón, cursor, undo/redo, Ctrl+Enter, guardado nativo y reapertura entre Forms; ratón desplazado de los cruces se ajusta a los puntos y guarda la distancia calibrada; importación/revisión de notas Word y guardado con enlaces. Los originales, otras apariciones, página vecina y dibujo base se verificaron según cada recorrido. Chromium también aprobó reelección, quitar/añadir, error de ajuste con borrador conservado y exportación de fuentes originales entre rutas.

El paquete interno **Reapdf.exe** aprobó **dos aperturas independientes**, edición/deshacer/rehacer/exportación/cierre sin navegador externo. Su huella queda en [results.json](validation/paths-curves-notes-20261104/results.json). Esto no acredita todas las herramientas en el paquete, Windows cliente/DPI, impresión física ni carga sostenida. El fallo intermitente de empaquetado registrado en la revisión anterior sigue conservado: no se ha identificado su causa y no se afirma una reparación definitiva.

## Lo que permanece abierto

Transformaciones no paralelas, texto con composición/espaciado especial/etiquetas y distribución general entre páginas; geometrías recortadas/capas y mediciones antiguas ambiguas; marcas repartidas entre varios fragmentos y notas al pie partidas. Continúan además los pendientes de formularios, OCR/Office, LT/LTA, estándares, vinculación avanzada, Windows y servicios del [plan vigente](PLAN_ACTUAL.md). No se declara cerrado ningún bloque completo por estos subconjuntos.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
