# Probar Reapdf en tu PC

Esta entrega contiene el código y comandos de arranque; todavía no es un instalador de aplicación independiente. El servidor iniciado en la nube pertenece a la máquina de desarrollo y no se abre usando la dirección local de tu PC.

## Portable sin instalación

La entrega `Reapdf-portable-Windows-x64.zip` incluye Python y dependencias para Windows 10/11 de 64 bits. Extrae todo y abre **Iniciar-Reapdf.cmd**. No requiere Python, Node.js ni privilegios de administrador instalados. Detalles y límites de validación en [PORTABLE.md](PORTABLE.md). El paquete todavía no se ha ejecutado en Windows desde este entorno.

## Windows: entrega de código

1. Instala **Python 3.12** desde https://www.python.org/downloads/ con el lanzador `py`, y **Node.js 24** desde https://nodejs.org/ con npm. Si acabas de instalarlos, abre una terminal nueva.
2. Extrae completamente el ZIP de prueba en una carpeta, por ejemplo `C:\Reapdf`. No ejecutes los archivos desde dentro del ZIP.
3. Haz doble clic en `instalar.cmd`. Necesita Internet para descargar dependencias verificadas. Al terminar debe aparecer «Instalacion completada».
4. Haz doble clic en `iniciar.cmd` y deja la ventana abierta.
5. Cuando aparezca `Application startup complete`, escribe `http://127.0.0.1:8000` en el navegador de ese mismo PC.
6. Pulsa **Abrir PDF** y selecciona `ejemplos/reapdf-demo.pdf`, incluido en el ZIP.

Los comandos para Windows están preparados, pero todavía no se han ejecutado en Windows en este proyecto. La validación actual corresponde a Linux y Chromium. Si aparece un error, guarda el texto de la ventana y la operación que estabas realizando, sin incluir documentos privados.

## Recorrido de aceptación

- Cambia de página y prueba el zoom. Usa **Páginas** para navegar por miniaturas e **Índice** para abrir los marcadores del ejemplo.
- En modo **Lectura**, selecciona texto con el ratón y cópialo con Ctrl+C.
- En **Buscar**, escribe una palabra o frase y navega entre coincidencias. Después de editar, la búsqueda debe usar el texto nuevo.
- En **Editar texto**, selecciona «Texto original» y reemplázalo por «Texto nuevo». La nueva frase debe caber en la región original.
- Al editar, prueba **Fuente de texto**, **Tamaño de texto** y **Color del texto**. Usa un texto corto al aumentar el tamaño. Un cambio que invade otro texto o sale de la página debe rechazarse.
- Dibuja con **Lápiz**. Cambia el color y el grosor.
- Arrastra para crear una **Línea**, **Flecha** y **Rectángulo**.
- Prueba **Resaltar**, **Subrayar** y **Tachar**: haz clic en una palabra o arrastra sobre el texto; las marcas abarcan palabras completas.
- En **Nota**, haz clic lejos de los bordes, escribe su contenido y pulsa **Guardar nota**. En **Seleccionar marca** puedes corregirlo y guardarlo de nuevo.
- En **Seleccionar marca**, pulsa el borde de una de tus marcas y luego **Eliminar marca**. Prueba **Deshacer** y **Rehacer**.
- Con una marca seleccionada, arrastra el tirador circular para moverla y el de la esquina inferior derecha para cambiar su tamaño. **Escape** cancela el arrastre; las notas solo se mueven.
- Prueba **Posición X/Y**, **Ancho/Alto de marca** y **Aplicar posición y tamaño**. Una posición fuera de página debe rechazarse sin añadir historial. Con el foco en un tirador, las flechas ajustan 1 punto y Mayús+flecha ajusta 10.
- En **Organizar páginas**, cambia el orden con las flechas, gira una selección y aplica. Prueba **Deshacer/Rehacer**.
- Abre de nuevo el organizador y usa **Extraer selección** para descargar otro PDF sin modificar el documento abierto.
- Prueba eliminar una página: no se permite eliminar todas.
- En **Unir o insertar PDF**, selecciona otro archivo, prueba un rango como `2,1` y elige la posición. Comprueba **Deshacer/Rehacer**. Para unir todo el archivo al final, deja los valores por defecto.
- En **Recortar páginas**, selecciona páginas y configura márgenes en puntos. Comprueba el área delimitada, aplica y prueba deshacer/rehacer. Usa **Restaurar página completa** para volver a MediaBox. No elimina contenido oculto.
- En **Reemplazar páginas**, elige otro PDF, un rango de origen, el inicio y cuántas páginas originales retirar. Verifica que las demás páginas conservan su contenido y prueba deshacer/rehacer.
- En **Dividir PDF**, prueba bloques de dos páginas y luego grupos personalizados, uno por línea. Debes incluir todas las páginas exactamente una vez. Extrae el ZIP y comprueba orden, notas y giros. Dividir no marca los cambios pendientes como exportados.
- Pulsa **Exportar copia**. Abre el archivo descargado en Acrobat u otro lector y comprueba texto, anotaciones y ambas páginas.
- El archivo original debe seguir intacto.

