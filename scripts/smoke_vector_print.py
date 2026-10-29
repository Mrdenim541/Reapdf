"""Virtual printer: genuine vector output and tiled large-format fallback."""
import tempfile
from pathlib import Path
import pymupdf as f
from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtGui import QPageSize,QPainter
from PySide6.QtCore import QSizeF,QRectF
from portable.native_print import paint_page
app=QApplication([]);root=Path(tempfile.mkdtemp(prefix='reapdf-vector-print-'))

def printer(path,width,height):
    p=QPrinter(QPrinter.PrinterMode.HighResolution);p.setResolution(150);p.setOutputFormat(QPrinter.OutputFormat.PdfFormat);p.setOutputFileName(str(path));p.setFullPage(True);p.setPageSize(QPageSize(QSizeF(width,height),QPageSize.Unit.Point));return p

with f.open() as source:
    page=source.new_page(width=400,height=500);page.insert_text((40,80),'VECTOR TEXT',fontsize=20);page.draw_rect(f.Rect(40,100,180,220),color=(.2,.3,.5))
    path=root/'vector.pdf';p=printer(path,400,500);paint=QPainter(p);area=p.pageRect(QPrinter.Unit.DevicePixel)
    method=paint_page(page,paint,QRectF(area),300);paint.end();assert method=='vector',method
    with f.open(path) as result:assert not result[0].get_images() and len(result[0].get_drawings())>5
with f.open() as source:
    page=source.new_page(width=2384,height=3370);page.draw_rect(page.rect,color=(0,.4,.8),fill=(0,.4,.8))
    path=root/'large-raster.pdf';p=printer(path,2384,3370);paint=QPainter(p);area=p.pageRect(QPrinter.Unit.DevicePixel)
    method=paint_page(page,paint,QRectF(area),150,allow_vector=False);paint.end();assert method=='raster_tiles'
    with f.open(path) as result:
        assert len(result[0].get_images())>1
        pix=result[0].get_pixmap(matrix=f.Matrix(.1,.1));assert all(abs(a-b)<=4 for a,b in zip(pix.pixel(74,74),(0,102,204)))
        for x in [72,73,74,75,146,147,148]:assert all(abs(a-b)<=4 for a,b in zip(pix.pixel(x,100),(0,102,204))),('seam',x,pix.pixel(x,100))
print('PASS: virtual PDF printer retains vector paths with no page bitmap; A0 fallback prints bounded tiles without sampled seams. No physical printer/Windows acceptance.')
