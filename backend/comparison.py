"""Comparación de texto y apariencia por posición de página; resultado de revisión."""
import base64
import difflib
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError


def compare_pdf(base,operations,reference):
    with open_pdf(base) as a,open_pdf(reference) as b:
        if any(not d.permissions & fitz.PDF_PERM_COPY for d in [a,b]):raise DocumentError('Ambos documentos deben permitir copiar su contenido para comparar.')
        if max(len(a),len(b))>20:raise DocumentError('Esta comparación admite hasta 20 páginas por documento. Extrae primero el tramo que quieras revisar.')
        total=0
        for doc in [a,b]:
            for p in doc:
                area=p.rect.width*p.rect.height;total+=area
                if area>3_000_000:raise DocumentError('Una página es demasiado grande para esta comparación.')
        if total>40_000_000:raise DocumentError('El lote de comparación supera el límite de 40 millones de píxeles a 72 ppp.')
    rows=[]
    with open_pdf(export_pdf(base,operations)) as a,open_pdf(reference) as b:
        counts=(len(a),len(b))
        for n in range(max(counts)):
            p=a[n] if n<len(a) else None;q=b[n] if n<len(b) else None
            ta=p.get_text(sort=True) if p else '';tb=q.get_text(sort=True) if q else ''
            if max(len(ta),len(tb))>100_000:raise DocumentError('Una página contiene demasiado texto para comparar.')
            ia=p.get_pixmap(alpha=False) if p else None;ib=q.get_pixmap(alpha=False) if q else None
            visual=not ia or not ib or ia.width!=ib.width or ia.height!=ib.height or ia.samples!=ib.samples
            textual=ta!=tb
            if visual or textual:
                changes=list(difflib.unified_diff(ta.splitlines(),tb.splitlines(),fromfile='Actual',tofile='Referencia',lineterm=''))
                previews=[]
                for page in [p,q]:
                    previews.append(base64.b64encode(page.get_pixmap(matrix=fitz.Matrix(min(310/page.rect.width,400/page.rect.height),min(310/page.rect.width,400/page.rect.height)),alpha=False).tobytes('png')).decode() if page else None)
                rows.append({'page':n,'visual_changed':bool(visual),'text_changed':textual,'diff':changes[:2000],'diff_truncated':len(changes)>2000,'previews':previews,'missing_current':p is None,'missing_reference':q is None})
    return {'current_pages':counts[0],'reference_pages':counts[1],'changes':rows,'changed_pages':len(rows)}
