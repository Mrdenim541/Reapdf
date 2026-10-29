from io import BytesIO
from zipfile import ZipFile
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.engine import DocumentError,spans
from backend.merge import merge_pdf
from backend.page_tools import crop_pdf,split_pdf
from backend.app import app


def make_doc(prefix='Base',count=3,rotation=0,widgets=False):
    with f.open() as d:
        for i in range(count):
            p=d.new_page(width=400,height=500)
            p.insert_text((50,80),f'{prefix} pagina {i+1}',fontsize=16)
            p.insert_text((10,18),'Margen ocultable')
            p.set_rotation(rotation)
            if widgets:
                w=f.Widget();w.field_name=f'Campo {i}';w.field_type=f.PDF_WIDGET_TYPE_TEXT
                w.rect=f.Rect(60,180,180,210);w.field_value=f'{prefix}-{i}';p.add_widget(w)
        d[0].add_text_annot((120,150),f'Nota {prefix}')
        d[0].insert_link({'kind':f.LINK_URI,'from':f.Rect(60,230,180,250),'uri':'https://example.com'})
        if count>1:d[-1].insert_link({'kind':f.LINK_GOTO,'from':f.Rect(60,260,180,280),'page':1,'to':f.Point(50,80)})
        d.set_toc([[1,f'{prefix} {i+1}',i+1] for i in range(count)])
        d.set_page_labels([{'startpage':0,'prefix':f'{prefix}-','style':'D','firstpagenum':1}])
        return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_crop_rotations_preserve_pixels_and_restore_everything(rotation):
    data=make_doc(rotation=rotation,widgets=True)
    result=crop_pdf(data,[],[0],[20,30,40,10])
    with f.open(stream=data,filetype='pdf') as before,f.open(stream=result,filetype='pdf') as after:
        p=after[0];rect=before[0].rect
        assert p.rect.width==rect.width-40 and p.rect.height==rect.height-60
        assert p.rotation==rotation
        # Se compara el contenido, sin iconos NoRotate cuyo anclaje es especial.
        expected=before[0].get_pixmap(clip=f.Rect(10,20,rect.width-30,rect.height-40),annots=False)
        actual=p.get_pixmap(annots=False)
        assert actual.samples==expected.samples
        assert after[1].get_pixmap().samples==before[1].get_pixmap().samples
        assert p.get_label()=='Base-1' and after.get_toc()==before.get_toc()
        assert next(p.widgets()).field_value=='Base-0'
        assert next(p.annots()).info['content']=='Nota Base'
    restored=crop_pdf(result,[],[0],reset=True)
    with f.open(stream=data,filetype='pdf') as before,f.open(stream=restored,filetype='pdf') as after:
        assert after[0].cropbox==before[0].mediabox
        assert after[0].get_pixmap().samples==before[0].get_pixmap().samples


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_repeated_crop_uses_current_cropbox(rotation):
    data=make_doc(rotation=rotation)
    first=crop_pdf(data,[],[0],[10,10,10,10])
    twice=crop_pdf(first,[],[0],[20,20,20,20])
    once=crop_pdf(data,[],[0],[30,30,30,30])
    with f.open(stream=twice,filetype='pdf') as a,f.open(stream=once,filetype='pdf') as b:
        assert a[0].cropbox==b[0].cropbox
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples


@pytest.mark.parametrize('pages,margins,reset',[
 ([],[0]*4,False),([0,0],[0]*4,False),([True],[0]*4,False),([3],[0]*4,False),
 ([0],[-1,0,0,0],False),([0],[True,0,0,0],False),([0],[float('nan'),0,0,0],False),
 ([0],[0,200,0,200],False),([0],[1,2],False),([0],None,False),([0],[0]*4,1),
])
def test_bad_crop_is_rejected(pages,margins,reset):
    with pytest.raises(DocumentError):crop_pdf(make_doc(),[],pages,margins,reset=reset)


def test_crop_includes_current_edits_and_source_bytes_are_unchanged():
    data=make_doc()
    with f.open(stream=data,filetype='pdf') as d:span=spans(d[0])[0]
    op={'type':'text','page':0,'span_id':span['id'],'text':'Base nueva'}
    result=crop_pdf(data,[op],[0],[20]*4)
    with f.open(stream=result,filetype='pdf') as d:assert 'Base nueva' in d[0].get_text()
    with f.open(stream=data,filetype='pdf') as d:assert 'Base pagina 1' in d[0].get_text()


