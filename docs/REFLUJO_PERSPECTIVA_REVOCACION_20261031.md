# Reflujo afín, tablas en perspectiva y revocación local

31 de octubre de 2026. Base: `c65a273`. Sin instalador ni portable nuevo.

Se amplían tres áreas del plan sin declarar cerrados los bloques comerciales completos. La estimación global pasa de **83,20 % a 83,69 %** con los mismos diecisiete pesos y alcance; no representa una medición de paridad con Acrobat ni aceptación del usuario.

## Edición directa y reflujo

Desde una línea seleccionada con el ratón, **Distribuir en líneas** admite texto con saltos o ajuste al ancho y alto del marco local. Conserva la fuente original, la matriz afín, el estado gráfico y la composición. Inserta posiciones absolutas de texto; cada línea compatible sigue siendo editable tras guardar y reabrir. No usa redacción ni sustituye la página por una imagen. Los controles se distribuyen sobre el editor al activar este modo.

El motor valida el contenido completo antes de publicar la copia. Comprueba recortes, límites de página, vecinos, imágenes, campos, anotaciones, enlaces y bordes. La relectura comprueba texto, fuente, geometría, color y opacidad. Los Forms compartidos se aíslan por aparición con el escritor existente; las otras apariciones y páginas se conservan. La detección de colisiones de la edición de línea utiliza ahora el contorno afín verificable del vecino, evitando rechazos por cajas rectangulares que se cruzan sin tocar el texto.

Alcance: un grupo original uniforme como origen, fuentes y transformaciones ya verificables, incluido TrueType/CFF y Forms compatibles. Ancho y alto locales de 10–2000 pt, máximo 4000 caracteres; conserva tamaño y estilo. No reúne párrafos originales de varios grupos transformados, no cambia la fuente ni permite contenido etiquetado en este reflujo. Texto bidireccional, geometrías ambiguas y colisiones permanecen protegidos. Las demás limitaciones de fuentes y composición del plan siguen vigentes.

## Tablas en perspectiva

**Extraer tabla por región → Corregir perspectiva** permite mover cuatro esquinas numeradas con el ratón. Se rectifica una imagen auxiliar mediante homografía y se aplica OCR a esa imagen. La revisión muestra la tabla rectificada, con separadores en su propio sistema de coordenadas; no dibuja una cuadrícula rectangular falsa sobre el original deformado. Se pueden redistribuir separadores, corregir celdas y exportar CSV/Word usando los recorridos existentes.

El resultado incluye el cuadrilátero de origen y la proyección de cada palabra al PDF. El original queda intacto. La vista previa está limitada a 1600 píxeles por lado; renderizado/reconocimiento mantiene el presupuesto de 16 MP y 8192 píxeles. Se conserva la protección de permisos y formularios. Solo se aceptan cuadriláteros convexos estables dentro de la selección y en orden de lectura; la orientación adicional se fija a cero para evitar sistemas contradictorios. La corrección usa OCR incluso en un PDF digital y exige revisión de cada celda. No resuelve tablas curvas, diseños arbitrarios o todas las tablas multilínea; no certifica exactitud general del OCR.

## Revocación sin red

**Verificar firmas digitales → Revocación con evidencias locales** acepta hasta veinte CRL/respuestas OCSP DER o PEM individuales, con 4 MB totales. Usa la confianza pública seleccionada para esta operación, sin instalar certificados ni guardar evidencias en proyectos. La validación exige cobertura de revocación de la cadena y comprueba firma, emisor, vigencia y estado con el validador PKI existente, con descargas deshabilitadas.

Cada firmante muestra un resultado independiente: no comprobado, aceptado con evidencia local, revocado o inconcluso. Una cadena criptográficamente aceptada con evidencia incompleta no se presenta como libre de revocación. Cuando se aportan CRL y OCSP se comprueban por separado: una respuesta favorable no oculta una revocación acreditada por la otra clase. Evidencias caducadas, alteradas, ajenas o sin confianza suficiente no acreditan el resultado. Seleccionar al propio firmante como ancla tampoco acredita una cadena independiente.

La comprobación es a la fecha de revisión, no una validación histórica del momento de firma. OCSP requiere que el certificado declare ese servicio para que el validador lo considere. El resultado global de revocación se refiere exclusivamente a las cadenas de firmantes; no incluye la TSA. La revisión separada de tokens RFC3161 existente se mantiene. No hay solicitud TSA/OCSP de red, servicios remotos, PAdES-LT/LTA, sellos documentales de archivo ni acreditación jurídica.

## Verificaciones

Resultados finales, comandos y huellas: `validation/affine-perspective-revocation-20261031/results.json`.

Las muestras son sintéticas. Se comprueban fuentes originales, inclinación/escala/reflexión, matrices de texto y de gráficos, Forms compartidos y reedición tras reflujo, junto con conservación de vecinos y otras páginas. La tabla sintética se deforma mediante una homografía inversa y se reconoce realmente; no se simula la respuesta OCR. Las evidencias PKI son firmadas y verificadas criptográficamente, incluidos revocado/caducado/manipulado y conflicto CRL/OCSP. Los recorridos gráficos cubren controles reales, corrección/exportación y guardado Qt.

Qt Linux offscreen no acredita Windows, DPI, impresora física ni aceptación personal. No se ha generado un paquete para el usuario.

## Pendientes y siguiente avance

Los bloques 1–4 conservan pendientes en edición/estructura, formularios/XFDF y OCR/Office; los bloques 5–8 también siguen abiertos. Consultar `PLAN_ACTUAL.md` para el detalle estable. Lo implementado aquí no vuelve a proponerse como trabajo futuro.

Siguiente trabajo recomendado: reflujo de varios grupos transformados con revisión visual conjunta; etiquetas Lbl separadas y celdas vacías con estructura revisada; medición angular y revisión de escalas. En paralelo de planificación, reservar ejecución real Windows antes de generar candidato. Mantener generación de informes/registros/ensayos excluida. Modelo recomendado: **6.1 Sol, razonamiento medio**.
