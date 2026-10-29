"""Native PDF review threads and bounded, copy-permission-aware review reports."""
from datetime import datetime,timezone
from uuid import uuid4
from io import StringIO
import csv,hashlib,json
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .existing_annotations import SUPPORTED,LOCKED
from .form_structure import pdf_string

STATES={'None':'Pendiente','Accepted':'Aceptado','Rejected':'Rechazado','Cancelled':'Cancelado','Completed':'Completado'}
MAX_COMMENTS=2000


def comment_model(doc):
    rows=[]
    for page in doc:
        for a in page.annots() or []:
            if len(rows)>=MAX_COMMENTS:raise DocumentError('La revisión admite hasta 2000 anotaciones por documento.')
            kind,parent=doc.xref_get_key(a.xref,'IRT');rt=doc.xref_get_key(a.xref,'RT')
            info=a.info;content=info.get('content','');author=info.get('title','');reason=''
            if doc.get_sigflags()>0 or not doc.permissions&f.PDF_PERM_ANNOTATE:reason='El documento no permite modificar comentarios.'
            elif a.type[0] not in SUPPORTED:reason='El tipo de anotación no es compatible con la revisión editable.'
            elif a.flags&LOCKED:reason='El comentario está bloqueado o es de solo lectura.'
            elif any(doc.xref_get_key(a.xref,key)[0]!='null' for key in ['A','AA','OC']):reason='El comentario contiene acciones o capas no compatibles.'
            elif len(content)>4000 or len(author)>100:reason='El comentario supera el límite editable de contenido o autor.'
            if kind not in ['xref','null'] or (kind=='xref' and rt not in [('null','null'),('name','/R')]):reason='Relación de comentario agrupada o no compatible.'
            model=doc.xref_get_key(a.xref,'StateModel');state=doc.xref_get_key(a.xref,'State')
            state_value=state[1].lstrip('/') if model==('string','Review') or model==('name','/Review') else None
            if state[0]=='string':state_value=state[1] if model in [('string','Review'),('name','/Review')] else None
            if (model[0]!='null' or state[0]!='null') and state_value not in STATES:reason='El registro usa un modelo o estado de revisión no compatible.'
            rows.append({'xref':a.xref,'page':page.number,'kind':a.type[0],'type':SUPPORTED.get(a.type[0],a.type[1]),
                'name':info.get('id','')[:200],'content':content[:4000],'author':author[:100],
                'created':info.get('creationDate','')[:100],'modified':info.get('modDate','')[:100],
                'rect':list(a.rect*page.rotation_matrix),'parent':int(parent.split()[0]) if kind=='xref' else None,
                'state':state_value if state_value in STATES else None,'truncated':len(content)>4000 or len(author)>100,'reason':reason})
    mapping={v['xref']:v for v in rows};roots={}
    for row in rows:
        node=row;seen=set();reason=row['reason'];depth=0
        while node['parent'] is not None:
            if node['xref'] in seen or depth>=16:reason='La conversación contiene un ciclo o supera 16 niveles.';break
            seen.add(node['xref']);target=mapping.get(node['parent'])
            if target is None:reason='La respuesta apunta a un comentario inexistente.';break
            node=target;depth+=1
        row.update(root=node['xref'],depth=depth,reason=reason);roots.setdefault(node['xref'],[]).append(row)
    for root,group in roots.items():
        reason=next((r['reason'] for r in group if r['reason']),'')
        if len({r['page'] for r in group})>1:reason='La conversación atraviesa páginas; se conserva sin editar.'
        status=next((r['state'] for r in reversed(group) if r['state']),'None')
        for row in group:
            row['editable']=not reason;row['reason']=reason;row['status']=status
            row['can_delete']=not reason and not row['state'] and row['kind']==f.PDF_ANNOT_TEXT and not any(v['parent']==row['xref'] for v in rows)
    return {'comments':rows,'threads':len(roots),'states':STATES}


def inspect_comments(base,operations):
    with open_pdf(export_pdf(base,operations)) as doc:return comment_model(doc)


