from copy import deepcopy
import pymupdf as f
import pytest
from backend.original_reflow import inspect
from backend.affine_reflow import reflow
from backend.engine import DocumentError


def source(matrix=(1,.25,.15,1),rotation=0,form=False,first_size=18,last_size=14):
    with f.open() as d:
        p=d.new_page(width=650,height=800);p.insert_font(fontname='hebo');p.insert_font(fontname='heit');p.insert_text((30,740),'NEIGHBOR UNCHANGED')
        m=f.Matrix(*matrix,300,400);second=f.Point(f.Font('hebo').text_length('HELLO ',fontsize=first_size),0)*m
        content=(f'q BT /hebo {first_size} Tf .8 0 0 rg '+' '.join(map(str,m))+f' Tm (HELLO ) Tj /heit {last_size} Tf 0 0 .8 rg '+' '.join(map(str,[*m[:4],second.x,second.y]))+' Tm (TEXT) Tj ET Q').encode()
        x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,content);d.xref_set_key(p.xref,'Contents','['+' '.join(f'{r} 0 R' for r in p.get_contents()+[x])+']');p.set_rotation(rotation);d.new_page().insert_text((30,40),'OTHER PAGE UNCHANGED');base=d.tobytes()
    if not form:return base
    with f.open(stream=base) as a,f.open() as d:
        a[0].set_rotation(0);p=d.new_page(width=1000,height=1300);p.show_pdf_page(f.Rect(0,0,650,800),a,0);p.show_pdf_page(f.Rect(550,700,875,1100),a,0);d.new_page().show_pdf_page(f.Rect(0,0,650,800),a,0);d[0].set_rotation(rotation);return d.tobytes()


def model(base):
    with f.open(stream=base) as d:
        d[0].set_rotation(0);s=next(s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text'].startswith('HELLO'))
    return inspect(base,[],0,list(s['origin']),s['text'])


def apply(base,value='HELLO HELLO ',tail='TEXT TEXT',width=130,height=150,preview=False):
    m=model(base);runs=[{'id':r['id'],'text':value if i==0 else tail} for i,r in enumerate(m['runs'])]
    return reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),width,height,preview,m['ids'],runs)


