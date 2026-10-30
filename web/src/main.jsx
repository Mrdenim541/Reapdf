import React, { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import './workspace.css';
import './professional.css';
import {Icon} from './ui-icons.jsx';
import {AreaNavigation,ToolCatalog,CommandPalette,PageJump,WorkspaceHelp} from './workspace-tools.jsx';
import {areas,unavailableReason,areaChangeReason,tools as catalogTools} from './tool-catalog.js';
import {DocumentReview} from './document-review.jsx';
import { drawingTools, markupTools, toolNames, Shape, MarkTargets, ReviewTargets, NoteForm } from './annotations.jsx';
import { ExistingPanel, ExistingTargets } from './existing-annotations.jsx';
import {existingGeometry,importedPathOperation,mergeAnnotationChanges} from './existing-geometry.js';
import {LineEndpoints} from './line-endpoints.jsx';
import {MultiAnnotations} from './multi-annotations.jsx';
import {selectionBounds,translateSelection,groupOperation} from './multi-geometry.js';
import { TransformForm, TransformHandles } from './transformer.jsx';
import { usePagePreview } from './preview.jsx';
import { contentTools, ContentTargets, ContentForm, LinkLayer } from './content-tools.jsx';
import { ImageTargets, readImage } from './images.jsx';
import { ToolGuide } from './tool-guide.jsx';
import { selectMarkupWords, selectMarkupCharacters, transformMark } from './geometry.js';
import { BookmarkEditor } from './bookmarks.jsx';
import {FieldProperties} from './field-properties.jsx';
import {CommentsManager} from './comments.jsx';
import {DocxExport} from './docx-export.jsx';
import {BatchProcessor} from './batch-processor.jsx';
import {LinkEditor} from './link-editor.jsx';
import {FindReplace} from './find-replace.jsx';
import {RegionOCR} from './region-ocr.jsx';
import {TableRegions} from './table-regions.jsx';
import {StructureEditor,Preflight} from './structure-preflight.jsx';
import {Interchange,WorkingCopy} from './interchange.jsx';
import {Measurements} from './measurements.jsx';
import {DocumentLinks} from './document-links.jsx';
import {Layers} from './layers.jsx';
import {InlineTextEditor,visibleTextBox,visibleTextQuad} from './inline-text.jsx';
import {caretIndex} from './inline-caret.js';
import {InlineParagraph} from './inline-paragraph.jsx';
import { ParagraphEditor } from './paragraph-editor.jsx';
import { ExistingImageEditor } from './existing-images.jsx';
import { FieldDesigner } from './field-designer.jsx';
import { ComparisonDialog } from './comparison.jsx';
import { SignatureDialog } from './signature.jsx';
import { RedactionDialog } from './redaction.jsx';
import { ProTools, BatesDialog } from './pro-tools.jsx';
import { AdvancedTools, PasswordDialog } from './advanced-tools.jsx';
import { FormEditor } from './forms.jsx';
import { ImagePdfCreator, PageImageExporter } from './conversions.jsx';
import { HeaderFooterEditor } from './headers.jsx';
import { Organizer } from './organizer.jsx';
import { PageCreation } from './page-creation.jsx';
import { useRecovery, projectPayload } from './recovery.jsx';
import { Cropper, Splitter } from './page-tools.jsx';
import { Inserter } from './inserter.jsx';
import { DocumentSidebar, TextLayer, SearchHighlights, useDocumentSearch } from './viewer.jsx';

const StandardsDialog=lazy(()=>import('./standards.jsx').then(m=>({default:m.StandardsDialog})));
const AccessibilityDialog=lazy(()=>import('./standards.jsx').then(m=>({default:m.AccessibilityDialog})));
const CompressionDialog=lazy(()=>import('./compression.jsx').then(m=>({default:m.CompressionDialog})));
const DigitalSignatures=lazy(()=>import('./digital-signatures.jsx').then(m=>({default:m.DigitalSignatures})));
const WordImport=lazy(()=>import('./word-import.jsx').then(m=>({default:m.WordImport})));
const Portfolio=lazy(()=>import('./portfolio.jsx').then(m=>({default:m.Portfolio})));
const TextFlow=lazy(()=>import('./text-flow.jsx').then(m=>({default:m.TextFlow})));
const FormRules=lazy(()=>import('./form-rules.jsx').then(m=>({default:m.FormRules})));
const FormCalculations=lazy(()=>import('./form-calculations.jsx').then(m=>({default:m.FormCalculations})));
const Automation=lazy(()=>import('./automation.jsx').then(m=>({default:m.Automation})));
const loadingTool=<div className="tool-loading" role="status">Cargando herramienta…</div>;

async function checked(response) {
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { /* error no JSON */ }
    throw new Error(typeof detail === 'string' ? detail : 'No se pudo completar la operación.');
  }
  return response;
}
const post = (operations) => ({method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({operations})});

