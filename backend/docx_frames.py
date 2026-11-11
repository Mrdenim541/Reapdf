"""Physical Word pages distinct from Story's column-sized layout rectangles."""
from .engine import DocumentError
PAGE_BREAK_PREFIX='REAPDF_PHYSICAL_PAGE_BREAK_042_'


class Frames:
    def __init__(self,columns,starts=(),heights=None):
        self.columns=columns;self.starts=set(starts);self.logical=[];self.heights=heights or {}

    def locate(self,index):
        if index!=len(self.logical):raise DocumentError('La secuencia de columnas Word cambió durante la conversión.')
        count=len(self.columns['widths']);logical=self.logical[-1]+1 if self.logical else 0
        if index in self.starts and logical%count:logical+=count-logical%count
        self.logical.append(logical)
        return logical//count,logical

    def rect(self,logical,width,height,left,top,right,bottom,reserve=0):
        from .docx_columns import frame
        media,rect,ctm=frame(self.columns,logical,width,height,left,top,right,bottom,reserve)
        page=logical//len(self.columns['widths'])
        if page in self.heights:rect.y1=min(rect.y1,rect.y0+self.heights[page])
        return media,rect,ctm
