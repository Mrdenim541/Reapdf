from copy import deepcopy
import re,shutil,subprocess,unicodedata
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.text_flow import flow_text,inspect_flow
from backend.paragraphs import paragraph_font
from backend.mixed_flow import validate_runs
from tests.test_text_flow import source,regions


def run(text,style='regular',size=12,color=None,family='sans'):
    return {'text':text,'family':family,'style':style,'size':size,'color':color or [0,0,0]}

def mixed_source(rotation=0,crop=False):
    with f.open() as doc:
        p=doc.new_page(width=400,height=500)
        x=40
        for row in [run('Texto ',size=12),run('destacado ',style='bold',size=18,color=[.2,.4,.6]),run('cursivo',style='italic',size=10,color=[.7,.1,.2],family='serif')]:
            font=paragraph_font(row['family'],row['style']);w=f.TextWriter(p.rect);w.append((x,75),row['text'],font=font,fontsize=row['size']);w.write_text(p,color=row['color']);x+=font.text_length(row['text'],fontsize=row['size'])
        p.insert_text((40,430),'Pie original conservado')
        doc.new_page(width=400,height=500).insert_text((40,430),'Pie destino conservado')
        doc.new_page(width=400,height=500).insert_text((40,75),'Otra pagina intacta')
        for p in doc:
            if crop:p.set_cropbox(f.Rect(10,10,390,490))
            p.set_rotation(rotation)
        return doc.tobytes()

def text(runs):return ''.join(row['text'] for row in runs)

def plans():return [run('Inicio regular. '*8),run('IMPORTANTE en negrita. '*8,'bold',18,[.2,.4,.6]),run('Texto cursivo ñ αβ. '*8,'italic',10,[.7,.1,.2],'serif'),run('Final monoespaciado. '*4,'bold-italic',14,[.1,.5,.2],'mono')]


def test_inspection_extracts_formats_and_sizes_without_flattening_text():
    inspected=inspect_flow(mixed_source(),[],regions());assert inspected['mixed_supported'],inspected
    runs=inspected['runs'];assert text(runs)==inspected['text']=='Texto destacado cursivo'
    assert [r['style'] for r in runs]==['regular','bold','italic']
    assert [r['size'] for r in runs]==[12,18,10] and runs[-1]['family']=='serif'
    assert runs[1]['color']==pytest.approx([.2,.4,.6],abs=1/255) and inspected['source_fonts'] and 'sustituyen' in inspected['font_notice']

