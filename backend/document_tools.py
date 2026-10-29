"""Herramientas de documento: texto, metadatos, optimización y copias cifradas."""
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError

META_KEYS={'title','author','subject','keywords','creator'}


def editable(doc):
    if doc.get_sigflags()>0 or not doc.permissions & fitz.PDF_PERM_MODIFY:raise DocumentError('El documento está firmado o no permite esta modificación.')


def selected_pages(doc,pages):
    if not isinstance(pages,list) or not 1<=len(pages)<=500 or any(type(n) is not int or not 0<=n<len(doc) for n in pages) or len(set(pages))!=len(pages):raise DocumentError('Elige páginas válidas sin repeticiones.')
    return pages


def export_text(base,operations,pages):
    with open_pdf(base) as source:
        if not source.permissions & fitz.PDF_PERM_COPY:raise DocumentError('El documento no permite extraer texto.')
        selected_pages(source,pages)
    with open_pdf(export_pdf(base,operations)) as doc:
        return '\n\n'.join(f'--- Página {n+1} ---\n'+doc[n].get_text(sort=True) for n in pages).encode('utf-8')


def read_metadata(base):
    with open_pdf(base) as doc:return {key:doc.metadata.get(key,'') or '' for key in sorted(META_KEYS)}


def metadata_pdf(base,operations,values,remove_xml=False):
    if not isinstance(values,dict) or set(values)!=META_KEYS or any(not isinstance(v,str) or len(v)>1000 or any(ord(c)<32 for c in v) for v in values.values()) or type(remove_xml) is not bool:raise DocumentError('Completa los cinco metadatos con hasta 1000 caracteres sin controles.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        doc.set_metadata({**doc.metadata,**values})
        if remove_xml:doc.del_xml_metadata()
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def optimize_pdf(base,operations):
    with open_pdf(base) as source:editable(source)
    edited=export_pdf(base,operations)
    with open_pdf(edited) as doc:
        candidate=doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True,deflate_images=True,deflate_fonts=True,use_objstms=1)
    result=candidate if len(candidate)<len(edited) else edited
    return result,{'before':len(edited),'after':len(result),'saved':len(edited)-len(result)}


def protect_pdf(base,operations,password,owner_password,allow_copy=True,allow_print=True):
    if any(not isinstance(v,str) or not 8<=len(v)<=100 or '\x00' in v for v in [password,owner_password]) or any(len(v.encode('utf-8'))>127 for v in [password,owner_password]) or password==owner_password:raise DocumentError('Usa contraseñas distintas de apertura y propietario, de 8 a 100 caracteres.')
    if type(allow_copy) is not bool or type(allow_print) is not bool:raise DocumentError('Permisos de copia o impresión no válidos.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        permissions=fitz.PDF_PERM_FORM|fitz.PDF_PERM_MODIFY|fitz.PDF_PERM_ANNOTATE|fitz.PDF_PERM_ASSEMBLE|fitz.PDF_PERM_ACCESSIBILITY
        if allow_copy:permissions|=fitz.PDF_PERM_COPY
        if allow_print:permissions|=fitz.PDF_PERM_PRINT|fitz.PDF_PERM_PRINT_HQ
        return doc.tobytes(garbage=4,deflate=True,encryption=fitz.PDF_ENCRYPT_AES_256,user_pw=password,owner_pw=owner_password,permissions=permissions)


class PasswordRequired(DocumentError):pass


def unlock_pdf(data,password=''):
    try:doc=fitz.open(stream=data,filetype='pdf')
    except Exception as exc:raise DocumentError('No se pudo abrir el PDF.') from exc
    with doc:
        if not doc.needs_pass:return data,False
        if not isinstance(password,str) or not password:raise PasswordRequired('Introduce la contraseña del PDF.')
        authorization=doc.authenticate(password)
        if not authorization:raise PasswordRequired('Contraseña incorrecta. Vuelve a intentarlo.')
        all_rights=fitz.PDF_PERM_COPY|fitz.PDF_PERM_MODIFY|fitz.PDF_PERM_ANNOTATE|fitz.PDF_PERM_FORM|fitz.PDF_PERM_ASSEMBLE|fitz.PDF_PERM_PRINT|fitz.PDF_PERM_PRINT_HQ
        if not authorization & 4 and doc.permissions & all_rights != all_rights:
            raise PasswordRequired('Este PDF tiene restricciones. Introduce la contraseña de propietario para trabajar con una copia descifrada.')
        if doc.get_sigflags()>0:raise DocumentError('Los PDF cifrados con firmas no se descifran en esta versión.')
        return doc.tobytes(garbage=4,deflate=True,encryption=fitz.PDF_ENCRYPT_NONE),True
