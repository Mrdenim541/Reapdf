"""Relleno inicial de campos AcroForm simples; no ejecuta cálculos ni scripts."""
from collections import Counter
import pymupdf as fitz
from .engine import DocumentError, finite
from .form_structure import field_structure,button_states,expand_values,raw_key,pdf_string

MAX_FIELDS = 500
TYPES = {fitz.PDF_WIDGET_TYPE_TEXT:'text',fitz.PDF_WIDGET_TYPE_CHECKBOX:'checkbox',
         fitz.PDF_WIDGET_TYPE_COMBOBOX:'choice',fitz.PDF_WIDGET_TYPE_LISTBOX:'choice',fitz.PDF_WIDGET_TYPE_RADIOBUTTON:'radio'}
# Widget.update() in pinned PyMuPDF only preserves these three text families.
# Other Base14 aliases silently fall back to Helvetica: keep them read-only.
BASE_FONTS = {'helv','tiro','cour'}


def choices(widget):
    result=[]
    for option in widget.choice_values or []:
        value,label=option if isinstance(option,(list,tuple)) and len(option)==2 else (option,option)
        if not isinstance(value,str) or not isinstance(label,str) or len(value)>2000 or len(label)>300:
            return None
        result.append({'value':value,'label':label})
    if len(result)>500 or len({o['value'] for o in result})!=len(result):return None
    return result


def form_model(doc):
    try:return _form_model(doc)
    except DocumentError:raise
    except Exception as exc:raise DocumentError('No se pudo interpretar la estructura del formulario. Se conserva el PDF original.') from exc


