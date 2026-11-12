"""Bounded column balancing and continuous column bands; no Office execution."""
import math,re
from io import BytesIO
from html.parser import HTMLParser
import pymupdf as f
from .engine import DocumentError
from .docx_frames import Frames,PAGE_BREAK_PREFIX


class NoFit(Exception):pass


def tail_marker(content):
    class Blocks(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.depth=0;self.last=None
        def handle_starttag(self,tag,attrs):
            if not self.depth:self.last=(self.getpos(),tag,dict(attrs))
            if tag not in ['br','img','hr','input','meta','link']:self.depth+=1
        def handle_endtag(self,tag):self.depth=max(0,self.depth-1)
        def handle_startendtag(self,tag,attrs):
            if not self.depth:self.last=(self.getpos(),tag,dict(attrs))
    parser=Blocks();parser.feed(content)
    if not parser.last:return content,None,0
    (line,column),tag,attrs=parser.last;identity=attrs.get('id')
    if not identity:
        identity='REAPDF_FLOW_END_042';offset=sum(len(v)+1 for v in content.split('\n')[:line-1])+column+len(tag)+1
        content=content[:offset]+' id="'+identity+'"'+content[offset:]
    style=attrs.get('style') or '';match=re.search(r'(?:^|;)margin-bottom:([0-9.]+)pt(?:;|$)',style)
    margin=float(match[1]) if match else {'p':8,'table':10}.get(tag,0)
    return content,identity,margin


def measure(content,css,archive,columns,geometry,starts,reserves,max_pages,start_page=0,start_y=None,heights=None):
    width,height,left,top,right,bottom=geometry;start_y=top if start_y is None else start_y
    content,tail_id,tail_margin=tail_marker(content)
    story=f.Story('<html><body>'+content+'</body></html>',user_css=css,archive=archive);tail_position=None
    frames=Frames(columns,starts);records=[];ids={};visible_pages={};breaks=set();more=True
    while more:
        index=len(records);page,logical=frames.locate(index);page+=start_page
        if page>=max_pages or index>=250:raise NoFit()
        band_top=start_y if page==start_page else top
        _,rect,_=frames.rect(logical,width,height,left,band_top,right,bottom,reserves.get(page,0))
        if heights and page in heights:rect.y1=min(rect.y1,rect.y0+heights[page])
        if rect.height<1:raise NoFit()
        more,filled=story.place(rect);filled=f.Rect(filled)
        if not all(math.isfinite(v) for v in filled) or filled.x0<rect.x0-.2 or filled.x1>rect.x1+.2 or filled.y0<rect.y0-.2:raise NoFit()
        def position(node):
            nonlocal tail_position
            if tail_id and node.id==tail_id:tail_position=(page,float(node.rect[3]))
            if node.id and node.open_close&1:
                if not f.Rect(node.rect).is_empty:visible_pages.setdefault(node.id,page)
                ids.setdefault(node.id,(page,index,logical%len(columns['widths']),tuple(node.rect)))
                if node.id.startswith(PAGE_BREAK_PREFIX):breaks.add(index)
        story.element_positions(position);story.draw(None)
        records.append({'page':page,'column':logical%len(columns['widths']),'rect':tuple(rect),'filled':tuple(filled),'more':bool(more),'columns':columns,'used_bottom':filled.y1 if not more else min(filled.y1,rect.y1)})
    if tail_position and tail_position[0]==records[-1]['page']:records[-1]['used_bottom']=max(records[-1]['used_bottom'],tail_position[1]+tail_margin)
    story.reset()
    return {'story':story,'records':records,'ids':ids,'visible_pages':visible_pages,'breaks':breaks,'last_page':records[-1]['page'],'count':records[-1]['page']-start_page+1}


def balanced(content,css,archive,columns,geometry,baseline,starts,reserves,max_pages,start_page=0,start_y=None,expected_refs=None):
    """Find a verified fitting height, retaining pages, references and breaks."""
    if len(columns['widths'])==1:return baseline,None
    width,height,left,top,right,bottom=geometry;last=baseline['last_page'];y=top if last!=start_page or start_y is None else start_y
    low=16.;high=height-bottom-reserves.get(last,0)-y;best=baseline;best_height=high
    for _ in range(16):
        if high-low<=.25:break
        mid=(low+high)/2
        try:
            trial=measure(content,css,archive,columns,geometry,starts,reserves,max_pages,start_page,start_y,{last:mid})
            refs={key:trial['visible_pages'].get(key,-1) for key in (expected_refs or {})}
            if trial['last_page']!=last or trial['breaks']!=baseline['breaks'] or any(trial['ids'][key][2]!=0 for key in trial['ids'] if key.startswith(PAGE_BREAK_PREFIX)) or expected_refs is not None and refs!=expected_refs:raise NoFit()
        except NoFit:low=mid;continue
        best=trial;best_height=mid;high=mid
    return best,best_height


def balance_notes(plan,columns,geometry,css,archive):
    if len(columns['widths'])<2:return plan
    try:base=measure(plan['layout_content'],css,archive,columns,geometry,plan['page_break_frames'],plan['reserves'],plan['count'])
    except NoFit:raise DocumentError('La distribución Word no permite comprobar el equilibrio de columnas.') from None
    if base['count']!=plan['count'] or base['breaks']!=set(plan['page_break_frames']) or {key:base['visible_pages'].get(key,-1) for key in plan['ref_pages']}!=plan['ref_pages']:raise DocumentError('El plan Word cambió antes de equilibrar sus columnas.')
    candidate,h=balanced(plan['layout_content'],css,archive,columns,geometry,base,plan['page_break_frames'],plan['reserves'],plan['count'],expected_refs=plan['ref_pages'])
    renderer=ContinuousStory([{'story':candidate['story'],'records':candidate['records'],'columns':columns}],geometry,plan['reserves'])
    return {**plan,'story':renderer,'balance_heights':{plan['count']-1:h},'balanced_pages':1}


def continuous_plan(flows,css,archive,geometry,max_pages,reserves=None,protected_ids=()):
    """Plan each column band; using shared physical-page note reserves."""
    if max_pages<1:raise DocumentError('La distribución Word supera 50 páginas; no se entrega una salida parcial.')
    width,height,left,top,right,bottom=geometry;page=0;y=top;plans=[];flat=[];breaks=[];reserves=reserves or {};element_pages={}
    for flow in flows:
        if not flow['content'].strip():
            plans.append({'story':None,'records':[],'columns':flow['columns'],'source_sections':flow['source_sections'],'height':None,'last_page':page,'empty_top':y});continue
        if height-bottom-reserves.get(page,0)-y<72:page+=1;y=top
        starts=set()
        for _ in range(12):
            try:base=measure(flow['content'],css,archive,flow['columns'],geometry,starts,reserves,max_pages,page,y)
            except NoFit:raise DocumentError('El contenido de una sección continua no cabe en sus columnas; no se entrega un PDF parcial.') from None
            # pageBreakBefore at the start of a later band must start a new page.
            if 0 in base['breaks'] and y>top+.1:page+=1;y=top;starts=set();continue
            if base['breaks']==starts:break
            starts=base['breaks']
        else:raise DocumentError('Los saltos de la sección continua no convergen dentro del límite.')
        chosen,h=balanced(flow['content'],css,archive,flow['columns'],geometry,base,starts,reserves,max_pages,page,y,{ref:base['visible_pages'][ref] for ref in protected_ids if ref in base['visible_pages']})
        for ident,number in chosen['visible_pages'].items():element_pages.setdefault(ident,number)
        plan={'story':chosen['story'],'records':chosen['records'],'columns':flow['columns'],'source_sections':flow['source_sections'],'height':h,'last_page':chosen['last_page']};plans.append(plan)
        breaks.extend(len(flat)+i for i in chosen['breaks']);flat.extend(chosen['records'])
        page=chosen['last_page'];y=max(rec['used_bottom'] for rec in chosen['records'] if rec['page']==page)
    renderer=ContinuousStory(plans,geometry,reserves)
    return {'story':renderer,'count':page+1,'reserves':reserves,'element_pages':element_pages,'foot_pages':{},'foot_heights':{},'ref_pages':{},'page_break_frames':breaks,'passes':1,'balanced_pages':sum(p['height'] is not None for p in plans),'continuous_bands':[{'source_sections':p['source_sections'],'columns':len(p['columns']['widths']),'first_page':p['records'][0]['page']+1 if p['records'] else p['last_page']+1,'last_page':p['last_page']+1,'top':p['records'][0]['rect'][1] if p['records'] else p['empty_top'],'last_bottom':max((row['used_bottom'] for row in p['records'] if row['page']==p['last_page']),default=p.get('empty_top',0))} for p in plans]}


class ContinuousStory:
    def __init__(self,plans,geometry,reserves=None):self.plans=plans;self.geometry=geometry;self.reserves=dict(reserves or {});self.current=None;self.frame_index=-1

    def write(self,writer,rectfn,positionfn=None,pagefn=None):
        self.frame_index=-1
        width,height,*_=self.geometry;box=f.Rect(0,0,width,height);active=None;device=None
        for plan in self.plans:
            story=plan['story']
            if story is None:continue
            story.reset()
            for row in plan['records']:
                self.frame_index+=1;self.current=row
                if active!=row['page']:
                    if device is not None:
                        if pagefn:pagefn(active+1,box,device,1)
                        writer.end_page()
                    active=row['page'];device=writer.begin_page(box)
                    if pagefn:pagefn(active+1,box,device,0)
                more,filled=story.place(f.Rect(row['rect']))
                if bool(more)!=row['more'] or max(abs(a-b) for a,b in zip(filled,row['filled']))>.1:raise DocumentError('La escritura de columnas continuas difiere del plan revisado.')
                if positionfn:
                    def record(node):node.page_num=active+1;positionfn(node)
                    story.element_positions(record)
                draw_checked(story,device,box,f.Rect(row['rect']))
        if device is None:
            active=0;device=writer.begin_page(box)
            if pagefn:pagefn(1,box,device,0)
        if device is not None:
            if pagefn:pagefn(active+1,box,device,1)
            writer.end_page()

    def separators(self,doc):
        for plan in self.plans:
            columns=plan['columns']
            if not plan['records']:continue
            if not columns['separator'] or len(columns['widths'])<2:continue
            by_page={}
            for row in plan['records']:
                page=row['page'];band=by_page.setdefault(page,[row['rect'][1],row['used_bottom']]);band[1]=max(band[1],row['rect'][3] if page<plan['records'][-1]['page'] else row['used_bottom'])
            for page,(y0,y1) in by_page.items():
                y1=min(y1,self.geometry[1]-self.geometry[5]-self.reserves.get(page,0))
                x=self.geometry[2]
                for width,gap in zip(columns['widths'],columns['gaps']):
                    x+=width;doc[page].draw_line((x+gap/2,y0),(x+gap/2,y1),color=(.25,.25,.25),width=.5);x+=gap


def draw_checked(story,device,box,region):
    """Replay the same native display list only after verifying its paint bounds."""
    display=f.DisplayList(f.JM_rect_from_py(box));recording=f.DeviceWrapper(display.this);story.draw(recording);n=f.mupdf;n.fz_close_device(recording.this)
    def replay(target):n.fz_run_display_list(display.this,target.this,f.JM_matrix_from_py(f.Identity),f.JM_rect_from_py(box),n.FzCookie())
    stream=BytesIO();writer=f.DocumentWriter(stream)
    try:
        temporary=writer.begin_page(box);replay(temporary);writer.end_page()
    finally:writer.close()
    with f.open(stream=stream.getvalue()) as proof:
        for kind,bounds in proof[0].get_bboxlog():
            rect=f.Rect(bounds)
            if not rect.is_empty and not (region+(-2,-2,2,2)).contains(rect):raise DocumentError('La pintura de un bloque Word rebasa sus columnas; no se entrega un PDF recortado o solapado.')
    replay(device)
