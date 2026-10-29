"""Read-only, paginated structural review. This is not PDF/A or forensic validation."""
import pymupdf as fitz
from .engine import DocumentError, export_pdf, open_pdf
from .page_labels import visible_labels

BATCH_SIZE = 20
MAX_XREFS = 100_000
MAX_PAGE_OBJECTS = 2000


def review_document(data, operations, offset=0, limit=BATCH_SIZE):
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= BATCH_SIZE:
        raise DocumentError('La revisión admite lotes de 1 a 20 páginas y una posición válida.')
    edited = export_pdf(data, operations)
    with open_pdf(edited) as doc:
        if offset >= len(doc):
            raise DocumentError('La posición de revisión queda fuera del documento.')
        if doc.xref_length() > MAX_XREFS:
            raise DocumentError('El documento supera el límite de objetos de esta revisión.')
        labels = visible_labels(doc)
        rows = []
        for number in range(offset, min(offset + limit, len(doc))):
            page = doc[number]
            # Count annotation/widget references without exposing field values or comments.
            refs = page.annot_xrefs()
            if len(refs) > MAX_PAGE_OBJECTS:
                raise DocumentError(f'La página {number + 1} supera el límite de anotaciones de la revisión.')
            widgets = sum(kind == fitz.PDF_ANNOT_WIDGET for _, kind, _ in refs)
            annotations = sum(kind not in {fitz.PDF_ANNOT_WIDGET, fitz.PDF_ANNOT_LINK, fitz.PDF_ANNOT_POPUP} for _, kind, _ in refs)
            links = len(page.get_links())
            images = len(page.get_images(full=True))
            fonts = page.get_fonts(full=True)
            if max(links, images, len(fonts)) > MAX_PAGE_OBJECTS:
                raise DocumentError(f'La página {number + 1} supera el límite de recursos de la revisión.')
            # No image payloads, pixels, font programs or extracted text leave this endpoint.
            # TEXTFLAGS_TEXT excludes image decoding; text presence is only a heuristic.
            has_text = bool(page.get_text('text', flags=fitz.TEXTFLAGS_TEXT).strip())
            rows.append({'page': number, 'label': labels[number],
                         'width': round(page.rect.width, 2), 'height': round(page.rect.height, 2),
                         'rotation': page.rotation, 'has_text': has_text,
                         'images': images, 'fonts': len(fonts), 'annotations': annotations,
                         'fields': widgets, 'links': links,
                         'ocr_candidate': not has_text and images > 0})
        return {'pages': rows, 'total_pages': len(doc), 'next_offset': offset + len(rows) if offset + len(rows) < len(doc) else None,
                'signed': doc.get_sigflags() > 0, 'layers': len(doc.get_ocgs()),
                'attachments': doc.embfile_count(),
                'permissions': {name: bool(doc.permissions & flag) for name, flag in
                                [('edit', fitz.PDF_PERM_MODIFY), ('annotate', fitz.PDF_PERM_ANNOTATE),
                                 ('copy', fitz.PDF_PERM_COPY), ('fill', fitz.PDF_PERM_FORM),
                                 ('organize', fitz.PDF_PERM_ASSEMBLE)]}}
