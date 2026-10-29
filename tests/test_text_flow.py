from copy import deepcopy
import re,shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.text_flow import flow_text,inspect_flow


def source(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=400,height=500);p.insert_text((40,70),'Texto original');p.insert_text((40,430),'Pie original conservado')
        p=d.new_page(width=400,height=500);p.insert_text((40,430),'Pie destino conservado')
        p=d.new_page(width=400,height=500);p.insert_text((40,70),'Otra pagina intacta')
        kind,raw=d.xref_get_key(d[0].xref,'Resources');d.xref_set_key(d[2].xref,'Resources',raw)
        for p in d:
            if crop:p.set_cropbox(f.Rect(10,10,390,490))
            p.set_rotation(rotation)
        return d.tobytes()


def regions():return [{'page':0,'box':[20,35,340,100],'replace':True},{'page':1,'box':[20,35,340,300],'replace':False}]


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_flow_replaces_only_selected_text_and_keeps_all_words_geometry_and_other_page(rotation,crop,tmp_path):
    base=source(rotation,crop);text=' '.join(f'palabra{i}' for i in range(100))
    out,r=flow_text(base,[],regions(),text)
    assert r['complete'] and r['characters']==len(text) and all(d['characters']>0 for d in r['regions'])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[2].get_pixmap().samples==b[2].get_pixmap().samples
        actual=b[0].get_text()+b[1].get_text();assert 'Texto original' not in actual
        assert 'Pie original conservado' in actual and 'Pie destino conservado' in actual
        assert re.findall(r'palabra\d+',actual)==re.findall(r'palabra\d+',text)
        for i in range(3):assert b[i].rotation==a[i].rotation and b[i].cropbox==a[i].cropbox
    if shutil.which('pdftotext'):
        path=tmp_path/'flow.pdf';path.write_bytes(out);actual=subprocess.check_output(['pdftotext','-raw',str(path),'-']).decode()
        assert len(re.findall(r'palabra\d+',actual))==100 and 'Texto original' not in actual


@pytest.mark.parametrize('align',[0,1,2,3])
def test_long_words_explicit_breaks_unicode_and_alignment(align):
    text='Primera αβγ\n\n'+('W'*170)+'\nFinal ñ'
    out,r=flow_text(source(),[],regions(),text,align=align)
    assert r['characters']==len(text)
    with f.open(stream=out) as d:
        result=d[0].get_text()+d[1].get_text();assert result.count('W')==170 and 'αβγ' in result and 'Final ñ' in result


def test_overflow_fails_atomically_and_auto_fit_reports_uniform_size():
    base=source();short=regions()[:1];text='palabra '*60
    with pytest.raises(DocumentError,match='no cabe'):flow_text(base,[],short,text,size=24)
    out,r=flow_text(base,[],short,text,size=24,auto_fit=True,min_size=6)
    assert r['adjusted'] and 6<=r['size']<24
    with f.open(stream=out) as d:assert 'Texto original' not in d[0].get_text()
    with pytest.raises(DocumentError,match='no cabe'):flow_text(base,[],short,text,size=24,auto_fit=True,min_size=23)
    assert inspect_flow(base,[],regions())['text']=='Texto original'


@pytest.mark.parametrize('kind',['text','image','field','annotation','line','link','form','layer'])
def test_unsafe_regions_rejected_before_mutation(kind):
    with f.open(stream=source()) as d:
        p=d[1]
        if kind=='text':p.insert_text((40,100),'Contenido ajeno')
        elif kind=='image':
            pix=f.Pixmap(f.csRGB,f.IRect(0,0,10,10),False);pix.clear_with(50);p.insert_image(f.Rect(40,100,100,160),pixmap=pix)
        elif kind=='field':
            w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name='Campo';w.rect=f.Rect(40,100,100,130);p.add_widget(w)
        elif kind=='annotation':p.add_text_annot((50,100),'No borrar')
        elif kind=='line':p.draw_line((40,100),(200,100),width=1)
        elif kind=='link':p.insert_link({'kind':f.LINK_URI,'from':f.Rect(40,100,100,130),'uri':'https://example.com'})
        elif kind=='form':
            with f.open() as other:other.new_page().insert_text((30,50),'Form');p.show_pdf_page(p.rect,other,0)
        else:d.add_ocg('Layer')
        base=d.tobytes()
    with pytest.raises(DocumentError):flow_text(base,[],regions(),'Nuevo texto')


