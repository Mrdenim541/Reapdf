"""Split extraction spans only at exact, uniquely verified source glyph groups."""
import math
from collections import defaultdict
import pymupdf as f
from .engine import DocumentError


def split(doc,page,blocks,objects=None,compatible=None):
    from .form_text import structure,resource_owner
    from .styled_text import OriginalFont,normal_name
    try:objects=structure(doc,page) if objects is None else objects
    except DocumentError:return blocks
    if len(page.get_fonts(full=True))>20:return blocks
    origins=defaultdict(list);cache={} if compatible is None else dict(compatible);programs=set();budget=0
    for obj in objects:
        point=obj['origin']*obj['matrix']*page.transformation_matrix
        if all(math.isfinite(v) for v in point):origins[(math.floor(point.x*50),math.floor(point.y*50))].append((obj,point))
    def face(obj):
        nonlocal budget
        key=(obj['scope'],obj['font'])
        if key not in cache:
            cache[key]=None
            try:
                owner=obj['scope'] or page.xref;kind,value=doc.xref_get_key(resource_owner(doc,owner),'Resources/Font/'+obj['font'])
                if kind!='xref':return None
                x=int(value.split()[0]);label,ext,kind,_=doc.extract_font(x);font=OriginalFont(doc,(x,ext,kind,label,obj['font'],'',obj['scope']))
                if x not in programs:budget+=font.program_bytes;programs.add(x)
                if budget>64*1024*1024:return None
                cache[key]=font
            except (DocumentError,ValueError,RuntimeError,UnicodeError):pass
        return cache[key]
    for block in blocks:
        for line in block.get('lines',[]):
            result=[]
            for span in line['spans']:
                chars=span.get('chars',[]);parts=[];at=0
                starts=0
                for char in chars:
                    x,y=char['origin']
                    if any(math.dist(point,char['origin'])<.02 for dx in [-1,0,1] for dy in [-1,0,1] for _,point in origins.get((math.floor(x*50)+dx,math.floor(y*50)+dy),[])):starts+=1
                    if starts>1:break
                if starts<2:result.append(span);continue
                while at<len(chars):
                    x,y=chars[at]['origin'];near=[]
                    for dx in [-1,0,1]:
                        for dy in [-1,0,1]:near.extend(origins.get((math.floor(x*50)+dx,math.floor(y*50)+dy),[]))
                    if len(near)<1:break
                    matches=[]
                    for obj,point in near:
                        if math.dist(point,chars[at]['origin'])>.02:continue
                        font=face(obj)
                        if font is None or normal_name(span['font']) not in font.aliases:continue
                        expected=obj['shows'][0].value;encoded=b''
                        for end in range(at,min(len(chars),at+4000)):
                            try:encoded+=font.encode(chars[end]['c'],1)[0]
                            except DocumentError:break
                            if not expected.startswith(encoded):break
                            if encoded==expected:matches.append(end+1);break
                    if len(matches)!=1:break
                    end=matches[0];chosen=chars[at:end];bounds=f.Rect(chosen[0]['bbox'])
                    for char in chosen[1:]:bounds|=f.Rect(char['bbox'])
                    parts.append({**span,'chars':chosen,'origin':chosen[0]['origin'],'bbox':tuple(bounds)});at=end
                result.extend(parts if at==len(chars) and len(parts)>1 else [span])
            line['spans']=result
    return blocks
