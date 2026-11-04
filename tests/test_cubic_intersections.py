import math,pytest,pymupdf as f
from backend.vector_intersections import cubic_cubic
from backend.measurement_geometry import targets


def cubic(xs,ys):return [list(p) for p in zip(xs,ys)]
def line(a,b):return [[a[0]+(b[0]-a[0])*i/3,a[1]+(b[1]-a[1])*i/3] for i in range(4)]
def hits(a,b):
    r=cubic_cubic(a,b);assert not r['limited'],r
    return sorted(r['points'])


@pytest.mark.parametrize('reverse',[False,True])
def test_two_cubics_cross_twice_without_using_polyline(reverse):
    a=[[0,0],[0,100],[100,100],[100,0]];b=line([-10,50],[110,50])
    if reverse:b.reverse()
    points=hits(a,b);assert len(points)==2
    assert [p[1] for p in points]==pytest.approx([50,50],abs=2e-6)
    assert [p[0] for p in points]==pytest.approx([11.509982054,88.490017946],abs=2e-6)


def test_tangency_endpoint_near_miss_and_nonisolated():
    a=[[0,0],[0,100],[100,100],[100,0]]
    points=hits(a,line([-10,75],[110,75]));assert len(points)==1 and points[0]==pytest.approx([50,75],abs=3e-6)
    assert not hits(a,line([-10,75.0001],[110,75.0001]))
    p=hits(a,line([-10,0],[110,0]));assert len(p)==2 and p[0]==pytest.approx([0,0],abs=3e-6) and p[1]==pytest.approx([100,0],abs=3e-6)
    for other in [a,list(reversed(a))]:assert cubic_cubic(a,other)['limited'] and not cubic_cubic(a,other)['points']
    assert cubic_cubic(line([0,0],[100,0]),line([20,0],[80,0]))['reason']=='collinear'


def test_three_crossings_with_cubic_representation_of_line():
    a=[[0,-.08],[1/3,.14],[2/3,-.14],[1,.08]]
    points=hits(a,line([-1,0],[2,0]));assert len(points)==3
    assert [p[0] for p in points]==pytest.approx([.2,.5,.8],abs=2e-6)


def test_two_genuinely_curved_parabolas_have_two_crossings():
    # y=x² and y=1-x² on -1<=x<=1, degree-elevated to cubics.
    a=cubic([-1,-1/3,1/3,1],[1,-1/3,-1/3,1]);b=cubic([-1,-1/3,1/3,1],[0,4/3,4/3,0])
    points=hits(a,b);assert len(points)==2
    assert [p[0] for p in points]==pytest.approx([-math.sqrt(.5),math.sqrt(.5)],abs=2e-6)
    assert [p[1] for p in points]==pytest.approx([.5,.5],abs=2e-6)


def test_tangent_curved_parabolas_do_not_create_cluster():
    a=cubic([-1,-1/3,1/3,1],[1,-1/3,-1/3,1]);b=cubic([-1,-1/3,1/3,1],[2,-2/3,-2/3,2])
    p=hits(a,b);assert len(p)==1 and p[0]==pytest.approx([0,0],abs=3e-6)


def test_budget_exhaustion_is_explicit_and_discards_partial_pair():
    a=[[0,0],[0,100],[100,100],[100,0]];b=line([-10,50],[110,50]);budget=[100000]
    r=cubic_cubic(a,b,budget);assert r['limited'] and r['reason']=='budget' and not r['points']


def pdf(rotation=0,clipped=False,coincident=False):
    with f.open() as d:
        p=d.new_page(width=300,height=300);s=p.new_shape();s.draw_bezier((40,180),(40,40),(220,40),(220,180));s.finish(color=(0,0,0));s.commit()
        s=p.new_shape();s.draw_bezier((40,60),(40,200),(220,200),(220,60));s.finish(color=(0,0,0));s.commit()
        if coincident:
            s=p.new_shape();s.draw_bezier((40,180),(40,40),(220,40),(220,180));s.finish(color=(0,0,0));s.commit()
        if clipped:
            x=p.get_contents()[-1];d.update_stream(x,b'q 0 0 20 20 re W n '+d.xref_stream(x)+b' Q')
        p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_page_targets_return_curve_crossings_in_display_coordinates(rotation):
    base=pdf(rotation);r=targets(base,[],0);assert r['curve_curve_intersections']==2 and not r['limited']
    with f.open(stream=base) as d:
        p=d[0];rotate=p.rotation_matrix
        expected=[[q[0]*rotate.a+q[1]*rotate.c+rotate.e,q[0]*rotate.b+q[1]*rotate.d+rotate.f] for q in hits([[40,180],[40,40],[220,40],[220,180]],[[40,60],[40,200],[220,200],[220,60]])]
    actual=[row['point'] for row in r['points'] if row['source']=='curve_curve_intersection']
    assert all(any(math.dist(q,point)<.000002 for point in actual) for q in expected)


def test_clipped_and_coincident_pairs_are_disclosed():
    clipped=targets(pdf(clipped=True),[],0);assert clipped['limited'] and clipped['curve_curve_intersections']==0
    duplicate=targets(pdf(coincident=True),[],0);assert duplicate['limited'] and duplicate['curve_curve_omitted_pairs']>=1


@pytest.mark.parametrize('scale,offset',[(.1,(40,70)),(50,(300,-100)),(1000,(-300,500))])
def test_crossings_are_invariant_under_affine_map(scale,offset):
    a=[[-1,1],[-1/3,-1/3],[1/3,-1/3],[1,1]];b=[[-1,0],[-1/3,4/3],[1/3,4/3],[1,0]]
    def transform(p):return [offset[0]+scale*(p[0]+.3*p[1]),offset[1]+scale*(.2*p[0]+p[1])]
    actual=hits([transform(p) for p in a],[transform(p) for p in b]);expected=sorted(transform(p) for p in hits(a,b))
    assert len(actual)==len(expected)==2
    for p,q in zip(actual,expected):assert p==pytest.approx(q,abs=5e-6)


def test_shared_endpoint_is_not_duplicated_and_disjoint_hulls_are_fast():
    a=[[0,0],[0,100],[100,100],[100,0]];b=[[100,0],[100,-100],[200,-100],[200,0]]
    r=hits(a,b);assert len(r)==1 and r[0]==pytest.approx([100,0],abs=3e-6)
    budget=[0];r=cubic_cubic(a,[[x+1000,y] for x,y in b],budget);assert not r['points'] and not r['limited'] and budget[0]==1


def test_different_parameterization_of_same_curved_path_is_bounded():
    from backend.vector_intersections import _split
    a=[[0,0],[0,100],[100,100],[100,0]];b=_split(tuple(tuple(p) for p in a))[0]
    r=cubic_cubic(a,b);assert r['limited'] and not r['points']
