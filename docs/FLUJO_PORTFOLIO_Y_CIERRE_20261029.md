# Flujo original, portfolios y cierre nativo

29 de octubre de 2026. Cuatro bloques implementados y comprobados dentro de los límites siguientes. **Avance global estimado: 74,60 % (≈75 %), antes 73,33 %.** Diecisiete áreas y pesos sin cambios. La subida corresponde a edición, interfaz, portfolios y fiabilidad; no es una medición objetiva de paridad con Acrobat ni horas restantes. [Matriz](avance-global.json), [plan](PLAN_ACTUAL.md).

## 1. Edición en objetos estirados

El editor de fuente original admite matrices positivas independientes por eje, tanto en contenido directo compatible como en apariciones de Forms compartidos. Se conserva la relación de escala, espaciado, programa original y ruta privada del objeto. Se comprueban Helvetica, TrueType, OpenType CFF y CID CFF, además de las cuatro rotaciones de página. Una aparición editada no altera las demás ni otra página. El texto ampliado tampoco puede salir de los recortes de Forms.

Límite de relación horizontal/vertical 0,1–10. No incluye giro interno, inclinación, reflexión, transparencia ni estructura semántica de Forms; CFF2, fuentes variables y Type3 continúan pendientes. No se trata de convertir cualquier PDF a texto libremente editable.

## 2. Flujo entre regiones conservando fuentes originales

Nuevo modo en «Continuar texto entre regiones»: conserva los programas de fuente, tamaños y colores de los fragmentos compatibles al distribuir el texto entre áreas de una o varias páginas. Permite alineación izquierda/centro/derecha/justificada y reducción proporcional explícita. Cada identificador se vuelve a validar contra el documento; el plan debe caber completo antes de modificarlo. Tras guardar se vuelve a leer el contenido y se comprueban los límites geométricos. No se sustituyen fuentes ni se recortan silenciosamente palabras.

La interfaz permite arrastrar un rectángulo sobre la página para definir la región, además de las coordenadas. «Continuar en otra región», desde el párrafo sobre la página, traslada el borrador cuando se identifica el mismo bloque. Se conserva la comparación de todas las páginas y el cambio completo puede deshacerse. Al cambiar la página se evita mostrar la imagen anterior bajo coordenadas nuevas.

Hasta ocho regiones, 12000 caracteres y 200 estilos originales, tamaños de 6–72 pt. Cada bloque original conserva el límite de inspección de 4000 caracteres. Solo regiones explícitas de texto directo compatible: sin etiquetas, capas, Forms, recortes o gráficos/enlaces/imágenes/campos/anotaciones que interfieran. Las continuaciones deben estar vacías. No crea páginas, desplaza contenido vecino ni ofrece selección continua entre todos los objetos. Los modos anteriores con familias Reapdf permanecen disponibles y avisan de la sustitución.

## 3. Portfolio PDF nativo

Herramienta separada «Portfolio PDF» en Documentos. Crea una colección PDF nativa con esquema de título, descripción y orden; configura lista detallada, mosaicos o portada primero. Permite editar metadatos, ordenar, filtrar y descargar archivos; guardar/reabrir, deshacer y retirar la presentación conservan los adjuntos. Para añadir o retirar archivos se mantiene «Archivos adjuntos».

El catálogo usa `/Collection`, `/Schema`, `/Sort` y cada archivo conserva su `/CI`. Se eleva la versión efectiva a PDF 1.7 cuando hace falta. Lectura comprobada también con el analizador de pyHanko, independiente de MuPDF. Normalización acotada de árboles de adjuntos anidados: ocho niveles, 200 nodos y 100 archivos; rechazo de ciclos, claves repetidas y nodos ambiguos. La descarga conserva los límites existentes: 8 MB, tamaño real comprobado y compresión simple.

Los esquemas externos personalizados se consultan sin sobrescribirlos. No se implementan carpetas de colección ni edición general de sus campos externos. No abre ni ejecuta adjuntos. Su presentación en otros visores y Acrobat/Nitro aún requiere verificación allí; escribir la estructura nativa no acredita esa aceptación externa.

## 4. Cierre fiable de la ventana propia

La comprobación Qt descubrió un aborto de Python al terminar una carga fallida mientras un hilo daemon leía `stdin.buffer`. Se sustituyó por sondeo no bloqueante del conducto desde un temporizador Qt, sin ese hilo: `select` en POSIX y `PeekNamedPipe` en Windows. El control de carga fallida exige ahora código de salida 1, en lugar de aceptar cualquier error que pudiera ocultar un aborto. Qt Linux comprobó ese cierre limpio y que la ventana sale tras morir su padre. Se incluyó el nuevo módulo en la lista de preparación del paquete, sin ensamblar ninguno.

La ruta Windows está implementada pero no ejecutada en Windows. No se aumenta la valoración de distribución por esta preparación.

## Validación y evidencia

Los resultados finales y registros están en [validation/flow-portfolio-native-20261029](validation/flow-portfolio-native-20261029), con huellas del código y compilación. **2509 pruebas** en la regresión Python repetida; **42 dirigidas** posteriores del cierre/paquete, incluidas tres nuevas del conducto; **112 JavaScript** y compilación aprobadas. Tres recorridos Chromium aprobados (nuevo bloque, flujo mixto anterior y CFF/Form/párrafo anterior). El recorrido Chromium nuevo comprueba traslado del borrador, regiones con ratón, flujo original entre páginas, comparación/exportación/deshacer/rehacer, metadatos de portfolio, reabrir/filtrar/descargar/deshacer y edición de un Form estirado. Tres controles Qt Linux: arranque y carga fallida, edición/guardado atómico y muerte del padre.

Una primera regresión encontró un timeout de arranque del hijo simulado de una prueba; su módulo completo volvió a pasar y se repitió la regresión. El aborto real de Qt se detectó en la comprobación de integración aparte y quedó corregido y vuelto a comprobar. La regresión repetida comenzó antes de ese último ajuste de cierre; las pruebas dirigidas y recorridos Qt posteriores cubren el cambio final. No se presenta como una única ejecución sobre una fuente inmutable.

Sin prueba personal, Windows, impresión física, nuevo portable, instalación de REA ni inspección de programas comerciales. Documentos privados y capturas fuera de Git. No se considera terminado el alcance completo.

## Siguiente trabajo concreto

- Medición: ajuste a vértices, edición de vértices y escalas por región, con coordenadas conservadas al guardar.
- Intercambio de anotaciones: ampliar los subtipos/geometrías XFDF pendientes con relectura independiente, sin anunciar hilos/estados ya presentes como novedades.
- Compatibilidad restante de edición: matrices inclinadas/reflejadas y estados gráficos de Forms; después CFF2/variables/Type3 según corpus representativo.
- Candidato Windows: migrar el recorrido histórico y ejecutar DPI, asociaciones, recuperación, impresión y paquete en Windows limpio cuando corresponda.

Para justificar un 90 % global aún hacen falta avances en formularios complejos, OCR/conversión Office, firmas/estándares, accesibilidad, interoperabilidad, fiabilidad y aceptación. Los cuatro bloques de esta pasada no completan esas áreas. Mantener el alcance y no aumentar el porcentaje por acumular pruebas o preparar herramientas.

Modelo recomendado para continuar: **6.1 Sol, razonamiento medio**.
