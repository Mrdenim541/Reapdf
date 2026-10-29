# Texto con fuentes y estilos originales — versión 0.20

**Reemplazar bloque de texto** incluye un segundo modo: **Conservar fuente y estilo por fragmentos**. Corrige texto digital compatible manteniendo la fuente del PDF, su tamaño, color RGB, línea base y posición. Puede tratar un bloque con varias familias, negrita, cursiva, tamaños y colores diferentes sin convertirlo todo en DejaVu Sans.

## Cómo probarlo

El portable incluye `ejemplos/reapdf-texto-con-estilos.pdf`.

1. Abre **Reemplazar bloque de texto** y selecciona **Conservar fuente y estilo por fragmentos**.
2. En el ejemplo, la región inicial incluye las tres líneas de muestra. Pulsa **Leer bloque seleccionado**.
3. Cambia los textos por «Texto en negrita», «Estilo cursiva» y «Fuente original 123». Cada fragmento muestra su fuente, tamaño, color y disponibilidad de edición.
4. Genera **Vista previa conservando estilo**. Amplía la imagen para revisar tipografía y posición; después aplica.
5. Exporta y reabre el PDF; prueba Deshacer/Rehacer, proyecto y recuperación. La segunda página debe permanecer igual.

En la fuente parcial de la tercera línea, un carácter como «Ú» que no esté disponible se rechaza antes de aplicar. No se introduce una fuente alternativa de forma silenciosa. El modo de párrafo con DejaVu Sans sigue disponible como una elección explícita, con sus límites anteriores.

## Ancho y posición

Por defecto, el texto nuevo debe caber en el ancho que ocupa el fragmento en la versión actual. No se cambian tamaño, fuente ni posición para hacerlo entrar.

**Usar el ancho disponible del área seleccionada** permite crecer hacia la derecha dentro de esa región. Se comprueba que no salga de la página ni se cruce con otros textos. No desplaza fragmentos vecinos, no redistribuye líneas ni crea espacio entre páginas. Tras cambiar el texto o esta opción, hay que actualizar la vista previa.

Si acortas el texto y consolidas una versión, su ancho actual también cambia. Puedes deshacer para recuperar el anterior o permitir el uso del ancho del área al editar de nuevo.

## Fuentes y estructuras compatibles

- Las 12 fuentes PDF base estándar, sin programas incrustados, anchuras personalizadas ni codificaciones especiales; caracteres disponibles en WinAnsi o ASCII según la fuente.
- Fuentes TrueType incrustadas en `FontFile2`, con `Type0`, codificación `Identity-H`, mapa Unicode compatible, anchuras y correspondencia CID/glifo verificables.
- Se admiten programas TrueType completos y subconjuntos. Se comprueba que haya un contorno disponible o un espacio compatible: que un carácter aparezca en ToUnicode no demuestra que su glifo esté incluido en el subconjunto.
- Se reutiliza el recurso original de la fuente. No se extrae para crear otra tipografía ni se sustituye por una fuente instalada. Las pruebas comparan las huellas de los programas de fuente decodificados antes y después.

El color conservado es el RGB extraído del PDF; no se promete conservar separaciones CMYK, tintas planas o perfiles de impresión. El modo no reconstruye ajustes complejos de espaciado, escalas horizontales, ligaduras ambiguas, escritura contextual o vertical. Las fuentes CFF/Type3, fuentes externas sin un programa verificable, mapas heredados y otras codificaciones todavía quedan protegidos.

Desde 0.25 admite páginas con giro de 90°/180°/270° mediante una vista enderezada que conserva la orientación final. Requiere texto directo, fragmentos completos y una región sin imágenes, campos o anotaciones. Bloquea capas, Form XObjects, contenido marcado, recortes y determinadas transparencias/patrones, así como texto oculto, contorneado o con ajustes no verificables. Algunas páginas etiquetadas o creadas por programas comerciales pueden entrar en estas restricciones. No es soporte universal de PDF ni conservación de todo su diseño.

Se permiten hasta 100 fragmentos y 4000 caracteres por región, 20 recursos de fuente por página, programas individuales de hasta 16 MB y hasta 64 MB de programas procesados. Los mapas y flujos tienen límites de lectura/descompresión propios, independientes de los tamaños declarados por el archivo.

## Conservación y guardado

Solo se retiran y reescriben los fragmentos modificados. Se conservan los demás textos y los recursos gráficos. Los diccionarios de recursos se separan antes de limpiar el texto para que una edición no retire fuentes de otras páginas que los compartan. La operación respeta firmas/permisos y conserva el cifrado cuando corresponda.

Aplicar crea una versión reversible y consolida los cambios anteriores, igual que el reemplazo de párrafo. El proyecto y la recuperación guardan esa versión aplicada; los borradores del diálogo no se guardan. La eliminación o sustitución de texto con esta herramienta **no equivale a censura o saneamiento**; el original, las versiones y otros objetos pueden conservar información.

## Evidencia

- **988 pruebas Python y 63 JavaScript: 1051 pruebas automáticas aprobadas**, compilación y recorrido completo de Chromium en Linux.
- 67 pruebas específicas del modo nuevo: 12 fuentes base, TrueType completo/parcial, rechazo de caracteres ausentes, varios estilos, límites, codificaciones, colisiones, ancho opcional, recortes, recursos compartidos, permisos/cifrado, proyectos y API.
- Poppler extrae y contrasta el texto exportado. Sus imágenes de salida se comparan con un PDF escrito por separado usando las fuentes esperadas; se comprueba la apariencia con fuentes completas y parciales, además de conservar otras páginas.
- Chromium verifica caracteres rechazados, ampliación opcional de ancho, invalidación de vistas previas, exportaciones reales, programa de fuente intacto, estilos/posiciones, deshacer/rehacer, proyectos y recuperación tras recarga.
- La autoprueba portable incluye edición con TrueType parcial y comparación del programa de fuente. Se ejecuta con Python Linux; el ZIP Windows solo se valida estáticamente. Sigue pendiente la ejecución real en Windows.

## Próximos trabajos

Ampliar tipografías/codificaciones y páginas con estructuras complejas; añadir reflujo controlado de párrafos; reconstruir correctamente los árboles al copiar formularios jerárquicos. Mantener la validación con más documentos reales y el portable Windows como trabajos abiertos.
