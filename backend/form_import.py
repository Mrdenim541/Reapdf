"""Rebuild copied AcroForm ownership without joining independent documents."""
import pymupdf as fitz
from .engine import DocumentError
from .form_fields import _references, _array, set_form_key
from .form_structure import field_structure, reference, raw_key, pdf_string

MAX_SIGNATURE_CHARS = 2_000_000


def checked_structure(doc):
    widgets, rows, groups, reason = field_structure(doc)
    if reason:
        raise DocumentError('No se puede importar este formulario: ' + reason)
    names = [rows[members[0]]['name'] for members in groups.values()]
    if len(names) != len(set(names)):
        raise DocumentError('El formulario contiene nombres completos ambiguos.')
    return widgets, rows, groups


def node_snapshot(doc, rows):
    nodes = {n for row in rows.values() for n in row['chain']}
    return {n: {key: raw_key(doc, n, key) for key in doc.xref_get_keys(n)
                if key != 'P' and doc.xref_get_key(n, key)[0] != 'null'} for n in nodes}


def prepare_source(doc):
    """Make inherited document defaults explicit before grafting field trees."""
    widgets, rows, groups = checked_structure(doc)
    if not widgets:
        return rows
    # DA and Q are inheritable field attributes. Keep the source defaults when
    # the destination already has a different AcroForm default appearance.
    for root, _ in _references(doc, doc.pdf_catalog(), 'AcroForm/Fields'):
        if doc.xref_get_key(root, 'T')[0] != 'string' or not doc.xref_get_key(root, 'T')[1]:
            raise DocumentError('Los campos importados necesitan nombres raíz no vacíos.')
    for key in ['DA', 'Q']:
        kind, value = doc.xref_get_key(doc.pdf_catalog(), 'AcroForm/' + key)
        if kind == 'null':
            continue
        if (key == 'DA' and (kind != 'string' or len(value) > 2048)) or (key == 'Q' and (kind != 'int' or value not in ['0', '1', '2'])):
            raise DocumentError('El formulario tiene valores predeterminados no compatibles.')
        for root, _ in _references(doc, doc.pdf_catalog(), 'AcroForm/Fields'):
            if doc.xref_get_key(root, key)[0] == 'null':
                doc.xref_set_key(root, key, pdf_string(value) if kind == 'string' else value)
    return rows


def rebuild_imported_tree(output, incoming, source_rows, base_roots, base_rows, base_snapshot, first_xref, position):
    if not source_rows:
        return
    mapping = {}
    reverse = {}
    for local_page in range(len(incoming)):
        src_refs = [x for x, k, _ in incoming[local_page].annot_xrefs() if k == fitz.PDF_ANNOT_WIDGET]
        dst_refs = [x for x, k, _ in output[position + local_page].annot_xrefs() if k == fitz.PDF_ANNOT_WIDGET]
        if len(src_refs) != len(dst_refs):
            raise DocumentError('No se copiaron todos los campos; se canceló la importación.')
        for src, dst in zip(src_refs, dst_refs):
            chain = []
            node = dst
            while node is not None:
                if node < first_xref or node >= output.xref_length() or node in chain or len(chain) >= 16:
                    raise DocumentError('La copia de campos contiene referencias no independientes o un ciclo.')
                chain.append(node)
                node = reference(output, node, 'Parent')
            expected = source_rows[src]['chain']
            if len(chain) != len(expected):
                raise DocumentError('El árbol copiado no conserva la profundidad del origen.')
            for a, b in zip(expected, reversed(chain)):
                if (a in source_rows and a in mapping and mapping[a] != b) or (b in reverse and reverse[b] != a):
                    raise DocumentError('La copia no conserva los grupos compartidos del formulario.')
                # MuPDF can create several clones of the same source ancestor
                # when named Widgets coexist with shared logical fields. Use
                # one canonical clone per source xref, never per field name.
                mapping.setdefault(a, b)
                reverse[b] = a

    # Rebuild Kids from the validated source, including ancestors omitted from
    # the native target Fields array. Never follow stale cloned Kids pointers.
    for src, dst in mapping.items():
        parent = reference(incoming, src, 'Parent')
        output.xref_set_key(dst, 'Parent', f'{mapping[parent]} 0 R' if parent is not None else 'null')
        kids = _references(incoming, src, 'Kids')
        output.xref_set_key(dst, 'Kids', _array([(mapping[x], 0) for x, _ in kids]) if kids else 'null')
        # The native copier may rename promoted terminal fields. Restore source
        # names first; collisions are handled once at the imported root below.
        output.xref_set_key(dst, 'T', raw_key(incoming, src, 'T'))

    used_roots = {output.xref_get_key(x, 'T')[1] for x, _ in base_roots}
    used_names = {row['name'] for row in base_rows.values()}
    source_roots = _references(incoming, incoming.pdf_catalog(), 'AcroForm/Fields')
    for root, _ in source_roots:
        name = incoming.xref_get_key(root, 'T')[1]
        suffixes = {row['name'][len(name):] for row in source_rows.values() if row['chain'][0] == root}
        candidate = name
        number = 2
        while candidate in used_roots or any(candidate + suffix in used_names for suffix in suffixes):
            candidate = f'{name} ({number})'
            number += 1
        output.xref_set_key(mapping[root], 'T', pdf_string(candidate))
        used_roots.add(candidate)
        used_names.update(candidate + suffix for suffix in suffixes)
    set_form_key(output, 'Fields', _array([*base_roots, *[(mapping[x], 0) for x, _ in source_roots]]))
    if node_snapshot(output, base_rows) != base_snapshot:
        raise DocumentError('La copia alteró campos originales; se canceló la importación.')


