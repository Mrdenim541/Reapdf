# Estados de texto y transparencia conservada

La edición sobre la página admite segmentos con posiciones absolutas independientes dentro de un mismo objeto de texto, opacidad normal visible y ciertos grupos de transparencia aislados. Conserva operadores, fuentes y grupos originales; no aplana el documento.

## Funciones incorporadas

- **Segmentos con Tm independiente:** se pueden editar líneas separadas por matrices absolutas dentro de `BT/ET`, aunque cambien fuente, tamaño, color, espaciado u opacidad. El analizador conserva/restaura el estado de fuente y no publica segmentos cuyo avance determine la posición del texto siguiente.
- **Opacidad normal:** se admite texto de relleno visible con alpha entre 0 y 1, excluyendo cero. Solo se admiten estados gráficos usados con claves Type, ca, CA, BM y SMask, mezcla Normal y máscara ausente/None. No se reescriben esos diccionarios. La lectura después de guardar contrasta texto, geometría, color, alpha y opacidad de la apariencia.
- **Grupos PDF aislados sencillos:** Transparency con I=true, K=false/ausente y CS DeviceRGB/DeviceGray/ausente. Se conserva el grupo al clonar únicamente la aparición elegida y se mantienen sus recortes. Un grupo compartido puede editarse sin cambiar otros usos o páginas.
- **Protección en la interfaz y el motor:** el texto transparente y el contenido de grupos admitidos requieren su fuente original. Sustituir la fuente o convertirlo a párrafo no puede descartar la composición, incluso si el texto dentro del grupo tiene alpha=100 %. El editor explica que conserva la transparencia.
- **Recorrido cotidiano actualizado:** `npm run test:ui:core` comprueba apertura, selección con ratón, edición sobre la página, lápiz, deshacer/rehacer, navegación, zoom, selección de lectura, búsqueda, exportación y reordenación/giro con conservación de anotaciones y marcadores. Inicia un backend propio en 8766, salvo URL explícita. Necesita Chromium/Playwright disponible. Es el subconjunto cotidiano migrado del recorrido histórico, no su sustitución completa.
- El control de candidato de escritorio incluye un noveno recorrido Qt para editar texto CFF transparente dentro de un grupo compartido y guardarlo de forma nativa. Ese recorrido individual pasó en Linux. Añadirlo a CI no acredita una ejecución Windows ni un nuevo resultado de los nueve recorridos agrupados.

## Límites vigentes

No se admiten máscaras de transparencia, mezclas especiales, grupos no aislados o knockout, espacios de color complejos, estados gráficos con claves adicionales, contenido invisible ni texto de trazo. Tampoco estados sin posición absoluta que dependan del avance anterior, escritura vertical/RTL compleja ni semántica/ActualText protegida.

Las fuentes admitidas siguen limitadas a los subconjuntos verificados: base, TrueType estáticas, CFF1, CFF2 OpenType estáticas y Type3 vectoriales sencillas. No se amplían ejes/instancias variables, reflujo afín ni sustitución de fuente en grupos transparentes. La comprobación de salida utiliza una nueva lectura MuPDF, no un motor independiente ni Acrobat/Nitro.

No se ejecutó Windows, impresión física ni aceptación personal. No se generó instalador/portable. Los documentos de las pruebas son sintéticos públicos; no se utilizaron archivos personales.

## Verificaciones

**Resultados finales:** 2899 pruebas Python generales aprobadas (3 avisos existentes), 453 dirigidas finales, 63 de motor/API y 67 de edición con estilos; los subconjuntos se solapan y no se suman. 116 JavaScript y compilación aprobados. Pasaron los dos recorridos Chromium (transparencia y uso cotidiano) y la edición/guardado Qt Linux. Evidencias y hashes en `validation/text-states-20261030/`. Las pruebas nuevas comprueban fuentes base/TrueType/CFF1/Type3/CFF2, cuatro giros de página, grupos compartidos, estados intermedios, apariencia de vecinos, programas originales, borrado y lotes atómicos. Los casos de máscara, mezcla, knockout, color complejo y dependencias de avance se mantienen protegidos.

El recorrido Chromium comprueba cinco casos sobre la página, incluido un grupo de texto opaco, con fuente original bloqueada, deshacer/rehacer y exportación. Qt Linux abre, edita y guarda desde la ventana propia. El recorrido cotidiano valida el PDF exportado y su estructura después de organizar páginas.

Dos expectativas históricas se actualizaron por la ampliación funcional: la transparencia normal visible ya no implica rechazo global; la mezcla especial sigue protegida. Se añadió comprobación de píxeles del contenido transparente vecino. No se eliminó esa protección para ocultar un fallo de integridad.

## Avance global

**≈76 % del programa completo: 76,40 ponderado**, antes 76,24. Texto/imágenes pasa de 96 a 97, +0,16 puntos globales. No cambian las 17 áreas, sus pesos ni el alcance. Las comprobaciones cotidianas y el noveno recorrido configurado no aumentan por sí solos el porcentaje de escritorio ni equivalen a aceptación personal.

La edición tiene cobertura amplia y quedan casos complejos y validación externa. Para ampliar la cobertura total, el próximo bloque recomendado es revisar los huecos de formularios complejos y fidelidad Office/OCR, sin repetir cálculos u otras funciones ya presentes. Después, completar el recorrido histórico extendido y la verificación Windows antes de preparar una entrega candidata. Los casos de composición y fuentes todavía incompatibles permanecen visibles en el plan.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
