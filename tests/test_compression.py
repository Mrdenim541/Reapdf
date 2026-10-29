import hashlib
import subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.compression import compress_images


def source(rotation=0,crop=False,shared=False,alpha=False):
    w,h=1200,1600
    # Uncompressed gradient is a reproducible high-resolution scan-like image.
    pixels=bytes(v for y in range(h) for x in range(w) for v in ((x//5)%256,(y//7)%256,128)) if not alpha else None
    pix=f.Pixmap(f.csRGB,w,h,pixels,False) if not alpha else f.Pixmap(f.csRGB,(0,0,w,h),True)
    if alpha:pix.clear_with(120)
    with f.open() as d:
        p=d.new_page(width=500,height=650);xref=p.insert_image(f.Rect(60,120,276,408),stream=pix.tobytes('png'));p.insert_text((60,80),'Texto conservado')
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation)
        if shared:
            p=d.new_page(width=600,height=850);p.insert_image(f.Rect(40,100,472,676),xref=xref)
        return d.tobytes(deflate=False)


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_downsample_reduces_preserves_text_geometry_and_digest(rotation,crop):
    base=source(rotation,crop);out,r=compress_images(base,[],150,80)
    assert r['reduced'] and len(r['changed_images'])==1 and r['text_preserved']
    assert r['sha256']==hashlib.sha256(out).hexdigest() and len(out)<len(base)*.5
    assert r['changed_images'][0]['after']==[450,600]
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_text()==b[0].get_text() and a[0].cropbox==b[0].cropbox and a[0].rotation==b[0].rotation
        assert b[0].get_images()[0][2:4]==(450,600)
        def profile(doc):
            import re
            kind,value=doc.xref_get_key(doc[0].get_images()[0][0],'ColorSpace')
            if kind=='xref':value=doc.xref_object(int(value.split()[0]))
            match=re.search(r'/ICCBased\s+(\d+)',value)
            return doc.xref_stream(int(match[1])) if match else value
        assert profile(a)==profile(b)


def test_shared_image_uses_largest_placement_and_keeps_one_resource():
    base=source(shared=True);out,r=compress_images(base,[],150,80)
    assert r['changed_images'][0]['after']==[900,1200] and r['changed_images'][0]['pages']==[0,1]
    with f.open(stream=out) as d:
        assert d[0].get_images()[0][0]==d[1].get_images()[0][0]
        assert d[0].get_image_rects(d[0].get_images()[0][0])[0]==f.Rect(60,120,276,408)


def test_unsupported_and_low_resolution_images_unchanged():
    base=source(alpha=True);out,r=compress_images(base,[],150,80);assert out==base and not r['reduced'] and r['skipped']
    with f.open() as d:
        p=d.new_page();pix=f.Pixmap(f.csRGB,(0,0,20,20),False);pix.clear_with(100);p.insert_image(f.Rect(50,100,250,300),stream=pix.tobytes('png'));base=d.tobytes()
    assert compress_images(base,[],150,80)[0]==base


@pytest.mark.parametrize('dpi,quality',[(True,80),(71,80),(301,80),(150,39),(150,96),(150,False),(150.0,80)])
def test_invalid_parameters(dpi,quality):
    with pytest.raises(DocumentError):compress_images(source(),[],dpi,quality)


@pytest.mark.parametrize('kind',['annot','field','layer','signed','permission'])
def test_complex_and_protected_sources_rejected(kind):
    with f.open(stream=source()) as d:
        p=d[0]
        if kind=='annot':p.add_text_annot((350,350),'No alterar')
        elif kind=='field':
            w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name='Name';w.rect=f.Rect(20,500,100,530);p.add_widget(w)
        elif kind=='layer':d.add_ocg('Layer')
        elif kind=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>')
        base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_COPY) if kind=='permission' else d.tobytes()
    with pytest.raises(DocumentError):compress_images(base,[],150,80)


def test_text_only_no_quality_loss_and_page_limit():
    with f.open() as d:
        d.new_page().insert_text((50,80),'Digital original');base=d.tobytes()
    assert compress_images(base,[],150,80)[0]==base
    with f.open() as d:
        for _ in range(31):d.new_page()
        with pytest.raises(DocumentError):compress_images(d.tobytes(),[],150,80)


def test_api_and_independent_extraction(monkeypatch,tmp_path):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'recovery'));base=source(90,True)
    with TestClient(app) as c:
        info=c.post('/api/documents',files={'file':('scan.pdf',base,'application/pdf')}).json();url=f"/api/documents/{info['id']}/compress-images";payload={'dpi':150,'quality':80}
        preview=c.post(url,json={**payload,'preview':True,'page':0});assert preview.status_code==200 and preview.json()['preview'].startswith('data:image/png;base64,')
        result=c.post(url,json=payload);assert result.status_code==200 and hashlib.sha256(result.content).hexdigest()==result.headers['X-PDF-SHA256']
        target=tmp_path/'compressed.pdf';target.write_bytes(result.content);assert 'Texto conservado' in subprocess.check_output(['pdftotext',str(target),'-']).decode()
        assert c.post(url,json={**payload,'preview':True,'page':99}).status_code==422