def validate_result(data):
    # Reopen after garbage collection: duplicate Widgets or lost references
    # must not be accepted merely because the in-memory tree looked correct.
    with fitz.open(stream=data, filetype='pdf') as doc:
        checked_structure(doc)


def widget_signatures(doc, include_appearance=True, page_numbers=None):
    """Semantic field attributes and encoded appearance bytes, without names/xrefs."""
    from hashlib import sha256
    native = fitz.mupdf
    digests = {}
    def appearance(xref):
        obj = native.pdf_load_object(fitz._as_pdf_document(doc), xref)
        ap = native.pdf_dict_gets(obj, 'AP')
        result = []
        for mode in ['N', 'R', 'D']:
            value = native.pdf_dict_gets(ap, mode)
            if native.pdf_is_null(value):
                result.append((mode, None));continue
            def stream_digest(stream):
                if not native.pdf_is_stream(stream):
                    raise DocumentError('Una apariencia de campo no contiene un flujo compatible.')
                ref = native.pdf_to_num(stream)
                if ref not in digests:digests[ref] = sha256(doc.xref_stream_raw(ref)).hexdigest()
                return digests[ref]
            if native.pdf_is_stream(value):
                result.append((mode, stream_digest(value)))
            elif native.pdf_is_dict(value):
                if native.pdf_dict_len(value) > 500:
                    raise DocumentError('La apariencia supera 500 estados por campo.')
                result.append((mode, tuple(sorted((native.pdf_to_name(native.pdf_dict_get_key(value, i)),
                                                  stream_digest(native.pdf_dict_get_val(value, i)))
                                                 for i in range(native.pdf_dict_len(value))))))
            else:
                raise DocumentError('La apariencia del campo tiene una estructura no compatible.')
        return tuple(result)
    result = []
    characters = 0
    for number in range(len(doc)) if page_numbers is None else page_numbers:
        page = doc[number]
        entries = []
        for xref, kind, _ in page.annot_xrefs():
            if kind != fitz.PDF_ANNOT_WIDGET:continue
            w = page.load_widget(xref)
            value, label, options = w.field_value, w.field_label, w.choice_values
            if any(isinstance(v, str) and len(v) > 2000 for v in [value, label]) or (options and (len(options) > 500 or any(not isinstance(v, str) or len(v) > 2000 for option in options for v in (option if isinstance(option, (list, tuple)) else [option])))):
                raise DocumentError('La copia admite hasta 2000 caracteres por valor/etiqueta y 500 opciones por campo.')
            attrs = (w.field_type, value, w.field_flags, tuple(round(v, 4) for v in w.rect),
                     label, w.text_font, w.text_fontsize, w.text_maxlen, options,
                     w.border_color, w.fill_color, w.border_width, w.text_color)
            characters += len(repr(attrs))
            if characters > MAX_SIGNATURE_CHARS:
                raise DocumentError('Los datos de formulario superan el límite de esta copia.')
            entries.append((attrs, appearance(xref) if include_appearance else None))
        result.append(entries)
    return result


def verify_imported_fields(doc, expected, position, include_appearance=True):
    actual = widget_signatures(doc, include_appearance, range(position, position + len(expected)))
    compare = expected if include_appearance else [[(attrs, None) for attrs, _ in entries] for entries in expected]
    if actual != compare:
        raise DocumentError('No se conservaron los valores, propiedades o apariencias del formulario importado.')
