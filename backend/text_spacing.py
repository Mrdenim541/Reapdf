"""Verified TJ kerning, horizontal scale and character/word spacing.

Only adjustments between unchanged adjacent characters are carried to new text.
Unchanged source operators, fonts and clipping remain intact.
"""
from difflib import SequenceMatcher
from .engine import DocumentError


def layout(font,text,size,spacing,kern):
    advance=0.;origins=[];scale=spacing['scale']/100
    for i,char in enumerate(text):
        origins.append(advance);encoded,width=font.encode(char,size)
        # PDF word spacing applies only to a one-byte space code (32).
        extra=spacing['char']+(spacing['word'] if encoded==b' ' else 0)
        advance+=width*scale
        if i<len(text)-1:advance+=(extra-kern[i]*size/1000)*scale
    return advance,origins


def source_layout(font,text,size,obj):
    offsets={0:0};encoded=b''
    for i,char in enumerate(text):
        encoded+=font.encode(char,size)[0];offsets[len(encoded)]=i+1
    at=0;kern=[0.]*max(0,len(text)-1)
    for part in obj['parts']:
        if part.kind=='string':at+=len(part.value)
        elif part.value:
            if not 0<at<len(encoded) or at not in offsets or abs(part.value)>10000:raise DocumentError('El ajuste TJ no queda entre caracteres completos o supera el límite.')
            kern[offsets[at]-1]+=part.value
    if at!=len(encoded):raise DocumentError('El texto no coincide con los códigos originales.')
    width,origins=layout(font,text,size,obj['spacing'],kern)
    if any(b<=a for a,b in zip(origins,origins[1:])):raise DocumentError('La línea tiene glifos superpuestos o invertidos.')
    return width,origins,{'state':obj['spacing'],'kern':kern}


def replacement(row,text):
    old=row['text'];positions={}
    for match in SequenceMatcher(None,old,text,autojunk=False).get_matching_blocks():
        for i in range(match.size):positions[match.b+i]=match.a+i
    original=row['_spacing'];kern=[0.]*max(0,len(text)-1)
    for i in range(len(kern)):
        a=positions.get(i);b=positions.get(i+1)
        if a is not None and b==a+1:kern[i]=original['kern'][a]
    font=row['_font'];width,origins=layout(font,text,row['size'],original['state'],kern)
    if any(b<=a for a,b in zip(origins,origins[1:])):raise DocumentError('El espaciado haría que los caracteres se superpongan.')
    chunks=[]
    for i,char in enumerate(text):
        chunks.append(b'<'+font.encode(char,row['size'])[0].hex().encode()+b'>')
        if i<len(kern) and kern[i]:chunks.append(format(kern[i],'.8f').rstrip('0').rstrip('.').encode())
    if row['_native'][2]=='string':return b'<'+font.encode(text,row['size'])[0].hex().encode()+b'>',width
    return b'['+b' '.join(chunks)+b']'+(b' TJ' if row['_native'][2]=='operator-array' else b''),width
