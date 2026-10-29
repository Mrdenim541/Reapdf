from io import BytesIO
from hashlib import sha256
from zipfile import ZipFile
from copy import deepcopy
import csv,json,shutil,subprocess,zlib
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError,export_pdf,metadata
from backend.pro_tools import *
from backend.redaction import redact_pdf
from backend.signature import visual_signature
from backend.existing_annotations import list_annotations
from backend.ocr import ocr_pdf
from tests.test_long_advance import source


def labels():return [{'startpage':0,'prefix':'Intro-','style':'r','firstpagenum':1},{'startpage':1,'prefix':'Capítulo-','style':'D','firstpagenum':7}]


def test_page_labels_roundtrip_visible_geometry_content_and_clear():
    base=source(rotation=90,crop=True);out=labels_pdf(base,[],labels())
    with f.open(stream=out) as d,f.open(stream=base) as a:
        assert [p['label'] for p in metadata(d)['pages']]==['Intro-i','Capítulo-7']
        assert label_rules(out)==labels()
        assert all(p.get_pixmap().samples==q.get_pixmap().samples for p,q in zip(d,a))
    cleared=labels_pdf(out,[],[])
    with f.open(stream=cleared) as d:assert all(not p.get_label() for p in d)


@pytest.mark.parametrize('patch',[{'startpage':True},{'startpage':2},{'prefix':'\n'},{'prefix':'a'*101},{'style':'X'},{'style':[]},{'firstpagenum':0},{'firstpagenum':True}])
def test_invalid_label_rules(patch):
    rules=labels();rules[1].update(patch)
    with pytest.raises(DocumentError):labels_pdf(source(),[],rules)


@pytest.mark.parametrize('rules',[[{'startpage':1,'prefix':'','style':'D','firstpagenum':1}],labels()[::-1],labels()+[labels()[1]],None,[{'startpage':0,'prefix':'','style':'r','firstpagenum':3999}]])
def test_label_order_boundaries_and_roman_overflow(rules):
    with pytest.raises(DocumentError):labels_pdf(source(),[],rules)


def test_attachment_add_download_remove_preserves_bytes_pixels_and_other_attachments():
    base=source();payload=bytes(range(256))*1000;first=add_attachment(base,[],'a.bin',payload);second=add_attachment(first,[],'datos ñ.txt','¡Hola!'.encode())
    assert download_attachment(second,0)==(payload,'a.bin') and download_attachment(second,1)==('¡Hola!'.encode(),'datos ñ.txt')
    result=attachment_pdf(second,[],0);assert download_attachment(result,0)[0]=='¡Hola!'.encode()
    assert len(attachment_model(first))==1 and len(attachment_model(result))==1
    with f.open(stream=base) as a,f.open(stream=result) as b:
        assert a.get_toc()==b.get_toc() and all(p.get_pixmap().samples==q.get_pixmap().samples for p,q in zip(a,b))
    with pytest.raises(DocumentError):add_attachment(first,[],'a.bin',b'other')
    assert '/' not in safe_name('../../x.exe')


@pytest.mark.parametrize('data',[b'',b'x'*(MAX_ATTACHMENT+1),'string',None])
def test_attachment_limits(data):
    with pytest.raises(DocumentError):add_attachment(source(),[],'file',data)


def test_attachment_declared_small_size_cannot_hide_inflation_bomb():
    base=add_attachment(source(),[],'bomb.txt',b'hello')
    with f.open(stream=base) as d:
        xref=d._embfile_info(0,{})
        d.update_stream(xref,b'X'*(MAX_ATTACHMENT+1),compress=True)
        d.xref_set_key(xref,'Params/Size','5');data=d.tobytes()
    with pytest.raises(DocumentError):download_attachment(data,0)


@pytest.mark.parametrize('index',[True,-1,2,None])
def test_attachment_invalid_identifiers(index):
    data=add_attachment(source(),[],'x',b'a')
    with pytest.raises(DocumentError):download_attachment(data,index)
    with pytest.raises(DocumentError):attachment_pdf(data,[],index)


