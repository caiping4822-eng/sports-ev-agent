from __future__ import annotations
import json,os
from datetime import datetime,timedelta
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ALIASES={
 '图凯拉特':['kairat','kairat almaty'], '奥莫尼亚':['omonia','omonia nicosia'],
 '波兹莱赫':['lech poznan','lech poznań'], '奥胡斯':['agf','aarhus'],
 '米拉索':['mirassol'], '雷莫':['remo'], '巴西国际':['internacional'],
 '弗拉门戈':['flamengo'], '弗鲁米嫩':['fluminense'], '巴伊亚':['bahia'],
 '维多利亚':['vitoria','vitória'], '帕梅拉斯':['palmeiras']}
BASE='https://v3.football.api-sports.io'
def call(path,params):
 key=os.getenv('API_FOOTBALL_KEY','').strip()
 if not key:raise RuntimeError('API_FOOTBALL_KEY 未配置')
 req=Request(BASE+path+'?'+urlencode(params),headers={'x-apisports-key':key})
 with urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8'))
def match(cn,name):return any(a in name.lower() for a in ALIASES.get(cn,[]))
def form(items,team_id):
 out=[]
 for x in reversed(items):
  h=x['teams']['home']['id']==team_id; winner=x['teams']['home'].get('winner') if h else x['teams']['away'].get('winner')
  out.append('W' if winner else 'L' if winner is False else 'D')
 return ''.join(out)
def fetch_context(events):
 # 2 fixture-date requests + at most 6 injury and 12 recent-form requests per scan.
 base_dates={e['kickoff'][:10] for e in events if e.get('kickoff')}
 # Query the day before / target day / day after because China-sale time differs from local league time.
 unique_dates=set()
 for d in base_dates:
  try:
   x=datetime.strptime(d,'%Y-%m-%d')
   unique_dates.update((x-timedelta(days=1)).strftime('%Y-%m-%d') for _ in [0])
   unique_dates.add(d)
   unique_dates.add((x+timedelta(days=1)).strftime('%Y-%m-%d'))
  except: unique_dates.add(d)
 fixtures=[];errors=[]
 try:
  for day in sorted(unique_dates):fixtures+=call('/fixtures',{'date':day}).get('response',[])
 except Exception as e:return {},['API-Football：'+type(e).__name__]
 out={}
 for e in events:
  f=next((x for x in fixtures if match(e['home'],x['teams']['home']['name']) and match(e['away'],x['teams']['away']['name'])),None)
  if not f:
   out[e['code']]={'status':'API未匹配（日期/队名/免费覆盖待核验）'};continue
  fid=f['fixture']['id'];hid=f['teams']['home']['id'];aid=f['teams']['away']['id']
  ctx={'status':'已匹配','fixture_id':fid,'venue':f['fixture'].get('venue',{}).get('name','-'),'league':f['league']['name'],'injury_home':0,'injury_away':0,'home_form':'-','away_form':'-','lineups':'待确认'}
  try:
   inj=call('/injuries',{'fixture':fid}).get('response',[])
   ctx['injury_home']=sum(1 for x in inj if x.get('team',{}).get('id')==hid);ctx['injury_away']=sum(1 for x in inj if x.get('team',{}).get('id')==aid)
  except Exception as ex:errors.append(f"{e['code']}伤停：{type(ex).__name__}")
  try:
   hf=call('/fixtures',{'team':hid,'last':5}).get('response',[]);af=call('/fixtures',{'team':aid,'last':5}).get('response',[])
   ctx['home_form']=form(hf,hid);ctx['away_form']=form(af,aid)
  except Exception as ex:errors.append(f"{e['code']}近期赛果：{type(ex).__name__}")
  out[e['code']]=ctx
 return out,errors
