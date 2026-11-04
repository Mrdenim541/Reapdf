from io import BytesIO
import base64
import pymupdf as f
import pytest
from pyhanko.pdf_utils.reader import PdfFileReader
from backend.basic_tagging import candidates,create
from backend.image_editing import image_model,edit_image,_page_matrix
from backend.engine import DocumentError
from backend.structure_editing import model
from backend.tagged_text_integrity import snapshot
from tests.test_media_tagging import source as untagged
from tests.test_images import picture


def source(rotation=0,crop=False,kind='integer'):
    base=untagged(rotation,crop,links=False,repeated=True);info=candidates(base,[])
    tagged=create(base,[],[{'id':e['id'],'role':'Figure','alt':'Original picture'} if e['kind']=='image' else {'id':e['id'],'role':'P'} for e in info['entries']],reviewed=True)[0]
    with f.open(stream=tagged) as doc:
        figures=[r for r in model(tagged,[])['nodes'] if r['role']=='Figure']
        attrs=doc.get_new_xref();doc.update_object(attrs,'<</O /Layout /Placement /Block /Width 180 /Height 120>>')
        for row in figures:
            native_box=[40,120,220,240] if row==figures[0] else [270,120,450,240]
            doc.xref_set_key(row['id'],'A',f'[<</O /Layout /BBox [{" ".join(map(str,native_box))}]>> {attrs} 0 R 0]')
            code=doc.xref_get_key(row['id'],'K')[1]
            if kind=='array':doc.xref_set_key(row['id'],'K',f'[{code}]')
            elif kind=='mcr':doc.xref_set_key(row['id'],'K',f'<</Type /MCR /Pg {doc[0].xref} 0 R /MCID {code}>>')
        return doc.tobytes(garbage=2)


def selected(base):
    with f.open(stream=base) as doc:return image_model(doc,0)['images'][0]


def inspect(data):
    reader=PdfFileReader(BytesIO(data));root=reader.root['/StructTreeRoot'];figures=[]
    def walk(obj):
        if hasattr(obj,'get_object'):obj=obj.get_object()
        if isinstance(obj,list):
            for child in obj:walk(child)
        elif hasattr(obj,'get'):
            if obj.get('/S')=='/Figure':figures.append(obj)
            k=obj.get('/K')
            if k is not None:walk(k)
    walk(root['/K']);return reader,figures


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
@pytest.mark.parametrize('kind',['integer','array','mcr'])
def test_native_move_keeps_tag_tree_order_other_image_and_selectable_text(rotation,crop,kind):
    base=source(rotation,crop,kind);row=selected(base);assert row['editable'] and row['tagged_figure']
    old=f.Rect(row['rect']);box=[old.x0+4,old.y0+3,old.width*.8,old.height*.7]
    result=edit_image(base,[],0,row['xref'],'move',box,occurrence=row['occurrence'])
    with f.open(stream=base) as a,f.open(stream=result) as b:
        assert a[0].get_text('dict',flags=f.TEXTFLAGS_TEXT)==b[0].get_text('dict',flags=f.TEXTFLAGS_TEXT)
        assert a[0].get_image_info(hashes=True)[1]['bbox']==b[0].get_image_info(hashes=True)[1]['bbox']
        assert a[0].get_image_info(hashes=True)[1]['digest']==b[0].get_image_info(hashes=True)[1]['digest']
        assert a[0].rotation==b[0].rotation and a[0].cropbox==b[0].cropbox
        new=image_model(b,0)['images'][0];assert new['editable'] and new['alt']=='Original picture'
        expected=f.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3])*~(_page_matrix(b[0])*b[0].rotation_matrix)
    _,before=inspect(base);_,after=inspect(result);assert len(before)==len(after)==2
    assert float(after[0]['/A'][1]['/Width'])==pytest.approx(old.width*.8 if rotation%180==0 else old.height*.7,abs=.001)
    assert [float(v) for v in after[0]['/A'][0]['/BBox']]==pytest.approx(list(expected),abs=.001)
    assert list(after[1]['/A'][0]['/BBox'])==list(before[1]['/A'][0]['/BBox'])
    assert after[1]['/A'][1]['/Width']==180 and after[1]['/A'][1]['/Height']==120


