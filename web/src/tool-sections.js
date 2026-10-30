// Every catalog tool appears once in its task area. Groups remain independent of
// permissions: unavailable actions keep their reason and their expected place.
export const toolSections={
 workspace:[['relations','Documentos relacionados',['document_links','portfolio']],['plans','Planos y contenido',['measurement','layers']],['interchange','Intercambio y estructura',['xfdf','structure']]],
 read:[['consult','Consultar',['view']],['review','Revisar',['accessibility','review','compare']],['document','Documento',['attachments','metadata']]],
 edit:[['text','Texto',['find_replace','text','paragraph','flow','textbox']],['links','Enlaces',['link','existing_links']],['images','Imágenes',['images','existing_images']],['layout','Composición',['headers','watermark']]],
 annotate:[['review','Revisión',['select','comments']],['text','Marcar texto',['highlight','underline','strikeout','note']],['drawing','Dibujar',['ink','line','arrow','rectangle']],['stamps','Sellos',['stamp']]],
 pages:[['compose','Componer',['organizer','insert','replace','duplicate','blank']],['adjust','Ajustar y separar',['crop','split']],['identify','Índice y numeración',['labels','bookmarks','numbering','bates']]],
 forms:[['fields','Campos y datos',['forms','field_properties','field','data','flatten','calculate','form_rules']],['sign','Firmas',['signature','digital_sign','verify_signatures']]],
 convert:[['recognize','Reconocer',['ocr','region_ocr']],['export','Exportar',['export_images','tables','table_region','docx','export_text']],['prepare','Preparar copias',['optimize','compress','archive']],['automate','Automatizar',['batch','automation']]],
 protect:[['security','Seguridad',['protect','redact','working_copy']],['validate','Conformidad e impresión',['standards','preflight']]],
};
export function sectionedTools(area,items){return (toolSections[area]||[]).map(([id,label,ids])=>({id,label,items:ids.map(id=>items.find(t=>t.id===id)).filter(Boolean)})).filter(s=>s.items.length);}
export function toolIcon(tool){
 if(['line','arrow','rectangle','ink','note','highlight','underline','strikeout','select'].includes(tool.id))return tool.id;
 if(['text','paragraph','flow','textbox','highlight','underline','strikeout'].includes(tool.id))return 'text';
 if(['images','existing_images','export_images'].includes(tool.id))return 'image';
 if(['link','existing_links'].includes(tool.id))return 'link';
 return tool.area;
}
