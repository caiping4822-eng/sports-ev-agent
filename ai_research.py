from __future__ import annotations
import json,os,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from api_football import TEAM_MAP
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8));VERSION=4
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def post(url,payload,headers):
 req=Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
 with urlopen(req,timeout=45) as r:return json.loads(r.read().decode('utf-8'))
def err(e):
 if isinstance(e,HTTPError):
  try:b=e.read().decode('utf8','replace')[:120].replace('\n',' ')
  except:b=''
  return f'HTTP {e.code} {b}'
 return type(e).__name__
def norm(x):return re.sub(r'[^a-z0-9]','',x.lower())
def relevant(result,home_aliases,away_aliases):
 text=norm(result.get('title','')+' '+result.get('content',''))
 return any(norm(a) in text for a in home_aliases) and any(norm(a) in text for a in away_aliases)
def search(q):
 k=os.getenv('TAVILY_API_KEY','').strip()
 if not k:raise RuntimeError('TAVILY_API_KEY未配置')
 return post('https://api.tavily.com/search',{'query':q,'search_depth':'basic','max_results':6},{'Authorization':'Bearer '+k})
def summarize(match,results):
 k=os.getenv('DEEPSEEK_API_KEY','').strip()
 if not k:raise RuntimeError('DEEPSEEK_API_KEY未配置')
 snips='\n\n'.join(f"URL:{r['url']}\nTITLE:{r['title']}\nTEXT:{r.get('content','')[:1000]}" for r in results)
 prompt=f'''仅使用以下已通过双方队名相关性过滤的搜索摘要，分析比赛 {match}。输出严格JSON：{{"confirmed":[],"uncertain":[],"risks":[],"summary":""}}。confirmed只能包含明确伤缺、停赛、首回合比分、官方赛程等；任何“可能/预计/或将/may/likely/predicted”必须写入uncertain；投注观点、赔率、推荐不得写入任何事实字段。\n{snips}'''
 d=post('https://api.deepseek.com/chat/completions',{'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'temperature':0.0,'response_format':{'type':'json_object'}},{'Authorization':'Bearer '+k})
 return json.loads(d['choices'][0]['message']['content'])
def section(data):
 cards=[]
 for x in data.get('events',[]):
  r=x['research'];src=' ｜ '.join(f'<a href="{escape(z["url"])}" target="_blank">{escape(z["title"][:45])}</a>' for z in x.get('sources',[]))
  cards.append(f"<div class='research'><h3>{escape(x['code'])} {escape(x['match'])}</h3><p><b>搜索质量：</b>{escape(x['status'])}</p><p><b>AI总结：</b>{escape(r.get('summary','数据不足'))}</p><p><b>已确认：</b>{escape('；'.join(r.get('confirmed',[]) or []) or '无')}</p><p><b>待确认：</b>{escape('；'.join(r.get('uncertain',[]) or []) or '无')}</p><p><b>风险：</b>{escape('；'.join(r.get('risks',[]) or []) or '无')}</p><p class='small'><b>有效来源：</b>{src or '无'}</p></div>")
 return '<!-- AI_START --><div class="card"><h2>AI 联网基本面研究</h2><p class="small">仅保留双方队名同时匹配的来源；球队别名未知、来源少于2个、无关页面均不进入综合裁判。</p>'+''.join(cards)+'</div><!-- AI_END -->'
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);today=datetime.now(CST).strftime('%Y-%m-%d');cache=load(DATA/'ai_research_daily.json',{});latest=load(DATA/'latest_zgzcw.json',{});events=latest.get('events',[]);closed=any('已停售' in str(x) for x in latest.get('errors',[]))
 if cache.get('date')==today and cache.get('pipeline_version')==VERSION:data=cache
 else:
  out=[]
  for e in events if not closed else []:
   ha=TEAM_MAP.get(e['home'],[]);aa=TEAM_MAP.get(e['away'],[])
   if not ha or not aa:
    out.append({'code':e['code'],'match':e['home']+' vs '+e['away'],'status':'球队别名未确认，AI搜索跳过','sources':[],'valid':False,'research':{'confirmed':[],'uncertain':[],'risks':['球队映射不足'],'summary':'不进入AI模型'}});continue
   try:
    raw=search(f'{ha[0]} {aa[0]} injury suspension team news predicted lineup');results=[r for r in raw.get('results',[]) if relevant(r,ha,aa)]
    if len(results)<2: raise RuntimeError('相关来源不足2个')
    research=summarize(ha[0]+' vs '+aa[0],results);status=f'有效来源 {len(results)} 个'
    valid=True
   except Exception as ex:
    results=[];research={'confirmed':[],'uncertain':[],'risks':['搜索/总结未通过：'+err(ex)],'summary':'AI研究无效'};status='AI研究无效';valid=False
   out.append({'code':e['code'],'match':e['home']+' vs '+e['away'],'status':status,'sources':[{'title':r.get('title',''),'url':r.get('url','')} for r in results],'valid':valid,'research':research})
  data={'date':today,'pipeline_version':VERSION,'updated_at':datetime.now(CST).isoformat(),'events':out};dump(DATA/'ai_research_daily.json',data)
 p=DOCS/'index.html'
 if p.exists():
  h=p.read_text(encoding='utf8');h=re.sub(r'<!-- AI_START -->.*?<!-- AI_END -->','',h,flags=re.S);h=h.replace('</main>',section(data)+'</main>');p.write_text(h,encoding='utf8')
if __name__=='__main__':main()