@pytest.mark.parametrize('patch',[
 {'text':''},{'text':'漢字'},{'text':'مرحبا'},{'text':'bad\ttext'},{'text':'x'*12001},
 {'size':True},{'size':5},{'align':4},{'line_height':float('nan')},{'auto_fit':1},{'min_size':13},
 {'regions':[]},{'regions':[{'page':0,'box':[20,35,340,100],'replace':False}]},
 {'regions':[{'page':0,'box':[20,35,340,100],'replace':True}]*2},
 {'regions':[{'page':True,'box':[20,35,340,100],'replace':True}]},
])
def test_invalid_requests_rejected(patch):
    args={'regions':regions(),'text':'Texto nuevo'}|patch
    with pytest.raises(DocumentError):flow_text(source(),[],**args)


@pytest.mark.parametrize('kind',['signed','permission'])
def test_permissions_and_signatures_enforced(kind):
    with f.open(stream=source()) as d:
        if kind=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');base=d.tobytes()
        else:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_COPY)
    with pytest.raises(DocumentError):flow_text(base,[],regions(),'Texto nuevo')


def test_api_preview_does_not_mutate_source_and_apply_creates_a_version():
    base=source();payload={'regions':regions(),'text':'Nuevo texto de flujo '*40}
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('flow.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        r=c.post(url+'/flow-text',json=payload|{'preview':True});assert r.status_code==200,r.text
        assert r.json()['report']['complete'] and len(r.json()['previews'])==2
        assert c.post(url+'/export',json={'operations':[]}).content==base
        applied=c.post(url+'/flow-text',json=payload);assert applied.status_code==200 and applied.json()['id']!=doc['id']
        out=c.post('/api/documents/'+applied.json()['id']+'/export',json={'operations':[]}).content
        with f.open(stream=out) as d:assert 'Nuevo texto' in d[0].get_text()


def test_blank_lines_can_fill_a_region_without_a_writer_error():
    text='\n'*7+'Texto después de líneas vacías'
    out,r=flow_text(source(),[],regions(),text)
    assert r['complete']
    with f.open(stream=out) as d:assert 'Texto después' in d[1].get_text()


@pytest.mark.parametrize('family',['sans','serif','mono'])
@pytest.mark.parametrize('style',['regular','bold','italic','bold-italic'])
def test_flow_font_metrics_remain_inside_regions(family,style):
    out,_=flow_text(source(),[],regions(),'Texto áñ αβ Привет '*40,family=family,style=style)
    with f.open(stream=out) as d:
        for row in regions():
            x,y,w,h=row['box'];rect=f.Rect(x,y,x+w,y+h)
            for block in d[row['page']].get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if span['font'].startswith('DejaVu'):assert rect.contains(f.Rect(span['bbox']))


@pytest.mark.parametrize('rotation',[90,180,270])
def test_rotated_native_links_are_detected_in_empty_destination_regions(rotation):
    with f.open(stream=source(rotation)) as d:
        p=d[1];p.set_rotation(0);p.insert_link({'kind':f.LINK_URI,'from':f.Rect(40,100,100,130),'uri':'https://example.com'});p.set_rotation(rotation);base=d.tobytes()
    with pytest.raises(DocumentError,match='enlace'):flow_text(base,[],regions(),'Texto nuevo')


def test_tagged_sources_are_not_silently_left_with_stale_semantic_structure():
    with f.open(stream=source()) as d:
        root=d.get_new_xref();d.update_object(root,'<</Type/StructTreeRoot/K[]>>');d.xref_set_key(d.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');base=d.tobytes()
    with pytest.raises(DocumentError,match='etiquetas semánticas'):flow_text(base,[],regions(),'Texto nuevo')