def table_source():
    with f.open() as d:
        p=d.new_page(width=500,height=650)
        for x in [30,180,340]:p.draw_line((x,40),(x,160))
        for y in [40,80,120,160]:p.draw_line((30,y),(340,y))
        for x,y,text in [(40,65,'Producto'),(190,65,'Cantidad'),(40,105,'A'),(190,105,'12'),(40,145,'=1+2'),(190,145,'30')]:p.insert_text((x,y),text)
        d.new_page();return d.tobytes()


def test_ruled_table_export_is_inspectable_csv_and_protects_formula_cells():
    data=table_source();report=extract_tables(data,[],[0,1]);assert report['cells']==6 and len(report['tables'])==1
    assert report['tables'][0]['rows']==[['Producto','Cantidad'],['A','12'],['=1+2','30']]
    with ZipFile(BytesIO(tables_zip(report))) as z:
        rows=list(csv.reader(z.read('pagina-001-tabla-01.csv').decode('utf-8-sig').splitlines()))
        assert rows[-1]==["'=1+2",'30'] and json.loads(z.read('manifest.json'))['formula_protection']
    assert extract_tables(source(),[],[0])['tables']==[]


@pytest.mark.parametrize('pages,strategy',[([], 'lines'),([True],'lines'),([0,0],'lines'),([2],'lines'),([0],'other')])
def test_table_validation(pages,strategy):
    with pytest.raises(DocumentError):extract_tables(table_source(),[],pages,strategy)


def test_batch_bates_sequence_manifest_and_unchanged_sources():
    a=source();b=source(rotation=90,crop=True);out=bates_batch([('../uno.pdf',a,[]),('dos.pdf',b,[])],'CASO-','-A',98,4)
    with ZipFile(BytesIO(out)) as z:
        manifest=json.loads(z.read('manifest.json'));rows=manifest['documents'];assert manifest['pages']==4
        assert (rows[0]['first'],rows[0]['last'],rows[1]['first'],rows[1]['last'])==('CASO-0098-A','CASO-0099-A','CASO-0100-A','CASO-0101-A')
        for index,row in enumerate(rows):
            data=z.read(row['file']);assert sha256(data).hexdigest()==row['output_sha256']
            assert row['source_sha256']==sha256([a,b][index]).hexdigest() and '/' not in row['file']
            with f.open(stream=data) as d,f.open(stream=[a,b][index]) as old:
                assert d[0].rotation==old[0].rotation and d.get_toc()==old.get_toc()
                assert row['first'] in d[0].get_text() and row['last'] in d[1].get_text()
                assert 'REAPDF' in d[0].get_text()
    with f.open(stream=a) as d:assert 'CASO-' not in d[0].get_text()


@pytest.mark.parametrize('patch',[{'prefix':'{numero}'},{'prefix':'✓'},{'suffix':'\n'},{'start':True},{'start':999999},{'padding':9},{'items':[]},{'items':[('x',source(),[])]*11}])
def test_bates_invalid_batch_is_atomic(patch):
    with pytest.raises(DocumentError):bates_batch(**{'items':[('x.pdf',source(),[])],**patch})


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('kind',['note','rectangle'])
def test_moving_imported_notes_and_rectangles_keeps_size_and_other_content(rotation,kind):
    with f.open(stream=source(rotation=rotation,crop=True)) as d:
        p=d[0];a=p.add_text_annot((100,250),'Comentario') if kind=='note' else p.add_rect_annot(f.Rect(100,250,180,290))
        a.set_colors(stroke=(1,0,0));a.update();base=d.tobytes()
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][0];assert row['can_move'];rect=row['rect'];target=[rect[0]+10,rect[1]+10,rect[2]+10,rect[3]+10]
    out=export_pdf(base,[{'type':'existing_annot','page':0,'xref':row['xref'],'action':'update','changes':{'rect':target,'color':[0,0,1]}}])
    with f.open(stream=out) as d:
        moved=list_annotations(d,0)['annotations'][0];assert moved['rect']==pytest.approx(target,abs=.02) and moved['color']==[0,0,1]
        if kind=='note':assert moved['content']=='Comentario'
        assert 'REAPDF' in d[0].get_text()