En **Seleccionar marca**, el panel **Marcas del PDF** permite seleccionar anotaciones preexistentes, incluidas las reabiertas desde una exportación. Prueba cambiar el color, corregir una nota, borrar un resaltado y deshacer/rehacer. Las anotaciones bloqueadas, hilos y tipos no compatibles muestran el motivo de solo lectura. El movimiento/tamaño importados está pendiente; los tiradores siguen disponibles para marcas nuevas de la sesión. Los cambios sin exportar se pierden al recargar o cerrar.

La edición de texto admite líneas simples de Helvetica, Times y Courier con sus variantes reconocidas, sin rotación y de un solo fragmento. Si no aparecen recuadros seleccionables, puede tratarse de otra fuente o de un escaneado; OCR pendiente. Para evaluar esta función comienza por el ejemplo incluido.

## Problemas habituales

| Mensaje o situación | Qué hacer |
|---|---|
| `py` no se reconoce | Instala Python 3.12 incluyendo su lanzador `py` |
| `node` o `npm` no se reconoce | Instala Node.js 24 y abre una terminal nueva |
| Error al descargar dependencias | Comprueba conexión y el mensaje del registro; conserva las verificaciones TLS |
| El navegador no conecta | Mantén `iniciar.cmd` abierto y comprueba que el servidor arrancó |
| Puerto 8000 ocupado | Cierra otra instancia de Reapdf que tú hayas iniciado; no termines procesos desconocidos |
| Texto demasiado largo | Acorta el reemplazo; el ajuste de párrafos todavía está pendiente |

Las dependencias se descargan durante la instalación. El procesamiento de tus PDF no necesita servicios externos. Para cerrar, exporta tus cambios y pulsa Ctrl+C en la ventana de arranque.

En 0.11 prueba zoom 200/400 %, **Ajustar ancho** y **Página completa**. Tras una breve actualización debe mejorar la nitidez del texto digital. Las herramientas están agrupadas y su guía explica el gesto. Aplica o cancela los cambios del panel antes de exportar. Véase USABILIDAD.md.

En 0.12 abre **Imágenes** e inserta un PNG/JPEG de hasta 2 MB. Prueba selección, movimiento, tamaño, eliminación e historial; exporta y abre el resultado. Solo se modifican imágenes nuevas. Véase IMAGENES.md y ESCRITORIO.md.

En 0.13 prueba Guardar proyecto y Abrir proyecto, espera al checkpoint y reinicia el motor antes de Recuperar sesión. Inserta dos hojas Carta, duplica una página editada y deshaz/rehaz. Archivo → Imprimir… abre el PDF para usar la impresión de su lector. Véanse SESIONES.md, PAGINAS_NUEVAS.md e IMPRESION.md.

En 0.14 prueba el modo ventana y su cierre; si falla, utiliza Abrir-en-navegador.cmd. Crea una caja en Añadir texto, aplícala y corrige su contenido. Añade un sello en una página a 0° y dos enlaces (página/web); comprueba el interno en Lectura y exporta. Guarda/abre el proyecto para continuar editando. Detalles en CONTENIDO_NUEVO.md y ESCRITORIO.md.

En 0.15 prueba Editar marcadores (crear hijo, mover rama y cambiar destino), Numerar páginas (inicio, ceros o romano, rango y vista previa) y Encabezados y pies (corregir y retirar configuración). Guarda/reabre proyecto y exporta para comprobar el índice y el texto. Guía detallada en MARCADORES_Y_ENCABEZADOS.md.

En 0.16 abre ejemplos/reapdf-formulario.pdf y usa Rellenar formulario. Comprueba texto, casilla, ciudad, notas y campo de solo lectura; aplica vista previa, guarda/reabre proyecto y exporta PDF. Crea otro PDF desde dos PNG/JPEG, cambia su orden y exporta páginas como imágenes a distinta resolución. Consulta FORMULARIOS.md y CONVERSIONES.md.

El avance largo 0.17 añade OCR, datos/aplanado/diseño de campos, imágenes existentes, bloques de texto, marca de agua, metadatos, optimización, cifrado/apertura y comparación. Usa los tres PDF sintéticos del portable. Guía de cada flujo y limitaciones: AVANCE_LARGO_017.md.

Desde 0.30, los asistentes de estándares consultan la disponibilidad de Java, Ghostscript y los recursos verificados. En este entorno Linux están disponibles; el antiguo portable 0.20 no incluye estas capacidades nuevas. La entrega del ejecutable propio y sus dependencias seguirá los criterios de validación Windows acordados. Guía: [ESTANDARES_Y_ACCESIBILIDAD.md](ESTANDARES_Y_ACCESIBILIDAD.md).
