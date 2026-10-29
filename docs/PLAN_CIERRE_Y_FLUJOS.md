# Plan de cierre y flujos documentales configurables

## Alcance y orden vigentes

Solicitud del usuario: entregar primero el avance actual como ejecutable para pruebas; después continuar el editor y las automatizaciones propias con nombres y reglas generales. Esta solicitud permite generar ahora una entrega experimental, aunque antes se había reservado el ejecutable para un avance posterior. No se reanuda la generación de portables en cada incremento.

Los ejemplos «registro», «plano», «ensayo» y «Release Note» describen un uso. No serán los nombres obligatorios del motor ni botones especializados del espacio principal. El área propuesta es **Flujos documentales**. La primera herramienta será **Relacionar y ensamblar documentos**; un perfil de ejemplo podrá llamarse «Registro y plano» si el usuario así lo elige.

## 0. Entrega ejecutable del estado actual

- ZIP Windows x64 con `Reapdf.exe`, motor y dependencias incluidas, interfaz compilada, ejemplos y guía. No exige instalación previa de Reapdf, Python ni Node.
- Doble clic: logo de inicio y apertura de la ventana de aplicación. El motor local solo escucha en 127.0.0.1. La ventana de esta entrega utiliza Edge o Chrome ya instalado; todavía no incorpora un contenedor de escritorio independiente.
- El inicio sin ventana disponible falla con una explicación y un registro, sin dejar el motor oculto funcionando como alternativa. La ruta de navegador sigue disponible expresamente mediante el archivo auxiliar.
- Validar integridad, arquitectura, recursos, arranque del motor y exportación. La ejecución gráfica Windows requiere una prueba en Windows real; la compilación cruzada no la demuestra.
- Primera prueba del usuario: abrir un PDF de copia, zoom, texto, anotaciones, exportación/reapertura y proyecto/recuperación. Resolver los problemas observados antes de ampliar funciones.

Cierre: paquete identificado por versión y SHA-256, prueba real documentada y errores bloqueantes resueltos. El paquete experimental puede entregarse antes de completar este cierre para realizar precisamente esa prueba.

## 1. Base común e interfaz de configuración

El asistente tendrá pasos separados: **Entradas → Reglas → Revisar → Generar → Resultados**. No se añadirán todas las opciones al visor.

| Configuración | Qué podrá elegir el usuario |
|---|---|
| Tipos de documentos | Crear y nombrar grupos; inicialmente «Documentos principales» y «Documentos relacionados». Elegir archivos y, cuando el sistema lo permita, carpetas. |
| Identificador de relación | Nombre de archivo, texto del PDF, región seleccionada, OCR o asignación manual. Mostrar cómo se obtuvo y permitir corregirlo. Las reglas avanzadas estarán separadas de la configuración habitual. |
| Forma de relacionar | Una coincidencia o varias, normalización de códigos, prioridades explícitas y documentos opcionales/obligatorios. |
| Orden del conjunto | Definir el orden de los grupos y de los documentos, conservando todas sus páginas. |
| Salida | Nombre, destino disponible, separación por conjunto, inventario y tratamiento de duplicados. |
| Perfil reutilizable | Guardar nombres y reglas por proyecto, importar/exportar configuración versionada y validar antes de ejecutar. |

Cierre: perfiles creados desde la interfaz, validación de entradas, navegación por teclado y borradores conservados. No basta con diseñar la pantalla: las reglas deben conectarse al motor y demostrarse en resultados.

## 2. Analizar e identificar documentos

- Inventariar archivos, páginas, huellas, tipo asignado y códigos encontrados, conservando originales.
- Distinguir documentos multipágina de varias unidades dentro de un PDF. Mostrar propuestas de límites antes de separar.
- Extraer texto directo primero; proponer OCR cuando sea necesario y mostrar su incertidumbre.
- Marcar documentos sin código, dañados, cifrados o con firmas y explicar las operaciones compatibles.

Cierre: corpus con códigos repetidos, ausentes, varias páginas, escaneados y caracteres especiales; cada propuesta conserva referencia al archivo y página de origen. No se confunde el primer código encontrado con una identificación confirmada.

## 3. Relacionar y ensamblar

