# Decisión provisional: prueba de edición PDF

## Qué se decidió

Usar PyMuPDF 1.28.2 como candidato experimental para probar renderizado, anotaciones de tinta y reemplazo real de líneas de texto. La selección comercial definitiva sigue abierta. React/Vite y una API local FastAPI permiten comprobar el flujo desde navegador; Tauri y el instalador de escritorio todavía no se han implementado.

## Evidencia técnica

Las pruebas verifican que el texto anterior desaparece de la extracción, el texto nuevo está presente, las páginas no editadas se renderizan igual y los píxeles fuera de la región cambiada se conservan. Se comprueba el fondo gris tras eliminar texto y la ubicación de trazos en una página rotada. El recorrido Chromium exporta un archivo que se vuelve a abrir para verificar contenido y anotaciones.

Estas pruebas sintéticas no prueban compatibilidad universal, fidelidad de fuentes incrustadas ni eliminación de datos en metadatos, adjuntos o historial externo. El reemplazo no se presenta como herramienta de censura segura.

## Límites del algoritmo inicial

Acepta líneas horizontales de un único fragmento, fuente base reconocida y página sin rotación. La versión 0.10 admite las familias Helvetica, Times y Courier con cuatro variantes cada una, además de alias reconocidos de Arial y equivalentes. Puede cambiar fuente base, tamaño y color; conserva origen y línea base, limita el ancho al original y rechaza cruces con otro texto o salidas de página. Elimina el texto original sin borrar imágenes ni gráficos de fondo. No reproduce fuentes arbitrarias incrustadas ni reorganiza párrafos. Véase TEXTO.md.


## Alternativas por evaluar

| Candidato | Papel posible | Falta comprobar |
|---|---|---|
| PyMuPDF/MuPDF | Motor general y edición controlada | Corpus amplio y obligaciones AGPL/comerciales |
| PDFium y PDF.js | Renderizado, visor y extracción | Capacidades de edición necesarias y combinación con otro motor |
| pypdf y pdf-lib | Estructura, creación y operaciones de páginas | No asumir edición general de párrafos a partir de estas capacidades |
| SDK comercial de edición PDF | Edición avanzada, conversiones y otras funciones | Licencia de evaluación, APIs, plataformas, fidelidad y costo |

No se ha comprado, integrado ni probado un SDK comercial. No se han verificado precios actuales. Las referencias de licencia deben revisarse en la distribución exacta y documentación oficial antes de publicar un producto propietario.

## Paso siguiente para decidir

Ejecutar las mismas operaciones sobre un corpus autorizado y comparar resultados en lectores independientes. Si el candidato no puede editar los documentos objetivo sin deterioro, sustituir el adaptador del motor antes de ampliar la interfaz. No convertir limitaciones del prototipo en promesas comerciales.
