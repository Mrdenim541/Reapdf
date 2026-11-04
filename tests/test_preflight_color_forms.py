import pytest,pymupdf as f
from backend.preflight import inspect


def sample(mode='spot',cycle=False):
    with f.open() as d:
        p=d.new_page();p.insert_text((30,40),'PLAN');res=int(d.xref_get_key(p.xref,'Resources')[1].split()[0]);fn=d.get_new_xref();d.update_object(fn,'<< /FunctionType 2 /Domain[0 1] /C0[0 0 0 0] /C1[0 1 0 0] /N 1 >>')
        child=d.get_new_xref();d.update_object(child,f'<< /Type/XObject /Subtype/Form /BBox[0 0 300 300] /Resources << /ColorSpace << /Spot [/Separation /BrandRed /DeviceCMYK {fn} 0 R] >> /ExtGState << /Ink << /OP true /op true /OPM 1 >> >> >> >>')
        content=b'/Spot cs .7 scn /Ink gs 40 40 100 100 re f' if mode=='spot' else b'.8 0 0 rg 40 40 100 100 re f'
        if cycle:d.xref_set_key(child,'Resources/XObject',f'<< /Self {child} 0 R >>');content+=b' /Self Do'
        d.update_stream(child,content);d.xref_set_key(res,'XObject',f'<< /Child {child} 0 R >>');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'q /Child Do Q');d.xref_set_key(p.xref,'Contents','['+' '.join(f'{v} 0 R' for v in p.get_contents()+[x])+']');return d.tobytes()


def test_separation_and_applied_overprint_inside_form_are_reported():
    r=inspect(sample(),[]);c=r['pages'][0]['color_analysis'];assert c['spot_colorants']==['BrandRed'] and len(c['overprint_states'])==1 and not c['limited']
    assert {'spot_colorants','overprint'}<={v['code'] for v in r['issues']} and 'Separation' in r['pages'][0]['vector_colors']


def test_form_rgb_no_longer_returns_unanalyzed_placeholder():
    r=inspect(sample('rgb'),[]);assert 'RGB' in r['pages'][0]['vector_colors'] and not any(i['code']=='form_colors' for i in r['issues'])


def test_recursive_form_returns_explicit_partial_diagnostic():
    r=inspect(sample(cycle=True),[]);assert r['pages'][0]['color_analysis']['limited'] and any(v['code']=='color_analysis_incomplete' for v in r['issues'])
