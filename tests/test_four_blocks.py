from io import BytesIO
import xml.etree.ElementTree as E
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.basic_tagging import candidates,create
from backend.structure_editing import model,reading_preview
from backend.variable_fonts import inspect,freeze
from backend.form_actions import policy,value
from backend import xfdf
from backend.table_regions import extract
from tests.test_form_standard_actions import source as form_source,fill


def variable_program():
    from fontTools.ttLib import TTFont
    from fontTools.fontBuilder import FontBuilder
    from fontTools.ttLib.tables.TupleVariation import TupleVariation
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    builder=FontBuilder(1000,isTTF=True);order=['.notdef','A','B','C','space'];builder.setupGlyphOrder(order);builder.setupCharacterMap({ord(c):c for c in 'ABC'}|{32:'space'});builder.setupHorizontalMetrics({name:(600,0) for name in order});builder.setupHorizontalHeader(ascent=800,descent=-200);builder.setupNameTable({'familyName':'ReapdfVariable','styleName':'Regular','psName':'ReapdfVariable'});builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200);builder.setupPost();glyphs={}
    for i,name in enumerate(order):
        pen=TTGlyphPen(None)
        if name not in ['.notdef','space']:
            pen.moveTo((40,0));pen.lineTo((500-i*40,0));pen.lineTo((500-i*40,700));pen.lineTo((40,700));pen.closePath()
        glyphs[name]=pen.glyph()
    builder.setupGlyf(glyphs);builder.setupMaxp();builder.setupFvar([('wght',100,400,900,'Weight')],[]);font=builder.font
    glyph=font['glyf']['A'];coords=glyph.getCoordinates(font['glyf'])[0];deltas=[(0,0)]*(len(coords)+4);deltas[0]=(40,0)
    builder.setupGvar({name:[TupleVariation({'wght':(0,1,1)},deltas)] if name=='A' else [] for name in font.getGlyphOrder()})
    out=BytesIO();font.save(out);return out.getvalue()


def variable_pdf():
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='OriginalVariable',fontbuffer=variable_program());p.insert_text((50,120),'ABC ABC',fontname='OriginalVariable',fontsize=20);p.insert_text((40,400),'UNCHANGED');d.new_page().insert_text((40,40),'SECOND PAGE');return d.tobytes()


