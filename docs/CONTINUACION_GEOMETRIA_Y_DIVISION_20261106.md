# Edición, continuación y división por tamaño · 6 de noviembre de 2026

## Trabajos incorporados en esta pasada

1. **Continuación con formato en una operación.** El botón ya no se desactiva al elegir fuente/tamaño. El asistente recibe las opciones y permite cambiarlas, conservar tamaños o volver a las fuentes originales. Vista previa y aplicación usan el mismo formato en todas las regiones. El texto guardado sigue siendo editable.
2. **Cajas geométricas coordinadas.** Redistribuir un párrafo completo compatible dentro de una página recalcula BBox y dimensiones numéricas Width/Height de Layout. Se clonan atributos y clases compartidos para no cambiar otros elementos. Auto se conserva. Fuente y geometría pueden cambiar juntas.
3. **Panel de párrafo accesible.** La altura se adapta al espacio real del visor, con desplazamiento interno y acciones al pie. Al desplegar opciones se mantiene visible; comprobado a 1366×900. [Captura sintética antes de aplicar](validation/continuation-geometry-size-20261106/paragraph-controls.png).
4. **Dividir por tamaño máximo.** Nuevo modo que calcula automáticamente las partes a partir de los bytes del PDF nativo de salida, conserva orden y calidad y admite la serie «1.46 PINTURA 001.pdf». Mantiene juntos los intervalos de grupos semánticos inseparables. Si una página o grupo mínimo no cabe, explica el límite sin reducir calidad ni entregar ZIP parcial. Cada salida vuelve a comprobarse después de guardarse.

Se añaden al formato común de párrafo y al desglose por páginas/nombres que ya existían; esas funciones anteriores no se contabilizan otra vez.

## Uso

**Editar y continuar:** Editar → Editar texto → clic sobre el texto → Editar párrafo. Escribe con cursor y ajusta ancho/alto. En Fuente y tamaño del párrafo puedes elegir familia/tamaño y conservar negritas/cursivas o aplicar estilo uniforme. Comprobar ajuste y Aplicar párrafo/Ctrl+Enter redistribuyen dentro de la página. Para continuar, pulsa Continuar en otra página sin aplicar antes; conserva borrador y formato. Elige áreas vacías con ratón o coordenadas y cambia el formato allí si hace falta. Comprobar distribución prepara el resultado; cambiar texto/formato/áreas invalida esa revisión. Un fallo conserva el borrador y no publica contenido parcial. Guarda desde la ventana propia de Reapdf.

**Dividir por tamaño:** Organizar páginas → Dividir PDF → Tamaño máximo por archivo. Introduce el máximo en MB; se calculan los rangos y se muestran tamaños medidos. Configura prefijo, separador, inicio y cifras o cambia nombres individuales. Espera Configuración comprobada y descarga el ZIP; la relación opcional registra páginas, nombres, bytes y hashes. Cambiar el límite recalcula los grupos y cambiar cualquier configuración vuelve a comprobarla. 1 MB = 1.000.000 bytes; el tamaño que se exige es el del PDF independiente, no su tamaño comprimido dentro del ZIP. El original permanece intacto.

## Integridad y límites

Las cajas se asocian mediante MCID, ParentTree y estructura, nunca por cercanía. Cada declaración afectada debe describir únicamente la selección completa en una página verificable, y su caja original debe contener el texto. Se conserva el grafo previsto y se comprueban marcadores, vecinos y estilos tras serializar. Admite atributos directos, arrays/revisiones y clases resolubles dentro de los presupuestos existentes. La edición de una línea sigue limitada por su caja original: no redistribuye todo el elemento.

Quedan pendientes cajas por página en elementos que abarcan varias, CSS/colocación restante, estilos heredados contradictorios, reflujo ActualText/Stm general y otras composiciones. La continuación con formato funciona en los perfiles que no requieren esa redistribución geométrica. No es reparación PDF/UA ni geometría universal.

La división conserva las guardas de firmas, permisos, capas, XFA, acciones y estructuras incompatibles. Ofrece 0,01–100 MB en la interfaz, hasta 500 partes/1024 mediciones y 100 MiB de PDF de salida acumulada. No garantiza llenar cada parte al máximo ni reparar cualquier PDF. Los grupos inseparables conservan todo su intervalo para mantener el orden. La alternativa explícita sin etiquetas sigue disponible con la pérdida de accesibilidad indicada en pantalla. Un cambio de documento/rangos/nombres/límite invalida el comprobante. Los bytes medidos no se usan como configuración: la representación del ID puede variar al serializar. El PDF final siempre debe respetar el máximo.

## Verificación real

