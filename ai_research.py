from __future__ import annotations
import json, os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from api_football import TEAM_MAP

ROOT=Path(__file__).parent; DATA=ROOT/'data'; DOCS=ROOT/'docs'; CST=timezone(timedelta(hours=8)); VERSION=7

def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def post(url,payload,headers):
 req=Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
 with urlopen(req,timeout=45) as r:return json.loads(r.read().decode('utf-8'))
def err(e):
 if isinstance(e,HTTPError):
  try:body=e.read().decode('utf8','replace')[:160].replace('\n',' ')
  except:body=''
  return f'HTTP {e.code} {body}'
 return type(e).__name__
def norm(x):return re.sub(r'[^a-z0-9]','',x.lower())
def relevant(result,home_aliases,away_aliases):
 raw=result.get('title','')+' '+result.get('content','')
 # Same-name women/youth pages must never become evidence for a men's lottery fixture.
 if re.search(r"women|women's|女子|女足|\(\s*W\s*\)",raw,re.I):return False
 text=norm(raw)
 return any(norm(a) in text for a in home_aliases) and any(norm(a) in text for a in away_aliases)
def search(query):
 key=os.getenv('TAVILY_API_KEY','').strip()
 if not key:raise RuntimeError('TAVILY_API_KEY未配置')
 return post('https://api.tavily.com/search',{'query':query,'search_depth':'basic','max_results':4},{'Authorization':'Bearer '+key})
def collect_sources(home_aliases,away_aliases):
 home,away=home_aliases[0],away_aliases[0]
 # Three independent lanes prevent injury pages from monopolising the research.
 lanes=[
  ('伤停与阵容',f'{home} {away} injury suspension official team news lineup'),
  ('联赛背景与战意依据',f'{home} {away} standings table title race relegation qualification match preview'),
  ('近期状态与赛程',f'{home} {away} recent form results schedule rest days travel head to head preview'),
 ]
 selected=[];known=set();failures=[]
 for category,query in lanes:
  try:
   raw=search(query)
   kept=[x for x in raw.get('results',[]) if relevant(x,home_aliases,away_aliases)]
   if not kept:failures.append(category+'：未取得双方相关来源')
   for item in kept:
    url=item.get('url','')
    if not url or url in known:continue
    known.add(url)
    selected.append({**item,'category':category})
  except Exception as ex:
   failures.append(category+'：'+err(ex))
 # Enough material for a fact summary; each lane's absence remains visible as a risk.
 if len(selected)<2:raise RuntimeError('三路检索后相关来源不足2个；'+'；'.join(failures))
 return selected[:9],failures
