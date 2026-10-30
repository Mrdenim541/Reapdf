from .page_labels import visible_labels,write_rules
"""Organización de copias: selección única, orden y rotación absoluta por página."""
import pymupdf as fitz
from .form_fields import select_pages
from .engine import open_pdf, export_pdf, DocumentError, MAX_PAGES


def organize_pdf(data, operations, pages, *, extract=False,partition_tags=False):
    with open_pdf(data) as source:
        if source.get_sigflags() > 0:
            raise DocumentError('No se organizan ni extraen PDF firmados en este prototipo.')
        required = fitz.PDF_PERM_COPY if extract else (fitz.PDF_PERM_ASSEMBLE | fitz.PDF_PERM_MODIFY)
        if not source.permissions & required:
            raise DocumentError('El documento no permite extraer páginas.' if extract else 'El documento no permite organizar páginas.')
        if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
            raise DocumentError('Conserva al menos una página y como máximo 500.')
        seen = set()
        for item in pages:
            if not isinstance(item, dict):
                raise DocumentError('Configuración de página no válida.')
            number, rotation = item.get('page'), item.get('rotation')
            if type(number) is not int or not 0 <= number < len(source):
                raise DocumentError('Página de origen no válida.')
            if type(rotation) is not int or rotation not in {0, 90, 180, 270}:
                raise DocumentError('La rotación debe ser 0, 90, 180 o 270 grados.')
            if number in seen:
                raise DocumentError('No se admiten páginas duplicadas en esta organización.')
            seen.add(number)
    edited = export_pdf(data, operations)
    with open_pdf(edited) as doc:
        has_labels = bool(doc.get_page_labels())
        labels = [visible_labels(doc)[item['page']] for item in pages] if has_labels else []
        # select actualiza destinos locales de enlaces/marcadores y conserva las
        # anotaciones. No se reconstruyen las páginas como imágenes.
        if partition_tags:
            from .structure_partition import partition
            partition(doc,[doc[item['page']].xref for item in pages])
        select_pages(doc, [item['page'] for item in pages])
        if partition_tags:
            # MuPDF select rewrites parent-tree keys; rebuild them against the
            # retained native page/annotation references before serializing.
            partition(doc,[p.xref for p in doc])
        for index, item in enumerate(pages):
            doc[index].set_rotation(item['rotation'])
        if has_labels:
            write_rules(doc,[{'startpage': i, 'prefix': label, 'style': ''}
                                 for i, label in enumerate(labels)])
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4, deflate=True)
