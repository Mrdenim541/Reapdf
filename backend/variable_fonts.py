"""Explicit default-instance conversion of embedded variable OpenType programs.

No axis is guessed and no font is substituted. Publish only after rendering and
text geometry agree on every page. Non-default design changes stay protected.
"""
from io import BytesIO
import math
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .document_tools import editable
from .styled_text import stream


def face(data):
    if len(data)>16*1024*1024:raise DocumentError('La fuente supera 16 MB.')
    try:
        font=TTFont(BytesIO(data),lazy=False)
        if len(font.keys())>200 or font['maxp'].numGlyphs>20000:raise ValueError()
        return font
    except Exception as exc:raise DocumentError('El programa OpenType no se puede inspeccionar de forma acotada.') from exc


def inventory(doc):
    if len(doc)>50:raise DocumentError('La preparación de fuentes admite hasta 50 páginas.')
    if doc.xref_length()>100000:raise DocumentError('Demasiados objetos PDF para inspeccionar fuentes.')
    found={};total=0;seen=set()
    # Inspect program streams, including fonts in nested Forms and field appearances.
    for x in range(1,doc.xref_length()):
        if doc.xref_get_key(x,'Type')!=('name','/FontDescriptor'):continue
        for key in ['FontFile2','FontFile3']:
            kind,value=doc.xref_get_key(x,key)
            if kind!='xref':continue
            ref=int(value.split()[0])
            if ref in seen:continue
            seen.add(ref)
            if key=='FontFile3' and doc.xref_get_key(ref,'Subtype')!=('name','/OpenType'):continue
            data=stream(doc,ref,16*1024*1024);total+=len(data)
            if total>64*1024*1024:raise DocumentError('Los programas de fuente superan 64 MB.')
            font=face(data)
            if 'fvar' not in font:font.close();continue
            if len(found)>=32 or not 1<=len(font['fvar'].axes)<=8:raise DocumentError('Demasiadas fuentes o ejes variables.')
            axes=[]
            for a in font['fvar'].axes:
                if not all(math.isfinite(v) and abs(v)<=1e6 for v in [a.minValue,a.defaultValue,a.maxValue]) or not a.minValue<=a.defaultValue<=a.maxValue:raise DocumentError('Los ejes variables no son verificables.')
                axes.append({'tag':a.axisTag,'minimum':a.minValue,'default':a.defaultValue,'maximum':a.maxValue})
            found[ref]={'xref':ref,'name':doc.xref_get_key(x,'FontName')[1].lstrip('/'),'axes':axes,'format':'CFF2' if 'CFF2' in font else 'TrueType','default_only':True}
            font.close()
    return list(found.values())


def inspect(base,ops):
    with open_pdf(base) as doc:
        editable(doc)
        if not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('Se necesita permiso de lectura para verificar las fuentes.')
    with open_pdf(export_pdf(base,ops)) as doc:
        return {'fonts':inventory(doc),'review_required':True,'source_modified':False,'scope':'Convierte explícitamente a la instancia predeterminada de cada eje, conservando apariencia y mapas. No cambia peso/ancho ni elige instancias con otro diseño.'}


def freeze(base,ops,selection,reviewed=False):
    if reviewed is not True:raise DocumentError('Revisa los ejes predeterminados antes de preparar fuentes estáticas.')
    with open_pdf(base) as doc:
        editable(doc)
        if not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('Se necesita permiso de lectura para verificar las fuentes.')
    snapshot=export_pdf(base,ops)
    with open_pdf(snapshot) as doc:
        available={r['xref']:r for r in inventory(doc)}
        if not isinstance(selection,list) or not 1<=len(selection)<=32:raise DocumentError('Selecciona de 1 a 32 programas variables.')
        seen=set();reports=[]
        for row in selection:
            if not isinstance(row,dict) or set(row)!={'xref','axes'} or type(row['xref']) is not int or row['xref'] not in available or row['xref'] in seen:raise DocumentError('Selección de fuentes obsoleta, repetida o no compatible.')
            x=row['xref'];seen.add(x);expected={a['tag']:a['default'] for a in available[x]['axes']};axes=row['axes']
            if not isinstance(axes,dict) or set(axes)!=set(expected) or any(not finite(v) or v!=expected[k] for k,v in axes.items()):raise DocumentError('Esta preparación conserva solo los valores predeterminados explícitos de todos los ejes.')
            original=face(stream(doc,x,16*1024*1024));order=original.getGlyphOrder();metrics=dict(original['hmtx'].metrics)
            try:
                static=instantiateVariableFont(original,axes,inplace=False,optimize=True)
                if 'fvar' in static or static.getGlyphOrder()!=order or static['hmtx'].metrics!=metrics:raise ValueError('Mapas o métricas cambiados')
                buffer=BytesIO();static.save(buffer);data=buffer.getvalue()
                if len(data)>16*1024*1024:raise ValueError('Fuente demasiado grande')
                from .styled_text import TrueType
                from .cff_fonts import CFFFace
                verified=CFFFace(data,'OpenType') if 'CFF2' in static or 'CFF ' in static else TrueType(data)
                if verified.count!=len(order):raise ValueError('Número de glifos cambiado')
            except Exception as exc:raise DocumentError('No se pudo obtener una instancia estática con mapas y métricas conservados.') from exc
            finally:original.close()
            doc.update_stream(x,data);doc.xref_set_key(x,'Length1',str(len(data)));reports.append({'xref':x,'axes':axes,'bytes':len(data)})
        result=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(snapshot) as before,open_pdf(result) as after:
        page_count=len(before)
        for a,b in zip(before,after):
            if a.get_text('words')!=b.get_text('words'):raise DocumentError('La instancia cambió el texto o sus posiciones; se conserva el original.')
            for target in [.75,1.5]:
                scale=min(target,math.sqrt(4_000_000/max(1,a.rect.get_area())))
                if a.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).samples!=b.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).samples:raise DocumentError('La instancia cambió la apariencia; se conserva el original.')
    return result,{'fonts':reports,'default_only':True,'appearance_verified':True,'pages':page_count}
