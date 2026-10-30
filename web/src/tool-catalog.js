// A single catalog drives the sidebar, command search and availability messages.
export const groups = [
 ['read','Lectura y revisión'],['edit','Contenido'],['annotate','Anotaciones'],
 ['pages','Páginas'],['forms','Formularios y firma'],['document','Documento y conversión'],
];
export const areas = [
 {id:'read',label:'Leer',description:'Lee, busca y revisa la estructura del documento.'},
 {id:'edit',label:'Editar',description:'Corrige texto e imágenes o añade contenido.'},
 {id:'annotate',label:'Comentar',description:'Revisa marcas, escribe notas y dibuja sobre la página.'},
 {id:'pages',label:'Organizar páginas',description:'Compón el documento, sus etiquetas y su índice.'},
 {id:'forms',label:'Formularios y firmas',description:'Completa campos, firma con certificado o revisa firmas digitales.'},
 {id:'convert',label:'Convertir y OCR',description:'Reconoce escaneados y exporta texto, tablas o imágenes.'},
 {id:'workspace',label:'Documentos',description:'Vincula archivos, mide planos y controla capas.'},
 {id:'protect',label:'Proteger',description:'Prepara copias protegidas o censuradas.'},
];
const areaMembers={
 workspace:['portfolio','document_links','measurement','layers','xfdf','structure'],
 read:['view','review','compare','attachments','metadata','accessibility'],
 edit:['find_replace','text','paragraph','flow','textbox','link','existing_links','images','existing_images','watermark','headers'],
 annotate:['comments','select','highlight','underline','strikeout','note','ink','line','arrow','rectangle','stamp'],
 pages:['organizer','insert','replace','duplicate','blank','crop','split','labels','bookmarks','numbering','bates'],
 forms:['form_rules','calculate','forms','field_properties','field','data','flatten','signature','digital_sign','verify_signatures'],
 convert:['ocr','region_ocr','table_region','export_images','tables','export_text','optimize','batch','automation','docx','archive','compress'],
 protect:['protect','redact','standards','working_copy','preflight'],
};
export const toolArea=id=>areas.find(a=>areaMembers[a.id].includes(id));
export function areaChangeReason(state={}){
 if(state.busy||state.transforming||state.stroke)return 'Espera a que termine la operación actual.';
 return state.draft?'Aplica o cancela los cambios pendientes antes de cambiar de área.':'';
}
const entry=(id,label,description,group,permission='edit',target='dialog',keywords='')=>({id,label,description,group,permission,target,keywords,area:toolArea(id)?.id});
export const tools = [
 entry('table_region','Extraer tabla por región','Reconoce tablas digitales o escaneadas, permite revisar celdas y exportar CSV o Word.','document','copy','dialog','tabla escaneada excel OCR celdas word'),
 entry('region_ocr','OCR de región','Reconoce zonas escaneadas y corrige inclinación o perspectiva sin cambiar su imagen.','document','edit_copy'),
 entry('structure','Etiquetas y orden de lectura','Revisa el flujo de texto y edita alternativas, roles, idiomas y orden de etiquetas hermanas.','read','read'),
 entry('preflight','Inspección de impresión','Revisa resolución efectiva, fuentes, cajas y colores antes de imprimir.','document','read'),
 entry('xfdf','Intercambiar XFDF','Importa y exporta anotaciones y datos compatibles de otros lectores.','document','copy'),
 entry('working_copy','Copia de trabajo sin firmas','Crea una copia editable identificada, sin trasladar validez de firmas digitales.','document','copy'),
 entry('document_links','Vincular documentos','Relaciona documentos mediante identificadores y destinos revisados.','document','copy'),
 entry('measurement','Medir planos','Calibra distancias y guarda longitudes, áreas y cantidades.','document','edit'),
 entry('layers','Capas del PDF','Revisa y configura la visibilidad de capas opcionales.','document','read'),
 entry('view','Lectura','Selecciona texto y sigue enlaces del documento.','read','read','tool'),
 entry('select','Seleccionar marca','Selecciona y modifica anotaciones compatibles.','read','read','tool'),
 entry('accessibility','Accesibilidad y preparación','Revisa etiquetas, alternativas, título e idioma y prepara metadatos compatibles.','read','read','dialog','pdf ua accesible idioma etiquetas alternativo'),
 entry('standards','Validar estándares PDF','Comprueba PDF/A y PDF/UA con veraPDF y genera un informe de reglas.','document','read','dialog','pdfa iso estándar conformidad preflight verapdf'),
 entry('archive','Crear copia PDF/A-2b','Reconstruye una copia de archivo y exige validación independiente antes de descargar.','document','edit_copy','dialog','pdfa archivo conservación preservación'),
 entry('review','Revisar documento','Localiza anotaciones, campos, enlaces y posibles escaneados.','read','read','dialog','diagnóstico inspección control calidad'),
 entry('compare','Comparar documentos','Compara texto y apariencia de dos PDF.','read','copy'),
 entry('find_replace','Buscar y reemplazar','Busca texto digital y revisa reemplazos con fuente compatible.','edit','read','dialog','buscar reemplazar coincidencias palabras mayúsculas'),
 entry('text','Editar texto','Pulsa el texto sobre la página y escribe; conserva la fuente compatible o cambia el formato.','edit','edit','tool'),
 entry('paragraph','Reemplazar bloque de texto','Corrige fragmentos con fuente original o redistribuye un párrafo.','edit','edit','dialog','fuentes estilo negrita cursiva párrafo'),
 entry('textbox','Añadir texto','Pulsa en la página y escribe; altura automática y formato en contexto.','edit','edit','tool'),
 entry('link','Enlaces','Crea y edita enlaces web o a páginas.','edit','edit','tool'),
 entry('existing_links','Editar enlaces del PDF','Cambia destinos, mueve, redimensiona o elimina enlaces existentes.','edit','edit','dialog','hipervínculos vínculos url destinos'),
 entry('images','Imágenes','Añade PNG o JPEG y ajusta su posición y tamaño.','edit','edit','tool'),
 entry('existing_images','Editar imágenes del PDF','Mueve, reemplaza o elimina imágenes compatibles del original.','edit'),
 ...[['highlight','Resaltar','Resalta palabras o fragmentos precisos del texto digital.'],['underline','Subrayar','Subraya palabras o caracteres sin modificar su contenido.'],['strikeout','Tachar','Marca texto tachado; su contenido se conserva.'],['note','Nota','Coloca una nota y escribe su comentario.'],['ink','Lápiz','Dibuja trazos libres con color y grosor.'],['line','Línea','Traza una línea entre dos puntos.'],['arrow','Flecha','Señala una zona con una flecha.'],['rectangle','Rectángulo','Delimita una zona con un rectángulo.'],['stamp','Sellos','Coloca uno de los sellos estándar.']].map(([id,label,description])=>entry(id,label,description,'annotate','annotate','tool')),
 entry('comments','Comentarios y revisión','Busca conversaciones, añade respuestas y exporta informes CSV/JSON.','annotate','read','dialog','comentarios respuestas estados revisión informe autor'),
 entry('organizer','Organizar páginas','Ordena, gira, elimina o extrae páginas.','pages','organize_or_extract','organizer'),
 entry('insert','Unir o insertar PDF','Incorpora páginas de otro PDF.','pages','organize','insert'),
 entry('replace','Reemplazar páginas','Sustituye páginas por otras de un PDF.','pages','organize','replace'),
 entry('duplicate','Duplicar páginas','Crea copias de páginas compatibles.','pages','duplicate'),
 entry('blank','Página en blanco','Inserta una página vacía.','pages','blank'),
 entry('crop','Recortar páginas','Ajusta el área visible; no elimina el contenido oculto.','pages'),
 entry('split','Dividir PDF','Divide por bloques, rangos o marcadores con nombres personalizados y descarga un ZIP.','pages','extract'),
 entry('labels','Etiquetas de página','Configura números romanos, letras y prefijos de navegación.','pages'),
 entry('bookmarks','Editar marcadores','Edita el índice jerárquico y sus destinos.','pages'),
 entry('headers','Encabezados y pies','Añade texto en los márgenes con vista previa.','pages'),
 entry('numbering','Numerar páginas','Añade números visibles en las páginas.','pages'),
 entry('forms','Rellenar formulario','Completa campos compatibles, incluidos grupos compartidos y radios.','forms','fill'),
 entry('field_properties','Propiedades de campos existentes','Ajusta nombre, opciones de listas, posición y formato conservando valores y grupos.','forms','edit','dialog','diseño formulario solo lectura obligatorio mover redimensionar'),
 entry('field','Crear o eliminar campos','Diseña campos simples o elimina grupos compatibles.','forms'),
 entry('data','Datos de formulario','Exporta o importa valores en JSON verificado.','forms','copy'),
 entry('flatten','Aplanar formulario','Convierte campos compatibles en contenido visible.','forms'),
 entry('digital_sign','Firmar con certificado','Firma una copia con P12/PFX y comprueba su integridad antes de descargar.','forms','sign','dialog','firma digital certificado criptografía p12 pfx'),
 entry('verify_signatures','Verificar firmas digitales','Revisa integridad, cambios y confianza explícita de los certificados.','forms','read','dialog','firma digital validación certificado confianza integridad'),
 entry('signature','Firma visual manuscrita','Dibuja una firma visual sin certificado digital.','forms','annotate'),
 entry('ocr','Reconocer texto (OCR)','Añade texto buscable a escaneados en español o inglés.','document','edit_copy','dialog','escáner escaneo digitalizar'),
 entry('export_images','Exportar páginas como imágenes','Descarga PNG o JPEG con resolución configurable.','document','copy'),
 entry('tables','Exportar tablas a CSV','Extrae tablas digitales a un ZIP de archivos CSV.','document','copy','dialog','excel hojas cálculo'),
 entry('docx','Exportar texto a Word','Crea un DOCX con texto, imágenes compatibles y tablas editables revisadas.','document','copy','dialog','word docx office texto editable conversión'),
 entry('export_text','Exportar texto','Descarga el texto del documento en TXT.','document','copy','text'),
 entry('portfolio','Portfolio PDF','Organiza adjuntos en una colección PDF nativa con títulos, descripciones y orden.','document','read','dialog','portfolio portafolio colección archivos paquete'),
 entry('attachments','Archivos adjuntos','Consulta y gestiona los archivos incrustados.','document','read'),
 entry('flow','Continuar texto entre regiones','Distribuye un texto entre bloques y áreas vacías de varias páginas.','edit','edit','dialog','reflujo párrafos continuar columnas flujo texto'),
 entry('form_rules','Cálculos automáticos del proyecto','Recalcula campos dependientes y conserva reglas en proyectos Reapdf.','forms','fill','dialog','fórmulas reglas dependencias automático suma promedio'),
 entry('calculate','Calcular valores de campos','Calcula sumas, productos y promedios en campos compatibles.','forms','fill','dialog','calculadora suma producto promedio mínimo máximo formularios'),
 entry('automation','Recetas de trabajo','Encadena tareas configurables sobre copias de varios PDF.','document','read','dialog','automatización recetas flujos procesos secuencias plantillas lotes'),
 entry('batch','Procesar varios PDF','Optimiza, extrae texto o protege copias de varios documentos.','document','read','dialog','lotes automatización masivo contraseñas compactar'),
 entry('bates','Numeración Bates por lotes','Numera consecutivamente varios PDF.','document'),
 entry('watermark','Marca de agua','Añade texto como marca de agua.','document'),
 entry('metadata','Propiedades del PDF','Edita metadatos del documento.','document'),
 entry('compress','Reducir imágenes del PDF','Reduce resolución y calidad de imágenes con comparación y copia revisada.','document','edit_copy','dialog','compresión comprimir dpi calidad tamaño peso jpeg'),
 entry('optimize','Optimizar PDF','Optimiza la estructura conservando imágenes originales.','document'),
 entry('protect','Proteger copia','Exporta una copia cifrada con contraseña y permisos.','document'),
 entry('redact','Censurar y sanear copia','Elimina contenido en regiones compatibles y sanea una copia.','document','edit_copy','dialog','redactar ocultar datos sensibles'),
];
export function normalizeQuery(value){return value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();}
export function searchTools(query,items=tools){const words=normalizeQuery(query).split(/\s+/).filter(Boolean);return items.filter(t=>words.every(w=>normalizeQuery(`${t.label} ${t.description} ${t.keywords} ${groups.find(g=>g[0]===t.group)?.[1]}`).includes(w)));}
export function unavailableReason(item,doc,state={}){
 if(!doc)return 'Abre un PDF para usar esta herramienta.';
 if(state.busy||state.transforming||state.stroke)return 'Espera a que termine la operación actual.';
 if(state.draft)return 'Aplica o cancela los cambios pendientes antes de cambiar de herramienta.';
 if(item.target==='tool'){
  if(state.loading&&item.permission==='annotate')return 'Espera a que se prepare la página.';
 }else{
  if(state.loading)return 'Espera a que se prepare la página.';
 }
 if(item.permission==='read')return '';
 if(doc.signed&&!['copy','sign'].includes(item.permission))return 'El documento firmado está disponible solo para lectura.';
 const allowed={sign:doc.can_edit&&doc.can_copy&&doc.can_fill,edit:doc.can_edit,annotate:doc.can_annotate,copy:doc.can_copy,fill:doc.can_fill,edit_copy:doc.can_edit&&doc.can_copy,organize:doc.can_organize,extract:doc.can_extract,organize_or_extract:doc.can_organize||doc.can_extract,duplicate:doc.can_organize&&doc.can_extract,blank:doc.can_organize};
 if(!allowed[item.permission])return 'Los permisos del PDF no permiten esta operación.';
 if(item.permission==='blank'&&doc.pages.length>=500)return 'Se alcanzó el límite de 500 páginas.';
 return '';
}
export function parsePageNumber(value,count){if(!/^\d+$/.test(value.trim()))return null;const n=Number(value);return Number.isSafeInteger(n)&&n>=1&&n<=count?n-1:null;}
