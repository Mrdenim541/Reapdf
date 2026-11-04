# Entrega solicitada para probar en PC · 4 de noviembre de 2026

El usuario pidió expresamente la versión actual para probarla. Se entrega un **portable Windows x64 con Reapdf.exe y ventana Qt propia**. No es un instalador ni un único ejecutable separable de sus carpetas. No requiere instalar Python, Node o Tesseract.

- [Descargar ZIP — 325,6 MB](https://github.com/Mrdenim541/Reapdf/releases/download/preview-windows-20261104-ddd9bdd/Reapdf-prueba-20261104-Windows-x64.zip)
- [Publicación y archivos](https://github.com/Mrdenim541/Reapdf/releases/tag/preview-windows-20261104-ddd9bdd)
- [Guía rápida](PROBAR_VERSION_ACTUAL.md): extraer todo, abrir Reapdf.exe y probar edición directamente sobre la página.
- [SHA256 publicado](https://github.com/Mrdenim541/Reapdf/releases/download/preview-windows-20261104-ddd9bdd/Reapdf-prueba-20261104-Windows-x64.zip.sha256)

La versión de prueba se identifica por la fecha y etiqueta `preview-windows-20261104-ddd9bdd`. Aunque el motor conserve numeración interna 0.43.0, contiene las mejoras actuales y no es el ZIP histórico de navegador.

## Verificación del archivo entregado

Fuente: `ddd9bddf55a2fcea23c0c4e21ebc2d0655825bcd`. Comprobante Windows: `41870300944-1`. El código de ejecución coincide con 51ffe62; los cambios de entrega son preparación, documentación y CI.

- 28 recorridos de escritorio Windows Server 2025 aprobados.
- Tres aperturas independientes del Reapdf.exe empaquetado: edición básica, espaciado/continuación y paginación automática; también ejecución real de una tarea programada dentro del paquete.
- ZIP de **325.574.685 bytes**, descargado de nuevo en CI y comparado íntegramente con el paquete probado y su checksum.
- Enlace público comprobado desde la nube: HTTP 206, contenido con cabecera ZIP válida, tamaño total correcto y checksum publicado coincidente. La comprobación pública leyó un rango; la descarga íntegra se verificó en Windows CI.
- SHA256: `44b62022562596e2e41cfd8d8aedc6e3a38560c9a4a03bbbf930bb36eb7b9394`.

[Evidencias](validation/windows-preview-20261104/results.json). Se mantienen las limitaciones conocidas: Windows cliente, DPI, impresión física, carga sostenida y funciones técnicas del [plan pendiente](PLAN_ACTUAL.md). Esta entrega no elimina esos pendientes.

**Estimación total sin cambios: 86,87 % provisional.** `technical_complete` y `accepted_complete` siguen falsos. No se añaden puntos por generar o publicar el portable. Modelo recomendado: 6.1 Sol, razonamiento medio.
