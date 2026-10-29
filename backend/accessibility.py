"""Bounded accessibility preparation and diagnostics; never manufactures tag compliance."""
from io import BytesIO
from datetime import datetime,timezone
import hashlib,re
from lxml import etree
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils import generic
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .form_structure import pdf_string

NS={'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#','dc':'http://purl.org/dc/elements/1.1/'}
LANGUAGE=re.compile(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z')
MAX_NODES=2000


def object_value(value):return value.get_object() if isinstance(value,generic.IndirectObject) else value


def tagged_structure(data):
    reader=PdfFileReader(BytesIO(data),strict=True)
    if reader.security_handler is not None:reader.decrypt('')
    root=object_value(reader.root.get('/StructTreeRoot'))
    if root is None or isinstance(root,generic.NullObject):return {'present':False,'nodes':0,'figures':0,'figures_without_alt':0,'links':0,'tables':0,'custom_roles':0,'repeated_nodes':False}
    if not isinstance(root,generic.DictionaryObject):raise DocumentError('El árbol de estructura no tiene un diccionario válido.')
    roles=object_value(root.get('/RoleMap',generic.DictionaryObject()));counts={'present':True,'nodes':0,'figures':0,'figures_without_alt':0,'links':0,'tables':0,'custom_roles':0,'repeated_nodes':False};seen=set()
    standard={'Document','Part','Art','Sect','Div','BlockQuote','Caption','TOC','TOCI','Index','NonStruct','Private','P','H','H1','H2','H3','H4','H5','H6','L','LI','Lbl','LBody','Table','TR','TH','TD','THead','TBody','TFoot','Span','Quote','Note','Reference','BibEntry','Code','Link','Annot','Ruby','RB','RT','RP','Warichu','WT','WP','Figure','Formula','Form'}
    def walk(value,depth):
        if depth>32:raise DocumentError('El árbol de etiquetas supera 32 niveles.')
        if isinstance(value,generic.IndirectObject):
            ident=(value.idnum,value.generation)
            if ident in seen:counts['repeated_nodes']=True;return
            seen.add(ident)
        value=object_value(value)
        if isinstance(value,generic.ArrayObject):
            for child in value:walk(child,depth+1)
            return
        if not isinstance(value,generic.DictionaryObject):return
        counts['nodes']+=1
        if counts['nodes']>MAX_NODES:raise DocumentError('La revisión admite hasta 2000 nodos de estructura.')
        role=str(value.get('/S','')).lstrip('/')
        if role and role not in standard:
            counts['custom_roles']+=1;visited=set()
            while role not in standard and role not in visited and len(visited)<16 and isinstance(roles,generic.DictionaryObject):
                visited.add(role);mapped=roles.get('/'+role)
                if mapped is None:break
                role=str(object_value(mapped)).lstrip('/')
        if role=='Figure':
            counts['figures']+=1;alt=object_value(value.get('/Alt',''));actual=object_value(value.get('/ActualText',''))
            if not (isinstance(alt,str) and alt.strip()) and not (isinstance(actual,str) and actual.strip()):counts['figures_without_alt']+=1
        if role=='Link':counts['links']+=1
        if role=='Table':counts['tables']+=1
        if '/K' in value:walk(value['/K'],depth+1)
    walk(root.get('/K'),0)
    return counts


def inspect_accessibility(base,operations):
    data=export_pdf(base,operations)
    with open_pdf(data) as doc:
        if len(doc)>100 or doc.xref_length()>50000:raise DocumentError('La revisión de accesibilidad admite 100 páginas y 50000 objetos.')
        catalog=doc.pdf_catalog();lang=doc.xref_get_key(catalog,'Lang');title=doc.metadata.get('title','') or '';display=doc.xref_get_key(catalog,'ViewerPreferences/DisplayDocTitle')==('bool','true')
        issues=[];add=lambda code,message,page=None:issues.append({'code':code,'message':message,'page':page})
        if not title.strip():add('missing_title','Falta un título de documento.')
        language=lang[1] if lang[0]=='string' else ''
        if not LANGUAGE.fullmatch(language):add('missing_language','Falta un idioma de documento con formato admitido.')
        if not display:add('display_title','El visor no tiene activada la preferencia de mostrar el título.')
        try:tags=tagged_structure(data)
        except DocumentError:raise
        except Exception:raise DocumentError('No se pudo interpretar de forma segura el árbol de etiquetas. No se declara accesibilidad.') from None
        if not tags['present']:add('missing_tags','No se ha encontrado árbol de etiquetas; título e idioma no sustituyen el etiquetado.')
        if tags['figures_without_alt']:add('figures_without_alt',f"Figuras etiquetadas sin texto alternativo detectado: {tags['figures_without_alt']}.")
        if tags['repeated_nodes']:add('tag_structure_repeated','El árbol contiene nodos repetidos o ciclos; necesita revisión especializada.')
        if tags['custom_roles']:add('custom_roles','Hay roles personalizados; revisar su mapeo y significado manualmente.')
        rows=[];objects=0
        for page in doc:
            refs=page.annot_xrefs();objects+=len(refs)
            if objects>5000:raise DocumentError('La revisión supera 5000 anotaciones/campos.')
            missing_labels=0
            for ref,kind,_ in refs:
                if kind!=f.PDF_ANNOT_WIDGET:continue
                node=ref;seen=set();label=False
                while node not in seen and len(seen)<16:
                    seen.add(node);typ,value=doc.xref_get_key(node,'TU')
                    if typ=='string' and value.strip():label=True;break
                    typ,value=doc.xref_get_key(node,'Parent')
                    if typ!='xref':break
                    node=int(value.split()[0])
                    if not 0<node<doc.xref_length():break
                if not label:missing_labels+=1
            has_text=bool(page.get_text('text',flags=f.TEXTFLAGS_TEXT).strip());images=len(page.get_images(full=True));fonts=page.get_fonts(full=True)
            if max(images,len(fonts))>2000:raise DocumentError('La página supera 2000 recursos por tipo.')
            missing_unicode=sum(1 for row in fonts if row[2]=='Type0' and doc.xref_get_key(row[0],'ToUnicode')[0]=='null')
            if images and not has_text:add('possible_scan','Imagen sin texto digital detectado: revisar OCR.',page.number)
            if missing_labels:add('field_labels',f'Campos sin descripción emergente: {missing_labels}.',page.number)
            if missing_unicode:add('unicode_mapping',f'Fuentes Type0 sin ToUnicode detectado: {missing_unicode}.',page.number)
            rows.append({'page':page.number,'has_text':has_text,'images':images,'fields_without_label':missing_labels,'type0_without_tounicode':missing_unicode})
        return {'schema':'reapdf-accessibility-1','source_sha256':hashlib.sha256(data).hexdigest(),'checked_at':datetime.now(timezone.utc).isoformat(),
            'title':title,'language':language,'display_document_title':display,'marked':doc.xref_get_key(catalog,'MarkInfo/Marked')==('bool','true'),
            'tags':tags,'pages':rows,'issues':issues,'can_prepare':doc.get_sigflags()<=0 and bool(doc.permissions&f.PDF_PERM_MODIFY),
            'scope':'Diagnóstico orientativo de preparación. No valida orden de lectura, calidad del texto alternativo, contraste, uso con lector de pantalla ni conformidad PDF/UA. Para reglas automáticas usa veraPDF y completa revisión manual.'}


def synchronize_xmp(old,title,language):
    parser=etree.XMLParser(resolve_entities=False,no_network=True,load_dtd=False,huge_tree=False)
    try:
        if old:
            if len(old.encode('utf-8'))>2*1024*1024:raise DocumentError('Los metadatos XMP superan 2 MB.')
            root=etree.fromstring(old.encode('utf-8'),parser)
            if root.getroottree().docinfo.doctype or any(isinstance(n,etree._Entity) for n in root.iter()):raise ValueError()
        else:root=etree.Element('{adobe:ns:meta/}xmpmeta',nsmap={'x':'adobe:ns:meta/','rdf':NS['rdf'],'dc':NS['dc']})
        rdf=root.find('.//{'+NS['rdf']+'}RDF') if root.tag!='{'+NS['rdf']+'}RDF' else root
        if rdf is None:rdf=etree.SubElement(root,'{'+NS['rdf']+'}RDF')
        descriptions=[n for n in rdf.findall('{'+NS['rdf']+'}Description') if n.get('{'+NS['rdf']+'}about','')=='']
        description=descriptions[0] if descriptions else etree.SubElement(rdf,'{'+NS['rdf']+'}Description',{'{'+NS['rdf']+'}about':''})
        # Remove all prior title representations, including RDF attributes, but preserve unrelated namespaces/properties.
        translations=[]
        from copy import deepcopy
        for element in descriptions:
            element.attrib.pop('{'+NS['dc']+'}title',None)
            for node in element.findall('{'+NS['dc']+'}title'):
                translations.extend(deepcopy(n) for n in node.findall('.//{'+NS['rdf']+'}li') if n.get('{http://www.w3.org/XML/1998/namespace}lang') not in [None,'x-default'])
                element.remove(node)
        node=etree.SubElement(description,'{'+NS['dc']+'}title');alt=etree.SubElement(node,'{'+NS['rdf']+'}Alt');etree.SubElement(alt,'{'+NS['rdf']+'}li',{'{http://www.w3.org/XML/1998/namespace}lang':'x-default'}).text=title
        for translation in translations:alt.append(translation)
        language_node=description.find('{'+NS['dc']+'}language')
        if language_node is None:language_node=etree.SubElement(description,'{'+NS['dc']+'}language')
        bag=language_node.find('{'+NS['rdf']+'}Bag')
        if bag is None:
            language_node.clear();bag=etree.SubElement(language_node,'{'+NS['rdf']+'}Bag')
        if not any(n.text==language for n in bag):etree.SubElement(bag,'{'+NS['rdf']+'}li').text=language
        return etree.tostring(root,encoding='unicode')
    except (etree.XMLSyntaxError,etree.XPathError,ValueError):raise DocumentError('Los metadatos XMP no son compatibles con una actualización segura. El original se conserva.') from None


def prepare_accessibility(base,operations,title,language,display_title=True):
    if not isinstance(title,str) or not 1<=len(title.strip())<=250 or any(ord(c)<32 or ord(c)==127 or 0xd800<=ord(c)<=0xdfff for c in title):raise DocumentError('El título admite 1–250 caracteres sin controles.')
    if not isinstance(language,str) or len(language)>63 or not LANGUAGE.fullmatch(language):raise DocumentError('Usa un idioma como es, es-PE o en-US (formato BCP 47 básico).')
    if type(display_title) is not bool:raise DocumentError('La preferencia de mostrar título debe ser verdadera o falsa.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        catalog=doc.pdf_catalog();xmp=synchronize_xmp(doc.get_xml_metadata(),title.strip(),language)
        values=dict(doc.metadata);values['title']=title.strip();doc.set_metadata(values);doc.set_xml_metadata(xmp);doc.xref_set_key(catalog,'Lang',pdf_string(language))
        kind,value=doc.xref_get_key(catalog,'ViewerPreferences')
        if kind=='xref':target=int(value.split()[0]);key='DisplayDocTitle'
        elif kind in ['null','dict']:
            if kind=='null':doc.xref_set_key(catalog,'ViewerPreferences','<<>>')
            target=catalog;key='ViewerPreferences/DisplayDocTitle'
        else:raise DocumentError('Las preferencias del visor tienen una estructura no compatible.')
        doc.xref_set_key(target,key,'true' if display_title else 'false')
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
