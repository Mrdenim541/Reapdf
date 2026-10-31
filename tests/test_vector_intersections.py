import pytest
import pymupdf as f
from backend.vector_intersections import line_cubic
from backend.measurement_geometry import targets


def test_cubic_crosses_horizontal_line_twice_and_tangent_once():
 c=[[0,0],[0,100],[100,100],[100,0]]
 hits=line_cubic([[-10,50],[110,50]],c);assert len(hits)==2 and all(abs(p[1]-50)<1e-6 for p in hits)
 hit=line_cubic([[-10,75],[110,75]],c);assert len(hit)==1 and hit[0]==pytest.approx([50,75],abs=1e-6)
 assert not line_cubic([[-10,76],[110,76]],c)


def test_three_roots_finite_segment_and_collinear_overlap():
 # y=(t-.2)(t-.5)(t-.8), converted to Bernstein controls.
 c=[[0,-.08],[1/3,.14],[2/3,-.14],[1,.08]]
 hits=line_cubic([[-1,0],[2,0]],c);assert [p[0] for p in hits]==pytest.approx([.2,.5,.8],abs=1e-6)
 assert len(line_cubic([[.3,0],[.7,0]],c))==1
 assert not line_cubic([[2,0],[3,0]],c)
 assert not line_cubic([[0,0],[2,0]],[[0,0],[.5,0],[1,0],[2,0]])
 assert not line_cubic([[0,0],[0,0]],c)


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_original_curve_line_intersections_are_available_as_rotated_snap_targets(rotation):
 with f.open() as d:
  p=d.new_page(width=500,height=650);p.draw_bezier((40,150),(40,50),(180,50),(180,150));p.draw_line((10,100),(220,100));p.set_rotation(rotation);base=d.tobytes();matrix=p.rotation_matrix
 result=targets(base,[],0);hits=[r for r in result['points'] if r['source']=='curve_intersection'];assert len(hits)==2
 for row in hits:
  native=f.Point(row['point'])*~matrix;assert native.y==pytest.approx(100,abs=1e-5) and 40<native.x<180
 assert result['curve_line_comparisons']>0