def sensitive_source(scan=False,rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((50,170),'SECRET-93847',fontsize=22);p.insert_text((50,260),'PUBLIC-58291',fontsize=22)
        if scan:
            pix=p.get_pixmap(matrix=f.Matrix(2,2));d=f.open();p=d.new_page(width=500,height=650);p.insert_image(p.rect,stream=pix.tobytes('png'))
        p.add_text_annot((350,350),'COMMENT-SECRET');p.insert_link({'kind':f.LINK_URI,'from':f.Rect(30,400,100,430),'uri':'https://example.com/private'})
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation)
        d.set_metadata({'title':'METADATA-SECRET'});d.embfile_add('hidden.txt',b'ATTACHMENT-SECRET');d.set_toc([[1,'BOOKMARK-SECRET',1]])
        return d.tobytes()


def region(base):
    with f.open(stream=base) as d:
        p=d[0];r=f.Rect(40-(20 if p.cropbox.x0 else 0),140-(30 if p.cropbox.y0 else 0),360-(20 if p.cropbox.x0 else 0),190-(30 if p.cropbox.y0 else 0))*p.rotation_matrix
        return [{'page':0,'box':[r.x0,r.y0,r.width,r.height]}]


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('scan',[False,True])
@pytest.mark.parametrize('crop',[False,True])
def test_redaction_really_removes_selected_content_and_sanitizes_download(rotation,scan,crop,tmp_path):
    base=sensitive_source(scan,rotation,crop);out=redact_pdf(base,[],region(base))
    with f.open(stream=base) as a,f.open(stream=out) as d:
        assert not d.embfile_count() and not d.get_toc() and not any(d.metadata.get(k) for k in ['title','author','keywords'])
        p=d[0];assert not list(p.annots() or []) and not p.get_links() and p.rotation==a[0].rotation
        assert 'SECRET-93847' not in p.get_text()
        if not scan:assert 'PUBLIC-58291' in p.get_text()
        for xref in range(1,d.xref_length()):
            content=(d.xref_stream(xref) or b'')+d.xref_object(xref).encode()
            for secret in [b'ATTACHMENT-SECRET',b'COMMENT-SECRET',b'METADATA-SECRET',b'BOOKMARK-SECRET']:
                assert secret not in content and secret.hex().encode() not in content.lower()
        if scan:
            original=a.extract_image(a[0].get_images()[0][0])['image'];assert all(d.extract_image(i[0])['image']!=original for i in p.get_images())
            # Native image pixels themselves must be white, independently of the
            # black fill overlay drawn over the redaction rectangle.
            image=f.Pixmap(d,p.get_images()[0][0]);assert image.pixel(150,330)[:3]==(255,255,255)
        assert a.embfile_count()==1
    if shutil.which('pdftotext') and not scan:
        target=tmp_path/'redacted.pdf';target.write_bytes(out);text=subprocess.check_output(['pdftotext',str(target),'-']).decode()
        assert 'SECRET-93847' not in text and 'PUBLIC-58291' in text


@pytest.mark.parametrize('regions',[[],[{'page':True,'box':[0,0,10,10]}],[{'page':0,'box':[0,0,0,10]}],[{'page':0,'box':[0,0,10000,10]}]])
def test_redaction_invalid_regions(regions):
    with pytest.raises(DocumentError):redact_pdf(source(),[],regions)


def test_redaction_blocks_shared_images_unflattened_fields_layers_and_internal_objects():
    from tests.test_forms import source as form_source
    with pytest.raises(DocumentError):redact_pdf(form_source(),[],[{'page':0,'box':[20,20,20,20]}])
    for kind in ['shared','ocg','form','actual']:
        with f.open(stream=sensitive_source(scan=kind=='shared')) as d:
            p=d[0]
            if kind=='shared':p.insert_image(f.Rect(350,450,450,580),xref=p.get_images()[0][0])
            elif kind=='ocg':d.add_ocg('layer')
            elif kind=='form':
                with f.open(stream=source()) as nested:p.show_pdf_page(f.Rect(200,200,350,400),nested,0)
            else:
                xref=p.get_contents()[0];d.update_stream(xref,b'/Span << /ActualText (SECRET) >> BDC\n'+d.xref_stream(xref)+b'\nEMC')
            base=d.tobytes()
        with pytest.raises(DocumentError):redact_pdf(base,[],region(base))


