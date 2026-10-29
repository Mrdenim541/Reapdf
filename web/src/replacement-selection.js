// Count actual PDF runs, including a match that crosses multiple styles.
export function replacementSelection(matches, ids) {
  const chosen = new Set(ids), runs = new Set();
  let count = 0;
  for (const m of matches) {
    if (!chosen.has(m.id)) continue;
    count++;
    for (const p of m.parts || []) {
      if (p.end > m.start && p.start < m.end) runs.add(`${m.page}:${p.id}`);
    }
  }
  return {count, runs: runs.size, valid: count <= 100 && runs.size <= 100};
}

export function selectCompatibleBatch(matches) {
  const ids = [], runs = new Set();
  for (const m of matches) {
    if (!m.editable) continue;
    const next = new Set(runs);
    for (const p of m.parts || []) {
      if (p.end > m.start && p.start < m.end) next.add(`${m.page}:${p.id}`);
    }
    if (ids.length >= 100 || next.size > 100) continue;
    ids.push(m.id);
    for (const key of next) runs.add(key);
  }
  return ids;
}
