"""Local Word running matter: explicit variants, bounded layout, no field code."""
import posixpath
import pymupdf as f
from .engine import DocumentError
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PAGE_TOKEN='REAPDF_RUNNING_PAGE_VALUE_039'
TOTAL_TOKEN='REAPDF_RUNNING_TOTAL_VALUE_039'
def tag(name):return '{'+W+'}'+name

def relationships(package,path,parse_xml):
    result={}
    if path in package:
        for node in parse_xml(package[path]):
            ident=node.attrib.get('Id')
            if not ident or ident in result:raise DocumentError('Relaciones Word ausentes o repetidas.')
            result[ident]=node.attrib
    return result


def running_parts(package,section,rels,parse_xml,render,warnings,fields=None):
    templates={};used=set();first=False;even=False
    if section is not None:
        title=section.find(tag('titlePg'));first=title is not None and title.attrib.get(tag('val'),'1') not in ['0','false','off']
        for kind in ['header','footer']:
            for ref in section.findall(tag(kind+'Reference')):
                variant=ref.attrib.get(tag('type'),'default');key=kind,variant
                if variant not in ['default','first','even'] or key in templates:raise DocumentError('Variantes de encabezados/pies Word repetidas o no compatibles.')
                rel=rels.get(ref.attrib.get('{'+R+'}id'),{})
                expected=R+'/'+kind
                if rel.get('TargetMode')=='External' or rel.get('Type')!=expected:
                    raise DocumentError('El encabezado/pie necesita una relación interna compatible; no se descargan recursos.')
                target=posixpath.normpath(posixpath.join('word',rel.get('Target','')))
                if target not in package or not target.startswith('word/') or '\\' in target:raise DocumentError('No se encuentra una parte de encabezado/pie Word válida.')
                root=parse_xml(package[target])
                if root.tag!=tag('hdr' if kind=='header' else 'ftr'):raise DocumentError('Parte de encabezado/pie Word de tipo incorrecto.')
                if any(n.tag in {tag(k) for k in ['ins','del','moveFrom','moveTo','object','altChunk']} for n in root.iter()):raise DocumentError('Resuelve revisiones y objetos no compatibles en encabezados/pies antes de importar.')
                path=posixpath.dirname(target)+'/_rels/'+posixpath.basename(target)+'.rels'
                templates[key]=render(root,relationships(package,path,parse_xml));used.add(target)
    if 'word/settings.xml' in package:
        settings=parse_xml(package['word/settings.xml']);setting=settings.find(tag('evenAndOddHeaders'))
        even=setting is not None and setting.attrib.get(tag('val'),'1') not in ['0','false','off']
    if any(name.startswith(('word/header','word/footer')) and name.endswith('.xml') and name not in used for name in package):warnings.add('Encabezados/pies sin referencia en la sección importada no se incorporan.')
    distances=[18.,18.]
    margin=section.find(tag('pgMar')) if section is not None else None
    if margin is not None:
        for i,key in enumerate(['header','footer']):
            if tag(key) in margin.attrib:
                try:distances[i]=int(margin.attrib[tag(key)])/20
                except ValueError:raise DocumentError('Distancia de encabezado/pie Word no válida.')
                if not 0<=distances[i]<=144:raise DocumentError('Distancia de encabezado/pie Word fuera de 0–144 pt.')
    return RunningMatter(templates,first,even,distances,fields)


class RunningMatter:
    def __init__(self,templates,first,even,distances,fields=None):
        self.fields=fields;self.templates=templates;self.first=first;self.even=even;self.distances=distances;self.heights={};self.positions=[];self.drawn=0;self.expected=[]
    def content(self,template,page,total,measure=False,section_total=None):
        content=template[0].replace(PAGE_TOKEN,str(page)).replace(TOTAL_TOKEN,str(total))
        return self.fields.replace(content,page,total,measure,section_total) if self.fields else content
    def prepare(self,width,height,left,right,top,bottom,css,archive):
        self.width,self.height,self.left,self.right=width,height,left,right;self.css,self.archive=css,archive
        for key,template in self.templates.items():
            story=f.Story(self.content(template,50,50,measure=True),user_css=css,archive=archive)
            rect=f.Rect(left,0,width-right,144);more,filled=story.place(rect);filled=f.Rect(filled)
            if more or filled.x0<rect.x0-.1 or filled.x1>rect.x1+.1 or filled.y1>144.1:raise DocumentError('Un encabezado/pie Word no cabe en el ancho o supera 144 pt de alto. Simplifícalo antes de importar.')
            self.heights[key]=max(1,filled.y1)
        header=max((v for k,v in self.heights.items() if k[0]=='header'),default=0)
        footer=max((v for k,v in self.heights.items() if k[0]=='footer'),default=0)
        top=max(top,self.distances[0]+header+8) if header else top
        bottom=max(bottom,self.distances[1]+footer+8) if footer else bottom
        if height-top-bottom<72:raise DocumentError('Encabezados y pies no dejan 72 pt de espacio para el cuerpo Word.')
        return top,bottom
    def draw(self,page,total,device,physical_page=None,section_total=None):
        variant='first' if page==1 and self.first else 'even' if (physical_page or page)%2==0 and self.even else 'default'
        for kind in ['header','footer']:
            key=kind,variant;template=self.templates.get(key)
            if template is None:continue
            start=self.distances[0] if kind=='header' else self.height-self.distances[1]-self.heights[key]
            rect=f.Rect(self.left,start,self.width-self.right,start+self.heights[key]+.05)
            story=f.Story(self.content(template,page,total,section_total=section_total),user_css=self.css,archive=self.archive);more,filled=story.place(rect)
            if more or f.Rect(filled).x1>rect.x1+.1:raise DocumentError('El encabezado/pie Word no cabe completo; no se entrega un PDF recortado.')
            def position(node):
                node.page_num=page;self.positions.append(node)
            story.element_positions(position);story.draw(device);self.drawn+=1;self.expected.extend(template[1])
