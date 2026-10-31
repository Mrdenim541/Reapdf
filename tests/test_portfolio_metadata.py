import hashlib
import pymupdf as f
import pytest
from backend.portfolio_metadata import model,edit
from backend.engine import DocumentError


def sample(shared=False):
    with f.open() as d:
        p=d.new_page();p.insert_text((50,70),'Portfolio cover')
        d.embfile_add('One.txt',b'Original file one');d.embfile_add('Two.txt',b'Original file two')
        d.xref_set_key(d.pdf_catalog(),'Collection','<< /Type /Collection /View /D /CustomFlag (Preserve) /Schema << /Code << /N (Code) /Subtype /S /E true >> /Amount << /N (Amount) /Subtype /N /E true >> /Date << /N (Date) /Subtype /D /E true >> /Locked << /N (Locked) /Subtype /S /E false >> >> >>')
        from backend.embedded_files import normalize
        n=f.mupdf;pdf=f._as_pdf_document(d);specs=normalize(d)
        ci=d.get_new_xref();d.update_object(ci,'<< /Code << /D (OLD) /P (Prefix) >> /Amount 12.5 /Date (D:20261031) /Locked (Do not edit) /ForeignValue (Keep) >>')
        for name,spec in specs:n.pdf_dict_puts(spec,'CI',n.pdf_new_indirect(pdf,ci,0))
        if shared:
            names=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/Names/EmbeddedFiles/Names');n.pdf_array_put(names,3,n.pdf_array_get(names,1))
        return d.tobytes()


@pytest.mark.parametrize('shared',[False,True])
def test_foreign_schema_prefix_unknown_fields_embedded_hashes_and_shared_metadata_preserved(shared):
    base=sample(shared);before=model(base);out=edit(base,[],[{'name':'One.txt','field':'Code','value':'NEW'},{'name':'One.txt','field':'Amount','value':'16.5'},{'name':'One.txt','field':'Date','value':'2027-02-28'}]);after=model(out)
    a=next(r for r in after['files'] if r['name']=='One.txt');b=next(r for r in after['files'] if r['name']=='Two.txt')
    assert a['values']['Code']=='NEW' and a['values']['Amount']==16.5 and a['values']['Date']=='D:20270228' and a['prefixes']['Code']=='Prefix'
    assert b['values']['Code']=='OLD'
    with f.open(stream=base) as x,f.open(stream=out) as y:
        assert x.xref_get_key(x.pdf_catalog(),'Collection')==y.xref_get_key(y.pdf_catalog(),'Collection')
        assert x[0].get_pixmap().samples==y[0].get_pixmap().samples
        assert {k:hashlib.sha256(x.embfile_get(k)).hexdigest() for k in x.embfile_names()}=={k:hashlib.sha256(y.embfile_get(k)).hexdigest() for k in y.embfile_names()}
        from backend.embedded_files import normalize
        assert all(f.mupdf.pdf_to_text_string(f.mupdf.pdf_dict_getp(spec,'CI/ForeignValue'))=='Keep' for _,spec in normalize(y))


@pytest.mark.parametrize('field,value',[('Locked','x'),('Missing','x'),('Amount','NaN'),('Amount','1000000000000000'),('Date','2026-02-30'),('Date','D:20260230120000Z'),('Date',5),('Code','x\x00')])
def test_invalid_or_locked_values_rejected(field,value):
    with pytest.raises(DocumentError):edit(sample(),[],[{'name':'One.txt','field':field,'value':value}])


def test_clear_and_duplicate_changes():
    base=sample();out=edit(base,[],[{'name':'One.txt','field':'Code','value':None}]);assert next(r for r in model(out)['files'] if r['name']=='One.txt')['values']['Code'] is None
    with pytest.raises(DocumentError):edit(base,[],[{'name':'One.txt','field':'Code','value':'x'}]*2)
