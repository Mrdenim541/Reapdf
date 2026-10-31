# Búsqueda con comodines y medición de trazados del PDF

Se amplían funciones de uso diario y de planos. Esta pasada no cierra los ocho bloques generales ni constituye una entrega final. Las pruebas personales del usuario se mantienen después de la entrega técnica.

## Buscar y reemplazar

En **Editar → Buscar y reemplazar**, el modo «Texto exacto» mantiene el comportamiento anterior. «Comodines tipo Excel» admite `?` para un carácter y `*` para varios, incluidos espacios dentro del mismo grupo digital contiguo. `~*`, `~?` y `~~` buscan los signos literales. Se elige la coincidencia más larga a partir de la primera posición posible; no cruza líneas ni inventa espacios entre columnas.

Ejemplo: `COD-?` permite localizar `COD-1`, `COD-2`, etc. Se conservan opciones de mayúsculas, palabra completa, página/rango/documento, selección de resultados, fuentes y estilos compatibles, vista previa y deshacer/rehacer. «Revisar reemplazo actual» prepara directamente la coincidencia mostrada, sin tener que marcarla primero; todavía exige revisar y aplicar. Entrar en el campo de búsqueda inicia la consulta.

El buscador usa programación dinámica acotada, no ejecuta expresiones regulares del usuario ni código PDF. Tiene un presupuesto acumulado de diez millones de estados, máximo de 500 coincidencias para inspección y hasta 100 coincidencias/fragmentos por reemplazo. La consulta completa, el modo y las operaciones pendientes quedan vinculados al comprobante y al token de vista previa. No se aplican planes antiguos a otra consulta. Las fuentes o geometrías incompatibles permanecen protegidas; no se convierten en texto aproximado para forzar un resultado.

## Longitud y área de un trazado

En **Documentos → Medir planos**, calibra o usa una referencia guardada. Elige longitud o área y pulsa «Seleccionar trazado del PDF»: puedes elegirlo sobre la muestra o en la lista. Los contornos cerrados sirven para área y para longitud completa. También se puede cerrar una polilínea manual con «Cerrar recorrido».

Las líneas y curvas Bézier compatibles se convierten en una polilínea revisable de hasta 200 vértices. La longitud se acota mediante cuerda y polígono de control; la desviación se acota con cápsulas que contienen los controles y detectan retrocesos colineales. Se busca un margen de longitud de 0,02 pt y desviación de 0,05 pt; **no se afirma que todos los trazados alcancen esos objetivos**. Si se alcanza el límite de vértices, se muestra el margen real mayor. Se rechazan trazados cuyo margen o desviación supera 1 pt, además de los límites por página y de trabajo.

La vista previa expresa el margen en la unidad real elegida. Para áreas se usa una cota conservadora basada en longitud y desviación de la frontera. Estos márgenes cubren la aproximación geométrica, no errores del plano o de calibración. La etiqueta se identifica como aproximada y adapta sus decimales al margen; no se presenta la polilínea como la curva original exacta.

Al guardar se conserva la referencia a la geometría, además de trazado y etiqueta PDF. Al leer se comprueban otra vez el origen, los vértices y el margen, incluyendo desplazamientos por serialización. Si el origen cambió o no puede identificarse, no se acredita su margen anterior. Editar manualmente un vértice convierte el recorrido en una medición manual. Una aproximación no puede alcanzar el límite de una región con otra escala.

Se admiten recortes rectangulares que contienen toda la geometría comprobada. Se omiten recortes que la cortan, capas no verificadas, casos ambiguos y geometrías fuera de los límites. Se conservan el fondo del plano, textos y otras páginas; las anotaciones se añaden por separado.

## Ajuste e intersecciones

El cursor puede proyectarse sobre trazados compatibles; en curvas utiliza la polilínea aproximada, con prioridad para los vértices disponibles. Las proyecciones equidistantes no fuerzan una elección.

Se añaden cruces de segmentos finitos con curvas Bézier cúbicas. Se aíslan raíces por intervalos monótonos y se comprueba su posición en la línea y la curva originales, incluyendo tangencias y hasta tres raíces. No se utilizan los cruces de la polilínea aproximada para simular esos puntos. Los solapamientos colineales se omiten porque no tienen un punto único. Hay límites explícitos de comparaciones y resoluciones; las intersecciones entre dos curvas siguen pendientes.

## Verificación y pendientes

**Revisión dbb770254aacff0ed773d0ee74de3a86aa76726e comprobada:** 3721 pruebas Python, tres avisos conocidos, 130 JavaScript, compilación, recorridos Chromium nuevo y cotidiano, y doce recorridos de escritorio Qt aprobados tanto en Windows Server 2025 como en Linux. Fuente limpia antes/después. El paquete interno Reapdf.exe también pasó su comprobación real; no se entregó ni publicó. Comprobante Git de CI `41228351049-1`, verificado contra fuente, objetos y logs; SHA256 del paquete `26c55c0842b60ade24eb1976aea049ad92cf0d46e72b97d16a65ae3ca84d103c`. Evidencia en [validation/wildcards-curves-20261031/results.json](validation/wildcards-curves-20261031/results.json). La prueba de funciones nuevas es desde fuente Qt; el recorrido empaquetado acredita arranque/edición cotidiana/exportación/cierre, no todos los diálogos nuevos por separado. Windows cliente limpio/DPI/impresión física siguen pendientes.

La estimación global pasa de 85,18 % a **85,26 % (≈85 %)** por los trazados y cruces compatibles: área de medición 95 → 97,5. Se mantienen diecisiete pesos y alcance; los comodines fortalecen edición sin sumar otra madurez a un área ya estimada alta. La cifra es provisional, no un porcentaje objetivo de paridad comercial ni una previsión temporal. El programa no está completo. La documentación de cierre se actualiza después de comprobar el código; no modifica ejecutables ni funciones. La guía integrada y el manual se han actualizado. La verificación privada del PDF previamente compartido usa la ventana Qt y guardado atómico; original, imágenes, dibujos y programas de fuente comprobados, con copia y detalles fuera de Git.

Permanecen las implementaciones y verificaciones del plan vigente, incluida edición avanzada, XFA, accesibilidad general, OCR/Office, firmas/estándares, variantes técnicas, Windows cliente y servicios. El código no se declara al 100 % por completar estos subconjuntos.
