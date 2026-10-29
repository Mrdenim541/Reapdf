import React from 'react';
export function ToolGuide({tool,selected,pending}) {
  const guides={
    textbox:['Añadir texto','Arrastra una caja, escribe a la derecha y aplica. Después puedes moverla, cambiar tamaño o corregir su texto.'],
    stamp:['Sellos','Define un área y elige un sello estándar. Para añadirlo, la página debe estar a 0°.'],
    link:['Enlaces','Define el área del enlace y elige una página o dirección web. En Lectura podrás activarlo.'],
    view:['Lectura','Selecciona texto para copiarlo. Usa el zoom o ajusta la página a la ventana.'],
    images:['Imágenes','Inserta un PNG o JPEG desde el panel derecho. Selecciona la imagen y arrastra su marco o su esquina.'],
    text:['Editar texto',selected?'Modifica el texto, la fuente, el tamaño o el color y pulsa Aplicar cambio.':'Paso 1: haz clic en una línea con borde verde. Sus opciones aparecerán a la derecha.'],
    select:['Seleccionar marca','Haz clic sobre una marca o elígela en el panel derecho para ver qué puedes modificar.'],
    ink:['Lápiz','Mantén pulsado y arrastra para dibujar. Elige color y grosor en el panel derecho.'],
    line:['Línea','Arrastra desde el inicio hasta el final de la línea.'],
    arrow:['Flecha','Arrastra hacia el lugar al que debe apuntar la flecha.'],
    rectangle:['Rectángulo','Arrastra entre dos esquinas opuestas para crear el rectángulo.'],
    highlight:['Resaltar','Elige palabras o caracteres en el panel derecho. Arrastra sobre el texto y revisa la selección coloreada.'],
    underline:['Subrayar','Elige palabras o caracteres en el panel derecho y arrastra sobre el texto para subrayarlo.'],
    strikeout:['Tachar','Elige palabras o caracteres y marca con un clic o arrastrando. El tachado conserva el contenido.'],
    note:['Nota','Paso 1: haz clic en la página. Paso 2: escribe la nota a la derecha y pulsa Guardar nota.'],
  };
  const [title,instruction]=guides[tool]||guides.view;
  return <div className={`tool-guide ${pending?'draft-pending':''}`} aria-live="polite"><strong>{title}</strong><span>{pending||instruction}</span></div>;
}
