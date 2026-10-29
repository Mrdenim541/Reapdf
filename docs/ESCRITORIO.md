> Actualización 0.43: se añade `Reapdf.exe`, lanzador Windows GUI compilado con logo de inicio, registro de errores y cierre del árbol de procesos propio. Sigue utilizando Edge/Chrome instalado; no incorpora aún un runtime independiente. La ejecución gráfica en Windows permanece sin comprobar. Guía actual: [LEEME](../portable/LEEME.md).

# Modo ventana — versión 0.14

**Iniciar-Reapdf.cmd** intenta abrir Reapdf en una ventana de aplicación sin barra de direcciones, usando Edge o Chrome instalado. No exige instalar Python o Node ni añade un navegador al sistema. Si no encuentra uno compatible o el proceso falla al arrancar, abre el navegador habitual y mantiene la dirección local en la consola. **Abrir-en-navegador.cmd** permite elegir expresamente ese modo.

La interfaz sigue siendo HTML/React y el motor PDF es Python/PyMuPDF local. Este es un primer modo de ventana sobre Chromium instalado; no es un contenedor nativo independiente ni incluye su propio Chromium. La función requiere comprobar el comportamiento de Edge/Chrome del equipo Windows de destino.

## Inicio y cierre

El motor reserva un puerto local antes de abrir la ventana. Se crea un perfil de navegador temporal exclusivo, separado del perfil habitual, con sincronización y extensiones deshabilitadas. No se cambia el navegador predeterminado ni se instala un servicio. La recuperación documental sigue en la carpeta descrita en SESIONES.md, separada de ese perfil.

Al finalizar normalmente el proceso de la ventana, se solicita el cierre del motor y sus temporales de sesión. Si hay ventanas de impresión de ese mismo proceso todavía abiertas, puede seguir activo hasta cerrarlas. Ctrl+C en la consola detiene el motor y termina únicamente el proceso de navegador que este lanzador creó. El perfil temporal se intenta limpiar; bloqueos de archivos o terminaciones abruptas pueden dejar temporales. Exporta/guarda el proyecto o espera el checkpoint antes de cerrar.

En el modo de navegador normal el cierre de una pestaña no termina el motor: utiliza Ctrl+C. Si el modo ventana no se comporta correctamente, usa Abrir-en-navegador.cmd y conserva el mensaje de la consola.

## Desarrollo y validación real

El lanzador empaquetado admite `--desktop`, `--no-browser`, `--self-test` y puerto opcional. `--desktop` y `--no-browser` son excluyentes. Se buscan rutas habituales de Edge/Chrome en Windows; una instalación en otra ruta puede requerir el modo de navegador normal.

Se probaron desde Linux la detección de rutas simuladas, argumentos sin shell y con espacios, perfil exclusivo, limpieza al fallar el lanzamiento, terminación del proceso propio, cierre del servidor al terminar un proceso controlado y alternativa cuando falta navegador. También se comprobó el lanzador real con Python Linux y los flujos HTTP de proyectos, recuperación, exportación e impresión. **No se abrió una ventana gráfica Windows ni se validó un navegador Windows real.** Esas pruebas controladas no certifican su comportamiento visual ni todos los procesos hijos en esa plataforma.

Siguiente paso de distribución: validar esta entrega en Windows con varias versiones de Edge/Chrome, cierre normal y abrupto, diálogos/descargas/impresión y recuperación. Después se decidirá si mantener este modo o incluir un runtime de escritorio para independencia del navegador instalado; incluirlo aumenta el tamaño y exige pruebas propias.
