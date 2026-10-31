"""Original-font reflow of one verified affine text group, without redaction."""
import copy,unicodedata
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .native_text import native_model
from .affine_text import polygon,rectangle,contains,overlap,verify
from .text_spacing import layout
from .text_flow import next_line


def reflow(base,ops,number,box,identifier,text,width,height,preview=False):
    if not isinstance(text,str) or not text.strip() or len(text)>4000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Usa de 1 a 4000 caracteres compatibles, con saltos de línea opcionales.')
    if not finite(width) or not finite(height) or not 10<=width<=2000 or not 10<=height<=2000:raise DocumentError('El ancho y alto deben estar entre 10 y 2000 pt en el marco del texto.')
    if type(number) is not int:raise DocumentError('Página no válida.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        if not 0<=number<len(doc):raise DocumentError('Página no válida.')
        page=doc[number];rotation=page.rotation;page.set_rotation(0)
        if doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null':raise DocumentError('El reflujo afín de contenido etiquetado necesita revisión estructural adicional.')
        if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Región de texto no válida.')
        region=f.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3]);_,selected=native_model(doc,number,region)
        rows=[r for r in selected if r['id']==identifier]
        if len(rows)!=1 or not rows[0]['editable']:raise DocumentError('Selecciona una línea original compatible.')
        row=rows[0];g=row['_geometry'];font=row['_font'];spacing=row['_spacing']['state']
        _,neighbors=native_model(doc,number,page.rect)
        obstacles=list(row['_obstacles'])+[rectangle(link['from']) for link in page.get_links()]
        obstacles += [rectangle(f.Rect(d['rect'])+(-.5,-.5,.5,.5)) for d in page.get_drawings()]
        obstacles += [other['quad'] or rectangle(f.Rect(other['bbox'])) for other in neighbors if other['id']!=identifier]
        # Tc/Tw can add advance between characters. Include it in the wrapping
        # prefix, then remove the last inter-character gap for each candidate.
        prefix=[0.]
        for char in text:
            extra=spacing['char']+(spacing['word'] if char==' ' and font.encode(char,row['size'])[0]==b' ' else 0)
            prefix.append(prefix[-1]+(0 if char=='\n' else font.encode(char,row['size'])[1]*spacing['scale']/100+max(0,extra)*spacing['scale']/100))
        leading=max(row['size']*1.35,g['ascent']-g['descent']);cursor=0;lines=[];prepared=[];commands=[];base_tm=f.Matrix(*row['_line_matrix'])
        while cursor<len(text):
            line,after,_=next_line(text,cursor,width,prefix)
            offset=len(lines)*leading
            if offset+g['ascent']-g['descent']>height+.01:raise DocumentError('El texto no cabe en el alto elegido. Amplía el área; no se publica texto parcial.')
            local=copy.copy(g);m=f.Matrix(*g['matrix']);origin=f.Point(0,-offset)*m;local['matrix']=list(m);local['matrix'][4:]=list(origin)
            extent,origins=layout(font,line,row['size'],spacing,[0.]*max(0,len(line)-1))
            if any(b<=a for a,b in zip(origins,origins[1:])):raise DocumentError('El espaciado produciría caracteres superpuestos; se conserva el original.')
            if extent<0 or extent>width+.05:raise DocumentError('El espaciado supera el ancho elegido.')
            cell=polygon(local,extent)
            if not contains(rectangle(page.rect),cell) or any(not contains(clip,cell) for clip in row['_clips']):raise DocumentError('El texto sale de la página o del recorte original.')
            if any(overlap(cell,obstacle)>.1 for obstacle in obstacles):raise DocumentError('El texto cruza otro texto, imagen, borde, enlace o anotación. Reduce el área o el contenido.')
            encoded=font.encode(line,row['size'])[0];operand=b'<'+encoded.hex().encode()+b'>'
            # Absolute Tm keeps every output line independently editable. The
            # source font, graphics state, opacity, clipping and Form path stay.
            tm=f.Matrix(base_tm);position=f.Point(0,-offset/g['factor'])*base_tm;tm[4]=position.x;tm[5]=position.y
            command=(' '.join(f'{n:.8f}' for n in tm)+' Tm ').encode()+operand
            commands.append((b'ET BT ' if lines else b'')+command+b' Tj');lines.append(line)
            if line:
                target={**row,'origin':list(origin),'_geometry':local,'_replacement_text':line,'_replacement_width':extent}
                prepared.append((target,b''))
            cursor=after
        report={'lines':len(lines),'font':row['font'],'size':row['size'],'width':width,'height':height,'preserves_affine':True,'source_groups':1}
        if preview:return report
        kind=row['_native'][2]
        # Original operator remains outside the replacement except for grouped
        # shows. End with a no-op operand of that same operator's type.
        tail=b'' if kind=='operator-array' else b' <>' if kind=='string' else b' []'
        from .form_text import write
        write(doc,page,[(row,b' '.join(commands)+tail)])
        page.set_rotation(rotation);data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    verify(data,{number:prepared})
    return data,report
