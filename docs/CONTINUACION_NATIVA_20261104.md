# Continuación de párrafos entre páginas

La entrega técnica final solicitada sigue pendiente. No se entregó otro ejecutable/portable ni se pidieron pruebas personales. La estimación global registrada permanece en 85,68 % provisional, sin nueva reevaluación por este subconjunto.

## Cambios implementados

**Continuación nativa desde la página.** En Editar texto, abre el párrafo sobre la página o selecciona varios bloques y redistribuye la selección. Escribe en la caja única, ajusta su ancho/alto inicial y pulsa Continuar en otra página. Se conserva el borrador, incluidos los estilos. Dibuja un área vacía en una página existente; puedes añadir y ordenar hasta siete áreas. Aplica con el botón o Ctrl+Enter; Comprobar distribución es opcional. No hay paso obligatorio de comparación para esta continuación.

**Fuentes y transformación conservadas entre páginas.** Redistribuye objetos completos, paralelos y opacos, incluidos Forms compartidos y rutas distintas, preservando programas de fuente, tamaños, colores y giro/inclinación compatibles. La primera región mantiene sus recortes originales. Las continuaciones usan áreas vacías explícitas, con un marco paralelo contenido dentro de cada área. La escritura elimina solo operandos seleccionados y copia únicamente sus apariciones; reutiliza los recursos de fuentes en las páginas de destino. No censura ni rasteriza el párrafo.

**Selección visual y edición simplificada.** Las vistas de destino están enderezadas; puedes arrastrar el área o editar coordenadas, cambiar página, ordenar y quitar destinos. La siguiente página es el destino inicial cuando existe. En el flujo avanzado anterior, Conservar fuentes originales ahora permite escribir en Texto completo del flujo original; los ajustes por fragmento quedan plegados y opcionales. Se mantiene su comparación por páginas. Se separó la identidad del documento de la del grupo de texto para conservar correctamente el borrador al abrir la continuación.

**Protecciones comprobadas.** Se planifica todo antes de escribir. Si falta espacio o un glifo, si el alto inicial no permite una línea o si un destino cruza texto, gráficos, imágenes, enlaces, campos o anotaciones, no se publica una versión parcial y se conserva el borrador. Las comprobaciones de destino incluyen trazos de texto: una declaración ActualText vacía puede ocultar la extracción sin ocultar las letras. Una prueba reprodujo la aceptación incorrecta de ese caso y ahora acredita su rechazo. Los textos guardados vuelven a ser editables con fuente original.

## Verificación

Fuente **835ae5b92140fe1742ab0f1707e4919a5bbff273**, respaldada en recovery/editing-20261029. **4077 Python**, incluidos **59 casos nuevos**, **140 JavaScript**, build y auditor del manual **74 herramientas + 15 operaciones generales** aprobados. Las dirigidas cubren giros, inclinación/reflexión/escala, apariciones compartidas, varias regiones, página recortada, CFF/CID y Type3 compatibles con programas/glifos conservados, guardas de área/glifos/etiquetas/capas, preview/API/exportación y reedición posterior.

**22 recorridos Qt Linux y 22 Windows Server 2025**, fuente limpia antes/después y objetos Git iguales; comprobante **41820459788-1**, hashes/logs contrastados. El recorrido nuevo usa cursor real, restaura estilos con undo, rechaza un destino ocupado sin perder el texto, dibuja con el ratón sobre una página girada, aplica con Ctrl+Enter y verifica undo/redo del documento, guardado nativo atómico y reapertura. Comprueba apariciones no elegidas, otras páginas, texto vecino y original intactos. Chromium también aprobó la continuación y la caja única del flujo original con undo/redo, comparación y exportación. Los recorridos de navegador se repitieron con el servidor corregido; la batería Qt final y la regresión completa también corresponden a esa fuente.

El paquete interno **Reapdf.exe** pasó **dos aperturas independientes** con edición/deshacer/rehacer/exportación/cierre y sin navegador externo. No acredita todas las herramientas empaquetadas, Windows cliente/DPI, impresión física ni carga sostenida. La intermitencia anterior de empaquetado conserva su registro y sigue sin causa confirmada; no se declara reparada por estas ejecuciones aprobadas. [Resultados y huella](validation/native-continuation-20261104/results.json).

## Límites y próximos pendientes

Hasta 4000 caracteres y siete continuaciones en otras páginas ya existentes; no crea páginas, no desplaza contenido ajeno ni admite continuaciones nativas adicionales dentro de la propia página de origen. Permanecen transformaciones no paralelas entre estilos, composición/espaciado especial, etiquetas/capas y redistribución automática general con nueva paginación. El resto de formularios, accesibilidad, OCR/Office, LT/LTA, estándares, vinculación, Windows y servicios sigue en el [plan vigente](PLAN_ACTUAL.md). No volver a proponer como pendiente la continuación explícita compatible implementada aquí.

Modelo recomendado: **6.1 Sol, razonamiento medio**.

La ejecución Windows anterior, fuente fe380d5 y comprobante 41820092939-1, agotó 150 segundos en smoke_timestamp_qt.py sin completar la batería. Se conserva como intento fallido, no como aprobación. La revisión final 835ae5b pasó esa misma prueba y las otras 21; no se modificó el recorrido TSA entre ambas revisiones ni se identificó la causa del timeout. La guarda ActualText no se presenta como corrección de ese problema. La estabilidad sostenida y el diagnóstico de la intermitencia Windows siguen abiertos.
