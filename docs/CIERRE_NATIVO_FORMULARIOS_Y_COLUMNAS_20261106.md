# Cierre nativo, formularios y columnas Word · 6 de noviembre de 2026

Esta implementación amplía tres áreas del plan. **No completa los ocho bloques generales ni la entrega final solicitada.** No se publica un nuevo portable y no se solicitan pruebas personales intermedias.

## Comportamiento incorporado

- **Cierre de la ventana propia.** Una vez confirmado el cierre, la ventana principal ordena explícitamente terminar el bucle de Qt. No depende de la opción implícita de cerrar al desaparecer la última ventana. Cancelar y una operación en curso mantienen la aplicación abierta. Cerrar normalmente antes de confirmar el inicio detiene también el servidor, sin anunciar una interfaz lista, abrir un navegador ni presentar un error de arranque. Se detiene el sondeo de disponibilidad al cerrar. En Windows, el arranque portable usa renderizado WebEngine por software por defecto para funcionar sin un controlador gráfico compatible; una configuración explícita de flags del entorno conserva prioridad. La ventana sigue siendo Qt propia y esto no reduce la resolución del PDF.
- **Formularios con fecha y hora.** Los cuatro formatos de fecha compatibles admiten hora de 24 horas con minutos o segundos. Se rechazan fechas inexistentes y horas fuera de rango; un borrador inválido se conserva para corregirlo. Las acciones estándar pueden estar en strings o streams locales sin compresión/Flate, con ASCII o BOM Unicode compatible, dentro del límite de 2.000 bytes. Se interpretan únicamente ayudantes reconocidos; no se ejecuta JavaScript. Acciones ambiguas, grandes, con otro filtro o código adicional siguen protegidas. El PDF guardado conserva campos editables, apariencias, acciones y páginas ajenas.
- **Saltos de columna Word.** En secciones de una a cuatro columnas, el salto explícito avanza a la columna siguiente y, desde la última, a una página nueva. Una continuación conserva estilo y no repite sangría de primera línea ni espacio de inicio/final de párrafo. Un enlace que cruza el salto produce fragmentos de enlace PDF con el mismo destino. En una columna también funciona el enlace que cruza un salto manual de página. Notas con referencia después del salto quedan en la página correspondiente. Los saltos de columna dentro de tablas, notas y encabezados/pies siguen protegidos.

## Uso

**Fecha y hora:** Formularios y firmas → Rellenar formulario. Selecciona el campo existente en la página o lista, escribe por ejemplo `06/11/2026 10:30:45` si ese es su patrón, espera la vista previa y pulsa Aplicar formulario. Guarda desde la ventana de Reapdf. No convierte texto impreso en un campo ni modifica el patrón de cualquier formulario arbitrario.

**Columnas Word:** Convertir y OCR → Importar Word. Abre el DOCX, revisa la conversión y ábrela como PDF. Los saltos de columna se interpretan automáticamente; el resumen indica su cantidad. Guarda el PDF desde Reapdf. El Word original no se modifica. Las fuentes se sustituyen por DejaVu Sans y la paginación puede cambiar; no garantiza fidelidad general de Office.

**Cerrar:** usa la X de la ventana. Con cambios sin guardar, Cancelar vuelve al trabajo y Descartar permite cerrar; durante una operación debes esperar a que termine. No se añade un paso al cierre limpio.

## Límites que permanecen

Word todavía no admite saltos manuales de **página** dentro de varias columnas, secciones continuas ni equilibrio general. Las tablas, campos, notas y fidelidad Office generales siguen abiertos. Los formularios conservan las restricciones de XFA, scripts/fórmulas/validadores generales, fuentes incompatibles e interoperabilidad externa.

El caso de cierre reproducido con la opción implícita de Qt desactivada demuestra una dependencia real corregida. **No demuestra por sí mismo la causa de todos los fallos históricos de Windows.** El arranque sin target CDP y el rechazo intermitente de ajuste siguen pendientes de causa demostrada. La prueba básica conserva la sustitución `Texto original` → `Ejecutable`; no se acorta para evitar el fallo ni se relaja el motor. Si falla, registra solicitud e inspección de la muestra sintética. El trazado opcional `REAPDF_TRACE_LIFECYCLE=1` informa etapas/tiempos/PID, sin contenido ni rutas de documentos, y permanece desactivado por defecto.

Las nuevas comprobaciones amplían cobertura; no sustituyen Windows cliente limpio, DPI, impresora física o carga/recuperación sostenidas.

## Verificación y procedencia

Fuente final `ad8d6fbb1086ef8670db28a4859de723013d510a`, respaldada en `recovery/editing-20261029`. **45 recorridos Qt desde fuente limpia en Linux y Windows Server 2025**. Recibo Windows **42268379355-1**, contrastado con objetos Git, logs y hashes; **18 ejecuciones independientes de Reapdf.exe aprobadas**, con tres repeticiones de la edición básica y dos recorridos nuevos: columnas Word y fecha/hora. Archivo interno SHA256 `248a4a6169584142c13c6b0756b7fc433e45eaf89bb7d84766e984d138b84aba`. No se publicó como nueva entrega.

