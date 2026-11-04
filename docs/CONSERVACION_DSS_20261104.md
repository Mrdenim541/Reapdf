# Conservación de evidencias DSS

No es una entrega final. El usuario pidió llegar directamente al programa técnicamente completo, con sus pruebas al final; esa solicitud todavía no está cumplida. No se entrega otro portable ni se recalcula un porcentaje por este cambio aislado. Siguen pendientes las implementaciones del plan vigente.

La herramienta Verificar firmas digitales permite conservar CRL/OCSP seleccionados en una copia incremental. Antes de incorporar datos exige que todas las firmas y TSA superen integridad, confianza y revocación local; rechaza firmas dañadas, evidencias caducadas/revocadas, cambios pendientes y documentos certificados/restringidos. Reabre y verifica la copia; conserva los bytes de revisiones anteriores. Incorpora certificados públicos y entradas DSS/VRI sin convertir esos certificados en confianza automática.

Para verificar usando evidencias ya incorporadas hay una opción explícita. Los datos se vuelven a validar a la fecha de comprobación. Límites: 20 CRL/OCSP, 4 MB; certificados DSS hasta 100, 64 KB por certificado y 4 MB totales. La descompresión se limita antes de leer los datos. No consulta Internet. No es validación histórica ni acredita PAdES-LT/LTA. Certificados y evidencia importados siguen sujetos a confianza y vigencia seleccionadas; un PDF no puede acreditarse a sí mismo.

El guardado utiliza el puente nativo existente; cancelar conserva la copia preparada. El recorrido DSS nuevo se verificó en Chromium y backend; los trece recorridos Qt existentes se comprobaron por separado en Linux y Windows Server 2025. El ejecutable interno Reapdf.exe también pasó arranque, edición, deshacer/rehacer, exportación y cierre. Comprobante 41746473806-1, fuente/objetos/logs/huella contrastados. No se registra el diálogo DSS nuevo como probado gráficamente en Windows.

Comprobaciones: 3778 Python, 96 dirigidas (incluidas en la regresión), 130 JavaScript, compilación, navegador real para guardar/reabrir/verificar DSS, pruebas de CRL/OCSP, ausencia de confianza automática y límites de expansión. Ensayo adicional con dos firmas y repetición de conservación: revisiones y deduplicación conservadas. Guía integrada y manual actualizados.

Fuente: d9007362e8d5485983ce70563ccdb1fd25b8d25b. Evidencia en [results.json](validation/dss-20261104/results.json). El porcentaje global anterior se conserva sin reevaluación; no se declara un cierre de bloque ni del producto. Siguen LT/LTA, validación histórica, edición avanzada y los otros pendientes de PLAN_ACTUAL.md.
