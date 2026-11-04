export function parsePageRange(value, count) {
  if (!Number.isInteger(count) || count < 1 || count > 500) throw new Error('Cantidad de páginas no válida.');
  if (typeof value !== 'string' || !value.trim()) throw new Error('Indica las páginas que quieres seleccionar.');
  if (value.length > 2000) throw new Error('La selección supera 2000 caracteres.');
  const result = [], seen = new Set();
  for (const part of value.split(',')) {
    const match = part.trim().match(/^(\d+)(?:\s*-\s*(\d+)(?:\s*\/\s*(\d+))?)?$/);
    if (!match) throw new Error('Usa páginas o rangos por comas: 1-3, 5. Para un salto: 1-9/2 selecciona 1, 3, 5, 7, 9.');
    const start = Number(match[1]), end = Number(match[2] ?? match[1]), step = Number(match[3] ?? 1);
    if (!Number.isSafeInteger(step) || step < 1 || step > count) throw new Error(`El salto debe ser un entero entre 1 y ${count}.`);
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end > count || start > end)
      throw new Error(`Usa páginas entre 1 y ${count}, con rangos de menor a mayor.`);
    for (let number = start; number <= end; number += step) {
      if (seen.has(number)) throw new Error(`La página ${number} está repetida.`);
      seen.add(number); result.push(number - 1);
    }
  }
  return result;
}
