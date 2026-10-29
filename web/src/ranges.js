export function parsePageRange(value, count) {
  if (!Number.isInteger(count) || count < 1 || count > 500) throw new Error('Cantidad de páginas no válida.');
  if (typeof value !== 'string' || !value.trim()) throw new Error('Indica las páginas que quieres seleccionar.');
  const result = [], seen = new Set();
  for (const part of value.split(',')) {
    const match = part.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if (!match) throw new Error('Usa páginas o rangos separados por comas, por ejemplo: 1-3, 5.');
    const start = Number(match[1]), end = Number(match[2] ?? match[1]);
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 1 || end > count || start > end)
      throw new Error(`Usa páginas entre 1 y ${count}, con rangos de menor a mayor.`);
    for (let number = start; number <= end; number++) {
      if (seen.has(number)) throw new Error(`La página ${number} está repetida.`);
      seen.add(number); result.push(number - 1);
    }
  }
  return result;
}
