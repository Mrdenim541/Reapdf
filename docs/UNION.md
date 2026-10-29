# Unión e inserción: alcance inicial

El editor añade un PDF completo al final o una selección de páginas en una posición elegida. Se procesa un archivo de origen por operación, repetible. La selección usa números desde 1 en la interfaz (`1-3, 5`), conserva el orden escrito y rechaza páginas repetidas, rangos descendentes y resultados mayores de 500 páginas.

El servidor crea una copia nueva después de aplicar las ediciones del documento abierto. El historial conserva el documento anterior y sus operaciones, por lo que se puede deshacer/rehacer. El PDF de origen cargado en el diálogo es temporal y se elimina al cambiarlo o cerrar el diálogo; los objetos necesarios ya están copiados en el resultado. Los archivos personales de entrada nunca se sobrescriben.

## Conservación comprobada

- Contenido y renderizado de páginas con tamaños y rotaciones diferentes.
- Anotaciones, notas y ediciones del documento abierto.
- Enlaces internos directos del documento base, remapeados tras desplazar páginas.
- Enlaces internos importados, incluyendo origen/destino rotados. Se reconstruyen usando coordenadas sin rotación para evitar una doble transformación detectada en `insert_pdf`.
- Enlaces URI y estilos directos de color, borde y resaltado admitidos.
- Marcadores locales y URI: los del origen se agrupan bajo su nombre de archivo. Los destinos a páginas excluidas desaparecen al seleccionar el subconjunto.
- Etiquetas de página visibles, preservadas como prefijos explícitos.
- Campos AcroForm básicos con valores independientes cuando sus nombres coinciden. El motor renombra los duplicados; no se unen sus valores. Se verifica modificación, guardado y reapertura.

La selección nativa de páginas retiraba AcroForm del catálogo aunque dejaba los widgets visibles. La capa de selección restaura la raíz y poda los campos correspondientes a páginas eliminadas, incluyendo jerarquías de campos. Esta corrección también se aplica a organización y extracción.

## Límites

La importación rechaza documentos con indicadores de firma, permisos de copia insuficientes, formularios XFA, capas, formularios con scripts u orden de cálculo, enlaces especiales y estilos de enlace con referencias no trasladables. Estos casos requieren otro incremento, sin modificar el documento abierto cuando se rechazan.

La copia de páginas no importa adjuntos, metadatos completos del origen, estructuras de accesibilidad, configuraciones de documento o portfolios. No se promete conservación universal de formularios complejos, acciones especiales ni documentos etiquetados. La validación actual usa corpus sintéticos y el mismo motor; lectores externos y Windows siguen pendientes.

La cuota de 300 MB incluye documentos, fuentes temporales y versiones. Una operación que excede la cuota se rechaza antes de guardar el resultado y conserva ambas fuentes. El historial no sobrevive a recarga/cierre.

## Reemplazo de bloques

La versión 0.8 reutiliza estas validaciones para reemplazar un bloque de páginas, con selección final antes de serializar. El total final, incluso al reemplazar en un PDF de 500 páginas, determina el límite. Los enlaces y marcadores a páginas originales retiradas desaparecen; no se redirigen automáticamente al contenido nuevo. El PDF base del reemplazo también se valida frente a capas, scripts/cálculos y acciones especiales. Véase PAGINAS_AVANZADAS.md.
