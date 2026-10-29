"""Arranque local sin instalar servicios, dependencias ni configuraciones globales."""
from pathlib import Path
import argparse
import json
import os
import socket
import sys
import threading
import time
import webbrowser

APP_ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(APP_ROOT))
_DLL_HANDLES=[]
if sys.platform=='win32':
    for directory in [APP_ROOT.parent/'runtime',APP_ROOT.parent/'runtime'/'DLLs',APP_ROOT.parent/'runtime'/'Lib'/'site-packages'/'pymupdf']:
        if directory.is_dir():_DLL_HANDLES.append(os.add_dll_directory(str(directory)))


def self_test():
    import pymupdf as fitz
    from backend.engine import export_pdf,spans
    from backend.app import health
    with fitz.open() as doc:
        page=doc.new_page(width=400,height=500)
        page.insert_text((40,80),'Texto original',fontsize=18)
        data=doc.tobytes();span=spans(page)[0]
    result=export_pdf(data,[{'type':'text','page':0,'span_id':span['id'],'text':'Prueba','font':'tibo','size':20,'color':[.1,.3,.7]}])
    with fitz.open(stream=result,filetype='pdf') as doc:
        assert 'Prueba' in doc[0].get_text() and 'original' not in doc[0].get_text()
        assert 'Times-Bold' in doc[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]['font']
    result=export_pdf(data,[{'type':'textbox','page':0,'points':[[40,180],[300,260]],'text':'Texto nuevo','font':'helv','size':14,'align':0,'color':[0,0,0]},
                            {'type':'stamp','page':0,'points':[[40,300],[240,360]],'stamp':'draft','color':[0,0,.5]},
                            {'type':'link','page':0,'points':[[40,400],[200,430]],'destination':'web','url':'https://example.com'}])
    with fitz.open(stream=result,filetype='pdf') as doc:
        page=doc[0];assert 'Texto nuevo' in page.get_text()
        assert next(page.annots()).type[0]==fitz.PDF_ANNOT_STAMP
        assert page.get_links()[0]['uri']=='https://example.com'
    from backend.headers import SLOTS
    result=export_pdf(data,[{'type':'bookmarks','page':0,'items':[{'level':1,'title':'Resumen','page':0}]},
                            {'type':'header_footer','page':0,'pages':[0],'slots':{**dict.fromkeys(SLOTS,''),'bottom_center':'Página {numero} de {total}'},'color':[0,0,0]}])
    with fitz.open(stream=result,filetype='pdf') as doc:
        assert doc.get_toc()==[[1,'Resumen',1]] and 'Página 1 de 1' in doc[0].get_text()
    from backend.forms import form_model
    from backend.conversions import images_to_pdf,export_page_images
    with fitz.open(stream=data) as doc:
        page=doc[0];widget=fitz.Widget();widget.field_name='Nombre';widget.field_type=fitz.PDF_WIDGET_TYPE_TEXT
        widget.rect=fitz.Rect(40,180,300,230);page.add_widget(widget)
        field=form_model(doc)['fields'][0];form_data=doc.tobytes()
    filled=export_pdf(form_data,[{'type':'form_fill','page':0,'values':[{'page':0,'xref':field['xref'],'value':'Ana'}]}])
    with fitz.open(stream=filled) as doc:
        page=doc[0];assert next(page.widgets()).field_value=='Ana' and 'Ana' in page.get_text()
    from zipfile import ZipFile
    from io import BytesIO
    with ZipFile(BytesIO(export_page_images(filled,[],[0],dpi=72))) as archive:
        image_data=archive.read(archive.namelist()[0])
    with fitz.open(stream=images_to_pdf([image_data])) as doc:assert len(doc)==1 and doc[0].get_images()
    from backend.ocr import ocr_pdf,ocr_status
    assert set(ocr_status()['languages'])=={'eng','spa'}
    with fitz.open() as doc:
        page=doc.new_page(width=400,height=300);page.insert_text((30,100),'REAPDF OCR 12345',fontsize=20)
        scan=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
    with fitz.open() as doc:
        page=doc.new_page(width=400,height=300);page.insert_image(page.rect,stream=scan.tobytes('png'));scan_data=doc.tobytes()
    recognized,report=ocr_pdf(scan_data,[],[0],language='eng',dpi=150)
    with fitz.open(stream=scan_data) as before,fitz.open(stream=recognized) as after:
        assert '12345' in after[0].get_text() and before[0].get_pixmap().samples==after[0].get_pixmap().samples
    from backend.document_tools import protect_pdf,unlock_pdf
    protected=protect_pdf(data,[],'test-read-123','test-owner-123')
    unlocked,flag=unlock_pdf(protected,'test-read-123');assert flag
    from backend.pro_tools import labels_pdf,add_attachment,download_attachment,bates_batch
    from backend.page_labels import visible_labels
    from backend.redaction import redact_pdf
    from backend.signature import visual_signature
    labeled=labels_pdf(data,[],[{'startpage':0,'prefix':'Anexo ñ/(1)-','style':'r','firstpagenum':1}])
    with fitz.open(stream=labeled) as doc:assert visible_labels(doc)==['Anexo ñ/(1)-i']
    attached=add_attachment(data,[],'datos ñ.txt',b'Prueba local')
    assert download_attachment(attached,0)==(b'Prueba local','datos ñ.txt')
    with ZipFile(BytesIO(bates_batch([('test.pdf',data,[])],'DOC-'))) as archive:
        assert json.loads(archive.read('manifest.json'))['documents'][0]['first']=='DOC-000001'
    redacted=redact_pdf(attached,[],[{'page':0,'box':[30,50,200,40]}])
    with fitz.open(stream=redacted) as doc:assert 'Texto original' not in doc[0].get_text() and not doc.embfile_count()
    signed=visual_signature(data,[],0,[40,300,180,70],[[[20,50],[80,100],[150,30],[250,60]]])
    with fitz.open(stream=signed) as doc:
        page=doc[0];assert next(page.annots()).type[0]==fitz.PDF_ANNOT_INK and doc.get_sigflags()<=0
    from backend.form_design import create_field
    from backend.form_data import flatten_form
    radio_pdf=create_field(data,[],{'name':'Decision','kind':'radio','page':0,'box':[40,280,250,70],'options':['Aceptar','Revisar']})
    with fitz.open(stream=radio_pdf) as doc:
        fields=form_model(doc)['fields'];assert len(fields)==2 and all(row['editable'] for row in fields)
    operation={'type':'form_fill','page':0,'values':[{'page':0,'xref':fields[0]['xref'],'value':'opcion_2'}]}
    radio_filled=export_pdf(radio_pdf,[operation]);radio_flat=flatten_form(radio_pdf,[operation])
    with fitz.open(stream=radio_filled) as a,fitz.open(stream=radio_flat) as b:
        assert all(row['value']=='opcion_2' for row in form_model(a)['fields'])
        assert not list(b[0].widgets() or []) and a[0].get_pixmap().samples==b[0].get_pixmap().samples
    from backend.page_creation import duplicate_pdf
    duplicated=duplicate_pdf(radio_filled,[],[0],1)
    with fitz.open(stream=duplicated) as doc:
        fields=form_model(doc)['fields'];assert len(fields)==4 and all(row['editable'] for row in fields)
        copied=next(row for row in fields if row['name']=='Decision (2)')
    changed=export_pdf(duplicated,[{'type':'form_fill','page':0,'values':[{'page':copied['page'],'xref':copied['xref'],'value':'opcion_1'}]}])
    with fitz.open(stream=changed) as doc:
        fields=form_model(doc)['fields']
        assert all(row['value']==('opcion_1' if row['name']=='Decision (2)' else 'opcion_2') for row in fields)
    from backend.styled_text import inspect_styled,replace_styled
    from hashlib import sha256
    with fitz.open() as doc:
        page=doc.new_page(width=400,height=500);page.insert_font(fontname='Original',fontfile=str(APP_ROOT/'resources'/'fonts'/'DejaVuSans.ttf'))
        page.insert_text((40,80),'Texto original 12345',fontname='Original',fontsize=14);doc.subset_fonts();styled=doc.tobytes()
    row=inspect_styled(styled,[],0,[30,50,340,60])['runs'][0];assert row['editable']
    output=replace_styled(styled,[],0,[30,50,340,60],[{'id':row['id'],'text':'Texto 123'}])
    with fitz.open(stream=styled) as a,fitz.open(stream=output) as b:
        assert 'Texto 123' in b[0].get_text()
        assert sha256(a.extract_font(a[0].get_fonts()[0][0])[3]).digest()==sha256(b.extract_font(b[0].get_fonts()[0][0])[3]).digest()
    from backend.document_review import review_document
    reviewed=review_document(form_data,[])
    assert reviewed['pages'][0]['fields']==1 and reviewed['pages'][0]['has_text']
    assert reviewed['next_offset'] is None
    assert (APP_ROOT/'resources'/'fonts'/'DejaVuSans.ttf').is_file()
    assert (APP_ROOT/'web'/'dist'/'index.html').is_file()
    print(json.dumps({'portable_self_test':'ok','python':sys.version.split()[0],**health()}))


