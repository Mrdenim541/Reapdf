# Recorridos extendidos de edición y escritorio

31 de octubre de 2026. Base: `e2ea707`. No se genera instalador ni portable.

Se trabaja sobre recorridos completos de edición, persistencia y reapertura, en varias áreas. El producto completo **no está terminado**. La madurez ponderada provisional pasa de 83,69 % a **84,25 %** con los mismos diecisiete pesos y alcance; no mide horas, tareas restantes ni paridad con Acrobat. No se añaden puntos por preparar herramientas ni por repetir pruebas.

## Trabajos incorporados

1. **Texto con posiciones relativas Td/TD.** El analizador conserva el objeto BT y la matriz de cada línea. Se verifican los caracteres, posiciones, códigos de fuente y trazas antes de habilitar la edición. El texto de un objeto con varias líneas puede editarse por grupos compatibles, en lugar de rechazarlo por completo. Operadores o estados no verificables continúan protegidos.
2. **Reflujo conjunto afín.** «Editar párrafo» desde una selección directa reconoce grupos paralelos continuos de un mismo objeto de texto. Redistribuye varios grupos con fuente original, conservando giro, escala y apariciones Form compatibles. Exige estilo, espaciado y composición compatibles; no reúne arbitrariamente objetos distintos por semejanza visual.
3. **Conservación de las líneas siguientes.** El reflujo restaura la matriz original antes de los operadores posteriores. Cambiar una línea no desplaza otra que use Td/TD relativo. Los grupos retirados se vacían de forma independiente, sin redacción ni rasterización de la página. Se comprueba contenido residual, posición y reedición.
4. **Ángulos.** Tres puntos —extremo, vértice, extremo— permiten calcular, guardar y editar ángulos de 0–180°, en grados o radianes, sin escala lineal. La geometría y etiqueta son anotaciones PDF, con identificador persistente y comprobación tras giro/recorte. Los brazos deben medir al menos 1 pt. No se asigna una escala de longitud falsa al ángulo.
5. **Intersecciones para medir.** El cursor se ajusta a cruces reales de segmentos finitos, además de extremos y esquinas. No se usan prolongaciones de líneas ni intersecciones inventadas de curvas. Barrido acotado a 2000 segmentos, 250000 comparaciones y el límite existente de 10000 puntos; si se alcanza un límite, la interfaz lo indica.
6. **Mediciones antiguas.** «Actualizar referencia» permite migrar registros v1 interpretables a v2. Exige una referencia nueva y conserva vértices nativos e identificador. Después de actualizar se pueden editar sus vértices con el recorrido normal. Geometrías antiguas ambiguas o fuera de la página siguen protegidas.
7. **Listas con etiquetas separadas.** Un objeto Lbl precede inmediatamente a su cuerpo LI. Se crea LI → [Lbl, LBody] con asociaciones MCID reales, conservando niveles de lista y apariencia. No se incrustan números o viñetas ficticios ni se reúnen etiquetas huérfanas por aproximación.
8. **Celdas semánticas vacías.** Se añaden explícitamente a una tabla revisada con fila y columna. TH/TD vacías tienen estructura y atributos, sin texto ni MCID inventados. Se validan huecos, duplicados, combinaciones y límites; sobreviven al proyecto y a la partición del árbol/ParentTree al conservar páginas.
9. **Configuraciones de capas.** Se pueden elegir configuraciones OCG existentes compatibles, revisar la vista previa y guardarlas como estado inicial. Se conservan bloqueos, exclusiones y las configuraciones originales. Reglas automáticas AS, estados Unchanged y estructuras no compatibles quedan protegidos; ocultar capas sigue sin ser censura.
10. **Columnas de portfolios externos.** Consulta y edición de campos declarados S/N/D compatibles sin sustituir el esquema. Texto, número y fecha se validan; vaciar un campo elimina solo ese valor. Se conservan prefijos, valores ajenos, adjuntos y portada. Se aíslan FileSpec/CI compartidos para no modificar otro archivo por accidente. Campos de solo lectura, complejos o desconocidos permanecen protegidos. El orden propio de Reapdf se cambia desde el organizador, no mediante un número arbitrario en columnas. No crea carpetas ni diseña esquemas nuevos.
11. **Recorridos de escritorio y documento real.** La batería automática incorpora los recorridos nuevos en ventana Qt, con guardado atómico y reapertura. Se realizó además una edición dirigida con fuente original en un PDF personal desde la ventana propia: copia guardada/reabierta, original intacto, imágenes, dibujos y programas de fuente conservados. El PDF, selección, copia y evidencias privadas quedan fuera de Git. Es una prueba dirigida y no aceptación de todo el documento o del producto.