STROKES=[[[10,50],[70,100],[120,20],[230,70]],[[250,60],[300,80],[350,50]]]


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_visual_signature_vector_persists_with_no_digital_signature(rotation):
    base=source(rotation=rotation,crop=True);out=visual_signature(base,[],0,[40,50,180,70],STROKES,'Ana ñ')
    with f.open(stream=out) as d,f.open(stream=base) as a:
        p=d[0];annots=list(p.annots());assert len(annots)==1 and annots[0].type[0]==f.PDF_ANNOT_INK
        assert 'sin certificado' in annots[0].info['content'] and annots[0].info['title']=='Ana ñ'
        assert len(annots[0].vertices)==2 and d.get_sigflags()<=0 and not p.get_images()
        assert p.get_text()==a[0].get_text() and d[1].get_pixmap().samples==a[1].get_pixmap().samples
        assert all(f.Rect(40,50,220,120).contains(f.Point(pt)*p.rotation_matrix) for stroke in annots[0].vertices for pt in stroke)


@pytest.mark.parametrize('patch',[{'strokes':[]},{'strokes':[[[0,0],[1,1]]]},{'strokes':[[[0,0],[601,20]]]},{'strokes':STROKES*30},{'box':[0,0,5,5]},{'page':True},{'name':'\n'}])
def test_visual_signature_rejects_invalid_geometry(patch):
    with pytest.raises(DocumentError):visual_signature(**{'base':source(),'operations':[],'page':0,'box':[40,50,180,70],'strokes':STROKES,**patch})


@pytest.mark.parametrize('physical',[0,90,180,270])
@pytest.mark.parametrize('rotation',[0,90])
def test_ocr_manual_orientation_aligns_words_and_preserves_image(physical,rotation):
    with f.open() as a:
        p=a.new_page(width=500,height=650);p.insert_text((50,170),'REAPDF DOCUMENTO 12345',fontsize=22)
        pix=p.get_pixmap(matrix=f.Matrix(2,2).prerotate(physical))
        with f.open() as d:
            p=d.new_page(width=650 if physical%180 else 500,height=500 if physical%180 else 650);p.insert_image(p.rect,stream=pix.tobytes('png'));p.set_rotation(rotation);base=d.tobytes()
    out,report=ocr_pdf(base,[],[0],'eng',200,(360-physical)%360)
    with f.open(stream=base) as a,f.open(stream=out) as d:
        assert '12345' in d[0].get_text() and a[0].get_pixmap().samples==d[0].get_pixmap().samples and d[0].rotation==rotation
        # Word area transformed into the physical scan's native coordinates.
        expected=f.Rect(298,148,358,174)*f.Matrix(physical)
        bounds=f.Rect(0,0,500,650)*f.Matrix(physical);expected=expected+(-bounds.x0,-bounds.y0,-bounds.x0,-bounds.y0)
        found=d[0].search_for('12345')[0];assert (expected&found).get_area()/found.get_area()>.9


@pytest.mark.parametrize('action',['labels','attachments','bates','redact','tables','signature'])
def test_new_tools_respect_permissions(action):
    with f.open(stream=source()) as d:
        permissions=f.PDF_PERM_PRINT
        base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner1234',user_pw='',permissions=permissions)
    with pytest.raises(DocumentError):
        if action=='labels':labels_pdf(base,[],labels())
        elif action=='attachments':add_attachment(base,[],'a',b'x')
        elif action=='bates':bates_batch([('a',base,[])])
        elif action=='redact':redact_pdf(base,[],[{'page':0,'box':[10,10,20,20]}])
        elif action=='tables':extract_tables(base,[],[0])
        else:visual_signature(base,[],0,[40,50,180,70],STROKES)


