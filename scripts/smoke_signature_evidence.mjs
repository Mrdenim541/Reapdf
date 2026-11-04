import {chromium,expect} from '@playwright/test';
import {openTool} from './smoke-tool-navigation.mjs';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const work=mkdtempSync(join(tmpdir(),'reapdf-dss-ui-')),python=process.env.REAPDF_TEST_PYTHON||'.venv/bin/python',base=process.env.REAPDF_TEST_URL||'http://127.0.0.1:8000';
execFileSync(python,['-c',`from pathlib import Path
import sys
from tests.test_affine_perspective_revocation import pki
from tests.signature_samples import document
from backend.digital_signatures import sign_document
p=Path(sys.argv[1]);identity,root,proof=pki();p.joinpath('signed.pdf').write_bytes(sign_document(document(),[],identity,'',{}));p.joinpath('root.pem').write_bytes(root);p.joinpath('proof.crl').write_bytes(proof)`,work]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'}),errors=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1080}});page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(20000);
 await page.goto(base);await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(join(work,'signed.pdf'));await page.getByAltText('Página 1 del documento').waitFor();
 await openTool(page,'Verificar firmas digitales');await page.getByLabel('Certificados de confianza para verificar').setInputFiles(join(work,'root.pem'));
 await page.getByText('Revocación con evidencias locales (opcional)',{exact:true}).click();await page.getByLabel('Evidencias locales de revocación').setInputFiles(join(work,'proof.crl'));
 await page.getByRole('button',{name:'Comprobar firmas',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('Cadena y revocación aceptadas con evidencia local');
 await page.getByText('Conservar evidencias en una copia',{exact:true}).click();const download=page.waitForEvent('download');await page.getByRole('button',{name:'Conservar evidencias y guardar copia',exact:true}).click();await (await download).saveAs(join(work,'copy.pdf'));
 await page.getByRole('button',{name:'Cerrar',exact:true}).click();await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(join(work,'copy.pdf'));await openTool(page,'Verificar firmas digitales');
 await page.getByLabel('Usar evidencias DSS incorporadas').check();await page.getByRole('button',{name:'Comprobar firmas',exact:true}).click();await expect(page.getByRole('dialog')).not.toContainText('Cadena y revocación aceptadas con evidencia local');
 await page.getByLabel('Certificados de confianza para verificar').setInputFiles(join(work,'root.pem'));await page.getByRole('button',{name:'Comprobar firmas',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('Cadena y revocación aceptadas con evidencia local');
 execFileSync(python,['-c',`from pathlib import Path
import sys
from backend.digital_signatures import verify_signatures
p=Path(sys.argv[1]);original=p.joinpath('signed.pdf').read_bytes();copy=p.joinpath('copy.pdf').read_bytes();assert copy.startswith(original);r=verify_signatures(copy,[],p.joinpath('root.pem').read_bytes(),use_embedded=True);assert r['signatures'][0]['modification_level']=='LTA_UPDATES' and r['signatures'][0]['revocation']['status']=='accepted_offline'`,work]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: real browser DSS save/reopen, explicit embedded-evidence opt-in, no automatic trust and original revision preserved.');
}finally{await browser.close();rmSync(work,{recursive:true,force:true});}
