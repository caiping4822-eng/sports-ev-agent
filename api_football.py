from __future__ import annotations
import json,os
from datetime import datetime,timedelta
from urllib.parse import urlencode
from urllib.request import Request,urlopen
import re
TEAM_MAP={
"中日德兰":["FC Midtjylland","Midtjylland"],"贝西克塔":["Besiktas","Beşiktaş"],"贝西克塔斯":["Besiktas","Beşiktaş"],"帕佛斯":["Pafos","Pafos FC"],"斯海杜克":["Hajduk Split","Hajduk"],"海杜克":["Hajduk Split","Hajduk"],"安德莱赫":["Anderlecht"],"哈马比":["Hammarby","Hammarby FF"],"费伦茨瓦":["Ferencvaros","Ferencváros"],"特温特":["Twente","FC Twente"],"本菲卡":["Benfica"],"圣加仑":["St Gallen","St. Gallen"],"科林蒂安":["Corinthians"],"巴竞技":["Athletico Paranaense","Athletico-PR"],"图凯拉特":["Kairat","Kairat Almaty"],"奥莫尼亚":["Omonia","Omonia Nicosia"],"波兹莱赫":["Lech Poznan","Lech Poznań"],"奥胡斯":["AGF","Aarhus"],"米拉索":["Mirassol"],"雷莫":["Remo"],"巴西国际":["Internacional"],"弗拉门戈":["Flamengo"],"弗鲁米嫩":["Fluminense"],"巴伊亚":["Bahia"],"维多利亚":["Vitoria","Vitória"],"帕梅拉斯":["Palmeiras"]}
def norm(x):return re.sub(r'[^a-z0-9]','',x.lower())
def matches(cn,english,mapping):
 e=norm(english);return any(norm(a) in e or e in norm(a) for a in mapping.get(cn,[]))
def score_event(event,fixture,mapping):
 return 140 if matches(event['home'],fixture['teams']['home']['name'],mapping) and matches(event['away'],fixture['teams']['away']['name'],mapping) else 0
def unresolved(event,mapping):return [x for x in (event['home'],event['away']) if x not in mapping]
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
 mapping=TEAM_MAP;days=set();errors=[]
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
