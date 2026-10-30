"""Read-only extraction of bounded digital/scanned table regions with editable grids."""
import csv,math
from io import StringIO
from bisect import bisect_right
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .ocr import ocr_status,TESSDATA


def boundaries(values,start,end,limit):
    if not isinstance(values,list) or not 2<=len(values)<=limit+1 or any(not finite(v) for v in values) or abs(values[0]-start)>.5 or abs(values[-1]-end)>.5 or any(b-a<3 for a,b in zip(values,values[1:])):raise DocumentError('La cuadrícula necesita separadores ordenados, de al menos 3 pt, dentro de la región.')
    return values


def detect_lines(pix,box):
    if pix.n!=1:raise DocumentError('La detección requiere una imagen gris.')
    width,height=pix.width,pix.height;mask=pix.samples.translate(bytes(1 if i<110 else 0 for i in range(256)))
    def centers(scores,extent,offset):
        hits=[i for i,v in enumerate(scores) if v>=.65];groups=[]
        for i in hits:
            if groups and i-groups[-1][-1]<=2:groups[-1].append(i)
            else:groups.append([i])
        return [offset+(sum(g)/len(g)+.5)*extent/len(scores) for g in groups]
    xs=centers([sum(mask[x::width])/height for x in range(width)],box.width,box.x0)
    ys=centers([sum(mask[y*width:(y+1)*width])/width for y in range(height)],box.height,box.y0)
    def edges(found,start,end,limit):
        inside=[p for p in found if p>start+3 and p<end-3]
        if len(inside)>limit-1:raise DocumentError('La región supera el número de separadores permitido.')
        return [start,*inside,end]
    return edges(xs,box.x0,box.x1,30),edges(ys,box.y0,box.y1,100),len(xs)>=2 and len(ys)>=2


def remove_lines(pix):
    width,height=pix.width,pix.height;raw=pix.samples;mask=raw.translate(bytes(1 if i<110 else 0 for i in range(256)));clean=bytearray(raw)
    horizontal=[y for y in range(height) if sum(mask[y*width:(y+1)*width])/width>=.65]
    vertical=[x for x in range(width) if sum(mask[x::width])/height>=.65]
    for y in horizontal:
        for at in range(max(0,y-1),min(height,y+2)):clean[at*width:(at+1)*width]=b'\xff'*width
    for x in vertical:
        for at in range(max(0,x-1),min(width,x+2)):
            clean[at::width]=b'\xff'*height
    result=f.Pixmap(f.csRGB,f.Pixmap(f.csGRAY,width,height,bytes(clean),False));result.set_origin(pix.x,pix.y);result.set_dpi(pix.xres,pix.yres);return result


def assign(words,columns,rows):
    cells=[[[] for _ in range(len(columns)-1)] for _ in range(len(rows)-1)];crossing=0
    for word in words:
        x0,y0,x1,y1=word['bbox'];x=(x0+x1)/2;y=(y0+y1)/2;c=bisect_right(columns,x)-1;r=bisect_right(rows,y)-1
        if not 0<=r<len(cells) or not 0<=c<len(cells[0]):continue
        crossing+=int(x0<columns[c]-.8 or x1>columns[c+1]+.8 or y0<rows[r]-.8 or y1>rows[r+1]+.8)
        cells[r][c].append(word)
    def text(items):
        lines=[]
        for word in sorted(items,key=lambda v:((v['bbox'][1]+v['bbox'][3])/2,v['bbox'][0])):
            center=(word['bbox'][1]+word['bbox'][3])/2;tol=max(2,(word['bbox'][3]-word['bbox'][1])*.45)
            if not lines or abs(lines[-1][0]-center)>tol:lines.append([center,[word]])
            else:lines[-1][1].append(word)
        return '\n'.join(' '.join(w['text'] for w in sorted(line,key=lambda v:v['bbox'][0])) for _,line in lines)
    return [[text(cell) for cell in row] for row in cells],crossing


