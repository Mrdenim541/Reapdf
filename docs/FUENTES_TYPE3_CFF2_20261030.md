# Edición con fuentes Type3 y CFF2 estáticas

Este avance incorpora dos subconjuntos de fuentes a la edición directa con ratón y al reemplazo literal. No convierte todas las fuentes en editables ni acredita paridad con Acrobat/Nitro.

## Implementación

- **Type3 vectoriales sin color:** codificación explícita Differences + ToUnicode de un byte; matriz de glifo estándar de 0,001; anchuras contrastadas con `d1`; contornos rellenos dentro de las cajas declaradas. No se adivina Unicode a partir del nombre del glifo. Se rechazan mapas ambiguos.
- **CFF2 OpenType estáticas:** un programa CFF2, 1000 unidades por em, sin `fvar` ni `VarStore`. Se reutiliza el mapa PDF original y se comprueban contornos con presupuesto/profundidad acotados. Se admiten las rutas simples WinAnsi y compuestas Identity-H verificables.
- Ambas conservan programas, recursos, colores, espaciados y matrices originales. La edición reemplaza operandos de texto; las apariciones de Forms compartidos se aíslan antes de modificar una sola. El resultado se relee antes de publicarse.
- Funcionan desde el editor sobre la página, con deshacer/rehacer/exportación, y desde buscar/reemplazar literal. Se comprueban giros de página, inclinación/reflexión, caracteres Unicode explícitos, eliminación y lotes atómicos.
- **Compatibilidad de documentos importados:** el analizador conserva fuente/tamaño entre `BT` y `ET` y los restaura mediante `q/Q`. Para sustituir párrafos con varios cambios de fuente/posición dentro del mismo objeto, comprueba todas las orientaciones efectivas; no concede por ello edición nativa a estados todavía no soportados. Se corrigen dos bloqueos de párrafos importados desde Word detectados durante la regresión.
- Las fuentes TrueType/CFF variables se detectan explícitamente. Se exige una instancia estática verificada en lugar de interpretar silenciosamente el programa como una fuente fija. El diagnóstico se muestra cuando es la única incompatibilidad de fuente.

## Límites

Type3: máximo 256 procedimientos, 64 KiB por procedimiento, 2 MiB de programas analizados y 2000 operaciones por glifo. Solo `d1` y vectores rellenos simples; sin recursos internos, color, trazos, imágenes, texto anidado, transformaciones del glifo ni estados externos. Las métricas deben coincidir con la representación extraída; de lo contrario se protege el fragmento. La apariencia se conserva en el PDF; el campo de escritura usa la fuente de interfaz.

CFF2: no se admiten fuentes variables, ejes/instancias, VarStore, formato CFF2 crudo, programas de múltiples fuentes ni unidades distintas de 1000. No se modifica ni instancia el programa. La extracción/representación y la relectura usan MuPDF; no equivalen a una validación independiente en Acrobat/Nitro o a aprobación del estándar de cada archivo externo.

No se amplía el reflujo de texto afín, la sustitución de su fuente, la escritura vertical/RTL compleja ni los Forms con transparencia/semántica protegida. No hay prueba Windows, instalación nueva ni aceptación personal. No se incluyen documentos privados.

## Verificación

**Resultados finales:** 2841 pruebas Python generales aprobadas (3 avisos existentes), 303 dirigidas tras corregir los párrafos, 97 de fuentes nuevas, 131 de integración literal y 10 de herencia/Word; los subconjuntos se solapan y no se suman. Chromium y Qt Linux aprobados con el backend final. No hubo cambios de frontend; se usó su compilación existente. La primera regresión detectó dos fallos de Word, corregidos antes de repetir y aprobar la suite completa. Resultados y hashes en `validation/fonts-20261030/`. Las pruebas usan documentos sintéticos públicos generados en memoria. El recorrido Chromium selecciona y edita Type3 directo, Type3 compartido y CFF2 compartido; prueba deshacer/rehacer y exportación. El recorrido Qt Linux abre un PDF Type3 compartido, edita sobre la página y guarda mediante escritura nativa atómica, conservando archivo original, otros usos, programas y otra página.

Comandos reproducibles, con backend actualizado en 127.0.0.1:8000:

```bash
.venv/bin/python -m pytest tests/test_type3_fonts.py tests/test_static_cff2.py -q
node scripts/smoke_font_compatibility.mjs
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu' .venv/bin/python -m scripts.smoke_fonts_native
```

## Avance global y siguiente bloque

**≈76 % del programa completo: 76,24 ponderado**, antes 76,08. Se mantienen las 17 áreas, sus pesos y el alcance. Solo edición de texto/imágenes pasa de 95 a 96 (+0,16 puntos globales); las áreas Windows, servicios, estándares y aceptación no aumentan por estas pruebas. El porcentaje es una estimación de madurez, no un conteo de pruebas ni una medición objetiva de paridad comercial.

Continuar con estados intermedios y transparencia de Forms verificables, migración del recorrido gráfico histórico y compatibilidad de instancias variables. Después, ampliar las áreas comerciales pendientes según la matriz. Windows y corpus externo requieren su verificación real antes de considerarlos completos. Modelo recomendado: **6.1 Sol, razonamiento medio**.
