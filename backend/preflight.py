"""Local print diagnostics, distinct from an ISO/PDF-X conformance validator."""
import math
from .engine import open_pdf,export_pdf,DocumentError

BASE14={'Helvetica','Helvetica-Bold','Helvetica-Oblique','Helvetica-BoldOblique','Times-Roman','Times-Bold','Times-Italic','Times-BoldItalic','Courier','Courier-Bold','Courier-Oblique','Courier-BoldOblique','Symbol','ZapfDingbats'}


def inspect(base,ops,min_dpi=150,profile="general"):
    from .press_preflight import PROFILES
    if profile!="general" and profile not in PROFILES:raise DocumentError("Perfil de impresión no válido.")
    if type(min_dpi) is not int or min_dpi not in [72,150,200,300,600]:raise DocumentError('Elige un umbral de 72, 150, 200, 300 o 600 ppp.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if len(doc)>100 or doc.xref_length()>50000:raise DocumentError('La inspección admite hasta 100 páginas y 50000 objetos.')
        pages=[];issues=[];fonts={};image_count=0;objects=0
        for page in doc:
            rows=[]
            for image in page.get_image_info(xrefs=True):
                image_count+=1
                if image_count>2000:raise DocumentError('Hasta 2000 imágenes por inspección.')
                if min(image['width'],image['height'])<=1:continue
                a,b,c,d,_,_=image['transform'];w=math.hypot(a,b);h=math.hypot(c,d)
                if min(w,h)<.001:continue
                xdpi=image['width']*72/w;ydpi=image['height']*72/h
                rows.append({'xref':image['xref'],'rect':list(image['bbox']),'pixels':[image['width'],image['height']],'dpi':[round(xdpi,1),round(ydpi,1)],'channels':image['colorspace'],'alpha':bool(image.get('has-mask'))})
                if min(xdpi,ydpi)<min_dpi:issues.append({'page':page.number,'code':'image_resolution','message':f'Imagen de {min(xdpi,ydpi):.1f} ppp efectivos; umbral {min_dpi}.','severity':'warning'})
            for item in page.get_fonts(full=True):
                if item[0] not in fonts:
                    fonts[item[0]]={'name':item[3],'type':item[2],'embedded':item[2]=='Type3' or item[1] not in ['n/a','none',''],'pages':[]}
                    if not fonts[item[0]]['embedded']:issues.append({'page':page.number,'code':'base_font' if item[3] in BASE14 else 'font_not_embedded','message':'Fuente sin programa incrustado: '+item[3],'severity':'info' if item[3] in BASE14 else 'warning'})
                fonts[item[0]]['pages'].append(page.number)
                if len(fonts)>500:raise DocumentError('Hasta 500 recursos de fuente por inspección.')
            drawings=page.get_drawings();traces=page.get_texttrace();objects+=len(drawings)+sum(len(t['chars']) for t in traces)
            if objects>1_000_000:raise DocumentError('Demasiado contenido para esta inspección.')
            from .preflight_colors import inspect as inspect_colors
            color_info=inspect_colors(doc,page);colors=set(color_info['colors'])
            if color_info['spot_colorants']:issues.append({'page':page.number,'code':'spot_colorants','message':'Colorantes declarados: '+', '.join(color_info['spot_colorants'])+'. Comprueba sus separaciones en imprenta.','severity':'info'})
            if color_info['overprint_states']:issues.append({'page':page.number,'code':'overprint','message':'Hay estados aplicados con sobreimpresión activada; revisa su resultado en una prueba de impresión.','severity':'warning'})
            if color_info['limited']:issues.append({'page':page.number,'code':'color_analysis_incomplete','message':'Análisis de color parcial: '+' '.join(color_info['reasons'] or ['Presupuesto de estados agotado.']),'severity':'warning'})
            boxes={key:list(getattr(page,key)) for key in ['mediabox','cropbox','trimbox','bleedbox']}
            if not page.bleedbox.contains(page.trimbox):issues.append({'page':page.number,'code':'bleed_trim','message':'La caja de sangrado no contiene la caja de corte.','severity':'warning'})
            if list(page.widgets() or []):issues.append({'page':page.number,'code':'interactive_fields','message':'La página contiene campos interactivos; revisa su apariencia antes de imprimir.','severity':'info'})
            pages.append({'page':page.number,'size':[page.rect.width,page.rect.height],'rotation':page.rotation,'boxes':boxes,'images':rows,'vector_colors':sorted(colors),'color_analysis':color_info})
            if len(issues)>2000:raise DocumentError('Más de 2000 hallazgos; divide el documento.')
        report={'pages':pages,'fonts':list(fonts.values()),'issues':issues,'min_dpi':min_dpi,'layers':len(doc.get_ocgs()),'signed':doc.get_sigflags()>0,'scope':'Diagnóstico de resolución efectiva, fuentes, cajas y contenido. Incluye espacios declarados en Forms, nombres de colorantes y estados de sobreimpresión aplicados. No evalúa funciones de tinta ni certifica PDF/X, cobertura de tinta o fidelidad de imprenta.'}

        if profile!='general':
            from .press_preflight import evaluate
            report['press_profile']=evaluate(doc,report,profile)
        return report
