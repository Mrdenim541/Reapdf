# Edición práctica, revisiones y preparación de la prueba de escritorio

Avance global estimado **≈72 % (71,9 ponderado)**, frente a 69,8. Se mantienen el alcance, las diecisiete áreas y todos los pesos de [avance-global.json](avance-global.json). No es aceptación final ni porcentaje de equivalencia con Acrobat. El incremento corresponde a cinco áreas que ya tenían cobertura amplia; no se recalculan las doce áreas restantes ni se suman puntos por cada prueba. Referencia anterior: [progress/20261029-before-revisions-reflow.json](progress/20261029-before-revisions-reflow.json).

## Trabajos terminados en este bloque

| Trabajo | Resultado nuevo | Límites que permanecen |
|---|---|---|
| Espaciado original | Edición de una instrucción TJ con ajustes verificables entre caracteres, y parámetros Tc/Tw. Los ajustes entre parejas de caracteres que permanecen juntas se conservan; los fragmentos nuevos usan espaciado normal del recurso. Se comprueban posiciones y anchuras antes de escribir. | No escala horizontal distinta de 100, varios Tj por BT, solapamientos ni espacios inferidos por el extractor. Una cadena sin correspondencia exacta con los bytes permanece en solo lectura. |
| Insertar texto con un clic | Añadir texto abre la entrada sobre la página. Altura automática, ancho configurable, varias líneas, tamaño/color/familia/estilo y Unicode cubierto por las fuentes incluidas. Deshacer/rehacer y exportación. No requiere dibujar una caja ni rellenar propiedades a la derecha. El modo opcional Caja ajustable conserva cajas movibles y editables del proyecto; su edición y reapertura se comprueban por separado. | No escritura RTL, máximo 4000 caracteres. Rechaza salir de la página o tapar texto/campos/anotaciones. En página girada se coloca mediante un Form orientado; volver a editar ese texto como contenido original del Form aún está pendiente. |
| Párrafo sobre la página | Desde Editar texto → pulsar fragmento → Editar párrafo. Se modifica el bloque completo, comprueba el ajuste y redistribuye en varias líneas reutilizando el programa de fuente original, tamaño y color. El área se puede ampliar sin invadir otro texto. | Un solo tamaño/color/fuente; se normalizan espaciados al redistribuir. Requiere glifos existentes, área sin dibujos/enlaces y página sin marcas, recortes, capas, etiquetas ni Form. No reflujo original mixto/entre páginas. La edición de línea anterior sigue disponible para casos marcados compatibles. |
| Actualizar un conjunto vinculado | Seleccionar archivo y nueva revisión, clasificar apariciones conservadas/movidas/ambiguas/ausentes, revisar cada destino y confirmar. La retirada de un vínculo es explícita. Deshacer la última revisión, guardar/reabrir el conjunto y navegar al nuevo destino. | No seguir silenciosamente un código cambiado ni inferir vínculos geométricos. Deshacer la revisión se conserva en la sesión, no como historial ilimitado dentro del archivo exportado. |
| Comparación de documentos | Origen y destino aparecen lado a lado en pantallas amplias. El destino de una revisión se compara con la aparición anterior. | Validación personal y pantallas pequeñas todavía pendientes. |
| Robustez de escritorio | La ventana Qt recibe una señal de cierre por EOF cuando desaparece su padre, incluso si se mata el padre de forma forzada. Evita dejar una ventana hija viva después del backend. Las pruebas de instancia se aíslan del programa que pueda estar abierto. | La muerte forzada no guarda un borrador aún sin aplicar. La recuperación de cambios aplicados ya existente sigue siendo necesaria; no se declara tolerancia a pérdida de energía. |
| Preparación de aceptación | Un ejecutor reúne ocho pruebas reales Qt y escribe informe de plataforma, huellas y registros. Workflow de fuente para Windows y Linux, sin construir otro portable. | Preparar/subir el workflow no acredita una ejecución aprobada. Impresión física y aceptación humana no están automatizadas. |

El reflujo conserva el programa de fuente; no implica conservar idénticos saltos de línea o ajustes tipográficos, precisamente porque se redistribuye el texto. CFF/Type3 y las transformaciones complejas siguen pendientes. No se generan documentos de ensayos, registros ni informes personales.

