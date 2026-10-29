from .page_labels import visible_labels,write_rules
"""Inserción de páginas con destinos explícitos y campos independientes."""
import copy
import re
import pymupdf as fitz
from .form_fields import select_pages, _references
from .form_import import checked_structure, prepare_source, node_snapshot, rebuild_imported_tree, validate_result, widget_signatures, verify_imported_fields
from .engine import open_pdf, export_pdf, DocumentError, MAX_PAGES


def _check_bookmarks(doc):
    toc = doc.get_toc(False)
    if any(row[3].get('kind') not in {fitz.LINK_NONE, fitz.LINK_GOTO, fitz.LINK_URI} for row in toc):
        raise DocumentError('Este prototipo no combina marcadores con acciones especiales. Usa otro documento por ahora.')
    return toc


def _check_source(doc):
    if doc.get_ocgs():
        raise DocumentError('La importación de PDF con capas todavía no está admitida; no se modificó el documento abierto.')
    if doc.xref_get_key(doc.pdf_catalog(), 'AcroForm/XFA')[0] != 'null':
        raise DocumentError('Los formularios XFA todavía no se pueden importar.')
    calc_kind, calc_value = doc.xref_get_key(doc.pdf_catalog(), 'AcroForm/CO')
    if calc_kind == 'xref':
        calc_value = doc.xref_object(int(calc_value.split()[0]))
    if calc_kind != 'null' and re.sub(r'\s', '', calc_value) != '[]':
        raise DocumentError('Los formularios con cálculos o scripts requieren una validación adicional antes de importarlos.')
    _, structure, _ = checked_structure(doc)
    nodes={n for row in structure.values() for n in row['chain']}
    if nodes:
        from .forms import special_form
        if special_form(doc) or any(doc.xref_get_key(n,key)[0]!='null' for n in nodes for key in ['AA','A','OC']):
            raise DocumentError('Los formularios con acciones o scripts todavía no se pueden importar.')
    for page in doc:
        for widget in page.widgets() or []:
            if widget.field_type==fitz.PDF_WIDGET_TYPE_SIGNATURE:raise DocumentError('No se copian campos de firma digital.')
            if any(getattr(widget, name, None) for name in
                   ['script', 'script_calc', 'script_change', 'script_format', 'script_stroke', 'script_blur', 'script_focus']):
                raise DocumentError('Los formularios con scripts requieren una validación adicional antes de importarlos.')


def _link_style(doc, xref):
    style = {}
    for key in ['C', 'Border', 'BS', 'H', 'F']:
        kind, value = doc.xref_get_key(xref, key)
        if kind == 'null':
            continue
        if kind == 'xref':
            value = doc.xref_object(int(value.split()[0]))
        if re.search(r'\b\d+\s+\d+\s+R\b', value):
            raise DocumentError('El PDF contiene un estilo de enlace con referencias que todavía no se puede importar.')
        style[key] = value
    return style


def _incoming_links(doc):
    result = []
    for page in doc:
        entries = []
        for link in page.get_links():
            if link['kind'] not in {fitz.LINK_GOTO, fitz.LINK_URI}:
                raise DocumentError('Solo se importan enlaces internos directos y enlaces web; este PDF contiene otro tipo de enlace.')
            data = {'kind': link['kind'], 'from': link['from'] * page.derotation_matrix}
            if link['kind'] == fitz.LINK_GOTO:
                target = link.get('page', -1)
                if not 0 <= target < len(doc):
                    raise DocumentError('El PDF contiene un enlace interno sin destino válido.')
                # get_links entrega coordenadas visibles; insert_link requiere las
                # coordenadas sin rotación tanto en el origen como en el destino.
                data.update(page=target, to=link.get('to', fitz.Point(0, 0)) * doc[target].derotation_matrix,
                            zoom=link.get('zoom', 0))
            else:
                data['uri'] = link['uri']
            entries.append((data, _link_style(doc, link['xref'])))
        result.append(entries)
    return result


