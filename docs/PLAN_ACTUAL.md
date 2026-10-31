# Plan vigente de cierre

**Entrega solicitada:** programa Windows técnicamente completo, en ventana propia, instalable o portable, con guía por función. Las revisiones personales del usuario son la última etapa. No pedirle pruebas intermedias ni entregar candidatos internos como producto terminado. Una protección o incompatibilidad del motor no equivale a una implementación completada.

La estimación global actual es **85,18 % (≈85 %)** y se consulta en [avance-global.json](avance-global.json); es una valoración provisional de ingeniería de diecisiete áreas con pesos estables, no un porcentaje objetivo de paridad con Acrobat ni de tiempo restante. No elevarla por documentación, preparación del entorno o repetición de pruebas. `technical_complete` y `accepted_complete` se registran por separado.

Último trabajo: [imágenes por aparición y comprobación del ejecutable](IMAGENES_Y_EJECUTABLE_20261031.md). Estado anterior: [guía integrada y Windows desde fuente](ENTREGA_TECNICA_Y_GUIA_20261031.md). El historial detallado permanece en [WORK_STATE.md](WORK_STATE.md); no repetir sus entregables como tareas futuras.

## Alcance que permanece abierto

Se conserva la numeración de ocho bloques. No trasladar los pendientes de 1–4 a otros bloques para declararlos terminados.

| Bloque | Implementación o cierre pendiente |
| --- | --- |
| **1. Edición avanzada** | Instancias/ejes de fuentes no predeterminados o con diferencias de renderizado; CFF2 crudo, Type3 con imágenes/recursos/FontMatrix no estándar; reflujo afín mixto/entre objetos/páginas y cambio de fuente; composición con máscaras de imágenes/texto/shadings/funciones, knockout y grupos/colores complejos. Ampliar edición de imágenes a variantes actualmente protegidas, coordinando su semántica. |
| **2. Accesibilidad y estructura** | Semántica interna general/mixta de Forms, imágenes inline/recortes, enlaces ambiguos, otras variantes de listas y celdas mixtas; reparación general y PDF/UA. Verificación externa con lector de pantalla al cerrar el alcance técnico. |
| **3. Formularios, anotaciones e intercambio** | XFA, JavaScript general, fórmulas/acciones adicionales, tipos y estilos XFDF restantes, grafos mixtos con reglas de proyecto. Verificación de interoperabilidad con otros lectores. |
| **4. OCR y Office** | Esquinas generales y bajo contraste, tablas irregulares/curvas y multilínea generales; otros idiomas y fidelidad Office general; notas Word partidas, reinicio por página de notas finales y marcas entre fragmentos. Ampliar corpus técnico. |
| **5. Firmas, seguridad y estándares** | Solicitud TSA, revocación por red/histórica y de TSA, LT/LTA y sellos documentales de archivo; censura compleja y PDF/X/preflight avanzado. Comprobaciones de interoperabilidad e imprenta. |
| **6. Planos, vinculación, portfolios y capas** | Curvas/intersecciones no lineales y medidas antiguas ambiguas; revisiones con identificadores cambiados y lotes mayores; carpetas y esquemas complejos de portfolio; reglas automáticas y contenido OCG avanzado. |
| **7. Windows y estabilidad** | Migrar el recorrido gráfico histórico extendido; comprobar el paquete final del producto completo, Windows cliente limpio, DPI/asociaciones, impresión física, recuperación empaquetada y carga/memoria sostenida. Once recorridos desde fuente ya pasaron en Windows Server 2025 y Linux. El paquete interno ya superó Reapdf.exe/Qt, edición, deshacer/rehacer, exportación y cierre en Windows Server 2025; no acredita Windows cliente limpio ni cierre funcional general. |
| **8. Servicios e IA** | Compartir/sincronizar/revisión y firmas remotas, asistencia del producto. Faltan implementación y definición de proveedores, costes y licencias; no inventar cuentas, servicios contratados ni autorizaciones de gasto. |

Los cuatro primeros bloques **no están completados al 100 %**. Los límites anteriores son trabajo técnico, no una lista de fallos que se delegue al usuario para descubrirlos. Tampoco basta que pasen las 73 herramientas documentadas para afirmar que todo el alcance comercial está implementado.

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
