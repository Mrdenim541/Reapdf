from pathlib import Path
from copy import deepcopy
import hashlib
import shutil
import subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError,export_pdf
from backend.styled_text import inspect_styled,replace_styled,unicode_cmap,stream
from backend.projects import build_project,read_project

FONT=Path(__file__).resolve().parent.parent/'resources/fonts/DejaVuSans.ttf'
BOX=[35,150,500,230]


def source(subset=False,crop=False,shared_resources=False):
    with f.open() as d:
        p=d.new_page(width=595,height=842)
        p.insert_text((45,70),'CONTENIDO CONSERVADO',fontsize=16)
        p.insert_text((45,200),'Texto original en negrita',fontname='hebo',fontsize=18,color=(.1,.2,.5))
        p.insert_text((45,250),'Estilo cursiva original',fontname='heit',fontsize=16,color=(.6,.1,.2))
        p.insert_font(fontname='FuenteOriginal',fontfile=str(FONT));p.insert_text((45,320),'Fuente incrustada original 12345',fontname='FuenteOriginal',fontsize=15,color=(.1,.4,.2))
        q=d.new_page(width=595,height=842);q.insert_text((45,80),'PAGINA SIN CAMBIOS',fontname='hebo',fontsize=18)
        if shared_resources:d.xref_set_key(q.xref,'Resources',d.xref_get_key(d[0].xref,'Resources')[1])
        if crop:d[0].set_cropbox(f.Rect(20,20,575,822))
        if subset:d.subset_fonts()
        return d.tobytes()


def region(crop=False):return [15,130,500,230] if crop else BOX


def runs(data,box=BOX):return inspect_styled(data,[],0,box)['runs']


def program_hashes(doc):
    return {hashlib.sha256(doc.extract_font(i[0])[3]).hexdigest() for p in doc for i in p.get_fonts() if i[1]=='ttf'}


def update(data,subset=False,crop=False):
    box=region(crop);rows=runs(data,box);assert len(rows)==3 and all(r['editable'] for r in rows)
    texts=['Texto en negrita','Estilo cursiva','Fuente original 123']
    return replace_styled(data,[],0,box,[{'id':r['id'],'text':text} for r,text in zip(rows,texts)])


@pytest.mark.parametrize('subset',[False,True])
@pytest.mark.parametrize('crop',[False,True])
@pytest.mark.parametrize('shared_resources',[False,True])
def test_preserves_original_fonts_styles_origins_other_page_and_embedded_program(subset,crop,shared_resources,tmp_path):
    base=source(subset,crop,shared_resources);before=runs(base,region(crop));out=update(base,subset,crop)
    after=runs(out,region(crop));assert [r['text'] for r in after]==['Texto en negrita','Estilo cursiva','Fuente original 123']
    for old,new in zip(before,after):
        assert (new['font'],new['size'],new['color'])==(old['font'],old['size'],old['color'])
        assert new['origin']==pytest.approx(old['origin'],abs=.01) and new['editable']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert 'CONTENIDO CONSERVADO' in b[0].get_text() and 'incrustada' not in b[0].get_text()
        assert program_hashes(a)==program_hashes(b) and not b[0].get_images()
        assert a[0].cropbox==b[0].cropbox
    if shutil.which('pdftotext'):
        path=tmp_path/'styles.pdf';path.write_bytes(out);text=subprocess.check_output(['pdftotext',str(path),'-']).decode()
        assert all(t in text for t in ['Texto en negrita','Estilo cursiva','Fuente original 123','PAGINA SIN CAMBIOS'])
        assert 'Fuente incrustada' not in text


def test_subset_rejects_missing_glyph_without_fallback_or_mutation():
    base=source(True);row=runs(base)[-1]
    with pytest.raises(DocumentError,match='carácter'):replace_styled(base,[],0,BOX,[{'id':row['id'],'text':'Útil'}])
    assert runs(base)[-1]['text']=='Fuente incrustada original 12345'
    # A complete program allows the character; the subset's full ToUnicode map
    # alone is not proof that its actual glyph outline exists.
    full=source(False);row=runs(full)[-1];out=replace_styled(full,[],0,BOX,[{'id':row['id'],'text':'Útil αβγ'}])
    assert runs(out)[-1]['text']=='Útil αβγ'


def test_delete_one_fragment_does_not_replace_others_or_claim_sanitization():
    base=source(True);rows=runs(base);out=replace_styled(base,[],0,BOX,[{'id':rows[1]['id'],'text':''}])
    result=runs(out);assert [r['text'] for r in result]==[rows[0]['text'],rows[2]['text']]
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert 'CONTENIDO CONSERVADO' in b[0].get_text()


@pytest.mark.parametrize('changes',[[],None,[{}],[{'id':'fake','text':'X'}],[{'id':True,'text':'X'}],[{'id':'1:0:0','text':'x','size':10}]])
def test_invalid_fragment_requests_fail_before_mutating_source(changes):
    with pytest.raises(DocumentError):replace_styled(source(),[],0,BOX,changes)


