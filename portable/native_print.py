"""Print the prepared PDF, rather than the HTML editor surrounding it."""
import base64,math
import pymupdf as fitz


def print_pdf(encoded,parent):
    from PySide6.QtPrintSupport import QPrinter,QPrintDialog
    from PySide6.QtWidgets import QDialog
    from PySide6.QtGui import QPainter,QImage
    from PySide6.QtCore import QRectF
    if not isinstance(encoded,str) or len(encoded)>84*1024*1024:raise ValueError('El PDF supera el límite de impresión.')
    data=base64.b64decode(encoded,validate=True)
    with fitz.open(stream=data,filetype='pdf') as doc:
        if doc.needs_pass or not 1<=len(doc)<=500 or not doc.permissions&fitz.PDF_PERM_PRINT:raise ValueError('El PDF no permite esta impresión.')
        max_dpi=300 if doc.permissions&fitz.PDF_PERM_PRINT_HQ else 150
        for page in doc:
            if not all(math.isfinite(v) and 0<v<=3000 for v in [page.rect.width,page.rect.height]):raise ValueError('La página supera el tamaño de impresión admitido.')
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
                page=doc[number];rect=page.rect
                if rect.width<=0 or rect.height<=0:raise ValueError('La página no tiene un tamaño imprimible.')
                dpi=min(max_dpi,72*math.sqrt(16_000_000/(rect.width*rect.height)))
                image=QImage.fromData(page.get_pixmap(dpi=max(1,int(dpi)),alpha=False).tobytes('png'))
                if image.isNull():raise ValueError('No se pudo representar una página.')
                area=printer.pageRect(QPrinter.Unit.DevicePixel)
                scale=min(area.width()/image.width(),area.height()/image.height())
                width=image.width()*scale;height=image.height()*scale
                target=QRectF(area.x()+(area.width()-width)/2,area.y()+(area.height()-height)/2,width,height)
                painter.drawImage(target,image)
        finally:painter.end()
        return 'printed'