@pytest.mark.parametrize('kind',['integer','array','mcr'])
def test_delete_removes_owner_and_parenttree_slot_without_touching_other_mcids(kind):
    base=source(kind=kind);row=selected(base);result=edit_image(base,[],0,row['xref'],'delete',occurrence=row['occurrence'])
    reader,figures=inspect(result);assert len(figures)==1
    nums=reader.root['/StructTreeRoot']['/ParentTree']['/Nums']
    # A real null occupies the removed figure MCID; all surviving indices stay stable.
    from pyhanko.pdf_utils.generic import NullObject
    assert isinstance(nums[1][2],NullObject)
    with f.open(stream=base) as a,f.open(stream=result) as b:
        assert a[0].get_text()==b[0].get_text() and len(b[0].get_image_info(hashes=True))==1
        assert b[0].get_image_info(hashes=True)[0]['bbox']==a[0].get_image_info(hashes=True)[1]['bbox']
        assert b'MCID 2' not in b[0].read_contents() and b'MCID 3' in b[0].read_contents()
        assert image_model(b,0)['images'][0]['editable']


def test_replacement_preserves_geometry_and_requires_updated_accessible_description():
    base=source();row=selected(base);data=base64.b64encode(picture()).decode()
    for alt in [None,'',' ','bad\x00text']:
        with pytest.raises(DocumentError,match='descripción'):edit_image(base,[],0,row['xref'],'replace',data=data,occurrence=row['occurrence'],alt=alt)
    result=edit_image(base,[],0,row['xref'],'replace',data=data,occurrence=row['occurrence'],alt='New diagram with dimensions')
    _,figures=inspect(result);assert figures[0]['/Alt']=='New diagram with dimensions' and figures[1]['/Alt']=='Original picture'
    with f.open(stream=result) as doc:
        rows=image_model(doc,0)['images'];assert rows[0]['rect']==row['rect'] and rows[0]['digest']!=row['digest'] and rows[0]['editable']


@pytest.mark.parametrize('variant',['ancestor_alt','leaf_alt','class','namespace','duplicate_owner','wrong_parent','duplicate_page_key','mixed_content','nested_actualtext','idtree'])
def test_ambiguous_semantics_stay_protected(variant):
    base=source();info=model(base,[]);figure=next(r for r in info['nodes'] if r['role']=='Figure')
    with f.open(stream=base) as doc:
        if variant=='ancestor_alt':doc.xref_set_key(figure['parent'],'ActualText','(Alternative)')
        elif variant=='leaf_alt':doc.xref_set_key(figure['id'],'ActualText','(Alternative)')
        elif variant=='class':doc.xref_set_key(figure['id'],'C','/Shared')
        elif variant=='namespace':doc.xref_set_key(figure['id'],'NS','<<>>')
        elif variant=='wrong_parent':doc.xref_set_key(figure['id'],'P',f'{info["root"]} 0 R')
        elif variant=='duplicate_owner':
            second=[r for r in info['nodes'] if r['role']=='Figure'][1];doc.xref_set_key(second['id'],'K','2')
        elif variant=='duplicate_page_key':
            key=doc.xref_get_key(doc[0].xref,'StructParents')[1];p=doc.new_page();doc.xref_set_key(p.xref,'StructParents',key)
        elif variant=='idtree':doc.xref_set_key(info['root'],'IDTree','<<>>')
        else:
            content=doc[0].read_contents();marker=b'/Figure <</MCID 2>> BDC'
            assert marker in content
            if variant=='mixed_content':content=content.replace(marker,marker+b'\n0 0 4 4 re f')
            else:content=content.replace(marker,marker+b'\n/Span <</ActualText (Hidden alternative)>> BDC').replace(b'/fzImg0 Do',b'/fzImg0 Do EMC',1)
            from backend.pdf_content import set_content
            set_content(doc,doc[0],content)
        bad=doc.tobytes(garbage=2)
    row=selected(bad)
    if variant=='idtree':assert row['editable'] and 'delete' not in row['actions']
    else:
        assert not row['editable']
        with pytest.raises(DocumentError):edit_image(bad,[],0,row['xref'],'move',[44,164,150,100],occurrence=row['occurrence'])


