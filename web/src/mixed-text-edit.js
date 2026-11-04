// Apply one textarea edit, keeping unchanged characters in their original runs.
// Insertions inherit the preceding character's style (first style at the start).
export function editMixedText(runs,text){
 const old=runs.flatMap((run,owner)=>Array.from(run.text,char=>({char,owner}))),next=Array.from(text);
 let prefix=0,suffix=0;
 while(prefix<old.length&&prefix<next.length&&old[prefix].char===next[prefix])prefix++;
 while(suffix<old.length-prefix&&suffix<next.length-prefix&&old[old.length-1-suffix].char===next[next.length-1-suffix])suffix++;
 const owner=old[Math.max(0,prefix-1)]?.owner??0,parts=runs.map(()=>[]);
 for(let i=0;i<prefix;i++)parts[old[i].owner].push(old[i].char);
 if(parts[owner])parts[owner].push(...next.slice(prefix,next.length-suffix));
 for(let i=old.length-suffix;i<old.length;i++)parts[old[i].owner].push(old[i].char);
 return runs.map((run,i)=>({...run,text:parts[i].join('')}));
}

// Browser undo may group multiple input events. Match its restored text to
// the corresponding immutable run snapshot so undo restores formatting too.
export function editMixedHistory(state,text,inputType,explicitRuns){
 const current=state.entries[state.index];
 if(inputType==='historyUndo'||inputType==='historyRedo'){
  const step=inputType==='historyUndo'?-1:1;
  for(let i=state.index+step;i>=0&&i<state.entries.length;i+=step){
   if(state.entries[i].map(r=>r.text).join('')===text)return {...state,index:i};
  }
  return state;
 }
 if(current.map(r=>r.text).join('')===text&&!explicitRuns)return state;
 const next=explicitRuns||editMixedText(current,text),entries=[...state.entries.slice(0,state.index+1),next].slice(-128);
 return {entries,index:entries.length-1};
}
