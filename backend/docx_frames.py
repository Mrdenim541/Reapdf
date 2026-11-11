"""Physical Word pages distinct from Story's column-sized layout rectangles."""
from .engine import DocumentError
PAGE_BREAK_PREFIX='REAPDF_PHYSICAL_PAGE_BREAK_042_'


class Frames:
    def __init__(self,columns,starts=()):
        self.columns=columns;self.starts=set(starts);self.logical=[]

    def locate(self,index):
        if index!=len(self.logical):raise DocumentError('La secuencia de columnas Word cambió durante la conversión.')
        count=len(self.columns['widths']);logical=self.logical[-1]+1 if self.logical else 0
        if index in self.starts and logical%count:logical+=count-logical%count
        self.logical.append(logical)
        return logical//count,logical

    def rect(self,logical,width,height,left,top,right,bottom,reserve=0):
        from .docx_columns import frame
        return frame(self.columns,logical,width,height,left,top,right,bottom,reserve)
