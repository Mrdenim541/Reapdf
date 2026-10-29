import pymupdf as f
import pytest
from backend.engine import DocumentError,open_pdf
from backend import structure_editing as tags,preflight,region_ocr,document_sets
from backend.rendering import render_page,MAX_PIXELS
from tests.test_document_workspaces import pdf,item,relation


def tagged():
    with f.open() as d:
        page=d.new_page();page.insert_text((40,80),'PARRAFO');page.draw_rect(f.Rect(40,100,140,150),color=(1,0,0));page_ref=page.xref
        root=d.get_new_xref();parent=d.get_new_xref();figure=d.get_new_xref();paragraph=d.get_new_xref();tree=d.get_new_xref()
        d.update_object(root,f'<</Type/StructTreeRoot/K[{parent} 0 R]/ParentTree {tree} 0 R>>')
        d.update_object(parent,f'<</Type/StructElem/S/Document/P {root} 0 R/K[{figure} 0 R {paragraph} 0 R]>>')
        d.update_object(figure,f'<</Type/StructElem/S/Figure/P {parent} 0 R/Pg {page_ref} 0 R/K 1/Alt(Figura original)>>')
        d.update_object(paragraph,f'<</Type/StructElem/S/P/P {parent} 0 R/Pg {page_ref} 0 R/K 0>>')
        d.update_object(tree,f'<</Nums[0[{paragraph} 0 R {figure} 0 R]]>>');d.xref_set_key(page_ref,'StructParents','0');d.xref_set_key(d.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');d.xref_set_key(d.pdf_catalog(),'MarkInfo','<</Marked true>>')
        data=page.read_contents();x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'/P<</MCID 0>>BDC\n'+data+b'\nEMC');page.set_contents(x)
        return d.tobytes()


def test_alternative_and_sibling_order_survive_save_with_identical_pixels():
    base=tagged();info=tags.model(base,[]);figure=next(r for r in info['nodes'] if r['role']=='Figure');assert figure['can_alt']
    out=tags.edit(base,[],figure['id'],alt='Plano técnico con dos elementos');updated=tags.model(out,[]);assert next(r for r in updated['nodes'] if r['role']=='Figure')['alt']=='Plano técnico con dos elementos'
    parent=next(r for r in updated['nodes'] if r['role']=='Document');out=tags.edit(out,[],parent['id'],order=list(reversed(parent['children'])))
    assert [r['role'] for r in tags.model(out,[])['nodes']]==['Document','P','Figure']
    with f.open(stream=base) as a,f.open(stream=out) as b:assert a[0].get_text()==b[0].get_text() and a[0].get_pixmap().samples==b[0].get_pixmap().samples


@pytest.mark.parametrize('kind',['unknown','duplicate_order','bad_parent','empty_alt','actual_text'])
def test_structure_edits_reject_ambiguous_or_unsafe_changes(kind):
    base=tagged();info=tags.model(base,[]);figure=next(r for r in info['nodes'] if r['role']=='Figure');parent=next(r for r in info['nodes'] if r['role']=='Document')
    if kind=='unknown':
        with pytest.raises(DocumentError):tags.edit(base,[],99999,alt='Alt')
    elif kind=='duplicate_order':
        with pytest.raises(DocumentError):tags.edit(base,[],parent['id'],order=[figure['id'],figure['id']])
    elif kind=='empty_alt':
        with pytest.raises(DocumentError):tags.edit(base,[],figure['id'],alt='')
    else:
        with f.open(stream=base) as d:
            d.xref_set_key(figure['id'],'P','1 0 R') if kind=='bad_parent' else d.xref_set_key(figure['id'],'ActualText','(Special)');base=d.tobytes()
        with pytest.raises(DocumentError):tags.edit(base,[],figure['id'],alt='Alt')


def test_preflight_effective_dpi_embedded_fonts_boxes_and_cmyk():
    with f.open() as d:
        page=d.new_page();pix=f.Pixmap(f.csRGB,f.IRect(0,0,100,100));pix.clear_with(100);page.insert_image(f.Rect(40,100,240,300),pixmap=pix);page.insert_text((40,80),'HELLO');data=d.tobytes()
    report=preflight.inspect(data,[],150);assert report['pages'][0]['images'][0]['dpi']==[36.,36.] and any(i['code']=='image_resolution' for i in report['issues'])
    with f.open(stream=data) as d:
        page=d[0];x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'0 1 0 0 k 0 0 50 50 re f');page.set_contents(x);data=d.tobytes()
    assert 'CMYK' in preflight.inspect(data,[])['pages'][0]['vector_colors']


