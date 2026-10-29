> Entrega vigente de prueba: 0.43, solicitada ahora por el usuario, con `Reapdf.exe` propio. [Guía actual](../portable/LEEME.md) y [alcance de validación](ENTREGA_EJECUTABLE_043.md). Las instrucciones y nombres de paquetes siguientes pueden corresponder a versiones históricas.

# Distribución Windows — preparación y antecedentes

**Política vigente:** por indicación del usuario, no se generan nuevos portables en cada avance. El código está en 0.23; el último portable generado corresponde a 0.20. La siguiente entrega para pruebas personales será un programa ejecutable cuando el alcance esté casi completo, con validación en Windows. Las instrucciones siguientes describen el paquete experimental existente y la preparación futura.

Archivo: `entregas/Reapdf-portable-Windows-x64.zip`. Contiene código, interfaz ya compilada, Python 3.13.16 de Python Software Foundation (NuGet), dependencias Windows x64, runtime C++ local, licencias, ejemplo y documentación. No requiere instalar Python, Node.js, pip ni Visual C++ Redistributable en el equipo de prueba.

Extraer todo y abrir **Iniciar-Reapdf.cmd**. El servidor reserva un puerto disponible en `127.0.0.1` e intenta abrir una ventana de Edge/Chrome al estar listo; ofrece navegador normal si falta o falla. La consola muestra la dirección real. Debe permanecer abierta; Ctrl+C detiene la aplicación. No se instala un servicio ni se modifica PATH. Se necesita permiso para ejecutar programas y usar una carpeta accesible; una política corporativa puede impedirlo.

El modo ventana usa Edge/Chrome instalado; no es un contenedor nativo independiente ni un instalador firmado. Véase ESCRITORIO.md. Se usan temporales del usuario y el navegador existente; no se promete ausencia de datos temporales o caché. Guarda un proyecto o espera a que la recuperación local esté actualizada antes de cerrar. Esta copia persiste en LocalAppData, fuera de la carpeta del portable; véase SESIONES.md. No incluye borradores ni historial completo.

## Construcción reproducible

1. Preparar el entorno de desarrollo y compilar la interfaz con `npm run build`.
2. Ejecutar `python scripts/package_portable.py`.
3. El script descarga el runtime fijado y las wheels de producción Windows x64, valida sus SHA256, extrae bibliotecas sin ejecutar instaladores y crea el ZIP y su archivo SHA256.
4. Verificación estática: `python -m scripts.verify_portable_windows entregas/Reapdf-portable-Windows-x64.zip --static-only`.
5. Verificación nativa, solo en Windows: el mismo comando sin `--static-only`.

Versiones, archivos y hashes se fijan en `portable/dependencies-windows.json` y `requirements-windows.lock`. Solo se incluyen dependencias de ejecución, no pytest ni Node. El runtime incluye las DLL C/C++ necesarias en la carpeta de la aplicación. Se conservan las licencias incluidas por sus distribuidores.

La construcción descarta el pip preinstalado del runtime para evitar herramientas y lanzadores de otras arquitecturas que no se usan al ejecutar la aplicación. Se comprueba la arquitectura PE x64 de todos los ejecutables y DLL/PYD extraídos. `MANIFIESTO.json` registra versión, procedencia y hashes de cada archivo. El código del motor/visor y el árbol de desarrollo completo se incluyen en `fuentes`, con dependencias y herramientas de construcción/pruebas. La aplicación de ejecución está separada en `app`. Para reconstruir, se trabaja desde `fuentes` con los requisitos de desarrollo indicados en su README.

## Verificación y límites reales

En esta entrega se comprobó desde Linux la integridad del archivo, contenido, arquitectura PE, hashes y dependencias fijadas. Se probó el mismo lanzador con Python Linux en una carpeta con espacios, autoprueba de edición y el recorrido HTTP de abrir y exportar un PDF.

**No se ejecutó el Python Windows ni se abrió el portable en Windows.** El manifiesto indica `windows_execution_verified: false`. Las comprobaciones estáticas no prueban compatibilidad con un equipo Windows real. `Diagnosticar.cmd` permite ejecutar la autoprueba nativa al recibir el paquete.

Se preparó `.github/workflows/portable.yml` para construir, ejecutar pruebas en Windows y guardar el ZIP como artefacto de Actions. El flujo todavía no se ejecutó ni se publicó desde esta sesión. No se ofrece una URL ficticia de descarga en GitHub.

El portable es de prueba personal. La decisión comercial del motor y sus licencias sigue abierta; revisar MOTOR.md antes de una publicación propietaria o comercial.

Prueba de este corte: editar un índice con hijos, añadir encabezado y pie numerado con vista previa, exportar y reabrir proyecto. Guía: MARCADORES_Y_ENCABEZADOS.md.

Desde 0.16 se incluye `ejemplos/reapdf-formulario.pdf` para probar texto, casillas y listas. También hay creación desde PNG/JPEG y exportación de páginas a PNG/JPEG en ZIP. Véanse FORMULARIOS.md y CONVERSIONES.md.

En 0.17 se incluyen idiomas OCR español/inglés con hashes y licencias, fuente DejaVu Sans y el ejemplo reapdf-escaneado.pdf. La autoprueba ejecuta OCR real, compara píxeles, cifra y descifra una copia autorizada. Las pruebas del lanzador se ejecutaron con Python Linux, no con Python Windows. Guía: AVANCE_LARGO_017.md.

En 0.18 la autoprueba añade etiquetas Unicode, adjuntos, Bates, firma visual y censura. La interfaz permite ampliar estas vistas previas. Guía: AVANCE_LARGO_018.md. No cambia la limitación: esta sesión no ha ejecutado el portable en Windows.

En 0.19 se añade el ejemplo reapdf-formulario-avanzado.pdf y la autoprueba de grupos de radio, valores y aplanado. Se mantiene pendiente la ejecución Windows. Guía: FORMULARIOS_AVANZADOS.md.

En 0.20 se añade reapdf-texto-con-estilos.pdf y la autoprueba de edición con un subconjunto TrueType conservando el programa original. Ejecución Windows todavía pendiente. Guía: TEXTO_CON_ESTILOS.md.

El código 0.21 prepara reapdf-recorrido.pdf, catálogo/búsqueda/favoritos, comandos y atajos, protección de borradores y revisión estructural con JSON. Consulta ESPACIO_DE_TRABAJO.md. El diagnóstico del lanzador comprueba también la revisión de un formulario. Ejecución real en Windows pendiente.