@pytest.mark.parametrize('position,count,incoming_pages',[(0,1,[2,0]),(1,2,[1]),(0,3,[2,1,0])])
def test_replace_whole_pages_preserves_retained_content_and_incoming_order(position,count,incoming_pages):
    base=make_doc(widgets=True);incoming=make_doc('Extra',widgets=True)
    result=merge_pdf(base,[],incoming,incoming_pages,position,'Extra',replace_count=count)
    with f.open(stream=base,filetype='pdf') as b,f.open(stream=incoming,filetype='pdf') as inc,f.open(stream=result,filetype='pdf') as d:
        order=[('base',i) for i in range(position)]+[('extra',i) for i in incoming_pages]+[('base',i) for i in range(position+count,3)]
        assert len(d)==len(order)
        for n,(kind,i) in enumerate(order):
            original=b[i] if kind=='base' else inc[i]
            assert d[n].get_pixmap().samples==original.get_pixmap().samples
            assert d[n].get_label()==original.get_label()
        assert sum(len(list(p.widgets() or [])) for p in d)==len(order)
        # Editar un campo importado no debe alterar los campos conservados.
        p=d[position];w=next(p.widgets());w.field_value='Nuevo';w.update()
        reopened=d.tobytes()
    with f.open(stream=reopened,filetype='pdf') as d:
        p=d[position];assert next(p.widgets()).field_value=='Nuevo'


def test_replace_removes_destinations_to_old_pages_instead_of_retargeting():
    base=make_doc();inc=make_doc('Extra')
    result=merge_pdf(base,[],inc,[0],1,replace_count=1)
    with f.open(stream=result,filetype='pdf') as d:
        assert len(d)==3
        assert d[2].get_links()==[]
        assert all(row[1]!='Base 2' for row in d.get_toc())
        assert [row for row in d.get_toc() if row[1]=='Base 3'][0][2]==3
        assert 'Extra pagina 1' in d[1].get_text()


@pytest.mark.parametrize('count',[-1,True,4,None,1.5])
def test_bad_replace_count_rejected(count):
    with pytest.raises(DocumentError):merge_pdf(make_doc(),[],make_doc('Extra'),[0],0,replace_count=count)


def test_replace_at_page_limit_does_not_fail_for_intermediate_page_count():
    base=make_doc(count=500);incoming=make_doc('Extra',count=1)
    result=merge_pdf(base,[],incoming,[0],250,replace_count=1)
    with f.open(stream=result,filetype='pdf') as d:
        assert len(d)==500 and 'Extra pagina 1' in d[250].get_text()
        assert 'Base pagina 252' in d[251].get_text()


@pytest.mark.parametrize('config,expected',[
 ({'size':1},[[0],[1],[2]]),({'size':2},[[0,1],[2]]),({'size':3},[[0,1,2]]),
 ({'groups':[[2,0],[1]]},[[2,0],[1]]),
])
def test_split_zip_content_order_forms_rotations_and_annotations(config,expected):
    data=make_doc(widgets=True,rotation=90)
    archive=split_pdf(data,[],**config)
    with ZipFile(BytesIO(archive)) as z,f.open(stream=data,filetype='pdf') as source:
        assert z.namelist()==[f'parte-{i:03d}.pdf' for i in range(1,len(expected)+1)]
        for filename,group in zip(z.namelist(),expected):
            with f.open(stream=z.read(filename),filetype='pdf') as part:
                assert len(part)==len(group)
                for i,number in enumerate(group):
                    assert part[i].get_pixmap().samples==source[number].get_pixmap().samples
                    assert next(part[i].widgets()).field_value==f'Base-{number}'
                    assert part[i].rotation==90
                for page in part:
                    for link in page.get_links():
                        if link['kind']==f.LINK_GOTO:assert 0<=link['page']<len(part)


@pytest.mark.parametrize('config',[
 {},{'size':True},{'size':0},{'size':4},{'size':1.5},{'groups':[]},
 {'groups':[[0],[0],[1,2]]},{'groups':[[0],[1]]},{'groups':[[True,1,2]]},
 {'groups':[[0,1,2]],'size':1},{'groups':['1-3']},
])
def test_bad_split_rejected(config):
    with pytest.raises(DocumentError):split_pdf(make_doc(),[],**config)


def test_split_output_quota(monkeypatch):
    monkeypatch.setattr('backend.page_tools.MAX_SPLIT_BYTES',10)
    with pytest.raises(DocumentError,match='100 MB'):split_pdf(make_doc(),[],size=1)


@pytest.mark.parametrize('action',['crop','split','replace'])
def test_new_tools_reject_signed_sources(action):
    with f.open(stream=make_doc(),filetype='pdf') as d:
        d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 1>>');data=d.tobytes()
    with pytest.raises(DocumentError):
        if action=='crop':crop_pdf(data,[],[0],[20]*4)
        elif action=='split':split_pdf(data,[],size=1)
        else:merge_pdf(data,[],make_doc(),[0],0,replace_count=1)


