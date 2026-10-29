"""Bounded export of explicit HTTP(S) links on complete PDF text spans."""
import pymupdf as f
from .engine import DocumentError
from .content_tools import safe_web_url


def page_links(page):
    matrix=page.derotation_matrix;links=page.get_links()
    if len(links)>200:raise DocumentError('Word admite hasta 200 enlaces por página.')
    rows=[];skipped=[]
    for item in links:
        if item['kind']!=f.LINK_URI:
            skipped.append({'reason':'Destino interno, archivo o acción no web: no se convierte en hipervínculo.'});continue
        try:uri=safe_web_url(item.get('uri'))
        except DocumentError:
            skipped.append({'reason':'Dirección web no compatible: no se convierte en hipervínculo.'});continue
        rows.append({'rect':f.Rect(item['from'])*matrix,'uri':uri,'used':False,'partial':False})
    return rows,skipped


def span_link(span,links):
    rect=f.Rect(span['bbox']);matches=[]
    for item in links:
        if (rect&item['rect']).get_area()<=.1:continue
        if (item['rect']+(-.5,-.5,.5,.5)).contains(rect):matches.append(item)
        else:item['partial']=True
    if len(matches)!=1:
        for item in matches:item['partial']=True
        return None
    matches[0]['used']=True
    return matches[0]['uri']
