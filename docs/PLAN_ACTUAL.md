# Plan vigente

1. Recuperar y respaldar la base: fuentes 0.43 restauradas. Localizar 0.55 sigue pendiente. Verificación y referencia remota en RECUPERACION_20261029.md.
2. Uso cotidiano: selección directa de texto con fuente original añadida en esta recuperación. Continuar con corrección práctica de texto, cajas, dibujo, guardado y reapertura. Cubrir casos reales y explicar incompatibilidades en el lugar de la acción.
3. Buscar y reemplazar: primera implementación compatible de página/rango/documento, palabras completas y mayúsculas, selección, vista previa y lote reversible. Cruce de fragmentos contiguos de una misma línea, TrueType simple WinAnsi y lotes de hasta 100 fragmentos incorporados. Pendientes reflujo entre líneas, fuentes CFF/Type3, espaciados y estructuras complejas.
4. Compatibilidad: priorizar regiones marcadas/recortadas y fuentes simples con mapas propios encontradas en el documento real del usuario; las imágenes de esa página siguen en solo lectura. Ampliar fuentes y estructuras con criterios concretos, OCR y conversiones. No confundir pruebas sintéticas con aceptación personal.
5. Vinculación general de documentos: archivos/roles elegidos por el usuario, identificadores, resolución de duplicados, navegación y persistencia. Generación de informes/registros/ensayos excluida.
6. Escritorio Windows: Qt, apertura de ruta inicial, guardado directo atómico, detección de cambios externos, impresión raster con rango y cierre protegido comprobados en Linux offscreen. Reenvío local, señal de interfaz/puente listos y cadena del lanzador comprobados en Linux; asociaciones y arranque Windows preparados. Continuar con aceptación Windows, impresión vectorial/gran formato, escalado, rendimiento, recuperación, empaquetado y aceptación Windows antes de entrega.

Cada avance agrupa entregables independientes cuando sea viable, identifica bloqueos acotados y evita repetir como nuevas funciones ya cerradas. Informar desarrollo, comprobación automática, aceptación real, estado global y modelo recomendado. No generar portables intermedios.

Referencia global vigente reconstruida: aproximadamente 50 %, intervalo subjetivo 40–60 %, en avance-global.json. Se conserva su alcance/pesos en revisiones futuras o se justifica explícitamente cualquier cambio. El 61,3 % anterior pertenece a código 0.55 no recuperado.
