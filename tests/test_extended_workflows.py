"""Extended user journeys: angles/snaps, label/empty-cell tags, affine paragraphs, OCG profiles."""
import math,re
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.measurements import measure,model as measurement_model
from backend.measurement_geometry import targets
from backend.basic_tagging import candidates,create
from backend.affine_reflow import reflow
from backend.original_reflow import inspect
from backend.layers import model as layer_model,apply as layers_apply


def blank(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=600,height=700)
        if crop:p.set_cropbox(f.Rect(20,30,580,680))
        p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('unit,factor',[('deg',180/math.pi),('rad',1)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_angles_without_scale_roundtrip_edit_and_delete(unit,factor,rotation,crop):
    base=blank(rotation,crop);pts=[[100,150],[100,100],[150,100]];out=measure(base,[],0,'angle',pts,None,unit)
    row=measurement_model(out,[],0)['measurements'][0];assert row['value']==pytest.approx(math.pi/2*factor) and row['points']==pts and row['editable']
    edited=measure(out,[],0,'angle',[[150,150],[100,100],[150,100]],None,unit,identity=row['id']);row2=measurement_model(edited,[],0)['measurements'][0]
    assert row2['id']==row['id'] and row2['value']==pytest.approx(math.pi/4*factor)
    with f.open(stream=edited) as d:
        assert len(list(d[0].annots()))==2 and d[0].rotation==rotation
        a=next(a for a in d[0].annots() if a.type[0]==f.PDF_ANNOT_POLY_LINE);assert d.xref_get_key(a.xref,'Measure')[0]=='null'
    from backend.measurements import delete_measure
    assert not measurement_model(delete_measure(edited,[],0,row['id']),[],0)['measurements']


@pytest.mark.parametrize('pts',[[[100,100],[100,100],[150,100]],[[100,100],[100.1,100],[150,100]],[[100,100],[150,100]],[[100,100],[150,100],[float('nan'),100]]])
def test_invalid_angles_rejected(pts):
    with pytest.raises(DocumentError):measure(blank(),[],0,'angle',pts,None,'deg')


def test_snap_intersection_inside_segments_and_excludes_extensions():
    with f.open() as d:
        p=d.new_page(width=400,height=400);p.draw_line((50,50),(250,250));p.draw_line((50,250),(250,50));p.draw_line((300,50),(300,100));base=d.tobytes()
    result=targets(base,[],0);assert {'point':[150,150],'source':'intersection'} in result['points']
    assert not any(r['point']==[300,300] for r in result['points']) and not result['limited']


def semantic_source():
    with f.open() as d:
        p=d.new_page();p.insert_text((40,60),'1.');p.insert_text((65,60),'First item');p.insert_text((40,85),'2.');p.insert_text((65,85),'Second item')
        for point,text in [((40,150),'HEAD A'),((200,150),'HEAD B'),((40,180),'DATA')]:p.insert_text(point,text)
        return d.tobytes()


def tagging_review():
    base=semantic_source();items=candidates(base,[])['entries'];roles=['Lbl','LI','Lbl','LI','TH','TH','TD'];entries=[]
    for i,(item,role) in enumerate(zip(items,roles)):
        cfg={'id':item['id'],'role':role}
        if i>=4:cfg.update(table=1,row=1 if i<6 else 2,column=2 if i==5 else 1)
        entries.append(cfg)
    return base,entries


def test_separate_labels_and_empty_table_cell_native_structure_and_pixels():
    base,entries=tagging_review();out,report=create(base,[],entries,reviewed=True,empty_cells=[{'page':0,'table':1,'row':2,'column':2}]);assert report['list_labels']==2 and report['empty_cells']==1 and report['table_cells']==4
    with f.open(stream=base) as a,f.open(stream=out) as d:
        assert a[0].get_text()==d[0].get_text() and a[0].get_pixmap().samples==d[0].get_pixmap().samples
        roles={x:d.xref_get_key(x,'S')[1] for x in range(1,d.xref_length())};labels=[x for x,r in roles.items() if r=='/Lbl'];assert len(labels)==2
        for x in labels:
            parent=int(d.xref_get_key(x,'P')[1].split()[0]);assert roles[parent]=='/LI';assert d.xref_get_key(parent,'K')[1].startswith('['+str(x)+' 0 R')
        empty=[x for x,r in roles.items() if r=='/TD' and d.xref_get_key(x,'K')==('array','[]')];assert len(empty)==1
        from backend.structure_partition import partition
        partition(d,[d[0].xref]);saved=d.tobytes()
    with f.open(stream=saved) as d:assert sum(d.xref_get_key(x,'S')==('name','/TD') and d.xref_get_key(x,'K')==('array','[]') for x in range(1,d.xref_length()))==1


@pytest.mark.parametrize('empty',[[{'page':0,'table':1,'row':1,'column':1}],[{'page':0,'table':9,'row':2,'column':2}],[{'page':0,'table':[],'row':2,'column':2}],[{'page':0,'table':1,'row':2,'column':2}]*2])
def test_semantic_invalid_empty_cells_rejected(empty):
    base,entries=tagging_review()
    with pytest.raises(DocumentError):create(base,[],entries,reviewed=True,empty_cells=empty)


def test_orphan_list_label_is_rejected():
    base,entries=tagging_review();entries[1]['role']='P'
    with pytest.raises(DocumentError,match='Lbl'):create(base,[],entries,reviewed=True)


def affine_paragraph():
    with f.open() as d:
        p=d.new_page();p.insert_text((130,200),'ALPHA BETA\nGAMMA DELTA',fontsize=14,morph=(f.Point(130,200),f.Matrix(20)))
        p.insert_text((40,500),'UNCHANGED');return d.tobytes()


def test_multi_group_affine_paragraph_inspect_edit_reopen_without_residual_text():
    base=affine_paragraph()
    with f.open(stream=base) as d:
        span=next(s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']=='ALPHA BETA');info=inspect(base,[],0,list(span['origin']),span['text'])
    assert info['affine'] and len(info['ids'])==2
    out,report=reflow(base,[],0,info['box'],info['ids'][0],'BETA ALPHA\nDELTA GAMMA',140,100,identifiers=info['ids']);assert report['source_groups']==2
    with f.open(stream=out) as d:
        text=d[0].get_text();assert 'BETA ALPHA' in text and 'DELTA GAMMA' in text and 'ALPHA BETA' not in text and 'GAMMA DELTA' not in text and 'UNCHANGED' in text


def layered():
    with f.open() as d:
        p=d.new_page();a=d.add_ocg('A');b=d.add_ocg('B');p.insert_text((50,70),'ONLY A',oc=a);p.insert_text((50,110),'ONLY B',oc=b);d.add_layer('Solo B',on=[b]);return d.tobytes(),a,b


def test_layer_alternate_configuration_selected_default_and_original_preserved():
    base,a,b=layered();info=layer_model(base,[]);assert info['configurations'][0]['name']=='Solo B' and info['configurations'][0]['visible']==[b]
    out=layers_apply(base,[],[b],0);info=layer_model(out,[]);assert [r['name'] for r in info['layers'] if r['visible']]==['B']
    with f.open(stream=base) as d,f.open(stream=out) as e:
        assert 'ONLY B' in e[0].get_text() and 'ONLY A' not in e[0].get_text() and d[0].read_contents()==e[0].read_contents()
        pix=e[0].get_pixmap().samples
        cfg=info['configurations'][0];restored=layers_apply(out,[],cfg['visible'],0)
    with f.open(stream=restored) as d:assert d[0].get_pixmap().samples==pix


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_migrate_legacy_measurement_requires_new_reference_and_preserves_identity(rotation):
    import json
    from backend.form_structure import pdf_string
    cal={'points':[[40,50],[140,50]],'distance':1,'unit':'m'}
    out=measure(blank(rotation),[],0,'distance',[[70,100],[170,100]],cal)
    record=measurement_model(out,[],0)['measurements'][0];identity=record['id']
    with f.open(stream=out) as d:
        a=next(a for a in d[0].annots() if d.xref_get_key(a.xref,'ReapdfMeasurement')[0]=='string')
        stored=json.loads(d.xref_get_key(a.xref,'ReapdfMeasurement')[1]);stored.update(version=1,points=record['points'],calibration=cal)
        d.xref_set_key(a.xref,'ReapdfMeasurement',pdf_string(json.dumps(stored)));legacy=d.tobytes()
    row=measurement_model(legacy,[],0)['measurements'][0];assert row['legacy']
    newer={**cal,'distance':2}
    with pytest.raises(DocumentError):measure(legacy,[],0,'distance',row['points'],newer,identity=identity)
    updated=measure(legacy,[],0,'distance',row['points'],newer,identity=identity,migrate=True)
    row=measurement_model(updated,[],0)['measurements'][0];assert not row['legacy'] and row['editable'] and row['id']==identity and row['value']==pytest.approx(2)


@pytest.mark.parametrize('operator',['Td','TD'])
def test_affine_reflow_restores_line_matrix_for_following_unselected_relative_line(operator):
    from backend.native_text import native_model
    with f.open() as d:
        p=d.new_page();p.insert_text((130,200),'ALPHA BETA\nGAMMA DELTA',fontsize=14,morph=(f.Point(130,200),f.Matrix(20)))
        x=p.get_contents()[0];d.update_stream(x,d.xref_stream(x).replace(b'0 -19.236 TD',b'0 -100 '+operator.encode()));base=d.tobytes()
        _,rows=native_model(d,0,p.rect);first,second=rows;assert first['editable'] and second['editable'];r=f.Rect(first['bbox']);box=[r.x0,r.y0,r.width,r.height]
    out,_=reflow(base,[],0,box,first['id'],'BETA ALPHA\nALPHA',120,100)
    with f.open(stream=out) as d:
        _,rows=native_model(d,0,d[0].rect);untouched=next(r for r in rows if r['text']=='GAMMA DELTA');assert untouched['origin']==pytest.approx(second['origin'],abs=.01) and untouched['editable']


def test_original_edit_inside_relative_line_object_remains_verifiable():
    from backend.native_text import native_model
    from backend.styled_text import replace_styled
    base=affine_paragraph()
    with f.open(stream=base) as d:
        _,rows=native_model(d,0,d[0].rect);row=rows[0];r=f.Rect(row['bbox']);box=[r.x0,r.y0,r.width,r.height]
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'BETA ALPHA'}])
    with f.open(stream=out) as d:assert 'BETA ALPHA' in d[0].get_text() and 'GAMMA DELTA' in d[0].get_text()