function App() {
  const [page, setPage] = useState(0);
  const [commandsOpen,setCommandsOpen]=useState(false),[helpOpen,setHelpOpen]=useState(false),[focusMode,setFocusMode]=useState(false);
  const pageJumpInput=useRef(null);
  const [area,setArea]=useState('read'),[navigationOpen,setNavigationOpen]=useState(true),[propertiesFolded,setPropertiesFolded]=useState(false);
  const [searchFocusRequest,setSearchFocusRequest]=useState(0);
  const [tool, setTool] = useState('view'), [zoom, setZoom] = useState(1);
  const [inlineSpan,setInlineSpan]=useState(null);
  const [inlineBlock,setInlineBlock]=useState(null),[flowStart,setFlowStart]=useState(null);
  const [textBoxMode,setTextBoxMode]=useState(false);
  const [linkWorkspace,setLinkWorkspace]=useState(null);
  const [color, setColor] = useState('#e34b40'), [width, setWidth] = useState(2);
  const [history, setHistory] = useState([{doc:null, operations:[]}]), [cursor, setCursor] = useState(0);
  const [spans, setSpans] = useState([]), [selected, setSelected] = useState(null), [text, setText] = useState('');
  const [textFont,setTextFont]=useState('helv'),[textSize,setTextSize]=useState(12),[textColor,setTextColor]=useState('#000000'),[textFonts,setTextFonts]=useState([]);
  const [existingDraft,setExistingDraft]=useState(false),[transformDraft,setTransformDraft]=useState(false);
  const [contentDraft,setContentDraft]=useState(null),[contentChanged,setContentChanged]=useState(false),[contentOutline,setContentOutline]=useState(null),[links,setLinks]=useState([]);
  const [contentLoading,setContentLoading]=useState(false);
  const [textItems, setTextItems] = useState([]), [words,setWords]=useState([]),[characters,setCharacters]=useState([]),[charactersTruncated,setCharactersTruncated]=useState(false),[markupMode,setMarkupMode]=useState('words');
  const [notePoint,setNotePoint]=useState(null), [noteContent,setNoteContent]=useState('');
  const [existingAnnotations,setExistingAnnotations]=useState([]),[selectedExisting,setSelectedExisting]=useState(null),[annotationsTruncated,setAnnotationsTruncated]=useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [stroke, setStroke] = useState(null), [selectedMark, setSelectedMark] = useState(null);
  const [transforming,setTransforming]=useState(false),[endpointMode,setEndpointMode]=useState(false),[multiMode,setMultiMode]=useState(false),[multiRefs,setMultiRefs]=useState([]),[multiDraft,setMultiDraft]=useState(false);
  const activePointer = useRef(null), sessionIds = useRef(new Set());
  const [organizerOpen, setOrganizerOpen] = useState(false), [inserterOpen,setInserterOpen] = useState(false);
  const [pageTool,setPageTool]=useState(null),[passwordFile,setPasswordFile]=useState(null);
  const paperScroll=useRef(null),paperElement=useRef(null),imageInput=useRef(null),projectInput=useRef(null),fileMenu=useRef(null);
  const fileInput = useRef(null), svg = useRef(null), strokeRef = useRef(null), saved = useRef('{"id":null,"operations":[]}'),projectSaved=useRef('');
  const {doc, operations} = history[cursor];
  const navigationDoc=useMemo(()=>{const index=operations.find(op=>op.type==='bookmarks');return doc&&index?{...doc,bookmarks:index.items.map(item=>({level:item.level,title:item.title,page:item.page})),bookmarks_truncated:false}:doc;},[doc,operations]);
  const fingerprint = JSON.stringify({id:doc?.id ?? null, operations});
  const dirty = fingerprint !== saved.current;
  const needsSave=dirty&&fingerprint!==projectSaved.current;
  const changeCount = (doc?.baseChanges || 0) + operations.length;
  const geometry = doc?.pages[page];
  const pagePreview=usePagePreview(doc,page,operations,zoom,setError);
  const preview=pagePreview.src,loading=pagePreview.loading||contentLoading;
  const currentText=selected&&operations.find(op=>op.type==='text'&&op.page===page&&op.span_id===selected.id);
  const originalTextColor=selected?'#'+selected.color.toString(16).padStart(6,'0'):'#000000';
  const appliedTextColor=currentText?.color?'#'+currentText.color.map(c=>Math.round(c*255).toString(16).padStart(2,'0')).join(''):originalTextColor;
  const textDraft=tool==='text'&&!!selected&&(text!==(currentText?.text??selected.text)||textFont!==(currentText?.font??selected.font_key)||textSize!==(currentText?.size??selected.size)||textColor!==appliedTextColor);
  const navigationGate=useRef(false);
  const navigatePage=useCallback(next=>{if(!navigationGate.current)setPage(next);},[]);
  const search = useDocumentSearch(doc, operations, navigatePage);
  const mayAnnotate = doc && !doc.signed && doc.can_annotate;
  const existingItems=useMemo(()=>existingAnnotations.map(item=>{
    const patch=operations.find(op=>op.type==='existing_annot'&&op.page===page&&op.xref===item.xref);
    return patch?.action==='delete'?null:existingGeometry(item,patch?.changes);
  }).filter(Boolean),[existingAnnotations,operations,page]);
  const multiItems=multiRefs.map(id=>existingItems.find(item=>item.xref===id&&item.visible&&item.editable&&item.can_move)).filter(Boolean);
  const activeExisting=existingItems.find(item=>item.xref===selectedExisting);
  const selectedOperation=operations.find(op=>op.id===selectedMark && op.page===page);
  const sessionMarks=operations.filter(op=>op.page===page&&op.id&&op.type!=='image'&&!contentTools.has(op.type));
  const contentItems=operations.filter(op=>op.page===page&&op.type===tool);
  const activeContent=contentDraft||(contentTools.has(tool)&&selectedOperation?.type===tool?selectedOperation:null);
  const sessionImages=operations.filter(op=>op.page===page&&op.type==='image');
  const noteEditDraft=tool==='select'&&selectedOperation?.type==='note'&&noteContent!==selectedOperation.content;
  const draftMessage=flowStart&&pageTool==='flow'?'Termina o cancela el flujo iniciado desde el párrafo antes de continuar.':inlineBlock?'Termina o cancela el párrafo sobre la página antes de continuar.':inlineSpan?'Termina o cancela la edición sobre la página antes de continuar.':(contentDraft||contentChanged)?'Hay contenido nuevo sin aplicar. Usa Aplicar o Cancelar contenido antes de exportar.':textDraft?'Hay texto sin aplicar. Pulsa Aplicar cambio o Cancelar antes de exportar.':
    (notePoint||noteEditDraft)?'Guarda la nota o cancela sus cambios antes de exportar.':
    multiDraft?'Aplica o cancela los cambios del grupo antes de continuar.':
    existingDraft?'Pulsa Aplicar propiedades existentes o cancela los cambios de la marca.':
    transformDraft?'Pulsa Aplicar posición y tamaño o cancela los valores pendientes.':'';
  navigationGate.current=busy||transforming||!!stroke||!!draftMessage;
  useEffect(()=>{window.__reapdfCloseState={dirty:!!(needsSave||draftMessage||linkWorkspace?.dirty),busy:!!(busy||transforming||stroke)};return()=>{delete window.__reapdfCloseState;};},[needsSave,draftMessage,busy,transforming,stroke,linkWorkspace?.dirty]);
  const mayEdit = doc && !doc.signed && doc.can_edit;
  const recovery=useRecovery(doc,operations,page,zoom);
  const commit = (ops) => {if (ops.length > 1000) {setError('El límite de esta sesión es 1000 cambios.'); return;} setSelectedMark(null);setHistory(h => [...h.slice(0, cursor + 1), {doc, operations:ops}]); setCursor(cursor + 1); setNotice('');};

  useEffect(() => {
    const handler = e => { if (needsSave || draftMessage || linkWorkspace?.dirty) {e.preventDefault(); e.returnValue = '';}};
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [needsSave, draftMessage,linkWorkspace?.dirty]);

  useEffect(() => {
    setMultiMode(false);setMultiRefs([]);setEndpointMode(false);setSelected(null); setSelectedMark(null); setSelectedExisting(null); setExistingAnnotations([]); setAnnotationsTruncated(false); setNotePoint(null); setContentDraft(null);setLinks([]);setSpans([]); setStroke(null); strokeRef.current = null; activePointer.current=null;
    if (!doc) return;
    const controller = new AbortController();
    fetch(`/api/documents/${doc.id}/pages/${page}`, {signal:controller.signal})
      .then(checked).then(r=>r.json()).then(r=>{if(!controller.signal.aborted){setSpans(r.spans);setTextFonts(r.text_fonts);setExistingAnnotations(r.annotations);setAnnotationsTruncated(r.annotations_truncated);}})
      .catch(e=>{if(e.name !== 'AbortError') setError(e.message);});
    return () => controller.abort();
  }, [doc, page]);

  useEffect(() => {
    if (!doc) return;
    const controller = new AbortController();
    setContentLoading(true);setTextItems([]);setWords([]);setCharacters([]);setCharactersTruncated(false);
    fetch(`/api/documents/${doc.id}/pages/${page}/text`,{...post(operations),signal:controller.signal})
      .then(checked).then(r=>r.json()).then(content=>{
        if(controller.signal.aborted)return;
        setTextItems(content.items);setWords(content.words);setCharacters(content.characters||[]);setCharactersTruncated(!!content.characters_truncated);setLinks(content.links||[]);setContentLoading(false);
      }).catch(e=>{if(e.name!=='AbortError'){setError(e.message);setContentLoading(false);}});
    return()=>controller.abort();
  }, [doc, page, operations]);

  const areaBlocked=areaChangeReason({busy,transforming,stroke,draft:draftMessage});
  const propertiesVisible=tool!=='view'&&tool!=='text'&&(tool!=='textbox'||!!activeContent||textBoxMode)&&!propertiesFolded;
  function changeArea(next){
    if(next===area||areaBlocked)return;
    setArea(next);setFocusMode(false);chooseTool('view');setPropertiesFolded(false);
  }
  const toolReason=item=>unavailableReason(item,doc,{busy,transforming,stroke,loading,draft:draftMessage});
  function runCatalogTool(item){
    if(toolReason(item))return;
    setError('');setArea(item.area);setFocusMode(false);setPropertiesFolded(false);
    if(item.target!=='tool')chooseTool('view');
    if(item.target==='tool')chooseTool(item.id);
    else if(item.target==='organizer')setOrganizerOpen(true);
    else if(item.target==='insert')setInserterOpen(true);
    else if(item.target==='replace')setInserterOpen('replace');
    else setPageTool(item.target==='text'?'text':item.id);
  }
  useEffect(()=>{
    const handler=e=>{
      // Native dialogs own the keyboard, including Escape and text editing.
      if(document.querySelector('dialog[open]')){if((e.ctrlKey||e.metaKey)&&['s','p','o','g','k','h'].includes(e.key.toLowerCase()))e.preventDefault();return;}
      if(e.key==='Escape'&&focusMode){setFocusMode(false);return;}
      if(!(e.ctrlKey||e.metaKey)||e.altKey)return;
      const key=e.key.toLowerCase();
      const editing=e.target instanceof HTMLElement&&(e.target.isContentEditable||!!e.target.closest('input,textarea,select'));
      const blocked=busy||transforming||!!stroke;
      if(key==='k'){e.preventDefault();if(!blocked)setCommandsOpen(true);}
      else if(key==='o'){e.preventDefault();if(!blocked)fileInput.current?.click();}
      else if(key==='s'){e.preventDefault();if(draftMessage){setError(draftMessage);return;}if(doc&&!blocked&&!loading){if(e.shiftKey)save();else saveProject();}}
      else if(key==='p'){e.preventDefault();if(draftMessage){setError(draftMessage);return;}if(doc&&!blocked&&!loading){if(doc.can_print)printDocument();else setError('El documento no permite la impresión disponible en esta versión.');}}
      else if(key==='g'){e.preventDefault();if(doc&&!blocked&&!draftMessage){pageJumpInput.current?.focus();pageJumpInput.current?.select();}}
      else if(key==='h'){e.preventDefault();if(doc&&!blocked&&!draftMessage&&!loading)setPageTool('find_replace');}
      else if(key==='f'){e.preventDefault();if(doc&&!blocked&&!draftMessage){setFocusMode(false);setNavigationOpen(true);setSearchFocusRequest(n=>n+1);}}
      else if((key==='z'||key==='y')&&!editing){e.preventDefault();if(!blocked&&!draftMessage){const next=cursor+(key==='y'||e.shiftKey?1:-1);if(next>=0&&next<history.length)restoreHistory(next);}}
    };
    window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler);
  });

  function adoptNewDocument(next,name) {
    setInlineSpan(null);setInlineBlock(null);setFlowStart(null);
    const previousIds=sessionIds.current;sessionIds.current=new Set([next.id]);
    saved.current=JSON.stringify({id:next.id,operations:[]});projectSaved.current='';
    setArea('read');setPropertiesFolded(false);setSearchFocusRequest(0);setHistory([{doc:{...next,name,nativeKey:next.id,baseChanges:0},operations:[]}]);setPage(0);setCursor(0);setTool('view');setPageTool(null);
    for(const id of previousIds)fetch(`/api/documents/${id}`,{method:'DELETE'}).catch(()=>{});
  }
  async function runAdvanced(action,params={}) {
    if(action==='watermark'){await applyDocumentTool('watermark',params.plan);return;}
    setBusy(true);setError('');
    try {
      let request={method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,...params})};
      if(action==='add-attachment'){const form=new FormData();form.append('file',params.file);form.append('operations',JSON.stringify(operations));request={method:'POST',body:form};}
      const r=await checked(await fetch(`/api/documents/${doc.id}/${action}`,request));
      if(['form-data','export-text','protect','export-tables'].includes(action)){
        download(await r.blob(),action==='export-tables'?'-tablas':action==='protect'?'-protegido':action==='form-data'?'-datos':'-texto',action==='export-tables'?'zip':action==='protect'?'pdf':action==='form-data'?'json':'txt');
        setNotice(action==='protect'?'Copia protegida preparada. La sesión y el proyecto no se han cifrado.':'Archivo preparado para descargar.');if(action!=='form-data')setPageTool(null);
      }else if(action==='calculate-fields'){const next=(await r.json()).operations;if(JSON.stringify(next)!==JSON.stringify(operations))commit(next);setPageTool(null);setNotice('Resultado calculado guardado como valor. Para actualizarlo, vuelve a calcular. Puedes deshacer.');}
      else if(action==='import-form-data'){commit((await r.json()).operations);setPageTool(null);setNotice('Datos verificados e importados. Puedes deshacer el cambio.');}
      else if(action==='ocr'){
        const result=await r.json();if(result.document)adoptVersion(result.document,`OCR aplicado a ${result.report.processed.length} páginas; ${result.report.skipped.length} omitidas con texto previo. Revisa los resultados.`,page);
        else {setPageTool(null);setNotice('No se añadió OCR: las páginas seleccionadas ya contienen texto digital.');}
      }else if(action==='optimize'){const result=await r.json();adoptVersion(result.document,`Optimización: ${result.report.before.toLocaleString()} → ${result.report.after.toLocaleString()} bytes (${result.report.saved.toLocaleString()} ahorrados).`,page);}
      else adoptVersion(await r.json(),action==='measure'?(params.id?'Vértices y valor de la medición actualizados. Puedes deshacer.':'Medición guardada con su etiqueta y escala. Puedes deshacer.'):action==='measurement-scale'?(params.remove?'Escala regional retirada; las mediciones anteriores conservan su calibración. Puedes deshacer.':'Escala regional guardada. Puedes deshacer.'):action==='delete-measurement'?'Medición y etiqueta retiradas. Puedes deshacer.':action==='configure-portfolio'?'Portfolio PDF actualizado. Puedes deshacer.':action==='prepare-accessibility'?'Título e idioma actualizados; el etiquetado no se modifica. Puedes deshacer.':action==='visual-signature'?'Firma visual incorporada; no contiene certificado digital. Puedes deshacer.':action==='labels'?'Etiquetas de página actualizadas. Puedes deshacer.':action==='add-attachment'?'Archivo adjuntado al PDF. Puedes deshacer.':action==='delete-attachment'?'Adjunto retirado del listado. Puedes deshacer.':action==='find-replace/apply'?'Reemplazos aplicados. Puedes deshacer el lote completo.':action==='replace-styled-text'?'Texto editado conservando la fuente, tamaño, color y posición de los fragmentos compatibles. Puedes deshacer.':action==='flow-text'?'Texto distribuido entre las regiones elegidas. Puedes deshacer el flujo completo.':action==='replace-paragraph'?'Bloque reemplazado con el formato elegido y fuente incrustada. Puedes deshacer.':action==='edit-field-properties'?'Propiedades del campo actualizadas, conservando sus valores. Puedes deshacer.':action==='edit-comment'?'Revisión incorporada al PDF. Puedes deshacer.':action==='edit-link'?'Enlace actualizado. Puedes deshacer.':action==='repair-calculation-order'?'Orden de cálculo corregido. Puedes revisar sus resultados o deshacer.':action==='edit-image'?'Imagen editada. Puedes deshacer para recuperar la versión anterior.':action==='create-field'?'Campo creado. Puedes rellenarlo, guardar proyecto o deshacer.':action==='delete-field'?'Campo eliminado. Puedes deshacer.':action==='flatten-form'?'Campos aplanados conservando su apariencia. Puedes deshacer para recuperar su edición.':'Propiedades actualizadas. Puedes deshacer el cambio.',page);
      return true;
    }catch(e){setError(e.message);return false;}finally{setBusy(false);}
  }
  async function createImagePdf(plan) {
    if((needsSave||draftMessage)&&!window.confirm('Crear otro documento descartará la sesión abierta. Guarda un proyecto o exporta antes de continuar. ¿Continuar?'))return;
    setBusy(true);setError('');
    try {
      if(!doc&&(await recovery.initialInfo())?.available&&!window.confirm('Crear este PDF reemplazará la recuperación automática existente. ¿Continuar?'))return;
      const form=new FormData();for(const file of plan.files)form.append('files',file);
      form.append('paper',plan.paper);form.append('dpi',plan.dpi);form.append('margin',plan.margin);
      const response=await checked(await fetch('/api/create/images',{method:'POST',body:form}));
      adoptNewDocument(await response.json(),'Imágenes.pdf');setNotice('PDF creado. Exporta una copia o guarda un proyecto para conservarlo.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function exportImages(plan) {
    setBusy(true);setError('');try{
      const response=await checked(await fetch(`/api/documents/${doc.id}/export-images`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,...plan})}));
      download(await response.blob(),'-imagenes','zip');setPageTool(null);setNotice('ZIP preparado con las imágenes de las páginas seleccionadas.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function openFile(file,password='',confirmed=false) {
    if (!file||busy) return;
    if (!confirmed&&(needsSave||draftMessage) && !window.confirm('Hay cambios sin exportar o aplicar. ¿Quieres abrir otro documento y descartarlos?')) return;
    setBusy(true); setError(''); setNotice('');
    try {
      if(!confirmed&&!doc&&(await recovery.initialInfo())?.available&&!window.confirm('Hay una sesión recuperable. Abrir este PDF reemplazará su recuperación automática. ¿Continuar?'))return;
      const form = new FormData(); form.append('file', file);if(password)form.append('password',password);
      const raw=await fetch('/api/documents',{method:'POST',body:form});
      if(raw.status===401){const message=(await raw.json()).detail;setPasswordFile(file);setPageTool('unlock');setError(password?message:'');return;}
      const response=await checked(raw);
      const next = await response.json();
      adoptNewDocument(next,file.name);setPasswordFile(null);if(next.opened_encrypted)setNotice('Copia descifrada abierta. Proyecto y recuperación no conservan el cifrado del original.');
    } catch(e) {setError(e.message);} finally {setBusy(false); if(fileInput.current) fileInput.current.value='';}
  }
  function closeFileMenu() {if(fileMenu.current)fileMenu.current.open=false;}
  async function saveProject() {
    closeFileMenu();setBusy(true);setError('');
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/project`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(projectPayload(doc,operations,page,zoom))}));
      if(window.reapdfDesktop){if(await nativeSave(await response.blob(),'-proyecto','reapdf',false)){projectSaved.current=fingerprint;setNotice('Proyecto guardado.');}else setNotice('Guardado cancelado; los cambios siguen pendientes.');return;}
      download(await response.blob(),'-proyecto','reapdf');projectSaved.current=fingerprint;setNotice('Proyecto preparado para descargar. Conserva el PDF base y los cambios aplicados; no incluye borradores ni el historial anterior.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  function adoptProject(restored,fromRecovery=false) {
    const next=restored.document,state=restored.state,previous=sessionIds.current;
    sessionIds.current=new Set([next.id]);saved.current='';projectSaved.current=fromRecovery?'':JSON.stringify({id:next.id,operations:restored.operations});
    setHistory([{doc:{...next,name:state.name,nativeKey:next.id,baseChanges:state.base_changes},operations:restored.operations}]);
    setCursor(0);setPage(state.page);setZoom(state.zoom);setTool('view');setSelected(null);setSelectedMark(null);setNotePoint(null);
    setOrganizerOpen(false);setInserterOpen(false);setPageTool(null);
    for(const id of previous)fetch(`/api/documents/${id}`,{method:'DELETE'}).catch(()=>{});
    setNotice('Sesión restaurada con sus cambios aplicados. Puedes continuar editando y exportar una copia. El historial comienza aquí.');
  }
  async function openProject(file) {
    closeFileMenu();if(!file)return;
    if((needsSave||draftMessage)&&!window.confirm('Hay cambios sin exportar o aplicar. ¿Quieres abrir el proyecto y descartarlos?'))return;
    setBusy(true);setError('');
    try {
      if(!doc&&(await recovery.initialInfo())?.available&&!window.confirm('Abrir este proyecto reemplazará la recuperación automática existente. ¿Continuar?'))return;
      const form=new FormData();form.append('file',file);
      const response=await checked(await fetch('/api/projects/open',{method:'POST',body:form}));
      adoptProject(await response.json());
    }catch(e){setError(e.message);}finally{setBusy(false);if(projectInput.current)projectInput.current.value='';}
  }
  async function restoreRecovery() {
    setBusy(true);setError('');
    try {
      const response=await checked(await fetch('/api/recovery/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:recovery.revision()})}));
      adoptProject(await response.json(),true);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function discardRecovery() {
    if(!window.confirm('¿Descartar la recuperación local? Tus PDF y archivos de proyecto guardados se conservan.'))return;
    setBusy(true);setError('');try{await recovery.discard();}catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function printDocument() {
    closeFileMenu();
    if(window.reapdfDesktop){
      setBusy(true);setError('');
      try{
        const response=await checked(await fetch(`/api/documents/${doc.id}/print`,post(operations)));
        const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;response.blob().then(blob=>reader.readAsDataURL(blob)).catch(reject);});
        const bridge=await window.reapdfDesktop,result=await new Promise(resolve=>bridge.printPdf(data,resolve));
        if(result.startsWith('error:'))throw new Error(result.slice(6));
        setNotice(result==='cancelled'?'Impresión cancelada.':'Documento enviado a impresión.');
      }catch(e){setError(e.message);}finally{setBusy(false);}
      return;
    }
    // Abrir dentro del gesto del usuario evita bloquear la ventana al esperar al motor.
    const target=window.open('','_blank');
    if(!target){setError('El navegador bloqueó la vista de impresión. Permite ventanas para esta aplicación o exporta el PDF e imprímelo desde tu lector.');return;}
    target.opener=null;target.document.title='Preparando impresión — Reapdf';target.document.body.textContent='Preparando el PDF con tus cambios aplicados…';
    setBusy(true);setError('');
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/print`,post(operations)));
      const url=URL.createObjectURL(await response.blob());target.location.replace(url);
      setTimeout(()=>URL.revokeObjectURL(url),600000);
      setNotice('Vista de impresión abierta con los cambios aplicados. Usa Imprimir o Ctrl+P en el lector PDF de esa ventana.');
    }catch(e){target.close();setError(e.message);}finally{setBusy(false);}
  }
  useEffect(()=>{const print=()=>{if(!doc)return;if(busy||transforming||draftMessage||document.querySelector('dialog[open]')){setError('Termina o cancela la edición actual antes de imprimir.');return;}if(!doc.can_print){setError('El documento no permite impresión.');return;}printDocument();};window.addEventListener('reapdf-print',print);return()=>window.removeEventListener('reapdf-print',print);},[doc,operations,busy,transforming,draftMessage]);
  async function createPages(plan) {
    setBusy(true);setError('');
    const mode=pageTool;
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/${mode}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,...plan})}));
      adoptVersion(await response.json(),mode==='blank'?'Páginas en blanco insertadas. Puedes deshacer la operación.':'Páginas duplicadas con los cambios aplicados. Puedes deshacer la operación.',plan.position);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  const [textRegion,setTextRegion]=useState(null);
  useEffect(()=>{if(pageTool!=='paragraph')setTextRegion(null);},[pageTool]);
  function editBlock(span){
    const g=doc.pages[page],x=Math.max(0,span.bbox[0]-2),y=Math.max(0,span.bbox[1]-2);
    setTextRegion([x,y,Math.min(g.width,span.bbox[2]+2)-x,Math.min(g.height,span.bbox[3]+2)-y]);setPageTool('paragraph');
  }
  function selectText(span) {
    const previous=operations.find(o=>o.type==='text'&&o.page===page&&o.span_id===span.id);
    setSelected(span);setText(previous?.text??span.text);setTextFont(previous?.font??span.font_key);
    setTextSize(previous?.size??span.size);
    setTextColor(previous?.color?'#'+previous.color.map(c=>Math.round(c*255).toString(16).padStart(2,'0')).join(''):'#'+span.color.toString(16).padStart(6,'0'));
  }
  async function applyText(e) {
    e.preventDefault(); setBusy(true); setError('');
    const next = [...operations.filter(o=>!(o.type==='text' && o.page===page && o.span_id===selected.id)),
      {type:'text', page, span_id:selected.id, text, font:textFont, size:textSize, color:[1,3,5].map(i=>parseInt(textColor.slice(i,i+2),16)/255)}];
    try {
      // Validar la transformación real antes de incorporarla al historial.
      await checked(await fetch(`/api/documents/${doc.id}/export`, post(next)));
      commit(next); setSelected(null);
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function nativeSave(blob,suffix,extension,saveAs){
    const encoded=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(new Error('No se pudo preparar el archivo.'));r.readAsDataURL(blob);});
    const bridge=await window.reapdfDesktop,name=doc.name.replace(/\.pdf$/i,'')+suffix+'.'+extension;
    const result=JSON.parse(await new Promise(resolve=>bridge.saveFile(encoded,name,doc.nativeKey||doc.id,saveAs!==false,resolve)));
    if(result.conflict||result.status==='error'){saved.current='';projectSaved.current='';}
    if(result.status==='error')throw new Error(result.message);
    return result.status==='saved';
  }
  useEffect(()=>{const guard=action=>()=>{if(!doc)return;if(busy||transforming||draftMessage||document.querySelector('dialog[open]')){setError('Termina o cancela la edición actual antes de guardar.');return;}action();};const saveCurrent=guard(()=>save(false)),saveAs=guard(()=>save(true));window.addEventListener('reapdf-save',saveCurrent);window.addEventListener('reapdf-save-as',saveAs);return()=>{window.removeEventListener('reapdf-save',saveCurrent);window.removeEventListener('reapdf-save-as',saveAs);};},[doc,operations,busy,transforming,draftMessage]);
  async function save(saveAs=true) {
    setBusy(true); setError('');
    try {
      const r=await checked(await fetch(`/api/documents/${doc.id}/export`,post(operations)));
      if(window.reapdfDesktop){if(await nativeSave(await r.blob(),'-editado','pdf',saveAs)){saved.current=fingerprint;setNotice('PDF guardado.');}else setNotice('Guardado cancelado; los cambios siguen pendientes.');return;}
      const url=URL.createObjectURL(await r.blob()); const a=document.createElement('a');
      a.href=url; a.download=doc.name.replace(/\.pdf$/i,'')+'-editado.pdf'; a.click();
      setTimeout(()=>URL.revokeObjectURL(url),10000);
      saved.current=fingerprint; setNotice('Copia preparada para descargar. El original se conserva.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  function restoreHistory(index) {
    const target=history[index];
    const keepPath=target.doc.id===doc.id&&activeExisting?.path_rect&&!target.operations.some(op=>op.type==='existing_annot'&&op.page===page&&op.xref===selectedExisting&&op.action==='delete');
    if(target.doc.id!==doc.id) {setMultiMode(false);setMultiRefs([]);setEndpointMode(false);setPage(Math.min(page,target.doc.pages.length-1));setTool('view');}
    setContentDraft(null);setContentChanged(false);setCursor(index); setSelected(null); setSelectedMark(null); setSelectedExisting(keepPath?selectedExisting:null); setNotice(''); setError('');
  }
  function download(blob, suffix, extension='pdf') {
    const url=URL.createObjectURL(blob); const link=document.createElement('a');
    link.href=url; link.download=doc.name.replace(/\.pdf$/i,'')+suffix+'.'+extension; link.click();
    setTimeout(()=>URL.revokeObjectURL(url),10000);
  }
  function adoptVersion(next, message, focus = 0) {
    setFlowStart(null);
    sessionIds.current.add(next.id);
    const {project_operations=[],...version}=next;
    setHistory(h=>[...h.slice(0,cursor+1),{doc:{...version,name:next.working_copy?doc.name.replace(/\.pdf$/i,'')+'-copia-trabajo.pdf':doc.name,nativeKey:next.working_copy?next.id:doc.nativeKey||doc.id,baseChanges:changeCount+1},operations:project_operations}]);
    setCursor(cursor+1);setPage(focus);setTool('view');setOrganizerOpen(false);setInserterOpen(false);setPageTool(null);setNotice(message+(next.project_operations?.length?' Los cálculos automáticos siguen activos.':''));
  }
  async function insertPages(plan) {
    setBusy(true);setError('');
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/${plan.replace_count?'replace':'insert'}`,{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,...plan}),
      }));
      adoptVersion(await response.json(),plan.replace_count?'Páginas reemplazadas. Puedes deshacer la operación o exportar una copia.':'Páginas insertadas. Puedes deshacer la operación o exportar una copia.',plan.position);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function cropPages(plan) {
    setBusy(true);setError('');
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/crop`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,...plan})}));
      adoptVersion(await response.json(),plan.reset?'Límites originales restaurados. Puedes deshacer la operación.':'Recorte aplicado. El contenido de los márgenes permanece en el PDF; puedes deshacer.',page);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function splitPages(plan) {
    setBusy(true);setError('');
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/split`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,...plan})}));
      download(await response.blob(),'-partes','zip');return true;
    }catch(e){setError(e.message);return false;}finally{setBusy(false);}
  }
  async function organizePages(pages) {
    setBusy(true); setError('');
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/organize`, {
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,pages}),
      }));
      const next=await response.json();
      adoptVersion(next,'Organización aplicada. Puedes deshacerla o exportar una copia.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function extractPages(pages) {
    setBusy(true); setError('');
    try {
      const response=await checked(await fetch(`/api/documents/${doc.id}/extract`, {
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,pages}),
      }));
      download(await response.blob(),'-extraido'); return true;
    }catch(e){setError(e.message);return false;}finally{setBusy(false);}
  }
  function point(e) {
    const rect=svg.current.getBoundingClientRect();
    return [Math.max(0,Math.min(geometry.width,(e.clientX-rect.left)/rect.width*geometry.width)),
      Math.max(0,Math.min(geometry.height,(e.clientY-rect.top)/rect.height*geometry.height))];
  }
  function changeZoom(value) {
    const next=Math.max(.05,Math.min(4,Math.round(value*100)/100));
    const scroll=paperScroll.current,paper=paperElement.current;
    let anchor;
    if(scroll&&paper){const a=scroll.getBoundingClientRect(),b=paper.getBoundingClientRect();anchor=[Math.max(0,Math.min(geometry.width,(a.left+a.width/2-b.left)/zoom)),Math.max(0,Math.min(geometry.height,(a.top+a.height/2-b.top)/zoom))];}
    setZoom(next);
    if(anchor)requestAnimationFrame(()=>{const a=scroll.getBoundingClientRect(),b=paper.getBoundingClientRect();scroll.scrollLeft+=b.left+anchor[0]*next-a.left-a.width/2;scroll.scrollTop+=b.top+anchor[1]*next-a.top-a.height/2;});
  }
  function fitPage(mode) {
    const scroll=paperScroll.current;if(!scroll||!geometry)return;
    const width=(scroll.clientWidth-48)/geometry.width,height=(scroll.clientHeight-48)/geometry.height;
    changeZoom(Math.floor((mode==='width'?width:Math.min(width,height))*100)/100);
  }
  function chooseTool(next) {
    setMultiMode(false);setMultiRefs([]);setEndpointMode(false);setTool(next); setSelected(null); setSelectedMark(null); setSelectedExisting(null); setNotePoint(null);setContentDraft(null);setContentChanged(false);
    if(next==='highlight'||next==='note')setColor('#f5cf28');
  }
  function deleteMark(id) {
    commit(operations.filter(op => op.id !== id));
  }
  function selectMark(id) {
    if(multiDraft){setError('Aplica o cancela los cambios del grupo antes de seleccionar otra marca.');return;}
    setMultiMode(false);setMultiRefs([]);setEndpointMode(false);setSelectedMark(id); setSelectedExisting(null); setNoteContent(operations.find(op=>op.id===id)?.content || '');
  }
  function selectExisting(xref,extend=false) {
    if(busy||loading||transforming||existingDraft||multiDraft)return;
    if(extend||multiMode){
      const item=existingItems.find(a=>a.xref===xref);
      if(!item?.can_move||!item?.editable||!item?.visible){setNotice('Esta marca no admite selección múltiple para mover.');return;}
      setMultiMode(true);setSelectedExisting(null);setSelectedMark(null);setEndpointMode(false);
      setMultiRefs(current=>{const ids=multiMode?current:selectedExisting?[selectedExisting]:[];return ids.includes(xref)?ids.filter(id=>id!==xref):ids.length<50?[...ids,xref]:ids;});return;
    }
    if(xref!==selectedExisting)setEndpointMode(false);
    setSelectedExisting(xref);setSelectedMark(null);
  }
  async function changeExisting(xref,changes,remove=false) {
    if(busy||loading||!mayAnnotate)return;
    setBusy(true);setError('');
    try {
      const previous=operations.find(op=>op.type==='existing_annot'&&op.page===page&&op.xref===xref);
      const patch=remove?{type:'existing_annot',page,xref,action:'delete'}:
        {type:'existing_annot',page,xref,action:'update',changes:mergeAnnotationChanges(previous?.changes,changes,existingItems.find(a=>a.xref===xref))};
      const next=[...operations.filter(op=>!(op.type==='existing_annot'&&op.page===page&&op.xref===xref)),patch];
      await checked(await fetch(`/api/documents/${doc.id}/export`,post(next)));
      commit(next);setSelectedExisting(remove?null:xref);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function changeExistingBatch(patches) {
    if(busy||loading||!mayAnnotate)return false;
    if(!patches.length||patches.length>50||new Set(patches.map(p=>p.xref)).size!==patches.length){setError('Elige entre 1 y 50 marcas distintas.');return false;}
    patches=patches.filter(p=>p.remove||Object.entries(p.changes||{}).some(([key,value])=>JSON.stringify(value)!==JSON.stringify(existingItems.find(a=>a.xref===p.xref)?.[key])));
    if(!patches.length)return true;
    setBusy(true);setError('');
    try{
      const ids=new Set(patches.map(p=>p.xref));
      const updated=patches.map(p=>{
        const previous=operations.find(op=>op.type==='existing_annot'&&op.page===page&&op.xref===p.xref);
        if(p.remove)return {type:'existing_annot',page,xref:p.xref,action:'delete'};
        return {type:'existing_annot',page,xref:p.xref,action:'update',changes:mergeAnnotationChanges(previous?.changes,p.changes,existingItems.find(a=>a.xref===p.xref))};
      });
      const next=[...operations.filter(op=>!(op.type==='existing_annot'&&op.page===page&&ids.has(op.xref))),...updated];
      if(next.length>1000)throw new Error('El límite de esta sesión es 1000 cambios.');
      await checked(await fetch(`/api/documents/${doc.id}/export`,post(next)));commit(next);return true;
    }catch(e){setError(e.message);return false;}finally{setBusy(false);}
  }
  async function applyTransform(target) {
    if(!selectedOperation||busy||loading||!((['image','textbox','link'].includes(selectedOperation.type))?mayEdit:mayAnnotate))return;
    setError('');
    try {
      const nextOp=transformMark(selectedOperation,target,geometry);
      if(JSON.stringify(nextOp)===JSON.stringify(selectedOperation))return;
      const next=operations.map(op=>op.id===nextOp.id?nextOp:op);
      setBusy(true);
      await checked(await fetch(`/api/documents/${doc.id}/export`,post(next)));
      commit(next);setSelectedMark(nextOp.id);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function applyContent(op) {
    if(busy||loading)return;
    setBusy(true);setError('');
    try {
      const next=[...operations.filter(item=>item.id!==op.id),op];
      await checked(await fetch(`/api/documents/${doc.id}/export`,post(next)));
      commit(next);setContentDraft(null);setContentChanged(false);setSelectedMark(op.id);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  function beginContent() {
    setSelectedMark(null);setContentChanged(false);setContentDraft(null);
    setNotice('Arrastra un rectángulo en la página para definir el área.');
  }
  async function applyDocumentTool(kind,plan) {
    setBusy(true);setError('');
    try {
      const next=[...operations.filter(op=>kind==='form_fill'?!['form_fill','form_recalculate'].includes(op.type):op.type!==kind),...(plan?[plan]:[])];
      await checked(await fetch(`/api/documents/${doc.id}/export`,post(next)));
      commit(next);setPageTool(null);setNotice(kind==='form_rules'?'Reglas actualizadas. Se recalculan en Reapdf y se conservan en el proyecto; el PDF exportado guarda valores.':kind==='watermark'?'Marca de agua actualizada. Puedes corregirla o deshacer.':kind==='form_fill'?'Formulario aplicado. Los valores se conservan en el PDF y el proyecto.':kind==='bookmarks'?'Índice aplicado. Puedes navegar por sus destinos y deshacer el cambio.':plan?'Encabezados y pies aplicados. Puedes corregir esta configuración o deshacer.':'Configuración de encabezados y pies retirada.');
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function insertImage(file) {
    if(!file||!mayEdit||busy)return;
    setBusy(true);setError('');
    try {
      const image=await readImage(file);
      const ratio=Math.min(geometry.width*.6/image.pixels[0],geometry.height*.6/image.pixels[1],1);
      const w=Math.max(1,image.pixels[0]*ratio),h=Math.max(1,image.pixels[1]*ratio);
      const x=(geometry.width-w)/2,y=(geometry.height-h)/2;
      const op={...image,type:'image',id:crypto.randomUUID(),page,points:[[x,y],[x+w,y+h]]};
      const next=[...operations,op];
      await checked(await fetch(`/api/documents/${doc.id}/export`,post(next)));
      commit(next);setSelectedMark(op.id);setNotice('Imagen insertada. Usa el marco azul para moverla y la esquina para cambiar su tamaño.');
    }catch(e){setError(e.message);}finally{setBusy(false);if(imageInput.current)imageInput.current.value='';}
  }
  async function saveNote(e) {
    e.preventDefault(); setBusy(true);setError('');
    const existing=operations.find(op=>op.id===selectedMark && op.type==='note');
    const op=existing ? {...existing,content:noteContent} : {id:crypto.randomUUID(),type:'note',page,point:notePoint,
      content:noteContent,color:[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255)};
    const next=[...operations.filter(item=>item.id!==op.id),op];
    try {await checked(await fetch(`/api/documents/${doc.id}/export`,post(next)));commit(next);setNotePoint(null);setNoteContent('');}
    catch(e){setError(e.message);}finally{setBusy(false);}
  }
  function start(e) {
    if(tool==='textbox'&&!textBoxMode&&!inlineSpan&&!activeContent&&preview&&!busy&&!loading&&e.button===0&&mayEdit&&e.target===svg.current){const p=point(e);e.preventDefault();setError('');setInlineSpan({id:crypto.randomUUID(),insert:true,text:'',bbox:[p[0],p[1],p[0]+200,p[1]+24],origin:p,size:14,color:0});return;}
    if(tool==='textbox'&&((!textBoxMode&&!activeContent)||inlineSpan))return;
    if(tool==='note'&&preview&&!busy&&!loading&&e.button===0&&mayAnnotate) {setNotePoint(point(e));setNoteContent('');return;}
    if((!drawingTools.has(tool)&&!markupTools.has(tool)&&!contentTools.has(tool))||!preview||busy||transforming||loading||e.button!==0||!(contentTools.has(tool)&&tool!=='stamp'?mayEdit:mayAnnotate)||activePointer.current!==null)return;
    activePointer.current=e.pointerId;
    e.preventDefault(); e.currentTarget.setPointerCapture(e.pointerId);
    strokeRef.current=[point(e)]; setStroke(strokeRef.current);
  }
  function move(e) {
    if(!strokeRef.current||activePointer.current!==e.pointerId)return;
    if(strokeRef.current.length>=10000)return;
    strokeRef.current=tool==='ink' ? [...strokeRef.current,point(e)] : [strokeRef.current[0],point(e)];
    setStroke(strokeRef.current);
  }
  function end(e) {
    if(activePointer.current!==e.pointerId)return;
    const pts=strokeRef.current; strokeRef.current=null; activePointer.current=null; setStroke(null);
    const enoughSize=pts?.length>1 && (tool==='rectangle'
      ? [0,1].every(i=>Math.abs(pts[0][i]-pts.at(-1)[i])>=1)
      : Math.hypot(pts[0][0]-pts.at(-1)[0],pts[0][1]-pts.at(-1)[1])>=1 || tool==='ink');
    if(contentTools.has(tool)&&pts?.length>1) {
      const a=pts[0],b=pts.at(-1),points=[[Math.min(a[0],b[0]),Math.min(a[1],b[1])],[Math.max(a[0],b[0]),Math.max(a[1],b[1])]];
      if(points[1][0]-points[0][0]<5||points[1][1]-points[0][1]<5)setError('Arrastra una caja de al menos 5 × 5 puntos.');
      else {setSelectedMark(null);setContentDraft({id:crypto.randomUUID(),type:tool,page,points,text:'',font:'helv',size:14,align:0,color:[0,0,0],stamp:'approved',destination:'web',url:'https://',target_page:page});setNotice('Área preparada. Completa las propiedades y pulsa Aplicar.');}
    }
    else if(markupTools.has(tool) && pts?.length) {
      const selectedWords=markupMode==='characters'?selectMarkupCharacters(characters,pts[0],pts.at(-1)):selectMarkupWords(words,pts[0],pts.at(-1));
      if(selectedWords.length>500)setError('Selecciona un máximo de 500 fragmentos por marca.');
      else if(selectedWords.length)commit([...operations,{id:crypto.randomUUID(),type:tool,page,quads:selectedWords.map(w=>w.quad),color:[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255)}]);
      else setNotice('No hay texto seleccionable en esa zona. Haz clic o arrastra sobre texto digital; los escaneados requieren OCR.');
    }
    else if(enoughSize)commit([...operations,{id:crypto.randomUUID(),type:tool,page,points:pts,width,color:[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255)}]);
    if(e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  }
  return <div className={`app${focusMode?' reading-focus':''}`}>
    <header><div className="brand"><span className="brand-icon">R</span> reapdf <span className="badge">0.41 · DESARROLLO</span></div>
      <div className="header-actions"><button className="help-button" onClick={()=>setHelpOpen(true)} disabled={busy||transforming}>Guía y atajos</button><span className="local-status"><span className="local-dot">●</span>Procesamiento local</span><details ref={fileMenu} className="file-menu"><summary>Archivo</summary><div>
        <button disabled={busy||transforming} onClick={()=>{closeFileMenu();projectInput.current.click();}}>Abrir proyecto…</button>
        <button disabled={!doc||busy||transforming||!!draftMessage||loading} onClick={saveProject}>Guardar proyecto</button>
        {doc&&(<button disabled={busy||transforming||!!stroke||!!draftMessage} onClick={()=>{closeFileMenu();setError('');setPageTool('create_images');}}>Crear PDF desde imágenes</button>)}
        <button disabled={busy||transforming||!!stroke||!!draftMessage} onClick={()=>{closeFileMenu();setPageTool('import_word');}}>Crear PDF desde Word</button>
        <button disabled={!doc||!doc.can_print||busy||transforming||!!draftMessage||loading} onClick={printDocument}>Imprimir…</button>
      </div></details><button onClick={()=>fileInput.current.click()} disabled={busy||transforming}>Abrir PDF</button><button className="primary" title={draftMessage?'Aplica o cancela los cambios pendientes antes de exportar':'Descargar PDF con los cambios aplicados'} disabled={!doc||busy||transforming||loading||!!draftMessage} onClick={save}>Exportar copia</button></div>
      <input ref={projectInput} aria-label="Archivo de proyecto" type="file" accept=".reapdf,application/zip" hidden onChange={e=>openProject(e.target.files[0])}/>
      <input ref={fileInput} aria-label="Archivo PDF" type="file" accept=".pdf,application/pdf" hidden onChange={e=>openFile(e.target.files[0])}/>
    </header>
    <div className="document-bar"><span>{doc ? doc.name : 'Tu espacio de trabajo PDF'}</span><span>{doc ? `${changeCount} cambios${dirty?' · sin exportar':''}` : 'Edición · organización · formularios · OCR'}</span></div>
    {doc&&<div className="session-bar"><span role="status">{recovery.status}</span>{recovery.error&&<button disabled={busy} onClick={recovery.refresh}>Reintentar recuperación</button>}<button disabled={busy||transforming||!!draftMessage||loading} onClick={saveProject}>Guardar proyecto</button></div>}
    {!doc&&(recovery.info?.available||recovery.info?.error)&&<div className="recovery-card"><div><strong>{recovery.info.available?'Hay una sesión recuperable':'No se pudo validar la recuperación'}</strong><p>{recovery.info.error||`${recovery.info.state.name} · ${new Date(recovery.info.saved_at).toLocaleString()}`}</p></div>{recovery.info.available&&<button className="primary" disabled={busy} onClick={restoreRecovery}>Recuperar sesión</button>}<button disabled={busy} onClick={discardRecovery}>Descartar recuperación</button></div>}
    {recovery.error&&<div className="banner error" role="alert">{recovery.error} Guarda un proyecto o exporta una copia para conservar tu trabajo.</div>}
    {error && <div className="banner error" role="alert">{error}<button aria-label="Cerrar error" onClick={()=>setError('')}>×</button></div>}
    {notice && <div className="banner" role="status">{notice}</div>}
    {operations.some(op=>op.type==='form_rules')&&<div className="banner">Cálculos automáticos activos en este proyecto. Se conservan en las operaciones compatibles de páginas y campos; se protegen sus dependencias. Otras transformaciones conservan valores: Deshacer recupera las reglas.</div>}
    {doc?.signed && <div className="banner">Documento con indicadores de firma: lectura y verificación disponibles. Puedes añadir una firma compatible en una copia; las demás ediciones están protegidas.</div>}
    {!doc ? <main className="welcome">
      <div className="eyebrow">UN NUEVO ESPACIO PARA TUS DOCUMENTOS</div><h1>Tu PDF.<br/><span>Con tus cambios.</span></h1>
      <p>Lee, corrige, organiza y prepara tus documentos en un espacio de trabajo local. Encuentra cada herramienta por su nombre o por lo que necesitas hacer.</p>
      <div className="welcome-actions"><button className="primary large" onClick={()=>fileInput.current.click()} disabled={busy||transforming}>{busy?'Abriendo…':'Seleccionar un PDF'}</button><button disabled={busy||transforming} onClick={()=>{setError('');setPageTool('create_images');}}>Crear PDF desde imágenes</button></div>
      <button disabled={busy||transforming} onClick={()=>setPageTool('import_word')}>Crear PDF desde Word</button>
      <div className="limits">Hasta 30 MB · 500 páginas · Sin envío a servicios externos</div>
      <div className="cards"><article><b>01 / Leer</b><h3>Encuentra tu página</h3><p>Miniaturas, índice, búsqueda y revisión de la estructura del documento.</p></article><article><b>02 / Marcar</b><h3>Deja tu trazo</h3><p>Anotaciones, notas, trazos, formularios y firma visual, con cambios reversibles.</p></article><article><b>03 / Editar</b><h3>Cambia el contenido</h3><p>Texto e imágenes compatibles, OCR local, organización y exportación de copias.</p></article></div>
      <div className="prototype">Versión en desarrollo. La edición depende de la estructura y fuentes del PDF. Incluye OCR local en español e inglés; las firmas visuales y las firmas con certificado tienen asistentes separados. Consulta la guía para conocer los flujos y límites.</div>
    </main> : <><div className="workspace-bar"><AreaNavigation area={area} blocked={areaBlocked} onChange={changeArea}/><div className="panel-controls"><button aria-expanded={navigationOpen&&!focusMode} aria-controls="document-navigation" disabled={busy||transforming||!!stroke} onClick={()=>{setFocusMode(false);setNavigationOpen(focusMode?true:!navigationOpen);}}>{navigationOpen&&!focusMode?'Ocultar navegación':'Mostrar navegación'}</button>{tool!=='view'&&tool!=='text'&&tool!=='textbox'&&<button aria-expanded={propertiesVisible&&!focusMode} aria-controls="tool-properties" disabled={!!areaBlocked} title={areaBlocked||'Mostrar u ocultar las propiedades de la herramienta'} onClick={()=>{setFocusMode(false);setPropertiesFolded(focusMode?false:!propertiesFolded);}}>{propertiesVisible&&!focusMode?'Ocultar propiedades':'Mostrar propiedades'}</button>}</div></div><div className={`workspace${!navigationOpen?' navigation-closed':''}${!propertiesVisible?' properties-closed':''}`}>

      <aside className="tools" aria-label="Herramientas PDF">
        <ToolCatalog area={area} active={tool} reason={toolReason} onRun={runCatalogTool} onCommands={()=>setCommandsOpen(true)}/>
        <div className="history-actions"><button disabled={cursor===0||busy||transforming||!!stroke||!!draftMessage} onClick={()=>restoreHistory(cursor-1)}>↶ Deshacer</button><button disabled={cursor===history.length-1||busy||transforming||!!stroke||!!draftMessage} onClick={()=>restoreHistory(cursor+1)}>↷ Rehacer</button></div>
      </aside>
      <DocumentSidebar doc={navigationDoc} page={page} operations={operations} onPage={navigatePage} search={search} searchFocusRequest={searchFocusRequest} disabled={busy||transforming||!!stroke||!!draftMessage}/>
      <main className="canvas-area">
        <div className="viewer-controls"><div><button aria-label="Página anterior" disabled={page===0||busy||transforming||!!stroke||!!draftMessage} onClick={()=>setPage(page-1)}>‹</button><PageJump page={page} count={doc.pages.length} inputRef={pageJumpInput} disabled={busy||transforming||!!stroke||!!draftMessage} onPage={next=>{setPage(next);paperScroll.current?.scrollTo(0,0);}}/>{doc.pages.some(p=>p.label)&&<select className="label-goto" aria-label="Ir a etiqueta de página" value={page} disabled={busy||transforming||!!stroke||!!draftMessage} onChange={e=>setPage(Number(e.target.value))}>{doc.pages.map((p,i)=><option key={i} value={i}>{p.label||String(i+1)} · pág. {i+1}</option>)}</select>}<button aria-label="Página siguiente" disabled={page===doc.pages.length-1||busy||transforming||!!stroke||!!draftMessage} onClick={()=>setPage(page+1)}>›</button><span className="page-dimensions" aria-label="Dimensiones de la página">{Math.round(geometry.width)} × {Math.round(geometry.height)} pt</span></div>
          <div className="zoom-actions"><button aria-pressed={focusMode} onClick={()=>setFocusMode(!focusMode)} disabled={!!stroke||transforming||busy} aria-label="Vista de lectura ampliada" title="Vista de lectura ampliada"><Icon name="focus"/></button><button disabled={!!stroke||transforming||busy||zoom<=.05} aria-label="Reducir zoom" onClick={()=>changeZoom(zoom-.1)}>−</button>
            <select aria-label="Nivel de zoom" value={Math.round(zoom*100)} disabled={!!stroke||transforming||busy} onChange={e=>changeZoom(Number(e.target.value)/100)}>
              {[...new Set([5,10,25,50,75,90,100,125,150,175,200,300,400,Math.round(zoom*100)])].sort((a,b)=>a-b).map(n=><option key={n} value={n}>{n}%</option>)}
            </select><button disabled={!!stroke||transforming||busy||zoom>=4} aria-label="Aumentar zoom" onClick={()=>changeZoom(zoom+.1)}>+</button>
            <button disabled={!!stroke||transforming||busy} onClick={()=>fitPage('width')} aria-label="Ajustar ancho" title="Ajustar al ancho disponible">Ancho</button><button disabled={!!stroke||transforming||busy} onClick={()=>fitPage('page')} aria-label="Página completa" title="Ver la página completa">Página</button>
          </div>
        </div>
        {tool==='view'&&area!=='read'?<div className="tool-guide"><strong>{areas.find(a=>a.id===area).label}</strong><span>{areas.find(a=>a.id===area).description} Elige una herramienta para comenzar.</span></div>:<ToolGuide tool={tool} selected={selected} pending={draftMessage}/>}

        {tool==='textbox'&&<div className="text-insertion-modes" role="group" aria-label="Modo de insertar texto"><button aria-pressed={!textBoxMode} disabled={!!draftMessage||busy} onClick={()=>{setTextBoxMode(false);setSelectedMark(null);setNotice('Pulsa un punto y escribe sobre la página.');}}>Escribir con clic</button><button aria-pressed={textBoxMode} disabled={!!draftMessage||busy} onClick={()=>{setTextBoxMode(true);setNotice('Arrastra una caja; sus propiedades permiten moverla y corregirla como elemento del proyecto.');}}>Caja ajustable</button></div>}
        <div className="render-status" aria-live="polite">{pagePreview.refining&&preview?'Actualizando nitidez…':pagePreview.limited?'Resolución limitada por el tamaño de esta página.':''}</div>
        <div ref={paperScroll} className="paper-scroll"><div ref={paperElement} className="paper" style={{width:geometry.width*zoom,height:geometry.height*zoom}}>
          {preview && <img src={preview} data-render-scale={pagePreview.scale} alt={`Página ${page+1} del documento`} draggable="false"/>}
          {preview&&tool==='view'&&<LinkLayer links={links} zoom={zoom} onPage={target=>{setPage(target);paperScroll.current?.scrollTo(0,0);}}/>}
          {preview && <TextLayer items={textItems} zoom={zoom} enabled={tool==='view'}/>}
          {inlineSpan&&<InlineTextEditor key={`${doc.id}:${page}:${inlineSpan.id}`} doc={doc} page={page} operations={operations} span={inlineSpan} zoom={zoom} busy={busy} error={error} onParagraph={()=>{setInlineBlock(inlineSpan);setInlineSpan(null);setError('');}} onApply={async(action,params)=>{const ok=await runAdvanced(action,params);if(ok)setTool(inlineSpan.insert?'textbox':'text');return ok;}} onCancel={()=>{setInlineSpan(null);setError('');}}/>}
          {inlineBlock&&<InlineParagraph onContinue={payload=>{setFlowStart({id:doc.id,...payload});setInlineBlock(null);setError('');setPageTool('flow');}} doc={doc} page={page} operations={operations} span={inlineBlock} zoom={zoom} busy={busy} error={error} onApply={async(action,params)=>{const ok=await runAdvanced(action,params);if(ok)setTool('text');return ok;}} onCancel={()=>{setInlineBlock(null);setError('');}}/>}
          {pagePreview.failed&&!preview&&<div className="loading"><button onClick={pagePreview.retry}>Reintentar vista de página</button></div>}
          {loading && <div className="loading" role="status">Preparando página…</div>}
          <svg ref={svg} aria-label="Lienzo de anotaciones" viewBox={`0 0 ${geometry.width} ${geometry.height}`} style={{cursor:(drawingTools.has(tool)||markupTools.has(tool)||contentTools.has(tool)||tool==='note')?'crosshair':'default',touchAction:(drawingTools.has(tool)||markupTools.has(tool)||tool==='select'||tool==='images'||contentTools.has(tool))?'none':'auto',pointerEvents:tool==='view'?'none':'auto'}} onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerCancel={()=>{strokeRef.current=null;activePointer.current=null;setStroke(null);}}>
            {inlineSpan?.quad&&<polygon className="text-edit-outline" points={visibleTextQuad(inlineSpan,geometry).map(p=>p.join(',')).join(' ')}/>}
            {tool==='text'&&!loading&&!inlineSpan&&!inlineBlock&&spans.map(s=>{const [x,y,w,h]=visibleTextBox(s,geometry);return <polygon key={s.id} role="button" tabIndex="0" aria-label={`Editar en página: ${s.text}`} points={visibleTextQuad(s,geometry).map(p=>p.join(',')).join(' ')} className="text-target" onClick={e=>{setError('');setInlineSpan({...s,caret:caretIndex(s.text,[x,y,w,h],characters,point(e))});}} onKeyDown={e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();setError('');setInlineSpan(s);}}}/>;})}

            <SearchHighlights search={search} page={page}/>
            <defs><marker id="arrow-tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill={color}/></marker></defs>
            {contentTools.has(tool)&&!loading&&<ContentTargets operations={operations} page={page} tool={tool} selected={selectedMark} onSelect={id=>{setContentDraft(null);selectMark(id);}}/>}
            {activeContent&&(contentDraft||contentChanged)&&contentTools.has(tool)&&<rect x={(contentOutline?.points||activeContent.points)[0][0]} y={(contentOutline?.points||activeContent.points)[0][1]} width={(contentOutline?.points||activeContent.points)[1][0]-(contentOutline?.points||activeContent.points)[0][0]} height={(contentOutline?.points||activeContent.points)[1][1]-(contentOutline?.points||activeContent.points)[0][1]} fill="none" stroke="#2785d2" strokeDasharray="5 3" pointerEvents="none"/>}
            {tool==='images'&&!loading&&<ImageTargets operations={operations} page={page} selectedId={selectedMark} onSelect={selectMark}/>}
            {tool==='select'&&!loading&&<ExistingTargets items={existingItems} selected={selectedExisting} onSelect={selectExisting} outlinePath={busy||!!draftMessage} multiSelected={multiMode?multiRefs:[]}/>}

            {tool==='select'&&!loading&&<MarkTargets operations={operations} page={page} selectedId={selectedMark} onSelect={selectMark} onDelete={deleteMark}/>}
            {tool==='select'&&!loading&&<ReviewTargets operations={operations} page={page} selectedId={selectedMark} onSelect={selectMark} onDelete={deleteMark}/>}
            {tool==='select'&&!multiMode&&!endpointMode&&!loading&&!busy&&!draftMessage&&mayAnnotate&&activeExisting?.visible&&activeExisting?.can_move&&activeExisting?.path_rect&&<TransformHandles key={`${doc.id}:${page}:${activeExisting.xref}`} op={importedPathOperation(activeExisting)} page={geometry} zoom={zoom} canResize={activeExisting.can_resize} labels={{move:'Mover trazado importado',mover:'Tirador para mover trazado importado',resize:'Redimensionar trazado importado'}} onGesture={setTransforming} onApply={b=>changeExisting(activeExisting.xref,{path_rect:[b.x,b.y,b.x+b.width,b.y+b.height]})}/>}
            {tool==='select'&&!multiMode&&endpointMode&&!loading&&!busy&&!draftMessage&&mayAnnotate&&activeExisting?.can_edit_endpoints&&<LineEndpoints key={`${doc.id}:${page}:${activeExisting.xref}`} points={activeExisting.line_points} page={geometry} zoom={zoom} onGesture={setTransforming} onApply={points=>changeExisting(activeExisting.xref,{line_points:points})}/>}
            {tool==='select'&&multiMode&&multiItems.length>0&&!loading&&!busy&&!draftMessage&&mayAnnotate&&<TransformHandles op={groupOperation(multiItems)} page={geometry} zoom={zoom} canResize={false} labels={{move:'Mover grupo de anotaciones',mover:'Tirador para mover grupo de anotaciones'}} onGesture={setTransforming} onApply={b=>{const box=selectionBounds(multiItems);changeExistingBatch(translateSelection(multiItems,b.x-box[0],b.y-box[1]));}}/>}
            {(tool==='select'||tool==='images'||contentTools.has(tool))&&!loading&&!busy&&!contentChanged&&!contentDraft&&((['image','textbox','link'].includes(selectedOperation?.type))?mayEdit:mayAnnotate)&&selectedOperation&&<TransformHandles op={selectedOperation} page={geometry} zoom={zoom} onApply={applyTransform} onGesture={setTransforming}/>}
            {notePoint&&tool==='note'&&<circle cx={notePoint[0]} cy={notePoint[1]} r="7" fill={color} pointerEvents="none"/>}
            {stroke&&markupTools.has(tool)&&(markupMode==='characters'?selectMarkupCharacters(characters,stroke[0],stroke.at(-1)):selectMarkupWords(words,stroke[0],stroke.at(-1))).slice(0,500).map((item,i)=><polygon key={`selection-${i}`} points={[item.quad[0],item.quad[1],item.quad[3],item.quad[2]].map(p=>p.join(',')).join(' ')} fill={color} fillOpacity=".35" pointerEvents="none"/>)}
            {stroke && <Shape kind={(markupTools.has(tool)||contentTools.has(tool))?'rectangle':tool} points={stroke} stroke={color} strokeWidth={width} fill="none" strokeLinecap="round" strokeLinejoin="round" markerEnd={tool==='arrow'?'url(#arrow-tip)':undefined}/>}

          </svg>
        </div></div>
      </main>
      <aside id="tool-properties" className="properties" hidden={!propertiesVisible}><span className="eyebrow">PROPIEDADES</span><h2>{toolNames[tool] || (tool==='select'?'Seleccionar marca':tool==='text'?'Editar texto':tool==='images'?'Imágenes':'Documento')}</h2>
        {contentTools.has(tool)?<>
          <p>Arrastra un rectángulo para crear {tool==='textbox'?'una caja de texto':tool==='stamp'?'un sello':'un enlace'}. Selecciona un elemento aplicado para modificarlo.</p>
          <button disabled={busy||loading||transforming} onClick={beginContent}>Crear otro elemento</button>
          {contentItems.length>0&&<label>Elementos de la sesión<select aria-label="Elemento de contenido" disabled={busy||loading||transforming} value={selectedMark||''} onChange={e=>{setContentDraft(null);selectMark(e.target.value);}}><option value="">Seleccionar…</option>{contentItems.map((op,i)=><option key={op.id} value={op.id}>{i+1}. {toolNames[op.type]}</option>)}</select></label>}
          {activeContent?<ContentForm key={activeContent.id} tool={tool} op={activeContent} doc={doc} geometry={geometry} disabled={busy||loading||transforming} onApply={applyContent} onCancel={()=>{setContentDraft(null);setSelectedMark(null);}} onDraftChange={setContentChanged} onOutline={setContentOutline}/>:<div className="empty-hint">Define una caja en la página. Los elementos preexistentes de este tipo todavía no se editan aquí.</div>}
          {selectedOperation?.type===tool&&<><button disabled={busy||loading||transforming} onClick={()=>deleteMark(selectedMark)}>Eliminar elemento</button></>}
        </>:tool==='images'?<>
          <p>Inserta una imagen PNG o JPEG. Selecciónala aquí o en la página y usa el marco azul para moverla. La esquina conserva sus proporciones; los valores numéricos permiten ajustar ambas dimensiones.</p>
          <button className="primary" disabled={busy||loading||transforming||!mayEdit} onClick={()=>imageInput.current.click()}>Insertar imagen</button>
          <input ref={imageInput} aria-label="Archivo de imagen" type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg" hidden onChange={e=>insertImage(e.target.files[0])}/>
          <p>Hasta 2 MB y 24 millones de píxeles por imagen. Se conserva la resolución original. Las imágenes se colocan sobre el contenido.</p>
          {sessionImages.length>0&&<label>Imagen de la sesión<select aria-label="Imagen de la sesión" value={selectedMark||''} disabled={busy||loading||transforming} onChange={e=>selectMark(e.target.value)}><option value="">Seleccionar…</option>{sessionImages.map((op,i)=><option key={op.id} value={op.id}>{i+1}. {op.name}</option>)}</select></label>}
          {selectedOperation?.type==='image'&&<><p>{selectedOperation.name} · {selectedOperation.pixels.join(' × ')} píxeles</p><TransformForm op={selectedOperation} page={geometry} disabled={busy||loading||transforming} onApply={applyTransform} onDraftChange={setTransformDraft}/><button disabled={busy||loading||transforming||!mayEdit} onClick={()=>deleteMark(selectedMark)}>Eliminar imagen</button></>}
          {!sessionImages.length&&<div className="empty-hint">No hay imágenes nuevas en esta página. Las imágenes que ya contiene el PDF todavía no se pueden seleccionar o modificar.</div>}
          <p>Tras organizar o recortar páginas, las imágenes nuevas pasan a formar parte del PDF. Deshaz esa operación para recuperar sus controles de sesión.</p>
        </>:(markupTools.has(tool)||tool==='note')?<><label>Color de anotación<input aria-label="Color de anotación" type="color" value={color} onChange={e=>setColor(e.target.value)}/></label>{tool==='note'?(notePoint?<NoteForm value={noteContent} onChange={setNoteContent} onSubmit={saveNote} disabled={busy||transforming||loading}/>:<p>Haz clic dentro de la página para colocar una nota.</p>):<><label>Precisión de selección<select aria-label="Precisión de selección" value={markupMode} disabled={busy||loading||!!stroke} onChange={e=>setMarkupMode(e.target.value)}><option value="words">Palabras completas</option><option value="characters">Caracteres y fragmentos</option></select></label><p>{markupMode==='characters'?'Haz clic en una letra o arrastra un área sobre los fragmentos. Se incluyen los caracteres cuyo centro queda dentro del área a lo largo del texto.':'Haz clic en una palabra o arrastra un área que cubra las palabras que quieras marcar.'} Texto digital alineado con los ejes y páginas giradas; los escaneados requieren OCR.</p>{charactersTruncated&&markupMode==='characters'&&<p role="alert">La selección precisa se limita a los primeros 100 000 caracteres de esta página.</p>}</>}{tool==='note'&&notePoint&&<button disabled={busy} onClick={()=>{setNotePoint(null);setNoteContent('');}}>Cancelar nota</button>}</>:drawingTools.has(tool)?<><label>Color del trazo<input aria-label="Color del trazo" type="color" value={color} onChange={e=>setColor(e.target.value)}/></label><label>Grosor · {width} pt<input aria-label="Grosor" type="range" min=".5" max="12" step=".5" value={width} onChange={e=>setWidth(Number(e.target.value))}/></label><p>Las marcas se exportan como anotaciones PDF, sin aplanar la página.</p></>:tool==='select'?<><p>Haz clic sobre una marca o elígela en la lista si hay marcas superpuestas.</p>{sessionMarks.length>0&&<section className="session-marks"><h3>Marcas nuevas</h3><label>Marca de la sesión<select aria-label="Marca de la sesión" value={selectedMark||''} onChange={e=>selectMark(e.target.value)} disabled={busy||transforming||loading}><option value="">Seleccionar…</option>{sessionMarks.map((op,index)=><option key={op.id} value={op.id}>{index+1}. {toolNames[op.type]}</option>)}</select></label>{selectedMark?<button className="delete-mark" disabled={busy||transforming||loading} onClick={()=>deleteMark(selectedMark)}>Eliminar marca</button>:selectedExisting===null?<div className="empty-hint">Todavía no hay una marca seleccionada.</div>:null}{selectedOperation&&<TransformForm op={selectedOperation} page={geometry} disabled={busy||loading||transforming} onApply={applyTransform} onDraftChange={setTransformDraft}/>}
        {operations.find(op=>op.id===selectedMark)?.type==='note'&&<NoteForm value={noteContent} onChange={setNoteContent} onSubmit={saveNote} disabled={busy||transforming||loading}/>}{noteEditDraft&&<button onClick={()=>setNoteContent(selectedOperation.content)}>Cancelar cambios de nota</button>}</section>}
        {(!sessionMarks.length&&!existingItems.length)&&<div className="empty-hint">Esta página no tiene marcas. Elige Lápiz, Resaltar o Nota para crear una.</div>}
        {existingItems.length>0&&<button aria-pressed={multiMode} disabled={busy||loading||transforming||!!draftMessage||!mayAnnotate} onClick={()=>{setMultiMode(!multiMode);setMultiRefs([]);setSelectedExisting(null);setSelectedMark(null);setEndpointMode(false);}}>{multiMode?'Volver a selección individual':'Selección múltiple'}</button>}
        {multiMode&&<MultiAnnotations items={existingItems} selected={multiRefs} onSelect={setMultiRefs} disabled={busy||loading||transforming} onApply={changeExistingBatch} onDraftChange={setMultiDraft}/>}
        {!multiMode&&(existingItems.length>0||annotationsTruncated)&&<ExistingPanel items={existingItems} selected={selectedExisting} truncated={annotationsTruncated} disabled={busy||loading||transforming} onSelect={selectExisting} onDraftChange={setExistingDraft} endpointMode={endpointMode} onEndpointMode={setEndpointMode} onUpdate={changeExisting} onDelete={xref=>changeExisting(xref,null,true)}/>}</>:tool==='text'?<>
          <p>Selecciona una línea marcada. La edición conserva la línea base y limita el ancho al espacio original. Puedes elegir una fuente base, tamaño y color.</p>
          {selected?<form onSubmit={applyText}><label>Nuevo texto<textarea aria-label="Nuevo texto" value={text} onChange={e=>setText(e.target.value)} rows="4" maxLength="2000"/></label><small>Original: {selected.font} · {selected.size.toFixed(1)} pt</small>
          <label>Fuente de texto<select aria-label="Fuente de texto" value={textFont} disabled={busy} onChange={e=>setTextFont(e.target.value)}>{textFonts.map(f=><option key={f.value} value={f.value}>{f.label}</option>)}</select></label>
          <label>Tamaño de texto (pt)<input type="number" aria-label="Tamaño de texto" min="6" max="144" step="any" value={Number.isNaN(textSize)?'':textSize} required disabled={busy} onChange={e=>setTextSize(e.target.valueAsNumber)}/></label>
          <label>Color del texto<input type="color" aria-label="Color del texto" value={textColor} disabled={busy} onChange={e=>setTextColor(e.target.value)}/></label><div className="property-actions"><button className="primary" disabled={busy||transforming}>Aplicar cambio</button><button type="button" onClick={()=>setSelected(null)}>Cancelar</button></div></form>:<div className="empty-hint">{spans.some(s=>s.editable)?'Haz clic en el texto de la página.':geometry.rotation!==0?'Esta página está girada. Usa Reemplazar bloque de texto: su vista de edición se endereza y conserva el giro del PDF.':textItems.length?'Hay texto, pero no cumple los límites actuales: una línea simple de Helvetica, Times o Courier. Usa Reemplazar bloque de texto para otros fragmentos y fuentes compatibles.':'No se detectó texto digital. Si es un escaneado, usa Reconocer texto (OCR) y revisa el resultado.'}</div>}
          <p>Aplica el cambio para verlo en el PDF y después exporta una copia. No se admiten párrafos ni texto más ancho que el original.</p>
        </>:null}
        <div className="session-note"><b>Conserva tu trabajo</b><br/>Aplica tus cambios. Guarda un proyecto para retomarlos o exporta una copia PDF. La recuperación automática conserva el último estado aplicado, sin borradores.</div>
      </aside>
    </div></>}
    {doc&&organizerOpen&&<Organizer doc={doc} currentPage={page} operations={operations} busy={busy} error={error} onClose={()=>setOrganizerOpen(false)} onApply={organizePages} onExtract={extractPages}/>}
    {doc&&inserterOpen&&<Inserter mode={inserterOpen==='replace'?'replace':'insert'} currentPage={page} doc={doc} busy={busy} error={error} onClearError={()=>setError('')} onClose={()=>setInserterOpen(false)} onApply={insertPages}/>}
    {doc&&['labels','attachments','tables'].includes(pageTool)&&<ProTools kind={pageTool} doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&['digital_sign','verify_signatures'].includes(pageTool)&&<Suspense fallback={loadingTool}><DigitalSignatures mode={pageTool} doc={doc} page={page} operations={operations} onClose={()=>setPageTool(null)}/></Suspense>}
    {doc&&pageTool==='signature'&&<SignatureDialog doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='redact'&&<RedactionDialog doc={doc} page={page} operations={operations} onClose={()=>setPageTool(null)}/>}
    {doc&&pageTool==='bates'&&<BatesDialog doc={doc} operations={operations} onClose={()=>setPageTool(null)}/>}
    {doc&&pageTool==='field_properties'&&<FieldProperties doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='comments'&&<CommentsManager doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='compress'&&<Suspense fallback={loadingTool}><CompressionDialog doc={doc} page={page} operations={operations} onClose={()=>setPageTool(null)}/></Suspense>}
    {doc&&['standards','archive'].includes(pageTool)&&<Suspense fallback={loadingTool}><StandardsDialog mode={pageTool} doc={doc} operations={operations} onClose={()=>setPageTool(null)}/></Suspense>}
    {doc&&pageTool==='accessibility'&&<Suspense fallback={loadingTool}><AccessibilityDialog doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced} onPage={next=>{setPageTool(null);setPage(next);paperScroll.current?.scrollTo(0,0);}}/></Suspense>}
    {doc&&pageTool==='docx'&&<DocxExport doc={doc} page={page} operations={operations} onClose={()=>setPageTool(null)}/>}
    {pageTool==='import_word'&&<Suspense fallback={loadingTool}><WordImport onClose={()=>setPageTool(null)} onImported={(next,name)=>{if(!doc&&recovery.info?.available&&!window.confirm('Abrir el Word convertido reemplazará la sesión recuperable. ¿Continuar?'))return false;if((needsSave||draftMessage)&&!window.confirm('Abrir el Word convertido reemplazará el documento actual. Guarda un proyecto para conservar sus cambios. ¿Continuar?'))return false;adoptNewDocument(next,name);setNotice('Word convertido a PDF. Revisa el resultado y guarda un proyecto o exporta una copia.');return true;}}/></Suspense>}
    {doc&&pageTool==='portfolio'&&<Suspense fallback={loadingTool}><Portfolio doc={doc} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/></Suspense>}
    {doc&&pageTool==='flow'&&<Suspense fallback={loadingTool}><TextFlow start={flowStart?.id===doc.id?flowStart:null} doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>{setFlowStart(null);setPageTool(null);}} onAction={runAdvanced}/></Suspense>}
    {doc&&pageTool==='form_rules'&&<Suspense fallback={loadingTool}><FormRules doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onApply={plan=>applyDocumentTool('form_rules',plan)}/></Suspense>}
    {doc&&pageTool==='calculate'&&<Suspense fallback={loadingTool}><FormCalculations doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/></Suspense>}
    {doc&&pageTool==='automation'&&<Suspense fallback={loadingTool}><Automation doc={doc} operations={operations} onClose={()=>setPageTool(null)}/></Suspense>}
    {doc&&pageTool==='batch'&&<BatchProcessor doc={doc} operations={operations} onClose={()=>setPageTool(null)}/>}
    {doc&&pageTool==='existing_links'&&<LinkEditor doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='find_replace'&&<FindReplace error={error} onClearError={()=>setError('')} doc={doc} page={page} operations={operations} busy={busy} onClose={()=>setPageTool(null)} onApply={params=>runAdvanced('find-replace/apply',params)}/>}
    {doc&&pageTool==='paragraph'&&<ParagraphEditor initialBox={textRegion} doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='document_links'&&<DocumentLinks doc={doc} operations={operations} workspace={linkWorkspace} onChange={setLinkWorkspace} onClose={()=>setPageTool(null)}/>}
    {doc&&pageTool==='table_region'&&<TableRegions doc={doc} page={page} operations={operations} busy={busy} onClose={()=>setPageTool(null)}/>}
    {doc&&pageTool==='region_ocr'&&<RegionOCR doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='structure'&&<StructureEditor doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='preflight'&&<Preflight doc={doc} operations={operations} onClose={()=>setPageTool(null)}/>}
    {doc&&pageTool==='xfdf'&&<Interchange doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='working_copy'&&<WorkingCopy doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='measurement'&&<Measurements doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='layers'&&<Layers doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='existing_images'&&<ExistingImageEditor doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='field'&&<FieldDesigner doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {doc&&pageTool==='compare'&&<ComparisonDialog doc={doc} operations={operations} onClose={()=>setPageTool(null)}/>}
    {pageTool==='unlock'&&<PasswordDialog busy={busy} error={error} onClose={()=>{setPageTool(null);setPasswordFile(null);setError('');}} onOpen={password=>openFile(passwordFile,password,true)}/>}
    {doc&&['data','flatten','ocr','watermark','metadata','optimize','protect','text'].includes(pageTool)&&<AdvancedTools kind={pageTool} doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onAction={runAdvanced}/>}
    {pageTool==='create_images'&&<ImagePdfCreator busy={busy} error={error} onClose={()=>setPageTool(null)} onCreate={createImagePdf}/>}
    {doc&&pageTool==='export_images'&&<PageImageExporter doc={doc} page={page} busy={busy} error={error} onClose={()=>setPageTool(null)} onExport={exportImages}/>}
    {doc&&pageTool==='forms'&&<FormEditor doc={doc} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onApply={plan=>applyDocumentTool('form_fill',plan)} onAction={runAdvanced}/>}
    {doc&&pageTool==='bookmarks'&&<BookmarkEditor doc={doc} page={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onApply={plan=>applyDocumentTool('bookmarks',plan)}/>}
    {doc&&(pageTool==='headers'||pageTool==='numbering')&&<HeaderFooterEditor doc={doc} page={page} operations={operations} numbering={pageTool==='numbering'} busy={busy} error={error} onClose={()=>setPageTool(null)} onApply={plan=>applyDocumentTool('header_footer',plan)}/>}
    {doc&&(pageTool==='blank'||pageTool==='duplicate')&&<PageCreation mode={pageTool} doc={doc} currentPage={page} busy={busy} error={error} onClose={()=>setPageTool(null)} onApply={createPages}/>}
    {doc&&pageTool==='crop'&&<Cropper doc={doc} currentPage={page} operations={operations} busy={busy} error={error} onClose={()=>setPageTool(null)} onApply={cropPages}/>}
    {doc&&pageTool==='split'&&<Splitter doc={doc} busy={busy} error={error} onClose={()=>setPageTool(null)} onSplit={splitPages}/>}
    {commandsOpen&&<CommandPalette reason={toolReason} onRun={runCatalogTool} onClose={()=>setCommandsOpen(false)}/>}
    {helpOpen&&<WorkspaceHelp onClose={()=>setHelpOpen(false)}/>}
    {doc&&pageTool==='review'&&<DocumentReview doc={doc} operations={operations} onSignatures={()=>runCatalogTool(catalogTools.find(t=>t.id==='verify_signatures'))} onClose={()=>setPageTool(null)} onPage={next=>{setPageTool(null);setPage(next);paperScroll.current?.scrollTo(0,0);}}/>}
    <footer><span>REAPDF / DESARROLLO 0.41</span><span>{doc?'Original conservado · Exportación en PDF':'Un editor en construcción, una función comprobada a la vez.'}</span></footer>
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