def merge_pdf(base_data, operations, incoming_data, pages, position, source_name='Documento insertado', *, replace_count=0):
    with open_pdf(base_data) as base, open_pdf(incoming_data) as incoming:
        if base.get_sigflags() > 0 or incoming.get_sigflags() > 0:
            raise DocumentError('No se combinan documentos con indicadores de firma en este prototipo.')
        if not base.permissions & (fitz.PDF_PERM_ASSEMBLE | fitz.PDF_PERM_MODIFY):
            raise DocumentError('El documento abierto no permite insertar páginas.')
        if not incoming.permissions & fitz.PDF_PERM_COPY:
            raise DocumentError('El documento de origen no permite copiar páginas.')
        if type(position) is not int or not 0 <= position <= len(base):
            raise DocumentError('Posición de inserción no válida.')
        if type(replace_count) is not int or not 0 <= replace_count <= len(base)-position:
            raise DocumentError('Cantidad de páginas a reemplazar no válida.')
        if not isinstance(pages, list) or not pages or len(pages) + len(base) - replace_count > MAX_PAGES:
            raise DocumentError('Selecciona páginas sin superar el límite de 500 páginas del resultado.')
        if any(type(number) is not int or not 0 <= number < len(incoming) for number in pages):
            raise DocumentError('Página de origen no válida.')
        if len(set(pages)) != len(pages):
            raise DocumentError('No se admiten páginas repetidas en la selección.')
        if not isinstance(source_name, str) or not 1 <= len(source_name.strip()) <= 200:
            raise DocumentError('Nombre de origen no válido.')
        if base.xref_get_key(base.pdf_catalog(), 'AcroForm/XFA')[0] != 'null':
            raise DocumentError('La inserción en formularios XFA todavía no está admitida.')
        if replace_count:
            _check_source(base)
            _incoming_links(base)  # La eliminación de destinos especiales no está validada.
        _check_bookmarks(base)
        _check_bookmarks(incoming)
        _check_source(incoming)
        incoming_labels = [visible_labels(incoming)[number] for number in pages]
        incoming_has_labels = bool(incoming.get_page_labels())
        select_pages(incoming, pages)
        source_rows = prepare_source(incoming)
        source_fields = widget_signatures(incoming) if source_rows else []
        links = _incoming_links(incoming)
        incoming_toc = _check_bookmarks(incoming)
        edited = export_pdf(base_data, operations)
        with open_pdf(edited) as output:
            labels = visible_labels(output)
            has_labels = bool(output.get_page_labels()) or incoming_has_labels
            base_roots = _references(output, output.pdf_catalog(), 'AcroForm/Fields')
            base_rows = checked_structure(output)[1] if source_rows else {}
            before_fields = node_snapshot(output, base_rows)
            first_xref = output.xref_length()
            output.insert_pdf(incoming, start_at=position, links=False, annots=True,
                              widgets=True, join_duplicates=False)
            rebuild_imported_tree(output, incoming, source_rows, base_roots, base_rows, before_fields, first_xref, position)
            # El motor remapea los destinos de los enlaces y marcadores del PDF base.
            # Los enlaces importados se reconstruyen para evitar su doble rotación.
            for local_page, entries in enumerate(links):
                for data, _ in entries:
                    link = copy.copy(data)
                    if link['kind'] == fitz.LINK_GOTO:
                        link['page'] += position
                    output[position + local_page].insert_link(link)
                target = output.reload_page(output[position + local_page])
                copied_links = target.get_links()
                if len(copied_links) != len(entries):
                    raise DocumentError('No se pudieron verificar todos los enlaces de origen; se canceló la inserción.')
                for copied, (_, style) in zip(copied_links, entries):
                    for key, raw in style.items():
                        output.xref_set_key(copied['xref'], key, raw)
            if incoming_toc:
                toc = output.get_toc(False)
                toc.append([1, source_name.strip(), position + 1])
                for row in incoming_toc:
                    row = copy.deepcopy(row)
                    row[0] += 1
                    if row[3]['kind'] == fitz.LINK_GOTO:
                        row[2] += position
                        row[3]['page'] += position
                    toc.append(row)
                output.set_toc(toc)
            labels[position:position] = incoming_labels
            if replace_count:
                # El bloque nuevo precede al antiguo; retirar las páginas originales
                # antes de serializar, incluso si la copia intermedia supera 500.
                removed = range(position+len(pages), position+len(pages)+replace_count)
                retained = [n for n in range(len(output)) if n not in removed]
                select_pages(output, retained)
                labels = [labels[n] for n in retained]
            if has_labels:
                write_rules(output,[{'startpage': i, 'prefix': label, 'style': ''}
                                        for i, label in enumerate(labels)])
            # Inserted widgets need their actual page reference before garbage
            # collection can deduplicate otherwise identical PDF dictionaries.
            for page in output:
                for xref,kind,_ in page.annot_xrefs():
                    if kind==fitz.PDF_ANNOT_WIDGET:output.xref_set_key(xref,'P',f'{page.xref} 0 R')
            if source_rows:verify_imported_fields(output, source_fields, position)
            result = output.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4, deflate=True)
            if source_rows or replace_count:validate_result(result)
            if source_rows:
                with open_pdf(result) as verified:verify_imported_fields(verified, source_fields, position, include_appearance=False)
            return result