def serve(open_browser=True,port=0,desktop=False,require_desktop=False,ready_file=None):
    import uvicorn
    from backend.app import app
    from desktop import DesktopWindow, find_browser
    if require_desktop and not desktop:raise ValueError('El inicio de escritorio estricto requiere --desktop.')
    if require_desktop and not find_browser():raise RuntimeError('No se encontro Edge o Chrome instalado para abrir la ventana de Reapdf.')
    windows=[];server=None;worker=None;startup_errors=[]
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        # Mantener el socket reservado evita carreras entre elegir y abrir puerto.
        sock.bind(('127.0.0.1',port));sock.listen(128)
        selected_port=sock.getsockname()[1]
        config=uvicorn.Config(app,host='127.0.0.1',port=selected_port,log_level='warning',access_log=False,loop='asyncio',http='h11')
        server=uvicorn.Server(config)
        url=f'http://127.0.0.1:{selected_port}'
        def ready():
            deadline=time.monotonic()+30
            while not server.started and not server.should_exit and time.monotonic()<deadline:time.sleep(.1)
            if server.started and not server.should_exit:
                print('REAPDF_URL='+url,flush=True)
                if desktop:
                    executable=find_browser()
                    if executable:
                        try:
                            window=DesktopWindow(executable,url);windows.append(window)
                            print('REAPDF_PRESENTATION=desktop',flush=True)
                            if ready_file:Path(ready_file).write_text(url,encoding='utf-8')
                            code=window.wait()
                            if code==0:
                                server.should_exit=True
                            elif require_desktop:
                                startup_errors.append('La ventana de Reapdf termino con un error.');server.should_exit=True
                            elif not server.should_exit:
                                print('La ventana no pudo iniciarse. Se abre el navegador; Ctrl+C cierra el motor.',flush=True)
                                webbrowser.open(url)
                        except OSError as exc:
                            print('No se pudo abrir la ventana: '+str(exc),flush=True)
                            if require_desktop:startup_errors.append(str(exc));server.should_exit=True
                            else:webbrowser.open(url)
                    else:
                        if require_desktop:startup_errors.append('No se encontro Edge/Chrome compatible.');server.should_exit=True
                        else:
                            print('No se encontró Edge/Chrome compatible. Se abre el navegador; Ctrl+C cierra el motor.',flush=True)
                            webbrowser.open(url)
                elif open_browser:webbrowser.open(url)
        worker=threading.Thread(target=ready,daemon=True);worker.start()
        print('Reapdf portable. Deja esta ventana abierta. Ctrl+C para cerrar.',flush=True)
        server.run(sockets=[sock])
    finally:
        sock.close()
        if server:server.should_exit=True
        # Evitar que el hilo abra una ventana después de detener el motor.
        if worker and threading.current_thread() is not worker:worker.join(timeout=1)
        for window in windows:window.close()
    if startup_errors:raise RuntimeError(" ".join(startup_errors))


def main():
    parser=argparse.ArgumentParser(description='Reapdf portable: servidor local y navegador.')
    parser.add_argument('--self-test',action='store_true')
    presentation=parser.add_mutually_exclusive_group()
    presentation.add_argument('--no-browser',action='store_true')
    presentation.add_argument('--desktop',action='store_true')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--require-desktop',action='store_true',help='Exige ventana; no abre una pestana como alternativa.')
    parser.add_argument('--ready-file',help='Confirmacion de inicio para el lanzador GUI.')
    args=parser.parse_args()
    if args.require_desktop and not args.desktop:parser.error('--require-desktop necesita --desktop')
    if args.ready_file and not args.require_desktop:parser.error('--ready-file necesita --require-desktop')
    try:
        if args.self_test:self_test()
        else:serve(not args.no_browser,args.port,args.desktop,args.require_desktop,args.ready_file)
    except Exception as exc:
        print('No se pudo iniciar Reapdf: '+str(exc),file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
