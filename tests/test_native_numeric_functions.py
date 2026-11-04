from decimal import Decimal
import pytest,pymupdf as f
from backend.form_expressions import parse,evaluate
from backend.engine import DocumentError
from backend.forms import form_model
from backend.engine import export_pdf
from tests.test_native_calculations import source


@pytest.mark.parametrize('expression,value,result',[
 ('Math.abs(F)',-3,'3'),('Math.round(F)',-1.5,'-1'),('Math.round(F)',1.5,'2'),('Math.floor(F)',-1.2,'-2'),('Math.ceil(F)',-1.2,'-1'),('Math.min(F, 2, 3)',5,'2'),('Math.max(1,Math.abs(F))',-5,'5'),('F % 3',-5,'-2'),('Math.round(F*100)/100',2.675,'2.68')])
def test_native_numeric_helpers_use_bounded_arithmetic(expression,value,result):
    m=parse('event.value='+expression.replace('F','this.getField("A").value')+';');assert evaluate(m['expression'],[Decimal(str(value))])==Decimal(result)


@pytest.mark.parametrize('expression',['Math.pow(F,2)','Math.random(F)','Math.abs(F,2)','Math.min()','Math.abs.constructor(F)','Math["abs"](F)','Math.max(F,...[1,2])','Math.max(F, x=2)','Math.abs(F);app.alert(1)','Math.abs(this.getField("A").value.value)'])
def test_other_calls_and_instructions_remain_protected(expression):
    with pytest.raises(DocumentError):parse('event.value='+expression.replace('F','this.getField("A").value')+';')


def test_modulo_zero_is_atomic_error():
    m=parse('event.value=this.getField("A").value%0;')
    with pytest.raises(DocumentError,match='cero'):evaluate(m['expression'],[Decimal(1)])


def test_native_pdf_field_recalculates_and_retains_its_action():
    with f.open(stream=source()) as d:
        target=next(w for w in d[0].widgets() if w.field_name=='Total');d.xref_set_key(target.xref,'AA/C/JS',f.get_pdf_str('event.value=Math.max(this.getField("A").value,this.getField("B").value);'));base=d.tobytes()
    with f.open(stream=base) as d:
        m=form_model(d);assert m['native_calculations'];a=next(v for v in m['fields'] if v['name']=='A');old=d.xref_get_key(next(w for w in d[0].widgets() if w.field_name=='Total').xref,'AA/C/JS')
    out=export_pdf(base,[{'type':'form_fill','page':0,'values':[{'page':a['page'],'xref':a['xref'],'value':'35'}]}])
    with f.open(stream=out) as d:
        w=next(w for w in d[0].widgets() if w.field_name=='Total');assert w.field_value=='35' and d.xref_get_key(w.xref,'AA/C/JS')==old
