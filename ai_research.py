from __future__ import annotations
import json,os,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from html import escape
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from api_football import TEAM_MAP
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs';CST=timezone(timedelta(hours=8))
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def err_text(e):
 if isinstance(e,HTTPError):
  try: body=e.read().decode('utf-8','replace')[:180].replace('\n',' ')
  except: body=''
  return f'HTTP {e.code} {body}'
 return type(e).__name__
def post(url,payload,headers):
 req=Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
 with urlopen(req,timeout=45) as r:return json.loads(r.read().decode('utf-8'))
def query_name(cn):
 a=TEAM_MAP.get(cn,[]);return a[0] if a else cn
def tavily(q):
 k=os.getenv('TAVILY_API_KEY','').strip()
 if not k:raise RuntimeError('TAVILY_API_KEY 未配置')
 return post('https://api.tavily.com/search',{'query':q,'search_depth':'basic','max_results':4,'include_answer':False},{'Authorization':'Bearer '+k})
def summarize(match,results):
 k=os.getenv('DEEPSEEK_API_KEY','').strip()
 if not k:raise RuntimeError('DEEPSEEK_API_KEY 未配置')
 snippets='\n\n'.join(f"来源:{x.get('url','')}\n标题:{x.get('title','')}\n内容:{x.get('content','')[:1200]}" for x in results)
 prompt=f'''你是足球赛前事实核验助手。只基于下方搜索摘要，禁止补充外部常识、禁止猜测、禁止推荐下注。包含“可能、预计、存疑、may、likely、predicted”等词的内容必须放入 uncertain，绝不能放入 confirmed。推荐、赔率观点、tipster观点不得放入 confirmed。比赛：{match}。输出严格JSON：{{"confirmed":["仅明确事实"],"uncertain":["媒体推测或待确认"],"risks":["赛制/伤停/旅行等风险"],"summary":"不超过80字中文客观总结"}}。若摘要没有信息，数组写空。\n\n{snippets}'''
 data=post('https://api.deepseek.com/chat/completions',{'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'temperature':0.1,'response_format':{'type':'json_object'}},{'Authorization':'Bearer '+k})
 return json.loads(data['choices'][0]['message']['content'])
def fact_gate(research):
    """Never allow tentative language or betting opinions into confirmed facts."""
    hedges=['可能','预计','或将','存疑','待确认','疑似','大概率','有望','传闻','或许','may ','might ','likely','predicted','doubtful','expected']
    opinions=['推荐','看好','投注','赔率','best bet','value bet','tipster','预测']
    confirmed=[]; uncertain=list(research.get('uncertain',[]) or []); risks=list(research.get('risks',[]) or [])
    for item in research.get('confirmed',[]) or []:
        low=item.lower()
        if any(w.lower() in low for w in opinions):
            risks.append('已过滤推荐/观点文本：'+item);continue
        if any(w.lower() in low for w in hedges):
            uncertain.append(item);continue
        confirmed.append(item)
    # Deduplicate while preserving order.
    def unique(xs):
        out=[]
        for x in xs:
            if x not in out:out.append(x)
        return out
    return {'confirmed':unique(confirmed),'uncertain':unique(uncertain),'risks':unique(risks),'summary':research.get('summary','数据不足')}
def section(data):
 cards=[]
 for x in data.get('events',[]):
  r=x.get('research',{});src=' ｜ '.join(f'<a href="{escape(s["url"])}" target="_blank">{escape(s["title"][:40])}</a>' for s in x.get('sources',[]))
  cards.append(f"<div class='research'><h3>{escape(x['code'])} {escape(x['match'])}</h3><p><b>AI客观总结：</b>{escape(r.get('summary','数据不足'))}</p><p><b>已确认：</b>{escape('；'.join(r.get('confirmed',[])) or '无')}</p><p><b>待确认：</b>{escape('；'.join(r.get('uncertain',[])) or '无')}</p><p><b>风险：</b>{escape('；'.join(r.get('risks',[])) or '无')}</p><p class='small'><b>搜索来源：</b>{src or '无'}</p></div>")
 return '<!-- AI_START --><div class="card"><h2>AI 联网基本面研究</h2><p class="small">仅基于当日搜索结果提取事实；“待确认”不进入严格EV模型。搜索来源、摘要与时间均会保存。</p>'+(''.join(cards) if cards else '<p>今日无可搜索的中国竞彩可售比赛。</p>')+'</div><!-- AI_END -->'
def main():
 DATA.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True);today=datetime.now(CST).strftime('%Y-%m-%d');cache=load(DATA/'ai_research_daily.json',{})
 latest=load(DATA/'latest_zgzcw.json',{});events=latest.get('events',[]);closed=any('已停售' in str(e) for e in latest.get('errors',[]))
 if cache.get('date')==today and cache.get('pipeline_version')==2:data=cache
 elif not events or closed:data={'date':today,'events':[],'status':'无当前可售比赛，不搜索'}
 else:
  out=[]
  for e in events:
   home=query_name(e['home']);away=query_name(e['away']);q=f'{home} {away} injury suspension team news predicted lineup preview'
   try:
    sr=tavily(q);sources=[{'title':x.get('title',''), 'url':x.get('url','')} for x in sr.get('results',[])]
   except Exception as ex:
    sources=[];research={'confirmed':[],'uncertain':[],'risks':['Tavily搜索不可用：'+err_text(ex)],'summary':'AI联网搜索未完成'}
   else:
    try: research=summarize(home+' vs '+away,sr.get('results',[]))
    except Exception as ex: research={'confirmed':[],'uncertain':[],'risks':['DeepSeek总结不可用：'+err_text(ex)],'summary':'AI搜索已完成，但总结未完成'}
   research=fact_gate(research)
   out.append({'code':e['code'],'match':e['home']+' vs '+e['away'],'sources':sources,'research':research})
  data={'date':today,'pipeline_version':2,'updated_at':datetime.now(CST).isoformat(),'events':out};dump(DATA/'ai_research_daily.json',data)
 p=DOCS/'index.html'
 if p.exists():
  html=p.read_text(encoding='utf8');html=re.sub(r'<!-- AI_START -->.*?<!-- AI_END -->','',html,flags=re.S);html=html.replace('</main>',section(data)+'</main>');p.write_text(html,encoding='utf8')
if __name__=='__main__':main()
