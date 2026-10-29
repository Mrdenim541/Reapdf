import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
export async function runCompressionSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const fixture=join(tmpdir(),'reapdf-compression-source.pdf');execFileSync(python,['-c',`from pathlib import Path;import sys;from tests.test_compression import source;Path(sys.argv[1]).write_bytes(source())`,fixture]);
 await p.goto(baseUrl);await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(fixture);await openTool(p,'Reducir imágenes del PDF');await expect(p.getByRole('button',{name:'Descargar PDF comprimido',exact:true})).toBeDisabled();await p.getByRole('button',{name:'Comprobar compresión',exact:true}).click();await expect(p.getByAltText('Resultado de compresión')).toBeVisible();await expect(p.getByRole('dialog')).toContainText('1 imágenes reducidas');await p.getByLabel('Aceptar pérdida de detalle por compresión',{exact:true}).check();await expect(p.getByRole('button',{name:'Descargar PDF comprimido',exact:true})).toBeEnabled();
 await p.getByLabel('Calidad de compresión',{exact:true}).selectOption('90');await expect(p.getByRole('button',{name:'Descargar PDF comprimido',exact:true})).toBeDisabled();await p.getByRole('button',{name:'Comprobar compresión',exact:true}).click();await expect(p.getByRole('button',{name:'Descargar PDF comprimido',exact:true})).toBeEnabled();await p.screenshot({path:join(tmpdir(),'reapdf-compresion-034.png')});
 let download=p.waitForEvent('download');await p.getByRole('button',{name:'Descargar PDF comprimido',exact:true}).click();const out=join(tmpdir(),'reapdf-compression-result.pdf');await(await download).saveAs(out);await expect(p.getByRole('button',{name:'Descargar informe de la copia comprimida',exact:true})).toBeVisible();download=p.waitForEvent('download');await p.getByRole('button',{name:'Descargar informe de la copia comprimida',exact:true}).click();const report=join(tmpdir(),'reapdf-compression-result.json');await(await download).saveAs(report);const data=JSON.parse(readFileSync(report,'utf8'));assert.equal(data.sha256,createHash('sha256').update(readFileSync(out)).digest('hex'));assert.equal(data.after_bytes,readFileSync(out).length);assert.ok(data.saved_bytes>0);assert.equal(data.quality,90);assert.equal(data.preview,undefined);
 execFileSync(python,['-c',`import sys,pymupdf as f,subprocess
with f.open(sys.argv[1]) as d:assert d[0].get_images()[0][2:4]==(450,600);assert 'Texto conservado' in d[0].get_text()
assert 'Texto conservado' in subprocess.check_output(['pdftotext',sys.argv[1],'-']).decode()`,out]);
 await p.getByRole('button',{name:'Cerrar',exact:true}).click();await expect(p.locator('.document-bar')).toContainText('0 cambios');assert.ok(readFileSync(out).length<readFileSync(fixture).length/2);
 const cmyk=join(tmpdir(),'reapdf-cmyk-nested-source.pdf');execFileSync(python,['-c',`from pathlib import Path;import sys,pymupdf as f;from tests.test_compression import cmyk_source
with f.open(stream=cmyk_source()) as original,f.open() as middle,f.open() as d:
 p=middle.new_page(width=400,height=500);p.show_pdf_page(p.rect,original,0)
 p=d.new_page(width=400,height=500);p.show_pdf_page(p.rect,middle,0);Path(sys.argv[1]).write_bytes(d.tobytes())`,cmyk]);
 await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(cmyk);await openTool(p,'Reducir imágenes del PDF');await p.getByRole('button',{name:'Comprobar compresión',exact:true}).click();await expect(p.getByAltText('Resultado de compresión')).toBeVisible();await expect(p.getByRole('dialog')).toContainText('1 imágenes reducidas');await p.getByLabel('Aceptar pérdida de detalle por compresión',{exact:true}).check();await p.screenshot({path:join(tmpdir(),'reapdf-compresion-cmyk-035.png')});
 download=p.waitForEvent('download');await p.getByRole('button',{name:'Descargar PDF comprimido',exact:true}).click();const cmOut=join(tmpdir(),'reapdf-cmyk-nested-compressed.pdf');await(await download).saveAs(cmOut);
 execFileSync(python,['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as a,f.open(sys.argv[2]) as b:
 assert b[0].get_xobjects();assert b[0].get_text()==a[0].get_text();image=b[0].get_images()[0];assert image[2:4]==(300,300);assert f.Pixmap(b,image[0]).n==4
 clip=f.Rect(42,122,182,262);x=a[0].get_pixmap(clip=clip).samples;y=b[0].get_pixmap(clip=clip).samples;assert sum(abs(i-j) for i,j in zip(x,y))/len(x)<4`,cmyk,cmOut]);
 await context.close();
}