@pytest.mark.parametrize('matrix',[(1,.25,.15,1),(0,1,-1,0),(-1,.1,.1,1),(1.4,.3,.2,.7)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
def test_parallel_mixed_reflow_preserves_styles_transform_and_neighbors(matrix,rotation,form):
    base=source(matrix,rotation,form);m=model(base);assert m['affine'] and m['mixed'] and len(m['runs'])==2
    out,report=apply(base);assert report['mixed'] and report['preserves_affine'] and report['lines']>=2
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].rotation==b[0].rotation and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        a[0].set_rotation(0);b[0].set_rotation(0)
        assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')
        normalized=''.join(b[0].get_text().split());assert normalized.count('HELLO')==(3 if form else 2) and normalized.count('TEXT')==(3 if form else 2)
        styles={(s['font'],s['color']) for block in b[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if 'HELLO' in s['text'] or 'TEXT' in s['text']}
        assert styles=={('Helvetica-Bold',0xcc0000),('Helvetica-Oblique',0x0000cc)}
        expected={(s['font'],round(s['size'],3)) for block in a[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if 'HELLO' in s['text'] or 'TEXT' in s['text']}
        actual={(s['font'],round(s['size'],3)) for block in b[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if 'HELLO' in s['text'] or 'TEXT' in s['text']};assert expected==actual


def test_preview_and_overflow_are_atomic():
    base=source();r=apply(base,preview=True);assert r['mixed'] and r['lines']>=2
    with pytest.raises(DocumentError,match='no cabe'):apply(base,'HELLO '*40,'TEXT '*40,30,10)


def test_stale_runs_wrong_order_and_unsupported_glyph_refused():
    base=source();m=model(base);runs=[{'id':r['id'],'text':r['text']} for r in m['runs']]
    for bad in [list(reversed(runs)),[{'id':'stale','text':'HELLO '},runs[1]],[{'id':runs[0]['id'],'text':'漢'},runs[1]]]:
        with pytest.raises(DocumentError):reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in bad),130,150,False,m['ids'],bad)


def test_horizontal_shared_form_also_uses_original_mixed_fonts():
    base=source((1,0,0,1),form=True);m=model(base);assert m['affine'] and m['mixed']
    out,_=apply(base)
    with f.open(stream=base) as a,f.open(stream=out) as b:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples


def test_multi_line_original_object_can_flow_with_mixed_styles():
    with f.open(stream=source()) as d:
        x=d[0].get_contents()[-1];data=d.xref_stream(x);first=data.index(b'BT ')+3;end=data.index(b' ET');line=data[first:end]
        # Duplicate the line within the same BT with explicit baseline shift.
        from backend.pdf_content import operations
        edits=[]
        for op,args,tok in operations(line):
            if op=='Tm':
                edits.append((args[4].start,args[4].end,format(args[4].value-40*args[2].value,'.8f').encode()))
                edits.append((args[5].start,args[5].end,format(args[5].value-40*args[3].value,'.8f').encode()))
        from backend.pdf_content import patch
        d.update_stream(x,data[:end]+b' '+patch(line,edits)+data[end:]);base=d.tobytes()
    m=model(base);assert len(m['runs'])==4
    runs=[{'id':r['id'],'text':r['text']} for r in m['runs']];out,r=reflow(base,[],0,m['box'],m['ids'][0],''.join(v['text'] for v in runs),150,200,False,m['ids'],runs)
    assert r['source_groups']==4
    with f.open(stream=out) as d:assert d[0].get_text().count('HELLO')==2 and d[0].get_text().count('TEXT')==2


def test_partial_object_and_cut_region_are_rejected():
    base=source();m=model(base);runs=[{'id':r['id'],'text':r['text']} for r in m['runs']]
    with pytest.raises(DocumentError):reflow(base,[],0,m['box'],m['ids'][0],runs[0]['text'],130,150,False,m['ids'][:1],runs[:1])
    box=m['box'].copy();box[2]/=2
    with pytest.raises(DocumentError):reflow(base,[],0,box,m['ids'][0],''.join(r['text'] for r in runs),130,150,False,m['ids'],runs)


def test_neighbor_collision_and_page_exit_are_atomic():
    with f.open(stream=source()) as d:
        d[0].draw_rect(f.Rect(290,390,500,470));blocked=d.tobytes()
    with pytest.raises(DocumentError,match='cruza'):apply(blocked)
    with pytest.raises(DocumentError):apply(source(),'HELLO '*100,'TEXT '*100,400,1500)


def test_tagged_document_remains_protected():
    with f.open(stream=source()) as d:d.xref_set_key(d.pdf_catalog(),'StructTreeRoot','<< /Type/StructTreeRoot >>');base=d.tobytes()
    with pytest.raises(DocumentError,match='etiquetado'):apply(base)


def test_api_mixed_affine_preview_and_apply():
    import json
    from fastapi.testclient import TestClient
    from backend.app import app
    base=source();m=model(base);runs=[{'id':r['id'],'text':'HELLO HELLO ' if i==0 else 'TEXT TEXT'} for i,r in enumerate(m['runs'])]
    payload={'page':0,'box':m['box'],'id':m['ids'][0],'ids':m['ids'],'runs':runs,'text':''.join(r['text'] for r in runs),'width':130,'height':150}
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('original.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']+'/reflow-affine'
        reviewed=c.post(url,json={**payload,'preview':True});assert reviewed.status_code==200 and reviewed.json()['mixed']
        result=c.post(url,json=payload);assert result.status_code==200 and result.json()['id']!=doc['id'] and result.json()['reflow_report']['mixed']
        bad=deepcopy(payload);bad['runs'][0]['id']='stale';assert c.post(url,json=bad).status_code==422


def test_paragraph_top_is_preserved_when_first_font_is_smaller():
    from backend.native_text import native_model
    base=source(first_size=14,last_size=18);m=model(base)
    with f.open(stream=base) as d:
        _,rows=native_model(d,0,d[0].rect);first=next(r for r in rows if r['text'].startswith('HELLO'));inverse=~f.Matrix(*first['_geometry']['matrix']);before=max((f.Point(r['origin'])*inverse).y+r['_geometry']['ascent'] for r in rows if r['id'] in m['ids'])
    out,_=apply(base)
    with f.open(stream=out) as d:
        _,rows=native_model(d,0,d[0].rect);after=max((f.Point(r['origin'])*inverse).y+r['_geometry']['ascent'] for r in rows if 'HELLO' in r['text'] or 'TEXT' in r['text'])
    assert after==pytest.approx(before,abs=.02)


@pytest.mark.parametrize('kind',['spacing','different_frame'])
def test_special_spacing_and_nonparallel_styles_remain_protected(kind):
    with f.open(stream=source()) as d:
        x=d[0].get_contents()[-1];content=d.xref_stream(x)
        if kind=='spacing':content=content.replace(b'BT ',b'BT 2 Tc ',1)
        else:
            from backend.pdf_content import operations,patch
            transforms=[args for op,args,_ in operations(content) if op=='Tm'];arg=transforms[1][2];content=patch(content,[(arg.start,arg.end,b'.35')])
        d.update_stream(x,content);base=d.tobytes()
    with pytest.raises(DocumentError):apply(base)


def test_uniform_horizontal_form_keeps_the_existing_paragraph_guard():
    from tests.test_cff_forms_mixed import form_pdf
    base=form_pdf()
    with f.open(stream=base) as d:
        s=next(s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']=='HELLO TEXT')
    with pytest.raises(DocumentError):inspect(base,[],0,list(s['origin']),s['text'])
