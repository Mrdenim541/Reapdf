import React from 'react';
import './tagged-copy.css';
export function TaggedCopy({disabled,onCreate}){
 return <section className="tagged-copy-choice"><p>Las etiquetas de accesibilidad impiden esta operación. Puedes crear una copia de trabajo sin esas etiquetas: conserva el texto, las imágenes y sus posiciones, sin convertir las páginas en imágenes. La copia pierde la estructura de accesibilidad y las declaraciones de conformidad PDF/UA y PDF/A. El original se conserva; puedes deshacer.</p><button disabled={disabled} onClick={onCreate}>Crear copia sin etiquetas para editar</button></section>;
}
