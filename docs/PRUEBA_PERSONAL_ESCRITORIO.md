# Prueba personal de la futura entrega de Reapdf

Este documento define qué se probará cuando se entregue el ejecutable candidato. No es una afirmación de que la entrega Windows esté lista. No requiere que el usuario instale Python, Node ni abra el programa en un navegador. El instalador o paquete portable deberá incluir las dependencias necesarias.

## Antes de entregar

- Verificar el mismo código en Windows mediante la ventana Qt; conservar informe/huellas. La prueba Linux no sustituye Windows.
- Ensamblar el paquete completo, comprobar dependencias/licencias, arrancarlo en un Windows limpio y repetir apertura/edición/guardado/recuperación.
- Publicar una descarga accesible y su SHA256; comprobar la descarga. No presentar una ruta interna del entorno como enlace web de distribución.
- Incluir instrucciones breves, limitaciones vigentes y muestras sintéticas. Mantener el PDF personal fuera de cualquier repositorio/artefacto público.

## Recorrido de aceptación

Trabajar con copias de los documentos originales. Marcar cada paso como aprobado/fallido y anotar el archivo, acción, resultado esperado/observado y, si ayuda, una captura.

| Paso | Comprobación esperada |
|---|---|
| Inicio | Doble clic en Reapdf, identidad propia y ventana de aplicación; sin exigir navegador instalado. |
| Abrir | Abrir por menú y con Abrir con; una segunda apertura llega a la misma instancia. |
| Leer | Zoom, ancho/página, búsqueda y navegación fluidos; plano A0 legible dentro de los límites publicados. |
| Corregir una línea | Pulsar un texto digital, seleccionar caracteres con ratón/cursor, escribir y aplicar sobre la página. Fuente original en casos compatibles y motivo claro si no lo es. |
| Párrafo | Entrar a Editar párrafo desde una línea, cambiar texto, revisar ajuste y aplicar sin cortar contenido ni afectar vecinos. |
| Texto nuevo | Pulsar un punto y escribir; varias líneas, tildes, tamaño/color, altura automática y deshacer. |
| Objetos y marcas | Mover un logotipo compatible y dibujar/resaltar; no modificar firmas/sellos administrativos por accidente. |
| Guardar | Cancelar conserva cambios pendientes; guardar/reabrir conserva texto y objetos. Un archivo cambiado fuera del programa avisa antes de reemplazar. |
| Firmado | El original conserva su firma; una copia de trabajo requiere aceptación y queda identificada como sin firmas digitales. |
| Vínculos | Elegir archivos/roles, resolver códigos repetidos, guardar/reabrir. Cargar una revisión movida exige revisar destinos; comprobar PDF vinculado en otro lector. |
| Medir y OCR | Calibrar con una distancia conocida, medir y reabrir. OCR solo en región escaneada sin duplicar texto existente. |
| Recuperación | Cierre protegido y recuperación de cambios aplicados tras interrupción. Documentar el límite de borradores aún sin aplicar. |
| Impresión | Rango, cancelación y resultado en impresora real; revisar planos, fuentes, colores y escala. |
| Pantalla | Windows al 100/125/150/200 % de DPI, tamaño de ventana y pantallas utilizadas por el usuario. Sin controles inaccesibles. |

La aceptación de estos recorridos habilita una prueba personal útil; no certifica paridad universal con Acrobat, PDF/UA/PDF/X, seguridad independiente ni el 100 % del alcance total.
