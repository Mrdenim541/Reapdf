# Importación de formularios compatibles — 0.23

Reapdf incorpora formularios AcroForm jerárquicos compatibles al **unir, insertar, duplicar o reemplazar páginas**. Los grupos dentro de cada copia conservan su propiedad lógica: un nombre compartido sigue sincronizado en sus páginas y un grupo de radio mantiene una sola selección. El original y la copia quedan independientes.

## Prueba de uso

1. Abre el ejemplo público generado por `scripts/create_advanced_form_sample.py`. Completa `Datos.Nombre` y el grupo de decisión desde **Formularios y firmas → Rellenar formulario**. Revisa y aplica.
2. En **Organizar páginas → Unir o insertar PDF**, selecciona otro formulario compatible y sus páginas. También puedes usar **Duplicar páginas** sobre el documento actual.
3. Si hay una colisión de nombres, el árbol importado recibe un sufijo en su raíz, por ejemplo `Datos (2).Nombre`. Sus posiciones siguen perteneciendo al mismo campo copiado, pero no al campo original `Datos.Nombre`.
4. Rellena el nombre de la copia y comprueba sus otras posiciones. Los valores del original deben conservarse. Los grupos de radio de cada árbol tienen selecciones independientes.
5. Exporta/reabre el PDF, guarda proyecto o prueba deshacer/rehacer. Los datos JSON y el aplanado siguen disponibles para los grupos compatibles del documento resultante.

La duplicación incorpora los cambios aplicados de la sesión. No copia borradores. Si se seleccionan solo algunas páginas y se excluye la opción de radio que estaba marcada, el grupo copiado queda sin selección. La opción original se conserva en el documento original.

## Qué se reconstruye y verifica

El copiador nativo puede crear clones adicionales de los padres, promover campos terminales a la lista raíz o dejar referencias antiguas en `Kids`. Reapdf identifica los nodos por su identidad en el PDF de origen, reconstruye `Parent`, `Kids` y `AcroForm/Fields`, y conserva un padre canónico por identidad. Nunca reúne grupos de documentos distintos únicamente porque coincidan sus nombres.

- Se validan ciclos, profundidad, propiedad de Widgets, nombres completos y límites antes de copiar.
- Las referencias de los campos importados deben ser nuevas y separadas del formulario base.
- Se conservan nombres Unicode y se resuelven colisiones de nombres completos, incluidos campos planos con nombres que contienen puntos.
- Se materializan los valores predeterminados heredados de apariencia y alineación cuando son compatibles.
- Se comparan valores, tipo, banderas, posición, opciones, propiedades de texto/color/borde y hashes de los flujos de apariencia copiados. Los diccionarios de campos originales no deben alterarse.
- Se asigna a cada Widget su página real antes de compactar, para evitar que se fusionen objetos de distintas páginas.
- Se reabre el PDF final y se verifica su árbol y los atributos de los campos importados después de la serialización.
- Al retirar páginas se conserva el árbol antes de reorganizar: el motor puede vaciar listas `Kids` de campos recién importados. Se reconstruyen únicamente las ramas que mantienen posiciones.
- Las escrituras de `Fields`/`CO` acceden al diccionario AcroForm correcto, tanto directo como indirecto. Esto evita una corrupción del setter anidado del motor y permite seguir creando/eliminando grupos en el resultado.

Si falla una comprobación, no se adopta una versión nueva ni se modifica la fuente original. Las versiones aceptadas siguen siendo reversibles en el historial.

## Alcance y límites

- La verificación de copia admite hasta 2000 caracteres por valor/etiqueta, 500 opciones/estados por campo y dos millones de caracteres de atributos por lote de páginas. Los flujos se comparan sin descomprimir imágenes o programas de fuente para calcular sus hashes.
- Se mantienen los límites generales de 500 páginas, 500 Widgets en el resultado, 16 niveles y 2000 nodos del árbol compatible. Un reemplazo puede superar temporalmente 500 Widgets en memoria si el resultado final respeta el límite.
- Se cubren texto, casillas, listas compatibles y radios estándar, incluidos árboles que mezclan campos individuales con grupos compartidos. Copiar un campo de solo lectura no lo convierte en editable.
- Los campos independientes dentro del origen con nombres completos ambiguos se rechazan.
- Continúan bloqueados los orígenes con indicadores de firma, campos de firma digital, capas, XFA, cálculos o acciones/scripts no admitidos. Los permisos del origen deben permitir copiar y los del destino deben permitir organizar/modificar páginas.
- La copia no añade soporte de relleno para fuentes, tipos, opciones avanzadas o estructuras que el editor no admitía. Esos campos pueden conservar sus restricciones; no se garantiza reconstruir apariencias ausentes.
- El nombre nuevo se asigna al incorporar el árbol. Puede mantenerse el sufijo aunque posteriormente se retiren las páginas del campo que causó la colisión.
- Las pruebas de apariencia y texto incluyen Poppler y el motor PDF local. No equivalen a una certificación de fidelidad universal, PDF/UA o ejecución gráfica en Windows.

## Evidencia

Pruebas positivas y negativas de inserción en distintas posiciones, subconjuntos en orden inverso, radio cuya opción desaparece, cuatro giros y recorte, varias generaciones de copia, ancestros adicionales, casillas compartidas, listas jerárquicas, nombres Unicode y colisiones, formularios directos/indirectos, campos de solo lectura, límites, permisos/cifrado, scripts/ciclos y corrupción simulada del copiador. Se verifican proyecto, JSON, aplanado, eliminación y apariencias/texto con Poppler.

Validación del corte: **1058 pruebas Python y 78 JavaScript**, compilación y recorrido completo de Chromium aprobados en Linux.

Chromium recorre importación, relleno independiente y sincronización dentro de cada copia, exportación con inspección del PDF, proyecto, recuperación tras recargar, duplicación con historial y reemplazo de páginas con formularios. No se genera un portable nuevo.

Siguiente prioridad: ampliar fuentes/codificaciones y reflujo de texto; después continuar con censura de estructuras complejas y corpus real. El ejecutable propio con logo y ventana de escritorio se entregará cuando el programa esté listo para la prueba personal.
