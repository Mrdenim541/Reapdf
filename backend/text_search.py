"""Bounded, non-backtracking Excel-style wildcard search over digital text."""
from .engine import DocumentError


def wildcard_tokens(pattern):
    result=[];i=0
    while i<len(pattern):
        c=pattern[i];i+=1
        if c=='~' and i<len(pattern) and pattern[i] in '*?~':
            result.append(('literal',pattern[i]));i+=1
        elif c=='*':
            if not result or result[-1][0]!='star':result.append(('star',''))
        elif c=='?':result.append(('any',''))
        else:result.append(('literal',c))
    return result


def wildcard_hits(text,tokens,case_sensitive=False,whole_word=False,budget=None):
    """Leftmost-longest non-empty matches, with O(text * pattern) work bounds.

    A star includes spaces, but cannot cross the caller's digital line group.
    End boundaries participate in matching; a greedy result cannot conceal an
    earlier valid whole-word end. No regex evaluation or user executable code.
    """
    cost=(len(text)+1)*(len(tokens)+1)
    if budget is not None:
        budget[0]+=cost
        if budget[0]>10_000_000:raise DocumentError('La búsqueda con comodines supera el límite de trabajo; reduce las páginas o el patrón.')
    elif cost>10_000_000:raise DocumentError('La búsqueda con comodines supera el límite de trabajo.')
    def word(c):return c.isalnum() or c=='_'
    n=len(text);m=len(tokens);ends=[-1]*(n+1);following=[-1]*(m+1)
    compared=[value if case_sensitive else value.casefold() for kind,value in tokens]
    for i in range(n,-1,-1):
        current=[-1]*(m+1)
        current[m]=i if not whole_word or i==n or not word(text[i]) else -1
        char=(text[i] if case_sensitive else text[i].casefold()) if i<n else None
        for j in range(m-1,-1,-1):
            kind,value=tokens[j]
            if kind=='star':current[j]=max(current[j+1],following[j] if i<n else -1)
            elif i<n and (kind=='any' or char==compared[j]):current[j]=following[j+1]
        ends[i]=current[0];following=current
    hits=[];i=0
    while i<n:
        end=ends[i]
        if end>i and (not whole_word or i==0 or not word(text[i-1])):
            hits.append((i,end,text[i:end]));i=end
            if len(hits)>500:raise DocumentError('Más de 500 coincidencias; limita la búsqueda.')
        else:i+=1
    return hits
