"""Vista raster del PDF a la densidad solicitada, con presupuesto de memoria."""
import math
import pymupdf as fitz
from .engine import DocumentError,finite

MAX_PIXELS=24_000_000
MAX_EDGE=8192


def render_page(page,requested=1.5):
    if not finite(requested) or not .1 <= requested <= 16:
        raise DocumentError('La escala de visualización debe estar entre 0.1 y 16.')
    width,height=page.rect.width,page.rect.height
    if not finite(width) or not finite(height) or width<=0 or height<=0:
        raise DocumentError('La página no tiene dimensiones válidas para mostrarse.')
    # Descontar un pixel de redondeo para no superar los límites al rasterizar.
    scale=min(requested,8,(MAX_EDGE-1)/max(width,height),math.sqrt((MAX_PIXELS-2*MAX_EDGE)/(width*height)))
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
    return pix.tobytes('png'),{'X-Render-Scale':str(scale),'X-Render-Limited':'true' if scale<requested-.001 else 'false',
                             'X-Render-Width':str(pix.width),'X-Render-Height':str(pix.height)}
