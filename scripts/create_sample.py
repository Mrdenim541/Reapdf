"""Documento sintético público para pruebas; no contiene información del usuario."""
from pathlib import Path
import sys
import pymupdf as fitz
path = Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/reapdf-demo.pdf')
doc=fitz.open()
p=doc.new_page(width=595,height=842)
p.draw_rect(fitz.Rect(0,0,595,12),color=None,fill=(.14,.41,.32))
p.insert_text((54,68),'REAPDF / DOCUMENTO DE PRUEBA',fontsize=10,color=(.23,.48,.38))
p.insert_text((54,126),'Un documento, nuevas posibilidades.',fontsize=23)
p.insert_text((54,165),'Prueba de lectura, texto y anotaciones.',fontsize=12,color=(.4,.46,.43))
p.draw_rect(fitz.Rect(44,218,551,290),fill=(.92,.94,.93),color=None)
p.insert_text((56,250),'Texto original',fontsize=18)
p.insert_text((56,273),'Selecciona Editar texto y cambia la linea anterior.',fontsize=11)
p.insert_text((54,340),'Un espacio para tus anotaciones',fontsize=17)
p.draw_rect(fitz.Rect(54,365,541,670),color=(.8,.85,.82),width=.7)
p.insert_text((54,735),'El original se conserva. Los cambios se exportan en otra copia.',fontsize=10)
p=doc.new_page(width=595,height=842)
p.insert_text((54,80),'Segunda pagina',fontsize=24)
p.insert_text((54,120),'Esta pagina permite comprobar la navegacion y la conservacion del contenido.',fontsize=11)
doc.set_toc([[1,'Inicio',1],[1,'Segunda pagina',2]])
doc.save(path);doc.close();print(path)
