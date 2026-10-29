import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, spans
from backend.viewer import text_items, search_document

@pytest.fixture
def pdf():
    with fitz.open() as doc:
        p=doc.new_page(width=400,height=500)
        p.insert_text((40,80),'Texto original',fontsize=16)
        p=doc.new_page(width=400,height=500)
        p.insert_text((40,80),'Otra pagina original',fontsize=12)
        p.set_rotation(90)
        return doc.tobytes()

@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_search_and_selection_geometry_matches_visible_page(rotation):
    with fitz.open() as doc:
        page=doc.new_page(width=400,height=500)
        page.insert_text((40,80),'Texto visible',fontsize=16)
        page.set_rotation(rotation)
        data=text_items(page)[0]
        source=fitz.Rect(spans(page)[0]['bbox'])
        anchor=source.tl*page.rotation_matrix
        assert (data['x'],data['y'])==pytest.approx((anchor.x,anchor.y))
        assert data['width']==pytest.approx(source.width)
        assert data['rotation']==rotation
        result=search_document(doc,'Texto visible')['results'][0]
        assert result['page']==0
        assert tuple(result['rect'])==pytest.approx(tuple(source*page.rotation_matrix),abs=.01)

@pytest.mark.parametrize('query',['', '   ', None, 12, 'a'*201])
def test_search_rejects_invalid_query(pdf,query):
    with fitz.open(stream=pdf,filetype='pdf') as doc:
        with pytest.raises(DocumentError):search_document(doc,query)

def test_search_limits_large_result_set():
    with fitz.open() as doc:
        page=doc.new_page(width=650,height=650)
        for row in range(20):
            for col in range(30):page.insert_text((10+col*20,20+row*25),'x',fontsize=6)
        result=search_document(doc,'x')
        assert len(result['results'])==500
        assert result['truncated'] is True

def test_search_text_and_thumbnails_use_current_edited_content(pdf):
    with TestClient(app) as client:
        info=client.post('/api/documents',files={'file':('demo.pdf',pdf)}).json()
        base=f"/api/documents/{info['id']}"
        source=client.get(base+'/pages/0').json()['spans'][0]
        op={'type':'text','page':0,'span_id':source['id'],'text':'Texto nuevo'}
        body={'operations':[op]}
        result=client.post(base+'/search',json={**body,'query':' original '})
        assert result.status_code==200
        matches=result.json()['results']
        assert len(matches)==1 and matches[0]['page']==1
        assert client.post(base+'/search',json={**body,'query':'nuevo'}).json()['results'][0]['page']==0
        assert client.post(base+'/search',json={**body,'query':'inexistente'}).json()['results']==[]
        text=client.post(base+'/pages/0/text',json=body)
        assert text.status_code==200
        assert [item['text'] for item in text.json()['items']]==['Texto nuevo']
        thumb=client.post(base+'/pages/0/thumbnail',json=body)
        original_thumb=client.post(base+'/pages/0/thumbnail',json={'operations':[]})
        assert thumb.status_code==200 and thumb.content.startswith(b'\x89PNG')
        image=fitz.Pixmap(thumb.content)
        assert image.width<=150 and image.height<=200
        assert thumb.content!=original_thumb.content
        # La fuente permanece disponible con su texto sin modificar.
        assert client.get(base+'/pages/0').json()['spans'][0]['text']=='Texto original'
        assert client.post(base+'/pages/99/text',json=body).status_code==404
        assert client.post(base+'/pages/99/thumbnail',json=body).status_code==404
        assert client.post(base+'/search',json={**body,'query':''}).status_code==422

def test_bookmark_hierarchy_and_destinations_survive_export(pdf):
    from backend.engine import metadata, export_pdf
    with fitz.open(stream=pdf,filetype='pdf') as doc:
        doc.set_toc([[1,'Inicio',1],[2,'Detalle',2],[1,'Sin destino',-1]])
        data=doc.tobytes()
        original=metadata(doc)
    assert original['bookmarks']==[
        {'level':1,'title':'Inicio','page':0},
        {'level':2,'title':'Detalle','page':1},
        {'level':1,'title':'Sin destino','page':None},
    ]
    op={'type':'line','page':0,'points':[[40,200],[150,200]],'color':[1,0,0],'width':2}
    with fitz.open(stream=export_pdf(data,[op]),filetype='pdf') as doc:
        assert metadata(doc)['bookmarks']==original['bookmarks']
