"""An explicitly unsigned, visibly identified working copy of a signed PDF."""
import hashlib
import pymupdf as f
from .engine import open_pdf,DocumentError

LABEL='COPIA DE TRABAJO - SIN FIRMAS DIGITALES'


def create(base,acknowledge=False):
    if acknowledge is not True:raise DocumentError('Confirma que la copia no conservará firmas digitales y que los campos se aplanarán.')
    with open_pdf(base) as source:
        if source.get_sigflags()<=0:raise DocumentError('Este documento no contiene indicadores de firma; puede editarse mediante las herramientas habituales.')
        if not source.permissions&f.PDF_PERM_COPY or not source.permissions&f.PDF_PERM_MODIFY:raise DocumentError('Se necesitan permisos de copia y modificación; no se eliminan restricciones de contraseña.')
        if any(p.rect.width<160 or p.rect.height<80 for p in source):raise DocumentError('Una página es demasiado pequeña para identificar de forma legible la copia.')
        signature_widgets=sum(1 for p in source for w in p.widgets() or [] if w.field_type==f.PDF_WIDGET_TYPE_SIGNATURE)
        fields=sum(1 for p in source for _ in p.widgets() or [])
        toc=source.get_toc();source.bake(annots=False,widgets=True)
        with f.open() as out:
            out.insert_pdf(source,links=True,annots=True,widgets=False)
            if toc:out.set_toc(toc)
            font=f.Font('helv')
            for page in out:
                rotation=page.rotation;page.set_rotation(0)
                size=min(8,(page.rect.width-24)/font.text_length(LABEL,fontsize=1))
                page.insert_text((12,page.rect.height-8),LABEL,fontsize=size,fontname='helv',color=(.65,.12,.08));page.set_rotation(rotation)
            out.set_metadata({'title':(source.metadata.get('title') or 'Documento')+' - copia de trabajo','author':source.metadata.get('author') or '', 'subject':'Copia sin firmas digitales; original SHA256 '+hashlib.sha256(base).hexdigest(),'creator':'Reapdf','producer':'Reapdf'})
            data=out.tobytes(garbage=4,deflate=True)
    with open_pdf(data) as check:
        if check.get_sigflags()>0 or any(list(p.widgets() or []) for p in check):raise DocumentError('No se pudo comprobar la retirada de campos de firma de la copia.')
        if any(LABEL not in p.get_text() for p in check):raise DocumentError('No se pudo verificar la identificación de la copia en todas las páginas.')
    return data,{'original_sha256':hashlib.sha256(base).hexdigest(),'signature_widgets':signature_widgets,'fields_flattened':fields,'digital_signatures_retained':False,'original_untouched':True,'note':'La copia no conserva validez de firmas, formularios editables, adjuntos ni etiquetado de accesibilidad del original. Se conserva su apariencia de página con identificación visible.'}
