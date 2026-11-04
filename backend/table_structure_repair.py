"""Repair existing standard table cell roles/spans without rewriting page content."""
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf
from .document_tools import editable
from .structure_scope import attributes


def inspect_table(doc,identity):
    if type(identity) is not int:raise DocumentError('Identificador de tabla no válido.')
    from .structure_editing import model
    tree=model(doc.tobytes(),[]);nodes={r['id']:r for r in tree['nodes'] if r['id']}
    table=nodes.get(identity)
    if not table or table['raw_role']!='Table' or table['role']!='Table' or not table['parent_valid']:raise DocumentError('Selecciona una tabla estándar existente con padre válido.')
    def children(row,allowed):
        ids=row['children']
        if not ids or len(ids)>500:raise DocumentError('La tabla necesita hijos estructurales indirectos compatibles.')
        result=[]
        for ref in ids:
            child=nodes.get(ref)
            if not child or not child['parent_valid'] or child['parent']!=row['id'] or child['raw_role']!=child['role'] or child['role'] not in allowed or doc.xref_get_key(ref,'NS')[0]!='null':raise DocumentError('La tabla contiene roles, padres o espacios de nombres que requieren reparación especializada.')
            result.append(child)
        return result
    groups=[];direct=[]
    for child in children(table,{'TR','THead','TBody','TFoot'}):
        if child['role']=='TR':direct.append(child)
        else:
            if direct:groups.append(direct);direct=[]
            groups.append(children(child,{'TR'}))
    if direct:groups.append(direct)
    rows=[]
    for group_index,group in enumerate(groups):
        for row in group:
            cells=[]
            for cell in children(row,{'TH','TD'}):
                if doc.xref_get_key(cell['id'],'C')[0]!='null':raise DocumentError('Los atributos por clases requieren revisión antes de reparar esta tabla.')
                n,_,_,index,parts=attributes(doc,cell['id']);a=parts[index] if index is not None else None;values={}
                for key in ['RowSpan','ColSpan']:
                    value=n.pdf_dict_gets(a,key) if a is not None else None
                    if value is None or n.pdf_is_null(value):values[key]=1
                    elif n.pdf_is_int(value) and 1<=n.pdf_to_int(value)<=100:values[key]=n.pdf_to_int(value)
                    else:raise DocumentError('La tabla tiene un intervalo de celdas no compatible.')
                scope=n.pdf_dict_gets(a,'Scope') if a is not None else None
                scope=n.pdf_to_name(scope) if scope is not None and n.pdf_is_name(scope) else ''
                if scope and scope not in ['Row','Column','Both']:raise DocumentError('La tabla tiene un alcance de cabecera desconocido.')
                cells.append({'id':cell['id'],'role':cell['role'],'rowspan':values['RowSpan'],'colspan':values['ColSpan'],'scope':scope or ('Column' if cell['role']=='TH' else '')})
            rows.append({'id':row['id'],'group':group_index,'cells':cells})
    if len(rows)>100 or sum(len(r['cells']) for r in rows)>500:raise DocumentError('Hasta 100 filas y 500 celdas por reparación.')
    return {'id':identity,'rows':rows,'page':table['page']}


def grid(table):
    occupied=set();widths=[];groups={r['group']:sum(v['group']==r['group'] for v in table['rows']) for r in table['rows']};group_rows={}
    for i,row in enumerate(table['rows']):
        local=group_rows.get(row['group'],0);group_rows[row['group']]=local+1;column=0
        for cell in row['cells']:
            while (i,column) in occupied:column+=1
            if local+cell['rowspan']>groups[row['group']] or column+cell['colspan']>100:raise DocumentError('Una celda combinada sale de su grupo de filas o supera 100 columnas.')
            points={(r,c) for r in range(i,i+cell['rowspan']) for c in range(column,column+cell['colspan'])}
            if points&occupied:raise DocumentError('Las celdas combinadas se solapan.')
            occupied|=points;column+=cell['colspan']
        used=[c for r,c in occupied if r==i];width=max(used,default=-1)+1
        if set(used)!=set(range(width)):raise DocumentError('La tabla deja huecos sin celdas etiquetadas.')
        widths.append(width)
    if not widths or not widths[0] or len(set(widths))!=1:raise DocumentError('Las filas deben cubrir el mismo número de columnas.')
    return widths[0]


def inspect(base,ops,identity):
    with open_pdf(export_pdf(base,ops)) as doc:
        table=inspect_table(doc,identity)
        try:table['columns']=grid(table);table['grid_issue']=''
        except DocumentError as e:table['columns']=None;table['grid_issue']=str(e)
        return table


def repair(base,ops,identity,cells,reviewed=False):
    if reviewed is not True:raise DocumentError('Revisa los roles, combinaciones y alcances de todas las celdas antes de guardar.')
    if not isinstance(cells,list) or not 1<=len(cells)<=500:raise DocumentError('Revisa entre 1 y 500 celdas existentes.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        table=inspect_table(doc,identity);original=[c for r in table['rows'] for c in r['cells']]
        if len(cells)!=len(original):raise DocumentError('La selección de celdas cambió; vuelve a preparar la tabla.')
        for old,new in zip(original,cells):
            if not isinstance(new,dict) or set(new)!={'id','role','rowspan','colspan','scope'} or new['id']!=old['id'] or type(new['id']) is not int or new['role'] not in ['TH','TD'] or any(type(new[k]) is not int or not 1<=new[k]<=100 for k in ['rowspan','colspan']) or new['scope'] not in (['Row','Column','Both'] if new['role']=='TH' else ['']):raise DocumentError('Propiedades de celda no válidas u obsoletas.')
            if old['role']=='TH' and new['role']=='TD':
                # Existing explicit header associations must not become dangling.
                if doc.xref_get_key(old['id'],'ID')[0]!='null':raise DocumentError('La cabecera tiene un identificador que puede usarse en asociaciones; conserva TH.')
            old.update(new)
        columns=grid(table)
        for cell in original:
            n,pdf,node,index,parts=attributes(doc,cell['id']);a=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(parts[index])) if index is not None else n.pdf_new_dict(pdf,4)
            n.pdf_dict_puts(a,'O',n.pdf_new_name('Table'));n.pdf_dict_puts(a,'RowSpan',n.pdf_new_int(cell['rowspan']));n.pdf_dict_puts(a,'ColSpan',n.pdf_new_int(cell['colspan']))
            if cell['role']=='TH':n.pdf_dict_puts(a,'Scope',n.pdf_new_name(cell['scope']))
            else:n.pdf_dict_dels(a,'Scope')
            n.pdf_dict_puts(node,'S',n.pdf_new_name(cell['role']))
            if not parts or len(parts)==1 and index==0:n.pdf_dict_puts(node,'A',a)
            else:
                array=n.pdf_new_array(pdf,len(parts)+1)
                for i,part in enumerate(parts):n.pdf_array_push(array,a if i==index else part)
                if index is None:n.pdf_array_push(array,a)
                n.pdf_dict_puts(node,'A',array)
        # Keep xrefs stable for a direct structural re-read before compacting.
        result=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,deflate=True)
    saved=inspect(result,[],identity)
    if saved['grid_issue'] or [c for r in saved['rows'] for c in r['cells']]!=cells:raise DocumentError('La tabla guardada no coincide con la reparación revisada.')
    return result,{'rows':len(table['rows']),'columns':columns,'cells':len(cells),'visible_content_changed':False}
