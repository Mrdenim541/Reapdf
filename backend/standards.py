"""Independent, bounded veraPDF validation and verified PDF/A-2b archival copies."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from datetime import datetime,timezone
from xml.etree import ElementTree as ET
import base64,hashlib,json,os,shutil,subprocess,unicodedata
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable

ROOT=Path(__file__).resolve().parent.parent/'resources/standards'
PROFILES={'1b':'PDF/A-1b','2b':'PDF/A-2b','3b':'PDF/A-3b','ua1':'PDF/UA-1'}
MAX_BYTES=30*1024*1024
MAX_REPORT=8*1024*1024
PROCESS_LOCK=Lock()


def standard_status():
    java=shutil.which('java');gs=shutil.which('gs') or shutil.which('gswin64c');valid={};manifest={}
    try:
        manifest=json.loads((ROOT/'manifest.json').read_text())
        for key in ['verapdf','icc']:
            entry=manifest[key];expected='verapdf-cli-1.30.3.jar' if key=='verapdf' else 'sRGB.icc';path=ROOT/expected;valid[key]=entry['file']==expected and (key!='verapdf' or entry.get('version')=='1.30.3') and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
    except (OSError,ValueError,KeyError,TypeError):pass
    return {'validation_available':bool(java and valid.get('verapdf')),'conversion_available':bool(java and gs and valid.get('verapdf') and valid.get('icc')),
        'verapdf_version':manifest.get('verapdf',{}).get('version'),'java_available':bool(java),'ghostscript_available':bool(gs),
        'verified_resources':valid,'profiles':PROFILES,'max_pages':50,'max_bytes':MAX_BYTES}


def check_size(data):
    if len(data)>MAX_BYTES:raise DocumentError('La revisión de estándares admite PDF de hasta 30 MB.')
    with open_pdf(data) as doc:
        if len(doc)>50 or doc.xref_length()>50000:raise DocumentError('Hasta 50 páginas y 50000 objetos por revisión de estándares.')


def parse_validation(data,profile):
    if len(data)>MAX_REPORT:raise DocumentError('El informe del validador supera 8 MB.')
    try:
        root=ET.fromstring(data);jobs=root.findall('./jobs/job');batch=root.find('batchSummary')
        if len(jobs)!=1 or batch is None or batch.get('totalJobs')!='1':raise ValueError()
        report=jobs[0].find('validationReport');details=report.find('details') if report is not None else None
        if report is None or details is None or report.get('jobEndStatus')!='normal' or report.get('profileName')!=PROFILES[profile]+' validation profile':raise ValueError()
        if any(batch.get(key)!='0' for key in ['failedToParse','encrypted','outOfMemory','veraExceptions']):raise ValueError()
        summary=batch.find('validationReports')
        if summary is None or summary.get('failedJobs')!='0':raise ValueError()
        compliant=report.get('isCompliant')=='true';failed=int(details.get('failedRules','-1'));checks=int(details.get('failedChecks','-1'))
        if failed<0 or checks<0 or compliant!=(failed==0 and checks==0):raise ValueError()
        if summary.get('compliant')!=('1' if compliant else '0') or summary.get('nonCompliant')!=('0' if compliant else '1'):raise ValueError()
        rules=[{'specification':r.get('specification',''),'clause':r.get('clause',''),'test_number':r.get('testNumber',''),
            'description':(r.findtext('description') or '')[:4000],'object':(r.findtext('object') or '')[:200],
            'test':(r.findtext('test') or '')[:2000],'failed_checks':int(r.get('failedChecks','0'))} for r in details.findall('rule') if r.get('status')=='failed']
        if len(rules)!=failed:raise ValueError()
        return {'profile':profile,'profile_name':PROFILES[profile],'validator_profile_name':report.get('profileName',''),
            'compliant':compliant,'complete':True,'passed_rules':int(details.get('passedRules','0')),'failed_rules':failed,'passed_checks':int(details.get('passedChecks','0')),'failed_checks':checks,'rules':rules}
    except (ET.ParseError,ValueError,TypeError,KeyError):raise DocumentError('El validador no completó un informe consistente. No se afirma conformidad.') from None


def validate_file(path,profile,work):
    command=[shutil.which('java'),'-Xmx384m','-Djavax.xml.accessExternalDTD=','-Djavax.xml.accessExternalSchema=','-Djavax.xml.accessExternalStylesheet=',
        '-jar',str(ROOT/'verapdf-cli-1.30.3.jar'),'--format','xml','--flavour',profile,'--maxfailuresdisplayed','1','--loglevel','0',str(path)]
    report=work/'validation.xml';errors=work/'validation.log'
    try:
        with report.open('wb') as out,errors.open('wb') as err:result=subprocess.run(command,stdout=out,stderr=err,timeout=90,cwd=work)
    except subprocess.TimeoutExpired:raise DocumentError('La validación superó 90 segundos. Reduce el tamaño del documento.') from None
    except OSError:raise DocumentError('No se pudo iniciar Java/veraPDF en este equipo.') from None
    if result.returncode not in [0,1] or report.stat().st_size>MAX_REPORT:raise DocumentError('El validador no terminó correctamente; no se afirma conformidad.')
    return parse_validation(report.read_bytes(),profile)


def validate_standard(base,operations,profile='2b'):
    if not isinstance(profile,str) or profile not in PROFILES:raise DocumentError('Selecciona un perfil de estándares admitido.')
    if not standard_status()['validation_available']:raise DocumentError('La validación requiere Java y los recursos veraPDF verificados en este equipo.')
    data=export_pdf(base,operations);check_size(data)
    if not PROCESS_LOCK.acquire(blocking=False):raise DocumentError('Hay una validación o conversión en curso. Espera y vuelve a intentarlo.')
    try:
        with TemporaryDirectory(prefix='reapdf-standard-') as folder:
            work=Path(folder);path=work/'document.pdf';path.write_bytes(data);result=validate_file(path,profile,work)
    finally:PROCESS_LOCK.release()
    return {'schema':'reapdf-standards-1','source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'checked_at':datetime.now(timezone.utc).isoformat(),
        'validator':'veraPDF','validator_version':'1.30.3',**result,
        'scope':'Conformidad del perfil seleccionado según veraPDF, sin afirmar fidelidad de conversión, validación jurídica o accesibilidad comprobada manualmente.'}


def archival_copy(base,operations,review=False):
    if not standard_status()['conversion_available']:raise DocumentError('Crear PDF/A-2b requiere Ghostscript, Java y recursos verificados en este equipo.')
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&f.PDF_PERM_COPY or source.metadata.get('encryption'):raise DocumentError('La copia PDF/A requiere permiso de copia y una copia de trabajo sin cifrado.')
    data=export_pdf(base,operations);check_size(data)
    with open_pdf(data) as doc:
        if doc.embfile_count() or doc.get_ocgs() or doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null':raise DocumentError('Esta conversión protege adjuntos, capas y estructura etiquetada; no se convierten en este alcance.')
        for page in doc:
            if page.annot_xrefs() or page.get_links():raise DocumentError('La copia de archivo inicial requiere un documento sin campos, comentarios ni enlaces. Revisa una copia aplanada antes de convertir.')
        page_count=len(doc);source_text=[' '.join(unicodedata.normalize('NFKC',p.get_text()).split()) for p in doc];source_sizes=[(p.rect.width,p.rect.height) for p in doc]
        first=doc[0];scale=min(1,768/max(first.rect.width,first.rect.height));source_preview=first.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).tobytes('png')
    if not PROCESS_LOCK.acquire(blocking=False):raise DocumentError('Hay una validación o conversión en curso. Espera y vuelve a intentarlo.')
    try:
        with TemporaryDirectory(prefix='reapdf-archive-') as folder:
            work=Path(folder);(work/'source.pdf').write_bytes(data);shutil.copyfile(ROOT/'sRGB.icc',work/'sRGB.icc')
            prefix='''%!PS
/ICCProfile (sRGB.icc) def
[/_objdef {icc_PDFA} /type /stream /OBJ pdfmark
[{icc_PDFA} << /N 3 >> /PUT pdfmark
[{icc_PDFA} ICCProfile (r) file /PUT pdfmark
[/_objdef {OutputIntent_PDFA} /type /dict /OBJ pdfmark
[{OutputIntent_PDFA} << /Type /OutputIntent /S /GTS_PDFA1 /DestOutputProfile {icc_PDFA} /OutputConditionIdentifier (sRGB) /Info (sRGB IEC61966-2.1) >> /PUT pdfmark
[{Catalog} << /OutputIntents [{OutputIntent_PDFA}] >> /PUT pdfmark
'''
            icc_path=(work/'sRGB.icc').as_posix().replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
            prefix=prefix.replace('(sRGB.icc)','('+icc_path+')')
            (work/'profile.ps').write_text(prefix)
            command=[shutil.which('gs') or shutil.which('gswin64c'),'-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=pdfwrite','-dPDFA=2','-dPDFACompatibilityPolicy=1',
                '-dAutoRotatePages=/None','-sColorConversionStrategy=RGB','-dEmbedAllFonts=true','-dSubsetFonts=true','-dDownsampleColorImages=false','-dDownsampleGrayImages=false','-dDownsampleMonoImages=false',
                '--permit-file-read='+str(work/'sRGB.icc'),'-sOutputFile='+str(work/'archive.pdf'),str(work/'profile.ps'),str(work/'source.pdf')]
            try:
                with (work/'conversion.log').open('wb') as log:result=subprocess.run(command,stdout=log,stderr=log,timeout=90,cwd=work)
            except subprocess.TimeoutExpired:raise DocumentError('La conversión superó 90 segundos. No se entrega una copia parcial.') from None
            except OSError:raise DocumentError('No se pudo iniciar Ghostscript.') from None
            output=work/'archive.pdf'
            if result.returncode!=0 or not output.is_file() or output.stat().st_size>MAX_BYTES:raise DocumentError('La conversión falló o supera 30 MB; no se entrega una copia parcial.')
            verified=validate_file(output,'2b',work)
            if not verified['compliant']:raise DocumentError('La copia generada no cumple PDF/A-2b según veraPDF. No se entrega como PDF/A.')
            content=output.read_bytes()
            with open_pdf(content) as doc:
                if len(doc)!=page_count:raise DocumentError('La conversión no conservó las páginas. No se entrega.')
                for n in range(page_count):
                    size=source_sizes[n];rect=doc[n].rect;text=' '.join(unicodedata.normalize('NFKC',doc[n].get_text()).split())
                    if abs(rect.width-size[0])>.5 or abs(rect.height-size[1])>.5:raise DocumentError('La conversión cambió el tamaño visible de una página. No se entrega.')
                    if source_text[n]!=text:raise DocumentError('La extracción de texto difiere tras convertir. Esta copia requiere otro flujo de revisión y no se entrega.')
                first=doc[0];scale=min(1,768/max(first.rect.width,first.rect.height));output_preview=first.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).tobytes('png')
            report={'schema':'reapdf-archive-1','source_sha256':hashlib.sha256(data).hexdigest(),'output_sha256':hashlib.sha256(content).hexdigest(),'source_bytes':len(data),'output_bytes':len(content),'pages':page_count,
                'text_check':'Texto normalizado NFKC y espacios, igual en todas las páginas','visible_sizes_preserved':True,
                'preview':{'page':1,'source':'data:image/png;base64,'+base64.b64encode(source_preview).decode(),'output':'data:image/png;base64,'+base64.b64encode(output_preview).decode()},
                'profile':'2b','validator':'veraPDF','validator_version':'1.30.3','validation':verified,'scope':'Copia reconstruida por Ghostscript. Revisa apariencia, texto y colores antes de compartir. No conserva interactividad ni implica PDF/UA.'}
    finally:PROCESS_LOCK.release()
    return report if review else (content,report)
