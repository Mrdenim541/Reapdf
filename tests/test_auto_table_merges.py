import hashlib
import pymupdf as f
import pytest
from backend.table_regions import extract,docx_bytes
from backend.engine import DocumentError

BOX=[40,80,450,180]


def source(scan=False,rotation=0,irregular=False,gap=False):
    with f.open() as d:
        p=d.new_page(width=540,height=400)
        for x in [40,490]:p.draw_line((x,80),(x,260),width=1)
        for y in [80,260]:p.draw_line((40,y),(490,y),width=1)
        # Header spans columns 1+2; left body cell spans rows 2+3.
        p.draw_line((190,140),(190,260),width=1);p.draw_line((340,80),(340,260),width=1)
        p.draw_line((40,140),(490,140),width=1);p.draw_line((190,200),(490,200),width=1)
        if irregular:
            # Missing another separator produces an L, never a rectangle.
            p.add_redact_annot(f.Rect(189,142,191,199),fill=(1,1,1));p.apply_redactions()
        if gap:
            p.add_redact_annot(f.Rect(339,155,341,185),fill=(1,1,1));p.apply_redactions()
        for point,text in [((70,117),'MERGED HEADER'),((365,117),'RIGHT'),((65,177),'TALL'),((215,177),'BETA'),((365,177),'GAMMA'),((215,237),'DELTA'),((365,237),'EPSILON')]:p.insert_text(point,text,fontsize=14)
        if scan:
            pix=p.get_pixmap(matrix=f.Matrix(2,2),alpha=False)
            with f.open() as out:
                q=out.new_page(width=540,height=400);q.insert_image(q.rect,stream=pix.tobytes('png'));q.set_rotation(rotation);return out.tobytes()
        p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('scan',[False,True])
def test_partial_separators_suggest_true_horizontal_vertical_merges(scan):
    base=source(scan);digest=hashlib.sha256(base).digest();report=extract(base,[],0,BOX,language='eng',detect_merges=True)
    assert report['spans']==[{'row':0,'column':0,'rowspan':1,'colspan':2},{'row':1,'column':0,'rowspan':2,'colspan':1}]
    assert report['cells']==[['MERGED HEADER','','RIGHT'],['TALL','BETA','GAMMA'],['','DELTA','EPSILON']]
    assert hashlib.sha256(base).digest()==digest and not report['source_modified']
    assert docx_bytes(report['cells'],spans=report['spans']).startswith(b'PK')


@pytest.mark.parametrize('scan',[False,True])
@pytest.mark.parametrize('rotation',[90,180,270])
def test_visible_rotations_keep_rectangular_spans_and_all_text(scan,rotation):
    base=source(scan,rotation)
    with f.open(stream=base) as d:r=f.Rect(40,80,490,260)*d[0].rotation_matrix
    report=extract(base,[],0,[r.x0,r.y0,r.width,r.height],language='eng',detect_merges=True)
    assert len(report['spans'])==2
    assert all(value in ' '.join(c for row in report['cells'] for c in row) for value in ['MERGED','HEADER','RIGHT','TALL','BETA','GAMMA','DELTA','EPSILON'])


def test_irregular_component_not_silently_promoted_to_rectangle():
    report=extract(source(irregular=True),[],0,BOX,detect_merges=True)
    assert all(not(s['row']==1 and s['column']==0) for s in report['spans'])
    assert any('no rectangulares' in w for w in report['warnings'])


def test_ambiguous_partial_line_not_used_to_join_cells():
    report=extract(source(gap=True),[],0,BOX,detect_merges=True)
    assert any('ambiguos' in w for w in report['warnings'])
    assert not any(s['column']==1 and s['row']==1 for s in report['spans'])


def test_open_border_prevents_merge_suggestions():
    with f.open(stream=source()) as d:
        d[0].add_redact_annot(f.Rect(39,81,41,259),fill=(1,1,1));d[0].apply_redactions();base=d.tobytes()
    report=extract(base,[],0,BOX,detect_merges=True);assert not report['spans'] and any('exterior' in w for w in report['warnings'])


def test_switch_and_manual_grid_are_honoured():
    grid={'columns':[40,190,340,490],'rows':[80,140,200,260]}
    assert not extract(source(),[],0,BOX,grid=grid)['spans']
    assert len(extract(source(),[],0,BOX,grid=grid,detect_merges=True)['spans'])==2
    with pytest.raises(DocumentError):extract(source(),[],0,BOX,detect_merges='yes')
