# Reapdf · continuidad del desarrollo

- Hablar con el usuario en español. Modelo habitual: 6.1 Sol, razonamiento medio. Al cerrar un avance indicar resultados, pruebas reales, limitaciones, porcentaje TOTAL y modelo recomendado.
- Leer `docs/PLAN_ACTUAL.md` y el inicio de `docs/WORK_STATE.md`; la matriz vigente es `docs/avance-global.json`. Referencia: 71,9 ponderado, aproximadamente 72 %. Mantener alcance/pesos y justificar cambios. Preparar herramientas o trasladar el repo no aumenta la madurez del producto.
- Esta fuente procede de 0.43 recuperado y mejoras posteriores. 0.55 no está recuperado; no afirmar que todo el historial está implementado.
- El usuario prioriza edición de texto con ratón/cursor sobre la página, interfaz clara y ventana Qt propia. Mantener también las cajas ajustables del proyecto.
- Excluir generación de informes, registros o documentos de ensayos personales. Mantener vinculación configurable con archivos/roles generales.
- No generar ni entregar instaladores/portables intermedios; preparar candidato cercano al 90 % con recorridos básicos y Windows comprobados, según autorización vigente del usuario.
- PDFs personales, copias, capturas, credenciales y resultados de inspección de programas externos deben quedar fuera de Git. Usar `.local-state/` para trabajo local privado. No copiar datos privados desde evidencias a documentación pública.
- Para Windows local, consultar `docs/CONTINUAR_EN_PC.md`. Preparar con `py -3.12 scripts/local_workspace.py setup`; ejecutar con `.venv\Scripts\python.exe scripts/local_workspace.py run`.
- Usar `.venv` para Python. Compilar con `npm run build`; comprobar JavaScript con `node --test tests/*.mjs`. Ejecutar pruebas dirigidas pertinentes y regresión completa cuando el alcance lo justifique.
- Pruebas propias de escritorio: `scripts/check_desktop_candidate.py`. Linux offscreen no acredita Windows, DPI ni impresión física. El recorrido histórico `scripts/smoke-ui.mjs` requiere migración de controles anteriores y no figura como aprobado.
- REA es opcional y separado del producto. Evaluación y plan en `docs/REA_PARA_REAPDF.md`. No asumir que instalar su MCP permite controlar Acrobat/Nitro o importar funciones automáticamente.
- No descartar trabajo de otro checkout ni usar push forzado. En PC usar una rama distinta de la de nube; integrar cambios revisados mediante Git.
