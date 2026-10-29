# Áreas de trabajo — 0.22

La apertura de un PDF muestra **Leer**, con cinco herramientas, la navegación y la página. El panel derecho no ocupa espacio durante la lectura. Las demás funciones se acceden desde las áreas de la barra superior.

| Área | Para qué sirve |
|---|---|
| Leer | Lectura, revisión estructural, comparación, adjuntos y metadatos. |
| Editar | Texto, párrafos, imágenes, enlaces, marcas de agua y encabezados/pies. |
| Comentar | Selección de marcas, notas, resaltado, subrayado, tachado, trazos, figuras y sellos. |
| Organizar páginas | Ordenar, girar, extraer, unir, sustituir, duplicar, insertar hojas, recortar, dividir, editar etiquetas/índice y numeración/Bates. |
| Formularios y firmas | Rellenar y diseñar campos, importar/exportar datos, aplanar y firma visual sin certificado. |
| Convertir y OCR | Reconocimiento local, exportación a imágenes/TXT/CSV y optimización estructural. La conversión a Office sigue pendiente. |
| Proteger | Copias con contraseña y censura/saneamiento de estructuras compatibles. |

## Un recorrido habitual

1. Abre el PDF en **Leer**. Navega con miniaturas, índice, búsqueda o número físico de página. El tamaño visible en puntos está junto a la navegación del visor.
2. En **Editar**, elige **Editar texto** para líneas simples o **Reemplazar bloque de texto** para un bloque compatible. Las herramientas muestran una descripción breve; los asistentes mantienen sus límites y vistas previas.
3. Para notas o trazos, abre **Comentar** y elige una herramienta. Sus propiedades aparecen a la derecha. Puedes plegarlas con **Ocultar propiedades** y recuperarlas con **Mostrar propiedades**; el componente conserva sus valores.
4. Aplica o cancela los borradores antes de cambiar de área, herramienta, página o historial. Los cambios de área quedan bloqueados con una explicación mientras hay un borrador o gesto activo. Así no se descarta trabajo de manera implícita.
5. Usa **Guardar proyecto** para continuar editando o **Exportar copia** para obtener el PDF. Esas acciones y el historial siguen accesibles sin depender del área.

Cambiar de área vuelve al modo de lectura del lienzo: el lápiz u otra herramienta anterior no continúa activo de forma accidental. No modifica el PDF, no crea una versión ni añade cambios al historial.

## Buscar sin recorrer áreas

**Buscar herramienta** y **Ctrl/⌘+K** siguen buscando en todas las áreas. Cada resultado indica su área; al abrirlo se activa la correspondiente y se limpia el filtro. **Mis favoritos** también reúne favoritos de todas las áreas; quitar el filtro recupera el catálogo del área activa. Las estrellas permanecen en este navegador, como en 0.21.

## Paneles y teclado

- **Ocultar navegación** libera el espacio de miniaturas, índice y búsqueda sin desmontar el panel. **Mostrar navegación** lo recupera; Ctrl/⌘+F lo abre y enfoca la búsqueda aunque estuviera plegado.
- Las propiedades se muestran al elegir una herramienta que las utiliza. Abrir un asistente dedicado deja el lienzo en lectura. Los borradores bloquean el plegado de propiedades para mantener accesibles Aplicar y Cancelar.
- **Vista de lectura ampliada** oculta los tres paneles. Esc los recupera respetando los plegados previos. Elegir otra área sale de esa vista.
- En la barra de áreas, las flechas recorren las áreas; Inicio y Fin llevan a los extremos. El área activa se identifica visualmente y mediante `aria-selected`; el panel de herramientas está asociado a ella.
- En ventanas estrechas la barra de áreas se desplaza horizontalmente y los paneles se distribuyen verticalmente. El espacio de lectura tiene su propio desplazamiento.

## Comprobaciones y alcance

Se comprueba que las 46 herramientas del catálogo sigan accesibles desde su área; apertura en Leer con cinco herramientas, navegación de teclado, búsqueda global y favoritos entre áreas, ausencia de escrituras PDF al cambiar de área, protección de borradores, plegado/restauración y ventanas de distintos tamaños. El recorrido completo anterior se adapta a seleccionar primero el área de cada herramienta y sigue comprobando los PDF y proyectos exportados.

Validación de este corte: 1004 pruebas Python y 78 JavaScript aprobadas; compilación de producción y recorrido completo de Chromium aprobados en Linux, incluidos OCR, formularios, censura, proyectos, recuperación y exportaciones. Windows sigue pendiente.

Este avance reorganiza la interfaz. No amplía el motor de edición ni acredita nuevas conversiones, firmas digitales o validación de estándares. La estimación global permanece en **74 % ±5 puntos** (73,5 ponderados). No se generan nuevos portables; el ejecutable para pruebas personales se reserva para un alcance casi completo y su validación en Windows.

En 0.26 el catálogo llega a 48 herramientas: **Editar enlaces del PDF** se incorpora a Editar y **Procesar varios PDF** a Convertir y OCR. La búsqueda global y la paleta usan el mismo catálogo; la referencia anterior a 46 herramientas corresponde al corte 0.22.

En 0.27 el catálogo llega a 51 herramientas. **Propiedades de campos existentes** se ubica en Formularios y firmas; **Comentarios y revisión**, en Comentar; **Exportar texto a Word**, en Convertir y OCR. Sus asistentes contienen controles y límites propios; búsqueda y favoritos siguen abriendo el área correspondiente.

En 0.28 las ampliaciones permanecen en sus asistentes: imágenes/tablas dentro de Exportar texto a Word, y nombres/opciones dentro de Propiedades de campos existentes. No se añaden controles permanentes al lienzo; el catálogo conserva 51 herramientas.

En 0.29 el catálogo llega a 53 herramientas: **Firmar con certificado** y **Verificar firmas digitales** en Formularios y firmas. La firma manuscrita visual permanece diferenciada. Revisar documento ofrece acceso al verificador cuando hay indicadores de firma. Los asistentes no añaden controles permanentes al lienzo.

En 0.30 el catálogo llega a 56 herramientas. **Accesibilidad y preparación** se ubica en Leer (seis herramientas iniciales); **Validar estándares PDF**, en Proteger; **Crear copia PDF/A-2b**, en Convertir y OCR. Cada una tiene su asistente y límites; las propiedades de título/idioma se mantienen plegadas hasta necesitarlas.

En 0.32 las áreas incorporan grupos de tareas plegables, iconos, descripciones opcionales persistentes y estilo visual común. La búsqueda sigue recorriendo todo el catálogo. Guía y capturas: [INTERFAZ_PROFESIONAL.md](INTERFAZ_PROFESIONAL.md).
