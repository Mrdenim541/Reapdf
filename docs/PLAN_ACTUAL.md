# Plan vigente de cierre

**Solicitud posterior del usuario:** entregar la versión actual para probarla en su PC. Se autoriza una entrega portable de prueba, descrita en [la guía rápida](PROBAR_VERSION_ACTUAL.md), sin declarar cierre técnico ni cambiar la estimación global. La prohibición anterior de paquetes intermedios no impide esta entrega expresamente solicitada.

**Entrega solicitada:** programa Windows técnicamente completo, en ventana propia, instalable o portable, con guía por función. Las revisiones personales del usuario son la última etapa. No pedirle pruebas intermedias ni entregar candidatos internos como producto terminado. Una protección o incompatibilidad del motor no equivale a una implementación completada.

La última estimación global registrada es **86,87 % (≈87 %)** y se consulta en [avance-global.json](avance-global.json); es una valoración provisional de ingeniería de diecisiete áreas con pesos estables, no un porcentaje objetivo de paridad con Acrobat ni de tiempo restante. No elevarla por documentación, preparación del entorno o repetición de pruebas. `technical_complete` y `accepted_complete` se registran por separado.

Último trabajo interno: [implementaciones y validación integral](IMPLEMENTACIONES_Y_VALIDACION_20261104.md), con estimación recalculada y sin entrega final. El historial detallado permanece en [WORK_STATE.md](WORK_STATE.md); no repetir como pendientes las funciones ya incorporadas y verificadas.

## Alcance que permanece abierto

Se conserva la numeración de ocho bloques. No trasladar los pendientes de 1–4 a otros bloques para declararlos terminados.

| Bloque | Implementación o cierre pendiente |
| --- | --- |
| **1. Edición avanzada** | Instancias/ejes no predeterminados, CFF2 crudo y Type3 fuera del subconjunto verificado; reflujo con transformaciones no paralelas, composición/espaciado especial restante y cambio general de fuente; etiquetas/ActualText/Stm y redistribución etiquetada general; máscaras, knockout, grupos/colores complejos e imágenes con semántica no verificable. Paginación automática compatible y edición de un fragmento nativo etiquetado ya incorporadas, junto con selección/continuación explícitas compatibles. |
| **2. Accesibilidad y estructura** | Reparación compatible de rol/RowSpan/ColSpan/Scope de tablas existentes, conservación de identidad de nodos iguales al guardar y edición de un fragmento nativo etiquetado incorporadas. Quedan semántica general/mixta interna de Forms, imágenes inline/recortes, enlaces ambiguos/listas/celdas complejas, ActualText/Stm y reparación general/PDF/UA. El texto nuevo no se etiqueta automáticamente. Lector de pantalla e interoperabilidad externos pendientes. |
| **3. Formularios, anotaciones e intercambio** | Condicionales numéricos, comparaciones y lógica acotada, aritmética y Math compatibles ya incorporados como analizador restringido. Quedan XFA, JavaScript/acciones/validadores generales, fórmulas fuera de su gramática, fuentes no compatibles, grafos mixtos con reglas de proyecto e interoperabilidad externa. Variantes XFDF y apariencias/anotaciones avanzadas restantes e interoperabilidad con otros lectores. |
| **4. OCR y Office** | Importación Word por lotes y saltos de sección par/impar con numeración ya incorporados. Quedan secciones continuas/columnas, campos y fidelidad Office general, OCR con esquinas/bajo contraste/idiomas y tablas irregulares/curvas/multilínea generales, notas Word partidas o con marcas fuera de fragmentos consecutivos compatibles y corpus externo. |
| **5. Firmas, seguridad y estándares** | Censura mediante reconstrucción raster completa incorporada como alternativa explícita con pérdidas, no censura nativa universal. Quedan revocación por red/histórica, PAdES-LT/LTA y renovación de archivo; certificaciones/DocMDP/FieldMDP protegidas, censura nativa compleja sin pérdida y PDF/X/preflight. RFC3161, DocTimeStamp básico, revocación local y DSS local básico ya incorporados; no equivalen a archivo LT/LTA. Comprobaciones externas e imprenta. |
| **6. Planos, vinculación, portfolios y capas** | Medidas de trazados recortados/capas no verificadas y geometrías fuera de presupuestos/precisión; lotes mayores y corpus externo. Revisiones con códigos cambiados ya incorporadas. Preferencias nativas Print/Export y resolución temporal de Print compatibles incorporadas; Export permanece preferencia del lector y no filtro del guardado. Quedan carpetas/esquemas complejos y tipos/valores restantes de portfolio, AS View/Zoom/Language y reglas OCG generales, edición de contenido de capas e interoperabilidad externa. Recetas con OCR/rangos y programación local ya incorporadas; no servicio siempre activo. |
| **7. Windows y estabilidad** | 28 recorridos desde fuente en Linux/Windows Server 2025 y tres aperturas independientes de Reapdf.exe (básica, espaciado/continuación y paginación automática), además de tarea programada real dentro del paquete, comprobados. Quedan paquete final del alcance completo, Windows cliente limpio, DPI/asociaciones/impresión física, carga y recuperación sostenidas, migración del recorrido histórico extendido y aceptación personal al final. Intermitencias históricas sin causa demostrada. Carga/memoria sostenida y pérdida de energía pendientes. |
| **8. Servicios e IA** | Compartir/sincronizar/revisión y firmas remotas, priorizando local sin servicios de pago. Consulta extractiva local y adaptador opcional Ollama loopback sin descargas/acciones y con rechazo Cloud incorporados. Protocolo simulado comprobado; faltan selección/distribución con licencia, recursos y evaluación de un modelo real local. No hay validación factual automática de respuestas ni modelo empaquetado. No activar servicios externos ni asumir gastos. |

