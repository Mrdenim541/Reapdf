# Formularios avanzados — versión 0.19

**Actualización 0.23:** se incorpora la importación/duplicación/reemplazo de árboles compatibles con verificación. Las restricciones de copia de 0.19 descritas abajo son históricas. Guía vigente: [IMPORTAR_FORMULARIOS.md](IMPORTAR_FORMULARIOS.md).

Reapdf puede rellenar campos AcroForm jerárquicos compatibles, sincronizar texto y casillas con varias posiciones y manejar grupos estándar de radio con una sola selección. No agrupa campos independientes solo porque tengan el mismo nombre.

## Prueba rápida

El portable incluye `ejemplos/reapdf-formulario-avanzado.pdf`, un ejemplo público de dos páginas:

1. Abre **Rellenar formulario** y completa `Datos.Nombre` en la primera posición.
2. Selecciona la segunda posición del nombre: debe mostrar el mismo valor.
3. Elige cualquier posición de `Datos.Decision` y marca **Rechazar**. El diálogo selecciona la posición de la página 2 para que puedas revisar su apariencia.
4. Genera la vista previa, aplica, exporta el PDF y vuelve a abrirlo. El nombre debe aparecer en las dos páginas y solo Rechazar debe estar activado.
5. Prueba Deshacer/Rehacer, guardar proyecto, datos JSON y aplanado. Aplanar conserva la apariencia, pero la copia deja de tener campos editables.

En **Crear o eliminar campos**, el tipo **Grupo de radio** permite crear de 2 a 10 opciones. La caja necesita al menos 24 puntos de alto por opción y espacio para sus etiquetas. Las etiquetas son texto impreso; permanecen si después eliminas el campo. La eliminación retira el campo lógico entero, incluidas todas sus posiciones en otras páginas; puedes deshacer.

## Estructuras admitidas

- Hasta 500 posiciones de campo por documento; árbol de hasta 16 niveles y 2000 nodos, con pertenencia y referencias Parent/Kids coherentes.
- Texto, casillas y listas simples como antes. Se admiten campos jerárquicos simples y texto/casillas compartidos mediante un propietario lógico común. Las listas con varios Widgets siguen protegidas.
- Radios con un campo lógico padre y apariencias Off/On válidas. Cada opción debe tener un estado de activación distinto, con nombre PDF simple ASCII de hasta 64 caracteres. Se conservan las apariencias existentes; seleccionar una opción no redibuja las demás.
- El valor se escribe en el campo lógico y todas sus apariencias se sincronizan. Los Widgets hijos no reciben valores locales que oculten el valor heredado. Se preservan nombres parciales, jerarquía, flags y opciones originales.
- Los campos comparten las restricciones de fuente y caracteres del editor inicial: fuentes base compatibles, texto latino y revisión de espacio en cada posición. No añade soporte universal para fuentes incrustadas ni todos los alfabetos.

La validación protege todo un grupo si un miembro tiene acciones, solo lectura, geometría incompatible, valores contradictorios o apariencias no compatibles. Bloquea nombres independientes ambiguos, referencias repetidas, ciclos, opciones de radio repetidas, estados visuales que no coincidan con el valor y estructuras fuera de límites. También protege XFA, cálculos, firmas y acciones especiales. No ejecuta scripts ni cálculos.

Los grupos que declaran que no se puede desactivar la selección respetan esa restricción. La interfaz permite volver a un estado inicial vacío sin inventar una selección; las solicitudes que intentan retirar una selección existente prohibida se rechazan.

## Datos, historial y páginas

Los proyectos y la recuperación conservan los valores aplicados, con las mismas limitaciones generales del guardado. Los borradores del diálogo no se guardan hasta aplicar. El JSON sigue vinculado a la huella del PDF base y a sus identificadores originales.

Una importación puede incluir una sola posición de un campo compartido y actualizará todo el grupo. Si incluye varias posiciones del mismo grupo con valores contradictorios, se rechaza completa. Exportar datos devuelve valores coherentes para todas las posiciones. No se añade compatibilidad FDF/XFDF.

Reordenar o extraer páginas conserva la jerarquía restante. Si se elimina la página que contiene la opción de radio seleccionada y esa opción desaparece del grupo, la copia limpia la selección y su valor por defecto si corresponde. Las opciones que permanecen siguen siendo rellenables. Insertar un PDF plano en un documento con estos grupos conserva los campos originales.

**Antecedente 0.19, superado para los casos compatibles en 0.23:** la importación o duplicación de campos jerárquicos/compartidos estaba bloqueada. El motor de copia promueve nodos y puede perder la relación entre padre e hijos. No se entrega una copia con un árbol roto. Se puede organizar el original o aplanar expresamente una copia antes de combinar, si se acepta perder su editabilidad. La reconstrucción de ese árbol importado necesita una fase propia.

El aplanado comprueba compatibilidad y apariencias de todos los campos antes de proceder. No aplana parcialmente un formulario con grupos no compatibles. No valida criptográficamente firmas ni conserva una firma digital al editar: los documentos con indicadores de firma permanecen protegidos.

## Verificación del avance

- **921 pruebas Python y 63 JavaScript: 984 en total**, más compilación de producción y recorrido completo de Chromium en Linux.
- 53 pruebas específicas nuevas cubren jerarquías, texto/casillas compartidos, radios, exclusividad, vaciado, restricciones, cifrado, importación JSON parcial, proyectos, aplanado, reorganización/extracción, diseño y eliminación de grupos, rechazo de copias no verificadas y preservación al insertar un PDF plano.
- Poppler `pdftotext` comprueba el texto compartido en salidas con giros/recortes. `pdftoppm` confirma el dibujo del radio seleccionado en la segunda página y su apariencia al aplanar.
- Chromium verifica edición sincronizada, cambio automático a la página de la opción, vista previa obligatoria, exportaciones reales, deshacer/rehacer, proyecto, JSON, aplanado, creación y eliminación reversible.
- La autoprueba portable crea un grupo, selecciona una opción y compara la apariencia antes/después de aplanar. El lanzador se prueba con Python Linux; el ZIP Windows se verifica estáticamente. **La ejecución real en Windows continúa pendiente.**

## Próximos trabajos

Conservar fuentes y estilos originales al editar texto; reconstruir de forma comprobable los árboles de formularios importados; ampliar tipografías y selección múltiple sin ejecutar scripts; validar el portable Windows y más documentos reales. Las firmas digitales, XFA, cálculos y servicios de firma remota permanecen fuera de este avance.