def summarize(match,kickoff,results,lane_failures):
 key=os.getenv('DEEPSEEK_API_KEY','').strip()
 if not key:raise RuntimeError('DEEPSEEK_API_KEY未配置')
 snips='\n\n'.join(f"类别:{r['category']}\nURL:{r['url']}\nTITLE:{r['title']}\nTEXT:{r.get('content','')[:850]}" for r in results)
 prompt=f'''你是 DeepSeek 足球赛前事实核验助手。仅使用下面提供的搜索摘要，分析比赛：{match}，开赛时间：{kickoff}。
所有文本必须使用简体中文。严格返回 JSON，且必须包含以下字段：
{{"summary":"","competition_context":[],"motivation_evidence":[],"form_schedule":[],"confirmed":[],"uncertain":[],"risks":[]}}

规则：
1. competition_context 只写可验证的联赛/杯赛背景、积分排名、首回合比分、晋级或保级条件；没有可靠资料则写“源未返回”。
2. motivation_evidence 只写可验证的战意依据，例如“距欧战区2分”“本场取胜可升至第2”“次回合需追回1球”。禁止写“战意强/必胜/无心恋战”等主观心理判断；资料不足时写“源未返回”。
3. form_schedule 只写摘要明确给出的近期战绩、主客场趋势、休息天数、连续客场或赛程信息；不可由常识推断。
4. confirmed 只能写明确伤缺、停赛、官方赛程、已确认首回合赛果等。任何“可能/预计/或将/may/likely/predicted”必须写入 uncertain。
5. 若来源过期、互相矛盾、只有预测站、或某一路检索无相关来源，写入 risks。不得补充网页摘要以外的事实，不得给投注建议。
6. summary 用2至4句概括，只描述事实与资料边界。
三路检索未取得材料：{'; '.join(lane_failures) if lane_failures else '无'}

搜索摘要：
{snips}'''
 data=post('https://api.deepseek.com/chat/completions',{'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'temperature':0.0,'response_format':{'type':'json_object'}},{'Authorization':'Bearer '+key})
 result=json.loads(data['choices'][0]['message']['content'])
 for field in ('competition_context','motivation_evidence','form_schedule','confirmed','uncertain','risks'):
  if not isinstance(result.get(field),list):result[field]=[]
 result['summary']=str(result.get('summary',''))
 return result
def text_list(value,empty='源未返回'):
 return '；'.join(value or []) or empty
def section(data):
 cards=[]
 for item in data.get('events',[]):
  research=item['research']; meta=item.get('deepseek',{}); success=bool(meta.get('success'))
  engine='DeepSeek 已调用（deepseek-chat）' if success else 'DeepSeek 未生成有效总结：'+meta.get('error','未调用')
  sources=' ｜ '.join(f'<a href="{escape(s["url"])}" target="_blank">[{escape(s.get("category","来源"))}] {escape(s["title"][:42])}</a>' for s in item.get('sources',[]))
  label='DeepSeek综合总结' if success else 'AI总结（未通过）'
  cards.append(f"<div class='research'><h3>{escape(item['code'])} {escape(item['match'])}</h3><p><b>搜索质量：</b>{escape(item['status'])}</p><p class='small'><b>总结引擎：</b>{escape(engine)}</p><p><b>{label}：</b>{escape(research.get('summary','数据不足'))}</p><p><b>联赛/杯赛背景：</b>{escape(text_list(research.get('competition_context')))}</p><p><b>可验证的战意依据：</b>{escape(text_list(research.get('motivation_evidence')))}</p><p><b>近期状态与赛程：</b>{escape(text_list(research.get('form_schedule')))}</p><p><b>已确认伤停/事实：</b>{escape(text_list(research.get('confirmed'),'无'))}</p><p><b>待确认：</b>{escape(text_list(research.get('uncertain'),'无'))}</p><p><b>来源冲突与主要风险：</b>{escape(text_list(research.get('risks'),'无'))}</p><p class='small'><b>有效来源：</b>{sources or '无'}</p></div>")
 return '<!-- AI_START --><div class="card"><h2>AI 联网基本面研究</h2><p class="small">三路检索：伤停与阵容、联赛背景与战意依据、近期状态与赛程。仅保留双方队名同时匹配的来源；女子/女足同名页面、来源少于2个、无关页面均不进入综合裁判。“战意”仅展示可核验的积分/赛制依据，不推测球队心理。</p>'+''.join(cards)+'</div><!-- AI_END -->'
def main():
 DATA.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True); today=datetime.now(CST).strftime('%Y-%m-%d')
 cache=load(DATA/'ai_research_daily.json',{}); latest=load(DATA/'latest_zgzcw.json',{}); events=latest.get('events',[]); closed=any('已停售' in str(x) for x in latest.get('errors',[]))
 if cache.get('date')==today and cache.get('pipeline_version')==VERSION:data=cache
 else:
  out=[]
  for event in events if not closed else []:
   home_aliases=TEAM_MAP.get(event['home'],[]); away_aliases=TEAM_MAP.get(event['away'],[])
   if not home_aliases or not away_aliases:
    out.append({'code':event['code'],'match':event['home']+' vs '+event['away'],'status':'球队别名未确认，AI搜索跳过','sources':[],'valid':False,'deepseek':{'success':False,'provider':'DeepSeek','model':'deepseek-chat','error':'球队别名未确认，未调用'},'research':{'summary':'不进入AI模型','competition_context':[],'motivation_evidence':[],'form_schedule':[],'confirmed':[],'uncertain':[],'risks':['球队映射不足']}});continue
   try:
    results,lane_failures=collect_sources(home_aliases,away_aliases)
    research=summarize(home_aliases[0]+' vs '+away_aliases[0],event.get('kickoff','未知'),results,lane_failures)
    status=f'有效来源 {len(results)} 个（伤停/背景/赛程三路）';deepseek={'success':True,'provider':'DeepSeek','model':'deepseek-chat'};valid=True
   except Exception as ex:
    results=[];reason=err(ex);research={'summary':'AI研究无效','competition_context':[],'motivation_evidence':[],'form_schedule':[],'confirmed':[],'uncertain':[],'risks':['搜索/总结未通过：'+reason]};status='AI研究无效';deepseek={'success':False,'provider':'DeepSeek','model':'deepseek-chat','error':reason};valid=False
   out.append({'code':event['code'],'match':event['home']+' vs '+event['away'],'status':status,'sources':[{'title':r.get('title',''),'url':r.get('url',''),'category':r.get('category','来源')} for r in results],'valid':valid,'deepseek':deepseek,'research':research})
  data={'date':today,'pipeline_version':VERSION,'updated_at':datetime.now(CST).isoformat(),'events':out};dump(DATA/'ai_research_daily.json',data)
 page=DOCS/'index.html'
 if page.exists():
  html=page.read_text(encoding='utf8');html=re.sub(r'<!-- AI_START -->.*?<!-- AI_END -->','',html,flags=re.S);html=html.replace('</main>',section(data)+'</main>');page.write_text(html,encoding='utf8')
if __name__=='__main__':main()
