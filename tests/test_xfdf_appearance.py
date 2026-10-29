from io import BytesIO
import xml.etree.ElementTree as E
import pymupdf as f
import pytest
from pyhanko.pdf_utils.reader import PdfFileReader
from backend import xfdf
from backend.engine import DocumentError
from backend.form_structure import pdf_string


def source(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=500,height=600);p.insert_text((40,500),'PRESERVED')
        a=p.add_freetext_annot(f.Rect(40,60,240,120),'Texto libre simple',fontsize=12,fontname='Helv',text_color=(.2,.3,.4),fill_color=(.9,.8,.7),align=1)
        a.set_info(title='Autor',subject='Tema',creationDate='D:20261029120000Z',modDate='D:20261029130000Z');a.set_flags(4|16);a.update()
        a=p.add_rect_annot(f.Rect(40,160,240,240));a.set_colors(stroke=(.1,.4,.6),fill=(.8,.9,.7));a.set_border(width=2,dashes=[4,2]);a.update()
        a=p.add_squiggly_annot(f.Rect(40,300,200,320));a.set_info(content='Ondulado');a.update()
        a=p.add_polyline_annot([(300,80),(350,120),(400,80)]);a.set_line_ends(f.PDF_ANNOT_LE_OPEN_ARROW,f.PDF_ANNOT_LE_CLOSED_ARROW);a.update()
        a=p.add_text_annot((300,350),'Nota',icon='Help');d.xref_set_key(a.xref,'Open','true');a.update()
        if crop:p.set_cropbox(f.Rect(10,20,480,580))
        p.set_rotation(rotation);return d.tobytes()


def blank(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=500,height=600);p.insert_text((40,500),'PRESERVED')
        if crop:p.set_cropbox(f.Rect(10,20,480,580))
        p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_extended_geometry_appearance_roundtrip_and_independent_pdf(rotation,crop):
    base=source(rotation,crop);xml,r=xfdf.export(base,[],include_fields=False);assert r['annotations']==5 and r['skipped_annotations']==0
    data,report=xfdf.import_data(blank(rotation,crop),[],xml,confirm=True);assert report['annotations']==5
    after,_=xfdf.export(data,[],include_fields=False)
    left=E.fromstring(xml).find(xfdf.tag('annots'));right=E.fromstring(after).find(xfdf.tag('annots'))
    for a,b in zip(left,right):
        assert a.tag==b.tag
        for key in ['rect','font','size','justification','rotation','text-color','interior-color','flags','subject','creationdate','date','dashes','head','tail','icon','open']:
            assert a.get(key)==b.get(key),(key,a.attrib,b.attrib)
    assert xfdf.import_data(data,[],xml,confirm=True,preview=True)['duplicates']==5
    root=PdfFileReader(BytesIO(data)).root;page=root['/Pages']['/Kids'][0].get_object();annotations=[v.get_object() for v in page['/Annots']];free=next(a for a in annotations if a['/Subtype']=='/FreeText');square=next(a for a in annotations if a['/Subtype']=='/Square')
    assert free['/Q']==1 and '/Helv 12' in str(free['/DA']) and free['/F']==20
    assert [float(v) for v in square['/IC']]==pytest.approx([.8,.9,.7],abs=1/255) and list(square['/BS']['/D'])==[4,2]
    with f.open(stream=data) as d:assert d[0].rotation==rotation and 'PRESERVED' in d[0].get_text()


@pytest.mark.parametrize('attribute,value',[('font','Unknown'),('size','100'),('justification','8'),('rotation','45'),('text-color','invalid'),('callout','40,50,60,70'),('flags','launch'),('dashes','0,0')])
def test_incompatible_appearance_fails_atomically(attribute,value):
    xml,_=xfdf.export(source(),[]);root=E.fromstring(xml);node=root.find('./'+xfdf.tag('annots')+'/'+xfdf.tag('freetext'));node.set(attribute,value)
    with pytest.raises(DocumentError):xfdf.import_data(blank(),[],E.tostring(root),confirm=True)


def test_name_conflicts_within_batch_and_unsupported_native_annotation():
    xml,_=xfdf.export(source(),[]);root=E.fromstring(xml);annots=root.find(xfdf.tag('annots'));first=annots[0];second=E.fromstring(E.tostring(first));second.find(xfdf.tag('contents')).text='Conflicting text';annots.append(second)
    with pytest.raises(DocumentError,match='mismo nombre'):xfdf.import_data(blank(),[],E.tostring(root),confirm=True)
    with f.open(stream=blank()) as d:
        p=d[0];a=p.add_stamp_annot(f.Rect(40,60,240,120));d.xref_set_key(a.xref,'NM',pdf_string(first.get('name')));base=d.tobytes()
    xml,_=xfdf.export(source(),[])
    with pytest.raises(DocumentError,match='mismo nombre'):xfdf.import_data(base,[],xml,confirm=True)


def test_rich_text_skipped_and_measurement_labels_not_exported_alone():
    from backend.measurements import measure
    from tests.test_measurement_precision import CAL
    data=measure(blank(),[],0,'distance',[[40,100],[140,100]],CAL);xml,r=xfdf.export(data,[]);assert r['annotations']==0 and r['skipped_annotations']==2
    with f.open(stream=source()) as d:
        p=d[0];a=next(p.annots());d.xref_set_key(a.xref,'RC',pdf_string('<body>Rich text</body>'));data=d.tobytes()
    _,report=xfdf.export(data,[]);assert report['skipped_annotations']==1


@pytest.mark.parametrize('font',['Helv','TiRo','Cour'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_plain_free_text_fonts_and_annotation_rotation(font,rotation):
    with f.open() as d:
        p=d.new_page(width=500,height=600);p.add_freetext_annot(f.Rect(40,60,240,120),'Texto simple',fontname=font,rotate=rotation);base=d.tobytes()
    xml,r=xfdf.export(base,[]);assert r['annotations']==1
    out,_=xfdf.import_data(blank(),[],xml,confirm=True);after,_=xfdf.export(out,[])
    a=E.fromstring(xml).find('./'+xfdf.tag('annots')+'/*');b=E.fromstring(after).find('./'+xfdf.tag('annots')+'/*')
    assert a.get('font')==b.get('font') and a.get('rotation')==b.get('rotation')==str(rotation)


def test_unsupported_free_text_style_is_rejected_instead_of_substituted():
    xml,_=xfdf.export(source(),[]);root=E.fromstring(xml);node=root.find('./'+xfdf.tag('annots')+'/'+xfdf.tag('freetext'));node.set('font','Helvetica-Bold')
    with pytest.raises(DocumentError):xfdf.import_data(blank(),[],E.tostring(root),confirm=True)


def test_fractional_dash_lengths_are_not_truncated():
    xml,_=xfdf.export(source(),[]);root=E.fromstring(xml);node=root.find('./'+xfdf.tag('annots')+'/'+xfdf.tag('square'));node.set('dashes','2.5,1.25')
    out,_=xfdf.import_data(blank(),[],E.tostring(root),confirm=True);after,_=xfdf.export(out,[]);node=E.fromstring(after).find('./'+xfdf.tag('annots')+'/'+xfdf.tag('square'));assert node.get('dashes')=='2.5,1.25'
