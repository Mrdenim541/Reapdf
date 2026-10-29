# Continuar Reapdf con Codex local en Windows

El código y el historial se trasladan mediante Git. No hace falta convertir la aplicación ni exportar la conversación completa. Abrir esta carpeta en una sesión **local** de Codex permite trabajar con el Windows donde corren Qt, Acrobat/Nitro y la impresora; una tarea enviada a la nube sigue ejecutándose en otro equipo y no ve esos programas.

## Qué se conserva

- Fuente actual, recursos incluidos, pruebas, planes y evidencias públicas: rama `recovery/editing-20261029` de `Mrdenim541/Reapdf`.
- Instrucciones para retomar: `AGENTS.md`, `docs/WORK_STATE.md`, `docs/PLAN_ACTUAL.md`, `docs/avance-global.json` y el mensaje inicial más abajo.
- No se trasladan automáticamente sesiones de ChatGPT/Codex, credenciales, MCP configurados en otro equipo, dependencias instaladas, proyectos `.reapdf` no guardados ni archivos personales excluidos de Git.
- El PDF dimensional y sus copias/capturas siguen fuera de Git. Para probarlo en PC, copiarlo directamente a una carpeta local privada, por ejemplo `.local-state/documentos/`, sin añadirlo al repositorio. Guardar un proyecto permite conservar cambios; copiar solo el PDF original no transfiere el historial del editor.

## Preparar una vez

Requisitos: Windows x64, Git, Python 3.12 y Node **24.x >=24.22.1** con npm. Esta versión de Node sirve tanto a Reapdf como a REA 6.8.0; Node 24.19 permite Reapdf pero no el REA fijado. Codex debe estar disponible en ese equipo mediante aplicación, extensión o CLI, con sesión iniciada. Instalar estas herramientas requiere que la PC lo permita; no se requiere modificar software de PDF para desarrollar Reapdf.

En PowerShell, dentro de una carpeta donde puedas trabajar:

```powershell
git clone --branch recovery/editing-20261029 --single-branch https://github.com/Mrdenim541/Reapdf.git Reapdf
cd Reapdf
git switch -c local/windows-validation
py -3.12 scripts/local_workspace.py check
py -3.12 scripts/local_workspace.py setup --dry-run
py -3.12 scripts/local_workspace.py setup
```

Si el repositorio es privado, Git pedirá acceso con tu cuenta autorizada. No pegar contraseñas/tokens en el chat ni en los archivos del proyecto. `setup` instala dependencias Python dentro de `.venv`, ejecuta `npm ci` y compila; no instala Python/Node, no cambia su configuración global ni conecta REA automáticamente. No copiar la `.venv` ni `node_modules` de Linux a Windows.

Si ya existe otro clon con trabajo, revisar `git status` antes de cambiar de rama. No sobreescribirlo ni usar reset destructivo. La rama local separada evita que dos sesiones modifiquen la misma rama remota a la vez. Al cerrar el bloque local, hacer commit, subir esa rama e integrar los cambios revisados; no copiar carpetas de vuelta sobre otra copia activa.

## Abrir y comprobar el escritorio

```powershell
.venv\Scripts\python.exe scripts/local_workspace.py run
```

Abre la **ventana propia Qt** usando la fuente, sin una pestaña de navegador. Es ejecución para desarrollo: aún no es el instalador/portable final ni obliga a entregarlo al usuario antes de lo acordado.

Después de cerrar esa ventana:

```powershell
.venv\Scripts\python.exe scripts/local_workspace.py verify
.venv\Scripts\python.exe -m pytest -q
node --test tests/*.mjs
```

`verify` inicia/cierra un servidor propio en el puerto 8000 y ejecuta ocho recorridos Qt sin pantalla; los resultados privados quedan en `.local-state/desktop-validation/desktop-report.json`. No detener un servidor ajeno si ese puerto está ocupado. Su informe Windows permite cerrar parte de la verificación automática, pero no acredita la prueba visual, DPI, asociaciones ni impresión física. Recorrido humano: `docs/PRUEBA_PERSONAL_ESCRITORIO.md`. El antiguo `scripts/smoke-ui.mjs` sigue pendiente de migrar a controles actuales.

Si alguna herramienta externa de estándares no está disponible en Windows, registrar la limitación y el error; no dar por aprobado lo que se omitió. El diagnóstico `check` informa versiones, Qt y compilación; no promete que todas las funciones externas estén listas.

## Retomar en Codex

Abrir la carpeta local `Reapdf` y usar una sesión que ejecute comandos en esa PC. Mensaje sugerido:

> Continúa este repositorio en modo local. Lee AGENTS.md, docs/WORK_STATE.md, docs/PLAN_ACTUAL.md y docs/CONTINUAR_EN_PC.md. Consulta la referencia global vigente en docs/avance-global.json y mantén sus pesos. Primero comprueba el entorno Windows y ejecuta las verificaciones de escritorio; corrige fallos reales. Después trabaja compatibilidad de edición y migra la prueba gráfica histórica. Mantén edición sobre la página, ventana Qt y los archivos personales fuera de Git. No generes portables intermedios. Para REA, sigue docs/REA_PARA_REAPDF.md; comprueba su disponibilidad y el proveedor antes de afirmar que puedes analizar Acrobat/Nitro. Al finalizar indica pruebas, límites, avance total y modelo recomendado.

No es necesario que Codex lea todo el historial del chat para retomar: esos documentos contienen el estado verificable y las decisiones vigentes. Una sesión nueva debe comprobar el estado del disco y no asumir acceso a ventanas o herramientas de otra máquina.

## Conectar REA, por separado

Desde el clon, después de preparar Node:

```powershell
py -3.12 scripts/local_workspace.py rea-plan
py -3.12 scripts/local_workspace.py rea-setup
```

`rea-plan` adquiere la versión fijada en una carpeta de herramientas fuera del repositorio y solicita un plan de configuración de Codex sin aplicarlo. `rea-setup` inicia la configuración interactiva de ese cliente: muestra los cambios para revisarlos. No configura todos los agentes ni instala Hopper automáticamente. Reiniciar la sesión local de Codex según indique REA. La adquisición mediante npx usa la caché de npm; no eliminar esa instalación mientras su registro MCP dependa de ella.

No ejecutar esta configuración en la nube esperando que aparezca en la PC: son perfiles y máquinas distintos. Detalles, fuentes y límites de REA: `docs/REA_PARA_REAPDF.md`.
