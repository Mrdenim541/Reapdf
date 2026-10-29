// Exercise the same area selection a user makes before opening a tool.
import {expect} from '@playwright/test';
import {areas,tools} from '../web/src/tool-catalog.js';
export async function openTool(page,label){
 // Opening a new PDF resets its area. Wait for that adoption before choosing one.
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled({timeout:20000});
 const item=tools.find(t=>t.label===label);if(!item)throw new Error(`Unknown tool: ${label}`);
 const area=areas.find(a=>a.id===item.area);
 const search=page.getByLabel('Buscar herramienta',{exact:true});if(await search.isVisible())await search.fill('');
 const favorites=page.getByRole('button',{name:/^Mis favoritos/});if(await favorites.getAttribute('aria-pressed')==='true')await favorites.click();
 const tab=page.getByRole('tab',{name:area.label,exact:true});
 if(await tab.getAttribute('aria-selected')!=='true')await tab.click();
 const button=page.getByLabel('Herramientas PDF').getByRole('button',{name:label,exact:true});const section=page.locator('.tool-section').filter({has:button});if(await section.count()&&await section.getAttribute('open')===null)await section.locator('summary').click();await expect(button).toBeVisible();await button.click();
}
