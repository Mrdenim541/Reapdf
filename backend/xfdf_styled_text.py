"""Literal Base-14 Latin free-text appearances with real bold/italic metrics."""
import pymupdf as f
from .engine import DocumentError

STYLES={
 'Helvetica':'helv','Helvetica-Bold':'hebo','Helvetica-Oblique':'heit','Helvetica-BoldOblique':'hebi',
 'Times-Roman':'tiro','Times-Bold':'tibo','Times-Italic':'tiit','Times-BoldItalic':'tibi',
 'Courier':'cour','Courier-Bold':'cobo','Courier-Oblique':'coit','Courier-BoldOblique':'cobi',
}
REGULAR={'Helvetica','Times-Roman','Courier'}
ALIASES={'Helv':'Helvetica','HeBo':'Helvetica-Bold','HeOb':'Helvetica-Oblique','HeBO':'Helvetica-BoldOblique','TiRo':'Times-Roman','TiBo':'Times-Bold','TiIt':'Times-Italic','TiBI':'Times-BoldItalic','Cour':'Courier','CoBo':'Courier-Bold','CoOb':'Courier-Oblique','CoBO':'Courier-BoldOblique'}
FONTS={**ALIASES,**{k:k for k in STYLES},**{v:k for k,v in STYLES.items()}}


def apply(doc,a,settings,rect,text,width,opacity):
    if settings['font'] in REGULAR:return
    try:text.encode('cp1252')
    except UnicodeError as exc:raise DocumentError('Las variantes de texto libre admiten caracteres latinos WinAnsi; no se sustituye una fuente Unicode.') from exc
    # MuPDF expands FreeText /Rect by the border during update(). Keep the
    # exchanged outer rectangle stable before installing our own appearance.
    a.set_rect(rect)
    w,h=rect.width,rect.height;padding=max(2,width+1);font=STYLES[settings['font']]
    if min(w,h)<=2*padding:raise DocumentError('La anotación no tiene espacio suficiente para su borde y texto.')
    with f.open() as temp:
        page=temp.new_page(width=w,height=h)
        if settings['fill'] is not None:page.draw_rect(page.rect,color=None,fill=settings['fill'])
        if width:
            # The border remains separate from the text geometry.
            dash='['+' '.join(str(v) for v in settings['dashes'])+'] 0' if settings['dashes'] else None
            page.draw_rect(page.rect+(width/2,width/2,-width/2,-width/2),color=settings.get('border_color',(0,0,0)),width=width,dashes=dash)
        result=page.insert_textbox(page.rect+(padding,padding,-padding,-padding),text,fontname=font,fontsize=settings['size'],color=settings['text_color'],align=settings['align'],rotate=settings['rotation'])
        if result<-.001:raise DocumentError('El texto libre con su estilo real no cabe en la anotación. Amplía su caja o reduce el texto/tamaño.')
        n=f.mupdf;native=f._as_pdf_document(doc);source=f._as_pdf_document(temp);resources=n.pdf_dict_gets(n.pdf_load_object(source,page.xref),'Resources');copied=n.pdf_graft_object(native,resources)
        x=doc.get_new_xref();doc.update_object(x,f'<< /Type /XObject /Subtype /Form /BBox [0 0 {w} {h}] >>');obj=n.pdf_load_object(native,x);n.pdf_dict_puts(obj,'Resources',copied)
        data=page.read_contents()
        if opacity<1:
            states=n.pdf_dict_gets(copied,'ExtGState')
            if n.pdf_is_null(states):states=n.pdf_new_dict(native,1);n.pdf_dict_puts(copied,'ExtGState',states)
            state=n.pdf_new_dict(native,2);n.pdf_dict_puts(state,'ca',n.pdf_new_real(opacity));n.pdf_dict_puts(state,'CA',n.pdf_new_real(opacity));n.pdf_dict_puts(states,'ReapdfAlpha',state);data=b'q /ReapdfAlpha gs\n'+data+b'\nQ'
        doc.update_stream(x,data);doc.xref_set_key(a.xref,'AP',f'<< /N {x} 0 R >>')
        color=' '.join(str(v) for v in settings['text_color']);doc.xref_set_key(a.xref,'DA',f.get_pdf_str(f'{color} rg /{font} {settings["size"]} Tf'));doc.xref_set_key(a.xref,'Q',str(settings['align']));doc.xref_set_key(a.xref,'Rotate',str(settings['rotation']))
        # DA resource lookup stays valid both in AP and in annotation resources.
        ann=n.pdf_load_object(native,a.xref);n.pdf_dict_puts(ann,'Resources',copied)
