# Estado funcional verificable de Reapdf

## Método vigente desde 0.40

El porcentaje global anterior, aproximadamente 90 %, procedía de ponderaciones amplias. **No era una auditoría completa del catálogo Acrobat ni una medición precisa del trabajo restante.** Se conserva como antecedente en AVANCE.md, sin subirlo por acumular pruebas o por ampliar funciones ya contadas.

El seguimiento actual distingue capacidades implementadas en un alcance definido, parciales, pendientes y sin validación de plataforma. Las filas tienen tamaños y dificultades distintos: **no se convierten en porcentaje contando filas o botones**. La matriz es una base de seguimiento del editor personal y sus límites; completar una subfunción no cierra toda su familia comercial.

## Bloque cerrado en 0.40

**Reflujo mixto compatible entre regiones: 5/5 criterios verificados.** Leer formatos, editar/separar fragmentos, distribuir sin uniformarlos, comprobar contenido/desbordamientos y revisar/conservar el resultado. Alcance y evidencia: [REFLUJO_MIXTO.md](REFLUJO_MIXTO.md).

## Bloque cerrado en 0.41

**Cinco entregables compatibles verificados:** PAGE/NUMPAGES complejos, inicio/formato de numeración, etiquetas PDF, combinaciones de tablas e informe/revisión integrados. Guía: [WORD_CAMPOS_TABLAS_041.md](WORD_CAMPOS_TABLAS_041.md).

## Bloque 0.42

Ocho entregables de secciones Word independientes, SECTIONPAGES, saltos manuales y revisión integrada. Alcance y evidencia: [WORD_SECCIONES_042.md](WORD_SECCIONES_042.md).

## Entrega de prueba 0.43

Lanzador propio `Reapdf.exe` compilado como Windows x64 GUI, con logo de inicio y paquete portable actual. El arranque se prueba de forma controlada desde Linux; la ejecución gráfica Windows permanece pendiente. Solicitud y guía: [ENTREGA_EJECUTABLE_043.md](ENTREGA_EJECUTABLE_043.md). Los flujos personales serán configurables y siguen sin implementar: [PLAN_CIERRE_Y_FLUJOS.md](PLAN_CIERRE_Y_FLUJOS.md).

## Matriz de seguimiento

| Capacidad y alcance | Estado | Qué permanece abierto |
|---|---|---|
| Lectura, zoom, búsqueda y navegación compatibles | Implementado y comprobado en su alcance | Corpus real más amplio y lectura universal. |
| Organización e importación de páginas y formularios compatibles | Implementado con límites | Documentos con estructuras/acciones especiales y corpus externo. |
| Anotaciones y selección múltiple | Parcial | Más geometrías importadas, resaltados transformables, grupos persistentes y corpus de fabricantes. |
| Edición de texto y objetos | Parcial | Fuentes exactas/codificaciones complejas, CFF/Type3, objetos y estructura semántica. |
| Reflujo entre regiones con formato común | Implementado con límites | No mueve objetos ajenos ni crea páginas automáticamente. |
| Reflujo mixto entre regiones con fuentes incluidas | Implementado y verificado en 0.40 | Fuente exacta original, semántica y los límites declarados del flujo. |
| Word compatible a/desde PDF, encabezados/pies, PAGE/NUMPAGES simples/complejos y tablas combinadas rectangulares | Parcial | Saltos de sección continuos/pares/impares, columnas, otros comandos de campos, objetos/tablas complejos y contraste visual Office. Secciones con salto a página siguiente, diseño independiente y SECTIONPAGES implementados en 0.42. |
| OCR y conversiones a imágenes | Implementado con límites | Corpus complejo, automatización OCR en recetas y revisión de resultados reales. |
| Reglas de cálculo de proyectos Reapdf y continuidad entre herramientas compatibles | Implementado con límites | Conservación en otras transformaciones y corpus real. |
| Fórmulas PDF nativas que recalculen en otros lectores | Pendiente | Implementación e interoperabilidad verificadas. No equivalen a reglas de proyecto. |
| Firmas digitales locales P12/PFX y comprobaciones compatibles | Parcial | Revocación, TSA y perfiles de conservación LT/LTA. |
| Censura y saneamiento | Parcial | Estructuras marcadas, Form XObjects, recursos compartidos y corpus OCR complejo. |
| Estándares profesionales y accesibilidad | Parcial | Etiquetas/orden de lectura, tecnologías de asistencia, PDF/X y preimpresión avanzada. |
| Automatización mediante recetas compatibles | Parcial | OCR, rangos por paso, importación Office por lotes y corpus. |
| Ejecutable propio de Windows | Sin validación de ejecución | Arranque, edición/exportación, impresión, permisos y recuperación en Windows real antes de la entrega personal. |

La matriz técnica de cierre sigue en [release-criteria.json](release-criteria.json). La evidencia local 0.43 demuestra regresión Linux y **no autoriza declarar 1.0**: [CIERRE_043.json](CIERRE_043.json).

## Regla para los siguientes avances

Cada avance debe identificar un alcance concreto, sus criterios y su evidencia, y separar trabajo terminado de ampliaciones futuras. PAGE/NUMPAGES complejos quedan implementados en 0.41. Las secciones compatibles quedan incorporadas en 0.42. El siguiente bloque recomendado es grupos persistentes de anotaciones; luego, cálculos nativos interoperables y validación Windows. No se volverán a presentar los bloques ya cerrados como si siguieran sin empezar.
