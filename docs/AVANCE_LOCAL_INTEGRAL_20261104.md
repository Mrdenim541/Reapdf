# Trabajo integral local · 4 de noviembre de 2026

Se implementaron cambios concretos en ocho áreas. **No está cumplida la entrega final solicitada:** aún hay implementaciones pendientes, además de validaciones técnicas. No se entrega un instalador intermedio ni se pide al usuario probarlo. La preferencia confirmada es funcionamiento local, sin servicios de pago.

## Cambios y uso

| Área | Comportamiento incorporado | Límite vigente |
| --- | --- | --- |
| Edición | El párrafo mixto compatible conserva espaciado de caracteres/palabras y ajustes TJ al editar directamente o continuar a otra página. Se aíslan apariciones de Forms compartidos. | Objetos completos, paralelos y opacos compatibles; no paginación automática, composición arbitraria ni transformaciones no paralelas. |
| Estructura | En Etiquetas y orden de lectura → Editar etiquetas → Rol e idioma se puede establecer Scope de encabezados TH existentes: fila, columna o ambas. Atributos compartidos se copian antes de cambiar. | No convierte cualquier documento en PDF/UA ni repara automáticamente todas sus tablas. |
| Formularios | Se reconocen cálculos nativos compatibles con Math.abs/round/floor/ceil/min/max y resto, conservando sus acciones PDF. | Analizador restringido de datos; no ejecuta JavaScript arbitrario ni cubre XFA. |
| Word | Se importan marcas personalizadas de notas repartidas entre fragmentos consecutivos con el estilo de referencia adecuado. | Hasta cuatro caracteres; no atraviesa campos, enlaces u otras estructuras ni resuelve notas partidas generales. |
| Preimpresión | El diagnóstico examina colores declarados en Forms anidados, nombres de tintas planas y estados de sobreimpresión aplicados. | Diagnóstico acotado; no evalúa tintas, cobertura de tinta ni certifica PDF/X. |
| Portfolio | Se muestran columnas nativas de nombre, descripción, tamaño declarado y fechas como datos derivados de solo lectura. | No verifica el tamaño leyendo binarios ni añade carpetas/esquemas complejos. |
| Escritorio | El ejecutable interno se prueba también editando un párrafo con espaciado y continuándolo entre páginas. Se añade instrumentación de bloqueos al recorrido de sellado temporal. | Windows Server 2025; no demuestra Windows cliente, DPI, impresión física ni resolución de intermitencias históricas. |
| Consulta local | Documentos → Consulta local → Consultar documento permite extraer un resumen o localizar pasajes por pregunta/identificador, con referencias y navegación a la página. Respeta permiso de copia. | Extractivo y **no generativo**, sin modelo remoto, red ni coste de servicio. Límites de páginas/texto explícitos; escaneados necesitan OCR. No equivale a comprender preguntas generales. |

El manual actualizado documenta 75 herramientas y 15 operaciones generales con acceso, pasos, resultados y límites. Se conserva la edición directa sobre la página y la ventana propia Qt.

## Evidencia real

Fuente de implementación: `c6de8ff99a836899f7884bdaf28d1ddddf888778`, respaldada en `recovery/editing-20261029`.

- 4.229 pruebas Python aprobadas, 152 casos nuevos; tres advertencias registradas en el log.
- 140 pruebas JavaScript, compilación web y comprobación del manual aprobadas.
- 24 recorridos de escritorio Linux y 24 Windows Server 2025, con fuente limpia antes y después.
- Comprobante Windows `41843318881-1`, contrastado localmente con los objetos Git y hashes de los logs.
- Dos aperturas independientes del programa empaquetado: edición básica y edición con espaciado/continuación. Se usa Reapdf.exe y su ventana Qt, sin navegador externo. Se comprobaron exportación, texto reabierto, página ajena sin cambios y fuente intacta.

[Resultados](validation/ordered-local-20261104/results.json), [evaluación Windows](validation/ordered-local-20261104/windows/assessment.json) y [regresión Python](validation/ordered-local-20261104/full.log). La prueba CDP local archivada es de fuente Linux; no se usa como sustituto del resultado del ejecutable Windows.

Los antiguos fallos intermitentes de edición empaquetada y tiempo de espera TSA permanecen sin causa confirmada. El nuevo resultado positivo y la instrumentación no acreditan haberlos corregido. Se conservan sus evidencias históricas.

## Pendientes reales después de estos cambios

El [plan vigente](PLAN_ACTUAL.md) conserva los ocho bloques y especifica las variantes abiertas; no se consideran terminados por haber trabajado en cada uno. Permanecen edición/composición/fuentes generales, reparación semántica, XFA y acciones generales, fidelidad OCR/Office restante, LT/LTA/censura/estándares, automatización y capas complejas, estabilidad/distribución final y colaboración local. Son implementaciones o verificaciones técnicas propias, no tareas que el usuario deba descubrir mediante pruebas.

La referencia global sigue en **85,68 % provisional (≈86 %)**, sin nueva puntuación en esta pasada. No es una medición objetiva de paridad con Acrobat. La matriz conserva pesos y alcance; ejecutar más pruebas no suma puntos automáticamente. `technical_complete` y `accepted_complete` siguen siendo falsos.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
