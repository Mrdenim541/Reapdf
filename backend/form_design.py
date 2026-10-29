"""Creación y eliminación explícita de campos AcroForm simples."""
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .form_structure import pdf_string
from .forms import form_model,prepare_fill,apply_fill,special_form,BASE_FONTS
from .content_tools import text_color


def field_style(config,kind):
    font=config.get('font','helv');size=config.get('size',12);width=config.get('border_width',1)
    label=config.get('label','');maximum=config.get('max_length',2000);required=config.get('required',False)
    if not isinstance(font,str) or font not in BASE_FONTS or not finite(size) or (size!=0 and not 6<=size<=72):raise DocumentError('Elige una fuente base y tamaño automático (0) o entre 6 y 72 pt.')
    if not finite(width) or not 0<=width<=5:raise DocumentError('El borde debe medir de 0 a 5 pt.')
    if not isinstance(label,str) or len(label)>250 or any(ord(c)<32 or ord(c)==127 for c in label):raise DocumentError('La descripción admite hasta 250 caracteres sin controles.')
    if type(maximum) is not int or not 1<=maximum<=2000 or type(required) is not bool:raise DocumentError('Límite de texto u obligatoriedad no válidos.')
    color=text_color(config.get('color',[0,0,0]));border=text_color(config.get('border_color',[.4,.4,.4]));fill=config.get('fill_color')
    if fill is not None:fill=text_color(fill)
    style=config.get('border_style','S')
    if style not in ['S','D','U']:raise DocumentError('Estilo de borde no compatible.')
    return {'font':font,'size':size,'width':width,'label':label,'maximum':maximum,'required':required,'color':color,'border':border,'fill':fill,'style':style}


