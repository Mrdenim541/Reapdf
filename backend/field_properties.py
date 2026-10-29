"""Native AcroForm design changes with group-aware validation and appearance refresh."""
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .forms import form_model,prepare_fill,apply_fill,BASE_FONTS
from .form_design import field_style
from .form_structure import field_structure,pdf_string,raw_key
from .link_editing import pdf_rectangle
from .existing_annotations import LOCKED
from .field_identity import rename_field,change_choices


def rgb_color(value,default):
    if value is None:return default
    return list(value)*3 if len(value)==1 else list(value)


def property_model(doc):
    _,structure,_,tree_reason=field_structure(doc);rows=form_model(doc)['fields'];result=[]
    # Revalidate read-only fields with only their own lock removed. This keeps
    # scripts, advanced flags, fonts and appearance restrictions effective.
    unlocked={};design_rows={}
    try:
        for row in rows:
            if row['reason']=='Campo de solo lectura.':
                owner=row['group'];kind,value=doc.xref_get_key(owner,'Ff')
                if kind=='int' and int(value)&1:
                    unlocked.setdefault(owner,raw_key(doc,owner,'Ff'));doc.xref_set_key(owner,'Ff',str(int(value)&~1))
        if unlocked:design_rows={r['xref']:r for r in form_model(doc)['fields']}
    finally:
        for owner,value in unlocked.items():doc.xref_set_key(owner,'Ff',value)
    for row in rows:
        page=doc[row['page']];w=page.load_widget(row['xref']);chain=structure.get(w.xref,{}).get('chain',[])
        reason=row['reason'] if not row['editable'] else ''
        if reason=='Campo de solo lectura.':
            reason=design_rows.get(row['xref'],row)['reason']
            if any(doc.xref_get_key(n,key)[0]!='null' for n in chain for key in ['AA','A','OC']):reason='Campo con acciones o capas; se conserva sin editar.'
            from .forms import special_form
            if special_form(doc):reason='El formulario contiene acciones o cálculos.'
        if not doc.permissions&f.PDF_PERM_MODIFY or doc.get_sigflags()>0:reason='El documento no permite diseñar campos.'
        if tree_reason:reason=tree_reason
        if doc.xref_get_key(w.xref,'F')[0]=='int' and int(doc.xref_get_key(w.xref,'F')[1])&LOCKED:reason='El Widget está bloqueado para modificar sus propiedades.'
        if any(doc.xref_get_key(n,'Ff')[0]=='int' and int(doc.xref_get_key(n,'Ff')[1])&1 for n in chain if n!=row['group']):reason='El bloqueo se hereda de un contenedor o Widget y no se modifica aisladamente.'
        if doc.xref_get_key(w.xref,'MK/R') not in [('null','null'),('int','0')]:reason='El campo tiene giro interno no compatible con el diseño.'
        box=row['rect'];style={'font':(w.text_font or 'helv').lower(),'size':w.text_fontsize,'color':rgb_color(w.text_color,[0,0,0]),
            'border_color':rgb_color(w.border_color,[.4,.4,.4]),'fill_color':rgb_color(w.fill_color,None),'border_width':w.border_width or 0,
            'border_style':{'Solid':'S','Dashed':'D','Underline':'U'}.get(w.border_style,w.border_style or 'S'),
            'partial_name':doc.xref_get_key(row['group'],'T')[1],
            **({'options':row['choices']} if row['kind']=='choice' else {}),
            'label':w.field_label or '', 'max_length':row['max_length'],'required':bool(w.field_flags&2),'readonly':bool(w.field_flags&1)}
        # Non-RGB imported appearances remain readable but are not approximated.
        if any(v is not None and (not isinstance(v,(list,tuple)) or len(v) not in [1,3]) for v in [w.text_color,w.border_color,w.fill_color]):reason='El campo usa colores CMYK o no compatibles; su apariencia se conserva sin editar.'
        if style['border_style'] not in ['S','D','U']:reason='El campo usa un estilo de borde no compatible.'
        result.append({**row,'box':[box[0],box[1],box[2]-box[0],box[3]-box[1]],'properties':style,'can_design':not reason,'design_reason':reason})
    return {'fields':result}


def inspect_properties(base,operations):
    with open_pdf(export_pdf(base,operations)) as doc:return property_model(doc)


