# División con nombres personalizados, marcadores y listas semánticas

Fecha local del usuario: 29 de octubre de 2026. La división ya existía por bloques y grupos con nombres fijos `parte-001.pdf`; este bloque añade los nombres personalizados solicitados y amplía la revisión, las secciones y la conservación de etiquetas. No se entrega otro portable.

## Cómo usar la división

En **Organizar páginas → Dividir PDF**, elige:

- **Bloques de tamaño fijo:** por ejemplo, un PDF por página o cada dos páginas.
- **Grupos personalizados:** un archivo por línea, por ejemplo `1-2`, `3,5`, `4,6`. El orden de páginas escrito se conserva.
- **Secciones por marcadores:** elige el nivel y prepara las partes; cada marcador inicia una sección hasta el siguiente. Las páginas anteriores al primero se incluyen como Inicio.

Después escribe el **nombre de cada parte**, o genera nombres numerados con un prefijo. Revisa las páginas indicadas junto a cada nombre. «Descargar partes ZIP» guarda todos los PDFs independientes juntos; descomprime el ZIP para abrirlos por separado. Opcionalmente incluye una relación JSON de archivos, páginas de origen y hashes. Esta relación describe la entrega, no genera informes personales ni contenido nuevo del documento.

Ejemplo: páginas 1–2 → `Portada.pdf`; páginas 3 y 5 → `Documento A.pdf`; páginas 4 y 6 → `Plano de ubicación.pdf`. El PDF combinado abierto y su historial se conservan.

## Trabajos completados

1. **Nombres personalizados:** extensión PDF automática, Unicode NFC, límites de longitud y nombres compatibles con las reglas de Windows. Se rechazan rutas, controles, nombres reservados y colisiones, también por mayúsculas o Unicode equivalente. No se cambia silenciosamente el nombre manual para eludir errores.
2. **Revisión de partición completa:** páginas y nombre por archivo, selección por bloques/rangos, numeración por prefijo, validación inmediata y endpoint de preparación sin generar documentos. Cada página aparece exactamente una vez; no hay pérdidas, duplicados ni sobrescrituras de partes. Las extracciones parciales continúan en su herramienta independiente.
3. **Marcadores como secciones:** nivel 1–10, destinos internos crecientes y páginas iniciales incluidas. Los títulos se convierten en nombres seguros numerados, editables antes de descargar. Destinos repetidos/desordenados o especiales requieren grupos manuales, sin inferir cortes ambiguos.
4. **PDFs y relación de entrega:** edición pendiente aplicada antes de dividir; conservación de páginas, giros, etiquetas de página, anotaciones, campos compatibles y enlaces internos dentro de cada parte. Los destinos hacia otras partes se retiran. ZIP completo o error, con límite total de 100 MB de PDF. Relación JSON opcional con páginas originales (base 1), tamaño y SHA-256 de cada salida y de la fuente editada.
5. **Listas semánticas iniciales:** el rol «Elemento de lista» agrupa objetos de texto consecutivos en L/LI/LBody/P. Orden y estructura son reales en el PDF, con MCID/ParentTree, manteniendo texto/apariencia. Los encabezados u otros objetos separan listas; no se infieren viñetas ni anidamientos. PDF y proyectos conservan el resultado.
6. **Partición de etiquetas:** se podan ramas de páginas excluidas y se reconstruyen ParentTree, StructParents y StructParent/OBJR de anotaciones retenidas. Se reconstruyen también después de la selección de páginas del intérprete. Se comprobó que una alternativa de imagen de otra parte no permanece en sus objetos serializados. Las estructuras no verificadas se rechazan, sin copiar un árbol residual ni declarar conformidad.
7. **Aplicación propia:** Chromium comprobó grupos no contiguos, nombres Unicode, colisiones, relación JSON, marcadores con nombres editados, listas revisadas y su división con estructura retenida. Qt Linux guardó los ZIP desde diálogo nativo y el PDF etiquetado con escritura atómica, comprobando que el original sigue intacto.

## Validación

**3255 pruebas Python generales aprobadas; 211 dirigidas finales, 126 JavaScript, compilación y recorridos Chromium/Qt Linux aprobados.** Resultados definitivos, registros y hashes en `validation/named-split-lists-20261029/`. La suite general precede a la protección final de ActualText en partición y las comprobaciones adicionales de MCR; la dirigida final cubre esa versión, páginas y proyectos. Sus subconjuntos se solapan y no se suman. Solo se usaron documentos sintéticos públicos; no se generó instalador ni portable. Windows, Acrobat/Nitro, lector de pantalla y aceptación personal permanecen sin ejecutar.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_named_split.py tests/test_list_tags_partition.py tests/test_page_tools.py tests/test_basic_tagging.py tests/test_media_tagging.py tests/test_pages.py tests/test_projects.py -q
node --test tests/*.mjs
npm run build
node scripts/smoke_named_split_lists.mjs
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu' .venv/bin/python -m scripts.smoke_named_split_lists_qt
```

## Límites

**División:** hasta 500 páginas/partes y 100 MB de PDF de salida. Nombres de hasta 120 caracteres/180 bytes, sin rutas ni caracteres reservados. Los archivos se entregan en ZIP; no hay escritura múltiple directa en una carpeta elegida. Los grupos deben cubrir todas las páginas una vez. Los marcadores elegidos necesitan destinos internos a páginas distintas y crecientes; hasta 2000 marcadores y diez niveles. Solo se emplean cortes de página, no separadores por contenido ni páginas en blanco.

**Conservación:** documentos firmados requieren copia de trabajo; no se conserva la validez criptográfica de una firma al extraer páginas. Capas, XFA, cálculos/scripts y estructuras no verificadas continúan protegidos. La partición etiquetada admite árboles indirectos acotados (2000 elementos/32 niveles), referencias de contenido simples/MCR sin stream y OBJR verificables. IDTree, ClassMap, Namespaces, atributos/referencias especiales y ActualText se rechazan. No se ofrece eliminar etiquetas como alternativa silenciosa. Se conservan los metadatos y recursos globales del documento.

Los MCR nativos compatibles se conservan con referencias de página/ParentTree verificadas mediante una segunda biblioteca. MuPDF no muestra la ruta de ciertos MCR ni en la fuente original; la división no afirma reparar esa limitación de vista de lectura ni ser un validador PDF/UA.

**Listas:** creación inicial revisada en documentos compatibles sin estructura, un objeto de texto por elemento y grupos consecutivos dentro de cada página. No hay listas anidadas, etiquetas de viñeta Lbl separadas, continuidad automática entre páginas ni tablas semánticas. El texto de viñetas/números permanece en el cuerpo original, sin reescribir contenido ni estilo visual. No certifica PDF/UA.

## Avance y continuación

**80,98 % estimado del programa completo (≈81 %)**, antes 80,54 %. Mismos alcance y diecisiete pesos: lectura/páginas 90→93 (+0,21), interfaz 96→97 (+0,07), accesibilidad 75→77 (+0,06) e interoperabilidad/migración 67,5→70 (+0,10). No se suman puntos por pruebas, documentación o herramientas. Estimación de madurez, no paridad certificada con Acrobat.

Siguiente bloque recomendado: tablas semánticas revisadas, contenido dentro de Forms y fuentes variables, con auditoría previa de variantes. Ampliar la partición de árboles complejos cuando exista prueba de conservación; no repetir como pendientes nombres personalizados, secciones por marcadores o listas simples ya incorporadas. Windows y aceptación personal siguen siendo puertas de entrega antes de preparar un candidato cercano al 90 %.

Modelo recomendado: **6.1 Sol, razonamiento medio**.