def create_field(base,operations,config):
    if not isinstance(config,dict):raise DocumentError('Configuración de campo no válida.')
    name,kind,number,box=config.get('name'),config.get('kind'),config.get('page'),config.get('box')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100 or any(ord(c)<32 or ord(c)==127 for c in name):raise DocumentError('El campo necesita un nombre único de 1 a 100 caracteres.')
    if kind not in ['text','multiline','checkbox','choice','radio'] or type(number) is not int:raise DocumentError('Elige texto, varias líneas, casilla, lista o grupo de radio.')
    if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Indica posición X/Y y ancho/alto del campo.')
    x,y,width,height=box
    if width<15 or height<15:raise DocumentError('El campo necesita al menos 15 × 15 puntos.')
    formatting=field_style(config,kind)
    options=config.get('options',[])
    if kind=='choice' and (not isinstance(options,list) or not 1<=len(options)<=100 or any(not isinstance(s,str) or not 1<=len(s)<=200 or any(ord(c)<32 or ord(c)>255 for c in s) for s in options) or len(set(options))!=len(options)):raise DocumentError('La lista necesita de 1 a 100 opciones latinas distintas, una por línea.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        if special_form(doc):raise DocumentError('No se añaden campos a documentos con XFA, cálculos o acciones especiales.')
        rows=form_model(doc)['fields']
        from .form_fields import _references
        root_names=[doc.xref_get_key(x,'T')[1] for x,_ in _references(doc,doc.pdf_catalog(),'AcroForm/Fields')]
        if name.strip() in root_names:raise DocumentError('El nombre coincide con un campo o contenedor existente.')
        if kind=='radio' and isinstance(options,list) and len(rows)+len(options)>500:raise DocumentError('El grupo superaría el límite de 500 campos.')
        if len(rows)>=500 or any(r['name']==name.strip() for r in rows):raise DocumentError('Nombre de campo repetido o límite de 500 campos alcanzado.')
        if any(not r['editable'] and r['reason']!='Campo de solo lectura.' for r in rows):raise DocumentError('No se añaden campos a formularios con estructuras avanzadas no compatibles.')
        if not 0<=number<len(doc):raise DocumentError('Página de campo no válida.')
        page=doc[number];rect=fitz.Rect(x,y,x+width,y+height)
        if page.rotation or not page.rect.contains(rect):raise DocumentError('Crea el campo dentro de una página sin giro; puedes girarla después.')
        if kind=='radio':
            refs=add_radio_group(doc,page,name.strip(),rect,options)
            owner=int(doc.xref_get_key(refs[0],'Parent')[1].split()[0])
            doc.xref_set_key(owner,'TU',pdf_string(formatting['label']))
            if formatting['required']:doc.xref_set_key(owner,'Ff',str(32768|2))
            apply_fill(doc,prepare_fill(doc,[{'page':number,'xref':refs[0],'value':config.get('value','')}]))
            return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
        widget=fitz.Widget();widget.field_name=name.strip();widget.field_type={'text':fitz.PDF_WIDGET_TYPE_TEXT,'multiline':fitz.PDF_WIDGET_TYPE_TEXT,'checkbox':fitz.PDF_WIDGET_TYPE_CHECKBOX,'choice':fitz.PDF_WIDGET_TYPE_COMBOBOX}[kind]
        widget.rect=rect;widget.text_font=formatting['font'];widget.text_fontsize=formatting['size'];widget.text_color=formatting['color'];widget.border_color=formatting['border'];widget.border_width=formatting['width'];widget.border_style=formatting['style'];widget.fill_color=formatting['fill'];widget.field_label=formatting['label']
        if kind=='multiline':widget.field_flags=4096
        if kind=='choice':widget.choice_values=options
        if kind in ['text','multiline']:widget.text_maxlen=formatting['maximum']
        if formatting['required']:widget.field_flags|=2
        created=page.add_widget(widget)
        # Validate the created field using exactly the same rules as imported ones.
        value=config.get('value',False if kind=='checkbox' else '')
        apply_fill(doc,prepare_fill(doc,[{'page':number,'xref':created.xref,'value':value}]))
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def delete_field(base,operations,number,xref):
    if type(number) is not int or type(xref) is not int:raise DocumentError('Campo no válido.')
    with open_pdf(base) as source:
        editable(source);row=next((r for r in form_model(source)['fields'] if r['page']==number and r['xref']==xref),None)
        if not row or not row.get('can_delete'):raise DocumentError('El campo no existe o no es compatible con su eliminación.')
    with open_pdf(export_pdf(base,operations)) as doc:
        from .form_structure import field_structure
        from .form_fields import _references,_array,set_form_key
        _,structure,groups,reason=field_structure(doc)
        matches=[r for r in form_model(doc)['fields'] if r['name']==row['name']]
        if not matches or len({r['group'] for r in matches})!=1:raise DocumentError('No se pudo identificar el campo de forma única.')
        owner=matches[0]['group'];chain=structure[matches[0]['xref']]['chain'];ancestors=chain[:chain.index(owner)]
        for match in matches:
            page=doc[match['page']];page.delete_widget(page.load_widget(match['xref']))
        node=owner
        for parent in reversed(ancestors):
            children=[r for r in _references(doc,parent,'Kids') if r[0]!=node]
            doc.xref_set_key(parent,'Kids',_array(children))
            if children:break
            node=parent
        else:
            roots=[r for r in _references(doc,doc.pdf_catalog(),'AcroForm/Fields') if r[0]!=node]
            set_form_key(doc,'Fields',_array(roots))
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def add_radio_group(doc,page,name,rect,options):
    """Create one terminal field with distinct native radio appearance states."""
    from .form_fields import _references,_array,set_form_key
    if not isinstance(options,list) or not 2<=len(options)<=10 or any(not isinstance(s,str) or not s or len(s)>100 or any(ord(c)<32 or ord(c)>255 for c in s) for s in options) or len(set(options))!=len(options):raise DocumentError('El grupo necesita de 2 a 10 opciones latinas distintas, de hasta 100 caracteres.')
    step=rect.height/len(options)
    if step<24 or rect.width<55 or any(fitz.get_text_length(s,fontsize=11)>rect.width-28 for s in options):raise DocumentError('Las opciones no caben. Amplía el grupo: al menos 24 puntos de alto por opción y espacio para sus etiquetas.')
    children=[]
    for i,label in enumerate(options):
        y=rect.y0+i*step;w=fitz.Widget();w.field_name=f'{name} temporal {i+1}';w.field_label=label
        w.field_type=fitz.PDF_WIDGET_TYPE_RADIOBUTTON;w.rect=fitz.Rect(rect.x0,y,rect.x0+18,y+18);w.field_value=False
        created=page.add_widget(w);xref=created.xref;children.append(xref)
        off=doc.xref_get_key(xref,'AP/N/Off')[1];on=doc.xref_get_key(xref,'AP/N/Yes')[1]
        doc.xref_set_key(xref,'AP/N',f'<</Off {off}/opcion_{i+1} {on}>>')
        page.insert_text((rect.x0+25,y+13),label,fontsize=11)
    owner=doc.get_new_xref();doc.update_object(owner,'<</FT/Btn/Ff 32768/T'+pdf_string(name)+'/V/Off/Kids'+_array([(n,0) for n in children])+'>>')
    for xref in children:
        for key in ['T','FT','Ff','V']:doc.xref_set_key(xref,key,'null')
        doc.xref_set_key(xref,'Parent',f'{owner} 0 R')
    roots=_references(doc,doc.pdf_catalog(),'AcroForm/Fields')
    set_form_key(doc,'Fields',_array([r for r in roots if r[0] not in children]+[(owner,0)]))
    return children
