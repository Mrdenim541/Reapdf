"""Etiquetas, adjuntos, tablas CSV y numeración Bates entre documentos."""
from io import BytesIO, StringIO
from hashlib import sha256
import csv
import json
import re
import zlib
from zipfile import ZipFile, ZIP_DEFLATED
import pymupdf as fitz
from .engine import open_pdf, export_pdf, DocumentError
from .document_tools import editable, selected_pages
from .headers import SLOTS, prepare_headers, apply_headers
from .page_labels import read_rules,write_rules

MAX_ATTACHMENT = 8 * 1024 * 1024


def label_rules(base):
    with open_pdf(base) as doc:return read_rules(doc)


def labels_pdf(base, operations, rules):
    with open_pdf(base) as source:
        editable(source)
        if not isinstance(rules,list) or len(rules)>100:raise DocumentError('Hasta 100 reglas de etiquetas.')
        starts=[]
        for rule in rules:
            if not isinstance(rule,dict) or set(rule)!={'startpage','prefix','style','firstpagenum'}:raise DocumentError('Regla de etiquetas incompleta.')
            n,prefix,style,first=(rule[k] for k in ['startpage','prefix','style','firstpagenum'])
            if type(n) is not int or not 0<=n<len(source) or not isinstance(prefix,str) or len(prefix)>100 or any(ord(c)<32 for c in prefix) or not isinstance(style,str) or style not in {'','D','R','r','A','a'} or type(first) is not int or not 1<=first<=10000:raise DocumentError('Página, prefijo o formato de etiqueta no válido.')
            starts.append(n)
        if starts and (starts[0]!=0 or starts!=sorted(set(starts))):raise DocumentError('Comienza en la página 1 y ordena las reglas sin repetir páginas.')
        for i,rule in enumerate(rules):
            end=starts[i+1] if i+1<len(starts) else len(source)
            if rule['style'] in {'R','r'} and rule['firstpagenum']+end-rule['startpage']-1>3999:raise DocumentError('Las etiquetas romanas admiten hasta 3999.')
    with open_pdf(export_pdf(base,operations)) as doc:
        write_rules(doc,rules)
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def attachment_info(doc,index):
    info=doc.embfile_info(index)
    # The pinned binding's embfile_info applies a Latin-1 escape conversion to
    # filenames. Use the underlying Unicode-aware PDF string API directly.
    native=fitz.mupdf
    names=native.pdf_dict_getp(native.pdf_trailer(fitz._as_pdf_document(doc)),'Root/Names/EmbeddedFiles/Names')
    spec=native.pdf_array_get(names,2*index+1)
    info['name']=native.pdf_to_text_string(native.pdf_array_get(names,2*index))
    for key,label in [('F','filename'),('UF','ufilename')]:info[label]=native.pdf_to_text_string(native.pdf_dict_gets(spec,key))
    return info


def attachment_model(base):
    with open_pdf(base) as doc:
        names=doc.embfile_names()
        if len(names)>100:raise DocumentError('Hasta 100 adjuntos por documento en esta herramienta.')
        return [{'index':i,**attachment_info(doc,i)} for i in range(len(names))]


def safe_name(value):
    value=re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]','_',value or 'archivo')
    return value.strip('. ')[:120] or 'archivo'


def add_attachment(base,operations,name,data):
    if not isinstance(data,bytes) or not 1<=len(data)<=MAX_ATTACHMENT:raise DocumentError('Adjunta archivos de 1 byte a 8 MB.')
    if not isinstance(name,str) or not name or len(name)>255:raise DocumentError('Nombre de adjunto no válido.')
    name=safe_name(name)
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        names=[attachment_info(doc,i)['name'] for i in range(doc.embfile_count())]
        if len(names)>=100 or name in names:raise DocumentError('Nombre de adjunto repetido o límite de 100 alcanzado.')
        sizes=[doc.embfile_info(i).get('size',0) for i in range(len(names))]
        if any(type(n) is not int or n<0 for n in sizes) or sum(sizes)+len(data)>32*1024*1024:raise DocumentError('Los tamaños declarados de adjuntos superan 32 MB o no son válidos.')
        doc.embfile_add(name,data,filename=name,ufilename=name,desc='Adjuntado con Reapdf')
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def attachment_pdf(base,operations,index):
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        if type(index) is not int or not 0<=index<doc.embfile_count():raise DocumentError('Adjunto no encontrado.')
        doc.embfile_del(index)
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def download_attachment(base,index):
    with open_pdf(base) as doc:
        if not doc.permissions & fitz.PDF_PERM_COPY:raise DocumentError('El documento no permite extraer adjuntos.')
        if type(index) is not int or not 0<=index<min(doc.embfile_count(),100):raise DocumentError('Adjunto no encontrado.')
        info=attachment_info(doc,index)
        if type(info.get('size')) is not int or not 0<=info['size']<=MAX_ATTACHMENT:raise DocumentError('El adjunto supera 8 MB o no declara un tamaño válido.')
        # This pinned MuPDF binding returns the embedded stream reference without
        # inflating it. Bound decompression independently of the untrusted /Size.
        xref=doc._embfile_info(index,{})
        raw=doc.xref_stream_raw(xref)
        if raw is None or len(raw)>MAX_ATTACHMENT*2:raise DocumentError('Flujo de adjunto no compatible o demasiado grande.')
        kind,value=doc.xref_get_key(xref,'Filter')
        if doc.xref_get_key(xref,'DecodeParms')[0]!='null':raise DocumentError('El adjunto usa parámetros de compresión no compatibles.')
        if kind=='null':data=raw
        elif (kind=='name' and value=='/FlateDecode') or (kind=='array' and re.sub(r'\s','',value)=='[/FlateDecode]'):
            try:
                decoder=zlib.decompressobj();data=decoder.decompress(raw,MAX_ATTACHMENT+1)
                if len(data)>MAX_ATTACHMENT or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:raise ValueError()
            except zlib.error as exc:raise DocumentError('Compresión de adjunto no válida.') from exc
            except ValueError as exc:raise DocumentError('El adjunto supera 8 MB o tiene un flujo no compatible.') from exc
        else:raise DocumentError('Solo se descargan adjuntos sin compresión o con FlateDecode simple.')
        if len(data)>MAX_ATTACHMENT or len(data)!=info['size']:raise DocumentError('El tamaño real del adjunto no coincide con el declarado.')
        return data,safe_name(info.get('ufilename') or info.get('filename') or info['name'])