@pytest.mark.parametrize('text',['x'*4001,'Texto\nOtra línea','A\tB','\x7f',False,None,'Texto original en negrita adicional demasiado largo'])
def test_invalid_text_and_overflow_are_rejected(text):
    base=source();row=runs(base)[0]
    with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[{'id':row['id'],'text':text}])


def test_duplicate_unchanged_and_atomic_multi_fragment_errors():
    base=source(True);rows=runs(base);entry={'id':rows[0]['id'],'text':'Texto'}
    with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[entry,entry])
    with pytest.raises(DocumentError,match='No hay cambios'):replace_styled(base,[],0,BOX,[{'id':rows[0]['id'],'text':rows[0]['text']}])
    with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[entry,{'id':rows[2]['id'],'text':'Útil'}])
    assert runs(base)[0]['text']==rows[0]['text']


@pytest.mark.parametrize('rotation',[90,180,270])
def test_rotated_pages_expose_native_text_coordinates(rotation):
    with f.open(stream=source()) as d:d[0].set_rotation(rotation);base=d.tobytes()
    assert inspect_styled(base,[],0,BOX)==inspect_styled(source(),[],0,BOX)


@pytest.mark.parametrize('kind',['layer','pending_redact','field','note','form','clip','transparency','hidden','tracking','overlap'])
def test_complex_regions_are_protected(kind):
    with f.open(stream=source()) as d:
        p=d[0]
        if kind=='layer':d.add_ocg('Capa')
        elif kind=='pending_redact':p.add_redact_annot(f.Rect(40,190,150,220))
        elif kind=='field':
            w=f.Widget();w.field_name='Campo';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(40,190,150,220);p.add_widget(w)
        elif kind=='note':p.add_text_annot((60,195),'Nota')
        elif kind=='form':
            with f.open(stream=source()) as other:p.show_pdf_page(f.Rect(45,450,250,700),other,1)
        elif kind=='clip':
            x=p.get_contents()[1];d.update_stream(x,b'q 0 0 595 842 re W n\n'+d.xref_stream(x)+b'\nQ')
        elif kind=='transparency':p.insert_text((45,450),'Transparente',fill_opacity=.5)
        elif kind=='hidden':p.insert_text((45,450),'Oculto',render_mode=3)
        elif kind=='tracking':
            x=p.get_contents()[1];d.update_stream(x,d.xref_stream(x).replace(b'BT',b'BT 2 Tc'))
        else:p.insert_text((50,200),'Solapado',fontsize=12)
        base=d.tobytes()
    if kind in ['form','clip']:
        rows=runs(base);assert all(r['editable'] for r in rows)
        out=replace_styled(base,[],0,BOX,[{'id':rows[0]['id'],'text':'Texto'}])
        assert runs(out)[0]['text']=='Texto'
        with f.open(stream=base) as a,f.open(stream=out) as b:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
    elif kind in ['tracking','overlap']:
        rows=runs(base)
        if kind=='tracking':assert not rows[0]['editable']
        else:
            row=next(r for r in rows if r['text']=='Texto original en negrita')
            with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[{'id':row['id'],'text':'Texto'}])
    else:
        with pytest.raises(DocumentError):inspect_styled(base,[],0,BOX)


def test_custom_base_font_encoding_is_readonly():
    with f.open(stream=source()) as d:
        x=next(i[0] for i in d[0].get_fonts() if i[3]=='Helvetica-Bold');d.xref_set_key(x,'Encoding','<</Type/Encoding/BaseEncoding/WinAnsiEncoding/Differences[65/B]>>');base=d.tobytes()
    row=runs(base)[0];assert not row['editable'] and 'codificación' in row['reason']


@pytest.mark.parametrize('fontname',['helv','hebo','heit','hebi','tiro','tibo','tiit','tibi','cour','cobo','coit','cobi'])
def test_all_twelve_standard_faces_keep_their_own_font(fontname):
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'Texto original largo',fontname=fontname,fontsize=16);base=d.tobytes()
    box=[30,50,400,60];row=runs(base,box)[0];assert row['editable']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'Texto útil'}])
    assert runs(out,box)[0]['font']==row['font'] and runs(out,box)[0]['text']=='Texto útil'


def test_unicode_cmap_supports_bfchar_bfrange_arrays_and_supplementary_pairs():
    data=b'1 begincodespacerange <0000><ffff> endcodespacerange 2 beginbfchar <0001><0041> <0002><d83dde00> endbfchar 2 beginbfrange <0003><0004><0042> <0005><0006>[<00e9><03b1>] endbfrange'
    assert unicode_cmap(data)=={1:'A',2:'😀',3:'B',4:'C',5:'é',6:'α'}


@pytest.mark.parametrize('suffix',[b'usecmap',b'1 beginbfchar <01><0041> endbfchar',b'1 beginbfrange <0005><0002><0041> endbfrange',b'2 beginbfchar <0001><0041><0001><0042> endbfchar'])
def test_unsupported_or_conflicting_cmaps_are_rejected(suffix):
    with pytest.raises(DocumentError):unicode_cmap(b'1 begincodespacerange <0000><ffff> endcodespacerange '+suffix)