def test_unrelated_actualtext_is_preserved_without_relaxing_text_edit_guard():
    base=source();info=model(base,[]);text=next(r for r in info['nodes'] if r['role']=='P')
    with f.open(stream=base) as d:d.xref_set_key(text['id'],'ActualText','(Separate alternative)');base=d.tobytes()
    row=selected(base);assert row['editable']
    result=edit_image(base,[],0,row['xref'],'move',[44,164,150,100],occurrence=row['occurrence'])
    with f.open(stream=result) as d:
        assert snapshot(d,0,allow_actual_text=True)
        with pytest.raises(DocumentError):snapshot(d,0)


def test_semantic_corruption_in_content_writer_aborts_publication(monkeypatch):
    from backend import image_editing
    original=image_editing.write
    def corrupt(doc,page,prepared):
        original(doc,page,prepared);root=int(doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[1].split()[0]);doc.xref_set_key(root,'Lang','(corrupt)')
    monkeypatch.setattr(image_editing,'write',corrupt);base=source();row=selected(base)
    with pytest.raises(DocumentError,match='estructura semántica'):edit_image(base,[],0,row['xref'],'move',[44,164,150,100],occurrence=row['occurrence'])


@pytest.mark.parametrize('action',['move','replace','delete'])
def test_api_preview_apply_and_export_preserve_original_and_tags(action):
    from fastapi.testclient import TestClient
    from backend.app import app
    from scripts.create_tagged_image_sample import create
    base=create()
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('tagged.pdf',base,'application/pdf')}).json()
        row=client.get(f"/api/documents/{doc['id']}/pages/0/existing-images").json()['images'][0]
        payload={'operations':[],'page':0,'xref':row['xref'],'occurrence':row['occurrence'],'action':action,'box':[50,150,150,70],'data':base64.b64encode(picture()).decode(),'alt':'Updated alternative'}
        url=f"/api/documents/{doc['id']}/edit-image"
        preview=client.post(url,json={**payload,'preview':True});assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
        changed=client.post(url,json=payload);assert changed.status_code==200,changed.text
        output=client.post(f"/api/documents/{changed.json()['id']}/export",json={'operations':[]}).content
        _,figures=inspect(output);assert len(figures)==(1 if action=='delete' else 2)
        if action=='replace':assert figures[0]['/Alt']=='Updated alternative'
        original=client.post(f"/api/documents/{doc['id']}/export",json={'operations':[]}).content
        with f.open(stream=base) as a,f.open(stream=original) as b:assert a[0].get_pixmap().samples==b[0].get_pixmap().samples

def test_pending_note_is_carried_once_without_altering_other_semantics():
    from scripts.create_tagged_image_sample import create
    base=create();row=selected(base);op={'type':'note','page':1,'point':[250,300],'content':'Pending note','color':[1,1,0]}
    result=edit_image(base,[op],0,row['xref'],'move',[50,150,150,70],occurrence=row['occurrence'])
    with f.open(stream=result) as d:assert [a.info['content'] for a in d[1].annots()]==['Pending note']
    assert len(inspect(result)[1])==2


def test_image_in_large_42_page_tag_tree_keeps_all_other_pages_and_tags():
    from scripts.create_split_sample import create as large
    with f.open(stream=large()) as d:
        n=f.mupdf;pdf=f._as_pdf_document(d);root=n.pdf_dict_gets(n.pdf_dict_gets(n.pdf_trailer(pdf),'Root'),'StructTreeRoot');document=n.pdf_dict_gets(root,'K');sections=n.pdf_dict_gets(document,'K');section=n.pdf_array_get(sections,0)
        pix=f.Pixmap(f.csRGB,f.IRect(0,0,80,40),False);pix.clear_with(100);d[0].insert_image(f.Rect(400,720,560,800),pixmap=pix)
        stream=d[0].get_contents()[-1];d.update_stream(stream,b'/Figure <</MCID 60>> BDC\n'+d.xref_stream(stream)+b'\nEMC')
        figure=d.get_new_xref();d.update_object(figure,f'<</Type /StructElem /S /Figure /P {n.pdf_to_num(section)} 0 R /Pg {d[0].xref} 0 R /K 60 /Alt (Diagram)>>');ref=n.pdf_new_indirect(pdf,figure,0);n.pdf_array_push(n.pdf_dict_gets(section,'K'),ref)
        nums=n.pdf_dict_gets(n.pdf_dict_gets(root,'ParentTree'),'Nums');n.pdf_array_push(n.pdf_array_get(nums,1),ref);base=d.tobytes()
    row=selected(base);assert row['editable']
    result=edit_image(base,[],0,row['xref'],'move',[410,725,140,70],occurrence=row['occurrence'])
    with f.open(stream=base) as a,f.open(stream=result) as b:
        assert len(a)==len(b)==42
        with pytest.raises(DocumentError):snapshot(a,0) # Las alternativas siguen protegidas en la edición de texto.
        assert snapshot(b,0,allow_actual_text=True)['nodes']>2000
        assert all(a[i].get_text()==b[i].get_text() and a[i].get_pixmap().samples==b[i].get_pixmap().samples for i in range(1,42))