Fuente exacta `d231c24200df59781d6aff3c2f990b892719e9f2`, respaldada en recovery/editing-20261029. **4.826 pruebas Python, 51 nuevas, tres advertencias de dependencias**. También 203 dirigidas de edición, 119 de división y las 20 específicas actuales de tamaño; la tanda de 119 es anterior a añadir el caso API y las dos regresiones de serialización, que sí están en la tanda de 20 y la regresión completa. **151 JavaScript**, build y manual 75 herramientas +15 operaciones aprobados. **42 recorridos Qt Linux y Windows Server 2025**, fuente limpia antes/después, comprobante 42233362960-1 contrastado con objetos Git y hashes.

**14 ejecuciones independientes de Reapdf.exe aprobadas**. Las nuevas cambian fuente y cajas de un párrafo etiquetado, llevan/cambian formato en continuación manual y configuran división por tamaño con nombres personalizados. El servidor incluido exporta los PDFs/ZIP y el intérprete incluido comprueba texto, fuentes, cajas, páginas, tamaños e imágenes. En el recorrido de tamaño el ZIP se solicita al servidor con la configuración revisada en la interfaz. No se presenta esa exportación como prueba del diálogo nativo de guardar del exe. Desde fuente Qt sí se comprueban guardado PDF/ZIP por diálogo nativo y reapertura. La captura usa una muestra sintética y no sustituye estas pruebas.

Se conservaron ensayos fallidos y se corrigieron problemas concretos. El primer límite de altura del panel aún lo recortaba; se sustituyó por la altura del visor. Dos aserciones de métricas Serif diferían 0,0213 pt: el test usa 0,05 pt y el verificador del motor mantiene 0,3 pt, sin relajar protección. Tres fixtures iniciales de tamaño se corrigieron para usar una página realmente grande, comprobar intervalos sin exigir una partición única y usar una operación de edición admitida. Un ensayo posterior reveló un fallo real: el comprobante incluía bytes de salida variables. Se reprodujeron IDs serializados de 66–70 bytes con tamaño constante del resto de cada PDF; el comprobante ahora vincula la configuración y la fuente, y el límite se exige nuevamente sobre la salida. Dos regresiones específicas cubren variación de bytes y exceso final. La regresión anterior se canceló al detectar el fallo y no se cuenta como aprobada.

### Fallos Windows intermedios que siguen registrados

- Primer intento: 41 recorridos desde fuente aprobados; el nuevo driver intentaba aceptar como diálogo del navegador una confirmación nativa de Qt. Se corrigió solo el driver para exportar y volver al original limpio antes de abrir otra muestra.
- Segundo: 41 recorridos desde fuente aprobados; spacing_flow cerró sin ventanas Qt observadas y el lanzador no terminó en el plazo. Causa no demostrada.
- Tercero: 41 recorridos desde fuente aprobados; el primer target del ejecutable no estuvo disponible en el plazo. Causa no demostrada.
- Cuarto: 42 recorridos desde fuente aprobados; la muestra básica recibió HTTP 422 por ajuste al intentar sustituir «Texto original» por «Ejecutable». La misma solicitud se comprobó satisfactoriamente en Qt local, pero eso no demuestra la causa de Windows ni la corrige.

Se añadieron diagnósticos de procesos y ventanas propios y del registro de arranque. **La aprobación posterior de las 14 ejecuciones no se presenta como solución de esas intermitencias.** Sus recibos, logs y valoraciones permanecen junto a la evidencia final. No acredita Windows cliente limpio, DPI, impresión física ni carga/recuperación sostenidas. Ningún PDF/captura personal en Git. No se publicó otro portable ni se pidieron pruebas personales intermedias.

[Evidencias y hashes](validation/continuation-geometry-size-20261106/results.json).

## Estado y siguiente trabajo

**Avance global estimado: 87,60 % provisional**, antes 87,48 %. Mismos diecisiete pesos/alcance: texto/imágenes 99,5→99,75 aporta 0,04 puntos, accesibilidad 98,75→99 aporta 0,0075 y lectura/páginas 96→97 aporta 0,07. Cambio exacto 87,4775→87,595, incremento 0,1175. No se suman puntos por panel, documentación, diagnósticos o repetir pruebas. Es juicio de ingeniería, no una medición objetiva de paridad comercial u horas restantes. [Baseline](progress/20261106-before-continuation-geometry-size.json).

Los ocho bloques generales siguen abiertos. **La entrega completa solicitada no está cumplida**; technical_complete/accepted_complete siguen falsos y no solo faltan pruebas personales. Siguiente: resolver con causa demostrada las intermitencias de Windows, geometría por página en elementos que continúan entre varias y compatibilidad restante de formularios. No repetir como ausentes las capacidades compatibles incorporadas aquí. Modelo recomendado: **6.1 Sol, razonamiento medio**.
