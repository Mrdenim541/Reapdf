"""Crea una entrega de código para prueba personal, sin entornos ni documentos privados."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
out_dir = root / 'entregas'
out_dir.mkdir(exist_ok=True)
output = out_dir / 'Reapdf-prueba.zip'
# Lista explícita de fuentes; evita incorporar temporales, credenciales o PDF del usuario.
files = [root / name for name in (
    'README.md', '.gitignore', 'package.json', 'package-lock.json', 'requirements.txt',
    'requirements-dev.txt', 'requirements-lock.txt', 'instalar.cmd', 'iniciar.cmd')]
for directory, patterns in {
    'backend': ['*.py'], 'web': ['index.html', 'vite.config.js'],
    'web/src': ['*.jsx', '*.css', '*.js'], 'scripts': ['*.py', '*.mjs', '*.sh'],
    'tests': ['*.py', '*.mjs'], 'portable': ['*.py','*.md','*.json','*.lock'], 'docs': ['*.md'], '.github/workflows': ['*.yml'],
}.items():
    for pattern in patterns:
        files.extend((root / directory).glob(pattern))
files.extend(path for path in (root/'resources').rglob('*') if path.is_file())
with TemporaryDirectory(prefix='reapdf-package-') as tmp:
    demo = Path(tmp) / 'reapdf-demo.pdf'
    subprocess.run([sys.executable, str(root / 'scripts/create_sample.py'), str(demo)], check=True, capture_output=True)
    form_demo=Path(tmp)/'reapdf-formulario.pdf'
    subprocess.run([sys.executable,str(root/'scripts/create_form_sample.py'),str(form_demo)],check=True,capture_output=True)
    scan_demo=Path(tmp)/'reapdf-escaneado.pdf'
    subprocess.run([sys.executable,str(root/'scripts/create_scan_sample.py'),str(scan_demo)],check=True,capture_output=True)
    advanced_demo=Path(tmp)/'reapdf-formulario-avanzado.pdf'
    subprocess.run([sys.executable,str(root/'scripts/create_advanced_form_sample.py'),str(advanced_demo)],check=True,capture_output=True)
    styled_demo=Path(tmp)/'reapdf-texto-con-estilos.pdf'
    subprocess.run([sys.executable,str(root/'scripts/create_styled_text_sample.py'),str(styled_demo)],check=True,capture_output=True)
    review_demo=Path(tmp)/'reapdf-recorrido.pdf'
    subprocess.run([sys.executable,str(root/'scripts/create_review_sample.py'),str(review_demo)],check=True,capture_output=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, Path('Reapdf') / path.relative_to(root))
        archive.write(demo, 'Reapdf/ejemplos/reapdf-demo.pdf')
        archive.write(form_demo,'Reapdf/ejemplos/reapdf-formulario.pdf')
        archive.write(scan_demo,'Reapdf/ejemplos/reapdf-escaneado.pdf')
        archive.write(advanced_demo,'Reapdf/ejemplos/reapdf-formulario-avanzado.pdf')
        archive.write(styled_demo,'Reapdf/ejemplos/reapdf-texto-con-estilos.pdf')
        archive.write(review_demo,'Reapdf/ejemplos/reapdf-recorrido.pdf')
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert 'Reapdf/iniciar.cmd' in archive.namelist()
        assert 'Reapdf/ejemplos/reapdf-demo.pdf' in archive.namelist()
        assert not any('/.venv/' in name or '/node_modules/' in name for name in archive.namelist())
print(output)
print('SHA256', hashlib.sha256(output.read_bytes()).hexdigest())
