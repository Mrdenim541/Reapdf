"""Directed acceptance against an explicit user PDF, through the actual Qt UI.

Does not write the input, bypass edit permissions or call editing APIs directly.
Outputs a test copy, screenshots and a private report in --output-dir.
"""
import argparse
from collections import Counter
import hashlib
import json
import time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window

parser=argparse.ArgumentParser()
parser.add_argument('pdf',type=Path)
parser.add_argument('--text',required=True)
parser.add_argument('--replacement',required=True)
parser.add_argument('--output-dir',required=True,type=Path)
args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
source=args.pdf.resolve();original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
output=args.output_dir/('PRUEBA_NO_USAR-'+source.name)
if output.resolve()==source:raise ValueError('The test copy must not overwrite its source')
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([]);QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(source));window.resize(1500,1000);window.show()
report={'source_sha256':original_hash,'host':'Reapdf Qt Linux offscreen','original_untouched':False,'events':[]}

def js(script):
    wrapped='(()=>{try{return eval('+json.dumps(script)+');}catch(e){return {__check_error:String(e)};}})()'
    values=[];loop=QEventLoop();window.page.runJavaScript(wrapped,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
    if not values:raise AssertionError('JavaScript did not respond')
    if isinstance(values[0],dict) and '__check_error' in values[0]:raise AssertionError(values[0]['__check_error']+' in '+script)
    return values[0]

def wait(script):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)

def button(name):
    return '[...(document.querySelector("dialog[open]")||document).querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(name)+')'

def click(name):
    wait(f'!!{button(name)} && !{button(name)}.disabled');js(f'{button(name)}.dispatchEvent(new MouseEvent("click",{{bubbles:true}}))')

def field(label):
    return 'document.querySelector('+json.dumps('[aria-label='+json.dumps(label,ensure_ascii=False)+']')+')'

def fill(label,value,select=False):
    selector='[aria-label='+json.dumps(label,ensure_ascii=False)+']'
    js('(()=>{const e=document.querySelector('+json.dumps(selector)+');Object.getOwnPropertyDescriptor('+( 'HTMLSelectElement' if select else 'HTMLTextAreaElement' if label=='Texto del bloque' else 'HTMLInputElement')+'.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event(' + json.dumps('change' if select else 'input') + ',{bubbles:true}));})()')

def tool(label):
    js('[...document.querySelectorAll("[role=tab]")].find(e=>e.textContent.trim()==="Editar").click()')
    selector=json.dumps('[aria-label='+json.dumps(label,ensure_ascii=False)+']')
    wait('!!document.querySelector('+selector+')')
    js('(()=>{const b=document.querySelector('+selector+');const section=b.closest("details");if(section)section.open=true;b.click();})()')

def screenshot(name):
    QTest.qWait(300);window.grab().save(str(args.output_dir/name))

