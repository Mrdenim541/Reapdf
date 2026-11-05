# Fuente, estilo y tamaño dentro de texto nativo etiquetado · 5 de noviembre de 2026

Se amplía una capacidad concreta que seguía pendiente: cambiar fuente y tamaño dentro de líneas nativas etiquetadas o en Form compatibles. Antes, esas líneas conservaban obligatoriamente la fuente/tamaño originales; la alternativa DejaVu para texto simple ya existía y no se contabiliza otra vez. El resultado incorpora la fuente al PDF y conserva texto editable, matriz, color, recortes, estructura y lectura accesible verificables.

## Uso

1. En **Editar → Editar texto**, pulsa el texto de la página. Elige **Fuente**, **Estilo** y tamaño; aplica o usa **Ctrl+Enter**.
2. **Original** conserva la fuente y admite cambiar solo su tamaño. Las fuentes incluidas son DejaVu Sans, Serif y Sans Mono, cada una regular, negrita, cursiva y ambas: doce variantes. El tamaño del perfil nativo va de **6 a 144 pt**.
3. Mediante **clic derecho → Editar**, abre **Fuente y tamaño** en el cuadro compacto para los mismos ajustes. Esa sección está plegada al abrir para mantener simple el cambio de texto habitual.
4. Si hay ActualText distinto, revisa la lectura accesible. Si coincide con el texto visible, ambos se actualizan juntos. Cancelar conserva el original; un fallo deja el borrador disponible. Deshacer/Rehacer recupera versiones; al volver a una versión el programa puede regresar a lectura y necesitar elegir Editar texto.
5. Aplica el cambio de formato antes de abrir reflujo o edición de párrafo. La nueva fuente se conserva en el reflujo existente cuando el contenedor/recorte lo permite; no se amplía un recorte para hacer caber texto.

El cambio de fuente permite introducir caracteres como Ω aunque no existan en la fuente original, siempre que estén en la incluida y pertenezcan al perfil de composición admitido. No se descarga una fuente ni se usa un servicio externo.

## Conservación del documento

- El motor sustituye únicamente el grupo y sus parámetros tipográficos verificados, restablece fuente/tamaño y matriz de línea para los grupos posteriores y añade recursos de fuente aislados. No borra el texto para cubrirlo con una caja ni rasteriza la página.
- Los Form con etiquetas de página aíslan la aparición elegida. Los streams con StructParents/MCR/Stm propios mantienen identidad cuando tienen una única aparición en todo el documento. Los streams etiquetados compartidos siguen protegidos.
- ActualText inline o de nodo se coordina con el texto visible mediante el plan semántico existente. Las referencias, ParentTree y marcadores se comprueban en el PDF guardado, junto con texto, geometría, color, opacidad, posiciones de caracteres y vecinos no seleccionados.
- Conserva Tc/Tw y los ajustes TJ entre pares coincidentes. Una fuente CID no aplica Tw al espacio de dos bytes: se representa ese espacio adicional explícitamente en TJ para no perderlo al sustituir la fuente.
- Los atributos Layout compatibles y BBox, Table y List permanecen intactos. Se revisan solo el elemento seleccionado y sus antecesores; una caja declarada debe coincidir con el texto y contener también el resultado. La tipografía declarada, clases o atributos no verificables no se contradicen silenciosamente: impiden el cambio de formato y muestran su motivo.
- Las ampliaciones deben permanecer dentro de página/recortes/cajas y no cruzar texto vecino, imágenes, campos, anotaciones, enlaces o bordes/trazados. Los controles de bordes curvos son conservadores. Un fallo de otra región impide publicar todo el lote. La vista previa de API no altera la versión original.

## Comprobación real

Fuente exacta `05f6a5c8efd4efa31d55e0a9f49157652682bb9d`, respaldada en `recovery/editing-20261029`. **4.734 pruebas Python (72 nuevas), 151 JavaScript, build y manual 75 herramientas +15 operaciones aprobados**. **167 pruebas dirigidas** aprobadas. **39 recorridos Qt en Linux y Windows Server 2025**, fuente limpia antes/después; comprobante `42075294339-1` contrastado con objetos Git y hashes. **Once aperturas independientes del ejecutable Windows** aprobadas; la nueva selecciona texto Stm, cambia a DejaVu Serif negrita a 13 pt, introduce Unicode y lectura accesible, deshace/rehace, exporta por su servidor real y reabre por su intérprete. No se atribuye a ese recorrido el diálogo nativo de guardar.

La prueba Qt desde fuente sí guarda mediante el diálogo nativo, reabre y reedita el tamaño desde el cuadro compacto. Las pruebas funcionales cubren las doce variantes, cuatro giros de página, Form anidados/compartidos de página, Stm único, nueve marcos afines en página/Form (giro, reflexión, inclinación y escala), espaciado, atributos, colisiones, nombres de recurso ya ocupados, vista previa/API y lote de dos páginas con fallo atómico. Otra comprobación integra formato y reflujo del Form cuando su recorte ofrece espacio y exige rechazo cuando no lo ofrece.

Al preparar los ensayos se corrigieron supuestos de las muestras: el Form con etiqueta de página no incluía ActualText y la segunda página de la muestra de lote necesitaba su ParentTree. El rechazo de esa estructura incompleta se conservó; no se relajó el motor. El verificador Qt esperaba objetivos de edición después de Deshacer, aunque el programa vuelve a lectura al cambiar de versión; se corrigió la navegación del verificador. Registros en [results.json](validation/native-format-20261105/results.json). No se publican PDFs/capturas personales: todas las muestras nuevas son sintéticas.

## Límites y siguiente trabajo

Esto no implementa formato universal: siguen pendientes tipografía declarada/clases que requieran actualizar atributos, formato conjunto de párrafos con varios estilos y redistribución general, composición/RTL/marcas combinantes, caracteres ausentes y variantes de fuentes/Forms protegidas. La sustitución requiere identificar primero el grupo original; no habilita fuentes que el analizador original no pueda verificar. Se mantienen los permisos y la protección de firmas. No certifica PDF/UA ni Windows cliente limpio, DPI, impresión física o estabilidad sostenida; las intermitencias históricas no se declaran resueltas por estas aprobaciones.

**Avance global: 87,43 % provisional**, antes 87,38 %. Mismos diecisiete pesos y alcance. Texto/imágenes 99→99,25 aporta 0,04 puntos y accesibilidad 98→98,5 aporta 0,015; incremento sin redondear 0,055, sin puntos por documentación o pruebas. Baseline [20261105-before-native-format.json](progress/20261105-before-native-format.json). Es una estimación de ingeniería, no una medición objetiva de paridad comercial ni de tiempo restante. Los ocho bloques generales siguen abiertos; `technical_complete` y `accepted_complete` permanecen falsos. La entrega técnica completa sigue pendiente.

No se publica otro portable; la preview anterior no contiene este trabajo. Siguiente recomendado: actualizar tipografía declarada/clases y permitir formato conjunto de párrafos con varios estilos, aprovechando el motor de línea incorporado aquí; no repetir la sustitución de líneas compatibles como ausente. Modelo recomendado: **6.1 Sol, razonamiento medio**.