def test_variable_explicit_default_can_then_be_edited_without_font_substitution():
    from backend.styled_text import inspect_styled,replace_styled
    from tests.test_cff_forms_mixed import box_for
    base=variable_pdf();info=inspect(base,[]);assert len(info['fonts'])==1 and info['fonts'][0]['axes']==[{'tag':'wght','minimum':100,'default':400,'maximum':900}]
    selected=[{'xref':info['fonts'][0]['xref'],'axes':{'wght':400}}]
    out,report=freeze(base,[],selected,True);assert report['appearance_verified'] and report['pages']==2 and not inspect(out,[])['fonts']
    box=box_for(out,'ABC ABC');row=inspect_styled(out,[],0,box)['runs'][0];assert row['editable'],row['reason']
    edited=replace_styled(out,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b,f.open(stream=edited) as c:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and 'CBA AB' in c[0].get_text()
        assert a[1].get_pixmap().samples==c[1].get_pixmap().samples


@pytest.mark.parametrize('mode',['review','axis','missing_axis','duplicate','unknown','empty'])
def test_variable_rejects_unreviewed_or_implicit_design_changes(mode):
    base=variable_pdf();row=inspect(base,[])['fonts'][0];selected=[{'xref':row['xref'],'axes':{'wght':400}}]
    if mode=='axis':selected[0]['axes']['wght']=700
    if mode=='missing_axis':selected[0]['axes']={}
    if mode=='duplicate':selected*=2
    if mode=='unknown':selected[0]['xref']=99999
    if mode=='empty':selected=[]
    with pytest.raises(DocumentError):freeze(base,[],selected,mode!='review')


def table_pdf(rotation=0):
    with f.open() as d:
        p=d.new_page(width=400,height=300)
        for x,y,text in [(40,50,'Name'),(220,50,'Value'),(40,100,'Alpha'),(220,100,'100'),(40,150,'Beta'),(220,150,'200')]:p.insert_text((x,y),text)
        p.set_rotation(rotation);return d.tobytes()


def table_entries(info):return [{'id':entry['id'],'role':'TH' if i<2 else 'TD','table':1,'row':i//2+1,'column':i%2+1,'scope':'Column'} for i,entry in enumerate(info['entries'])]


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_semantic_table_tree_real_order_and_pixels(rotation):
    base=table_pdf(rotation);info=candidates(base,[]);out,report=create(base,[],table_entries(info),reviewed=True)
    assert report['tables']==1 and report['table_cells']==6
    rows=model(out,[])['nodes'];assert [r['role'] for r in rows]==['Document','Sect','Table','TR','TH','TH','TR','TD','TD','TR','TD','TD']
    flow=reading_preview(out,[],0)['blocks'];assert [r['text'] for r in flow]==['Name','Value','Alpha','100','Beta','200'] and all('Table' in r['roles'] for r in flow)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        head=next(r for r in rows if r['role']=='TH');assert b.xref_get_key(head['id'],'A/Scope')==('name','/Column')


@pytest.mark.parametrize('mode',['gap','overlap','no_header','order','bad_scope','wrong_role'])
def test_invalid_table_structure_never_publishes_partial_tags(mode):
    base=table_pdf();entries=table_entries(candidates(base,[]))
    if mode=='gap':entries[-1]['column']=3
    if mode=='overlap':entries[-1]['column']=1
    if mode=='no_header':
        for e in entries:e['role']='TD'
    if mode=='order':entries[0],entries[1]=entries[1],entries[0]
    if mode=='bad_scope':entries[0]['scope']='evil'
    if mode=='wrong_role':entries[0]['role']='P'
    with pytest.raises(DocumentError):create(base,[],entries,reviewed=True)


def test_semantic_table_rectangular_merged_cell():
    base=table_pdf();entries=table_entries(candidates(base,[]));entries[0]['colspan']=2;entries[1]={'id':entries[1]['id'],'role':'P'}
    # A non-cell interrupts the table and must not silently merge regions.
    with pytest.raises(DocumentError,match='continua'):create(base,[],entries,reviewed=True)
    with f.open() as d:
        p=d.new_page()
        for x,y,text in [(40,50,'Header'),(40,100,'A'),(220,100,'B')]:p.insert_text((x,y),text)
        base=d.tobytes()
    info=candidates(base,[]);entries=[{'id':e['id'],'role':'TH' if i==0 else 'TD','table':1,'row':1 if i==0 else 2,'column':1 if i<2 else 2,'colspan':2 if i==0 else 1} for i,e in enumerate(info['entries'])]
    out,_=create(base,[],entries,reviewed=True)
    with f.open(stream=out) as d:
        node=next(r for r in model(out,[])['nodes'] if r['role']=='TH');assert d.xref_get_key(node['id'],'A/ColSpan')==('int','2')


@pytest.mark.parametrize('fmt,key,text,shown',[
 ('AFTime_FormatEx("HH:MM");','AFTime_KeystrokeEx("HH:MM");','23:59','23:59'),
 ('AFTime_Format(2);','AFTime_Keystroke(2);','09:15:32','09:15:32'),
 ('AFTime_Format(1);','AFTime_Keystroke(1);','1:05 PM','1:05 PM'),
 ('AFSpecial_Format(0);','AFSpecial_Keystroke(0);','00123','00123'),
 ('AFSpecial_Format(1);','AFSpecial_Keystroke(1);','001234567','00123-4567'),
 ('AFSpecial_Format(2);','AFSpecial_Keystroke(2);','0123456789','(012) 345-6789'),
 ('AFSpecial_Format(3);','AFSpecial_Keystroke(3);','001234567','001-23-4567'),
 ])
def test_time_special_forms_native_actions_and_appearance_preserved(fmt,key,text,shown):
    base=form_source(fmt,key,initial='');out=fill(base,text)
    with f.open(stream=base) as a,f.open(stream=out) as d:
        w=next(d[0].widgets());assert w.field_value==shown and shown in d[0].get_text();old=next(a[0].widgets());assert a.xref_get_key(old.xref,'AA')==d.xref_get_key(w.xref,'AA')
    out2=fill(out,shown)
    with f.open(stream=out2) as d:assert next(d[0].widgets()).field_value==shown


@pytest.mark.parametrize('fmt,key,text',[
 ('AFTime_Format(0);','AFTime_Keystroke(0);','24:00'),('AFTime_Format(1);','AFTime_Keystroke(1);','13:00 PM'),
 ('AFTime_Format(0);','AFTime_Keystroke(0);','1:00'),('AFTime_Format(2);','AFTime_Keystroke(2);','12:59:60'),
 ('AFSpecial_Format(0);','AFSpecial_Keystroke(0);','1234'),('AFSpecial_Format(2);','AFSpecial_Keystroke(2);','١٢٣٤٥٦٧٨٩٠'),
 ])
def test_invalid_time_special_values_are_atomic(fmt,key,text):
    with pytest.raises(DocumentError):fill(form_source(fmt,key,initial=''),text)


def comment_pdf():
    with f.open() as d:
        p=d.new_page();p.insert_text((40,40),'THREAD TEST');a=p.add_text_annot((50,100),'Root');a.set_info(title='Author');d.xref_set_key(a.xref,'NM','(root)');b=p.add_text_annot((80,120),'Reply');d.xref_set_key(b.xref,'NM','(reply)');d.xref_set_key(b.xref,'IRT',f'{a.xref} 0 R');d.xref_set_key(b.xref,'RT','/R');c=p.add_text_annot((90,140),'Accepted');d.xref_set_key(c.xref,'NM','(state)');d.xref_set_key(c.xref,'IRT',f'{b.xref} 0 R');d.xref_set_key(c.xref,'RT','/R');d.xref_set_key(c.xref,'StateModel','(Review)');d.xref_set_key(c.xref,'State','(Accepted)');return d.tobytes()


def blank_pdf():
    with f.open() as d:d.new_page();return d.tobytes()


def test_xfdf_threads_out_of_order_states_duplicate_import_and_roundtrip():
    data,report=xfdf.export(comment_pdf(),[],True,False);assert report['annotations']==3 and not report['skipped_annotations'];root=xfdf.parse(data);annots=root.find(xfdf.tag('annots'));annots[:]=list(reversed(list(annots)));data=E.tostring(root);base=blank_pdf();out,report=xfdf.import_data(base,[],data,True);assert report['annotations']==3
    with f.open(stream=out) as doc:
        page=doc[0];rows={a.info['id']:a.xref for a in page.annots()};assert doc.xref_get_key(rows['reply'],'IRT')==('xref',f'{rows["root"]} 0 R') and doc.xref_get_key(rows['state'],'IRT')==('xref',f'{rows["reply"]} 0 R');assert doc.xref_get_key(rows['state'],'State')==('string','Accepted')
    _,repeat=xfdf.import_data(out,[],data,True);assert repeat['duplicates']==3 and not repeat['annotations']
    again,report=xfdf.export(out,[],True,False);assert report['annotations']==3 and not report['skipped_annotations'];assert xfdf.parse(again).find('./'+xfdf.tag('annots')+'/'+xfdf.tag('text')+'[@name="state"]').get('statemodel')=='Review'


@pytest.mark.parametrize('mode',['cycle','orphan','cross_page','duplicate','bad_state','group'])
def test_xfdf_thread_invalid_graph_is_atomic(mode):
    data,_=xfdf.export(comment_pdf(),[],True,False);root=xfdf.parse(data);nodes=list(root.find(xfdf.tag('annots')))
    if mode=='cycle':nodes[0].set('inreplyto','state');nodes[0].set('replyType','R')
    if mode=='orphan':nodes[1].set('inreplyto','absent')
    if mode=='cross_page':nodes[1].set('page','1')
    if mode=='duplicate':nodes[1].set('name','root')
    if mode=='bad_state':nodes[2].set('state','Unknown')
    if mode=='group':nodes[1].set('replyType','Group')
    with pytest.raises(DocumentError):xfdf.import_data(blank_pdf(),[],E.tostring(root),True)


def test_borderless_table_real_text_suggested_grid_and_cells():
    base=table_pdf();report=extract(base,[],0,[20,20,330,170],mode='digital');assert report['grid_source']=='text_gaps' and report['detected_grid'];assert report['cells']==[['Name','Value'],['Alpha','100'],['Beta','200']] and report['review_required'] and not report['source_modified']


def test_borderless_no_table_from_single_column_or_uneven_rows():
    from backend.table_text_grid import infer
    box=f.Rect(0,0,400,200)
    assert infer([{'bbox':[20,20,60,30],'text':'One'},{'bbox':[20,60,60,70],'text':'Two'}],box) is None


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_orthogonal_trials_suggest_reviewable_orientation_and_keep_original(rotation):
    from backend.ocr_orientation import inspect as orientation
    from tests.test_scan_geometry import scan
    base=scan(rotation=rotation)
    with f.open(stream=base) as d:rect=f.Rect(60,90,550,300)*d[0].rotation_matrix
    report=orientation(base,[],0,[rect.x0,rect.y0,rect.width,rect.height],'eng')
    assert len(report['trials'])==4 and report['review_required'] and not report['source_modified']
    target=(360-rotation)%360;row=next(r for r in report['trials'] if r['orientation']==target);assert 'GEOMETRY TEST 12345' in row['sample'];assert report['orientation'] in [target,None]


@pytest.mark.parametrize('clip',[b'',b'40 -50 500 800 re W n ',b'40 -50 500 800 re W* n '])
def test_type3_dash_clipping_original_program_editable(clip):
    from tests.test_type3_fonts import type3_pdf,mutate
    from backend.styled_text import OriginalFont,inspect_styled,replace_styled
    from tests.test_cff_forms_mixed import box_for
    proc=b'600 0 0 -200 600 800 d1 q '+clip+b'12 w 1 J 1 j [8 3] 2 d 50 0 400 700 re S Q'
    base=mutate(type3_pdf(),None,None,proc=proc)
    with f.open(stream=base) as d:OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))
    box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=out) as d:assert 'CBA AB' in d[0].get_text() and any(d.xref_stream(x)==proc for x in range(1,d.xref_length()) if d.xref_is_stream(x))


