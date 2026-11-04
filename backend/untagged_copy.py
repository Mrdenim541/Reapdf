"""Explicit editable copy without an active accessibility structure.

This is not rasterization, redaction, signature removal or a security sanitizer.
Page streams and all other original binary streams stay unchanged. Old unused
objects may remain in the copy; the source is never overwritten.
"""
import hashlib
import xml.etree.ElementTree as ET
from .engine import open_pdf,export_pdf,DocumentError

IDENTIFIERS={'http://www.aiim.org/pdfua/ns/id/','http://www.aiim.org/pdfa/ns/id/'}


def state(doc):
    if doc.xref_length()>100000:raise DocumentError('La copia supera el límite de objetos verificables.')
    kind,value=doc.xref_get_key(doc.pdf_catalog(),'Metadata')
    metadata=int(value.split()[0]) if kind=='xref' else None
    streams={};size=0
    for x in range(1,doc.xref_length()):
        if x==metadata or not doc.xref_is_stream(x):continue
        raw=doc.xref_stream_raw(x) or b'';size+=len(raw)
        if size>128*1024*1024:raise DocumentError('La copia supera 128 MB de recursos verificables.')
        streams[x]=hashlib.sha256(raw).hexdigest()
    pages=[(tuple(p.mediabox),tuple(p.cropbox),p.rotation,hashlib.sha256(p.read_contents()).hexdigest()) for p in doc]
    return streams,pages


def detach(doc):
    """Remove structural associations only; caller must check permissions."""
    xml=doc.get_xml_metadata()
    if any(ns in xml for ns in IDENTIFIERS):
        if len(xml)>2*1024*1024:raise DocumentError('Los metadatos superan el límite verificable de la copia.')
        try:root=ET.fromstring(xml)
        except ET.ParseError:raise DocumentError('No se pueden retirar las declaraciones de conformidad de estos metadatos.') from None
        names=tuple('{'+ns+'}' for ns in IDENTIFIERS)
        for parent in root.iter():
            for child in list(parent):
                if isinstance(child.tag,str) and child.tag.startswith(names):parent.remove(child)
            for key in list(parent.attrib):
                if key.startswith(names):del parent.attrib[key]
        doc.set_xml_metadata(ET.tostring(root,encoding='unicode'))
    for key in ['StructTreeRoot','MarkInfo']:doc.xref_set_key(doc.pdf_catalog(),key,'null')
    for x in range(1,doc.xref_length()):
        keys=doc.xref_get_keys(x)
        for key in ['StructParent','StructParents']:
            if key in keys:doc.xref_set_key(x,key,'null')
    for page in doc:
        if doc.xref_get_key(page.xref,'Tabs')==('name','/S'):doc.xref_set_key(page.xref,'Tabs','null')


def create(base,operations,acknowledge=False):
    if acknowledge is not True:raise DocumentError('Confirma que la copia perderá las etiquetas de accesibilidad y las declaraciones PDF/UA y PDF/A.')
    from .document_tools import editable
    import pymupdf as f
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('La copia requiere permiso de copia y modificación.')
    edited=export_pdf(base,operations)
    with open_pdf(edited) as doc:
        if doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]=='null':raise DocumentError('El PDF no tiene un árbol de etiquetas de accesibilidad que retirar.')
        before=state(doc);permissions=doc.permissions
        detach(doc)
        # Keep xrefs and original stream encodings stable for independent checks.
        result=doc.tobytes(garbage=0,deflate=False,encryption=f.PDF_ENCRYPT_KEEP)
    with open_pdf(result) as check:
        if check.permissions!=permissions or state(check)!=before or check.xref_get_key(check.pdf_catalog(),'StructTreeRoot')[0]!='null':raise DocumentError('La copia alteró contenido o permisos; no se publica.')
    return result,{'original_untouched':True,'rasterized':False,'page_streams_and_binary_resources_verified':True,'accessibility_tags_retained':False,'standard_identifiers_retained':False}
