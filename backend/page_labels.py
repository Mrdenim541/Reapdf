"""Read/write PDF label strings through the PDF parser, including Unicode/escapes."""
import pymupdf as fitz



def read_rules(doc):
    result=[]
    # The public rule_dict implementation splits on '/', strips parentheses and
    # does not decode PDF strings. Let MuPDF parse each dictionary instead.
    with fitz.open() as parser:
        xref=parser.get_new_xref()
        for start,raw in doc._get_page_labels():
            if len(result)>=2000:
                from .engine import DocumentError
                raise DocumentError('El documento supera 2000 reglas de etiquetas.')
            parser.update_object(xref,raw)
            prefix=parser.xref_get_key(xref,'P');style=parser.xref_get_key(xref,'S');first=parser.xref_get_key(xref,'St')
            result.append({'startpage':start,'prefix':prefix[1] if prefix[0]=='string' else '', 'style':style[1].lstrip('/') if style[0]=='name' else '', 'firstpagenum':int(first[1]) if first[0]=='int' and int(first[1])>0 else 1})
    return result


def write_rules(doc,rules):
    rows=[]
    for rule in rules:
        text=rule.get("prefix", "")
        prefix=fitz.get_pdf_str(text) if text.isascii() else "<FEFF"+text.encode("utf-16-be").hex().upper()+">"
        value=f"{rule['startpage']}<</P{prefix}"
        if rule.get('style'):value+='/S/'+rule['style']
        value+=f"/St {rule.get('firstpagenum',1)}>>";rows.append(value)
    doc.xref_set_key(doc.pdf_catalog(),'PageLabels','<</Nums['+''.join(rows)+']>>' if rows else 'null')


def visible_labels(doc):
    from .headers import roman
    rules=read_rules(doc);result=[];position=0
    for page in range(len(doc)):
        if not rules or rules[0]['startpage']>page:result.append('');continue
        while position+1<len(rules) and rules[position+1]['startpage']<=page:position+=1
        rule=rules[position];number=rule['firstpagenum']+page-rule['startpage'];style=rule['style'];suffix=''
        if style=='D':suffix=str(number)
        elif style in {'r','R'} and number<=3999:suffix=roman(number);suffix=suffix.lower() if style=='r' else suffix
        elif style in {'a','A'} and number<=10000:
            # ISO 32000: after Z, AA, BB ... ZZ, AAA. This differs from Excel.
            suffix=chr(65+(number-1)%26)*(1+(number-1)//26);suffix=suffix.lower() if style=='a' else suffix
        result.append(rule['prefix']+suffix)
    return result