try:
    wait('document.querySelector(".text-layer")?.textContent.includes('+json.dumps(args.text)+')')
    tool('Buscar y reemplazar');wait('!!'+field('Texto a buscar'));fill('Texto a buscar',args.text);click('Buscar coincidencias')
    wait('document.querySelector("dialog[open] [role=status]")?.textContent.includes("coincidencias")')
    search=js('document.querySelector("dialog[open]").innerText')
    report['events'].append({'stage':'find_original_font','ui_result':search})
    screenshot('01-busqueda-qt.png');click('Cancelar')
    tool('Editar imágenes del PDF');wait(field('Imagen existente')+'?.options.length>0')
    images=[];count=int(js(field('Imagen existente')+'.options.length'))
    for index in range(count):
        fill('Imagen existente',str(index),True);QTest.qWait(100)
        images.append({'index':index+1,'status':js('document.querySelector("dialog[open] [role=status]")?.textContent||"Editable"'),'apply_disabled':js(button('Aplicar imagen editada')+'.disabled')})
    report['events'].append({'stage':'existing_images','images':images});screenshot('02-imagenes-qt.png');click('Cancelar')
    tool('Editar texto');click('Editar bloque: '+args.text)
    wait('!!'+field('Modo de edición del bloque'))
    wait('!!document.querySelector("dialog[open] [role=alert]") || !!'+field('Texto del fragmento 1'))
    report['events'].append({'stage':'original_style_editor','ui_result':js('document.querySelector("dialog[open]").innerText')})
    click('Usar una fuente incluida')
    wait(field('Texto del bloque')+'?.value==='+json.dumps(args.text))
    report['events'].append({'stage':'reflow','font_notice':'Explicit paragraph replacement with bundled font; does not retain the original font program for this block.'})
    fill('Texto del bloque',args.replacement);click('Vista previa del bloque')
    wait(f'!{button("Aplicar párrafo")}.disabled')
    screenshot('03-vista-previa-qt.png');click('Aplicar párrafo')
    wait('!document.querySelector("dialog[open]") && document.querySelector(".text-layer")?.textContent.includes('+json.dumps(args.replacement)+')')
    # Undo/redo the actual version, using the same toolbar as the user.
    js('[...document.querySelectorAll("button")].find(e=>(e.getAttribute("aria-label")||e.textContent).includes("Deshacer")).click()')
    wait('document.querySelector(".text-layer")?.textContent.includes('+json.dumps(args.text)+')')
    js('[...document.querySelectorAll("button")].find(e=>(e.getAttribute("aria-label")||e.textContent).includes("Rehacer")).click()')
    wait('document.querySelector(".text-layer")?.textContent.includes('+json.dumps(args.replacement)+')')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_action.trigger()
    wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    screenshot('04-resultado-qt.png')
    with f.open(source) as before,f.open(output) as after:
        assert len(before)==len(after)==1
        expected=Counter(before[0].get_text().split());expected.subtract(Counter(args.text.split()));expected.update(Counter(args.replacement.split()))
        assert +expected==Counter(after[0].get_text().split()),'Other extracted text changed'
        original_images=[(i['digest'].hex(),i['bbox']) for i in before[0].get_image_info(xrefs=True)]
        saved_images=[(i['digest'].hex(),i['bbox']) for i in after[0].get_image_info(xrefs=True)]
        assert original_images==saved_images,'Images moved or changed'
        assert len(before[0].get_drawings())==len(after[0].get_drawings()),'Vector drawing count changed'
        targets=before[0].search_for(args.text)
        if len(targets)==1:
            rect=targets[0]+(-4,-4,4,4)
            a,b=before[0].get_pixmap(alpha=False),after[0].get_pixmap(alpha=False)
            assert (a.width,a.height,a.n)==(b.width,b.height,b.n)
            aa,bb=a.samples,b.samples
            for y in range(a.height):
                left=y*a.stride;right=left+a.stride
                if y<rect.y0 or y>rect.y1:assert aa[left:right]==bb[left:right],'Pixels outside edited region changed'
                else:
                    x0=max(0,int(rect.x0))*a.n;x1=min(a.width,int(rect.x1)+1)*a.n
                    assert aa[left:left+x0]==bb[left:left+x0] and aa[left+x1:right]==bb[left+x1:right],'Pixels outside edited region changed'
            report['pixels_outside_edited_region_unchanged']=True
        after[0].get_pixmap(matrix=f.Matrix(2,2)).save(str(args.output_dir/'resultado-150porciento.png'))
        report['events'].append({'stage':'saved_copy','text_changed':True,'undo_redo':True,'all_other_extracted_words_unchanged':True,'image_count_unchanged':len(saved_images),'image_digests_and_positions_unchanged':True,'drawing_count_unchanged':len(after[0].get_drawings()),'output':output.name})
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original_hash
    report['original_untouched']=True;report['result']='passed_with_original_font_and_image_editing_limitations'
    print('PASS: actual Qt UI searched original, inspected images, replaced a block with bundled font, undo/redo, native save and reopened PDF integrity checks.')
finally:
    (args.output_dir/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    window.allow_close=True;window.close();app.processEvents()