def extract(base,ops,number,box,grid=None,mode='auto',language='spa+eng',dpi=200,orientation=0):
    if mode not in ['auto','digital','ocr'] or language not in ['eng','spa','spa+eng'] or type(dpi) is not int or dpi not in [150,200,300] or type(orientation) is not int or orientation not in [0,90,180,270]:raise DocumentError('Configuración de extracción no válida.')
    with open_pdf(base) as source:
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite extraer tablas.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc) or not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Página o región de tabla no válida.')
        page=doc[number];x,y,w,h=box;visible=f.Rect(x,y,x+w,y+h)
        if min(w,h)<15 or not page.rect.contains(visible):raise DocumentError('Selecciona una región dentro de la página, de al menos 15 × 15 pt.')
        native=visible*page.derotation_matrix;rotation=page.rotation;rotation_matrix=f.Matrix(page.rotation_matrix);words=[];warnings=[]
        use_ocr=mode=='ocr' or mode=='auto' and any((f.Rect(i['bbox'])&native).get_area()>.1 for i in page.get_image_info())
        if any((widget.rect&native).get_area()>.1 for widget in page.widgets() or []):raise DocumentError('La región cruza campos de formulario. Exporta sus datos o usa una copia aplanada antes de extraerla.')
        scale=dpi/72
        if math.ceil(w*scale)*math.ceil(h*scale)>16_000_000 or max(w,h)*scale>8192:raise DocumentError('La región supera 16 millones de píxeles; reduce área o resolución.')
        preview=page.get_pixmap(matrix=f.Matrix(scale,scale),clip=visible,colorspace=f.csGRAY,alpha=False,annots=False)
        if grid is None:columns,rows,detected=detect_lines(preview,visible)
        else:
            if not isinstance(grid,dict) or set(grid)!={'columns','rows'}:raise DocumentError('Cuadrícula no válida.')
            columns=boundaries(grid['columns'],visible.x0,visible.x1,30);rows=boundaries(grid['rows'],visible.y0,visible.y1,100);detected=False
        if grid is None and not detected:warnings.append('No se detectó una cuadrícula completa. Ajusta los separadores antes de usar la tabla.')
        if (len(rows)-1)*(len(columns)-1)>3000:raise DocumentError('La tabla supera 3000 celdas.')
        try:
            page.set_rotation(0)
            if use_ocr:
                if any(lang not in ocr_status()['languages'] for lang in language.split('+')):raise DocumentError('Faltan idiomas OCR verificados.')
                matrix=f.Matrix(scale,scale).prerotate(orientation);pix=page.get_pixmap(matrix=matrix,clip=native,colorspace=f.csGRAY,alpha=False,annots=False);pix.set_dpi(dpi,dpi);pix=remove_lines(pix)
                try:data=pix.pdfocr_tobytes(language=language,tessdata=str(TESSDATA))
                except Exception as exc:raise DocumentError('No se completó el OCR de tabla. Se conserva el documento.') from exc
                with f.open(stream=data) as recognized:
                    for item in recognized[0].get_text('words'):
                        corners=[f.Point(px*scale+pix.x,py*scale+pix.y)*~matrix*rotation_matrix for px,py in [(item[0],item[1]),(item[2],item[1]),(item[2],item[3]),(item[0],item[3])]]
                        words.append({'text':item[4],'bbox':[min(p.x for p in corners),min(p.y for p in corners),max(p.x for p in corners),max(p.y for p in corners)]})
                warnings.append('Texto reconocido por OCR: revisa cada celda. No se dispone de una puntuación de confianza verificable.')
            else:
                for item in page.get_text('words',clip=native):
                    rect=f.Rect(item[:4])*rotation_matrix;words.append({'text':item[4],'bbox':list(rect)})
        finally:page.set_rotation(rotation)
        if not words:raise DocumentError('No se encontró texto. Prueba OCR o corrige la región, idioma u orientación.')
        if len(words)>10000 or sum(len(word['text']) for word in words)>100000:raise DocumentError('La tabla supera el límite de texto. Reduce la región.')
        cells,crossing=assign(words,columns,rows)
        if crossing:warnings.append(f'{crossing} palabras cruzan separadores; revisa o mueve la cuadrícula.')
        return {'page':number,'box':box,'columns':columns,'rows':rows,'cells':cells,'words':words,'method':'ocr' if use_ocr else 'digital','detected_grid':detected,'warnings':warnings,'review_required':True,'source_modified':False}


def csv_bytes(cells):
    if not isinstance(cells,list) or not 1<=len(cells)<=100 or any(not isinstance(row,list) or not 1<=len(row)<=30 for row in cells) or len({len(r) for r in cells})!=1 or any(not isinstance(v,str) or len(v)>4000 for row in cells for v in row) or sum(len(v) for row in cells for v in row)>100000:raise DocumentError('Tabla CSV no válida o demasiado grande.')
    out=StringIO(newline='');writer=csv.writer(out)
    for row in cells:writer.writerow(["'"+v if v.lstrip().startswith(('=','+','-','@')) else v for v in row])
    return out.getvalue().encode('utf-8-sig')


def docx_bytes(cells,header=True):
    csv_bytes(cells)  # Shared dimensions/text budgets; this conversion uses literal text.
    if type(header) is not bool:raise DocumentError('La opción de encabezado debe ser verdadera o falsa.')
    from io import BytesIO
    from zipfile import ZipFile,ZIP_DEFLATED
    from xml.etree.ElementTree import Element,SubElement
    from .docx_export import tag,element,xml,text_run,section,R,RPKG
    document=Element(tag('document'));body=element(document,'body');table=element(body,'tbl');props=element(table,'tblPr');width=756 if len(cells[0])>6 else 523
    element(props,'tblW',{'w':width*20,'type':'dxa'});element(props,'tblLayout',{'type':'fixed'});borders=element(props,'tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:element(borders,edge,{'val':'single','sz':4,'color':'CCD5D8'})
    grid=element(table,'tblGrid');colwidth=round(width*20/len(cells[0]))
    for _ in cells[0]:element(grid,'gridCol',{'w':colwidth})
    for ri,row in enumerate(cells):
        tr=element(table,'tr')
        if header and ri==0:element(element(tr,'trPr'),'tblHeader')
        for value_ in row:
            cell=element(tr,'tc');pr=element(cell,'tcPr');element(pr,'tcW',{'w':colwidth,'type':'dxa'})
            if header and ri==0:element(pr,'shd',{'val':'clear','fill':'EDF2F3'})
            for line in value_.split('\n'):
                p=element(cell,'p');text_run(p,line,{'font':'Arial','size':10,'flags':16 if header and ri==0 else 0,'color':0})
    element(body,'p');section(body,828 if len(cells[0])>6 else 595,595 if len(cells[0])>6 else 842)
    types=b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels=Element('{'+RPKG+'}Relationships');SubElement(rels,'{'+RPKG+'}Relationship',{'Id':'rId1','Type':R+'/officeDocument','Target':'word/document.xml'})
    output=BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml',types);archive.writestr('_rels/.rels',xml(rels));archive.writestr('word/document.xml',xml(document))
    return output.getvalue()
