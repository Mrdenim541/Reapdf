"""Mantener el árbol AcroForm al seleccionar un subconjunto de páginas."""
import re
from .engine import DocumentError

_REFERENCE = re.compile(r'(\d+)\s+(\d+)\s+R')


def _references(doc, xref, key):
    kind, raw = doc.xref_get_key(xref, key)
    if kind == 'null':
        return []
    if kind == 'xref':
        raw = doc.xref_object(int(raw.split()[0]))
    raw = raw.strip()
    if not raw.startswith('[') or not raw.endswith(']') or _REFERENCE.sub('', raw[1:-1]).strip():
        raise DocumentError('El formulario contiene una estructura de campos que todavía no se puede reorganizar.')
    return [(int(match[0]), int(match[1])) for match in _REFERENCE.findall(raw)]


def _array(refs):
    return '[' + ' '.join(f'{number} {generation} R' for number, generation in refs) + ']'


def set_form_key(doc, key, value):
    """Write directly to an indirect AcroForm, avoiding nested setter corruption."""
    kind, raw = doc.xref_get_key(doc.pdf_catalog(), 'AcroForm')
    if kind == 'xref':
        doc.xref_set_key(int(raw.split()[0]), key, value)
    elif kind == 'dict':
        doc.xref_set_key(doc.pdf_catalog(), 'AcroForm/' + key, value)
    else:
        raise DocumentError('El diccionario del formulario no es compatible.')


def select_pages(doc, pages):
    catalog = doc.pdf_catalog()
    form_kind, form_value = doc.xref_get_key(catalog, 'AcroForm')
    if form_kind == 'null':
        doc.select(pages)
        return
    if doc.xref_get_key(catalog, 'AcroForm/XFA')[0] != 'null':
        raise DocumentError('Los formularios XFA todavía no se pueden reorganizar.')
    roots = _references(doc, catalog, 'AcroForm/Fields')
    calculations = _references(doc, catalog, 'AcroForm/CO')
    # MuPDF may clear Kids arrays while rearranging recently imported fields.
    # Snapshot the topology before invoking it; reading Kids afterwards can lose
    # retained widgets even though their page annotations and Parent survive.
    children_before = {}
    def remember(xref, path):
        if xref in path or len(path) > 100 or len(children_before) > 10000:
            raise DocumentError('La estructura del formulario es demasiado compleja o contiene un ciclo.')
        if xref in children_before:return
        children_before[xref] = _references(doc, xref, 'Kids')
        for child, _ in children_before[xref]:remember(child, path | {xref})
    for root, _ in roots:remember(root, set())
    # MuPDF select elimina AcroForm del catálogo; las anotaciones Widget permanecen.
    doc.select(pages)
    widgets = {widget.xref for page in doc for widget in page.widgets() or []}
    retained = set()
    visited = set()

    def keep(ref, path):
        xref = ref[0]
        if xref in path or len(path) > 100 or len(visited) > 10000:
            raise DocumentError('La estructura del formulario es demasiado compleja o contiene un ciclo.')
        visited.add(xref)
        kids = children_before[xref]
        if kids:
            children = [kid for kid in kids if keep(kid, path | {xref})]
            if not children and xref not in widgets:
                return False
            doc.xref_set_key(xref, 'Kids', _array(children))
        elif xref not in widgets and doc.xref_get_key(xref, 'Subtype')[1] == '/Widget':
            return False
        # Los campos lógicos sin Widget ni página se mantienen como datos del formulario.
        retained.add(xref)
        return True

    roots = [root for root in roots if keep(root, set())]
    if roots:
        doc.xref_set_key(catalog, 'AcroForm', form_value)
        set_form_key(doc, 'Fields', _array(roots))
        if calculations:
            set_form_key(doc, 'CO', _array([ref for ref in calculations if ref[0] in retained]))
        normalize_selected_radios(doc)



def normalize_selected_radios(doc):
    """A copied/extracted group cannot keep a value for an option it lost."""
    from .form_structure import field_structure,button_states
    _,structure,groups,reason=field_structure(doc)
    if reason:return
    for owner,members in groups.items():
        first=structure[members[0]];page=doc[first['page']];widget=page.load_widget(members[0])
        if widget.field_type!=5 or owner==members[0]:continue
        states=[button_states(doc,xref) for xref in members]
        if any(s is None for s in states):continue
        for key in ['V','DV']:
            kind,value=doc.xref_get_key(owner,key)
            if kind=='name' and value not in ['/Off',*['/'+s for s in states]]:
                doc.xref_set_key(owner,key,'/Off')
                if key=='V':
                    for xref in members:doc.xref_set_key(xref,'AS','/Off')
