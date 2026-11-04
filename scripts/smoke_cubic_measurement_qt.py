"""Real Qt mouse snapping to cubic/cubic crossings and native PDF save/reopen."""
import json,tempfile,time,math
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_cubic_intersections import pdf
from tests.test_measurement_paths import CAL
from backend.measurements import measure,model
from backend.measurement_geometry import targets
root=Path(tempfile.mkdtemp(prefix='reapdf-cubic-qt-'));original=root/'Curves.pdf';output=root/'Measured.pdf';base=measure(pdf(),[],0,'distance',CAL['points'],CAL);original.write_bytes(base)
hits=[r['point'] for r in targets(base,[],0)['points'] if r['source']=='curve_curve_intersection'];assert len(hits)==2
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1700,1150);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
    if not values:raise AssertionError('Qt did not respond')
    return values[0]
def wait(script):
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)
def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'
def click(label):
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')'
    wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.dispatchEvent(new MouseEvent("click",{bubbles:true}))')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Curves.pdf")')
    click('Documentos');wait(field('Medir planos')+'?.disabled===false');js('(()=>{const b='+field('Medir planos')+';b.closest("details").open=true;b.click();})()')
    wait('!!document.querySelector(".field-placement img") && document.querySelector(".field-placement img").complete')
    wait('document.body.innerText.includes("Escala calibrada")');assert js(field('Ajustar a geometría del PDF')+'.checked')
    # The actual mouse is deliberately offset from both crossings. The UI must
    # use the original-curve target instead of the cursor/polyline projection.
    for i,hit in enumerate(hits):
        svg=field('Puntos de medición sobre el plano');js(svg+'.scrollIntoView({block:"center",inline:"center"})');QTest.qWait(200)
        point=json.loads(js('JSON.stringify((()=>{const s='+svg+';const p=s.createSVGPoint();p.x='+str(hit[0]+.5)+';p.y='+str(hit[1]+.4)+';const q=p.matrixTransform(s.getScreenCTM());return {x:q.x,y:q.y};})())'))
        QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(point['x']),round(point['y'])));wait('document.querySelectorAll(".measurement-vertex").length=='+str(i+1))
    click('Calcular medición');wait('!!document.querySelector(".measurement-result")');click('Guardar medición en PDF');wait('!document.querySelector("dialog[open]")')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    rows=model(output.read_bytes(),[],0)['measurements'];assert any(all(math.dist(p,q)<.0001 for p,q in zip(r['points'],hits)) for r in rows)
    with f.open(stream=base) as a,f.open(output) as b:assert a[0].get_pixmap(annots=False).samples==b[0].get_pixmap(annots=False).samples
    assert original.read_bytes()==base
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Measured.pdf")')
    print('PASS: actual Qt mouse offset from two original cubic/cubic crossings snaps to both precise targets, calculates calibrated distance, saves natively and reopens; underlying plan and source unchanged.')
finally:window.allow_close=True;window.close();app.processEvents()
