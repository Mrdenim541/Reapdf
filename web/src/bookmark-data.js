export function branchEnd(items,index) {
  let end=index+1;while(end<items.length&&items[end].level>items[index].level)end++;return end;
}
export function previousSibling(items,index) {
  const level=items[index].level;
  for(let i=index-1;i>=0;i--){if(items[i].level===level)return i;if(items[i].level<level)break;}return -1;
}
export function moveBranch(items,index,direction) {
  const end=branchEnd(items,index),previous=previousSibling(items,index);
  if(direction<0){if(previous<0)return {items,index};return {items:[...items.slice(0,previous),...items.slice(index,end),...items.slice(previous,index),...items.slice(end)],index:previous};}
  if(end>=items.length||items[end].level!==items[index].level)return {items,index};
  const nextEnd=branchEnd(items,end);
  return {items:[...items.slice(0,index),...items.slice(end,nextEnd),...items.slice(index,end),...items.slice(nextEnd)],index:index+nextEnd-end};
}
export function indentBranch(items,index,direction) {
  const end=branchEnd(items,index),branch=items.slice(index,end);
  if(direction>0){if(previousSibling(items,index)<0||branch.some(item=>item.level>=10))return {items,index};return {items:items.map((item,i)=>i>=index&&i<end?{...item,level:item.level+1}:item),index};}
  if(items[index].level===1)return {items,index};
  let parent=index-1;while(parent>=0&&items[parent].level>=items[index].level)parent--;
  const parentEnd=branchEnd(items,parent),shifted=branch.map(item=>({...item,level:item.level-1}));
  return {items:[...items.slice(0,index),...items.slice(end,parentEnd),...shifted,...items.slice(parentEnd)],index:parentEnd-branch.length};
}
export function validateBookmarks(items,count) {
  let previous=0;
  if(items.length>2000)return 'Máximo 2000 marcadores.';
  for(const item of items){
    if(!Number.isInteger(item.level)||item.level<1||item.level>10||item.level>previous+1)return 'Revisa los niveles del índice.';
    if(!item.title.trim()||item.title.trim().length>300||/[\x00-\x1f\x7f]/.test(item.title))return 'Cada marcador necesita un título válido.';
    if(!Number.isInteger(item.page)||item.page<0||item.page>=count)return 'Revisa las páginas de destino.';
    previous=item.level;
  }
  return '';
}
