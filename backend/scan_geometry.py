"""Bounded quadrilateral rectification; maps OCR words back without altering scans."""
import math
from pathlib import Path
import pymupdf as f
from .engine import DocumentError,finite
from .ocr import TESSDATA


def homography(points):
    # Unit square -> convex quadrilateral, including its projective component.
    equations=[]
    for (u,v),(x,y) in zip([(0,0),(1,0),(1,1),(0,1)],points):
        equations.extend([[u,v,1,0,0,0,-u*x,-v*x,x],[0,0,0,u,v,1,-u*y,-v*y,y]])
    for col in range(8):
        pivot=max(range(col,8),key=lambda r:abs(equations[r][col]))
        if abs(equations[pivot][col])<1e-10:raise DocumentError('La perspectiva no tiene una transformación estable.')
        equations[col],equations[pivot]=equations[pivot],equations[col];div=equations[col][col];equations[col]=[n/div for n in equations[col]]
        for r in range(8):
            if r!=col:
                factor=equations[r][col];equations[r]=[a-factor*b for a,b in zip(equations[r],equations[col])]
    return [equations[r][-1] for r in range(8)]


def project(h,u,v):
    denominator=h[6]*u+h[7]*v+1
    if denominator<=1e-6:raise DocumentError('La perspectiva invierte o comprime excesivamente la región.')
    return f.Point((h[0]*u+h[1]*v+h[2])/denominator,(h[3]*u+h[4]*v+h[5])/denominator)


def corners(box,correction,bounds):
    if not isinstance(correction,dict) or set(correction) not in [{'angle'},{'quad'}]:raise DocumentError('Elige una inclinación o cuatro esquinas, no ambas.')
    if 'angle' in correction:
        angle=correction['angle']
        if not finite(angle) or abs(angle)>15:raise DocumentError('La inclinación admite entre −15 y 15 grados.')
        center=(box.tl+box.br)/2;matrix=f.Matrix(angle);points=[center+(p-center)*matrix for p in [box.tl,box.tr,box.br,box.bl]]
    else:
        values=correction['quad']
        if not isinstance(values,list) or len(values)!=4 or any(not isinstance(p,list) or len(p)!=2 or any(not finite(n) for n in p) for p in values):raise DocumentError('Indica cuatro esquinas: superior izquierda, superior derecha, inferior derecha e inferior izquierda.')
        points=[f.Point(p) for p in values]
    if any(not bounds.contains(p) for p in points):raise DocumentError('Las cuatro esquinas deben quedar dentro de la página.')
    edges=[points[(i+1)%4]-points[i] for i in range(4)];lengths=[abs(e) for e in edges]
    if min(lengths)<10 or max(lengths)/min(lengths)>25:raise DocumentError('Las aristas de perspectiva deben medir al menos 10 pt y conservar proporciones estables.')
    if any(edges[i].x*edges[(i+1)%4].y-edges[i].y*edges[(i+1)%4].x<10 for i in range(4)):raise DocumentError('Las esquinas deben formar un cuadrilátero convexo en sentido horario.')
    h=homography(points)
    for u in [0,.5,1]:
        for v in [0,.5,1]:project(h,u,v)
    return points


def recognize(page,points,language,dpi,orientation=0):
    # Points use visible page coordinates. Crop/rotation are handled by MuPDF's
    # renderer; the output mapping is subsequently derotated to PDF coordinates.
    points=points[-orientation//90:]+points[:-orientation//90] if orientation else points
    lengths=[abs(points[(i+1)%4]-points[i]) for i in range(4)]
    width=math.ceil(max(lengths[0],lengths[2])*dpi/72);height=math.ceil(max(lengths[1],lengths[3])*dpi/72)
    clip=f.Quad(points[0],points[1],points[3],points[2]).rect
    pixels=math.ceil(clip.width*dpi/72)*math.ceil(clip.height*dpi/72)
    if min(width,height)<16 or max(width,height)>8192 or width*height>16_000_000 or pixels>16_000_000:raise DocumentError('La corrección supera el presupuesto de 16 millones de píxeles.')
    pix=page.get_pixmap(matrix=f.Matrix(dpi/72,dpi/72),clip=clip,colorspace=f.csRGB,alpha=False,annots=False)
    quad=[p*(dpi/72)-f.Point(pix.x,pix.y) for p in points];pix.set_origin(0,0)
    corrected=rectify(pix,quad,width,height,dpi)
    try:data=corrected.pdfocr_tobytes(language=language,tessdata=str(TESSDATA))
    except Exception as exc:raise DocumentError('No terminó el OCR corregido. Se conserva el documento completo.') from exc
    h=homography(points);words=[]
    with f.open(stream=data) as recognized:
        rect=recognized[0].rect
        for word in recognized[0].get_text('words'):
            coords=[project(h,x/rect.width,y/rect.height)*page.derotation_matrix for x,y in [(word[0],word[1]),(word[2],word[1]),(word[2],word[3]),(word[0],word[3])]]
            words.append({'text':word[4],'quad':[[p.x,p.y] for p in coords]})
    if not words or len(words)>10000 or sum(len(w['text']) for w in words)>100000:raise DocumentError('El OCR corregido no encontró texto o supera el límite de contenido.')
    return words,width*height


def overlay(page,words):
    font=f.Font(fontfile=str(Path(__file__).resolve().parent.parent/'resources/fonts/DejaVuSans.ttf'))
    height=font.ascender-font.descender
    for word in words:
        text=word['text'];tl,tr,br,bl=[f.Point(p) for p in word['quad']];length=font.text_length(text,fontsize=1)
        if not length or any(not font.has_glyph(ord(c)) for c in text):raise DocumentError('Un carácter OCR no tiene una fuente invisible compatible.')
        # Each word uses a local affine approximation to its projective quad.
        # Exact corner coordinates are retained in the report for review.
        x=(tr-tl)/length;y=(bl-tl)/height;origin=tl+y*font.ascender
        writer=f.TextWriter(page.rect);writer.append(origin,text,font=font,fontsize=1)
        writer.write_text(page,render_mode=3,morph=(origin,f.Matrix(x.x,-x.y,-y.x,y.y,0,0)))


def rectify(pix,quad,width,height,dpi):
    # Perspective coefficients map output pixels to the rendered source image.
    # MuPDF's warp uses bilinear corners, which cannot share this homography.
    from PIL import Image
    h=homography(quad)
    coefficients=(h[0]/width,h[1]/height,h[2],h[3]/width,h[4]/height,h[5],h[6]/width,h[7]/height)
    with Image.frombytes('RGB',(pix.width,pix.height),pix.samples) as source:
        with source.transform((width,height),Image.Transform.PERSPECTIVE,coefficients,Image.Resampling.BICUBIC,fillcolor='white') as corrected:
            result=f.Pixmap(f.csRGB,width,height,corrected.tobytes(),False)
    result.set_dpi(dpi,dpi)
    return result