@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_flow_retains_mixed_fonts_sizes_colors_all_text_and_unaffected_pages(rotation,crop,tmp_path):
    base=mixed_source(rotation,crop);runs=plans();out,report=flow_text(base,[],regions(),text(runs),runs=runs)
    assert report['mode']=='mixed' and report['text_verified'] and report['characters']==len(text(runs)) and report['mixed']['fragments']==4 and not report['adjusted']
    with f.open(stream=base) as before,f.open(stream=out) as after:
        assert before[2].get_pixmap().samples==after[2].get_pixmap().samples
        for p,q in zip(before,after):assert p.rotation==q.rotation and p.cropbox==q.cropbox
        spans=[]
        for row in regions():
            p=after[row['page']];p.set_rotation(0);rect=f.Rect(row['box'][0],row['box'][1],row['box'][0]+row['box'][2],row['box'][1]+row['box'][3])
            for block in p.get_text('dict',clip=rect)['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:assert rect.contains(f.Rect(span['bbox']));spans.append(span)
        assert any(s['flags']&16 and s['size']==pytest.approx(18) and s['color']==0x336699 for s in spans)
        assert any(s['flags']&2 and s['size']==pytest.approx(10) for s in spans)
        assert any('Mono' in s['font'] and s['flags']&16 and s['flags']&2 for s in spans)
        assert 'Pie original conservado' in after[0].get_text() and 'Pie destino conservado' in after[1].get_text()
        assert not any('destacado' in s['text'] for s in spans)
    if shutil.which('pdftotext'):
        path=tmp_path/'mixed.pdf';path.write_bytes(out);actual=subprocess.check_output(['pdftotext','-raw',str(path),'-']).decode()
        assert 'IMPORTANTE' in actual and 'Final' in actual

@pytest.mark.parametrize('align',[0,1,2,3])
def test_words_cross_style_boundaries_and_color_changes_keep_reading_order(align):
    runs=[run('super','bold',18,[1,0,0]),run('califragilistico ',size=11),run('αβγ ñ '*70,'italic',12,[0,0,1])]
    out,r=flow_text(source(),[],regions(),text(runs),runs=runs,align=align)
    assert r['text_verified'] and r['complete']


def test_proportional_fit_preserves_size_ratios_and_minimum():
    runs=[run('GRANDE '*20,'bold',24,[.2,.4,.6]),run('pequeño '*20,'italic',12)]
    with pytest.raises(DocumentError,match='no cabe'):flow_text(source(),[],regions()[:1],text(runs),runs=runs)
    out,r=flow_text(source(),[],regions()[:1],text(runs),runs=runs,auto_fit=True,min_size=6)
    assert r['adjusted'] and r['mixed']['min_size']>=6 and r['mixed']['max_size']/r['mixed']['min_size']==pytest.approx(2)
    with pytest.raises(DocumentError):flow_text(source(),[],regions()[:1],text(runs),runs=runs,auto_fit=True,min_size=12)

@pytest.mark.parametrize('patch',[
 [],[run('otro')],[run('Nuevo')|{'size':True}],[run('Nuevo')|{'size':73}],
 [run('Nuevo')|{'family':[]}],[run('Nuevo')|{'style':'unknown'}],[run('Nuevo')|{'color':[2,0,0]}],
 [run('Nuevo')|{'extra':True}],[run('')],[run('Nuevo')]*201,
])
def test_invalid_run_models_fail_before_source_is_changed(patch):
    base=source()
    with pytest.raises(DocumentError):flow_text(base,[],regions(),'Nuevo',runs=patch)
    assert inspect_flow(base,[],regions())['text']=='Texto original'

@pytest.mark.parametrize('bad',['漢字','مرحبا','a\tb','a\x00b','a\x7fb'])
def test_unsupported_characters_cannot_bypass_run_validation(bad):
    with pytest.raises(DocumentError):validate_runs([run(bad)],bad)


def test_multiple_sources_line_breaks_and_blank_lines_keep_run_alignment():
    rows=regions();rows[1]['box']=[20,395,340,65];rows[1]['replace']=True
    data=inspect_flow(mixed_source(),[],rows);assert data['mixed_supported'] and text(data['runs'])==data['text']
    runs=[run('\n'*6),run('Texto después de blancos. ','bold',16,[0,0,1]),run('W'*150,'italic',9)]
    out,r=flow_text(source(),[],regions(),text(runs),runs=runs);assert r['text_verified'] and r['complete']


def test_api_preview_is_atomic_and_apply_returns_editable_native_text():
    base=mixed_source();runs=plans();payload={'operations':[],'regions':regions(),'text':text(runs),'runs':runs}
    with TestClient(app) as c:
        d=c.post('/api/documents',files={'file':('mixto.pdf',base,'application/pdf')}).json();url='/api/documents/'+d['id']
        info=c.post(url+'/inspect-flow',json={'regions':regions()}).json();assert info['mixed_supported'] and len(info['runs'])==3
        preview=c.post(url+'/flow-text',json=payload|{'preview':True});assert preview.status_code==200,preview.text
        assert preview.json()['report']['mode']=='mixed' and len(preview.json()['previews'])==2
        assert c.post(url+'/export',json={'operations':[]}).content==base
        response=c.post(url+'/flow-text',json=payload);assert response.status_code==200,response.text
        result=c.post('/api/documents/'+response.json()['id']+'/export',json={'operations':[]}).content
        with f.open(stream=result) as doc:assert not any(p.get_images() or p.get_xobjects() for p in doc)
        before=set(app.state.root.glob('*.pdf'));bad=c.post(url+'/flow-text',json=payload|{'regions':regions()[:1]})
        assert bad.status_code==422 and set(app.state.root.glob('*.pdf'))==before


def test_reinspecting_bundled_mono_font_does_not_misclassify_its_native_flags():
    runs=[run('Monoespaciada negrita cursiva','bold-italic',14,[.1,.5,.2],'mono')]
    out,_=flow_text(source(),[],regions(),text(runs),runs=runs)
    inspected=inspect_flow(out,[],regions());assert inspected['mixed_supported']
    assert all(r['family']=='mono' and r['style']=='bold-italic' for r in inspected['runs'])


def test_post_render_verification_rejects_a_missing_fragment(monkeypatch):
    from backend import mixed_flow
    monkeypatch.setattr(mixed_flow,'draw_mixed',lambda doc,draws:None)
    base=mixed_source();runs=plans()
    with pytest.raises(DocumentError,match='comprobación de texto'):flow_text(base,[],regions(),text(runs),runs=runs)
    assert inspect_flow(base,[],regions())['text']=='Texto destacado cursivo'


def test_too_small_original_type_reports_mixed_unsupported_without_breaking_plain_inspection():
    with f.open(stream=source()) as d:
        p=d[0];p.insert_text((40,115),'Texto diminuto',fontsize=5);base=d.tobytes()
    result=inspect_flow(base,[],regions());assert 'Texto diminuto' in result['text'] and not result['mixed_supported'] and not result['runs'] and '6 y 72' in result['mixed_reason']
