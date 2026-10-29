# Entrega ejecutable de prueba — 0.43

El usuario solicita probar el avance actual antes de ampliar las automatizaciones personales. Se prepara un portable con lanzador **Reapdf.exe**; no es necesario instalar previamente Reapdf. No se genera un instalador en esta entrega.

## Qué contiene

- Lanzador GUI Windows x64 con icono propio, logo de arranque, versión y nombre Reapdf en sus recursos.
- Motor Python y dependencias Windows fijadas por huella, interfaz compilada, fuentes y OCR español/inglés, ejemplos y documentación.
- Cierre del árbol de procesos iniciado por el lanzador; perfiles de ventana separados del navegador habitual. El cierre usa un Job Object propio y no termina procesos ajenos al programa.
- Registro de arranque por proceso en `%LOCALAPPDATA%\Reapdf\logs`. Si falla el inicio estricto no se abre una pestaña como alternativa ni se mantiene el motor oculto. El modo de navegador se puede elegir expresamente mediante el auxiliar.
- Manifiesto con versión, huellas de archivos y declaración de que la ejecución Windows todavía no está verificada.

La ventana usa Edge o Chrome ya instalado, en modo aplicación sin barra de direcciones. El `.exe` es propio; el motor visual de esta entrega depende de ese navegador. Un contenedor de escritorio independiente sigue siendo un trabajo posterior. Java/Ghostscript para determinadas funciones de estándares no se incluyen.

## Cómo probar

1. Extraer **todo** el ZIP; abrir `Reapdf-portable`.
2. Doble clic en `Reapdf.exe`. Mantener junto a `runtime`, `app` y demás archivos.
3. Abrir una copia de un PDF; probar zoom, edición, anotaciones y exportación/reapertura.
4. Guardar/reabrir un proyecto y comprobar recuperación tras cerrar/reiniciar.
5. Comunicar versión, operación, resultado esperado y observado. Si falla el inicio, consultar el registro indicado en el mensaje.

La guía del usuario completa es [LEEME](../portable/LEEME.md). No se requiere administrador para el diseño portable; las políticas de un equipo pueden impedir ejecutar programas externos. El binario de prueba aún no tiene firma de editor: no debe confundirse con una distribución final firmada.

## Verificación y límites

El lanzador se compila con Zig 0.13.0 para `x86_64-windows-gnu`, verificando cabecera PE x64 y subsistema GUI (sin consola). Los paquetes Windows se verifican mediante SHA-256, arquitectura, lista exacta de archivos y recursos requeridos. La construcción no incorpora `.local-state`, documentos personales ni el entorno de desarrollo.

La regresión del motor y la interfaz se ejecuta en Linux. Las pruebas controladas del inicio comprueban señal de preparación, cierre al terminar el proceso propio, rechazo al faltar el navegador y ausencia de alternativa oculta. **No prueban el logo, la ventana ni el comportamiento del ejecutable en Windows real.** Esa comprobación queda pendiente de la prueba de esta entrega.

Se conservan sin modificar los paquetes antiguos 0.20; el nuevo ZIP incluye su número de versión. La guía anterior del portable tenía instrucciones y restricciones históricas; la guía incluida en esta entrega está actualizada al estado actual.

## Continuación del desarrollo

La entrega experimental permite recoger problemas de uso antes del siguiente bloque. Después, desarrollar flujos documentales generales y configurables: [PLAN_CIERRE_Y_FLUJOS.md](PLAN_CIERRE_Y_FLUJOS.md). «Registro y plano» será un perfil posible, no una denominación obligatoria ni una función ya implementada. El 100 % del producto sigue pendiente; este incremento mejora su distribución de prueba.

Regresión local de cierre: **2071 pruebas Python + 105 JavaScript = 2176 pruebas aprobadas**, compilación y recorrido completo de Chromium. Evidencia: [CIERRE_043.json](CIERRE_043.json) y [recibo](validation/0.43/receipt.json). La ejecución gráfica Windows sigue sin comprobar.
