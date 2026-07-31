from __future__ import annotations
import json,re
from html import unescape
from pathlib import Path
from urllib.request import Request,urlopen
from api_football import call,TEAM_MAP
ROOT=Path(__file__).parent;DATA=ROOT/'data';RESULT_URL='https://cp.zgzcw.com/dc/getKaijiangFootBall.action'
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def clean(x):return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]+>',' ',x))).strip()
def same(cn,got):
 if cn==got or cn in got or got in cn:return True
 return any(a.lower() in got.lower() or got.lower() in a.lower() for a in TEAM_MAP.get(cn,[]))
def china_result_rows():
 try:
  req=Request(RESULT_URL,headers={'User-Agent':'Mozilla/5.0 (compatible; SportsEVResearch/1.0)'})
  with urlopen(req,timeout=30) as r:raw=r.read().decode('utf8','replace')
  out=[]
  for row in re.findall(r'<tr[^>]*>.*?</tr>',raw,re.I|re.S):
   c=[clean(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',row,re.I|re.S)]
   if len(c)<6 or not re.match(r'周[一二三四五六日]\d{3}',c[0]):continue
   score=next((x for x in c if re.search(r'\d+\s*:\s*\d+',x)),None)
   if score:
    m=re.search(r'(\d+)\s*:\s*(\d+)',score);out.append({'code':c[0],'home':c[3],'away':c[5],'score':m.group(1)+':'+m.group(2),'hg':int(m.group(1)),'ag':int(m.group(2))})
  return out
 except:return []
def result_for(record):
 seed=load(DATA/'verified_results_seed.json',{}).get(record['key'])
 if seed:return {'score':seed['score'],'outcome':seed['outcome'],'source':'verified_seed','verified':len(seed.get('verified_sources',[]))>=2,'sources':seed.get('verified_sources',[])}
 api=None
 if record.get('fixture_id'):
  try:
   f=call('/fixtures',{'id':record['fixture_id']}).get('response',[])
   if f:
    f=f[0];sc=f.get('score',{}).get('fulltime',{});hg=sc.get('home');ag=sc.get('away')
    if hg is not None and ag is not None:api={'hg':hg,'ag':ag,'score':f'{hg}:{ag}'}
  except:pass
 china=next((x for x in china_result_rows() if x['code']==record['code'] and same(record['home'],x['home']) and same(record['away'],x['away'])),None)
 if api and china and api['score']==china['score']:
  hg,ag=api['hg'],api['ag'];out='主胜' if hg>ag else '客胜' if ag>hg else '平';return {'score':api['score'],'outcome':out,'source':'api+zgzcw','verified':True,'sources':['api_football','zgzcw_result']}
 if api:
  hg,ag=api['hg'],api['ag'];out='主胜' if hg>ag else '客胜' if ag>hg else '平';return {'score':api['score'],'outcome':out,'source':'api_single','verified':False,'sources':['api_football']}
 return None
