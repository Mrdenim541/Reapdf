# Estado comprobado · recuperación del 29 de octubre de 2026

La base recuperada es 0.43.0, extraída de la entrega GitHub b75864ebcd9fc2fad952effb2197829ad4f4dad4. El ZIP original tiene SHA256 c7b37849bd2491ef2e0eacc13a31d60e868ef33f73c6e175b8ff8e8d28bd59c9. Se recuperaron 435 archivos de fuentes, pruebas y recursos. No se recuperó el código 0.44–0.55; sus mejoras constan en la conversación, pero no se deben presentar como presentes en esta base.

Nuevo cambio sobre la recuperación: pulsar un fragmento no editable por la herramienta compacta, en página sin giro, abre el editor de bloques con región precargada y modo fuente original. Las limitaciones del motor siguen aplicándose; no amplía por sí solo las fuentes soportadas. Muestra TrueType comprobada desde selección hasta exportación, con deshacer/rehacer y contenido vecino conservado. Prueba reproducible: `node scripts/smoke-recovered-editing.mjs`, con backend en puerto 8000 y Chromium instalado.

Se regeneró package-lock.json mediante npm a partir de las versiones declaradas: el lock recuperado pedía scheduler 0.30.0, cuyo tarball devolvía 404; el manifiesto publicado de react-dom 19.1.0 requiere ^0.26.0. No se omitieron comprobaciones de integridad. El lock original continúa dentro del ZIP de entrega.

Preferencias vigentes: excluir generación de informes, registros y documentos de ensayos. Mantener vinculación general configurable entre documentos. Buscar y reemplazar similar a Excel sigue como función futura. Priorizar edición práctica y escritorio propio. No generar instalable ni portable hasta aproximadamente 90 % del alcance y con recorridos básicos comprobados. Dots queda pospuesto. Recomendar modelo al finalizar cada avance; continuar normalmente con 6.1 Sol, razonamiento medio.

Porcentaje: 61,3 % corresponde al historial de 0.55; no es una evaluación verificable de esta recuperación. Reestablecer cobertura global cuando se contraste el inventario recuperado y se localicen o reconstruyan las diferencias; no aumentar porcentaje por recuperación ni número de pruebas.

Siguiente bloque: mejorar interacción de edición y casos de texto incompatibles; definir y desarrollar alojamiento de escritorio propio. La entrega recuperada utiliza navegador en modo ventana y no acredita una ventana nativa ni ejecución Windows. Conservar el origen recuperado en Git y una rama remota verificable para evitar depender del disco de una sesión.