def extract_tables(base,operations,pages,strategy='lines'):
    if strategy not in ['lines','text']:raise DocumentError('Elige tablas con líneas o alineación de texto.')
    with open_pdf(base) as source:
        if not source.permissions & fitz.PDF_PERM_COPY:raise DocumentError('El documento no permite extraer tablas.')
        selected_pages(source,pages)
        if len(pages)>20:raise DocumentError('Hasta 20 páginas por extracción de tablas.')
    result=[];cells=0
    with open_pdf(export_pdf(base,operations)) as doc:
        for number in pages:
            page=doc[number]
            if max(page.rect.width,page.rect.height)>4000 or len(page.get_text())>200000 or len(page.get_drawings())>20000:raise DocumentError('La página supera los límites de extracción de tablas.')
            finder=page.find_tables(strategy=strategy)
            for index,table in enumerate(finder.tables):
                rows=table.extract();cells+=sum(len(row) for row in rows)
                if cells>50000 or len(result)>=100:raise DocumentError('Hasta 100 tablas y 50000 celdas por extracción.')
                result.append({'page':number,'table':index+1,'bbox':list(table.bbox),'rows':[[value or '' for value in row] for row in rows]})
    return {'tables':result,'cells':cells,'strategy':strategy}


def tables_zip(report):
    stream=BytesIO();manifest=[]
    with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
        for table in report['tables']:
            text=StringIO(newline='');writer=csv.writer(text)
            for row in table['rows']:
                writer.writerow(["'"+v if v.lstrip().startswith(('=','+','-','@')) else v for v in row])
            name=f"pagina-{table['page']+1:03d}-tabla-{table['table']:02d}.csv"
            archive.writestr(name,text.getvalue().encode('utf-8-sig'));manifest.append({'file':name,'page':table['page']+1,'bbox':table['bbox'],'rows':len(table['rows'])})
        archive.writestr('manifest.json',json.dumps({'tables':manifest,'formula_protection':True,'strategy':report['strategy']},ensure_ascii=False,indent=2))
    return stream.getvalue()


def bates_batch(items,prefix='',suffix='',start=1,padding=6):
    if not isinstance(items,list) or not 1<=len(items)<=10:raise DocumentError('El lote Bates admite de 1 a 10 PDF.')
    if any(not isinstance(t,str) or len(t)>40 or any(ord(c)<32 or ord(c)>255 or c in '{}' for c in t) for t in [prefix,suffix]):raise DocumentError('Prefijo y sufijo: hasta 40 caracteres latinos sin llaves ni controles.')
    if type(start) is not int or not 1<=start<=999999 or type(padding) is not int or not 0<=padding<=8:raise DocumentError('Inicio 1–999999 y relleno de 0 a 8 cifras.')
    outputs=[];counter=start;total=0
    for index,(name,base,ops) in enumerate(items):
        with open_pdf(base) as source:editable(source)
        edited=export_pdf(base,ops)
        with open_pdf(edited) as doc:
            total+=len(doc)
            if total>100:raise DocumentError('Hasta 100 páginas en todo el lote Bates.')
            slots={key:'' for key in SLOTS};slots['bottom_right']=prefix+'{numero}'+suffix
            plan={'pages':list(range(len(doc))),'slots':slots,'start':counter,'padding':padding,'size':9,'font':'helv','color':[0,0,0],'margins':[20,24,20,24]}
            prepared=prepare_headers(doc,plan);apply_headers(doc,prepared)
            output=doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
            first=prefix+str(counter).zfill(padding)+suffix;counter+=len(doc)
            last=prefix+str(counter-1).zfill(padding)+suffix
            filename=f'{index+1:02d}-{safe_name(name)}'
            if not filename.lower().endswith('.pdf'):filename+='.pdf'
            outputs.append((filename,output,{'file':filename,'pages':len(doc),'first':first,'last':last,'source_sha256':sha256(base).hexdigest(),'output_sha256':sha256(output).hexdigest()}))
        if sum(len(v[1]) for v in outputs)>100*1024*1024:raise DocumentError('El lote de salida supera 100 MB.')
    stream=BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
        for name,data,_ in outputs:archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps({'format':'reapdf-bates','pages':total,'documents':[v[2] for v in outputs]},ensure_ascii=False,indent=2))
    return stream.getvalue()
