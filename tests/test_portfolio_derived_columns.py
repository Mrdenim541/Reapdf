import pytest,pymupdf as f
from backend.portfolio_metadata import model,edit
from backend.engine import DocumentError
from backend.embedded_files import normalize


def source():
    with f.open() as d:
        d.new_page();d.embfile_add('entry',b'ATTACHMENT BYTES',filename='original.txt',ufilename='original.txt',desc='Original description');spec=normalize(d)[0][1];n=f.mupdf;params=n.pdf_dict_getp(spec,'EF/F/Params');n.pdf_dict_puts(params,'CreationDate',n.pdf_new_text_string('D:20260102030405Z'));n.pdf_dict_puts(params,'ModDate',n.pdf_new_text_string('D:20260304050607Z'))
        schema=' '.join('/'+key+' << /Subtype/'+kind+' /N('+key+') /E true /O '+str(i)+' >>' for i,(key,kind) in enumerate([('File','F'),('Details','Desc'),('Bytes','Size'),('Created','CreationDate'),('Changed','ModDate')]))
        d.xref_set_key(d.pdf_catalog(),'Collection','<< /Schema << '+schema+' >> >>');return d.tobytes()


def test_builtin_collection_columns_show_derived_values_without_editing_them():
    base=source();r=model(base);v=r['files'][0]['values'];assert v['File']=='original.txt' and v['Details']=='Original description' and v['Bytes']==len(b'ATTACHMENT BYTES')
    assert v['Created']=='D:20260102030405Z' and v['Changed']=='D:20260304050607Z';assert all(c['derived'] and not c['editable'] for c in r['columns'])
    with f.open(stream=base) as d:assert d.embfile_get('entry')==b'ATTACHMENT BYTES'


@pytest.mark.parametrize('field',['File','Details','Bytes','Created','Changed'])
def test_builtin_columns_cannot_be_overwritten_as_arbitrary_collection_values(field):
    with pytest.raises(DocumentError):edit(source(),[],[{'name':'entry','field':field,'value':'changed'}])