- Tabla de revisión: documento principal, clave, candidatos relacionados, orden, estado y problema.
- Coincidencias exactas propuestas; faltantes y ambigüedades bloquean los conjuntos afectados hasta resolverlos o excluirlos expresamente.
- Selección manual de candidatos, incorporación de varios y previsualización del conjunto completo.
- Generar principal completo seguido de relacionados completos según la configuración. Nunca elegir el primero alfabético como regla oculta.
- Invalidar la revisión si cambian archivos o reglas; no sobrescribir originales ni salidas existentes sin una decisión explícita.

Cierre: ninguna asociación ambigua se ejecuta automáticamente; recuento, orden, texto y aspecto de páginas contrastados, con origen de cada página y huella de cada salida. Este es el primer flujo personal que debe llegar a uso real.

## 4. Clasificar, separar y armar expedientes

| Herramienta general | Aplicación personal de ejemplo |
|---|---|
| Clasificar y separar documentos | Pintura, ensayos MT/UT, actas y registros multipágina. |
| Organizar expedientes | Agrupar por Release Note, sector, contrato o cualquier clave elegida. |
| Verificar requisitos | Detectar documentos obligatorios, opcionales y faltantes según un perfil. |
| Inventariar y conciliar | Excel con incluidos, excluidos, faltantes, ambigüedades y resultados realmente generados. |

Permitir relaciones de un documento con varios expedientes sin perder trazabilidad. Las excepciones particulares se guardan en el perfil del proyecto, no como reglas globales.

Cierre: expedientes reproducibles e inventario conciliado con las salidas. Si los nombres originales no existen, indicar que se reconstruyeron desde los códigos.

## 5. Cambios repetitivos y plantillas

- **Editar por plantilla**: seleccionar campo/región, transformación, alcance y vista antes/después. Distinguir texto digital, campos y escaneados.
- **Aplicar observaciones**: anclas, orientación, tamaño de letra y zonas protegidas; revisión de páginas afectadas.
- Ejemplo: extraer el sufijo posterior a un patrón configurable, como `-DWG-`, conservando fondo y elementos cercanos.
- Exportar archivos individuales y resultados por lote con inventario; sin cambios sobre originales.

Cierre: comprobaciones de contenido y comparación visual fuera de las regiones admitidas; fuentes o fondos no compatibles rechazan el cambio o exigen una alternativa explícita.

## 6. Ejecuciones seguras y comprobables

Se desarrolla junto con los bloques 2–5: manifiestos con entradas/salidas y huellas, registro de decisiones, cancelación sin archivos parciales presentados como terminados, reanudación validada y prevención de duplicados accidentales. Exportar perfiles sin documentos, credenciales ni rutas privadas innecesarias. El motor no ejecuta código arbitrario de los perfiles.

Cierre: interrumpir, reiniciar y repetir un lote no corrompe originales ni publica resultados incompletos; la revisión sigue vigente solo para las entradas verificadas.

## 7. Cierre del editor general

Trabajos distintos que siguen abiertos: grupos persistentes y geometrías de anotaciones; fuentes/estructuras complejas; fórmulas de formulario interoperables; conversión Office pendiente; censura compleja; firmas con revocación/TSA; accesibilidad y PDF/X; compresión de estructuras aún no admitidas. La matriz técnica sigue en [release-criteria.json](release-criteria.json). Una mejora de Word ya cerrada no vuelve a contarse como trabajo nuevo.

Se ordenan por problemas observados en la prueba personal y criticidad. Cada bloque declara lo que admite, lo que rechaza y su evidencia, sin prometer compatibilidad universal.

## 8. Programa distribuible

Después de estabilizar el uso personal: decidir el contenedor de escritorio independiente, incluir las dependencias externas necesarias o declarar funciones no disponibles, probar Windows sin herramientas de desarrollo, impresión, permisos, rutas largas, recuperación y documentos reales. Preparar instalador opcional, actualización y firma del ejecutable según la distribución elegida. Un `.exe` portable y un instalador `.exe` son entregas diferentes.

## Qué significa terminar

El cierre del producto requiere: editor personal aceptado con documentos reales, flujos personales configurables aceptados, integridad y recuperación verificadas y ejecución Windows comprobada. Una versión experimental, un bloque 8/8 o un alto número de pruebas no equivalen a ese cierre. Se mantendrá el avance por entregables y pendientes comprobables, sin convertir listas de tamaños distintos en un porcentaje global artificial.