**4.878 pruebas Python aprobadas, 52 netas nuevas, tres advertencias**, sobre el contenido de `14783b7f909adefcddde1cfa3843806401b52d0e`; la tanda empezó antes de crear ese commit y el contenido probado se conservó. También 405 dirigidas, 151 JavaScript, build y guía de 75 herramientas +15 operaciones. Después de la tanda completa solo cambiaron `portable/native_window.py`, `portable/lifecycle.py` y `scripts/smoke_native_lifecycle.py`: política gráfica y trazas. Se comprobaron 39 pruebas dirigidas nativas y los 45 recorridos Qt finales en ambas plataformas; estos últimos incluyen todos esos cambios. Una segunda tanda completa redundante se canceló intencionadamente; **sus 130 casos parciales no se atribuyen como otra regresión completa aprobada**. Backend, web y tests conservan los objetos de la regresión completa.

Desde fuente Qt se guardan y reabren los resultados Word/formulario mediante la ruta nativa, con selección de archivo sustituida por el test para no requerir intervención. El driver compartido se probó primero en Qt fuente; sus mensajes «compiled Qt» no certifican por sí mismos un exe. La evidencia del ejecutable proviene de Windows CI. En los dos recorridos compilados nuevos el PDF se exporta por el servidor incluido y se comprueba con su intérprete. Fecha/hora observa la solicitud real de Aplicar y la repite para recuperar el PDF; no se presenta como prueba del diálogo nativo de guardar del exe. Se verifican valores, apariencias, acciones, texto, posiciones, estilos y destinos, además de páginas ajenas y original intactos.

## Ensayos fallidos conservados

El primer candidato Windows (`14783b7f`, recibo **42266053190-1**) aprobó 45 recorridos fuente pero falló al iniciar la primera ventana compilada: no confirmó disponibilidad antes del límite; **no se le atribuye aprobación del ejecutable**. Se incorporó la política de renderizado por software y trazas de fases anteriores, ahora por stderr. La posterior aprobación de 18 ejecuciones demuestra el recorrido de esa configuración; no prueba que se haya determinado la causa de todo fallo histórico de arranque, cierre o ajuste. No se ampliaron plazos, acortó «Ejecutable», relajó ajuste ni añadió un reintento que ignorase un fallo.

El control negativo local reprodujo una ventana cerrada/oculta cuyo bucle permanecía vivo al desactivar la salida implícita de Qt. El cierre explícito lo resuelve y cuatro subprocesos comprueban cierre limpio, ocupado, Cancelar/Descartar y cierre antes de disponibilidad; en Windows ejercitan la política gráfica por defecto. Esa reproducción no prueba por sí sola la causa del cierre histórico de Windows.

Los primeros ensayos locales detectaron un fixture de paquete mínimo que aún no copiaba lifecycle.py (producción ya lo incluía), un backend de prueba aún cargado con la versión Word anterior y un verificador que intentaba pulsar Aplicar cuando la vista previa inválida lo desactivaba correctamente. Se corrigieron los fixtures/verificadores y se usó un servidor nuevo. Otro verificador quedó esperando el cuerpo binario de la respuesta por CDP; ahora observa Aplicar y recupera el PDF mediante la misma solicitud al servidor. Dos sondas locales se solaparon antes de aislar sus procesos; no se computan como pruebas aprobadas. El recorrido aislado posterior pasó. Ninguno de esos cambios retira guardas del motor.

[Evidencias y hashes](validation/native-forms-columns-20261106/results.json). Solo muestras sintéticas; documentos y capturas personales fuera de Git.

## Estado global y trabajo pendiente

**Estimación global provisional: 87,73 % (≈88 %)**; antes 87,60 %, cálculo exacto **87,595 → 87,730**, incremento **0,135**. Mismos diecisiete pesos y alcance: formularios 93→94 aporta 0,06; OCR/Office 98→98,5 aporta 0,045; escritorio 85→85,5 aporta 0,03 por cierre explícito/cancelación y arranque compatible. No se añaden puntos por documentación, diagnósticos o repetir pruebas. Es juicio de ingeniería, no una medición objetiva de paridad con Acrobat ni de horas restantes. [Referencia anterior](progress/20261106-before-native-forms-columns.json).

**Los ocho bloques generales siguen abiertos y la entrega completa solicitada no está cumplida.** No solo faltan tus pruebas. Permanecen implementaciones de edición/semántica/CSS y cajas multipágina, formularios XFA y acciones generales, Office/OCR general, estándares y firmas de archivo, planos/portfolios/capas avanzados, estabilidad/distribución final y servicios/IA locales. El [plan vigente](PLAN_ACTUAL.md) mantiene el detalle por bloque y la [guía por función](MANUAL_DE_FUNCIONES.md) describe uso, resultado esperado y límites de las funciones actuales. No se transfieren esas implementaciones a tu etapa de verificación.

Siguiente trabajo funcional: geometría por página y CSS de estructuras continuadas, seguido por compatibilidad de formularios fuera de los ayudantes ya incorporados. El seguimiento de intermitencias Windows sigue abierto, sin repetir los recorridos nuevos como funciones ausentes. Modelo recomendado: **6.1 Sol, razonamiento medio**.
