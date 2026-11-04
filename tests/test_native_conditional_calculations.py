from decimal import Decimal
import pytest,pymupdf as f
from backend.form_expressions import parse,evaluate
from backend.engine import DocumentError,export_pdf
from backend.forms import form_model
from tests.test_native_calculations import source


@pytest.mark.parametrize('expr,a,expected',[
 ('F ? 1 : 2',0,2),('F ? 1 : 2',5,1),
 ('F>0 ? F*2 : 0',5,10),('F>0 ? F*2 : 0',-5,0),
 ('F===2 ? 7 : 9',2,7),('F!==2 ? 7 : 9',2,9),
 ('F>=1 && F<=5 ? 100 : 200',3,100),('F<1 || F>5 ? 100 : 200',3,200),
 ('F>0 ? (F>10 ? 1 : 2) : 3',11,1),('F>0 ? 1 : F<0 ? 2 : 3',0,3),
 ('Number(F)*2',2,4),('F==0 ? 0 : 1/F',0,0),
 ('F!=0 && 1/F>0 ? 10 : 20',0,20),('F>0 ? Math.round(F*100)/100 : Math.abs(F)',2.675,2.68)])
def test_conditional_numeric_formulas_are_data_with_short_circuit(expr,a,expected):
    rule=parse('event.value='+expr.replace('F','this.getField("A").value')+';')
    assert evaluate(rule['expression'],[Decimal(str(a))])==Decimal(str(expected))


@pytest.mark.parametrize('expr',['F?1','F?:2','F?1:','F?app.alert(1):0','F?1:"text"','F>0','F && 1','Number.constructor(F)','Number(F,2)','F?1:2;app.alert(1)','F?1:2,3','F<3<5?1:0','F>>1?1:0','F&1?1:0','F=2?1:0'])
def test_general_javascript_and_ambiguous_numeric_expressions_are_rejected(expr):
    with pytest.raises(DocumentError):parse('event.value='+expr.replace('F','this.getField("A").value')+';')


def test_conditional_action_survives_save_and_recalculates_native_field():
    code='event.value = Number(this.getField("A").value)>0 ? this.getField("A").value*2 : 0;'
    with f.open(stream=source()) as d:
        total=next(w for w in d[0].widgets() if w.field_name=='Total');d.xref_set_key(total.xref,'AA/C/JS',f.get_pdf_str(code));base=d.tobytes();a=next(v for v in form_model(d)['fields'] if v['name']=='A')
    out=export_pdf(base,[{'type':'form_fill','page':0,'values':[{'page':a['page'],'xref':a['xref'],'value':'35'}]}])
    with f.open(stream=out) as d:
        total=next(w for w in d[0].widgets() if w.field_name=='Total');assert total.field_value=='70' and d.xref_get_key(total.xref,'AA/C/JS')==('string',code)