def edit_properties(base,operations,number,xref,changes):
    if type(number) is not int or type(xref) is not int or not isinstance(changes,dict) or not changes:raise DocumentError('Campo o cambios no válidos.')
    allowed={'box','label','required','readonly','font','size','color','border_color','fill_color','border_width','border_style','max_length','partial_name','options'}
    if set(changes)-allowed:raise DocumentError('Propiedades de campo no compatibles.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        rows=property_model(doc)['fields'];selected=next((v for v in rows if v['page']==number and v['xref']==xref),None)
        if not selected or not selected['can_design']:raise DocumentError(selected['design_reason'] if selected else 'El campo no pertenece a esta versión del documento.')
        group=[v for v in rows if v['group']==selected['group']]
        if any(not v['can_design'] for v in group):raise DocumentError('El grupo incluye posiciones incompatibles con la edición de propiedades.')
        style_keys=set(changes)-{'box','label','required','readonly','max_length','partial_name','options'}
        if selected['kind']=='radio' and (style_keys or 'max_length' in changes):raise DocumentError('En radios se editan posición, descripción, obligatoriedad y solo lectura; se conservan sus apariencias.')
        if selected['kind']=='checkbox' and style_keys&{'font','size','color'}:raise DocumentError('Las casillas conservan la fuente y color de su símbolo; edita borde y fondo.')
        if selected['kind']=='checkbox' and style_keys and selected['properties']['font'] not in BASE_FONTS:raise DocumentError('La apariencia de este botón conserva su fuente original; solo se editan posición y propiedades lógicas.')
        if 'max_length' in changes and selected['kind']!='text':raise DocumentError('El límite de caracteres corresponde a campos de texto.')
        settings={**selected['properties'],**changes};formatting=field_style(settings|({'font':'helv'} if selected['kind'] in ['checkbox','radio'] else {}),selected['kind'])
        if type(settings['readonly']) is not bool:raise DocumentError('Solo lectura debe ser verdadero o falso.')
        final_name=rename_field(doc,selected,changes['partial_name']) if 'partial_name' in changes else selected['name']
        if 'options' in changes:change_choices(doc,selected,changes['options'])
        owner=selected['group'];owner_flags=doc.xref_get_key(owner,'Ff')
        flags=int(owner_flags[1]) if owner_flags[0]=='int' else doc[selected['page']].load_widget(xref).field_flags
        # Temporarily permit appearance validation on fields marked read-only.
        doc.xref_set_key(owner,'Ff',str(flags&~1))
        if 'box' in changes:
            box=changes['box']
            if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box) or min(box[2:])<15:raise DocumentError('El campo necesita un área válida de al menos 15 × 15 pt.')
            page=doc[number];x,y,w,h=box;rect=f.Rect(x,y,x+w,y+h)
            if not page.rect.contains(rect):raise DocumentError('El campo debe quedar dentro de la página visible.')
            native=pdf_rectangle(page,rect);doc.xref_set_key(xref,'Rect','['+' '.join(str(v) for v in native)+']')
        if 'label' in changes:
            doc.xref_set_key(owner,'TU',pdf_string(formatting['label']))
            for row in group:
                if row['xref']!=owner and selected['kind']!='radio':doc.xref_set_key(row['xref'],'TU','null')
        if 'max_length' in changes:
            doc.xref_set_key(owner,'MaxLen',str(formatting['maximum']))
            for row in group:
                if row['xref']!=owner:doc.xref_set_key(row['xref'],'MaxLen','null')
        if style_keys:
            for row in group:
                ref=row['xref']
                old=row['properties'];values={**old,**{k:changes[k] for k in style_keys}}
                checked=field_style(values,row['kind'])
                if style_keys&{'font','size','color'}:
                    color=checked['color'];da=' '.join(str(v) for v in color)+f" rg /{checked['font']} {checked['size']} Tf"
                    doc.xref_set_key(ref,'DA',pdf_string(da))
                for key,pdfkey in [('border_color','MK/BC'),('fill_color','MK/BG')]:
                    if key in changes:
                        value=changes[key];doc.xref_set_key(ref,pdfkey,'['+' '.join(map(str,value))+']' if value is not None else 'null')
                if 'border_width' in changes:doc.xref_set_key(ref,'BS/W',str(checked['width']))
                if 'border_style' in changes:doc.xref_set_key(ref,'BS/S','/'+checked['style'])
        if 'required' in changes:flags=(flags|2) if formatting['required'] else flags&~2
        doc.xref_set_key(owner,'Ff',str(flags&~1))
        # Re-read raw dictionaries: source Page handles can cache old Widget values.
        values=[{'page':selected['page'],'xref':xref,'value':selected['value']}]
        if selected['kind']!='checkbox' or style_keys:apply_fill(doc,prepare_fill(doc,values))
        final_flags=(flags|1) if settings['readonly'] else flags&~1
        doc.xref_set_key(owner,'Ff',str(final_flags))
        output=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(output) as check:
        final=[v for v in form_model(check)['fields'] if v['name']==final_name]
        if len(final)!=len(group) or any(v['value']!=selected['value'] for v in final):raise DocumentError('No se pudieron conservar el grupo y sus valores.')
    return output
