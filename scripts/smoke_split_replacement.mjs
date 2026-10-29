import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-split-')),source=join(root,'original.pdf'),out=join(root,'result.pdf');
execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
d=f.open();p=d.new_page();p.insert_font(fontname='Simple',fontfile='resources/fonts/DejaVuSans.ttf',set_simple=True)
p.insert_text((40,80),'MM',fontsize=18)
x=40+f.get_text_length('MM',fontsize=18)
p.insert_text((x,80),'MM',fontname='Simple',fontsize=18,color=(.1,.3,.5))
p=d.new_page()
for i in range(25):p.insert_text((40,40+i*25),'MMMM',fontsize=18)
d.save(sys.argv[1])`,source]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
 const page=await browser.newPage();page.on('dialog',d=>d.accept());const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');await page.getByLabel('Archivo PDF').setInputFiles(source);await openTool(page,'Buscar y reemplazar');
 await page.getByLabel('Texto a buscar').fill('MMMM');await page.getByLabel('Reemplazar por',{exact:true}).fill('NNNN');await page.getByLabel('Ámbito de búsqueda').selectOption('document');
 await page.getByRole('button',{name:'Buscar coincidencias',exact:true}).click();await expect(page.getByRole('dialog').getByRole('status')).toContainText('26 coincidencias');
 await expect(page.getByRole('dialog').getByText('Varios estilos',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Seleccionar todas compatibles',exact:true}).click();await expect(page.getByRole('dialog').getByRole('status')).toContainText('27 fragmentos');
 await page.getByRole('button',{name:'Preparar vista previa',exact:true}).click();await expect(page.getByRole('button',{name:'Aplicar reemplazos',exact:true})).toBeEnabled();
 await expect(page.getByAltText('Reemplazo en página 2')).toBeVisible();
 await page.screenshot({path:join(tmpdir(),'reapdf-split-replacement.png')});
 await page.getByRole('button',{name:'Aplicar reemplazos',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('.text-layer')).toContainText('NN');
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('MM');
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('NN');
 const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(out);
 execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f,hashlib
with f.open(sys.argv[1]) as a,f.open(sys.argv[2]) as b:
 spans=[s for block in b[0].get_text('dict',flags=f.TEXTFLAGS_TEXT|f.TEXT_INHIBIT_SPACES)['blocks'] for line in block.get('lines',[]) for s in line['spans']]
 assert ''.join(s['text'] for s in sorted(spans,key=lambda s:s['origin'][0]))=='NNNN'
 assert len({s['font'] for s in spans})==2 and len({s['color'] for s in spans})==2
 programs=lambda d:{hashlib.sha256(d.extract_font(i[0])[3]).hexdigest() for i in d[0].get_fonts() if i[1]=='ttf'}
 assert programs(a)==programs(b) and b[1].get_text().split()==['NNNN']*25`,source,out]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: mixed base/WinAnsi split match, 26 replacements/27 runs, preview, undo/redo and exported styles/program.');
}finally{await browser.close();}
