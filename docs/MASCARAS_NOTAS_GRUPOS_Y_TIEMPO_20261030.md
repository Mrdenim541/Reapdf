# Máscaras, notas por página, grupos XFDF y tiempo · 30 de octubre de 2026

Base: `34bb194179ec774e52208e2ec9b1dbb0752d5ded`, sobre 0.43 recuperada y mejoras posteriores. 0.55 sigue sin recuperar. Se usan documentos y certificados sintéticos; no se incorporan PDFs personales, claves privadas ni credenciales a Git. Sin nuevo instalador/portable.

## Edición original de texto con máscara

En **Editar → Editar texto**, los casos compatibles de máscaras vectoriales **Alpha/Luminosity** pueden editarse sobre la página conservando su fuente y composición. Se comprueban también apariciones dentro de Forms compartidos y páginas giradas. La máscara no se transforma, rasteriza ni sustituye; permanecen intactos sus streams y recursos. El cambio de fuente y la sustitución del párrafo siguen protegidos cuando eliminarían la composición.

Auditoría acotada: grupo de transparencia RGB/Gray, sin knockout; caminos, clipping, colores literales, pen y matrices compatibles; opacidad interna normal; Forms vectoriales anidados; BC válido y TR ausente/Identity. Hasta ocho niveles, cien llamadas, diez mil operaciones, 2 MB por stream/8 MB total. Se rechazan imágenes, texto, patrones/shadings, funciones de transferencia, máscaras recursivas y estados adicionales no compatibles. No equivale a admitir todas las máscaras existentes.

Pruebas de Alpha y Luminosity, opacidad interna efectiva, anidamiento, giros, fuentes/vecinos, recursos y otras apariciones/páginas; rechazo de ciclos, colores/estados/transferencias desconocidos y bypass por sustitución de párrafo.

## Notas Word numeradas en su página real

**Archivo → Crear PDF desde Word → convertir y revisar** admite `numRestart=eachPage` en notas al pie. La importación repagina, asigna números según la página real de la referencia, actualiza referencia y etiqueta de nota y vuelve a comprobar posiciones antes de publicar. Hasta doce pasadas para converger; si no converge o una nota no cabe, no se entrega un PDF incompleto.

- Número inicial y formatos estándar compatibles, incluidos romanos.
- Marcas personalizadas conservadas sin consumir números automáticos.
- Transición entre reinicio por página, continuidad y reinicio por sección usando el contador de la última página real.
- Enlaces de ida/retorno y nota al pie en la misma página de su referencia; texto original comprobado.
- El resumen indica cuántas notas usan reinicio por página.

Las pruebas comparan tanto la etiqueta de la nota como los caracteres de su enlace de referencia, con saltos manuales y cambios de página por contenido/reserva de notas. No se incorporan notas partidas entre páginas ni reinicio por página de notas finales. El número queda como contenido PDF: no es un campo Word que se recalcule después de reorganizar o editar el PDF.

## Grupos de revisión XFDF

**Documentos → Intercambiar XFDF** conserva relaciones nativas **IRT/RT=Group** entre anotaciones compatibles de la misma página. Admite entrada desordenada, grupos anidados y reimportación idempotente. Resuelve los padres antes que los hijos y rechaza ciclos, padres ausentes/de otra página, tipos de relación desconocidos y estados Review/Marked usados como grupos. Los estados de respuesta R siguen separados.

El PDF guardado conserva las relaciones y se comprueba además con un lector estructural independiente. Si al exportar un padre no es compatible, sus descendientes se omiten de forma contada para no crear grupos huérfanos. Se mantienen límites XFDF de 2 MB y 500 anotaciones. No añade edición conjunta de grupos ni mueve todos sus miembros desde la herramienta de anotaciones existentes; esa protección permanece explícita.

## Comprobación local de sellos de tiempo de firma

**Formularios y firmas → Verificar firmas digitales** muestra por separado:

- Integridad y firma del documento, cobertura/revisiones y confianza del firmante.
- Integridad del imprint y firma criptográfica del token de tiempo.
- Fecha del token, certificado de su autoridad y confianza de su cadena con los certificados públicos seleccionados por el usuario.

La confianza del firmante no implica confianza en la autoridad de tiempo. El momento solo se acepta localmente si token/imprint, firma, cadena y política admitida pasan sus comprobaciones. Se exige certificado de TSA no CA con EKU exclusivo crítico de timestamping, claves RSA/EC admitidas, SHA-256/384/512 tanto en el imprint como en la firma CMS y fecha del token dentro de su vigencia. Una fecha más de cinco minutos por delante del reloj de comprobación requiere revisión y no se acredita.

Comprobación sin red, sin instalar certificados en el sistema ni almacenarlos en proyecto. Las pruebas usan tokens RFC 3161 reales creados con una TSA sintética; distinguen raíces del firmante/TSA, propósito incorrecto, fecha futura y token alterado conservando intacta la firma principal del documento. La revocación no se comprueba y se muestra expresamente. No se solicitan sellos a un servidor TSA ni se generan sellos desde el asistente de firma; tampoco acredita PAdES-LT/LTA, sellos documentales de archivo, cualificación legal ni confianza pública automática.

## Verificación y alcance pendiente

**Aprobadas:** 3475 pruebas Python generales (476,94 s), 551 dirigidas finales, 128 JavaScript, compilación y recorridos Chromium/Qt Linux. La batería dirigida final incluye el control independiente de algoritmo del imprint, añadido después de iniciar la regresión general, y su caso con CMS fuerte/imprint SHA-1.

Resultados finales, comandos y huellas: `validation/masks-page-notes-groups-time-20261030/results.json`. Las pruebas dirigidas y generales se superponen y no se suman como cobertura independiente. Chromium verifica controles reales de edición con máscara, revisión/importación de grupos XFDF, importación Word con revisión de sus páginas y comprobación de tiempo antes/después de seleccionar confianza. Qt Linux comprueba ventana propia, guardado atómico y reapertura de texto con máscara/grupos nativos. Windows, impresión física, lector de pantalla y aceptación en Acrobat/Nitro siguen pendientes.

No se declaran cerrados los bloques 1–4: quedan máscaras/recursos/fuentes/reflujo más complejos, estructura mixta/reparación y PDF/UA, XFA/JavaScript/intercambio adicional y Office/escaneos generales. Del bloque 5 se añade comprobación local de tokens de firma; siguen pendientes revocación, solicitud TSA, LT/LTA/tokens y seguridad/estándares restantes. Los bloques 6–8 mantienen pendientes de planos/vinculación/portfolios/capas, Windows/estabilidad y servicios/IA.

Siguiente avance recomendado: reflujo afín con fuente original, tablas en perspectiva con revisión y revocación mediante evidencias locales verificadas. No volver a anunciar como pendientes las máscaras vectoriales acotadas, notas al pie con reinicio por página, RT=Group ni la revisión offline de tokens de firma ya incorporados. Modelo recomendado: **6.1 Sol, razonamiento medio**.
