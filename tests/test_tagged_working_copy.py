from io import BytesIO
from zipfile import ZipFile
import json
import xml.etree.ElementTree as ET
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.basic_tagging import candidates,create as tag
from backend.untagged_copy import create
from backend.engine import DocumentError
from backend.find_replace import inspect,replace
from backend.image_editing import image_model,edit_image
from backend.page_tools import split_pdf


def source(rotation=0,crop=False,complex=True):
    with f.open() as d:
        pix=f.Pixmap(f.csRGB,f.IRect(0,0,60,30),False);pix.clear_with(90)
        for i in range(3):
            p=d.new_page(width=400,height=500);p.insert_text((40,80),'CODIGO GENERAL',fontsize=12)
            p.draw_rect(f.Rect(20,30,380,460));p.insert_image(f.Rect(100,170,220,230),pixmap=pix)
            if crop:p.set_cropbox(f.Rect(10,15,390,480))
            p.set_rotation(rotation)
        base=d.tobytes()
    info=candidates(base,[])
    entries=[{'id':e['id'],'role':'Figure','alt':'Logo'} if e['kind']=='image' else {'id':e['id'],'role':'P'} for e in info['entries']]
    base=tag(base,[],entries,reviewed=True)[0]
    with f.open(stream=base) as d:
        if complex:d.xref_set_key(int(d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[1].split()[0]),'ActualText',f.get_pdf_str('Alternate reading text'))
        d[0].add_text_annot((250,300),'KEEP THIS COMMENT')
        d.set_xml_metadata('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:pdfuaid="http://www.aiim.org/pdfua/ns/id/" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" xmlns:dc="http://purl.org/dc/elements/1.1/" pdfuaid:part="1"><pdfaid:part>2</pdfaid:part><pdfaid:conformance>A</pdfaid:conformance><dc:title>Keep title</dc:title></rdf:Description></rdf:RDF></x:xmpmeta>')
        return d.tobytes(garbage=2)


def query():return {'text':'CODIGO GENERAL','pages':[0,1,2],'case_sensitive':True,'whole_word':True}


@pytest.mark.parametrize('rotation,crop',[(0,False),(90,True),(180,False),(270,True)])
def test_copy_preserves_native_content_images_geometry_comments_and_pixels(rotation,crop):
    base=source(rotation,crop);out,report=create(base,[],True)
    assert report['page_streams_and_binary_resources_verified'] and not report['rasterized']
    with f.open(stream=base) as before,f.open(stream=out) as after:
        assert before.xref_get_key(before.pdf_catalog(),'StructTreeRoot')[0]!='null'
        assert after.xref_get_key(after.pdf_catalog(),'StructTreeRoot')[0]=='null'
        for a,b in zip(before,after):
            assert a.get_pixmap(matrix=f.Matrix(1.5,1.5)).samples==b.get_pixmap(matrix=f.Matrix(1.5,1.5)).samples
            assert a.get_text('words')==b.get_text('words') and a.rotation==b.rotation and a.cropbox==b.cropbox
            assert a.read_contents()==b.read_contents()
            assert [(v['bbox'],v['transform'],v['digest']) for v in a.get_image_info(hashes=True)]==[(v['bbox'],v['transform'],v['digest']) for v in b.get_image_info(hashes=True)]
        assert list(after[0].annots())[0].info['content']=='KEEP THIS COMMENT'
        xml=ET.fromstring(after.get_xml_metadata());assert 'Keep title' in ''.join(xml.itertext())
        assert not any(v.tag.startswith(('{http://www.aiim.org/pdfua/ns/id/}','{http://www.aiim.org/pdfa/ns/id/}')) for v in xml.iter())
        assert not any(k.startswith('{http://www.aiim.org/pdfua/ns/id/}') for v in xml.iter() for k in v.attrib)


def test_structure_is_checked_before_matches_can_be_selected_then_copy_can_replace():
    base=source();review=inspect(base,[],query());assert len(review['matches'])==3 and review['structure_blocked_pages']==[0,1,2]
    assert not any(m['editable'] for m in review['matches'])
    out,_=create(base,[],True);review=inspect(out,[],query());assert not review['structure_blocked_pages'] and all(m['editable'] for m in review['matches'])
    result,_,count=replace(out,[],query(),review['receipt'],[m['id'] for m in review['matches']],'CODIGO NUEVO');assert count==3
    with f.open(stream=result) as d:assert all('CODIGO NUEVO' in p.get_text() for p in d)


def test_copy_enables_native_image_movement_without_changing_other_pages():
    base=source()
    with f.open(stream=base) as d:assert not any(i['editable'] for i in image_model(d,0)['images'])
    out,_=create(base,[],True)
    with f.open(stream=out) as d:item=image_model(d,0)['images'][0];assert item['editable'],item['reason']
    result=edit_image(out,[],0,item['xref'],'move',[110,180,100,50],occurrence=item['occurrence'])
    with f.open(stream=out) as a,f.open(stream=result) as b:
        assert a[0].get_text()==b[0].get_text() and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert list(b[0].get_image_info()[0]['bbox'])==[110,180,210,230]