@pytest.mark.parametrize('transformed',[False,True])
def test_native_rectangular_page_clip_allows_full_frame_inside_clip(transformed):
    from backend.pdf_content import set_content
    base=source()
    with f.open(stream=base) as d:
        prefix=b'q 2 0 0 2 -20 -20 cm 10 10 250 200 re W n 0.5 0 0 0.5 10 10 cm\n' if transformed else b'q 0 0 500 400 re W n\n'
        set_content(d,d[0],prefix+d[0].read_contents()+b'\nQ');base=d.tobytes()
    row=selected(base);assert row['editable'];assert edit_image(base,[],0,row['xref'],'move',[44,164,150,100],occurrence=row['occurrence'])


def test_crossing_native_page_clip_is_rejected_before_publication():
    from backend.pdf_content import set_content
    base=source()
    with f.open(stream=base) as d:set_content(d,d[0],b'q 40 120 180 120 re W n\n'+d[0].read_contents()+b'\nQ');base=d.tobytes()
    row=selected(base);assert row['editable']
    with pytest.raises(DocumentError,match='recorte de la página'):edit_image(base,[],0,row['xref'],'move',[80,164,180,120],occurrence=row['occurrence'])


def test_curved_page_clip_requires_coordinated_clipping_edit():
    from backend.pdf_content import set_content
    base=source()
    with f.open(stream=base) as d:set_content(d,d[0],b'q 0 0 m 500 0 l 500 400 0 400 0 0 c W n\n'+d[0].read_contents()+b'\nQ');base=d.tobytes()
    row=selected(base);assert row['editable'] and row['actions']==['replace','delete']
    assert edit_image(base,[],0,row['xref'],'delete',occurrence=row['occurrence'])
    replacement=edit_image(base,[],0,row['xref'],'replace',data=base64.b64encode(picture()).decode(),occurrence=row['occurrence'],alt='Replacement within original clip')
    assert len(inspect(replacement)[1])==2


@pytest.mark.parametrize('masked',[False,True])
def test_external_softmask_keeps_replacement_and_delete_but_protects_movement(masked):
    from backend.pdf_content import set_content
    base=source()
    with f.open(stream=base) as d:
        form=d.get_new_xref();d.update_object(form,'<</Type /XObject /Subtype /Form /BBox [0 0 500 400] /Resources <<>> /Group <</S /Transparency /CS /DeviceGray>>>>');d.update_stream(form,b'1 g 0 0 500 400 re f')
        mask=f'<</S /Alpha /G {form} 0 R>>' if masked else '/None'
        resources=int(d.xref_get_key(d[0].xref,'Resources')[1].split()[0]);d.xref_set_key(resources,'ExtGState',f'<</Mask <</Type /ExtGState /SMask {mask}>>>>');set_content(d,d[0],b'q /Mask gs\n'+d[0].read_contents()+b'\nQ');base=d.tobytes()
    row=selected(base);assert row['editable'] and ('move' in row['actions']) is not masked
    replacement=edit_image(base,[],0,row['xref'],'replace',data=base64.b64encode(picture()).decode(),occurrence=row['occurrence'],alt='New masked image')
    assert len(inspect(replacement)[1])==2
    if masked:
        with pytest.raises(DocumentError,match='recorte'):edit_image(base,[],0,row['xref'],'move',[44,164,150,100],occurrence=row['occurrence'])