@pytest.mark.parametrize('program',[b'[0 0] 0 d',b'[1 -1] 0 d',b'[2 1] -1 d',b'[2 /Bad] 0 d',b'W n',b'50 0 400 700 re W 2 w n'])
def test_invalid_type3_dash_or_clip_stays_protected(program):
    from backend.type3_fonts import validate
    with pytest.raises(DocumentError):validate(b'600 0 0 -200 600 800 d1 '+program,[0,-200,600,800])


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_text_only_shared_nested_forms_tagged_per_occurrence_without_rewriting_streams(rotation):
    with f.open() as src,f.open() as d:
        p=src.new_page(width=200,height=100);p.insert_text((20,40),'FORM CONTENT')
        p=d.new_page(width=500,height=400);p.show_pdf_page(f.Rect(20,20,220,120),src,0);p.show_pdf_page(f.Rect(250,170,450,270),src,0);p.set_rotation(rotation)
        d.new_page(width=500,height=400).show_pdf_page(f.Rect(20,20,220,120),src,0);base=d.tobytes()
    info=candidates(base,[]);assert len(info['entries'])==3 and all(e['form_occurrence'] for e in info['entries']);entries=[{'id':e['id'],'role':'H1' if i==0 else 'P'} for i,e in enumerate(info['entries'])];out,report=create(base,[],entries,reviewed=True);assert report['form_occurrences']==3
    flow=reading_preview(out,[],0)['blocks'];assert [r['roles'][-1] for r in flow]==['H1','P'] and not reading_preview(out,[],0)['untagged_blocks']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for p,q in zip(a,b):assert p.get_text()==q.get_text() and p.get_pixmap().samples==q.get_pixmap().samples
        streams=lambda doc:{doc.xref_stream(row[0]) for p in doc for row in p.get_xobjects()}
        assert streams(a)==streams(b)
    from backend.page_tools import split_pdf
    from zipfile import ZipFile
    with ZipFile(BytesIO(split_pdf(out,[],size=1))) as z:
        for name in z.namelist():assert reading_preview(z.read(name),[],0)['untagged_blocks']==0


