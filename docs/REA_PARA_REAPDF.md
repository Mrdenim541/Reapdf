# Uso concreto de REA en el desarrollo de Reapdf

Se revisaron el repositorio oficial [morluto/rea](https://github.com/morluto/rea), su [instalación](https://github.com/morluto/rea/blob/main/docs/installation.md), [inspección de aplicaciones](https://github.com/morluto/rea/blob/main/docs/desktop-applications.md) y metadatos npm el 29 de octubre de 2026. Versión publicada observada: **rea-agents 6.8.0**, licencia MIT. Referencia de versión/integridad y fuentes: `tools/rea-reference.json`. No se ha instalado ni conectado REA en la PC del usuario desde esta sesión.

## Qué aporta y qué no se presupone

REA ofrece MCP y CLI para inventariar instalaciones, reconocer componentes y, con un proveedor adecuado, analizar binarios. Puede entregar referencias/evidencias sobre comportamientos o componentes para investigar una función concreta. No convierte automáticamente una función de Acrobat/Nitro en código de Reapdf, no desbloquea capacidades premium y su instalación por sí sola no crea control del escritorio Windows ni acceso a las ventanas de esos programas.

El inventario básico de una instalación no requiere descompilar todo el programa. El análisis nativo profundo requiere herramientas aparte, como Ghidra o IDA. Según su documentación, la integración Ghidra en Windows x64 está en estado **experimental P0**. Ghidra/JDK deben corresponder a versiones compatibles; la guía cita Ghidra 12.1.4 con JDK 21 y requisitos distintos para 12.2. El instalador automático de Hopper no es una solución Windows. Antes de cada investigación, usar doctor y comprobar el proveedor real; no sumar al producto una capacidad aún no disponible.

Node exigido por REA 6.8.0: `^22.23.4 || ^24.22.1 || >=26.12.1`. Como Reapdf fija Node 24.x, elegir **24.x >=24.22.1**. El Node 24.19 de esta nube no satisface REA 6.8.0: no se ejecutó forzando su motor. REA queda fuera de las dependencias de la aplicación y del instalador final.

## Secuencia para ahorrar trabajo

1. **Observar un caso pequeño.** En la PC, usar una copia sintética del mismo PDF en Reapdf y en Acrobat/Nitro instalados con acceso a la función. Ejemplo: seleccionar una palabra, ampliar el texto, comprobar reflujo y guardar. Registrar versión, pasos, resultado y fallos. La primera prueba de interfaz no necesita REA.
2. **Comprobar el PDF de salida.** Extraer fuentes, texto, posiciones, imágenes, enlaces y firmas; contrastar apariencia. Así se determina qué debería conservar Reapdf sin investigar internamente toda la aplicación.
3. **Usar REA para una incógnita concreta.** Inventariar la instalación seleccionada y comprobar el proveedor. Limitar la búsqueda al componente pertinente y retener evidencias resumidas. Evitar análisis masivos de todos los módulos de Acrobat/Nitro: no hay garantía de ahorro de cuota y puede consumir más tiempo/contexto.
4. **Especificar comportamiento.** Elaborar una especificación funcional breve con entradas, resultados, casos límite y criterios de aceptación. Implementar en nuestro motor y verificar con documentos. El inventario, pseudocódigo o interfaz ajenos no se presentan como funciones importadas del producto.

Usar copias y muestras sintéticas para la comparación. Separar los resultados privados del análisis de los archivos que se subirán a GitHub; la licencia MIT de REA no concede derechos sobre el código de los programas inspeccionados. La implementación de Reapdf debe ser propia, sin copiar binarios/código comercial ni eludir activaciones.

## Primeras investigaciones recomendadas

| Incógnita | Comparación observable | Aplicación en Reapdf |
|---|---|---|
| Edición de fuentes CFF y texto en Form | Selección, fuente resultante, cambios de recurso y texto/píxeles fuera de la edición | Ampliar casos ahora rechazados, conservando evidencia de integridad. |
| Reflujo con varios estilos | Dónde corta líneas y cómo mantiene fuentes, tamaños y colores | Reflujo original mixto, sin sustitución silenciosa. |
| Selección/movimiento de objetos | Cómo identifica imagen, bloque o grupo y presenta sus controles | Menos pasos y controles en contexto. |
| Guardado/recuperación en Windows | Cancelación, bloqueo externo, cierre inesperado y reapertura | Corregir fallos de nuestro escritorio real antes del paquete final. |

## Registro en Codex local

El helper del proyecto prepara comandos fijados:

```powershell
py -3.12 scripts/local_workspace.py rea-plan
py -3.12 scripts/local_workspace.py rea-setup
```

El primero usa `setup --client codex --dry-run --json`; el segundo inicia el setup interactivo del cliente elegido. La configuración resultante pertenece a esa PC. Reiniciar Codex cuando REA lo indique y comprobar que sus herramientas realmente aparecen; si no aparecen, no afirmar que se ejecutaron.

Para comprobar registro/proveedor, en la carpeta de herramientas fuera del proyecto:

```powershell
npx --yes rea-agents@6.8.0 doctor --client codex --json
npx --yes rea-agents@6.8.0 doctor --provider ghidra --json
```

Un fallo del proveedor no significa que la aplicación de PDF esté dañada. Reparar esa dependencia o continuar con comparación funcional y análisis de PDF. No ejecutar descargas ni instalar motores nativos automáticamente para disimular el fallo.

La CLI documenta inventario acotado con `inspect-desktop-application RUTA --detail summary --evidence_output ARCHIVO --json`. La ruta debe seleccionarse en la PC, sin inventar dónde están Acrobat/Nitro. La salida debe ser nueva y privada. No usar esta sesión de nube para afirmar observaciones sobre programas que no están aquí.

**Criterio de utilidad:** cerrar una incógnita que bloquee una función y transformarla en una implementación propia comprobada. Trasladar el repositorio o instalar REA mantiene el avance total en **71,9 % (≈72 %)**; no añade puntos al software.