def test_api_end_to_end_new_tools(tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    with TestClient(app) as c:
        base=source();doc=c.post('/api/documents',files={'file':('source.pdf',base)}).json();url='/api/documents/'+doc['id']
        assert c.get(url+'/labels').json()=={'rules':[]}
        labeled=c.post(url+'/labels',json={'rules':labels()});assert labeled.status_code==200 and labeled.json()['pages'][1]['label']=='Capítulo-7'
        attached=c.post(url+'/add-attachment',files={'file':('example.txt',b'bytes')});assert attached.status_code==200
        aid=attached.json()['id'];files=c.get(f'/api/documents/{aid}/attachments').json()['files'];assert len(files)==1
        assert c.get(f'/api/documents/{aid}/attachments/0').content==b'bytes'
        assert c.post(f'/api/documents/{aid}/delete-attachment',json={'index':0}).status_code==200
        batch={'items':[{'id':doc['id'],'name':'source.pdf'}]}
        assert c.post('/api/bates',json={**batch,'preview':True}).headers['content-type']=='image/png'
        assert c.post('/api/bates',json=batch).content.startswith(b'PK')
        assert c.post(url+'/redact',json={'regions':[{'page':0,'box':[40,140,400,40]}],'preview':True}).content.startswith(b'\x89PNG')
        assert c.post(url+'/redact',json={'regions':[{'page':0,'box':[40,140,400,40]}]}).content.startswith(b'%PDF')
        config={'page':0,'box':[40,50,180,70],'strokes':STROKES,'preview':True}
        assert c.post(url+'/visual-signature',json=config).headers['content-type']=='image/png'
        assert c.post(url+'/visual-signature',json={**config,'preview':False}).status_code==200
        assert c.post(url+'/tables',json={'pages':[0]}).json()['tables']==[]
        assert c.post(url+'/export-tables',json={'pages':[0]}).content.startswith(b'PK')


@pytest.mark.parametrize('prefix',['Anexo ñ/(1)-','\\P () /St 999 /S/R','中文 αβγ 😀','Ã±'])
def test_page_label_prefixes_are_pdf_strings_and_survive_page_changes(prefix):
    from backend.page_labels import visible_labels
    from backend.pages import organize_pdf
    from backend.page_creation import duplicate_pdf
    rules=[{'startpage':0,'prefix':prefix,'style':'D','firstpagenum':2}]
    out=labels_pdf(source(),[],rules)
    with f.open(stream=out) as d:assert visible_labels(d)==[prefix+'2',prefix+'3']
    assert label_rules(out)==rules
    reordered=organize_pdf(out,[],[{'page':1,'rotation':0},{'page':0,'rotation':0}])
    with f.open(stream=reordered) as d:assert visible_labels(d)==[prefix+'3',prefix+'2']
    duplicated=duplicate_pdf(out,[],[0],2)
    with f.open(stream=duplicated) as d:assert visible_labels(d)==[prefix+'2',prefix+'3',prefix+'2']


@pytest.mark.parametrize('name',['datos ñ😀.txt','Ã±.txt','報告.pdf'])
def test_attachment_unicode_names_do_not_guess_or_corrupt_encoding(name):
    base=add_attachment(source(),[],name,b'hello');assert attachment_model(base)[0]['name']==name
    assert download_attachment(base,0)==(b'hello',name)
    with pytest.raises(DocumentError):add_attachment(base,[],name,b'other')


@pytest.mark.parametrize('action',['labels','attachment','bates','signature','redact'])
def test_new_versions_keep_source_encryption_and_copy_print_restrictions(action):
    permissions=f.PDF_PERM_COPY|f.PDF_PERM_MODIFY|f.PDF_PERM_ANNOTATE|f.PDF_PERM_FORM
    with f.open(stream=source()) as d:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner1234',user_pw='',permissions=permissions)
    if action=='labels':out=labels_pdf(base,[],labels())
    elif action=='attachment':out=add_attachment(base,[],'file',b'x')
    elif action=='signature':out=visual_signature(base,[],0,[40,50,180,70],STROKES)
    elif action=='redact':out=redact_pdf(base,[],[{'page':0,'box':[10,10,20,20]}])
    else:
        with ZipFile(BytesIO(bates_batch([('a.pdf',base,[])]))) as z:out=z.read(z.namelist()[0])
    with f.open(stream=out) as d:
        assert not d.permissions&f.PDF_PERM_PRINT and d.permissions&f.PDF_PERM_COPY
        assert 'AES' in d.metadata['encryption']