def mixed_scan(rotation=0):
    with f.open() as scan:
        p=scan.new_page(width=400,height=120);p.insert_text((15,70),'SCAN ID-123',fontsize=28);image=p.get_pixmap(matrix=f.Matrix(2,2)).tobytes('png')
    with f.open() as doc:
        p=doc.new_page(width=600,height=800);p.insert_text((40,60),'DIGITAL HEADER');p.insert_image(f.Rect(40,150,440,270),stream=image);p.set_rotation(rotation);doc.new_page().insert_text((40,80),'OTHER PAGE');return doc.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_region_ocr_on_mixed_page_preserves_pixels_and_maps_search_boxes(rotation):
    base=mixed_scan(rotation)
    with f.open(stream=base) as d:visible=f.Rect(40,150,440,270)*d[0].rotation_matrix
    box=[visible.x0,visible.y0,visible.width,visible.height]
    out,report=region_ocr.recognize(base,[],[{'page':0,'box':box}],language='eng',dpi=200)
    assert report['words']>=2
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert '123' in b[0].get_text() and 'DIGITAL HEADER' in b[0].get_text() and b[0].rotation==rotation
        # Adding GlyphLessFont can change renderer anti-alias rounding by one
        # RGB level on pre-existing vector text. Raster image bytes and original
        # content operators remain unchanged; do not claim bit-identical raster.
        assert max(abs(x-y) for x,y in zip(a[0].get_pixmap().samples,b[0].get_pixmap().samples))<=1
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert a[0].get_image_info(xrefs=True)[0]['digest']==b[0].get_image_info(xrefs=True)[0]['digest']
        assert all((visible+(-1,-1,1,1)).contains(rect*b[0].rotation_matrix) for rect in b[0].search_for('123'))
    with pytest.raises(DocumentError):region_ocr.recognize(out,[],[{'page':0,'box':box}],language='eng')


@pytest.mark.parametrize('kind',['digital','overlap','bounds','unit'])
def test_region_ocr_rejects_invalid_regions_before_recognition(kind):
    base=mixed_scan();regions=[{'page':0,'box':[40,150,400,120]}];kwargs={}
    if kind=='digital':regions=[{'page':0,'box':[20,20,500,300]}]
    if kind=='overlap':regions*=2
    if kind=='bounds':regions=[{'page':0,'box':[-1,0,200,200]}]
    if kind=='unit':kwargs['dpi']=1000
    with pytest.raises(DocumentError):region_ocr.recognize(base,[],regions,**kwargs)


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_compiled_pdf_keeps_page_pixels_and_resolved_native_links(rotation):
    a=item(pdf('PLAN-01',rotation=rotation));b=item(pdf('PLAN-01'),'Destino');r=relation(a,b)
    data,report=document_sets.compile_pdf([a,b],[r],'Compilado');assert report['pages']==2 and report['links']==1
    with f.open(stream=a['data']) as x,f.open(stream=b['data']) as y,f.open(stream=data) as out:
        assert out[0].get_pixmap().samples==x[0].get_pixmap().samples and out[1].get_pixmap().samples==y[0].get_pixmap().samples
        links=out[0].get_links();assert len(links)==1 and links[0]['page']==1 and list(links[0]['from'])==pytest.approx(r['source']['rect'],abs=.02)
        assert len(out.get_toc())>=2


def test_compilation_rejects_one_anchor_with_multiple_targets():
    a=item(pdf());b=item(pdf(repeat=True),'Destino');r=relation(a,b);second={**r,'id':'f'*32,'target':document_sets.analyze([a,b],a['id'],b['id'])['candidates'][0]['target'][1]}
    with pytest.raises(DocumentError,match='varios destinos'):document_sets.compile_pdf([a,b],[r,second],'X')


def test_a0_and_large_pages_open_with_memory_bounded_render():
    with f.open() as doc:doc.new_page(width=2384,height=3370);base=doc.tobytes()
    with open_pdf(base) as doc:
        png,headers=render_page(doc[0],4);assert int(headers['X-Render-Width'])*int(headers['X-Render-Height'])<=MAX_PIXELS and png.startswith(b'\x89PNG')
    with f.open() as doc:doc.new_page(width=6001,height=100);too_big=doc.tobytes()
    with pytest.raises(DocumentError):open_pdf(too_big)
