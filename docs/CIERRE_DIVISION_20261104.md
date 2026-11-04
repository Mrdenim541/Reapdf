# Cierre funcional de división de PDF · 4 de noviembre de 2026

El módulo de división queda cerrado para el alcance definido abajo, sujeto a las pruebas registradas. No cierra ninguno de los ocho bloques globales de paridad comercial ni declara completo Reapdf. La petición de al menos un bloque se aborda como un módulo funcional completo, tal como se delimitó al iniciar esta pasada.

## Qué se incorporó ahora

- Comprobación automática desde la ventana para los tres modos; cancela respuestas obsoletas y deshabilita descarga hasta validar páginas, nombres y estructura. Cada descarga queda ligada al documento, cambios y plan comprobados.
- Conservación nativa de atributos Layout compatibles, arrays de atributos con revisión y ActualText asociado a páginas completas. Los árboles pueden tener hasta 100.000 nodos, profundidad 64 y 500.000 pasos, con presupuestos adicionales. Una alternativa o caja que cruza partes se detecta antes de exportar; mantener esas páginas juntas es una salida válida.
- Verificación independiente de cada parte antes de publicar el ZIP: texto, fuente/tamaño/color/posición, geometría, campos, etiquetas de página y apariencia renderizada. Una discrepancia cancela el ZIP completo; no se publican partes a medias.
- Relación opcional con SHA256, páginas originales, etiquetas retenidas y resolución de comprobación por parte. Se actualizó la guía por función.

Los formatos de nombre con prefijo, separador, inicio y cifras mínimas ya existían antes de esta pasada; se integraron con la nueva comprobación y se verificaron completos. No se cuentan de nuevo como implementación nueva.

## Criterios de cierre del módulo

| Criterio | Prueba |
| --- | --- |
| Separar por tamaño, grupos personalizados y marcadores, cubriendo todas las páginas una sola vez | Recorrido Qt con tres ZIP realmente guardados; regresión de rangos, orden y destinos ambiguos |
| Formato «1.46 PINTURA 001.pdf … 042.pdf», nombres individuales y recuperación de errores | Recorrido Qt con 42 partes y nombre inválido corregido; pruebas Windows/Unicode/duplicados/reservados |
| Conservar contenido digital y etiquetas compatibles | 42 páginas, más de 2.000 nodos y ActualText; atributos Layout/BBox; comprobación de texto y píxeles independientes |
| Prevenir daños semánticos y descargar solo la configuración revisada | Pruebas de alternativas entre páginas, atributos inválidos, token estable/obsoleto y parte deliberadamente adulterada |
| Alternativa explícita para etiquetas no compatibles, sin rasterizar ni alterar el original | Recorrido observado Qt y pruebas de copia, imágenes/campos/anotaciones/permisos/firmas |
| Abrir, guardar ZIP y verificar resultados desde la ventana propia | Recorridos Qt Linux y Windows; prueba adicional del motor realmente incluido en el paquete Windows |
| Conservar el documento original | Pruebas API, hash antes/después en Qt y prueba privada |
| Documentación y regresión | Manual por función, Python, JavaScript y compilación de interfaz |

## Alcance y límites que continúan vigentes

Se conservan los límites de 500 partes y 100 MiB de PDFs de salida. No se eluden firmas o permisos. IDTree, ClassMap, referencias Stm y otras estructuras no verificables requieren la alternativa explícita sin etiquetas o una copia adecuada; no son conservación semántica nativa general. La alternativa sin etiquetas pierde accesibilidad y declaraciones PDF/UA/PDF/A. Capas, XFA y scripts fuera del perfil siguen protegidos.

La comparación visual es exacta para el raster comprobado, hasta 72 ppp y adaptativa a 4 Mpx por página/64 Mpx por documento. No certifica impresión a cualquier resolución ni conformidad PDF/UA. El PDF privado disponible se probó conservando sus etiquetas Layout; no es el documento de 42 páginas mostrado en las capturas, que no está disponible.

No se entregó ni publicó otro portable. La descarga anterior contiene una fuente anterior y no incorpora este cambio. Las comprobaciones de Windows Server y del candidato interno no sustituyen Windows cliente/DPI/impresión física ni la aceptación personal final.

## Incidencia detectada en Windows

La primera ejecución Windows, fuente `3e853adf007b25fb4ea2ab1157184b1d080e40ac`, se detuvo en el recorrido TSA tras 13 comprobaciones: se agotó la espera de apertura inicial y un `QMessageBox.warning` síncrono mantuvo un bucle modal hasta el límite de la prueba. No fue un resultado aprobado y se conserva el informe y la traza.

Se cambió la espera de apertura a un plazo monotónico de 30 s, reiniciado cuando la interfaz está ocupada; el aviso abre de forma asíncrona y el estado de sondeo se libera al agotar el plazo. Una prueba independiente retrasa la página más de 10 s, comprueba la apertura inicial, fuerza el agotamiento y verifica la respuesta de JavaScript y la apertura tras reintento. Esto corrige defectos concretos de espera/aviso/reintento; no demuestra la causa de toda carga lenta ni resuelve por sí solo todas las intermitencias históricas.

## Estimación global

Se mantienen las diecisiete áreas y sus pesos. La madurez estimada de lectura/páginas pasa de 93 a 96 por el nuevo soporte semántico de división y el flujo completo de comprobación/exportación atómica, con caso real privado conservando etiquetas. El formato de nombres ya implementado, la documentación y repetir pruebas no reciben puntos nuevos. Con peso 7, el total pasa de 86,8725 a 87,0825 (87,08 %; aproximadamente 87 %). Es una valoración provisional de ingeniería, no paridad medida con Acrobat ni porcentaje de horas restantes. La implementación completa y la aceptación siguen marcadas como falsas. Ninguno de los ocho grandes bloques generales se declara cerrado por este módulo.

## Verificaciones registradas

Fuente final `1103094eddcf1e4e1a29313a69cd43d21143a598`; motor de división `3e853adf007b25fb4ea2ab1157184b1d080e40ac`. Entre ambas revisiones solo cambian apertura inicial y sus verificadores; backend, interfaz y pruebas pytest conservan los mismos objetos Git.

- 4.427 pruebas Python aprobadas (+8), 3 advertencias conocidas; suite iniciada en la revisión del motor. Seguimiento de escritorio en fuente final: 28 pruebas dirigidas aprobadas.
- 151 pruebas JavaScript, build y cobertura del manual (75 herramientas + 15 operaciones generales) aprobados.
- 31 recorridos Qt Linux y 31 Windows Server 2025 con fuente limpia antes/después. Comprobante Windows `41902515607-1`, contrastado con objetos Git y hashes de logs.
- Tres aperturas independientes del ejecutable compilado, con tareas de edición/continuación/paginación; adicionalmente, división de 42 páginas ejecutada por API contra el motor realmente incluido y reabierta con el intérprete del paquete. No confundir esta última prueba con hacer clic en división dentro del ejecutable compilado: el recorrido visual de división usa la fuente Qt Windows.
- PDF privado dividido en Qt sin retirar etiquetas: texto, píxeles y original intactos. Solo se conserva un resumen booleano sin PDF, captura, texto ni logs privados.

[Evidencia consolidada](validation/split-closure-20261104/results.json) · [Manual por función](funciones-uso.json) · [Pendientes generales](PLAN_ACTUAL.md).
