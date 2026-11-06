import pytest
import pymupdf as f
from scripts.create_shared_choice_sample import create
from backend.forms import form_model
from backend.engine import export_pdf,DocumentError
from backend.form_data import flatten_form,export_form_data,import_form_data


def rows(data):
    with f.open(stream=data) as d:return form_model(d)['fields']


def fill(data,value):
    row=rows(data)[1];assert row['editable'],row['reason']
    return export_pdf(data,[{'type':'form_fill','page':0,'values':[{'page':row['page'],'xref':row['xref'],'value':value}]}])


@pytest.mark.parametrize('kind',['combo','list'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_shared_choice_syncs_all_appearances_and_keeps_value_only_on_owner(kind,rotation,crop):
    base=create(kind,rotation,crop);out=fill(base,'LIM');r=rows(out);assert len(r)==2 and all(v['editable'] and v['value']=='LIM' and v['group_size']==2 for v in r)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[2].get_pixmap().samples==b[2].get_pixmap().samples
        assert b.xref_get_key(r[0]['group'],'V')==('string','LIM') and b.xref_get_key(r[0]['group'],'I')==('array','[1]')
        for row in r:
            assert b.xref_get_key(row['xref'],'V')[0]=='null' and b.xref_get_key(row['xref'],'I')[0]=='null'
            assert b[row['page']].rotation==rotation
            assert 'Lima' in b[row['page']].get_text()
            assert a[row['page']].load_widget(next(a[row['page']].widgets()).xref).rect==b[row['page']].load_widget(row['xref']).rect
    cleared=fill(out,'');assert all(r['value']=='' for r in rows(cleared))
    changed=fill(cleared,'CUS');assert all(r['value']=='CUS' for r in rows(changed))
    with f.open(stream=flatten_form(changed,[])) as d:assert all(not list(p.widgets() or []) for p in d)


@pytest.mark.parametrize('bad',['options','labels','index','multi_index','local_value','readonly','mixed_kind'])
def test_ambiguous_shared_choice_blocks_the_whole_group(bad):
    with f.open(stream=create()) as d:
        row=form_model(d)['fields'][1];x=row['xref']
        if bad in ['options','labels']:d.xref_set_key(x,'Opt','[[(BOG)(Other)] [(NEW)(Different)]]' if bad=='options' else '[[(BOG)(Other)] [(LIM)(Lima)] [(CUS)(Cusco)]]')
        elif bad=='index':d.xref_set_key(x,'I','[2]')
        elif bad=='multi_index':d.xref_set_key(x,'I','[0 1]')
        elif bad=='local_value':d.xref_set_key(x,'V','(CUS)')
        else:d.xref_set_key(x,'Ff','131073' if bad=='readonly' else '0')
        data=d.tobytes()
    r=rows(data);assert all(not v['editable'] for v in r)
    with pytest.raises(DocumentError):export_pdf(data,[{'type':'form_fill','page':0,'values':[{'page':r[0]['page'],'xref':r[0]['xref'],'value':'LIM'}]}])


def test_conflicting_shared_choice_values_are_atomic():
    base=create();r=rows(base)
    with pytest.raises(DocumentError,match='contradictorios'):export_pdf(base,[{'type':'form_fill','page':0,'values':[{'page':v['page'],'xref':v['xref'],'value':name} for v,name in zip(r,['LIM','CUS'])]}])
    assert all(v['value']=='BOG' for v in rows(base))


def test_shared_choice_data_roundtrip_accepts_one_widget_and_synchronizes_both():
    base=create();data=export_form_data(base,[]);assert len(data['fields'])==2
    data['fields']=data['fields'][:1];data['fields'][0]['value']='CUS';ops=import_form_data(base,[],data);out=export_pdf(base,ops);assert all(r['value']=='CUS' for r in rows(out))
    again=export_form_data(base,ops);assert [r['value'] for r in again['fields']]==['CUS','CUS']