def test_explicit_split_without_tags_preserves_native_pages_and_original():
    base=source();names=[f'1.46 PINTURA {n:03d}' for n in range(1,4)]
    with pytest.raises(DocumentError,match='estructura etiquetada'):split_pdf(base,[],size=1,names=names)
    data=split_pdf(base,[],size=1,names=names,preserve_tags=False,manifest=True)
    with ZipFile(BytesIO(data)) as z,f.open(stream=base) as original:
        assert z.namelist()==[n+'.pdf' for n in names]+['reapdf-division.json']
        assert json.loads(z.read('reapdf-division.json'))['accessibility_tags_retained'] is False
        for i,name in enumerate(names):
            with f.open(stream=z.read(name+'.pdf')) as part:
                assert part.xref_get_key(part.pdf_catalog(),'StructTreeRoot')[0]=='null'
                assert part[0].get_pixmap().samples==original[i].get_pixmap().samples
                assert 'CODIGO GENERAL' in part[0].get_text() and part[0].get_images()
        assert original.xref_get_key(original.pdf_catalog(),'StructTreeRoot')[0]!='null'


@pytest.mark.parametrize('ack',[False,None,1,'yes'])
def test_tag_removal_needs_explicit_acknowledgement(ack):
    with pytest.raises(DocumentError,match='Confirma'):create(source(),[],ack)


def test_permissions_and_signature_flags_cannot_be_bypassed():
    base=source()
    with f.open(stream=base) as d:protected=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner123',permissions=f.PDF_PERM_COPY)
    with pytest.raises(DocumentError):create(protected,[],True)
    with pytest.raises(DocumentError):split_pdf(protected,[],size=1,preserve_tags=False)
    with f.open(stream=base) as d:
        d.xref_set_key(d.pdf_catalog(),'AcroForm','<< /SigFlags 3 >>');signed=d.tobytes()
    with pytest.raises(DocumentError):create(signed,[],True)
    with pytest.raises(DocumentError):split_pdf(signed,[],size=1,preserve_tags=False)


def test_unexpected_content_change_aborts_the_copy(monkeypatch):
    import backend.untagged_copy as module
    detach=module.detach
    def broken(d):detach(d);d[0].insert_text((40,400),'ACCIDENTAL CHANGE')
    monkeypatch.setattr(module,'detach',broken)
    with pytest.raises(DocumentError,match='alteró contenido'):create(source(),[],True)


def test_api_preserves_source_and_creates_new_working_identity():
    base=source()
    with TestClient(app) as c:
        d=c.post('/api/documents',files={'file':('Tagged.pdf',base,'application/pdf')}).json();url='/api/documents/'+d['id']
        assert c.post(url+'/untagged-copy',json={}).status_code==422
        result=c.post(url+'/untagged-copy',json={'acknowledge':True});assert result.status_code==200,result.text
        copy=result.json();assert copy['working_copy'] and copy['id']!=d['id'] and not copy['tagged']
        assert c.post(url+'/export',json={}).content==base
        split=c.post(url+'/split',json={'size':1,'preserve_tags':False,'names':['A','B','C']});assert split.status_code==200,split.text
        with ZipFile(BytesIO(split.content)) as z:assert z.namelist()==['A.pdf','B.pdf','C.pdf']


def test_copy_preserves_live_form_values_appearances_and_field_actions():
    with f.open(stream=source()) as d:
        w=f.Widget();w.field_name='KEEP_FIELD';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_value='KEEP VALUE';w.rect=f.Rect(40,350,200,380);d[0].add_widget(w)
        widget=next(d[0].widgets());d.xref_set_key(widget.xref,'AA','<< /K << /S/JavaScript /JS (event.rc = true;) >> >>');base=d.tobytes()
    out,_=create(base,[],True)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        old=next(a[0].widgets());new=next(b[0].widgets());assert (new.field_name,new.field_value,new.rect)==(old.field_name,old.field_value,old.rect)
        assert a.xref_get_key(old.xref,'AA')==b.xref_get_key(new.xref,'AA')
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples


def test_pending_annotation_is_carried_into_copy_once_without_touching_source():
    base=source();op={'type':'note','page':1,'point':[250,300],'content':'PENDING NOTE','color':[1,1,0]}
    result,_=create(base,[op],True)
    with f.open(stream=result) as d:assert [a.info['content'] for a in d[1].annots()]==['PENDING NOTE']
    with f.open(stream=base) as d:assert not list(d[1].annots() or [])


@pytest.mark.parametrize('mode',[0,'false'])
def test_tag_preservation_choice_is_never_coerced_to_false(mode):
    with pytest.raises(DocumentError,match='etiquetas de accesibilidad'):split_pdf(source(),[],size=1,preserve_tags=mode)
