"""Local extractive summaries and passage retrieval with PDF page references.

No model, network, prompt execution or generated factual claims.
"""
import math,re,unicodedata
from collections import Counter
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
STOP=set('a al algo algunas algunos ante antes asi aun bajo cada como con contra cual cuando de del desde donde dos el ella ellas ello ellos en entre era es esa esas ese eso esos esta estaba estas este esto estos fue ha hacia hasta hay la las le les lo los mas me mi muy ni no nos o otra otras otro otros para pero por porque que quien se sea ser si sin sobre son su sus tal tambien te tener tiene todo todos tu un una unas uno unos y ya the a an and are as at be by for from has have in is it of on or that this to was were what when which who with'.split())


def fold(text):return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
def words(text):return [w for w in re.findall(r'\w+(?:[-./]\w+)*',fold(text)) if len(w)>1 and w not in STOP]


def collect(doc,requested):
    if requested is None:requested=list(range(len(doc)))
    if not isinstance(requested,list) or not requested or any(type(p) is not int or not 0<=p<len(doc) for p in requested) or len(set(requested))!=len(requested):raise DocumentError('Selecciona páginas existentes y sin repetir.')
    limited=len(requested)>200;rows=[];count=0;processed=[];text_pages=0
    for number in requested[:200]:
        page=doc[number];processed.append(number);had_text=False
        for block in page.get_text('blocks',flags=f.TEXTFLAGS_TEXT,sort=True):
            text=' '.join(block[4].split())
            if not text:continue
            had_text=True
            if count+len(text)>400000:text=text[:max(0,400000-count)];limited=True
            count+=len(text)
            for sentence in re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ0-9¿¡])',text):
                while sentence:
                    stop=len(sentence) if len(sentence)<=650 else sentence.rfind(' ',0,650)
                    if stop<=0:stop=min(650,len(sentence))
                    fragment=sentence[:stop].strip();sentence=sentence[stop:].lstrip();terms=words(fragment)
                    if terms:rows.append({'page':number,'box':[block[0],block[1],block[2]-block[0],block[3]-block[1]],'text':fragment,'terms':terms})
                    if len(rows)>=8000:limited=True;break
                if len(rows)>=8000:break
            if count>=400000 or len(rows)>=8000:limited=True;break
        text_pages+=int(had_text)
        if count>=400000 or len(rows)>=8000:break
    return rows,{'processed_pages':processed,'requested_pages':len(requested),'text_pages':text_pages,'limited':limited}


def analyze(base,ops,mode='summary',question='',pages=None,limit=8):
    if mode not in ['summary','query'] or type(limit) is not int or not 1<=limit<=12:raise DocumentError('Elige resumen o consulta y entre 1 y 12 pasajes.')
    if not isinstance(question,str) or len(question)>300 or any(ord(c)<32 for c in question):raise DocumentError('La consulta admite hasta 300 caracteres sin controles.')
    query=set(words(question))
    if mode=='query' and not query:raise DocumentError('Escribe un identificador o palabras significativas para buscar.')
    with open_pdf(base) as source:
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('El PDF no permite extraer texto para esta consulta.')
    with open_pdf(export_pdf(base,ops)) as doc:rows,meta=collect(doc,pages)
    frequency=Counter(t for row in rows for t in set(row['terms']));ranked=[]
    for i,row in enumerate(rows):
        terms=Counter(row['terms']);length=max(1,len(row['terms']))
        if mode=='query':score=sum((1+math.log(terms[t]))*(1+math.log((len(rows)+1)/(frequency[t]+1))) for t in query if t in terms)/math.sqrt(length)
        else:score=sum(min(count,3)*math.log1p(frequency[t]) for t,count in terms.items())/math.sqrt(length)
        if score>0:ranked.append((score,i,row))
    ranked.sort(key=lambda item:(-item[0],item[1]));selected=[];seen=set()
    for _,_,row in ranked:
        identity=fold(row['text'])
        if identity in seen:continue
        # Repeated headers/near-duplicate passages should not fill a summary.
        tokens=set(row['terms'])
        if mode=='summary' and any(len(tokens&set(v['terms']))/max(1,len(tokens|set(v['terms'])))>.85 for v in selected):continue
        seen.add(identity);selected.append(row)
        if len(selected)==limit:break
    sources=[{k:row[k] for k in ['page','box','text']} for row in selected]
    for i,row in enumerate(sources):row['reference']='['+str(i+1)+']'
    reason='' if sources else 'No se encontraron pasajes coincidentes.' if rows else 'No hay texto extraíble suficiente. Aplica OCR a los escaneados antes de consultar.'
    if meta['limited']:reason=(reason+' ' if reason else '')+'Resultado parcial: se alcanzó un límite de páginas o texto.'
    return {**meta,'mode':mode,'sources':sources,'reason':reason,'generative':False,'network_used':False,'scope':'Pasajes extraídos del PDF con referencias. No genera conclusiones, no interpreta imágenes sin OCR ni ejecuta instrucciones del documento.'}
