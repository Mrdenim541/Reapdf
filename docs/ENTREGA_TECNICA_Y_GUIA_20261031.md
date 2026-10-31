# Entrega técnica, manual y revisiones personales

La revisión personal del usuario se realiza después de entregar el programa completo técnicamente. No se le piden instalaciones, pruebas o capturas intermedias para continuar trabajos independientes. Las comprobaciones automáticas del motor, interfaz y Windows siguen siendo responsabilidad del desarrollo. No se genera un ejecutable de avance en esta pasada.

El manual actual cubre las 73 herramientas del catálogo y 15 operaciones generales de escritorio. Cada herramienta especifica acceso, pasos, resultado esperado y límites. `scripts/check_function_manual.mjs` comprueba la correspondencia con el catálogo; esa comprobación no acredita que todas las variantes comerciales estén implementadas. Guía y datos: [MANUAL_DE_FUNCIONES.md](MANUAL_DE_FUNCIONES.md), `funciones-uso.json`. La antigua `FUNCIONES.md` se identifica como histórica para no presentar sus estados viejos como actuales.

Se implementa además diseño de columnas de portfolios compatibles: crear texto/número/fecha, renombrar, ordenar y retirar columnas con revisión explícita. La retirada elimina sus valores; los adjuntos y la portada se conservan. Se conservan las columnas protegidas, prefijos, otros metadatos y la ordenación restante. Se mantiene el organizador propio después de añadir columnas. Los tipos existentes no se convierten automáticamente; carpetas, valores complejos y otras variantes siguen pendientes.

Comprobaciones locales: 91 pruebas Python dirigidas (incluido protocolo de evidencias CI), 128 JavaScript, compilación y recorrido nuevo Chromium/Qt Linux, con guardado atómico/reapertura y huellas de adjuntos conservadas. No se repite la regresión general histórica como si verificara módulos añadidos después. La matriz conserva 84,25 % provisional; no se suma por documentación ni preparación de CI.

## Comprobante automático de Windows

La batería de escritorio ahora incluye once recorridos. El informe registra revisión Git, estado limpio antes/después, objetos Git, huellas de fuente, resultados y logs. El workflow de código fuente ejecuta Windows/Linux y publica un comprobante en `validation/desktop-windows`, separado de la rama de aplicación. Publica únicamente desde pushes confiables de `recovery/**`; el job de pruebas conserva permisos de lectura y solo el job de comprobantes recibe escritura. No publica PDFs personales, no envía mensajes y no hace push forzado.

El comprobante verifica plataforma Windows, revisión exacta, fuente limpia, objetos Git coincidentes, batería completa y huellas/resultado de cada log. Un informe ausente, de otra plataforma/revisión, alterado o incompleto queda expresamente sin aprobar. Los tests del protocolo usan muestras sintéticas y **no son una prueba de ejecución Windows del producto**. El resultado real solo se acredita después de recuperar y comprobar el informe de la ejecución CI.

El comprobante se puede recuperar mediante Git desde el mismo repositorio, sin consultar la API de Actions bloqueada en este entorno. Es una salida de la comprobación normal del proyecto; no modifica la política de red del entorno. La publicación utiliza una rama propia con avance normal y no cambia la fuente ni su índice. Los eventos de esa rama de evidencias no vuelven a ejecutar la CI de aplicación.

Estos recorridos comprueban la aplicación desde código fuente. No sustituyen la futura comprobación del ejecutable empaquetado, DPI, asociaciones, impresión física, aceptación externa ni la revisión personal final. La solicitud de 100 % no permite marcar esos pendientes como hechos.

## Resultado real comprobado

La revisión de código **571ee166073523cbdb50fccba54916662d09b16e** pasó los once recorridos de escritorio tanto en **Windows Server 2025 (Python 3.12.10)** como en Linux, con fuente limpia antes/después. Se recuperó el comprobante Windows desde `validation/desktop-windows`, ejecución `41220957405-1`, y se volvió a verificar contra objetos Git y huellas de logs. Incluye la guía integrada con buscador, áreas, 73 herramientas y 15 operaciones generales, atajos de guardado correctos para escritorio y el diseño de columnas. No es un resultado simulado del protocolo.

Evidencia: `validation/delivery-guide-windows-20261031/results.json`, informes Windows/Linux y registros por recorrido. Regresión general: 3616 Python; dirigidas: 91 (con solapamiento); 128 JavaScript; compilación y recorridos Chromium/Qt aprobados. La última ampliación de instrucciones generales de la guía se comprobó por interfaz después de la regresión del backend. Las huellas vinculan el contenido de la guía incorporada al programa con la revisión probada.

La estimación global pasa de 84,25 % a **84,88 % (≈85 %)** por la ejecución real Windows y el diseño compatible de columnas. Se mantienen alcance y pesos; no se suma por documentación o por preparar herramientas. `technical_complete` y `accepted_complete` siguen siendo falsos: faltan funciones y la comprobación del ejecutable empaquetado en Windows cliente. La revisión personal sigue siendo la última etapa, sin impedir el desarrollo independiente.

La consulta directa a la API de Actions continúa bloqueada; ya no impide acreditar estas pruebas mediante el comprobante del propio repositorio. No se cambió la política de red ni se publicó una configuración del entorno. No se generó ni entregó un portable/instalador intermedio.