## Verificación

**Resultado final: 2301 pruebas Python y 109 JavaScript aprobadas, compilación correcta, recorridos actuales Chromium y ocho comprobaciones reales Qt Linux aprobados.** El informe Qt identifica el commit de fuente y sus huellas; no había modificaciones locales al iniciarlo.

La carpeta [validation/revisions-reflow-20261029](validation/revisions-reflow-20261029) contiene los resultados finales, huellas de fuente y registros de los recorridos. Se ejecutan compilación, JavaScript, regresión Python y comprobaciones Qt/Chromium. Los totales definitivos figuran en `results.json`; no confundir la regresión previa de 2286 casos con la regresión final tras añadir el nuevo reflujo y sus pruebas.

Pruebas específicas: cuatro rotaciones para espaciado, inserción y reflujo; glifos ausentes, desbordamientos, texto vecino, dibujos, enlaces, etiquetas y recortes rechazados antes de publicar un resultado. API de revisión con confirmación obligatoria y API de párrafo con fallo de ajuste sin modificar el original. Chromium modifica párrafo/texto, exporta, revisa un vínculo movido a otra página, deshace la revisión, guarda y vuelve a abrir.

La prueba del PDF real del usuario se repite mediante la ventana **Qt de Reapdf**: fuente original, imagen de cabecera movida 2 pt, deshacer/rehacer, guardado/reapertura e integridad exterior. Original/copia/capturas se conservan fuera de Git en `/workspace/reapdf-pruebas-edicion-revision/`. No se aplicó reflujo al registro real porque contiene marcas/recortes; esta ampliación no los reescribe.

## Estado de la entrega para probar

**Todavía no se entrega un ejecutable de prueba.** Se mantiene la condición de una entrega candidata próxima al 90 % y verificada, en lugar de repetir portables intermedios. Ya existe alojamiento Qt propio y lanzador Windows; este avance no abre el programa en un navegador externo.

El ejecutor local es:

```text
python scripts/check_desktop_candidate.py --output desktop-validation
```

Requiere las dependencias del proyecto/PySide6 y el frontend compilado. Inicia y cierra su propio servidor; `--reuse-server` se reserva para un servidor de este repositorio ya abierto. Es una herramienta de desarrollo, no el modo de instalación que se pedirá al usuario final. `.github/workflows/desktop-source.yml` ejecuta este proceso en Windows/Linux y conserva informes como artefactos de CI, sin generar un paquete distribuible.

En este entorno, `gh run list` no puede consultar `api.github.com`: devuelve **Forbidden**. No se elude la restricción ni se interpreta un workflow preparado como resultado aprobado. El informe local acredita Linux; Windows permanece sin ratificar. La prueba personal final y la impresora física también permanecen pendientes. El recorrido histórico `scripts/smoke-ui.mjs` todavía usa selectores del antiguo editor lateral: no se declara aprobado como suite de interfaz vigente. Antes del paquete se debe migrar ese recorrido completo; los recorridos actuales de edición, vinculación y Qt se ejecutan por separado y constan en las evidencias.

Prueba de aceptación prevista: [PRUEBA_PERSONAL_ESCRITORIO.md](PRUEBA_PERSONAL_ESCRITORIO.md). Los criterios comerciales más amplios continúan en [release-criteria.json](release-criteria.json).

## Siguientes trabajos concretos

1. Fuentes CFF y texto dentro de Form; escalas horizontales y modelos con más de una instrucción de texto. Usar casos hoy rechazados, conservar fuente/vecinos y verificar exportación.
2. Reflujo original con estilos mixtos, selección de palabras/bloques más flexible y anclas manuales de vínculos. No volver a anunciar como nueva la revisión de códigos o el reflujo uniforme ya incorporados.
3. Obtener el resultado Windows, corregirlo donde falle y validar DPI, apertura/asociaciones, recuperación e impresión. Después ensamblar y ejecutar el paquete candidato completo antes de entregarlo al usuario.

Modelo recomendado para continuar: **6.1 Sol, razonamiento medio**.
