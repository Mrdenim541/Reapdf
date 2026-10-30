"""Rejoin renderer fragments only when a verified Type3 source group proves identity."""
import math
import pymupdf as f
from .engine import DocumentError


def merge_lines(doc,page,blocks,objects=None,faces=None):
    from .styled_text import OriginalFont,normal_name
    if faces is None:
        items=page.get_fonts(full=True)
        if len(items)>20 or not any(v[2]=='Type3' for v in items):return blocks
        faces=[]
        for item in items:
            if item[2]=='Type3':
                try:faces.append(OriginalFont(doc,item))
                except (DocumentError,ValueError,UnicodeError):pass
    faces=[face for face in faces if face.type=='Type3']
    if not faces:return blocks
    if objects is None:
        from .form_text import structure
        try:objects=structure(doc,page)
        except DocumentError:return blocks
    render_traces=page.get_texttrace()
    for block in blocks:
        for line in block.get('lines',[]):
            original=line['spans'];joined=[];index=0
            while index<len(original):
                first=original[index];end=index+1;key=lambda s:tuple(s.get(k) for k in ['font','size','color','ascender','descender'])
                while end<len(original) and key(original[end])==key(first):end+=1
                parts=original[index:end];raw='chars' in first;text=''.join(''.join(c['c'] for c in s['chars']) if raw else s['text'] for s in parts);verified=False
                if text and (len(parts)>1 or first.get('alpha')==0):
                    for face in faces:
                        if normal_name(first['font']) not in face.aliases:continue
                        try:encoded,_=face.encode(text,1)
                        except DocumentError:continue
                        for obj in objects:
                            if obj['font']!=face.resource or obj['shows'][0].value!=encoded:continue
                            origin=obj['origin']*obj['matrix']*page.transformation_matrix
                            if math.dist(origin,first['origin'])<.02:verified=True;break
                        if verified:break
                if verified:
                    span=dict(first);bounds=f.Rect(first['bbox'])
                    for part in parts[1:]:bounds|=f.Rect(part['bbox'])
                    span['bbox']=tuple(bounds)
                    source_traces=[t for t in render_traces if t['chars'] and t['chars'][0][0]==ord(text[0]) and normal_name(t['font']) in face.aliases and math.dist(t['chars'][0][2],first['origin'])<.02]
                    if len(source_traces)==1:span['alpha']=round(source_traces[0]['opacity']*255)
                    if raw:span['chars']=[c for s in parts for c in s['chars']]
                    else:span['text']=text
                    joined.append(span)
                else:joined.extend(parts)
                index=end
            line['spans']=joined
    return blocks


def trace(font,span,traces):
    from .styled_text import normal_name
    if font.type!='Type3':return None
    chars=[];opacity=None;layer=None
    for source in span['chars']:
        if len(source['c'])!=1:return None
        matches=[]
        for item in traces:
            if item['type'] not in [0,3] or normal_name(item['font']) not in font.aliases or item['layer'] or not 0<item['opacity']<=1:continue
            for char in item['chars']:
                if char[0]==ord(source['c']) and math.dist(char[2],source['origin'])<.02:matches.append((item,char))
        if len(matches)!=1:return None
        item,char=matches[0]
        if opacity is not None and abs(opacity-item['opacity'])>1e-6:return None
        opacity=item['opacity'];layer=item['layer'];chars.append(char)
    if not chars:return None
    return {'chars':chars,'opacity':opacity,'layer':layer,'type':0}