def review_text(value,label,maximum,empty=False):
    if not isinstance(value,str) or len(value)>maximum or (not empty and not value.strip()) or any(ord(c)<32 and c not in ('\n\t' if label=='Contenido' else '') or ord(c)==127 for c in value):raise DocumentError(f'{label}: usa hasta {maximum} caracteres sin controles no compatibles.')
    return value


def edit_comment(base,operations,number,xref,action,content=None,author='',state=None):
    if type(number) is not int or type(xref) is not int or action not in ['update','reply','state','delete']:raise DocumentError('Comentario u operación no válidos.')
    with open_pdf(export_pdf(base,operations)) as doc:
        model=comment_model(doc);row=next((v for v in model['comments'] if v['xref']==xref and v['page']==number),None)
        if not row or not row['editable']:raise DocumentError(row['reason'] if row else 'El comentario no pertenece a esta versión del documento.')
        page=doc[number];root=next(v for v in model['comments'] if v['xref']==row['root'])
        now=datetime.now(timezone.utc).strftime('D:%Y%m%d%H%M%SZ')
        if action=='delete':
            if not row['can_delete']:raise DocumentError('Solo se eliminan notas o respuestas sin descendientes y sin estado de revisión.')
            page.delete_annot(page.load_annot(xref))
        elif action=='update':
            if row['state']:raise DocumentError('Los registros de estado se conservan; añade otro estado para actualizar la revisión.')
            text=review_text(content,'Contenido',4000,empty=row['kind']!=f.PDF_ANNOT_TEXT);author=review_text(author,'Autor',100,True)
            doc.xref_set_key(xref,'Contents',pdf_string(text));doc.xref_set_key(xref,'T',pdf_string(author));doc.xref_set_key(xref,'M',pdf_string(now))
        else:
            if len(model['comments'])>=MAX_COMMENTS:raise DocumentError('La revisión supera 2000 anotaciones.')
            author=review_text(author,'Autor',100,True)
            if action=='state':
                if state not in STATES:raise DocumentError('Estado de revisión no válido.')
                text='Estado de revisión: '+STATES[state]
            else:text=review_text(content,'Contenido',4000)
            parent=page.load_annot(root['xref'] if action=='state' else xref)
            bounds=page.rect*page.derotation_matrix
            point=f.Point(max(bounds.x0,min(parent.rect.x0+20,bounds.x1-22)),max(bounds.y0,min(parent.rect.y0+20,bounds.y1-22)))
            a=page.add_text_annot(point,text)
            a.set_info(title=author,creationDate=now,modDate=now)
            doc.xref_set_key(a.xref,'NM',pdf_string('Reapdf-'+uuid4().hex));doc.xref_set_key(a.xref,'IRT',f'{root["xref"] if action=="state" else xref} 0 R');doc.xref_set_key(a.xref,'RT','/R')
            if action=='state':
                # State and StateModel are PDF text strings (not names).
                doc.xref_set_key(a.xref,'StateModel','(Review)');doc.xref_set_key(a.xref,'State',pdf_string(state))
                a.set_flags((a.flags&~f.PDF_ANNOT_IS_PRINT)|f.PDF_ANNOT_IS_HIDDEN|f.PDF_ANNOT_IS_NO_VIEW)
            a.update()
        result=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(result) as check:comment_model(check)
    return result


def comment_report(base,operations,format='json'):
    if format not in ['json','csv']:raise DocumentError('Elige informe JSON o CSV.')
    with open_pdf(base) as source:
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite exportar comentarios.')
    snapshot=export_pdf(base,operations)
    with open_pdf(snapshot) as doc:model=comment_model(doc)
    report={'schema':'reapdf-review-1','source_sha256':hashlib.sha256(snapshot).hexdigest(),**model}
    if format=='json':return json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8')
    stream=StringIO(newline='');writer=csv.writer(stream)
    writer.writerow(['Página','Referencia','Raíz','Respuesta a','Tipo','Estado','Autor','Contenido','Creado','Modificado','Truncado'])
    def safe(value):
        value=str(value);return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
    for row in model['comments']:
        writer.writerow([safe(v) for v in [row['page']+1,row['xref'],row['root'],row['parent'] or '',row['type'],STATES[row['status']],row['author'],row['content'],row['created'],row['modified'],row['truncated']]])
    return ('\ufeff'+stream.getvalue()).encode('utf-8')
