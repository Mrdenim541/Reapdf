# Firmas digitales — avance 0.29

Reapdf incorpora firma local con certificado y verificación criptográfica, separadas de la firma manuscrita visual. Se usa pyHanko 0.38.0 con SHA-256; el certificado se maneja mediante cryptography. No se genera otro portable en este avance.

## Firmar una copia

1. Abre el PDF y termina sus ediciones. En **Formularios y firmas → Firmar con certificado**, selecciona tu archivo P12/PFX y su contraseña.
2. **Inspeccionar certificado** muestra titular, emisor, fechas UTC, tipo/tamaño de clave y huella SHA-256. Un certificado compatible para firmar no implica que su cadena sea de confianza o que no esté revocado.
3. Puedes añadir motivo y lugar. La **marca visible** es opcional: elige una página sin giro y define X/Y/ancho/alto en puntos. El recuadro sobre la página indica ubicación; el texto final incluye titular y fecha. Se requiere un área mínima de 180 × 65 pt dentro de la página. El recorte de página está admitido; para páginas giradas se admite firma sin marca visible.
4. Pulsa **Revisar copia para firmar**. Cambiar certificado, contraseña, posición, motivo o lugar invalida esa revisión. Solo una revisión vigente habilita **Firmar y descargar copia**.
5. Se firma y se verifica la copia antes de entregarla. El editor abierto conserva su historial y PDF actual. El archivo P12/PFX y la contraseña se retiran del asistente tras la descarga; cerrarlo también retira el componente. No se guardan en proyectos, recuperación o informes. No se promete borrado físico de memoria del navegador/sistema.
6. Abre la copia descargada y usa **Verificar firmas digitales**. El PDF firmado queda protegido frente a las ediciones ordinarias de Reapdf.

La firma es una firma de aprobación CMS/CAdES con subfiltro `ETSI.CAdES.detached`, realizada de forma incremental. No se certifica el documento con DocMDP. Si hay cambios aplicados en la sesión, se incluyen antes de crear la firma. El P12/PFX debe contener clave privada y certificado correspondiente, medir hasta 2 MB y tener hasta 20 certificados auxiliares. Contraseña de hasta 256 caracteres; también se admite un P12/PFX sin contraseña.

Se admiten RSA de 2048–8192 bits y EC con curvas P-256/P-384/P-521. El certificado debe estar vigente, declarar uso de firma digital o compromiso de contenido y no ser una autoridad. Si contiene usos extendidos, deben admitir firma de documentos. No se incorporan tokens USB, tarjetas, HSM, firma remota ni autenticación de proveedores.

## Añadir una segunda firma

Abre la copia ya firmada y selecciona **Firmar con certificado** de nuevo. Reapdf verifica las firmas existentes y añade una revisión incremental sin reescribir los bytes anteriores. Se distinguen las firmas que cubren una revisión anterior de la última que cubre el archivo actual.

Se admiten hasta 20 firmas y 40 MB de PDF firmado. No se añade otra firma si la revisión de integridad/cambios falla, queda inconclusa o presenta cambios que requieren revisión. Los documentos certificados o con restricciones DocMDP/FieldMDP permanecen protegidos. Tampoco se aprovechan campos vacíos preexistentes: se crea un campo de firma nuevo con nombre único. Un PDF con indicadores de firma sin una firma interpretable se conserva sin firmar.

La copia debe permitir modificar, rellenar y copiar. Los PDF cifrados deben abrirse como copias autorizadas sin cifrado; Reapdf no descifra documentos firmados para volver a firmarlos. El modo firma de aprobación está separado de organizar, editar, censurar o añadir anotaciones a documentos firmados.

## Verificar firmas digitales

En **Formularios y firmas → Verificar firmas digitales**, pulsa **Comprobar firmas**. Desde **Leer → Revisar documento**, un documento con indicadores de firma ofrece acceso directo al mismo asistente.

El informe separa:

- **Integridad de bytes y firma criptográfica**: si el resumen del contenido y la firma CMS corresponden a los bytes cubiertos.
- **Cobertura y cambios posteriores**: archivo completo o revisión anterior, con la clasificación de cambios de pyHanko. Una firma anterior puede permanecer intacta aunque no cubra la última revisión. Las firmas/campos posteriores compatibles se distinguen de cambios ajenos o inconclusos.
- **Confianza del certificado**: sin certificados seleccionados no se establece confianza, aunque la firma sea criptográficamente correcta. No se usan silenciosamente las autoridades del sistema ni se confía por estar un certificado incluido dentro del PDF.
- **Vigencia y uso**: se muestran las fechas y restricciones de la política local. Un certificado caducado, de autoridad o de uso incompatible no recibe el estado de cadena aceptada para firma personal.
- **Fecha declarada**: es la hora declarada por el firmante, no una prueba del momento real de firma. Se señala la presencia de un token de tiempo sin acreditar aquí una TSA confiable.

Para comprobar una cadena con confianza explícita, selecciona uno o varios certificados públicos PEM/DER en un archivo, hasta 20 certificados/512 KB. Deben ser certificados que hayas decidido aceptar para esa comprobación; se pueden retirar con **Quitar confianza seleccionada**. No se añaden al sistema, no se reutilizan automáticamente en otra sesión y no se aceptan claves privadas como material de confianza.

La operación es **sin red**: no consulta AIA, OCSP o CRL ni acredita el estado de revocación. «Cadena aceptada con la confianza seleccionada» no equivale a una validación jurídica, una lista de confianza oficial, una firma cualificada ni validación histórica a largo plazo. No se declara PAdES-LT/LTA ni PDF/A por usar un subfiltro CAdES. Estas limitaciones aparecen en la interfaz y en el informe.

## Informe JSON y recuperación

**Descargar informe de firmas JSON** conserva huella SHA-256 y tamaño del PDF verificado, hora de comprobación, certificados de confianza utilizados, resultados por firma, cobertura, algoritmos, certificados públicos y límites de la revisión. No contiene clave privada ni contraseña. Verificar y descargar el informe no crean historial ni modifican el documento.

Los proyectos y la recuperación conservan exactamente los bytes del PDF firmado: no se compacta ni se vuelve a guardar el PDF al empaquetarlo. El recorrido automatizado comprueba que las firmas siguen intactas tras recuperar. Los informes y revisiones no se guardan como una afirmación permanente de confianza dentro del proyecto; se vuelven a calcular.

## Evidencia y pendientes

Se usan certificados sintéticos de prueba; no se han usado credenciales personales. Hay pruebas reales RSA/EC, firma sucesiva, marca visible con recorte, firma invisible con cuatro giros y conservación de píxeles, certificado caducado/futuro/de uso incorrecto/débil, confianza equivocada, permisos, límites, alteraciones de bytes y revisiones posteriores, proyectos y solicitudes HTTP. Se comprueba ausencia de conexiones incluso con URLs AIA/OCSP en el certificado de prueba. Poppler `pdfsig` verifica de forma independiente la firma generada.

La ejecución real en Windows y la interfaz de Acrobat/Nitro siguen pendientes. Las dependencias Windows se fijan con hashes y se comprueban por descarga; esto no acredita la ejecución de un nuevo portable o ejecutable. Revocación, TSA, validación histórica/LT/LTA, firma remota, tokens y políticas de certificación tienen trabajos propios.

## Próximo bloque recomendado

1. Contrastar firmas y documentos representativos en lectores externos, incluida ejecución Windows.
2. Incorporar validación de revocación y sello de tiempo con proveedores configurables, límites de red y un modelo explícito de confianza y fecha de validación.
3. Validadores de estándares y accesibilidad; continuar estructuras complejas de edición/censura y conversión Office.
4. Preparar la entrega del ejecutable propio con logo, ventana y recuperación cuando se cumplan sus criterios de prueba.

## Capturas

- [Firma con certificado](images/Reapdf-Firma-certificado-0.29.png).
- [Verificación con confianza explícita](images/Reapdf-Verificacion-firmas-0.29.png).

Validación del cierre 0.29: **1396 pruebas Python y 84 JavaScript aprobadas (1480 en total)**, compilación de producción y recorrido completo en Chromium aprobados en Linux. El recorrido incluye firma visible, limpieza de credenciales del asistente, verificación sin confianza y con confianza explícita, informes, segunda firma, proyecto/recuperación con bytes intactos y detección de alteración, además de todos los flujos anteriores. Poppler pdfsig verifica independientemente la firma generada. Las 40 dependencias Windows se descargaron y validaron con hashes; no se ejecutó Windows ni se generó un nuevo portable. Revocación, TSA y LT/LTA siguen pendientes.
