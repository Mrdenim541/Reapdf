import math
import pymupdf as f
import pytest
from backend.measurement_paths import model,flatten,path_points
from backend.measurements import measure,model as saved,calculate
from backend.engine import DocumentError

CAL={'points':[[20,20],[120,20]],'distance':1,'unit':'m'}


def sample(rotation=0,crop=False):
 with f.open() as d:
  p=d.new_page(width=500,height=650);p.insert_text((20,30),'ORIGINAL PLAN')
  p.draw_bezier((40,150),(60,50),(160,50),(180,150));p.draw_circle((300,300),60);p.draw_rect(f.Rect(50,350,150,430))
  if crop:p.set_cropbox(f.Rect(10,10,490,640))
  p.set_rotation(rotation);d.new_page().insert_text((20,40),'Other page');return d.tobytes()


def simpson_speed(c,steps=20000):
 def speed(t):
  x=3*(1-t)**2*(c[1][0]-c[0][0])+6*(1-t)*t*(c[2][0]-c[1][0])+3*t*t*(c[3][0]-c[2][0])
  y=3*(1-t)**2*(c[1][1]-c[0][1])+6*(1-t)*t*(c[2][1]-c[1][1])+3*t*t*(c[3][1]-c[2][1])
  return math.hypot(x,y)
 return (speed(0)+speed(1)+sum((4 if i%2 else 2)*speed(i/steps) for i in range(1,steps)))/(3*steps)


@pytest.mark.parametrize('curve',[
 [(0,0),(0,100),(100,100),(100,0)],[(0,0),(200,0),(-100,0),(100,0)],
 [(0,0),(100,100),(-100,100),(0,0)],[(10,10),(10,10),(20,20),(20,20)],
])
def test_curve_length_and_finite_chord_bounds_against_independent_quadrature(curve):
 pts,bounds=flatten([curve]);length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]));exact=simpson_speed(curve)
 assert bounds['length_lower_pt']<=exact+1e-6<=bounds['length_upper_pt']+1e-6
 assert abs(exact-length)<=bounds['length_error_pt'] and len(pts)<=200
 assert bounds['max_deviation_pt']<=1.000002


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
@pytest.mark.parametrize('kind',['perimeter','area'])
def test_trace_preview_save_reopen_preserves_plan_and_other_page(rotation,crop,kind):
 base=sample(rotation,crop);paths=model(base,[],0)['paths'];assert len(paths)==3
 path=next(p for p in paths if p['curved'] and p['closed']);pts=path_points(path,kind)
 preview=measure(base,[],0,kind,pts,CAL,preview=True,trace=path['id'])
 assert preview['approximation']['error_bound']>0 and 'aproximada' in preview['label']
 out=measure(base,[],0,kind,pts,CAL,trace=path['id']);rows=saved(out,[],0)['measurements'];assert len(rows)==1
 assert rows[0]['trace_source_verified'] and not rows[0]['trace_source_changed']
 assert rows[0]['value']==pytest.approx(preview['value'],rel=1e-6)
 with f.open(stream=base) as a,f.open(stream=out) as b:
  assert a[0].get_pixmap(annots=False).samples==b[0].get_pixmap(annots=False).samples
  assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
  p=b[0]
  for annot in list(p.annots() or []):p.delete_annot(annot)
  assert a[0].get_text()==p.get_text()


def test_closed_perimeter_and_manual_reedit_keep_geometry_and_label_together():
 base=sample();path=next(p for p in model(base,[],0)['paths'] if p['closed'] and not p['curved'])
 out=measure(base,[],0,'perimeter',path['points'],CAL,trace=path['id']);row=saved(out,[],0)['measurements'][0]
 assert row['value']==pytest.approx(3.6)
 pts=[list(p) for p in row['points']];pts[1][0]+=10
 changed=measure(out,[],0,'perimeter',pts,None,identity=row['id'])
 row2=saved(changed,[],0)['measurements'][0];assert row2['id']==row['id'] and row2['approximation'] is None
 assert row2['value']!=row['value']


def test_stale_trace_and_modified_vertices_refuse_before_publishing():
 base=sample();path=model(base,[],0)['paths'][0]
 with pytest.raises(DocumentError,match='cambió'):measure(base,[],0,'perimeter',path['points'],CAL,trace='0'*64)
 pts=[list(p) for p in path['points']];pts[0][0]+=1
 with pytest.raises(DocumentError,match='coinciden'):measure(base,[],0,'perimeter',pts,CAL,trace=path['id'])
 with pytest.raises(DocumentError,match='cerrado'):path_points(path,'area')


def test_huge_curve_and_clipped_or_layer_geometry_are_not_claimed_complete():
 with f.open() as d:
  p=d.new_page(width=500,height=650);p.draw_bezier((10,10),(300000,300000),(-300000,100000),(100,100));base=d.tobytes()
 assert not model(base,[],0)['paths']
 with f.open(stream=sample()) as d:d.add_ocg('Hidden alternative');base=d.tobytes()
 assert not model(base,[],0)['paths']


@pytest.mark.parametrize('rotation',[90,180,270])
def test_saved_trace_keeps_verified_source_after_page_rotation(rotation):
 base=sample();path=next(p for p in model(base,[],0)['paths'] if p['closed'] and p['curved'])
 out=measure(base,[],0,'perimeter',path['points'],CAL,trace=path['id'])
 with f.open(stream=out) as d:d[0].set_rotation(rotation);rotated=d.tobytes()
 row=saved(rotated,[],0)['measurements'][0];assert row['trace_source_verified'] and row['value']>0


def test_partial_clip_is_omitted_but_contained_rectangular_clip_is_supported():
 with f.open(stream=sample()) as d:
  p=d[0];data=p.read_contents();x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'q 0 450 200 200 re W n '+data+b' Q');p.set_contents(x);clipped=d.tobytes()
 result=model(clipped,[],0);assert len(result['paths'])==1 and not result['paths'][0]['closed'] and result['skipped_paths']


def test_curve_uncertainty_cannot_cross_regional_scale_boundary():
 from backend.measurement_geometry import configure_profile
 cal={'points':[[250,250],[350,250]],'distance':1,'unit':'m'}
 base=configure_profile(sample(),[],0,'Circle region',[240,240,120,120],cal)
 profile=saved(base,[],0)['scales'][0]['id'];path=next(p for p in model(base,[],0)['paths'] if p['closed'] and p['curved'])
 with pytest.raises(DocumentError,match='límite|escala regional'):measure(base,[],0,'perimeter',path['points'],None,profile=profile,trace=path['id'])
