import re,itertools
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.text_search import wildcard_hits,wildcard_tokens
from backend.find_replace import inspect,replace


def hits(s,p,**kwargs):return wildcard_hits(s,wildcard_tokens(p),**kwargs)


@pytest.mark.parametrize('text,pattern,expected',[
 ('COD-1 COD-2','COD-?',[(0,5,'COD-1'),(6,11,'COD-2')]),
 ('ABC xx ABC yy','A*',[(0,13,'ABC xx ABC yy')]),
 ('literal * ? ~','~*',[(8,9,'*')]),
 ('literal * ? ~','~?',[(10,11,'?')]),
 ('literal * ? ~','~~',[(12,13,'~')]),
 ('~x ~','~x',[(0,2,'~x')]),('~x ~','~',[(0,1,'~'),(3,4,'~')]),
 ('abc','*',[(0,3,'abc')]),('','*',[]),('abc','***',[(0,3,'abc')]),
 ('aßé','???',[(0,3,'aßé')]),('aβ aΒ','a?',[(0,2,'aβ'),(3,5,'aΒ')]),
])
def test_excel_wildcards_escaping_unicode_and_longest(text,pattern,expected):assert hits(text,pattern)==expected


def test_literal_behavior_case_and_boundaries():
 assert hits('ABC abc','ab?',case_sensitive=True)==[(4,7,'abc')]
 assert hits('XA1 A2Z A3','A?',whole_word=True)==[(8,10,'A3')]
 assert hits('A1x A2','A*?',whole_word=True)==[(0,6,'A1x A2')]


def test_small_patterns_match_independent_greedy_regex_oracle():
 for n in range(1,5):
  for values in itertools.product('ab*?',repeat=n):
   pattern=''.join(values);regex=''.join('.*' if c=='*' else '.' if c=='?' else re.escape(c) for c in pattern)
   for text in ['','a','b','ab','aba','aa bb','ababab']:
    expected=[(m.start(),m.end(),m[0]) for m in re.finditer(regex,text) if m.end()>m.start()]
    assert hits(text,pattern)==expected,(text,pattern)


def test_adversarial_pattern_stops_at_work_budget():
 with pytest.raises(DocumentError,match='límite'):wildcard_hits('a'*100000,wildcard_tokens('*a'*100),budget=[0])
 budget=[9_999_995]
 with pytest.raises(DocumentError,match='límite'):wildcard_hits('abc',wildcard_tokens('a*'),budget=budget)


def sample(rotation=0):
 with f.open() as d:
  p=d.new_page();p.insert_text((40,90),'COD-1 COD-2 COD-3',fontsize=14);p.insert_text((40,180),'Conservar vecino');p.set_rotation(rotation)
  d.new_page().insert_text((40,90),'Untouched page');return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_wildcard_select_preview_receipt_atomic_replace_and_original_font(rotation):
 base=sample(rotation);q={'text':'COD-?','pages':[0],'case_sensitive':False,'whole_word':True,'mode':'wildcard'}
 result=inspect(base,[],q);assert len(result['matches'])==3 and all(m['editable'] for m in result['matches'])
 out,token,count=replace(base,[],q,result['receipt'],[result['matches'][1]['id']],'X');assert count==1 and token
 with f.open(stream=base) as a,f.open(stream=out) as b:
  assert 'COD-1 X COD-3' in b[0].get_text() and 'Conservar vecino' in b[0].get_text()
  assert a[1].get_pixmap().samples==b[1].get_pixmap().samples and b[0].rotation==rotation
  assert a[0].get_fonts()[0][3]==b[0].get_fonts()[0][3]
 with pytest.raises(DocumentError,match='cambió'):replace(base,[],{**q,'mode':'literal'},result['receipt'],[result['matches'][1]['id']],'X')


def test_wildcard_crosses_contiguous_original_styles_and_keeps_suffix():
 from tests.test_find_replace_fragments import source,spans
 base=source();q={'text':'M??M','pages':[0],'case_sensitive':True,'whole_word':True,'mode':'wildcard'}
 result=inspect(base,[],q);assert len(result['matches'])==1 and result['matches'][0]['split']
 out,_,_=replace(base,[],q,result['receipt'],[result['matches'][0]['id']],'NNNN')
 with f.open(stream=base) as a,f.open(stream=out) as b:
  assert [s['text'] for s in spans(b)]==['NN','NN',' QQ']
  assert [s['font'] for s in spans(a)]==[s['font'] for s in spans(b)]
