from __future__ import annotations
import json, os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from api_football import TEAM_MAP

ROOT=Path(__file__).parent; DATA=ROOT/'data'; DOCS=ROOT/'docs'; CST=timezone(timedelta(hours=8)); VERSION=5

def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def post(url,payload,headers):
 req=Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
 with urlopen(req,timeout=45) as r:return json.loads(r.read().decode('utf-8'))
def err(e):
 if isinstance(e,HTTPError):
  try:body=e.read().decode('utf8','replace')[:120].replace('\n',' ')
  except:body=''
  return f'HTTP {e.code} {body}'
 return type(e).__name__
def norm(x):return re.sub(r'[^a-z0-9]','',x.lower())
def relevant(result,home_aliases,away_aliases):
 raw=result.get('title','')+' '+result.get('content','')
 # Same-name women/youth pages are not evidence for the men's lottery fixture.
 if re.search(r"women|women's|女子|女足|\(\s*W\s*\)",raw,re.I):return False
 text=norm(raw)
 return any(norm(a) in text for a in home_aliases) and any(norm(a) in text for a in away_aliases)
def search(query):
 key=os.getenv('TAVILY_API_KEY','').strip()
 if not key:raise RuntimeError('TAVILY_API_KEY未配置')
 return post('https://api.tavily.com/search',{'query':query,'search_depth':'basic','max_results':6},{'Authorization':'Bearer '+key})
def summarize(match,results):
 key=os.getenv('DEEPSEEK_API_KEY','').strip()
 if not key:raise RuntimeError('DEEPSEEK_API_KEY未配置')
 snips='\n\n'.join(f"URL:{r['url']}\nTITLE:{r['title']}\nTEXT:{r.get('content','')[:1000]}" for r in results)
 prompt=f'''你是 DeepSeek 足球事实核验助手。仅使用以下已通过双方队名相关性过滤的搜索摘要，分析比赛 {match}。
所有输出必须使用简体中文。输出严格JSON：{{"confirmed":[],"uncertain":[],"risks":[],"summary":""}}。
confirmed只能包含摘要中明确写出的伤缺、停赛、首回合比分、官方赛程等；任何“可能/预计/或将/may/likely/predicted”必须写入uncertain；投注观点、赔率、推荐不得写入任何事实字段。来源不足或相互矛盾时，在risks中明确说明，不得补充常识或猜测。
{snips}'''
 data=post('https://api.deepseek.com/chat/completions',{'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'temperature':0.0,'response_format':{'type':'json_object'}},{'Authorization':'Bearer '+key})
 return json.loads(data['choices'][0]['message']['content'])
def section(data):
 cards=[]
 for item in data.get('events',[]):
  research=item['research']; meta=item.get('deepseek',{}); sources=' ｜ '.join(f'<a href="{escape(s["url"])}" target="_blank">{escape(s["title"][:45])}</a>' for s in item.get('sources',[]))
  success=bool(meta.get('success'))
  engine='DeepSeek 已调用（deepseek-chat）' if success else 'DeepSeek 未生成有效总结：'+meta.get('error','未调用')
  label='DeepSeek总结' if success else 'AI总结（未通过）'
  cards.append(f"<div class='research'><h3>{escape(item['code'])} {escape(item['match'])}</h3><p><b>搜索质量：</b>{escape(item['status'])}</p><p class='small'><b>总结引擎：</b>{escape(engine)}</p><p><b>{label}：</b>{escape(research.get('summary','数据不足'))}</p><p><b>已确认：</b>{escape('；'.join(research.get('confirmed',[]) or []) or '无')}</p><p><b>待确认：</b>{escape('；'.join(research.get('uncertain',[]) or []) or '无')}</p><p><b>风险：</b>{escape('；'.join(research.get('risks',[]) or []) or '无')}</p><p class='small'><b>有效来源：</b>{sources or '无'}</p></div>")
 return '<!-- AI_START --><div class="card"><h2>AI 联网基本面研究</h2><p class="small">仅保留双方队名同时匹配的来源；球队别名未知、来源少于2个、女子/女足同名页面、无关页面均不进入综合裁判。</p>'+''.join(cards)+'</div><!-- AI_END -->'
def main():
 DATA.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True); today=datetime.now(CST).strftime('%Y-%m-%d')
 cache=load(DATA/'ai_research_daily.json',{}); latest=load(DATA/'latest_zgzcw.json',{}); events=latest.get('events',[]); closed=any('已停售' in str(x) for x in latest.get('errors',[]))
 if cache.get('date')==today and cache.get('pipeline_version')==VERSION:data=cache
 else:
  out=[]
  for event in events if not closed else []:
   home_aliases=TEAM_MAP.get(event['home'],[]); away_aliases=TEAM_MAP.get(event['away'],[])
   if not home_aliases or not away_aliases:
    out.append({'code':event['code'],'match':event['home']+' vs '+event['away'],'status':'球队别名未确认，AI搜索跳过','sources':[],'valid':False,'deepseek':{'success':False,'provider':'DeepSeek','model':'deepseek-chat','error':'球队别名未确认，未调用'},'research':{'confirmed':[],'uncertain':[],'risks':['球队映射不足'],'summary':'不进入AI模型'}}); continue
   try:
    raw=search(f'{home_aliases[0]} {away_aliases[0]} injury suspension team news predicted lineup')
    results=[r for r in raw.get('results',[]) if relevant(r,home_aliases,away_aliases)]
    if len(results)<2:raise RuntimeError('相关来源不足2个')
    research=summarize(home_aliases[0]+' vs '+away_aliases[0],results)
    status=f'有效来源 {len(results)} 个'; deepseek={'success':True,'provider':'DeepSeek','model':'deepseek-chat'}; valid=True
   except Exception as ex:
    results=[]; reason=err(ex); research={'confirmed':[],'uncertain':[],'risks':['搜索/总结未通过：'+reason],'summary':'AI研究无效'}; status='AI研究无效'; deepseek={'success':False,'provider':'DeepSeek','model':'deepseek-chat','error':reason}; valid=False
   out.append({'code':event['code'],'match':event['home']+' vs '+event['away'],'status':status,'sources':[{'title':r.get('title',''),'url':r.get('url','')} for r in results],'valid':valid,'deepseek':deepseek,'research':research})
  data={'date':today,'pipeline_version':VERSION,'updated_at':datetime.now(CST).isoformat(),'events':out}; dump(DATA/'ai_research_daily.json',data)
 page=DOCS/'index.html'
 if page.exists():
  html=page.read_text(encoding='utf8'); html=re.sub(r'<!-- AI_START -->.*?<!-- AI_END -->','',html,flags=re.S); html=html.replace('</main>',section(data)+'</main>'); page.write_text(html,encoding='utf8')
if __name__=='__main__':main()
