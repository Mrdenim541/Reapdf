import shutil,subprocess
from pathlib import Path
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.find_replace import inspect,replace

FONT=Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf'
Q={'text':'REG','pages':[0,1],'case_sensitive':True,'whole_word':True}

def test_original_truetype_and_partial_selection_keep_styles_and_other_content(tmp_path):
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='Embedded',fontfile=str(FONT));p.insert_text((40,80),'REG REG',fontname='Embedded',fontsize=18,color=(.1,.2,.6))
        d.new_page().insert_text((40,80),'REG');base=d.tobytes()
    found=inspect(base,[],Q);out,_,_=replace(base,[],Q,found['receipt'],[found['matches'][0]['id']],'OK')
    with f.open(stream=base) as before,f.open(stream=out) as after:
        assert 'OK REG' in after[0].get_text() and before[1].get_pixmap().samples==after[1].get_pixmap().samples
        old=before[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0];new=after[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
        assert old['font']==new['font'] and old['size']==new['size'] and old['color']==new['color']
        fonts=lambda doc:{doc.extract_font(i[0])[3] for i in doc[0].get_fonts() if i[1]=='ttf'}
        assert fonts(before)==fonts(after)
    if shutil.which('pdftotext'):
        path=tmp_path/'result.pdf';path.write_bytes(out)
        assert 'OK REG' in subprocess.check_output(['pdftotext',str(path),'-']).decode()

def test_later_missing_glyph_leaves_the_original_unchanged():
    with f.open() as d:
        d.new_page().insert_text((40,80),'REG')
        p=d.new_page();p.insert_font(fontname='Subset',fontfile=str(FONT));p.insert_text((40,80),'REG',fontname='Subset');d.subset_fonts();base=d.tobytes()
    found=inspect(base,[],Q);assert all(m['editable'] for m in found['matches'])
    with pytest.raises(DocumentError):replace(base,[],Q,found['receipt'],[m['id'] for m in found['matches']],'Z')
    with f.open(stream=base) as d:assert all(p.get_text().strip()=='REG' for p in d)

def test_over_many_matches_and_run_limit_are_explicit():
    with f.open() as d:
        p=d.new_page(width=600,height=1000)
        for i in range(21):p.insert_text((40,30+i*35),'REG',fontsize=14)
        base=d.tobytes()
    q={**Q,'pages':[0]};found=inspect(base,[],q)
    with pytest.raises(DocumentError,match='20 fragmentos'):replace(base,[],q,found['receipt'],[m['id'] for m in found['matches']],'X')