def test_explicit_empty_cells_and_labels_survive_project_roundtrip_and_real_split():
    from backend.projects import build_project,read_project
    base,entries=tagging_review();out,report=create(base,[],entries,reviewed=True,empty_cells=[{'page':0,'table':1,'row':2,'column':2}])
    project,_=build_project(out,[],{'name':'Semantic.pdf'});restored,_,_=read_project(project)
    # Reopen bytes independently before pruning structure to a retained page.
    with f.open(stream=restored) as d:
        from backend.structure_partition import partition
        partition(d,[d[0].xref]);copy=d.tobytes(garbage=4)
    with f.open(stream=copy) as d:
        n=f.mupdf;root=n.pdf_dict_getp(n.pdf_trailer(f._as_pdf_document(d)),'Root/StructTreeRoot');tree=n.pdf_dict_gets(root,'ParentTree');nums=n.pdf_dict_gets(tree,'Nums');array=n.pdf_array_get(nums,1)
        assert n.pdf_array_len(array)==7
        assert sum(d.xref_get_key(x,'S')==('name','/Lbl') for x in range(1,d.xref_length()))==2


def test_nondefault_layer_configuration_locked_and_unknown_rules_protected():
    base,a,b=layered()
    with f.open(stream=base) as d:
        d.xref_set_key(d.pdf_catalog(),'OCProperties/Configs',f'[<< /Name (Locked B) /BaseState /OFF /ON [{b} 0 R] /Locked [{b} 0 R] >> << /Name (Automatic) /AS [] /ON [{a} 0 R] >>]');base=d.tobytes()
    info=layer_model(base,[]);assert info['configurations'][0]['locked']==[b] and not info['configurations'][1]['supported']
    with pytest.raises(DocumentError,match='bloqueada'):layers_apply(base,[],[],0)
    with pytest.raises(DocumentError):layers_apply(base,[],[a],1)
