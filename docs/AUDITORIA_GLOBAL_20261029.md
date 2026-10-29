# Referencia global de la base recuperada

Estimación conservadora actual: **aproximadamente 48 % del programa completo**, intervalo subjetivo **40–60 %**. No es una medida objetiva de paridad con Acrobat ni una previsión de horas restantes.

Se evalúa el código 0.43 recuperado y las mejoras de edición/escritorio añadidas después de su recuperación. La cifra histórica de 61,3 % correspondía a 0.55 y sus archivos no están disponibles. Esta evaluación inaugura una referencia reconstruida; no permite calcular una subida o bajada comparable contra aquella versión. La matriz anterior tampoco se recuperó: las áreas y pesos publicados aquí son la nueva referencia, que deberá conservarse en siguientes revisiones o cambiarse con justificación explícita.

## Método y alcance

Cada área tiene peso dentro del producto completo y una madurez estimada: 0 sin implementación, 25 subconjunto pequeño, 50 cobertura parcial utilizable, 75 cobertura amplia con huecos, 90 casi completo pero sin aceptación final y 100 implementado/comprobado/aceptado. La ponderación suma 100. El resultado aritmético es 47,7 %, comunicado como aproximadamente 48 % para no aparentar precisión que el juicio de ingeniería no tiene.

La revisión combina el inventario FUNCIONES.md de la base recuperada, módulos backend/desktop, pruebas presentes, los recorridos dirigidos ejecutados y sus limitaciones. Las referencias y pendientes por área están en avance-global.json. Las pruebas sintéticas no equivalen a aceptación con documentos reales, Windows ni impresoras físicas.

| Área | Peso | Madurez estimada |
|---|---:|---:|
| Lectura y páginas | 7 | 85 |
| Interfaz y facilidad de uso | 7 | 65 |
| Edición de texto e imágenes | 16 | 50 |
| Anotaciones y comentarios | 7 | 70 |
| Formularios | 6 | 60 |
| OCR y conversión | 9 | 55 |
| Seguridad, censura y firmas | 7 | 50 |
| Estándares y optimización | 5 | 35 |
| Accesibilidad | 3 | 20 |
| Automatización y vinculación | 9 | 35 |
| Escritorio y distribución | 6 | 40 |
| Migración e interoperabilidad | 4 | 30 |
| Rendimiento y recuperación | 4 | 60 |
| Medición calibrada de planos | 3 | 0 |
| Portfolios y capas | 3 | 25 |
| Colaboración y servicios | 3 | 0 |
| Asistencia IA dentro del producto | 1 | 0 |

Excluida la generación de documentos de ensayos, registros e informes mediante plantillas personales. La vinculación general entre documentos sí se mantiene; sus identificadores, relaciones, duplicados y navegación persistente aún requieren implementación. Las recetas de procesamiento ya presentes aportan parte de la madurez de automatización. Buscar/reemplazar está pendiente y forma parte de edición. Dots y REA son herramientas auxiliares de desarrollo; instalarlas no aumenta la cobertura del programa.

## Qué falta para una entrega avanzada

El guardado y la ventana propios tienen comprobaciones locales, pero faltan asociaciones, segunda instancia, empaquetado y Windows real. La edición necesita ampliar estructuras/fuentes y buscar/reemplazar. Conversión/OCR requieren corpus y casos complejos. Vinculación, medición y servicios tienen huecos importantes. Se deben resolver las licencias de distribución de los motores antes de un lanzamiento comercial.

La próxima revisión debe indicar qué categoría cambia, su criterio nuevo, evidencia y efecto ponderado. No sumar puntos por cantidad de archivos/pruebas o por restaurar una copia. Alcanzar el porcentaje previsto de entrega no sustituye comprobar los recorridos cotidianos y el ejecutable en Windows.
