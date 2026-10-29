# Fuentes CFF, objetos compartidos y edición sobre la página

Estado: 29 de octubre de 2026. Avance global estimado **73,33 %**, aproximadamente 73 %, frente a 72,75. Mismos diecisiete pesos y alcance: el aumento se concentra en edición e interfaz, no supone terminar las demás áreas comerciales. [Matriz](avance-global.json), [plan](PLAN_ACTUAL.md).

## Entregables comprobados

- Edición con programa original CFF1: OpenType CFF de 1000 unidades/em, Type1C WinAnsi y CIDFontType0C Identity-H. Se comprueban mapas, contornos y anchuras; los bytes de la fuente se conservan. CID y GID pueden diferir. Límites de tokens y profundidad contienen programas malformados.
- Edición de una aparición seleccionada de un Form compartido, incluso anidado. Se copia su ruta de invocación y recursos privados, sin alterar otras apariciones ni páginas. Se comprueba también un lote con texto raíz y varias apariciones. Admitidas traslación y escala uniforme positiva; máximo ocho niveles, 200 nodos, 32 MB recorridos y 64 MB copiados por operación/documento.
- Reflujo de párrafos con varios estilos originales. El editor sobre la página mantiene fuentes, tamaños y colores por fragmento, comprueba el ajuste completo y vuelve a abrir el resultado para verificar extracción. Conserva el reflujo uniforme anterior.
- Selección ajustada al fragmento: permite texto pequeño y evita invadir estilos contiguos. El cursor se coloca cerca del clic con geometría ya cargada, sin otra petición al servidor; si es ambigua se conserva la selección completa anterior. Activación por teclado mantiene selección completa.

## Límites explícitos

CFF2, fuentes variables y Type3 siguen pendientes. No se amplía la compatibilidad por sustitución silenciosa. Forms con giro interno, inclinación, reflexión, escala no uniforme, transparencia, capas o estructura etiquetada quedan fuera de esta ruta. Las propiedades de marcado con alternativas requieren revisión conjunta y se bloquean conservadoramente, incluso si no se usan. La rotación de página sí se prueba en los cuatro ángulos.

Reflujo mixto: hasta 4000 caracteres en regiones compatibles, sin bordes, enlaces ni dibujos que interfieran; sin RTL, Forms, contenido etiquetado ni continuidad entre páginas. No se afirma identidad visual dentro de la región cambiada. La edición de documentos firmados no implica conservar la validez de una firma tras modificar su contenido.

## Verificación real

Regresión Python completa: **2443 aprobadas**. Después se añadieron ajustes de selección/cursor y límites defensivos; la comprobación dirigida final de los módulos afectados aprobó **238 pruebas**. No se afirma haber repetido toda la regresión sobre el último ajuste.

JavaScript: **112 aprobadas**; compilación de producción aprobada. Tres recorridos Chromium aprobados: nuevo CFF/Form/reflujo mixto con exportación y deshacer/rehacer; escala/grupos y vínculos manuales; inserción Unicode, reflujo uniforme y revisión de vínculos. Programas de fuentes conservados; otras apariciones y páginas permanecen intactas en las muestras previstas. Pruebas reproducibles en `tests/test_cff_forms_mixed.py`, `tests/test_inline_caret.mjs` y `scripts/smoke_cff_forms_mixed.mjs`.

El PDF privado del usuario sigue siendo compatible en la inspección de solo lectura con el motor actual. No se editó ese archivo en esta pasada ni se publicaron sus datos. Evidencias y huellas del código/compilación en [validation/cff-forms-mixed-20261029](validation/cff-forms-mixed-20261029).

Windows, impresión física y aceptación personal siguen pendientes y aplazados. Chromium no certifica Windows. No se generó portable, no se instaló REA ni se inspeccionaron programas comerciales.

## Continuación sin repetir entregables

1. Ampliar casos de edición aún rechazados: Forms con transformaciones y estados gráficos complejos; después CFF2/variables/Type3 con preservación verificable.
2. Reflujo mixto entre páginas y selección continua, con previsualización y límites claros.
3. Migrar el recorrido gráfico histórico y preparar la verificación Windows; no dar por aprobado ni entregar un candidato antes de ejecutarlo allí.
4. Cerrar el alcance comercial restante por área: portfolios PDF nativos, conversiones complejas, accesibilidad y firmas avanzadas, servicios y licencias.

Siguiente modelo recomendado: **6.1 Sol, razonamiento medio**. Reservar un modelo de mayor coste para un bloqueo técnico concreto, no para cada pasada.
