# Reapdf 0.43 — prueba personal Windows x64

## Abrir sin instalar

1. Descarga el ZIP y elige **Extraer todo** en una carpeta tuya, por ejemplo Descargas. No ejecutes el programa dentro del ZIP.
2. Abre la carpeta extraída `Reapdf-portable` y haz doble clic en **Reapdf.exe**.
3. Aparecerá el logo de inicio y después la ventana de Reapdf. Usa **Abrir PDF** para elegir una copia de un documento o uno de `ejemplos`.
4. Guarda tus cambios con **Exportar copia**; para continuar otro día utiliza **Guardar proyecto**. Conserva los originales.
5. Guarda o espera «Recuperación local actualizada» antes de cerrar la ventana.

No necesitas instalar previamente Reapdf, Python, Node ni Tesseract; el paquete incluye el motor y OCR español/inglés. Mantén juntos el ejecutable y las carpetas `runtime`, `app` y el resto del contenido. Este `.exe` es un lanzador portable, no un instalador ni un archivo único que puedas separar del paquete.

Necesitas Windows 10/11 de 64 bits y Edge o Chrome ya instalado: la ventana de esta entrega utiliza su modo aplicación, sin barra de direcciones. No se incluye todavía un contenedor de escritorio independiente. El motor trabaja localmente en 127.0.0.1 y elige un puerto disponible. Algunas funciones de estándares requieren Java/Ghostscript, que no se incluyen en este paquete; la interfaz indicará si no están disponibles.

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

Las automatizaciones personales configurables todavía están planificadas: consulta `docs/PLAN_CIERRE_Y_FLUJOS.md`. Esta entrega permite probar el editor actual; no representa el cierre del producto.

## Estado de validación

El ejecutable se compiló como Windows x64 GUI y se comprobó su estructura, recursos y paquete desde Linux. Los flujos del motor y la interfaz se prueban en Linux. **La ventana y el binario incluidos todavía requieren ejecución real en Windows.** El manifiesto declara esa limitación; compilar un `.exe` no demuestra que se haya probado en tu PC.
