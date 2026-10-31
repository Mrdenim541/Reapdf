"""Conservative repeated-whitespace grid suggestions for borderless text tables."""
from statistics import median


def infer(words,box):
    if not 4<=len(words)<=10000:return None
    heights=[w['bbox'][3]-w['bbox'][1] for w in words];tolerance=max(1,median(heights)*.35);lines=[]
    for word in sorted(words,key=lambda w:((w['bbox'][1]+w['bbox'][3])/2,w['bbox'][0])):
        center=(word['bbox'][1]+word['bbox'][3])/2
        if not lines or abs(lines[-1]['center']-center)>tolerance:lines.append({'center':center,'words':[word]})
        else:lines[-1]['words'].append(word)
    if not 2<=len(lines)<=100:return None
    # Only gaps present on every row may separate columns. This deliberately
    # leaves irregular/multiline tables for the editable manual grid.
    gaps=[(box.x0,box.x1)]
    for line in lines:
        cells=sorted(line['words'],key=lambda w:w['bbox'][0]);line['words']=cells
        if len(cells)<2:return None
        row_gaps=[(a['bbox'][2],b['bbox'][0]) for a,b in zip(cells,cells[1:]) if b['bbox'][0]-a['bbox'][2]>=max(8,median(heights))]
        gaps=[(max(a,c),min(b,d)) for a,b in gaps for c,d in row_gaps if min(b,d)-max(a,c)>=max(6,median(heights)*.6)]
        if not gaps:return None
    separators=[(a+b)/2 for a,b in gaps]
    if not 1<=len(separators)<=29:return None
    columns=[box.x0,*separators,box.x1]
    for line in lines:
        if any(not any(a<=(w['bbox'][0]+w['bbox'][2])/2<b for w in line['words']) for a,b in zip(columns,columns[1:])):return None
    rows=[box.y0,*[(max(w['bbox'][3] for w in a['words'])+min(w['bbox'][1] for w in b['words']))/2 for a,b in zip(lines,lines[1:])],box.y1]
    if any(b-a<3 for a,b in zip(rows,rows[1:])):return None
    return columns,rows