@pytest.mark.parametrize('kind',['single','total'])
def test_pixel_budgets_checked_before_native_placement_decoding(kind,monkeypatch):
    with f.open() as d:
        p=d.new_page()
        for index in range(1 if kind=='single' else 6):
            pix=f.Pixmap(f.csRGB,(0,0,1,1),False);pix.clear_with(index+1)
            xref=p.insert_image(f.Rect(20+index*20,100,30+index*20,110),stream=pix.tobytes('png'))
            d.xref_set_key(xref,'Width','6000' if kind=='single' else '4000');d.xref_set_key(xref,'Height','6000' if kind=='single' else '3000')
        base=d.tobytes()
    def forbidden(*args,**kwargs):raise AssertionError('No se debe decodificar antes de comprobar el presupuesto.')
    monkeypatch.setattr(f.Page,'get_image_rects',forbidden)
    with pytest.raises(DocumentError,match='24 MP|64 MP'):compress_images(base,[],150,80)


def cmyk_source(profile=True):
    w,h=800,800
    samples=bytes(v for y in range(h) for x in range(w) for v in (x//4,y//4,80,20))
    pix=f.Pixmap(f.csCMYK,w,h,samples,False)
    with f.open() as d:
        p=d.new_page(width=400,height=500);xref=p.insert_image(f.Rect(40,120,184,264),pixmap=pix);p.insert_text((40,60),'CMYK conservado')
        if not profile:d.xref_set_key(xref,'ColorSpace','/DeviceCMYK')
        return d.tobytes()


@pytest.mark.parametrize('profile',[False,True])
def test_cmyk_compression_keeps_native_samples_profile_and_rendered_colors(profile,tmp_path):
    import re,shutil
    base=cmyk_source(profile);out,r=compress_images(base,[],150,95)
    assert r['reduced'] and r['changed_images'][0]['after']==[300,300]
    def icc(doc,xref):
        value=doc.xref_get_key(xref,'ColorSpace')[1]
        if value.endswith(' R'):value=doc.xref_object(int(value.split()[0]))
        match=re.search(r'/ICCBased\s+(\d+)',value)
        return doc.xref_stream(int(match[1])) if match else value
    with f.open(stream=base) as a,f.open(stream=out) as b:
        x=b[0].get_images()[0][0];original=a[0].get_images()[0][0]
        assert f.Pixmap(b,x).n==4 and icc(a,original)==icc(b,x)
        assert b[0].get_text()==a[0].get_text()
        # Whole-page averages could hide severe local inversions: compare the
        # image area only, where the old double Decode inversion was visible.
        clip=f.Rect(42,122,182,262)
        first=a[0].get_pixmap(clip=clip).samples;second=b[0].get_pixmap(clip=clip).samples
        assert sum(abs(x-y) for x,y in zip(first,second))/len(first)<3
    if shutil.which('pdftoppm'):
        before=tmp_path/'a.pdf';after=tmp_path/'b.pdf';before.write_bytes(base);after.write_bytes(out)
        pics=[]
        for path in [before,after]:
            subprocess.run(['pdftoppm','-scale-to','500','-singlefile','-png',str(path),str(path.with_suffix(''))],check=True,capture_output=True)
            pix=f.Pixmap(str(path.with_suffix('.png')));pics.append(pix.samples)
        assert sum(abs(x-y) for x,y in zip(*pics))/len(pics[0])<3


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_nested_form_images_use_all_placements_and_preserve_forms(rotation):
    # A scan is embedded two levels deep; its largest placement is on page 2.
    with f.open(stream=source()) as original,f.open() as middle,f.open() as d:
        p=middle.new_page(width=500,height=650);p.show_pdf_page(p.rect,original,0)
        p=d.new_page(width=500,height=650);p.show_pdf_page(p.rect,middle,0);p.set_rotation(rotation)
        p=d.new_page(width=1000,height=1300);p.show_pdf_page(p.rect,middle,0)
        base=d.tobytes()
    out,r=compress_images(base,[],150,90)
    assert r['changed_images'][0]['after']==[900,1200] and r['changed_images'][0]['pages']==[0,1]
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for index in range(2):
            assert b[index].get_text()==a[index].get_text() and b[index].rotation==a[index].rotation
            assert len(b[index].get_xobjects())==len(a[index].get_xobjects())
            assert b[index].get_images()[0][0]==b[0].get_images()[0][0]


def test_form_budget_is_checked_before_decoding(monkeypatch):
    monkeypatch.setattr(f.Page,'get_xobjects',lambda p:[(n,0,'Form',f.Rect(0,0,10,10)) for n in range(201)])
    monkeypatch.setattr(f.Page,'get_image_rects',lambda *a,**k:pytest.fail('No debe decodificar.'))
    with pytest.raises(DocumentError,match='200 Form'):compress_images(source(),[],150,80)