def test_font_stream_inflation_is_bounded_independently_of_pdf_size():
    with f.open() as d:
        d.new_page();x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'A'*5000,compress=True)
        with pytest.raises(DocumentError):stream(d,x,1000)
        assert stream(d,x,6000)==b'A'*5000


@pytest.mark.parametrize('permissions',[f.PDF_PERM_MODIFY,f.PDF_PERM_PRINT])
def test_permissions_and_encryption_are_kept(permissions):
    with f.open(stream=source()) as d:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner1234',permissions=permissions)
    if permissions==f.PDF_PERM_PRINT:
        with pytest.raises(DocumentError):inspect_styled(base,[],0,BOX)
    else:
        row=runs(base)[0];out=replace_styled(base,[],0,BOX,[{'id':row['id'],'text':'Texto'}])
        with f.open(stream=out) as d:assert not d.permissions&f.PDF_PERM_COPY and not d.permissions&f.PDF_PERM_PRINT and 'AES' in d.metadata['encryption']


def test_styled_snapshot_project_roundtrip_and_source_are_independent():
    base=source(True);out=update(base,True);project,_=build_project(out,[],{'name':'styles.pdf','page':0,'zoom':1,'base_changes':1})
    restored,ops,_=read_project(project);assert restored==out and ops==[]
    assert runs(base)[-1]['text']=='Fuente incrustada original 12345'
    assert runs(restored)[-1]['text']=='Fuente original 123'


def test_api_inspect_preview_and_new_version_preserve_source(tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'));base=source(True)
    with TestClient(app) as c:
        document=c.post('/api/documents',files={'file':('styles.pdf',base)}).json();url='/api/documents/'+document['id'];payload={'page':0,'box':BOX}
        response=c.post(url+'/inspect-styled-text',json=payload);assert response.status_code==200
        rows=response.json()['runs'];assert all('_font' not in r for r in rows)
        config={**payload,'changes':[{'id':rows[2]['id'],'text':'Fuente original 123'}]}
        assert c.post(url+'/replace-styled-text',json={**config,'preview':True}).content.startswith(b'\x89PNG')
        version=c.post(url+'/replace-styled-text',json=config);assert version.status_code==200 and version.json()['id']!=document['id']
        assert c.post(url+'/inspect-styled-text',json=payload).json()['runs'][2]['text']==rows[2]['text']


@pytest.mark.parametrize('subset',[False,True])
def test_poppler_appearance_matches_independently_written_original_fonts(subset,tmp_path):
    if not shutil.which('pdftoppm'):pytest.skip('Poppler no disponible')
    base=source(subset);actual=update(base,subset)
    with f.open() as d:
        p=d.new_page(width=595,height=842);p.insert_text((45,70),'CONTENIDO CONSERVADO',fontsize=16)
        p.insert_text((45,200),'Texto en negrita',fontname='hebo',fontsize=18,color=(.1,.2,.5))
        p.insert_text((45,250),'Estilo cursiva',fontname='heit',fontsize=16,color=(.6,.1,.2))
        p.insert_font(fontname='Esperada',fontfile=str(FONT));p.insert_text((45,320),'Fuente original 123',fontname='Esperada',fontsize=15,color=(.1,.4,.2));expected=d.tobytes()
    pixmaps=[]
    for name,data in [('actual',actual),('expected',expected)]:
        path=tmp_path/(name+'.pdf');path.write_bytes(data);prefix=tmp_path/name
        subprocess.run(['pdftoppm','-f','1','-l','1','-r','72','-singlefile','-png',str(path),str(prefix)],check=True,capture_output=True)
        pixmaps.append(f.Pixmap(str(prefix)+'.png'))
    a,b=pixmaps;differences=[abs(x-y) for x,y in zip(a.samples,b.samples)]
    assert max(differences)<=3 and sum(differences)/len(differences)<.02


def test_explicit_expansion_keeps_style_and_uses_only_the_selected_area():
    base=source(True);row=runs(base)[-1];text='Fuente incrustada original 12345 Fuente original'
    with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[{'id':row['id'],'text':text}])
    out=replace_styled(base,[],0,BOX,[{'id':row['id'],'text':text}],expand=True);edited=runs(out)[-1]
    assert edited['text']==text and edited['size']==row['size'] and edited['font']==row['font'] and edited['origin']==row['origin']
    with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[{'id':row['id'],'text':text*4}],expand=True)


@pytest.mark.parametrize('value',[1,'true',None])
def test_expansion_does_not_accept_non_boolean_options(value):
    with pytest.raises(DocumentError):replace_styled(source(),[],0,BOX,[{'id':'1:0:0','text':'X'}],expand=value)


def test_expansion_cannot_overwrite_an_adjacent_fragment():
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'Izquierda',fontsize=14);p.insert_text((120,80),'Derecha',fontname='hebo',fontsize=14);base=d.tobytes()
    box=[30,50,400,60];row=runs(base,box)[0]
    with pytest.raises(DocumentError,match='cruza'):replace_styled(base,[],0,box,[{'id':row['id'],'text':'Izquierda más larga'}],expand=True)
