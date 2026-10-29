"""Firma manuscrita visual vectorial. No contiene certificado ni validación de identidad."""
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError,finite


def visual_signature(base,operations,page,box,strokes,name=''):
    if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Posición de firma no válida.')
    if not isinstance(strokes,list) or not 1<=len(strokes)<=50 or any(not isinstance(s,list) or not 2<=len(s)<=2000 for s in strokes) or sum(map(len,strokes))>10000:raise DocumentError('Firma: de 1 a 50 trazos y hasta 10000 puntos.')
    for stroke in strokes:
        if any(not isinstance(p,list) or len(p)!=2 or any(not finite(v) for v in p) or not 0<=p[0]<=600 or not 0<=p[1]<=180 for p in stroke):raise DocumentError('Los trazos deben quedar dentro del recuadro de firma.')
    if not isinstance(name,str) or len(name)>100 or any(ord(c)<32 for c in name):raise DocumentError('Nombre descriptivo de hasta 100 caracteres sin controles.')
    with open_pdf(base) as source:
        if source.get_sigflags()>0 or not source.permissions & fitz.PDF_PERM_ANNOTATE:raise DocumentError('El documento está firmado o no permite añadir una firma visual.')
        if type(page) is not int or not 0<=page<len(source):raise DocumentError('Página de firma no válida.')
        x,y,w,h=box
        if min(w,h)<10 or not source[page].rect.contains(fitz.Rect(x,y,x+w,y+h)):raise DocumentError('La firma debe quedar dentro de la página, con al menos 10 puntos por lado.')
    xs=[p[0] for s in strokes for p in s];ys=[p[1] for s in strokes for p in s]
    width,height=max(xs)-min(xs),max(ys)-min(ys)
    if width<5 or height<2:raise DocumentError('Dibuja una firma reconocible antes de insertarla.')
    scale=min((w-4)/width,(h-4)/height);ox=x+(w-width*scale)/2;oy=y+(h-height*scale)/2
    with open_pdf(export_pdf(base,operations)) as doc:
        target=doc[page];matrix=target.derotation_matrix
        paths=[[list(fitz.Point(ox+(px-min(xs))*scale,oy+(py-min(ys))*scale)*matrix) for px,py in s] for s in strokes]
        annot=target.add_ink_annot(paths);annot.set_border(width=1.2);annot.set_colors(stroke=(0,.08,.3));annot.set_info(title=name or 'Reapdf',content='Firma visual manuscrita; sin certificado digital ni verificación de identidad.');annot.update()
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
