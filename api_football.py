from __future__ import annotations
import json,os
from datetime import datetime,timedelta
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from team_resolver import load_map,score_event,unresolved
BASE='https://v3.football.api-sports.io'
def call(path,params):
 key=os.getenv('API_FOOTBALL_KEY','').strip()
 if not key:raise RuntimeError('API_FOOTBALL_KEY 未配置')
 req=Request(BASE+path+'?'+urlencode(params),headers={'x-apisports-key':key})
 with urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8'))
def form(items,team_id):
 out=[]
 for x in reversed(items):
  home=x['teams']['home']['id']==team_id;w=x['teams']['home'].get('winner') if home else x['teams']['away'].get('winner')
  out.append('W' if w else 'L' if w is False else 'D')
 return ''.join(out)
def fetch_context(events):
 mapping=load_map();days=set();errors=[]
 for e in events:
  try:
   d=datetime.strptime(e['kickoff'][:10],'%Y-%m-%d');days.update([(d+timedelta(days=i)).strftime('%Y-%m-%d') for i in (-1,0,1)])
  except:pass
 try:
  fixtures=[]
  for d in sorted(days):fixtures+=call('/fixtures',{'date':d}).get('response',[])
 except Exception as e:return {},['API-Football：'+type(e).__name__]
 out={}
 for e in events:
  missing=unresolved(e,mapping)
  candidates=sorted(((score_event(e,f,mapping),f) for f in fixtures),key=lambda x:x[0],reverse=True)
  score,f=(candidates[0] if candidates else (0,None))
  if score<100 or not f:
   status='球队别名未收录：'+','.join(missing) if missing else 'API未匹配（联赛/日期/免费覆盖待核验）'
   out[e['code']]={'status':status,'mapping_score':score};continue
  fid=f['fixture']['id'];hid=f['teams']['home']['id'];aid=f['teams']['away']['id']
  ctx={'status':'已匹配（别名库）','mapping_score':score,'fixture_id':fid,'venue':f['fixture'].get('venue',{}).get('name','-'),'league':f['league']['name'],'injury_home':0,'injury_away':0,'home_form':'-','away_form':'-','lineups':'待确认'}
  try:
   inj=call('/injuries',{'fixture':fid}).get('response',[]);ctx['injury_home']=sum(1 for x in inj if x.get('team',{}).get('id')==hid);ctx['injury_away']=sum(1 for x in inj if x.get('team',{}).get('id')==aid)
  except Exception as ex:errors.append(f"{e['code']}伤停：{type(ex).__name__}")
  try:
   ctx['home_form']=form(call('/fixtures',{'team':hid,'last':5}).get('response',[]),hid);ctx['away_form']=form(call('/fixtures',{'team':aid,'last':5}).get('response',[]),aid)
  except Exception as ex:errors.append(f"{e['code']}近期赛果：{type(ex).__name__}")
  out[e['code']]=ctx
 return out,errors
