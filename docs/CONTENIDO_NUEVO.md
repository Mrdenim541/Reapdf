# Texto nuevo, sellos y enlaces — versión 0.14

## Flujo común

Elige **Añadir texto**, **Sellos** o **Enlaces**, arrastra un rectángulo en la página y completa las propiedades. Pulsa **Aplicar** para verlo en el PDF. También puedes ajustar X, Y, ancho y alto en puntos PDF. La guía indica los borradores pendientes antes de guardar, exportar o imprimir.

Selecciona un elemento de la sesión en la página o en su lista para corregir sus propiedades. El marco y los tiradores permiten mover/redimensionar los elementos ya aplicados; las flechas del teclado dan ajustes finos. Aplica o cancela las propiedades pendientes antes de usar los tiradores. **Crear otro elemento** prepara una caja nueva. **Eliminar elemento**, Deshacer y Rehacer funcionan con estas operaciones.

Los proyectos y la recuperación conservan sus datos editables. Al organizar, recortar, insertar o duplicar páginas, los cambios quedan incorporados al PDF; deshaz esa operación para recuperar sus controles de sesión. Reabrir un PDF exportado los trata como contenido preexistente: esta entrega no ofrece editar todos esos objetos importados.

## Texto nuevo

Las cajas admiten de 1 a 2000 caracteres latinos, saltos de línea, ajuste de líneas dentro de la caja, las 12 variantes base de Helvetica/Times/Courier, tamaño 6–144 pt, color y alineación izquierda/centro/derecha. El texto queda como contenido vectorial, buscable y seleccionable; no se rasteriza la página. La selección y el marcado reconocen texto sobre los ejes de página, incluido el texto nuevo en hojas giradas.

Se comprueba que todo el texto cabe, con margen vertical para sus métricas de fuente. Si no cabe, ajusta dimensiones o tamaño antes de aplicar. Cambiar el tamaño de la caja reorganiza las líneas y conserva el tamaño de fuente. El fondo es transparente y se añade sobre el contenido existente; no elimina ni censura lo que cubre.

Esto permite escribir en una hoja en blanco o agregar texto a un PDF digital o escaneado. No aplica OCR al escaneado ni ofrece reflujo de párrafos existentes, fuentes arbitrarias, alfabetos fuera del conjunto admitido o formato distinto por palabra. La edición de líneas originales conserva sus límites anteriores, descritos en TEXTO.md. Se admiten los cuatro giros globales y páginas recortadas para las cajas nuevas.

## Sellos estándar

Hay cuatro apariencias nativas PDF Stamp: APPROVED, DRAFT, CONFIDENTIAL y NOT APPROVED. Los nombres de sus opciones se explican en español; el texto visible del sello estándar es inglés. Puedes elegir color, posición y tamaño. Se conserva la proporción de su apariencia dentro del área elegida, que debe medir al menos 40 × 15 pt.

Los sellos nuevos requieren páginas a 0°. Vuelve a esa orientación desde Organizar páginas antes de añadirlos. No hay sellos personalizados, dinámicos, fecha automática ni edición de sellos importados. Un sello es una anotación visual; no valida una identidad, aprobación ni firma criptográfica.

## Enlaces

Define un rectángulo de al menos 5 × 5 pt y un destino:

- Página del documento: se guarda como destino PDF interno y en Lectura lleva al inicio de esa página.
- Dirección web: HTTP/HTTPS completa, hasta 2048 caracteres, sin espacios, controles o credenciales. Solo se navega cuando activas el enlace.

En Lectura, el área responde al puntero y al teclado; al pasar por ella se muestra su destino y un contorno. Las direcciones web se abren aparte. En el PDF exportado el área es invisible y funciona con el lector que lo abra. Se muestran hasta 2000 enlaces de la página; otros tipos de acciones permanecen fuera del flujo interactivo de esta versión. No se crean enlaces a archivos locales, scripts o correo.

Los enlaces nuevos pueden modificarse en su sesión. Los enlaces internos se remapean al organizar páginas mediante las funciones existentes; los destinos eliminados se retiran. Falta editar o eliminar enlaces preexistentes desde la interfaz y validar un corpus amplio con lectores externos.

## Validación

Pruebas de motor/API cubren tamaño y desbordamiento, fuentes y alineación, cajas y enlaces en cuatro giros con y sin recorte, selección/búsqueda/marcado de texto, destinos inválidos, enlaces a la propia página girada, sellos nativos, permisos, firmas, proyectos y reordenación. Chromium crea y corrige elementos, mueve texto con teclado, sigue un enlace interno, inspecciona los PDF descargados y vuelve a editar tras abrir un proyecto y recuperar una sesión. La impresora física y Windows nativo siguen pendientes.
