"""Withdraw only previous standards-identification claims from a prepared copy."""
from lxml import etree as E
import pymupdf as f
from .engine import DocumentError
from .styled_text import stream
IDENTIFIERS={'http://www.npes.org/pdfx/ns/id/','http://www.aiim.org/pdfa/ns/id/','http://www.aiim.org/pdfua/ns/id/'}
CUSTOM='http://ns.adobe.com/pdfx/1.3/'
KEYS={'GTS_PDFXVersion','GTS_PDFXConformance'}


def xml(doc):
    n=f.mupdf;x=n.pdf_to_num(n.pdf_dict_gets(n.pdf_load_object(f._as_pdf_document(doc),doc.pdf_catalog()),'Metadata'))
    if not x:return 0,None
    raw=stream(doc,x,2*1024*1024)
    try:
        root=E.fromstring(raw,E.XMLParser(resolve_entities=False,no_network=True,load_dtd=False,huge_tree=False,remove_blank_text=False,strip_cdata=False))
        if root.getroottree().docinfo.doctype or any(isinstance(el,E._Entity) for el in root.iter()):raise ValueError()
        return x,root
    except (E.XMLSyntaxError,ValueError):raise DocumentError('Los metadatos XML no permiten revisar las declaraciones de estándares con seguridad.') from None


def claims(doc):
    n=f.mupdf;trailer=n.pdf_trailer(f._as_pdf_document(doc));info=n.pdf_dict_gets(trailer,'Info');values=[]
    for key in KEYS:
        v=n.pdf_dict_gets(info,key)
        if not n.pdf_is_null(v):values.append({'source':'Info','key':key,'value':n.pdf_to_text_string(v) if n.pdf_is_string(v) else 'Tipo no compatible'})
    _,root=xml(doc)
    if root is not None:
        for el in root.iter():
            if not isinstance(el.tag,str):continue
            q=E.QName(el)
            if q.namespace in IDENTIFIERS or q.namespace==CUSTOM and q.localname in KEYS:values.append({'source':'XMP','key':q.localname,'namespace':q.namespace,'value':(el.text or '')[:300]})
            for key,value in el.attrib.items():
                q=E.QName(key)
                if q.namespace in IDENTIFIERS or q.namespace==CUSTOM and q.localname in KEYS:values.append({'source':'XMP','key':q.localname,'namespace':q.namespace,'value':value[:300]})
    return values


def withdraw(doc):
    n=f.mupdf;info=n.pdf_dict_gets(n.pdf_trailer(f._as_pdf_document(doc)),'Info');removed=[]
    for key in KEYS:
        if not n.pdf_is_null(n.pdf_dict_gets(info,key)):removed.append('Info/'+key);n.pdf_dict_dels(info,key)
    x,root=xml(doc)
    if root is not None:
        for el in list(root.iter()):
            if not isinstance(el.tag,str):continue
            for key in list(el.attrib):
                q=E.QName(key)
                if q.namespace in IDENTIFIERS or q.namespace==CUSTOM and q.localname in KEYS:del el.attrib[key];removed.append('XMP/'+q.localname)
            q=E.QName(el)
            if q.namespace in IDENTIFIERS or q.namespace==CUSTOM and q.localname in KEYS:
                parent=el.getparent()
                if parent is None:raise DocumentError('La identificación de estándares no es un paquete XMP editable.')
                parent.remove(el);removed.append('XMP/'+q.localname)
        if removed:doc.update_stream(x,E.tostring(root,encoding='utf-8'),compress=True)
    return removed
