# Sellos RFC3161, revisión TSA y guardado de copias

El programa todavía no está listo para las pruebas personales finales: conserva los pendientes funcionales y de entrega de `PLAN_ACTUAL.md`. Esta implementación amplía firmas y seguridad; no declara terminado el producto ni entrega un ejecutable intermedio.

## Funciones incorporadas

- **Sellar documento:** añade un DocTimeStamp RFC3161 incremental, sin P12 personal, conservando íntegros los bytes de revisiones anteriores.
- **Firmar con certificado:** conserva la firma de aprobación con P12/PFX y permite añadir un token RFC3161 a esa firma.
- **Verificar firmas digitales:** distingue firmas de aprobación, sellos documentales y tokens de firma, con cobertura de revisión, confianza y resultados de revocación separados.
- **Revocación TSA local:** acepta CRL/OCSP suministrados explícitamente, comprueba firma, cobertura y vigencia a la fecha de revisión. Un dato contradictorio que acredita revocación prevalece; la evidencia insuficiente o caducada no se acepta como estado bueno. Las respuestas OCSP explícitas se verifican también cuando el certificado no publica una URL AIA.
- **Guardar copia preparada:** cancelar o fallar al guardar mantiene la copia comprobada en el asistente. Reintentar no vuelve a firmar ni a consultar la TSA. Cambiar ajustes o cerrar descarta esa preparación. La confirmación de guardado nativo se obtiene después de la escritura atómica.

El certificado personal, su contraseña y los ajustes TSA no se guardan en proyectos ni recuperación. Al completar el guardado se retiran de los controles. La copia firmada contiene los certificados públicos necesarios, como corresponde al formato PDF.

## Uso y configuración

En **Formularios y firmas → Sellar documento**, indica una URL HTTPS pública compatible y selecciona la confianza pública de la TSA. «Revisar copia para sellar» comprueba configuración y documento sin solicitar tokens. «Sellar y guardar copia» solicita el sello, lo incorpora y vuelve a verificar el resultado antes de guardarlo. Abre la copia para revisar sus firmas y sellos.

Para firmar con P12, utiliza **Firmar con certificado** y activa «Añadir sello de tiempo a la firma». El certificado de la TSA y el certificado del firmante son distintos: aceptar la cadena de uno no acepta automáticamente la del otro.

La confianza seleccionada valida el token CMS. La conexión HTTPS utiliza la confianza TLS del equipo; no se desactiva su comprobación ni se usa el archivo de confianza TSA para saltarse TLS. Esta versión no configura servicios, contrata proveedores ni admite autenticación HTTP adicional, mTLS o autoridades en redes privadas. Falta comprobar interoperabilidad con proveedores reales elegidos para el uso final.

Solo se envían una huella SHA-256 y un nonce aleatorio de 128 bits, con los datos del protocolo. No se envían el PDF, el P12 ni su contraseña. La estimación y creación pueden requerir dos consultas; la operación admite hasta tres. Una respuesta solo se acepta después de comprobar resultado RFC3161, nonce, algoritmo/huella, fecha, firma CMS, uso del certificado y cadena de confianza seleccionada. Extensiones críticas desconocidas no se acreditan. La fecha del token debe quedar dentro de cinco minutos del reloj de comprobación.

La conexión respeta el proxy y la confianza CA configurados en el equipo, exige HTTPS verificado, no sigue redirecciones y comprueba que la resolución del destino dé direcciones públicas antes de consultar. Hay un plazo total de 15 segundos por consulta, incluyendo resolución, y 512 KB de respuesta. No acepta HTML ni respuestas comprimidas en lugar de un token. No se admiten credenciales en la URL.

## Integridad y alcance

El sellado es incremental y la copia se reabre para verificar el sello nuevo y las firmas previas. Una firma de aprobación puede cubrir una revisión anterior sin cubrir el archivo actual; se informa expresamente. Un token previo dañado impide añadir otra firma o sello, aunque la firma de aprobación que lo contiene siga siendo válida matemáticamente. La evidencia de revocación no oculta ese fallo de integridad.

La verificación de copias es local y no consulta Internet. La revocación del firmante y la de la TSA se mantienen separadas. Sin evidencias se puede comprobar integridad y confianza seleccionada, pero no se acredita revocación. Seleccionar el certificado final como única ancla no acredita una cadena independiente para revocación.

No hay validación histórica, descarga automática de CRL/OCSP, conservación PAdES-LT/LTA, renovación de sellos de archivo ni aceptación jurídica/comercial. DocMDP/FieldMDP y documentos certificados siguen protegidos en estas operaciones. El sello documental básico no se presenta como conservación de archivo.

## Comprobación

**3770 pruebas Python y 130 JavaScript aprobadas**, build y regresión Chromium de firmas aprobados. Trece recorridos Qt aprobaron Linux y Windows Server 2025 con fuente exacta 1c3170c08bfe9064b4103a110050181fe6b8e54e, limpia antes/después. Reapdf.exe interno pasó ventana propia, edición, deshacer/rehacer, exportación y cierre normal en Windows; los diálogos TSA se comprobaron por separado desde fuente. Comprobante 41232766350-1, objetos Git/logs/huella contrastados. [Resultados y evidencias](validation/tsa-workflows-20261031/results.json).

**85,68 % global provisional (≈86 %)**: seguridad/firmas pasa de 71 a 77 con peso 7; suma 0,42 puntos al total. Se mantienen los diecisiete pesos y el alcance. No se asignan puntos por documentación ni repetición de pruebas.

La guía cubre 74 herramientas y 15 operaciones generales; no certifica completitud. No hubo entrega intermedia. Las pruebas usan certificados y claves generados para la prueba, respuestas TSA criptográficas y un servidor HTTPS local con TLS realmente verificado. El recorrido gráfico usa una TSA sintética dentro del proceso de prueba; no introduce un modo de prueba ni una excepción de red en el producto. No se ha contactado con una autoridad externa real.