def test_semantic_tables_can_be_split_without_leaking_other_page_nodes():
    with f.open(stream=table_pdf()) as source,f.open() as d:
        d.insert_pdf(source);d.insert_pdf(source);base=d.tobytes()
    info=candidates(base,[]);entries=[]
    for page in [0,1]:entries.extend(table_entries({'entries':[e for e in info['entries'] if e['page']==page]}))
    out,_=create(base,[],entries,reviewed=True)
    from backend.page_tools import split_pdf
    from zipfile import ZipFile
    with ZipFile(BytesIO(split_pdf(out,[],size=1))) as z:
        for name in z.namelist():
            rows=model(z.read(name),[])['nodes'];assert sum(r['role']=='Table' for r in rows)==1 and sum(r['role']=='TH' for r in rows)==2


def test_nested_lists_real_parentage_read_order_and_project():
    with f.open() as d:
        p=d.new_page()
        for i,text in enumerate(['Parent','Child','Grandchild','Sibling','Next parent']):p.insert_text((40+i*5,50+i*30),text)
        base=d.tobytes()
    info=candidates(base,[]);entries=[{'id':e['id'],'role':'LI','level':level} for e,level in zip(info['entries'],[1,2,3,2,1])];out,_=create(base,[],entries,reviewed=True)
    rows=model(out,[])['nodes'];assert sum(r['role']=='L' for r in rows)==3 and all(r['parent_valid'] for r in rows)
    flow=reading_preview(out,[],0)['blocks'];assert [r['roles'].count('L') for r in flow]==[1,2,3,2,1] and [r['text'] for r in flow]==[e['text'] for e in info['entries']]
    from backend.projects import build_project,read_project
    restored,_,_=read_project(build_project(out,[],{'name':'List.pdf'})[0]);assert restored==out
    entries[0]['level']=2
    with pytest.raises(DocumentError,match='nivel 1'):create(base,[],entries,reviewed=True)


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_paper_corner_suggestion_contrast_review_and_original_intact(rotation):
    from backend.scan_corners import inspect as scan_corners
    with f.open() as d:
        p=d.new_page(width=400,height=300);p.draw_rect(p.rect,fill=(.1,.1,.1));shape=p.new_shape();shape.draw_polyline([(60,50),(340,60),(320,250),(70,240),(60,50)]);shape.finish(fill=(1,1,1),color=(1,1,1));shape.commit();p.insert_text((100,120),'PAPER TEST');p.set_rotation(rotation);base=d.tobytes()
    with f.open(stream=base) as d:box=[0,0,d[0].rect.width,d[0].rect.height]
    result=scan_corners(base,[],0,box);assert result['quad'] and result['review_required'] and not result['source_modified']
    with f.open(stream=base) as d:
        actual={tuple(round(v/5)*5 for v in point) for point in result['quad']};expected={tuple(round(v/5)*5 for v in (f.Point(p)*d[0].rotation_matrix)) for p in [(60,50),(340,60),(320,250),(70,240)]};assert actual==expected