Los cuatro primeros bloques **no están completados al 100 %**. Los límites anteriores son trabajo técnico, no una lista de fallos que se delegue al usuario para descubrirlos. Tampoco basta que pasen las 75 herramientas documentadas para afirmar que todo el alcance comercial está implementado.

**Siguiente prioridad recomendada:** variantes de composición, espaciado fuera del subconjunto ya incorporado y transformaciones no paralelas; la continuación explícita y la paginación automática compatibles ya están incorporadas; no repetir el reflujo de objetos completos y continuos ya incorporado. También siguen pendientes formularios avanzados, LT/LTA y el resto del cuadro. No contratar servicios ni inventar credenciales.

## Cómo continuar sin repetir avances

1. Seleccionar pendientes funcionales concretos del cuadro, revisar su código y los límites ya documentados, e implementar recorridos completos con resultado guardado y reabierto. Continuar con varios trabajos autorizados; no detenerse por terminar una tanda pequeña ni pedir «procede» por cada bloque.
2. Ejecutar pruebas automáticas pertinentes. Comprobar la fuente exacta y el paquete en Windows; un resultado de Linux o del Python incluido no sustituye el uso de `Reapdf.exe`. No registrar un resultado pendiente como aprobado.
3. Mantener guía y matriz coherentes con la evidencia. Si una restricción real impide el cierre solicitado, explicarla antes del trabajo y conservarla visible. No responder que solo falta la prueba personal mientras existan implementaciones pendientes.
4. Resolver alcance y obligaciones de distribución antes de la entrega final. Entregar únicamente cuando se cumplan los criterios técnicos del alcance acordado; después, guiar las pruebas personales por función.

## Continuidad y límites del entorno

- Base 0.43 recuperada y mejoras posteriores, respaldadas en `recovery/editing-20261029`; 0.55 sigue sin recuperarse. No afirmar que todas sus mejoras históricas estén presentes.
- Prioridad de uso: edición directa de texto con ratón/cursor sobre la página, operaciones prácticas y ventana Qt propia. Conservar las cajas ajustables.
- Excluida la generación de informes/registros/documentos de ensayos personales. Mantener vinculación configurable con archivos y roles generales.
- Guía actual: [MANUAL_DE_FUNCIONES.md](MANUAL_DE_FUNCIONES.md), `funciones-uso.json` y buscador integrado en «Guía y atajos». Expone resultados y límites, no acredita cierre técnico general.
- La API de Actions está bloqueada, pero los resultados reales de Windows se recuperan por Git desde `validation/desktop-windows`. No repetirla como impedimento para toda comprobación Windows ni cambiar la política de red.
- [Continuación en PC](CONTINUAR_EN_PC.md). REA es opcional y separado según [su evaluación](REA_PARA_REAPDF.md); no importa automáticamente funciones de Acrobat/Nitro. Dots pospuesto.
- PDFs personales, copias y capturas fuera de Git. Revisiones personales después de la entrega técnica.
- Modelo recomendado para continuar: **6.1 Sol, razonamiento medio**.
