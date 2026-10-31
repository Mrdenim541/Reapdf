> Guía de distribución en preparación. El paquete interno con Reapdf.exe ya se ensambló y comprobó en Windows Server 2025; no es una entrega completa del producto. Las pruebas personales se harán después de la entrega técnica final. El ZIP histórico 0.43 usa navegador y no contiene estas mejoras.

# Reapdf — guía de distribución Windows x64

## Abrir sin instalar

1. Descarga el ZIP y elige **Extraer todo** en una carpeta tuya, por ejemplo Descargas. No ejecutes el programa dentro del ZIP.
2. Abre la carpeta extraída `Reapdf-portable` y haz doble clic en **Reapdf.exe**.
3. Aparecerá el logo de inicio y después la ventana de Reapdf. Usa **Abrir PDF** para elegir una copia de un documento o uno de `ejemplos`.
4. Guarda tus cambios con **Guardar PDF** o **Exportar copia**; para continuar otro día utiliza **Guardar proyecto**. Conserva los originales.
5. Guarda o espera «Recuperación local actualizada» antes de cerrar la ventana.

No necesitas instalar previamente Reapdf, Python, Node ni Tesseract; el paquete incluye el motor y OCR español/inglés. Mantén juntos el ejecutable y las carpetas `runtime`, `app` y el resto del contenido. Este `.exe` es un lanzador portable, no un instalador ni un archivo único que puedas separar del paquete.

La futura distribución requiere Windows 10/11 de 64 bits y las dependencias Qt incluidas en el paquete completo. Su ventana integra el motor web y no depende de Edge/Chrome externo. El recorrido del ejecutable interno está comprobado en Windows Server 2025; Windows cliente limpio, DPI, asociaciones y otras verificaciones finales siguen pendientes. El motor trabaja localmente en 127.0.0.1 y elige un puerto disponible. Algunas funciones de estándares requieren Java/Ghostscript, que no se incluyen en este paquete; la interfaz indicará si no están disponibles.

## Si no abre

- Comprueba que extrajiste todo el ZIP y que tu equipo permite ejecutar aplicaciones externas. No requiere elevación, pero un equipo corporativo puede bloquearlo.
- El ejecutable experimental aún no está firmado digitalmente; Windows puede mostrar una advertencia de reputación. Verifica la procedencia y la huella del paquete. Si tu organización lo bloquea, consulta con TI; no desactives sus protecciones.
- El mensaje de error indica el registro de inicio: `%LOCALAPPDATA%\Reapdf\logs`. Puedes revisar ese texto para identificar la causa. No contiene los archivos PDF; revísalo antes de compartirlo.
- **Diagnosticar.cmd** comprueba el motor incluido y muestra el resultado en una consola. **Abrir-en-navegador.cmd** es una alternativa explícita de navegador; en ese modo cierra el motor con Ctrl+C en la consola.
- La recuperación está en `%LOCALAPPDATA%\Reapdf`, fuera de la carpeta del programa. Mover o borrar el portable no elimina esa recuperación. Los proyectos exportados permanecen donde los guardaste.

## Primera prueba recomendada

1. Abre `ejemplos/reapdf-demo.pdf`; prueba zoom 200/400 %, búsqueda y navegación.
2. Edita un texto y añade un trazo o comentario; deshaz y rehace.
3. Exporta y reabre la copia para comprobar contenido y apariencia.
4. Guarda/reabre un proyecto; aplica un cambio y prueba cerrar/reabrir y recuperar la sesión.
5. Abre uno de tus PDF habituales y anota qué función usaste, qué esperabas y qué ocurrió. Guarda el archivo original por separado.

La vinculación configurable entre documentos está incorporada con límites. Los pendientes actuales se consultan en `docs/PLAN_ACTUAL.md`; los planes históricos no sustituyen ese estado. Esta guía no convierte un paquete interno en una entrega final.

## Estado de validación

El paquete interno de la revisión c24f305 fue ejecutado en Windows Server 2025 con Python 3.13.16 incluido. Se comprobó Reapdf.exe, su ventana Qt, apertura de un PDF, edición directa, deshacer/rehacer, exportación y cierre normal, además de once recorridos desde fuente Windows/Linux. La exportación del recorrido del ejecutable usa el servidor de la ventana; guardado atómico y diálogos se verifican por separado. No acredita impresión física, DPI, asociaciones, Windows cliente limpio ni cierre de todas las funciones. El resultado del paquete se vincula a su SHA256 mediante un comprobante separado del manifiesto de construcción; véase `docs/IMAGENES_Y_EJECUTABLE_20261031.md`. No es una prueba personal del equipo del usuario.
