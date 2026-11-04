# Reapdf · versión de prueba para Windows

Esta entrega se prepara por petición expresa del usuario para probar el estado actual. **No es la versión final ni un programa completado al 100 %.** Estimación total vigente: 86,87 % provisional; generar el portable no añade puntos. Funciones y límites: `docs/MANUAL_DE_FUNCIONES.md` y `docs/PLAN_ACTUAL.md`, incluidos en el ZIP.

## Descargar y abrir

1. Descarga **Reapdf-prueba-20261104-Windows-x64.zip** desde los archivos de esta publicación. No elijas los archivos automáticos «Source code».
2. Pulsa con el botón derecho en el ZIP → **Extraer todo**. Espera a que termine.
3. Abre la carpeta extraída **Reapdf-portable** y haz doble clic en **Reapdf.exe**. Aparecerán el logo de inicio y la ventana del programa.
4. Mantén todo el contenido de la carpeta extraída junto al ejecutable, especialmente `app` y `runtime`. No ejecutes el programa dentro del ZIP ni copies solo el `.exe`.

Es un portable para **Windows 10/11 de 64 bits**: no instala Reapdf ni requiere que instales Python, Node o Tesseract. Incluye OCR español/inglés y abre una ventana Qt propia. La edición habitual funciona localmente y sin suscripciones. Algunas funciones de estándares necesitan Java/Ghostscript externos y la generación opcional con Ollama necesita un modelo local propio; no se descargan automáticamente.

El ejecutable no está firmado digitalmente. Si Windows o las políticas de tu equipo lo bloquean, consulta con TI; no desactives sus protecciones. La huella SHA256 del ZIP se ofrece junto a la descarga. Se comprueba en Windows Server 2025; Windows 10/11 cliente, DPI e impresión física siguen pendientes de verificación.

## Primera prueba · unos minutos

1. Abre `ejemplos/reapdf-demo.pdf`. Prueba navegación, búsqueda y zoom 200/400 %.
2. En **Editar → Editar texto**, pulsa directamente sobre un texto del documento. Coloca el cursor, modifica el texto y aplica con **Ctrl+Enter**. No necesitas buscarlo en un panel lateral.
3. Para añadir texto, activa **Añadir texto**, pulsa un lugar vacío y escribe. Ajusta ancho/tamaño si hace falta y pulsa **Ctrl+Enter**.
4. Prueba un trazo o comentario y **Deshacer/Rehacer**. Guarda una copia con **Archivo → Guardar como** y vuelve a abrirla para comprobar texto y apariencia. Conserva el original.
5. Prueba después una copia de uno de tus documentos habituales. Ante un fallo, anota la herramienta, el paso exacto, el resultado esperado y el mensaje mostrado. No publiques documentos personales al informar del problema.

Para un PDF firmado, conserva el original. Una firma digital no puede conservar su validez si se cambia el contenido firmado; usa la opción de copia de trabajo cuando corresponda. Las restricciones de documentos certificados pueden impedir operaciones.

## Ayuda

- El menú **Guía y atajos** explica las herramientas. El manual completo incluido cubre 75 herramientas y 15 operaciones generales, con sus límites.
- Si no abre, ejecuta **Diagnosticar.cmd** y revisa los registros indicados en `%LOCALAPPDATA%\Reapdf\logs`.
- Los proyectos y las copias se guardan donde elijas. La recuperación local queda en `%LOCALAPPDATA%\Reapdf`, fuera del portable.
- **Abrir-en-navegador.cmd** es una alternativa opcional; para la prueba del programa utiliza **Reapdf.exe**.

La compilación se publica después de comprobar la ventana nativa y el ejecutable Windows. Esas pruebas no certifican que todas las variantes de PDF sean editables ni que el programa esté terminado.
