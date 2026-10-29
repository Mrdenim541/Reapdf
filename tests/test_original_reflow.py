import hashlib
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.original_reflow import inspect,reflow
from pathlib import Path
FONT=Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf'


def source(rotation=0):
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='Original',fontfile=str(FONT));p.insert_text((40,80),'Texto original para probar el parrafo',fontname='Original',fontsize=14);p.insert_text((40,400),'CONTENIDO CONSERVADO');p.set_rotation(rotation);d.subset_fonts();return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_reflow_wraps_original_subset_and_preserves_neighbor_program_rotation(rotation):
    base=source(rotation)
    with f.open(stream=base) as d:span=d[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
    model=inspect(base,[],0,list(span['origin']),span['text']);assert model['original_available'],model['reason']
    box=model['box'];box=[box[0],box[1],box[2],120];text='Texto original para probar el parrafo Texto original para probar el parrafo'
    preview=reflow(base,[],0,box,text,True,model['box']);out,report=reflow(base,[],0,box,text,source_box=model['box']);assert report==preview and report['lines']>=2
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].rotation==rotation and 'CONTENIDO CONSERVADO' in b[0].get_text()
        assert b[0].search_for('CONTENIDO CONSERVADO')==a[0].search_for('CONTENIDO CONSERVADO')
        old=next(i for i in a[0].get_fonts() if i[2]=='Type0');new=next(i for i in b[0].get_fonts() if i[2]=='Type0');assert hashlib.sha256(a.extract_font(old[0])[3]).digest()==hashlib.sha256(b.extract_font(new[0])[3]).digest()
        assert 'Texto original para probar el parrafo' in ' '.join(b[0].get_text().split())


@pytest.mark.parametrize('kind',['glyph','overflow','neighbor','drawing','tagged','clip','layer','link'])
def test_reflow_refuses_unsupported_without_partial_edits(kind):
    base=source();text='Texto original para probar el parrafo';box=[38,62,280,120]
    if kind=='glyph':text+=' Ω'
    if kind=='overflow':text='Texto '*100;box[3]=25
    if kind in ['neighbor','drawing','tagged','clip','layer','link']:
        with f.open(stream=base) as d:
            p=d[0]
            if kind=='neighbor':p.insert_text((40,140),'OTRO BLOQUE')
            if kind=='drawing':p.draw_line((35,120),(400,120))
            if kind=='tagged':d.xref_set_key(d.pdf_catalog(),'StructTreeRoot','<< /Type /StructTreeRoot /K [] >>')
            if kind=='clip':
                x=p.get_contents()[0];d.update_stream(x,b'q 0 0 595 842 re W n '+d.xref_stream(x)+b' Q')
            if kind=='layer':d.add_ocg('Capa')
            if kind=='link':p.insert_link({'kind':f.LINK_URI,'from':f.Rect(40,110,100,130),'uri':'https://example.com'})
            base=d.tobytes()
    before=hashlib.sha256(base).hexdigest()
    with pytest.raises(DocumentError):reflow(base,[],0,box,text,source_box=[38,62,280,25])
    assert hashlib.sha256(base).hexdigest()==before


def test_inline_paragraph_api_keeps_source_on_failed_fit(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'));base=source()
    with f.open(stream=base) as d:span=d[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('Parrafo.pdf',base)}).json();url=f"/api/documents/{doc['id']}"
        model=client.post(url+'/inline-block',json={'page':0,'origin':list(span['origin']),'text':span['text']}).json();box=[*model['box'][:3],120]
        payload={'page':0,'box':box,'source_box':model['box'],'text':span['text']+' '+span['text']}
        preview=client.post(url+'/reflow-original',json={**payload,'preview':True});assert preview.status_code==200 and preview.json()['lines']>=2
        out=client.post(url+'/reflow-original',json=payload);assert out.status_code==200 and out.json()['id']!=doc['id']
        assert client.post(url+'/reflow-original',json={**payload,'text':'Ω'}).status_code==422
        assert client.post(url+'/export',json={'operations':[]}).content==base
