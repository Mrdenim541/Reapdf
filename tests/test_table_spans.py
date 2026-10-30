from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as E
import pytest
from backend.engine import DocumentError
from backend.table_regions import csv_bytes,docx_bytes
from backend.table_spans import validate

NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+NS['w']+'}'
CELLS=[['HEADER','','X'],['A','','Y'],['','','Z']]
SPANS=[{'row':0,'column':0,'rowspan':1,'colspan':2},{'row':1,'column':0,'rowspan':2,'colspan':2}]


def test_word_horizontal_and_vertical_merges_and_literal_text_survive():
    data=docx_bytes(CELLS,True,SPANS)
    with ZipFile(BytesIO(data)) as z:
        root=E.fromstring(z.read('word/document.xml'));rows=root.findall('.//w:tr',NS)
        assert [len(r.findall('w:tc',NS)) for r in rows]==[2,2,2]
        assert [n.get(W+'val') for n in root.findall('.//w:gridSpan',NS)]==['2','2','2']
        assert [n.get(W+'val') for n in root.findall('.//w:vMerge',NS)]==['restart','continue']
        text=''.join(root.itertext());assert all(v in text for row in CELLS for v in row)
    assert b'HEADER,,X' in csv_bytes(CELLS,SPANS)


@pytest.mark.parametrize('spans',[
 [{'row':0,'column':0,'rowspan':0,'colspan':2}],
 [{'row':0,'column':0,'rowspan':1,'colspan':1}],
 [{'row':0,'column':0,'rowspan':4,'colspan':2}],
 [{'row':True,'column':0,'rowspan':1,'colspan':2}],
 [{'row':0,'column':0,'rowspan':1,'colspan':3}],
 SPANS+[SPANS[0]],{},[{'row':0}],
 ])
def test_unsafe_merges_rejected_in_both_exports(spans):
    with pytest.raises(DocumentError):docx_bytes(CELLS,False,spans)
    with pytest.raises(DocumentError):csv_bytes(CELLS,spans)


def test_repeated_header_cannot_cross_body_rows():
    with pytest.raises(DocumentError,match='encabezado'):docx_bytes([['ALL',''],['','']],True,[{'row':0,'column':0,'rowspan':2,'colspan':2}])
    assert docx_bytes([['ALL',''],['','']],False,[{'row':0,'column':0,'rowspan':2,'colspan':2}]).startswith(b'PK')


def test_api_exports_reviewed_merges_and_blocks_hidden_text():
    from fastapi.testclient import TestClient
    from backend.app import app
    from tests.test_table_regions import source
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('table.pdf',source(),'application/pdf')}).json();url='/api/documents/'+doc['id']+'/export-region-table'
        assert c.post(url,json={'format':'docx','cells':CELLS,'spans':SPANS}).status_code==200
        assert c.post(url,json={'format':'csv','cells':[['A','HIDDEN']],'spans':[SPANS[0]]}).status_code==422