## Comprobaciones y evidencia

Resultados y huellas finales: `validation/extended-workflows-20261031/results.json`. Las pruebas dirigidas se solapan con la regresión: sus cantidades no deben sumarse como casos independientes.

- Regresión Python completa de edición, geometría, etiquetas, capas y mediciones; los metadatos de portfolio se añadieron después y tienen comprobación dirigida final independiente.
- Pruebas de grados/radianes, giro/recorte, migración con identidad estable, cruces finitos, etiquetas/celdas, matrices posteriores, estilos, grupos compartidos y valores protegidos.
- Portfolios sintéticos con columnas externas, prefijos y metadatos/FileSpec compartidos; esquemas, adjuntos y píxeles comprobados antes y después.
- JavaScript, compilación y recorrido cotidiano Chromium; recorrido ampliado Chromium con corrección, guardado y reapertura mediante lectores independientes.
- Ventana Qt propia con los controles nuevos y guardado atómico; batería de escritorio con arranque, recuperación, impresión controlada, instancia única y vigilancia de procesos.

La prueba histórica que prohibía cualquier Td entre shows se ajustó a la capacidad nueva: exige grupos separados y sigue rechazando la escritura si las celdas se superponen. No se desactivó la protección de colisiones para aprobarla.

Qt Linux offscreen y una impresora PDF controlada **no acreditan** ejecución Windows, DPI, asociación de archivos, impresión física ni aceptación personal. La consulta de GitHub Actions para comprobar resultados de Windows devolvió `Forbidden`; no se presenta ningún resultado remoto como aprobado. La configuración del entorno se conserva sin publicar cambios.

## Cierre pendiente del programa completo

Se mantienen los ocho bloques; lo implementado arriba se retira de sus listas futuras.

| Bloque | Pendiente real |
| --- | --- |
| 1 · Edición | Fuentes/ejes y composición complejos restantes; reflujo mixto y entre objetos/páginas transformados; corpus más amplio. |
| 2 · Accesibilidad | Contenido mixto interno de Forms, imágenes inline/recortes, enlaces ambiguos, reparación general, PDF/UA y lector de pantalla. |
| 3 · Formularios e intercambio | XFA, JavaScript general, acciones/fórmulas y variantes XFDF restantes; aceptación externa. |
| 4 · OCR y Office | Tablas curvas/irregulares/multilínea, bajo contraste, notas partidas y fidelidad Office general. |
| 5 · Seguridad y estándares | TSA de red, revocación histórica/TSA, LT/LTA, sellos de archivo, censura y preflight complejos; estándares/corpus externos. |
| 6 · Planos y documentos | Curvas e intersecciones no lineales, referencias antiguas ambiguas, carpetas/esquemas de portfolio, OCG automáticos y contenido de capas, revisiones/lotes de vínculos restantes. |
| 7 · Entrega | Windows real, DPI/asociaciones/impresión/recuperación, paquete probado, carga sostenida y aceptación personal. |
| 8 · Servicios | Compartir/sincronización, revisión y firmas remotas, asistencia dentro del producto; proveedores, costes y alcance pendientes. |

La prioridad de cierre es comprobar la edición cotidiana y la aplicación de escritorio en un corpus representativo y en Windows, resolver los fallos encontrados y completar los pendientes de función de esta tabla. No convertir cada subconjunto compatible en un nuevo cierre comercial. No afirmar 100 % ni generar candidato solo porque una cifra estimada se acerque a 90 %.

Se conserva la exclusión de generación de informes, registros y ensayos personales; vinculación por archivos y roles generales. Base 0.43 recuperada con mejoras actuales; 0.55 sigue sin recuperarse. Modelo recomendado: **6.1 Sol, razonamiento medio**.