def test_white_on_white_and_irregular_scans_do_not_invent_corners():
    from backend.scan_corners import inspect as scan_corners
    base=table_pdf();assert scan_corners(base,[],0,[0,0,400,300])['quad'] is None
    with f.open() as d:
        p=d.new_page(width=400,height=300);p.draw_rect(p.rect,fill=(0,0,0));p.draw_circle((200,150),100,fill=(1,1,1));base=d.tobytes()
    assert scan_corners(base,[],0,[0,0,400,300])['quad'] is None


def test_cff2_real_blend_varstore_frozen_default_then_editable():
    from tests.test_static_cff2 import program
    from fontTools.ttLib import TTFont
    from fontTools.cffLib import VarStoreData
    from fontTools.varLib.builder import buildVarStore,buildVarRegionList,buildVarData
    from backend.styled_text import inspect_styled,replace_styled
    from tests.test_cff_forms_mixed import box_for
    font=TTFont(BytesIO(program(True)),recalcBBoxes=False);top=font['CFF2'].cff.topDictIndex[0];regions=buildVarRegionList([{'wght':(0,1,1)}],['wght']);top.VarStore=VarStoreData(otVarStore=buildVarStore(regions,[buildVarData([0],None,optimize=False)]));char=top.CharStrings['A'];char.decompile();char.program[0:1]=[char.program[0],20,1,'blend'];buffer=BytesIO();font.save(buffer)
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='VariableCFF2',fontbuffer=buffer.getvalue());p.insert_text((50,120),'ABC ABC',fontname='VariableCFF2',fontsize=20);base=d.tobytes()
    info=inspect(base,[]);assert info['fonts'][0]['format']=='CFF2';out,report=freeze(base,[],[{'xref':info['fonts'][0]['xref'],'axes':{'wght':400}}],True);assert report['appearance_verified']
    box=box_for(out,'ABC ABC');row=inspect_styled(out,[],0,box)['runs'][0];assert row['editable'],row['reason'];edited=replace_styled(out,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=edited) as d:assert 'CBA AB' in d[0].get_text()


