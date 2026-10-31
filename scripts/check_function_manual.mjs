// Audit the user manual against the actual tool catalog; no feature-completion claim.
import {readFileSync} from 'node:fs';
import {tools} from '../web/src/tool-catalog.js';
const guide=JSON.parse(readFileSync(new URL('../docs/funciones-uso.json',import.meta.url),'utf8')),markdown=readFileSync(new URL('../docs/MANUAL_DE_FUNCIONES.md',import.meta.url),'utf8'),entries=guide.functions;
if(!Array.isArray(entries)||entries.length!==tools.length||new Set(entries.map(e=>e.id)).size!==tools.length)throw new Error('Manual and tool counts do not match.');
for(const tool of tools){const e=entries.find(e=>e.id===tool.id);if(!e||e.label!==tool.label||e.area!==tool.area||!Array.isArray(e.steps)||e.steps.length<2||e.steps.some(s=>typeof s!=='string'||!s.trim())||!e.expected?.trim()||!e.limits?.trim()||!markdown.includes(`id="funcion-${tool.id}"`))throw new Error(`Manual missing or stale: ${tool.id}`);}
if(guide.user_review!=='after_final_technical_delivery')throw new Error('Personal acceptance must remain after technical delivery.');
console.log(`PASS: manual covers all ${tools.length} current tools with access, steps, expected result and limits; personal acceptance remains last. This does not certify feature completion.`);
