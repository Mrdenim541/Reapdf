"""Conservative image and ruled-table extraction for reflowable Word exports."""
import re
import pymupdf as f
from .engine import DocumentError

MAX_IMAGES=100
MAX_PIXELS=20_000_000
MAX_MEDIA_BYTES=20*1024*1024
MAX_TABLES=50
MAX_CELLS=5000


def page_tables(page,budget):
    if max(page.rect.width,page.rect.height)>4000 or len(page.get_drawings())>20000:
        raise DocumentError('La página supera los límites de detección de tablas para Word.')
    result=[];skipped=[];text_blocks=page.get_text('dict',flags=f.TEXTFLAGS_TEXT)['blocks']
    # Work in the same unrotated coordinates as text and embedded images.
    rotation=page.rotation
    try:
        page.set_rotation(0)
        finder=page.find_tables(strategy='lines_strict')
        for table in finder.tables:
            rows=table.extract();box=f.Rect(table.bbox)
            reason=''
            if not rows or table.row_count<2 or table.col_count<2:reason='Tabla sin cuadrícula suficiente.'
            elif any(cell is None for row in table.rows for cell in row.cells):reason='Tabla con celdas combinadas o estructura irregular.'
            elif any(box.intersects(t['rect']) for t in result):reason='Tablas superpuestas.'
            else:
                # A span crossing the table boundary must remain in the text.
                for block in text_blocks:
                    for line in block.get('lines',[]):
                        for span in line['spans']:
                            r=f.Rect(span['bbox'])
                            if r.intersects(box) and not (box+(-1,-1,1,1)).contains(r):reason='Texto que cruza el límite de la tabla.'
            if reason:skipped.append({'bbox':list(box),'reason':reason});continue
            budget['tables']+=1;budget['cells']+=sum(len(row) for row in rows)
            if budget['tables']>MAX_TABLES or budget['cells']>MAX_CELLS:raise DocumentError('Word admite hasta 50 tablas y 5000 celdas por exportación.')
            result.append({'rect':box,'bbox':list(box),'rows':[[v or '' for v in row] for row in rows]})
    finally:page.set_rotation(rotation)
    return result,skipped


def page_images(page,budget):
    result=[];skipped=[]
    doc=page.parent
    direct={image[0] for image in page.get_images(full=True) if image[-1]==0}
    complex_page=doc.xref_get_key(page.xref,'Resources/ExtGState')[0]!='null' or bool(re.search(rb'(?:^|\s)W\*?(?=\s)',page.read_contents()))
    for info in page.get_image_info(xrefs=True):
        budget['images_seen']+=1
        if budget['images_seen']>MAX_IMAGES:raise DocumentError('Word admite hasta 100 posiciones de imagen por exportación.')
        rect=f.Rect(info['bbox']);a,b,c,d,_,_=info['transform'];xref=info.get('xref',0);reason=''
        if min(info['width'],info['height'])<=1:reason='Imagen mínima o auxiliar de máscara.'
        elif not xref or xref not in direct:reason='Imagen en línea o dentro de una estructura gráfica.'
        elif complex_page or doc.xref_get_key(xref,'OC')[0]!='null':reason='Página o imagen con recortes, capas o transparencia especial.'
        elif abs(b)>1e-5 or abs(c)>1e-5 or a<=0 or d<=0:reason='Imagen girada, reflejada o inclinada internamente.'
        elif rect.is_empty or not (page.rect*page.derotation_matrix).contains(rect):reason='Imagen recortada por el límite de página.'
        elif info['width']*info['height']>MAX_PIXELS:reason='Imagen de más de 20 millones de píxeles.'
        if reason:skipped.append({'bbox':list(rect),'reason':reason});continue
        doc=page.parent;image=doc.extract_image(xref)
        if not image:skipped.append({'bbox':list(rect),'reason':'Recurso de imagen no extraíble.'});continue
        data=image['image'];ext=image['ext']
        if len(data)>MAX_MEDIA_BYTES:raise DocumentError('La imagen supera el presupuesto de 20 MB para Word.')
        # Native masks and non-Office encodings become an RGB(A) PNG.
        if image.get('smask') or ext not in ['png','jpeg'] or image.get('colorspace')!=3:
            pix=f.Pixmap(doc,xref)
            if pix.colorspace is None:skipped.append({'bbox':list(rect),'reason':'Máscara de imagen sin espacio de color.'});continue
            if pix.colorspace.n!=3:pix=f.Pixmap(f.csRGB,pix)
            if image.get('smask'):
                mask=f.Pixmap(doc,image['smask'])
                if pix.width!=mask.width or pix.height!=mask.height:skipped.append({'bbox':list(rect),'reason':'Máscara con dimensiones incompatibles.'});continue
                if pix.alpha:pix=f.Pixmap(pix,0)
                pix=f.Pixmap(pix,mask)
            data=pix.tobytes('png');ext='png'
        budget['media_bytes']+=len(data)
        if budget['media_bytes']>MAX_MEDIA_BYTES:raise DocumentError('Las imágenes superan 20 MB para esta exportación Word.')
        result.append({'rect':rect,'bbox':list(rect),'data':data,'ext':ext,'width':info['width'],'height':info['height']})
    return result,skipped