def _form_model(doc):
    locations,structure,groups,tree_reason=field_structure(doc)
    rows=[]
    for page in doc:
        for w in page.widgets() or []:
            rows.append((page.number,w))
            if len(rows)>MAX_FIELDS:raise DocumentError('Este editor admite hasta 500 campos por documento.')
    names=Counter(r['name'] for owner,refs in groups.items() for r in [structure[refs[0]]])
    catalog=doc.pdf_catalog()
    blocked=doc.get_sigflags()>0 or not doc.permissions & fitz.PDF_PERM_FORM
    special=special_form(doc)
    result=[]
    for number,w in rows:
        # Keep the Page alive while accessing its Widget.
        page=doc[number];w=page.load_widget(w.xref)
        reason=''
        info=structure.get(w.xref,{'owner':w.xref,'chain':[w.xref],'name':w.field_name})
        owner=info['owner'];members=groups.get(owner,[w.xref]);chain=info['chain']
        kind=TYPES.get(w.field_type,'unsupported');flags=w.field_flags
        inherited_readonly=any(doc.xref_get_key(n,'Ff')[0]=='int' and int(doc.xref_get_key(n,'Ff')[1])&1 for n in chain)
        options=choices(w) if kind=='choice' else []
        if blocked:reason='El documento está firmado o no permite rellenar formularios.'
        elif special:reason='El formulario contiene XFA, cálculos o scripts; se conserva sin rellenar.'
        elif tree_reason:reason=tree_reason
        elif kind=='unsupported':reason='Tipo de campo todavía no compatible (incluye botones y firmas).'
        elif inherited_readonly:reason='Campo de solo lectura.'
        elif names[info['name']]>1:reason='Hay campos independientes con el mismo nombre; no se sincronizan sin un propietario común.'
        elif any(doc.xref_get_key(n,key)[0]!='null' for n in chain for key in ['AA','A','OC']):reason='Campo con acciones o scripts; no se modifica.'
        elif flags & (8192|1048576|2097152|16777216|33554432):reason='Opciones de campo avanzadas todavía no compatibles.'
        elif kind in {'text','choice'} and (not isinstance(w.text_font,str) or w.text_font.lower() not in BASE_FONTS or not finite(w.text_fontsize) or not 0<=w.text_fontsize<=144):reason='La fuente o tamaño del campo todavía no es compatible.'
        elif kind=='choice' and (not options or any(o['value']=='' for o in options) or any(any(ord(c)<32 or ord(c)>255 for c in o['label']) for o in options) or w.field_value not in ['',None,*[o['value'] for o in options]]):reason='Opciones o valor del campo no compatibles.'
        elif kind=='checkbox' and (not isinstance(w.on_state(),str) or w.on_state()=='Off'):reason='La casilla no tiene un estado de activación compatible.'
        if not reason and owner!=w.xref and doc.xref_get_key(w.xref,'V')[0]!='null':reason='Un Widget compartido contiene un valor local que oculta al campo lógico.'
        if not reason and kind=='radio' and (owner==w.xref or flags & 33554432):reason='El radio necesita un grupo estándar de opciones exclusivas.'
        if not reason and len(members)>1 and kind=='choice':reason='Las listas con varios Widgets todavía son de solo lectura.'
        value=(w.field_value==w.on_state()) if kind=='checkbox' else (w.field_value or '')
        if kind=='radio':
            stored=doc.xref_get_key(owner,'V')
            value=stored[1].lstrip('/') if stored[0]=='name' and stored[1]!='/Off' else ''
            if stored[0] not in ['null','name']:reason='El radio no tiene un valor de grupo de tipo nombre PDF.'
        rect=w.rect*page.rotation_matrix
        if not page.rect.contains(rect):reason='El campo queda fuera de la página visible.'
        result.append({'page':number,'xref':w.xref,'name':w.field_name,'label':w.field_label or w.field_name,
                       'group':owner,'group_size':len(members),'can_delete':not reason,
                       'can_clear':not bool(flags&16384),'kind':kind,'value':value,'choices':options or [],'multiline':bool(flags & 4096),
                       'max_length':min(w.text_maxlen or 2000,2000),'rect':list(rect),
                       'editable':not reason,'reason':reason})
    # One incompatible member must block the whole logical field, never a
    # partial update with different values/appearances on other pages.
    for owner,refs in groups.items():
        items=[r for r in result if r['xref'] in refs]
        reason=next((r['reason'] for r in items if r['reason']),'')
        kinds={r['kind'] for r in items}
        if len(kinds)!=1:reason='Los Widgets del grupo tienen tipos distintos.'
        if len({(type(r['value']),r['value']) for r in items if isinstance(r['value'],(str,bool))})>1:reason='El grupo contiene valores heredados o locales contradictorios.'
        if not reason and items and items[0]['kind'] in {'radio','checkbox'}:
            states=[button_states(doc,r['xref']) for r in items]
            if any(s is None for s in states):reason='Las apariencias de botón no son compatibles.'
            elif items[0]['kind']=='radio':
                if len(set(states))!=len(states):reason='El grupo de radio tiene opciones de activación repetidas.'
                else:
                    value=items[0]['value']
                    if value not in ['',*states]:reason='El valor del radio no coincide con sus opciones.'
                    for row,state in zip(items,states):
                        row['choices']=[{'value':s,'label':doc.xref_get_key(r['xref'],'TU')[1] if doc.xref_get_key(r['xref'],'TU')[0]=='string' else s,'page':r['page']} for r,s in zip(items,states)]
                        row['radio_state']=state
                        if doc.xref_get_key(row['xref'],'AS')[1]!='/'+(state if value==state else 'Off'):reason='El valor y las apariencias del grupo de radio no coinciden.'
            elif len(set(states))!=1:reason='Las casillas compartidas usan estados de activación distintos.'
            elif len(items)>1:
                stored=doc.xref_get_key(owner,'V')
                if stored[0] not in ['name','null'] or stored[1] not in ['null','/Off','/'+states[0]]:reason='Valor de casilla compartida no compatible.'
                elif any(doc.xref_get_key(r['xref'],'AS')[1] != stored[1] for r in items):reason='Los valores y apariencias de casilla compartida no coinciden.'
        if reason:
            for row in items:row.update(editable=False,can_delete=False,reason=reason)
    return {'fields':result}


def fitted_text_size(widget,text,multiline=False):
    face=fitz.Font(widget.text_font.lower());box=widget.rect+(2,2,-2,-2)
    size=widget.text_fontsize
    if size==0:
        longest=max((face.text_length(line,fontsize=1) for line in text.split('\n')),default=1)
        size=min(12,box.width/max(longest,.01),box.height/max(1,len(text.split('\n')))/(face.ascender-2*face.descender+.1))
    if size<6 or box.width<5 or box.height<5:raise DocumentError('El campo no dispone de espacio legible suficiente (mínimo 6 pt).')
    if text and not multiline and face.text_length(text,fontsize=size)>box.width:
        raise DocumentError('El texto no cabe en el campo. Acórtalo antes de aplicar.')
    if text:
        with fitz.open() as probe:
            page=probe.new_page(width=max(10,widget.rect.width),height=max(10,widget.rect.height))
            if page.insert_textbox(fitz.Rect(2,2,widget.rect.width-2,widget.rect.height-2),text,fontname=widget.text_font.lower(),fontsize=size)<-1e-5:
                raise DocumentError('El texto no cabe en el campo. Acórtalo antes de aplicar.')
    return size


