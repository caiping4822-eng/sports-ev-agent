from __future__ import annotations
import json,re
from pathlib import Path
from html import escape
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs'
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def devig(o):
 x=[1/v for v in o];s=sum(x);return [v/s for v in x]
def pct(x):return f'{x*100:.1f}%'
def main():
 latest=load(DATA/'latest_zgzcw.json',{});events=latest.get('events',[]);bj=load(DATA/'latest_bjzs.json',{});ext=load(DATA/'latest_external_markets.json',{});api=load(DATA/'api_context.json',{});fund=load(DATA/'fundamentals_daily.json',{});ai=load(DATA/'ai_research_daily.json',{});hist=load(DATA/'market_history.json',[])
 fby={x['code']:x for x in fund.get('events',[])};aby={x['code']:x for x in ai.get('events',[])}
 decisions=[]
 for e in events:
  t=next((m for m in e.get('markets',[]) if m.get('market')=='1X2'),None);b=bj.get(e.get('analysis_match_id') or e.get('source_match_id'))
  if not t or not b:continue
  p=devig(b['current']);pc=[max(0,x-.02) for x in p];od=[t['home_win'],t['draw'],t['away_win']];labels=['主胜','平','客胜'];ev=[pc[i]*od[i]-1 for i in range(3)]
  ap=api.get(e['code'],{});fp=fby.get(e['code'],{});ar=aby.get(e['code'],{});er=ext.get(e['source_match_id'],{});books=len(er.get('books',[])) if er.get('available') else 0
  score=35 # China + average + market model exist
  if str(ap.get('status','')).startswith('已匹配'):score+=10
  if fp and fp.get('home_stats',{}).get('form') not in ('源未返回','-',''):score+=15
  if ar.get('sources'):score+=10
  if books>=3:score+=25
  if len(hist)>=2:score+=5
  conf='高' if score>=75 else '中' if score>=55 else '低'
  best_prob=max(range(3),key=lambda i:pc[i] if od[i]>=1.8 else -1)
  best_ev=max(range(3),key=lambda i:ev[i])
  strict=(books>=3 and score>=70 and ev[best_ev]>=.03)
  confirmed=ar.get('research',{}).get('confirmed',[]);uncertain=ar.get('research',{}).get('uncertain',[]);risks=ar.get('research',{}).get('risks',[])
  gaps=[]
  if books<3:gaps.append('外部同场机构不足3家')
  if not str(ap.get('status','')).startswith('已匹配'):gaps.append('API-Football未匹配')
  if not fp:gaps.append('赛季基本面未返回')
  if not ar.get('sources'):gaps.append('AI联网研究未完成')
  if len(hist)<2:gaps.append('盘口变化尚无第二次快照')
  decisions.append({'code':e['code'],'match':e['home']+' vs '+e['away'],'odds':od,'market_p':p,'conservative_p':pc,'confidence':score,'conf_label':conf,'strict':strict,'strict_i':best_ev,'forced_i':best_prob,'ev':ev,'confirmed':confirmed,'uncertain':uncertain,'risks':risks,'gaps':gaps})
 stricts=[d for d in decisions if d['strict']];forced=max(decisions,key=lambda d:d['conservative_p'][d['forced_i']]) if decisions else None
 def lines(d):
  i=d['strict_i'] if d['strict'] else d['forced_i'];lab=['主胜','平','客胜'][i]
  return f"<div class='decision'><h3>{escape(d['code'])} {escape(d['match'])}</h3><p><b>综合保守概率：</b>{pct(d['conservative_p'][i])} ｜ <b>中国竞彩：</b>{lab} @ {d['odds'][i]:.2f} ｜ <b>保守EV：</b>{d['ev'][i]*100:.1f}%</p><p><b>数据可信度：</b>{d['confidence']}分 / {d['conf_label']}</p><p><b>已确认：</b>{escape('；'.join(d['confirmed']) or '无')}</p><p><b>待确认：</b>{escape('；'.join(d['uncertain']) or '无')}</p><p><b>主要风险：</b>{escape('；'.join(d['risks']) or '无')}</p><p><b>数据缺口：</b>{escape('；'.join(d['gaps']) or '无')}</p></div>"
 if stricts:
  head='<h2>今日综合裁判结论：严格EV候选</h2>'+''.join(lines(d) for d in stricts)
 elif forced:
  i=forced['forced_i'];lab=['主胜','平','客胜'][i]
  head=f"<h2>今日综合裁判结论</h2><p class='pick'>严格EV：无候选</p><p><b>强制娱乐推荐：</b>{escape(forced['code'])} {escape(forced['match'])} — {lab} @ {forced['odds'][i]:.2f}</p><p>综合保守概率 {pct(forced['conservative_p'][i])} ｜ 保守EV {forced['ev'][i]*100:.1f}% ｜ 严格Kelly 0% ｜ 娱乐仓上限0.25%</p>"+lines(forced)
 else:head='<h2>今日综合裁判结论</h2><p>当前无中国竞彩可售比赛或无足够数据。</p>'
 per_cards=''.join("<div class='decision'><h3>"+escape(d['code'])+" "+escape(d['match'])+"</h3><p><b>本场强制娱乐：</b>"+['主胜','平','客胜'][d['forced_i']]+" @ "+f"{d['odds'][d['forced_i']]:.2f}"+" ｜ 保守概率 "+pct(d['conservative_p'][d['forced_i']])+" ｜ 保守EV "+f"{d['ev'][d['forced_i']]*100:.1f}%"+"</p><p><b>严格EV：</b>"+('候选' if d['strict'] else 'PASS')+" ｜ <b>可信度：</b>"+str(d['confidence'])+"分/"+d['conf_label']+" ｜ <b>Kelly：</b>0%"+"</p><p><b>已确认：</b>"+escape('；'.join(d['confirmed']) or '无')+"</p><p><b>主要风险：</b>"+escape('；'.join(d['risks']) or '无')+"</p><p><b>数据缺口：</b>"+escape('；'.join(d['gaps']) or '无')+"</p></div>" for d in decisions)
 section='<!-- DECISION_START --><div class="card decisionbox">'+head+"<h2>逐场综合裁判与强制娱乐结果</h2>"+per_cards+'</div><!-- DECISION_END -->'
 p=DOCS/'index.html'
 if p.exists():
  html=p.read_text(encoding='utf8');html=re.sub(r'<!-- DECISION_START -->.*?<!-- DECISION_END -->','',html,flags=re.S);html=html.replace('</header><main>','</header><main>'+section);p.write_text(html,encoding='utf8')
 dump(DATA/'decision_daily.json',{'decisions':decisions})
if __name__=='__main__':main()
