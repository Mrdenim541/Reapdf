# Imágenes nuevas — versión 0.12

## Uso

1. Abre un PDF y elige **Imágenes** en Leer y editar.
2. Pulsa **Insertar imagen** y selecciona un PNG o JPEG. Aparece centrado, sin salir de la página.
3. Selecciona la imagen en la página o en **Imagen de la sesión**. Esto permite elegir imágenes superpuestas.
4. Arrastra el marco azul o su tirador superior para moverla. Arrastra la esquina inferior derecha para redimensionarla conservando la proporción actual. Escape cancela el gesto. Las flechas del teclado permiten ajustes finos; Mayús aumenta el paso.
5. Para medidas exactas, introduce X, Y, ancho y alto en puntos PDF y pulsa **Aplicar posición y tamaño**. Los valores numéricos permiten cambiar la proporción; usa Cancelar para restaurar los aplicados.
6. **Eliminar imagen**, Deshacer y Rehacer permiten corregir la sesión. Exporta una copia para conservar el resultado.

## Calidad y alcance

Se incorpora la imagen como contenido PDF, sobre el contenido anterior, sin convertir la página entera en una imagen. No se reducen sus dimensiones en píxeles al moverla o cambiar su tamaño. El flujo JPEG original se conserva; PNG puede convertirse en los flujos internos PDF y conserva el canal alfa. No se garantiza conservar metadatos de fotografía, perfiles de color o formatos de alta profundidad. La orientación EXIF de fotografías y un corpus amplio de variantes aún requieren validación. La pantalla mantiene los límites de resolución descritos en USABILIDAD.md.

No es una herramienta de censura: cubrir texto con una imagen no elimina ese texto. No se admiten recorte interno de imagen, filtros, giro independiente, orden entre objetos ni modificación de imágenes ya incorporadas al PDF de origen. Las anotaciones PDF se muestran por encima del contenido según el lector.

Al organizar, insertar/reemplazar o recortar páginas, los cambios anteriores quedan incorporados en la nueva versión del documento. Las imágenes pasan a ser contenido existente; deshacer esa operación recupera la versión con los controles de sesión. Al exportar y volver a abrir también se consideran contenido existente.

## Límites y arquitectura

- PNG/JPEG de hasta 2 MB y 24 millones de píxeles por imagen; se comprueban sus cabeceras antes de decodificar.
- Hasta 4 MB de datos de imagen codificados, sumados entre todas las páginas de la sesión. La solicitud completa sigue limitada a 5 MB. El mensaje explica cuándo exportar y volver a abrir para insertar más; las imágenes incorporadas dejarán de ser editables en la sesión nueva.
- Cada dimensión visible debe medir al menos 1 punto, dentro de la página. La importación inicial encaja la imagen en un máximo del 60 % de ancho y alto visibles.
- Los PDF firmados o sin permiso de modificación no admiten inserción. Los permisos de anotación por sí solos no permiten cambiar contenido.
- El prototipo mantiene los datos originales codificados en sus operaciones para que historial, vistas y composición de páginas usen la misma exportación validada. Desde 0.13 el proyecto y checkpoint conservan estos datos; el historial completo y un almacén separado de recursos aún están pendientes.

## Validación

32 pruebas nuevas de motor/API cubren posición y orientación en cuatro giros con y sin CropBox, conservación del JPEG original, transparencia PNG, píxeles originales, preservación de texto y otras páginas, cabeceras y posiciones inválidas, dimensiones excesivas, presupuesto de datos, permisos, firmas, vista previa, exportación, orden y recorte.

8 pruebas JavaScript validan lectura de cabeceras y rechazo de formatos inválidos. La geometría verifica que mover o escalar conserva los datos originales. Chromium inserta, ajusta medidas, mueve y redimensiona con ratón, borra, deshace y comprueba los píxeles, dimensiones y región del PDF descargado. Pendiente Windows y lectores independientes.
