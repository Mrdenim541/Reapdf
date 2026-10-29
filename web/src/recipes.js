// Recipes contain only declarative options. Passwords never enter this model.
export const recipeStorageKey='reapdf.recipes.v1';
export const stepLabels={metadata:'Propiedades del documento',watermark:'Marca de agua',numbering:'Numeración de páginas',compress:'Reducir imágenes',optimize:'Optimizar estructura',flatten:'Aplanar campos',docx:'Convertir a Word editable',text:'Extraer texto UTF-8',protect:'Proteger con contraseña'};
export const defaultStep=type=>({
 metadata:{type,values:{title:'',author:'',subject:'',keywords:'',creator:''},remove_xml:false},
 watermark:{type,text:'COPIA',size:36,opacity:.15,angle:45,color:[.35,.35,.35]},
 numbering:{type,template:'{numero} / {total}',start:1,size:10},compress:{type,dpi:150,quality:85},
 docx:{type,keep_lines:true,include_images:false,include_tables:false,include_links:false},optimize:{type},flatten:{type},text:{type},protect:{type,allow_copy:true,allow_print:true},
}[type]);
export function newRecipe(name='Mi receta',steps=['optimize']){return {format:'reapdf-recipe',version:1,name,filename:'{name}-{recipe}',steps:steps.map(defaultStep)};}
export const presetRecipes=[newRecipe('Copia ligera',['compress','optimize']),newRecipe('Copia para revisión',['watermark','numbering','optimize']),newRecipe('Formulario final',['flatten','numbering','optimize']),newRecipe('Texto para trabajar',['text'])];
export function moveStep(recipe,index,direction){const to=index+direction;if(to<0||to>=recipe.steps.length)return recipe;const steps=[...recipe.steps];[steps[index],steps[to]]=[steps[to],steps[index]];return {...recipe,steps};}
export function parseRecipeFile(text){if(typeof text!=='string'||new TextEncoder().encode(text).length>65536)throw new Error('La receta supera 64 KB.');const value=JSON.parse(text);if(!value||value.format!=='reapdf-recipe'||value.version!==1||!Array.isArray(value.steps))throw new Error('Archivo de receta no compatible.');return value;}
export function loadRecipes(storage){try{const values=JSON.parse(storage.getItem(recipeStorageKey)||'[]');return Array.isArray(values)?values.slice(0,20).filter(v=>v?.format==='reapdf-recipe'&&v.version===1&&Array.isArray(v.steps)):[];}catch{return [];}}
export function saveRecipe(storage,recipe,previous){const next=[recipe,...previous.filter(v=>v.name!==recipe.name)].slice(0,20);storage.setItem(recipeStorageKey,JSON.stringify(next));return next;}
