import csv,io,hashlib
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.table_regions import extract,csv_bytes,assign

VALUES=[['ITEM','COUNT','VALUE'],['BOLT','12','24.50'],['PLATE','4','10.00']]
BOX=[40,80,450,150]


def source(scan=False,rotation=0,orientation=0):
    with f.open() as d:
        p=d.new_page(width=540,height=400)
        for x in [40,190,340,490]:p.draw_line((x,80),(x,230),width=1)
        for y in [80,130,180,230]:p.draw_line((40,y),(490,y),width=1)
        for r,row in enumerate(VALUES):
            for c,value in enumerate(row):p.insert_text((55+c*150,111+r*50),value,fontsize=14)
        if scan:
            pix=p.get_pixmap(matrix=f.Matrix(2,2).prerotate(orientation),alpha=False);pic=pix.tobytes('png')
            with f.open() as out:
                q=out.new_page(width=540,height=400);q.insert_image(q.rect,stream=pic,keep_proportion=False);q.set_rotation(rotation);return out.tobytes()
        p.set_rotation(rotation);return d.tobytes()


def box_for(base):
    with f.open(stream=base) as d:return list(f.Rect(40,80,490,230)*d[0].rotation_matrix)


@pytest.mark.parametrize('scan',[False,True])
def test_digital_and_real_scan_table_grid_and_cells_without_modifying_source(scan):
    base=source(scan);digest=hashlib.sha256(base).digest();report=extract(base,[],0,BOX,language='eng',dpi=200)
    assert report['method']==('ocr' if scan else 'digital');assert report['cells']==VALUES
    assert len(report['columns'])==4 and len(report['rows'])==4 and report['detected_grid'] and not report['source_modified']
    assert hashlib.sha256(base).digest()==digest
    assert list(csv.reader(io.StringIO(csv_bytes(report['cells']).decode('utf-8-sig'))))==VALUES


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_visible_rotation_maps_digital_grid_and_words(rotation):
    base=source(False,rotation)
    with f.open(stream=base) as d:r=f.Rect(40,80,490,230)*d[0].rotation_matrix
    report=extract(base,[],0,[r.x0,r.y0,r.width,r.height],mode='digital');flat=[c for row in report['cells'] for c in row];assert sorted(flat)==sorted(v for row in VALUES for v in row)
    assert len(report['columns'])==4 and len(report['rows'])==4


@pytest.mark.parametrize('grid',[
 {'columns':[40,190,340,490],'rows':[80,130,180,230]},
 {'columns':[40,200,350,490],'rows':[80,132,183,230]},
 ])
def test_manual_grid_controls_cell_assignment(grid):
    report=extract(source(),[],0,BOX,grid,mode='digital');assert report['cells']==VALUES and not report['detected_grid']


@pytest.mark.parametrize('grid',[
 {'columns':[40,490,190],'rows':[80,230]}, {'columns':[40,41,490],'rows':[80,230]},
 {'columns':[41,490],'rows':[80,230]}, {'columns':[40,float('nan'),490],'rows':[80,230]},
 {'columns':[40,490],'rows':[80,230],'extra':True},
 ])
def test_invalid_grids_rejected(grid):
    with pytest.raises(DocumentError):extract(source(),[],0,BOX,grid,mode='digital')


def test_explicit_ocr_on_digital_page_still_captures_all_cells():
    assert extract(source(),[],0,BOX,mode='ocr',language='eng')['cells']==VALUES


def test_grid_crossing_words_are_flagged_and_no_words_silently_joined():
    words=[{'text':'AB','bbox':[5,2,15,8]},{'text':'NEXT','bbox':[22,3,28,8]}]
    cells,crossing=assign(words,[0,10,20,30],[0,10]);assert crossing==1 and cells==[['','AB','NEXT']]