def prepare_fill(doc,values):
    rows=form_model(doc)['fields'];values=expand_values(rows,values)
    model={(row['page'],row['xref']):row for row in rows};result=[]
    for entry in values:
        key=entry['page'],entry['xref'];row=model[key]
        value=entry.get('value');page=doc[key[0]];w=page.load_widget(key[1]);size=None;display=None;choice_index=None
        if row['kind']=='radio':
            if not isinstance(value,str) or value not in ['',*[o['value'] for o in row['choices']]]:raise DocumentError('Elige una opción válida del grupo de radio.')
            if not value and not row['can_clear'] and row['value']:raise DocumentError('Este grupo de radio no permite retirar la selección.')
        elif row['kind']=='checkbox':
            if type(value) is not bool:raise DocumentError('Una casilla necesita un valor verdadero o falso.')
            value=w.on_state() if value else 'Off'
        elif row['kind']=='choice':
            if not isinstance(value,str) or value not in ['',*[o['value'] for o in row['choices']]]:
                raise DocumentError('Elige un valor de la lista del campo.')
            choice_index=next((i for i,o in enumerate(row['choices']) if o['value']==value),-1)
            if w.field_type==fitz.PDF_WIDGET_TYPE_COMBOBOX:
                display=row['choices'][choice_index]['label'] if choice_index>=0 else ''
                size=fitted_text_size(w,display)
        else:
            if not isinstance(value,str) or len(value)>row['max_length'] or any(ord(c)>255 or ord(c)<32 and not(c=='\n' and row['multiline']) for c in value):
                raise DocumentError(f"El campo {row['label']} admite hasta {row['max_length']} caracteres latinos y sus saltos de línea permitidos.")
            size=fitted_text_size(w,value,row['multiline'])
        result.append((key[0],key[1],value,size,display,choice_index,row['group'],row['kind'],row.get('radio_state')))
    return result


def apply_fill(doc,prepared):
    structural={xref:{key:raw_key(doc,xref,key) for key in ['T','FT','Ff','MaxLen','Opt','TU','Parent']} for _,xref,*_ in prepared}
    for number,xref,value,size,display,choice_index,owner,kind,on_state in prepared:
        page=doc[number];widget=page.load_widget(xref)
        doc.xref_set_key(xref,'P',f'{page.xref} 0 R')
        if widget is None:raise DocumentError('Una edición anterior retiró el campo. Rellena antes de modificar esa región.')
        if kind=='radio':
            doc.xref_set_key(owner,'V','/'+(value or 'Off'))
            doc.xref_set_key(xref,'AS','/'+(on_state if value==on_state else 'Off'))
            if xref!=owner:doc.xref_set_key(xref,'V','null')
            continue
        # MuPDF's update skips falsey strings; clear /V and selection explicitly
        # so the former value cannot survive after an empty edit.
        if value=='':
            doc.xref_set_key(xref,'V','()')
            doc.xref_set_key(xref,'I','null')
        if choice_index is not None:doc.xref_set_key(xref,'I',f'[{choice_index}]' if choice_index>=0 else 'null')
        widget.field_value=display if display is not None else value
        if size is not None:widget.text_fontsize=size
        widget.update()
        if display is not None:
            # MuPDF paints combo export codes instead of their display labels.
            # Generate the label appearance, then retain the actual export value.
            doc.xref_set_key(xref,'V',fitz.get_pdf_str(value))
        if choice_index is not None:doc.xref_set_key(xref,'I',f'[{choice_index}]' if choice_index>=0 else 'null')

    # Native updates materialize inherited flags on widgets and may leave /V on
    # bare widget children. Restore the source ownership and keep values at the
    # logical field owner, with all sibling appearances already generated.
    for number,xref,value,size,display,choice_index,owner,kind,on_state in prepared:
        if kind=='radio':continue
        for key,raw in structural[xref].items():doc.xref_set_key(xref,key,raw)
        encoded='/'+value if kind=='checkbox' else pdf_string(value)
        doc.xref_set_key(owner,'V',encoded)
        if choice_index is not None:doc.xref_set_key(owner,'I',f'[{choice_index}]' if choice_index>=0 else 'null')
        if owner!=xref:
            doc.xref_set_key(xref,'V','null');doc.xref_set_key(xref,'I','null')


def special_form(doc):
    from .form_fields import _references
    return any(doc.xref_get_key(doc.pdf_catalog(),key)[0]!='null' for key in ['AcroForm/XFA','Names/JavaScript','AA','OpenAction']) or bool(_references(doc,doc.pdf_catalog(),'AcroForm/CO'))