def test_semantic_full_rowspan_has_placeholder_rows():
    with f.open() as d:p=d.new_page();p.insert_text((40,60),'Header spans three rows');base=d.tobytes()
    entry=candidates(base,[])['entries'][0];out,_=create(base,[],[{'id':entry['id'],'role':'TH','rowspan':3,'colspan':2}],reviewed=True)
    assert sum(r['role']=='TR' for r in model(out,[])['nodes'])==3


def test_new_api_actions_and_review_failures_preserve_original():
    from fastapi.testclient import TestClient
    from backend.app import app,document_path
    with TestClient(app) as client:
        base=variable_pdf();original=client.post('/api/documents',files={'file':('Variable.pdf',base,'application/pdf')}).json();url='/api/documents/'+original['id'];info=client.post(url+'/variable-fonts',json={}).json();row=info['fonts'][0]
        request={'fonts':[{'xref':row['xref'],'axes':{'wght':400}}]};bad=client.post(url+'/freeze-variable-fonts',json=request);assert bad.status_code==422
        result=client.post(url+'/freeze-variable-fonts',json={**request,'reviewed':True});assert result.status_code==200,result.text;assert result.json()['font_report']['appearance_verified'] and result.json()['id']!=original['id'];assert document_path(original['id']).read_bytes()==base
        for action in ['detect-orientation','detect-scan-corners']:
            result=client.post(url+'/'+action,json={'page':True,'box':[0,0,100,100]});assert result.status_code==422


@pytest.mark.parametrize('expression,expected',[
 ('this.getField("A").value + this.getField("B").value * 2','6.75'),
 ('(this.getField("A").value + this.getField("B").value) / 2','2'),
 ('-this.getField("A").value + 10.5','9.25'),
 ('this.getField("A").value / this.getField("A").value','1'),
 ])
def test_declarative_arithmetic_native_formulas_keep_actions_recalculate_dependents(expression,expected):
    from tests.test_native_calculations import source,values,fill as native_fill
    from backend.engine import export_pdf
    with f.open(stream=source()) as d:
        target=next(w for w in d[0].widgets() if w.field_name=='Total');d.xref_set_key(target.xref,'AA/C/JS',f.get_pdf_str('event.value = '+expression+';'));base=d.tobytes()
    out=export_pdf(base,[{'type':'form_recalculate','page':0}]);assert values(out)['Total']==expected
    with f.open(stream=base) as a,f.open(stream=out) as b:
        wa=next(w for w in a[0].widgets() if w.field_name=='Total');wb=next(w for w in b[0].widgets() if w.field_name=='Total');assert a.xref_get_key(wa.xref,'AA/C/JS')==b.xref_get_key(wb.xref,'AA/C/JS')
    changed=export_pdf(base,native_fill(base,'A','4'));assert values(changed)['Total']!=expected or 'value / this.getField' in expression


@pytest.mark.parametrize('expression',[
 'this.getField("A").value / 0','this.getField("A").value * 1000000000000',
 ])
def test_formula_numeric_failure_is_atomic(expression):
    from tests.test_native_calculations import source
    from backend.engine import export_pdf
    with f.open(stream=source()) as d:
        target=next(w for w in d[0].widgets() if w.field_name=='Total');d.xref_set_key(target.xref,'AA/C/JS',f.get_pdf_str('event.value='+expression+';'));base=d.tobytes()
    with pytest.raises(DocumentError):export_pdf(base,[{'type':'form_recalculate','page':0}])


@pytest.mark.parametrize('code',[
 'event.value=this.getField("A").value;app.alert(1);',
 'event.value=this.getField("A").value+F0;',
 'event.value=this.getField("A").value**2;',
 'event.value=this.getField("A").value//2;',
 'event.value=Math.max(this.getField("A").value,2);',
 'event.value=this.getField("A").value++1;',
 'event.value=this.getField("A").value.constructor;',
 'event.value=__import__("os").system("false");',
 'event.value=this.getField("A").value ? 1 : 2;',
 ])
def test_unknown_formula_scripts_are_never_executed(code):
    from backend.form_expressions import parse
    with pytest.raises(DocumentError):parse(code)
