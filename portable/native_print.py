"""Print the prepared PDF with verified SVG vectors or bounded raster tiles."""
import base64,math
import xml.etree.ElementTree as E
import pymupdf as fitz


def vector_renderer(page):
    """Use Qt SVG only for a bounded subset and a matching rendered sample.

    Unsupported SVG features fall back to raster; no external SVG resources are
    fetched. This is a rendering check, not proof of perfect print equivalence.
    """
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtGui import QImage,QPainter
    from PySide6.QtCore import QByteArray,QRectF,Qt
    try:
        data=page.get_svg_image(text_as_path=True).encode()
        if len(data)>8*1024*1024:return None
        root=E.fromstring(data);nodes=list(root.iter())
        if len(nodes)>15000:return None
        allowed={'svg','defs','g','path','use','image','rect'}
        for node in nodes:
            if node.tag.split('}')[-1] not in allowed:return None
            for key,value in node.attrib.items():
                if key.split('}')[-1]=='href' and not value.startswith(('#','data:image/')):return None
        renderer=QSvgRenderer(QByteArray(data))
        if not renderer.isValid():return None
        scale=min(1,256/max(page.rect.width,page.rect.height));pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,annots=True)
        reference=QImage.fromData(pix.tobytes('png'));sample=QImage(reference.size(),QImage.Format.Format_RGB32);sample.fill(Qt.GlobalColor.white)
        painter=QPainter(sample);renderer.render(painter,QRectF(0,0,sample.width(),sample.height()));painter.end()
        diff=QImage(sample);painter=QPainter(diff);painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Difference);painter.drawImage(0,0,reference);painter.end()
        reduced=diff.scaled(64,64,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGB888)
        mean=sum(bytes(reduced.constBits()))/(64*64*3*255)
        if mean>.008:return None
        return renderer
    except (ImportError,ValueError,RuntimeError,E.ParseError):return None


def paint_page(page,painter,target,max_dpi=300,allow_vector=True):
    from PySide6.QtGui import QImage
    from PySide6.QtCore import QRectF
    if allow_vector:
        renderer=vector_renderer(page)
        if renderer is not None:renderer.render(painter,target);return 'vector'
    rect=page.rect
    # Match destination device pixels, up to the requested source resolution.
    # Tiles retain that resolution without allocating the entire large page.
    scale=min(max_dpi/72,target.width()/rect.width,target.height()/rect.height)
    tile_points=1536/max(scale,.01)
    for y in range(math.ceil(rect.height/tile_points)):
        for x in range(math.ceil(rect.width/tile_points)):
            clip=fitz.Rect(x*tile_points,y*tile_points,min(rect.width,(x+1)*tile_points),min(rect.height,(y+1)*tile_points))
            pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),clip=clip,alpha=False)
            image=QImage.fromData(pix.tobytes('png'))
            if image.isNull():raise ValueError('No se pudo representar una región de impresión.')
            # MuPDF rounds the raster origin to whole device pixels. Use that
            # actual origin/extent so adjoining tiles have no artificial seam.
            px=fitz.Rect(pix.x/scale,pix.y/scale,(pix.x+pix.width)/scale,(pix.y+pix.height)/scale)&rect
            painter.save();tile=QRectF(target.x()+clip.x0/rect.width*target.width(),target.y()+clip.y0/rect.height*target.height(),clip.width/rect.width*target.width(),clip.height/rect.height*target.height());painter.setClipRect(tile)
            painter.drawImage(QRectF(target.x()+px.x0/rect.width*target.width(),target.y()+px.y0/rect.height*target.height(),px.width/rect.width*target.width(),px.height/rect.height*target.height()),image);painter.restore()
    return 'raster_tiles'


def print_pdf(encoded,parent):
    from PySide6.QtPrintSupport import QPrinter,QPrintDialog
    from PySide6.QtWidgets import QDialog
    from PySide6.QtGui import QPainter
    from PySide6.QtCore import QRectF
    if not isinstance(encoded,str) or len(encoded)>84*1024*1024:raise ValueError('El PDF supera el límite de impresión.')
    data=base64.b64decode(encoded,validate=True)
    with fitz.open(stream=data,filetype='pdf') as doc:
        if doc.needs_pass or not 1<=len(doc)<=500 or not doc.permissions&fitz.PDF_PERM_PRINT:raise ValueError('El PDF no permite esta impresión.')
        high=bool(doc.permissions&fitz.PDF_PERM_PRINT_HQ);max_dpi=300 if high else 150
        for page in doc:
            if not all(math.isfinite(v) and 0<v<=6000 for v in [page.rect.width,page.rect.height]):raise ValueError('La página supera el tamaño de impresión admitido.')
        printer=QPrinter(QPrinter.PrinterMode.HighResolution);printer.setResolution(300)
        printer.setDocName('Reapdf');printer.setFromTo(1,len(doc))
        dialog=QPrintDialog(printer,parent);dialog.setMinMax(1,len(doc))
        if dialog.exec()!=QDialog.DialogCode.Accepted:return 'cancelled'
        first=max(1,printer.fromPage() or 1);last=min(len(doc),printer.toPage() or len(doc))
        pages=list(range(first-1,last))
        if printer.pageOrder()==QPrinter.PageOrder.LastPageFirst:pages.reverse()
        if not pages:raise ValueError('El rango de impresión está vacío.')
        painter=QPainter()
        if not painter.begin(printer):raise ValueError('No se pudo iniciar la impresora.')
        try:
            for index,number in enumerate(pages):
                if index and not printer.newPage():raise ValueError('La impresora no aceptó otra página.')
                page=doc[number];rect=page.rect;area=printer.pageRect(QPrinter.Unit.DevicePixel)
                scale=min(area.width()/rect.width,area.height()/rect.height)
                width=rect.width*scale;height=rect.height*scale
                target=QRectF(area.x()+(area.width()-width)/2,area.y()+(area.height()-height)/2,width,height)
                paint_page(page,painter,target,max_dpi,allow_vector=high)
        finally:painter.end()
        return 'printed'
