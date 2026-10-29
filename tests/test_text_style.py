import pymupdf as f
import pytest
from backend.engine import export_pdf,spans,DocumentError
from backend.text_style import FONT_OPTIONS


def source(font='helv',size=18,baseline=100,neighbor=None):
    with f.open() as d:
        p=d.new_page(width=400,height=500)
        p.draw_rect(f.Rect(30,40,350,130),color=None,fill=(.9,.9,.9))
        p.insert_text((50,baseline),'Texto original largo',fontname=font,fontsize=size,color=(.2,.3,.4))
        if neighbor:p.insert_text((50,neighbor),'Otra linea cercana',fontsize=12)
        d.new_page().insert_text((50,80),'Pagina intacta')
        return d.tobytes()


def operation(data,**changes):
    with f.open(stream=data,filetype='pdf') as d:span=spans(d[0])[0]
    return {'type':'text','page':0,'span_id':span['id'],'text':'Nuevo',**changes}


@pytest.mark.parametrize('font,name',FONT_OPTIONS)
def test_twelve_base_font_variants_can_be_edited_and_style_defaults_preserved(font,name):
    data=source(font)
    with f.open(stream=data,filetype='pdf') as before,f.open(stream=export_pdf(data,[operation(data)]),filetype='pdf') as after:
        span=spans(after[0])[0]
        assert span['font']==name
        assert span['size']==18 and span['text']=='Nuevo'
        assert span['color']==spans(before[0])[0]['color']
        assert after[1].get_pixmap().samples==before[1].get_pixmap().samples


@pytest.mark.parametrize('font,name',FONT_OPTIONS)
def test_change_font_size_color_and_keep_baseline(font,name):
    data=source()
    with f.open(stream=data,filetype='pdf') as before:
        original=spans(before[0])[0]
        output=export_pdf(data,[operation(data,font=font,size=24,color=[1,0,0])])
        with f.open(stream=output,filetype='pdf') as after:
            current=spans(after[0])[0]
            assert current['font']==name and current['size']==24 and current['color']==0xff0000
            assert current['origin']==original['origin']
            assert 'original' not in after[0].get_text()
            assert after[1].get_pixmap().samples==before[1].get_pixmap().samples
            # La zona alejada de ambos textos conserva el fondo, sin parche blanco.
            assert after[0].get_pixmap().pixel(330,70)==before[0].get_pixmap().pixel(330,70)


@pytest.mark.parametrize('changes',[
 {'font':'Calibri'},{'font':None},{'size':True},{'size':5},{'size':145},{'size':float('nan')},
 {'color':[1,0]},{'color':[0,0,2]},{'color':[False,0,0]}, {'text':'Texto que claramente no cabe en la caja con muchos caracteres'},
])
def test_invalid_text_style_rejected(changes):
    data=source()
    with pytest.raises(DocumentError):export_pdf(data,[operation(data,**changes)])


def test_growth_into_neighbor_and_off_page_rejected():
    data=source(neighbor=60)
    with pytest.raises(DocumentError,match='cruza'):export_pdf(data,[operation(data,size=50,text='A')])
    data=source(baseline=25)
    with pytest.raises(DocumentError,match='sale'):export_pdf(data,[operation(data,size=60,text='A')])


def test_smaller_font_can_fit_longer_text_without_expanding_original_width():
    data=source()
    text='Texto nuevo algo mas largo'
    with pytest.raises(DocumentError):export_pdf(data,[operation(data,text=text,size=18)])
    with f.open(stream=export_pdf(data,[operation(data,text=text,size=10)]),filetype='pdf') as d:
        assert text in d[0].get_text()


def test_two_grown_lines_must_not_overlap_each_other():
    with f.open() as d:
        p=d.new_page(width=400,height=500)
        p.insert_text((50,100),'Fuente pequena suficientemente larga',fontsize=6)
        p.insert_text((50,140),'Otra linea pequena suficientemente larga',fontsize=6)
        data=d.tobytes();lines=spans(p)
    operations=[{'type':'text','page':0,'span_id':line['id'],'text':'A','size':size} for line,size in zip(lines,[24,35])]
    # Cada cambio aislado cabe, pero juntos deben rechazarse.
    for op in operations:export_pdf(data,[op])
    with pytest.raises(DocumentError,match='Dos textos'):export_pdf(data,operations)


def test_text_style_api_font_options_and_export():
    from fastapi.testclient import TestClient
    from backend.app import app
    data=source()
    with TestClient(app) as c:
        identity=c.post('/api/documents',files={'file':('style.pdf',data)}).json()['id']
        detail=c.get(f'/api/documents/{identity}/pages/0').json()
        assert len(detail['text_fonts'])==12
        op=operation(data,font='cobo',size=20,color=[0,.5,1])
        response=c.post(f'/api/documents/{identity}/export',json={'operations':[op]})
        assert response.status_code==200
        with f.open(stream=response.content,filetype='pdf') as d:
            line=spans(d[0])[0];assert line['font']=='Courier-Bold' and line['size']==20
            assert line['color']==0x007fff or line['color']==0x0080ff
