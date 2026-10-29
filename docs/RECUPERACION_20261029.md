# Recuperación y edición directa · 29 de octubre de 2026

Se recuperaron 435 archivos del ZIP 0.43 previamente respaldado en la rama entrega-0.43. Su hash coincide con el publicado. La versión 0.55 no se encontró en las referencias Git disponibles ni en los archivos revisados del entorno; no se afirma que esté recuperada ni que se haya perdido definitivamente.

Se habilitó selección directa de fragmentos que la herramienta compacta no podía seleccionar: se abre el editor de bloques con el área calculada y la fuente original. La interfaz carga el texto sin tener que introducir coordenadas manualmente. El motor mantiene sus restricciones; CFF/Type3 y estructuras no compatibles no pasan a ser editables por este cambio.

Se regeneró el lock npm desde los manifiestos publicados para corregir una dependencia inexistente. Reinstalación limpia con npm ci y compilación aprobadas.

## Comprobación de esta base

- 2071 pruebas Python aprobadas; dos avisos conocidos (deprecación del cliente y ZIP duplicado intencionado).
- 105 pruebas JavaScript aprobadas.
- Recorrido Chromium nuevo: seleccionar TrueType, carga automática con fuente original, corregir, vista previa, aplicar, deshacer, rehacer y exportar. El PDF exportado contiene el texto nuevo, conserva el contenido vecino y la fuente TrueType. Recorrido repetido después de reinstalar dependencias.
- No suite gráfica completa ni ejecución Windows. La ventana nativa sigue pendiente; no se generó un portable.

Fuentes y recursos respaldados en la rama remota `recovery/editing-20261029`. Commit inicial: 000cb5d. Evidencias de comandos y hashes en validation/recovery-20261029/. No se ha comprobado restauración en otra máquina.

Alcance posterior: completar interacción cotidiana y alojamiento de escritorio propio, después buscar/reemplazar, compatibilidad y vinculación configurable de documentos. Excluir generación de informes/registros/documentos de ensayos. Próximo modelo recomendado: 6.1 Sol, razonamiento medio.

Porcentaje global actual pendiente de reevaluación: el 61,3 % del historial corresponde a una versión posterior no disponible. No se atribuyen puntos de avance por restaurar archivos o acumular pruebas.
