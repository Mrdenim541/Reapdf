"""Arithmetic native calculation expressions interpreted as data, never JavaScript.

Only event.value = arithmetic(this.getField("literal").value, decimal literals)
is accepted. No calls, properties, conditionals, assignment chains or execution.
"""
import ast,re
from decimal import Decimal,localcontext,DecimalException
from .engine import DocumentError

FIELD=re.compile(r'''this\s*\.\s*getField\s*\(\s*("(?:[^"\\\x00-\x1f]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"|'(?:[^'\\\x00-\x1f]|\\['\\])*')\s*\)\s*\.\s*value\b''')


def parse(code):
    from .form_actions import call
    def fail():raise DocumentError('El cálculo necesita una expresión aritmética explícita con campos literales; no se ejecuta JavaScript.')
    if not isinstance(code,str) or len(code)>4000:fail()
    match=re.fullmatch(r'\s*event\s*\.\s*value\s*=\s*([^;]+?)\s*;?\s*',code,re.S)
    if not match:fail()
    remainder=FIELD.sub('',match[1])
    if re.search(r'[^0-9.\s+*/()\-]',remainder) or '++' in remainder or '--' in remainder:fail()
    names=[]
    def field(m):
        name=call('X('+m[1]+')')[1][0]
        if not isinstance(name,str) or not 1<=len(name)<=200 or any(ord(c)<32 for c in name):fail()
        if name not in names:names.append(name)
        return 'F'+str(names.index(name))
    expression=FIELD.sub(field,match[1])
    if not names or len(names)>50 or re.search(r'[^F0-9.\s+*/()\-]',expression):fail()
    try:tree=ast.parse(expression.strip(),mode='eval')
    except (SyntaxError,ValueError,RecursionError) as exc:raise DocumentError('Expresión de cálculo no válida.') from exc
    if len(list(ast.walk(tree)))>100:fail()
    binary={ast.Add:'+',ast.Sub:'-',ast.Mult:'*',ast.Div:'/'}
    def walk(node,depth=0):
        if depth>12:fail()
        if isinstance(node,ast.Name) and re.fullmatch(r'F\d{1,2}',node.id) and int(node.id[1:])<len(names):return ['field',int(node.id[1:])]
        if isinstance(node,ast.Constant) and type(node.value) in [int,float]:
            raw=ast.get_source_segment(expression.strip(),node)
            if not raw or len(raw)>30 or not re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)',raw) or abs(Decimal(raw))>Decimal('1e12'):fail()
            return ['literal',raw]
        if isinstance(node,ast.BinOp) and type(node.op) in binary:return [binary[type(node.op)],walk(node.left,depth+1),walk(node.right,depth+1)]
        if isinstance(node,ast.UnaryOp) and type(node.op) in [ast.UAdd,ast.USub]:return ['positive' if isinstance(node.op,ast.UAdd) else 'negative',walk(node.operand,depth+1)]
        fail()
    return {'operation':'EXPR','sources':names,'expression':walk(tree.body)}


def evaluate(expression,inputs):
    def walk(node):
        kind=node[0]
        if kind=='field':result=inputs[node[1]]
        elif kind=='literal':result=Decimal(node[1])
        elif kind in ['positive','negative']:result=walk(node[1])*(1 if kind=='positive' else -1)
        else:
            a,b=walk(node[1]),walk(node[2])
            if kind=='+':result=a+b
            elif kind=='-':result=a-b
            elif kind=='*':result=a*b
            elif kind=='/':
                if not b:raise DocumentError('La fórmula divide entre cero; corrige sus datos antes de guardar.')
                result=a/b
            else:raise DocumentError('Operador de fórmula no compatible.')
        if not result.is_finite() or abs(result)>Decimal('1e12'):raise DocumentError('Un resultado intermedio de la fórmula supera 10¹².')
        return result
    try:
        with localcontext() as ctx:ctx.prec=34;return walk(expression)
    except DecimalException as exc:raise DocumentError('La fórmula no tiene un resultado decimal válido.') from exc