def test_csv_formula_protection_quotes_and_unicode():
    data=csv_bytes([['=1+1',' +cmd','@SUM(A1)','-2','á,"x"\nnext']]);row=next(csv.reader(io.StringIO(data.decode('utf-8-sig'))));assert all(row[i].startswith("'") for i in range(4));assert row[4]=='á,"x"\nnext'


@pytest.mark.parametrize('cells',[[],[['x'],['x','y']],[['x'*4001]],[[1]]])
def test_invalid_exports_fail(cells):
    with pytest.raises(DocumentError):csv_bytes(cells)


def test_reviewed_table_word_conversion_is_editable_and_reimports_all_cells():
    from backend.table_regions import docx_bytes
    from backend.docx_import import import_docx
    from zipfile import ZipFile
    from xml.etree import ElementTree as E
    data=docx_bytes(VALUES)
    with ZipFile(io.BytesIO(data)) as z:
        root=E.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        assert len(root.findall('.//w:tr',ns))==3 and len(root.findall('.//w:tc',ns))==9
        assert root.find('.//w:tblHeader',ns) is not None and all('vba' not in name.lower() for name in z.namelist())
    pdf,report=import_docx(data)
    with f.open(stream=pdf) as d:
        text=' '.join(p.get_text() for p in d)
        assert all(value in text for row in VALUES for value in row) and report['tables']==1 and report['text_check_passed']


def test_region_api_returns_review_without_creating_a_document_and_exports_corrections():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('Table.pdf',source(True),'application/pdf')}).json();url='/api/documents/'+doc['id']
        response=client.post(url+'/extract-table-region',json={'page':0,'box':BOX,'language':'eng'});assert response.status_code==200,response.text
        result=response.json();assert result['cells']==VALUES and result['review_required'] and 'document' not in result
        result['cells'][1][0]='CORRECTED'
        csv_result=client.post(url+'/export-region-table',json={'format':'csv','cells':result['cells']});assert csv_result.status_code==200 and b'CORRECTED' in csv_result.content
        word=client.post(url+'/export-region-table',json={'format':'docx','cells':result['cells']});assert word.status_code==200 and word.content.startswith(b'PK')
        assert client.post(url+'/export-region-table',json={'format':'exe','cells':result['cells']}).status_code==422


@pytest.mark.parametrize('rotation',[90,180,270])
def test_real_ocr_words_map_to_visible_page_rotations(rotation):
    base=source(True,rotation)
    with f.open(stream=base) as d:r=f.Rect(40,80,490,230)*d[0].rotation_matrix
    report=extract(base,[],0,[r.x0,r.y0,r.width,r.height],language='eng');assert sorted(v for row in report['cells'] for v in row)==sorted(v for row in VALUES for v in row)


def test_real_ocr_orientation_correction_preserves_visible_grid():
    base=source(True,orientation=180);report=extract(base,[],0,[50,170,450,150],mode='ocr',language='eng',orientation=180)
    assert sorted(v for row in report['cells'] for v in row)==sorted(v for row in VALUES for v in row)


@pytest.mark.parametrize('scan',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_cropbox_offset_and_page_rotation_keep_cell_coordinates(scan,rotation):
    with f.open(stream=source(scan)) as d:
        d[0].set_cropbox(f.Rect(10,20,530,390));d[0].set_rotation(rotation);r=f.Rect(30,60,480,210)*d[0].rotation_matrix;base=d.tobytes()
    report=extract(base,[],0,[r.x0,r.y0,r.width,r.height],language='eng');assert sorted(v for row in report['cells'] for v in row)==sorted(v for row in VALUES for v in row)


def test_largest_permitted_regular_grid_has_exactly_3000_cells():
    columns=[540*i/30 for i in range(31)];rows=[400*i/100 for i in range(101)]
    report=extract(source(),[],0,[0,0,540,400],{'columns':columns,'rows':rows},mode='digital');assert len(report['cells'])==100 and all(len(row)==30 for row in report['cells'])