def test_page_tools_api_snapshots_zip_and_invalid_plans():
    with TestClient(app) as client:
        base=make_doc();incoming=make_doc('Extra')
        a=client.post('/api/documents',files={'file':('a.pdf',base)}).json()['id']
        b=client.post('/api/documents',files={'file':('b.pdf',incoming)}).json()['id']
        root=f'/api/documents/{a}'
        cropped=client.post(root+'/crop',json={'pages':[0],'margins':[20]*4})
        assert cropped.status_code==200 and cropped.json()['id']!=a
        assert cropped.json()['pages'][0]['width']==360
        replaced=client.post(root+'/replace',json={'source_id':b,'pages':[2,0],'position':1,'replace_count':1})
        assert replaced.status_code==200 and len(replaced.json()['pages'])==4
        split=client.post(root+'/split',json={'groups':[[2,0],[1]]})
        assert split.status_code==200 and split.headers['content-type']=='application/zip'
        with ZipFile(BytesIO(split.content)) as z:assert len(z.namelist())==2
        assert client.post(root+'/crop',json={'pages':[0],'margins':[-1]*4}).status_code==422
        assert client.post(root+'/replace',json={'source_id':b,'pages':[0],'position':1,'replace_count':0}).status_code==422
        assert client.post(root+'/split',json={'groups':[[0],[1]]}).status_code==422
        assert client.post(root+'/export',json={}).content==base


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_crop_and_restore_nonzero_mediabox(rotation):
    with f.open() as d:
        p=d.new_page(width=400,height=500);p.set_mediabox(f.Rect(20,30,420,530))
        p.insert_text((50,80),'Contenido');p.set_rotation(rotation);data=d.tobytes()
    cropped=crop_pdf(data,[],[0],[20]*4)
    restored=crop_pdf(cropped,[],[0],reset=True)
    with f.open(stream=data,filetype='pdf') as original,f.open(stream=restored,filetype='pdf') as output:
        assert output[0].get_pixmap().samples==original[0].get_pixmap().samples
        assert output[0].mediabox==original[0].mediabox
        assert output[0].cropbox==original[0].cropbox


@pytest.mark.parametrize('action',['crop','split','replace'])
def test_new_tools_enforce_original_document_permissions(action):
    with f.open(stream=make_doc(),filetype='pdf') as d:
        data=d.tobytes(encryption=f.PDF_ENCRYPT_AES_128,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT)
    with pytest.raises(DocumentError):
        if action=='crop':crop_pdf(data,[],[0],[20]*4)
        elif action=='split':split_pdf(data,[],size=1)
        else:merge_pdf(data,[],make_doc(),[0],0,replace_count=1)


@pytest.mark.parametrize('action',['split','replace'])
@pytest.mark.parametrize('feature',['layers','xfa','calculation'])
def test_partition_and_replacement_reject_unverified_document_structures(action,feature):
    with f.open(stream=make_doc(),filetype='pdf') as d:
        if feature=='layers':d.add_ocg('Capa')
        elif feature=='xfa':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</XFA (no compatible)>>')
        else:d.xref_set_key(d.pdf_catalog(),'AcroForm','<</CO [1 0 R]>>')
        data=d.tobytes()
    with pytest.raises(DocumentError):
        if action=='split':split_pdf(data,[],size=1)
        else:merge_pdf(data,[],make_doc(),[0],0,replace_count=1)


def test_split_applies_current_operations_before_producing_parts():
    data=make_doc()
    with f.open(stream=data,filetype='pdf') as d:span=spans(d[0])[0]
    op={'type':'text','page':0,'span_id':span['id'],'text':'Texto editado'}
    archive=split_pdf(data,[op],size=2)
    with ZipFile(BytesIO(archive)) as z,f.open(stream=z.read('parte-001.pdf'),filetype='pdf') as d:
        assert 'Texto editado' in d[0].get_text()
        assert 'Base pagina 1' not in d[0].get_text()


def test_replacement_keeps_edits_on_unaffected_pages():
    data=make_doc()
    with f.open(stream=data,filetype='pdf') as d:span=spans(d[0])[0]
    op={'type':'text','page':0,'span_id':span['id'],'text':'Texto editado'}
    result=merge_pdf(data,[op],make_doc('Extra'),[1],1,replace_count=1)
    with f.open(stream=result,filetype='pdf') as d:
        assert 'Texto editado' in d[0].get_text()
        assert 'Extra pagina 2' in d[1].get_text()
        assert 'Base pagina 3' in d[2].get_text()
